"""Build the frozen Step-003 pilot without reading official benchmark tests."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from paper1.experiments.covol.audit_provenance import (
    validate_trusted_training_source,
    verify_formal_power_failure,
)
from paper1.experiments.covol.build_image_manifest import (
    SPLIT_ORDER,
    _file_sha256,
    _select_scene_grouped,
    _validated_records,
)

PILOT_SEED = 20260821
PILOT_SPLIT_COUNTS = {"train": 300, "dev": 100, "internal_test": 100}
PILOT_STATUS = "PASS_PREFREEZE_NO_TEST_ACCESS"
PILOT_SCOPE = "STEP003_ONLY_NOT_STEP005_OR_OFFICIAL_TEST"
PILOT_SELECTION_STAGE = "PILOT_V1"
EXPANDED_SELECTION_STAGE = "EXPANDED_FOR_POWER"
PILOT_COMPONENT_CAPS = {"train": 60, "dev": 20, "internal_test": 5}
MINIMUM_INTERNAL_TEST_SCENES = 20


def _record_split_source_sha256(record: Mapping[str, Any], *, line_number: int) -> str:
    return validate_trusted_training_source(
        record,
        context=f"training source record {line_number}",
    )


def _split_source_sha256(records: Sequence[Mapping[str, Any]]) -> str:
    values = {
        _record_split_source_sha256(record, line_number=line_number)
        for line_number, record in enumerate(records, start=1)
    }
    if len(values) != 1:
        raise ValueError("one dataset training pool must use one split-source SHA256")
    return next(iter(values))


def _internal_overlap(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    fields = {
        "image_count": "image_id",
        "cluster_count": "cluster_id",
        "scene_count": "scene_id",
        "sequence_count": "sequence_id",
        "rgb_sha256_count": "rgb_sha256",
    }
    overlaps = {name: 0 for name in fields}
    split_values: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {split: set() for split in SPLIT_ORDER}
    )
    for record in records:
        split = str(record["split"])
        for output_name, field in fields.items():
            split_values[output_name][split].add(str(record[field]))

    for output_name in fields:
        by_split = split_values[output_name]
        for left_index, left in enumerate(SPLIT_ORDER):
            for right in SPLIT_ORDER[left_index + 1 :]:
                overlaps[output_name] += len(by_split[left] & by_split[right])
    if any(overlaps.values()):
        raise AssertionError(f"internal pilot leakage detected: {overlaps}")
    return overlaps


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            records.append(value)
    return records


def _read_json_mapping(path: Path, *, label: str) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _resolve_config_path(
    config: Mapping[str, Any],
    key: str,
    *,
    config_dir: Path,
) -> Path:
    value = str(config.get(key, "")).strip()
    if not value:
        raise ValueError(f"{EXPANDED_SELECTION_STAGE} requires {key}")
    path = (config_dir / value).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _validate_expansion_inputs(
    config: Mapping[str, Any],
    *,
    config_dir: Path,
) -> tuple[
    list[dict[str, Any]],
    Mapping[str, Any],
    dict[str, str],
    dict[str, Path],
]:
    parent_manifest_path = _resolve_config_path(
        config,
        "parent_manifest",
        config_dir=config_dir,
    )
    parent_audit_path = _resolve_config_path(
        config,
        "parent_split_audit",
        config_dir=config_dir,
    )
    trigger_power_path = _resolve_config_path(
        config,
        "trigger_power_audit",
        config_dir=config_dir,
    )
    parent_records = _read_jsonl(parent_manifest_path)
    parent_manifest_hash = _file_sha256(parent_manifest_path)
    parent_audit = _read_json_mapping(parent_audit_path, label="parent split audit")
    if parent_audit.get("status") != PILOT_STATUS:
        raise ValueError("parent split audit did not pass the pre-freeze gate")
    if parent_audit.get("selection_stage") != PILOT_SELECTION_STAGE:
        raise ValueError("power expansion parent must be a PILOT_V1 selection")
    if str(parent_audit.get("manifest_sha256", "")).lower() != (parent_manifest_hash):
        raise ValueError("parent split audit does not match parent manifest")
    if parent_audit.get("official_test_audit") != {"status": "DEFERRED_FROZEN"}:
        raise ValueError("parent split audit must preserve the official-test freeze")
    parent_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {split: 0 for split in SPLIT_ORDER}
    )
    for record in parent_records:
        dataset = str(record.get("dataset", ""))
        split = str(record.get("split", ""))
        if not dataset or split not in SPLIT_ORDER:
            raise ValueError("parent manifest contains invalid dataset/split fields")
        parent_counts[dataset][split] += 1
    from paper1.experiments.covol.audit_provenance import verify_split_audit

    verify_split_audit(
        parent_audit_path,
        manifest_sha256=parent_manifest_hash,
        manifest_record_count=len(parent_records),
        manifest_split_counts=parent_counts,
        required_datasets=frozenset(parent_counts),
    )

    parent_split_audit_hash = _file_sha256(parent_audit_path)
    verify_formal_power_failure(
        trigger_power_path,
        parent_manifest_sha256=parent_manifest_hash,
        parent_split_audit_sha256=parent_split_audit_hash,
    )
    return (
        parent_records,
        parent_audit,
        {
            "parent_manifest_sha256": parent_manifest_hash,
            "parent_split_audit_sha256": parent_split_audit_hash,
            "trigger_power_audit_sha256": _file_sha256(trigger_power_path),
        },
        {
            "parent_manifest": parent_manifest_path,
            "parent_split_audit": parent_audit_path,
            "trigger_power_audit": trigger_power_path,
        },
    )


def build_training_pilot_dataset(
    spec: Mapping[str, Any],
    *,
    config_dir: Path,
    selection_stage: str = PILOT_SELECTION_STAGE,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select one dataset's pre-freeze official-training design."""

    dataset = str(spec["name"]).strip()
    if not dataset:
        raise ValueError("dataset name must not be empty")
    if "official_test_manifest" in spec:
        raise ValueError(
            f"{dataset}: training-pilot config must not reference an official test "
            "manifest"
        )
    dataset_seed = int(spec.get("seed", PILOT_SEED))
    if dataset_seed != PILOT_SEED:
        raise ValueError(f"{dataset}: Step-003 pilot seed must be {PILOT_SEED}")
    split_counts = {
        split: int(spec.get("split_counts", {}).get(split, 0)) for split in SPLIT_ORDER
    }
    pilot_counts_valid = split_counts == PILOT_SPLIT_COUNTS
    expanded_counts_valid = (
        split_counts["train"] == PILOT_SPLIT_COUNTS["train"]
        and split_counts["dev"] == PILOT_SPLIT_COUNTS["dev"]
        and split_counts["internal_test"] >= PILOT_SPLIT_COUNTS["internal_test"]
    )
    if selection_stage == PILOT_SELECTION_STAGE and not pilot_counts_valid:
        raise ValueError(
            f"{dataset}: Step-003 split counts must be {PILOT_SPLIT_COUNTS}"
        )
    if selection_stage == EXPANDED_SELECTION_STAGE and not expanded_counts_valid:
        raise ValueError(
            f"{dataset}: power expansion must keep train/dev at 300/100 and "
            "must not shrink internal_test"
        )
    if selection_stage not in {PILOT_SELECTION_STAGE, EXPANDED_SELECTION_STAGE}:
        raise ValueError("unknown training-pilot selection_stage")
    if int(spec.get("select_count", 0)) != sum(split_counts.values()):
        raise ValueError(f"{dataset}: select_count must equal the split-count sum")

    training_path = (config_dir / str(spec["training_manifest"])).resolve()
    training_records = _validated_records(
        training_path,
        dataset=dataset,
        required_split="train",
    )
    split_source_hash = _split_source_sha256(training_records)
    selected, selected_cluster_counts = _select_scene_grouped(
        training_records,
        dataset=dataset,
        split_counts=split_counts,
        seed=PILOT_SEED,
        max_images_per_component=PILOT_COMPONENT_CAPS,
    )
    selected = [
        {
            **record,
            "manifest_scope": "training_pilot_step003",
            "official_test_audit_status": "DEFERRED_FROZEN",
            "selection_stage": selection_stage,
        }
        for record in selected
    ]
    if selected_cluster_counts["internal_test"] < MINIMUM_INTERNAL_TEST_SCENES:
        raise ValueError(
            f"{dataset}: internal_test requires at least "
            f"{MINIMUM_INTERNAL_TEST_SCENES} independent scene/sequence clusters"
        )
    overlap = _internal_overlap(selected)
    audit = {
        "dataset": dataset,
        "status": PILOT_STATUS,
        "selection_stage": selection_stage,
        "seed": PILOT_SEED,
        "input": {
            "official_training_count": len(training_records),
            "training_manifest_sha256": _file_sha256(training_path),
            "split_source_sha256": split_source_hash,
        },
        "selected_counts": {
            split: sum(record["split"] == split for record in selected)
            for split in SPLIT_ORDER
        },
        "selected_cluster_counts": selected_cluster_counts,
        "minimum_internal_test_scenes": MINIMUM_INTERNAL_TEST_SCENES,
        "max_images_per_scene_sequence_component": PILOT_COMPONENT_CAPS,
        "internal_overlap": overlap,
        "expansion_triggered": (
            selection_stage == EXPANDED_SELECTION_STAGE
            and split_counts["internal_test"] > PILOT_SPLIT_COUNTS["internal_test"]
        ),
    }
    return selected, audit


