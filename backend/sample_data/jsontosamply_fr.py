import json
import os
from fpdf import FPDF

OUTPUT_DIR = "pdfs_formates_fr"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEXT = {
    "YES": "Oui",
    "NO": "Non"
}

class FormattedPDF(FPDF):
    def add_address_box(self, title, name, details_text, x, y, w, h):
        self.set_xy(x, y)
        self.set_font("Arial", "B", 10)
        self.set_fill_color(230, 230, 230)
        self.cell(w, 6, title, border=1, fill=True, ln=2)

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
    for data, w in zip(data_list, widths):
        pdf.cell(w, 6, str(data), border=1, align="C")
    pdf.ln()

def generate_bol(data, product_id):
    pdf = FormattedPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "CONNAISSEMENT DE TRANSPORT", ln=True, align="C")
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, f"Numéro BOL: {data.get('bill_of_lading_number','')}", ln=True, align="C")
    pdf.ln(5)

    ship_from = data.get("ship_from", {})
    ship_to = data.get("ship_to", {})
    third = data.get("third_party_bill_to", {})

    y = pdf.get_y()

    pdf.add_address_box("Expéditeur", ship_from.get("name",""),
        f"{ship_from.get('address','')}\n{ship_from.get('city_state_zip','')}",
        10, y, 60, 35)

    pdf.add_address_box("Destinataire", ship_to.get("name",""),
        f"{ship_to.get('address','')}\n{ship_to.get('city_state_zip','')}",
        75, y, 60, 35)

    pdf.add_address_box("Facturation Tiers", third.get("name",""),
        f"{third.get('address','')}\n{third.get('city_state_zip','')}",
        140, y, 60, 35)

    pdf.output(os.path.join(OUTPUT_DIR, f"{product_id}_BOL_fr.pdf"))

def generate_invoice(data, product_id):
    pdf = FormattedPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "FACTURE COMMERCIALE", ln=True, align="C")

    pdf.output(os.path.join(OUTPUT_DIR, f"{product_id}_Invoice_fr.pdf"))

def generate_packing_list(data, product_id):
    pdf = FormattedPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "LISTE DE COLISAGE", ln=True, align="C")

    pdf.output(os.path.join(OUTPUT_DIR, f"{product_id}_Packing_fr.pdf"))

def main():
    with open("samples.json") as f:
        records = json.load(f)

    for r in records:
        pid = r.get("product_id","UNK")
        if "bill_of_lading" in r:
            generate_bol(r["bill_of_lading"], pid)
        if "invoice" in r:
            generate_invoice(r["invoice"], pid)
        if "packing_list" in r:
            generate_packing_list(r["packing_list"], pid)

if __name__ == "__main__":
    main()