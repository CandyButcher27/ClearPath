import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import structurer  # noqa: E402


class _FakeGroqResponse:
    def __init__(self, payload: str):
        self.choices = [type("Choice", (), {"message": type("Msg", (), {"content": payload})()})()]


class _FakeCompletions:
    def __init__(self, payload: str):
        self._payload = payload

    def create(self, **kwargs):
        return _FakeGroqResponse(self._payload)


class _FakeGroqClient:
    def __init__(self, payload: str):
        self.chat = type("Chat", (), {"completions": _FakeCompletions(payload)})()


class StructurerCategoryMetadataTests(unittest.TestCase):
    def setUp(self):
        self.texts = {
            "bill_of_lading": "BOL text",
            "invoice": "Invoice HS Code: 0810.10",
            "packing_list": "PL text",
        }

    def _run_bundle_with_payload(self, bundle_payload: dict, category_fallback_payload: dict | None = None):
        raw_payload = json.dumps(bundle_payload)
        fallback_payload = category_fallback_payload or {"category": "General", "metadata_fields": {}}

        with patch.object(structurer, "_get_groq_client", return_value=_FakeGroqClient(raw_payload)), \
             patch.object(structurer, "_dump_groq_output", return_value=None), \
             patch.object(structurer, "_dump_structured_snapshot", return_value=None), \
             patch.object(structurer, "structure_category_metadata", return_value=fallback_payload) as fallback_mock:
            bol, inv, pl, category_meta = structurer.structure_shipment_document_bundle(self.texts)
            return bol, inv, pl, category_meta, fallback_mock

    def test_non_general_empty_metadata_triggers_targeted_fallback(self):
        payload = {
            "bill_of_lading": {"bill_of_lading_number": "B1"},
            "invoice": {
                "invoice_number": "I1",
                "line_items": [{"hs_code": "0810.10"}],
            },
            "packing_list": {},
            "category_metadata": {"category": "Perishables", "metadata_fields": {}},
        }
        fallback = {
            "category": "Perishables",
            "metadata_fields": {
                "expiry_date": "2026-04-20",
                "temperature_control": {"required": True, "min_temp": 2, "max_temp": 4, "unit": "Celsius"},
            },
        }
        _, _, _, category_meta, fallback_mock = self._run_bundle_with_payload(payload, fallback)
        self.assertEqual(category_meta["category"], "Perishables")
        self.assertEqual(category_meta["metadata_fields"]["expiry_date"], "2026-04-20")
        self.assertTrue(fallback_mock.called)

    def test_general_category_does_not_trigger_fallback(self):
        self.texts["invoice"] = "Invoice without hs"
        payload = {
            "bill_of_lading": {"bill_of_lading_number": "B1"},
            "invoice": {"invoice_number": "I1", "line_items": [{"hs_code": ""}]},
            "packing_list": {},
            "category_metadata": {"category": "General", "metadata_fields": {}},
        }
        _, _, _, category_meta, fallback_mock = self._run_bundle_with_payload(payload)
        self.assertEqual(category_meta["category"], "General")
        self.assertEqual(category_meta["metadata_fields"], {})
        self.assertFalse(fallback_mock.called)

    def test_sparse_bundle_metadata_is_merged_with_fallback_preserving_non_default(self):
        payload = {
            "bill_of_lading": {"bill_of_lading_number": "B2"},
            "invoice": {
                "invoice_number": "I2",
                "line_items": [{"hs_code": "2505.10"}],
            },
            "packing_list": {},
            "category_metadata": {
                "category": "Raw Materials",
                "metadata_fields": {"country_of_origin": "Brazil"},
            },
        }
        fallback = {
            "category": "Raw Materials",
            "metadata_fields": {"country_of_origin": "Chile", "purity_percentage": 99.5},
        }
        _, _, _, category_meta, fallback_mock = self._run_bundle_with_payload(payload, fallback)
        self.assertTrue(fallback_mock.called)
        self.assertEqual(category_meta["category"], "Raw Materials")
        self.assertEqual(category_meta["metadata_fields"]["country_of_origin"], "Brazil")
        self.assertEqual(category_meta["metadata_fields"]["purity_percentage"], 99.5)

    def test_detect_category_uses_any_invoice_line_item_hs(self):
        invoice = {"line_items": [{"hs_code": ""}, {"hs_code": "847130"}]}
        category = structurer.detect_category(invoice, "")
        self.assertEqual(category, "Manufactured Goods")

    def test_detect_category_falls_back_to_invoice_text_hs(self):
        invoice = {"line_items": [{"hs_code": ""}]}
        category = structurer.detect_category(invoice, "HS Code: 2505.10")
        self.assertEqual(category, "Raw Materials")


if __name__ == "__main__":
    unittest.main()
