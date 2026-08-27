from __future__ import annotations

import numpy as np
from paper1.experiments.bar_depth.core import (
    depth_boundary_weights,
    extract_square_context,
    make_regions,
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
