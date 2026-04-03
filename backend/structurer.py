"""
Text → Structured JSON using Groq API (free tier).

Takes raw text extracted from shipping PDFs and structures it into JSON
matching the base_templates and category_templates schemas used by
normalizer.py's ShipmentProcessor.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from groq import Groq

logger = logging.getLogger(__name__)

# Resolve template directories relative to this file
_BASE = Path(__file__).parent
_BASE_TEMPLATES = _BASE / "base_templates"
_CATEGORY_TEMPLATES = _BASE / "category_templates"


def _get_groq_client():
    """Get Groq client with API key."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. "
            "Add it to backend/.env and restart the server. "
            "Get a free key at https://console.groq.com"
        )
    return Groq(api_key=api_key)


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


def structure_shipment_document_bundle(texts: Dict[str, str]) -> Tuple[dict, dict, dict, dict]:
    """Structure all three shipment docs and category metadata in one AI request."""
    use_mock = os.environ.get("USE_MOCK_DATA", "").lower() == "true"
    if use_mock:
        logger.info("Mock mode enabled — returning mock data for all documents")
        bol = _coerce_types(_get_mock_data("Bill of Lading"), _load_template(_BASE_TEMPLATES / "bill_of_lading.json"))
        inv = _coerce_types(_get_mock_data("Commercial Invoice"), _load_template(_BASE_TEMPLATES / "invoice.json"))
        pl = _coerce_types(_get_mock_data("Packing List"), _load_template(_BASE_TEMPLATES / "packing_list.json"))
        category = detect_category(inv)
        return bol, inv, pl, {"category": category, "metadata_fields": {}}

    bol_template = _load_template(_BASE_TEMPLATES / "bill_of_lading.json")
    inv_template = _load_template(_BASE_TEMPLATES / "invoice.json")
    pl_template = _load_template(_BASE_TEMPLATES / "packing_list.json")
    category_templates = {
        "Perishables": _load_template(_CATEGORY_TEMPLATES / "perishables.json"),
        "Manufactured Goods": _load_template(_CATEGORY_TEMPLATES / "manufactured_goods.json"),
        "Raw Materials": _load_template(_CATEGORY_TEMPLATES / "raw_materials.json"),
    }

    prompt = f"""Extract logistics data from three documents and return a JSON object with keys: bill_of_lading, invoice, packing_list, category_metadata.

Use these field names only:

BILL_OF_LADING: bill_of_lading_number, ship_from (name, address, city_state_zip, sid_number, fob_point), ship_to (name, location_number, address, city_state_zip, cid_number, fob_point), carrier_details (carrier_name, trailer_number, seal_numbers, scac, pro_number, freight_charge_terms), customer_order_info (order_number, pkgs_count, weight, pallet_slip, additional_info), carrier_commodity_info (handling_unit_qty, handling_unit_type, package_qty, package_type, weight, is_hazardous, commodity_description, nmfc_number)

INVOICE: invoice_number, seller_info (company_name, address, reg_number, tax_number), bill_to_info (client_name, address, reg_number, tax_number), payment_details (bank_name, bic, account_number, invoice_date, due_date), line_items (hs_code, container_number, description, quantity, unit_of_measure, unit_price, subtotal, tax_amount, tax_percentage), totals (subtotal, tax_total, grand_total, currency, amount_in_words)

PACKING_LIST: delivery_to (customer_name, address_lines, telephone, email), from_business (business_name, address_lines), shipping_refs (order_reference, order_date, delivery_method, delivery_number, delivery_date), items (item_number, description, qty_ordered, qty_shipped, weight_kg, volume_cbm, container_number), notes

category_metadata: category (one of: Perishables, Manufactured Goods, Raw Materials, General), metadata_fields (empty object if General)

RETURN ONLY VALID JSON. Start with {{ and end with }}. No markdown, no explanation.

BILL OF LADING:
{texts["bill_of_lading"][:800]}

COMMERCIAL INVOICE:
{texts["invoice"][:800]}

PACKING LIST:
{texts["packing_list"][:800]}
"""

    logger.info("Requesting Groq to structure all documents in one request")
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2048,
        )
        raw_json = response.choices[0].message.content
    except Exception as exc:
        logger.error("Groq bundled structuring failed: %s", exc)
        if _should_fallback_to_mock(exc):
            logger.warning("Falling back to mock data for all documents due to Groq error")
            bol = _coerce_types(_get_mock_data("Bill of Lading"), bol_template)
            inv = _coerce_types(_get_mock_data("Commercial Invoice"), inv_template)
            pl = _coerce_types(_get_mock_data("Packing List"), pl_template)
            category = detect_category(inv)
            return bol, inv, pl, {"category": category, "metadata_fields": {}}
        raise RuntimeError(f"Failed to structure shipment bundle: {exc}") from exc

    try:
        # Extract JSON from markdown code blocks if present
        if "```json" in raw_json:
            raw_json = raw_json.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_json:
            raw_json = raw_json.split("```")[1].split("```")[0].strip()
        
        parsed = raw_json if isinstance(raw_json, dict) else json.loads(raw_json)
        
        if not isinstance(parsed, dict):
            raise json.JSONDecodeError("Response is not a JSON object", raw_json, 0)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Groq returned invalid JSON for bundle: %s", str(raw_json)[:200])
        logger.warning("Falling back to mock data due to JSON parse error")
        bol = _coerce_types(_get_mock_data("Bill of Lading"), bol_template)
        inv = _coerce_types(_get_mock_data("Commercial Invoice"), inv_template)
        pl = _coerce_types(_get_mock_data("Packing List"), pl_template)
        category = detect_category(inv)
        return bol, inv, pl, {"category": category, "metadata_fields": {}}
    except Exception as exc:
        logger.error("Unexpected error parsing Groq response: %s", exc)
        logger.warning("Falling back to mock data")
        bol = _coerce_types(_get_mock_data("Bill of Lading"), bol_template)
        inv = _coerce_types(_get_mock_data("Commercial Invoice"), inv_template)
        pl = _coerce_types(_get_mock_data("Packing List"), pl_template)
        category = detect_category(inv)
        return bol, inv, pl, {"category": category, "metadata_fields": {}}

    try:
        bol = _coerce_types(parsed.get("bill_of_lading", {}), bol_template)
        inv = _coerce_types(parsed.get("invoice", {}), inv_template)
        pl = _coerce_types(parsed.get("packing_list", {}), pl_template)
    except Exception as exc:
        logger.error("Failed to extract document types from response: %s", exc)
        logger.warning("Falling back to mock data")
        bol = _coerce_types(_get_mock_data("Bill of Lading"), bol_template)
        inv = _coerce_types(_get_mock_data("Commercial Invoice"), inv_template)
        pl = _coerce_types(_get_mock_data("Packing List"), pl_template)
        category = detect_category(inv)
        return bol, inv, pl, {"category": category, "metadata_fields": {}}

    try:
        category_data = parsed.get("category_metadata", {})
        if not isinstance(category_data, dict):
            category_data = {}
        category = category_data.get("category", "General")
        metadata_fields = category_data.get("metadata_fields", {}) or {}
        if category in category_templates:
            metadata_fields = _coerce_types(metadata_fields, category_templates[category].get("metadata_fields", {}))
    except Exception as exc:
        logger.error("Failed to extract category metadata: %s", exc)
        category = "General"
        metadata_fields = {}

    return bol, inv, pl, {"category": category, "metadata_fields": metadata_fields}


