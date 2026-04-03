"""Convert a DocStruct Document to Markdown format."""

from __future__ import annotations

import re
from typing import List

from schemas.document import Document


def _escape_pipe(text: str) -> str:
    """Escape pipe characters inside GFM table cells."""
    return text.replace("|", "\\|")


def _table_to_gfm(block) -> str:
    """Render a table block as a GFM markdown table.

    Strategy:
    1. If table_data contains row/column structure, use it.
    2. Otherwise, attempt to parse the raw text into rows/cells.
    3. Fall back to a fenced code block if no structure can be inferred.
    """
    table_data = block.table_data
    text = (block.text or "").strip()

    # Try structured rows first (future-proof: if table_data ever contains cell content)
    if table_data and isinstance(table_data, dict):
        rows_raw = table_data.get("rows")
        if rows_raw and isinstance(rows_raw, list):
            return _rows_to_gfm(rows_raw)

    # Parse raw text: split on newlines → rows, split each row on 2+ spaces or tabs → cells
    if text:
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if len(lines) >= 1:
            parsed_rows = []
            for ln in lines:
                # Split on tab or 2+ consecutive spaces
                cells = re.split(r"\t| {2,}", ln.strip())
                cells = [c.strip() for c in cells if c.strip()]
                if cells:
                    parsed_rows.append(cells)

            if parsed_rows:
                return _rows_to_gfm(parsed_rows)

    # Last resort: fenced code block
    if text:
        return f"```\n{text}\n```\n\n"

    return ""


def _rows_to_gfm(rows: List[List[str]]) -> str:
    """Convert a list of row-lists into a GFM pipe table string."""
    if not rows:
        return ""

    # Normalise all cells to strings
    str_rows = [[str(cell) for cell in row] for row in rows]

    # Determine max column count
    max_cols = max(len(r) for r in str_rows)

    # Pad rows to equal width
    padded = [r + [""] * (max_cols - len(r)) for r in str_rows]

    header = padded[0]
    body = padded[1:] if len(padded) > 1 else []

    header_line = "| " + " | ".join(_escape_pipe(c) for c in header) + " |"
    separator = "| " + " | ".join("---" for _ in header) + " |"
    body_lines = [
        "| " + " | ".join(_escape_pipe(c) for c in row) + " |"
        for row in body
    ]

    parts = [header_line, separator] + body_lines
    return "\n".join(parts) + "\n\n"


def document_to_markdown(document: Document) -> str:
    """Convert a Document to a Markdown string.

    Block rendering rules:
    - header  → ## <text>
    - text    → <text> (paragraph, blank line after)
    - table   → GFM pipe table (parsed from block.text or table_data)
    - figure  → blockquote placeholder
    - caption → *<text>* (italicised)

    Pages are separated by a horizontal rule.
    Blocks within each page are emitted in reading_order.
    """
    sections: List[str] = []

    for page_idx, page in enumerate(document.pages):
        page_parts: List[str] = []

        # Sort blocks by reading_order
        sorted_blocks = sorted(page.blocks, key=lambda b: b.reading_order)

        for block in sorted_blocks:
            text = (block.text or "").strip()
            btype = block.block_type

            if btype == "header":
                if text:
                    page_parts.append(f"## {text}\n\n")

            elif btype == "text":
                if text:
                    page_parts.append(f"{text}\n\n")

            elif btype == "table":
                rendered = _table_to_gfm(block)
                if rendered:
                    page_parts.append(rendered)
                elif text:
                    page_parts.append(f"{text}\n\n")

            elif btype == "figure":
                page_parts.append("> [Figure]\n\n")

            elif btype == "caption":
                if text:
                    page_parts.append(f"*{text}*\n\n")

        if page_parts:
            sections.append("".join(page_parts).rstrip("\n"))

    return "\n\n---\n\n".join(sections) + "\n"
