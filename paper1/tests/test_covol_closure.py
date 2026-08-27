from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from paper1.experiments.covol.scientific_gate import KNOWN_ACTIONS
from paper1.experiments.covol.validate_covol_closure import (
    ARCHIVED_STATUS,
    validate_covol_closure,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(root: Path) -> dict[str, object]:
    roles = (
        "scientific_gate",
        "sensitivity_rows",
        "sensitivity_summary",
        "intervention_validity",
        "family_artifact_control",
        "direct_postmortem",
        "practical_effects_postmortem",
        "closure_note",
    )
    artifacts = []
    for index, role in enumerate(roles):
        path = root / f"artifact-{index}.txt"
        path.write_text(role, encoding="utf-8")
        artifacts.append({"path": path.name, "sha256": _sha256(path), "role": role})
    external = root / "raw.jsonl"
    external.write_text("{}\n", encoding="utf-8")
    return {
        "schema_version": "covol-closure-manifest-v1",
        "status": ARCHIVED_STATUS,
        "scientific_scope": {
            "actual_input": "DETERMINISTIC_NYUV2_GT_RELATION_TEMPLATES",
            "automatic_caption_question": "UNTESTED",
            "human_naturalness": "NOT_ASSESSED",
        },
        "actions": {action: False for action in KNOWN_ACTIONS},
        "tracked_artifacts": artifacts,
        "rebuildable_external_inputs": [
            {
                "path": external.name,
                "sha256": _sha256(external),
                "rebuildable": True,
            }
        ],
        "supersedes": [
            {
                "path": "old.json",
                "prior_status": "PENDING_INDEPENDENT_PRECISION_AND_H_SENSITIVITY",
            }
        ],
    }


def test_closure_validates_hashes_actions_and_scope(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)

    result = validate_covol_closure(manifest, repository_root=tmp_path)

    assert result["tracked_artifact_count"] == 8
    assert result["locally_verified_external_input_count"] == 1
    assert result["authorized_action_count"] == 0


def test_closure_rejects_tampering_and_overbroad_scope(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    (tmp_path / "artifact-1.txt").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        validate_covol_closure(manifest, repository_root=tmp_path)

    manifest = _manifest(tmp_path)
    manifest["scientific_scope"]["automatic_caption_question"] = "FALSIFIED"
    with pytest.raises(ValueError, match="automatic captions"):
        validate_covol_closure(manifest, repository_root=tmp_path)
