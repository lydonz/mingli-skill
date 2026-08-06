"""Shared chart construction and flow-period evaluation.

The historical multiple-choice scorer remains source-inert during the current
migration; ``predict`` always abstains and product code consumes only the
auditable chart, period and interpretation interfaces.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from typing import Any, Optional

from tools.calendar_engine import (
    DIZHI,
    DIZHI_IDX,
    TIANGAN,
    TIANGAN_IDX,
    WUXING_GAN,
    WUXING_SHENG,
    WUXING_ZHI,
    ZHI_CANG_GAN,
    build_dayun_precise,
    build_four_pillars,
    lunar_new_year_datetime,
    shi_shen,
    solar_term_datetime,
    wuxing_relation,
    year_ganzhi,
)

shen = shi_shen

from tools.tool_integration import build_tool_data
from tools.birth_context import normalize_birth_context, normalize_gender
from tools.chart_assessment import (
    attach_strength_assessment,
    classify_preference_signals,
    get_resolved_preference,
)
from tools.computed_chart import ComputedChart


def _chart_id_for(
    effective_time: datetime,
    calendar_time: datetime,
    gender: str,
    year_boundary: str,
    time_basis: str,
    zi_hour_convention: str,
) -> str:
    payload = {
        "effective_time": effective_time.isoformat(timespec="seconds"),
        "calendar_time": calendar_time.isoformat(timespec="seconds"),
        "gender": gender,
        "year_boundary": year_boundary,
        "time_basis": time_basis,
        "zi_hour_convention": zi_hour_convention,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()[:16]


def _ziwei_hour_index(hour: int, convention: str) -> int:
    if hour == 23:
        return 0 if convention == "early" else 12
    if hour == 0 and convention == "late":
        return 12
    return (hour + 1) // 2


def _uncertainty_candidate_times(
    effective_time: datetime,
    calendar_time: datetime,
    uncertainty_minutes: int,
    year_boundary: str,
) -> list[tuple[datetime, list[str]]]:
    """Enumerate every hour/day and calendar-boundary chart in an interval."""
    start = effective_time - timedelta(minutes=uncertainty_minutes)
    end = effective_time + timedelta(minutes=uncertainty_minutes)
    candidates: dict[datetime, list[str]] = {
        start: ["range_start"],
        effective_time: ["nominal"],
        end: ["range_end"],
    }

    def add_candidate(value: datetime, reason: str) -> None:
        if start <= value <= end:
            candidates.setdefault(value, []).append(reason)

    day_cursor = start.replace(hour=0, minute=0, second=0, microsecond=0)
    final_day = end.replace(hour=0, minute=0, second=0, microsecond=0)
    while day_cursor <= final_day:
        for hour in (0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23):
            add_candidate(
                day_cursor.replace(hour=hour),
                "hour_or_day_boundary",
            )
        day_cursor += timedelta(days=1)

    calendar_offset = calendar_time - effective_time
    calendar_start = start + calendar_offset
    calendar_end = end + calendar_offset
    for year in range(calendar_start.year - 1, calendar_end.year + 2):
        for term_index in range(0, 24, 2):
            boundary = solar_term_datetime(year, term_index)
            if calendar_start <= boundary <= calendar_end:
                add_candidate(boundary - calendar_offset, "solar_term_boundary")
        if year_boundary == "lunar_new_year":
            boundary = lunar_new_year_datetime(year)
            if calendar_start <= boundary <= calendar_end:
                add_candidate(boundary - calendar_offset, "lunar_new_year_boundary")

    return sorted(candidates.items(), key=lambda item: item[0])


def _candidate_charts(
    effective_time: datetime,
    calendar_time: datetime,
    uncertainty_minutes: int,
    gender: str,
    year_boundary: str,
    time_basis: str,
    zi_hour_convention: str,
    nominal_pillars: dict,
    nominal_effective_time: datetime,
) -> list[dict]:
    """Return distinct Bazi and Ziwei candidates within the uncertainty range."""
    nominal_ziwei_key = (
        nominal_effective_time.date().isoformat(),
        _ziwei_hour_index(nominal_effective_time.hour, zi_hour_convention),
    )
    candidates_by_chart: dict[tuple[Any, Any], dict] = {}
    for candidate_time, reasons in _uncertainty_candidate_times(
        effective_time,
        calendar_time,
        uncertainty_minutes,
        year_boundary,
    ):
        candidate_calendar_time = calendar_time + (
            candidate_time - effective_time
        )
        pillars = build_four_pillars(
            candidate_time.year,
            candidate_time.month,
            candidate_time.day,
            candidate_time.hour,
            gender=gender,
            minute=candidate_time.minute,
            second=candidate_time.second,
            year_boundary=year_boundary,
            term_datetime=candidate_calendar_time,
        )["四柱"]
        pillar_key = tuple(sorted(pillars.items()))
        ziwei_key = (
            candidate_time.date().isoformat(),
            _ziwei_hour_index(candidate_time.hour, zi_hour_convention),
        )
        changed_fields = [
            name for name, value in pillars.items()
            if nominal_pillars.get(name) != value
        ]
        if ziwei_key != nominal_ziwei_key:
            changed_fields.append("紫微")
        entry = candidates_by_chart.setdefault(
            (pillar_key, ziwei_key),
            {
                "effective_time": candidate_time.isoformat(timespec="seconds"),
                "calendar_time": candidate_calendar_time.isoformat(
                    timespec="seconds"
                ),
                "chart_id": _chart_id_for(
                    candidate_time,
                    candidate_calendar_time,
                    gender,
                    year_boundary,
                    time_basis,
                    zi_hour_convention,
                ),
                "四柱": pillars,
                "紫微候选": {
                    "solar_date": ziwei_key[0],
                    "iztro_hour_index": ziwei_key[1],
                },
                "changed_fields": changed_fields,
                "boundaries": [],
            },
        )
        entry["boundaries"].extend(reasons)

    for entry in candidates_by_chart.values():
        entry["boundaries"] = sorted(set(entry["boundaries"]))
    return sorted(
        candidates_by_chart.values(),
        key=lambda item: item["effective_time"],
    )


def compute_chart(bi) -> ComputedChart:
    normalized_context = normalize_birth_context(
        bi, bi.get("birth_context")
    )
    effective = normalized_context.effective_time
    y, m, d, h = (
        effective.year,
        effective.month,
        effective.day,
        effective.hour,
    )
    g = normalize_gender(bi.get("gender") or "男")
    minute = effective.minute
    second = effective.second
    year_boundary = bi.get("year_boundary", "lichun")
    if not all([y, m, d]):
        return {}
    c = ComputedChart(build_four_pillars(
        y,
        m,
        d,
        h,
        gender=g,
        minute=minute,
        second=second,
        year_boundary=year_boundary,
        term_datetime=normalized_context.calendar_time,
    ))
    c["gender"] = g
    c["birth_year"] = y
    c["birth_month"] = m
    c["birth_day"] = d
    c["birth_hour"] = h
    c["birth_minute"] = minute
    c["birth_second"] = second
    c["year_boundary"] = year_boundary
    c["birth_time"] = normalized_context.as_dict()
    attach_strength_assessment(c)

    c["chart_id"] = _chart_id_for(
        effective,
        normalized_context.calendar_time,
        g,
        year_boundary,
        c["birth_time"]["time_basis"],
        c["birth_time"]["zi_hour_convention"],
    )

    pillars = c.get("四柱", {})
    ygz = pillars.get("年柱", "")
    mgz = pillars.get("月柱", "")
    if ygz and mgz:
        c["大运"] = build_dayun_precise(
            y,
            m,
            d,
            h,
            g,
            minute=minute,
            second=second,
            year_boundary=year_boundary,
            term_datetime=normalized_context.calendar_time,
        )
        c["大运精度"] = c["大运"][0].get("精度", "unknown") if c["大运"] else "unknown"
    if normalized_context.uncertainty_minutes:
        variants = _candidate_charts(
            effective,
            normalized_context.calendar_time,
            normalized_context.uncertainty_minutes,
            g,
            year_boundary,
            c["birth_time"]["time_basis"],
            c["birth_time"]["zi_hour_convention"],
            c["四柱"],
            effective,
        )
        c["birth_time"]["chart_stability"] = {
            "stable": len(variants) == 1,
            "candidate_charts": variants,
        }
    return c


def _get_tool_data(bi, chart: Optional[ComputedChart] = None):
    """Build secondary data from the caller's canonical chart when supplied."""
    chart = chart or compute_chart(bi)
    if not chart:
        return {}
    try:
        return build_tool_data(
            chart["birth_year"],
            chart["birth_month"],
            chart["birth_day"],
            chart["birth_hour"],
            chart.get("gender", "男"),
            chart=chart,
        )
    except Exception as exc:
        return {
            "component_status": {
                "tool_data": {
                    "status": "error",
                    "code": "tool_data_failed",
                    "message": str(exc),
                },
            },
        }


