"""Budget-matched extraction of the Boosting MDE 2021 patch criterion."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from ..core import Region


def official_thresholded_sobel_gradient(image_rgb: np.ndarray) -> np.ndarray:
    """Reproduce the official selector's thresholded RGB Sobel magnitude."""
    image = np.asarray(image_rgb)
    if image.ndim != 3 or image.shape[2] < 3:
        raise ValueError("Boosting selector expects an RGB image")
    image_float = image[..., :3].astype(np.float64)
    if image_float.max(initial=0.0) > 1.0:
        image_float /= 255.0
    gray = np.dot(image_float, np.asarray([0.2989, 0.5870, 0.1140]))
    gradient = np.abs(cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)) + np.abs(
        cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    )
    positive = gradient[gradient > 0]
    if positive.size == 0:
        return np.zeros_like(gradient)
    threshold = float(positive.mean())
    return np.where(gradient >= threshold, gradient, 0.0)


def score_fixed_regions(
    image_rgb: np.ndarray, regions: list[Region]
) -> tuple[np.ndarray, float]:
    """Score frozen target cells by official local/global gradient density."""
    gradient = official_thresholded_sobel_gradient(image_rgb)
    global_density = float(gradient.mean())
    if global_density <= 0:
        return np.zeros(len(regions), dtype=np.float64), global_density
    integral = cv2.integral(gradient)
    scores: list[float] = []
    for region in regions:
        area = (region.x1 - region.x0) * (region.y1 - region.y0)
        gradient_sum = (
            integral[region.y1, region.x1]
            - integral[region.y0, region.x1]
            - integral[region.y1, region.x0]
            + integral[region.y0, region.x0]
        )
        local_density = float(gradient_sum / area)
        scores.append(local_density / global_density)
    return np.asarray(scores, dtype=np.float64), global_density


def select_boosting_regions(
    scores: np.ndarray, *, budget_count: int, require_official_density_threshold: bool
) -> np.ndarray:
    """Select Top-K scores, optionally applying the official score>=1 filter."""
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1 or not 0 < budget_count <= values.size:
        raise ValueError("Invalid Boosting selector scores or budget")
    order = np.argsort(-values, kind="stable")[:budget_count]
    if require_official_density_threshold:
        order = order[values[order] >= 1.0]
    return order


def boosting_score_records(
    scores: np.ndarray, exact_selected: np.ndarray, threshold_selected: np.ndarray
) -> list[dict[str, Any]]:
    """Return serializable per-region score and selection records."""
    exact = set(int(value) for value in exact_selected)
    threshold = set(int(value) for value in threshold_selected)
    return [
        {
            "region_id": region_id,
            "boosting_gradient_density_ratio": float(score),
            "passes_official_density_threshold": bool(score >= 1.0),
            "selected_exact_k": region_id in exact,
            "selected_at_most_k_official_threshold": region_id in threshold,
        }
        for region_id, score in enumerate(np.asarray(scores, dtype=np.float64))
    ]
