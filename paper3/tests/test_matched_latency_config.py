from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from paper3.experiments.bar_depth.analyze_budget_baselines import (
    select_region_indices,
)
from paper3.experiments.bar_depth.analyze_matched_latency import (
    _latency_evidence_mode,
    apply_pareto_gate,
)
from paper3.experiments.bar_depth.benchmark_matched_latency import (
    _physical_gpu_index,
    _selected_regions,
)
from paper3.experiments.bar_depth.core import gradient_score, make_regions
from paper3.experiments.bar_depth.io_utils import file_digest, read_json, read_jsonl
from paper3.experiments.bar_depth.run_direct_resolution import _aligned_error
from paper3.experiments.bar_depth.run_direct_resolution import (
    _process_sample as process_direct_sample,
)
from PIL import Image


def test_matched_latency_contract_is_bound_and_cross_scan() -> None:
    config = read_json(Path("paper3/configs/bar_depth/matched_latency_v1.json"))
    assert file_digest(Path(config["base_config"])) == config["base_config_sha256"]
    assert file_digest(Path(config["merge_config"])) == config["merge_config_sha256"]
    assert file_digest(Path(config["manifest"])) == config["manifest_sha256"]

    sizes = [int(value) for value in config["whole_image_input_sizes"]]
    assert sizes == sorted(set(sizes))
    assert sizes[0] == int(config["regional_pipeline"]["base_input_size"])
    assert all(value % 14 == 0 for value in sizes)

    manifest = {
        int(row["sample_index"]): row for row in read_jsonl(Path(config["manifest"]))
    }
    timing_indices = [
        int(value) for value in config["latency"]["timing_sample_indices"]
    ]
    assert len(timing_indices) == 20
    assert len({str(manifest[index]["scan_id"]) for index in timing_indices}) == 20
    assert int(config["latency"]["warmup_images"]) <= len(timing_indices)


def test_independent_positive_median_alignment_recovers_inverse_depth() -> None:
    depth = np.linspace(1.0, 20.0, 80, dtype=np.float64).reshape(8, 10)
    valid = np.ones_like(depth, dtype=bool)
    disparity = 3.5 / depth
    metric = {
        "inverse_depth_epsilon": 1e-6,
        "min_depth": 0.1,
        "max_depth": 350.0,
    }
    error, scale = _aligned_error(disparity, depth, valid, metric)
    np.testing.assert_allclose(error, 0.0, atol=1e-14)
    assert np.isclose(scale, 1.0 / 3.5)


def test_timing_selector_matches_signed_baseline_selector() -> None:
    rng = np.random.default_rng(23)
    image = rng.random((24, 32, 3))
    base = rng.random((24, 32))
    regions = make_regions(24, 32, 3, 4, 1.5)
    rows = [
        {
            "sample_index": 0,
            "region_id": region.region_id,
            "rgb_gradient_score": gradient_score(image, region),
            "base_gradient_score": gradient_score(base, region),
            "primary_utility_sum": 0.0,
        }
        for region in regions
    ]
    expected = select_region_indices(
        rows,
        method="rgb_base_rank_combination_topk",
        budget_count=3,
    )
    actual = _selected_regions(image, base, regions, 3)
    np.testing.assert_array_equal(actual, expected)


def test_formal_timing_requires_one_numeric_visible_gpu(monkeypatch: object) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "2")
    assert _physical_gpu_index() == 2
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0,1")
    try:
        _physical_gpu_index()
    except ValueError as error:
        assert "one numeric" in str(error)
    else:
        raise AssertionError("Multiple visible GPUs must invalidate formal timing")


def test_pareto_gate_requires_positive_paired_lower_bound() -> None:
    passed = apply_pareto_gate(
        oracle_estimate=0.10,
        direct_estimate=0.07,
        paired_differences=[0.01, 0.02, 0.03, 0.04],
        confidence_level=0.95,
        require_point_above_zero=True,
        require_ci_lower_above_zero=True,
    )
    assert passed["decision"] == "GO_REGIONAL_ORACLE_PARETO"

    failed = apply_pareto_gate(
        oracle_estimate=0.10,
        direct_estimate=0.09,
        paired_differences=[-0.02, 0.0, 0.02, 0.04],
        confidence_level=0.95,
        require_point_above_zero=True,
        require_ci_lower_above_zero=True,
    )
    assert failed["decision"] == "STOP_DIRECT_RESOLUTION_DOMINATES"
    assert failed["point_pass"]
    assert not failed["paired_ci_pass"]


def test_shared_latency_requires_explicit_diagnostic_opt_in() -> None:
    assert _latency_evidence_mode("COMPLETE_EXCLUSIVE_MATCHED_LATENCY", False) == (
        "exclusive",
        True,
    )
    assert _latency_evidence_mode(
        "COMPLETE_SHARED_DIAGNOSTIC_MATCHED_LATENCY", True
    ) == ("shared_diagnostic", False)
    try:
        _latency_evidence_mode("COMPLETE_SHARED_DIAGNOSTIC_MATCHED_LATENCY", False)
    except ValueError as error:
        assert "not an accepted" in str(error)
    else:
        raise AssertionError("Shared latency must not enter the formal default path")


def test_direct_resolution_sample_reuses_base_forward(tmp_path: Path) -> None:
    class FakeBackend:
        def __init__(self) -> None:
            self.input_size = 518
            self.calls: list[int] = []

        def _target_shape(self, height: int, width: int) -> tuple[int, int]:
            return self.input_size, self.input_size

        def infer(self, images: list[np.ndarray]) -> tuple[list[np.ndarray], float]:
            self.calls.append(self.input_size)
            factor = self.input_size / 518.0
            return [np.full(image.shape[:2], factor) for image in images], factor

    image = np.full((8, 10, 3), 127, dtype=np.uint8)
    Image.fromarray(image).save(tmp_path / "image.png")
    np.save(tmp_path / "depth.npy", np.full((8, 10), 2.0))
    np.save(tmp_path / "mask.npy", np.ones((8, 10), dtype=bool))
    record: dict[str, Any] = {
        "sample_index": 0,
        "domain": "indoor",
        "scene_id": "scene",
        "scan_id": "scan",
        "image_relpath": "image.png",
        "depth_relpath": "depth.npy",
        "mask_relpath": "mask.npy",
    }
    config = {
        "model": {"input_size": 518},
        "metric": {
            "boundary_gradient_quantile": 0.9,
            "boundary_weight": 5.0,
            "inverse_depth_epsilon": 1e-6,
            "min_depth": 0.1,
            "max_depth": 350.0,
        },
    }
    backend = FakeBackend()
    rows = process_direct_sample(
        backend=backend,
        dataset_root=tmp_path,
        record=record,
        base_config=config,
        input_sizes=[518, 574],
    )
    assert backend.calls == [518, 574]
    assert [row["input_size"] for row in rows] == [518, 574]
    assert all(np.isclose(row["primary_utility_sum"], 0.0) for row in rows)
