"""
PDF Text Extraction using Unstract LLMWhisperer V2.

Extracts raw text from shipping document PDFs (Bill of Lading, Invoice,
Packing List) using the LLMWhisperer API with layout-preserving output
optimised for downstream LLM structuring.
"""

import os
import logging

from unstract.llmwhisperer import LLMWhispererClientV2

logger = logging.getLogger(__name__)


def _get_client() -> LLMWhispererClientV2:
    """Initialise and return a LLMWhisperer V2 client.

    The API key is read from the LLMWHISPERER_API_KEY environment variable
    (loaded from .env by the Flask app at startup).
    """
    api_key = os.environ.get("LLMWHISPERER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "LLMWHISPERER_API_KEY is not set. "
            "Add it to backend/.env and restart the server."
        )
    return LLMWhispererClientV2(api_key=api_key)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using LLMWhisperer.

    Uses ``native_text`` mode because the target documents are digitally
    generated shipping PDFs (not scans).  Falls back to ``low_cost`` OCR
    if native extraction yields very little text (< 50 chars).

    Parameters
    ----------
    file_path : str
        Absolute path to the PDF file on disk.

    Returns
    -------
    str
        The extracted text content.

    Raises
    ------
    RuntimeError
        If extraction fails or produces empty output.
    """
    client = _get_client()

    logger.info("Extracting text from %s (mode=native_text)", file_path)

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

    # Fallback: if native_text returned almost nothing, try low_cost OCR
    if len(extracted.strip()) < 50:
        logger.warning(
            "native_text yielded only %d chars — retrying with low_cost",
            len(extracted.strip()),
        )
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
        "Extracted %d characters from %s",
        len(extracted),
        os.path.basename(file_path),
    )
    return extracted
