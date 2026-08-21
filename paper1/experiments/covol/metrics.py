"""Unique image-level metric definitions for CoVoL-Depth."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import fmean


class NoCleanGainError(ValueError):
    """Raised when clean D1 gain is not demonstrably positive."""


@dataclass(frozen=True)
class Coverage:
    """Micro and macro coverage over eligible regions."""

    micro: float
    macro: float


@dataclass(frozen=True)
class CorruptionMetrics:
    """Metrics after variants are aggregated within image."""

    mean_regret: float
    worst_of_n: float
    cvar: float


def _finite(values: Sequence[float], *, name: str) -> list[float]:
    result = [float(value) for value in values]
    if not result:
        raise ValueError(f"{name} must not be empty")
    if any(not math.isfinite(value) for value in result):
        raise ValueError(f"{name} contains a non-finite value")
    return result


def image_regrets(
    d0_losses: Sequence[float],
    routed_variant_losses: Sequence[Sequence[float]],
) -> list[list[float]]:
    """Return signed loss differences, grouped by image then caption variant."""

    d0 = _finite(d0_losses, name="d0_losses")
    if len(d0) != len(routed_variant_losses):
        raise ValueError("d0_losses and routed_variant_losses length mismatch")

    grouped: list[list[float]] = []
    for index, (baseline, variants) in enumerate(
        zip(d0, routed_variant_losses, strict=True)
    ):
        variant_values = _finite(variants, name=f"variants[{index}]")
        grouped.append([loss - baseline for loss in variant_values])
    return grouped


def corruption_metrics(
    d0_losses: Sequence[float],
    routed_variant_losses: Sequence[Sequence[float]],
    *,
    expected_variants: int = 3,
    tail_fraction: float = 0.20,
) -> CorruptionMetrics:
    """Aggregate variants within image before aggregating across images."""

    regrets = image_regrets(d0_losses, routed_variant_losses)
    if any(len(values) != expected_variants for values in regrets):
        raise ValueError(f"each image must have exactly {expected_variants} variants")

    image_mean_regret = [fmean(values) for values in regrets]
    image_worst_regret = [max(values) for values in regrets]
    positive_image_worst = [max(0.0, value) for value in image_worst_regret]
    return CorruptionMetrics(
        mean_regret=fmean(image_mean_regret),
        worst_of_n=fmean(image_worst_regret),
        cvar=upper_tail_mean(positive_image_worst, tail_fraction=tail_fraction),
    )


def upper_tail_mean(
    image_risks: Sequence[float],
    *,
    tail_fraction: float = 0.20,
) -> float:
    """Empirical CVaR: mean of the largest ceil(alpha * n) image risks."""

    risks = _finite(image_risks, name="image_risks")
    if not 0.0 < tail_fraction <= 1.0:
        raise ValueError("tail_fraction must be in (0, 1]")
    tail_count = math.ceil(tail_fraction * len(risks))
    return fmean(sorted(risks, reverse=True)[:tail_count])


def coverage(
    selected_d1: Sequence[Sequence[bool]],
    eligible: Sequence[Sequence[bool]],
) -> Coverage:
    """Compute coverage using eligible regions as the only denominator."""

    if not selected_d1 or len(selected_d1) != len(eligible):
        raise ValueError("selected_d1 and eligible must have equal nonzero length")

    total_selected = 0
    total_eligible = 0
    image_coverages: list[float] = []
    for index, (selected_row, eligible_row) in enumerate(
        zip(selected_d1, eligible, strict=True)
    ):
        if len(selected_row) != len(eligible_row) or not eligible_row:
            raise ValueError(f"region shape mismatch at image {index}")
        eligible_count = sum(bool(value) for value in eligible_row)
        if eligible_count == 0:
            raise ValueError(f"image {index} has no eligible region")
        selected_count = sum(
            bool(selected) and bool(is_eligible)
            for selected, is_eligible in zip(
                selected_row,
                eligible_row,
                strict=True,
            )
        )
        total_selected += selected_count
        total_eligible += eligible_count
        image_coverages.append(selected_count / eligible_count)

    return Coverage(
        micro=total_selected / total_eligible,
        macro=fmean(image_coverages),
    )


def clean_gain_retention(
    d0_clean_losses: Sequence[float],
    d1_clean_losses: Sequence[float],
    routed_clean_losses: Sequence[float],
    *,
    clean_gain_ci_lower: float,
) -> float:
    """Return aggregate clean-gain retention or raise STOP_NO_CLEAN_GAIN."""

    d0 = _finite(d0_clean_losses, name="d0_clean_losses")
    d1 = _finite(d1_clean_losses, name="d1_clean_losses")
    routed = _finite(routed_clean_losses, name="routed_clean_losses")
    if len(d0) != len(d1) or len(d0) != len(routed):
        raise ValueError("clean loss arrays must have equal length")
    if clean_gain_ci_lower <= 0.0:
        raise NoCleanGainError("STOP_NO_CLEAN_GAIN")

    baseline_gain = fmean(d0) - fmean(d1)
    if baseline_gain <= 0.0:
        raise NoCleanGainError("STOP_NO_CLEAN_GAIN")
    routed_gain = fmean(d0) - fmean(routed)
    return routed_gain / baseline_gain


def pareto_hypervolume(
    points: Sequence[tuple[float, float]],
    *,
    reference_retention: float,
    reference_cvar: float,
) -> float:
    """2D hypervolume for maximizing retention and minimizing CVaR."""

    if not points:
        raise ValueError("points must not be empty")
    valid: list[tuple[float, float]] = []
    for retention, cvar in points:
        retention = float(retention)
        cvar = float(cvar)
        if not math.isfinite(retention) or not math.isfinite(cvar):
            raise ValueError("points contain a non-finite value")
        if retention > reference_retention and cvar < reference_cvar:
            valid.append((retention, cvar))
    if not valid:
        return 0.0

    valid.sort(key=lambda point: point[0], reverse=True)
    area = 0.0
    best_cvar = reference_cvar
    for index, (retention, cvar) in enumerate(valid):
        best_cvar = min(best_cvar, cvar)
        next_retention = (
            valid[index + 1][0] if index + 1 < len(valid) else reference_retention
        )
        width = max(0.0, retention - max(reference_retention, next_retention))
        area += width * (reference_cvar - best_cvar)
    return area


def advantage_tie_band(repeated_numeric_differences: Sequence[float]) -> float:
    """Nearest-rank 95th percentile of absolute repeated-run differences."""

    values = sorted(
        abs(value)
        for value in _finite(
            repeated_numeric_differences,
            name="repeated_numeric_differences",
        )
    )
    rank = math.ceil(0.95 * len(values))
    return values[rank - 1]
