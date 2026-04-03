"""
Text → Structured JSON using Google Gemini.

Takes raw text extracted from shipping PDFs and structures it into JSON
matching the base_templates and category_templates schemas used by
normalizer.py's ShipmentProcessor.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Resolve template directories relative to this file
_BASE = Path(__file__).parent
_BASE_TEMPLATES = _BASE / "base_templates"
_CATEGORY_TEMPLATES = _BASE / "category_templates"


def _get_model():
    """Configure and return a Gemini generative model."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Add it to backend/.env and restart the server."
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def _load_template(template_path: Path) -> dict:
    """Load a JSON template file."""
    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _coerce_types(data: Any, template: Any) -> Any:
    """Recursively coerce values in *data* to match the types declared in
    *template*.  The templates use strings like ``"number"``, ``"boolean"``,
    ``"string"`` as type hints.

    This handles the common case where Gemini returns ``"42"`` (string)
    when the template expects ``"number"`` (i.e. an actual int/float).
    """
    if isinstance(template, dict) and isinstance(data, dict):
        result = {}
        for key, tmpl_val in template.items():
            if key in data:
                result[key] = _coerce_types(data[key], tmpl_val)
            else:
                result[key] = None
        # Keep any extra keys Gemini returned that aren't in the template
        for key in data:
            if key not in result:
                result[key] = data[key]
        return result

    if isinstance(template, list) and isinstance(data, list):
        if template:
            return [_coerce_types(item, template[0]) for item in data]
        return data

    # Leaf — coerce based on template type hint string
    if isinstance(template, str):
        hint = template.lower()
        if hint == "number":
            if data is None:
                return None
            try:
                return float(data) if "." in str(data) else int(data)
            except (ValueError, TypeError):
                return data
        if hint == "boolean":
            if isinstance(data, bool):
                return data
            if isinstance(data, str):
                return data.lower() in ("true", "yes", "1")
            return bool(data) if data is not None else None
        # "string" or any other hint — return as-is
        return data

    return data


# ---------------------------------------------------------------------------
# Public API — one function per document type
# ---------------------------------------------------------------------------

def structure_bill_of_lading(text: str) -> dict:
    """Convert raw BoL text into structured JSON matching
    ``base_templates/bill_of_lading.json``.
    """
    template = _load_template(_BASE_TEMPLATES / "bill_of_lading.json")
    return _structure_document(text, template, "Bill of Lading")


def structure_invoice(text: str) -> dict:
    """Convert raw invoice text into structured JSON matching
    ``base_templates/invoice.json``.
    """
    template = _load_template(_BASE_TEMPLATES / "invoice.json")
    return _structure_document(text, template, "Commercial Invoice")


def structure_packing_list(text: str) -> dict:
    """Convert raw packing list text into structured JSON matching
    ``base_templates/packing_list.json``.
    """
    template = _load_template(_BASE_TEMPLATES / "packing_list.json")
    return _structure_document(text, template, "Packing List")


def _structure_document(text: str, template: dict, doc_type: str) -> dict:
    """Common helper — sends the extracted text + schema to Gemini and
    parses/validates the response."""

    model = _get_model()
    schema_str = json.dumps(template, indent=2)

    prompt = f"""You are a logistics document parsing expert. Extract all data from the following {doc_type} document text and return it as a JSON object that exactly matches this schema.

SCHEMA (use these exact keys, with proper types — "number" means a numeric value, "boolean" means true/false, "string" means text):
{schema_str}

RULES:
- For arrays (like line_items or items), extract ALL entries found in the document.
- If a field is not found in the document, use null.
- For numbers, return actual numeric values, not strings.
- For booleans, return true or false, not strings.
- Return ONLY valid JSON matching the schema. No markdown, no explanation.

DOCUMENT TEXT:
{text}
"""

    logger.info("Requesting Gemini to structure %s", doc_type)

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        )
        raw_json = response.text
    except Exception as exc:
        logger.error("Gemini structuring failed for %s: %s", doc_type, exc)
        raise RuntimeError(f"Failed to structure {doc_type}: {exc}") from exc

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        logger.error("Gemini returned invalid JSON for %s: %s", doc_type, raw_json[:200])
        raise RuntimeError(
            f"Gemini returned invalid JSON for {doc_type}. "
            f"Raw response: {raw_json[:300]}"
        ) from exc

    # Coerce types to match template expectations
    structured = _coerce_types(parsed, template)
    logger.info("Successfully structured %s (%d keys)", doc_type, len(structured))
    return structured


