"""Rebuild the MPFR directed-rounding audit artifact."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from collections.abc import Callable
from dataclasses import asdict
from decimal import Decimal, localcontext
from pathlib import Path

from experiments.interval_backend import Interval, IntervalResult, IntervalStatus
from experiments.provenance import (
    canonical_sha256,
    git_state,
    runtime_provenance,
    source_file_hashes,
)
from experiments.rigorous_backend import (
    add,
    backend_info,
    divide,
    exp,
    expm1,
    log,
    multiply,
    sqrt,
    subtract,
)

_PAPER_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_OUTPUT = _PAPER_ROOT / "results/blockstamp/rigorous_backend_summary.json"
_MAX_BINARY64 = Decimal.from_float(float.fromhex("0x1.fffffffffffffp+1023"))


def _contains(result: IntervalResult, exact: Decimal) -> bool:
    if result.status is not IntervalStatus.OK or result.interval is None:
        return False
    return (
        Decimal.from_float(result.interval.lower)
        <= exact
        <= Decimal.from_float(result.interval.upper)
    )


def _binary_inputs(
    generator: random.Random, operation_name: str
) -> tuple[float, float]:
    left = math.ldexp(generator.uniform(-1.0, 1.0), generator.randint(-500, 500))
    right = math.ldexp(generator.uniform(-1.0, 1.0), generator.randint(-500, 500))
    if operation_name == "div" and right == 0.0:
        right = math.ulp(0.0)
    return left, right


def _audit_binary(
    operation_name: str,
    operation: Callable[[Interval, Interval], IntervalResult],
    oracle: Callable[[Decimal, Decimal], Decimal],
    samples: int,
    seed: int,
) -> dict[str, int | float]:
    generator = random.Random(seed)
    supported = 0
    unsupported = 0
    violations = 0
    started = time.perf_counter()
    with localcontext() as context:
        context.prec = 2_500
        for _ in range(samples):
            left, right = _binary_inputs(generator, operation_name)
            exact = oracle(Decimal.from_float(left), Decimal.from_float(right))
            result = operation(Interval.point(left), Interval.point(right))
            representable = exact.copy_abs() <= _MAX_BINARY64
            if result.status is IntervalStatus.OK:
                supported += 1
                if not _contains(result, exact):
                    violations += 1
            else:
                unsupported += 1
                if representable:
                    violations += 1
    return {
        "random_cases": samples,
        "supported_cases": supported,
        "unsupported_cases": unsupported,
        "containment_violations": violations,
        "oracle_precision_decimal_digits": 2_500,
        "oracle_precision_bits": 8_304,
        "seconds": time.perf_counter() - started,
    }


def _unary_input(generator: random.Random, operation_name: str) -> float:
    if operation_name == "exp":
        return generator.uniform(-744.0, 709.0)
    if operation_name == "expm1":
        return generator.uniform(-50.0, 50.0)
    return math.ldexp(generator.uniform(0.5, 1.0), generator.randint(-1_073, 1_023))


def _audit_unary(
    operation_name: str,
    operation: Callable[[Interval], IntervalResult],
    oracle: Callable[[Decimal], Decimal],
    samples: int,
    seed: int,
    decimal_digits: int,
) -> dict[str, int | float]:
    generator = random.Random(seed)
    supported = 0
    unsupported = 0
    violations = 0
    started = time.perf_counter()
    with localcontext() as context:
        context.prec = decimal_digits
        for _ in range(samples):
            value = _unary_input(generator, operation_name)
            exact = oracle(Decimal.from_float(value))
            result = operation(Interval.point(value))
            representable = exact.copy_abs() <= _MAX_BINARY64
            if result.status is IntervalStatus.OK:
                supported += 1
                if not _contains(result, exact):
                    violations += 1
            else:
                unsupported += 1
                if representable:
                    violations += 1
    return {
        "random_cases": samples,
        "supported_cases": supported,
        "unsupported_cases": unsupported,
        "containment_violations": violations,
        "oracle_decimal_digits": decimal_digits,
        "oracle_precision_decimal_digits": decimal_digits,
        "oracle_precision_bits": int(decimal_digits * math.log2(10)),
        "seconds": time.perf_counter() - started,
    }


def _edge_result_is_valid(result: IntervalResult, exact: Decimal | None) -> bool:
    if exact is None or exact.copy_abs() > _MAX_BINARY64:
        return result.status is IntervalStatus.UNSUPPORTED
    return _contains(result, exact)


def _edge_audit() -> dict[str, dict[str, object]]:
    """Exercise a fixed, operation-specific edge corpus.

    The cases are explicit rather than inferred from the random generator.  ``None``
    is the oracle marker for a deliberately unsupported mathematical domain.
    """

    minimum = math.ulp(0.0)
    maximum = float.fromhex("0x1.fffffffffffffp+1023")
    next_one = math.nextafter(1.0, math.inf)
    binary_cases: dict[
        str,
        tuple[
            Callable[[Interval, Interval], IntervalResult],
            Callable[[Decimal, Decimal], Decimal],
            tuple[tuple[str, Interval, Interval, bool], ...],
        ],
    ] = {
        "add": (
            add,
            lambda left, right: left + right,
            (
                (
                    "positive_subnormal",
                    Interval.point(minimum),
                    Interval.point(minimum),
                    True,
                ),
                (
                    "negative_subnormal",
                    Interval.point(-minimum),
                    Interval.point(-minimum),
                    True,
                ),
                (
                    "strong_cancellation",
                    Interval.point(1e300),
                    Interval.point(-1e300),
                    True,
                ),
                (
                    "near_one_rounding",
                    Interval.point(next_one),
                    Interval.point(minimum),
                    True,
                ),
                (
                    "finite_overflow_frontier",
                    Interval.point(maximum),
                    Interval.point(-math.ulp(maximum)),
                    True,
                ),
                (
                    "positive_overflow",
                    Interval.point(maximum),
                    Interval.point(maximum),
                    True,
                ),
                (
                    "signed_zero_neighborhood",
                    Interval.point(-minimum),
                    Interval.point(minimum),
                    True,
                ),
            ),
        ),
        "sub": (
            subtract,
            lambda left, right: left - right,
            (
                (
                    "positive_subnormal",
                    Interval.point(minimum),
                    Interval.point(-minimum),
                    True,
                ),
                (
                    "negative_subnormal",
                    Interval.point(-minimum),
                    Interval.point(minimum),
                    True,
                ),
                (
                    "strong_cancellation",
                    Interval.point(1e300),
                    Interval.point(1e300),
                    True,
                ),
                (
                    "near_one_rounding",
                    Interval.point(next_one),
                    Interval.point(1.0),
                    True,
                ),
                (
                    "finite_overflow_frontier",
                    Interval.point(maximum),
                    Interval.point(math.ulp(maximum)),
                    True,
                ),
                (
                    "positive_overflow",
                    Interval.point(maximum),
                    Interval.point(-maximum),
                    True,
                ),
                (
                    "signed_zero_neighborhood",
                    Interval.point(-minimum),
                    Interval.point(minimum),
                    True,
                ),
            ),
        ),
        "mul": (
            multiply,
            lambda left, right: left * right,
            (
                (
                    "subnormal_underflow",
                    Interval.point(minimum),
                    Interval.point(0.5),
                    True,
                ),
                (
                    "negative_subnormal",
                    Interval.point(-minimum),
                    Interval.point(1.5),
                    True,
                ),
                ("signed_product", Interval.point(-3.0), Interval.point(7.0), True),
                (
                    "near_one_rounding",
                    Interval.point(next_one),
                    Interval.point(next_one),
                    True,
                ),
                (
                    "finite_overflow_frontier",
                    Interval.point(maximum),
                    Interval.point(0.5),
                    True,
                ),
                (
                    "positive_overflow",
                    Interval.point(maximum),
                    Interval.point(2.0),
                    True,
                ),
                ("exact_zero", Interval.point(maximum), Interval.point(0.0), True),
            ),
        ),
        "div": (
            divide,
            lambda left, right: left / right,
            (
                (
                    "subnormal_result",
                    Interval.point(minimum),
                    Interval.point(2.0),
                    True,
                ),
                (
                    "near_zero_denominator",
                    Interval.point(minimum),
                    Interval.point(minimum),
                    True,
                ),
                (
                    "negative_near_zero_denominator",
                    Interval.point(1.0),
                    Interval.point(-minimum),
                    True,
                ),
                (
                    "zero_crossing_denominator",
                    Interval.point(1.0),
                    Interval(-minimum, minimum),
                    False,
                ),
                (
                    "near_one_rounding",
                    Interval.point(next_one),
                    Interval.point(3.0),
                    True,
                ),
                (
                    "finite_overflow_frontier",
                    Interval.point(maximum),
                    Interval.point(2.0),
                    True,
                ),
                (
                    "positive_overflow",
                    Interval.point(maximum),
                    Interval.point(0.5),
                    True,
                ),
            ),
        ),
    }
    unary_cases: dict[
        str,
        tuple[
            Callable[[Interval], IntervalResult],
            Callable[[Decimal], Decimal],
            int,
            tuple[tuple[str, Interval, bool], ...],
        ],
    ] = {
        "exp": (
            exp,
            lambda value: value.exp(),
            220,
            (
                ("subnormal_underflow", Interval.point(-745.0), True),
                ("finite_overflow_frontier", Interval.point(709.0), True),
                ("positive_overflow", Interval.point(710.0), True),
                ("exact_origin", Interval.point(0.0), True),
                ("cancellation_sensitive_small", Interval.point(math.ulp(1.0)), True),
                ("rounding_probe_positive", Interval.point(next_one), True),
                ("rounding_probe_negative", Interval.point(-next_one), True),
            ),
        ),
        "expm1": (
            expm1,
            lambda value: value.exp() - Decimal(1),
            220,
            (
                ("negative_saturation", Interval.point(-1_000.0), True),
                ("finite_overflow_frontier", Interval.point(709.0), True),
                ("positive_overflow", Interval.point(710.0), True),
                ("exact_origin", Interval.point(0.0), True),
                ("cancellation_sensitive_small", Interval.point(math.ulp(1.0)), True),
                ("rounding_probe_positive", Interval.point(next_one), True),
                ("rounding_probe_negative", Interval.point(-next_one), True),
            ),
        ),
        "log": (
            log,
            lambda value: value.ln(),
            220,
            (
                ("smallest_subnormal", Interval.point(minimum), True),
                ("largest_finite", Interval.point(maximum), True),
                ("domain_zero", Interval.point(0.0), False),
                ("domain_crossing", Interval(-minimum, minimum), False),
                ("exact_one", Interval.point(1.0), True),
                ("cancellation_sensitive_near_one", Interval.point(next_one), True),
                (
                    "rounding_probe",
                    Interval.point(float.fromhex("0x1.0000000000001p-20")),
                    True,
                ),
            ),
        ),
        "sqrt": (
            sqrt,
            lambda value: value.sqrt(),
            600,
            (
                ("smallest_subnormal", Interval.point(minimum), True),
                ("largest_finite", Interval.point(maximum), True),
                ("domain_negative", Interval.point(-minimum), False),
                ("domain_crossing", Interval(-minimum, minimum), False),
                ("exact_zero", Interval.point(0.0), True),
                ("irrational_two", Interval.point(2.0), True),
                ("rounding_probe", Interval.point(next_one), True),
            ),
        ),
    }
    audited: dict[str, dict[str, object]] = {}
    with localcontext() as context:
        context.prec = 2_500
        for name, (operation, oracle, cases) in binary_cases.items():
            failures: list[str] = []
            supported = 0
            unsupported = 0
            for family, left, right, has_oracle in cases:
                exact = (
                    oracle(
                        Decimal.from_float(left.lower), Decimal.from_float(right.lower)
                    )
                    if has_oracle
                    and left.lower == left.upper
                    and right.lower == right.upper
                    else None
                )
                result = operation(left, right)
                supported += int(result.status is IntervalStatus.OK)
                unsupported += int(result.status is IntervalStatus.UNSUPPORTED)
                if not _edge_result_is_valid(result, exact):
                    failures.append(family)
            audited[name] = {
                "edge_cases": len(cases),
                "supported_cases": supported,
                "unsupported_cases": unsupported,
                "containment_violations": len(failures),
                "edge_families": [family for family, *_ in cases],
                "failures": failures,
            }
        for name, (operation, oracle, decimal_digits, cases) in unary_cases.items():
            failures = []
            supported = 0
            unsupported = 0
            with localcontext() as unary_context:
                unary_context.prec = decimal_digits
                for family, value, has_oracle in cases:
                    exact = (
                        oracle(Decimal.from_float(value.lower)) if has_oracle else None
                    )
                    result = operation(value)
                    supported += int(result.status is IntervalStatus.OK)
                    unsupported += int(result.status is IntervalStatus.UNSUPPORTED)
                    if not _edge_result_is_valid(result, exact):
                        failures.append(family)
            audited[name] = {
                "edge_cases": len(cases),
                "supported_cases": supported,
                "unsupported_cases": unsupported,
                "containment_violations": len(failures),
                "edge_families": [family for family, *_ in cases],
                "failures": failures,
            }
    return audited


def run_audit(samples: int, seed: int) -> dict[str, object]:
    """Run the frozen arithmetic audit and return its serializable summary."""

    info = backend_info()
    if info is None:
        raise RuntimeError("MPFR backend is unavailable")
    binary_operations = {
        "add": (add, lambda left, right: left + right),
        "sub": (subtract, lambda left, right: left - right),
        "mul": (multiply, lambda left, right: left * right),
        "div": (divide, lambda left, right: left / right),
    }
    unary_operations = {
        "exp": (exp, lambda value: value.exp(), 220),
        "expm1": (expm1, lambda value: value.exp() - Decimal(1), 220),
        "log": (log, lambda value: value.ln(), 220),
        # Exact square roots of very small dyadic inputs can require almost 400
        # decimal digits.  A shorter Decimal context creates an oracle false alarm.
        "sqrt": (sqrt, lambda value: value.sqrt(), 600),
    }
    operations: dict[str, dict[str, int | float]] = {}
    for index, (name, (operation, oracle)) in enumerate(binary_operations.items()):
        operations[name] = _audit_binary(name, operation, oracle, samples, seed + index)
    for index, (name, (operation, oracle, digits)) in enumerate(
        unary_operations.items()
    ):
        operations[name] = _audit_unary(
            name, operation, oracle, samples, seed + 100 + index, digits
        )
    edge = _edge_audit()
    for name, edge_result in edge.items():
        random_violations = int(operations[name]["containment_violations"])
        random_supported = int(operations[name]["supported_cases"])
        random_unsupported = int(operations[name]["unsupported_cases"])
        operations[name].update(
            {
                "edge_cases": edge_result["edge_cases"],
                "edge_supported_cases": edge_result["supported_cases"],
                "edge_unsupported_cases": edge_result["unsupported_cases"],
                "random_supported_cases": random_supported,
                "random_unsupported_cases": random_unsupported,
                "supported_cases": random_supported
                + int(edge_result["supported_cases"]),
                "unsupported_cases": random_unsupported
                + int(edge_result["unsupported_cases"]),
                "random_containment_violations": random_violations,
                "edge_containment_violations": edge_result["containment_violations"],
                "containment_violations": random_violations
                + int(edge_result["containment_violations"]),
                "edge_families": edge_result["edge_families"],
                "edge_failures": edge_result["failures"],
            }
        )
    violations = sum(
        int(result["containment_violations"]) for result in operations.values()
    )
    oracle_precision = {
        "binary_decimal_digits": 2_500,
        "exp_decimal_digits": 220,
        "expm1_decimal_digits": 220,
        "log_decimal_digits": 220,
        "sqrt_decimal_digits": 600,
    }
    configuration = {
        "samples_per_operation": samples,
        "seed": seed,
        "precision_bits": info.precision_bits,
        "oracle_precision": oracle_precision,
        "edge_corpus_version": 2,
    }
    source_hashes = source_file_hashes(
        _PAPER_ROOT,
        (
            Path(__file__).resolve(),
            _PAPER_ROOT / "experiments/rigorous_backend.py",
            _PAPER_ROOT / "experiments/interval_backend.py",
            _PAPER_ROOT / "experiments/provenance.py",
        ),
    )
    supported_cases = sum(
        int(result["supported_cases"]) for result in operations.values()
    )
    unsupported_cases = sum(
        int(result["unsupported_cases"]) for result in operations.values()
    )
    edge_cases = sum(int(result["edge_cases"]) for result in operations.values())
    return {
        "schema_version": 1,
        "status": "PASS" if violations == 0 else "STOP",
        "claim_scope": (
            "directed-rounding implementation audit; not a formal MPFR proof"
        ),
        **git_state(_PAPER_ROOT.parent, "paper2"),
        **runtime_provenance(),
        "command": (
            "python3 -m experiments.run_rigorous_backend "
            f"--samples {samples} --seed {seed}"
        ),
        "config_sha256": canonical_sha256(configuration),
        "input_sha256": canonical_sha256(
            {"seed": seed, "generator_version": 1, "edge_corpus_version": 2}
        ),
        "source_files_sha256": source_hashes,
        "attempted_cases": samples * len(operations) + edge_cases,
        "supported_cases": supported_cases,
        "unsupported_cases": unsupported_cases,
        "failure_codes": [] if violations == 0 else ["CONTAINMENT_VIOLATION"],
        "first_failure": None if violations == 0 else {"replay": "see operations"},
        "backend": asdict(info),
        "rounding_modes": {"lower": "RNDD", "upper": "RNDU"},
        "oracle": {
            "name": "Python Decimal independent expression",
            "precision": oracle_precision,
        },
        "random_seeds": {
            "base": seed,
            **{name: seed + index for index, name in enumerate(binary_operations)},
            **{name: seed + 100 + index for index, name in enumerate(unary_operations)},
        },
        "random_cases_per_operation": samples,
        "operations": operations,
        "edge_corpus": {
            "version": 2,
            "total_cases": edge_cases,
            "containment_violations": sum(
                int(result["containment_violations"]) for result in edge.values()
            ),
            "operations": edge,
        },
        "containment_violations": violations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=20_260_831)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    if arguments.samples <= 0:
        parser.error("--samples must be positive")
    summary = run_audit(arguments.samples, arguments.seed)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
