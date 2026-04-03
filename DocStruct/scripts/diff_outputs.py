"""Compute per-page diffs between model-first and true-hybrid JSON outputs.

For each page in each doc, identifies:
  - model_only_blocks:  blocks in model output with no matching hybrid block
  - hybrid_only_blocks: blocks in hybrid output with no matching model block
  - boundary_blocks:    matched pairs where IoU is in [0.3, 0.7) — same location,
                        different confidence or slightly shifted bbox

A page is "flagged" if any of these lists is non-empty.

Output: data/flagged_pages.json

Usage:
    python scripts/diff_outputs.py
    python scripts/diff_outputs.py --num-docs 30 --output data/flagged_pages.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# IoU thresholds
MATCH_IOU_THRESHOLD = 0.50   # blocks with IoU >= this are "matched"
BOUNDARY_IOU_LOW    = 0.30   # matched pairs with IoU in [LOW, HIGH) are "boundary"
BOUNDARY_IOU_HIGH   = 0.70


# ---------------------------------------------------------------------------
# IoU helper — dict-based, no project imports needed
# Mirrors evaluation/metrics.py::_iou() exactly.
# ---------------------------------------------------------------------------

def _iou_dicts(a: dict[str, float], b: dict[str, float]) -> float:
    """IoU between two bbox dicts with keys x0, y0, x1, y1."""
    x_left   = max(a["x0"], b["x0"])
    y_top    = max(a["y0"], b["y0"])
    x_right  = min(a["x1"], b["x1"])
    y_bottom = min(a["y1"], b["y1"])
    if x_right <= x_left or y_bottom <= y_top:
        return 0.0
    inter = (x_right - x_left) * (y_bottom - y_top)
    area_a = (a["x1"] - a["x0"]) * (a["y1"] - a["y0"])
    area_b = (b["x1"] - b["x0"]) * (b["y1"] - b["y0"])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _minimal_block(block: dict[str, Any]) -> dict[str, Any]:
    """Extract only the fields needed downstream from a raw block dict."""
    return {
        "block_id":   block.get("block_id", ""),
        "block_type": block.get("block_type", "text"),
        "bbox":       block.get("bbox", {}),
        "confidence": block.get("confidence", {}),
    }


# ---------------------------------------------------------------------------
# Core matching logic
# ---------------------------------------------------------------------------

def match_blocks_for_page(
    model_blocks: list[dict[str, Any]],
    hybrid_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Greedy one-to-one matching between model and hybrid blocks for one page.

    Matching rules:
      - Blocks must have the same block_type to be eligible for matching.
      - For each model block, the best-IoU eligible hybrid block (IoU >= MATCH_IOU_THRESHOLD)
        is chosen greedily; ties broken by IoU descending.
      - Matched pairs with IoU in [BOUNDARY_IOU_LOW, BOUNDARY_IOU_HIGH) are
        classified as boundary blocks.

    Returns:
        {
          "matched_pairs":   [(model_block, hybrid_block, iou), ...],
          "model_only":      [block, ...],
          "hybrid_only":     [block, ...],
          "boundary_blocks": {"model": [...], "hybrid": [...]},
        }
    """
    used_hybrid: set[int] = set()
    matched_pairs: list[tuple[dict, dict, float]] = []
    model_only: list[dict] = []

    for model_block in model_blocks:
        model_bbox = model_block.get("bbox", {})
        model_type = model_block.get("block_type", "")

        # Find best candidate among unused hybrid blocks with same type
        best_idx: int | None = None
        best_iou: float = 0.0

        for j, hybrid_block in enumerate(hybrid_blocks):
            if j in used_hybrid:
                continue
            if hybrid_block.get("block_type", "") != model_type:
                continue
            iou = _iou_dicts(model_bbox, hybrid_block.get("bbox", {}))
            if iou > best_iou:
                best_iou = iou
                best_idx = j

        if best_idx is not None and best_iou >= MATCH_IOU_THRESHOLD:
            matched_pairs.append((model_block, hybrid_blocks[best_idx], best_iou))
            used_hybrid.add(best_idx)
        else:
            model_only.append(_minimal_block(model_block))

    hybrid_only = [
        _minimal_block(hybrid_blocks[j])
        for j in range(len(hybrid_blocks))
        if j not in used_hybrid
    ]

    # Boundary: matched but IoU in [LOW, HIGH) — bbox agreement is weak
    boundary_model  = [_minimal_block(p[0]) for p in matched_pairs if BOUNDARY_IOU_LOW <= p[2] < BOUNDARY_IOU_HIGH]
    boundary_hybrid = [_minimal_block(p[1]) for p in matched_pairs if BOUNDARY_IOU_LOW <= p[2] < BOUNDARY_IOU_HIGH]

    return {
        "matched_pairs":   matched_pairs,
        "model_only":      model_only,
        "hybrid_only":     hybrid_only,
        "boundary_blocks": {"model": boundary_model, "hybrid": boundary_hybrid},
    }


