"""Core geometry, merging, and utility calculations for BAR-Depth."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter


@dataclass(frozen=True)
class Region:
    """A non-overlapping target cell and its square context crop."""

    region_id: int
    row: int
    column: int
    x0: int
    y0: int
    x1: int
    y1: int
    context_x0: int
    context_y0: int
    context_side: int
    core_x0: int
    core_y0: int


def make_regions(
    height: int, width: int, rows: int, columns: int, context_scale: float
) -> list[Region]:
    """Create a regular target grid with equally sized square context crops."""
    if rows <= 0 or columns <= 0 or context_scale < 1.0:
        raise ValueError("Invalid region geometry")
    y_edges = np.linspace(0, height, rows + 1, dtype=np.int64)
    x_edges = np.linspace(0, width, columns + 1, dtype=np.int64)
    regions: list[Region] = []
    region_id = 0
    for row in range(rows):
        for column in range(columns):
            x0, x1 = int(x_edges[column]), int(x_edges[column + 1])
            y0, y1 = int(y_edges[row]), int(y_edges[row + 1])
            target_width = x1 - x0
            target_height = y1 - y0
            side = int(np.ceil(max(target_width, target_height) * context_scale))
            center_x = 0.5 * (x0 + x1)
            center_y = 0.5 * (y0 + y1)
            context_x0 = int(np.floor(center_x - side / 2))
            context_y0 = int(np.floor(center_y - side / 2))
            core_x0 = x0 - context_x0
            core_y0 = y0 - context_y0
            regions.append(
                Region(
                    region_id=region_id,
                    row=row,
                    column=column,
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    context_x0=context_x0,
                    context_y0=context_y0,
                    context_side=side,
                    core_x0=core_x0,
                    core_y0=core_y0,
                )
            )
            region_id += 1
    return regions


def extract_square_context(array: np.ndarray, region: Region) -> np.ndarray:
    """Extract a context crop using reflect padding beyond image boundaries."""
    height, width = array.shape[:2]
    x0 = region.context_x0
    y0 = region.context_y0
    x1 = x0 + region.context_side
    y1 = y0 + region.context_side
    pad_left = max(0, -x0)
    pad_top = max(0, -y0)
    pad_right = max(0, x1 - width)
    pad_bottom = max(0, y1 - height)
    padding = ((pad_top, pad_bottom), (pad_left, pad_right))
    if array.ndim == 3:
        padding += ((0, 0),)
    padded = np.pad(array, padding, mode="reflect")
    source_x0 = x0 + pad_left
    source_y0 = y0 + pad_top
    return padded[
        source_y0 : source_y0 + region.context_side,
        source_x0 : source_x0 + region.context_side,
        ...,
    ]


def robust_affine_fit(
    source: np.ndarray,
    target: np.ndarray,
    *,
    trim_quantile: float,
    iterations: int,
    require_positive_slope: bool = True,
) -> tuple[float, float]:
    """Fit an affine map from source to target with residual trimming."""
    source_flat = np.asarray(source, dtype=np.float64).reshape(-1)
    target_flat = np.asarray(target, dtype=np.float64).reshape(-1)
    finite = np.isfinite(source_flat) & np.isfinite(target_flat)
    source_flat = source_flat[finite]
    target_flat = target_flat[finite]
    if source_flat.size < 16:
        raise ValueError("Too few finite values for affine alignment")
    keep = np.ones(source_flat.size, dtype=bool)
    scale, shift = 1.0, 0.0
    for _ in range(iterations):
        design = np.column_stack((source_flat[keep], np.ones(int(keep.sum()))))
        scale, shift = np.linalg.lstsq(design, target_flat[keep], rcond=None)[0]
        residual = np.abs(scale * source_flat + shift - target_flat)
        cutoff = float(np.quantile(residual, trim_quantile))
        keep = residual <= cutoff
    if require_positive_slope and scale <= 0:
        denominator = float(np.dot(source_flat, source_flat))
        scale = float(np.dot(source_flat, target_flat) / max(denominator, 1e-12))
        scale = max(scale, 1e-6)
        shift = float(np.median(target_flat - scale * source_flat))
    return float(scale), float(shift)


def positive_median_scale_fit(
    source: np.ndarray, target: np.ndarray
) -> tuple[float, float]:
    """Fit a positive scale-only map using the ratio of positive medians."""
    source_flat = np.asarray(source, dtype=np.float64).reshape(-1)
    target_flat = np.asarray(target, dtype=np.float64).reshape(-1)
    keep = (
        np.isfinite(source_flat)
        & np.isfinite(target_flat)
        & (source_flat > 0)
        & (target_flat > 0)
    )
    if int(keep.sum()) < 16:
        raise ValueError("Too few positive finite values for median-scale alignment")
    scale = float(np.median(target_flat[keep]) / np.median(source_flat[keep]))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("Median-scale alignment did not produce a positive scale")
    return scale, 0.0


def depth_boundary_weights(
    depth: np.ndarray,
    valid_mask: np.ndarray,
    *,
    gradient_quantile: float,
    boundary_weight: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return GT log-depth boundary weights and the binary boundary mask."""
    valid = np.asarray(valid_mask, dtype=bool) & np.isfinite(depth) & (depth > 0)
    log_depth = np.zeros_like(depth, dtype=np.float64)
    log_depth[valid] = np.log(depth[valid])
    gradient = np.zeros_like(log_depth)

    horizontal_valid = valid[:, 1:] & valid[:, :-1]
    horizontal = np.zeros_like(log_depth[:, 1:])
    horizontal[horizontal_valid] = np.abs(
        log_depth[:, 1:][horizontal_valid] - log_depth[:, :-1][horizontal_valid]
    )
    gradient[:, 1:] = np.maximum(gradient[:, 1:], horizontal)
    gradient[:, :-1] = np.maximum(gradient[:, :-1], horizontal)

    vertical_valid = valid[1:, :] & valid[:-1, :]
    vertical = np.zeros_like(log_depth[1:, :])
    vertical[vertical_valid] = np.abs(
        log_depth[1:, :][vertical_valid] - log_depth[:-1, :][vertical_valid]
    )
    gradient[1:, :] = np.maximum(gradient[1:, :], vertical)
    gradient[:-1, :] = np.maximum(gradient[:-1, :], vertical)

    positive = gradient[valid & (gradient > 0)]
    if positive.size:
        threshold = float(np.quantile(positive, gradient_quantile))
        boundary = valid & (gradient >= threshold)
    else:
        boundary = np.zeros_like(valid)
    weights = np.where(boundary, boundary_weight, 1.0).astype(np.float64)
    weights[~valid] = 0.0
    return weights, boundary


