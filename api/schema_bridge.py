"""
Rule-based parser that converts DocStruct markdown output into the
JSON schema expected by backend/normalizer.py ShipmentProcessor.

Three parsers handle each document type. All return dicts that match the
backend's base_templates schemas; missing fields fall back to sane defaults.
"""
from __future__ import annotations

import re
import uuid
from typing import Any


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _find_value(text: str, *patterns: str, default: str = "") -> str:
    """Return first capture group from the first pattern that matches."""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return default


def _find_float(text: str, *patterns: str, default: float = 0.0) -> float:
    val = _find_value(text, *patterns, default="")
    if val:
        clean = re.sub(r"[^\d.\-]", "", val.replace(",", ""))
        try:
            return float(clean)
        except ValueError:
            pass
    return default


def _find_bool(text: str, *patterns: str, default: bool = False) -> bool:
    val = _find_value(text, *patterns, default="").lower()
    if val in ("yes", "true", "1"):
        return True
    if val in ("no", "false", "0"):
        return False
    return default


def _parse_pipe_table(text: str) -> list[list[str]]:
    """Extract rows from a GFM pipe table as a list of string lists."""
    rows = []
    for line in text.splitlines():
        if re.match(r"^\s*\|[-: |]+\|\s*$", line):
            continue  # separator line
        if "|" in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if any(cells):
                rows.append(cells)
    return rows


def _find_table_after(text: str, header_pattern: str) -> list[list[str]]:
    """Find the first pipe table that appears after a regex header match."""
    m = re.search(header_pattern, text, re.IGNORECASE | re.MULTILINE)
    if not m:
        # try to find any table in the whole text
        return _parse_pipe_table(text)
    snippet = text[m.end():]
    table_match = re.search(r"(\|.+\|)", snippet, re.DOTALL)
    if table_match:
        return _parse_pipe_table(table_match.group(0))
    return []


# ---------------------------------------------------------------------------
# Category detection from HS codes
# ---------------------------------------------------------------------------

_HS_PERISHABLES = re.compile(r"^(07|08|04|21)")
_HS_MANUFACTURED = re.compile(r"^(84|85|94)")
_HS_RAW = re.compile(r"^(25|26|27|28|29|38)")


def _detect_category(hs_code: str) -> str:
    code = re.sub(r"[.\s-]", "", hs_code)
    if _HS_PERISHABLES.match(code):
        return "Perishables"
    if _HS_MANUFACTURED.match(code):
        return "Manufactured Goods"
    if _HS_RAW.match(code):
        return "Raw Materials"
    return "General"


def _build_metadata_fields(category: str) -> dict[str, Any]:
    """Return reasonable default metadata fields for the detected category."""
    if category == "Perishables":
        return {
            "date_of_harvest": None,
            "date_of_shipping": None,
            "expiry_date": None,
            "temperature_control": {"required": True, "min_temp": 2.0, "max_temp": 8.0, "unit": "Celsius"},
            "humidity_requirement": 85.0,
            "ventilation_required": True,
            "ripening_stage": "Near-Ripe",
            "is_frozen": False,
            "shelf_life_remaining_days": 30,
        }
    if category == "Raw Materials":
        return {
            "net_weight": 0.0,
            "gross_weight": 0.0,
            "volume": {"value": 0.0, "unit": "m3"},
            "purity_percentage": 99.0,
            "grade_quality": "Standard",
            "country_of_origin": "",
            "batch_lot_number": "",
            "msds_link": "",
            "is_hazardous_material": False,
            "storage_container_type": "Standard",
        }
    if category == "Manufactured Goods":
        return {
            "serial_number": "",
            "model_number": "",
            "brand_name": "",
            "dimensions": {"length": 0.0, "width": 0.0, "height": 0.0, "unit": "cm"},
            "warranty_period_months": 12,
            "fragility_rating": "Medium",
            "assembly_required": False,
            "upc_ean_code": "",
            "packaging_material": "Cardboard",
        }
    return {}


# ---------------------------------------------------------------------------
# Invoice parser
# ---------------------------------------------------------------------------