def year_ganzhi_detail(
    year,
    month=None,
    day=None,
    hour=12,
    minute=0,
    second=0,
    year_boundary="lichun",
):
    gz = year_ganzhi(
        year,
        month,
        day,
        hour,
        minute,
        second,
        year_boundary=year_boundary,
    )
    return {
        "ganzhi": gz, "gan": gz[0], "zhi": gz[1],
        "gan_wx": WUXING_GAN[gz[0]], "zhi_wx": WUXING_ZHI[gz[1]],
    }


def get_dayun_at(
    day_gan,
    year_ganzhi_str,
    month_ganzhi_str,
    gender,
    target_year,
    birth_year,
    dayun_list=None,
    target_month=7,
    target_day=1,
):
    """Return the Da Yun active on a concrete date.

    When precise entries are available, the transition date wins over the
    old age-bucket approximation.  July 1 is used for annual summaries so a
    year containing a transition is not silently assigned to the new luck.
    """
    if dayun_list:
        target = date(target_year, target_month, target_day)
        for item in dayun_list:
            start = item.get("起运日期")
            end = item.get("止运日期")
            if not start or not end:
                continue
            if start <= target.isoformat() < end:
                gz = item["大运"]
                return {
                    "ganzhi": gz,
                    "gan": gz[0],
                    "zhi": gz[1],
                    "gan_wx": WUXING_GAN[gz[0]],
                    "zhi_wx": WUXING_ZHI[gz[1]],
                    "start_age": item.get("起运年龄"),
                    "end_age": item.get("止运年龄"),
                    "start_date": start,
                    "end_date": end,
                    "precision": item.get("精度", "solar-term"),
                }

    yin_yang = TIANGAN_IDX[year_ganzhi_str[0]] % 2
    male = gender in ("男", "M", "male")
    forward = (male and yin_yang == 0) or (not male and yin_yang == 1)
    mg = TIANGAN_IDX[month_ganzhi_str[0]]
    mz = DIZHI_IDX[month_ganzhi_str[1]]
    age = target_year - birth_year
    for i in range(8):
        if forward:
            g = (mg + i + 1) % 10; z = (mz + i + 1) % 12
        else:
            g = (mg - i - 1) % 10; z = (mz - i - 1) % 12
        s = i * 10 + 1; e = s + 9
        if s <= age <= e:
            gz = TIANGAN[g] + DIZHI[z]
            return {"ganzhi": gz, "gan": gz[0], "zhi": gz[1],
                    "gan_wx": WUXING_GAN[gz[0]], "zhi_wx": WUXING_ZHI[gz[1]],
                    "start_age": s, "end_age": e}
    return {}


