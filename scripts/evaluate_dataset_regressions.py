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

    if args.purpose == "bazi_chart_regression":
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
