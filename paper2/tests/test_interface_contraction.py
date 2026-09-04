from experiments.benchmark import (
    measure_contractive_pointwise_prefix,
    measure_contractive_slab_prefix,
    measure_greedy_contractive_prefix,
)
from experiments.checkers import CheckerVerdict
from experiments.interval_backend import Interval
from experiments.mna import rc_closed_form_next, rc_source_circuit, rc_state
from experiments.producers import ProducerPrecision, TraceResult, TraceStep, TubeRule
from experiments.run_interface_contraction_canary import (
    run_interface_contraction_canary,
)


def _rc_trace(steps: int) -> tuple[TraceResult, tuple[float, ...]]:
    previous = rc_state(0.0)
    records = []
    radii = (1e-9, 1e-12, 1e-12)
    for index in range(steps):
        current = rc_state(rc_closed_form_next(previous[0], 1e-5))
        tube = tuple(
            Interval(value - radius, value + radius)
            for value, radius in zip(current, radii, strict=True)
        )
        records.append(
            TraceStep(
                index,
                current,
                tube,
                radii,
                True,
                1,
                0.0,
                0.0,
                None,
                current,
                0.0,
                True,
                CheckerVerdict.UNKNOWN,
                None,
                None,
                0.0,
                0.0,
                0.0,
                0.0,
            )
        )
        previous = current
    return (
        TraceResult(
            "rc",
            "analytic",
            ProducerPrecision.FLOAT64,
            0.0,
            steps,
            1e-5,
            1.0,
            TubeRule(radii, (1.0, 1.0, 1.0), 1.0),
            "analytic",
            tuple(records),
            None,
        ),
        rc_state(0.0),
    )


def test_contractive_pointwise_fixed_and_greedy_cover_analytic_rc() -> None:
    trace, initial = _rc_trace(4)
    circuit = rc_source_circuit()
    pointwise = measure_contractive_pointwise_prefix(trace, circuit, initial)
    fixed = measure_contractive_slab_prefix(trace, circuit, initial, 2)
    greedy = measure_greedy_contractive_prefix(trace, circuit, initial, (4, 2, 1))
    assert pointwise.verdict is CheckerVerdict.ACCEPT
    assert fixed.verdict is CheckerVerdict.ACCEPT
    assert greedy.verdict is CheckerVerdict.ACCEPT
    assert pointwise.certified_prefix_steps == 4
    assert fixed.segment_lengths == (2, 2)
    assert greedy.segment_lengths == (4,)
    assert len(pointwise.outgoing_interfaces) == 4


def test_reduced_interface_canary_preserves_all_registered_diode_instances() -> None:
    result = run_interface_contraction_canary(steps=2, circuit_filter="diode_rc")
    assert result["status"] == "PASS-CANARY"
    assert result["attempted_traces"] == 3
    assert result["completed_traces"] == 3
    assert result["success_only_filtering"] is False
    assert result["claim_w_killer_baseline"]["status"] == "REDUCED-TEST-ONLY"
    assert all(record["trace_sha256"] for record in result["records"])
