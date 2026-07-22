#!/usr/bin/env python3
"""Validate MingLi Skill chart output against MingLi-Bench iztro fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.calendar_engine import build_four_pillars, solar_to_lunar
from tools.ziwei_tools import ZiweiToolkit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark-root",
        required=True,
        help="Path to a checked-out DestinyLinker/MingLi-Bench repository.",
    )
    parser.add_argument("--output", help="Optional JSON report path.")
    parser.add_argument(
        "--year-boundary",
        choices=("lichun", "lunar_new_year"),
        default="lichun",
        help="Year-pillar convention used for Bazi comparison.",
    )
    args = parser.parse_args()

    fixture_path = Path(args.benchmark_root) / "data" / "fortune_api_results.json"
    fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
    ziwei = ZiweiToolkit()
    report = {
        "cases": len(fixtures),
        "lunar": {"matched": 0, "mismatches": []},
        "bazi": {"matched": 0, "mismatches": []},
        "ziwei": {
            "engine": "iztro",
            "soul_palace_matched": 0,
            "body_palace_matched": 0,
            "major_stars_matched": 0,
            "major_stars_total": 0,
            "mismatches": [],
        },
        "notes": [],
    }

    for fixture in fixtures:
        birth = fixture["birth_info"]
        reference = fixture["api_response"]["data"]["data"]
        case_id = fixture["case_id"]
        year, month, day = birth["year"], birth["month"], birth["day"]
        hour, minute = birth.get("hour", 12), birth.get("minute", 0)
        gender = birth["gender"]

        lunar = solar_to_lunar(year, month, day, hour, minute)
        reference_lunar = reference["rawDates"]["lunarDate"]
        lunar_actual = (
            lunar["year"], lunar["month"], lunar["day"], lunar["is_leap_month"]
        )
        lunar_expected = (
            reference_lunar["lunarYear"],
            reference_lunar["lunarMonth"],
            reference_lunar["lunarDay"],
            reference_lunar["isLeap"],
        )
        if lunar_actual == lunar_expected:
            report["lunar"]["matched"] += 1
        else:
            report["lunar"]["mismatches"].append({
                "case_id": case_id,
                "actual": lunar_actual,
                "expected": lunar_expected,
            })

        four_pillars = build_four_pillars(
            year, month, day, hour, gender=gender, minute=minute,
            year_boundary=args.year_boundary,
        )
        bazi_actual = "".join(four_pillars["四柱"].values())
        bazi_expected = reference["chineseDate"].replace(" ", "")
        if bazi_actual == bazi_expected:
            report["bazi"]["matched"] += 1
        else:
            report["bazi"]["mismatches"].append({
                "case_id": case_id,
                "actual": bazi_actual,
                "expected": bazi_expected,
            })

        actual = json.loads(ziwei.paipan(year, month, day, hour, gender))
        if actual.get("排盘引擎") != "iztro":
            raise RuntimeError("iztro backend unavailable; cannot validate Ziwei.")

        expected_soul = reference["earthlyBranchOfSoulPalace"]
        expected_body = reference["earthlyBranchOfBodyPalace"]
        actual_soul = actual["命宫"]["地支"]
        actual_body = actual["十二宫"][actual["身宫"]]["宫位地支"]
        report["ziwei"]["soul_palace_matched"] += actual_soul == expected_soul
        report["ziwei"]["body_palace_matched"] += actual_body == expected_body

        expected_stars = {
            star["name"]: palace["earthlyBranch"]
            for palace in reference["palaces"]
            for star in palace.get("majorStars", [])
        }
        actual_stars = {
            star: palace["宫位地支"]
            for palace in actual["十二宫"].values()
            for star in palace["主星"]
        }
        case_star_matches = sum(
            actual_stars.get(star) == branch
            for star, branch in expected_stars.items()
        )
        report["ziwei"]["major_stars_matched"] += case_star_matches
        report["ziwei"]["major_stars_total"] += len(expected_stars)
        if (
            actual_soul != expected_soul
            or actual_body != expected_body
            or case_star_matches != len(expected_stars)
        ):
            report["ziwei"]["mismatches"].append({
                "case_id": case_id,
                "soul": {"actual": actual_soul, "expected": expected_soul},
                "body": {"actual": actual_body, "expected": expected_body},
                "major_stars": {
                    "matched": case_star_matches,
                    "total": len(expected_stars),
                },
            })

    report["ziwei"]["major_star_accuracy"] = (
        report["ziwei"]["major_stars_matched"] / report["ziwei"]["major_stars_total"]
        if report["ziwei"]["major_stars_total"] else 0
    )
    report["bazi"]["year_boundary"] = args.year_boundary
    if report["bazi"]["mismatches"]:
        report["notes"].append(
            "Bazi reference data may use lunar-new-year year pillars for dates "
            "before Chinese New Year; the skill uses the conventional 立春 boundary."
        )
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")

    ziwei_ok = (
        report["ziwei"]["soul_palace_matched"] == report["cases"]
        and report["ziwei"]["body_palace_matched"] == report["cases"]
        and report["ziwei"]["major_stars_matched"] == report["ziwei"]["major_stars_total"]
    )
    return 0 if ziwei_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
