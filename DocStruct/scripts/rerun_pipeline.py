"""Re-run the DocStruct pipeline for all docs that have existing outputs.

Reads the doc IDs from data/model-outputs/ (or data/hybrid-outputs/) and
re-runs both pipeline modes for each document found.

Usage:
    python scripts/rerun_pipeline.py
    python scripts/rerun_pipeline.py --no-skip          # overwrite existing outputs
    python scripts/rerun_pipeline.py --mode model       # model-only outputs
    python scripts/rerun_pipeline.py --mode hybrid      # hybrid-only outputs
    python scripts/rerun_pipeline.py --dpi 150          # (no effect here, passed to main)
    python scripts/rerun_pipeline.py --doc doc1 doc3    # run specific docs only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PDF_DIR        = PROJECT_ROOT / "data" / "raw-pdfs"
MODEL_OUT_DIR  = PROJECT_ROOT / "data" / "model-outputs"
HYBRID_OUT_DIR = PROJECT_ROOT / "data" / "hybrid-outputs"


def discover_doc_ids(source_dir: Path) -> list[str]:
    """Return sorted list of doc IDs from existing output filenames."""
    ids: list[str] = []
    for f in sorted(source_dir.glob("*.json")):
        # filenames like doc1_model.json or doc1_hybrid.json
        stem = f.stem  # e.g. "doc1_model"
        doc_id = stem.rsplit("_", 1)[0]  # e.g. "doc1"
        if doc_id not in ids:
            ids.append(doc_id)
    return ids


def run_one(
    doc_id: str,
    mode: str,
    output_path: Path,
    skip_existing: bool,
    verbose: bool,
) -> bool:
    """Run main.py for a single doc+mode. Returns True on success."""
    pdf_path = PDF_DIR / f"{doc_id}.pdf"

    if not pdf_path.exists():
        print(f"  WARN: {pdf_path} not found, skipping {doc_id}")
        return False

    if skip_existing and output_path.exists():
        print(f"  skip (exists): {output_path.name}")
        return True

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "main.py"),
        str(pdf_path),
        str(output_path),
        "--mode", mode,
        "--detector", "doclaynet",
        "--fail-on-detector-error",
    ]
    if verbose:
        cmd.append("--verbose")

    print(f"  {doc_id} [{mode}] …", end=" ", flush=True)
    result = subprocess.run(cmd, capture_output=not verbose, text=True)
    if result.returncode == 0:
        print("ok")
        return True
    else:
        print("FAILED")
        if result.stderr:
            # Print last few lines of stderr for quick diagnosis
            lines = result.stderr.strip().splitlines()
            for line in lines[-5:]:
                print(f"    {line}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-run DocStruct pipeline for all docs with existing outputs"
    )
    parser.add_argument(
        "--mode",
        choices=["model", "hybrid", "both"],
        default="both",
        help="Which pipeline(s) to run (default: both)",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Re-run even if output file already exists",
    )
    parser.add_argument(
        "--doc",
        nargs="+",
        metavar="DOC_ID",
        help="Run only these specific doc IDs (e.g. --doc doc1 doc3)",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    skip_existing = not args.no_skip

    # Discover which docs to process
    if args.doc:
        doc_ids = sorted(args.doc)
        print(f"Processing {len(doc_ids)} specified doc(s): {', '.join(doc_ids)}")
    else:
        # Prefer model-outputs as source of truth; fall back to hybrid-outputs
        source_dir = MODEL_OUT_DIR if MODEL_OUT_DIR.exists() else HYBRID_OUT_DIR
        if not source_dir.exists():
            print(f"ERROR: Neither {MODEL_OUT_DIR} nor {HYBRID_OUT_DIR} exists.")
            print("Run the pipeline manually for at least one doc first.")
            sys.exit(1)
        doc_ids = discover_doc_ids(source_dir)
        print(f"Discovered {len(doc_ids)} doc(s) from {source_dir.name}: {', '.join(doc_ids)}")

    MODEL_OUT_DIR.mkdir(parents=True, exist_ok=True)
    HYBRID_OUT_DIR.mkdir(parents=True, exist_ok=True)

    successes = 0
    failures  = 0
    total     = 0

    for doc_id in doc_ids:
        if args.mode in ("model", "both"):
            total += 1
            out = MODEL_OUT_DIR / f"{doc_id}_model.json"
            ok = run_one(doc_id, "model-first", out, skip_existing, args.verbose)
            successes += int(ok)
            failures  += int(not ok)

        if args.mode in ("hybrid", "both"):
            total += 1
            out = HYBRID_OUT_DIR / f"{doc_id}_hybrid.json"
            ok = run_one(doc_id, "true-hybrid", out, skip_existing, args.verbose)
            successes += int(ok)
            failures  += int(not ok)

    print(f"\n{'='*50}")
    print(f"Done. {successes}/{total} runs succeeded.")
    if failures:
        print(f"Failures: {failures} — check stderr above for details.")
    print(f"\nNext steps:")
    print(f"  python scripts/diff_outputs.py")
    print(f"  python scripts/generate_inspection_images.py --no-skip")
    print(f"  python scripts/compute_review_stats.py")


if __name__ == "__main__":
    main()
