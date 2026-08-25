"""Tests for private remote profile validation."""

from pathlib import Path

import pytest

from researchclaw.remote_profile import RemoteProfile


def _write_profile(tmp_path: Path, body: str) -> Path:
    ssh_config = tmp_path / "config"
    ssh_config.write_text("Host gpu\n  HostName example.invalid\n", encoding="utf-8")
    profile = tmp_path / "profile.yaml"
    profile.write_text(body, encoding="utf-8")
    return profile


def test_profile_resolves_private_ssh_config(tmp_path: Path) -> None:
    profile_path = _write_profile(
        tmp_path,
        """version: 1
ssh:
  config: config
  host: gpu
snapshot:
  remote_python: ~/whr/paper1/envs/py312/bin/python
  root: ~/whr
  output: ~/whr/A800_STATUS.md
""",
    )

    profile = RemoteProfile.load(profile_path)

    assert profile.ssh_config == (tmp_path / "config").resolve()
    assert profile.host == "gpu"
    assert profile.root == "~/whr"
    assert profile.output == "~/whr/A800_STATUS.md"


def test_profile_rejects_output_outside_root(tmp_path: Path) -> None:
    profile_path = _write_profile(
        tmp_path,
        """version: 1
ssh:
  config: config
  host: gpu
snapshot:
  remote_python: /usr/bin/python3
  root: ~/whr
  output: ~/outside/status.md
""",
    )

    with pytest.raises(ValueError, match="below snapshot.root"):
        RemoteProfile.load(profile_path)


def test_profile_rejects_unsafe_host_alias(tmp_path: Path) -> None:
    profile_path = _write_profile(
        tmp_path,
        """version: 1
ssh:
  config: config
  host: -oProxyCommand=bad
snapshot:
  remote_python: /usr/bin/python3
  root: ~/whr
  output: ~/whr/status.md
""",
    )

    with pytest.raises(ValueError, match="safe OpenSSH alias"):
        RemoteProfile.load(profile_path)