# ---------------------------------------------------------------------------
# Per-document and full-batch diff
# ---------------------------------------------------------------------------

def diff_single_doc(
    model_json_path: Path,
    hybrid_json_path: Path,
    doc_id: str,
) -> list[dict[str, Any]]:
    """Diff model vs hybrid outputs for one document.

    Returns a list of flagged page records (only pages with differences).
    Each record:
    {
      "doc_id":             str,
      "page_num":           int,
      "page_width":         float,
      "page_height":        float,
      "model_only_blocks":  [minimal_block, ...],
      "hybrid_only_blocks": [minimal_block, ...],
      "boundary_blocks":    {"model": [...], "hybrid": [...]},
    }
    """
    with model_json_path.open("r", encoding="utf-8") as f:
        model_data = json.load(f)
    with hybrid_json_path.open("r", encoding="utf-8") as f:
        hybrid_data = json.load(f)

    # Build page dicts keyed by page_num
    model_pages  = {p["page_num"]: p for p in model_data.get("pages", [])}
    hybrid_pages = {p["page_num"]: p for p in hybrid_data.get("pages", [])}

    common_page_nums = set(model_pages) & set(hybrid_pages)
    if len(model_pages) != len(hybrid_pages):
        print(
            f"  WARN: {doc_id} has {len(model_pages)} model pages and "
            f"{len(hybrid_pages)} hybrid pages — diffing {len(common_page_nums)} common pages"
        )

    flagged: list[dict[str, Any]] = []

    for page_num in sorted(common_page_nums):
        model_page  = model_pages[page_num]
        hybrid_page = hybrid_pages[page_num]

        dims = model_page.get("dimensions", {})
        page_width  = float(dims.get("width", 0))
        page_height = float(dims.get("height", 0))

        model_blocks  = model_page.get("blocks", [])
        hybrid_blocks = hybrid_page.get("blocks", [])

        diff = match_blocks_for_page(model_blocks, hybrid_blocks)

        has_diff = (
            bool(diff["model_only"])
            or bool(diff["hybrid_only"])
            or bool(diff["boundary_blocks"]["model"])
        )

        if has_diff:
            flagged.append({
                "doc_id":             doc_id,
                "page_num":           page_num,
                "page_width":         page_width,
                "page_height":        page_height,
                "model_only_blocks":  diff["model_only"],
                "hybrid_only_blocks": diff["hybrid_only"],
                "boundary_blocks":    diff["boundary_blocks"],
            })

    return flagged


def run_all_diffs(
    model_out_dir: Path,
    hybrid_out_dir: Path,
    output_path: Path,
    num_docs: int = 30,
) -> None:
    """Diff all docs and write combined flagged_pages.json."""
    all_flagged: list[dict[str, Any]] = []

    for i in range(1, num_docs + 1):
        doc_id = f"doc{i}"
        model_path  = model_out_dir  / f"{doc_id}_model.json"
        hybrid_path = hybrid_out_dir / f"{doc_id}_hybrid.json"

        if not model_path.exists():
            print(f"  WARN: {model_path.name} not found, skipping {doc_id}")
            continue
        if not hybrid_path.exists():
            print(f"  WARN: {hybrid_path.name} not found, skipping {doc_id}")
            continue

        print(f"  diffing {doc_id} …")
        try:
            flagged = diff_single_doc(model_path, hybrid_path, doc_id)
        except Exception as e:
            print(f"  ERROR diffing {doc_id}: {e}")
            continue

        all_flagged.extend(flagged)
        print(f"    → {len(flagged)} flagged pages")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(all_flagged, f, indent=2)

    print(f"\n{'='*50}")
    print(f"Done. {len(all_flagged)} flagged pages across all docs.")
    print(f"Written to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diff model-first vs true-hybrid JSON outputs, flagging pages with differences"
    )
    parser.add_argument(
        "--model-out-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "model-outputs",
    )
    parser.add_argument(
        "--hybrid-out-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "hybrid-outputs",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "flagged_pages.json",
    )
    parser.add_argument("--num-docs", type=int, default=30)
    args = parser.parse_args()

    run_all_diffs(
        model_out_dir=args.model_out_dir,
        hybrid_out_dir=args.hybrid_out_dir,
        output_path=args.output,
        num_docs=args.num_docs,
    )


if __name__ == "__main__":
    main()
