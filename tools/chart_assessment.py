"""Canonical, versioned chart assessments shared by all analysis modules."""
from __future__ import annotations

from typing import Any, Dict

from .calendar_engine import (
    WUXING_BEING_KE,
    WUXING_BEING_SHENG,
    WUXING_KE,
    WUXING_SHENG,
    WUXING_ZHI,
)


STRENGTH_RULESET_VERSION = "seasonal-strength-v2"
PREFERENCE_RULESET_VERSION = "element-balance-v1"
STRONG_DAY_ELEMENT_SHARE = 0.35
WEAK_DAY_ELEMENT_SHARE = 0.20


def _derive_preference(
    day_element: str,
    strength_label: str,
) -> Dict[str, str]:
    """Derive preference fields from the same strength rule used downstream.

    The legacy chart builder used a separate 20% element-share threshold and
    could produce a ``喜用神`` that contradicted the seasonal assessment. This
    small, explicit balance rule prevents the three preference fields from
    overlapping while keeping the old values available for compatibility.
    """
    if strength_label in ("身旺", "中和偏旺"):
        return {
            "喜用神": WUXING_KE[day_element],
            "喜神": WUXING_BEING_KE[day_element],
            "忌神": day_element,
            "balance_direction": "drain_and_control",
        }
    return {
        "喜用神": WUXING_BEING_SHENG[day_element],
        "喜神": day_element,
        "忌神": WUXING_SHENG[day_element],
        "balance_direction": "support_and_consolidate",
    }


def build_strength_assessment(chart: Dict[str, Any]) -> Dict[str, Any]:
    """Build the one seasonal strength assessment used by derived analyses.

    This intentionally keeps the historical 20% threshold available as
    ``legacy_strength`` on the chart, but does not use that threshold for new
    interpretation templates.
    """
    day_element = chart["日主五行"]
    element_scores = chart["五行力量"]
    total = sum(element_scores.values()) or 1
    ratio = element_scores.get(day_element, 0) / total
    month_pillar = chart["四柱"]["月柱"]
    month_element = WUXING_ZHI[month_pillar[1]]
    in_season = (
        month_element == day_element
        or WUXING_SHENG.get(month_element) == day_element
    )

    if ratio > STRONG_DAY_ELEMENT_SHARE and in_season:
        label = "身旺"
        pattern = "身旺格"
    elif ratio < WEAK_DAY_ELEMENT_SHARE:
        label = "身弱"
        pattern = "身弱格"
    elif in_season:
        label = "中和偏旺"
        pattern = "中和格"
    else:
        label = "中和偏弱"
        pattern = "中和格"

    preference = _derive_preference(day_element, label)
    legacy_label = chart.get("日主强弱", "")
    legacy_preference = {
        "喜用神": chart.get("喜用神", ""),
        "喜神": chart.get("喜神", ""),
        "忌神": chart.get("忌神", ""),
    }
    legacy_bucket = "身旺" if legacy_label == "身强" else "身弱"
    canonical_bucket = "身旺" if label in ("身旺", "中和偏旺") else "身弱"
    conflicts = []
    if legacy_label and legacy_bucket != canonical_bucket:
        conflicts.append("strength_model_conflict")
    if any(
        legacy_preference[key]
        and legacy_preference[key] != preference[key]
        for key in ("喜用神", "喜神", "忌神")
    ):
        conflicts.append("preference_model_conflict")

    return {
        "version": STRENGTH_RULESET_VERSION,
        "preference_ruleset_version": PREFERENCE_RULESET_VERSION,
        "旺衰": label,
        "格局": pattern,
        "得令": in_season,
        "日主五行占比": round(ratio, 4),
        "五行得分": element_scores,
        **preference,
        "legacy_preference": {
            **legacy_preference,
            "deprecated": True,
            "note": "仅为兼容旧字段保留；新解释和流年规则不应读取。",
        },
        "evidence": {
            "strength_ruleset_version": STRENGTH_RULESET_VERSION,
            "preference_ruleset_version": PREFERENCE_RULESET_VERSION,
            "thresholds": {
                "strong_day_element_share_gt": STRONG_DAY_ELEMENT_SHARE,
                "weak_day_element_share_lt": WEAK_DAY_ELEMENT_SHARE,
            },
            "month_branch": month_pillar[1],
            "month_element": month_element,
            "day_element": day_element,
            "in_season": in_season,
            "day_element_score": element_scores.get(day_element, 0),
            "total_score": total,
        },
        "conflicts": conflicts,
    }


