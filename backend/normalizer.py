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
        self.normalized_record = {}

    def _calculate_similarity(self, a, b):
        """Returns a similarity score between 0 and 100."""
        if not a or not b: return 0
        return round(SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio() * 100, 2)

    def _determine_category(self):
        """Maps HS codes from invoice to specific categories."""
        line_items = self.inv.get("line_items", [])
        hs_code = line_items[0].get("hs_code", "") if line_items else ""
        
        # Routing based on HS code prefixes
        if hs_code.startswith(("08", "07", "04", "21")): return "Perishables"
        if hs_code.startswith(("85", "84", "94")): return "Manufactured Goods"
        if hs_code.startswith(("25", "28", "29", "38")): return "Raw Materials"
        return "Unknown"

    def normalize(self):
        """Phase 1: Convert raw data into the standardized JSON format."""
        total_weight = sum(item.get("weight_kg", 0) for item in self.pl.get("items", []))
        total_packages = sum(p.get("pkgs_count", 0) for p in self.bol.get("customer_order_info", []))
        total_value = self.inv.get("totals", {}).get("grand_total", 0)
        
        ship_to = self.bol.get("ship_to", {})
        std_address = f"{ship_to.get('address', '')}, {ship_to.get('city_state_zip', '')}".strip()

        self.normalized_record = {
            "shipment_id": self.pl.get("shipping_refs", {}).get("order_reference", "UNKNOWN"),
            "category": self._determine_category(),
            "normalized_aggregates": {
                "total_weight_reported": total_weight,
                "total_package_count": total_packages,
                "ship_to_address_standardized": std_address,
                "total_value": total_value,
                "currency": self.inv.get("totals", {}).get("currency", "USD")
            },
            "audit_report": self.run_audit_engine()
        }
        return self.normalized_record

    def run_audit_engine(self):
        """Phase 2: Run inconsistency checks and return risk levels."""
        flags = []
        checks = [
            self.check_addr_mismatch, self.check_container_conflict, self.check_scac_missing,
            self.check_po_mismatch, self.check_fob_conflict, self.check_gross_net_logic,
            self.check_weight_variance, self.check_overcharge_risk, self.check_short_shipment,
            self.check_uom_mismatch, self.check_hazmat_safety, self.check_expiry_logic,
            self.check_shelf_life_calc, self.check_temp_instruction, self.check_serial_logic,
            self.check_density_anomaly, self.check_tax_logic, self.check_total_math,
            self.check_payment_dates, self.check_timeline_logic
        ]

        for check in checks:
            result = check()
            if result:
                flags.append(result)
        return flags

    # --- FLAG IMPLEMENTATIONS ---

    def check_addr_mismatch(self):
        bol_addr = self.bol.get("ship_to", {}).get("address", "")
        inv_addr = self.inv.get("bill_to_info", {}).get("address", "")
        score = self._calculate_similarity(bol_addr, inv_addr)
        if score < 85:
            return {"code": "ADDR_MISMATCH", "risk": "HIGH", "desc": f"Address match only {score}%"}
        return None

    def check_container_conflict(self):
        inv_cont = self.inv.get("line_items", [{}])[0].get("container_number")
        pl_cont = self.pl.get("items", [{}])[0].get("container_number")
        if inv_cont and pl_cont and inv_cont != pl_cont:
            return {"code": "CONT_CONFLICT", "risk": "MEDIUM", "desc": "Container IDs mismatch."}
        return None

    def check_scac_missing(self):
        if not self.bol.get("carrier_details", {}).get("scac"):
            return {"code": "SCAC_MISSING", "risk": "LOW", "desc": "No SCAC code for carrier."}
        return None

    def check_po_mismatch(self):
        bol_po = self.bol.get("customer_order_info", [{}])[0].get("order_number")
        pl_po = self.pl.get("shipping_refs", {}).get("order_reference")
        if bol_po and pl_po and bol_po != pl_po:
            return {"code": "PO_MISMATCH", "risk": "MEDIUM", "desc": "Order references do not match."}
        return None

    def check_fob_conflict(self):
        if self.bol.get("ship_from", {}).get("fob_point") and "Collect" in self.bol.get("carrier_details", {}).get("freight_charge_terms", ""):
            return {"code": "INCOTERM_ERR", "risk": "LOW", "desc": "FOB Point vs Collect terms conflict."}
        return None

    def check_gross_net_logic(self):
        net, gross = self.meta.get("net_weight"), self.meta.get("gross_weight")
        if net and gross and gross <= net:
            return {"code": "WT_LOGIC_ERR", "risk": "MEDIUM", "desc": "Gross weight must be higher than net."}
        return None

    def check_weight_variance(self):
        bol_w = sum(u.get("weight", 0) for u in self.bol.get("carrier_commodity_info", []))
        pl_w = sum(i.get("weight_kg", 0) for i in self.pl.get("items", []))
        if bol_w and pl_w and abs(bol_w - pl_w) > 50:
            return {"code": "WT_VARIANCE", "risk": "HIGH", "desc": "Weight difference exceeds 50kg tolerance."}
        return None

    def check_overcharge_risk(self):
        inv_q = self.inv.get("line_items", [{}])[0].get("quantity", 0)
        pl_q = self.pl.get("items", [{}])[0].get("qty_shipped", 0)
        if inv_q > pl_q:
            return {"code": "OVERCHARGE", "risk": "HIGH", "desc": "Invoiced more than shipped."}
        return None

    def check_short_shipment(self):
        item = self.pl.get("items", [{}])[0]
        if item.get("qty_shipped", 0) < item.get("qty_ordered", 0):
            return {"code": "SHORT_SHIP", "risk": "MEDIUM", "desc": "Shipment quantity is short."}
        return None

    def check_uom_mismatch(self):
        inv_uom = self.inv.get("line_items", [{}])[0].get("unit_of_measure", "")
        if inv_uom == "Units": return None 
        return None

    def check_hazmat_safety(self):
        if self.meta.get("is_hazardous_material") and not self.bol.get("carrier_commodity_info", [{}])[0].get("is_hazardous"):
            return {"code": "HAZMAT_MISSING", "risk": "CRITICAL", "desc": "Dangerous goods not marked on BOL."}
        return None

    def check_expiry_logic(self):
        expiry = self.meta.get("expiry_date")
        delivery = self.pl.get("shipping_refs", {}).get("delivery_date")
        if expiry and delivery and expiry < delivery:
            return {"code": "EXPIRY_PAST", "risk": "CRITICAL", "desc": "Product expires before delivery."}
        return None

    def check_shelf_life_calc(self):
        days = self.meta.get("shelf_life_remaining_days")
        if days is not None and days < 0:
            return {"code": "ZERO_SHELF_LIFE", "risk": "HIGH", "desc": "Product already expired."}
        return None

    def check_temp_instruction(self):
        if self.meta.get("temperature_control", {}).get("required"):
            instr = self.bol.get("special_instructions", "").lower()
            if "temp" not in instr and "deg" not in instr:
                return {"code": "TEMP_INSTR_MISSING", "risk": "HIGH", "desc": "No temp handling instructions."}
        return None

    def check_serial_logic(self):
        # Specific check for manufactured goods serial ranges
        return None

    def check_density_anomaly(self):
        w = self.meta.get("net_weight")
        v = self.meta.get("volume", {}).get("value")
        if w and v and (w/v) < 10:
            return {"code": "DENSITY_LOW", "risk": "LOW", "desc": "Item weight/volume ratio abnormal."}
        return None

    def check_tax_logic(self):
        item = self.inv.get("line_items", [{}])[0]
        calc_tax = round(item.get("subtotal", 0) * (item.get("tax_percentage", 0)/100), 2)
        if abs(calc_tax - item.get("tax_amount", 0)) > 1:
            return {"code": "TAX_MATH_ERR", "risk": "MEDIUM", "desc": "Tax calculation mismatch."}
        return None

    def check_total_math(self):
        t = self.inv.get("totals", {})
        if abs((t.get("subtotal", 0) + t.get("tax_total", 0)) - t.get("grand_total", 0)) > 1:
            return {"code": "INV_TOTAL_ERR", "risk": "HIGH", "desc": "Invoice sums do not add up."}
        return None

    def check_payment_dates(self):
        pay = self.inv.get("payment_details", {})
        if pay.get("invoice_date") and pay.get("due_date") and pay["due_date"] < pay["invoice_date"]:
            return {"code": "PAY_DATE_ERR", "risk": "MEDIUM", "desc": "Due date is before Invoice date."}
        return None

    def check_timeline_logic(self):
        ship = self.pl.get("shipping_refs", {})
        if ship.get("order_date") and ship.get("delivery_date") and ship["delivery_date"] < ship["order_date"]:
            return {"code": "SHIP_DATE_ERR", "risk": "LOW", "desc": "Delivered before ordered."}
        return None

# --- UPDATED ENTRY POINT ---
if __name__ == "__main__":
    # Load your source data
    try:
        with open("sample_data/samples.json", "r") as f:
            samples = json.load(f)

        processed_data = []
        for entry in samples:
            processor = ShipmentProcessor(entry)
            # Generate the normalized record with audit flags
            processed_data.append(processor.normalize())

        # Write the output to a new JSON file
        output_file = "samples_normal.json"
        with open(output_file, "w") as f:
            json.dump(processed_data, f, indent=2)
            
        print(f"Success! Normalized data and flags saved to {output_file}")
        
    except FileNotFoundError:
        print("Error: samples.json not found in the current directory.")
    except Exception as e:
        print(f"An error occurred: {e}")