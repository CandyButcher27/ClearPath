"""
Orchestrates the full ClearPath verification pipeline:
  PDF → DocStruct → markdown → schema_bridge → normalizer → report PDF
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup: make DocStruct and backend importable.
# This module is imported after run.py has already inserted project_root and
# DocStruct dir into sys.path, but we guard here as well.
# ---------------------------------------------------------------------------
_api_dir = Path(__file__).parent
_project_root = _api_dir.parent
_docstruct_dir = _project_root / "DocStruct"
_backend_dir = _project_root / "backend"

for _p in [str(_project_root), str(_docstruct_dir), str(_backend_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# DocStruct imports (relative to DocStruct/ directory on sys.path)
from main import process_pdf_true_hybrid  # noqa: E402
from pipeline.markdown_serializer import document_to_markdown  # noqa: E402

# Backend imports
from normalizer import ShipmentProcessor  # noqa: E402
from generate_report_card import ReportCardGenerator  # noqa: E402

from api.schema_bridge import assemble_shipment  # noqa: E402


# ---------------------------------------------------------------------------
# Log helper
# ---------------------------------------------------------------------------

def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


async def _log(queue: asyncio.Queue, level: str, message: str) -> None:
    await queue.put({"timestamp": _ts(), "level": level, "message": message})


# ---------------------------------------------------------------------------
# DocStruct wrapper (synchronous — runs in thread pool)
# ---------------------------------------------------------------------------

def _run_docstruct(pdf_path: str, output_json: str) -> object:
    """Call DocStruct true-hybrid pipeline. Returns Document object."""
    return process_pdf_true_hybrid(
        pdf_path=pdf_path,
        output_path=output_json,
        detector_type="doclaynet",
    )


# ---------------------------------------------------------------------------
# Main pipeline coroutine
# ---------------------------------------------------------------------------

async def run_pipeline(
    job_id: str,
    bol_path: str,
    inv_path: str,
    pl_path: str,
    log_queue: asyncio.Queue,
    job_store: dict,
) -> None:
    """
    Full verification pipeline. All heavy work runs via asyncio.to_thread so
    the event loop stays unblocked. Results and report path are written to
    job_store[job_id] when complete.
    """
    try:
        await _log(log_queue, "SYSTEM", "ClearPath Verification Engine v3.1.4 — initializing")
        await _log(log_queue, "INFO", f"Job {job_id} | Received 3 document payloads")

        tmp_dir = Path(tempfile.mkdtemp(prefix="clearpath_"))

        # ----------------------------------------------------------------
        # Stage 1: DocStruct layout extraction (x3)
        # ----------------------------------------------------------------
        await _log(log_queue, "INFO", "Extracting layout: Bill of Lading…")
        bol_json = str(tmp_dir / "bol_layout.json")
        bol_doc = await asyncio.to_thread(_run_docstruct, bol_path, bol_json)
        bol_blocks = sum(len(p.blocks) for p in bol_doc.pages)
        await _log(log_queue, "OK", f"Bill of Lading: {bol_blocks} blocks extracted")

        await _log(log_queue, "INFO", "Extracting layout: Invoice…")
        inv_json = str(tmp_dir / "inv_layout.json")
        inv_doc = await asyncio.to_thread(_run_docstruct, inv_path, inv_json)
        inv_blocks = sum(len(p.blocks) for p in inv_doc.pages)
        await _log(log_queue, "OK", f"Invoice: {inv_blocks} blocks extracted")

        await _log(log_queue, "INFO", "Extracting layout: Packing List…")
        pl_json = str(tmp_dir / "pl_layout.json")
        pl_doc = await asyncio.to_thread(_run_docstruct, pl_path, pl_json)
        pl_blocks = sum(len(p.blocks) for p in pl_doc.pages)
        await _log(log_queue, "OK", f"Packing List: {pl_blocks} blocks extracted")

        # ----------------------------------------------------------------
        # Stage 2: Convert to markdown
        # ----------------------------------------------------------------
        await _log(log_queue, "INFO", "Serializing extracted blocks to text…")
        bol_md = document_to_markdown(bol_doc)
        inv_md = document_to_markdown(inv_doc)
        pl_md = document_to_markdown(pl_doc)
        await _log(log_queue, "OK", "Markdown serialization complete")

        # ----------------------------------------------------------------
        # Stage 3: Rule-based field extraction
        # ----------------------------------------------------------------
        await _log(log_queue, "INFO", "Parsing structured fields from extracted text…")
        structured = await asyncio.to_thread(assemble_shipment, bol_md, inv_md, pl_md)
        category = structured.get("category", "General")
        inv_items = len(structured.get("invoice", {}).get("line_items", []))
        pl_items = len(structured.get("packing_list", {}).get("items", []))
        await _log(log_queue, "OK",
                   f"Fields extracted | category={category} | "
                   f"invoice line items={inv_items} | packing list items={pl_items}")

        # ----------------------------------------------------------------
        # Stage 4: Cross-document validation
        # ----------------------------------------------------------------
        await _log(log_queue, "INFO", "Running cross-document validation (16 checks)…")
        processor = ShipmentProcessor(structured)
        normalized = await asyncio.to_thread(processor.process)

        flags = normalized.get("inconsistency_flags", {})
        flagged_count = sum(
            1 for cat in flags.values() if isinstance(cat, dict)
            for f in cat.values() if isinstance(f, dict) and f.get("is_flagged")
        )
        await _log(log_queue, "WARN" if flagged_count else "OK",
                   f"Validation complete — {flagged_count} flag(s) raised")

        # Emit individual flag summaries
        for cat_name, cat_data in flags.items():
            if not isinstance(cat_data, dict):
                continue
            for flag_name, flag_data in cat_data.items():
                if isinstance(flag_data, dict) and flag_data.get("is_flagged"):
                    label = flag_name.replace("_", " ").upper()
                    await _log(log_queue, "WARN", f"  FLAG: {label}")

        # ----------------------------------------------------------------
        # Stage 5: Generate PDF report
        # ----------------------------------------------------------------
        await _log(log_queue, "INFO", "Generating PDF report card…")
        report_path = str(tmp_dir / "report.pdf")

        success = await asyncio.to_thread(
            ReportCardGenerator.generate_from_data,
            [normalized],
            normalized.get("product_id", job_id),
            report_path,
        )

        if success:
            await _log(log_queue, "OK", f"Report generated: {Path(report_path).name}")
        else:
            await _log(log_queue, "WARN", "Report generation encountered issues — partial output saved")

        await _log(log_queue, "SYSTEM", "Verification complete — certificate payload ready")

        # ----------------------------------------------------------------
        # Store results
        # ----------------------------------------------------------------
        job_store[job_id]["results"] = normalized
        job_store[job_id]["report_path"] = report_path
        job_store[job_id]["status"] = "complete"
        job_store[job_id]["product_id"] = normalized.get("product_id", job_id)

    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        await _log(log_queue, "WARN", f"Pipeline error: {exc}")
        await _log(log_queue, "SYSTEM", "Partial results may still be available")
        job_store[job_id]["status"] = "error"
        job_store[job_id]["error"] = str(exc)
        job_store[job_id]["traceback"] = tb

    finally:
        # Signal the SSE stream that we're done
        await log_queue.put(None)  # sentinel
