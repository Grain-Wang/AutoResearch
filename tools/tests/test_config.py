"""Tests for the compact toolbox configuration."""

from pathlib import Path

import pytest

from researchclaw.config import RCConfig


def _base_config() -> dict[str, object]:
    return {"research": {"topic": "test algorithm"}}


def test_minimal_config_uses_real_local_execution(tmp_path: Path) -> None:
    config = RCConfig.from_dict(_base_config(), project_root=tmp_path)

    assert config.research.topic == "test algorithm"
    assert config.experiment.mode == "sandbox"
    assert config.experiment.sandbox.python_path


@pytest.mark.parametrize("mode", ["simulated", "docker", "colab_drive"])
def test_removed_experiment_modes_are_rejected(tmp_path: Path, mode: str) -> None:
    raw = _base_config()
    raw["experiment"] = {"mode": mode}

    with pytest.raises(ValueError, match="experiment.mode"):
        RCConfig.from_dict(raw, project_root=tmp_path)


def test_removed_product_configuration_is_rejected(tmp_path: Path) -> None:
    raw = _base_config()
    raw["llm"] = {"provider": "hosted"}

    with pytest.raises(ValueError, match="unsupported keys"):
        RCConfig.from_dict(raw, project_root=tmp_path)


def test_ssh_configuration_limits_gpu_count(tmp_path: Path) -> None:
    raw = _base_config()
    raw["experiment"] = {
        "mode": "ssh_remote",
        "ssh_remote": {"host": "gpu-node", "gpu_ids": [0, 1, 2, 3, 4]},
    }

    with pytest.raises(ValueError, match="four GPUs"):
        RCConfig.from_dict(raw, project_root=tmp_path)


def test_ssh_configuration_rejects_unsafe_address(tmp_path: Path) -> None:
    raw = _base_config()
    raw["experiment"] = {
        "mode": "ssh_remote",
        "ssh_remote": {"host": "-oProxyCommand=bad"},
    }

    with pytest.raises(ValueError, match="must be safe"):
        RCConfig.from_dict(raw, project_root=tmp_path)
