"""
ClearPath API Server — FastAPI application.

Endpoints:
  POST /api/verify           Accept 3 PDF uploads, return job_id
  GET  /api/verify/{id}/status   SSE stream of log lines + final results
  GET  /api/verify/{id}/report   Serve generated PDF report
"""
from __future__ import annotations

import asyncio
import json
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

app = FastAPI(title="ClearPath API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory job store
# Each entry: { status, queue, results, report_path, product_id, error }
# ---------------------------------------------------------------------------
jobs: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# POST /api/verify
# ---------------------------------------------------------------------------

@app.post("/api/verify")
async def start_verification(
    background_tasks: BackgroundTasks,
    bill_of_lading: UploadFile,
    invoice: UploadFile,
    packing_list: UploadFile,
):
    """Accept 3 PDF uploads, kick off background verification pipeline."""
    job_id = str(uuid.uuid4())
    log_queue: asyncio.Queue = asyncio.Queue()

    jobs[job_id] = {
        "status": "running",
        "queue": log_queue,
        "results": None,
        "report_path": None,
        "product_id": None,
        "error": None,
    }

    # Save uploaded files to a temp dir
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"clearpath_{job_id[:8]}_"))

    async def _save(upload: UploadFile, dest: Path) -> None:
        content = await upload.read()
        dest.write_bytes(content)

    bol_path = tmp_dir / "bill_of_lading.pdf"
    inv_path = tmp_dir / "invoice.pdf"
    pl_path = tmp_dir / "packing_list.pdf"

    await _save(bill_of_lading, bol_path)
    await _save(invoice, inv_path)
    await _save(packing_list, pl_path)

    # Lazy import to avoid loading PyTorch at startup
    from api.pipeline import run_pipeline  # noqa: PLC0415

    background_tasks.add_task(
        run_pipeline,
        job_id=job_id,
        bol_path=str(bol_path),
        inv_path=str(inv_path),
        pl_path=str(pl_path),
        log_queue=log_queue,
        job_store=jobs,
    )

    return {"job_id": job_id}


# ---------------------------------------------------------------------------
# GET /api/verify/{job_id}/status — SSE stream
# ---------------------------------------------------------------------------

@app.get("/api/verify/{job_id}/status")
async def verification_status(job_id: str):
    """Stream real-time log lines, then emit a final 'complete' event."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    queue: asyncio.Queue = job["queue"]

    async def event_stream():
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                # Keep-alive ping
                yield "event: ping\ndata: {}\n\n"
                continue

            if item is None:
                # Sentinel — pipeline finished
                break

            yield f"data: {json.dumps(item)}\n\n"

        # Emit final complete event with full results
        results = job.get("results") or {}
        error = job.get("error")
        payload = {"results": results, "error": error, "status": job.get("status")}
        yield f"event: complete\ndata: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# GET /api/verify/{job_id}/report — PDF download
# ---------------------------------------------------------------------------

@app.get("/api/verify/{job_id}/report")
async def get_report(job_id: str):
    """Serve the generated PDF report card."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    report_path = job.get("report_path")
    if not report_path or not Path(report_path).exists():
        raise HTTPException(status_code=404, detail="Report not yet available")

    product_id = job.get("product_id", job_id)
    return FileResponse(
        path=report_path,
        media_type="application/pdf",
        filename=f"clearpath_report_{product_id}.pdf",
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok"}
