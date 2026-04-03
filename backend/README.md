# ClearPath Backend

## Installation

```bash
pip install reportlab
```

## Usage

Generate normalized data:
```bash
python normalizer.py
```

Generate PDF report card for a product:
```bash
python generate_report_card.py <product_id> <output_pdf_path>
```

Examples:
```bash
python generate_report_card.py PRD-001 report_PRD001.pdf
python generate_report_card.py PRD-003 complex_issues_report.pdf
python generate_report_card.py PRD-005 hazmat_report.pdf
python generate_report_card.py PRD-010 clean_report.pdf
```
