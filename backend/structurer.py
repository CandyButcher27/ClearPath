"""
Text â†’ Structured JSON using Groq API (free tier).

Takes raw text extracted from shipping PDFs and structures it into JSON
matching the base_templates and category_templates schemas used by
normalizer.py's ShipmentProcessor.
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from groq import Groq
try:
    from .prompts import get_prompt
except ImportError:
    from prompts import get_prompt

logger = logging.getLogger(__name__)

# Resolve template directories relative to this file
_BASE = Path(__file__).parent
_BASE_TEMPLATES = _BASE / "base_templates"
_CATEGORY_TEMPLATES = _BASE / "category_templates"
_DEBUG_OUTPUTS = _BASE / "debug_outputs"
_DEFAULT_MODEL = os.environ.get("STRUCTURER_MODEL", "llama-3.3-70b-versatile")
_MAX_DOC_CHARS = int(os.environ.get("STRUCTURER_MAX_DOC_CHARS", "12000"))
_BUNDLE_MAX_TOTAL_CHARS = int(os.environ.get("STRUCTURER_BUNDLE_MAX_TOTAL_CHARS", "30000"))
_USE_BUNDLE_FIRST = os.environ.get("STRUCTURER_USE_BUNDLE_FIRST", "true").lower() in ("1", "true", "yes")


def _render_prompt(name: str, values: Dict[str, Any]) -> str:
    template = get_prompt(name)
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


def _default_for_template(template: Any) -> Any:
    if isinstance(template, dict):
        return {k: _default_for_template(v) for k, v in template.items()}
    if isinstance(template, list):
        return []
    if isinstance(template, str):
        hint = template.lower()
        if hint == "number":
            return 0
        if hint == "boolean":
            return False
        return ""
    return ""


def _is_table_like_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    lower = s.lower()
    keywords = (
        "item",
        "qty",
        "quantity",
        "unit",
        "subtotal",
        "total",
        "container",
        "weight",
        "volume",
        "tax",
        "hs code",
    )
    has_keyword = any(k in lower for k in keywords)
    has_numeric = bool(re.search(r"\d", s))
    dense_cols = s.count("  ") >= 2 or "|" in s
    return has_keyword or (has_numeric and dense_cols)


def _prepare_doc_text(text: str, max_chars: int) -> str:
    raw = (text or "").strip()
    if len(raw) <= max_chars:
        return raw

    lines = raw.splitlines()
    table_lines = [ln for ln in lines if _is_table_like_line(ln)]

    head_budget = max_chars // 3
    table_budget = max_chars // 3
    tail_budget = max_chars - head_budget - table_budget

    head = raw[:head_budget]
    table = "\n".join(table_lines)[:table_budget]
    tail = raw[-tail_budget:] if tail_budget > 0 else ""

    merged = f"{head}\n\n[TABLE_SECTION]\n{table}\n\n[FOOTER_SECTION]\n{tail}".strip()
    return merged[:max_chars]


def _log_doc_coverage(label: str, original_text: str, sent_text: str) -> None:
    original_len = len((original_text or "").strip())
    sent_len = len((sent_text or "").strip())
    ratio = 0.0 if original_len == 0 else sent_len / original_len
    logger.info(
        "[coverage] %s chars_sent=%d chars_extracted=%d ratio=%.3f",
        label,
        sent_len,
        original_len,
        ratio,
    )


def _dump_structured_snapshot(tag: str, raw_structured: Any, coerced_structured: Any, *, mode: str) -> None:
    _dump_groq_output(
        tag,
        {
            "raw_structured": raw_structured,
            "coerced_structured": coerced_structured,
        },
        mode=mode,
    )


def _dump_groq_output(
    tag: str,
    raw_output: Any,
    parse_error: Optional[str] = None,
    *,
    model: str = _DEFAULT_MODEL,
    attempt: Optional[int] = None,
    mode: Optional[str] = None,
) -> None:
    """Persist Groq response payloads for debugging parse issues."""
    try:
        _DEBUG_OUTPUTS.mkdir(exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        out_path = _DEBUG_OUTPUTS / f"{ts}_{tag}.json"
        payload = {
            "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "tag": tag,
            "model": model,
            "attempt": attempt,
            "mode": mode,
            "parse_error": parse_error,
            "raw_output": raw_output,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
        logger.info("Saved Groq debug output to %s", out_path)
    except Exception as exc:
        logger.warning("Failed to save Groq debug output: %s", exc)


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


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped JSON in them."""
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()
    return text.strip()


