import hashlib
import json
from fractions import Fraction

from experiments.generate_numerical_defects import (
    ProducerPrecision,
    build_case,
    exact_diagonal_oracle,
    generate_cases,
    write_cases,
)
from experiments.interval_backend import Interval


def test_conditioning_sweep_uses_real_producer_oracle_and_checker() -> None:
    cases = generate_cases()
    assert len(cases) == 24
    assert all(case["producer_converged"] == "true" for case in cases)
    assert all(case["producer_iterations"] == "0" for case in cases)
    assert all(case["oracle_root_in_tube"] == "false" for case in cases)
    assert all(case["oracle_forward_error_inf"] == "1" for case in cases)
    assert all(case["checker_verdict"] == "UNKNOWN" for case in cases)
    assert all(case["false_accept"] == "false" for case in cases)
    assert all("certificate_verdict" not in case for case in cases)


def test_float32_and_float64_paths_use_distinct_binary_values() -> None:
    cases = generate_cases()
    paired = {
        (case["epsilon_requested"], case["producer_precision"]): case for case in cases
    }
    assert any(
        paired[(f"1e-{exponent}", "float32")]["epsilon_used_hex"]
        != paired[(f"1e-{exponent}", "float64")]["epsilon_used_hex"]
        for exponent in range(5, 17)
    )
    assert {case["producer_precision"] for case in cases} == {
        "float32",
        "float64",
    }


def test_strict_threshold_executes_newton_update_and_checker_accepts() -> None:
    for precision in (ProducerPrecision.FLOAT32, ProducerPrecision.FLOAT64):
        case = build_case(8, precision, residual_threshold=0.0)
        assert case["producer_iterations"] == "1"
        assert case["producer_converged"] == "true"
        assert case["oracle_root_in_tube"] == "true"
        assert case["oracle_forward_error_inf"] == "0"
        assert case["checker_verdict"] == "ACCEPT"
        assert case["false_accept"] == "false"


def test_exact_oracle_derives_nontrivial_roots_from_declared_inputs() -> None:
    oracle = exact_diagonal_oracle(
        (2.0, 3.0),
        (1.0, 1.0),
        (0.5, 0.25),
        (Interval(0.49, 0.51), Interval(0.32, 0.34)),
    )
    assert oracle.root == (Fraction(1, 2), Fraction(1, 3))
    assert oracle.root_in_tube
    assert oracle.forward_error_inf == Fraction(1, 12)


def test_writer_rebuilds_csv_and_provenance(tmp_path) -> None:
    output = tmp_path / "cases.csv"
    csv_path, metadata_path = write_cases(output, seed=29)
    first_csv = csv_path.read_bytes()
    first_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    write_cases(output, seed=29)
    assert output.read_bytes() == first_csv
    second_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert {
        key: value for key, value in first_metadata.items() if key != "generated_at_utc"
    } == {
        key: value
        for key, value in second_metadata.items()
        if key != "generated_at_utc"
    }

    metadata = second_metadata
    assert metadata["status"] == "PASS"
    assert metadata["seed"] == 29
    assert metadata["randomness_used"] is False
    assert metadata["row_count"] == 24
    assert metadata["csv_sha256"] == hashlib.sha256(first_csv).hexdigest()
    assert metadata["oracle"].startswith("fractions.Fraction")
    assert metadata["strict_threshold_controls"] == {
        "all_checker_accept": True,
        "all_performed_one_update": True,
        "all_roots_in_tube": True,
        "cases": 2,
        "false_accepts": 0,
    }
    assert set(metadata["source_files_sha256"]) == {
        "experiments/blockstamp_operator.py",
        "experiments/checkers/pointwise_krawczyk.py",
        "experiments/generate_numerical_defects.py",
        "experiments/interval_backend.py",
        "experiments/provenance.py",
        "experiments/rigorous_backend.py",
    }
