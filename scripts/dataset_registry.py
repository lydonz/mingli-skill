"""Dataset provenance and purpose policy for MingLi Skill evaluations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "datasets" / "manifest.json"
REQUIRED_SOURCE_FIELDS = {
    "id",
    "provider",
    "repository",
    "revision",
    "license",
    "evidence_level",
    "allowed_uses",
    "prohibited_uses",
}


def load_manifest(path: Path = DEFAULT_MANIFEST) -> Dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: Dict[str, Any]) -> None:
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported dataset manifest schema_version")
    source_ids = set()
    for source in manifest.get("sources", []):
        missing = REQUIRED_SOURCE_FIELDS - source.keys()
        if missing:
            raise ValueError(f"Dataset {source.get('id', '<unknown>')} missing {sorted(missing)}")
        source_id = source["id"]
        if source_id in source_ids:
            raise ValueError(f"Duplicate dataset id: {source_id}")
        source_ids.add(source_id)
        if not source["revision"] or len(source["revision"]) < 7:
            raise ValueError(f"Dataset {source_id} must pin an immutable revision")
        if not source["allowed_uses"]:
            raise ValueError(f"Dataset {source_id} must declare allowed uses")
        prohibited = set(source["prohibited_uses"])
        if "event_prediction_accuracy_claim" not in prohibited:
            raise ValueError(
                f"Dataset {source_id} must prohibit event prediction accuracy claims"
            )


def get_source(source_id: str, path: Path = DEFAULT_MANIFEST) -> Dict[str, Any]:
    for source in load_manifest(path)["sources"]:
        if source["id"] == source_id:
            return source
    raise KeyError(f"Unknown dataset source: {source_id}")


def require_allowed_use(source: Dict[str, Any], purpose: str) -> None:
    if purpose not in source["allowed_uses"]:
        raise PermissionError(
            f"{source['id']} is not approved for {purpose}; "
            f"allowed uses: {', '.join(source['allowed_uses'])}"
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