def _is_likely_truncated_json(raw_text: str, exc: json.JSONDecodeError) -> bool:
    """Heuristic for retryable malformed JSON caused by truncation/cutoff."""
    msg = str(exc).lower()
    tail = (raw_text or "").rstrip()[-5:]
    return (
        "unterminated string" in msg
        or "expecting value" in msg
        or "expecting ',' delimiter" in msg
        or (tail and tail[-1] not in ("]", "}"))
    )


def _parse_bundle_response(raw_json: Any) -> dict:
    """Parse and validate bundle response shape."""
    required = {"bill_of_lading", "invoice", "packing_list", "category_metadata"}

    if isinstance(raw_json, dict):
        parsed = raw_json
    else:
        cleaned = _strip_markdown_fences(str(raw_json))
        parsed = json.loads(cleaned)

    if not isinstance(parsed, dict):
        raise ValueError("Bundle response is not a JSON object")

    missing = required - set(parsed.keys())
    if missing:
        raise ValueError(f"Bundle response missing keys: {sorted(missing)}")

    return parsed


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
    if isinstance(template, dict):
        # If model returned a scalar/list where object is expected, coerce to {}
        # so all expected keys still exist with safe defaults.
        if not isinstance(data, dict):
            data = {}
        result = {}
        for key, tmpl_val in template.items():
            if key in data:
                result[key] = _coerce_types(data[key], tmpl_val)
            else:
                result[key] = _default_for_template(tmpl_val)
        # Keep any extra keys model returned that aren't in the template
        for key in data:
            if key not in result:
                result[key] = data[key]
        return result

    if isinstance(template, list):
        if not template:
            return data if isinstance(data, list) else []
        # Normalize common shape errors:
        # - dict returned instead of single-item list
        # - scalar returned instead of list
        if data is None or data == "":
            return []
        if isinstance(data, list):
            return [_coerce_types(item, template[0]) for item in data]
        if isinstance(data, dict):
            return [_coerce_types(data, template[0])]
        return [_coerce_types(data, template[0])]

    # Leaf â€” coerce based on template type hint string
    if isinstance(template, str):
        hint = template.lower()
        if hint == "number":
            if data is None:
                return 0
            if isinstance(data, str) and data.strip().lower() in ("", "n/a", "na", "null", "none", "-"):
                return 0
            try:
                return float(data) if "." in str(data) else int(data)
            except (ValueError, TypeError):
                return 0
        if hint == "boolean":
            if data is None:
                return False
            if isinstance(data, bool):
                return data
            if isinstance(data, str):
                return data.lower() in ("true", "yes", "1")
            return bool(data)
        # "string" or any other hint â€” return as-is
        if data is None:
            return ""
        return str(data)

    return data


# ---------------------------------------------------------------------------
# Public API â€” one function per document type
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


def _structure_with_per_document(texts: Dict[str, str]) -> Tuple[dict, dict, dict, dict]:
    bol = structure_bill_of_lading(texts.get("bill_of_lading", ""))
    inv = structure_invoice(texts.get("invoice", ""))
    pl = structure_packing_list(texts.get("packing_list", ""))
    category = detect_category(inv)
    all_text = "\n\n".join(
        [
            texts.get("bill_of_lading", ""),
            texts.get("invoice", ""),
            texts.get("packing_list", ""),
        ]
    )
    category_meta = structure_category_metadata(all_text, category)
    return bol, inv, pl, category_meta


