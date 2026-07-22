"""Validation for optional, evidence-linked interpretation text.

The calendar and chart layers intentionally do not generate prose conclusions.
This contract lets a caller attach human- or model-written text to a completed
chart while preserving its chart identifier, evidence references, and limits.
"""
from __future__ import annotations

import re
from typing import Any, Mapping


INTERPRETATION_SCHEMA_VERSION = "interpretation-v1"
_SECTION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,47}$")
_MAX_SECTIONS = 8
_MAX_TITLE_LENGTH = 100
_MAX_BODY_LENGTH = 4000
_MAX_UNCERTAINTY_LENGTH = 600


def _is_present(value: Any) -> bool:
    return value not in (None, "", [], {})


def build_interpretation_brief(analysis: Mapping[str, Any]) -> dict:
    """Return the evidence IDs a separate interpretation may reference."""
    bazi = analysis.get("bazi", {})
    ziwei = analysis.get("ziwei_raw", {})
    candidates = {
        "bazi.four_pillars": bazi.get("四柱") if isinstance(bazi, Mapping) else None,
        "bazi.dayun": bazi.get("大运") if isinstance(bazi, Mapping) else None,
        "strength_assessment": analysis.get("strength_assessment"),
        "career_analysis": analysis.get("career_analysis"),
        "wealth_analysis": analysis.get("wealth_analysis"),
        "marriage_analysis": analysis.get("marriage_analysis"),
        "health_analysis": analysis.get("health_analysis"),
        "liunian": analysis.get("liunian"),
        "ziwei.palaces": ziwei.get("十二宫") if isinstance(ziwei, Mapping) else None,
        "ziwei.year_mutagens": (
            ziwei.get("生年四化") if isinstance(ziwei, Mapping) else None
        ),
        "knowledge_references": analysis.get("knowledge_references"),
    }
    evidence_ids = [
        evidence_id
        for evidence_id, value in candidates.items()
        if _is_present(value)
    ]
    return {
        "schema_version": INTERPRETATION_SCHEMA_VERSION,
        "chart_id": analysis.get("chart_id"),
        "allowed_evidence_ids": evidence_ids,
        "required_section_fields": (
            "id、title、body、evidence_ids、uncertainty"
        ),
        "constraints": [
            "每段必须至少关联一项已提供的 evidence_ids。",
            "body 是未经验证的解释文本，不得改写排盘、历法或 chart_id。",
            "uncertainty 必须说明仍需现实信息验证的部分。",
            "不得将解释文本表述为未来事件、健康、财富或职业结果的确定预测。",
        ],
    }


def _error(code: str, message: str, **extra: Any) -> dict:
    return {
        "status": "error",
        "code": code,
        "message": message,
        **extra,
    }


def validate_interpretation_document(
    document: Any,
    brief: Mapping[str, Any],
) -> dict:
    """Validate an interpretation document without evaluating its claims."""
    if not isinstance(document, Mapping):
        return _error(
            "interpretation_document_invalid",
            "interpretation_document 必须是对象。",
        )
    if document.get("schema_version") != INTERPRETATION_SCHEMA_VERSION:
        return _error(
            "interpretation_schema_unsupported",
            "interpretation_document 的 schema_version 不受支持。",
        )
    chart_id = brief.get("chart_id")
    if not chart_id or document.get("chart_id") != chart_id:
        return _error(
            "interpretation_chart_id_mismatch",
            "interpretation_document.chart_id 必须匹配当前命盘。",
        )

    sections = document.get("sections")
    if not isinstance(sections, list) or not sections:
        return _error(
            "interpretation_sections_missing",
            "interpretation_document.sections 必须是非空列表。",
        )
    if len(sections) > _MAX_SECTIONS:
        return _error(
            "interpretation_sections_too_many",
            f"解释段落不得超过 {_MAX_SECTIONS} 段。",
        )

    allowed_evidence = set(brief.get("allowed_evidence_ids", []))
    normalized_sections = []
    used_ids = set()
    for index, section in enumerate(sections):
        if not isinstance(section, Mapping):
            return _error(
                "interpretation_section_invalid",
                f"第 {index + 1} 段必须是对象。",
            )
        section_id = section.get("id")
        title = section.get("title")
        body = section.get("body")
        uncertainty = section.get("uncertainty")
        evidence_ids = section.get("evidence_ids")
        if (
            not isinstance(section_id, str)
            or not _SECTION_ID_RE.fullmatch(section_id)
            or section_id in used_ids
        ):
            return _error(
                "interpretation_section_id_invalid",
                f"第 {index + 1} 段 id 无效或重复。",
            )
        if not isinstance(title, str) or not 1 <= len(title) <= _MAX_TITLE_LENGTH:
            return _error(
                "interpretation_title_invalid",
                f"第 {index + 1} 段 title 必须是 1 至 {_MAX_TITLE_LENGTH} 个字符。",
            )
        if not isinstance(body, str) or not 1 <= len(body) <= _MAX_BODY_LENGTH:
            return _error(
                "interpretation_body_invalid",
                f"第 {index + 1} 段 body 必须是 1 至 {_MAX_BODY_LENGTH} 个字符。",
            )
        if (
            not isinstance(uncertainty, str)
            or not 1 <= len(uncertainty) <= _MAX_UNCERTAINTY_LENGTH
        ):
            return _error(
                "interpretation_uncertainty_missing",
                f"第 {index + 1} 段必须提供不超过 {_MAX_UNCERTAINTY_LENGTH} 个字符的 uncertainty。",
            )
        if (
            not isinstance(evidence_ids, list)
            or not evidence_ids
            or not all(
                isinstance(evidence_id, str)
                and evidence_id in allowed_evidence
                for evidence_id in evidence_ids
            )
        ):
            return _error(
                "interpretation_evidence_invalid",
                f"第 {index + 1} 段必须引用当前命盘允许的 evidence_ids。",
                allowed_evidence_ids=sorted(allowed_evidence),
            )
        used_ids.add(section_id)
        normalized_sections.append({
            "id": section_id,
            "title": title,
            "body": body,
            "evidence_ids": list(dict.fromkeys(evidence_ids)),
            "uncertainty": uncertainty,
        })

    return {
        "status": "ok",
        "schema_version": INTERPRETATION_SCHEMA_VERSION,
        "document": {
            "schema_version": INTERPRETATION_SCHEMA_VERSION,
            "chart_id": chart_id,
            "sections": normalized_sections,
        },
        "notice": (
            "解释文本与命盘计算分离；它仅引用已提供的结构化证据，"
            "不构成对现实结果或未来事件的确定预测。"
        ),
    }