class InvoiceParser:
    """Extract structured invoice fields from DocStruct markdown."""

    def __init__(self, markdown: str):
        self.md = markdown

    def parse(self) -> dict[str, Any]:
        return {
            "invoice_number": self._invoice_number(),
            "seller_info": self._seller_info(),
            "bill_to_info": self._bill_to_info(),
            "payment_details": self._payment_details(),
            "line_items": self._line_items(),
            "totals": self._totals(),
        }

    def _invoice_number(self) -> str:
        return _find_value(
            self.md,
            r"invoice\s+(?:number|no\.?|#)[:\s]+([A-Z0-9\-/]+)",
            r"inv(?:oice)?\s*[-#]?\s*([A-Z0-9\-/]+)",
            default="INV-UNKNOWN",
        )

    def _seller_info(self) -> dict[str, str]:
        company = _find_value(
            self.md,
            r"(?:seller|from|shipper|vendor|supplier)[:\s]+([^\n,]{3,60})",
            r"(?:company|business)\s+name[:\s]+([^\n,]{3,60})",
            default="",
        )
        address = _find_value(
            self.md,
            r"(?:seller|from|shipper)\s+address[:\s]+([^\n]{5,120})",
            default="",
        )
        reg = _find_value(self.md, r"(?:reg(?:istration)?\s*(?:number|no\.?|#)?)[:\s]+([A-Z0-9\-]+)", default="")
        tax = _find_value(self.md, r"(?:tax\s*(?:number|no\.?|id)?)[:\s]+([A-Z0-9\-]+)", default="")
        return {"company_name": company, "address": address, "reg_number": reg, "tax_number": tax}

    def _bill_to_info(self) -> dict[str, str]:
        client = _find_value(
            self.md,
            r"(?:bill\s+to|sold\s+to|buyer|client|consignee)[:\s]+([^\n,]{3,60})",
            default="",
        )
        address = _find_value(
            self.md,
            r"(?:bill\s+to|buyer|client)\s+address[:\s]+([^\n]{5,120})",
            default="",
        )
        return {"client_name": client, "address": address, "reg_number": "", "tax_number": ""}

    def _payment_details(self) -> dict[str, Any]:
        bank = _find_value(self.md, r"bank\s*(?:name)?[:\s]+([^\n,]{3,60})", default="")
        bic = _find_value(self.md, r"(?:bic|swift)[:\s]+([A-Z0-9]{6,12})", default="")
        acct = _find_value(self.md, r"account\s*(?:number|no\.?)?[:\s]+([\d\-]+)", default="")
        inv_date = _find_value(
            self.md,
            r"invoice\s+date[:\s]+([\d]{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/][\d]{2,4})",
            default="",
        )
        due_date = _find_value(
            self.md,
            r"(?:due|payment)\s+date[:\s]+([\d]{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/][\d]{2,4})",
            default="",
        )
        return {
            "bank_name": bank, "bic": bic, "account_number": acct,
            "invoice_date": inv_date, "due_date": due_date,
        }

    def _line_items(self) -> list[dict[str, Any]]:
        rows = _find_table_after(self.md, r"(?:line\s+items?|items?|description|hs\s+code)")
        if not rows:
            return []
        # First row is header
        if len(rows) < 2:
            return []
        header = [h.lower() for h in rows[0]]
        items = []
        for row in rows[1:]:
            if len(row) < 2:
                continue
            item: dict[str, Any] = {
                "hs_code": "",
                "container_number": "",
                "description": "",
                "quantity": 0.0,
                "unit_of_measure": "",
                "unit_price": 0.0,
                "subtotal": 0.0,
                "tax_amount": 0.0,
                "tax_percentage": 0.0,
            }
            for col_idx, col_name in enumerate(header):
                if col_idx >= len(row):
                    break
                val = row[col_idx]
                if any(k in col_name for k in ("hs", "code", "tariff")):
                    item["hs_code"] = val
                elif any(k in col_name for k in ("container",)):
                    item["container_number"] = val
                elif any(k in col_name for k in ("desc", "product", "item", "commodity")):
                    item["description"] = val
                elif any(k in col_name for k in ("qty", "quantity", "units")):
                    try:
                        item["quantity"] = float(re.sub(r"[^\d.]", "", val) or "0")
                    except ValueError:
                        pass
                elif any(k in col_name for k in ("uom", "unit of", "measure")):
                    item["unit_of_measure"] = val
                elif any(k in col_name for k in ("unit price", "unit_price", "rate", "price")):
                    try:
                        item["unit_price"] = float(re.sub(r"[^\d.]", "", val) or "0")
                    except ValueError:
                        pass
                elif any(k in col_name for k in ("subtotal", "sub_total", "amount", "total")):
                    try:
                        item["subtotal"] = float(re.sub(r"[^\d.]", "", val) or "0")
                    except ValueError:
                        pass
                elif any(k in col_name for k in ("tax amount", "tax_amount")):
                    try:
                        item["tax_amount"] = float(re.sub(r"[^\d.]", "", val) or "0")
                    except ValueError:
                        pass
                elif any(k in col_name for k in ("tax%", "tax_pct", "tax pct", "tax percentage", "vat%")):
                    try:
                        item["tax_percentage"] = float(re.sub(r"[^\d.]", "", val) or "0")
                    except ValueError:
                        pass
            if item["description"] or item["hs_code"]:
                items.append(item)
        return items

    def _totals(self) -> dict[str, Any]:
        subtotal = _find_float(
            self.md,
            r"sub\s*total[:\s]+([£$€]?[\d,]+\.?\d*)",
            default=0.0,
        )
        tax_total = _find_float(
            self.md,
            r"tax\s+total[:\s]+([£$€]?[\d,]+\.?\d*)",
            r"total\s+tax[:\s]+([£$€]?[\d,]+\.?\d*)",
            default=0.0,
        )
        grand_total = _find_float(
            self.md,
            r"grand\s+total[:\s]+([£$€]?[\d,]+\.?\d*)",
            r"total\s+amount[:\s]+([£$€]?[\d,]+\.?\d*)",
            r"total[:\s]+([£$€]?[\d,]+\.?\d*)",
            default=0.0,
        )
        currency_m = re.search(r"\b(USD|EUR|GBP|AED|INR|CNY|JPY)\b", self.md, re.IGNORECASE)
        currency = currency_m.group(1).upper() if currency_m else "USD"
        amount_words = _find_value(
            self.md,
            r"(?:amount\s+in\s+words?|in\s+words?)[:\s]+([^\n]{5,120})",
            default="",
        )
        return {
            "subtotal": subtotal, "tax_total": tax_total,
            "grand_total": grand_total, "currency": currency,
            "amount_in_words": amount_words,
        }


