"""Unique image-level metric definitions for CoVoL-Depth."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import fmean


class NoCleanGainError(ValueError):
    """Raised when clean D1 gain is not demonstrably positive."""


@dataclass(frozen=True)
class Coverage:
    """Cluster-balanced primary coverage plus sensitivity summaries."""

    cluster_balanced: float
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


def cluster_balanced_weights(cluster_ids: Sequence[str]) -> list[float]:
    """Give every cluster equal mass and every image equal within-cluster mass."""

    normalized = [str(value).strip() for value in cluster_ids]
    if not normalized or any(not value for value in normalized):
        raise ValueError("cluster_ids must contain nonempty strings")
    counts = Counter(normalized)
    cluster_count = len(counts)
    return [1.0 / (cluster_count * counts[value]) for value in normalized]


def weighted_mean(values: Sequence[float], weights: Sequence[float]) -> float:
    """Return a finite weighted mean after normalizing nonnegative weights."""

    normalized_values = _finite(values, name="values")
    normalized_weights = _finite(weights, name="weights")
    if len(normalized_values) != len(normalized_weights):
        raise ValueError("values and weights length mismatch")
    if any(weight < 0.0 for weight in normalized_weights):
        raise ValueError("weights must be nonnegative")
    total = sum(normalized_weights)
    if total <= 0.0:
        raise ValueError("weights must have positive total mass")
    return (
        sum(
            value * weight
            for value, weight in zip(
                normalized_values,
                normalized_weights,
                strict=True,
            )
        )
        / total
    )


def weighted_upper_tail_mean(
    image_risks: Sequence[float],
    sample_weights: Sequence[float],
    *,
    tail_fraction: float = 0.20,
) -> float:
    """Weighted empirical upper-tail CVaR with fractional boundary mass."""

    risks = _finite(image_risks, name="image_risks")
    weights = _finite(sample_weights, name="sample_weights")
    if len(risks) != len(weights):
        raise ValueError("image_risks and sample_weights length mismatch")
    if any(weight < 0.0 for weight in weights):
        raise ValueError("sample_weights must be nonnegative")
    if not 0.0 < tail_fraction <= 1.0:
        raise ValueError("tail_fraction must be in (0, 1]")
    total = sum(weights)
    if total <= 0.0:
        raise ValueError("sample_weights must have positive total mass")
    normalized = [weight / total for weight in weights]
    remaining = tail_fraction
    tail_sum = 0.0
    for risk, weight in sorted(
        zip(risks, normalized, strict=True),
        key=lambda item: item[0],
        reverse=True,
    ):
        included = min(weight, remaining)
        tail_sum += included * risk
        remaining -= included
        if remaining <= 1e-15:
            break
    return tail_sum / tail_fraction


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
    cluster_ids: Sequence[str],
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
    if len(cluster_ids) != len(regrets):
        raise ValueError("cluster_ids and image losses length mismatch")
    weights = cluster_balanced_weights(cluster_ids)
    return CorruptionMetrics(
        mean_regret=weighted_mean(image_mean_regret, weights),
        worst_of_n=weighted_mean(image_worst_regret, weights),
        cvar=weighted_upper_tail_mean(
            positive_image_worst,
            weights,
            tail_fraction=tail_fraction,
        ),
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
    *,
    cluster_ids: Sequence[str],
) -> Coverage:
    """Compute cluster-balanced primary and micro/macro sensitivity coverage."""

    if not selected_d1 or len(selected_d1) != len(eligible):
        raise ValueError("selected_d1 and eligible must have equal nonzero length")
    if len(cluster_ids) != len(selected_d1):
        raise ValueError("cluster_ids and image rows length mismatch")

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

    image_weights = cluster_balanced_weights(cluster_ids)
    return Coverage(
        cluster_balanced=weighted_mean(image_coverages, image_weights),
        micro=total_selected / total_eligible,
        macro=fmean(image_coverages),
    )


def clean_gain_retention(
    d0_clean_losses: Sequence[float],
    d1_clean_losses: Sequence[float],
    routed_clean_losses: Sequence[float],
    *,
    cluster_ids: Sequence[str],
    clean_gain_ci_lower: float,
) -> float:
    """Return aggregate clean-gain retention or raise STOP_NO_CLEAN_GAIN."""

    d0 = _finite(d0_clean_losses, name="d0_clean_losses")
    d1 = _finite(d1_clean_losses, name="d1_clean_losses")
    routed = _finite(routed_clean_losses, name="routed_clean_losses")
    if len(d0) != len(d1) or len(d0) != len(routed):
        raise ValueError("clean loss arrays must have equal length")
    if len(cluster_ids) != len(d0):
        raise ValueError("cluster_ids and clean loss arrays length mismatch")
    if clean_gain_ci_lower <= 0.0:
        raise NoCleanGainError("STOP_NO_CLEAN_GAIN")

    weights = cluster_balanced_weights(cluster_ids)
    baseline_gain = weighted_mean(d0, weights) - weighted_mean(d1, weights)
    if baseline_gain <= 0.0:
        raise NoCleanGainError("STOP_NO_CLEAN_GAIN")
    routed_gain = weighted_mean(d0, weights) - weighted_mean(routed, weights)
    return routed_gain / baseline_gain


def fixed_reference_cvar(
    always_d1_dev_cvar: float,
    *,
    margin_multiplier: float = 1.05,
) -> float:
    """Freeze the HV reference using always-D1 dev risk only."""

    value = float(always_d1_dev_cvar)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("always_d1_dev_cvar must be finite and positive")
    if not math.isfinite(margin_multiplier) or margin_multiplier <= 1.0:
        raise ValueError("margin_multiplier must be finite and greater than 1")
    return margin_multiplier * value


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
