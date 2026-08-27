"""Validate the unique hash-linked closure manifest for archived CoVoL work."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from paper1.experiments.covol.scientific_gate import KNOWN_ACTIONS

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ARCHIVED_STATUS = "STOPPED_BY_H_SENSITIVITY_CONTROL"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repository_path(repository_root: Path, value: object, *, must_exist: bool) -> Path:
    relative = Path(str(value).strip())
    if not str(relative) or relative.is_absolute():
        raise ValueError("closure paths must be nonempty and repository-relative")
    root = repository_root.resolve(strict=True)
    candidate = (root / relative).resolve(strict=must_exist)
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("closure path escapes repository root") from error
    return candidate


def _items(value: object, *, name: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a nonempty list")
    if not all(isinstance(item, Mapping) for item in value):
        raise ValueError(f"{name} entries must be objects")
    return value


def validate_covol_closure(
    manifest: Mapping[str, Any],
    *,
    repository_root: Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    """Validate closure status, action stops, artifact identities, and scope."""

    if manifest.get("schema_version") != "covol-closure-manifest-v1":
        raise ValueError("unsupported CoVoL closure schema")
    if manifest.get("status") != ARCHIVED_STATUS:
        raise ValueError("closure manifest lacks the frozen archive status")
    scope = manifest.get("scientific_scope")
    if not isinstance(scope, Mapping):
        raise ValueError("closure manifest lacks scientific_scope")
    if scope.get("actual_input") != "DETERMINISTIC_NYUV2_GT_RELATION_TEMPLATES":
        raise ValueError("closure must name the actual diagnostic input")
    if scope.get("automatic_caption_question") != "UNTESTED":
        raise ValueError("closure must not generalize to automatic captions")
    if scope.get("human_naturalness") != "NOT_ASSESSED":
        raise ValueError("closure must preserve the human-naturalness limitation")

    actions = manifest.get("actions")
    if not isinstance(actions, Mapping) or set(actions) != set(KNOWN_ACTIONS):
        raise ValueError("closure actions must exactly cover every scientific action")
    if any(actions[action] is not False for action in KNOWN_ACTIONS):
        raise ValueError("every archived CoVoL action must be false")

    tracked = _items(manifest.get("tracked_artifacts"), name="tracked_artifacts")
    seen_paths: set[str] = set()
    roles: set[str] = set()
    for item in tracked:
        relative = str(item.get("path", ""))
        if relative in seen_paths:
            raise ValueError(f"duplicate tracked artifact path: {relative}")
        path = _repository_path(repository_root, relative, must_exist=True)
        if not path.is_file():
            raise ValueError(f"tracked artifact is not a file: {relative}")
        if _sha256(path) != str(item.get("sha256", "")):
            raise ValueError(f"tracked artifact SHA256 mismatch: {relative}")
        role = str(item.get("role", "")).strip()
        if not role:
            raise ValueError(f"tracked artifact lacks a role: {relative}")
        seen_paths.add(relative)
        roles.add(role)
    required_roles = {
        "scientific_gate",
        "sensitivity_rows",
        "sensitivity_summary",
        "intervention_validity",
        "family_artifact_control",
        "direct_postmortem",
        "practical_effects_postmortem",
        "closure_note",
    }
    if not required_roles <= roles:
        raise ValueError("closure manifest is missing required artifact roles")

    external = manifest.get("rebuildable_external_inputs", [])
    if not isinstance(external, list):
        raise ValueError("rebuildable_external_inputs must be a list")
    locally_verified = 0
    for item in external:
        if not isinstance(item, Mapping) or item.get("rebuildable") is not True:
            raise ValueError("external inputs must be rebuildable objects")
        path = _repository_path(repository_root, item.get("path"), must_exist=False)
        if path.exists():
            if not path.is_file() or _sha256(path) != str(item.get("sha256", "")):
                raise ValueError(f"external input SHA256 mismatch: {item.get('path')}")
            locally_verified += 1

    supersedes = manifest.get("supersedes")
    if not isinstance(supersedes, list) or not supersedes:
        raise ValueError("closure manifest must name superseded diagnostic state")
    if not any(
        isinstance(item, Mapping)
        and item.get("prior_status")
        == "PENDING_INDEPENDENT_PRECISION_AND_H_SENSITIVITY"
        for item in supersedes
    ):
        raise ValueError("closure must supersede the old pending diagnostic artifact")
    return {
        "status": ARCHIVED_STATUS,
        "tracked_artifact_count": len(tracked),
        "rebuildable_external_input_count": len(external),
        "locally_verified_external_input_count": locally_verified,
        "authorized_action_count": 0,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=REPOSITORY_ROOT)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        value = json.loads(args.manifest.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("closure manifest must contain a JSON object")
        result = validate_covol_closure(value, repository_root=args.repository_root)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"INVALID_COVOL_CLOSURE: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