# ---------------------------------------------------------------------------
# Bill of Lading parser
# ---------------------------------------------------------------------------

class BolParser:
    """Extract structured BOL fields from DocStruct markdown."""

    def __init__(self, markdown: str):
        self.md = markdown

    def parse(self) -> dict[str, Any]:
        return {
            "bill_of_lading_number": self._bol_number(),
            "ship_from": self._ship_from(),
            "ship_to": self._ship_to(),
            "third_party_bill_to": self._third_party(),
            "special_instructions": self._special_instructions(),
            "carrier_details": self._carrier_details(),
            "customer_order_info": self._customer_order_info(),
            "carrier_commodity_info": self._carrier_commodity_info(),
            "cod_details": {"amount": 0.0, "fee_terms": "None", "customer_check_acceptable": False},
        }

    def _bol_number(self) -> str:
        return _find_value(
            self.md,
            r"bill\s+of\s+lading\s+(?:number|no\.?|#)[:\s]+([A-Z0-9\-]+)",
            r"b/?l\s*(?:number|no\.?|#)?[:\s]+([A-Z0-9\-]+)",
            r"bol\s*(?:number|no\.?|#)?[:\s]+([A-Z0-9\-]+)",
            default="BOL-UNKNOWN",
        )

    def _ship_from(self) -> dict[str, Any]:
        name = _find_value(
            self.md,
            r"ship\s+from[:\s]+([^\n,]{3,60})",
            r"shipper[:\s]+([^\n,]{3,60})",
            r"from[:\s]+([^\n,]{3,60})",
            default="",
        )
        address = _find_value(
            self.md,
            r"ship(?:per)?\s+from\s+address[:\s]+([^\n]{5,120})",
            default="",
        )
        city = _find_value(self.md, r"ship\s+from.*?city[:\s]+([^\n,]{3,40})", default="")
        sid = _find_value(self.md, r"sid[:\s]+([A-Z0-9\-]+)", default="")
        fob = _find_bool(self.md, r"fob\s+(?:point|origin)[:\s]+(yes|no|true|false)", default=True)
        return {"name": name, "address": address, "city_state_zip": city, "sid_number": sid, "fob_point": fob}

    def _ship_to(self) -> dict[str, Any]:
        name = _find_value(
            self.md,
            r"ship\s+to[:\s]+([^\n,]{3,60})",
            r"consignee[:\s]+([^\n,]{3,60})",
            r"to[:\s]+([^\n,]{3,60})",
            default="",
        )
        address = _find_value(
            self.md,
            r"ship\s+to\s+address[:\s]+([^\n]{5,120})",
            default="",
        )
        city = _find_value(self.md, r"ship\s+to.*?city[:\s]+([^\n,]{3,40})", default="")
        loc = _find_value(self.md, r"location\s*(?:number|no\.?|#)?[:\s]+([A-Z0-9\-]+)", default="")
        cid = _find_value(self.md, r"cid[:\s]+([A-Z0-9\-]+)", default="")
        return {"name": name, "location_number": loc, "address": address, "city_state_zip": city,
                "cid_number": cid, "fob_point": False}

    def _third_party(self) -> dict[str, Any]:
        name = _find_value(self.md, r"third\s+party[:\s]+([^\n,]{3,60})", default="")
        return {"name": name, "address": "", "city_state_zip": ""}

    def _special_instructions(self) -> str:
        return _find_value(
            self.md,
            r"special\s+instructions?[:\s]+([^\n]{5,200})",
            r"instructions?[:\s]+([^\n]{5,200})",
            default="",
        )

    def _carrier_details(self) -> dict[str, Any]:
        carrier = _find_value(
            self.md,
            r"carrier\s*(?:name)?[:\s]+([^\n,]{3,60})",
            r"(?:trucking|shipping)\s+company[:\s]+([^\n,]{3,60})",
            default="",
        )
        trailer = _find_value(self.md, r"trailer\s*(?:number|no\.?|#)?[:\s]+([A-Z0-9\-]+)", default="")
        seal = _find_value(self.md, r"seal\s*(?:number|no\.?|#)?[:\s]+([A-Z0-9,\s\-]+)", default="")
        scac = _find_value(self.md, r"scac[:\s]+([A-Z]{2,6})", default="")
        pro = _find_value(self.md, r"pro\s*(?:number|no\.?|#)?[:\s]+([A-Z0-9\-]+)", default="")
        terms = _find_value(
            self.md,
            r"freight\s+(?:charge\s+)?terms?[:\s]+([^\n,]{3,40})",
            r"payment\s+terms?[:\s]+([^\n,]{3,40})",
            default="Prepaid",
        )
        return {
            "carrier_name": carrier, "trailer_number": trailer, "seal_numbers": seal,
            "scac": scac, "pro_number": pro, "freight_charge_terms": terms,
        }

    def _customer_order_info(self) -> list[dict[str, Any]]:
        rows = _find_table_after(self.md, r"(?:customer\s+order|order\s+info|po|purchase\s+order)")
        if not rows or len(rows) < 2:
            # fallback: build single entry from scattered fields
            order_num = _find_value(self.md, r"(?:order|po)\s*(?:number|no\.?|#)?[:\s]+([A-Z0-9\-]+)", default="")
            pkgs = int(_find_float(self.md, r"(?:packages?|pkgs?)[:\s]+([\d]+)", default=0))
            weight = _find_float(self.md, r"(?:weight|wt\.?)[:\s]+([\d,]+\.?\d*)\s*(?:kg|lbs?)?", default=0.0)
            return [{"order_number": order_num, "pkgs_count": pkgs, "weight": weight,
                     "pallet_slip": False, "additional_info": ""}]
        header = [h.lower() for h in rows[0]]
        results = []
        for row in rows[1:]:
            entry: dict[str, Any] = {"order_number": "", "pkgs_count": 0, "weight": 0.0,
                                     "pallet_slip": False, "additional_info": ""}
            for i, col in enumerate(header):
                if i >= len(row):
                    break
                v = row[i]
                if any(k in col for k in ("order", "po")):
                    entry["order_number"] = v
                elif any(k in col for k in ("pkg", "package", "count")):
                    try:
                        entry["pkgs_count"] = int(float(re.sub(r"[^\d.]", "", v) or "0"))
                    except ValueError:
                        pass
                elif "weight" in col:
                    try:
                        entry["weight"] = float(re.sub(r"[^\d.]", "", v) or "0")
                    except ValueError:
                        pass
                elif "pallet" in col:
                    entry["pallet_slip"] = v.lower() in ("yes", "true", "1")
                elif any(k in col for k in ("info", "note", "additional")):
                    entry["additional_info"] = v
            results.append(entry)
        return results

    def _carrier_commodity_info(self) -> list[dict[str, Any]]:
        rows = _find_table_after(self.md, r"(?:commodity|cargo|goods|carrier\s+info)")
        if not rows or len(rows) < 2:
            desc = _find_value(self.md, r"(?:commodity|goods|cargo|description)[:\s]+([^\n]{3,80})", default="")
            hazmat = _find_bool(self.md, r"(?:hazardous|hazmat)[:\s]+(yes|no|true|false)", default=False)
            weight = _find_float(self.md, r"weight[:\s]+([\d,]+\.?\d*)\s*(?:kg|lbs?)?", default=0.0)
            return [{"handling_unit_qty": 1, "handling_unit_type": "Pallets",
                     "package_qty": 1, "package_type": "Boxes",
                     "weight": weight, "is_hazardous": hazmat,
                     "commodity_description": desc, "nmfc_number": "", "class": ""}]
        header = [h.lower() for h in rows[0]]
        results = []
        for row in rows[1:]:
            entry: dict[str, Any] = {
                "handling_unit_qty": 1, "handling_unit_type": "",
                "package_qty": 1, "package_type": "",
                "weight": 0.0, "is_hazardous": False,
                "commodity_description": "", "nmfc_number": "", "class": "",
            }
            for i, col in enumerate(header):
                if i >= len(row):
                    break
                v = row[i]
                if "handling" in col and "qty" in col:
                    try:
                        entry["handling_unit_qty"] = int(float(re.sub(r"[^\d.]", "", v) or "1"))
                    except ValueError:
                        pass
                elif "handling" in col and "type" in col:
                    entry["handling_unit_type"] = v
                elif "package" in col and "qty" in col:
                    try:
                        entry["package_qty"] = int(float(re.sub(r"[^\d.]", "", v) or "1"))
                    except ValueError:
                        pass
                elif "package" in col and "type" in col:
                    entry["package_type"] = v
                elif "weight" in col:
                    try:
                        entry["weight"] = float(re.sub(r"[^\d.]", "", v) or "0")
                    except ValueError:
                        pass
                elif "hazard" in col:
                    entry["is_hazardous"] = v.lower() in ("yes", "true", "1")
                elif any(k in col for k in ("desc", "commodity", "product")):
                    entry["commodity_description"] = v
                elif "nmfc" in col:
                    entry["nmfc_number"] = v
                elif col == "class":
                    entry["class"] = v
            results.append(entry)
        return results


