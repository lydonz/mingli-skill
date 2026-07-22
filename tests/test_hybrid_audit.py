import json
from pathlib import Path
import tempfile
from unittest import mock
import unittest

from tools import HybridMingliToolkit


class HybridAuditTests(unittest.TestCase):
    def setUp(self):
        self.toolkit = HybridMingliToolkit()

    def _analyze(self, **kwargs):
        result = self.toolkit.analyze_question(
            1990, 6, 15, 12, "女", "事业", "分析示例年度", "[]", **kwargs
        )
        return json.loads(result)

    def test_legacy_call_keeps_standard_chart_and_marks_missing_location(self):
        result = self._analyze()
        self.assertEqual(
            result["bazi"]["四柱"],
            {"年柱": "庚午", "月柱": "壬午", "日柱": "辛亥", "时柱": "甲午"},
        )
        self.assertIn(
            "旧接口未提供出生地，按标准时间排盘，未应用真太阳时校正。",
            result["data_quality_warnings"],
        )
        self.assertEqual(result["birth_time"]["time_basis"], "standard")

    def test_derived_analyses_share_chart_id_and_canonical_strength(self):
        result = self._analyze(
            birth_context={"place": {"name": "Guangzhou", "country_code": "CN"}}
        )
        chart_id = result["chart_id"]
        self.assertEqual(result["wealth_analysis"]["chart_id"], chart_id)
        self.assertEqual(result["career_analysis"]["chart_id"], chart_id)
        self.assertEqual(
            result["strength_assessment"]["旺衰"],
            result["huoyuan_analysis"]["旺衰"],
        )
        self.assertIn(
            "strength_model_conflict",
            result["strength_assessment"]["conflicts"],
        )
        self.assertIn("抑制", result["wealth_analysis"]["财运提示"])

    def test_explicit_period_splits_at_lichun(self):
        result = self._analyze(
            birth_context={"place": {"name": "Guangzhou", "country_code": "CN"}},
            analysis_period={
                "start": "2026-01-31",
                "end": "2026-02-05",
                "granularity": "day",
            },
        )
        segments = result["liunian"]["civil_to_bazi_year_segments"]
        self.assertEqual(segments[0]["流年干支"], "乙巳")
        self.assertEqual(segments[1]["流年干支"], "丙午")
        self.assertEqual(
            result["liunian"]["年份流年对比"][0]["干支"], "乙巳"
        )

    def test_city_resolution_failure_is_visible(self):
        result = self._analyze(
            birth_context={"place": {"name": "not-a-real-place"}}
        )
        self.assertEqual(result["error"]["code"], "location_not_found")
        self.assertEqual(
            result["component_status"]["birth_context"]["status"], "error"
        )

    def test_ziwei_failure_is_visible_without_dropping_bazi_results(self):
        with mock.patch(
            "tools.tool_integration.get_ziwei_chart",
            side_effect=RuntimeError("bridge failed"),
        ):
            result = self._analyze()
        self.assertEqual(result["component_status"]["ziwei"]["status"], "error")
        self.assertEqual(result["component_status"]["bazi"]["status"], "ok")
        self.assertIn("wealth_analysis", result)

    def test_month_period_contains_solar_term_flow_month_segments(self):
        result = self._analyze(
            birth_context={"place": {"name": "Guangzhou", "country_code": "CN"}},
            analysis_period={
                "start": "2026-01-31",
                "end": "2026-02-10",
                "granularity": "month",
            },
        )
        segments = result["liunian"]["流月分段"]
        self.assertEqual(segments[0]["流月干支"], "己丑")
        self.assertEqual(segments[1]["流月干支"], "庚寅")
        self.assertEqual(segments[1]["边界"], "区间结束")

    def test_html_report_is_self_contained_and_written_only_on_request(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.html"
            result = json.loads(self.toolkit.generate_html_report(
                1990,
                6,
                15,
                12,
                "女",
                "事业",
                "分析示例年度",
                birth_context={
                    "place": {"name": "Guangzhou", "country_code": "CN"},
                },
                title="测试报告",
                subject_name="示例",
                output_path=str(output_path),
            ))
            self.assertTrue(result["success"])
            self.assertEqual(result["report_version"], "html-report-v2")
            self.assertTrue(result["html"].startswith("<!doctype html>"))
            self.assertNotIn("https://", result["html"])
            self.assertEqual(Path(result["output_path"]), output_path.resolve())
            self.assertEqual(output_path.read_text(encoding="utf-8"), result["html"])


if __name__ == "__main__":
    unittest.main()
