import json
import unittest

from engine.run_tools_engine import compute_chart, eval_year
from tools import BaziToolkit, HybridMingliToolkit, ZiweiToolkit
from tools.birth_context import BirthContextError, normalize_birth_context
from tools.liunian_analyzer import integrate_year_analysis


class TimeBoundaryConsistencyTests(unittest.TestCase):
    def test_calendar_terms_use_one_backend_timescale_for_international_births(self):
        chart = compute_chart({
            "year": 2024,
            "month": 2,
            "day": 4,
            "hour": 9,
            "gender": "男",
            "birth_context": {
                "time_basis": "standard",
                "place": {
                    "name": "London",
                    "longitude": -0.1276,
                    "latitude": 51.5072,
                    "timezone": "Europe/London",
                },
            },
        })

        self.assertEqual(
            chart["birth_time"]["calendar_time"],
            "2024-02-04T17:00:00",
        )
        self.assertEqual(chart["四柱"]["年柱"], "甲辰")
        self.assertEqual(chart["四柱"]["月柱"], "丙寅")

    def test_standard_timezone_does_not_require_a_place_record(self):
        chart = compute_chart({
            "year": 2024,
            "month": 2,
            "day": 4,
            "hour": 9,
            "gender": "男",
            "birth_context": {
                "time_basis": "standard",
                "timezone": "Europe/London",
            },
        })

        self.assertEqual(chart["birth_time"]["time_basis"], "standard")
        self.assertEqual(chart["birth_time"]["timezone"], "Europe/London")
        self.assertIsNone(chart["birth_time"]["place"])

    def test_future_period_boundaries_use_birth_timezone(self):
        result = json.loads(HybridMingliToolkit().analyze_question(
            1990,
            6,
            15,
            12,
            "女",
            "事业",
            "2026年事业",
            "[]",
            birth_context={
                "time_basis": "standard",
                "place": {
                    "name": "New York",
                    "country_code": "US",
                },
            },
            analysis_period={
                "start": "2026-02-03",
                "end": "2026-02-05",
                "granularity": "day",
            },
        ))

        self.assertEqual(result["liunian"]["period_timezone"], "America/New_York")
        self.assertTrue(
            result["liunian"]["civil_to_bazi_year_segments"][0]["end"].startswith(
                "2026-02-03T15:02:"
            )
        )

    def test_lunar_new_year_boundary_is_used_by_chart_dayun_and_flow_periods(self):
        birth = {
            "year": 1988,
            "month": 2,
            "day": 15,
            "hour": 16,
            "minute": 50,
            "gender": "女",
            "year_boundary": "lunar_new_year",
        }
        chart = compute_chart(birth)
        flow = json.loads(integrate_year_analysis(
            birth,
            chart,
            "",
            "[]",
            {
                "start": "1988-02-05",
                "end": "1988-02-16",
                "granularity": "month",
            },
        ))

        self.assertEqual(chart["四柱"]["年柱"], "丁卯")
        self.assertEqual(flow["year_boundary"], "lunar_new_year")
        self.assertEqual(flow["civil_to_bazi_year_segments"][0]["流年干支"], "丁卯")
        self.assertEqual(flow["流月分段"][0]["流年干支"], "丁卯")
        self.assertEqual(eval_year(chart, 1988, 2, 15)["ln"]["ganzhi"], "丁卯")
        self.assertEqual(chart["大运"][0]["年界规则"], "农历新年")

    def test_uncertainty_enumerates_each_distinct_hour_pillar(self):
        chart = compute_chart({
            "year": 1990,
            "month": 6,
            "day": 15,
            "hour": 12,
            "gender": "女",
            "birth_context": {
                "time_basis": "standard",
                "uncertainty_minutes": 240,
                "place": {
                    "name": "Beijing",
                    "longitude": 116.39723,
                    "latitude": 39.9075,
                    "timezone": "Asia/Shanghai",
                },
            },
        })
        candidates = chart["birth_time"]["chart_stability"]["candidate_charts"]

        self.assertFalse(chart["birth_time"]["chart_stability"]["stable"])
        self.assertEqual(
            {item["四柱"]["时柱"] for item in candidates},
            {"壬辰", "癸巳", "甲午", "乙未", "丙申"},
        )
        self.assertTrue(all(item["chart_id"] for item in candidates))
        self.assertTrue(all("changed_fields" in item for item in candidates))

    def test_uncertainty_includes_ziwei_changes_when_bazi_is_stable(self):
        chart = compute_chart({
            "year": 2000,
            "month": 1,
            "day": 1,
            "hour": 23,
            "minute": 50,
            "gender": "男",
            "birth_context": {
                "time_basis": "standard",
                "timezone": "Asia/Shanghai",
                "uncertainty_minutes": 20,
            },
        })

        stability = chart["birth_time"]["chart_stability"]
        self.assertFalse(stability["stable"])
        self.assertTrue(
            any("紫微" in item["changed_fields"] for item in stability["candidate_charts"])
        )

    def test_invalid_gender_is_visible_error(self):
        with self.assertRaises(BirthContextError) as error:
            compute_chart({
                "year": 1990,
                "month": 6,
                "day": 15,
                "hour": 12,
                "gender": "未知",
            })
        self.assertEqual(error.exception.code, "invalid_gender")

    def test_public_bazi_and_ziwei_entrypoints_share_the_computed_chart(self):
        context = {"place": {"name": "Guangzhou", "country_code": "CN"}}
        hybrid = json.loads(HybridMingliToolkit().analyze_question(
            1990,
            6,
            15,
            23,
            "女",
            "事业",
            "",
            "[]",
            minute=3,
            birth_context=context,
        ))
        bazi = json.loads(BaziToolkit().paipan(
            1990,
            6,
            15,
            23,
            "女",
            minute=3,
            birth_context=context,
        ))
        ziwei = json.loads(ZiweiToolkit().paipan(
            1990,
            6,
            15,
            23,
            "女",
            minute=3,
            birth_context=context,
        ))

        self.assertEqual(bazi["data"]["四柱"], hybrid["bazi"]["四柱"])
        self.assertEqual(bazi["data"]["chart_id"], hybrid["chart_id"])
        self.assertEqual(ziwei["chart_id"], hybrid["chart_id"])
        self.assertEqual(
            ziwei["birth_time"]["effective_time"],
            hybrid["birth_time"]["effective_time"],
        )
        career = json.loads(BaziToolkit().analyze_career(
            1990,
            6,
            15,
            23,
            "女",
            minute=3,
            birth_context=context,
        ))
        self.assertEqual(career["chart_id"], hybrid["chart_id"])

    def test_flow_month_by_date_uses_computed_chart_time_context(self):
        context = {
            "time_basis": "standard",
            "place": {
                "name": "London",
                "longitude": -0.1276,
                "latitude": 51.5072,
                "timezone": "Europe/London",
            },
        }
        result = json.loads(BaziToolkit().analyze_liuyue_by_date(
            2024,
            2,
            4,
            9,
            year_boundary="lichun",
            birth_context=context,
        ))

        self.assertTrue(result["success"])
        self.assertEqual(result["流年干支"], "甲辰")
        self.assertEqual(result["流月干支"], "丙寅")
        self.assertEqual(
            result["birth_time"]["calendar_time"],
            "2024-02-04T17:00:00",
        )
        self.assertEqual(
            result["component_status"]["backend"],
            "shared-computed-chart",
        )

    def test_invalid_coordinates_and_dst_gap_are_visible_errors(self):
        with self.assertRaises(BirthContextError) as coordinates_error:
            normalize_birth_context(
                {"year": 2024, "month": 1, "day": 1, "hour": 12},
                {
                    "place": {
                        "longitude": 999,
                        "latitude": 1,
                        "timezone": "UTC",
                    },
                },
            )
        self.assertEqual(coordinates_error.exception.code, "invalid_coordinates")

        with self.assertRaises(BirthContextError) as dst_error:
            normalize_birth_context(
                {"year": 2024, "month": 3, "day": 31, "hour": 1, "minute": 30},
                {
                    "place": {
                        "name": "London",
                        "longitude": -0.1276,
                        "latitude": 51.5072,
                        "timezone": "Europe/London",
                    },
                },
            )
        self.assertEqual(dst_error.exception.code, "nonexistent_local_time")


if __name__ == "__main__":
    unittest.main()