def _record_identity(record: Mapping[str, Any]) -> str:
    semantic_record = {
        str(key): value for key, value in record.items() if key != "selection_stage"
    }
    return json.dumps(
        semantic_record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _validate_expanded_selection(
    records: Sequence[Mapping[str, Any]],
    dataset_audits: Sequence[Mapping[str, Any]],
    *,
    parent_records: Sequence[Mapping[str, Any]],
    parent_audit: Mapping[str, Any],
) -> None:
    current_by_dataset_split: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {split: set() for split in SPLIT_ORDER}
    )
    parent_by_dataset_split: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {split: set() for split in SPLIT_ORDER}
    )
    for source_records, destination in (
        (records, current_by_dataset_split),
        (parent_records, parent_by_dataset_split),
    ):
        for record in source_records:
            dataset = str(record.get("dataset", ""))
            split = str(record.get("split", ""))
            if split not in SPLIT_ORDER:
                raise ValueError("parent/current manifest has an invalid split")
            destination[dataset][split].add(_record_identity(record))

    if set(current_by_dataset_split) != set(parent_by_dataset_split):
        raise ValueError("power expansion datasets must exactly match the parent")
    for dataset in current_by_dataset_split:
        current = current_by_dataset_split[dataset]
        parent = parent_by_dataset_split[dataset]
        for split in ("train", "dev"):
            if current[split] != parent[split]:
                raise ValueError(
                    f"{dataset}: power expansion changed the frozen {split} images"
                )
        if not parent["internal_test"] <= current["internal_test"]:
            raise ValueError(
                f"{dataset}: expanded internal_test must preserve every parent row"
            )

    parent_datasets = {
        str(value.get("dataset", "")): value
        for value in parent_audit.get("datasets", [])
        if isinstance(value, Mapping)
    }
    current_datasets = {
        str(value.get("dataset", "")): value for value in dataset_audits
    }
    if set(parent_datasets) != set(current_datasets):
        raise ValueError("power expansion audit datasets must match the parent")
    for dataset, current in current_datasets.items():
        parent_input = parent_datasets[dataset].get("input")
        current_input = current.get("input")
        if not isinstance(parent_input, Mapping) or not isinstance(
            current_input, Mapping
        ):
            raise ValueError("dataset source provenance must be JSON objects")
        for field in ("training_manifest_sha256", "split_source_sha256"):
            if parent_input.get(field) != current_input.get(field):
                raise ValueError(
                    f"{dataset}: power expansion changed source provenance"
                )
        expanded = len(current_by_dataset_split[dataset]["internal_test"]) > len(
            parent_by_dataset_split[dataset]["internal_test"]
        )
        if current.get("expansion_triggered") is not expanded:
            raise ValueError(f"{dataset}: expansion_triggered is inconsistent")
    if not any(
        bool(value.get("expansion_triggered")) for value in current_datasets.values()
    ):
        raise ValueError("EXPANDED_FOR_POWER must expand at least one dataset")


