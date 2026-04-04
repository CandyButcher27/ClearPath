"""
PDF text extraction routing for shipment documents.

Supports:
- DocStruct local parser (default)
- Unstract LLMWhisperer fallback
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_VALID_PROVIDERS = {"docstruct", "unstract", "auto"}
_DOCSTRUCT_MIN_CHARS_DEFAULT = 80
_DOCSTRUCT_TIMEOUT_DEFAULT = 120


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name, "") or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid integer for %s=%r. Using default=%d.", name, raw, default)
        return default


def _get_provider() -> str:
    provider = (os.environ.get("PDF_EXTRACTOR_PROVIDER", "docstruct") or "").strip().lower()
    if provider not in _VALID_PROVIDERS:
        logger.warning("Unknown PDF_EXTRACTOR_PROVIDER=%r. Falling back to 'docstruct'.", provider)
        return "docstruct"
    return provider


def _get_docstruct_root() -> Path:
    configured = (os.environ.get("DOCSTRUCT_ROOT", "") or "").strip()
    if configured:
        return Path(configured).resolve()
    return (Path(__file__).resolve().parent.parent / "DocStruct").resolve()


def _get_docstruct_python(docstruct_root: Path) -> Path:
    configured = (os.environ.get("DOCSTRUCT_PYTHON", "") or "").strip()
    if configured:
        return Path(configured).resolve()

    windows_python = docstruct_root / "venv" / "Scripts" / "python.exe"
    if windows_python.exists():
        return windows_python
    return docstruct_root / "venv" / "bin" / "python"


def _get_unstract_client():
    """Initialize and return a LLMWhisperer V2 client."""
    api_key = os.environ.get("LLMWHISPERER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "LLMWHISPERER_API_KEY is not set. Add it to backend/.env and restart the server."
        )
    try:
        from unstract.llmwhisperer import LLMWhispererClientV2
    except ImportError as exc:
        raise RuntimeError(
            "unstract.llmwhisperer is not installed. Install backend requirements."
        ) from exc
    return LLMWhispererClientV2(api_key=api_key)


def _rows_to_gfm(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    padded_cols = max(len(r) for r in rows)
    normalized = [r + [""] * (padded_cols - len(r)) for r in rows]
    esc = lambda s: s.replace("|", "\\|")
    header = "| " + " | ".join(esc(c) for c in normalized[0]) + " |"
    divider = "| " + " | ".join("---" for _ in normalized[0]) + " |"
    body = ["| " + " | ".join(esc(c) for c in row) + " |" for row in normalized[1:]]
    lines = [header, divider] + body
    return "\n".join(lines)


def _table_to_markdown(block: dict[str, Any]) -> str:
    table_data = block.get("table_data")
    text = str(block.get("text") or "").strip()

    if isinstance(table_data, dict):
        rows_raw = table_data.get("rows")
        if isinstance(rows_raw, list) and rows_raw:
            rows = []
            for row in rows_raw:
                if isinstance(row, list):
                    rows.append([str(cell) for cell in row])
            if rows:
                return _rows_to_gfm(rows)

    if text:
        parsed_rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            cells = re.split(r"\t| {2,}", line)
            cells = [cell.strip() for cell in cells if cell.strip()]
            if cells:
                parsed_rows.append(cells)
        if parsed_rows:
            return _rows_to_gfm(parsed_rows)
        return text

    return ""


def _docstruct_json_to_markdown(payload: dict[str, Any]) -> str:
    pages = payload.get("pages")
    if not isinstance(pages, list):
        return ""

    page_sections: list[str] = []
    for page in pages:
        blocks = page.get("blocks", []) if isinstance(page, dict) else []
        if not isinstance(blocks, list):
            continue
        ordered_blocks = sorted(
            [b for b in blocks if isinstance(b, dict)],
            key=lambda b: int(b.get("reading_order", 10**9)),
        )
        parts: list[str] = []
        for block in ordered_blocks:
            btype = str(block.get("block_type") or "").strip().lower()
            text = str(block.get("text") or "").strip()
            if btype == "header" and text:
                parts.append(f"## {text}")
            elif btype == "text" and text:
                parts.append(text)
            elif btype == "table":
                rendered = _table_to_markdown(block)
                if rendered:
                    parts.append(rendered)
            elif btype == "caption" and text:
                parts.append(f"*{text}*")
            elif btype == "figure":
                parts.append("[Figure]")
        if parts:
            page_sections.append("\n\n".join(parts))

    if not page_sections:
        return ""
    return "\n\n---\n\n".join(page_sections).strip() + "\n"


def _extract_with_unstract(file_path: str) -> str:
    """Extract text from a PDF file using LLMWhisperer with OCR fallback."""
    client = _get_unstract_client()
    logger.info("Extracting text from %s via Unstract (mode=native_text)", file_path)

    try:
        result = client.whisper(
            file_path=file_path,
            mode="native_text",
            output_mode="layout_preserving",
            wait_for_completion=True,
        )
    except Exception as exc:
        logger.error("LLMWhisperer native_text failed for %s: %s", file_path, exc)
        raise RuntimeError(f"PDF extraction failed: {exc}") from exc

    extracted = result.get("extraction", {}).get("result_text", "")

    if len(extracted.strip()) < 50:
        logger.warning("native_text yielded only %d chars, retrying with low_cost", len(extracted.strip()))
        try:
            result = client.whisper(
                file_path=file_path,
                mode="low_cost",
                output_mode="layout_preserving",
                wait_for_completion=True,
            )
            extracted = result.get("extraction", {}).get("result_text", "")
        except Exception as exc:
            logger.error("LLMWhisperer low_cost failed for %s: %s", file_path, exc)
            raise RuntimeError(f"PDF extraction (fallback) failed: {exc}") from exc

    if not extracted or not extracted.strip():
        raise RuntimeError(
            f"No text could be extracted from {os.path.basename(file_path)}. "
            "Ensure the PDF contains readable content."
        )

    logger.info(
        "Extracted %d characters from %s via Unstract",
        len(extracted),
        os.path.basename(file_path),
    )
    return extracted


def _extract_with_docstruct(file_path: str) -> str:
    docstruct_root = _get_docstruct_root()
    if not docstruct_root.exists():
        raise RuntimeError(f"DocStruct root not found: {docstruct_root}")

    docstruct_python = _get_docstruct_python(docstruct_root)
    if not docstruct_python.exists():
        raise RuntimeError(
            f"DocStruct Python not found: {docstruct_python}. "
            "Set DOCSTRUCT_PYTHON or ensure DocStruct venv exists."
        )

    mode = (os.environ.get("DOCSTRUCT_MODE", "standard") or "").strip() or "standard"
    detector = (os.environ.get("DOCSTRUCT_DETECTOR", "stub") or "").strip() or "stub"
    timeout_sec = _env_int("DOCSTRUCT_TIMEOUT_SEC", _DOCSTRUCT_TIMEOUT_DEFAULT)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        output_path = Path(tmp.name)

    cmd = [
        str(docstruct_python),
        "main.py",
        "--mode",
        mode,
        "--detector",
        detector,
        str(file_path),
        str(output_path),
    ]
    logger.info("Extracting text from %s via DocStruct (mode=%s, detector=%s)", file_path, mode, detector)

    try:
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(docstruct_root),
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"DocStruct timed out after {timeout_sec}s for {os.path.basename(file_path)}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"DocStruct process failed: {exc}") from exc

        if proc.returncode != 0:
            stderr_tail = (proc.stderr or "").strip()[-1000:]
            raise RuntimeError(
                f"DocStruct exited with code {proc.returncode}. stderr={stderr_tail}"
            )

        with open(output_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        extracted = _docstruct_json_to_markdown(payload)
    finally:
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            pass

    if not extracted.strip():
        raise RuntimeError(
            f"DocStruct returned empty text for {os.path.basename(file_path)}"
        )

    logger.info(
        "Extracted %d characters from %s via DocStruct",
        len(extracted),
        os.path.basename(file_path),
    )
    return extracted


def extract_text_from_pdf_with_source(file_path: str) -> tuple[str, str]:
    """Extract text from a PDF and return (text, source label)."""
    provider = _get_provider()
    min_chars = _env_int("DOCSTRUCT_MIN_CHARS", _DOCSTRUCT_MIN_CHARS_DEFAULT)

    if provider == "unstract":
        return _extract_with_unstract(file_path), "unstract"

    try:
        docstruct_text = _extract_with_docstruct(file_path)
        if len(docstruct_text.strip()) < min_chars:
            raise RuntimeError(
                f"DocStruct output below min threshold ({len(docstruct_text.strip())} < {min_chars})"
            )
        return docstruct_text, "docstruct"
    except Exception as exc:
        logger.warning(
            "DocStruct extraction failed for %s: %s. Falling back to Unstract.",
            file_path,
            exc,
        )
        fallback_text = _extract_with_unstract(file_path)
        return fallback_text, "unstract_fallback"


def extract_text_from_pdf(file_path: str) -> str:
    """Backward-compatible extraction API used by existing pipeline."""
    text, _ = extract_text_from_pdf_with_source(file_path)
    return text
