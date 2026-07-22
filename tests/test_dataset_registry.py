import sys
import unittest
from datetime import datetime

sys.path.insert(0, ".")

from scripts.dataset_registry import get_source, load_manifest, require_allowed_use, validate_manifest
from scripts.evaluate_dataset_regressions import evaluate_calculation
from scripts.import_hf_dataset import normalize


class DatasetRegistryTests(unittest.TestCase):
    def test_manifest_has_pinned_sources_and_event_claim_guardrails(self):
        manifest = load_manifest()
        self.assertGreaterEqual(len(manifest["sources"]), 4)
        for source in manifest["sources"]:
            self.assertGreaterEqual(len(source["revision"]), 7)
            self.assertIn("event_prediction_accuracy_claim", source["prohibited_uses"])

    def test_synthetic_reasoning_cannot_be_used_as_chart_truth(self):
        source = get_source("czuo03-bazi-reasoning-300")
        with self.assertRaises(PermissionError):
            require_allowed_use(source, "bazi_chart_regression")

    def test_manifest_rejects_missing_event_accuracy_prohibition(self):
        invalid = {
            "schema_version": 1,
            "sources": [{
                "id": "bad-source",
                "provider": "test",
                "repository": "example/test",
                "revision": "1234567",
                "license": "MIT",
                "evidence_level": "unknown",
                "allowed_uses": ["testing"],
                "prohibited_uses": [],
            }],
        }
        with self.assertRaises(ValueError):
            validate_manifest(invalid)

    def test_calculation_adapter_and_evaluator_use_four_pillars_only(self):
        record = normalize("czuo03-bazi-calculate-rlvr", {
            "birthday": datetime(1990, 6, 15, 12, 0, 0),
            "question": "八字是什么？",
            "answer": "庚午 壬午 辛亥 甲午",
        })
        report = evaluate_calculation([{
            "source_id": "czuo03-bazi-calculate-rlvr",
            "record_index": 0,
            "record": record,
        }])
        self.assertEqual(report["accuracy"], 1)
        self.assertEqual(report["source_observed_compatibility"]["accuracy"], 1)

    def test_reasoning_adapter_marks_generated_content_as_synthetic(self):
        record = normalize("czuo03-bazi-reasoning-300", {
            "question": "测试问题",
            "reasoning": "合成推理",
            "answer": "合成回答",
        })
        self.assertEqual(record["synthetic_reasoning"], "合成推理")
        self.assertNotIn("expected", record)


if __name__ == "__main__":
    unittest.main()
