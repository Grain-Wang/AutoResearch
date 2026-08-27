"""Independently parse a stratified 100-row diagnostic predicate audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

AUDIT_PER_FAMILY = 25
FAMILIES = (
    "semantic_preserving",
    "target_deletion",
    "local_entity_conflict",
    "depth_relation_conflict",
)


def _stable_hash(row: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        "/".join(
            (
                "diagnostic-independent-audit-v1",
                str(row.get("image_id", "")),
                str(row.get("error_type", "")),
                str(row.get("variant_id", "")),
            )
        ).encode("utf-8")
    ).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            rows.append(value)
    return rows


def _evidence(row: Mapping[str, Any]) -> tuple[str, str, str, float, float]:
    value = row.get("machine_check")
    if not isinstance(value, Mapping):
        raise ValueError("audit row lacks machine-check evidence")
    near = str(value.get("near_class_name", "")).strip().casefold()
    far = str(value.get("far_class_name", "")).strip().casefold()
    distractor = str(value.get("absent_distractor", "")).strip().casefold()
    near_depth = float(value.get("near_depth_m"))
    far_depth = float(value.get("far_depth_m"))
    if not near or not far or not distractor or not near_depth < far_depth:
        raise ValueError("audit evidence lacks a valid near/far/distractor contract")
    return near, far, distractor, near_depth, far_depth


def independently_verify_predicate(row: Mapping[str, Any]) -> bool:
    """Verify caption polarity/content without reading generator pass/fail flags."""

    near, far, distractor, _, _ = _evidence(row)
    caption = str(row.get("intervention", "")).strip().casefold()
    family = str(row.get("error_type", ""))
    variant = int(row.get("variant_id", -1))
    has_near = near in caption
    has_far = far in caption
    has_distractor = distractor in caption
    if family == "semantic_preserving":
        patterns = (
            has_near and has_far and "closer" in caption,
            has_near and has_far and "shorter" in caption,
            has_near and has_far and "greater" in caption,
        )
        return 0 <= variant < 3 and patterns[variant] and not has_distractor
    if family == "target_deletion":
        no_relation = not any(
            token in caption for token in ("closer", "farther", "distance")
        )
        patterns = (
            has_far and not has_near,
            has_near and not has_far,
            has_near and has_far,
        )
        return 0 <= variant < 3 and no_relation and patterns[variant]
    if family == "local_entity_conflict":
        return (
            has_distractor
            and (has_near or has_far)
            and ("closer" in caption or "shorter" in caption)
        )
    if family == "depth_relation_conflict":
        patterns = (
            has_near and has_far and "greater" in caption,
            has_near and has_far and "farther" in caption,
            has_near and has_far and "closer" in caption,
        )
        return 0 <= variant < 3 and patterns[variant] and not has_distractor
    return False


def select_predicate_audit_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Select the frozen 25-row-per-family predicate audit sample."""

    selected = []
    for family in FAMILIES:
        family_rows = [row for row in rows if row.get("error_type") == family]
        if len(family_rows) < AUDIT_PER_FAMILY:
            raise ValueError(f"{family}: fewer than 25 rows for independent audit")
        selected.extend(sorted(family_rows, key=_stable_hash)[:AUDIT_PER_FAMILY])
    return selected


def audit_diagnostic_predicates(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Audit 25 stable-hash rows per family using an independent parser."""

    selected = select_predicate_audit_rows(rows)
    passed = [independently_verify_predicate(row) for row in selected]
    pass_count = sum(passed)
    precision = pass_count / len(selected)
    family_pass_counts = Counter(
        str(row["error_type"])
        for row, result in zip(selected, passed, strict=True)
        if result
    )
    audited_keys = sorted(
        f"{row['image_id']}/{row['error_type']}/{row['variant_id']}" for row in selected
    )
    return {
        "schema_version": "covol-diagnostic-independent-audit-v1",
        "status": (
            "PASS_PREDICATE_PRECISION_NATURALNESS_PENDING"
            if precision >= 0.95
            else "STOP_PREDICATE_PRECISION"
        ),
        "audit_method": "INDEPENDENT_RULE_PARSER_STRATIFIED_STABLE_HASH_SAMPLE",
        "audited_row_count": len(selected),
        "audited_row_set_sha256": hashlib.sha256(
            "\n".join(audited_keys).encode("utf-8")
        ).hexdigest(),
        "pass_count": pass_count,
        "predicate_precision": precision,
        "minimum_precision": 0.95,
        "family_audited_counts": {family: AUDIT_PER_FAMILY for family in FAMILIES},
        "family_pass_counts": {
            family: family_pass_counts[family] for family in FAMILIES
        },
        "naturalness_audit_status": "PENDING_NOT_ESTIMATED_BY_RULE_PARSER",
        "scientific_evidence": (
            "PREDICATE_VALIDITY_ONLY_NOT_CAPTION_NATURALNESS_OR_MODEL_EFFECT"
        ),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = audit_diagnostic_predicates(_read_jsonl(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if result["predicate_precision"] < result["minimum_precision"]:
        raise SystemExit(4)


if __name__ == "__main__":
    main()
