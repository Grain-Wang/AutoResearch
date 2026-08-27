from __future__ import annotations

import numpy as np
import pytest
from paper1.experiments.covol.run_sensitivity_diagnostic import (
    _CSV_FIELDS,
    EvalProtocol,
    _encoder_weight_provenance,
    _load_resume_results,
    _write_csv,
    cluster_bootstrap_interval,
    evaluate_prediction_pair,
    summarize_sensitivity,
    target_region_mask,
)


def _protocol() -> EvalProtocol:
    return EvalProtocol(
        image_height=8,
        image_width=8,
        y_start=0,
        y_end=8,
        x_start=0,
        x_end=8,
        minimum_depth=0.001,
        maximum_depth=10.0,
        depth_key="rawDepths",
    )


def test_target_mask_and_paired_metrics_use_union_region() -> None:
    labels = np.zeros((8, 8), dtype=np.int64)
    instances = np.zeros((8, 8), dtype=np.int64)
    labels[:4] = 3
    instances[:4] = 5
    labels[4:] = 85
    instances[4:] = 13
    region = target_region_mask(
        labels,
        instances,
        {
            "near_entity_id": "nyuv2:0481:class-3:instance-5",
            "far_entity_id": "nyuv2:0481:class-85:instance-13",
        },
    )
    ground_truth = np.full((8, 8), 2.0, dtype=np.float32)
    clean = ground_truth.copy()
    variant = np.full((8, 8), 2.4, dtype=np.float32)

    result = evaluate_prediction_pair(
        ground_truth=ground_truth,
        clean_prediction=clean,
        variant_prediction=variant,
        region_mask=region,
        protocol=_protocol(),
    )

    assert result["region_valid_pixel_count"] == 64
    assert result["region_abs_rel_degradation"] == pytest.approx(0.2)
    assert result["region_d1_degradation"] == 0.0


def test_cluster_bootstrap_is_cluster_balanced_and_deterministic() -> None:
    rows = [
        {"cluster_id": "large", "value": 1.0},
        {"cluster_id": "large", "value": 1.0},
        {"cluster_id": "large", "value": 1.0},
        {"cluster_id": "small", "value": 3.0},
    ]

    first = cluster_bootstrap_interval(
        rows, value_key="value", replicates=1_000, seed=17
    )
    second = cluster_bootstrap_interval(
        rows, value_key="value", replicates=1_000, seed=17
    )

    assert first == second
    assert first["point"] == 2.0


def test_h_sensitivity_requires_conflict_signal_and_null_control() -> None:
    rows = []
    for family in (
        "semantic_preserving",
        "target_deletion",
        "local_entity_conflict",
        "depth_relation_conflict",
    ):
        for cluster_index in range(8):
            delta = 0.0 if family == "semantic_preserving" else 0.1
            rows.append(
                {
                    "error_type": family,
                    "cluster_id": f"cluster-{cluster_index}",
                    "region_abs_rel_degradation": delta,
                    "region_d1_degradation": delta,
                    "full_abs_rel_degradation": delta,
                    "full_d1_degradation": delta,
                }
            )

    result = summarize_sensitivity(rows, replicates=500, seed=29)

    assert result["status"] == "PASS_H_SENSITIVITY"
    assert result["control_ci_contains_zero"] is True
    assert result["supported_conflict_families"] == [
        "target_deletion",
        "local_entity_conflict",
        "depth_relation_conflict",
    ]


def test_resume_checkpoint_requires_twelve_complete_rows(tmp_path) -> None:
    intervention_rows = [
        {
            "image_id": "nyuv2_train_000001",
            "error_type": f"family-{index // 3}",
            "variant_id": index % 3,
            "template_id": f"template-{index}",
        }
        for index in range(12)
    ]
    result_rows = []
    for row in intervention_rows:
        result = {
            field: 1.0 if "pixel_count" not in field else 32 for field in _CSV_FIELDS
        }
        result.update({"dataset": "NYUv2", "cluster_id": "cluster-1", **row})
        result_rows.append(result)
    output = tmp_path / "checkpoint.csv"
    _write_csv(output, result_rows)

    assert len(_load_resume_results(output, intervention_rows)) == 12

    _write_csv(output, result_rows[:-1])
    with pytest.raises(ValueError, match="incomplete image"):
        _load_resume_results(output, intervention_rows)


def test_encoder_provenance_hashes_required_clip_and_dino_assets(tmp_path) -> None:
    clip_path = tmp_path / "clip" / "ViT-L-14.pt"
    dino_path = tmp_path / "torchhub" / "dinov2_vitl14_pretrain.pth"
    clip_path.parent.mkdir()
    dino_path.parent.mkdir()
    clip_path.write_bytes(b"clip")
    dino_path.write_bytes(b"dino")

    assets = _encoder_weight_provenance(tmp_path)

    assert [asset["path_within_cache"] for asset in assets] == [
        "clip/ViT-L-14.pt",
        "torchhub/dinov2_vitl14_pretrain.pth",
    ]
    assert all(len(asset["sha256"]) == 64 for asset in assets)
