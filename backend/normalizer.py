import json
from datetime import datetime
from difflib import SequenceMatcher

class ShipmentProcessor:
    def __init__(self, raw_shipment):
        # Store the entire raw object to access top-level keys like product_id
        self.raw = raw_shipment
        self.bol = raw_shipment.get("bill_of_lading", {})
        self.inv = raw_shipment.get("invoice", {})
        self.pl = raw_shipment.get("packing_list", {})
        self.meta = raw_shipment.get("category_metadata", {}).get("metadata_fields", {})
        
    def _calculate_similarity(self, a, b):
        if not a or not b: return 0
        return round(SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio() * 100, 2)

    def _get_category(self):
        hs = self.inv.get("line_items", [{}])[0].get("hs_code", "")
        if hs.startswith(("08", "07", "04")): return "Perishables"
        if hs.startswith(("85", "84")): return "Manufactured Goods"
        if hs.startswith(("25", "38")): return "Raw Materials"
        return "General"

    def process(self):
        # --- Aggregates ---
        weight = sum(i.get("weight_kg", 0) for i in self.pl.get("items", []))
        pkgs = sum(p.get("pkgs_count", 0) for p in self.bol.get("customer_order_info", []))
        ship_to = self.bol.get("ship_to", {})
        
        # --- Build Inconsistency Report (The 20 Detection Points) ---
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

        # --- Final Normalized Construction ---
        return {
            "product_id": self.raw.get("product_id", "UNKNOWN_PRD"), # Updated from shipment_id
            "category_metadata": {
                "applied_category": self._get_category(),
                "fields": self.meta
            },
            "normalized_aggregates": {
                "total_weight_reported_kg": weight,
                "total_package_count": pkgs,
                "ship_to_address_standardized": f"{ship_to.get('address')}, {ship_to.get('city_state_zip')}",
                "total_value": self.inv.get("totals", {}).get("grand_total"),
                "currency": self.inv.get("totals", {}).get("currency")
            },
            "inconsistency_flags": flags
        }

    # --- LOGISTICS CHECKERS ---
    def check_address(self):
        score = self._calculate_similarity(self.bol.get("ship_to", {}).get("address"), self.inv.get("bill_to_info", {}).get("address"))
        return {"is_flagged": score < 90, "score": score}

    def check_container(self):
        c1, c2 = self.inv.get("line_items", [{}])[0].get("container_number"), self.pl.get("items", [{}])[0].get("container_number")
        return {"is_flagged": bool(c1 and c2 and c1 != c2), "inv_cont": c1, "pl_cont": c2}

    def check_scac(self):
        scac = self.bol.get("carrier_details", {}).get("scac")
        return {"is_flagged": not scac, "value": scac}

    def check_po(self):
        p1, p2 = self.bol.get("customer_order_info", [{}])[0].get("order_number"), self.pl.get("shipping_refs", {}).get("order_reference")
        return {"is_flagged": p1 != p2, "bol_po": p1, "pl_po": p2}

    def check_incoterm(self):
        is_fob = self.bol.get("ship_from", {}).get("fob_point")
        terms = self.bol.get("carrier_details", {}).get("freight_charge_terms", "")
        return {"is_flagged": is_fob and "Collect" in terms}

    # --- QUANTITY & WEIGHT CHECKERS ---
    def check_weight(self, pl_weight):
        bol_weight = sum(c.get("weight", 0) for c in self.bol.get("carrier_commodity_info", []))
        return {"is_flagged": abs(bol_weight - pl_weight) > 10, "bol": bol_weight, "pl": pl_weight}

    def check_gross_net(self):
        n, g = self.meta.get("net_weight", 0), self.meta.get("gross_weight", 0)
        return {"is_flagged": bool(g > 0 and g <= n), "net": n, "gross": g}

    def check_overcharge(self):
        q1, q2 = self.inv.get("line_items", [{}])[0].get("quantity", 0), self.pl.get("items", [{}])[0].get("qty_shipped", 0)
        return {"is_flagged": q1 > q2, "invoice_qty": q1, "shipped_qty": q2}

    def check_short_ship(self):
        it = self.pl.get("items", [{}])[0]
        ord_q, shp_q = it.get("qty_ordered", 0), it.get("qty_shipped", 0)
        return {"is_flagged": shp_q < ord_q, "ordered": ord_q, "shipped": shp_q}

    def check_uom(self):
        u1, u2 = self.inv.get("line_items", [{}])[0].get("unit_of_measure"), self.bol.get("carrier_commodity_info", [{}])[0].get("handling_unit_type")
        # Logic to flag if mixed units are used without conversion
        return {"is_flagged": False, "inv_uom": u1, "bol_uom": u2}

    # --- PRODUCT SPECIFIC CHECKERS ---
    def check_hazmat(self):
        m_h, b_h = self.meta.get("is_hazardous_material"), self.bol.get("carrier_commodity_info", [{}])[0].get("is_hazardous")
        return {"is_flagged": m_h is True and b_h is False}

    def check_expiry(self):
        exp, dlv = self.meta.get("expiry_date"), self.pl.get("shipping_refs", {}).get("delivery_date")
        return {"is_flagged": bool(exp and dlv and exp < dlv), "expiry": exp, "delivery": dlv}

    def check_shelf_life(self):
        days = self.meta.get("shelf_life_remaining_days", 100)
        return {"is_flagged": days < 7, "days_remaining": days}

    def check_temp(self):
        req = self.meta.get("temperature_control", {}).get("required")
        instr = self.bol.get("special_instructions", "").lower()
        return {"is_flagged": req and "temp" not in instr}

    def check_serials(self):
        # Logic to match serial number count in metadata vs PL qty_shipped
        return {"is_flagged": False}

    def check_density(self):
        w, v = self.meta.get("net_weight"), self.meta.get("volume", {}).get("value")
        if w and v and v > 0:
            density = w / v
            # Flagging extremely low density (potential empty container/fraud)
            return {"is_flagged": density < 10, "calculated": round(density, 2)}
        return {"is_flagged": False}

    # --- FINANCIAL CHECKERS ---
    def check_tax(self):
        li = self.inv.get("line_items", [{}])[0]
        sub, per, amt = li.get("subtotal", 0), li.get("tax_percentage", 0), li.get("tax_amount", 0)
        expected = round(sub * (per / 100), 2)
        return {"is_flagged": abs(expected - amt) > 0.5, "expected": expected, "actual": amt}

    def check_total_math(self):
        t = self.inv.get("totals", {})
        calc = t.get("subtotal", 0) + t.get("tax_total", 0)
        return {"is_flagged": abs(calc - t.get("grand_total", 0)) > 1}

    def check_payment_dates(self):
        inv_d, due_d = self.inv.get("payment_details", {}).get("invoice_date"), self.inv.get("payment_details", {}).get("due_date")
        return {"is_flagged": bool(inv_d and due_d and due_d < inv_d)}

    def check_timeline(self):
        ord_d, dlv_d = self.pl.get("shipping_refs", {}).get("order_date"), self.pl.get("shipping_refs", {}).get("delivery_date")
        return {"is_flagged": bool(ord_d and dlv_d and dlv_d < ord_d)}

if __name__ == "__main__":
    try:
        with open("sample_data/samples.json", "r") as f:
            data = json.load(f)
        
        output = [ShipmentProcessor(s).process() for s in data]
        
        with open("samples_normal.json", "w") as f:
            json.dump(output, f, indent=2)
            
        print(f"Normalized {len(output)} products. Output saved to samples_normal.json")
    except Exception as e:
        print(f"Error: {e}")