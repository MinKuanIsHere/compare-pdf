# Plan: Web UI for Local PDF Comparison (TDD)

## Goals
- Build a local, offline-friendly PDF diff tool with API + React/Vite UI on top of existing pipeline.
- Keep current pipeline logic (extract → match → diff → annotate → export) as the single source of truth.
- Drive changes with TDD: write/extend tests per feature before implementation.

## Milestones & TDD Tasks
1) **Pipeline Hardening**
   - Add unit tests for `pdf_utils.extract_content`, `matcher.match_all`, `differ.diff_all` using small fixture PDFs (create minimal synthetic PDFs in tests).
   - Add regression test that runs `main.main` on fixtures and asserts outputs (JSON shape, annotated PDF exists).
   - Add configurable thresholds via env/args; test defaults and overrides.

2) **Backend API (FastAPI)**
   - Endpoints:
     - `POST /compare` (multipart: pdf_a, pdf_b, optional params) → job id.
     - `GET /status/{job_id}` → state + progress log.
     - `GET /result/{job_id}` → metadata including original files and all outputs:
       - Originals: `file_a`, `file_b` (names/size/page count + download URLs).
       - Outputs: `annotated_a_pdf`, `annotated_b_pdf`, `extracted_json_a`, `extracted_json_b`, `matched_json`, `diff_json`, `summary_md`, `detailed_json`.
     - Static file serving for outputs and originals (stored once, not duplicated).
   - Job runner wraps existing pipeline; writes stepwise status logs and captures errors (with traceback).
   - Tests:
     - Use `TestClient` to post fixture PDFs, poll status, fetch result, and assert files exist + JSON keys.
     - Error cases: missing files, invalid PDF, job not found.

3) **Dual Annotation & BBox-to-Viewer Mapping**
   - Define coordinate contract (PyMuPDF uses points at 72 DPI).
   - Produce annotated PDFs for both perspectives: `*_annotated_b.pdf` (add/modify highlights) and `*_annotated_a.pdf` (show deletes/changes from A view).
   - Provide helper to convert `page` + `bbox` to pdf.js viewport offsets.
   - Tests: pure function tests for bbox scaling given viewport sizes and zoom levels; integration asserts both annotated files are generated and non-empty.

4) **Front-End (React/Vite)**
   - Pages:
     - Upload & run: dropzone for two PDFs, parameter fields, Run button, progress indicator.
     - Result view: embedded pdf.js viewer for annotated PDF, side panel listing changes (added/deleted/modified) with click-to-scroll via `page` + `bbox`.
     - Downloads for annotated PDF, JSON, MD.
   - State: poll `/status/{job_id}` until done; then fetch `/result/{job_id}`.
   - Tests:
     - Component tests for upload form validation.
     - Integration test (msw) mocking API: submit run, poll status, render diff list, click scroll function called with correct bbox.

5) **Packaging & Ops**
   - Docker: extend current `Dockerfile`/`docker-compose.yml` to include API + UI (multi-stage build for Vite assets).
   - CLI fallback: keep `python main.py` working for headless use.
   - Tests: build succeeds locally; API e2e test via docker-compose in CI matrix (optional).

## Definition of Done
- Green test suite covering pipeline core, API endpoints, bbox mapping, and key UI flows.
- `POST /compare` → annotated PDF + reports downloadable; UI shows changes and scroll-to-diff works.
- Dockerized run: `docker compose up` serves API+UI locally.
- Existing CLI flow remains functional.
