#!/usr/bin/env python3
"""Evaluate normalized datasets without conflating their evidence levels."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.dataset_registry import get_source, require_allowed_use
from tools.calendar_engine import (
    _get_solar_term_date,
    build_four_pillars,
    day_ganzhi_from_datetime,
    ganzhi_from_offset,
    month_ganzhi,
)
from tools.ziwei_tools import ZiweiToolkit


def read_records(path: Path):
    with path.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                yield json.loads(line)


def _source_observed_pillars(birthday: datetime):
    """Reproduce the declared source convention without changing skill defaults."""
    term_boundaries = [
        (10, 22, -1), (11, 0, 0), (0, 2, 0), (1, 4, 0),
        (2, 6, 0), (3, 8, 0), (4, 10, 0), (5, 12, 0),
        (6, 14, 0), (7, 16, 0), (8, 18, 0), (9, 20, 0),
        (10, 22, 0),
    ]
    month_index = 10
    for candidate, term_index, year_offset in term_boundaries:
        term_month, term_day = _get_solar_term_date(
            birthday.year + year_offset, term_index
        )
        if (birthday.year, birthday.month, birthday.day) >= (
            birthday.year + year_offset, term_month, term_day
        ):
            month_index = candidate
    lichun_month, lichun_day = _get_solar_term_date(birthday.year, 2)
    bazi_year = birthday.year if (birthday.month, birthday.day) >= (
        lichun_month, lichun_day
    ) else birthday.year - 1
    year_pillar = ganzhi_from_offset((bazi_year - 4) % 60)
    skill_default = list(build_four_pillars(
        birthday.year, birthday.month, birthday.day, birthday.hour,
        minute=birthday.minute, year_boundary="lichun",
    )["四柱"].values())
    return [
        year_pillar,
        month_ganzhi(year_pillar[0], month_index),
        day_ganzhi_from_datetime(
            birthday.year, birthday.month, birthday.day, birthday.hour,
            birthday.minute, zi_hour_changes_day=False,
        ),
        skill_default[3],
    ]


def _match_report(name, matched, total, mismatches):
    return {
        "convention": name,
        "matched": matched,
        "total": total,
        "accuracy": matched / total if total else 0,
        "mismatches": mismatches,
    }


def evaluate_calculation(records):
    default_matched = 0
    compatibility_matched = 0
    total = 0
    default_mismatches = []
    compatibility_mismatches = []
    for item in records:
        birthday = datetime.fromisoformat(item["record"]["input"]["birthday"])
        expected = item["record"]["expected"]["four_pillars"]
        actual = list(build_four_pillars(
            birthday.year, birthday.month, birthday.day, birthday.hour,
            minute=birthday.minute, year_boundary="lichun",
        )["四柱"].values())
        compatibility_actual = _source_observed_pillars(birthday)
        total += 1
        if actual == expected:
            default_matched += 1
        elif len(default_mismatches) < 20:
            default_mismatches.append({
                "record_index": item["record_index"],
                "birthday": birthday.isoformat(),
                "actual": actual,
                "expected": expected,
            })
        if compatibility_actual == expected:
            compatibility_matched += 1
        elif len(compatibility_mismatches) < 20:
            compatibility_mismatches.append({
                "record_index": item["record_index"],
                "birthday": birthday.isoformat(),
                "actual": compatibility_actual,
                "expected": expected,
            })
    return {
        "metric": "four_pillar_exact_match",
        "matched": default_matched,
        "total": total,
        "accuracy": default_matched / total if total else 0,
        "skill_default": _match_report(
            "precise_term_and_late_zi_day", default_matched, total,
            default_mismatches,
        ),
        "source_observed_compatibility": _match_report(
            "civil_term_date_civil_day_late_zi_hour", compatibility_matched, total,
            compatibility_mismatches,
        ),
    }


def evaluate_terminology_coverage(records):
    total = len(records)
    complete = sum(
        bool(item["record"].get("question"))
        and bool(item["record"].get("synthetic_reasoning"))
        and bool(item["record"].get("synthetic_answer"))
        for item in records
    )
    return {
        "metric": "synthetic_explanation_record_completeness",
        "records": total,
        "complete_records": complete,
        "completeness": complete / total if total else 0,
        "interpretation": (
            "This is an import and coverage audit, not a correctness score for "
            "the synthetic reasoning or its conclusions."
        ),
    }


def _mingli_bench_records(records):
    for item in records:
        record = item.get("record", {})
        expected = record.get("expected", {})
        input_data = record.get("input", {})
        birthday = datetime.fromisoformat(input_data["civil_birth_time"])
        gender = input_data["gender"]
        yield item, record, expected, birthday, gender


def _bounded_mismatch(mismatches, item, payload):
    if len(mismatches) < 20:
        mismatches.append({
            "record_index": item["record_index"],
            "case_id": item["record"].get("case_id"),
            **payload,
        })


def evaluate_mingli_bench_bazi(records):
    """Compare four pillars without treating event answers as ground truth."""
    labels = ("year", "month", "day", "hour")
    component_matches = {label: 0 for label in labels}
    exact_matches = 0
    mismatches = []
    total = 0

    for item, _record, expected, birthday, gender in _mingli_bench_records(records):
        expected_pillars = expected["four_pillars"]
        if len(expected_pillars) != 4:
            raise ValueError("MingLi-Bench fixture must contain four expected pillars")
        actual_pillars = list(build_four_pillars(
            birthday.year,
            birthday.month,
            birthday.day,
            birthday.hour,
            minute=birthday.minute,
            gender=gender,
            year_boundary="lichun",
        )["四柱"].values())
        total += 1
        field_mismatches = {}
        for label, actual, source_value in zip(
            labels, actual_pillars, expected_pillars
        ):
            if actual == source_value:
                component_matches[label] += 1
            else:
                field_mismatches[label] = {
                    "actual": actual,
                    "source": source_value,
                }
        if not field_mismatches:
            exact_matches += 1
        else:
            _bounded_mismatch(mismatches, item, {
                "mismatched_pillars": field_mismatches,
            })

    return {
        "metric": "mingli_bench_four_pillar_component_match",
        "total": total,
        "full_pillar_exact_match": {
            "matched": exact_matches,
            "accuracy": exact_matches / total if total else 0,
        },
        "pillar_component_matches": {
            label: {
                "matched": matched,
                "total": total,
                "accuracy": matched / total if total else 0,
            }
            for label, matched in component_matches.items()
        },
        "mismatches": mismatches,
        "interpretation": (
            "This compares the source's precomputed iztro chineseDate field "
            "with this project's explicit lichun year-boundary convention. "
            "It does not score MingLi-Bench event answers or establish "
            "future-event prediction accuracy."
        ),
    }


def _actual_ziwei_fixture(birthday, gender):
    result = json.loads(ZiweiToolkit().paipan(
        birthday.year,
        birthday.month,
        birthday.day,
        birthday.hour,
        gender,
    ))
    backend_status = result.get("后端状态", {})
    if (
        not result.get("success")
        or result.get("排盘引擎") != "iztro"
        or backend_status.get("status") != "ok"
    ):
        raise RuntimeError(
            "MingLi-Bench Ziwei regression requires the healthy iztro backend: "
            f"{result.get('error') or backend_status}"
        )
    palaces = result["十二宫"]
    body_palace = result["身宫"]
    return {
        "lunar_date": result["农历日期"],
        "soul_palace_branch": result["命宫"]["地支"],
        "body_palace_branch": palaces[body_palace]["宫位地支"],
        "five_elements_class": result["五行局"],
        "zodiac": result["生肖"],
        "palaces": {
            name: {
                "earthly_branch": palace["宫位地支"],
                "major_stars": palace["主星"],
                "minor_stars": palace["辅星"],
            }
            for name, palace in palaces.items()
        },
    }


def evaluate_mingli_bench_ziwei(records):
    """Compare deterministic Ziwei structures against the bundled iztro output."""
    fields = (
        "lunar_date",
        "soul_palace_branch",
        "body_palace_branch",
        "five_elements_class",
        "zodiac",
        "palaces",
    )
    field_matches = {field: 0 for field in fields}
    exact_matches = 0
    mismatches = []
    total = 0

    for item, _record, expected, birthday, gender in _mingli_bench_records(records):
        expected_ziwei = expected["ziwei"]
        actual_ziwei = _actual_ziwei_fixture(birthday, gender)
        total += 1
        failed_fields = [
            field for field in fields
            if actual_ziwei[field] != expected_ziwei[field]
        ]
        for field in fields:
            if field not in failed_fields:
                field_matches[field] += 1
        if not failed_fields:
            exact_matches += 1
        else:
            _bounded_mismatch(mismatches, item, {
                "failed_fields": failed_fields,
            })

    return {
        "metric": "mingli_bench_ziwei_structure_exact_match",
        "total": total,
        "full_chart_exact_match": {
            "matched": exact_matches,
            "accuracy": exact_matches / total if total else 0,
        },
        "field_matches": {
            field: {
                "matched": matched,
                "total": total,
                "accuracy": matched / total if total else 0,
            }
            for field, matched in field_matches.items()
        },
        "mismatches": mismatches,
        "interpretation": (
            "This compares deterministic iztro chart fields only. It does not "
            "score MingLi-Bench event answers or establish future-event "
            "prediction accuracy."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    source = get_source(args.source_id)
    require_allowed_use(source, args.purpose)
    records = list(read_records(args.records))
    if any(record["source_id"] != source["id"] for record in records):
        raise ValueError("records file source_id does not match --source-id")

    if args.source_id == "mingli-bench":
        if args.purpose == "bazi_chart_regression":
            report = evaluate_mingli_bench_bazi(records)
        elif args.purpose == "ziwei_chart_regression":
            report = evaluate_mingli_bench_ziwei(records)
        else:
            raise ValueError(
                "MingLi-Bench event-answer scoring is intentionally unsupported"
            )
    elif args.purpose == "bazi_chart_regression":
        report = evaluate_calculation(records)
    elif args.purpose == "terminology_coverage":
        report = evaluate_terminology_coverage(records)
    else:
        raise ValueError(f"No evaluator is implemented for {args.purpose}")
    report.update({
        "source_id": source["id"],
        "source_revision": source["revision"],
        "evidence_level": source["evidence_level"],
        "purpose": args.purpose,
    })
    report.setdefault(
        "interpretation",
        "This measures chart-output agreement only. It does not measure or "
        "establish future-event, career, or wealth prediction accuracy.",
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