def raised_cosine_window(
    height: int, width: int, feather_fraction: float
) -> np.ndarray:
    """Build a separable window that is zero on target-cell boundaries."""
    if not 0 <= feather_fraction < 0.5:
        raise ValueError("feather_fraction must be in [0, 0.5)")

    def axis_window(length: int) -> np.ndarray:
        window = np.ones(length, dtype=np.float64)
        feather = max(1, int(round(length * feather_fraction)))
        phase = np.linspace(0.0, np.pi / 2.0, feather, endpoint=True)
        ramp = np.sin(phase) ** 2
        window[:feather] = ramp
        window[-feather:] = ramp[::-1]
        return window

    return np.outer(axis_window(height), axis_window(width))


def highpass_refined_core(
    base_context: np.ndarray,
    patch_context: np.ndarray,
    region: Region,
    *,
    sigma_fraction: float,
    feather_fraction: float,
    trim_quantile: float,
    affine_iterations: int,
) -> tuple[np.ndarray, float, float]:
    """Return a globally anchored, high-frequency refined target core."""
    scale, shift = robust_affine_fit(
        patch_context,
        base_context,
        trim_quantile=trim_quantile,
        iterations=affine_iterations,
    )
    aligned_patch = scale * patch_context + shift
    sigma = max(1.0, region.context_side * sigma_fraction)
    patch_high = aligned_patch - gaussian_filter(aligned_patch, sigma=sigma)
    base_high = base_context - gaussian_filter(base_context, sigma=sigma)
    correction = patch_high - base_high

    core_height = region.y1 - region.y0
    core_width = region.x1 - region.x0
    cy0, cx0 = region.core_y0, region.core_x0
    core_correction = correction[
        cy0 : cy0 + core_height,
        cx0 : cx0 + core_width,
    ]
    base_core = base_context[
        cy0 : cy0 + core_height,
        cx0 : cx0 + core_width,
    ]
    window = raised_cosine_window(core_height, core_width, feather_fraction)
    return base_core + window * core_correction, scale, shift


def prediction_error_maps(
    disparity: np.ndarray,
    depth: np.ndarray,
    valid_mask: np.ndarray,
    *,
    metric_scale: float,
    metric_shift: float,
    inverse_depth_epsilon: float,
    min_depth: float,
    max_depth: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert relative disparity with a fixed alignment and return AbsRel maps."""
    if not 0 < min_depth < max_depth:
        raise ValueError("Invalid prediction depth evaluation range")
    aligned_inverse = np.maximum(
        metric_scale * disparity.astype(np.float64) + metric_shift,
        inverse_depth_epsilon,
    )
    predicted_depth = np.clip(1.0 / aligned_inverse, min_depth, max_depth)
    valid = np.asarray(valid_mask, dtype=bool) & np.isfinite(depth) & (depth > 0)
    error = np.zeros_like(depth, dtype=np.float64)
    error[valid] = np.abs(predicted_depth[valid] - depth[valid]) / depth[valid]
    return error, predicted_depth


def gradient_score(array: np.ndarray, region: Region) -> float:
    """Compute a cheap mean gradient score inside a target region."""
    values = np.asarray(array, dtype=np.float64)
    if values.ndim == 3:
        values = (
            0.2989 * values[..., 0] + 0.5870 * values[..., 1] + 0.1140 * values[..., 2]
        )
    gy, gx = np.gradient(values)
    magnitude = np.hypot(gx, gy)
    core = magnitude[region.y0 : region.y1, region.x0 : region.x1]
    return float(np.mean(core))
