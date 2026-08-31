from __future__ import annotations

import numpy as np
from paper3.experiments.bar_depth.core import (
    depth_boundary_weights,
    extract_square_context,
    make_regions,
    positive_median_scale_fit,
    prediction_error_maps,
    robust_affine_fit,
)


def test_regions_partition_targets_and_extract_context() -> None:
    regions = make_regions(768, 1024, rows=3, columns=4, context_scale=1.5)
    coverage = np.zeros((768, 1024), dtype=np.int64)
    image = np.arange(768 * 1024, dtype=np.float64).reshape(768, 1024)
    for region in regions:
        coverage[region.y0 : region.y1, region.x0 : region.x1] += 1
        context = extract_square_context(image, region)
        assert context.shape == (384, 384)
    assert len(regions) == 12
    assert np.all(coverage == 1)


def test_robust_affine_fit_recovers_positive_mapping() -> None:
    source = np.linspace(0.1, 2.0, 1000)
    target = 2.5 * source - 0.3
    target[0] = 1000.0
    scale, shift = robust_affine_fit(source, target, trim_quantile=0.9, iterations=3)
    assert np.isclose(scale, 2.5, atol=1e-6)
    assert np.isclose(shift, -0.3, atol=1e-6)


def test_positive_median_scale_fit_preserves_positive_domain() -> None:
    source = np.linspace(0.1, 2.0, 1000)
    target = 3.0 * source
    target[0] = 1000.0
    scale, shift = positive_median_scale_fit(source, target)
    assert np.isclose(scale, 3.0, rtol=0.01)
    assert shift == 0.0
    assert np.all(scale * source + shift > 0)


def test_prediction_depth_is_clipped_to_evaluation_range() -> None:
    disparity = np.asarray([[0.0, 100.0]])
    depth = np.asarray([[350.0, 0.1]])
    valid = np.ones_like(depth, dtype=bool)
    error, prediction = prediction_error_maps(
        disparity,
        depth,
        valid,
        metric_scale=1.0,
        metric_shift=0.0,
        inverse_depth_epsilon=1e-6,
        min_depth=0.1,
        max_depth=350.0,
    )
    assert np.allclose(prediction, depth)
    assert np.allclose(error, 0.0)


def test_boundary_weights_emphasize_depth_step() -> None:
    depth = np.ones((8, 8), dtype=np.float64)
    depth[:, 4:] = 2.0
    valid = np.ones_like(depth, dtype=bool)
    weights, boundary = depth_boundary_weights(
        depth, valid, gradient_quantile=0.9, boundary_weight=5.0
    )
    assert boundary[:, 3:5].all()
    assert np.all(weights[boundary] == 5.0)
    assert np.all(weights[~boundary] == 1.0)