# ---------------------------------------------------------------------------
# Category detection & metadata
# ---------------------------------------------------------------------------

def detect_category(invoice_data: dict) -> str:
    """Determine the product category from HS codes in the invoice.

    Mirrors the logic in ``normalizer.py → ShipmentProcessor._get_category``.
    """
    line_items = invoice_data.get("line_items") or []
    hs = line_items[0].get("hs_code", "") if line_items else ""
    if not hs:
        return "General"

    hs = str(hs)
    if hs.startswith(("07", "08", "04", "21")):
        return "Perishables"
    if hs.startswith(("84", "85", "94")):
        return "Manufactured Goods"
    if hs.startswith(("25", "26", "27", "28", "29", "38")):
        return "Raw Materials"
    return "General"


def structure_category_metadata(
    all_text: str,
    category: str,
) -> dict:
    """Extract category-specific metadata using the appropriate category
    template schema.

    Parameters
    ----------
    all_text : str
        Combined text from all three documents (BoL + Invoice + PL).
    category : str
        One of "Perishables", "Manufactured Goods", "Raw Materials", or
        "General".

    Returns
    -------
    dict
        ``{"category": ..., "metadata_fields": {...}}`` matching the
        category_templates schema.
    """
    template_map = {
        "Perishables": "perishables.json",
        "Manufactured Goods": "manufactured_goods.json",
        "Raw Materials": "raw_materials.json",
    }

    template_file = template_map.get(category)
    if not template_file:
        # General category — no category-specific metadata
        return {"category": "General", "metadata_fields": {}}

    template = _load_template(_CATEGORY_TEMPLATES / template_file)
    metadata_schema = template.get("metadata_fields", {})
    schema_str = json.dumps(metadata_schema, indent=2)

    model = _get_model()

    prompt = f"""You are a logistics document parsing expert. Based on the following shipping document texts, extract category-specific metadata for a "{category}" shipment.

Return a JSON object matching this schema (use these exact keys):
{schema_str}

RULES:
- For numbers, return actual numeric values.
- For booleans, return true or false.
- For dates, use ISO 8601 format (YYYY-MM-DD).
- If a field cannot be determined from the documents, use null.
- Return ONLY valid JSON. No markdown, no explanation.

DOCUMENT TEXTS:
{all_text}
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        )
        metadata_fields = json.loads(response.text)
    except Exception as exc:
        logger.error("Category metadata extraction failed: %s", exc)
        metadata_fields = {}

    # Coerce types
    metadata_fields = _coerce_types(metadata_fields, metadata_schema)

    return {
        "category": category,
        "metadata_fields": metadata_fields,
    }


# ---------------------------------------------------------------------------
# Assemble final shipment object
# ---------------------------------------------------------------------------

def build_shipment(
    bol: dict,
    invoice: dict,
    packing_list: dict,
    category_metadata: dict,
    product_id: Optional[str] = None,
) -> dict:
    """Assemble the final shipment object in the format expected by
    ``normalizer.py``'s ``ShipmentProcessor``.

    This matches the structure found in ``sample_data/samples.json``.
    """
    category = category_metadata.get("category", "General")

    return {
        "product_id": product_id or "PRD-UPLOAD",
        "status": "PENDING_VERIFICATION",
        "category": category,
        "category_metadata": category_metadata,
        "bill_of_lading": bol,
        "invoice": invoice,
        "packing_list": packing_list,
    }