def structure_shipment_document_bundle(texts: Dict[str, str]) -> Tuple[dict, dict, dict, dict]:
    """Structure all three shipment docs and category metadata in one AI request."""
    use_mock = os.environ.get("USE_MOCK_DATA", "").lower() == "true"
    if use_mock:
        logger.info("Mock mode enabled - returning mock data for all documents")
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

    if not _USE_BUNDLE_FIRST:
        logger.info("STRUCTURER_USE_BUNDLE_FIRST=false; using per-document extraction path.")
        return _structure_with_per_document(texts)

    bol_text = _prepare_doc_text(texts.get("bill_of_lading", ""), _MAX_DOC_CHARS)
    inv_text = _prepare_doc_text(texts.get("invoice", ""), _MAX_DOC_CHARS)
    pl_text = _prepare_doc_text(texts.get("packing_list", ""), _MAX_DOC_CHARS)

    _log_doc_coverage("bill_of_lading", texts.get("bill_of_lading", ""), bol_text)
    _log_doc_coverage("invoice", texts.get("invoice", ""), inv_text)
    _log_doc_coverage("packing_list", texts.get("packing_list", ""), pl_text)

    bundle_total_chars = len(bol_text) + len(inv_text) + len(pl_text)
    if bundle_total_chars > _BUNDLE_MAX_TOTAL_CHARS:
        logger.warning(
            "Bundle prompt budget exceeded (chars=%d > %d). Switching to per-document extraction first.",
            bundle_total_chars,
            _BUNDLE_MAX_TOTAL_CHARS,
        )
        return _structure_with_per_document(texts)

    prompt = _render_prompt(
        "bundle_user.txt",
        {
            "BOL_SCHEMA": json.dumps(bol_template, separators=(",", ":")),
            "INV_SCHEMA": json.dumps(inv_template, separators=(",", ":")),
            "PL_SCHEMA": json.dumps(pl_template, separators=(",", ":")),
            "BILL_OF_LADING_TEXT": bol_text,
            "INVOICE_TEXT": inv_text,
            "PACKING_LIST_TEXT": pl_text,
        },
    )
    system_prompt = get_prompt("bundle_system.txt")

    logger.info("Requesting Groq to structure all documents in one request")
    client = _get_groq_client()
    parsed: Optional[dict] = None
    last_parse_error: Optional[Exception] = None

    for attempt in (1, 2):
        temperature = 0.1 if attempt == 1 else 0.0
        try:
            response = client.chat.completions.create(
                model=_DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=3072,
            )
            raw_json = response.choices[0].message.content
            _dump_groq_output(
                "bundle_response",
                raw_json,
                model=_DEFAULT_MODEL,
                attempt=attempt,
                mode="bundle",
            )
        except Exception as exc:
            logger.error("Groq bundled structuring failed on attempt %d: %s", attempt, exc)
            if attempt == 2:
                if _should_fallback_to_mock(exc):
                    logger.warning("Falling back to mock data for all documents due to Groq API error")
                    bol = _coerce_types(_get_mock_data("Bill of Lading"), bol_template)
                    inv = _coerce_types(_get_mock_data("Commercial Invoice"), inv_template)
                    pl = _coerce_types(_get_mock_data("Packing List"), pl_template)
                    category = detect_category(inv)
                    return bol, inv, pl, {"category": category, "metadata_fields": {}}
                logger.warning("Falling back to per-document parsing after bundle API failures")
                break
            continue

        try:
            parsed = _parse_bundle_response(raw_json)
            logger.info("Bundle parsing succeeded on attempt %d", attempt)
            break
        except json.JSONDecodeError as exc:
            last_parse_error = exc
            logger.warning("Bundle attempt %d failed parse: %s", attempt, exc)
            _dump_groq_output(
                "bundle_parse_error",
                raw_json,
                parse_error=str(exc),
                model=_DEFAULT_MODEL,
                attempt=attempt,
                mode="bundle",
            )
            if attempt == 1 and _is_likely_truncated_json(str(raw_json), exc):
                logger.info("Bundle attempt 1 appears truncated; retrying once")
                continue
            if attempt == 2:
                logger.warning("Bundle retries exhausted; falling back to per-document parsing")
            break
        except ValueError as exc:
            last_parse_error = exc
            logger.warning("Bundle attempt %d returned invalid structure: %s", attempt, exc)
            _dump_groq_output(
                "bundle_parse_error",
                raw_json,
                parse_error=str(exc),
                model=_DEFAULT_MODEL,
                attempt=attempt,
                mode="bundle",
            )
            if attempt == 2:
                logger.warning("Bundle retries exhausted; falling back to per-document parsing")
            continue

    if parsed is None:
        logger.info("Falling back to per-document parsing")
        try:
            bol, inv, pl, category_meta = _structure_with_per_document(texts)
            logger.info("Per-document fallback parsing succeeded")
            return bol, inv, pl, category_meta
        except Exception as exc:
            logger.error("Per-document fallback parsing failed: %s", exc)
            if last_parse_error is not None:
                logger.error("Last bundle parse error before fallback: %s", last_parse_error)
            logger.warning("Falling back to mock data after structured parsing failures")
            bol = _coerce_types(_get_mock_data("Bill of Lading"), bol_template)
            inv = _coerce_types(_get_mock_data("Commercial Invoice"), inv_template)
            pl = _coerce_types(_get_mock_data("Packing List"), pl_template)
            category = detect_category(inv)
            return bol, inv, pl, {"category": category, "metadata_fields": {}}

    try:
        raw_bol = parsed.get("bill_of_lading", {})
        raw_inv = parsed.get("invoice", {})
        raw_pl = parsed.get("packing_list", {})
        bol = _coerce_types(raw_bol, bol_template)
        inv = _coerce_types(raw_inv, inv_template)
        pl = _coerce_types(raw_pl, pl_template)
        _dump_structured_snapshot(
            "bundle_documents_coercion",
            {"bill_of_lading": raw_bol, "invoice": raw_inv, "packing_list": raw_pl},
            {"bill_of_lading": bol, "invoice": inv, "packing_list": pl},
            mode="bundle",
        )
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
            coerced_metadata = _coerce_types(metadata_fields, category_templates[category].get("metadata_fields", {}))
            _dump_structured_snapshot(
                "bundle_category_metadata_coercion",
                metadata_fields,
                coerced_metadata,
                mode="bundle",
            )
            metadata_fields = coerced_metadata
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
    """Common helper â€” sends the extracted text + schema to Groq and
    parses/validates the response."""

    # Check if mock mode is enabled
    use_mock = os.environ.get("USE_MOCK_DATA", "").lower() == "true"
    if use_mock:
        logger.info("Mock mode enabled â€” returning mock data for %s", doc_type)
        mock_data = _get_mock_data(doc_type)
        return _coerce_types(mock_data, template)

    schema_str = json.dumps(template, indent=2)
    prepared_text = _prepare_doc_text(text, _MAX_DOC_CHARS)
    _log_doc_coverage(doc_type.lower().replace(" ", "_"), text, prepared_text)

    prompt = _render_prompt(
        "per_document_user.txt",
        {
            "DOC_TYPE": doc_type,
            "SCHEMA": schema_str,
            "DOCUMENT_TEXT": prepared_text,
        },
    )
    system_prompt = get_prompt("per_document_system.txt")

    logger.info("Requesting Groq to structure %s", doc_type)

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=_DEFAULT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
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
        _dump_groq_output(
            f"{doc_type.lower().replace(' ', '_')}_response",
            raw_json,
            model=_DEFAULT_MODEL,
            mode="per_document",
        )
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
        _dump_groq_output(
            f"{doc_type.lower().replace(' ', '_')}_parse_error",
            raw_json,
            parse_error=str(exc),
            mode="per_document",
        )
        raise RuntimeError(
            f"Groq returned invalid JSON for {doc_type}. Raw response: {raw_json[:300]}"
        ) from exc

    # Coerce types to match template expectations
    structured = _coerce_types(parsed, template)
    _dump_structured_snapshot(
        f"{doc_type.lower().replace(' ', '_')}_coercion",
        parsed,
        structured,
        mode="per_document",
    )
    logger.info("Successfully structured %s (%d keys)", doc_type, len(structured))
    return structured


