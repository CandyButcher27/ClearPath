"""Visualize DocStruct JSON output overlaid on the source PDF.

Renders one overlay image per page and saves them to overlay_output/<doc_id>/.

Usage:
    python scripts/visualize_doc.py doc1
    python scripts/visualize_doc.py doc1 --mode hybrid
    python scripts/visualize_doc.py doc1 --mode both   # side-by-side model vs hybrid
    python scripts/visualize_doc.py doc1 --dpi 200
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from visualize_overlay import create_overlays, create_comparison_overlays


PDF_DIR        = PROJECT_ROOT / "data" / "raw-pdfs"
MODEL_OUT_DIR  = PROJECT_ROOT / "data" / "model-outputs"
HYBRID_OUT_DIR = PROJECT_ROOT / "data" / "hybrid-outputs"
OVERLAY_DIR    = PROJECT_ROOT / "overlay_output"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Overlay DocStruct JSON blocks on source PDF pages"
    )
    parser.add_argument("doc_id", help="Document ID, e.g. doc1")
    parser.add_argument(
        "--mode",
        choices=["model", "hybrid", "both"],
        default="model",
        help="Which output to visualize (default: model)",
    )
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()

    doc_id  = args.doc_id
    pdf     = PDF_DIR / f"{doc_id}.pdf"
    model_json  = MODEL_OUT_DIR  / f"{doc_id}_model.json"
    hybrid_json = HYBRID_OUT_DIR / f"{doc_id}_hybrid.json"

    if not pdf.exists():
        print(f"ERROR: PDF not found: {pdf}")
        sys.exit(1)

    out_dir = OVERLAY_DIR / doc_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "both":
        if not model_json.exists():
            print(f"ERROR: Model JSON not found: {model_json}")
            sys.exit(1)
        if not hybrid_json.exists():
            print(f"ERROR: Hybrid JSON not found: {hybrid_json}")
            sys.exit(1)
        print(f"Generating side-by-side comparison → {out_dir}")
        create_comparison_overlays(pdf, model_json, hybrid_json, out_dir, dpi=args.dpi)

    else:
        if args.mode == "model":
            json_path = model_json
        else:
            json_path = hybrid_json

        if not json_path.exists():
            print(f"ERROR: JSON not found: {json_path}")
            sys.exit(1)

        print(f"Generating {args.mode} overlays → {out_dir}")
        create_overlays(pdf, json_path, out_dir, dpi=args.dpi)

    images = sorted(out_dir.glob("*.png"))
    print(f"Done. {len(images)} page image(s) written to {out_dir}")


if __name__ == "__main__":
    main()
