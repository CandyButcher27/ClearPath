# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ClearPath** is a DP World hackathon submission — a logistics document verification platform. It validates cross-document consistency across Bill of Lading, Invoice, and Packing List documents and flags anomalies.

Three independent components, each with its own dependencies and runtime:

| Component | Location | Purpose |
|-----------|----------|---------|
| `backend/` | Python stdlib only | Normalizer: validates and flags inconsistencies across shipment documents |
| `frontend/` | Node/React | UI: document upload and verification results display (mock data only, no API) |
| `DocStruct/` | Python + PyTorch | PDF layout analysis pipeline: extracts structured content from PDFs |

## Commands

### Backend (Normalizer)
```bash
cd backend
python normalizer.py          # Run the normalizer (no CLI args; modify directly or import as module)
```
No dependencies beyond Python stdlib. No test framework configured.

### Frontend
```bash
cd frontend
npm install
npm run dev       # Dev server at http://localhost:5173
npm run build     # TypeScript check + Vite production build
npm run lint      # ESLint
npm run preview   # Serve production build locally
```

### DocStruct
```bash
cd DocStruct
pip install -r requirements.txt
python main.py input.pdf output.json --mode true-hybrid --detector doclaynet
python -m pytest tests/ -v
python -m pytest tests/test_pipeline.py -v    # Single test file
```
Requires Tesseract OCR binaries and a `HUGGINGFACE_TOKEN` in `DocStruct/.env`.

## Backend Architecture

`backend/normalizer.py` is a single-file module (~800 lines) centered on `ShipmentProcessor`.

**Processing flow:**
1. Parse raw shipment JSON into three document types (BOL, Invoice, Packing List)
2. Categorize shipment by HS code → `Perishables`, `ManufacturedGoods`, or `RawMaterials`
3. Run cross-document validation checks
4. Return normalized output with an `inconsistency_flags` object

**Key validation checks:**
- `check_weight()` — BOL vs. Packing List weight comparison
- `check_density()` — HS-code-specific bulk density validation (e.g. salt: 1000–3500 kg/m³)
- `check_uom()` — Unit-of-measure compatibility (weight vs. count)
- `check_temp()` — Cold-chain requirements for perishables
- `check_expiry()` — Date logic and shelf-life validation (harvest → shipping → expiry)
- `check_overcharge()` — Financial calculation audits (tax, totals)

**Schema files:**
- `base_templates/` — Structure definitions for BOL, Invoice, Packing List, and normalized output
- `category_templates/` — Category-specific fields and rules (perishables, manufactured goods, raw materials)
- `sample_data/samples.json` — Test data with deliberate inconsistencies

## Component Relationship

The intended data flow is:
```
PDF documents → DocStruct → structured JSON → backend normalizer → flagged output → frontend display
```
This integration is **not yet wired up** — the frontend uses static mock data from `src/data/mockData.ts` and the backend has no HTTP server. Each component currently runs independently.

## Sub-component CLAUDE.md files

- `frontend/CLAUDE.md` — Screen routing, styling, animation details
- `DocStruct/CLAUDE.md` — Pipeline architecture, schemas, detector interface, configuration
