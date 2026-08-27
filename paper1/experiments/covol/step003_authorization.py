"""Hard authorization boundary between Step003 and downstream experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BLOCKED_EXIT_CODE = 3
FORMAL_ACTIONS = frozenset(
    {
        "step004_b",
        "step005",
        "step006",
        "step007",
        "step008",
        "official_test",
    }
)
DIAGNOSTIC_ACTIONS = frozenset(
    {
        "second_dataset_audit",
        "kitti_oracle_gap_audit",
        "nyuv2_diagnostic_corpus",
        "nyuv2_h_sensitivity",
    }
)
KNOWN_ACTIONS = FORMAL_ACTIONS | DIAGNOSTIC_ACTIONS


@dataclass(frozen=True)
class ActionAuthorization:
    """Resolved permission for one named research action."""

    action: str
    status: str
    decision: str
    authorized: bool
    exit_code: int


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
    path = Path(str(relative_path).strip())
    if not str(path) or path.is_absolute():
        raise ValueError("source coverage path must be repository-relative")
    root = repository_root.resolve(strict=True)
    resolved = (root / path).resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("source coverage path escapes repository root") from error
    if not resolved.is_file():
        raise ValueError("source coverage path is not a file")
    return resolved


def resolve_action_authorization(
    authorization: Mapping[str, Any],
    *,
    action: str,
    repository_root: Path = REPOSITORY_ROOT,
) -> ActionAuthorization:
    """Validate source lineage and resolve one diagnostic or formal action."""

    if action not in KNOWN_ACTIONS:
        raise ValueError(f"unknown Step003 action: {action!r}")
    if authorization.get("schema_version") != "covol-step003-authorization-v1":
        raise ValueError("unsupported Step003 authorization schema")
    if authorization.get("blocked_exit_code") != BLOCKED_EXIT_CODE:
        raise ValueError("blocked_exit_code must be 3")

    source = authorization.get("source_coverage")
    if not isinstance(source, Mapping):
        raise ValueError("authorization must bind a source_coverage object")
    coverage_path = _repository_file(repository_root, source.get("path"))
    expected_sha = str(source.get("sha256", ""))
    if _sha256(coverage_path) != expected_sha:
        raise ValueError("source coverage SHA256 mismatch")
    coverage = _read_object(coverage_path)

    action_flags = authorization.get("actions")
    if not isinstance(action_flags, Mapping):
        raise ValueError("authorization actions must be an object")
    declared = action_flags.get(action)
    if not isinstance(declared, bool):
        raise ValueError(f"authorization lacks boolean action {action!r}")

    decision = str(authorization.get("decision", "")).strip()
    if action in DIAGNOSTIC_ACTIONS:
        authorized = declared
        return ActionAuthorization(
            action=action,
            status="AUTHORIZED_DIAGNOSTIC" if authorized else "BLOCKED_BY_SCOPE",
            decision=decision,
            authorized=authorized,
            exit_code=0 if authorized else BLOCKED_EXIT_CODE,
        )

    coverage_claim = coverage.get("claim_dataset_decision")
    if not isinstance(coverage_claim, Mapping):
        raise ValueError("source coverage lacks claim_dataset_decision")
    coverage_decision = str(coverage_claim.get("decision", "")).strip()
    coverage_datasets = coverage_claim.get("local_claim_datasets")
    formal_datasets = authorization.get("formal_claim_datasets")
    datasets_match = (
        isinstance(coverage_datasets, list)
        and isinstance(formal_datasets, list)
        and [str(value) for value in coverage_datasets]
        == [str(value) for value in formal_datasets]
    )
    formal_gate_pass = (
        declared
        and authorization.get("status") == "PASS"
        and str(coverage.get("status", "")) == "PASS"
        and decision.startswith("GO_LOCAL_CLAIMS_")
        and coverage_decision == decision
        and datasets_match
        and len(formal_datasets) >= 2
    )
    return ActionAuthorization(
        action=action,
        status="AUTHORIZED_FORMAL" if formal_gate_pass else "BLOCKED_BY_STEP003",
        decision=decision,
        authorized=formal_gate_pass,
        exit_code=0 if formal_gate_pass else BLOCKED_EXIT_CODE,
    )


def load_action_authorization(
    authorization_path: Path,
    *,
    action: str,
    repository_root: Path = REPOSITORY_ROOT,
) -> ActionAuthorization:
    """Load and resolve a hash-linked Step003 authorization artifact."""

    return resolve_action_authorization(
        _read_object(authorization_path),
        action=action,
        repository_root=repository_root,
    )


def require_action_authorized(
    authorization_path: Path,
    *,
    action: str,
    repository_root: Path = REPOSITORY_ROOT,
) -> ActionAuthorization:
    """Raise SystemExit(3) when a valid artifact does not authorize the action."""

    result = load_action_authorization(
        authorization_path,
        action=action,
        repository_root=repository_root,
    )
    if not result.authorized:
        raise SystemExit(result.exit_code)
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--action", choices=sorted(KNOWN_ACTIONS), required=True)
    parser.add_argument("--repository-root", type=Path, default=REPOSITORY_ROOT)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        result = load_action_authorization(
            args.authorization,
            action=args.action,
            repository_root=args.repository_root,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"INVALID_STEP003_AUTHORIZATION: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    print(json.dumps(asdict(result), sort_keys=True))
    raise SystemExit(result.exit_code)


if __name__ == "__main__":
    main()
