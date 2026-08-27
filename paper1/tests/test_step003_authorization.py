from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from paper1.experiments.covol.step003_authorization import (
    BLOCKED_EXIT_CODE,
    FORMAL_ACTIONS,
    load_action_authorization,
    require_action_authorized,
    resolve_action_authorization,
)

CURRENT_AUTHORIZATION = Path("paper1/artifacts/covol/step003_authorization.json")


@pytest.mark.parametrize("action", sorted(FORMAL_ACTIONS))
def test_current_stop_artifact_blocks_every_formal_entry(action: str) -> None:
    result = load_action_authorization(CURRENT_AUTHORIZATION, action=action)

    assert result.status == "BLOCKED_BY_STEP003"
    assert result.exit_code == BLOCKED_EXIT_CODE
    with pytest.raises(SystemExit) as error:
        require_action_authorized(CURRENT_AUTHORIZATION, action=action)
    assert error.value.code == BLOCKED_EXIT_CODE


def test_failed_coverage_nonempty_dataset_array_cannot_bypass_gate() -> None:
    result = load_action_authorization(CURRENT_AUTHORIZATION, action="step005")

    coverage = json.loads(
        Path("paper1/results/covol/annotation_coverage.json").read_text()
    )
    assert coverage["claim_dataset_decision"]["local_claim_datasets"] == ["NYUv2"]
    assert not result.authorized


def test_current_scope_explicitly_allows_train_only_diagnostics() -> None:
    for action in (
        "second_dataset_audit",
        "kitti_oracle_gap_audit",
        "nyuv2_diagnostic_corpus",
        "nyuv2_h_sensitivity",
    ):
        result = load_action_authorization(CURRENT_AUTHORIZATION, action=action)
        assert result.status == "AUTHORIZED_DIAGNOSTIC"
        assert result.exit_code == 0


def test_source_coverage_hash_is_recomputed(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    source = root / "coverage.json"
    source.parent.mkdir(parents=True)
    source.write_text("{}\n", encoding="utf-8")
    authorization = {
        "schema_version": "covol-step003-authorization-v1",
        "blocked_exit_code": 3,
        "decision": "STOPPED_CURRENT_DATA_BRANCH",
        "source_coverage": {"path": "coverage.json", "sha256": "0" * 64},
        "actions": {"step005": False},
    }

    with pytest.raises(ValueError, match="source coverage SHA256 mismatch"):
        resolve_action_authorization(
            authorization,
            action="step005",
            repository_root=root,
        )


def test_hash_linked_two_dataset_pass_authorizes_formal_action(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    source = root / "coverage.json"
    source.parent.mkdir(parents=True)
    coverage = {
        "status": "PASS",
        "claim_dataset_decision": {
            "decision": "GO_LOCAL_CLAIMS_NYUV2_CITYSCAPES",
            "local_claim_datasets": ["NYUv2", "Cityscapes"],
        },
    }
    source.write_text(json.dumps(coverage) + "\n", encoding="utf-8")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    authorization = {
        "schema_version": "covol-step003-authorization-v1",
        "blocked_exit_code": 3,
        "status": "PASS",
        "decision": "GO_LOCAL_CLAIMS_NYUV2_CITYSCAPES",
        "formal_claim_datasets": ["NYUv2", "Cityscapes"],
        "source_coverage": {"path": "coverage.json", "sha256": source_sha},
        "actions": {"step005": True},
    }

    result = resolve_action_authorization(
        authorization,
        action="step005",
        repository_root=root,
    )

    assert result.status == "AUTHORIZED_FORMAL"
    assert result.exit_code == 0
