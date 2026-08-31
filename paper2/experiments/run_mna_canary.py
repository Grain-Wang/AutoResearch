"""Run the frozen RC/diode-RC BE assembly and B2 pointwise canary."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

from experiments.checkers import (
    CheckerVerdict,
    check_be_step,
    pointwise_krawczyk,
)
from experiments.devices import MosParameters, mos_interval
from experiments.interval_backend import Interval
from experiments.mna import (
    Circuit,
    MnaStatus,
    Resistor,
    diode_rc_decimal_bracket,
    interval_be_residual_jacobian,
    point_be_residual_jacobian,
    rc_closed_form_next,
    rc_exact_next,
    rc_source_circuit,
    rc_state,
)
from experiments.mna.minimal_circuits import RESISTANCE, SOURCE_VOLTAGE
from experiments.provenance import (
    canonical_sha256,
    git_state,
    runtime_provenance,
    sha256_file,
    source_file_hashes,
)
from experiments.rigorous_backend import backend_info

_PAPER_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_OUTPUT = _PAPER_ROOT / "results/blockstamp/mna_canary.json"
_DEFAULT_FAIRNESS = _PAPER_ROOT / "results/blockstamp/b2_fairness.json"
_CONFIG = _PAPER_ROOT / "configs/blockstamp/b2_canary.yaml"
_SHARED_COMPONENTS = {
    "arithmetic_backend": _PAPER_ROOT / "experiments/rigorous_backend.py",
    "device_semantics": _PAPER_ROOT / "experiments/devices/stamps.py",
    "mna_semantics": _PAPER_ROOT / "experiments/mna/fixed_be.py",
    "pointwise_checker": _PAPER_ROOT / "experiments/checkers/pointwise_krawczyk.py",
    "be_binding": _PAPER_ROOT / "experiments/checkers/be_step.py",
    "configuration": _CONFIG,
}
_PROVENANCE_FILES = tuple(_SHARED_COMPONENTS.values()) + (
    Path(__file__).resolve(),
    _PAPER_ROOT / "experiments/mna/oracles.py",
    _PAPER_ROOT / "experiments/mna/minimal_circuits.py",
    _PAPER_ROOT / "experiments/provenance.py",
)
_RADII = (1e-9, 1e-12, 1e-12)


def _tube(state: tuple[float, ...]) -> tuple[Interval, ...]:
    return tuple(
        Interval(value - radius, value + radius)
        for value, radius in zip(state, _RADII, strict=True)
    )


def _fraction_oracle_inside(
    image: tuple[Interval, ...] | None, exact: tuple[Fraction, ...]
) -> bool:
    if image is None:
        return False
    return all(
        Fraction.from_float(enclosure.lower)
        <= exact_value
        <= Fraction.from_float(enclosure.upper)
        for enclosure, exact_value in zip(image, exact, strict=True)
    )


def _decimal_bracket_inside(
    image: tuple[Interval, ...] | None,
    bracket: tuple[tuple[Decimal, Decimal], ...],
) -> bool:
    if image is None:
        return False
    return all(
        Decimal.from_float(enclosure.lower) <= lower
        and upper <= Decimal.from_float(enclosure.upper)
        for enclosure, (lower, upper) in zip(image, bracket, strict=True)
    )


def _run_trajectory(*, diode: bool, steps: int, step_size: float) -> dict[str, object]:
    circuit = rc_source_circuit(diode=diode)
    previous = rc_state(0.0)
    accepted = 0
    unknown = 0
    unsupported = 0
    oracle_outside_image = 0
    checker_false_accepts = 0
    max_point_residual = 0.0
    jacobian_sample_count = 0
    jacobian_containment_violations = 0
    minimum_margin = float("inf")
    first_failure_step: int | None = None
    started = time.perf_counter()
    for step_index in range(steps):
        if diode:
            lower_voltage, upper_voltage = diode_rc_decimal_bracket(
                previous[0], step_size
            )
            with localcontext() as context:
                context.prec = 160
                voltage = float((lower_voltage + upper_voltage) / 2)
                source = Decimal.from_float(SOURCE_VOLTAGE)
                resistance = Decimal.from_float(RESISTANCE)
                lower_current = (lower_voltage - source) / resistance
                upper_current = (upper_voltage - source) / resistance
            decimal_bracket = (
                (lower_voltage, upper_voltage),
                (source, source),
                (lower_current, upper_current),
            )
            exact_fraction_state = None
        else:
            exact_voltage = rc_exact_next(previous[0], step_size)
            voltage = float(exact_voltage)
            source_fraction = Fraction.from_float(SOURCE_VOLTAGE)
            exact_fraction_state = (
                exact_voltage,
                source_fraction,
                (exact_voltage - source_fraction) / Fraction.from_float(RESISTANCE),
            )
            decimal_bracket = None
        current = rc_state(voltage)
        previous_box = tuple(Interval.point(value) for value in previous)
        point_evaluation = point_be_residual_jacobian(
            circuit, current, previous, step_size
        )
        interval_evaluation = interval_be_residual_jacobian(
            circuit, _tube(current), previous_box, step_size
        )
        if (
            point_evaluation.status is not MnaStatus.OK
            or point_evaluation.residual is None
            or point_evaluation.jacobian is None
            or interval_evaluation.status is not MnaStatus.OK
            or interval_evaluation.jacobian is None
        ):
            unsupported += 1
            if first_failure_step is None:
                first_failure_step = step_index
            previous = current
            continue
        max_point_residual = max(
            max_point_residual,
            max(abs(value) for value in point_evaluation.residual),
        )
        for point_row, interval_row in zip(
            point_evaluation.jacobian,
            interval_evaluation.jacobian,
            strict=True,
        ):
            for point_value, interval_value in zip(
                point_row, interval_row, strict=True
            ):
                jacobian_sample_count += 1
                if not interval_value.contains(point_value):
                    jacobian_containment_violations += 1
        checked = check_be_step(
            circuit,
            current,
            _tube(current),
            previous_box,
            step_size,
        )
        if checked.verdict is CheckerVerdict.ACCEPT:
            accepted += 1
        elif checked.verdict is CheckerVerdict.UNKNOWN:
            unknown += 1
        else:
            unsupported += 1
        if checked.verdict is not CheckerVerdict.ACCEPT and first_failure_step is None:
            first_failure_step = step_index
        oracle_inside = (
            _decimal_bracket_inside(checked.image, decimal_bracket)
            if decimal_bracket is not None
            else _fraction_oracle_inside(checked.image, exact_fraction_state)
        )
        if not oracle_inside:
            oracle_outside_image += 1
            if checked.verdict is CheckerVerdict.ACCEPT:
                checker_false_accepts += 1
        if checked.inclusion_margin is not None:
            minimum_margin = min(minimum_margin, checked.inclusion_margin)
        previous = current
    return {
        "circuit": "diode-rc-source" if diode else "rc-source",
        "steps": steps,
        "accepted": accepted,
        "unknown": unknown,
        "unsupported": unsupported,
        "oracle": ("Decimal-160 bisection bracket" if diode else "exact Fraction root"),
        "oracle_precision_decimal_digits": 160 if diode else None,
        "oracle_precision_bits": 531 if diode else None,
        "oracle_precision_kind": "finite Decimal" if diode else "exact rational",
        "root_contained_steps": steps - oracle_outside_image,
        "root_excluded_steps": oracle_outside_image,
        "oracle_bracket_outside_checker_image": oracle_outside_image,
        "max_point_residual": max_point_residual,
        "jacobian_sample_count": jacobian_sample_count,
        "jacobian_containment_violations": jacobian_containment_violations,
        "checker_false_accepts": checker_false_accepts,
        "minimum_inclusion_margin": (
            minimum_margin if minimum_margin != float("inf") else None
        ),
        "first_failure_step": first_failure_step,
        "seconds": time.perf_counter() - started,
    }


def _wrong_history_audit(step_size: float) -> dict[str, object]:
    circuit = rc_source_circuit()
    records: list[dict[str, object]] = []
    for index in range(10):
        correct_previous_voltage = 0.02 * index
        wrong_previous_voltage = correct_previous_voltage + 0.2
        voltage = rc_closed_form_next(correct_previous_voltage, step_size)
        current = rc_state(voltage)
        checked = check_be_step(
            circuit,
            current,
            _tube(current),
            tuple(Interval.point(value) for value in rc_state(wrong_previous_voltage)),
            step_size,
        )
        records.append(
            {
                "case_id": f"wrong-history-{index}",
                "oracle_root_in_tube": False,
                "checker_verdict": checked.verdict.value,
                "failure_code": "WRONG_BE_HISTORY_NOT_CERTIFIED",
            }
        )

    true_voltage = rc_closed_form_next(0.0, step_size)
    wrong_center = rc_state(true_voltage + 0.2)
    root_excluding = check_be_step(
        circuit,
        wrong_center,
        _tube(wrong_center),
        tuple(Interval.point(value) for value in rc_state(0.0)),
        step_size,
    )
    records.append(
        {
            "case_id": "root-excluding-tube",
            "oracle_root_in_tube": False,
            "checker_verdict": root_excluding.verdict.value,
            "failure_code": "STRICT_INCLUSION_FAILED",
        }
    )
    correct_state = rc_state(rc_closed_form_next(0.0, step_size))
    permuted_state = (correct_state[1], correct_state[0], correct_state[2])
    permuted = check_be_step(
        circuit,
        permuted_state,
        _tube(permuted_state),
        tuple(Interval.point(value) for value in rc_state(0.0)),
        step_size,
    )
    records.append(
        {
            "case_id": "state-permutation-mismatch",
            "oracle_root_in_tube": False,
            "checker_verdict": permuted.verdict.value,
            "failure_code": "STATE_PERMUTATION_NOT_CERTIFIED",
        }
    )
    singular = pointwise_krawczyk(
        (0.0,),
        (Interval(-1.0, 1.0),),
        (Interval.point(2.0),),
        ((Interval.point(0.0),),),
    )
    records.append(
        {
            "case_id": "singular-midpoint-operator",
            "oracle_root_in_tube": None,
            "checker_verdict": singular.verdict.value,
            "failure_code": "SINGULAR_OPERATOR",
        }
    )
    invalid_topology = point_be_residual_jacobian(
        Circuit(node_count=1, resistors=(Resistor(1, 1, 1_000.0),)),
        (0.0,),
        (0.0,),
        step_size,
    )
    records.append(
        {
            "case_id": "invalid-node-mapping",
            "oracle_root_in_tube": None,
            "checker_verdict": (
                CheckerVerdict.UNSUPPORTED.value
                if invalid_topology.status is MnaStatus.UNSUPPORTED
                else CheckerVerdict.ACCEPT.value
            ),
            "failure_code": "INVALID_TOPOLOGY",
        }
    )
    malformed_state = point_be_residual_jacobian(circuit, (0.0,), (0.0,), step_size)
    records.append(
        {
            "case_id": "malformed-state-layout",
            "oracle_root_in_tube": None,
            "checker_verdict": (
                CheckerVerdict.UNSUPPORTED.value
                if malformed_state.status is MnaStatus.UNSUPPORTED
                else CheckerVerdict.ACCEPT.value
            ),
            "failure_code": "STATE_DIMENSION_MISMATCH",
        }
    )
    diode_domain = interval_be_residual_jacobian(
        rc_source_circuit(diode=True),
        (Interval(1_000.0, 1_001.0), Interval.point(1.0), Interval.point(0.0)),
        tuple(Interval.point(value) for value in rc_state(0.0)),
        step_size,
    )
    records.append(
        {
            "case_id": "unsupported-diode-domain-box",
            "oracle_root_in_tube": None,
            "checker_verdict": (
                CheckerVerdict.UNSUPPORTED.value
                if diode_domain.status is MnaStatus.UNSUPPORTED
                else CheckerVerdict.ACCEPT.value
            ),
            "failure_code": "UNSUPPORTED_DEVICE_DOMAIN",
        }
    )
    branch_crossing = mos_interval(
        Interval(0.49, 0.51), Interval(0.0, 0.1), MosParameters()
    )
    records.append(
        {
            "case_id": "mos-region-branch-crossing",
            "oracle_root_in_tube": None,
            "checker_verdict": (
                CheckerVerdict.UNSUPPORTED.value
                if branch_crossing is None
                else CheckerVerdict.ACCEPT.value
            ),
            "failure_code": "UNSUPPORTED_BRANCH_CROSSING",
        }
    )
    false_accepts = sum(
        record["checker_verdict"] == CheckerVerdict.ACCEPT.value for record in records
    )
    return {
        "cases": len(records),
        "false_accepts": false_accepts,
        "records": records,
    }


def run_canary(
    steps: int, step_size: float
) -> tuple[dict[str, object], dict[str, object]]:
    """Return MNA correctness and B2 fairness artifacts."""

    info = backend_info()
    if info is None:
        raise RuntimeError("MPFR backend is unavailable")
    trajectories = [
        _run_trajectory(diode=False, steps=steps, step_size=step_size),
        _run_trajectory(diode=True, steps=steps, step_size=step_size),
    ]
    wrong_history = _wrong_history_audit(step_size)
    violations = sum(
        int(trajectory["oracle_bracket_outside_checker_image"])
        + int(trajectory["jacobian_containment_violations"])
        + int(trajectory["checker_false_accepts"])
        + int(trajectory["unknown"])
        + int(trajectory["unsupported"])
        for trajectory in trajectories
    ) + int(wrong_history["false_accepts"])
    source_hashes = source_file_hashes(_PAPER_ROOT, _PROVENANCE_FILES)
    topology_payload = {
        "rc": asdict(rc_source_circuit()),
        "diode_rc": asdict(rc_source_circuit(diode=True)),
    }
    valid_accepted = sum(int(item["accepted"]) for item in trajectories)
    valid_supported = sum(
        int(item["accepted"]) + int(item["unknown"]) for item in trajectories
    )
    valid_unsupported = sum(int(item["unsupported"]) for item in trajectories)
    negative_records = wrong_history["records"]
    expected_unsupported = sum(
        record["checker_verdict"] == CheckerVerdict.UNSUPPORTED.value
        for record in negative_records
    )
    negative_supported = len(negative_records) - expected_unsupported
    common = {
        **git_state(_PAPER_ROOT.parent, "paper2"),
        **runtime_provenance(),
        "backend": {
            "name": info.name,
            "version": info.version,
            "precision_bits": info.precision_bits,
            "library": info.library,
        },
    }
    result = {
        "schema_version": 1,
        "status": "PASS" if violations == 0 else "STOP",
        "claim_scope": (
            "restricted BE MNA and dense pointwise checker canary; not B2-strong"
        ),
        **common,
        "command": (
            "python3 -m experiments.run_mna_canary "
            f"--steps {steps} --step-size {step_size}"
        ),
        "config_sha256": sha256_file(_CONFIG),
        "input_sha256": canonical_sha256(topology_payload),
        "source_files_sha256": source_hashes,
        "random_seeds": {},
        "attempted_cases": 2 * steps + int(wrong_history["cases"]),
        "supported_cases": valid_supported + negative_supported,
        "unsupported_cases": valid_unsupported + expected_unsupported,
        "failure_codes": [] if violations == 0 else ["MNA_CANARY_VIOLATION"],
        "first_failure": None if violations == 0 else {"replay": "see trajectories"},
        "semantics_sha256": source_hashes["experiments/mna/fixed_be.py"],
        "state_layout_sha256": canonical_sha256(
            "non-ground node voltages then voltage-source currents"
        ),
        "topology_sha256": canonical_sha256(topology_payload),
        "step_method": "fixed-step-backward-euler",
        "step_size": step_size,
        "steps": steps,
        "steps_per_circuit": steps,
        "trajectories": trajectories,
        "circuits": {
            "rc": trajectories[0],
            "diode_rc": trajectories[1],
        },
        "negative_cases": wrong_history,
        "wrong_history_audit": wrong_history,
        "violations": violations,
    }
    component_hashes = {
        name: sha256_file(path) for name, path in _SHARED_COMPONENTS.items()
    }
    fairness = {
        "schema_version": 1,
        "status": "ITERATE",
        "stage": "B2-CANARY-ONLY",
        "strong_baseline_status": "UNIMPLEMENTED-VERIFIED-SPARSE",
        **common,
        "command": (
            "python3 -m experiments.run_mna_canary "
            f"--steps {steps} --step-size {step_size}"
        ),
        "config_sha256": sha256_file(_CONFIG),
        "input_sha256": canonical_sha256(topology_payload),
        "source_files_sha256": source_hashes,
        "random_seeds": {},
        "attempted_cases": 2 * steps + int(wrong_history["cases"]),
        "supported_cases": valid_supported + negative_supported,
        "unsupported_cases": valid_unsupported + expected_unsupported,
        "failure_codes": [],
        "first_failure": None,
        "shared_component_sha256": component_hashes,
        "fairness_manifest_sha256": canonical_sha256(component_hashes),
        "all_required_hashes_present": False,
        "all_shared_hashes_match": None,
        "allowed_method_differences": ["verification organization only"],
        "easy_case_accepts": valid_accepted,
        "known_bad_cases": int(wrong_history["cases"]),
        "confirmed_false_accepts": int(wrong_history["false_accepts"]),
        "frozen_fields": {
            "candidate": "independent analytic/Decimal root",
            "tube_radii": list(_RADII),
            "scaling": "identity",
            "ordering": "normalized state layout",
            "midpoint_factor": "checker-side dense verified elimination",
            "threads": 1,
        },
        "missing_for_b2_strong": [
            "verified sparse kernel",
            "component-matched BlockStamp circuit path",
            "timing/RSS/certificate-byte ladder",
        ],
    }
    return result, fairness


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--step-size", type=float, default=1e-5)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--fairness-output", type=Path, default=_DEFAULT_FAIRNESS)
    arguments = parser.parse_args()
    if arguments.steps <= 0:
        parser.error("--steps must be positive")
    if arguments.step_size <= 0.0:
        parser.error("--step-size must be positive")
    result, fairness = run_canary(arguments.steps, arguments.step_size)
    for path, payload in (
        (arguments.output, result),
        (arguments.fairness_output, fairness),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(fairness, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
