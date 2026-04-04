"""
ClearPath Backend â€” Flask API Server.

Receives PDF uploads from the React frontend, processes them through the
LLMWhisperer â†’ Gemini â†’ Normalizer pipeline, and returns the normalised
audit results.
"""

import json
import logging
import os
import re
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, after_this_request, jsonify, request, send_file
from flask_cors import CORS

from normalizer import ShipmentProcessor
from pdf_parser import extract_text_from_pdf
from structurer import (
    build_shipment,
    detect_category,
    structure_bill_of_lading,
    structure_category_metadata,
    structure_invoice,
    structure_packing_list,
    structure_shipment_document_bundle,
)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

# Load .env from the backend directory
load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                re.compile(r"^http://localhost(?::\d+)?$"),
                re.compile(r"^http://127\.0\.0\.1(?::\d+)?$"),
                re.compile(r"^http://\[::1\](?::\d+)?$"),
            ]
        }
    },
)

# Temp directory for uploaded files (cleaned up after processing)
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Maximum upload size: 16 MB per file
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

REQUIRED_FILES = ["bill_of_lading", "invoice", "packing_list"]

# In-memory session log/event store (hackathon scope, single process)
_session_lock = threading.Lock()
_session_events: dict[str, list[dict]] = {}
_session_status: dict[str, str] = {}
_session_condition: dict[str, threading.Condition] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _ensure_session(session_id: str) -> None:
    with _session_lock:
        if session_id not in _session_events:
            _session_events[session_id] = []
            _session_status[session_id] = "running"
            _session_condition[session_id] = threading.Condition()


def _append_session_event(session_id: str, level: str, message: str, *, phase: str = "system") -> None:
    _ensure_session(session_id)
    event = {
        "timestamp": _now_iso(),
        "level": level,
        "phase": phase,
        "message": message,
    }
    with _session_lock:
        _session_events[session_id].append(event)
        cond = _session_condition[session_id]
    with cond:
        cond.notify_all()


def _set_session_status(session_id: str, status: str) -> None:
    _ensure_session(session_id)
    with _session_lock:
        _session_status[session_id] = status
        cond = _session_condition[session_id]
    with cond:
        cond.notify_all()


def _iter_flag_items(normalized: dict):
    flags_root = (normalized or {}).get("inconsistency_flags", {})
    if not isinstance(flags_root, dict):
        return
    for category, checks in flags_root.items():
        if not isinstance(checks, dict):
            continue
        for flag_name, payload in checks.items():
            yield category, flag_name, payload


def _compute_completeness(raw_shipment: dict) -> float:
    filled = 0
    total = 0

    def walk(node):
        nonlocal filled, total
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
        else:
            total += 1
            if node not in (None, "", [], {}):
                filled += 1

    walk(raw_shipment or {})
    if total == 0:
        return 0.0
    return round((filled / total) * 100, 2)


def _build_explainability(normalized: dict, raw_shipment: dict) -> dict:
    items: list[dict] = []
    total_checks = 0
    flagged_checks = 0

    severity_map = {
        "scac_missing": "high",
        "hazmat_mismatch": "high",
        "tax_calculation_error": "high",
        "weight_mismatch": "medium",
        "destination_address_mismatch": "medium",
    }

    for category, flag_name, payload in _iter_flag_items(normalized):
        if not isinstance(payload, dict):
            continue
        total_checks += 1
        is_flagged = bool(payload.get("is_flagged"))
        if is_flagged:
            flagged_checks += 1
        evidence = []
        source_fields = []
        for k, v in payload.items():
            if k == "is_flagged":
                continue
            source_fields.append(k)
            if isinstance(v, (str, int, float, bool)):
                evidence.append({"path": f"{category}.{flag_name}.{k}", "value": v})
            elif isinstance(v, list) and v:
                evidence.append({"path": f"{category}.{flag_name}.{k}", "value": f"{len(v)} entries"})

        score = payload.get("score")
        confidence = 0.7
        if isinstance(score, (int, float)):
            confidence = round(max(0.2, min(0.99, float(score) / 100.0)), 2)

        threshold_text = f"score < 75" if isinstance(score, (int, float)) else "rule-specific threshold"
        reason = (
            f"{flag_name.replace('_', ' ').title()} check {'failed' if is_flagged else 'passed'} "
            f"using {threshold_text}."
        )

        items.append(
            {
                "id": f"{category}:{flag_name}",
                "category": category,
                "flag_name": flag_name,
                "is_flagged": is_flagged,
                "severity": severity_map.get(flag_name, "medium" if is_flagged else "low"),
                "confidence": confidence,
                "rule": reason,
                "threshold": threshold_text,
                "source_fields": source_fields,
                "evidence": evidence[:6],
            }
        )

    completeness = _compute_completeness(raw_shipment)
    return {
        "items": items,
        "summary": {
            "total_checks": total_checks,
            "flagged_checks": flagged_checks,
            "completeness_index": completeness,
        },
    }