def attach_strength_assessment(chart: Dict[str, Any]) -> Dict[str, Any]:
    if "legacy_strength" not in chart:
        chart["legacy_strength"] = {
            "value": chart.get("日主强弱", ""),
            "喜用神": chart.get("喜用神", ""),
            "喜神": chart.get("喜神", ""),
            "忌神": chart.get("忌神", ""),
            "version": "element-share-v1",
            "deprecated": True,
            "note": "仅为兼容旧接口保留；衍生分析不应使用该字段。",
        }
    chart["strength_assessment"] = build_strength_assessment(chart)
    return chart


def get_resolved_preference(chart: Dict[str, Any]) -> Dict[str, Any]:
    """Return the versioned preference fields used by new interpretation rules."""
    assessment = chart.get("strength_assessment")
    required_fields = {"喜用神", "喜神", "忌神", "preference_ruleset_version"}
    if (
        not isinstance(assessment, dict)
        or assessment.get("version") != STRENGTH_RULESET_VERSION
        or not required_fields.issubset(assessment)
    ):
        assessment = attach_strength_assessment(chart)["strength_assessment"]
    return {
        "喜用神": assessment["喜用神"],
        "喜神": assessment["喜神"],
        "忌神": assessment["忌神"],
        "ruleset_version": assessment["preference_ruleset_version"],
        "conflicts": assessment.get("conflicts", []),
    }


def classify_preference_signals(
    chart: Dict[str, Any],
    element_sources: Dict[str, str],
) -> Dict[str, Any]:
    """Classify direct and supporting preference signals for a set of elements.

    A stem or branch that *generates* a preferred element is not the same as a
    direct hit.  The distinction is exposed so callers do not render indirect
    support as a categorical "喜用神年" or "忌神年" conclusion.
    """
    preference = get_resolved_preference(chart)
    favorable = []
    adverse = []
    for source, element in element_sources.items():
        if not element:
            continue
        if element == preference["喜用神"]:
            favorable.append({
                "code": "direct_yong",
                "source": source,
                "element": element,
            })
        if element == preference["喜神"]:
            favorable.append({
                "code": "direct_xi",
                "source": source,
                "element": element,
            })
        if WUXING_SHENG.get(element) == preference["喜用神"]:
            favorable.append({
                "code": "supports_yong",
                "source": source,
                "element": element,
            })
        if WUXING_SHENG.get(element) == preference["喜神"]:
            favorable.append({
                "code": "supports_xi",
                "source": source,
                "element": element,
            })
        if element == preference["忌神"]:
            adverse.append({
                "code": "direct_ji",
                "source": source,
                "element": element,
            })
        if WUXING_SHENG.get(element) == preference["忌神"]:
            adverse.append({
                "code": "supports_ji",
                "source": source,
                "element": element,
            })

    return {
        "ruleset_version": preference["ruleset_version"],
        "preference": {
            key: preference[key] for key in ("喜用神", "喜神", "忌神")
        },
        "favorable": favorable,
        "adverse": adverse,
        # Compatibility flags preserve the prior broad "direct or generates"
        # behavior. New consumers should inspect the signal lists instead.
        "is_yong_related": any(
            item["code"] in ("direct_yong", "supports_yong")
            for item in favorable
        ),
        "is_ji_related": any(
            item["code"] in ("direct_ji", "supports_ji")
            for item in adverse
        ),
    }
