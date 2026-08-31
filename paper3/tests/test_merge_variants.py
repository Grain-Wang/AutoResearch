from __future__ import annotations

import numpy as np
from paper3.experiments.bar_depth.core import make_regions
from paper3.experiments.bar_depth.merge_variants import (
    PATCH_VARIANTS,
    base_depth_unsharp_mask,
    patch_refined_core,
    patch_refined_cores,
    rgb_guided_bilateral_sharpening,
)


def test_aligned_replacement_is_identity_for_identical_contexts() -> None:
    region = make_regions(24, 32, 3, 4, 1.5)[5]
    rng = np.random.default_rng(5)
    context = rng.normal(size=(region.context_side, region.context_side))
    refined, scale, shift = patch_refined_core(
        context,
        context,
        region,
        variant="aligned_patch_replacement",
        sigma_fraction=0.03125,
        feather_fraction=0.125,
        trim_quantile=0.9,
        affine_iterations=3,
    )
    expected = context[
        region.core_y0 : region.core_y0 + region.y1 - region.y0,
        region.core_x0 : region.core_x0 + region.x1 - region.x0,
    ]
    np.testing.assert_allclose(refined, expected, atol=1e-10)
    assert np.isclose(scale, 1.0)
    assert np.isclose(shift, 0.0)


def test_shared_patch_intermediates_match_independent_variants() -> None:
    region = make_regions(48, 64, 3, 4, 1.5)[6]
    rng = np.random.default_rng(17)
    base_context = rng.normal(size=(region.context_side, region.context_side))
    patch_context = (
        1.7 * base_context - 0.2 + rng.normal(scale=0.05, size=base_context.shape)
    )
    parameters = {
        "sigma_fraction": 0.03125,
        "feather_fraction": 0.125,
        "trim_quantile": 0.9,
        "affine_iterations": 3,
    }
    shared, shared_scale, shared_shift = patch_refined_cores(
        base_context,
        patch_context,
        region,
        **parameters,
    )
    for variant in PATCH_VARIANTS:
        independent, scale, shift = patch_refined_core(
            base_context,
            patch_context,
            region,
            variant=variant,
            **parameters,
        )
        np.testing.assert_array_equal(shared[variant], independent)
        assert shared_scale == scale
        assert shared_shift == shift


def test_no_forward_sharpeners_are_finite_and_shape_preserving() -> None:
    rng = np.random.default_rng(9)
    base = rng.normal(size=(16, 20))
    image = rng.random(size=(16, 20, 3))
    unsharp = base_depth_unsharp_mask(base, sigma_pixels=2.0, amount=0.5)
    guided = rgb_guided_bilateral_sharpening(
        base,
        image,
        radius=1,
        spatial_sigma=1.0,
        color_sigma=0.1,
        amount=0.5,
    )
    assert unsharp.shape == base.shape
    assert guided.shape == base.shape
    assert np.isfinite(unsharp).all()
    assert np.isfinite(guided).all()


def test_rgb_guided_sharpening_preserves_constant_disparity() -> None:
    base = np.full((12, 12), 3.0)
    image = np.zeros((12, 12, 3))
    image[:, 6:] = 1.0
    guided = rgb_guided_bilateral_sharpening(
        base,
        image,
        radius=1,
        spatial_sigma=1.0,
        color_sigma=0.1,
        amount=0.5,
    )
    np.testing.assert_allclose(guided, base, atol=1e-12)
