"""Tests for honest local and SSH experiment execution."""

import sys
from pathlib import Path

from researchclaw.config import SandboxConfig, SshRemoteConfig
from researchclaw.experiment.sandbox import ExperimentSandbox, parse_metrics
from researchclaw.experiment.ssh_sandbox import SshRemoteSandbox


def test_parse_metrics_keeps_only_finite_scalars() -> None:
    metrics = parse_metrics(
        "accuracy: 0.91\nloss: nan\ncondition=hard seed=0 f1: 0.7\ninfo: 3\n"
    )

    assert metrics == {"accuracy": 0.91, "hard/f1": 0.7, "f1": 0.7}


def test_local_project_runs_real_python_and_preserves_metrics(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text(
        "from pathlib import Path\n"
        "Path('proof.txt').write_text('real', encoding='utf-8')\n"
        "print('score: 0.75')\n",
        encoding="utf-8",
    )
    sandbox = ExperimentSandbox(SandboxConfig(sys.executable), tmp_path / "runs")

    result = sandbox.run_project(project)

    assert result.returncode == 0
    assert result.metrics == {"score": 0.75}
    assert list((tmp_path / "runs").glob("project-*/proof.txt"))


def test_local_project_rejects_symlinks(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("print('score: 1')", encoding="utf-8")
    (project / "escape").symlink_to(tmp_path)
    sandbox = ExperimentSandbox(SandboxConfig(sys.executable), tmp_path / "runs")

    result = sandbox.run_project(project)

    assert result.returncode == -1
    assert "symlink" in result.stderr


def test_ssh_command_requires_batch_mode_without_disabling_host_keys() -> None:
    config = SshRemoteConfig(host="gpu-node", user="researcher")

    command = SshRemoteSandbox._ssh_base(config)

    assert "BatchMode=yes" in command
    assert not any("StrictHostKeyChecking" in item for item in command)
    assert command[-1] == "researcher@gpu-node"
