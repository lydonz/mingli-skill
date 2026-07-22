import sys
import unittest
from datetime import datetime

sys.path.insert(0, ".")

from scripts.dataset_registry import get_source, load_manifest, require_allowed_use, validate_manifest
from scripts.evaluate_dataset_regressions import (
    evaluate_calculation,
    evaluate_mingli_bench_bazi,
)
from scripts.import_hf_dataset import normalize
from scripts.import_mingli_bench import _normalize_fixture


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

    def test_mingli_bench_event_answers_are_not_an_approved_metric(self):
        source = get_source("mingli-bench")
        with self.assertRaises(PermissionError):
            require_allowed_use(source, "event_answer_scoring")

    def test_mingli_bench_normalizer_excludes_raw_birth_and_event_text(self):
        source_fixture = {
            "case_id": "fixture-1",
            "birth_info": {
                "raw": "不应写入标准化记录",
                "gender": "女",
                "year": 2000,
                "month": 1,
                "day": 2,
                "hour": 3,
                "minute": 4,
                "location": "不应写入标准化记录",
            },
            "api_response": {
                "success": True,
                "data": {
                    "data": {
                        "chineseDate": "庚辰 戊子 甲子 丙寅",
                        "lunarDate": "示例农历",
                        "earthlyBranchOfSoulPalace": "子",
                        "earthlyBranchOfBodyPalace": "丑",
                        "fiveElementsClass": "木三局",
                        "zodiac": "龙",
                        "palaces": [
                            {
                                "name": f"宫位{index}",
                                "earthlyBranch": f"支{index}",
                                "majorStars": [{"name": f"主星{index}"}],
                                "minorStars": [{"name": f"辅星{index}"}],
                            }
                            for index in range(12)
                        ],
                    }
                },
            },
        }

        normalized = _normalize_fixture(source_fixture)
        rendered = str(normalized)

        self.assertEqual(
            normalized["input"]["civil_birth_time"], "2000-01-02T03:04"
        )
        self.assertNotIn("raw", normalized["input"])
        self.assertNotIn("location", normalized["input"])
        self.assertNotIn("不应写入标准化记录", rendered)

    def test_mingli_bench_bazi_evaluator_compares_fixture_only(self):
        records = [{
            "source_id": "mingli-bench",
            "record_index": 0,
            "record": {
                "case_id": "fixture-1",
                "input": {
                    "civil_birth_time": "1990-06-15T12:00",
                    "gender": "女",
                },
                "expected": {
                    "four_pillars": ["庚午", "壬午", "辛亥", "甲午"],
                },
            },
        }]

        report = evaluate_mingli_bench_bazi(records)

        self.assertEqual(report["full_pillar_exact_match"]["matched"], 1)
        self.assertEqual(report["pillar_component_matches"]["year"]["matched"], 1)
        self.assertFalse(report["mismatches"])

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
