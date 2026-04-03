"""Generate side-by-side inspection images for flagged pages.

For each page in data/flagged_pages.json:
  - LEFT panel:  only model-only blocks + boundary blocks (model perspective)
  - RIGHT panel: only hybrid-only blocks + boundary blocks (hybrid perspective)
  - Header label: "docXpageY" centered at top

Also generates inspection/review_template.csv pre-filled with likely category
per block (one row per block).

Usage:
    python scripts/generate_inspection_images.py
    python scripts/generate_inspection_images.py --dpi 150 --flagged data/flagged_pages.json
    python scripts/generate_inspection_images.py --csv-only  # regenerate CSV without re-rendering images
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

# Add project root to path so we can import visualize_overlay and utils
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from visualize_overlay import BLOCK_COLORS, _pdf_to_image_coords, _draw_label  # noqa: E402
from utils.rendering import render_page_as_png  # noqa: E402

HEADER_HEIGHT = 32   # px — slightly taller than visualize_overlay.py's 24 to fit page label
SUB_HEADER_HEIGHT = 20  # px — sub-label above each panel
PANEL_GAP = 20       # px — gap between left and right panels


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _draw_blocks_on_image(
    image: Image.Image,
    blocks: list[dict[str, Any]],
    page_width: float,
    page_height: float,
) -> Image.Image:
    """Draw colored bounding boxes for given blocks on a copy of image."""
    img = image.copy().convert("RGB")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    for block in blocks:
        bbox = block.get("bbox", {})
        if not bbox:
            continue
        block_type = block.get("block_type", "text")
        color = BLOCK_COLORS.get(block_type, (80, 80, 80))

        left, top, right, bottom = _pdf_to_image_coords(
            bbox, img.width, img.height, page_width, page_height
        )
        draw.rectangle([left, top, right, bottom], outline=color, width=2)

        conf = block.get("confidence", {})
        final_conf = conf.get("final_confidence") if isinstance(conf, dict) else None
        label = f"{block_type} {'n/a' if final_conf is None else f'{float(final_conf):.2f}'}"
        _draw_label(draw, label, left + 2, max(0, top - 12), color, font)

    return img


def _compose_panel(
    left_img: Image.Image,
    right_img: Image.Image,
    header_text: str,
    left_label: str,
    right_label: str,
) -> Image.Image:
    """Compose left and right panels with a shared header bar."""
    total_width  = left_img.width + PANEL_GAP + right_img.width
    total_height = max(left_img.height, right_img.height) + HEADER_HEIGHT + SUB_HEADER_HEIGHT

    canvas = Image.new("RGB", (total_width, total_height), (240, 240, 240))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    # Header bar (dark background)
    draw.rectangle([0, 0, total_width, HEADER_HEIGHT], fill=(40, 40, 40))
    # Center the header text
    try:
        text_bbox = draw.textbbox((0, 0), header_text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
    except Exception:
        text_w = len(header_text) * 6
    draw.text(
        ((total_width - text_w) // 2, (HEADER_HEIGHT - 10) // 2),
        header_text,
        fill=(255, 255, 255),
        font=font,
    )

    # Sub-labels above each panel
    sub_y = HEADER_HEIGHT + 4
    draw.text((10, sub_y), left_label, fill=(60, 60, 60), font=font)
    draw.text((left_img.width + PANEL_GAP + 10, sub_y), right_label, fill=(60, 60, 60), font=font)

    # Paste panel images
    content_y = HEADER_HEIGHT + SUB_HEADER_HEIGHT
    canvas.paste(left_img, (0, content_y))
    canvas.paste(right_img, (left_img.width + PANEL_GAP, content_y))

    return canvas


# ---------------------------------------------------------------------------
# Per-page image generation
# ---------------------------------------------------------------------------

def generate_for_page(
    record: dict[str, Any],
    pdf_dir: Path,
    output_dir: Path,
    dpi: int = 150,
) -> bool:
    """Render one flagged page as a side-by-side inspection image. Returns True on success."""
    doc_id   = record["doc_id"]
    page_num = record["page_num"]
    page_w   = record.get("page_width", 0)
    page_h   = record.get("page_height", 0)

    pdf_path   = pdf_dir / f"{doc_id}.pdf"
    out_path   = output_dir / f"{doc_id}page{page_num}.png"

    if not pdf_path.exists():
        print(f"  WARN: {pdf_path} not found, skipping {doc_id}page{page_num}")
        return False

    png_bytes = render_page_as_png(str(pdf_path), page_num, dpi=dpi)
    if png_bytes is None:
        print(f"  WARN: render_page_as_png returned None for {doc_id} page {page_num}")
        return False

    base_image = Image.open(BytesIO(png_bytes)).convert("RGB")

    # Left panel: model-only + boundary[model]
    left_blocks = record.get("model_only_blocks", []) + record.get("boundary_blocks", {}).get("model", [])
    # Right panel: hybrid-only + boundary[hybrid]
    right_blocks = record.get("hybrid_only_blocks", []) + record.get("boundary_blocks", {}).get("hybrid", [])

    left_img  = _draw_blocks_on_image(base_image, left_blocks,  page_w, page_h)
    right_img = _draw_blocks_on_image(base_image, right_blocks, page_w, page_h)

    composed = _compose_panel(
        left_img,
        right_img,
        header_text=f"{doc_id}page{page_num}",
        left_label=f"Model-only ({len(left_blocks)} blocks)",
        right_label=f"Hybrid-only ({len(right_blocks)} blocks)",
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    composed.save(str(out_path), format="PNG")
    return True


def run_all(
    flagged_path: Path,
    pdf_dir: Path,
    output_dir: Path,
    dpi: int = 150,
    skip_existing: bool = True,
) -> None:
    """Render inspection images for all flagged pages."""
    with flagged_path.open("r", encoding="utf-8") as f:
        records: list[dict[str, Any]] = json.load(f)

    print(f"Generating inspection images for {len(records)} flagged pages …")
    successes = 0
    failures  = 0

    for record in records:
        doc_id   = record["doc_id"]
        page_num = record["page_num"]
        out_path = output_dir / f"{doc_id}page{page_num}.png"

        if skip_existing and out_path.exists():
            print(f"  skip (exists): {out_path.name}")
            successes += 1
            continue

        print(f"  {doc_id}page{page_num} …", end=" ")
        ok = generate_for_page(record, pdf_dir, output_dir, dpi=dpi)
        if ok:
            print("ok")
            successes += 1
        else:
            print("FAILED")
            failures += 1

    print(f"\n{'='*50}")
    print(f"Done. {successes}/{len(records)} images generated → {output_dir}")
    if failures:
        print(f"Failures: {failures}")


# ---------------------------------------------------------------------------
# Review template CSV generation
# ---------------------------------------------------------------------------

def generate_review_template(
    flagged_path: Path,
    output_csv_path: Path,
) -> None:
    """Generate pre-filled review_template.csv from flagged_pages.json.

    One row per block. model_only → precision_loss, hybrid_only → recall_gain,
    boundary → boundary_improvement. Reviewers may override category to 'neutral'.
    """
    with flagged_path.open("r", encoding="utf-8") as f:
        records: list[dict[str, Any]] = json.load(f)

    fieldnames = ["image_file", "doc_id", "page_num", "block_type", "category", "notes"]
    rows: list[dict[str, str]] = []

    for record in records:
        doc_id   = record["doc_id"]
        page_num = record["page_num"]
        img_file = f"inspection/{doc_id}page{page_num}.png"

        def make_row(block: dict, category: str) -> dict:
            return {
                "image_file": img_file,
                "doc_id":     doc_id,
                "page_num":   str(page_num),
                "block_type": block.get("block_type", ""),
                "category":   category,
                "notes":      "",
            }

        for block in record.get("model_only_blocks", []):
            rows.append(make_row(block, "precision_loss"))

        for block in record.get("hybrid_only_blocks", []):
            rows.append(make_row(block, "recall_gain"))

        # Boundary: one row per pair (use model-perspective block, dedup by block_id)
        seen_boundary_ids: set[str] = set()
        for block in record.get("boundary_blocks", {}).get("model", []):
            bid = block.get("block_id", "")
            if bid and bid in seen_boundary_ids:
                continue
            seen_boundary_ids.add(bid)
            rows.append(make_row(block, "boundary_improvement"))

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with output_csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Review template written: {output_csv_path} ({len(rows)} rows)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate inspection images and review template from flagged pages"
    )
    parser.add_argument(
        "--flagged",
        type=Path,
        default=PROJECT_ROOT / "data" / "flagged_pages.json",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw-pdfs",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "inspection",
    )
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Re-render images even if they already exist",
    )
    parser.add_argument(
        "--csv-only",
        action="store_true",
        help="Only regenerate review_template.csv, skip image rendering",
    )
    args = parser.parse_args()

    if not args.flagged.exists():
        print(f"ERROR: {args.flagged} not found. Run diff_outputs.py first.")
        sys.exit(1)

    if not args.csv_only:
        run_all(
            flagged_path=args.flagged,
            pdf_dir=args.pdf_dir,
            output_dir=args.output_dir,
            dpi=args.dpi,
            skip_existing=not args.no_skip,
        )

    generate_review_template(
        flagged_path=args.flagged,
        output_csv_path=args.output_dir / "review_template.csv",
    )


if __name__ == "__main__":
    main()
