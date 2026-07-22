"""Canonical, versioned chart assessments shared by all analysis modules."""
from __future__ import annotations

from typing import Any, Dict

from .calendar_engine import WUXING_SHENG, WUXING_ZHI


STRENGTH_RULESET_VERSION = "seasonal-strength-v1"


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

    if ratio > 0.35 and in_season:
        label = "身旺"
        pattern = "身旺格"
    elif ratio < 0.2:
        label = "身弱"
        pattern = "身弱格"
    elif in_season:
        label = "中和偏旺"
        pattern = "中和格"
    else:
        label = "中和偏弱"
        pattern = "中和格"

    legacy_label = chart.get("日主强弱", "")
    legacy_bucket = "身旺" if legacy_label == "身强" else "身弱"
    canonical_bucket = "身旺" if label in ("身旺", "中和偏旺") else "身弱"
    conflicts = []
    if legacy_label and legacy_bucket != canonical_bucket:
        conflicts.append("strength_model_conflict")

    return {
        "version": STRENGTH_RULESET_VERSION,
        "旺衰": label,
        "格局": pattern,
        "得令": in_season,
        "日主五行占比": round(ratio, 4),
        "五行得分": element_scores,
        "喜用神": chart.get("喜用神", ""),
        "喜神": chart.get("喜神", ""),
        "忌神": chart.get("忌神", ""),
        "evidence": {
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
            "version": "element-share-v1",
            "deprecated": True,
            "note": "仅为兼容旧接口保留；衍生分析不应使用该字段。",
        }
    chart["strength_assessment"] = build_strength_assessment(chart)
    return chart
