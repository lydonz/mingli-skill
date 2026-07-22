import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest import mock

from tools import HybridMingliToolkit, KnowledgeToolkit
from tools.knowledge_tools import (
    search_local_knowledge,
    validate_pack,
)


PACK_ID = "bazi-ziwei-mingli-cn"
SOURCE_REVISION = "f086546f9d4ab0e6fd00f8c37364269241249115"


class KnowledgePackTests(unittest.TestCase):
    def test_bundled_pack_is_versioned_and_integrity_checked(self):
        result = validate_pack(PACK_ID)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["pack_id"], PACK_ID)
        self.assertEqual(result["source"]["revision"], SOURCE_REVISION)
        self.assertEqual(result["source"]["license"], "MIT")
        self.assertTrue(
            any(item["path"] == "core/methodology.md" for item in result["files"])
        )

    def test_hash_mismatch_is_a_visible_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack_root = root / "test-pack"
            pack_root.mkdir()
            (pack_root / "document.md").write_text(
                "# Test\n\n本地文档。\n",
                encoding="utf-8",
            )
            license_text = "MIT License\n"
            (pack_root / "LICENSE").write_text(license_text, encoding="utf-8")
            manifest = {
                "schema_version": "knowledge-pack-v1",
                "id": "test-pack",
                "version": "test",
                "source": {
                    "repository": "https://example.invalid/test",
                    "revision": "fixed-revision",
                    "license": "MIT",
                },
                "files": [
                    {
                        "path": "LICENSE",
                        "sha256": hashlib.sha256(
                            license_text.encode("utf-8")
                        ).hexdigest(),
                        "role": "license",
                    },
                    {
                        "path": "document.md",
                        "sha256": "0" * 64,
                        "role": "methodology",
                    },
                ],
            }
            (pack_root / "manifest.json").write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )

            result = validate_pack("test-pack", root)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "knowledge_file_hash_mismatch")
        self.assertEqual(result["file"], "document.md")

    def test_search_returns_line_level_local_methodology_citation(self):
        result = search_local_knowledge(
            "大运流年的传统分析顺序",
            pack_ids=[PACK_ID],
            limit=2,
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["code"], "knowledge_references_found")
        self.assertTrue(result["references"])
        reference = result["references"][0]
        self.assertEqual(reference["pack_id"], PACK_ID)
        self.assertEqual(reference["source"]["revision"], SOURCE_REVISION)
        self.assertGreater(reference["line_start"], 0)
        self.assertGreaterEqual(reference["line_end"], reference["line_start"])
        self.assertTrue(reference["excerpt"])
        self.assertEqual(
            reference["use"], "methodology_and_cultural_context_only"
        )

    def test_search_without_match_is_not_silently_successful_reference(self):
        result = search_local_knowledge(
            "qzv-unique-token-77",
            pack_ids=[PACK_ID],
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["code"], "no_matching_knowledge_reference")
        self.assertEqual(result["references"], [])

    def test_missing_requested_pack_is_visible_in_component_result(self):
        result = search_local_knowledge(
            "大运流年",
            pack_ids=["missing-pack"],
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "knowledge_pack_unavailable")
        self.assertEqual(
            result["pack_statuses"][0]["code"],
            "knowledge_manifest_missing",
        )

    def test_search_is_local_even_if_network_connections_are_unavailable(self):
        with mock.patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("network must not be used"),
        ):
            result = search_local_knowledge(
                "紫微斗数十二宫",
                pack_ids=[PACK_ID],
                limit=1,
            )

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["references"])

    def test_public_toolkit_exposes_local_pack_search(self):
        result = json.loads(KnowledgeToolkit().search(
            "八字方法论",
            pack_ids=[PACK_ID],
            limit=1,
        ))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["references"][0]["pack_id"], PACK_ID)


class HybridKnowledgeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.toolkit = HybridMingliToolkit()

    def _analyze(self, **kwargs):
        return json.loads(self.toolkit.analyze_question(
            1990,
            6,
            15,
            12,
            "女",
            "事业",
            "分析未来十年大运与事业",
            "[]",
            **kwargs,
        ))

    def test_legacy_call_does_not_search_or_add_knowledge_references(self):
        result = self._analyze()

        self.assertNotIn("knowledge_references", result)
        self.assertEqual(
            result["component_status"]["knowledge"]["code"],
            "not_requested",
        )

    def test_explicit_knowledge_search_returns_auditable_references(self):
        result = self._analyze(
            knowledge_query="大运流年的传统分析顺序",
            knowledge_packs=[PACK_ID],
        )

        self.assertEqual(
            result["component_status"]["knowledge"]["status"],
            "ok",
        )
        self.assertEqual(
            result["component_status"]["knowledge"]["code"],
            "knowledge_references_found",
        )
        self.assertTrue(result["knowledge_references"])
        self.assertIn(
            "不构成对未来事件或现实结果的预测证据",
            result["knowledge_context"]["notice"],
        )

    def test_html_report_includes_requested_knowledge_citations(self):
        report = json.loads(self.toolkit.generate_html_report(
            1990,
            6,
            15,
            12,
            "女",
            "事业",
            "分析未来十年大运与事业",
            knowledge_query="大运流年的传统分析顺序",
            knowledge_packs=[PACK_ID],
        ))

        self.assertTrue(report["success"])
        self.assertIn("本地知识参考", report["html"])
        self.assertIn("core/methodology.md", report["html"])
        self.assertIn(SOURCE_REVISION, report["html"])


if __name__ == "__main__":
    unittest.main()
