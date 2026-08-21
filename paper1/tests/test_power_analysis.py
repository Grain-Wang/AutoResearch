from __future__ import annotations

import csv
import hashlib
import json

import pytest
from paper1.experiments.covol.audit_provenance import (
    NYUV2_EVAL_PROTOCOL_SHA256,
    NYUV2_LABELED_ARCHIVE_SHA256,
    NYUV2_OFFICIAL_SPLITS_SHA256,
    canonical_json_sha256,
    verify_split_audit,
)
from paper1.experiments.covol.power_analysis import (
    DEFAULT_GRID_PATH,
    PREREGISTERED_GRID_SHA256,
    DatasetDesign,
    PowerScenario,
    _policy_outcomes_from_scores,
    load_power_grid,
    read_dataset_designs,
    run_power_analysis,
    simulate_power_scenario,
)


def _write_manifest(path) -> None:
    rows = []
    for split, image_count in (("dev", 5), ("internal_test", 20)):
        for scene_index in range(4):
            for image_index in range(image_count):
                image_id = f"{split}-image-{scene_index}-{image_index}"
                rows.append(
                    {
                        "dataset": "NYUv2",
                        "image_id": image_id,
                        "scene_id": f"{split}-scene-{scene_index}",
                        "sequence_id": f"{split}-scene-{scene_index}",
                        "cluster_id": hashlib.sha256(
                            f"cluster-{split}-{scene_index}".encode()
                        ).hexdigest(),
                        "official_split": "train",
                        "split": split,
                        "rgb_sha256": hashlib.sha256(
                            f"rgb-{image_id}".encode()
                        ).hexdigest(),
                        "selection_hash": hashlib.sha256(
                            f"selection-{image_id}".encode()
                        ).hexdigest(),
                        "manifest_scope": "training_pilot_step003",
                        "official_test_audit_status": "DEFERRED_FROZEN",
                        "selection_stage": "PILOT_V1",
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
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_preregistered_power_grid_has_exactly_twenty_unique_rows() -> None:
    grid = load_power_grid()

    assert len(grid.scenarios) == 20
    assert len({scenario.scenario_id for scenario in grid.scenarios}) == 20
    assert grid.primary_scenario_id in {
        scenario.scenario_id for scenario in grid.scenarios
    }
    assert grid.primary_scenario_id == "prev05_icc30_hv20"
    assert grid.formal_simulations == 5_000
    assert grid.planning_auc_delta == pytest.approx(0.05)
    assert grid.minimum_auc_delta == pytest.approx(0.03)
    assert grid.minimum_power == pytest.approx(0.80)
    assert grid.minimum_independent_scenes == 20
    assert grid.hv_reference_margin_multiplier == pytest.approx(1.05)
    assert grid.policy_coverage_grid == tuple(index / 20 for index in range(21))
    assert canonical_json_sha256(DEFAULT_GRID_PATH) == PREREGISTERED_GRID_SHA256


def test_manifest_design_counts_independent_scenes(tmp_path) -> None:
    manifest = tmp_path / "manifest.jsonl"
    _write_manifest(manifest)

    designs = read_dataset_designs(manifest)

    assert designs == [
        DatasetDesign(
            dataset="NYUv2",
            scene_sizes=(20, 20, 20, 20),
            dev_scene_sizes=(5, 5, 5, 5),
        )
    ]


def test_manifest_rejects_one_scene_declared_as_multiple_clusters(tmp_path) -> None:
    manifest = tmp_path / "manifest.jsonl"
    _write_manifest(manifest)
    rows = [json.loads(line) for line in manifest.read_text().splitlines()]
    rows[1]["cluster_id"] = hashlib.sha256(b"forged-cluster").hexdigest()
    manifest.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="maps to multiple cluster_id"):
        read_dataset_designs(manifest)


def test_small_simulation_is_deterministic_and_not_a_formal_gate(tmp_path) -> None:
    manifest = tmp_path / "manifest.jsonl"
    first_csv = tmp_path / "first.csv"
    first_json = tmp_path / "first.json"
    second_csv = tmp_path / "second.csv"
    second_json = tmp_path / "second.json"
    _write_manifest(manifest)

    first = run_power_analysis(
        manifest,
        output_csv=first_csv,
        output_json=first_json,
        simulations=8,
        seed=17,
    )
    second = run_power_analysis(
        manifest,
        output_csv=second_csv,
        output_json=second_json,
        simulations=8,
        seed=17,
    )

    assert first == second
    assert first["status"] == "DIAGNOSTIC_ONLY"
    assert first["run_mode"] == "DIAGNOSTIC"
    assert len(first["datasets"][0]["scenarios"]) == 20
    assert all(
        scenario["scenario_power_threshold_pass"]
        == scenario["full_statistical_gate_power_threshold_pass"]
        for scenario in first["datasets"][0]["scenarios"]
    )
    assert first_json.read_bytes() == second_json.read_bytes()
    with first_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 20
    assert {row["grid_sha256"] for row in rows} == {
        first["grid"]["grid_sha256"]
    }


def test_inestimable_replicates_count_as_power_failures() -> None:
    grid = load_power_grid(DEFAULT_GRID_PATH)
    scenario = PowerScenario(
        scenario_id="test-low-prevalence",
        error_prevalence=0.01,
        scene_icc=0.0,
        conditional_advantage_standardized_effect=10.0,
    )

    result = simulate_power_scenario(
        DatasetDesign(
            dataset="test",
            scene_sizes=(5, 5, 5, 5),
            dev_scene_sizes=(5, 5, 5, 5),
        ),
        scenario,
        grid,
        simulations=20,
        seed=29,
    )

    assert result["estimable_simulations"] == 0
    assert result["auc_joint_power"] == 0.0
    assert result["hv_joint_power"] == 0.0
    assert result["full_statistical_gate_power"] == 0.0
    assert all(contrast["power"] == 0.0 for contrast in result["contrasts"].values())


def test_split_audit_must_hash_link_and_match_counts(tmp_path) -> None:
    split_audit = tmp_path / "split_audit.json"
    manifest_hash = "a" * 64
    selected_counts = {"train": 300, "dev": 100, "internal_test": 100}
    dataset_audit = {
        "dataset": "NYUv2",
        "status": "PASS_PREFREEZE_NO_TEST_ACCESS",
        "selection_stage": "PILOT_V1",
        "seed": 20260821,
        "input": {
            "training_manifest_sha256": "c" * 64,
            "split_source_sha256": "d" * 64,
        },
        "selected_counts": selected_counts,
        "internal_overlap": {
            "image_count": 0,
            "cluster_count": 0,
            "scene_count": 0,
            "sequence_count": 0,
            "rgb_sha256_count": 0,
        },
    }
    split_audit.write_text(
        json.dumps(
            {
                "audit_mode": "training_pilot",
                "selection_stage": "PILOT_V1",
                "authorization_scope": "STEP003_ONLY_NOT_STEP005_OR_OFFICIAL_TEST",
                "status": "PASS_PREFREEZE_NO_TEST_ACCESS",
                "seed": 20260821,
                "config_sha256": "e" * 64,
                "official_test_audit": {"status": "DEFERRED_FROZEN"},
                "manifest_sha256": manifest_hash,
                "record_count": 1_000,
                "datasets": [
                    dataset_audit,
                    {**dataset_audit, "dataset": "KITTI"},
                ],
            }
        ),
        encoding="utf-8",
    )
    counts = {"NYUv2": selected_counts, "KITTI": selected_counts}

    link = verify_split_audit(
        split_audit,
        manifest_sha256=manifest_hash,
        manifest_record_count=1_000,
        manifest_split_counts=counts,
        required_datasets=frozenset({"KITTI", "NYUv2"}),
    )

    assert link.datasets == ("KITTI", "NYUv2")
    with pytest.raises(ValueError, match="manifest_sha256"):
        verify_split_audit(
            split_audit,
            manifest_sha256="b" * 64,
            manifest_record_count=1_000,
            manifest_split_counts=counts,
            required_datasets=frozenset({"KITTI", "NYUv2"}),
        )


def test_policy_selector_uses_discrete_shared_d0_or_d1_losses() -> None:
    outcomes = _policy_outcomes_from_scores(
        scores=[0.0, 2.0, 1.0],
        dev_scores=[0.0, 2.0, 1.0],
        clusters=[0, 1, 2],
        d0_clean_losses=[1.0, 1.1, 1.2],
        d1_clean_losses=[0.8, 0.9, 1.0],
        d1_variant_losses=[
            (1.3, 1.4, 1.5),
            (1.0, 1.1, 1.2),
            (1.1, 1.2, 1.3),
        ],
        coverage_grid=(0.0, 1.0 / 3.0, 1.0),
    )

    assert outcomes[0].routed_clean_losses == (1.0, 1.0, 0.8)
    assert outcomes[1].routed_clean_losses == (1.1, 0.9, 0.9)
    assert outcomes[2].routed_clean_losses == (1.2, 1.2, 1.0)
    assert outcomes[1].routed_variant_losses[1] == (1.0, 1.1, 1.2)
    assert outcomes[0].routed_variant_losses[1] == (1.0, 1.0, 1.0)

    shifted_test_outcomes = _policy_outcomes_from_scores(
        scores=[1.4, 1.3, 1.2],
        dev_scores=[0.0, 2.0, 1.0],
        clusters=[0, 1, 2],
        d0_clean_losses=[1.0, 1.1, 1.2],
        d1_clean_losses=[0.8, 0.9, 1.0],
        d1_variant_losses=[
            (1.3, 1.4, 1.5),
            (1.0, 1.1, 1.2),
            (1.1, 1.2, 1.3),
        ],
        coverage_grid=(0.0, 1.0 / 3.0, 1.0),
    )
    assert all(
        outcome.routed_clean_losses[1] == d0
        for outcome, d0 in zip(
            shifted_test_outcomes,
            (1.0, 1.1, 1.2),
            strict=True,
        )
    )
