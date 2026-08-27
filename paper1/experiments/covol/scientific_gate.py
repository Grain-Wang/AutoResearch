"""Global scientific stop boundary for every archived CoVoL downstream action."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from paper1.experiments.covol.step003_authorization import (
        ActionAuthorization,
        require_action_authorized,
    )
except ModuleNotFoundError:  # Direct script consumers in this directory.
    from step003_authorization import (  # type: ignore
        ActionAuthorization,
        require_action_authorized,
    )

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCIENTIFIC_GATE = Path("paper1/artifacts/covol/covol_scientific_gate.json")
STOPPED_EXIT_CODE = 4
STOPPED_STATUS = "STOPPED_BY_H_SENSITIVITY"
KNOWN_ACTIONS = frozenset(
    {
        "second_dataset_recovery",
        "step004_b",
        "step005",
        "step006",
        "step007",
        "step008",
        "official_test",
    }
)


@dataclass(frozen=True)
class ScientificAuthorization:
    """Resolved global permission for one archived CoVoL action."""

    action: str
    status: str
    authorized: bool
    exit_code: int
    evidence_status: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _repository_file(repository_root: Path, relative_path: object) -> Path:
    candidate = Path(str(relative_path).strip())
    if not str(candidate) or candidate.is_absolute():
        raise ValueError("scientific evidence path must be repository-relative")
    root = repository_root.resolve(strict=True)
    resolved = (root / candidate).resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("scientific evidence path escapes repository root") from error
    if not resolved.is_file():
        raise ValueError("scientific evidence path is not a file")
    return resolved


def resolve_scientific_authorization(
    gate: Mapping[str, Any],
    *,
    action: str,
    repository_root: Path = REPOSITORY_ROOT,
) -> ScientificAuthorization:
    """Validate the locked 004-A lineage and resolve a downstream action."""

    if action not in KNOWN_ACTIONS:
        raise ValueError(f"unknown CoVoL scientific action: {action!r}")
    if gate.get("schema_version") != "covol-scientific-gate-v1":
        raise ValueError("unsupported CoVoL scientific gate schema")
    if gate.get("stopped_exit_code") != STOPPED_EXIT_CODE:
        raise ValueError("stopped_exit_code must be 4")

    evidence = gate.get("evidence")
    if not isinstance(evidence, Mapping):
        raise ValueError("scientific gate must bind an evidence object")
    summary_path = _repository_file(repository_root, evidence.get("summary_path"))
    csv_path = _repository_file(repository_root, evidence.get("csv_path"))
    if _sha256(summary_path) != str(evidence.get("summary_sha256", "")):
        raise ValueError("sensitivity summary SHA256 mismatch")
    if _sha256(csv_path) != str(evidence.get("csv_sha256", "")):
        raise ValueError("sensitivity CSV SHA256 mismatch")
    summary = _read_object(summary_path)
    if summary.get("status") != "STOP_H_SENSITIVITY":
        raise ValueError("sensitivity summary does not contain the frozen STOP")
    if summary.get("output_sha256") != evidence.get("csv_sha256"):
        raise ValueError("sensitivity summary does not bind the declared CSV")

    actions = gate.get("actions")
    if not isinstance(actions, Mapping) or set(actions) != set(KNOWN_ACTIONS):
        raise ValueError("scientific gate actions must exactly match known actions")
    if any(actions[known_action] is not False for known_action in KNOWN_ACTIONS):
        raise ValueError("every action in the stopped scientific gate must be false")
    if gate.get("status") != "STOPPED_BY_H_SENSITIVITY_CONTROL":
        raise ValueError("scientific gate lacks the frozen stop status")
    if gate.get("decision") != "ARCHIVE_GT_TEMPLATE_PROBE_AND_MAIN_PR_PATH":
        raise ValueError("scientific gate lacks the frozen archive decision")
    return ScientificAuthorization(
        action=action,
        status=STOPPED_STATUS,
        authorized=False,
        exit_code=STOPPED_EXIT_CODE,
        evidence_status=str(summary["status"]),
    )


def load_scientific_authorization(
    gate_path: Path,
    *,
    action: str,
    repository_root: Path = REPOSITORY_ROOT,
) -> ScientificAuthorization:
    """Load and validate the global scientific gate."""

    return resolve_scientific_authorization(
        _read_object(gate_path), action=action, repository_root=repository_root
    )


def require_scientific_action_authorized(
    gate_path: Path,
    *,
    action: str,
    repository_root: Path = REPOSITORY_ROOT,
) -> ScientificAuthorization:
    """Raise ``SystemExit(4)`` for every action stopped by the 004-A result."""

    result = load_scientific_authorization(
        gate_path, action=action, repository_root=repository_root
    )
    if not result.authorized:
        raise SystemExit(result.exit_code)
    return result


def require_covol_action_authorized(
    *,
    step003_authorization_path: Path,
    scientific_gate_path: Path,
    scientific_action: str,
    step003_action: str,
    repository_root: Path = REPOSITORY_ROOT,
) -> ActionAuthorization:
    """Require both the final scientific gate and the historical Step003 gate."""

    require_scientific_action_authorized(
        scientific_gate_path,
        action=scientific_action,
        repository_root=repository_root,
    )
    return require_action_authorized(
        step003_authorization_path,
        action=step003_action,
        repository_root=repository_root,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, default=DEFAULT_SCIENTIFIC_GATE)
    parser.add_argument("--action", choices=sorted(KNOWN_ACTIONS), required=True)
    parser.add_argument("--repository-root", type=Path, default=REPOSITORY_ROOT)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        result = load_scientific_authorization(
            args.gate,
            action=args.action,
            repository_root=args.repository_root,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"INVALID_COVOL_SCIENTIFIC_GATE: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    print(json.dumps(asdict(result), sort_keys=True))
    raise SystemExit(result.exit_code)


if __name__ == "__main__":
    main()
