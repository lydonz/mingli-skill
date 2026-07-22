import json
from pathlib import Path
import re
import unittest
from unittest import mock

from tools import HybridMingliToolkit
from tools.calendar_engine import (
    _get_solar_term_date,
    _solar_term_cache,
    _solar_term_datetime_cache,
)
from engine.run_tools_engine import predict
from engine.run_tools_engine import compute_chart
from tools.tool_integration import build_tool_data


ROOT = Path(__file__).resolve().parents[1]


class RuntimeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.toolkit = HybridMingliToolkit()

    def _analyze(self, category="事业", question="分析事业", options_json="[]"):
        return json.loads(self.toolkit.analyze_question(
            1990,
            6,
            15,
            12,
            "女",
            category,
            question,
            options_json,
        ))

    def test_free_question_does_not_run_multiple_choice_rules(self):
        result = self._analyze()

        self.assertIsNone(result["rules_suggestion"]["suggested_answer"])
        self.assertEqual(
            result["component_status"]["rules_suggestion"]["code"],
            "rules_suggestion_no_options",
        )

    def test_high_risk_question_suppresses_rules_suggestion(self):
        result = self._analyze(
            category="健康",
            question="2027年会不会需要手术",
            options_json=(
                '[{"letter":"A","text":"需要手术"},'
                '{"letter":"B","text":"平安"}]'
            ),
        )

        self.assertIsNone(result["rules_suggestion"]["suggested_answer"])
        self.assertEqual(
            result["component_status"]["rules_suggestion"]["code"],
            "rules_suggestion_high_risk_category",
        )

    def test_direct_rules_engine_does_not_bypass_high_risk_gate(self):
        prediction = predict({
            "birth_info": {
                "year": 1990,
                "month": 6,
                "day": 15,
                "hour": 12,
                "gender": "女",
            },
            "category": "健康",
            "question": "2027年会不会需要手术",
            "options": [
                {"letter": "A", "text": "需要手术"},
                {"letter": "B", "text": "平安"},
            ],
            "case_id": "high-risk-test",
        }, {})

        self.assertIsNone(prediction)

    def test_financial_decision_content_is_suppressed_even_in_career_category(self):
        result = self._analyze(
            question="是否应该投资股票",
            options_json=(
                '[{"letter":"A","text":"买入"},'
                '{"letter":"B","text":"不买"}]'
            ),
        )

        self.assertEqual(
            result["component_status"]["rules_suggestion"]["code"],
            "rules_suggestion_high_risk_content",
        )

    def test_health_structure_uses_cultural_labels_not_treatment_language(self):
        result = self._analyze(category="健康", question="传统五行结构")
        health = result["health_analysis"]
        element = health["五行健康分析"]["土"]

        self.assertIn("传统对应范畴", element)
        self.assertIn("五行符号状态", element)
        self.assertNotIn("对应脏腑", element)
        self.assertNotIn("需调理", json.dumps(health, ensure_ascii=False))
        self.assertIn("不构成健康评估", health["医疗声明"])

    def test_ziwei_backend_fallback_is_degraded_and_visible(self):
        with mock.patch("tools.ziwei_tools.shutil.which", return_value=None):
            result = self._analyze()

        status = result["component_status"]["ziwei"]
        self.assertEqual(status["status"], "degraded")
        self.assertEqual(status["code"], "ziwei_node_runtime_missing")
        self.assertEqual(
            result["ziwei_raw"]["排盘引擎"],
            "approximate-fallback",
        )

    def test_ziwei_precision_is_available_only_for_exact_backend(self):
        chart = compute_chart({
            "year": 1990,
            "month": 6,
            "day": 15,
            "hour": 12,
            "gender": "女",
        })
        exact = build_tool_data(1990, 6, 15, 12, "女", chart=chart)
        self.assertEqual(exact["zw_precision"], "iztro")

        with mock.patch("tools.ziwei_tools.shutil.which", return_value=None):
            fallback = build_tool_data(1990, 6, 15, 12, "女", chart=chart)
        self.assertEqual(fallback["zw_precision"], "approximate")

    def test_solar_term_date_does_not_silently_use_rough_fallback(self):
        _solar_term_cache.clear()
        _solar_term_datetime_cache.clear()
        with mock.patch("tools.calendar_engine._SolarPython", None):
            with self.assertRaises(RuntimeError):
                _get_solar_term_date(2026, 2)


class RepositoryHygieneTests(unittest.TestCase):
    def test_obsolete_private_samples_and_windows_scripts_are_absent(self):
        for relative_path in (
            "blind_10_charts.json",
            "blind_10_charts_fixed.json",
            "chart_data.json",
            "sampled_ids.json",
            "sampled_questions.json",
            "final_score.py",
            "get_charts.py",
            "hybrid_router.py",
            "predict_mingli.py",
            "run_bench_10.py",
            "run_bench_10_v2.py",
            "run_bench_blind.py",
            "sample_10.py",
            "sample_blind.py",
            "validate_mingli_bench.py",
        ):
            self.assertFalse((ROOT / relative_path).exists(), relative_path)

    def test_skill_instructions_do_not_claim_prediction_accuracy(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertNotIn("全球排名", skill)
        self.assertIsNone(
            re.search(r"(?:预测准确率|准确率)\s*[:：]?\s*\d", skill)
        )
        self.assertIn("不验证或提升预测准确率", skill)
        self.assertNotIn("predict_mingli.py", skill)


if __name__ == "__main__":
    unittest.main()
