"""
liunian_analyzer.py — 流年决策分析辅助工具
给定出生信息和目标年份，输出详细的流年分析，供 agent 推理使用。
支持：单年分析、多年对比、自动从问题文本检测年份。
"""
from __future__ import annotations

import json
import os
import sys
import re
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.run_tools_engine import (
    eval_year, compute_chart, year_ganzhi_detail, get_dayun_at,
    shen, wuxing_relation,
)
from tools.calendar_engine import (
    TIANGAN, DIZHI, WUXING_GAN, WUXING_ZHI,
    ZHI_CANG_GAN, WUXING_SHENG, build_four_pillars, year_ganzhi,
    solar_term_datetime,
)

FLOW_MONTH_TERM_INDICES = (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22)


def extract_years(text: str) -> list[int]:
    """从问题文本中提取年份（4位数字）。"""
    years = []
    for m in re.finditer(r'(1[89]\d{2}|20\d{2})', text):
        y = int(m.group())
        if 1800 <= y <= 2099:
            years.append(y)
    return sorted(set(years))


def analyze_single_year(chart: dict, year: int, anchor: date | None = None) -> dict:
    """对单个年份做详细分析，返回人类可读的中文字段。"""
    anchor = anchor or date(year, 7, 1)
    ev = eval_year(chart, year, anchor.month, anchor.day)
    ln = ev["ln"]
    du = ev.get("du") or {}
    day_gan = ev["day_gan"]

    result = {
        "年份": year,
        "分析日期": anchor.isoformat(),
        "流年干支": f"{ln['gan']}{ln['zhi']}",
        "流年天干": ln["gan"],
        "流年地支": ln["zhi"],
        "天干五行": ln["gan_wx"],
        "地支五行": ln["zhi_wx"],
        "天干十神": ln.get("gan_ss", ""),
        "地支藏干": ln.get("zhi_cang", []),
        "地支藏干十神": ln.get("zhi_cang_ss", []),
        "该年是喜用神年": ln.get("is_yong", False),
        "该年是忌神年": ln.get("is_ji", False),
    }

    if du:
        result["当前大运"] = {
            "大运干支": du.get("ganzhi", ""),
            "起运年龄": du.get("start_age", 0),
            "大运天干十神": du.get("gan_ss", ""),
            "大运是喜用神": du.get("is_yong", False),
            "大运是忌神": du.get("is_ji", False),
        }

    if ev["chong"]:
        result["冲"] = [f"{a}冲{b}({c})" for a, b, c in ev["chong"]]

    if ev["he"]:
        result["合"] = [f"{a}合{b}({c})" for a, b, c in ev["he"]]

    result["流年十神集合"] = list(ev["all_ss"])

    result["喜用神"] = ev["yong"]
    result["忌神"] = ev["ji"]

    return result


def analyze_years(chart: dict, years: list[int]) -> dict:
    """对多年进行对比分析。"""
    results = []
    for y in years:
        results.append(analyze_single_year(chart, y))
    return {
        "日主": chart.get("日主", ""),
        "日主强弱": chart.get("日主强弱", ""),
        "喜用神": chart.get("喜用神", []),
        "忌神": chart.get("忌神", []),
        "四柱": chart.get("四柱", {}),
        "年份分析": results,
    }


def format_year_analysis(chart: dict, year: int) -> str:
    """格式化输出单个年份的分析（人类可读文本）。"""
    a = analyze_single_year(chart, year)
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"  {year}年 流年分析")
    lines.append(f"{'='*60}")
    lines.append(f"  流年干支: {a['流年干支']} (天干{a['天干五行']} / 地支{a['地支五行']})")
    lines.append(f"  天干十神: {a['天干十神']}")
    lines.append(f"  地支藏干: {a['地支藏干']} → 十神: {a['地支藏干十神']}")

    if a.get("当前大运"):
        du = a["当前大运"]
        lines.append(f"  当前大运: {du['大运干支']} (起运{du['起运年龄']}岁) 天干十神: {du['大运天干十神']}")

    tag_yong = "★喜用神年★" if a["该年是喜用神年"] else ""
    tag_ji = "⚠忌神年⚠" if a["该年是忌神年"] else ""
    tag = tag_yong or tag_ji or "平年"
    lines.append(f"  年运属性: {tag}")

    if a.get("冲"):
        lines.append(f"  冲: {'; '.join(a['冲'])} (冲主动荡/变动/冲突)")
    if a.get("合"):
        lines.append(f"  合: {'; '.join(a['合'])} (合主合作/结合/牵绊)")

    lines.append(f"  出现十神: {a['流年十神集合']}")
    return "\n".join(lines)


