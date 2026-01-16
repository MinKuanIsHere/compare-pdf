import os
import threading
import traceback
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

import fitz  # type: ignore
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from pipeline import run_pipeline

OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", "output"))
# Simple limits
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 50 * 1024 * 1024))  # 50MB default

app = FastAPI(title="PDF Compare API", version="0.1.0")

# Simple CORS for local dev UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Job:
    def __init__(self, job_id: str, workspace: Path):
        self.job_id = job_id
        self.workspace = workspace
        self.state = "queued"
        self.progress = []
        self.error = None
        self.result: Dict[str, Any] = {}
        self.created_at = datetime.utcnow()

    def add_progress(self, step: str, status: str = "running", message: str = ""):
        self.progress.append(
            {"step": step, "status": status, "message": message, "ts": datetime.utcnow().isoformat() + "Z"}
        )


JOBS: Dict[str, Job] = {}
JOBS_LOCK = threading.Lock()


def sanitize_filename(filename: str) -> str:
    # Keep only basename to avoid traversal; strip path separators
    return Path(filename).name.replace("/", "_").replace("\\", "_")


def save_upload(upload: UploadFile, dest: Path) -> Path:
    data = upload.file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
    # Basic PDF signature check
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF file")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        f.write(data)
    return dest


def get_pdf_meta(path: Path) -> Dict[str, Any]:
    try:
        doc = fitz.open(path)
        pages = len(doc)
        doc.close()
    except Exception:
        pages = None
    stat = path.stat()
    return {"name": path.name, "size_bytes": stat.st_size, "pages": pages}


def run_job(job: Job, file_a: Path, file_b: Path, text_threshold: float, image_threshold: int):
    job.state = "running"
    job.add_progress("start", "running", "Job started")

    def progress_cb(step, status, message=""):
        job.add_progress(step, status, message)

    try:
        outputs = run_pipeline(
            str(file_a),
            str(file_b),
            str(job.workspace),
            progress_cb=progress_cb,
            text_threshold=text_threshold,
            image_threshold=image_threshold,
        )
        job.state = "done"
        job.result = {
            "files": {
                "file_a": {**get_pdf_meta(file_a), "download_url": f"/files/{job.job_id}/{file_a.name}"},
                "file_b": {**get_pdf_meta(file_b), "download_url": f"/files/{job.job_id}/{file_b.name}"},
            },
            "outputs": {
                "annotated_a_pdf": f"/files/{job.job_id}/{Path(outputs['annotated_pdf_a']).name}",
                "annotated_b_pdf": f"/files/{job.job_id}/{Path(outputs['annotated_pdf_b']).name}",
                "extracted_a_json": f"/files/{job.job_id}/{Path(outputs['extracted_a']).name}",
                "extracted_b_json": f"/files/{job.job_id}/{Path(outputs['extracted_b']).name}",
                "matched_json": f"/files/{job.job_id}/{Path(outputs['matched']).name}",
                "diff_json": f"/files/{job.job_id}/{Path(outputs['diffs']).name}",
                "summary_md": f"/files/{job.job_id}/{Path(outputs['summary_md']).name}",
                "detailed_json": f"/files/{job.job_id}/{Path(outputs['detailed_json']).name}",
            },
        }
        job.add_progress("done", "done", "Job completed")
    except Exception as e:
        job.state = "error"
        # Attach traceback for easier debugging while keeping message concise
        tb = traceback.format_exc()
        job.error = f"{e}"
        job.add_progress("error", "error", job.error)
        job.add_progress("traceback", "error", tb)


@app.post("/compare")
async def compare(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    text_threshold: float = Form(0.8),
    image_threshold: int = Form(5),
):
    if not (file_a.content_type and file_a.content_type.endswith("pdf")):
        raise HTTPException(status_code=400, detail="file_a must be a PDF")
    if not (file_b.content_type and file_b.content_type.endswith("pdf")):
        raise HTTPException(status_code=400, detail="file_b must be a PDF")

    job_id = str(uuid.uuid4())
    workspace = OUTPUT_ROOT / job_id
    workspace.mkdir(parents=True, exist_ok=True)

    path_a = save_upload(file_a, workspace / file_a.filename)
    path_b = save_upload(file_b, workspace / file_b.filename)

    job = Job(job_id, workspace)
    with JOBS_LOCK:
        JOBS[job_id] = job

    thread = threading.Thread(
        target=run_job, args=(job, path_a, path_b, text_threshold, image_threshold), daemon=True
    )
    thread.start()

    return {"job_id": job_id, "state": job.state}


@app.get("/status/{job_id}")
def status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.job_id,
        "state": job.state,
        "progress": job.progress,
        "error": job.error,
    }


@app.get("/result/{job_id}")
def result(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.state != "done":
        raise HTTPException(status_code=409, detail="Job not completed")
    return {"job_id": job.job_id, "state": job.state, **job.result}


@app.get("/files/{job_id}/{filename}")
def files(job_id: str, filename: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    safe_name = sanitize_filename(filename)
    path = job.workspace / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


@app.get("/")
def root():
    return {"message": "PDF Compare API"}