def _uses_strong_path(chart):
    assessment = chart.get("strength_assessment", {})
    value = assessment.get("旺衰")
    if value:
        return value in ("身旺", "中和偏旺")
    return chart.get("日主强弱") == "身强"


def eval_year(chart, year, target_month=7, target_day=1):
    """Evaluate the Bazi dynamics for a specific year. Returns rich dict."""
    day_gan = chart["日主"]
    day_wx = chart["日主五行"]
    strong = _uses_strong_path(chart)
    preference = get_resolved_preference(chart)
    yong = preference["喜用神"]
    ji = preference["忌神"]
    pillars = chart["四柱"]
    wx = chart["五行力量"]
    tg = chart["十神"]

    ln = year_ganzhi_detail(
        year,
        target_month,
        target_day,
        year_boundary=chart.get("year_boundary", "lichun"),
    )
    ln["gan_ss"] = shen(day_gan, ln["gan"])
    ln["zhi_cang"] = ZHI_CANG_GAN.get(ln["zhi"], [])
    ln["zhi_cang_ss"] = [shen(day_gan, c) for c in ln["zhi_cang"]]
    ln["rel_gan"] = wuxing_relation(day_wx, ln["gan_wx"])
    ln["rel_zhi"] = wuxing_relation(day_wx, ln["zhi_wx"])

    ln["preference_signals"] = classify_preference_signals(
        chart,
        {
            "流年天干": ln["gan_wx"],
            "流年地支": ln["zhi_wx"],
        },
    )
    ln["is_yong"] = ln["preference_signals"]["is_yong_related"]
    ln["is_ji"] = ln["preference_signals"]["is_ji_related"]

    ygz = pillars.get("年柱", "")
    mgz = pillars.get("月柱", "")
    du = get_dayun_at(
        day_gan,
        ygz,
        mgz,
        chart.get("gender", "男"),
        year,
        chart.get("birth_year", 1990),
        dayun_list=chart.get("大运"),
        target_month=target_month,
        target_day=target_day,
    )
    if du:
        du["gan_ss"] = shen(day_gan, du["gan"])
        du["zhi_cang"] = ZHI_CANG_GAN.get(du["zhi"], [])
        du["zhi_cang_ss"] = [shen(day_gan, c) for c in du["zhi_cang"]]
        du["preference_signals"] = classify_preference_signals(
            chart,
            {
                "大运天干": du["gan_wx"],
                "大运地支": du["zhi_wx"],
            },
        )
        du["is_yong"] = du["preference_signals"]["is_yong_related"]
        du["is_ji"] = du["preference_signals"]["is_ji_related"]

    all_ss = set()
    for s in [ln["gan_ss"]] + ln["zhi_cang_ss"]:
        if s: all_ss.add(s)
    if du:
        for s in [du.get("gan_ss", "")] + du.get("zhi_cang_ss", []):
            if s: all_ss.add(s)

    chong_pairs = []
    he_pairs = []
    hai_pairs = []
    po_pairs = []
    pillar_zhis = [gz[1] for gz in pillars.values() if gz and len(gz) > 1]
    for pzh in pillar_zhis:
        r = _check_chong_he(pzh, ln["zhi"])
        if "六冲" in r: chong_pairs.append((pzh, ln["zhi"], "流年冲命"))
        if "六合" in r: he_pairs.append((pzh, ln["zhi"], "流年合命"))
        if "半合" in r: he_pairs.append((pzh, ln["zhi"], "流年半合命"))
        if "六害" in r: hai_pairs.append((pzh, ln["zhi"], "流年害命"))
        if "六破" in r: po_pairs.append((pzh, ln["zhi"], "流年破命"))
    if du:
        for pzh in pillar_zhis:
            r = _check_chong_he(pzh, du["zhi"])
            if "六冲" in r: chong_pairs.append((pzh, du["zhi"], "大运冲命"))
            if "六合" in r: he_pairs.append((pzh, du["zhi"], "大运合命"))
            if "六害" in r: hai_pairs.append((pzh, du["zhi"], "大运害命"))
            if "六破" in r: po_pairs.append((pzh, du["zhi"], "大运破命"))

    return {"ln": ln, "du": du, "all_ss": all_ss,
            "chong": chong_pairs, "he": he_pairs,
            "hai": hai_pairs, "po": po_pairs,
            "day_gan": day_gan, "day_wx": day_wx,
            "strong": strong, "yong": yong, "ji": ji,
            "wx": wx, "tg": tg, "pillars": pillars}