def build_training_pilot_manifests(
    config_path: Path,
    output_path: Path,
    audit_path: Path,
) -> None:
    """Build all Step-003 training-only pilots and their pre-freeze audit."""

    config_path = config_path.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, Mapping) or not isinstance(config.get("datasets"), list):
        raise ValueError("config must contain a datasets list")
    if int(config.get("seed", PILOT_SEED)) != PILOT_SEED:
        raise ValueError(f"Step-003 pilot seed must be {PILOT_SEED}")
    if config.get("audit_mode", "training_pilot") != "training_pilot":
        raise ValueError("Step-003 audit_mode must be training_pilot")
    selection_stage = str(config.get("selection_stage", PILOT_SELECTION_STAGE)).strip()
    if selection_stage not in {PILOT_SELECTION_STAGE, EXPANDED_SELECTION_STAGE}:
        raise ValueError("selection_stage must be PILOT_V1 or EXPANDED_FOR_POWER")
    lineage_keys = (
        "parent_manifest",
        "parent_split_audit",
        "trigger_power_audit",
    )
    parent_records: list[dict[str, Any]] = []
    parent_audit: Mapping[str, Any] = {}
    lineage_hashes: dict[str, str] = {}
    lineage_paths: dict[str, Path] = {}
    if selection_stage == EXPANDED_SELECTION_STAGE:
        (
            parent_records,
            parent_audit,
            lineage_hashes,
            lineage_paths,
        ) = _validate_expansion_inputs(config, config_dir=config_path.parent)
    elif any(key in config for key in lineage_keys):
        raise ValueError("PILOT_V1 config must not contain expansion lineage")

    records: list[dict[str, Any]] = []
    dataset_audits: list[dict[str, Any]] = []
    seen_datasets: set[str] = set()
    for raw_spec in config["datasets"]:
        if not isinstance(raw_spec, Mapping):
            raise ValueError("each dataset spec must be a JSON object")
        dataset = str(raw_spec.get("name", "")).strip()
        if dataset in seen_datasets:
            raise ValueError(f"duplicate dataset spec: {dataset!r}")
        seen_datasets.add(dataset)
        selected, audit = build_training_pilot_dataset(
            raw_spec,
            config_dir=config_path.parent,
            selection_stage=selection_stage,
        )
        records.extend(selected)
        dataset_audits.append(audit)

    if not records:
        raise ValueError("training-pilot config must select at least one dataset")
    records.sort(
        key=lambda record: (
            str(record["dataset"]),
            SPLIT_ORDER.index(str(record["split"])),
            str(record["selection_hash"]),
        )
    )
    if selection_stage == EXPANDED_SELECTION_STAGE:
        _validate_expanded_selection(
            records,
            dataset_audits,
            parent_records=parent_records,
            parent_audit=parent_audit,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    audit_payload = {
        "audit_mode": "training_pilot",
        "authorization_scope": PILOT_SCOPE,
        "status": PILOT_STATUS,
        "selection_stage": selection_stage,
        "seed": PILOT_SEED,
        "config_sha256": _file_sha256(config_path),
        "record_count": len(records),
        "manifest_sha256": _file_sha256(output_path),
        "official_test_audit": {"status": "DEFERRED_FROZEN"},
        "datasets": dataset_audits,
        **lineage_hashes,
    }
    if lineage_paths:
        audit_payload["lineage_artifacts"] = {
            key: Path(os.path.relpath(path, audit_path.parent)).as_posix()
            for key, path in lineage_paths.items()
        }
    audit_path.write_text(
        json.dumps(audit_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    build_training_pilot_manifests(args.config, args.output, args.audit)


if __name__ == "__main__":
    main()
