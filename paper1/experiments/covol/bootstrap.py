"""Paired frozen-cluster bootstrap for CoVoL policy comparisons."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace

try:
    from paper1.experiments.covol.metrics import (
        clean_gain_retention,
        corruption_metrics,
        pareto_hypervolume,
    )
except ModuleNotFoundError:  # Direct script consumers in this directory.
    from metrics import (  # type: ignore[no-redef]
        clean_gain_retention,
        corruption_metrics,
        pareto_hypervolume,
    )


@dataclass(frozen=True)
class PolicyImageOutcome:
    """Per-image losses for every frozen coverage threshold."""

    image_id: str
    cluster_id: str
    d0_clean_loss: float
    d1_clean_loss: float
    routed_clean_losses: tuple[float, ...]
    routed_variant_losses: tuple[tuple[float, ...], ...]


@dataclass(frozen=True)
class ClusterBootstrapResult:
    """Point estimate and percentile interval for a paired HV difference."""

    status: str
    estimate: float | None
    ci_lower: float | None
    ci_upper: float | None
    cluster_count: int
    replicates: int
    valid_replicates: int
    invalid_replicates: int
    invalid_fraction: float


@dataclass(frozen=True)
class ConstrainedRiskBootstrapResult:
    """Paired primary-risk differences at dev-frozen operating points."""

    status: str
    cvar_estimate: float | None
    cvar_ci_lower: float | None
    cvar_ci_upper: float | None
    worst_of_n_estimate: float | None
    worst_of_n_ci_lower: float | None
    worst_of_n_ci_upper: float | None
    cluster_count: int
    replicates: int
    valid_replicates: int
    invalid_replicates: int
    invalid_fraction: float


class UnstableCleanGainError(ValueError):
    """Raised when a sampled clean-gain denominator is not practically positive."""


def _validate_outcomes(outcomes: Sequence[PolicyImageOutcome]) -> tuple[int, int]:
    if not outcomes:
        raise ValueError("outcomes must not be empty")
    threshold_count = len(outcomes[0].routed_clean_losses)
    if threshold_count == 0:
        raise ValueError("each outcome must contain at least one threshold")
    if len(outcomes[0].routed_variant_losses) != threshold_count:
        raise ValueError("clean/corruption threshold count mismatch")
    variant_count = len(outcomes[0].routed_variant_losses[0])
    if variant_count == 0:
        raise ValueError("each threshold must contain caption variants")
    seen_images: set[str] = set()
    for outcome in outcomes:
        if not outcome.image_id or not outcome.cluster_id:
            raise ValueError("image_id and cluster_id must be nonempty")
        if outcome.image_id in seen_images:
            raise ValueError(f"duplicate image_id: {outcome.image_id}")
        if len(outcome.routed_clean_losses) != threshold_count:
            raise ValueError("threshold count mismatch")
        if len(outcome.routed_variant_losses) != threshold_count:
            raise ValueError("clean/corruption threshold count mismatch")
        if any(
            len(variants) != variant_count for variants in outcome.routed_variant_losses
        ):
            raise ValueError("caption variant count mismatch")
        numeric_values = (
            outcome.d0_clean_loss,
            outcome.d1_clean_loss,
            *outcome.routed_clean_losses,
            *(
                value
                for variants in outcome.routed_variant_losses
                for value in variants
            ),
        )
        if any(not math.isfinite(float(value)) for value in numeric_values):
            raise ValueError("outcomes contain a non-finite loss")
        seen_images.add(outcome.image_id)
    return threshold_count, variant_count


def policy_hypervolume(
    outcomes: Sequence[PolicyImageOutcome],
    *,
    reference_cvar: float,
    minimum_clean_gain: float = 0.0,
) -> float:
    """Recompute retention, CVaR, Pareto front, and HV from image rows."""

    threshold_count, variant_count = _validate_outcomes(outcomes)
    if not math.isfinite(minimum_clean_gain) or minimum_clean_gain < 0.0:
        raise ValueError("minimum_clean_gain must be finite and nonnegative")
    d0_losses = [outcome.d0_clean_loss for outcome in outcomes]
    d1_losses = [outcome.d1_clean_loss for outcome in outcomes]
    clean_gain = sum(
        d0_loss - d1_loss for d0_loss, d1_loss in zip(d0_losses, d1_losses, strict=True)
    ) / len(d0_losses)
    if clean_gain <= minimum_clean_gain:
        raise UnstableCleanGainError(
            "STOP_UNSTABLE_CLEAN_GAIN: sampled clean gain does not exceed "
            "the frozen practical threshold"
        )
    points: list[tuple[float, float]] = []
    for threshold in range(threshold_count):
        retention = clean_gain_retention(
            d0_losses,
            d1_losses,
            [outcome.routed_clean_losses[threshold] for outcome in outcomes],
            clean_gain_ci_lower=clean_gain,
        )
        risks = corruption_metrics(
            d0_losses,
            [outcome.routed_variant_losses[threshold] for outcome in outcomes],
            expected_variants=variant_count,
        )
        points.append((retention, risks.cvar))
    return pareto_hypervolume(
        points,
        reference_retention=0.0,
        reference_cvar=reference_cvar,
    )


def cluster_bootstrap_indices(
    cluster_ids: Sequence[str],
    *,
    replicates: int,
    seed: int,
) -> list[tuple[int, ...]]:
    """Sample clusters with replacement while retaining all member images."""

    if replicates <= 0:
        raise ValueError("replicates must be positive")
    if not cluster_ids or any(not cluster_id for cluster_id in cluster_ids):
        raise ValueError("cluster_ids must be nonempty strings")
    members: dict[str, list[int]] = defaultdict(list)
    for index, cluster_id in enumerate(cluster_ids):
        members[cluster_id].append(index)
    clusters = sorted(members)
    if len(clusters) < 2:
        raise ValueError("at least two independent clusters are required")
    rng = random.Random(seed)
    samples: list[tuple[int, ...]] = []
    for _ in range(replicates):
        indices: list[int] = []
        for _ in clusters:
            sampled_cluster = rng.choice(clusters)
            indices.extend(members[sampled_cluster])
        samples.append(tuple(indices))
    return samples


def _percentile(values: Sequence[float], probability: float) -> float:
    if not values or not 0.0 <= probability <= 1.0:
        raise ValueError("invalid percentile input")
    ordered = sorted(float(value) for value in values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def cluster_bootstrap_hypervolume_difference(
    left: Sequence[PolicyImageOutcome],
    right: Sequence[PolicyImageOutcome],
    *,
    reference_cvar: float,
    replicates: int = 10_000,
    seed: int = 20260821,
    confidence: float = 0.95,
    minimum_clean_gain: float,
    maximum_invalid_fraction: float = 0.05,
) -> ClusterBootstrapResult:
    """Paired cluster bootstrap with full metric recomputation per replicate."""

    _validate_outcomes(left)
    _validate_outcomes(right)
    if len(left) != len(right):
        raise ValueError("paired methods must contain the same images")
    for left_row, right_row in zip(left, right, strict=True):
        if (left_row.image_id, left_row.cluster_id) != (
            right_row.image_id,
            right_row.cluster_id,
        ):
            raise ValueError("paired methods must have identical image ordering")
        if (
            left_row.d0_clean_loss != right_row.d0_clean_loss
            or left_row.d1_clean_loss != right_row.d1_clean_loss
        ):
            raise ValueError("paired methods must share the same frozen experts")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1)")
    if not 0.0 <= maximum_invalid_fraction < 1.0:
        raise ValueError("maximum_invalid_fraction must be in [0, 1)")

    try:
        estimate = policy_hypervolume(
            left,
            reference_cvar=reference_cvar,
            minimum_clean_gain=minimum_clean_gain,
        ) - policy_hypervolume(
            right,
            reference_cvar=reference_cvar,
            minimum_clean_gain=minimum_clean_gain,
        )
    except UnstableCleanGainError:
        return ClusterBootstrapResult(
            status="STOP_UNSTABLE_CLEAN_GAIN",
            estimate=None,
            ci_lower=None,
            ci_upper=None,
            cluster_count=len({row.cluster_id for row in left}),
            replicates=replicates,
            valid_replicates=0,
            invalid_replicates=replicates,
            invalid_fraction=1.0,
        )
    sampled_indices = cluster_bootstrap_indices(
        [row.cluster_id for row in left],
        replicates=replicates,
        seed=seed,
    )
    differences: list[float] = []
    for indices in sampled_indices:
        left_sample = [
            replace(
                left[index],
                image_id=f"{left[index].image_id}@bootstrap-{position}",
            )
            for position, index in enumerate(indices)
        ]
        right_sample = [
            replace(
                right[index],
                image_id=f"{right[index].image_id}@bootstrap-{position}",
            )
            for position, index in enumerate(indices)
        ]
        try:
            difference = policy_hypervolume(
                left_sample,
                reference_cvar=reference_cvar,
                minimum_clean_gain=minimum_clean_gain,
            ) - policy_hypervolume(
                right_sample,
                reference_cvar=reference_cvar,
                minimum_clean_gain=minimum_clean_gain,
            )
        except UnstableCleanGainError:
            continue
        differences.append(difference)
    valid_replicates = len(differences)
    invalid_replicates = replicates - valid_replicates
    invalid_fraction = invalid_replicates / replicates
    if invalid_fraction > maximum_invalid_fraction or not differences:
        return ClusterBootstrapResult(
            status="STOP_UNSTABLE_CLEAN_GAIN",
            estimate=estimate,
            ci_lower=None,
            ci_upper=None,
            cluster_count=len({row.cluster_id for row in left}),
            replicates=replicates,
            valid_replicates=valid_replicates,
            invalid_replicates=invalid_replicates,
            invalid_fraction=invalid_fraction,
        )
    tail = (1.0 - confidence) / 2.0
    return ClusterBootstrapResult(
        status="PASS",
        estimate=estimate,
        ci_lower=_percentile(differences, tail),
        ci_upper=_percentile(differences, 1.0 - tail),
        cluster_count=len({row.cluster_id for row in left}),
        replicates=replicates,
        valid_replicates=valid_replicates,
        invalid_replicates=invalid_replicates,
        invalid_fraction=invalid_fraction,
    )


def _fixed_threshold_risks(
    outcomes: Sequence[PolicyImageOutcome],
    *,
    threshold_index: int,
) -> tuple[float, float]:
    _, variant_count = _validate_outcomes(outcomes)
    if (
        isinstance(threshold_index, bool)
        or not isinstance(threshold_index, int)
        or not 0 <= threshold_index < len(outcomes[0].routed_variant_losses)
    ):
        raise ValueError("threshold_index lies outside the frozen coverage grid")
    risks = corruption_metrics(
        [row.d0_clean_loss for row in outcomes],
        [row.routed_variant_losses[threshold_index] for row in outcomes],
        expected_variants=variant_count,
    )
    return risks.cvar, risks.worst_of_n


def _practical_clean_gain(
    outcomes: Sequence[PolicyImageOutcome],
    *,
    minimum_clean_gain: float,
) -> float:
    clean_gain = sum(row.d0_clean_loss - row.d1_clean_loss for row in outcomes) / len(
        outcomes
    )
    if clean_gain <= minimum_clean_gain:
        raise UnstableCleanGainError(
            "STOP_UNSTABLE_CLEAN_GAIN: sampled clean gain does not exceed "
            "the frozen practical threshold"
        )
    return clean_gain


def cluster_bootstrap_constrained_risk_difference(
    left: Sequence[PolicyImageOutcome],
    right: Sequence[PolicyImageOutcome],
    *,
    left_threshold_index: int,
    right_threshold_index: int,
    minimum_clean_gain: float,
    replicates: int = 10_000,
    seed: int = 20260821,
    confidence: float = 0.95,
    maximum_invalid_fraction: float = 0.05,
) -> ConstrainedRiskBootstrapResult:
    """Compare primary risks at thresholds frozen independently on dev.

    Threshold indices are inputs rather than selected here, so no internal-test
    value can change either method's operating point.
    """

    _validate_outcomes(left)
    _validate_outcomes(right)
    if len(left) != len(right):
        raise ValueError("paired methods must contain the same images")
    for left_row, right_row in zip(left, right, strict=True):
        if (left_row.image_id, left_row.cluster_id) != (
            right_row.image_id,
            right_row.cluster_id,
        ):
            raise ValueError("paired methods must have identical image ordering")
        if (
            left_row.d0_clean_loss != right_row.d0_clean_loss
            or left_row.d1_clean_loss != right_row.d1_clean_loss
        ):
            raise ValueError("paired methods must share the same frozen experts")
    if not math.isfinite(minimum_clean_gain) or minimum_clean_gain < 0.0:
        raise ValueError("minimum_clean_gain must be finite and nonnegative")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1)")
    if not 0.0 <= maximum_invalid_fraction < 1.0:
        raise ValueError("maximum_invalid_fraction must be in [0, 1)")

    cluster_count = len({row.cluster_id for row in left})
    try:
        _practical_clean_gain(left, minimum_clean_gain=minimum_clean_gain)
        left_cvar, left_worst = _fixed_threshold_risks(
            left,
            threshold_index=left_threshold_index,
        )
        right_cvar, right_worst = _fixed_threshold_risks(
            right,
            threshold_index=right_threshold_index,
        )
    except UnstableCleanGainError:
        return ConstrainedRiskBootstrapResult(
            status="STOP_UNSTABLE_CLEAN_GAIN",
            cvar_estimate=None,
            cvar_ci_lower=None,
            cvar_ci_upper=None,
            worst_of_n_estimate=None,
            worst_of_n_ci_lower=None,
            worst_of_n_ci_upper=None,
            cluster_count=cluster_count,
            replicates=replicates,
            valid_replicates=0,
            invalid_replicates=replicates,
            invalid_fraction=1.0,
        )

    sampled_indices = cluster_bootstrap_indices(
        [row.cluster_id for row in left],
        replicates=replicates,
        seed=seed,
    )
    cvar_differences: list[float] = []
    worst_differences: list[float] = []
    for indices in sampled_indices:
        left_sample = [
            replace(
                left[index],
                image_id=f"{left[index].image_id}@bootstrap-{position}",
            )
            for position, index in enumerate(indices)
        ]
        right_sample = [
            replace(
                right[index],
                image_id=f"{right[index].image_id}@bootstrap-{position}",
            )
            for position, index in enumerate(indices)
        ]
        try:
            _practical_clean_gain(
                left_sample,
                minimum_clean_gain=minimum_clean_gain,
            )
        except UnstableCleanGainError:
            continue
        sampled_left_cvar, sampled_left_worst = _fixed_threshold_risks(
            left_sample,
            threshold_index=left_threshold_index,
        )
        sampled_right_cvar, sampled_right_worst = _fixed_threshold_risks(
            right_sample,
            threshold_index=right_threshold_index,
        )
        cvar_differences.append(sampled_left_cvar - sampled_right_cvar)
        worst_differences.append(sampled_left_worst - sampled_right_worst)

    valid_replicates = len(cvar_differences)
    invalid_replicates = replicates - valid_replicates
    invalid_fraction = invalid_replicates / replicates
    common = {
        "cvar_estimate": left_cvar - right_cvar,
        "worst_of_n_estimate": left_worst - right_worst,
        "cluster_count": cluster_count,
        "replicates": replicates,
        "valid_replicates": valid_replicates,
        "invalid_replicates": invalid_replicates,
        "invalid_fraction": invalid_fraction,
    }
    if invalid_fraction > maximum_invalid_fraction or not cvar_differences:
        return ConstrainedRiskBootstrapResult(
            status="STOP_UNSTABLE_CLEAN_GAIN",
            cvar_ci_lower=None,
            cvar_ci_upper=None,
            worst_of_n_ci_lower=None,
            worst_of_n_ci_upper=None,
            **common,
        )
    tail = (1.0 - confidence) / 2.0
    return ConstrainedRiskBootstrapResult(
        status="PASS",
        cvar_ci_lower=_percentile(cvar_differences, tail),
        cvar_ci_upper=_percentile(cvar_differences, 1.0 - tail),
        worst_of_n_ci_lower=_percentile(worst_differences, tail),
        worst_of_n_ci_upper=_percentile(worst_differences, 1.0 - tail),
        **common,
    )