def _build_telemetry(
    *,
    started_at: float,
    extracted_texts: dict[str, str],
    explainability: dict,
    fallback_used: bool,
    parse_retries: int,
) -> dict:
    total_duration_ms = int((time.perf_counter() - started_at) * 1000)
    chars_extracted = sum(len(v or "") for v in extracted_texts.values())
    chars_sent = chars_extracted  # coarse estimate for now
    summary = explainability.get("summary", {}) if isinstance(explainability, dict) else {}
    total_checks = int(summary.get("total_checks", 0) or 0)
    flagged_checks = int(summary.get("flagged_checks", 0) or 0)
    checks_passed = max(0, total_checks - flagged_checks)
    risk_score = min(100, flagged_checks * 12)
    time_saved_minutes = round(8 + (checks_passed * 0.7), 1)

    return {
        "timing": {"total_duration_ms": total_duration_ms},
        "extraction": {
            "chars_extracted": chars_extracted,
            "chars_sent": chars_sent,
            "coverage_ratio": round(0 if chars_extracted == 0 else chars_sent / chars_extracted, 3),
            "parse_retries": parse_retries,
            "fallback_used": fallback_used,
        },
        "kpis": {
            "risk_score": risk_score,
            "checks_passed": checks_passed,
            "total_checks": total_checks,
            "estimated_time_saved_minutes": time_saved_minutes,
            "completeness_index": summary.get("completeness_index", 0),
        },
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    """Simple health-check endpoint."""
    return jsonify({"status": "ok", "service": "clearpath-backend"})


@app.route("/api/process-shipment/logs/<session_id>", methods=["GET"])
def stream_session_logs(session_id: str):
    """SSE stream for process-shipment session logs."""
    _ensure_session(session_id)

    def generate():
        cursor = 0
        while True:
            with _session_lock:
                events = list(_session_events.get(session_id, []))
                status = _session_status.get(session_id, "running")
                cond = _session_condition.get(session_id)

            while cursor < len(events):
                event = events[cursor]
                cursor += 1
                yield f"data: {json.dumps(event)}\n\n"

            if status in ("done", "error") and cursor >= len(events):
                yield f"event: status\ndata: {json.dumps({'status': status})}\n\n"
                break

            if cond is None:
                yield "data: {}\n\n"
                time.sleep(0.5)
                continue

            with cond:
                cond.wait(timeout=1.0)
            yield "event: ping\ndata: {}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/process-shipment/logs/<session_id>/snapshot", methods=["GET"])
def session_logs_snapshot(session_id: str):
    _ensure_session(session_id)
    with _session_lock:
        return jsonify(
            {
                "session_id": session_id,
                "status": _session_status.get(session_id, "running"),
                "events": _session_events.get(session_id, []),
            }
        )


# ---------------------------------------------------------------------------
# Main processing endpoint
# ---------------------------------------------------------------------------

