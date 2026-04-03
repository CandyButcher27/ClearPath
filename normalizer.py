import json
from difflib import SequenceMatcher

class ShippingDocumentNormalizer:
    def __init__(self, bol_data, invoice_data, pl_data):
        self.bol_data = bol_data
        self.invoice_data = invoice_data
        self.pl_data = pl_data
        self.normalized_record = {}

    def _calculate_similarity(self, a, b):
        """Returns a similarity score between 0 and 100 using difflib."""
        if not a or not b:
            return 0
        # Convert to lowercase for better matching
        score = SequenceMatcher(None, a.lower(), b.lower()).ratio()
        return round(score * 100, 2)

    def generate_normalized_record(self):
        """Main orchestrator to build the normalized JSON."""
        
        # Step 1 & 2: ID Linking and Raw Data Assembly
        shipment_id = self.pl_data.get("shipping_refs", {}).get("order_reference", "UNKNOWN_ID")
        
        self.normalized_record = {
            "shipment_id": shipment_id,
            "source_documents": {
                "bol_data": self.bol_data,
                "invoice_data": self.invoice_data,
                "packing_list_data": self.pl_data
            },
            "normalized_aggregates": {},
            "inconsistency_flags": {}
        }

        # Step 3: Calculate Aggregates
        self._calculate_aggregates()
        
        # Step 4: Run Flags
        self._run_inconsistency_engine()

        return self.normalized_record

    def _calculate_aggregates(self):
        """Extracts and sums the ground truth data."""
        # 1. Total Weight from Packing List
        total_weight = sum(item.get("weight_kg", 0) for item in self.pl_data.get("items", []))
        
        # 2. Total Packages from Bill of Lading
        total_packages = sum(pkg.get("pkgs_count", 0) for pkg in self.bol_data.get("customer_order_info", []))
        
        # 3. Standardized Address (Using BoL as primary truth for logistics)
        ship_to = self.bol_data.get("ship_to", {})
        standardized_address = f"{ship_to.get('address', '')}, {ship_to.get('city_state_zip', '')}".strip()
        
        # 4. Total Value from Invoice
        total_value = self.invoice_data.get("totals", {}).get("grand_total", 0)

        self.normalized_record["normalized_aggregates"] = {
            "total_weight_reported_kg": total_weight,
            "total_package_count": total_packages,
            "ship_to_address_standardized": standardized_address,
            "total_value": total_value
        }

    def _run_inconsistency_engine(self):
        """Cross-checks the parsed data to flag anomalies."""
        flags = {}
        
        # --- 1. Weight Mismatch Check ---
        pl_weight = self.normalized_record["normalized_aggregates"]["total_weight_reported_kg"]
        # Assuming BoL weight is in KG for this example
        bol_weight = sum(unit.get("weight", 0) for unit in self.bol_data.get("carrier_commodity_info", []))
        
        weight_variance = abs(bol_weight - pl_weight)
        flags["weight_mismatch"] = {
            "is_flagged": weight_variance > 50, # 50kg tolerance
            "bol_weight": bol_weight,
            "packing_list_weight": pl_weight,
            "variance": weight_variance
        }

        # --- 2. Quantity Mismatch Check ---
        bol_pkgs = self.normalized_record["normalized_aggregates"]["total_package_count"]
        # To compare apples to apples, we might check if PL ordered matches PL shipped
        pl_items = self.pl_data.get("items", [])
        qty_ordered = sum(item.get("qty_ordered", 0) for item in pl_items)
        qty_shipped = sum(item.get("qty_shipped", 0) for item in pl_items)
        
        flags["quantity_mismatch"] = {
            "is_flagged": qty_ordered != qty_shipped,
            "bol_package_count": bol_pkgs, # Kept for context
            "packing_list_ordered": qty_ordered,
            "packing_list_shipped": qty_shipped,
            "variance": abs(qty_ordered - qty_shipped),
            "discrepancy_source": "PL Ordered vs PL Shipped" if qty_ordered != qty_shipped else None
        }

        # --- 3. Address Mismatch Check ---
        bol_address = self.normalized_record["normalized_aggregates"]["ship_to_address_standardized"]
        
        pl_delivery = self.pl_data.get("delivery_to", {})
        pl_address = ", ".join(pl_delivery.get("address_lines", []))
        
        invoice_bill_to = self.invoice_data.get("bill_to_info", {})
        invoice_address = invoice_bill_to.get("address", "")

        # Compare BoL Delivery to Invoice Bill-To (Most common fraud vector)
        similarity = self._calculate_similarity(bol_address, invoice_address)
        
        flags["address_mismatch"] = {
            "is_flagged": similarity < 85.0, # Flag if less than 85% match
            "mismatched_party": "Consignee / Bill To",
            "bol_address": bol_address,
            "invoice_address": invoice_address,
            "packing_list_address": pl_address,
            "similarity_score": similarity
        }

        # --- 4. Missing Signatures (Mock implementation based on OCR output) ---
        # Assuming OCR adds a boolean "is_signed" to the base templates
        missing_from = []
        if not self.bol_data.get("is_signed", True): missing_from.append("bill_of_lading")
        if not self.invoice_data.get("is_signed", True): missing_from.append("invoice")
        if not self.pl_data.get("is_signed", True): missing_from.append("packing_list")
        
        flags["missing_signatures"] = {
            "is_flagged": len(missing_from) > 0,
            "bol_signed": "bill_of_lading" not in missing_from,
            "invoice_signed": "invoice" not in missing_from,
            "packing_list_signed": "packing_list" not in missing_from,
            "missing_from": missing_from
        }

        self.normalized_record["inconsistency_flags"] = flags

    def generate_normalized_record(self):
        # 1. Setup Base Record
        self.normalized_record = {
            "shipment_id": self.pl_data.get("shipping_refs", {}).get("order_reference", "UNKNOWN"),
            "source_documents": { ... },
            "normalized_aggregates": {},
            "inconsistency_flags": {},
            "category_metadata": {} # Initialize new section
        }

        self._calculate_aggregates()
        self._run_inconsistency_engine()
        
        # 2. Run the Category logic
        self._apply_category_metadata()

        return self.normalized_record

    def _determine_category(self, hs_code):
        """Mock router: Maps HS codes to your category templates."""
        if hs_code.startswith("08") or hs_code.startswith("07"):
            return "Perishables"
        elif hs_code.startswith("85") or hs_code.startswith("84"):
            return "Manufactured Goods"
        elif hs_code.startswith("28") or hs_code.startswith("29"):
            return "Raw Materials"
        return "Unknown"

    def _apply_category_metadata(self):
        """Extracts category-specific data based on the identified category."""
        
        # 1. Find the primary HS Code (usually from the first invoice line item)
        line_items = self.invoice_data.get("line_items", [])
        primary_hs_code = line_items[0].get("hs_code", "") if line_items else ""
        
        # 2. Route to the correct category
        category = self._determine_category(primary_hs_code)
        
        metadata_fields = {}

        # 3. Extract the specific fields based on the template
        if category == "Perishables":
            # If perishable, check BoL special instructions for temperature logic
            special_instructions = self.bol_data.get("special_instructions", "").lower()
            
            metadata_fields = {
                "temperature_control": {
                    "required": "keep frozen" in special_instructions or "reefer" in special_instructions,
                    # In a real system, you'd regex extract the exact temp numbers here
                },
                "is_frozen": "frozen" in special_instructions
            }

        elif category == "Manufactured Goods":
            # If manufactured, look for dimensions or fragility in the Packing List
            # (Assuming you updated PL items to have dimensions)
            metadata_fields = {
                "fragility_rating": "Handle with Care" in self.bol_data.get("special_instructions", "")
            }

        # 4. Save to the normalized record
        self.normalized_record["category_metadata"] = {
            "applied_category": category,
            "fields": metadata_fields
        }


# ==========================================
# Example Usage
# ==========================================
if __name__ == "__main__":
    # Mock data based on your schemas
    mock_bol = {
        "customer_order_info": [{"pkgs_count": 40}],
        "carrier_commodity_info": [{"weight": 15000}], # 15,000 kg
        "ship_to": {"address": "123 Main St", "city_state_zip": "London, UK"},
        "is_signed": True
    }
    
    mock_invoice = {
        "totals": {"grand_total": 45000.00},
        "bill_to_info": {"address": "456 Shell Corp Blvd, Cayman Islands"},
        "is_signed": True
    }
    
    mock_pl = {
        "shipping_refs": {"order_reference": "PO-998877"},
        "items": [
            {"weight_kg": 15000, "qty_ordered": 1000, "qty_shipped": 950} # Short shipment!
        ],
        "delivery_to": {"address_lines": ["123 Main St", "London, UK"]},
        "is_signed": False # Missing signature!
    }

    # Initialize and run
    pipeline = ShippingDocumentNormalizer(mock_bol, mock_invoice, mock_pl)
    result = pipeline.generate_normalized_record()

    # Output the result
    print(json.dumps(result["inconsistency_flags"], indent=2))