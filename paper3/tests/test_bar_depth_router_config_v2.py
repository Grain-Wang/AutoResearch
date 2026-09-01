from __future__ import annotations

import copy
from pathlib import Path

import pytest
from paper3.experiments.bar_depth.router_contract_v2 import (
    load_router_config_v2,
    validate_router_config_v2,
)

CONFIG_PATH = Path("paper3/configs/bar_depth/router_probe_v2.json")


def test_router_probe_v2_is_objective_and_risk_aligned() -> None:
    config = load_router_config_v2(CONFIG_PATH)
    assert (
        config["objective"]["training_target"]["denominator"]
        == "image_base_primary_error_sum"
    )
    assert config["risk"]["max_event_probability"] == 0.1
    assert config["calibration"]["threshold_grid"]["count"] == 101


def test_router_probe_v2_rejects_region_varying_denominator() -> None:
    config = load_router_config_v2(CONFIG_PATH)
    invalid = copy.deepcopy(config)
    invalid["objective"]["training_target"]["denominator"] = "weight_sum"
    with pytest.raises(ValueError, match="rank-preserving image denominator"):
        validate_router_config_v2(invalid)


def test_router_probe_v2_rejects_missing_risk_bound() -> None:
    config = load_router_config_v2(CONFIG_PATH)
    invalid = copy.deepcopy(config)
    invalid["risk"]["upper_bound"] = "point_estimate"
    with pytest.raises(ValueError, match="one-sided upper bound"):
        validate_router_config_v2(invalid)


def test_router_probe_v2_rejects_short_threshold_grid() -> None:
    config = load_router_config_v2(CONFIG_PATH)
    invalid = copy.deepcopy(config)
    invalid["calibration"]["threshold_grid"]["count"] = 11
    with pytest.raises(ValueError, match="101 quantiles"):
        validate_router_config_v2(invalid)


def test_router_probe_v2_rejects_missing_fallback() -> None:
    config = load_router_config_v2(CONFIG_PATH)
    invalid = copy.deepcopy(config)
    invalid["calibration"]["fallback_when_no_threshold_is_feasible"] = "top_one"
    with pytest.raises(ValueError, match="abstain-all fallback"):
        validate_router_config_v2(invalid)