def format_years_compare(chart: dict, years: list[int]) -> str:
    """格式化多年对比分析。"""
    lines = []
    lines.append(f"\n{'#'*60}")
    lines.append(f"  多年流年对比分析")
    lines.append(f"  日主: {chart.get('日主','')}({chart.get('日主五行','')}) | {chart.get('日主强弱','')}")
    lines.append(f"  喜用: {chart.get('喜用神',[])} | 忌: {chart.get('忌神',[])}")
    lines.append(f"  四柱: {chart.get('四柱',{})}")
    lines.append(f"{'#'*60}")

    for y in years:
        a = analyze_single_year(chart, y)
        tags = []
        if a["该年是喜用神年"]:
            tags.append("喜用")
        if a["该年是忌神年"]:
            tags.append("忌神")
        if a.get("冲"):
            tags.append("冲")
        if a.get("合"):
            tags.append("合")
        tag_str = ",".join(tags) if tags else "—"

        du_info = ""
        if a.get("当前大运"):
            du = a["当前大运"]
            du_info = f" 大运:{du['大运干支']}({du['天干十神']})"

        lines.append(
            f"  {y}: {a['流年干支']} "
            f"天干{a['天干十神']} {a['地支藏干十神']}"
            f"  [{tag_str}]{du_info}"
        )

    return "\n".join(lines)


def _parse_period(value: dict) -> tuple[date, date, str]:
    if not isinstance(value, dict):
        raise ValueError("analysis_period 必须是对象。")
    try:
        start = datetime.fromisoformat(str(value["start"])).date()
        end = datetime.fromisoformat(str(value["end"])).date()
    except (KeyError, ValueError) as exc:
        raise ValueError("analysis_period 需要 ISO 格式的 start 和 end。") from exc
    if end < start:
        raise ValueError("analysis_period.end 不能早于 start。")
    granularity = value.get("granularity", "year")
    if granularity not in ("year", "month", "day"):
        raise ValueError("analysis_period.granularity 必须是 year、month 或 day。")
    span_days = (end - start).days
    if granularity == "day" and span_days > 366:
        raise ValueError("day 粒度最多支持 366 天；请改用 month 或 year。")
    if granularity == "month" and span_days > 3660:
        raise ValueError("month 粒度最多支持 10 年；请改用 year。")
    return start, end, granularity


def _period_anchors(start: date, end: date, granularity: str) -> list[date]:
    if granularity == "day":
        return [start + timedelta(days=index) for index in range((end - start).days + 1)]
    if granularity == "month":
        anchors = []
        cursor = date(start.year, start.month, 1)
        while cursor <= end:
            anchors.append(max(cursor, start))
            if cursor.month == 12:
                cursor = date(cursor.year + 1, 1, 1)
            else:
                cursor = date(cursor.year, cursor.month + 1, 1)
        return anchors
    return [
        date(year, 7, 1)
        for year in range(start.year, end.year + 1)
        if start <= date(year, 7, 1) <= end
    ] or [start]


def _lichun_segments(start: date, end: date) -> list[dict]:
    """Split a civil interval at the precise Li Chun boundary."""
    segments = []
    cursor = datetime.combine(start, datetime.min.time())
    final = datetime.combine(end + timedelta(days=1), datetime.min.time())
    boundaries = [
        solar_term_datetime(year, 2)
        for year in range(start.year - 1, end.year + 2)
    ]
    for boundary in boundaries:
        if cursor < boundary < final:
            segments.append({
                "start": cursor.isoformat(timespec="seconds"),
                "end": boundary.isoformat(timespec="seconds"),
                "流年干支": year_ganzhi(
                    cursor.year,
                    cursor.month,
                    cursor.day,
                    cursor.hour,
                    cursor.minute,
                    cursor.second,
                ),
                "boundary": "立春",
            })
            cursor = boundary
    segments.append({
        "start": cursor.isoformat(timespec="seconds"),
        "end": final.isoformat(timespec="seconds"),
        "流年干支": year_ganzhi(
            cursor.year,
            cursor.month,
            cursor.day,
            cursor.hour,
            cursor.minute,
            cursor.second,
        ),
    })
    return segments


