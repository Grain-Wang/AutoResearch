from experiments.benchmark import METHODS, RESULT_COLUMNS
from experiments.run_component_ladder import run_component_ladder


def test_component_ladder_has_all_methods_and_matching_shared_hashes() -> None:
    rows, manifest, fairness = run_component_ladder(
        steps=2,
        slab_lengths=(1,),
        replicates=1,
        circuit_filter="diode_rc",
    )
    assert len(rows) == 3 * len(METHODS)
    assert all(set(RESULT_COLUMNS) <= row.keys() for row in rows)
    assert set(row["method"] for row in rows) == set(METHODS)
    assert manifest["coverage_complete"] is True
    assert manifest["success_only_filtering"] is False
    assert manifest["confirmed_false_accepts"] == 0
    assert fairness["strong_baseline_status"] == "IMPLEMENTED"
    assert fairness["all_required_hashes_present"] is True
    assert fairness["all_shared_hashes_match"] is True


def test_component_ladder_preserves_unknown_rows() -> None:
    rows, manifest, _ = run_component_ladder(
        steps=3,
        slab_lengths=(2,),
        replicates=1,
        circuit_filter="nmos_ring_3stage",
    )
    assert len(rows) == 3 * len(METHODS)
    assert manifest["row_count"] == len(rows)
    assert sum(manifest["verdict_counts"].values()) == len(rows)
