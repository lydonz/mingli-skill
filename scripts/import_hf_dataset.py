#!/usr/bin/env python3
"""Import a pinned Hugging Face dataset split into provenance-preserving JSONL."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.dataset_registry import get_source, require_allowed_use, sha256_file


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _pillar_text(pillar: Dict[str, Any]) -> str:
    return f"{pillar.get('stem', '')}{pillar.get('branch', '')}"


def normalize(source_id: str, row: Dict[str, Any]) -> Dict[str, Any]:
    if source_id == "czuo03-bazi-calculate-rlvr":
        answer = str(row["answer"]).split()
        if len(answer) != 4 or any(len(pillar) != 2 for pillar in answer):
            raise ValueError(f"Invalid four-pillar answer: {row['answer']!r}")
        return {
            "input": {"birthday": _json_value(row["birthday"])},
            "expected": {"four_pillars": answer},
            "question": row["question"],
        }
    if source_id == "czuo03-bazi-reasoning-300":
        return {
            "question": row["question"],
            "synthetic_reasoning": row["reasoning"],
            "synthetic_answer": row["answer"],
        }
    if source_id == "amareshhebbar-bazi-sft":
        facts = row["facts"]
        return {
            "example_id": row["example_id"],
            "input": _json_value(facts["birth_input"]),
            "reported_pillars": {
                name: _pillar_text(pillar)
                for name, pillar in facts["pillars"].items()
            },
            "question_type": row["question_type"],
            "question": row["user_question"],
            "synthetic_response": row["response"],
            "citations": row["citations"],
        }
    raise KeyError(f"No normalization adapter for {source_id}")


def read_parquet(path: Path) -> Iterable[Dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError(
            "Parquet import requires pyarrow. Run `python3 -m pip install -r requirements.txt`."
        ) from exc
    return pq.read_table(path).to_pylist()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--input", type=Path, help="Use an already-downloaded parquet file.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "datasets" / "cache")
    parser.add_argument("--max-rows", type=int)
    args = parser.parse_args()

    source = get_source(args.source_id)
    if source["provider"] != "huggingface":
        raise ValueError(f"{args.source_id} is not a Hugging Face source")
    require_allowed_use(source, args.purpose)
    split_path = source.get("splits", {}).get(args.split)
    if not split_path:
        raise ValueError(f"{args.source_id} does not expose split {args.split!r}")

    destination_dir = args.output_dir / args.source_id / source["revision"] / args.split
    parquet_path = args.input or destination_dir / Path(split_path).name
    if args.input is None:
        url = (
            f"https://huggingface.co/datasets/{source['repository']}/resolve/"
            f"{source['revision']}/{split_path}"
        )
        download(url, parquet_path)

    rows = list(read_parquet(parquet_path))
    actual_columns = set(rows[0]) if rows else set()
    required_columns = set(source.get("expected_columns", []))
    if not required_columns.issubset(actual_columns):
        raise ValueError(
            f"Unexpected schema for {args.source_id}: missing "
            f"{sorted(required_columns - actual_columns)}"
        )
    if args.max_rows is not None:
        rows = rows[:args.max_rows]

    jsonl_path = destination_dir / "records.jsonl"
    metadata_path = destination_dir / "metadata.json"
    destination_dir.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as output:
        for index, row in enumerate(rows):
            record = {
                "source_id": source["id"],
                "source_revision": source["revision"],
                "license": source["license"],
                "evidence_level": source["evidence_level"],
                "record_index": index,
                "record": normalize(source["id"], row),
            }
            output.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    metadata = {
        "source_id": source["id"],
        "repository": source["repository"],
        "revision": source["revision"],
        "license": source["license"],
        "evidence_level": source["evidence_level"],
        "purpose": args.purpose,
        "split": args.split,
        "records": len(rows),
        "source_file": str(parquet_path),
        "source_sha256": sha256_file(parquet_path),
        "normalized_sha256": sha256_file(jsonl_path),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