def _flow_month_segments(chart: dict, start: date, end: date) -> list[dict]:
    """Split a civil interval at the twelve Bazi-month ``jie`` boundaries."""
    cursor = datetime.combine(start, datetime.min.time())
    final = datetime.combine(end + timedelta(days=1), datetime.min.time())
    boundaries = sorted(
        solar_term_datetime(year, term_index)
        for year in range(start.year - 1, end.year + 2)
        for term_index in FLOW_MONTH_TERM_INDICES
        if cursor < solar_term_datetime(year, term_index) < final
    )
    segments = []
    for boundary in boundaries + [final]:
        segment_start = cursor
        if segment_start >= boundary:
            continue
        flow_chart = build_four_pillars(
            segment_start.year,
            segment_start.month,
            segment_start.day,
            segment_start.hour,
            gender=chart.get("gender", "男"),
            minute=segment_start.minute,
            second=segment_start.second,
        )
        flow_year = flow_chart["四柱"]["年柱"]
        flow_month = flow_chart["四柱"]["月柱"]
        day_gan = chart["日主"]
        month_cang = ZHI_CANG_GAN.get(flow_month[1], [])
        flow_eval = eval_year(
            chart,
            segment_start.year,
            segment_start.month,
            segment_start.day,
        )
        dayun = flow_eval.get("du") or {}
        segments.append({
            "start": segment_start.isoformat(timespec="seconds"),
            "end": boundary.isoformat(timespec="seconds"),
            "流年干支": flow_year,
            "流月干支": flow_month,
            "流月天干十神": shen(day_gan, flow_month[0]),
            "流月地支藏干": month_cang,
            "流月地支藏干十神": [
                shen(day_gan, stem) for stem in month_cang
            ],
            "当前大运": dayun.get("ganzhi", ""),
            "边界": "节气" if boundary != final else "区间结束",
        })
        cursor = boundary
    return segments


def _summary_row(analysis: dict) -> dict:
    tags = []
    if analysis["该年是喜用神年"]:
        tags.append("喜用年(吉利)")
    if analysis["该年是忌神年"]:
        tags.append("忌神年(不利)")
    if analysis.get("冲"):
        tags.append(f"冲:{', '.join(analysis['冲'])}")
    if analysis.get("合"):
        tags.append(f"合:{', '.join(analysis['合'])}")
    du = analysis.get("当前大运") or {}
    return {
        "年份": analysis["年份"],
        "分析日期": analysis["分析日期"],
        "干支": analysis["流年干支"],
        "天干十神": analysis["天干十神"],
        "地支藏干十神": analysis["地支藏干十神"],
        "十神集合": analysis["流年十神集合"],
        "标签": tags,
        "大运": du.get("大运干支", ""),
    }


def integrate_year_analysis(
    birth_info: dict,
    chart: dict | None,
    question: str,
    options_json: str,
    analysis_period: dict | None = None,
) -> str:
    """Analyze an explicit civil period or a legacy year-only question."""
    warnings = []
    if chart is None:
        chart = compute_chart(birth_info)
    if not chart:
        return json.dumps({
            "success": False,
            "component_status": {
                "status": "error",
                "code": "chart_unavailable",
                "message": "无法构建流年分析所需命盘。",
            },
        }, ensure_ascii=False)

    if analysis_period:
        start, end, granularity = _parse_period(analysis_period)
        anchors = _period_anchors(start, end, granularity)
        source = "explicit_period"
        segments = _lichun_segments(start, end)
        month_segments = (
            _flow_month_segments(chart, start, end)
            if granularity in ("month", "day") else []
        )
    else:
        years = extract_years(question)
        if options_json:
            try:
                options = json.loads(options_json)
            except json.JSONDecodeError as exc:
                return json.dumps({
                    "success": False,
                    "component_status": {
                        "status": "error",
                        "code": "invalid_options_json",
                        "message": str(exc),
                    },
                }, ensure_ascii=False)
            for option in options:
                years.extend(extract_years(option.get("text", "")))
        years = sorted(set(years))
        if not years:
            return json.dumps({
                "success": True,
                "检测到的年份": [],
                "年份流年对比": [],
                "component_status": {
                    "status": "degraded",
                    "code": "no_target_period",
                    "message": "未提供 analysis_period，问题文本中也未检测到年份。",
                },
            }, ensure_ascii=False)
        anchors = [date(year, 7, 1) for year in years]
        start, end, granularity = anchors[0], anchors[-1], "year"
        source = "question_year_fallback"
        warnings.append(
            "仅从文本提取年份并以7月1日作为年度锚点；具体事件请提供 analysis_period。"
        )
        segments = []
        month_segments = []

    rows = [
        _summary_row(analyze_single_year(chart, anchor.year, anchor))
        for anchor in anchors
    ]
    assessment = chart.get("strength_assessment", {})
    return json.dumps({
        "success": True,
        "chart_id": chart.get("chart_id"),
        "analysis_source": source,
        "analysis_period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "granularity": granularity,
        },
        "civil_to_bazi_year_segments": segments,
        "流月分段": month_segments,
        "检测到的年份": sorted({anchor.year for anchor in anchors}),
        "日主": chart.get("日主", ""),
        "日主强弱": assessment.get("旺衰", chart.get("日主强弱", "")),
        "喜用神": chart.get("喜用神", []),
        "忌神": chart.get("忌神", []),
        "年份流年对比": rows,
        "warnings": warnings,
        "component_status": {
            "status": "ok",
            "backend": "shared-computed-chart",
            "ruleset_version": assessment.get("version"),
        },
    }, ensure_ascii=False)
