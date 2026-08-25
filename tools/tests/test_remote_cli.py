"""Tests for strict remote command construction and dispatch."""

from pathlib import Path

from researchclaw.cli import build_parser
from researchclaw.remote_cli import _ssh_base
from researchclaw.remote_profile import RemoteProfile


def test_public_cli_exposes_explicit_remote_actions() -> None:
    parser = build_parser()

    args = parser.parse_args(["remote", "snapshot"])

    assert args.remote_action == "snapshot"
    assert args.profile == ".local-deps/ssh/a800.yaml"


def test_ssh_command_forces_key_only_strict_host_checking(tmp_path: Path) -> None:
    ssh_config = tmp_path / "config"
    ssh_config.write_text("Host gpu\n  HostName example.invalid\n", encoding="utf-8")
    profile = RemoteProfile(
        ssh_config=ssh_config,
        host="gpu",
        remote_python="~/whr/envs/py312/bin/python",
        root="~/whr",
        output="~/whr/A800_STATUS.md",
    )

    command = _ssh_base(profile)

    assert command[:3] == ["ssh", "-F", str(ssh_config)]
    assert "BatchMode=yes" in command
    assert "PasswordAuthentication=no" in command
    assert "KbdInteractiveAuthentication=no" in command
    assert "StrictHostKeyChecking=yes" in command
    assert "IdentitiesOnly=yes" in command
    assert "ClearAllForwardings=yes" in command
    assert command[-1] == "gpu"
    assert "StrictHostKeyChecking=no" not in command
