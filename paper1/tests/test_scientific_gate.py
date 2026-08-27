from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from paper1.experiments.covol.scientific_gate import (
    KNOWN_ACTIONS,
    load_scientific_authorization,
    require_covol_action_authorized,
    require_scientific_action_authorized,
    resolve_scientific_authorization,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CURRENT_GATE = REPOSITORY_ROOT / "paper1/artifacts/covol/covol_scientific_gate.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("action", sorted(KNOWN_ACTIONS))
def test_current_gate_stops_every_downstream_action(action: str) -> None:
    result = load_scientific_authorization(CURRENT_GATE, action=action)

    assert result.status == "STOPPED_BY_H_SENSITIVITY"
    assert result.evidence_status == "STOP_H_SENSITIVITY"
    assert result.exit_code == 4
    assert not result.authorized
    with pytest.raises(SystemExit) as stopped:
        require_scientific_action_authorized(CURRENT_GATE, action=action)
    assert stopped.value.code == 4


def test_fake_step003_pass_cannot_bypass_scientific_stop(tmp_path: Path) -> None:
    fake_step003 = tmp_path / "step003.json"
    fake_step003.write_text("{}\n", encoding="utf-8")

    with pytest.raises(SystemExit) as stopped:
        require_covol_action_authorized(
            step003_authorization_path=fake_step003,
            scientific_gate_path=CURRENT_GATE,
            scientific_action="step005",
            step003_action="step005",
        )
    assert stopped.value.code == 4


def test_tampered_summary_is_rejected(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    csv_path = tmp_path / "rows.csv"
    csv_path.write_text("value\n1\n", encoding="utf-8")
    summary.write_text(
        json.dumps(
            {"status": "PASS_H_SENSITIVITY", "output_sha256": _sha256(csv_path)}
        ),
        encoding="utf-8",
    )
    payload = {
        "schema_version": "covol-scientific-gate-v1",
        "stopped_exit_code": 4,
        "status": "STOPPED_BY_H_SENSITIVITY_CONTROL",
        "decision": "ARCHIVE_GT_TEMPLATE_PROBE_AND_MAIN_PR_PATH",
        "evidence": {
            "summary_path": summary.name,
            "summary_sha256": _sha256(summary),
            "csv_path": csv_path.name,
            "csv_sha256": _sha256(csv_path),
        },
        "actions": {action: False for action in KNOWN_ACTIONS},
    }

    with pytest.raises(ValueError, match="frozen STOP"):
        resolve_scientific_authorization(
            payload, action="step005", repository_root=tmp_path
        )


def test_declared_true_action_cannot_reopen_frozen_stop() -> None:
    payload = json.loads(CURRENT_GATE.read_text(encoding="utf-8"))
    payload["actions"]["step005"] = True

    with pytest.raises(ValueError, match="must be false"):
        resolve_scientific_authorization(payload, action="step005")
