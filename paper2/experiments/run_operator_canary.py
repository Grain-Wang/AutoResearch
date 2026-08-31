"""Cross-check the BlockStamp recurrence against an exact dense rational oracle."""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import time
from fractions import Fraction
from pathlib import Path

from experiments.blockstamp_operator import (
    OperatorStatus,
    assemble_dense_matrix,
    dense_verified_apply,
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
_DEFAULT_OUTPUT = _PAPER_ROOT / "results/blockstamp/operator_canary.json"
_IMPLEMENTATION_FILES = (
    Path(__file__).resolve(),
    _PAPER_ROOT / "experiments/blockstamp_operator.py",
    _PAPER_ROOT / "experiments/rigorous_backend.py",
    _PAPER_ROOT / "experiments/provenance.py",
)


def _fraction_solve(
    matrix: tuple[tuple[float, ...], ...], right_hand_side: tuple[float, ...]
) -> tuple[Fraction, ...]:
    """Solve the materialized dense equation exactly over dyadic rationals."""

    coefficients = [[Fraction.from_float(value) for value in row] for row in matrix]
    values = [Fraction.from_float(value) for value in right_hand_side]
    dimension = len(coefficients)
    for column in range(dimension):
        candidates = [
            row for row in range(column, dimension) if coefficients[row][column] != 0
        ]
        if not candidates:
            raise ArithmeticError("exact dense matrix is singular")
        pivot_row = max(candidates, key=lambda row: abs(coefficients[row][column]))
        if pivot_row != column:
            coefficients[column], coefficients[pivot_row] = (
                coefficients[pivot_row],
                coefficients[column],
            )
            values[column], values[pivot_row] = values[pivot_row], values[column]
        pivot = coefficients[column][column]
        for row in range(column + 1, dimension):
            if coefficients[row][column] == 0:
                continue
            factor = coefficients[row][column] / pivot
            for target in range(column + 1, dimension):
                if coefficients[column][target] != 0:
                    coefficients[row][target] -= factor * coefficients[column][target]
            values[row] -= factor * values[column]
            coefficients[row][column] = Fraction(0)
    solution = [Fraction(0) for _ in range(dimension)]
    for row in range(dimension - 1, -1, -1):
        residual = values[row] - sum(
            coefficients[row][column] * solution[column]
            for column in range(row + 1, dimension)
            if coefficients[row][column] != 0
        )
        solution[row] = residual / coefficients[row][row]
    return tuple(solution)


def _fraction_box_solve(
    matrix: tuple[tuple[float, ...], ...],
    right_hand_side: tuple[Interval, ...],
) -> tuple[tuple[Fraction, Fraction], ...]:
    """Return the exact coordinate hull of a dense dyadic linear box action."""

    dimension = len(matrix)
    inverse_columns = [
        _fraction_solve(
            matrix,
            tuple(1.0 if row == column else 0.0 for row in range(dimension)),
        )
        for column in range(dimension)
    ]
    bounds: list[tuple[Fraction, Fraction]] = []
    for output_index in range(dimension):
        lower = Fraction(0)
        upper = Fraction(0)
        for input_index, interval in enumerate(right_hand_side):
            coefficient = inverse_columns[input_index][output_index]
            interval_lower = Fraction.from_float(interval.lower)
            interval_upper = Fraction.from_float(interval.upper)
            if coefficient >= 0:
                lower += coefficient * interval_lower
                upper += coefficient * interval_upper
            else:
                lower += coefficient * interval_upper
                upper += coefficient * interval_lower
        bounds.append((lower, upper))
    return tuple(bounds)


def _generate_case(
    seed: int,
    block_dimension: int,
    slab_length: int,
    *,
    interval_remainder: bool,
) -> tuple:
    generator = random.Random(seed)
    diagonal_blocks = []
    subdiagonal_blocks = []
    remainder_blocks = []
    for block_index in range(slab_length):
        rows = []
        for row in range(block_dimension):
            values = [generator.randint(-2, 2) / 4 for _ in range(block_dimension)]
            values[row] = sum(abs(value) for value in values) + 1.0
            rows.append(tuple(values))
        diagonal_blocks.append(tuple(rows))
        remainder_values = []
        for _ in range(block_dimension):
            center = generator.randint(-16, 16) / 8
            if interval_remainder:
                radius = generator.randint(1, 4) / 64
                remainder_values.append(Interval(center - radius, center + radius))
            else:
                remainder_values.append(Interval.point(center))
        remainder_blocks.append(tuple(remainder_values))
        if block_index > 0:
            subdiagonal_blocks.append(
                tuple(
                    tuple(generator.randint(-2, 2) / 8 for _ in range(block_dimension))
                    for _ in range(block_dimension)
                )
            )
    return (
        tuple(diagonal_blocks),
        tuple(subdiagonal_blocks),
        tuple(remainder_blocks),
    )


def _contains_exact_box(interval: Interval, exact: tuple[Fraction, Fraction]) -> bool:
    lower = Fraction.from_float(interval.lower)
    upper = Fraction.from_float(interval.upper)
    return lower <= exact[0] and exact[1] <= upper


def _grid_audit(
    block_dimension: int,
    slab_length: int,
    cases: int,
    base_seed: int,
    dense_canary_cases: int,
) -> dict[str, object]:
    violations = 0
    dense_violations = 0
    unsupported = 0
    failure_seeds: list[int] = []
    max_width = 0.0
    max_width_ulps = 0.0
    widths: list[float] = []
    inflations: list[float] = []
    width_ulps: list[float] = []
    verified_pivots = 0
    recursive_seconds = 0.0
    oracle_seconds = 0.0
    dense_seconds = 0.0
    for case_index in range(cases):
        seed = (
            base_seed + 1_000_000 * block_dimension + 10_000 * slab_length + case_index
        )
        interval_remainder = case_index < dense_canary_cases
        diagonal, subdiagonal, remainder = _generate_case(
            seed,
            block_dimension,
            slab_length,
            interval_remainder=interval_remainder,
        )
        dense_matrix = assemble_dense_matrix(diagonal, subdiagonal)
        flat_remainder = tuple(value for block in remainder for value in block)
        started = time.perf_counter()
        if interval_remainder:
            exact = _fraction_box_solve(dense_matrix, flat_remainder)
        else:
            exact_point = _fraction_solve(
                dense_matrix, tuple(value.lower for value in flat_remainder)
            )
            exact = tuple((value, value) for value in exact_point)
        oracle_seconds += time.perf_counter() - started
        started = time.perf_counter()
        recursive = recursive_verified_apply(diagonal, subdiagonal, remainder)
        recursive_seconds += time.perf_counter() - started
        flattened = recursive.flattened()
        if recursive.status is not OperatorStatus.OK or flattened is None:
            unsupported += 1
            failure_seeds.append(seed)
            continue
        verified_pivots += recursive.verified_pivots
        case_failed = False
        for enclosure, exact_bounds in zip(flattened, exact, strict=True):
            if not _contains_exact_box(enclosure, exact_bounds):
                violations += 1
                case_failed = True
            width = enclosure.upper - enclosure.lower
            widths.append(width)
            max_width = max(max_width, width)
            exact_width = exact_bounds[1] - exact_bounds[0]
            enclosure_width = Fraction.from_float(
                enclosure.upper
            ) - Fraction.from_float(enclosure.lower)
            inflations.append(max(0.0, float(enclosure_width - exact_width)))
            oracle_float = float((exact_bounds[0] + exact_bounds[1]) / 2)
            if oracle_float != 0.0:
                ulp_width = width / math.ulp(oracle_float)
                width_ulps.append(ulp_width)
                max_width_ulps = max(max_width_ulps, ulp_width)
        if case_failed:
            failure_seeds.append(seed)

        if case_index < dense_canary_cases:
            started = time.perf_counter()
            dense = dense_verified_apply(diagonal, subdiagonal, remainder)
            dense_seconds += time.perf_counter() - started
            if dense.status is not OperatorStatus.OK or dense.enclosure is None:
                dense_violations += 1
                failure_seeds.append(seed)
            elif any(
                not _contains_exact_box(enclosure, exact_bounds)
                for enclosure, exact_bounds in zip(dense.enclosure, exact, strict=True)
            ):
                dense_violations += 1
                failure_seeds.append(seed)
    return {
        "block_dimension": block_dimension,
        "slab_length": slab_length,
        "cases": cases,
        "attempted_cases": cases,
        "supported_cases": cases - unsupported,
        "dense_canary_cases": min(cases, dense_canary_cases),
        "interval_rhs_cases": min(cases, dense_canary_cases),
        "recursive_containment_violations": violations,
        "dense_containment_violations": dense_violations,
        "containment_violations": violations + dense_violations,
        "unsupported_cases": unsupported,
        "verified_pivots": verified_pivots,
        "enclosure_inflation_definition": (
            "binary64 enclosure width minus exact Fraction coordinate-hull width, "
            "clipped at zero; ULP width excludes an exact zero midpoint"
        ),
        "max_enclosure_width": max_width,
        "median_enclosure_width": statistics.median(widths) if widths else None,
        "max_enclosure_inflation": max(inflations) if inflations else None,
        "median_enclosure_inflation": (
            statistics.median(inflations) if inflations else None
        ),
        "max_enclosure_width_ulps": max_width_ulps,
        "median_enclosure_width_ulps": (
            statistics.median(width_ulps) if width_ulps else None
        ),
        "recursive_seconds": recursive_seconds,
        "exact_dense_oracle_seconds": oracle_seconds,
        "dense_verified_canary_seconds": dense_seconds,
        "failure_seeds": sorted(set(failure_seeds)),
        "failure_case_ids": [
            f"d{block_dimension}-s{slab_length}-seed{failure_seed}"
            for failure_seed in sorted(set(failure_seeds))
        ],
    }


def run_canary(
    cases_per_grid: int, seed: int, dense_canary_cases: int
) -> dict[str, object]:
    """Run the frozen dimension/slab grid and return a JSON-ready result."""

    info = backend_info()
    if info is None:
        raise RuntimeError("MPFR backend is unavailable")
    grids = [
        _grid_audit(dimension, slab, cases_per_grid, seed, dense_canary_cases)
        for dimension in (1, 2, 4, 8)
        for slab in (2, 4, 8)
    ]
    violations = sum(
        int(grid["recursive_containment_violations"])
        + int(grid["dense_containment_violations"])
        for grid in grids
    )
    unsupported = sum(int(grid["unsupported_cases"]) for grid in grids)
    singular_result = recursive_verified_apply(
        (((0.0,),),), (), ((Interval.point(1.0),),)
    )
    singular_false_supported = int(singular_result.status is OperatorStatus.OK)
    violations += singular_false_supported
    source_hashes = source_file_hashes(_PAPER_ROOT, _IMPLEMENTATION_FILES)
    configuration = {
        "block_dimensions": [1, 2, 4, 8],
        "slab_lengths": [2, 4, 8],
        "cases_per_grid": cases_per_grid,
        "dense_canary_cases": dense_canary_cases,
        "seed": seed,
        "generator_version": 1,
        "recurrence_version": 1,
    }
    total_cases = sum(int(grid["cases"]) for grid in grids)
    first_failure_seed = next(
        (int(grid["failure_seeds"][0]) for grid in grids if grid["failure_seeds"]),
        None,
    )
    return {
        "schema_version": 1,
        "status": "PASS" if violations == 0 and unsupported == 0 else "STOP",
        "claim_scope": (
            "exact-real point/interval operator containment canary; "
            "efficiency and novelty unverified"
        ),
        **git_state(_PAPER_ROOT.parent, "paper2"),
        **runtime_provenance(),
        "command": (
            "python3 -m experiments.run_operator_canary "
            f"--cases-per-grid {cases_per_grid} "
            f"--dense-canary-cases {dense_canary_cases} --seed {seed}"
        ),
        "config_sha256": canonical_sha256(configuration),
        "input_sha256": canonical_sha256({"seed": seed, "generator_version": 1}),
        "source_files_sha256": source_hashes,
        "implementation_sha256": canonical_sha256(source_hashes),
        "attempted_cases": total_cases + 1,
        "supported_cases": total_cases - unsupported,
        "unsupported_cases": unsupported + 1,
        "failure_codes": [] if violations == 0 else ["CONTAINMENT_FAILURE"],
        "first_failure": (
            None
            if first_failure_seed is None and singular_false_supported == 0
            else {
                "seed": first_failure_seed,
                "singular_false_supported": singular_false_supported,
            }
        ),
        "recurrence_version": 1,
        "generator_version": 1,
        "generator_seed": seed,
        "backend_sha256": source_hashes["experiments/rigorous_backend.py"],
        "backend": {
            "name": info.name,
            "version": info.version,
            "precision_bits": info.precision_bits,
            "library": info.library,
        },
        "dense_oracle": (
            "exact Fraction coordinate hull of the materialized dense "
            "dyadic-rational linear box action"
        ),
        "random_seeds": {"base": seed},
        "cases_per_grid": cases_per_grid,
        "total_cases": total_cases,
        "total_recursive_containment_violations": violations,
        "total_unsupported_cases": unsupported,
        "singular_cases": {
            "attempted_cases": 1,
            "verdict": singular_result.status.value,
            "verdict_distribution": {singular_result.status.value: 1},
            "false_supported": singular_false_supported,
            "false_supported_count": singular_false_supported,
        },
        "grids": grids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-per-grid", type=int, default=200)
    parser.add_argument("--dense-canary-cases", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20_260_831)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    if arguments.cases_per_grid <= 0:
        parser.error("--cases-per-grid must be positive")
    if arguments.dense_canary_cases < 0:
        parser.error("--dense-canary-cases must be nonnegative")
    result = run_canary(
        arguments.cases_per_grid, arguments.seed, arguments.dense_canary_cases
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
