from __future__ import annotations

import copy
from pathlib import Path

import pytest
from paper3.experiments.bar_depth.router_contract import (
    load_router_config,
    validate_router_config,
)

CONFIG_PATH = Path("paper3/configs/bar_depth/router_probe_v1.json")


def test_router_probe_config_is_complete() -> None:
    config = load_router_config(CONFIG_PATH)
    assert config["actions"]["primary_budget_count"] == 3
    assert config["bootstrap"]["replicates"] == 10000
    assert config["gate"]["absrel_safety_statistic"] == "paired_ci_upper"


def test_router_probe_rejects_train_evaluation_alias() -> None:
    config = load_router_config(CONFIG_PATH)
    invalid = copy.deepcopy(config)
    invalid["dataset"]["train_partition"] = invalid["dataset"]["evaluation_partition"]
    with pytest.raises(ValueError, match="partitions must differ"):
        validate_router_config(invalid)


def test_router_probe_rejects_leaky_feature() -> None:
    config = load_router_config(CONFIG_PATH)
    invalid = copy.deepcopy(config)
    invalid["features"]["allowlist"].append("primary_utility")
    with pytest.raises(ValueError, match="features overlap"):
        validate_router_config(invalid)


def test_router_probe_rejects_point_only_safety_gate() -> None:
    config = load_router_config(CONFIG_PATH)
    invalid = copy.deepcopy(config)
    invalid["gate"]["absrel_safety_statistic"] = "point_estimate"
    with pytest.raises(ValueError, match="paired CI upper bound"):
        validate_router_config(invalid)


def test_router_probe_rejects_out_of_range_budget() -> None:
    config = load_router_config(CONFIG_PATH)
    invalid = copy.deepcopy(config)
    invalid["actions"]["budget_counts"].append(13)
    with pytest.raises(ValueError, match="candidate action space"):
        validate_router_config(invalid)
