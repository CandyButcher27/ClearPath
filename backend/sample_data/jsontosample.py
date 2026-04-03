import json
import os
from fpdf import FPDF

OUTPUT_DIR = "formatted_pdfs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class FormattedPDF(FPDF):
    def add_address_box(self, title, name, details_text, x, y, w, h):
        self.set_xy(x, y)
        self.set_font("Arial", "B", 10)
        self.set_fill_color(230, 230, 230)
        self.cell(w, 6, title, border=1, fill=True, ln=2)
        
        # Build the interior text
        self.set_font("Arial", "B", 9)
        self.cell(w, 5, name, border="LR", ln=2)
        
        self.set_font("Arial", "", 8)
        self.multi_cell(w, 4, details_text, border="LRB")

def draw_table_header(pdf, cols, widths):
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(200, 220, 255)
    for col, w in zip(cols, widths):
        pdf.cell(w, 8, col, border=1, fill=True, align="C")
    pdf.ln()

def draw_table_row(pdf, data_list, widths):
    pdf.set_font("Arial", "", 8)
    max_h = 6
    for data, w in zip(data_list, widths):
        pdf.cell(w, max_h, str(data), border=1, align="C")
    pdf.ln()

def generate_bol(data, product_id):
    pdf = FormattedPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "BILL OF LADING", ln=True, align="C")
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, f"BOL Number: {data.get('bill_of_lading_number', '')}", ln=True, align="C")
    pdf.ln(5)

    y_start = pdf.get_y()
    ship_from = data.get("ship_from", {})
    ship_to = data.get("ship_to", {})
    third_party = data.get("third_party_bill_to", {})
    
    # Construct detailed text blocks
    from_txt = f"{ship_from.get('address', '')}\n{ship_from.get('city_state_zip', '')}\nSID#: {ship_from.get('sid_number', 'N/A')}\nFOB: {'Yes' if ship_from.get('fob_point') else 'No'}"
    to_txt = f"Loc#: {ship_to.get('location_number', 'N/A')}\n{ship_to.get('address', '')}\n{ship_to.get('city_state_zip', '')}\nCID#: {ship_to.get('cid_number', 'N/A')}\nFOB: {'Yes' if ship_to.get('fob_point') else 'No'}"
    third_txt = f"{third_party.get('address', '')}\n{third_party.get('city_state_zip', '')}"
    
    pdf.add_address_box("Ship From", ship_from.get("name", ""), from_txt, 10, y_start, 60, 35)
    pdf.add_address_box("Ship To", ship_to.get("name", ""), to_txt, 75, y_start, 60, 35)
    pdf.add_address_box("3rd Party Bill To", third_party.get("name", ""), third_txt, 140, y_start, 60, 35)
    
    pdf.set_y(y_start + 35)

    # Carrier Info Box (Detailed)
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 6, "Carrier & Shipment Details", border=1, fill=True, ln=True)
    pdf.set_font("Arial", "", 9)
    carrier = data.get("carrier_details", {})
    cod = data.get("cod_details", {})
    
    carrier_txt = (
        f"Carrier: {carrier.get('carrier_name','')} | Trailer No: {carrier.get('trailer_number','')} | Seals: {carrier.get('seal_numbers','')}\n"
        f"SCAC: {carrier.get('scac','')} | Pro No: {carrier.get('pro_number','')} | Freight Terms: {carrier.get('freight_charge_terms','')}\n"
        f"COD Amount: ${cod.get('amount', 0)} | Fee Terms: {cod.get('fee_terms', 'None')}"
    )
    pdf.multi_cell(0, 5, carrier_txt, border=1)
    
    if "special_instructions" in data:
        pdf.set_font("Arial", "BI", 9)
        pdf.multi_cell(0, 6, f"Special Instructions: {data['special_instructions']}", border=1)
    
    pdf.ln(5)

    # Customer Order Info Table
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Customer Order Information", ln=True)
    order_cols = ["Order Number", "Pkgs", "Weight", "Pallet/Slip", "Additional Info"]
    order_widths = [40, 20, 25, 25, 80]
    draw_table_header(pdf, order_cols, order_widths)
    
    for order in data.get("customer_order_info", []):
        row = [
            order.get("order_number", ""),
            order.get("pkgs_count", ""),
            order.get("weight", ""),
            "Yes" if order.get("pallet_slip") else "No",
            order.get("additional_info", "")
        ]
        draw_table_row(pdf, row, order_widths)
    pdf.ln(5)

    # Commodity Table
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Carrier Commodity Information", ln=True)
    cols = ["HU Qty/Type", "Pkg Qty/Type", "Weight", "Description", "NMFC", "Class", "Hazmat"]
    widths = [30, 30, 20, 55, 25, 15, 15]
    draw_table_header(pdf, cols, widths)
    
    for item in data.get("carrier_commodity_info", []):
        row = [
            f"{item.get('handling_unit_qty', '')} {item.get('handling_unit_type', '')}",
            f"{item.get('package_qty', '')} {item.get('package_type', '')}",
            item.get("weight", ""),
            item.get("commodity_description", "")[:35],
            item.get("nmfc_number", ""),
            item.get("class", ""),
            "Y" if item.get("is_hazardous") else "N"
        ]
        draw_table_row(pdf, row, widths)
        
    pdf.output(os.path.join(OUTPUT_DIR, f"{product_id}_BOL.pdf"))

