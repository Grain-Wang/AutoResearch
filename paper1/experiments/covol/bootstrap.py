"""Paired frozen-cluster bootstrap for CoVoL policy comparisons."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from statistics import fmean, stdev

try:
    from paper1.experiments.covol.metrics import (
        clean_gain_retention,
        cluster_balanced_weights,
        corruption_metrics,
        pareto_hypervolume,
        weighted_mean,
    )
except ModuleNotFoundError:  # Direct script consumers in this directory.
    from metrics import (  # type: ignore[no-redef]
        clean_gain_retention,
        cluster_balanced_weights,
        corruption_metrics,
        pareto_hypervolume,
        weighted_mean,
    )


@dataclass(frozen=True)
class PolicyImageOutcome:
    """Per-image losses for every frozen coverage threshold."""

    image_id: str
    cluster_id: str
    training_seed: int
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
    training_seed: int


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
    training_seed: int


@dataclass(frozen=True)
class RetentionBootstrapResult:
    """Retention point estimate and cluster-bootstrap uncertainty."""

    status: str
    estimate: float | None
    one_sided_lower: float | None
    ci_lower: float | None
    ci_upper: float | None
    cluster_count: int
    replicates: int
    valid_replicates: int
    invalid_replicates: int
    invalid_fraction: float
    training_seed: int


@dataclass(frozen=True)
class FixedSeedSummary:
    """Descriptive summary for preregistered fixed training repeats."""

    seeds: tuple[int, ...]
    estimates: tuple[float, ...]
    mean: float
    sample_sd: float
    favorable_direction: str
    direction_pass: bool


class UnstableCleanGainError(ValueError):
    """Raised when a sampled clean-gain denominator is not practically positive."""


def summarize_fixed_seed_estimates(
    estimates: Mapping[int, float],
    *,
    expected_seeds: Sequence[int] = (17, 29, 43),
    favorable_direction: str,
) -> FixedSeedSummary:
    """Report mean/SD and direction agreement without a seed-population CI."""

    seeds = tuple(int(seed) for seed in expected_seeds)
    if len(seeds) < 2 or len(set(seeds)) != len(seeds):
        raise ValueError("expected_seeds must contain at least two unique seeds")
    if set(estimates) != set(seeds):
        raise ValueError("estimates must cover every expected seed exactly once")
    values = tuple(float(estimates[seed]) for seed in seeds)
    if any(not math.isfinite(value) for value in values):
        raise ValueError("seed estimates must be finite")
    if favorable_direction == "negative":
        direction_pass = all(value < 0.0 for value in values)
    elif favorable_direction == "positive":
        direction_pass = all(value > 0.0 for value in values)
    else:
        raise ValueError("favorable_direction must be 'negative' or 'positive'")
    return FixedSeedSummary(
        seeds=seeds,
        estimates=values,
        mean=fmean(values),
        sample_sd=stdev(values),
        favorable_direction=favorable_direction,
        direction_pass=direction_pass,
    )


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
    training_seeds: set[int] = set()
    for outcome in outcomes:
        if not outcome.image_id or not outcome.cluster_id:
            raise ValueError("image_id and cluster_id must be nonempty")
        if outcome.image_id in seen_images:
            raise ValueError(f"duplicate image_id: {outcome.image_id}")
        if isinstance(outcome.training_seed, bool) or outcome.training_seed < 0:
            raise ValueError("training_seed must be a nonnegative integer")
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
        training_seeds.add(outcome.training_seed)
    if len(training_seeds) != 1:
        raise ValueError("one outcome table must contain exactly one training seed")
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
    cluster_ids = [outcome.cluster_id for outcome in outcomes]
    weights = cluster_balanced_weights(cluster_ids)
    clean_gain = weighted_mean(
        [
            d0_loss - d1_loss
            for d0_loss, d1_loss in zip(d0_losses, d1_losses, strict=True)
        ],
        weights,
    )
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
            cluster_ids=cluster_ids,
            clean_gain_ci_lower=clean_gain,
        )
        risks = corruption_metrics(
            d0_losses,
            [outcome.routed_variant_losses[threshold] for outcome in outcomes],
            cluster_ids=cluster_ids,
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

    draws = _cluster_bootstrap_draws(
        cluster_ids,
        replicates=replicates,
        seed=seed,
    )
    return [tuple(index for group in draw for index in group) for draw in draws]


def _cluster_bootstrap_draws(
    cluster_ids: Sequence[str],
    *,
    replicates: int,
    seed: int,
) -> list[tuple[tuple[int, ...], ...]]:
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
    return [
        tuple(tuple(members[rng.choice(clusters)]) for _ in clusters)
        for _ in range(replicates)
    ]


def _resample_outcomes(
    outcomes: Sequence[PolicyImageOutcome],
    draw: Sequence[Sequence[int]],
) -> list[PolicyImageOutcome]:
    sampled: list[PolicyImageOutcome] = []
    image_position = 0
    for draw_position, members in enumerate(draw):
        for index in members:
            row = outcomes[index]
            sampled.append(
                replace(
                    row,
                    image_id=f"{row.image_id}@bootstrap-{image_position}",
                    cluster_id=(f"{row.cluster_id}@bootstrap-cluster-{draw_position}"),
                )
            )
            image_position += 1
    return sampled


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


def _training_seed(outcomes: Sequence[PolicyImageOutcome]) -> int:
    _validate_outcomes(outcomes)
    return outcomes[0].training_seed


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
    training_seed = _training_seed(left)
    if _training_seed(right) != training_seed:
        raise ValueError("paired methods must use the same training seed")
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
            training_seed=training_seed,
        )
    sampled_draws = _cluster_bootstrap_draws(
        [row.cluster_id for row in left],
        replicates=replicates,
        seed=seed,
    )
    differences: list[float] = []
    for draw in sampled_draws:
        left_sample = _resample_outcomes(left, draw)
        right_sample = _resample_outcomes(right, draw)
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
            training_seed=training_seed,
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
        training_seed=training_seed,
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
        cluster_ids=[row.cluster_id for row in outcomes],
        expected_variants=variant_count,
    )
    return risks.cvar, risks.worst_of_n


def _practical_clean_gain(
    outcomes: Sequence[PolicyImageOutcome],
    *,
    minimum_clean_gain: float,
) -> float:
    clean_gain = weighted_mean(
        [row.d0_clean_loss - row.d1_clean_loss for row in outcomes],
        cluster_balanced_weights([row.cluster_id for row in outcomes]),
    )
    if clean_gain <= minimum_clean_gain:
        raise UnstableCleanGainError(
            "STOP_UNSTABLE_CLEAN_GAIN: sampled clean gain does not exceed "
            "the frozen practical threshold"
        )
    return clean_gain


def _fixed_threshold_retention(
    outcomes: Sequence[PolicyImageOutcome],
    *,
    threshold_index: int,
    minimum_clean_gain: float,
) -> float:
    _validate_outcomes(outcomes)
    if (
        isinstance(threshold_index, bool)
        or not isinstance(threshold_index, int)
        or not 0 <= threshold_index < len(outcomes[0].routed_clean_losses)
    ):
        raise ValueError("threshold_index lies outside the frozen coverage grid")
    clean_gain = _practical_clean_gain(
        outcomes,
        minimum_clean_gain=minimum_clean_gain,
    )
    return clean_gain_retention(
        [row.d0_clean_loss for row in outcomes],
        [row.d1_clean_loss for row in outcomes],
        [row.routed_clean_losses[threshold_index] for row in outcomes],
        cluster_ids=[row.cluster_id for row in outcomes],
        clean_gain_ci_lower=clean_gain,
    )


def cluster_bootstrap_retention(
    outcomes: Sequence[PolicyImageOutcome],
    *,
    threshold_index: int,
    minimum_clean_gain: float,
    replicates: int = 10_000,
    seed: int = 20260821,
    confidence: float = 0.95,
    maximum_invalid_fraction: float = 0.05,
) -> RetentionBootstrapResult:
    """Estimate retention with one-sided and two-sided cluster intervals."""

    _validate_outcomes(outcomes)
    if not math.isfinite(minimum_clean_gain) or minimum_clean_gain < 0.0:
        raise ValueError("minimum_clean_gain must be finite and nonnegative")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1)")
    if not 0.0 <= maximum_invalid_fraction < 1.0:
        raise ValueError("maximum_invalid_fraction must be in [0, 1)")
    training_seed = _training_seed(outcomes)
    cluster_count = len({row.cluster_id for row in outcomes})
    try:
        estimate = _fixed_threshold_retention(
            outcomes,
            threshold_index=threshold_index,
            minimum_clean_gain=minimum_clean_gain,
        )
    except UnstableCleanGainError:
        return RetentionBootstrapResult(
            status="STOP_UNSTABLE_CLEAN_GAIN",
            estimate=None,
            one_sided_lower=None,
            ci_lower=None,
            ci_upper=None,
            cluster_count=cluster_count,
            replicates=replicates,
            valid_replicates=0,
            invalid_replicates=replicates,
            invalid_fraction=1.0,
            training_seed=training_seed,
        )

    draws = _cluster_bootstrap_draws(
        [row.cluster_id for row in outcomes],
        replicates=replicates,
        seed=seed,
    )
    values: list[float] = []
    for draw in draws:
        sample = _resample_outcomes(outcomes, draw)
        try:
            values.append(
                _fixed_threshold_retention(
                    sample,
                    threshold_index=threshold_index,
                    minimum_clean_gain=minimum_clean_gain,
                )
            )
        except UnstableCleanGainError:
            continue
    valid_replicates = len(values)
    invalid_replicates = replicates - valid_replicates
    invalid_fraction = invalid_replicates / replicates
    common = {
        "estimate": estimate,
        "cluster_count": cluster_count,
        "replicates": replicates,
        "valid_replicates": valid_replicates,
        "invalid_replicates": invalid_replicates,
        "invalid_fraction": invalid_fraction,
        "training_seed": training_seed,
    }
    if invalid_fraction > maximum_invalid_fraction or not values:
        return RetentionBootstrapResult(
            status="STOP_UNSTABLE_CLEAN_GAIN",
            one_sided_lower=None,
            ci_lower=None,
            ci_upper=None,
            **common,
        )
    two_sided_tail = (1.0 - confidence) / 2.0
    return RetentionBootstrapResult(
        status="PASS",
        one_sided_lower=_percentile(values, 1.0 - confidence),
        ci_lower=_percentile(values, two_sided_tail),
        ci_upper=_percentile(values, 1.0 - two_sided_tail),
        **common,
    )


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
    training_seed = _training_seed(left)
    if _training_seed(right) != training_seed:
        raise ValueError("paired methods must use the same training seed")
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
            training_seed=training_seed,
        )

    sampled_draws = _cluster_bootstrap_draws(
        [row.cluster_id for row in left],
        replicates=replicates,
        seed=seed,
    )
    cvar_differences: list[float] = []
    worst_differences: list[float] = []
    for draw in sampled_draws:
        left_sample = _resample_outcomes(left, draw)
        right_sample = _resample_outcomes(right, draw)
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
        "training_seed": training_seed,
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
