import json
import unittest

from tools import HybridMingliToolkit


class ZiweiReportAndInterpretationTests(unittest.TestCase):
    def setUp(self):
        self.toolkit = HybridMingliToolkit()

    def _analysis(self, **kwargs):
        return json.loads(self.toolkit.analyze_question(
            1990,
            6,
            15,
            12,
            "女",
            "事业",
            "分析未来十年事业",
            "[]",
            **kwargs,
        ))

    def test_hybrid_exposes_audited_ziwei_chart_with_shared_chart_id(self):
        result = self._analysis()

        self.assertEqual(result["ziwei_raw"]["chart_id"], result["chart_id"])
        self.assertEqual(len(result["ziwei_raw"]["十二宫"]), 12)
        self.assertEqual(len(result["ziwei_raw"]["生年四化"]), 4)
        self.assertEqual(
            result["component_status"]["ziwei"]["zi_hour_convention"],
            "benchmark",
        )

    def test_interpretation_document_requires_current_evidence(self):
        base = self._analysis()
        document = {
            "schema_version": "interpretation-v1",
            "chart_id": base["chart_id"],
            "sections": [{
                "id": "career",
                "title": "事业节奏",
                "body": "该段文本只作为传统文化解释，不替代现实决策。",
                "evidence_ids": [
                    "career_analysis",
                    "ziwei.palaces",
                ],
                "uncertainty": "仍需结合行业、岗位和实际业绩验证。",
            }],
        }

        result = self._analysis(interpretation_document=document)

        self.assertEqual(result["interpretation"]["status"], "ok")
        self.assertEqual(
            result["component_status"]["interpretation"]["code"],
            "validated",
        )
        self.assertEqual(
            result["interpretation"]["document"]["sections"][0]["evidence_ids"],
            ["career_analysis", "ziwei.palaces"],
        )

    def test_invalid_interpretation_document_is_visible_without_dropping_chart(self):
        result = self._analysis(interpretation_document={
            "schema_version": "interpretation-v1",
            "chart_id": "another-chart",
            "sections": [],
        })

        self.assertEqual(
            result["component_status"]["interpretation"]["status"],
            "error",
        )
        self.assertEqual(
            result["interpretation"]["code"],
            "interpretation_chart_id_mismatch",
        )
        self.assertIn("ziwei_raw", result)

    def test_html_report_renders_board_and_escapes_interpretation_text(self):
        base = self._analysis()
        document = {
            "schema_version": "interpretation-v1",
            "chart_id": base["chart_id"],
            "sections": [{
                "id": "career",
                "title": "事业",
                "body": "<script>alert('unsafe')</script>",
                "evidence_ids": ["career_analysis"],
                "uncertainty": "需要现实信息验证。",
            }],
        }
        report = json.loads(self.toolkit.generate_html_report(
            1990,
            6,
            15,
            12,
            "女",
            "事业",
            "分析未来十年事业",
            interpretation_document=document,
        ))

        self.assertTrue(report["success"])
        self.assertIn("class=\"ziwei-board\"", report["html"])
        self.assertIn("紫微十二宫", report["html"])
        self.assertIn("&lt;script&gt;alert(&#x27;unsafe&#x27;)&lt;/script&gt;", report["html"])
        self.assertNotIn("<script>alert('unsafe')</script>", report["html"])


if __name__ == "__main__":
    unittest.main()
