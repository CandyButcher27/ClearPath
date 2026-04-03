"""Compute statistics from the manually filled review_template.csv.

Calculates:
  - Overall % per category
  - % per category broken down by block_type
  - % per block_type broken down by category

Outputs inspection/review_stats.json and prints a formatted summary.

Usage:
    python scripts/compute_review_stats.py
    python scripts/compute_review_stats.py --csv inspection/review_template.csv --output inspection/review_stats.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

VALID_CATEGORIES = {"recall_gain", "precision_loss", "boundary_improvement", "neutral"}
VALID_BLOCK_TYPES = {"text", "header", "table", "figure", "caption"}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_review_data(csv_path: Path) -> list[dict[str, str]]:
    """Read filled review_template.csv. Skips rows with empty or invalid category."""
    rows: list[dict[str, str]] = []
    skipped = 0

    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # start=2 (row 1 = header)
            cat = row.get("category", "").strip().lower()
            bt  = row.get("block_type", "").strip().lower()

            if not cat:
                skipped += 1
                continue
            if cat not in VALID_CATEGORIES:
                print(f"  WARN: row {i} has unknown category '{cat}', skipping")
                skipped += 1
                continue
            if bt not in VALID_BLOCK_TYPES:
                print(f"  WARN: row {i} has unknown block_type '{bt}', skipping")
                skipped += 1
                continue

            rows.append({
                "image_file": row.get("image_file", ""),
                "doc_id":     row.get("doc_id", ""),
                "page_num":   row.get("page_num", ""),
                "block_type": bt,
                "category":   cat,
                "notes":      row.get("notes", ""),
            })

    if skipped:
        print(f"  ({skipped} rows skipped due to empty/invalid category or block_type)")
    return rows


# ---------------------------------------------------------------------------
# Statistics computation
# ---------------------------------------------------------------------------

def _pct(count: int, total: int) -> float:
    """Return count/total as a percentage rounded to 2 decimal places."""
    if total == 0:
        return 0.0
    return round(count / total * 100, 2)


def compute_stats(rows: list[dict[str, str]]) -> dict:
    """Compute category/block_type cross-tabulation statistics."""
    total = len(rows)

    # Raw counts
    cat_counts:        defaultdict[str, int] = defaultdict(int)
    bt_counts:         defaultdict[str, int] = defaultdict(int)
    cat_bt_counts:     defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))

    for row in rows:
        cat = row["category"]
        bt  = row["block_type"]
        cat_counts[cat] += 1
        bt_counts[bt]   += 1
        cat_bt_counts[cat][bt] += 1

    # Overall % per category
    overall = {
        cat: _pct(cat_counts[cat], total)
        for cat in sorted(VALID_CATEGORIES)
    }
    overall["_total_rows"] = total  # type: ignore[assignment]

    # % per block_type broken down by category
    by_block_type: dict[str, dict[str, float]] = {}
    for bt in sorted(VALID_BLOCK_TYPES):
        bt_total = bt_counts[bt]
        by_block_type[bt] = {
            cat: _pct(cat_bt_counts[cat][bt], bt_total)
            for cat in sorted(VALID_CATEGORIES)
        }
        by_block_type[bt]["_total_rows"] = bt_total  # type: ignore[assignment]

    # % per category broken down by block_type
    by_category: dict[str, dict[str, float]] = {}
    for cat in sorted(VALID_CATEGORIES):
        cat_total = cat_counts[cat]
        by_category[cat] = {
            bt: _pct(cat_bt_counts[cat][bt], cat_total)
            for bt in sorted(VALID_BLOCK_TYPES)
        }
        by_category[cat]["_total_rows"] = cat_total  # type: ignore[assignment]

    return {
        "total_reviewed": total,
        "overall":        overall,
        "by_block_type":  by_block_type,
        "by_category":    by_category,
    }


# ---------------------------------------------------------------------------
# Pretty-print summary
# ---------------------------------------------------------------------------

def print_summary(stats: dict) -> None:
    total = stats["total_reviewed"]
    print(f"\n{'='*60}")
    print(f"REVIEW STATISTICS  ({total} blocks reviewed)")
    print(f"{'='*60}")

    print("\n── Overall category breakdown ──────────────────────────────")
    overall = {k: v for k, v in stats["overall"].items() if not k.startswith("_")}
    for cat, pct in sorted(overall.items(), key=lambda x: -x[1]):
        n = round(pct * total / 100)
        print(f"  {cat:<25} {pct:>6.2f}%   (≈{n} blocks)")

    print("\n── By block_type (% within each type) ──────────────────────")
    header = f"  {'block_type':<10}" + "".join(f"  {c[:12]:<12}" for c in sorted(VALID_CATEGORIES))
    print(header)
    print("  " + "-" * (len(header) - 2))
    for bt in sorted(VALID_BLOCK_TYPES):
        row = stats["by_block_type"].get(bt, {})
        n   = row.get("_total_rows", 0)
        cells = "".join(
            f"  {row.get(c, 0.0):>10.2f}% "
            for c in sorted(VALID_CATEGORIES)
        )
        print(f"  {bt:<10}{cells}  (n={n})")

    print("\n── By category (% of block_types within each category) ─────")
    header2 = f"  {'category':<25}" + "".join(f"  {bt:<8}" for bt in sorted(VALID_BLOCK_TYPES))
    print(header2)
    print("  " + "-" * (len(header2) - 2))
    for cat in sorted(VALID_CATEGORIES):
        row = stats["by_category"].get(cat, {})
        n   = row.get("_total_rows", 0)
        cells = "".join(
            f"  {row.get(bt, 0.0):>6.2f}% "
            for bt in sorted(VALID_BLOCK_TYPES)
        )
        print(f"  {cat:<25}{cells}  (n={n})")

    print(f"\n{'='*60}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute statistics from filled review_template.csv"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=PROJECT_ROOT / "inspection" / "review_template.csv",
        help="Path to filled review CSV",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "inspection" / "review_stats.json",
        help="Output path for stats JSON",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"ERROR: {args.csv} not found.")
        sys.exit(1)

    print(f"Loading review data from {args.csv} …")
    rows = load_review_data(args.csv)

    if not rows:
        print("ERROR: no valid rows found in CSV.")
        sys.exit(1)

    stats = compute_stats(rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"Stats written to: {args.output}")

    print_summary(stats)


if __name__ == "__main__":
    main()
