"""
ClearPath Backend — Flask API Server.

Receives PDF uploads from the React frontend, processes them through the
LLMWhisperer → Gemini → Normalizer pipeline, and returns the normalised
audit results.
"""

import json
import logging
import os
import tempfile
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
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
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

# Temp directory for uploaded files (cleaned up after processing)
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Maximum upload size: 16 MB per file
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

REQUIRED_FILES = ["bill_of_lading", "invoice", "packing_list"]


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    """Simple health-check endpoint."""
    return jsonify({"status": "ok", "service": "clearpath-backend"})


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

    # ------------------------------------------------------------------
    # 1. Validate uploads
    # ------------------------------------------------------------------
    missing = [name for name in REQUIRED_FILES if name not in request.files]
    if missing:
        return jsonify({
            "error": "Missing required PDF files",
            "missing": missing,
            "expected": REQUIRED_FILES,
        }), 400

    for name in REQUIRED_FILES:
        f = request.files[name]
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            return jsonify({
                "error": f"File '{name}' must be a PDF",
                "filename": f.filename,
            }), 400

    # ------------------------------------------------------------------
    # 2. Save files to temp directory
    # ------------------------------------------------------------------
    session_id = str(uuid.uuid4())[:8]
    saved_paths: dict[str, str] = {}

    try:
        for name in REQUIRED_FILES:
            f = request.files[name]
            safe_name = f"{session_id}_{name}.pdf"
            path = UPLOAD_DIR / safe_name
            f.save(str(path))
            saved_paths[name] = str(path)
            logger.info("Saved %s → %s", name, path)

        # ------------------------------------------------------------------
        # 3. Extract text from each PDF via LLMWhisperer
        # ------------------------------------------------------------------
        logger.info("[%s] Step 1/4: Extracting text from PDFs...", session_id)
        extracted_texts: dict[str, str] = {}
        for name, path in saved_paths.items():
            extracted_texts[name] = extract_text_from_pdf(path)

        # ------------------------------------------------------------------
        # 4. Structure text → JSON and extract category metadata in one request
        # ------------------------------------------------------------------
        logger.info("[%s] Step 2/4: Structuring extracted text and category metadata...", session_id)
        bol_json, inv_json, pl_json, category_meta = structure_shipment_document_bundle(extracted_texts)

        # ------------------------------------------------------------------
        # 5. Assemble shipment & run normaliser
        # ------------------------------------------------------------------
        logger.info("[%s] Step 3/4: Running normaliser...", session_id)
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

        logger.info("[%s] Processing complete ✓", session_id)

        return jsonify({
            "success": True,
            "session_id": session_id,
            "normalized": normalised,
            "raw_shipment": shipment,
        })

    except RuntimeError as exc:
        logger.error("[%s] Pipeline error: %s", session_id, exc)
        return jsonify({"error": str(exc)}), 500

    except Exception as exc:
        logger.exception("[%s] Unexpected error", session_id)
        return jsonify({"error": f"Internal server error: {exc}"}), 500

    finally:
        # Clean up uploaded files
        for path in saved_paths.values():
            try:
                os.remove(path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting ClearPath backend on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
