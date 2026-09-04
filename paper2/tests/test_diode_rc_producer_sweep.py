from experiments.mna import DIODE_RC_INSTANCES
from experiments.run_diode_rc_sweep import generate_sweep


def test_diode_profiles_are_three_distinct_executable_instances() -> None:
    assert len(DIODE_RC_INSTANCES) == 3
    assert len({instance.name for instance in DIODE_RC_INSTANCES}) == 3
    assert len({instance.resistance for instance in DIODE_RC_INSTANCES}) == 3
    assert len({instance.initial_voltage for instance in DIODE_RC_INSTANCES}) == 3


def test_reduced_diode_sweep_is_complete_and_unfiltered() -> None:
    rows, manifest = generate_sweep(steps_override=2)
    assert len(rows) == 3 * 2 * 4 * 4
    assert manifest["row_count"] == len(rows)
    assert manifest["incomplete_traces"] == 0
    assert manifest["eligible_reference_excluding_accepts"] == 0
    assert {row["producer_precision"] for row in rows} == {"float32", "float64"}
    assert {row["instance"] for row in rows} == {
        "nominal",
        "fast_load",
        "slow_hot_start",
    }