# ---------------------------------------------------------------------------
# Packing List parser
# ---------------------------------------------------------------------------

class PackingListParser:
    """Extract structured packing list fields from DocStruct markdown."""

    def __init__(self, markdown: str):
        self.md = markdown

    def parse(self) -> dict[str, Any]:
        return {
            "delivery_to": self._delivery_to(),
            "from_business": self._from_business(),
            "shipping_refs": self._shipping_refs(),
            "items": self._items(),
            "notes": self._notes(),
        }

    def _delivery_to(self) -> dict[str, Any]:
        customer = _find_value(
            self.md,
            r"delivery\s+to[:\s]+([^\n,]{3,60})",
            r"ship\s+to[:\s]+([^\n,]{3,60})",
            r"consignee[:\s]+([^\n,]{3,60})",
            default="",
        )
        address_lines = []
        addr = _find_value(
            self.md,
            r"(?:delivery|ship)\s+to\s+address[:\s]+([^\n]{5,120})",
            default="",
        )
        if addr:
            address_lines = [addr]
        phone = _find_value(self.md, r"(?:telephone|phone|tel)[:\s]+([+\d\s\-()]{6,20})", default="")
        email = _find_value(self.md, r"(?:e-?mail)[:\s]+([\w.+\-]+@[\w.\-]+)", default="")
        return {"customer_name": customer, "address_lines": address_lines, "telephone": phone, "email": email}

    def _from_business(self) -> dict[str, Any]:
        name = _find_value(
            self.md,
            r"from\s+business[:\s]+([^\n,]{3,60})",
            r"(?:shipper|seller|supplier|from)[:\s]+([^\n,]{3,60})",
            default="",
        )
        address_lines = []
        addr = _find_value(self.md, r"from\s+(?:business\s+)?address[:\s]+([^\n]{5,120})", default="")
        if addr:
            address_lines = [addr]
        return {"business_name": name, "address_lines": address_lines}

    def _shipping_refs(self) -> dict[str, Any]:
        order_ref = _find_value(
            self.md,
            r"(?:order\s+reference|order\s+ref|po|purchase\s+order)[:\s]+([A-Z0-9\-]+)",
            default="",
        )
        order_date = _find_value(
            self.md,
            r"order\s+date[:\s]+([\d]{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/][\d]{2,4})",
            default="",
        )
        delivery_method = _find_value(
            self.md,
            r"(?:delivery\s+method|shipping\s+method|mode)[:\s]+([^\n,]{3,40})",
            default="",
        )
        delivery_num = _find_value(
            self.md,
            r"delivery\s*(?:number|no\.?|#)?[:\s]+([A-Z0-9\-]+)",
            default="",
        )
        delivery_date = _find_value(
            self.md,
            r"delivery\s+date[:\s]+([\d]{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/][\d]{2,4})",
            default="",
        )
        return {
            "order_reference": order_ref, "order_date": order_date,
            "delivery_method": delivery_method, "delivery_number": delivery_num,
            "delivery_date": delivery_date,
        }

    def _items(self) -> list[dict[str, Any]]:
        rows = _find_table_after(self.md, r"(?:items?|packing|goods|contents?)")
        if not rows or len(rows) < 2:
            return []
        header = [h.lower() for h in rows[0]]
        items = []
        for row in rows[1:]:
            entry: dict[str, Any] = {
                "item_number": "", "description": "",
                "qty_ordered": 0, "qty_shipped": 0,
                "weight_kg": 0.0, "volume_cbm": 0.0,
                "container_number": "",
            }
            for i, col in enumerate(header):
                if i >= len(row):
                    break
                v = row[i]
                if any(k in col for k in ("item no", "item#", "item_number", "item number", "sku")):
                    entry["item_number"] = v
                elif any(k in col for k in ("desc", "product", "goods", "commodity")):
                    entry["description"] = v
                elif any(k in col for k in ("qty order", "ordered")):
                    try:
                        entry["qty_ordered"] = int(float(re.sub(r"[^\d.]", "", v) or "0"))
                    except ValueError:
                        pass
                elif any(k in col for k in ("qty ship", "shipped", "quantity")):
                    try:
                        entry["qty_shipped"] = int(float(re.sub(r"[^\d.]", "", v) or "0"))
                    except ValueError:
                        pass
                elif "weight" in col:
                    try:
                        entry["weight_kg"] = float(re.sub(r"[^\d.]", "", v) or "0")
                    except ValueError:
                        pass
                elif any(k in col for k in ("volume", "cbm", "m3")):
                    try:
                        entry["volume_cbm"] = float(re.sub(r"[^\d.]", "", v) or "0")
                    except ValueError:
                        pass
                elif "container" in col:
                    entry["container_number"] = v
            if entry["description"] or entry["item_number"]:
                items.append(entry)
        return items

    def _notes(self) -> str:
        return _find_value(
            self.md,
            r"(?:notes?|remarks?|comments?)[:\s]+([^\n]{5,200})",
            default="",
        )


# ---------------------------------------------------------------------------
# Assembly: combine 3 parsers into ShipmentProcessor-ready dict
# ---------------------------------------------------------------------------

def assemble_shipment(bol_markdown: str, invoice_markdown: str, packing_list_markdown: str) -> dict[str, Any]:
    """
    Parse all 3 document markdowns and return a dict that
    ShipmentProcessor(data).process() can consume directly.
    """
    bol = BolParser(bol_markdown).parse()
    invoice = InvoiceParser(invoice_markdown).parse()
    pl = PackingListParser(packing_list_markdown).parse()

    # Detect category from invoice HS codes
    first_hs = ""
    if invoice.get("line_items"):
        first_hs = invoice["line_items"][0].get("hs_code", "")
    category = _detect_category(first_hs) if first_hs else "General"

    product_id = f"CP-{str(uuid.uuid4())[:8].upper()}"

    return {
        "product_id": product_id,
        "status": "PENDING",
        "category": category,
        "category_metadata": {
            "category": category,
            "metadata_fields": _build_metadata_fields(category),
        },
        "bill_of_lading": bol,
        "invoice": invoice,
        "packing_list": pl,
    }
