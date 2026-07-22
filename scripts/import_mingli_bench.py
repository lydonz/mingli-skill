#!/usr/bin/env python3
"""Import chart fixtures from a pinned local MingLi-Bench checkout.

The benchmark's multiple-choice answers describe historical events. They are
intentionally not imported or scored here. Only its precomputed iztro chart
fields are retained for deterministic calendar and Ziwei regression checks.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.dataset_registry import get_source, require_allowed_use, sha256_file


def _require_dict(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    return value


def _star_names(stars: Any, label: str) -> list[str]:
    return [
        str(_require_dict(star, label).get("name", ""))
        for star in _require_list(stars, label)
    ]


def _normalize_fixture(source_fixture: Dict[str, Any]) -> Dict[str, Any]:
    """Return only deterministic chart fields, excluding raw questions/answers."""
    case_id = str(source_fixture.get("case_id", "")).strip()
    if not case_id:
        raise ValueError("MingLi-Bench fixture is missing case_id")
    birth = _require_dict(source_fixture.get("birth_info"), f"{case_id}.birth_info")
    response = _require_dict(
        source_fixture.get("api_response"), f"{case_id}.api_response"
    )
    if not response.get("success"):
        raise ValueError(f"{case_id} has no successful precomputed chart")
    response_data = _require_dict(response.get("data"), f"{case_id}.api_response.data")
    chart = _require_dict(response_data.get("data"), f"{case_id}.chart")

    try:
        birthday = datetime(
            int(birth["year"]),
            int(birth["month"]),
            int(birth["day"]),
            int(birth["hour"]),
            int(birth.get("minute", 0)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{case_id} has invalid civil birth fields") from exc
    gender = str(birth.get("gender", "")).strip()
    if gender not in {"男", "女"}:
        raise ValueError(f"{case_id} has unsupported gender {gender!r}")

    pillars = str(chart.get("chineseDate", "")).split()
    if len(pillars) != 4 or any(len(pillar) != 2 for pillar in pillars):
        raise ValueError(f"{case_id} has invalid chineseDate")

    expected_palaces = {}
    for palace_value in _require_list(chart.get("palaces"), f"{case_id}.palaces"):
        palace = _require_dict(palace_value, f"{case_id}.palace")
        name = str(palace.get("name", "")).strip()
        branch = str(palace.get("earthlyBranch", "")).strip()
        if not name or not branch:
            raise ValueError(f"{case_id} has a palace without name or branch")
        if name in expected_palaces:
            raise ValueError(f"{case_id} has duplicate palace {name}")
        expected_palaces[name] = {
            "earthly_branch": branch,
            "major_stars": _star_names(
                palace.get("majorStars"), f"{case_id}.{name}.majorStars"
            ),
            "minor_stars": _star_names(
                palace.get("minorStars"), f"{case_id}.{name}.minorStars"
            ),
        }
    if len(expected_palaces) != 12:
        raise ValueError(f"{case_id} must contain 12 palaces")

    return {
        "case_id": case_id,
        "input": {
            "civil_birth_time": birthday.isoformat(timespec="minutes"),
            "gender": gender,
        },
        "expected": {
            "four_pillars": pillars,
            "ziwei": {
                "lunar_date": str(chart.get("lunarDate", "")),
                "soul_palace_branch": str(
                    chart.get("earthlyBranchOfSoulPalace", "")
                ),
                "body_palace_branch": str(
                    chart.get("earthlyBranchOfBodyPalace", "")
                ),
                "five_elements_class": str(chart.get("fiveElementsClass", "")),
                "zodiac": str(chart.get("zodiac", "")),
                "palaces": expected_palaces,
            },
        },
        "source_limitations": [
            "The source location text is intentionally omitted because it does "
            "not provide normalized coordinates for true-solar-time validation.",
            "MingLi-Bench event questions and answer keys are intentionally "
            "not imported or used as prediction ground truth.",
        ],
    }


def _checkout_revision(source_dir: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(source_dir), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "source-dir must be a Git checkout so its immutable revision can "
            "be verified."
        )
    return result.stdout.strip()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}") from exc


def import_chart_fixtures(
    source_dir: Path,
    output_dir: Path,
    source: Dict[str, Any],
    purpose: str,
) -> Dict[str, Any]:
    """Normalize one pinned checkout and return provenance metadata."""
    require_allowed_use(source, purpose)
    if purpose not in {"bazi_chart_regression", "ziwei_chart_regression"}:
        raise PermissionError(
            "MingLi-Bench chart import only supports bazi_chart_regression or "
            "ziwei_chart_regression; event-answer scoring is not supported."
        )

    source_dir = source_dir.resolve()
    revision = _checkout_revision(source_dir)
    if revision != source["revision"]:
        raise ValueError(
            f"MingLi-Bench revision mismatch: expected {source['revision']}, "
            f"got {revision}"
        )

    questions_path = source_dir / "data" / "data.json"
    charts_path = source_dir / "data" / "fortune_api_results.json"
    questions = _require_dict(_read_json(questions_path), "data.json")
    chart_fixtures = _require_list(
        _read_json(charts_path), "fortune_api_results.json"
    )
    normalized = [_normalize_fixture(item) for item in chart_fixtures]
    case_ids = [item["case_id"] for item in normalized]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("MingLi-Bench contains duplicate chart fixture case_id values")

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "chart-fixtures.jsonl"
    metadata_path = output_dir / "metadata.json"
    with records_path.open("w", encoding="utf-8") as output:
        for index, record in enumerate(normalized):
            output.write(json.dumps({
                "source_id": source["id"],
                "source_revision": source["revision"],
                "license": source["license"],
                "evidence_level": source["evidence_level"],
                "record_index": index,
                "record": record,
            }, ensure_ascii=False, sort_keys=True) + "\n")

    question_categories = Counter(
        str(question.get("category", "unknown"))
        for question in _require_list(questions.get("questions"), "questions")
        if isinstance(question, dict)
    )
    metadata = {
        "source_id": source["id"],
        "repository": source["repository"],
        "revision": source["revision"],
        "license": source["license"],
        "evidence_level": source["evidence_level"],
        "purpose": purpose,
        "records": len(normalized),
        "records_file": str(records_path),
        "records_sha256": sha256_file(records_path),
        "source_files": {
            "questions": {
                "path": str(questions_path),
                "sha256": sha256_file(questions_path),
                "question_count": sum(question_categories.values()),
                "category_counts": dict(sorted(question_categories.items())),
            },
            "chart_fixtures": {
                "path": str(charts_path),
                "sha256": sha256_file(charts_path),
                "chart_fixture_count": len(normalized),
            },
        },
        "event_answer_handling": (
            "Question text, options, and answers are not included in the "
            "normalized records and are not scored."
        ),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "datasets" / "cache" / "mingli-bench",
    )
    parser.add_argument(
        "--purpose",
        required=True,
        choices=("bazi_chart_regression", "ziwei_chart_regression"),
    )
    args = parser.parse_args()

    source = get_source("mingli-bench")
    metadata = import_chart_fixtures(
        args.source_dir, args.output_dir, source, args.purpose
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
