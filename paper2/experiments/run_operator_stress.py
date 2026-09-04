"""Stress the verified BlockStamp operator on difficult interval right-hand sides.

The original operator canary intentionally uses easy diagonally dominant blocks and
only a small interval-RHS subset.  This runner exercises every registered
dimension/slab cell with nonzero-width boxes.  Its generated point matrix is an
exactly representable, scaled bidiagonal chain, materialized in BlockStamp blocks:

``M = scale * (I - coupling * S)``

where ``S`` is the nilpotent lower shift.  This family is non-normal, admits exact
condition and coordinate-hull calculations over :class:`fractions.Fraction`, and
can independently stress temporal amplification, strong subdiagonal coupling, and
near-singular scales without using the verified operator as its oracle.

An ``OK`` operator result is checked coordinate-by-coordinate against the exact
dense-chain hull.  A mathematically nonsingular case for which interval elimination
is inconclusive is reported as ``UNKNOWN`` rather than as a successful check.
Singular and deliberately inconclusive edge cases are required to fail closed.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from fractions import Fraction
from functools import cache
from pathlib import Path

from experiments.blockstamp_operator import (
    OperatorStatus,
    PointMatrix,
    assemble_dense_matrix,
    recursive_verified_apply,
)
from experiments.interval_backend import Interval
from experiments.provenance import (
    canonical_sha256,
    git_state,
    runtime_provenance,
    source_file_hashes,
)
from experiments.rigorous_backend import backend_info

_PAPER_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_OUTPUT = _PAPER_ROOT / "results/blockstamp/operator_stress.json"
_DIMENSIONS = (1, 2, 4, 8)
_SLAB_LENGTHS = (2, 4, 8, 16)
_COUPLING_DENOMINATOR = 1 << 20
_GENERATOR_VERSION = 1
_ORACLE_VERSION = 1
_RECURRENCE_VERSION = 1
_IMPLEMENTATION_FILES = (
    Path(__file__).resolve(),
    _PAPER_ROOT / "experiments/blockstamp_operator.py",
    _PAPER_ROOT / "experiments/rigorous_backend.py",
    _PAPER_ROOT / "experiments/provenance.py",
)

type ExactBounds = tuple[Fraction, Fraction]


@dataclass(frozen=True, slots=True)
class ConditionBucket:
    """One frozen exact infinity-condition bucket."""

    label: str
    lower: int
    upper: int
    target: int


CONDITION_BUCKETS = (
    ConditionBucket("1e0-1e2", 1, 100, 10),
    ConditionBucket("1e2-1e4", 100, 10_000, 1_000),
    ConditionBucket("1e4-1e6", 10_000, 1_000_000, 100_000),
    ConditionBucket("1e6-1e8", 1_000_000, 100_000_000, 10_000_000),
)


@dataclass(frozen=True, slots=True)
class StressCase:
    """A generated nonsingular stress input plus exact diagnostics."""

    case_id: str
    seed: int
    block_dimension: int
    slab_length: int
    bucket: ConditionBucket
    bucket_index: int
    coupling: Fraction
    scale: Fraction
    scenario: str
    diagonal_blocks: tuple[PointMatrix, ...]
    subdiagonal_blocks: tuple[PointMatrix, ...]
    remainder_blocks: tuple[tuple[Interval, ...], ...]
    exact_condition_inf: Fraction
    exact_block_pivot_growth: Fraction


@dataclass(frozen=True, slots=True)
class UnsupportedCase:
    """An edge case that must not receive an ``OK`` operator status."""

    case_id: str
    category: str
    exact_matrix_nonsingular: bool
    diagonal_blocks: tuple[PointMatrix, ...]
    subdiagonal_blocks: tuple[PointMatrix, ...]
    remainder_blocks: tuple[tuple[Interval, ...], ...]


@dataclass(frozen=True, slots=True)
class _CaseAudit:
    supported: bool
    unknown_reason: str | None
    violation_coordinates: int
    max_absolute_inflation: float | None
    max_relative_inflation: float | None
    elapsed_seconds: float


@dataclass(slots=True)
class _Accumulator:
    attempted_cases: int = 0
    supported_cases: int = 0
    unknown_cases: int = 0
    violation_cases: int = 0
    violation_coordinates: int = 0
    interval_rhs_cases: int = 0
    interval_rhs_coordinates: int = 0
    strong_subdiagonal_cases: int = 0
    nonnormal_global_matrix_cases: int = 0
    nonnormal_block_cases: int = 0
    near_singular_cases: int = 0
    near_singular_supported_cases: int = 0
    operator_seconds: float = 0.0
    exact_conditions: list[float] = field(default_factory=list)
    pivot_growths: list[float] = field(default_factory=list)
    absolute_inflations: list[float] = field(default_factory=list)
    relative_inflations: list[float] = field(default_factory=list)
    failure_case_ids: list[str] = field(default_factory=list)
    unknown_reasons: Counter[str] = field(default_factory=Counter)

    def add(self, case: StressCase, audit: _CaseAudit) -> None:
        """Accumulate one stress-case result."""

        self.attempted_cases += 1
        self.interval_rhs_cases += 1
        self.interval_rhs_coordinates += case.block_dimension * case.slab_length
        self.strong_subdiagonal_cases += int(case.coupling >= 1)
        self.nonnormal_global_matrix_cases += 1
        self.nonnormal_block_cases += int(case.block_dimension > 1)
        near_singular = case.scenario == "near_singular_supported_probe"
        self.near_singular_cases += int(near_singular)
        self.operator_seconds += audit.elapsed_seconds
        self.exact_conditions.append(float(case.exact_condition_inf))
        self.pivot_growths.append(float(case.exact_block_pivot_growth))
        if audit.supported:
            self.supported_cases += 1
            self.near_singular_supported_cases += int(near_singular)
            if audit.max_absolute_inflation is not None:
                self.absolute_inflations.append(audit.max_absolute_inflation)
            if audit.max_relative_inflation is not None:
                self.relative_inflations.append(audit.max_relative_inflation)
        else:
            self.unknown_cases += 1
            self.unknown_reasons[audit.unknown_reason or "unspecified"] += 1
        if audit.violation_coordinates:
            self.violation_cases += 1
            self.violation_coordinates += audit.violation_coordinates
            self.failure_case_ids.append(case.case_id)

    def to_dict(self) -> dict[str, object]:
        """Return a stable JSON-ready aggregate."""

        return {
            "attempted_cases": self.attempted_cases,
            "supported_cases": self.supported_cases,
            "violations": self.violation_cases,
            "containment_violation_coordinates": self.violation_coordinates,
            "UNKNOWN": self.unknown_cases,
            "verdict_distribution": {
                "OK": self.supported_cases,
                "UNKNOWN": self.unknown_cases,
            },
            "interval_rhs_cases": self.interval_rhs_cases,
            "nonzero_width_interval_rhs_coordinates": self.interval_rhs_coordinates,
            "strong_subdiagonal_cases": self.strong_subdiagonal_cases,
            "nonnormal_global_matrix_cases": self.nonnormal_global_matrix_cases,
            "nonnormal_block_cases": self.nonnormal_block_cases,
            "near_singular_cases": self.near_singular_cases,
            "near_singular_supported_cases": self.near_singular_supported_cases,
            "condition_inf": _range_summary(self.exact_conditions),
            "partial_pivot_growth": _range_summary(self.pivot_growths),
            "inflation": {
                "definition": (
                    "per supported case, maximum over coordinates of binary64 "
                    "enclosure width minus exact Fraction dense-chain hull width; "
                    "relative inflation divides by the nonzero exact hull width"
                ),
                "samples": len(self.absolute_inflations),
                "max_absolute": _maximum(self.absolute_inflations),
                "median_absolute": _median(self.absolute_inflations),
                "max_relative": _maximum(self.relative_inflations),
                "median_relative": _median(self.relative_inflations),
            },
            "operator_seconds": self.operator_seconds,
            "unknown_reasons": dict(sorted(self.unknown_reasons.items())),
            "failure_case_ids": sorted(self.failure_case_ids),
        }


def _maximum(values: list[float]) -> float | None:
    return max(values) if values else None


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _range_summary(values: list[float]) -> dict[str, float | None]:
    return {
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
        "median": statistics.median(values) if values else None,
    }


def _chain_condition(size: int, coupling: Fraction) -> Fraction:
    inverse_norm = sum((coupling**power for power in range(size)), Fraction(0))
    return (1 + coupling) * inverse_norm


@cache
def _coupling_for_target(size: int, target: int) -> Fraction:
    lower = 0
    upper = _COUPLING_DENOMINATOR
    target_fraction = Fraction(target)
    while _chain_condition(size, Fraction(upper, _COUPLING_DENOMINATOR)) < target:
        upper *= 2
    while lower + 1 < upper:
        middle = (lower + upper) // 2
        candidate = Fraction(middle, _COUPLING_DENOMINATOR)
        if _chain_condition(size, candidate) < target_fraction:
            lower = middle
        else:
            upper = middle
    return Fraction(upper, _COUPLING_DENOMINATOR)


def _build_chain_blocks(
    block_dimension: int,
    slab_length: int,
    coupling: Fraction,
    scale: Fraction,
) -> tuple[tuple[PointMatrix, ...], tuple[PointMatrix, ...]]:
    diagonal_blocks: list[PointMatrix] = []
    subdiagonal_blocks: list[PointMatrix] = []
    diagonal_value = float(scale)
    predecessor_value = float(-scale * coupling)
    for block_index in range(slab_length):
        rows: list[tuple[float, ...]] = []
        for row_index in range(block_dimension):
            row = [0.0] * block_dimension
            row[row_index] = diagonal_value
            if row_index > 0:
                row[row_index - 1] = predecessor_value
            rows.append(tuple(row))
        diagonal_blocks.append(tuple(rows))
        if block_index > 0:
            coupling_rows = [
                [0.0 for _ in range(block_dimension)] for _ in range(block_dimension)
            ]
            coupling_rows[0][-1] = predecessor_value
            subdiagonal_blocks.append(tuple(tuple(row) for row in coupling_rows))
    return tuple(diagonal_blocks), tuple(subdiagonal_blocks)


def _generate_remainder(
    generator: random.Random,
    block_dimension: int,
    slab_length: int,
    scale: Fraction,
) -> tuple[tuple[Interval, ...], ...]:
    blocks: list[tuple[Interval, ...]] = []
    for _ in range(slab_length):
        values: list[Interval] = []
        for _ in range(block_dimension):
            center = Fraction(generator.randint(-128, 128), 64)
            radius = Fraction(generator.randint(1, 32), 1_024)
            lower = float(scale * (center - radius))
            upper = float(scale * (center + radius))
            values.append(Interval(lower, upper))
        blocks.append(tuple(values))
    return tuple(blocks)


def _exact_partial_pivot_growth(matrix: PointMatrix) -> Fraction:
    coefficients = [[Fraction.from_float(value) for value in row] for row in matrix]
    largest_original = max(abs(value) for row in coefficients for value in row)
    largest_seen = largest_original
    dimension = len(coefficients)
    for column in range(dimension):
        pivot_row = max(
            range(column, dimension),
            key=lambda row: abs(coefficients[row][column]),
        )
        if coefficients[pivot_row][column] == 0:
            raise ArithmeticError("pivot-growth diagnostic received a singular block")
        if pivot_row != column:
            coefficients[column], coefficients[pivot_row] = (
                coefficients[pivot_row],
                coefficients[column],
            )
        pivot = coefficients[column][column]
        for row in range(column + 1, dimension):
            factor = coefficients[row][column] / pivot
            for target_column in range(column + 1, dimension):
                coefficients[row][target_column] -= (
                    factor * coefficients[column][target_column]
                )
                largest_seen = max(largest_seen, abs(coefficients[row][target_column]))
            coefficients[row][column] = Fraction(0)
    return largest_seen / largest_original


def generate_stress_case(
    block_dimension: int,
    slab_length: int,
    bucket_index: int,
    case_ordinal: int,
    base_seed: int,
) -> StressCase:
    """Generate one deterministic, exactly auditable interval-RHS stress case."""

    if block_dimension not in _DIMENSIONS:
        raise ValueError(f"unsupported block dimension: {block_dimension}")
    if slab_length not in _SLAB_LENGTHS:
        raise ValueError(f"unsupported slab length: {slab_length}")
    try:
        bucket = CONDITION_BUCKETS[bucket_index]
    except IndexError as error:
        raise ValueError(f"unsupported bucket index: {bucket_index}") from error
    if case_ordinal < 0:
        raise ValueError("case ordinal must be nonnegative")

    size = block_dimension * slab_length
    coupling = _coupling_for_target(size, bucket.target)
    exact_condition = _chain_condition(size, coupling)
    if not Fraction(bucket.lower) <= exact_condition < Fraction(bucket.upper):
        raise AssertionError("quantized coupling escaped its condition bucket")

    near_singular = bucket_index == len(CONDITION_BUCKETS) - 1 and not (
        case_ordinal % 5
    )
    scale = Fraction(1, 1 << 80) if near_singular else Fraction(1)
    scenario = (
        "near_singular_supported_probe" if near_singular else "conditioned_nonnormal"
    )
    diagonal_blocks, subdiagonal_blocks = _build_chain_blocks(
        block_dimension, slab_length, coupling, scale
    )
    case_seed = (
        base_seed
        + 1_000_000_000 * block_dimension
        + 1_000_000 * slab_length
        + 10_000 * bucket_index
        + case_ordinal
    )
    remainder_blocks = _generate_remainder(
        random.Random(case_seed), block_dimension, slab_length, scale
    )
    pivot_growth = _exact_partial_pivot_growth(diagonal_blocks[0])
    return StressCase(
        case_id=(
            f"d{block_dimension}-s{slab_length}-{bucket.label}-"
            f"n{case_ordinal}-seed{case_seed}"
        ),
        seed=case_seed,
        block_dimension=block_dimension,
        slab_length=slab_length,
        bucket=bucket,
        bucket_index=bucket_index,
        coupling=coupling,
        scale=scale,
        scenario=scenario,
        diagonal_blocks=diagonal_blocks,
        subdiagonal_blocks=subdiagonal_blocks,
        remainder_blocks=remainder_blocks,
        exact_condition_inf=exact_condition,
        exact_block_pivot_growth=pivot_growth,
    )


def _scale_bounds(bounds: ExactBounds, coefficient: Fraction) -> ExactBounds:
    products = (coefficient * bounds[0], coefficient * bounds[1])
    return min(products), max(products)


def exact_fraction_dense_hull(
    matrix: PointMatrix, right_hand_side: tuple[Interval, ...]
) -> tuple[ExactBounds, ...]:
    """Return the exact coordinate hull of a materialized bidiagonal chain.

    The function consumes the global dense matrix, verifies its sparsity pattern,
    and solves over exact dyadic rationals.  It does not call either BlockStamp's
    verified block recurrence or its interval Gaussian elimination.
    """

    dimension = len(matrix)
    if dimension == 0 or any(len(row) != dimension for row in matrix):
        raise ValueError("oracle matrix must be nonempty and square")
    if len(right_hand_side) != dimension:
        raise ValueError("oracle right-hand side dimension mismatch")

    output: list[ExactBounds] = []
    for row_index, row in enumerate(matrix):
        exact_row = tuple(Fraction.from_float(value) for value in row)
        allowed_columns = {row_index}
        if row_index > 0:
            allowed_columns.add(row_index - 1)
        if any(
            value != 0 and column_index not in allowed_columns
            for column_index, value in enumerate(exact_row)
        ):
            raise ValueError("oracle supports only a global lower-bidiagonal chain")
        diagonal = exact_row[row_index]
        if diagonal == 0:
            raise ArithmeticError("oracle matrix is singular")
        rhs_bounds = (
            Fraction.from_float(right_hand_side[row_index].lower),
            Fraction.from_float(right_hand_side[row_index].upper),
        )
        current = _scale_bounds(rhs_bounds, 1 / diagonal)
        if row_index > 0:
            predecessor_coefficient = -exact_row[row_index - 1] / diagonal
            predecessor = _scale_bounds(output[-1], predecessor_coefficient)
            current = (
                current[0] + predecessor[0],
                current[1] + predecessor[1],
            )
        output.append(current)
    return tuple(output)


def _contains_exact_bounds(enclosure: Interval, exact: ExactBounds) -> bool:
    return Fraction.from_float(enclosure.lower) <= exact[0] and exact[
        1
    ] <= Fraction.from_float(enclosure.upper)


def _audit_case(case: StressCase) -> _CaseAudit:
    dense = assemble_dense_matrix(case.diagonal_blocks, case.subdiagonal_blocks)
    flattened_rhs = tuple(value for block in case.remainder_blocks for value in block)
    exact = exact_fraction_dense_hull(dense, flattened_rhs)
    started = time.perf_counter()
    result = recursive_verified_apply(
        case.diagonal_blocks, case.subdiagonal_blocks, case.remainder_blocks
    )
    elapsed_seconds = time.perf_counter() - started
    enclosure = result.flattened()
    if result.status is not OperatorStatus.OK or enclosure is None:
        return _CaseAudit(
            supported=False,
            unknown_reason=result.reason or result.status.value,
            violation_coordinates=0,
            max_absolute_inflation=None,
            max_relative_inflation=None,
            elapsed_seconds=elapsed_seconds,
        )

    violation_coordinates = 0
    absolute_inflations: list[Fraction] = []
    relative_inflations: list[Fraction] = []
    for interval, exact_bounds in zip(enclosure, exact, strict=True):
        violation_coordinates += int(not _contains_exact_bounds(interval, exact_bounds))
        enclosure_width = Fraction.from_float(interval.upper) - Fraction.from_float(
            interval.lower
        )
        exact_width = exact_bounds[1] - exact_bounds[0]
        inflation = max(Fraction(0), enclosure_width - exact_width)
        absolute_inflations.append(inflation)
        if exact_width <= 0:
            raise AssertionError("stress generator produced a zero-width exact hull")
        relative_inflations.append(inflation / exact_width)
    return _CaseAudit(
        supported=True,
        unknown_reason=None,
        violation_coordinates=violation_coordinates,
        max_absolute_inflation=float(max(absolute_inflations)),
        max_relative_inflation=float(max(relative_inflations)),
        elapsed_seconds=elapsed_seconds,
    )


def expected_unsupported_cases(
    block_dimension: int, slab_length: int
) -> tuple[UnsupportedCase, ...]:
    """Return singular and inconclusive edge cases for one grid cell."""

    if block_dimension not in _DIMENSIONS or slab_length not in _SLAB_LENGTHS:
        raise ValueError("unsupported dimension/slab cell")

    identity_blocks, zero_couplings = _build_chain_blocks(
        block_dimension, slab_length, Fraction(0), Fraction(1)
    )
    singular_first = tuple(
        tuple(0.0 for _ in range(block_dimension)) for _ in range(block_dimension)
    )
    singular_blocks = (singular_first, *identity_blocks[1:])
    ordinary_rhs = tuple(
        tuple(Interval(-1.0, 1.0) for _ in range(block_dimension))
        for _ in range(slab_length)
    )
    singular = UnsupportedCase(
        case_id=f"d{block_dimension}-s{slab_length}-singular",
        category="exact_singular",
        exact_matrix_nonsingular=False,
        diagonal_blocks=singular_blocks,
        subdiagonal_blocks=zero_couplings,
        remainder_blocks=ordinary_rhs,
    )

    if block_dimension == 1:
        tiny = float.fromhex("0x0.0000000000001p-1022")
        first = ((tiny,),)
        inconclusive_blocks = (first, *identity_blocks[1:])
        first_rhs = (Interval(1.0, math.nextafter(1.0, math.inf)),)
        inconclusive_rhs = (first_rhs, *ordinary_rhs[1:])
        category = "nonsingular_output_overflow_inconclusive"
    else:
        rows = [list(row) for row in identity_blocks[0]]
        rows[0][0] = 3.0
        rows[0][1] = 1.0
        rows[1][0] = 1.0
        rows[1][1] = 1.0 / 3.0
        inconclusive_blocks = (tuple(tuple(row) for row in rows), *identity_blocks[1:])
        inconclusive_rhs = ordinary_rhs
        category = "nonsingular_pivot_interval_inconclusive"
    inconclusive = UnsupportedCase(
        case_id=f"d{block_dimension}-s{slab_length}-inconclusive",
        category=category,
        exact_matrix_nonsingular=True,
        diagonal_blocks=inconclusive_blocks,
        subdiagonal_blocks=zero_couplings,
        remainder_blocks=inconclusive_rhs,
    )
    return singular, inconclusive


def _unsupported_audit(block_dimension: int, slab_length: int) -> dict[str, object]:
    records: list[dict[str, object]] = []
    false_ok_cases = 0
    for case in expected_unsupported_cases(block_dimension, slab_length):
        result = recursive_verified_apply(
            case.diagonal_blocks, case.subdiagonal_blocks, case.remainder_blocks
        )
        false_ok = result.status is OperatorStatus.OK
        false_ok_cases += int(false_ok)
        records.append(
            {
                "case_id": case.case_id,
                "category": case.category,
                "exact_matrix_nonsingular": case.exact_matrix_nonsingular,
                "operator_status": result.status.value,
                "stress_verdict": "FALSE_OK" if false_ok else "UNKNOWN",
                "reason": result.reason,
            }
        )
    return {
        "attempted_cases": len(records),
        "UNKNOWN": len(records) - false_ok_cases,
        "false_OK": false_ok_cases,
        "records": records,
    }


def _bucket_payload(
    bucket: ConditionBucket, accumulator: _Accumulator
) -> dict[str, object]:
    return {
        "bucket": bucket.label,
        "lower_inclusive": bucket.lower,
        "upper_exclusive": bucket.upper,
        "target": bucket.target,
        **accumulator.to_dict(),
    }


def run_stress(cases_per_cell: int, seed: int) -> dict[str, object]:
    """Run the complete operator stress grid and return a JSON-ready artifact."""

    if cases_per_cell <= 0:
        raise ValueError("cases per cell must be positive")
    info = backend_info()
    if info is None:
        raise RuntimeError("MPFR backend is unavailable")

    overall = _Accumulator()
    overall_buckets = [_Accumulator() for _ in CONDITION_BUCKETS]
    grids: list[dict[str, object]] = []
    expected_records: list[dict[str, object]] = []
    expected_false_ok = 0
    for block_dimension in _DIMENSIONS:
        for slab_length in _SLAB_LENGTHS:
            grid = _Accumulator()
            grid_buckets = [_Accumulator() for _ in CONDITION_BUCKETS]
            bucket_ordinals = [0 for _ in CONDITION_BUCKETS]
            for case_index in range(cases_per_cell):
                bucket_index = case_index % len(CONDITION_BUCKETS)
                case_ordinal = bucket_ordinals[bucket_index]
                bucket_ordinals[bucket_index] += 1
                case = generate_stress_case(
                    block_dimension,
                    slab_length,
                    bucket_index,
                    case_ordinal,
                    seed,
                )
                if any(
                    interval.lower == interval.upper
                    for block in case.remainder_blocks
                    for interval in block
                ):
                    raise AssertionError(
                        "stress interval RHS contains a point interval"
                    )
                audit = _audit_case(case)
                grid.add(case, audit)
                grid_buckets[bucket_index].add(case, audit)
                overall.add(case, audit)
                overall_buckets[bucket_index].add(case, audit)

            unsupported = _unsupported_audit(block_dimension, slab_length)
            expected_records.extend(unsupported["records"])
            expected_false_ok += int(unsupported["false_OK"])
            grids.append(
                {
                    "block_dimension": block_dimension,
                    "slab_length": slab_length,
                    **grid.to_dict(),
                    "conditioning_and_pivot_growth_buckets": [
                        _bucket_payload(bucket, accumulator)
                        for bucket, accumulator in zip(
                            CONDITION_BUCKETS, grid_buckets, strict=True
                        )
                    ],
                    "expected_unsupported": unsupported,
                }
            )

    minimum_cases = min(int(grid["interval_rhs_cases"]) for grid in grids)
    all_buckets_covered = all(
        int(bucket["attempted_cases"]) > 0
        for grid in grids
        for bucket in grid["conditioning_and_pivot_growth_buckets"]
    )
    strong_coupling_covered = all(
        int(grid["strong_subdiagonal_cases"]) > 0 for grid in grids
    )
    near_singular_supported = all(
        int(grid["near_singular_supported_cases"]) > 0 for grid in grids
    )
    coverage = {
        "required_interval_rhs_cases_per_cell": 200,
        "minimum_interval_rhs_cases_per_cell": minimum_cases,
        "all_16_dimension_slab_cells_present": len(grids) == 16,
        "all_four_condition_buckets_present_per_cell": all_buckets_covered,
        "strong_subdiagonal_present_per_cell": strong_coupling_covered,
        "nonnormal_global_matrix_cases": overall.nonnormal_global_matrix_cases,
        "nonnormal_block_cases": overall.nonnormal_block_cases,
        "dimension_one_block_nonnormality": (
            "not applicable to scalar blocks; the assembled temporal matrix is "
            "non-normal"
        ),
        "near_singular_supported_present_per_cell": near_singular_supported,
    }
    coverage_pass = (
        minimum_cases >= 200
        and bool(coverage["all_16_dimension_slab_cells_present"])
        and all_buckets_covered
        and strong_coupling_covered
        and near_singular_supported
    )
    soundness_pass = overall.violation_cases == 0 and expected_false_ok == 0
    failure_codes: list[str] = []
    if overall.violation_cases:
        failure_codes.append("SUPPORTED_CONTAINMENT_VIOLATION")
    if expected_false_ok:
        failure_codes.append("SINGULAR_OR_INCONCLUSIVE_FALSE_OK")
    if not coverage_pass:
        failure_codes.append("STRESS_COVERAGE_INCOMPLETE")

    source_hashes = source_file_hashes(_PAPER_ROOT, _IMPLEMENTATION_FILES)
    generator_contract = {
        "matrix_family": "scale * (I - coupling * nilpotent_lower_shift)",
        "coupling_quantization_denominator": _COUPLING_DENOMINATOR,
        "coupling_selection": (
            "smallest positive quantized coupling whose exact condition_inf "
            "reaches the bucket target"
        ),
        "rhs_centers": "independent signed multiples of 1/64 in [-2, 2]",
        "rhs_radii": "independent positive multiples of 1/1024 in [1/1024, 1/32]",
        "near_singular_rule": (
            "every fifth case in bucket 1e6-1e8 uses matrix and RHS scale 2^-80"
        ),
        "expected_unsupported_per_cell": [
            "one exact-singular block system",
            "one exact-nonsingular but interval-inconclusive system",
        ],
    }
    configuration = {
        "block_dimensions": list(_DIMENSIONS),
        "slab_lengths": list(_SLAB_LENGTHS),
        "cases_per_cell": cases_per_cell,
        "condition_buckets": [
            {
                "label": bucket.label,
                "lower": bucket.lower,
                "upper": bucket.upper,
                "target": bucket.target,
            }
            for bucket in CONDITION_BUCKETS
        ],
        "seed": seed,
        "generator_contract": generator_contract,
        "generator_version": _GENERATOR_VERSION,
        "oracle_version": _ORACLE_VERSION,
        "recurrence_version": _RECURRENCE_VERSION,
    }
    expected_unknown = len(expected_records) - expected_false_ok
    return {
        "schema_version": 1,
        "status": "PASS" if coverage_pass and soundness_pass else "STOP",
        "status_semantics": (
            "PASS means required coverage, zero observed containment violations "
            "among OK cases, and fail-closed expected edges; UNKNOWN is retained "
            "and is never counted as a supported success"
        ),
        "claim_scope": (
            "synthetic exact-dyadic operator stress only; no efficiency, less-"
            "wrapping, novelty, or real-MNA distribution claim"
        ),
        **git_state(_PAPER_ROOT.parent, "paper2"),
        **runtime_provenance(),
        "command": (
            "python3 -m experiments.run_operator_stress "
            f"--cases-per-cell {cases_per_cell} --seed {seed}"
        ),
        "config_sha256": canonical_sha256(configuration),
        "input_sha256": canonical_sha256(
            {
                "seed": seed,
                "generator_version": _GENERATOR_VERSION,
                "condition_targets": [bucket.target for bucket in CONDITION_BUCKETS],
            }
        ),
        "source_files_sha256": source_hashes,
        "implementation_sha256": canonical_sha256(source_hashes),
        "generator_version": _GENERATOR_VERSION,
        "oracle_version": _ORACLE_VERSION,
        "recurrence_version": _RECURRENCE_VERSION,
        "generator_seed": seed,
        "generator_contract": generator_contract,
        "random_seeds": {"base": seed, "case_seed_formula_version": 1},
        "backend": {
            "name": info.name,
            "version": info.version,
            "precision_bits": info.precision_bits,
            "library": info.library,
        },
        "backend_sha256": source_hashes["experiments/rigorous_backend.py"],
        "oracle": {
            "name": "exact_fraction_materialized_dense_chain_coordinate_hull",
            "independent_of_verified_solve": True,
            "arithmetic": "fractions.Fraction over exact binary64 inputs",
            "matrix_contract": (
                "materialized global lower-bidiagonal matrix with independently "
                "checked sparsity and nonzero diagonal"
            ),
        },
        "bucketing_metric": (
            "exact infinity-norm condition number of the materialized scaled "
            "bidiagonal chain; exact partial-pivot growth is also reported"
        ),
        "attempted_cases": overall.attempted_cases + len(expected_records),
        "interval_rhs_attempted_cases": overall.attempted_cases,
        "supported_cases": overall.supported_cases,
        "UNKNOWN": overall.unknown_cases + expected_unknown,
        "main_nonsingular_UNKNOWN": overall.unknown_cases,
        "containment_violations": overall.violation_cases,
        "containment_violation_coordinates": overall.violation_coordinates,
        "failure_codes": failure_codes,
        "coverage": coverage,
        "overall": overall.to_dict(),
        "conditioning_and_pivot_growth_buckets": [
            _bucket_payload(bucket, accumulator)
            for bucket, accumulator in zip(
                CONDITION_BUCKETS, overall_buckets, strict=True
            )
        ],
        "expected_unsupported": {
            "attempted_cases": len(expected_records),
            "UNKNOWN": expected_unknown,
            "false_OK": expected_false_ok,
            "records": expected_records,
        },
        "grids": grids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-per-cell", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20_260_831)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    if arguments.cases_per_cell < 200:
        parser.error("--cases-per-cell must be at least 200 for the frozen stress grid")
    result = run_stress(arguments.cases_per_cell, arguments.seed)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
