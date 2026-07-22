"""Local, versioned knowledge-pack discovery and citation retrieval.

Knowledge packs are intentionally independent from calendar calculations and
rules-engine conclusions.  They are local files only: this module performs no
network access and never receives or transmits birth data beyond the caller.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from tools.toolkit_base import Toolkit


KNOWLEDGE_PACK_SCHEMA = "knowledge-pack-v1"
PACKS_ROOT = Path(__file__).resolve().parents[1] / "knowledge_packs"
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_WORD_RE = re.compile(r"[a-zA-Z0-9_+-]{2,}")
_CJK_RE = re.compile(r"[\u3400-\u9fff]+")
_QUERY_STOP_WORDS = {
    "分析", "请问", "这个", "那个", "如何", "什么", "关于", "以及", "还有",
    "一下", "一个", "我们", "你们", "可以", "需要", "是否", "怎样", "怎么",
}


def _safe_relative_path(value: Any) -> Path | None:
    """Return a pack-relative path or reject traversal and absolute paths."""
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path


def _pack_root_for(pack_id: str, packs_root: Path | str | None) -> Path:
    root = Path(packs_root) if packs_root is not None else PACKS_ROOT
    return root / pack_id


def _error(pack_id: str, code: str, message: str, **extra: Any) -> dict:
    return {
        "status": "error",
        "pack_id": pack_id,
        "code": code,
        "message": message,
        **extra,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_pack(
    pack_id: str,
    packs_root: Path | str | None = None,
) -> dict:
    """Validate a local pack manifest and every manifest-listed file hash.

    The returned status is structured so callers can display corrupt or absent
    packs instead of silently searching unverified documentation.
    """
    if not isinstance(pack_id, str) or not pack_id:
        return _error("", "invalid_pack_id", "知识包标识必须是非空字符串。")
    if "/" in pack_id or "\\" in pack_id or pack_id in {".", ".."}:
        return _error(pack_id, "invalid_pack_id", "知识包标识不能包含路径分隔符。")

    pack_root = _pack_root_for(pack_id, packs_root)
    manifest_path = pack_root / "manifest.json"
    if not manifest_path.is_file():
        return _error(
            pack_id,
            "knowledge_manifest_missing",
            "未找到知识包 manifest.json。",
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _error(
            pack_id,
            "knowledge_manifest_invalid",
            f"无法读取知识包清单：{exc}",
        )

    if not isinstance(manifest, dict):
        return _error(
            pack_id,
            "knowledge_manifest_invalid",
            "知识包清单必须是 JSON 对象。",
        )
    if manifest.get("schema_version") != KNOWLEDGE_PACK_SCHEMA:
        return _error(
            pack_id,
            "knowledge_schema_unsupported",
            f"不支持的知识包清单版本：{manifest.get('schema_version')!r}。",
        )
    if manifest.get("id") != pack_id:
        return _error(
            pack_id,
            "knowledge_pack_id_mismatch",
            "清单中的 id 与目录名称不一致。",
        )
    if not isinstance(manifest.get("version"), str) or not manifest["version"]:
        return _error(
            pack_id,
            "knowledge_version_missing",
            "知识包清单缺少可追溯版本。",
        )

    source = manifest.get("source")
    if not isinstance(source, dict) or not all(
        isinstance(source.get(key), str) and source[key]
        for key in ("repository", "revision", "license")
    ):
        return _error(
            pack_id,
            "knowledge_source_missing",
            "知识包清单缺少来源仓库、固定版本或许可证。",
        )

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return _error(
            pack_id,
            "knowledge_file_list_missing",
            "知识包清单未声明要校验的文件。",
        )

    checked_files = []
    seen_paths = set()
    has_license_file = False
    for entry in files:
        if not isinstance(entry, dict):
            return _error(
                pack_id,
                "knowledge_file_entry_invalid",
                "知识包文件清单包含非对象条目。",
            )
        relative_path = _safe_relative_path(entry.get("path"))
        expected_hash = entry.get("sha256")
        if (
            relative_path is None
            or not isinstance(expected_hash, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_hash)
        ):
            return _error(
                pack_id,
                "knowledge_file_entry_invalid",
                "知识包文件条目必须包含安全路径和 SHA-256。",
            )
        relative_text = relative_path.as_posix()
        if relative_text in seen_paths:
            return _error(
                pack_id,
                "knowledge_file_entry_duplicate",
                f"知识包文件清单重复声明：{relative_text}。",
            )
        seen_paths.add(relative_text)

        file_path = pack_root / relative_path
        try:
            file_path.resolve().relative_to(pack_root.resolve())
        except ValueError:
            return _error(
                pack_id,
                "knowledge_file_path_unsafe",
                f"知识包文件路径越出包目录：{relative_text}。",
            )
        if not file_path.is_file():
            return _error(
                pack_id,
                "knowledge_file_missing",
                f"知识包文件不存在：{relative_text}。",
            )

        actual_hash = _sha256(file_path)
        if actual_hash != expected_hash:
            return _error(
                pack_id,
                "knowledge_file_hash_mismatch",
                f"知识包文件校验失败：{relative_text}。",
                file=relative_text,
                expected_sha256=expected_hash,
                actual_sha256=actual_hash,
            )
        checked_files.append({
            "path": relative_text,
            "role": entry.get("role", "reference"),
        })
        if entry.get("role") == "license":
            has_license_file = True

    if not has_license_file:
        return _error(
            pack_id,
            "knowledge_license_file_missing",
            "知识包清单必须包含经过校验的许可证文件。",
        )

    return {
        "status": "ok",
        "pack_id": pack_id,
        "version": manifest.get("version", ""),
        "title": manifest.get("title", pack_id),
        "source": source,
        "files": checked_files,
        "allowed_uses": manifest.get("allowed_uses", []),
        "prohibited_uses": manifest.get("prohibited_uses", []),
    }


def discover_packs(packs_root: Path | str | None = None) -> list[dict]:
    """Return validation metadata for every local knowledge-pack directory."""
    root = Path(packs_root) if packs_root is not None else PACKS_ROOT
    if not root.is_dir():
        return []
    return [
        validate_pack(path.name, root)
        for path in sorted(root.iterdir(), key=lambda item: item.name)
        if path.is_dir()
    ]


def _query_terms(query: str) -> list[str]:
    """Extract deterministic matching terms without a remote tokenizer."""
    normalized = query.strip().lower()
    terms = set(_WORD_RE.findall(normalized))
    for run in _CJK_RE.findall(normalized):
        if 2 <= len(run) <= 12 and run not in _QUERY_STOP_WORDS:
            terms.add(run)
        for width in (2, 3, 4):
            for index in range(max(0, len(run) - width + 1)):
                term = run[index:index + width]
                if term not in _QUERY_STOP_WORDS:
                    terms.add(term)
    return sorted(terms, key=lambda item: (-len(item), item))


def _markdown_sections(path: Path) -> list[dict]:
    """Split Markdown into heading-scoped, line-addressable search sections."""
    lines = path.read_text(encoding="utf-8").splitlines()
    headings = []
    for index, line in enumerate(lines, start=1):
        match = _HEADING_RE.match(line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2)))

    if not headings:
        return [{
            "section": path.stem,
            "line_start": 1,
            "line_end": len(lines),
            "text": "\n".join(lines),
        }]

    sections = []
    for heading_index, (start, level, heading) in enumerate(headings):
        end = len(lines)
        for next_start, next_level, _ in headings[heading_index + 1:]:
            if next_level <= level:
                end = next_start - 1
                break
        sections.append({
            "section": heading,
            "line_start": start,
            "line_end": end,
            "text": "\n".join(lines[start - 1:end]),
        })
    return sections


def _score_section(query: str, terms: list[str], section: dict) -> int:
    text = section["text"].lower()
    heading = section["section"].lower()
    score = 0
    normalized_query = query.strip().lower()
    if normalized_query and normalized_query in text:
        score += 30 + min(len(normalized_query), 20)
    for term in terms:
        text_count = min(text.count(term), 3)
        if not text_count:
            continue
        score += text_count * min(len(term), 8)
        if term in heading:
            score += 12 + min(len(term), 8)
    return score


def _excerpt(section: dict, maximum_length: int = 360) -> str:
    """Produce a compact, line-preserving local quote for a citation."""
    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in section["text"].splitlines()
        if line.strip() and not line.startswith("```")
    ]
    text = " ".join(lines)
    if len(text) <= maximum_length:
        return text
    return f"{text[:maximum_length - 1].rstrip()}…"


def _citation(
    validation: dict,
    relative_path: str,
    section: dict,
    score: int,
) -> dict:
    return {
        "pack_id": validation["pack_id"],
        "pack_version": validation["version"],
        "source": validation["source"],
        "file": relative_path,
        "section": section["section"],
        "line_start": section["line_start"],
        "line_end": section["line_end"],
        "excerpt": _excerpt(section),
        "score": score,
        "use": "methodology_and_cultural_context_only",
    }


def search_local_knowledge(
    query: str,
    pack_ids: list[str] | None = None,
    limit: int = 3,
    packs_root: Path | str | None = None,
) -> dict:
    """Search validated local Markdown packs and return cited references.

    Search is deliberately lexical and deterministic.  It does not call a
    hosted embedding model, make network requests, or turn documentation into
    a rules-engine conclusion.
    """
    if not isinstance(query, str) or not query.strip():
        return {
            "status": "degraded",
            "code": "empty_knowledge_query",
            "message": "知识库检索需要非空查询文本。",
            "query": query if isinstance(query, str) else "",
            "references": [],
            "pack_statuses": [],
        }
    if not isinstance(limit, int) or limit < 1:
        return {
            "status": "degraded",
            "code": "invalid_knowledge_limit",
            "message": "知识库检索条数必须是大于零的整数。",
            "query": query,
            "references": [],
            "pack_statuses": [],
        }

    root = Path(packs_root) if packs_root is not None else PACKS_ROOT
    selected_ids = pack_ids
    if selected_ids is None:
        selected_ids = [
            path.name for path in sorted(root.iterdir(), key=lambda item: item.name)
            if path.is_dir()
        ] if root.is_dir() else []
    if not isinstance(selected_ids, list) or not all(
        isinstance(pack_id, str) for pack_id in selected_ids
    ):
        return {
            "status": "degraded",
            "code": "invalid_knowledge_packs",
            "message": "knowledge_packs 必须是知识包标识列表。",
            "query": query,
            "references": [],
            "pack_statuses": [],
        }
    selected_ids = list(dict.fromkeys(selected_ids))

    validations = [validate_pack(pack_id, root) for pack_id in selected_ids]
    valid_packs = [item for item in validations if item["status"] == "ok"]
    terms = _query_terms(query)
    candidates = []
    for validation in valid_packs:
        pack_root = _pack_root_for(validation["pack_id"], root)
        for file_entry in validation["files"]:
            relative_path = file_entry["path"]
            if not relative_path.endswith(".md"):
                continue
            for section in _markdown_sections(pack_root / relative_path):
                score = _score_section(query, terms, section)
                if score:
                    candidates.append(_citation(
                        validation, relative_path, section, score
                    ))

    candidates.sort(
        key=lambda item: (
            -item["score"],
            item["pack_id"],
            item["file"],
            item["line_start"],
        )
    )
    references = candidates[:limit]
    failed_packs = [item for item in validations if item["status"] != "ok"]
    if not valid_packs:
        status, code, message = (
            "error",
            "knowledge_pack_unavailable",
            "没有可通过完整性校验的本地知识包。",
        )
    elif failed_packs:
        status, code, message = (
            "degraded",
            "knowledge_pack_partially_unavailable",
            "部分本地知识包未通过完整性校验。",
        )
    elif references:
        status, code, message = (
            "ok",
            "knowledge_references_found",
            "已从本地、已校验的知识包返回参考资料。",
        )
    else:
        status, code, message = (
            "ok",
            "no_matching_knowledge_reference",
            "本地知识包中没有与该查询直接匹配的参考资料。",
        )

    return {
        "status": status,
        "code": code,
        "message": message,
        "query": query,
        "references": references,
        "pack_statuses": validations,
        "notice": (
            "引用仅用于传统命理的方法论与文化语境，"
            "不构成对未来事件或现实结果的预测证据。"
        ),
    }


class KnowledgeToolkit(Toolkit):
    """Public wrapper for inspecting and searching local knowledge packs."""

    def __init__(self):
        super().__init__(name="local_knowledge")

    def list_packs(self) -> str:
        """Return all installed packs together with integrity status."""
        packs = discover_packs()
        return json.dumps({
            "component_status": {
                "status": "ok",
                "backend": "local_knowledge",
                "network": "disabled",
            },
            "packs": packs,
        }, ensure_ascii=False)

    def search(
        self,
        query: str,
        pack_ids: list[str] | None = None,
        limit: int = 3,
    ) -> str:
        """Search local documentation and return versioned, line-level cites."""
        return json.dumps(
            search_local_knowledge(query, pack_ids=pack_ids, limit=limit),
            ensure_ascii=False,
        )
