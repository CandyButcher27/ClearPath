# ClearPath: Intelligent Shipment Verification

ClearPath is a full-stack document intelligence workflow for logistics verification.  
Upload a Bill of Lading, Invoice, and Packing List; the system extracts structure, runs consistency/compliance checks, streams live processing logs, and generates a final PDF certificate.

## Why This Matters

Manual shipment verification is slow, error-prone, and expensive in high-volume operations.  
ClearPath provides:

- Automated cross-document checks
- Explainable flagged issues with evidence
- Business-facing KPI framing (risk, checks passed, time saved, completeness)
- One-click final certificate generation

## Demo Flow (60–90s Pitch)

1. Upload 3 documents (`bill_of_lading`, `invoice`, `packing_list`).
2. Show the live processing terminal with backend-driven session logs.
3. Open the trust dashboard:
   - KPI strip (risk score, checks passed, time saved, completeness)
   - Operations brief and decision trace
   - Explainability evidence panels for flagged checks
4. Download the generated PDF certificate.

## Architecture

Frontend (`React + Vite + Tailwind`)
- Upload flow and processing console
- SSE log stream + fallback simulation
- Explainability dashboard and report actions

Backend (`Flask`)
- `/api/process-shipment`: ingest, extraction, structuring, normalization
- `/api/process-shipment/logs/<session_id>`: real-time SSE event stream
- `/api/process-shipment/logs/<session_id>/snapshot`: polling fallback
- `/api/generate-report`: PDF certificate generation

ML/Rule Pipeline
- PDF extraction (`pdf_parser.py`)
- Structured parsing (`structurer.py`)
- Rule-based normalization and inconsistency detection (`normalizer.py`)
- Report rendering (`generate_report_card.py`)

## Project Structure

```text
backend/
  app.py
  pdf_parser.py
  structurer.py
  normalizer.py
  generate_report_card.py
  prompts/
frontend/
  src/
    components/
      ClearPathScreen.tsx
      ProcessingScreen.tsx
      VerificationResultsScreen.tsx
```

## Setup

### 1) Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`  
Backend: `http://localhost:5000`

## Environment Variables (`backend/.env`)

Required:

- `LLMWHISPERER_API_KEY`
- `GROQ_API_KEY`

Optional:

- `USE_MOCK_DATA=true|false`
- `STRUCTURER_MODEL`
- `STRUCTURER_MAX_DOC_CHARS`
- `STRUCTURER_BUNDLE_MAX_TOTAL_CHARS`
- `STRUCTURER_USE_BUNDLE_FIRST`

## API Contracts

### `POST /api/process-shipment`

Form-data inputs:
- `bill_of_lading` (pdf)
- `invoice` (pdf)
- `packing_list` (pdf)
- `session_id` (optional string for live log streaming)

Response includes:
- `normalized`
- `raw_shipment`
- `telemetry` (timing/extraction/kpi)
- `explainability` (items + summary)

### `GET /api/process-shipment/logs/<session_id>`

Server-sent events stream:
- lifecycle steps
- extraction/structuring/normalization progress
- completion/error status event

### `POST /api/generate-report`

Input:
- `{ "normalized": { ... } }`

Output:
- PDF download stream

## Known Limitations

- In-memory session logs are process-local (not distributed).
- KPI values are heuristic for demo framing.
- Extraction quality depends on source PDF quality and parser model behavior.

## Roadmap

- Persist session logs and audit traces in Redis/Postgres
- Multi-provider parser A/B with quality scoring
- Human-in-the-loop correction UI with instant re-evaluation
- Multi-shipment batch processing and queueing
- Judge-ready architecture diagram image (`docs/architecture.png`)
