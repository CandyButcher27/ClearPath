import json
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path


# ---------------------------------------------------------------------------
# Per-HS-chapter density bounds (kg/m³).
# Used by check_density to replace the single magic-number threshold.
# Keys are the first two digits of the HS code (string).
# ---------------------------------------------------------------------------
HS_DENSITY_BOUNDS = {
    "25": (1000, 3500),   # Salt, sulphur, stone, sand
    "26": (1500, 5000),   # Ores, slag, ash
    "27": (700,  1100),   # Mineral fuels, oils
    "28": (500,  3500),   # Inorganic chemicals
    "29": (400,  2000),   # Organic chemicals
    "38": (300,  2000),   # Misc chemical products
}
# Default bounds used when the HS chapter is not in the table above.
DEFAULT_DENSITY_BOUNDS = (50, 5000)

# UoM type classification sets used by check_overcharge and check_uom.
# If invoice quantity is in WEIGHT_UOMS but PL qty_shipped is a unit count,
# the two numbers are dimensionally incompatible and must not be compared.
WEIGHT_UOMS = {
    "kg", "g", "gram", "grams", "kilogram", "kilograms",
    "lbs", "lb", "pound", "pounds",
    "tonne", "tonnes", "ton", "mt",
}
COUNT_UOMS = {
    "unit", "units", "pcs", "pc", "piece", "pieces",
    "carton", "cartons", "crate", "crates",
    "box", "boxes", "tub", "tubs",
    "pallet", "pallets", "bag", "bags",
    "sack", "sacks", "drum", "drums",
    "each", "ea", "set", "sets", "roll", "rolls",
}

# Cold-chain keywords used by check_temp.
COLD_CHAIN_KEYWORDS = {
    "temperature", "refriger", "reefer", "cool", "frozen",
    "cold chain", "chill", "controlled", "keep cold",
}


