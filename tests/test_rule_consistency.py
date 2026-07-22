import json
import unittest

from engine.run_tools_engine import compute_chart, eval_year
from tools import HybridMingliToolkit
from tools.chart_assessment import (
    PREFERENCE_RULESET_VERSION,
    STRENGTH_RULESET_VERSION,
    _derive_preference,
    get_resolved_preference,
)


class RuleConsistencyTests(unittest.TestCase):
    """Protect the versioned rules consumed by all derived analysis modules."""

    @staticmethod
    def _birth_info():
        return {
            "year": 1990,
            "month": 6,
            "day": 15,
            "hour": 12,
            "gender": "女",
        }

    def test_canonical_preference_replaces_conflicting_legacy_fields(self):
        chart = compute_chart(self._birth_info())
        assessment = chart["strength_assessment"]
        preference = get_resolved_preference(chart)

        self.assertEqual(assessment["version"], STRENGTH_RULESET_VERSION)
        self.assertEqual(
            assessment["preference_ruleset_version"],
            PREFERENCE_RULESET_VERSION,
        )
        self.assertEqual(assessment["旺衰"], "中和偏弱")
        self.assertEqual(preference["喜用神"], "土")
        self.assertEqual(preference["喜神"], "金")
        self.assertEqual(preference["忌神"], "水")
        self.assertIn("strength_model_conflict", assessment["conflicts"])
        self.assertIn("preference_model_conflict", assessment["conflicts"])
        self.assertEqual(
            assessment["legacy_preference"]["喜用神"],
            chart["legacy_strength"]["喜用神"],
        )
        self.assertEqual(
            set(preference[key] for key in ("喜用神", "喜神", "忌神")),
            {"土", "金", "水"},
        )

    def test_all_balance_paths_keep_preference_fields_distinct(self):
        for day_element in ("木", "火", "土", "金", "水"):
            for strength in ("身旺", "中和偏旺", "身弱", "中和偏弱"):
                preference = _derive_preference(day_element, strength)
                self.assertEqual(
                    len({
                        preference["喜用神"],
                        preference["喜神"],
                        preference["忌神"],
                    }),
                    3,
                    f"{day_element} {strength}",
                )

    def test_stale_assessment_is_rebuilt_before_derived_rules_read_it(self):
        chart = compute_chart(self._birth_info())
        chart["strength_assessment"] = {
            "version": "seasonal-strength-v1",
            "喜用神": "木",
        }

        preference = get_resolved_preference(chart)

        self.assertEqual(
            chart["strength_assessment"]["version"],
            STRENGTH_RULESET_VERSION,
        )
        self.assertEqual(
            preference["ruleset_version"],
            PREFERENCE_RULESET_VERSION,
        )
        self.assertEqual(preference["喜用神"], "土")

    def test_year_evaluation_exposes_direct_and_supporting_signal_evidence(self):
        chart = compute_chart(self._birth_info())
        preference = get_resolved_preference(chart)
        evaluation = eval_year(chart, 2026)
        signals = evaluation["ln"]["preference_signals"]

        self.assertEqual(evaluation["yong"], preference["喜用神"])
        self.assertEqual(evaluation["ji"], preference["忌神"])
        self.assertEqual(signals["ruleset_version"], preference["ruleset_version"])
        self.assertEqual(signals["preference"]["喜用神"], preference["喜用神"])
        self.assertTrue(signals["favorable"] or signals["adverse"])
        for signal in signals["favorable"] + signals["adverse"]:
            self.assertIn(signal["source"], ("流年天干", "流年地支"))
            self.assertIn(
                signal["code"],
                {
                    "direct_yong",
                    "direct_xi",
                    "supports_yong",
                    "supports_xi",
                    "direct_ji",
                    "supports_ji",
                },
            )

    def test_hybrid_outputs_share_the_same_canonical_preference(self):
        result = json.loads(HybridMingliToolkit().analyze_question(
            1990,
            6,
            15,
            12,
            "女",
            "事业",
            "分析2026年的事业结构",
            "[]",
        ))
        assessment = result["strength_assessment"]

        for source in (
            result["bazi"],
            result["liunian"],
            result["wealth_analysis"],
            result["career_analysis"],
        ):
            self.assertEqual(source["喜用神"], assessment["喜用神"])
        self.assertEqual(
            result["bazi"]["喜用神规则版本"],
            assessment["preference_ruleset_version"],
        )
        self.assertEqual(result["career_analysis"]["解释状态"], "degraded")
        self.assertEqual(result["career_analysis"]["格局倾向"], "待定")
        self.assertIn("喜忌信号", result["liunian"]["年份流年对比"][0])


if __name__ == "__main__":
    unittest.main()
