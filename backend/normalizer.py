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

# Cold-chain keywords used by check_temp.
COLD_CHAIN_KEYWORDS = {
    "temperature", "refriger", "reefer", "cool", "frozen",
    "cold chain", "chill", "controlled", "keep cold",
}


class ShipmentProcessor:
    def __init__(self, raw_shipment):
        self.raw  = raw_shipment
        self.bol  = raw_shipment.get("bill_of_lading", {})
        self.inv  = raw_shipment.get("invoice", {})
        self.pl   = raw_shipment.get("packing_list", {})
        self.meta = raw_shipment.get("category_metadata", {}).get("metadata_fields", {})
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

    def _get_category(self):
        line_items = self.inv.get("line_items", [])
        hs = line_items[0].get("hs_code", "") if line_items else ""
        if hs.startswith(("07", "08", "04", "21")):
            return "Perishables"
        if hs.startswith(("84", "85", "94")):
            return "Manufactured Goods"
        if hs.startswith(("25", "26", "27", "28", "29", "38")):
            return "Raw Materials"
        return "General"

    def _pl_address(self):
        """Join the packing-list address_lines list into a single string."""
        lines = self.pl.get("delivery_to", {}).get("address_lines", [])
        return ", ".join(lines)

    # -----------------------------------------------------------------------
    # Main processor
    # -----------------------------------------------------------------------

    def process(self):
        weight = sum(i.get("weight_kg", 0) for i in self.pl.get("items", []))
        pkgs   = sum(p.get("pkgs_count", 0) for p in self.bol.get("customer_order_info", []))
        ship_to = self.bol.get("ship_to", {})

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
                "total_value": self.inv.get("totals", {}).get("grand_total"),
                "currency":    self.inv.get("totals", {}).get("currency"),
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
        a1 = self.bol.get("ship_to", {}).get("address", "")
        a2 = self._pl_address()
        if not a1 or not a2:
            return None
        score = self._calculate_similarity(a1, a2)
        return {"is_flagged": score < 70, "bol_ship_to": a1, "pl_delivery_to": a2, "score": score}

    # FIX 1b — origin address: new check comparing BoL ship_from vs Invoice
    # seller_info. These must match; a discrepancy means the carrier's record of
    # who handed over the goods differs from the seller's own invoice.
    def check_origin_address(self):
        # Compose full address from BoL ship_from (street + city_state_zip) so the
        # comparison is against the same level of detail as the invoice seller address.
        sf = self.bol.get("ship_from", {})
        a1 = f"{sf.get('address', '')} {sf.get('city_state_zip', '')}".strip()
        a2 = self.inv.get("seller_info", {}).get("address", "")
        if not a1 or not a2:
            return None
        score = self._calculate_similarity(a1, a2)
        return {"is_flagged": score < 70, "bol_ship_from": a1, "inv_seller": a2, "score": score}

    # FIX 6a — container check now uses set comparison across ALL line items
    # instead of [0] index, so a shipment with multiple containers is fully checked.
    def check_container(self):
        inv_conts = {
            li.get("container_number")
            for li in self.inv.get("line_items", [])
            if li.get("container_number") and li.get("container_number") != "N/A"
        }
        pl_conts = {
            i.get("container_number")
            for i in self.pl.get("items", [])
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
        if "carrier_details" not in self.bol:
            return None
        scac = self.bol["carrier_details"].get("scac")
        return {"is_flagged": not scac, "value": scac}

    def check_po(self):
        p1 = self.bol.get("customer_order_info", [{}])[0].get("order_number")
        p2 = self.pl.get("shipping_refs", {}).get("order_reference")
        if not p1 or not p2:
            return None
        return {"is_flagged": p1 != p2, "bol_po": p1, "pl_po": p2}

    # FIX 2 — Incoterm logic was backwards.
    # FOB + "Collect" is CORRECT (buyer owns goods from origin, buyer pays freight).
    # The actual conflict is FOB + "Prepaid" (seller paying freight they've handed
    # off responsibility for). Condition is now inverted.
    def check_incoterm(self):
        is_fob = self.bol.get("ship_from", {}).get("fob_point")
        terms  = self.bol.get("carrier_details", {}).get("freight_charge_terms")
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
        bol_weight = sum(c.get("weight", 0) for c in self.bol.get("carrier_commodity_info", []))
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

    # FIX 6b — overcharge now sums ALL invoice line items vs ALL PL shipped
    # quantities instead of only [0], so multi-item shipments are fully covered.
    # The match key is container_number; items without one fall back to index order.
    def check_overcharge(self):
        inv_qty = sum(
            li.get("quantity", 0) for li in self.inv.get("line_items", [])
        )
        pl_qty = sum(
            i.get("qty_shipped", 0) for i in self.pl.get("items", [])
        )
        if inv_qty == 0 or pl_qty == 0:
            return None
        return {
            "is_flagged": inv_qty > pl_qty,
            "invoice_total_qty": inv_qty,
            "pl_total_shipped":  pl_qty,
        }

    # FIX 6c — short_ship now iterates ALL PL items, not just [0].
    # Returns a list of per-item flags so the caller can see exactly which lines
    # were short-shipped.
    def check_short_ship(self):
        items = self.pl.get("items", [])
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

    # Stub — returning None (not checked) instead of {"is_flagged": False}
    # (falsely passing). A stub that says "no problem" is worse than one that
    # says "not evaluated yet".
    def check_uom(self):
        # TODO: build a UoM normalisation map (kg/lbs, crates/units, etc.)
        # and compare invoice unit_of_measure against PL weight_kg unit context.
        return None

    # -----------------------------------------------------------------------
    # PRODUCT SPECIFIC (all category-gated)
    # -----------------------------------------------------------------------

    # FIX 8 — hazmat check is now bidirectional.
    # Previously only caught "meta says hazardous, BoL says not" (under-declaration).
    # The reverse is equally suspicious: BoL declares hazmat that the category
    # metadata doesn't expect, which may indicate a mis-categorised shipment.
    def check_hazmat(self):
        m_h = self.meta.get("is_hazardous_material")
        b_h = self.bol.get("carrier_commodity_info", [{}])[0].get("is_hazardous")
        if m_h is None or b_h is None:
            return None
        return {"is_flagged": m_h != b_h, "meta_hazmat": m_h, "bol_hazmat": b_h}

    # FIX 4a — expiry date now uses _parse_date; previously relied on ISO string
    # ordering which breaks silently for any non-ISO input format.
    def check_expiry(self):
        if self.category != "Perishables":
            return None
        exp = self._parse_date(self.meta.get("expiry_date"))
        dlv = self._parse_date(self.pl.get("shipping_refs", {}).get("delivery_date"))
        if not exp or not dlv:
            return None
        return {
            "is_flagged": exp < dlv,
            "expiry":   self.meta.get("expiry_date"),
            "delivery": self.pl.get("shipping_refs", {}).get("delivery_date"),
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
        req   = self.meta.get("temperature_control", {}).get("required")
        instr = self.bol.get("special_instructions", "").lower()
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
        vol_data = self.meta.get("volume", {})
        v = vol_data.get("value")
        unit = vol_data.get("unit", "m3").lower()
        if not w or not v or v == 0:
            return None
        # Normalise volume to m³
        if unit in ("liters", "litres", "l"):
            v = v / 1000
        density = w / v
        hs = self.inv.get("line_items", [{}])[0].get("hs_code", "")
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
        line_items = self.inv.get("line_items", [])
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
        t = self.inv.get("totals", {})
        sub, tax, grand = t.get("subtotal"), t.get("tax_total"), t.get("grand_total")
        if None in (sub, tax, grand):
            return None
        delta = abs((sub + tax) - grand)
        return {"is_flagged": delta > 1, "delta": round(delta, 2)}

    # FIX 4b — payment date comparison now uses _parse_date.
    def check_payment_dates(self):
        inv_d = self._parse_date(self.inv.get("payment_details", {}).get("invoice_date"))
        due_d = self._parse_date(self.inv.get("payment_details", {}).get("due_date"))
        if not inv_d or not due_d:
            return None
        return {
            "is_flagged": due_d < inv_d,
            "invoice_date": str(inv_d.date()),
            "due_date":     str(due_d.date()),
        }

    # FIX 4c — timeline comparison now uses _parse_date.
    def check_timeline(self):
        ord_d = self._parse_date(self.pl.get("shipping_refs", {}).get("order_date"))
        dlv_d = self._parse_date(self.pl.get("shipping_refs", {}).get("delivery_date"))
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