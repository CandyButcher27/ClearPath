import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pdf_parser  # noqa: E402


class PdfParserRoutingTests(unittest.TestCase):
    def test_forced_unstract_provider(self):
        with patch.dict(os.environ, {"PDF_EXTRACTOR_PROVIDER": "unstract"}, clear=False), patch.object(
            pdf_parser, "_extract_with_unstract", return_value="u-text"
        ) as unstract_mock, patch.object(pdf_parser, "_extract_with_docstruct") as docstruct_mock:
            text, source = pdf_parser.extract_text_from_pdf_with_source("invoice.pdf")
            self.assertEqual(text, "u-text")
            self.assertEqual(source, "unstract")
            self.assertTrue(unstract_mock.called)
            self.assertFalse(docstruct_mock.called)

    def test_docstruct_primary_success(self):
        with patch.dict(
            os.environ,
            {"PDF_EXTRACTOR_PROVIDER": "docstruct", "DOCSTRUCT_MIN_CHARS": "10"},
            clear=False,
        ), patch.object(pdf_parser, "_extract_with_docstruct", return_value="d-text-good"), patch.object(
            pdf_parser, "_extract_with_unstract", return_value="u-text"
        ) as unstract_mock:
            text, source = pdf_parser.extract_text_from_pdf_with_source("invoice.pdf")
            self.assertEqual(text, "d-text-good")
            self.assertEqual(source, "docstruct")
            self.assertFalse(unstract_mock.called)

    def test_docstruct_error_falls_back_to_unstract(self):
        with patch.dict(os.environ, {"PDF_EXTRACTOR_PROVIDER": "docstruct"}, clear=False), patch.object(
            pdf_parser, "_extract_with_docstruct", side_effect=RuntimeError("docstruct boom")
        ), patch.object(pdf_parser, "_extract_with_unstract", return_value="u-fallback"):
            text, source = pdf_parser.extract_text_from_pdf_with_source("invoice.pdf")
            self.assertEqual(text, "u-fallback")
            self.assertEqual(source, "unstract_fallback")

    def test_docstruct_near_empty_falls_back_to_unstract(self):
        with patch.dict(
            os.environ,
            {"PDF_EXTRACTOR_PROVIDER": "docstruct", "DOCSTRUCT_MIN_CHARS": "20"},
            clear=False,
        ), patch.object(pdf_parser, "_extract_with_docstruct", return_value="tiny"), patch.object(
            pdf_parser, "_extract_with_unstract", return_value="u-fallback"
        ):
            text, source = pdf_parser.extract_text_from_pdf_with_source("invoice.pdf")
            self.assertEqual(text, "u-fallback")
            self.assertEqual(source, "unstract_fallback")

    def test_docstruct_timeout_raises_controlled_error(self):
        with patch.object(pdf_parser, "_get_docstruct_root", return_value=BACKEND_DIR), patch.object(
            pdf_parser, "_get_docstruct_python", return_value=Path(sys.executable)
        ), patch(
            "pdf_parser.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="main.py", timeout=1),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                pdf_parser._extract_with_docstruct("invoice.pdf")
            self.assertIn("timed out", str(ctx.exception).lower())

    def test_docstruct_json_to_markdown_conversion(self):
        payload = {
            "pages": [
                {
                    "page_num": 0,
                    "blocks": [
                        {"reading_order": 1, "block_type": "text", "text": "Body line"},
                        {"reading_order": 0, "block_type": "header", "text": "Invoice Title"},
                        {"reading_order": 2, "block_type": "table", "text": "Item  Qty\nWidget  3"},
                    ],
                }
            ]
        }
        md = pdf_parser._docstruct_json_to_markdown(payload)
        self.assertIn("## Invoice Title", md)
        self.assertIn("Body line", md)
        self.assertIn("| Item | Qty |", md)


if __name__ == "__main__":
    unittest.main()