def _get_mock_data(doc_type: str) -> dict:
    """Return mock document data for testing without API calls."""
    if doc_type == "Bill of Lading":
        return {
            "bill_of_lading_number": "BOL-2024-001",
            "ship_from": {
                "name": "Tech Supplies Inc.",
                "address": "123 Industrial Ave",
                "city_state_zip": "Shanghai, China 200120",
                "sid_number": "SH-12345",
                "fob_point": True
            },
            "ship_to": {
                "name": "Global Distribution Ltd.",
                "location_number": "LOC-456",
                "address": "456 Commerce Street",
                "city_state_zip": "Rotterdam, Netherlands 3011AA",
                "cid_number": "ROT-789",
                "fob_point": False
            },
            "carrier_details": {
                "carrier_name": "Global Logistics Co.",
                "trailer_number": "TR-2024-001",
                "seal_numbers": "SEAL-ABC123",
                "scac": "GLCO",
                "pro_number": "PRO-2024-001",
                "freight_charge_terms": "Prepaid"
            },
            "customer_order_info": [
                {
                    "order_number": "ORD-2024-0001",
                    "pkgs_count": 50,
                    "weight": 2500.0,
                    "pallet_slip": True,
                    "additional_info": "High-value electronics"
                }
            ],
            "carrier_commodity_info": [
                {
                    "handling_unit_qty": 5,
                    "handling_unit_type": "Pallet",
                    "package_qty": 50,
                    "package_type": "Box",
                    "weight": 2500.0,
                    "is_hazardous": False,
                    "commodity_description": "Electronic Components",
                    "nmfc_number": "111400"
                }
            ]
        }
    elif doc_type == "Commercial Invoice":
        return {
            "invoice_number": "INV-2024-001",
            "seller_info": {
                "company_name": "Tech Supplies Inc.",
                "address": "123 Industrial Ave",
                "reg_number": "CN-987654321",
                "tax_number": "TX-555666777"
            },
            "bill_to_info": {
                "client_name": "Global Distribution Ltd.",
                "address": "456 Commerce Street",
                "reg_number": "NL-123456789",
                "tax_number": "NL-VAT-AB12345"
            },
            "payment_details": {
                "bank_name": "International Trade Bank",
                "bic": "ITBKUS20",
                "account_number": "1234567890",
                "invoice_date": "2024-04-01",
                "due_date": "2024-05-01"
            },
            "line_items": [
                {
                    "hs_code": "847130",
                    "container_number": "CONT-001",
                    "description": "Semiconductor Chips",
                    "quantity": 5000,
                    "unit_of_measure": "Unit",
                    "unit_price": 50.0,
                    "subtotal": 250000.0,
                    "tax_amount": 52500.0,
                    "tax_percentage": 21.0
                }
            ],
            "totals": {
                "subtotal": 250000.0,
                "tax_total": 52500.0,
                "grand_total": 302500.0,
                "currency": "EUR",
                "amount_in_words": "Three hundred two thousand five hundred Euros"
            }
        }
    elif doc_type == "Packing List":
        return {
            "delivery_to": {
                "customer_name": "Global Distribution Ltd.",
                "address_lines": ["456 Commerce Street", "Rotterdam, Netherlands 3011AA"],
                "telephone": "+31 10 123 4567",
                "email": "logistics@globaldist.nl"
            },
            "from_business": {
                "business_name": "Tech Supplies Inc.",
                "address_lines": ["123 Industrial Ave", "Shanghai, China 200120"]
            },
            "shipping_refs": {
                "order_reference": "ORD-2024-0001",
                "order_date": "2024-03-20",
                "delivery_method": "Ocean Freight",
                "delivery_number": "DEL-2024-001",
                "delivery_date": "2024-04-15"
            },
            "items": [
                {
                    "item_number": "ITEM-001",
                    "description": "Semiconductor Chips - Grade A",
                    "qty_ordered": 5000,
                    "qty_shipped": 5000,
                    "weight_kg": 500.0,
                    "volume_cbm": 2.5,
                    "container_number": "CONT-001"
                }
            ],
            "notes": "Fragile - Handle with care. Store in cool, dry place."
        }
    return {}