def _check_chong_he(z1, z2):
    pair = tuple(sorted([z1, z2]))
    liu_chong = {("子", "午"), ("丑", "未"), ("寅", "申"), ("卯", "酉"),
                 ("辰", "戌"), ("巳", "亥")}
    liu_he = {("子", "丑"), ("寅", "亥"), ("卯", "戌"), ("辰", "酉"),
              ("巳", "申"), ("午", "未")}
    liu_hai = {tuple(sorted(p)) for p in [("子", "未"), ("丑", "午"), ("寅", "巳"), ("卯", "辰"),
               ("申", "亥"), ("酉", "戌")]}
    liu_po = {tuple(sorted(p)) for p in [("子", "酉"), ("寅", "亥"), ("辰", "丑"), ("午", "卯"),
              ("申", "巳"), ("戌", "未")]}
    san_he = [{("申", "子"), ("子", "辰"), ("辰", "申")},
              {("亥", "卯"), ("卯", "未"), ("未", "亥")},
              {("寅", "午"), ("午", "戌"), ("戌", "寅")},
              {("巳", "酉"), ("酉", "丑"), ("丑", "巳")}]

    results = []
    if pair in liu_chong: results.append("六冲")
    if pair in liu_he: results.append("六合")
    if pair in liu_hai: results.append("六害")
    if pair in liu_po: results.append("六破")
    for trio in san_he:
        if z1 in set().union(*[set(t) for t in trio]) and z2 in set().union(*[set(t) for t in trio]) and z1 != z2:
            # A two-branch match is only a partial combination.  Reporting it
            # as a completed 三合 overstated the strength of many flow-year
            # interactions.
            results.append("半合")
    return results



def predict(q, chart_cache, qimen_data=None):
    """Retired historical-event answer predictor; always abstain."""
    return None
