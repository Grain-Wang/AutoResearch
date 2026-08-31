from experiments.run_next_round_gate import run_gate


def test_next_round_gate_keeps_canary_and_paper_claims_separate() -> None:
    result = run_gate()
    assert result["m0"]["status"] == "PASS-CANARY"
    assert result["m1"]["claim_i"] == "IMPLEMENTATION-CANARY-PASS"
    assert result["m1"]["status"] == "ITERATE"
    assert result["m2"]["status"] == "NOT-STARTED"
    assert result["paper_candidate"] == "FAIL-UNVERIFIED"
    assert "B2_STRONG_UNIMPLEMENTED" in result["blockers"]