def generate_invoice(data, product_id):
    pdf = FormattedPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "COMMERCIAL INVOICE", ln=True, align="C")
    pdf.ln(5)

    payment = data.get("payment_details", {})
    pdf.set_font("Arial", "B", 10)
    pdf.cell(50, 6, f"Invoice No: {data.get('invoice_number', '')}")
    pdf.cell(50, 6, f"Date: {payment.get('invoice_date', '')}")
    pdf.cell(50, 6, f"Due Date: {payment.get('due_date', '')}")
    pdf.ln(10)

    y_start = pdf.get_y()
    seller = data.get("seller_info", {})
    buyer = data.get("bill_to_info", {})
    
    seller_txt = f"{seller.get('address', '')}\nReg No: {seller.get('reg_number', '')}\nTax ID: {seller.get('tax_number', '')}"
    buyer_txt = f"{buyer.get('address', '')}\n{buyer.get('city_state_zip', '')}\nReg No: {buyer.get('reg_number', '')}\nTax ID: {buyer.get('tax_number', '')}"
    
    pdf.add_address_box("From / Seller", seller.get("company_name", ""), seller_txt, 10, y_start, 90, 25)
    pdf.add_address_box("Bill To / Consignee", buyer.get("client_name", ""), buyer_txt, 110, y_start, 90, 25)
    
    pdf.set_y(y_start + 30)

    # Bank Details
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    bank_txt = f"Bank: {payment.get('bank_name', '')} | BIC: {payment.get('bic', '')} | Account: {payment.get('account_number', '')}"
    pdf.cell(0, 6, bank_txt, border=1, fill=True, ln=True)
    pdf.ln(5)

    # Line Items Table
    cols = ["Container", "HS Code", "Description", "Qty", "U/M", "Unit Price", "Tax %", "Subtotal"]
    widths = [25, 20, 55, 15, 15, 20, 15, 25]
    draw_table_header(pdf, cols, widths)
    
    for item in data.get("line_items", []):
        row = [
            item.get("container_number", ""),
            item.get("hs_code", ""),
            item.get("description", "")[:35],
            item.get("quantity", ""),
            item.get("unit_of_measure", ""),
            f"${item.get('unit_price', 0):.2f}",
            f"{item.get('tax_percentage', 0)}%",
            f"${item.get('subtotal', 0):.2f}"
        ]
        draw_table_row(pdf, row, widths)

    # Totals
    pdf.ln(5)
    pdf.set_x(130)
    totals = data.get("totals", {})
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 6, "Subtotal:", border=1)
    pdf.cell(40, 6, f"${totals.get('subtotal', 0):.2f}", border=1, align="R", ln=True)
    pdf.set_x(130)
    pdf.cell(30, 6, "Tax:", border=1)
    pdf.cell(40, 6, f"${totals.get('tax_total', 0):.2f}", border=1, align="R", ln=True)
    pdf.set_x(130)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(30, 8, "Grand Total:", border=1, fill=True)
    pdf.cell(40, 8, f"${totals.get('grand_total', 0):.2f} {totals.get('currency', '')}", border=1, fill=True, align="R", ln=True)

    pdf.output(os.path.join(OUTPUT_DIR, f"{product_id}_Invoice.pdf"))

def generate_packing_list(data, product_id):
    pdf = FormattedPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "PACKING LIST", ln=True, align="C")
    pdf.ln(5)

    refs = data.get("shipping_refs", {})
    pdf.set_font("Arial", "B", 9)
    pdf.cell(45, 6, f"Order Ref: {refs.get('order_reference', '')}")
    pdf.cell(45, 6, f"Order Date: {refs.get('order_date', '')}")
    pdf.cell(55, 6, f"Delivery No: {refs.get('delivery_number', '')}")
    pdf.cell(45, 6, f"Method: {refs.get('delivery_method', '')}")
    pdf.ln(10)

    y_start = pdf.get_y()
    from_biz = data.get("from_business", {})
    to_biz = data.get("delivery_to", {})
    
    from_txt = "\n".join(from_biz.get("address_lines", []))
    to_txt = f"{chr(10).join(to_biz.get('address_lines', []))}\nTel: {to_biz.get('telephone', '')}\nEmail: {to_biz.get('email', '')}"
    
    pdf.add_address_box("Shipper", from_biz.get("business_name", ""), from_txt, 10, y_start, 90, 25)
    pdf.add_address_box("Delivery To", to_biz.get("customer_name", ""), to_txt, 110, y_start, 90, 25)
    
    pdf.set_y(y_start + 30)

    cols = ["Container", "Item Number", "Description", "Ordered", "Shipped", "Weight(kg)", "Vol(cbm)"]
    widths = [25, 25, 55, 20, 20, 22, 23]
    draw_table_header(pdf, cols, widths)
    
    for item in data.get("items", []):
        row = [
            item.get("container_number", ""),
            item.get("item_number", ""),
            item.get("description", "")[:30],
            item.get("qty_ordered", ""),
            item.get("qty_shipped", ""),
            item.get("weight_kg", ""),
            item.get("volume_cbm", "")
        ]
        draw_table_row(pdf, row, widths)
        
    if "notes" in data:
        pdf.ln(10)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, "Special Notes:", ln=True)
        pdf.set_font("Arial", "I", 9)
        pdf.multi_cell(0, 6, data["notes"], border=1)

    pdf.output(os.path.join(OUTPUT_DIR, f"{product_id}_PackingList.pdf"))

def main():
    try:
        with open("samples.json", "r") as file:
            records = json.load(file)
            
        print(f"Found {len(records)} records. Generating professional PDFs...")
        
        for record in records:
            product_id = record.get("product_id", "UNKNOWN")
            if "bill_of_lading" in record: generate_bol(record["bill_of_lading"], product_id)
            if "invoice" in record: generate_invoice(record["invoice"], product_id)
            if "packing_list" in record: generate_packing_list(record["packing_list"], product_id)
                
        print(f"\nSuccess! Highly formatted PDFs saved in the '{OUTPUT_DIR}' directory.")
        
    except FileNotFoundError:
        print("Error: 'samples.json' not found.")
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    main()
