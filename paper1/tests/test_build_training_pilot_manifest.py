from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from paper1.experiments.covol.audit_provenance import (
    KITTI_CANONICAL_TRAINING_SPLIT_SHA256,
    KITTI_SOURCE_REPOSITORY_ID,
    KITTI_SOURCE_REPOSITORY_REVISION,
    NYUV2_EVAL_PROTOCOL_SHA256,
    NYUV2_LABELED_ARCHIVE_SHA256,
    NYUV2_OFFICIAL_SPLITS_SHA256,
    POWER_GRID_CANONICAL_SHA256,
    STEP003_AUTHORIZATION_SCOPE,
    file_sha256,
)
from paper1.experiments.covol.build_training_pilot_manifest import (
    PILOT_SELECTION_STAGE,
    PILOT_STATUS,
    _validate_expanded_selection,
    build_training_pilot_manifests,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_source(path: Path, dataset: str, *, count: int = 1_000) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for index in range(count):
            record: dict[str, object] = {
                "dataset": dataset,
                "image_id": f"image-{index}",
                "scene_id": f"scene-{index // 2}",
                "sequence_id": f"scene-{index // 2}",
                "frame_index": index % 2,
                "rgb_sha256": _sha(f"rgb-{index}"),
                "official_split": "train",
                "entities": [],
            }
            if dataset == "NYUv2":
                record.update(
                    {
                        "adapter": "nyuv2-labeled-mat-v1",
                        "archive_integrity_scope": "blind_whole_archive_sha256",
                        "semantic_decode_scope": "official_train_only",
                        "annotation_sha256": NYUV2_LABELED_ARCHIVE_SHA256,
                        "depth_sha256": NYUV2_LABELED_ARCHIVE_SHA256,
                        "eval_protocol_sha256": NYUV2_EVAL_PROTOCOL_SHA256,
                        "source_detail": {
                            "official_split": {
                                "sha256": NYUV2_OFFICIAL_SPLITS_SHA256,
                            }
                        },
                    }
                )
            elif dataset == "KITTI":
                record.update(
                    {
                        "adapter": "kitti-source-v1",
                        "canonical_split_source_sha256": (
                            KITTI_CANONICAL_TRAINING_SPLIT_SHA256
                        ),
                        "source_repository_id": KITTI_SOURCE_REPOSITORY_ID,
                        "source_repository_revision": (
                            KITTI_SOURCE_REPOSITORY_REVISION
                        ),
                        "source_split_list_sha256": _sha("selected-kitti-split"),
                        "selection_audit_sha256": _sha("kitti-selection-audit"),
                    }
                )
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")


def _config(
    tmp_path: Path,
    *,
    include_test: bool = False,
    include_kitti: bool = False,
) -> Path:
    source = tmp_path / "train.jsonl"
    _write_source(source, "NYUv2")
    spec: dict[str, object] = {
        "name": "NYUv2",
        "training_manifest": source.name,
        "select_count": 500,
        "split_counts": {"train": 300, "dev": 100, "internal_test": 100},
    }
    if include_test:
        spec["official_test_manifest"] = "must-not-be-read.jsonl"
    specs = [spec]
    if include_kitti:
        kitti_source = tmp_path / "kitti-train.jsonl"
        _write_source(kitti_source, "KITTI")
        specs.append(
            {
                "name": "KITTI",
                "training_manifest": kitti_source.name,
                "select_count": 500,
                "split_counts": {
                    "train": 300,
                    "dev": 100,
                    "internal_test": 100,
                },
            }
        )
    config = {
        "audit_mode": "training_pilot",
        "selection_stage": PILOT_SELECTION_STAGE,
        "seed": 20260821,
        "datasets": specs,
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_builds_deterministic_prefreeze_manifest_without_test_reference(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    first_output = tmp_path / "first.jsonl"
    first_audit = tmp_path / "first-audit.json"
    second_output = tmp_path / "second.jsonl"
    second_audit = tmp_path / "second-audit.json"

    build_training_pilot_manifests(config, first_output, first_audit)
    build_training_pilot_manifests(config, second_output, second_audit)

    assert first_output.read_bytes() == second_output.read_bytes()
    records = [json.loads(line) for line in first_output.read_text().splitlines()]
    assert len(records) == 500
    assert {record["official_split"] for record in records} == {"train"}
    assert {record["manifest_scope"] for record in records} == {
        "training_pilot_step003"
    }
    assert {record["selection_stage"] for record in records} == {PILOT_SELECTION_STAGE}
    audit = json.loads(first_audit.read_text())
    assert audit["status"] == PILOT_STATUS
    assert audit["selection_stage"] == PILOT_SELECTION_STAGE
    assert audit["official_test_audit"] == {"status": "DEFERRED_FROZEN"}
    assert audit["datasets"][0]["internal_overlap"] == {
        "image_count": 0,
        "cluster_count": 0,
        "rgb_sha256_count": 0,
        "scene_count": 0,
        "sequence_count": 0,
    }
    assert audit["datasets"][0]["selected_counts"] == {
        "train": 300,
        "dev": 100,
        "internal_test": 100,
    }
    assert audit["datasets"][0]["max_images_per_scene_sequence_component"] == {
        "train": 60,
        "dev": 20,
        "internal_test": 5,
    }
    assert audit["datasets"][0]["selected_cluster_counts"]["internal_test"] >= 20


def test_rejects_any_official_test_manifest_reference(tmp_path: Path) -> None:
    config = _config(tmp_path, include_test=True)

    with pytest.raises(ValueError, match="must not reference an official test"):
        build_training_pilot_manifests(
            config,
            tmp_path / "output.jsonl",
            tmp_path / "audit.json",
        )


def test_rejects_noncanonical_pilot_seed(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = json.loads(config.read_text())
    payload["seed"] = 1
    config.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="pilot seed must be 20260821"):
        build_training_pilot_manifests(
            config,
            tmp_path / "output.jsonl",
            tmp_path / "audit.json",
        )


def test_power_expansion_preserves_parent_and_links_formal_failure(
    tmp_path: Path,
) -> None:
    pilot_config = _config(tmp_path, include_kitti=True)
    parent_manifest = tmp_path / "parent.jsonl"
    parent_audit = tmp_path / "parent-audit.json"
    build_training_pilot_manifests(
        pilot_config,
        parent_manifest,
        parent_audit,
    )
    parent_hash = hashlib.sha256(parent_manifest.read_bytes()).hexdigest()
    trigger_power = tmp_path / "power-fail.json"
    parent_audit_hash = file_sha256(parent_audit)
    implementation_hash = file_sha256(
        Path("paper1/experiments/covol/power_analysis.py")
    )
    formal_conditions = {
        "exact_simulations_met": True,
        "preregistered_grid_matched": True,
        "split_is_internal_test": True,
        "seed_is_preregistered": True,
        "required_power_datasets_present": True,
        "analysis_datasets_exact": True,
        "split_audit_linked": True,
        "minimum_internal_test_scenes_met": True,
        "minimum_dev_scenes_met": True,
    }
    scenarios = [
        {
            "scenario_id": (
                "prev05_icc30_hv20" if index == 0 else f"scenario-{index:02d}"
            ),
            "is_primary": index == 0,
            "scenario_power_threshold_pass": False if index == 0 else True,
        }
        for index in range(20)
    ]
    trigger_power.write_text(
        json.dumps(
            {
                "schema_version": "covol-power-analysis-v1",
                "status": "FAIL",
                "run_mode": "FORMAL",
                "dataset_decision": {
                    "source": "preregistered_primary_default",
                    "decision": "GO_LOCAL_CLAIMS_NYUV2_KITTI",
                    "selected_datasets": ["KITTI", "NYUv2"],
                },
                "input": {
                    "manifest_sha256": parent_hash,
                    "split": "internal_test",
                    "selection_stage": "PILOT_V1",
                    "datasets": ["KITTI", "NYUv2"],
                    "power_analysis_datasets": ["KITTI", "NYUv2"],
                },
                "split_audit": {
                    "manifest_sha256": parent_hash,
                    "split_audit_sha256": parent_audit_hash,
                    "selection_stage": "PILOT_V1",
                    "datasets": ["KITTI", "NYUv2"],
                },
                "authorization_scope": STEP003_AUTHORIZATION_SCOPE,
                "implementation_sha256": implementation_hash,
                "simulation": {
                    "formal_run": True,
                    "simulations": 5_000,
                    "seed": 20260821,
                    "formal_conditions": formal_conditions,
                },
                "grid": {
                    "matches_preregistered_grid": True,
                    "grid_sha256": POWER_GRID_CANONICAL_SHA256,
                    "preregistered_grid_sha256": POWER_GRID_CANONICAL_SHA256,
                    "scenario_count": 20,
                    "primary_scenario_id": "prev05_icc30_hv20",
                    "formal_simulations": 5_000,
                    "minimum_power": 0.8,
                },
                "datasets": [
                    {
                        "dataset": dataset,
                        "primary_power_threshold_pass": False,
                        "formal_gate_pass": False,
                        "scenarios": scenarios,
                    }
                    for dataset in ("KITTI", "NYUv2")
                ],
            }
        ),
        encoding="utf-8",
    )
    expansion_config = tmp_path / "expanded-config.json"
    expansion_config.write_text(
        json.dumps(
            {
                "audit_mode": "training_pilot",
                "selection_stage": "EXPANDED_FOR_POWER",
                "seed": 20260821,
                "parent_manifest": parent_manifest.name,
                "parent_split_audit": parent_audit.name,
                "trigger_power_audit": trigger_power.name,
                "datasets": [
                    {
                        "name": "NYUv2",
                        "training_manifest": "train.jsonl",
                        "select_count": 600,
                        "split_counts": {
                            "train": 300,
                            "dev": 100,
                            "internal_test": 200,
                        },
                    },
                    {
                        "name": "KITTI",
                        "training_manifest": "kitti-train.jsonl",
                        "select_count": 600,
                        "split_counts": {
                            "train": 300,
                            "dev": 100,
                            "internal_test": 200,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "expanded.jsonl"
    audit_path = tmp_path / "expanded-audit.json"

    build_training_pilot_manifests(expansion_config, output, audit_path)

    records = [json.loads(line) for line in output.read_text().splitlines()]
    audit = json.loads(audit_path.read_text())
    assert len(records) == 1_200
    assert audit["selection_stage"] == "EXPANDED_FOR_POWER"
    assert audit["parent_manifest_sha256"] == parent_hash
    assert audit["datasets"][0]["expansion_triggered"] is True
    assert audit["datasets"][0]["selected_counts"]["internal_test"] == 200
    assert audit["lineage_artifacts"] == {
        "parent_manifest": "parent.jsonl",
        "parent_split_audit": "parent-audit.json",
        "trigger_power_audit": "power-fail.json",
    }


def test_power_expansion_preserves_complete_parent_row_semantics() -> None:
    parent = {
        "dataset": "NYUv2",
        "image_id": "image-1",
        "scene_id": "scene-a",
        "sequence_id": "sequence-a",
        "rgb_sha256": _sha("rgb"),
        "selection_hash": _sha("selection"),
        "split": "train",
        "selection_stage": "PILOT_V1",
        "entities": [{"entity_id": "chair"}],
        "source_detail": {"official_split": {"sha256": "a" * 64}},
    }
    changed = {
        **parent,
        "scene_id": "scene-b",
        "selection_stage": "EXPANDED_FOR_POWER",
    }
    dataset_audit = {
        "dataset": "NYUv2",
        "input": {
            "training_manifest_sha256": "b" * 64,
            "split_source_sha256": "c" * 64,
        },
        "expansion_triggered": True,
    }
    parent_audit = {"datasets": [dataset_audit]}

    with pytest.raises(ValueError, match="changed the frozen train images"):
        _validate_expanded_selection(
            [changed],
            [dataset_audit],
            parent_records=[parent],
            parent_audit=parent_audit,
        )


def test_rejects_self_reported_untrusted_source_hashes(tmp_path: Path) -> None:
    config = _config(tmp_path)
    source = tmp_path / "train.jsonl"
    records = [json.loads(line) for line in source.read_text().splitlines()]
    records[0]["adapter"] = "self-reported-adapter"
    source.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="untrusted NYUv2 adapter"):
        build_training_pilot_manifests(
            config,
            tmp_path / "output.jsonl",
            tmp_path / "audit.json",
        )
