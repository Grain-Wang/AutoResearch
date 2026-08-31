"""Frozen patch and no-extra-forward merge variants for BAR-Depth."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from .core import Region, raised_cosine_window, robust_affine_fit

PATCH_VARIANTS = (
    "highpass_residual",
    "aligned_patch_replacement",
    "patch_high_frequency_without_base_subtraction",
)


def _aligned_patch(
    base_context: np.ndarray,
    patch_context: np.ndarray,
    *,
    trim_quantile: float,
    affine_iterations: int,
) -> tuple[np.ndarray, float, float]:
    scale, shift = robust_affine_fit(
        patch_context,
        base_context,
        trim_quantile=trim_quantile,
        iterations=affine_iterations,
    )
    return scale * patch_context + shift, scale, shift


def _core(array: np.ndarray, region: Region) -> np.ndarray:
    height = region.y1 - region.y0
    width = region.x1 - region.x0
    return array[
        region.core_y0 : region.core_y0 + height,
        region.core_x0 : region.core_x0 + width,
    ]


def patch_refined_core(
    base_context: np.ndarray,
    patch_context: np.ndarray,
    region: Region,
    *,
    variant: str,
    sigma_fraction: float,
    feather_fraction: float,
    trim_quantile: float,
    affine_iterations: int,
) -> tuple[np.ndarray, float, float]:
    """Apply one frozen patch-based merge variant to a target cell."""
    aligned_patch, scale, shift = _aligned_patch(
        base_context,
        patch_context,
        trim_quantile=trim_quantile,
        affine_iterations=affine_iterations,
    )
    base_core = _core(base_context, region)
    patch_core = _core(aligned_patch, region)
    window = raised_cosine_window(
        region.y1 - region.y0,
        region.x1 - region.x0,
        feather_fraction,
    )
    if variant == "aligned_patch_replacement":
        refined = base_core + window * (patch_core - base_core)
    elif variant in {
        "highpass_residual",
        "patch_high_frequency_without_base_subtraction",
    }:
        sigma = max(1.0, region.context_side * sigma_fraction)
        patch_high = aligned_patch - gaussian_filter(aligned_patch, sigma=sigma)
        correction = patch_high
        if variant == "highpass_residual":
            base_high = base_context - gaussian_filter(base_context, sigma=sigma)
            correction = patch_high - base_high
        refined = base_core + window * _core(correction, region)
    else:
        raise ValueError(f"Unknown patch merge variant: {variant}")
    return refined, scale, shift


def patch_refined_cores(
    base_context: np.ndarray,
    patch_context: np.ndarray,
    region: Region,
    *,
    sigma_fraction: float,
    feather_fraction: float,
    trim_quantile: float,
    affine_iterations: int,
) -> tuple[dict[str, np.ndarray], float, float]:
    """Compute all patch variants while sharing identical intermediate arrays."""
    aligned_patch, scale, shift = _aligned_patch(
        base_context,
        patch_context,
        trim_quantile=trim_quantile,
        affine_iterations=affine_iterations,
    )
    base_core = _core(base_context, region)
    patch_core = _core(aligned_patch, region)
    window = raised_cosine_window(
        region.y1 - region.y0,
        region.x1 - region.x0,
        feather_fraction,
    )
    sigma = max(1.0, region.context_side * sigma_fraction)
    patch_high = aligned_patch - gaussian_filter(aligned_patch, sigma=sigma)
    base_high = base_context - gaussian_filter(base_context, sigma=sigma)
    refinements = {
        "aligned_patch_replacement": base_core + window * (patch_core - base_core),
        "patch_high_frequency_without_base_subtraction": base_core
        + window * _core(patch_high, region),
        "highpass_residual": base_core + window * _core(patch_high - base_high, region),
    }
    return refinements, scale, shift


def base_depth_unsharp_mask(
    base_disparity: np.ndarray, *, sigma_pixels: float, amount: float
) -> np.ndarray:
    """Sharpen base disparity without another model forward pass."""
    if sigma_pixels <= 0 or amount < 0:
        raise ValueError("Invalid base unsharp parameters")
    base = np.asarray(base_disparity, dtype=np.float64)
    smooth = gaussian_filter(base, sigma=sigma_pixels)
    return base + amount * (base - smooth)


def rgb_guided_bilateral_sharpening(
    base_disparity: np.ndarray,
    image_rgb: np.ndarray,
    *,
    radius: int,
    spatial_sigma: float,
    color_sigma: float,
    amount: float,
) -> np.ndarray:
    """Apply a small joint bilateral unsharp filter guided by RGB differences."""
    if radius < 1 or spatial_sigma <= 0 or color_sigma <= 0 or amount < 0:
        raise ValueError("Invalid RGB-guided bilateral parameters")
    base = np.asarray(base_disparity, dtype=np.float64)
    image = np.asarray(image_rgb, dtype=np.float64)
    if image.shape[:2] != base.shape or image.ndim != 3 or image.shape[2] < 3:
        raise ValueError("RGB guide and base disparity shapes disagree")
    padded_base = np.pad(base, radius, mode="reflect")
    padded_image = np.pad(
        image[..., :3], ((radius, radius), (radius, radius), (0, 0)), mode="reflect"
    )
    weighted_sum = np.zeros_like(base)
    weight_sum = np.zeros_like(base)
    height, width = base.shape
    for offset_y in range(-radius, radius + 1):
        for offset_x in range(-radius, radius + 1):
            y0 = radius + offset_y
            x0 = radius + offset_x
            neighbor_base = padded_base[y0 : y0 + height, x0 : x0 + width]
            neighbor_image = padded_image[y0 : y0 + height, x0 : x0 + width]
            spatial_distance = float(offset_x**2 + offset_y**2)
            color_distance = np.sum((neighbor_image - image[..., :3]) ** 2, axis=2)
            weight = np.exp(
                -spatial_distance / (2.0 * spatial_sigma**2)
                - color_distance / (2.0 * color_sigma**2)
            )
            weighted_sum += weight * neighbor_base
            weight_sum += weight
    smooth = weighted_sum / np.maximum(weight_sum, 1e-12)
    return base + amount * (base - smooth)