class ShipmentProcessor:
    def __init__(self, raw_shipment):
        self.raw = raw_shipment if isinstance(raw_shipment, dict) else {}
        self.bol = self._as_dict(self.raw.get("bill_of_lading"))
        self.inv = self._as_dict(self.raw.get("invoice"))
        self.pl = self._as_dict(self.raw.get("packing_list"))
        category_meta = self._as_dict(self.raw.get("category_metadata"))
        self.meta = self._as_dict(category_meta.get("metadata_fields"))
        # FIX 11: pre-compute category once so every method can read self.category
        # without triggering repeated HS-code parsing.
        self.category = self._get_category()

    # -----------------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------------

    def _calculate_similarity(self, a, b):
        """Fuzzy string similarity, 0-100."""
        if not a or not b:
            return 0
        return round(
            SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio() * 100, 2
        )

    # FIX 4: centralised date parser.
    # All date comparisons now go through this method.
    # Previously every check did raw string comparison ("2026-04-20" < "2026-04-03"),
    # which silently produces wrong results for any non-ISO date format.
    def _parse_date(self, s):
        """Return a datetime object or None. Tries ISO format first, then common
        alternatives so a single non-standard date doesn't crash the whole run."""
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None  # unparseable — caller treats as missing

    def _as_dict(self, value):
        """Normalize a value to dict for null/shape-safe nested access."""
        return value if isinstance(value, dict) else {}

    def _as_list(self, value):
        """Normalize a value to list for null/shape-safe iteration."""
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return [value]
        return []

    def _get_category(self):
        # Primary: derive from invoice HS code (most authoritative for a complete doc)
        line_items = self._as_list(self.inv.get("line_items"))
        hs = line_items[0].get("hs_code", "") if line_items else ""
        if hs.startswith(("07", "08", "04", "21")):
            return "Perishables"
        if hs.startswith(("84", "85", "94")):
            return "Manufactured Goods"
        if hs.startswith(("25", "26", "27", "28", "29", "38")):
            return "Raw Materials"
        # Fallback: use the category declared at the top level of the raw shipment
        # (set by the document parser or the test harness). This handles the case
        # where the invoice is missing or has null line_items — without this,
        # a perishable with a broken invoice would be classified as "General" and
        # skip all perishable-specific checks including expiry.
        declared = self.raw.get("category")
        if declared in ("Perishables", "Manufactured Goods", "Raw Materials"):
            return declared
        return "General"

    def _pl_address(self):
        """Join the packing-list address_lines list into a single string."""
        delivery_to = self._as_dict(self.pl.get("delivery_to"))
        lines = delivery_to.get("address_lines", [])
        if isinstance(lines, str):
            lines = [lines]
        elif not isinstance(lines, list):
            lines = []
        return ", ".join(lines)

    def _classify_uom(self, uom_str):
        """Return 'weight', 'count', or 'unknown' for a unit-of-measure string."""
        if not uom_str:
            return "unknown"
        uom = uom_str.lower().strip()
        if uom in WEIGHT_UOMS:
            return "weight"
        if uom in COUNT_UOMS:
            return "count"
        return "unknown"

    def _first_dict(self, items):
        """Return first dict from a list-like value, otherwise {}."""
        if isinstance(items, dict):
            return items
        if not isinstance(items, list) or not items:
            return {}
        first = items[0]
        return first if isinstance(first, dict) else {}

    # -----------------------------------------------------------------------
    # Main processor
    # -----------------------------------------------------------------------

    def process(self):
        weight = sum(
            i.get("weight_kg", 0)
            for i in self._as_list(self.pl.get("items"))
            if isinstance(i, dict)
        )
        pkgs = sum(
            p.get("pkgs_count", 0)
            for p in self._as_list(self.bol.get("customer_order_info"))
            if isinstance(p, dict)
        )
        ship_to = self._as_dict(self.bol.get("ship_to"))
        totals = self._as_dict(self.inv.get("totals"))

        flags = {
            "logistics_flags": {
                "destination_address_mismatch": self.check_destination_address(),
                "origin_address_mismatch":      self.check_origin_address(),
                "container_conflict":           self.check_container(),
                "scac_missing":                 self.check_scac(),
                "po_mismatch":                  self.check_po(),
                "incoterm_conflict":            self.check_incoterm(),
            },
            "quantity_weight_flags": {
                "weight_mismatch":  self.check_weight(weight),
                "gross_net_logic":  self.check_gross_net(),
                "overcharge_risk":  self.check_overcharge(),
                "short_shipment":   self.check_short_ship(),
                "uom_mismatch":     self.check_uom(),
            },
            "product_specific_flags": {
                "hazmat_mismatch":        self.check_hazmat(),
                "expiry_check":           self.check_expiry(),
                "shelf_life_error":       self.check_shelf_life(),
                "temp_control_missing":   self.check_temp(),
                "serial_count_mismatch":  self.check_serials(),
                "density_anomaly":        self.check_density(),
            },
            "financial_timing_flags": {
                "tax_calculation_error": self.check_tax(),
                "total_value_mismatch":  self.check_total_math(),
                "payment_due_logic":     self.check_payment_dates(),
                "lead_time_anomaly":     self.check_timeline(),
            },
        }

        return {
            "product_id": self.raw.get("product_id", "UNKNOWN"),
            "category_metadata": {
                "applied_category": self.category,
                "fields": self.meta,
            },
            "normalized_aggregates": {
                "total_weight_reported_kg": weight,
                "total_package_count": pkgs,
                "ship_to_address_standardized": (
                    f"{ship_to.get('address', '')}, {ship_to.get('city_state_zip', '')}"
                ),
                "total_value": totals.get("grand_total"),
                "currency": totals.get("currency"),
            },
            "inconsistency_flags": flags,
        }

    # -----------------------------------------------------------------------
    # LOGISTICS
    # -----------------------------------------------------------------------

    # FIX 1a — destination address: now compares BoL ship_to vs PL delivery_to.
    # Previously compared BoL ship_to vs Invoice bill_to_info, which are
    # legitimately different parties in most international shipments
    # (third-party billing is normal) and therefore produced constant false flags.
    def check_destination_address(self):
        a1 = self._as_dict(self.bol.get("ship_to")).get("address", "")
        a2 = self._pl_address()
        if not a1 or not a2:
            return None
        score = self._calculate_similarity(a1, a2)
        return {"is_flagged": score < 75, "bol_ship_to": a1, "pl_delivery_to": a2, "score": score}

    # FIX 1b — origin address: new check comparing BoL ship_from vs Invoice
    # seller_info. These must match; a discrepancy means the carrier's record of
    # who handed over the goods differs from the seller's own invoice.
    def check_origin_address(self):
        # Compose full address from BoL ship_from (street + city_state_zip) so the
        # comparison is against the same level of detail as the invoice seller address.
        sf = self._as_dict(self.bol.get("ship_from"))
        a1 = f"{sf.get('address', '')} {sf.get('city_state_zip', '')}".strip()
        a2 = self._as_dict(self.inv.get("seller_info")).get("address", "")
        if not a1 or not a2:
            return None
        score = self._calculate_similarity(a1, a2)
        return {"is_flagged": score < 75, "bol_ship_from": a1, "inv_seller": a2, "score": score}

    # FIX 6a — container check now uses set comparison across ALL line items
    # instead of [0] index, so a shipment with multiple containers is fully checked.
    def check_container(self):
        inv_conts = {
            li.get("container_number")
            for li in self._as_list(self.inv.get("line_items"))
            if isinstance(li, dict)
            if li.get("container_number") and li.get("container_number") != "N/A"
        }
        pl_conts = {
            i.get("container_number")
            for i in self._as_list(self.pl.get("items"))
            if isinstance(i, dict)
            if i.get("container_number") and i.get("container_number") != "N/A"
        }
        if not inv_conts or not pl_conts:
            return None
        only_inv = list(inv_conts - pl_conts)
        only_pl  = list(pl_conts - inv_conts)
        return {
            "is_flagged":    bool(only_inv or only_pl),
            "only_in_invoice": only_inv,
            "only_in_pl":      only_pl,
        }

    def check_scac(self):
        scac = self._as_dict(self.bol.get("carrier_details")).get("scac")
        if scac is None:
            return None
        return {"is_flagged": not scac, "value": scac}

    def check_po(self):
        p1 = self._first_dict(self.bol.get("customer_order_info")).get("order_number")
        p2 = self._as_dict(self.pl.get("shipping_refs")).get("order_reference")
        if not p1 or not p2:
            return None
        return {"is_flagged": p1 != p2, "bol_po": p1, "pl_po": p2}

    # FIX 2 — Incoterm logic was backwards.
    # FOB + "Collect" is CORRECT (buyer owns goods from origin, buyer pays freight).
    # The actual conflict is FOB + "Prepaid" (seller paying freight they've handed
    # off responsibility for). Condition is now inverted.
    def check_incoterm(self):
        is_fob = self._as_dict(self.bol.get("ship_from")).get("fob_point")
        terms = self._as_dict(self.bol.get("carrier_details")).get("freight_charge_terms")
        if is_fob is None or not terms:
            return None
        # Flagged when: FOB point is True AND seller is paying freight (Prepaid)
        return {"is_flagged": bool(is_fob and "Prepaid" in terms), "fob": is_fob, "terms": terms}

    # -----------------------------------------------------------------------
    # WEIGHTS & QUANTITIES
    # -----------------------------------------------------------------------

    # FIX 3 — weight tolerance is now percentage-based.
    # A flat 10 kg threshold is meaningless for a 25,000 kg bulk cargo shipment
    # (0.04%) and alarmingly lenient for a 40 kg parcel (25%).
    # New rule: flag if variance exceeds 2% of PL weight, with a 10 kg floor to
    # avoid noise on very small shipments.
    def check_weight(self, pl_weight):
        bol_weight = sum(
            c.get("weight", 0)
            for c in self._as_list(self.bol.get("carrier_commodity_info"))
            if isinstance(c, dict)
        )
        if bol_weight == 0 or pl_weight == 0:
            return None
        variance  = abs(bol_weight - pl_weight)
        threshold = max(10, pl_weight * 0.02)
        return {
            "is_flagged": variance > threshold,
            "bol_kg": bol_weight,
            "pl_kg":  pl_weight,
            "variance_kg": round(variance, 2),
            "threshold_kg": round(threshold, 2),
        }

    # FIX 7 — gross_net now flags only when gross is STRICTLY LESS THAN net
    # (physically impossible). Previously used <=, which incorrectly flagged
    # bulk liquids in tare-less containers where gross == net is valid.
    # Guard extended to Manufactured Goods — a packed crate also has packaging
    # weight, making this check relevant beyond Raw Materials.
    def check_gross_net(self):
        if self.category not in ("Raw Materials", "Manufactured Goods"):
            return None
        n = self.meta.get("net_weight")
        g = self.meta.get("gross_weight")
        if n is None or g is None:
            return None
        return {"is_flagged": g < n, "net": n, "gross": g}

    # FIX: UoM trap — check_overcharge now classifies the invoice unit_of_measure
    # before comparing numbers. If the invoice bills in a weight unit (kg) but the
    # PL counts discrete items (tubs, crates), the raw numbers are dimensionally
    # incompatible and comparing them produces a guaranteed false positive.
    # e.g. invoice_qty=300 kg vs pl_qty=50 tubs is not an overcharge — 50 tubs
    # may weigh exactly 300 kg. When a type mismatch is detected the check returns
    # is_flagged=False with a clear reason so the output stays informative.
    def check_overcharge(self):
        inv_items = self._as_list(self.inv.get("line_items"))
        pl_items = self._as_list(self.pl.get("items"))
        if not inv_items or not pl_items:
            return None

        # Use the first invoice line's UoM as representative for the shipment.
        inv_uom      = inv_items[0].get("unit_of_measure", "")
        uom_type     = self._classify_uom(inv_uom)

        inv_qty = sum(li.get("quantity", 0) for li in inv_items)
        pl_qty  = sum(i.get("qty_shipped", 0) for i in pl_items)

        if inv_qty == 0 or pl_qty == 0:
            return None

        # If the invoice is denominated in weight units, the qty number represents
        # a mass (e.g. 300 kg). PL qty_shipped is always a unit count (50 tubs).
        # These cannot be compared numerically — bail out rather than false-flag.
        if uom_type == "weight":
            return {
                "is_flagged": False,
                "reason": "uom_incompatible",
                "note": (
                    f"Invoice qty ({inv_qty}) is in weight unit '{inv_uom}'; "
                    f"PL qty_shipped ({pl_qty}) is a unit count. "
                    "Numeric comparison suppressed to prevent false positive."
                ),
            }

        return {
            "is_flagged": inv_qty > pl_qty,
            "invoice_total_qty": inv_qty,
            "pl_total_shipped":  pl_qty,
            "uom": inv_uom,
        }

    # FIX 6c — short_ship now iterates ALL PL items, not just [0].
    # Returns a list of per-item flags so the caller can see exactly which lines
    # were short-shipped.
    def check_short_ship(self):
        items = self._as_list(self.pl.get("items"))
        if not items:
            return None
        per_item = []
        for item in items:
            ordered = item.get("qty_ordered")
            shipped = item.get("qty_shipped")
            if ordered is None or shipped is None:
                continue
            if shipped < ordered:
                per_item.append({
                    "item_number": item.get("item_number"),
                    "ordered": ordered,
                    "shipped": shipped,
                    "shortfall": ordered - shipped,
                })
        return {"is_flagged": bool(per_item), "short_items": per_item}

    # FIX: check_uom is now a real check instead of a stub returning None.
    # Classifies the invoice unit_of_measure and flags when the invoice and PL
    # are using units from different families (weight vs count), which makes every
    # downstream quantity comparison meaningless. This is the root-cause detection
    # that check_overcharge uses to decide whether to proceed with its math.
    def check_uom(self):
        inv_uom = self._first_dict(self.inv.get("line_items")).get("unit_of_measure")
        if not inv_uom:
            return None
        uom_type = self._classify_uom(inv_uom)
        # PL qty_shipped is always a unit count by schema definition.
        # If the invoice is also count-based, the types are compatible.
        # If the invoice is weight-based, the types are incompatible.
        if uom_type == "weight":
            return {
                "is_flagged": True,
                "reason": "invoice_uses_weight_unit_pl_uses_count",
                "invoice_uom": inv_uom,
                "note": (
                    "Invoice quantity is denominated in a weight unit. "
                    "PL qty_shipped is a unit count. "
                    "Direct quantity comparison will produce false positives."
                ),
            }
        if uom_type == "unknown":
            return {
                "is_flagged": False,
                "reason": "unrecognised_uom",
                "invoice_uom": inv_uom,
                "note": f"UoM '{inv_uom}' not in known weight or count sets — manual review recommended.",
            }
        return {"is_flagged": False, "invoice_uom": inv_uom, "uom_type": uom_type}

    # -----------------------------------------------------------------------
    # PRODUCT SPECIFIC (all category-gated)
    # -----------------------------------------------------------------------

    # FIX 8 — hazmat check is now bidirectional.
    # Previously only caught "meta says hazardous, BoL says not" (under-declaration).
    # The reverse is equally suspicious: BoL declares hazmat that the category
    # metadata doesn't expect, which may indicate a mis-categorised shipment.
    def check_hazmat(self):
        m_h = self.meta.get("is_hazardous_material")
        b_h = self._first_dict(self.bol.get("carrier_commodity_info")).get("is_hazardous")
        if m_h is None or b_h is None:
            return None
        return {"is_flagged": m_h != b_h, "meta_hazmat": m_h, "bol_hazmat": b_h}

    # FIX: Missing data fail-safe — previously returned None whenever delivery_date
    # was absent from shipping_refs, meaning a shipment with a fully missing
    # shipping_refs block (like PRD-007) silently passed expiry checks even when
    # the product was already expired.
    #
    # Fallback chain (most → least authoritative):
    #   1. PL delivery_date      — scheduled delivery, most relevant reference
    #   2. Invoice invoice_date  — at minimum, goods must not be expired at billing
    #   3. datetime.now()        — last resort: is the product already expired today?
    #
    # The fallback used is recorded in the output so auditors know what was compared.
    def check_expiry(self):
        if self.category != "Perishables":
            return None
        exp = self._parse_date(self.meta.get("expiry_date"))
        if not exp:
            return None  # No expiry date in metadata — nothing to check

        shipping_refs = self._as_dict(self.pl.get("shipping_refs"))
        payment_details = self._as_dict(self.inv.get("payment_details"))
        dlv = self._parse_date(shipping_refs.get("delivery_date"))
        fallback_used = None

        if not dlv:
            # Fallback 1: invoice date
            dlv = self._parse_date(payment_details.get("invoice_date"))
            fallback_used = "invoice_date"

        if not dlv:
            # Fallback 2: today
            dlv = datetime.now()
            fallback_used = "system_date"

        return {
            "is_flagged":    exp < dlv,
            "expiry":        self.meta.get("expiry_date"),
            "compared_against": str(dlv.date()),
            "reference_source": fallback_used or "delivery_date",
        }

    def check_shelf_life(self):
        if self.category != "Perishables":
            return None
        days = self.meta.get("shelf_life_remaining_days")
        if days is None:
            return None
        return {"is_flagged": days < 7, "days_remaining": days}

    # FIX 5 — temperature check now uses a set of specific cold-chain keywords
    # instead of the single substring "temp", which matched unrelated strings
    # like "temporary holding instructions" and produced false negatives.
    def check_temp(self):
        if self.category != "Perishables":
            return None
        temp_ctrl = self.meta.get("temperature_control")
        if not isinstance(temp_ctrl, dict):
            temp_ctrl = {}
        req   = temp_ctrl.get("required")
        instr = str(self.bol.get("special_instructions", "")).lower()
        if req is None:
            return None
        found = any(kw in instr for kw in COLD_CHAIN_KEYWORDS)
        return {"is_flagged": bool(req and not found), "instructions_found": found}

    # Stub — None instead of {"is_flagged": False}. Serial parsing requires
    # knowing whether meta serial_number is a single value, a range ("SN001-SN050"),
    # or a comma-separated list — that normalisation isn't done yet.
    def check_serials(self):
        if self.category != "Manufactured Goods":
            return None
        # TODO: normalise serial_number field and count entries vs qty_shipped.
        return None

    # FIX 9 — density bounds are now looked up per HS chapter instead of using
    # a single threshold (previously 10 kg/m³, which is below aerogel and lets
    # almost everything through). The HS_DENSITY_BOUNDS table at the top of the
    # file defines physically meaningful ranges per commodity class.
    def check_density(self):
        if self.category != "Raw Materials":
            return None
        w = self.meta.get("net_weight")
        vol_data = self._as_dict(self.meta.get("volume"))
        v = vol_data.get("value")
        unit = vol_data.get("unit", "m3").lower()
        if not w or not v or v == 0:
            return None
        # Normalise volume to m³
        if unit in ("liters", "litres", "l"):
            v = v / 1000
        density = w / v
        hs = self._first_dict(self.inv.get("line_items")).get("hs_code", "")
        lo, hi = HS_DENSITY_BOUNDS.get(hs[:2], DEFAULT_DENSITY_BOUNDS)
        return {
            "is_flagged": not (lo <= density <= hi),
            "calculated_kg_m3": round(density, 2),
            "expected_range":   [lo, hi],
            "hs_chapter":       hs[:2],
        }

    # -----------------------------------------------------------------------
    # FINANCIAL & TIMING
    # -----------------------------------------------------------------------

    # FIX 6d — tax check now iterates ALL line items and returns per-item results.
    # Previously only checked [0], so any mis-calculated tax on items 2..N was
    # silently ignored.
    def check_tax(self):
        line_items = self._as_list(self.inv.get("line_items"))
        if not line_items:
            return None
        errors = []
        for li in line_items:
            sub = li.get("subtotal")
            per = li.get("tax_percentage")
            amt = li.get("tax_amount")
            if None in (sub, per, amt):
                continue
            expected = round(sub * (per / 100), 2)
            if abs(expected - amt) > 0.5:
                errors.append({
                    "description": li.get("description"),
                    "expected_tax": expected,
                    "actual_tax":   amt,
                    "delta":        round(abs(expected - amt), 2),
                })
        return {"is_flagged": bool(errors), "tax_errors": errors}

    def check_total_math(self):
        t = self._as_dict(self.inv.get("totals"))
        sub, tax, grand = t.get("subtotal"), t.get("tax_total"), t.get("grand_total")
        if None in (sub, tax, grand):
            return None
        delta = abs((sub + tax) - grand)
        return {"is_flagged": delta > 1, "delta": round(delta, 2)}

    # FIX 4b — payment date comparison now uses _parse_date.
    def check_payment_dates(self):
        payment_details = self._as_dict(self.inv.get("payment_details"))
        inv_d = self._parse_date(payment_details.get("invoice_date"))
        due_d = self._parse_date(payment_details.get("due_date"))
        if not inv_d or not due_d:
            return None
        return {
            "is_flagged": due_d < inv_d,
            "invoice_date": str(inv_d.date()),
            "due_date":     str(due_d.date()),
        }

    # FIX 4c — timeline comparison now uses _parse_date.
    def check_timeline(self):
        shipping_refs = self._as_dict(self.pl.get("shipping_refs"))
        ord_d = self._parse_date(shipping_refs.get("order_date"))
        dlv_d = self._parse_date(shipping_refs.get("delivery_date"))
        if not ord_d or not dlv_d:
            return None
        return {
            "is_flagged": dlv_d < ord_d,
            "order_date":    str(ord_d.date()),
            "delivery_date": str(dlv_d.date()),
        }


# ---------------------------------------------------------------------------
# Entry point
# FIX 12 — path is now resolved relative to this file via pathlib, so the
# script can be run from any working directory, not only from backend/.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        base = Path(__file__).parent
        with open(base / "sample_data" / "samples.json") as f:
            data = json.load(f)
        output = [ShipmentProcessor(s).process() for s in data]
        out_path = base / "samples_normal.json"
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Audit complete. {len(output)} records → {out_path}")
    except Exception as e:
        print(f"Error: {e}")
        raise
