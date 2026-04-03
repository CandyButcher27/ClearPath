import json
from datetime import datetime
from difflib import SequenceMatcher

class ShipmentProcessor:
    def __init__(self, raw_shipment):
        self.raw = raw_shipment
        self.bol = raw_shipment.get("bill_of_lading", {})
        self.inv = raw_shipment.get("invoice", {})
        self.pl = raw_shipment.get("packing_list", {})
        self.meta = raw_shipment.get("category_metadata", {}).get("metadata_fields", {})
        # Pre-determine category to gatekeep specific functions
        self.category = self._get_category()
        
    def _calculate_similarity(self, a, b):
        if not a or not b: return 0
        return round(SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio() * 100, 2)

    def _get_category(self):
        line_items = self.inv.get("line_items", [])
        hs = line_items[0].get("hs_code", "") if line_items else ""
        if hs.startswith(("08", "07", "04", "21")): return "Perishables"
        if hs.startswith(("85", "84", "94")): return "Manufactured Goods"
        if hs.startswith(("25", "28", "29", "38")): return "Raw Materials"
        return "General"

    def process(self):
        weight = sum(i.get("weight_kg", 0) for i in self.pl.get("items", []))
        pkgs = sum(p.get("pkgs_count", 0) for p in self.bol.get("customer_order_info", []))
        ship_to = self.bol.get("ship_to", {})
        
        flags = {
            "logistics_flags": {
                "address_mismatch": self.check_address(),
                "container_conflict": self.check_container(),
                "scac_missing": self.check_scac(),
                "po_mismatch": self.check_po(),
                "incoterm_conflict": self.check_incoterm()
            },
            "quantity_weight_flags": {
                "weight_mismatch": self.check_weight(weight),
                "gross_net_logic": self.check_gross_net(),
                "overcharge_risk": self.check_overcharge(),
                "short_shipment": self.check_short_ship(),
                "uom_mismatch": self.check_uom()
            },
            "product_specific_flags": {
                "hazmat_mismatch": self.check_hazmat(),
                "expiry_check": self.check_expiry(),
                "shelf_life_error": self.check_shelf_life(),
                "temp_control_missing": self.check_temp(),
                "serial_count_mismatch": self.check_serials(),
                "density_anomaly": self.check_density()
            },
            "financial_timing_flags": {
                "tax_calculation_error": self.check_tax(),
                "total_value_mismatch": self.check_total_math(),
                "payment_due_logic": self.check_payment_dates(),
                "lead_time_anomaly": self.check_timeline()
            }
        }

        return {
            "product_id": self.raw.get("product_id", "UNKNOWN"),
            "category_metadata": {
                "applied_category": self.category,
                "fields": self.meta
            },
            "normalized_aggregates": {
                "total_weight_reported_kg": weight,
                "total_package_count": pkgs,
                "ship_to_address_standardized": f"{ship_to.get('address', '')}, {ship_to.get('city_state_zip', '')}",
                "total_value": self.inv.get("totals", {}).get("grand_total"),
                "currency": self.inv.get("totals", {}).get("currency")
            },
            "inconsistency_flags": flags
        }

    # --- LOGISTICS ---
    def check_address(self):
        a1, a2 = self.bol.get("ship_to", {}).get("address"), self.inv.get("bill_to_info", {}).get("address")
        if not a1 or not a2: return None
        score = self._calculate_similarity(a1, a2)
        return {"is_flagged": score < 60, "score": score}

    def check_container(self):
        c1 = self.inv.get("line_items", [{}])[0].get("container_number")
        c2 = self.pl.get("items", [{}])[0].get("container_number")
        if not c1 or not c2 or c1 == "N/A" or c2 == "N/A": return None
        return {"is_flagged": c1 != c2, "inv_cont": c1, "pl_cont": c2}

    def check_scac(self):
        scac = self.bol.get("carrier_details", {}).get("scac")
        return {"is_flagged": not scac} if "carrier_details" in self.bol else None

    def check_po(self):
        p1 = self.bol.get("customer_order_info", [{}])[0].get("order_number")
        p2 = self.pl.get("shipping_refs", {}).get("order_reference")
        if not p1 or not p2: return None
        return {"is_flagged": p1 != p2, "bol_po": p1, "pl_po": p2}

    def check_incoterm(self):
        is_fob = self.bol.get("ship_from", {}).get("fob_point")
        terms = self.bol.get("carrier_details", {}).get("freight_charge_terms")
        if is_fob is None or not terms: return None
        return {"is_flagged": is_fob and "Collect" in terms}

    # --- WEIGHTS & QTY ---
    def check_weight(self, pl_weight):
        bol_weight = sum(c.get("weight", 0) for c in self.bol.get("carrier_commodity_info", []))
        if bol_weight == 0 or pl_weight == 0: return None
        return {"is_flagged": abs(bol_weight - pl_weight) > 10, "bol": bol_weight, "pl": pl_weight}

    def check_gross_net(self):
        if self.category != "Raw Materials": return None # Guard
        n, g = self.meta.get("net_weight"), self.meta.get("gross_weight")
        if n is None or g is None: return None
        return {"is_flagged": g <= n, "net": n, "gross": g}

    def check_overcharge(self):
        q1 = self.inv.get("line_items", [{}])[0].get("quantity")
        q2 = self.pl.get("items", [{}])[0].get("qty_shipped")
        if q1 is None or q2 is None: return None
        return {"is_flagged": q1 > q2, "invoice_qty": q1, "shipped_qty": q2}

    def check_short_ship(self):
        it = self.pl.get("items", [{}])[0]
        ord_q, shp_q = it.get("qty_ordered"), it.get("qty_shipped")
        if ord_q is None or shp_q is None: return None
        return {"is_flagged": shp_q < ord_q, "ordered": ord_q, "shipped": shp_q}

    def check_uom(self):
        u1 = self.inv.get("line_items", [{}])[0].get("unit_of_measure")
        u2 = self.bol.get("carrier_commodity_info", [{}])[0].get("handling_unit_type")
        if not u1 or not u2: return None
        return {"is_flagged": False} # Logic for UoM conversion mismatch

    # --- PRODUCT SPECIFIC (CATEGORY GATED) ---
    def check_hazmat(self):
        m_h = self.meta.get("is_hazardous_material")
        b_h = self.bol.get("carrier_commodity_info", [{}])[0].get("is_hazardous")
        if m_h is None or b_h is None: return None
        return {"is_flagged": m_h is True and b_h is False}

    def check_expiry(self):
        if self.category != "Perishables": return None # Guard
        exp, dlv = self.meta.get("expiry_date"), self.pl.get("shipping_refs", {}).get("delivery_date")
        if not exp or not dlv: return None
        return {"is_flagged": exp < dlv, "expiry": exp, "delivery": dlv}

    def check_shelf_life(self):
        if self.category != "Perishables": return None # Guard
        days = self.meta.get("shelf_life_remaining_days")
        if days is None: return None
        return {"is_flagged": days < 7, "days_remaining": days}

    def check_temp(self):
        if self.category != "Perishables": return None # Guard
        req = self.meta.get("temperature_control", {}).get("required")
        instr = self.bol.get("special_instructions", "").lower()
        if req is None: return None
        return {"is_flagged": req and "temp" not in instr}

    def check_serials(self):
        if self.category != "Manufactured Goods": return None # Guard
        qty = self.pl.get("items", [{}])[0].get("qty_shipped")
        serials = self.meta.get("serial_number")
        if not qty or not serials: return None
        return {"is_flagged": False} # Parsing logic for serial ranges

    def check_density(self):
        if self.category != "Raw Materials": return None # Guard
        w, v = self.meta.get("net_weight"), self.meta.get("volume", {}).get("value")
        if not w or not v or v == 0: return None
        density = w / v
        return {"is_flagged": density < 10, "calculated": round(density, 2)}

    # --- FINANCIAL ---
    def check_tax(self):
        li = self.inv.get("line_items", [{}])[0]
        sub, per, amt = li.get("subtotal"), li.get("tax_percentage"), li.get("tax_amount")
        if None in [sub, per, amt]: return None
        expected = round(sub * (per / 100), 2)
        return {"is_flagged": abs(expected - amt) > 0.5, "expected": expected, "actual": amt}

    def check_total_math(self):
        t = self.inv.get("totals", {})
        sub, tax, grand = t.get("subtotal"), t.get("tax_total"), t.get("grand_total")
        if None in [sub, tax, grand]: return None
        return {"is_flagged": abs((sub + tax) - grand) > 1}

    def check_payment_dates(self):
        inv_d, due_d = self.inv.get("payment_details", {}).get("invoice_date"), self.inv.get("payment_details", {}).get("due_date")
        if not inv_d or not due_d: return None
        return {"is_flagged": due_d < inv_d}

    def check_timeline(self):
        ord_d, dlv_d = self.pl.get("shipping_refs", {}).get("order_date"), self.pl.get("shipping_refs", {}).get("delivery_date")
        if not ord_d or not dlv_d: return None
        return {"is_flagged": dlv_d < ord_d}

if __name__ == "__main__":
    try:
        with open("sample_data/samples.json", "r") as f:
            data = json.load(f)
        output = [ShipmentProcessor(s).process() for s in data]
        with open("samples_normal.json", "w") as f:
            json.dump(output, f, indent=2)
        print(f"Audit complete. Processed {len(output)} records into samples_normal.json")
    except Exception as e:
        print(f"Error: {e}")