"""Tests for bounded, atomic, secret-conscious remote status snapshots."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from researchclaw import remote_snapshot


def _fake_run(
    args: list[str] | tuple[str, ...], *, timeout: int = 15
) -> tuple[int, str]:
    del timeout
    command = list(args)
    if command[0] == "nvidia-smi" and "--query-gpu" in command[1]:
        return 0, "0, NVIDIA A800 80GB PCIe, 550.54, 10, 81920, 0, 40"
    if command[0] == "nvidia-smi":
        return 0, "123, 1024"
    if command[0] == "du":
        return 0, "1.0G\tfixture"
    if command[0] == "ps":
        return 0, "101 00:01 python\n102 00:02 bash"
    if command[-1] == "--version":
        return 0, "Python 3.12.13"
    return 127, "unavailable"


def _build_fixture(root: Path) -> None:
    result_dir = root / "paper1" / "runs" / "run-a" / "repo" / "paper1" / "results"
    result_dir.mkdir(parents=True)
    payload = {
        "status": "FAIL",
        "password": "must-not-appear",
        "claim_dataset_decision": {"decision": "STOP_TWO_DATASET_CLAIM"},
        "datasets": [
            {
                "dataset": "NYUv2",
                "image_count": 500,
                "eligible_pair_count": 105779,
                "gate_pass": True,
            }
        ],
    }
    (result_dir / "gate.json").write_text(json.dumps(payload), encoding="utf-8")
    steps = result_dir.parent / "steps"
    steps.mkdir()
    (steps / "README.md").write_text(
        "| step | status |\n| --- | --- |\n| 003 | STOP |\n", encoding="utf-8"
    )
    queue = root / "paper1" / "queue"
    queue.mkdir()
    connection = sqlite3.connect(queue / "state.sqlite")
    connection.execute(
        "CREATE TABLE tasks (task_id TEXT, status TEXT, attempts INTEGER)"
    )
    connection.execute("INSERT INTO tasks VALUES ('qa-pytest', 'PASSED', 1)")
    connection.commit()
    connection.close()
    env_python = root / "paper1" / "envs" / "py312" / "bin" / "python"
    env_python.parent.mkdir(parents=True)
    env_python.write_text("fixture", encoding="utf-8")
    (root / ".env").write_text("PASSWORD=must-not-appear", encoding="utf-8")


def test_snapshot_reports_results_and_filters_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "whr"
    root.mkdir()
    _build_fixture(root)
    output = root / "A800_STATUS.md"
    monkeypatch.setattr(remote_snapshot, "_run", _fake_run)
    monkeypatch.setattr(remote_snapshot.shutil, "which", lambda name: None)

    content = remote_snapshot.render_snapshot(root, output, 2, 10)

    assert "NVIDIA A800 80GB PCIe" in content
    assert "Python 3.12.13" in content
    assert "STOP_TWO_DATASET_CLAIM" in content
    assert "105779" in content
    assert "qa-pytest" in content
    assert "Checkpoints: 0" in content
    assert "must-not-appear" not in content
    assert str(tmp_path) not in content


def test_atomic_write_replaces_file_with_private_permissions(tmp_path: Path) -> None:
    output = tmp_path / "A800_STATUS.md"
    output.write_text("old", encoding="utf-8")

    digest = remote_snapshot.write_snapshot(tmp_path, output, "new\n")

    assert output.read_text(encoding="utf-8") == "new\n"
    assert oct(output.stat().st_mode & 0o777) == "0o600"
    assert digest == remote_snapshot.hashlib.sha256(b"new\n").hexdigest()


def test_atomic_write_failure_preserves_old_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "A800_STATUS.md"
    output.write_text("old", encoding="utf-8")

    def fail_replace(source: Path, destination: Path) -> None:
        del source, destination
        raise OSError("simulated replace failure")

    monkeypatch.setattr(remote_snapshot.os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated"):
        remote_snapshot.write_snapshot(tmp_path, output, "new")

    assert output.read_text(encoding="utf-8") == "old"
    assert not list(tmp_path.glob(".A800_STATUS.md.*.tmp"))


def test_validate_paths_rejects_symlink_output(tmp_path: Path) -> None:
    root = tmp_path / "whr"
    root.mkdir()
    target = root / "target.md"
    target.write_text("target", encoding="utf-8")
    output = root / "A800_STATUS.md"
    output.symlink_to(target)

    with pytest.raises(ValueError, match="must not be a symlink"):
        remote_snapshot._validate_paths(str(root), str(output))


def test_environment_path_hides_external_absolute_parent(tmp_path: Path) -> None:
    root = tmp_path / "whr"
    root.mkdir()

    assert (
        remote_snapshot._environment_display_path(Path("/home/shared/anaconda3"), root)
        == "<external>/anaconda3"
    )