@app.route("/api/process-shipment", methods=["POST"])
def process_shipment():
    """Process uploaded shipping PDFs through the full pipeline.

    Expects ``multipart/form-data`` with three PDF files:
    - ``bill_of_lading``
    - ``invoice``
    - ``packing_list``

    Returns the normalised audit result JSON.
    """
    started_at = time.perf_counter()
    session_id = (request.form.get("session_id") or str(uuid.uuid4())[:8]).strip()[:32]
    _ensure_session(session_id)
    _append_session_event(session_id, "SYSTEM", "Session initialized.", phase="init")

    missing = [name for name in REQUIRED_FILES if name not in request.files]
    if missing:
        _append_session_event(session_id, "WARN", f"Missing files: {', '.join(missing)}", phase="validate")
        _set_session_status(session_id, "error")
        return jsonify({
            "error": "Missing required PDF files",
            "missing": missing,
            "expected": REQUIRED_FILES,
            "session_id": session_id,
        }), 400

    for name in REQUIRED_FILES:
        f = request.files[name]
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            _append_session_event(session_id, "WARN", f"Invalid file format for {name}", phase="validate")
            _set_session_status(session_id, "error")
            return jsonify({
                "error": f"File '{name}' must be a PDF",
                "filename": f.filename,
                "session_id": session_id,
            }), 400

    saved_paths: dict[str, str] = {}
    extracted_texts: dict[str, str] = {}
    fallback_used = False
    parse_retries = 0

    try:
        _append_session_event(session_id, "INFO", "Saving upload payloads...", phase="ingest")
        for name in REQUIRED_FILES:
            f = request.files[name]
            safe_name = f"{session_id}_{name}.pdf"
            path = UPLOAD_DIR / safe_name
            f.save(str(path))
            saved_paths[name] = str(path)
            logger.info("Saved %s -> %s", name, path)
            _append_session_event(session_id, "INFO", f"Saved {name}: {f.filename}", phase="ingest")

        logger.info("[%s] Step 1/4: Extracting text from PDFs (parallel)...", session_id)
        _append_session_event(session_id, "INFO", "Extracting text from PDFs (parallel)...", phase="extract")

        def _extract(name_path):
            name, path = name_path
            text = extract_text_from_pdf(path)
            return name, text

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(_extract, item): item[0] for item in saved_paths.items()}
            for future in as_completed(futures):
                name, text = future.result()
                extracted_texts[name] = text
                _append_session_event(
                    session_id,
                    "OK",
                    f"Extracted {name} text ({len(text)} chars)",
                    phase="extract",
                )

        logger.info("[%s] Step 2/4: Structuring extracted text and category metadata...", session_id)
        _append_session_event(session_id, "INFO", "Structuring documents with LLM parser...", phase="structure")
        bol_json, inv_json, pl_json, category_meta = structure_shipment_document_bundle(extracted_texts)
        _append_session_event(session_id, "OK", "Structured data generated.", phase="structure")

        logger.info("[%s] Step 3/4: Running normaliser...", session_id)
        _append_session_event(session_id, "INFO", "Running consistency and compliance checks...", phase="normalize")
        product_id = f"PRD-{session_id.upper()}"
        shipment = build_shipment(
            bol=bol_json,
            invoice=inv_json,
            packing_list=pl_json,
            category_metadata=category_meta,
            product_id=product_id,
        )

        processor = ShipmentProcessor(shipment)
        normalised = processor.process()
        _append_session_event(session_id, "OK", "Normalization complete.", phase="normalize")

        explainability = _build_explainability(normalised, shipment)
        telemetry = _build_telemetry(
            started_at=started_at,
            extracted_texts=extracted_texts,
            explainability=explainability,
            fallback_used=fallback_used,
            parse_retries=parse_retries,
        )

        logger.info("[%s] Processing complete", session_id)
        _append_session_event(session_id, "OK", "Verification pipeline complete.", phase="complete")
        _set_session_status(session_id, "done")

        return jsonify({
            "success": True,
            "session_id": session_id,
            "normalized": normalised,
            "raw_shipment": shipment,
            "explainability": explainability,
            "telemetry": telemetry,
        })

    except RuntimeError as exc:
        logger.error("[%s] Pipeline error: %s", session_id, exc)
        _append_session_event(session_id, "WARN", str(exc), phase="error")
        _set_session_status(session_id, "error")
        return jsonify({"error": str(exc), "session_id": session_id}), 500

    except Exception as exc:
        logger.exception("[%s] Unexpected error", session_id)
        _append_session_event(session_id, "WARN", f"Internal server error: {exc}", phase="error")
        _set_session_status(session_id, "error")
        return jsonify({"error": f"Internal server error: {exc}", "session_id": session_id}), 500

    finally:
        for path in saved_paths.values():
            try:
                os.remove(path)
            except OSError:
                pass

# ---------------------------------------------------------------------------
# Report generation endpoint
# ---------------------------------------------------------------------------

@app.route("/api/generate-report", methods=["POST"])
def generate_report():
    """Generate and download a PDF report for a normalized shipment result.

    Expects JSON body:
    {
      "normalized": { ... }   # output from /api/process-shipment
    }
    """
    payload = request.get_json(silent=True) or {}
    normalized = payload.get("normalized")

    if not isinstance(normalized, dict):
        return jsonify({"error": "Missing or invalid 'normalized' payload"}), 400

    product_id = normalized.get("product_id") or f"PRD-{uuid.uuid4().hex[:8].upper()}"
    safe_product_id = "".join(ch for ch in str(product_id) if ch.isalnum() or ch in ("-", "_"))
    if not safe_product_id:
        safe_product_id = f"PRD-{uuid.uuid4().hex[:8].upper()}"

    temp_json_path: Path | None = None
    temp_pdf_path: Path | None = None

    try:
        # Import lazily so backend startup is unaffected if report dependencies are missing.
        try:
            from generate_report_card import ReportCardGenerator
        except SystemExit as exc:
            logger.error("Report generator dependency error: %s", exc)
            return jsonify({
                "error": "Report generator dependencies are missing. Install reportlab in backend environment."
            }), 500

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as jf:
            json.dump([normalized], jf, ensure_ascii=False)
            temp_json_path = Path(jf.name)

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as pf:
            temp_pdf_path = Path(pf.name)

        generator = ReportCardGenerator(str(temp_json_path))
        ok = generator.generate_report_card(str(safe_product_id), str(temp_pdf_path))
        if not ok:
            return jsonify({"error": "Failed to generate report PDF"}), 500

        @after_this_request
        def cleanup_files(response):
            for p in (temp_json_path, temp_pdf_path):
                if p is None:
                    continue
                try:
                    p.unlink(missing_ok=True)
                except OSError:
                    pass
            return response

        return send_file(
            str(temp_pdf_path),
            as_attachment=True,
            download_name=f"report_{safe_product_id}.pdf",
            mimetype="application/pdf",
        )

    except Exception as exc:
        logger.exception("Failed to generate report")
        # Best effort cleanup if send_file path wasn't reached
        for p in (temp_json_path, temp_pdf_path):
            if p is None:
                continue
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        return jsonify({"error": f"Failed to generate report: {exc}"}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting ClearPath backend on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)