def _should_fallback_to_mock(exc: Exception) -> bool:
    """Detect rate-limit or throttling failures and fall back to mock mode."""
    message = str(exc).lower()
    return any(
        keyword in message
        for keyword in [
            "rate limit",
            "too many requests",
            "429",
            "tokens",
            "token",
            "quota",
            "decommissioned",
            "rate_limit_exceeded",
        ]
    )


def _structure_document(text: str, template: dict, doc_type: str) -> dict:
    """Common helper — sends the extracted text + schema to Groq and
    parses/validates the response."""

    # Check if mock mode is enabled
    use_mock = os.environ.get("USE_MOCK_DATA", "").lower() == "true"
    if use_mock:
        logger.info("Mock mode enabled — returning mock data for %s", doc_type)
        mock_data = _get_mock_data(doc_type)
        return _coerce_types(mock_data, template)

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

    logger.info("Requesting Groq to structure %s", doc_type)

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1024,
        )
        raw_json = response.choices[0].message.content
    except Exception as exc:
        logger.error("Groq structuring failed for %s: %s", doc_type, exc)
        if _should_fallback_to_mock(exc):
            logger.warning("Falling back to mock data for %s due to Groq error", doc_type)
            mock_data = _get_mock_data(doc_type)
            return _coerce_types(mock_data, template)
        raise RuntimeError(f"Failed to structure {doc_type}: {exc}") from exc

    try:
        if isinstance(raw_json, dict):
            parsed = raw_json
        else:
            parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        logger.error("Groq returned invalid JSON for %s: %s", doc_type, raw_json[:200])
        raise RuntimeError(
            f"Groq returned invalid JSON for {doc_type}. Raw response: {raw_json[:300]}"
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

    # Check if mock mode is enabled
    use_mock = os.environ.get("USE_MOCK_DATA", "").lower() == "true"
    if use_mock:
        logger.info("Mock mode enabled — returning mock category metadata for %s", category)
        mock_metadata = {}
        if category == "Manufactured Goods":
            mock_metadata = {
                "manufacturer": "Tech Supplies Inc.",
                "manufacturing_date": "2024-03-01",
                "certifications": ["ISO 9001", "CE Mark"],
                "warranty_months": 24,
                "technical_specs": "High-grade semiconductors, Grade A quality"
            }
        elif category == "Perishables":
            mock_metadata = {
                "storage_temperature": 4,
                "humidity_range": "45-55%",
                "expiry_date": "2024-06-01",
                "handling_instructions": "Keep refrigerated"
            }
        elif category == "Raw Materials":
            mock_metadata = {
                "material_grade": "Premium Grade",
                "purity": 99.5,
                "source_country": "China",
                "certifications": ["ISO 14001"]
            }
        metadata_fields = _coerce_types(mock_metadata, metadata_schema)
        return {
            "category": category,
            "metadata_fields": metadata_fields,
        }

    schema_str = json.dumps(metadata_schema, indent=2)

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
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1024,
        )
        raw_json = response.choices[0].message.content
        if isinstance(raw_json, dict):
            metadata_fields = raw_json
        else:
            metadata_fields = json.loads(raw_json)
    except Exception as exc:
        logger.error("Category metadata extraction failed: %s", exc)
        if _should_fallback_to_mock(exc):
            logger.warning("Falling back to mock category metadata for %s due to Groq error", category)
            metadata_fields = {
                "manufacturer": "Tech Supplies Inc.",
                "manufacturing_date": "2024-03-01",
                "certifications": ["ISO 9001", "CE Mark"],
                "warranty_months": 24,
                "technical_specs": "High-grade semiconductors, Grade A quality"
            } if category == "Manufactured Goods" else {}
        else:
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
