import json
import os
from fpdf import FPDF

OUTPUT_DIR = "pdfs_formateados_es"
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
    pdf.cell(0, 10, "CONOCIMIENTO DE EMBARQUE", ln=True, align="C")
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, f"Número de BOL: {data.get('bill_of_lading_number', '')}", ln=True, align="C")
    pdf.ln(5)

    y_start = pdf.get_y()
    ship_from = data.get("ship_from", {})
    ship_to = data.get("ship_to", {})
    third_party = data.get("third_party_bill_to", {})
    
    # Construct detailed text blocks
    from_txt = f"{ship_from.get('address', '')}\n{ship_from.get('city_state_zip', '')}\nSID#: {ship_from.get('sid_number', 'N/A')}\nFOB: {'Sí' if ship_from.get('fob_point') else 'No'}"
    to_txt = f"Loc#: {ship_to.get('location_number', 'N/A')}\n{ship_to.get('address', '')}\n{ship_to.get('city_state_zip', '')}\nCID#: {ship_to.get('cid_number', 'N/A')}\nFOB: {'Sí' if ship_to.get('fob_point') else 'No'}"
    third_txt = f"{third_party.get('address', '')}\n{third_party.get('city_state_zip', '')}"
    
    pdf.add_address_box("Enviar desde", ship_from.get("name", ""), from_txt, 10, y_start, 60, 35)
    pdf.add_address_box("Enviar a", ship_to.get("name", ""), to_txt, 75, y_start, 60, 35)
    pdf.add_address_box("Facturar a Tercero", third_party.get("name", ""), third_txt, 140, y_start, 60, 35)
    
    pdf.set_y(y_start + 35)

    # Carrier Info Box (Detailed)
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 6, "Detalles del Transportista y Envío", border=1, fill=True, ln=True)
    pdf.set_font("Arial", "", 9)
    carrier = data.get("carrier_details", {})
    cod = data.get("cod_details", {})
    
    carrier_txt = (
        f"Transportista: {carrier.get('carrier_name','')} | No. Remolque: {carrier.get('trailer_number','')} | Sellos: {carrier.get('seal_numbers','')}\n"
        f"SCAC: {carrier.get('scac','')} | No. Pro: {carrier.get('pro_number','')} | Términos de Flete: {carrier.get('freight_charge_terms','')}\n"
        f"Monto COD: ${cod.get('amount', 0)} | Términos de Tarifa: {cod.get('fee_terms', 'Ninguno')}"
    )
    pdf.multi_cell(0, 5, carrier_txt, border=1)
    
    if "special_instructions" in data:
        pdf.set_font("Arial", "BI", 9)
        pdf.multi_cell(0, 6, f"Instrucciones Especiales: {data['special_instructions']}", border=1)
    
    pdf.ln(5)

    # Customer Order Info Table
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Información del Pedido del Cliente", ln=True)
    order_cols = ["No. Pedido", "Paquetes", "Peso", "Pallet/Hoja", "Info Adicional"]
    order_widths = [35, 20, 25, 25, 85]
    draw_table_header(pdf, order_cols, order_widths)
    
    for order in data.get("customer_order_info", []):
        row = [
            order.get("order_number", ""),
            order.get("pkgs_count", ""),
            order.get("weight", ""),
            "Sí" if order.get("pallet_slip") else "No",
            order.get("additional_info", "")
        ]
        draw_table_row(pdf, row, order_widths) # <-- FIXED LINE
    pdf.ln(5)

    # Commodity Table
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Información de Mercancía del Transportista", ln=True)
    cols = ["Cant/Tipo UM", "Cant/Tipo Paq", "Peso", "Descripción", "NMFC", "Clase", "Peligroso"]
    widths = [25, 25, 15, 60, 25, 20, 20]
    draw_table_header(pdf, cols, widths)
    
    for item in data.get("carrier_commodity_info", []):
        row = [
            f"{item.get('handling_unit_qty', '')} {item.get('handling_unit_type', '')}",
            f"{item.get('package_qty', '')} {item.get('package_type', '')}",
            item.get("weight", ""),
            item.get("commodity_description", "")[:35],
            item.get("nmfc_number", ""),
            item.get("class", ""),
            "SÍ" if item.get("is_hazardous") else "NO"
        ]
        draw_table_row(pdf, row, widths)
        
    # Signature box
    pdf.ln(15)
    pdf.set_font("Arial", "", 10)
    pdf.cell(80, 10, "Firma del Remitente: _______________________", ln=0)
    pdf.cell(80, 10, "Firma del Transportista: _______________________", ln=True)

    pdf.output(os.path.join(OUTPUT_DIR, f"{product_id}_BOL_es.pdf"))