# ---------------------------------------------------------------------------
# Category detection & metadata
# ---------------------------------------------------------------------------

def detect_category(invoice_data: dict) -> str:
    """Determine the product category from HS codes in the invoice.

    Mirrors the logic in ``normalizer.py â†’ ShipmentProcessor._get_category``.
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
        # General category â€” no category-specific metadata
        return {"category": "General", "metadata_fields": {}}

    template = _load_template(_CATEGORY_TEMPLATES / template_file)
    metadata_schema = template.get("metadata_fields", {})

    # Check if mock mode is enabled
    use_mock = os.environ.get("USE_MOCK_DATA", "").lower() == "true"
    if use_mock:
        logger.info("Mock mode enabled â€” returning mock category metadata for %s", category)
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
    prepared_text = _prepare_doc_text(all_text, _MAX_DOC_CHARS * 2)
    _log_doc_coverage("category_metadata_input", all_text, prepared_text)

    prompt = (
        f'Extract category-specific metadata for a "{category}" shipment.\n\n'
        f"Return a JSON object matching this schema:\n{schema_str}\n\n"
        "Rules:\n"
        "- Use type-safe defaults when fields are absent.\n"
        "- Return only valid JSON.\n\n"
        f"DOCUMENT TEXTS:\n{prepared_text}\n"
    )
    system_prompt = get_prompt("category_metadata_system.txt")

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=_DEFAULT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
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
        _dump_groq_output(
            f"category_{category.lower().replace(' ', '_')}_response",
            raw_json,
            model=_DEFAULT_MODEL,
            mode="category_metadata",
        )
        if isinstance(raw_json, dict):
            metadata_fields = raw_json
        else:
            metadata_fields = json.loads(raw_json)
    except Exception as exc:
        logger.error("Category metadata extraction failed: %s", exc)
        raw_for_dump = locals().get("raw_json")
        if raw_for_dump is not None:
            _dump_groq_output(
                f"category_{category.lower().replace(' ', '_')}_parse_error",
                raw_for_dump,
                parse_error=str(exc),
                mode="category_metadata",
            )
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
    raw_metadata_fields = metadata_fields
    metadata_fields = _coerce_types(metadata_fields, metadata_schema)
    _dump_structured_snapshot(
        f"category_{category.lower().replace(' ', '_')}_coercion",
        raw_metadata_fields,
        metadata_fields,
        mode="category_metadata",
    )

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

