from experiments.generate_numerical_defects import generate_cases


def test_conditioning_sweep_exposes_residual_forward_error_gap() -> None:
    cases = generate_cases()
    assert len(cases) == 24
    assert all(case["producer_converged"] == "true" for case in cases)
    assert all(float(case["forward_error_inf"]) == 1.0 for case in cases)
    assert all(
        case["certificate_verdict"] == "REJECT_ROOT_OUTSIDE_TUBE" for case in cases
    )