def generate_invoice(data, product_id):
    pdf = FormattedPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "FACTURA COMERCIAL", ln=True, align="C")
    pdf.ln(5)

    payment = data.get("payment_details", {})
    pdf.set_font("Arial", "B", 10)
    pdf.cell(50, 6, f"Factura No: {data.get('invoice_number', '')}")
    pdf.cell(50, 6, f"Fecha: {payment.get('invoice_date', '')}")
    pdf.cell(60, 6, f"Fecha Vencimiento: {payment.get('due_date', '')}")
    pdf.ln(10)

    y_start = pdf.get_y()
    seller = data.get("seller_info", {})
    buyer = data.get("bill_to_info", {})
    
    seller_txt = f"{seller.get('address', '')}\nNo. Reg: {seller.get('reg_number', '')}\nRFC/NIF: {seller.get('tax_number', '')}"
    buyer_txt = f"{buyer.get('address', '')}\n{buyer.get('city_state_zip', '')}\nNo. Reg: {buyer.get('reg_number', '')}\nRFC/NIF: {buyer.get('tax_number', '')}"
    
    pdf.add_address_box("De / Vendedor", seller.get("company_name", ""), seller_txt, 10, y_start, 90, 25)
    pdf.add_address_box("Facturar a / Consignatario", buyer.get("client_name", ""), buyer_txt, 110, y_start, 90, 25)
    
    pdf.set_y(y_start + 30)

    # Bank Details
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    bank_txt = f"Banco: {payment.get('bank_name', '')} | BIC: {payment.get('bic', '')} | Cuenta: {payment.get('account_number', '')}"
    pdf.cell(0, 6, bank_txt, border=1, fill=True, ln=True)
    pdf.ln(5)

    # Line Items Table
    cols = ["Contenedor", "Código HS", "Descripción", "Cant", "U/M", "Precio Unit", "Imp %", "Subtotal"]
    widths = [22, 20, 55, 12, 12, 24, 15, 30]
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
    pdf.set_x(120)
    totals = data.get("totals", {})
    pdf.set_font("Arial", "B", 10)
    pdf.cell(35, 6, "Subtotal:", border=1)
    pdf.cell(45, 6, f"${totals.get('subtotal', 0):.2f}", border=1, align="R", ln=True)
    pdf.set_x(120)
    pdf.cell(35, 6, "Impuesto:", border=1)
    pdf.cell(45, 6, f"${totals.get('tax_total', 0):.2f}", border=1, align="R", ln=True)
    pdf.set_x(120)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(35, 8, "Total General:", border=1, fill=True)
    pdf.cell(45, 8, f"${totals.get('grand_total', 0):.2f} {totals.get('currency', '')}", border=1, fill=True, align="R", ln=True)

    pdf.output(os.path.join(OUTPUT_DIR, f"{product_id}_Factura_es.pdf"))

def generate_packing_list(data, product_id):
    pdf = FormattedPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "LISTA DE EMPAQUE", ln=True, align="C")
    pdf.ln(5)

    refs = data.get("shipping_refs", {})
    pdf.set_font("Arial", "B", 9)
    pdf.cell(45, 6, f"Ref. Pedido: {refs.get('order_reference', '')}")
    pdf.cell(45, 6, f"Fecha Pedido: {refs.get('order_date', '')}")
    pdf.cell(50, 6, f"No. Entrega: {refs.get('delivery_number', '')}")
    pdf.cell(50, 6, f"Método: {refs.get('delivery_method', '')}")
    pdf.ln(10)

    y_start = pdf.get_y()
    from_biz = data.get("from_business", {})
    to_biz = data.get("delivery_to", {})
    
    from_txt = "\n".join(from_biz.get("address_lines", []))
    to_txt = f"{chr(10).join(to_biz.get('address_lines', []))}\nTel: {to_biz.get('telephone', '')}\nEmail: {to_biz.get('email', '')}"
    
    pdf.add_address_box("Remitente", from_biz.get("business_name", ""), from_txt, 10, y_start, 90, 25)
    pdf.add_address_box("Entregar a", to_biz.get("customer_name", ""), to_txt, 110, y_start, 90, 25)
    
    pdf.set_y(y_start + 30)

    cols = ["Contenedor", "No. Artículo", "Descripción", "Pedido", "Enviado", "Peso(kg)", "Vol(m3)"]
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
        pdf.cell(0, 6, "Notas Especiales:", ln=True)
        pdf.set_font("Arial", "I", 9)
        pdf.multi_cell(0, 6, data["notes"], border=1)

    pdf.output(os.path.join(OUTPUT_DIR, f"{product_id}_ListaEmpaque_es.pdf"))

def main():
    try:
        with open("samples.json", "r") as file:
            records = json.load(file)
            
        print(f"Found {len(records)} records. Generating professional Spanish PDFs...")
        
        for record in records:
            product_id = record.get("product_id", "UNKNOWN")
            if "bill_of_lading" in record: generate_bol(record["bill_of_lading"], product_id)
            if "invoice" in record: generate_invoice(record["invoice"], product_id)
            if "packing_list" in record: generate_packing_list(record["packing_list"], product_id)
                
        print(f"\n¡Éxito! Highly formatted Spanish PDFs saved in the '{OUTPUT_DIR}' directory.")
        
    except FileNotFoundError:
        print("Error: 'samples.json' not found.")
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    main()