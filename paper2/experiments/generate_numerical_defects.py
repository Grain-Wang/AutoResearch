"""Generate a reproducible ill-conditioned passive-MNA defect canary.

The producer is a real residual-stopped diagonal Newton solve. It starts from the
plausible warm state ``(1, 0)`` and performs arithmetic in the declared binary32 or
binary64 precision. A loose residual threshold can therefore terminate before the
Newton correction even though the second voltage has one volt of forward error.

Oracle facts and checker verdicts are deliberately separate: exact rational arithmetic
solves the declared binary system, while the executable pointwise Krawczyk checker is
the only source of ``checker_verdict``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from experiments.checkers.pointwise_krawczyk import (
    CheckerResult,
    CheckerVerdict,
    pointwise_krawczyk,
)
from experiments.interval_backend import Interval, IntervalResult, IntervalStatus
from experiments.producers.precision import BinaryArithmetic, ProducerPrecision
from experiments.provenance import (
    canonical_sha256,
    git_state,
    runtime_provenance,
    sha256_file,
    source_file_hashes,
)
from experiments.rigorous_backend import (
    backend_info,
    multiply,
    subtract,
)

DEFAULT_SEED = 17
DEFAULT_RESIDUAL_THRESHOLD = 1e-5
DEFAULT_TUBE_RADIUS = 1e-3
SCHEMA_VERSION = "2"
_PAPER_ROOT = Path(__file__).resolve().parents[1]
_PROVENANCE_FILES = (
    Path(__file__).resolve(),
    _PAPER_ROOT / "experiments/blockstamp_operator.py",
    _PAPER_ROOT / "experiments/checkers/pointwise_krawczyk.py",
    _PAPER_ROOT / "experiments/interval_backend.py",
    _PAPER_ROOT / "experiments/producers/precision.py",
    _PAPER_ROOT / "experiments/provenance.py",
    _PAPER_ROOT / "experiments/rigorous_backend.py",
)


@dataclass(frozen=True, slots=True)
class ProducerResult:
    """Trace summary from one actual residual-stopped diagonal solve."""

    center: tuple[float, ...]
    residual: tuple[float, ...]
    residual_inf: float
    threshold: float
    iterations: int
    converged: bool


@dataclass(frozen=True, slots=True)
class OracleResult:
    """Exact-rational facts for a declared binary diagonal system and tube."""

    root: tuple[Fraction, ...]
    root_in_tube: bool
    forward_error_inf: Fraction


def _cast(value: float, precision: ProducerPrecision) -> float:
    return BinaryArithmetic(precision).cast(value)


def _producer_add(left: float, right: float, precision: ProducerPrecision) -> float:
    return BinaryArithmetic(precision).add(left, right)


def _producer_subtract(
    left: float, right: float, precision: ProducerPrecision
) -> float:
    return BinaryArithmetic(precision).subtract(left, right)


def _producer_multiply(
    left: float, right: float, precision: ProducerPrecision
) -> float:
    return BinaryArithmetic(precision).multiply(left, right)


def _producer_divide(left: float, right: float, precision: ProducerPrecision) -> float:
    return BinaryArithmetic(precision).divide(left, right)


def _producer_residual(
    diagonal: tuple[float, ...],
    right_hand_side: tuple[float, ...],
    center: tuple[float, ...],
    precision: ProducerPrecision,
) -> tuple[float, ...]:
    return tuple(
        _producer_subtract(
            _producer_multiply(coefficient, value, precision), target, precision
        )
        for coefficient, target, value in zip(
            diagonal, right_hand_side, center, strict=True
        )
    )


def solve_diagonal_system(
    diagonal: tuple[float, ...],
    right_hand_side: tuple[float, ...],
    initial_center: tuple[float, ...],
    precision: ProducerPrecision,
    residual_threshold: float,
    *,
    max_iterations: int = 1,
) -> ProducerResult:
    """Run a residual-stopped diagonal Newton solve in the declared precision."""

    dimension = len(diagonal)
    if dimension == 0 or len(right_hand_side) != dimension:
        raise ValueError("diagonal system dimensions do not match")
    if len(initial_center) != dimension:
        raise ValueError("initial center dimension does not match")
    if max_iterations < 0:
        raise ValueError("max_iterations must be nonnegative")

    coefficients = tuple(_cast(value, precision) for value in diagonal)
    targets = tuple(_cast(value, precision) for value in right_hand_side)
    center = tuple(_cast(value, precision) for value in initial_center)
    threshold = _cast(residual_threshold, precision)
    if threshold < 0.0 or not math.isfinite(threshold):
        raise ValueError("residual threshold must be finite and nonnegative")
    if any(value == 0.0 or not math.isfinite(value) for value in coefficients):
        raise ValueError("diagonal coefficients must be finite and nonzero")

    iterations = 0
    residual = _producer_residual(coefficients, targets, center, precision)
    residual_inf = max(abs(value) for value in residual)
    while residual_inf > threshold and iterations < max_iterations:
        center = tuple(
            _producer_add(
                value,
                _producer_divide(-error, coefficient, precision),
                precision,
            )
            for coefficient, value, error in zip(
                coefficients, center, residual, strict=True
            )
        )
        iterations += 1
        residual = _producer_residual(coefficients, targets, center, precision)
        residual_inf = max(abs(value) for value in residual)

    return ProducerResult(
        center=center,
        residual=residual,
        residual_inf=residual_inf,
        threshold=threshold,
        iterations=iterations,
        converged=residual_inf <= threshold,
    )


def exact_diagonal_oracle(
    diagonal: tuple[float, ...],
    right_hand_side: tuple[float, ...],
    center: tuple[float, ...],
    tube: tuple[Interval, ...],
) -> OracleResult:
    """Solve the declared binary system exactly using rational arithmetic."""

    dimension = len(diagonal)
    if (
        dimension == 0
        or len(right_hand_side) != dimension
        or len(center) != dimension
        or len(tube) != dimension
    ):
        raise ValueError("oracle dimensions do not match")
    if any(value == 0.0 for value in diagonal):
        raise ValueError("oracle system is singular")

    root = tuple(
        Fraction.from_float(target) / Fraction.from_float(coefficient)
        for coefficient, target in zip(diagonal, right_hand_side, strict=True)
    )
    root_in_tube = all(
        Fraction.from_float(interval.lower)
        <= root_value
        <= Fraction.from_float(interval.upper)
        for root_value, interval in zip(root, tube, strict=True)
    )
    forward_error = max(
        abs(root_value - Fraction.from_float(center_value))
        for root_value, center_value in zip(root, center, strict=True)
    )
    return OracleResult(root, root_in_tube, forward_error)


def _require_interval(result: IntervalResult) -> Interval:
    if result.status is not IntervalStatus.OK or result.interval is None:
        raise RuntimeError(result.reason or "rigorous interval operation failed")
    return result.interval


def _checker_residual(
    diagonal: tuple[float, ...],
    right_hand_side: tuple[float, ...],
    center: tuple[float, ...],
) -> tuple[Interval, ...]:
    return tuple(
        _require_interval(
            subtract(
                _require_interval(
                    multiply(Interval.point(coefficient), Interval.point(value))
                ),
                Interval.point(target),
            )
        )
        for coefficient, target, value in zip(
            diagonal, right_hand_side, center, strict=True
        )
    )


def _run_checker(
    diagonal: tuple[float, ...],
    right_hand_side: tuple[float, ...],
    center: tuple[float, ...],
    tube: tuple[Interval, ...],
) -> CheckerResult:
    zero = Interval.point(0.0)
    jacobian = tuple(
        tuple(
            Interval.point(diagonal[row]) if row == column else zero
            for column in range(len(diagonal))
        )
        for row in range(len(diagonal))
    )
    return pointwise_krawczyk(
        center, tube, _checker_residual(diagonal, right_hand_side, center), jacobian
    )


def _format_float(value: float) -> str:
    return f"{value:.17g}"


def _format_fraction(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def build_case(
    exponent: int,
    precision: ProducerPrecision,
    *,
    residual_threshold: float = DEFAULT_RESIDUAL_THRESHOLD,
    tube_radius: float = DEFAULT_TUBE_RADIUS,
    seed: int = DEFAULT_SEED,
) -> dict[str, str]:
    """Build one row from an executed producer, exact oracle, and real checker."""

    if exponent < 1:
        raise ValueError("exponent must be positive")
    if tube_radius <= 0.0 or not math.isfinite(tube_radius):
        raise ValueError("tube radius must be finite and positive")
    if backend_info() is None:
        raise RuntimeError("the rigorous MPFR backend is required for checker verdicts")

    requested_epsilon = 10.0**-exponent
    epsilon = _cast(requested_epsilon, precision)
    diagonal = (_cast(1.0, precision), epsilon)
    right_hand_side = (_cast(1.0, precision), epsilon)
    producer = solve_diagonal_system(
        diagonal,
        right_hand_side,
        (_cast(1.0, precision), _cast(0.0, precision)),
        precision,
        residual_threshold,
    )
    tube = tuple(
        Interval(
            math.nextafter(value - tube_radius, -math.inf),
            math.nextafter(value + tube_radius, math.inf),
        )
        for value in producer.center
    )
    oracle = exact_diagonal_oracle(diagonal, right_hand_side, producer.center, tube)
    checker = _run_checker(diagonal, right_hand_side, producer.center, tube)
    false_accept = checker.verdict is CheckerVerdict.ACCEPT and not oracle.root_in_tube

    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": f"gmin_1e-{exponent}_{precision.value}",
        "mechanism": "weak_conductance_residual_early_stop",
        "run_seed": str(seed),
        "producer_algorithm": "residual_stopped_diagonal_newton",
        "producer_precision": precision.value,
        "producer_iterations": str(producer.iterations),
        "producer_converged": str(producer.converged).lower(),
        "epsilon_requested": f"1e-{exponent}",
        "epsilon_used": _format_float(epsilon),
        "epsilon_used_hex": epsilon.hex(),
        "condition_estimate": _format_float(1.0 / epsilon),
        "candidate_v0_hex": producer.center[0].hex(),
        "candidate_v1_hex": producer.center[1].hex(),
        "producer_residual_inf": _format_float(producer.residual_inf),
        "producer_residual_threshold": _format_float(producer.threshold),
        "declared_tube_radius": _format_float(tube_radius),
        "oracle_method": "exact_fraction_on_declared_binary_system",
        "oracle_root_v0": _format_fraction(oracle.root[0]),
        "oracle_root_v1": _format_fraction(oracle.root[1]),
        "oracle_root_in_tube": str(oracle.root_in_tube).lower(),
        "oracle_forward_error_inf": _format_fraction(oracle.forward_error_inf),
        "checker_method": "pointwise_krawczyk_midpoint_inverse",
        "checker_verdict": checker.verdict.value,
        "checker_inclusion_margin": (
            ""
            if checker.inclusion_margin is None
            else _format_float(checker.inclusion_margin)
        ),
        "checker_reason": checker.reason or "",
        "false_accept": str(false_accept).lower(),
    }


def generate_cases(seed: int = DEFAULT_SEED) -> list[dict[str, str]]:
    """Generate the complete unfiltered precision-by-conditioning grid."""

    return [
        build_case(exponent, precision, seed=seed)
        for exponent in range(5, 17)
        for precision in (ProducerPrecision.FLOAT32, ProducerPrecision.FLOAT64)
    ]


def _provenance(
    rows: list[dict[str, str]], csv_path: Path, seed: int
) -> dict[str, Any]:
    info = backend_info()
    if info is None:
        raise RuntimeError("the rigorous MPFR backend is unavailable")
    false_accept_rows = [
        row["case_id"] for row in rows if row["false_accept"] == "true"
    ]
    unsupported = sum(
        row["checker_verdict"] == CheckerVerdict.UNSUPPORTED.value for row in rows
    )
    configuration = {
        "seed": seed,
        "exponents": list(range(5, 17)),
        "precisions": [precision.value for precision in ProducerPrecision],
        "residual_threshold": DEFAULT_RESIDUAL_THRESHOLD,
        "tube_radius": DEFAULT_TUBE_RADIUS,
        "max_iterations": 1,
    }
    strict_controls = [
        build_case(8, precision, residual_threshold=0.0, seed=seed)
        for precision in ProducerPrecision
    ]
    sources = source_file_hashes(_PAPER_ROOT, _PROVENANCE_FILES)
    return {
        "schema_version": 2,
        "status": "PASS" if not false_accept_rows else "STOP",
        "claim_scope": (
            "static linear motivation canary; not nonlinear transient evidence"
        ),
        **git_state(_PAPER_ROOT.parent, "paper2"),
        **runtime_provenance(),
        "command": (
            "python3 -m experiments.generate_numerical_defects "
            "--output paper2/results/blockstamp/numerical_defect_cases.csv "
            f"--seed {seed}"
        ),
        "config_sha256": canonical_sha256(configuration),
        "input_sha256": canonical_sha256(
            {"seed": seed, "generator_version": 2, "case_order": "exponent_precision"}
        ),
        "source_files_sha256": sources,
        "random_seeds": {"base": seed},
        "attempted_cases": len(rows),
        "supported_cases": len(rows) - unsupported,
        "unsupported_cases": unsupported,
        "failure_codes": [] if not false_accept_rows else ["CHECKER_FALSE_ACCEPT"],
        "first_failure": (
            None if not false_accept_rows else {"case_id": false_accept_rows[0]}
        ),
        "artifact": "numerical_defect_cases.csv",
        "row_count": len(rows),
        "seed": seed,
        "randomness_used": False,
        "case_order": "exponent_ascending_then_float32_float64",
        "producer": "residual_stopped_diagonal_newton",
        "oracle": "fractions.Fraction exact solve of declared binary inputs",
        "checker": "pointwise_krawczyk_midpoint_inverse",
        "precision_semantics": {
            "float32": "round every producer operation through IEEE-754 binary32",
            "float64": "CPython IEEE-754 binary64 operations",
        },
        "strict_threshold_controls": {
            "cases": len(strict_controls),
            "all_performed_one_update": all(
                row["producer_iterations"] == "1" for row in strict_controls
            ),
            "all_roots_in_tube": all(
                row["oracle_root_in_tube"] == "true" for row in strict_controls
            ),
            "all_checker_accept": all(
                row["checker_verdict"] == CheckerVerdict.ACCEPT.value
                for row in strict_controls
            ),
            "false_accepts": sum(
                row["false_accept"] == "true" for row in strict_controls
            ),
        },
        "backend": {
            "name": info.name,
            "version": info.version,
            "precision_bits": info.precision_bits,
            "library": info.library,
        },
        "csv_sha256": sha256_file(csv_path),
    }


def write_cases(
    output: Path,
    *,
    provenance_output: Path | None = None,
    seed: int = DEFAULT_SEED,
) -> tuple[Path, Path]:
    """Write deterministic rows and a provenance sidecar without filtering."""

    rows = generate_cases(seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    metadata_path = provenance_output or output.with_suffix(".manifest.json")
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(_provenance(rows, output, seed), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output, metadata_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provenance-output", type=Path)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    arguments = parser.parse_args()
    write_cases(
        arguments.output,
        provenance_output=arguments.provenance_output,
        seed=arguments.seed,
    )


if __name__ == "__main__":
    main()
