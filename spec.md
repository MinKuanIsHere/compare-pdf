# PDF Compare MVP Spec (Backend + UI)

## Scope
- Local/offline PDF diff tool with API + React/Vite UI, orchestrated via Docker Compose.
- Use existing pipeline (extract → match → diff → annotate → export). No LLM.
- Dual annotations: B-view highlights additions/changes; A-view highlights deletions/changes.

## Functional Requirements
1) Upload & Run
   - User uploads two PDFs (fileA, fileB) via UI → `POST /compare`.
   - Optional params: `text_threshold` (float, default 0.8), `image_threshold` (int, pHash distance default 5).
2) Progress
   - UI polls `GET /status/{job_id}` until `state` in {queued, running, done, error}.
   - `progress` list of step logs: {step, status, message, ts}.
3) Results
   - `GET /result/{job_id}` returns:
     - `files`: `file_a`, `file_b` (name, size_bytes, pages, download_url).
     - `outputs`: `annotated_a_pdf`, `annotated_b_pdf`, `extracted_a_json`, `extracted_b_json`, `matched_json`, `diff_json`, `summary_md`, `detailed_json`.
     - `diff_counts`: added, deleted, modified counts per type (paragraphs/images/tables).
   - Static serving for all file URLs.
4) UI
   - Upload panel: dropzone for two PDFs, threshold inputs, Run button.
   - Progress indicator reflecting `status` polling.
   - Preview modes:
     - Side-by-side original fileA/fileB.
     - Annotated view (toggle A-view/B-view).
   - Change list: grouped by type (added/deleted/modified), shows text snippet or UID; clicking scrolls PDF viewer to `page` + `bbox`.
   - Downloads for all output files.
5) Storage & Lifecycle
   - Job workspace: `output/{job_id}/`.
   - Keep originals once (no duplication), reuse for serving; cleanup policy: best-effort TTL (configurable) or manual clean (MVP: manual script).

## API Contracts (FastAPI)
- `POST /compare`
  - multipart: `file_a` (pdf), `file_b` (pdf); form fields: `text_threshold` (float, optional), `image_threshold` (int, optional).
  - 200: `{ "job_id": "uuid", "state": "queued" }`
  - 400: missing/invalid files.
- `GET /status/{job_id}`
  - 200: `{ "job_id": "...", "state": "queued|running|done|error", "progress": [ { "step": "...", "status": "pending|running|done|error", "message": "...", "ts": "iso8601" } ], "error": "..."? }`
  - 404: job not found.
- `GET /result/{job_id}`
  - 200: `{ "job_id": "...", "state": "done", "files": { "file_a": {...}, "file_b": {...} }, "outputs": {...}, "diff_counts": {...} }`
  - 409: job not done.
  - 404: job not found.

## Annotation Rules
- B-view (`*_annotated_b.pdf`): highlight new/modified items from B perspective (existing behavior).
- A-view (`*_annotated_a.pdf`): highlight deleted/modified items from A perspective (needs implementation).
- Highlight color stays red; bbox from matched/diff data.

## BBox to Viewer Mapping
- Coordinates are PyMuPDF points (72 dpi). Provide helper to convert `{page, bbox}` to pdf.js viewport offsets given current zoom/scale. UI uses this to scroll on change click.

## Docker Compose (MVP expectation)
- Services:
  - `api`: FastAPI app exposing endpoints + static file serving; mounts repo and `output/`.
  - `ui`: React/Vite built assets served (could be `npm run dev` or static from `api` in prod).
- Shared volume: `output/` for results.
- Expose ports: API (e.g., 8000), UI (e.g., 5173 or via API static).

## Testing (TDD)
- Pipeline unit tests: extract/match/diff on tiny fixture PDFs; thresholds override tests.
- End-to-end API test: upload fixture PDFs via `TestClient`, poll status, fetch result, assert files exist (including annotated A/B PDFs) and JSON keys.
- BBox helper unit tests: scaling math.
- UI tests: component form validation; msw-based flow for submit → polling → render change list → scroll call with expected bbox.

## Non-Goals (MVP)
- No LLM summaries.
- No persistent database; jobs tracked in memory + filesystem.
- No auth/multi-tenant isolation beyond per-job directories.
