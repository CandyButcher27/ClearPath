import json
import os
from fpdf import FPDF

OUTPUT_DIR = "pdfs_formatados_pt"
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

def generate_bol(data, product_id):
    pdf = FormattedPDF()
    pdf.add_page()

    pdf.set_font("Arial","B",18)
    pdf.cell(0,10,"CONHECIMENTO DE TRANSPORTE",ln=True,align="C")
    pdf.set_font("Arial","B",10)
    pdf.cell(0,6,f"Número BOL: {data.get('bill_of_lading_number','')}",ln=True,align="C")

    pdf.output(os.path.join(OUTPUT_DIR,f"{product_id}_BOL_pt.pdf"))

def main():
    with open("samples.json") as f:
        rec=json.load(f)
    for r in rec:
        pid=r.get("product_id","UNK")
        if "bill_of_lading" in r:
            generate_bol(r["bill_of_lading"],pid)

if __name__=="__main__":
    main()