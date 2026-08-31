from __future__ import annotations

import cv2
import numpy as np
from paper3.experiments.bar_depth.core import make_regions
from paper3.experiments.bar_depth.selectors.boosting2021_selector import (
    official_thresholded_sobel_gradient,
    score_fixed_regions,
    select_boosting_regions,
)


def test_official_gradient_matches_direct_reference_formula() -> None:
    image = np.zeros((24, 32, 3), dtype=np.uint8)
    image[:, 16:] = 255
    gray = np.dot(image.astype(np.float64) / 255.0, [0.2989, 0.5870, 0.1140])
    reference = np.abs(cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)) + np.abs(
        cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    )
    threshold = reference[reference > 0].mean()
    reference[reference < threshold] = 0
    actual = official_thresholded_sobel_gradient(image)
    np.testing.assert_allclose(actual, reference, rtol=0, atol=0)


def test_scores_are_local_over_global_density_ratios() -> None:
    rng = np.random.default_rng(7)
    image = rng.integers(0, 256, size=(24, 32, 3), dtype=np.uint8)
    regions = make_regions(24, 32, rows=3, columns=4, context_scale=1.0)
    scores, density = score_fixed_regions(image, regions)
    assert density > 0
    assert scores.shape == (12,)
    assert np.isclose(scores.mean(), 1.0)


def test_official_threshold_track_can_abstain() -> None:
    scores = np.asarray([2.0, 1.5, 0.9, 0.8])
    exact = select_boosting_regions(
        scores, budget_count=3, require_official_density_threshold=False
    )
    thresholded = select_boosting_regions(
        scores, budget_count=3, require_official_density_threshold=True
    )
    assert exact.tolist() == [0, 1, 2]
    assert thresholded.tolist() == [0, 1]
