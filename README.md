# ClearPath: Shipment Verification Pipeline

## 1) How to Run the Full App

### Start Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

### Start Frontend
```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, upload the 3 PDFs:
- `bill_of_lading`
- `invoice`
- `packing_list`

After processing, you are taken to the dashboard where you can review flags and download the PDF report.

---

## 2) Extraction Layer (DocStruct Primary, Unstract Backup)

We support two extraction providers:
- **Primary:** locally hosted **DocStruct**
- **Fallback:** **Unstract LLMWhisperer**

The backend defaults to DocStruct-first and automatically falls back to Unstract if DocStruct fails or returns near-empty output.

### DocStruct 11-Stage Pipeline Modules
From `DocStruct/pipeline`:
1. `decomposition.py`
2. `layout.py`
3. `hybrid_proposals.py`
4. `proposal_fusion.py`
5. `classification.py`
6. `table_candidates.py`
7. `tables_figures.py`
8. `reading_order.py`
9. `confidence.py`
10. `markdown_serializer.py`
11. `validator.py`

### 3-Level Schema Validation in DocStruct
From `DocStruct/schemas`:
- `document.py` (document-level contract)
- `page.py` (page-level contract)
- `block.py` (block-level contract)

### Model Support in DocStruct
From `DocStruct/hf_models`:
- `deformable-detr-doclaynet`
- `table-transformer`

### Modes You Can Use
DocStruct runtime modes in backend config:
- **standard**: geometry/visual heuristics driven extraction
- **model-only** (implemented as model-driven `model-first` path): extraction driven by model detections
- **hybrid** (true-hybrid): combines geometry + model outputs and reconciles using confidence/fusion logic

### Backend Env Controls for Extraction
Set these in `backend/.env`:
```env
PDF_EXTRACTOR_PROVIDER=docstruct   # docstruct | unstract | auto
DOCSTRUCT_ROOT=..\DocStruct
DOCSTRUCT_PYTHON=
DOCSTRUCT_MODE=standard
DOCSTRUCT_DETECTOR=stub
DOCSTRUCT_TIMEOUT_SEC=120
DOCSTRUCT_MIN_CHARS=80
```

---

## 3) Document Intelligence + Consistency Checks

We process 3 logistics documents:
- Bill of Lading
- Invoice
- Packing List

### Multi-Language Support
The pipeline supports shipment documents written in:
- English
- Spanish
- Italian
- German
- French
- Portuguese

Pipeline behavior:
1. Extract text/layout from PDFs (DocStruct primary).
2. Convert extracted content into structured JSON.
3. Run cross-document consistency checks and category-aware validation.
4. Return normalized results, explainability evidence, and KPIs to the dashboard.

### Supported Shipment Categories
- Manufactured Goods
- Perishables
- Raw Materials

### Examples of Inconsistency Checks
- Destination address mismatch
- Weight mismatch (for example, per-box weight x quantity vs declared total)
- Tax calculation mismatch
- Hazardous material consistency checks
- Missing carrier identifiers (for example SCAC/pro details)

All detected issues are surfaced in the dashboard as explainable flags with evidence, and the user can generate/download a final PDF verification report.

---

## Notes
- If DocStruct cannot run (missing venv/model/runtime issue), the backend falls back to Unstract automatically.
