"""Tests for the cooperative GPU queue."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from researchclaw.gpu_queue.gpu import GpuSnapshot, IdleTracker, probe_gpus
from researchclaw.gpu_queue.models import QueueConfig
from researchclaw.gpu_queue.scheduler import QueueScheduler, evaluate_gate
from researchclaw.gpu_queue.state import QueueRunLock, QueueState, TaskStatus


def _write_config(
    tmp_path: Path,
    tasks: list[dict[str, object]],
    *,
    idle_samples: int = 1,
    max_parallel_gpu_tasks: int = 2,
    report_path: Path | None = None,
) -> Path:
    path = tmp_path / "queue.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_root": str(tmp_path / "runs"),
                **(
                    {"report_path": str(report_path)} if report_path is not None else {}
                ),
                "scheduler": {
                    "poll_interval_seconds": 0.01,
                    "idle_samples": idle_samples,
                    "memory_used_limit_mib": 1024,
                    "utilization_limit_percent": 5,
                    "max_parallel_gpu_tasks": max_parallel_gpu_tasks,
                    "max_parallel_cpu_tasks": 2,
                    "random_backoff_seconds": 0,
                    "shared_memory_reserve_mib": 4096,
                },
                "tasks": tasks,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _python_write_task(
    task_id: str,
    output: str,
    *,
    gpu_count: int = 0,
    depends_on: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": task_id,
        "command": [
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({output!r}).write_text('ok')",
        ],
        "cwd": ".",
        "gpu_count": gpu_count,
        "depends_on": depends_on or [],
        "required_outputs": [output],
        "timeout_seconds": 10,
    }


def _idle_gpu(index: int) -> GpuSnapshot:
    return GpuSnapshot(
        index=index,
        uuid=f"GPU-{index}",
        memory_used_mib=10,
        utilization_percent=0,
        memory_total_mib=81920,
        memory_free_mib=81910,
    )


def _busy_gpu(index: int, *, memory_free_mib: int) -> GpuSnapshot:
    return GpuSnapshot(
        index=index,
        uuid=f"GPU-{index}",
        memory_used_mib=81920 - memory_free_mib,
        utilization_percent=100,
        memory_total_mib=81920,
        memory_free_mib=memory_free_mib,
        compute_pids=(1000 + index,),
    )


def test_queue_config_validates_graph_and_filters_disabled(tmp_path: Path) -> None:
    tasks = [
        _python_write_task("first", "first.txt"),
        _python_write_task("second", "second.txt", depends_on=["first"]),
        {**_python_write_task("disabled", "disabled.txt"), "enabled": False},
    ]
    config = QueueConfig.load(_write_config(tmp_path, tasks))

    assert tuple(task.task_id for task in config.tasks) == ("first", "second")
    assert config.resolve_task_cwd(config.tasks[0]) == tmp_path


def test_queue_config_rejects_cycles(tmp_path: Path) -> None:
    tasks = [
        _python_write_task("first", "first.txt", depends_on=["second"]),
        _python_write_task("second", "second.txt", depends_on=["first"]),
    ]

    with pytest.raises(ValueError, match="dependency cycle"):
        QueueConfig.load(_write_config(tmp_path, tasks))


def test_queue_config_rejects_multigpu_task(tmp_path: Path) -> None:
    task = _python_write_task("bad", "bad.txt")
    task["gpu_count"] = 2

    with pytest.raises(ValueError, match="gpu_count must be 0 or 1"):
        QueueConfig.load(_write_config(tmp_path, [task]))


def test_probe_gpus_joins_processes_by_uuid() -> None:
    outputs = (
        "0, GPU-a, 81920, 500, 81420, 2\n" "1, GPU-b, 81920, 2000, 79920, 7\n",
        "GPU-b, 123\nGPU-b, 456\n",
    )
    with patch("researchclaw.gpu_queue.gpu._run_nvidia_smi", side_effect=outputs):
        snapshots = probe_gpus()

    assert snapshots[0].compute_pids == ()
    assert snapshots[1].compute_pids == (123, 456)
    assert snapshots[0].memory_total_mib == 81920
    assert snapshots[1].memory_free_mib == 79920


def test_shared_gpu_task_requires_declared_memory(tmp_path: Path) -> None:
    task = _python_write_task("shared", "result.txt", gpu_count=1)
    task["allocation_mode"] = "shared"

    with pytest.raises(ValueError, match="requires memory_required_mib"):
        QueueConfig.load(_write_config(tmp_path, [task]))


def test_comparison_group_requires_shared_and_exclusive_pair(tmp_path: Path) -> None:
    task = _python_write_task("shared", "result.txt", gpu_count=1)
    task.update(
        allocation_mode="shared",
        memory_required_mib=1024,
        comparison_group="experiment",
    )

    with pytest.raises(ValueError, match="requires exactly one shared"):
        QueueConfig.load(_write_config(tmp_path, [task]))


def test_idle_tracker_requires_consecutive_samples() -> None:
    tracker = IdleTracker(required_samples=2)
    idle = (_idle_gpu(0),)
    busy = (
        GpuSnapshot(
            index=0,
            uuid="GPU-0",
            memory_used_mib=10,
            utilization_percent=0,
            compute_pids=(123,),
        ),
    )

    assert (
        tracker.observe(idle, memory_used_limit_mib=1024, utilization_limit_percent=5)
        == ()
    )
    assert tracker.observe(
        idle, memory_used_limit_mib=1024, utilization_limit_percent=5
    ) == (0,)
    assert (
        tracker.observe(busy, memory_used_limit_mib=1024, utilization_limit_percent=5)
        == ()
    )
    assert (
        tracker.observe(idle, memory_used_limit_mib=1024, utilization_limit_percent=5)
        == ()
    )


def test_evaluate_gate_uses_dotted_json_field(tmp_path: Path) -> None:
    artifact = tmp_path / "gate.json"
    artifact.write_text('{"decision": {"status": "PASS"}}', encoding="utf-8")
    task = {
        **_python_write_task("gate", "done.txt"),
        "gate": {
            "artifact": str(artifact),
            "field": "decision.status",
            "equals": "PASS",
        },
    }
    gate = QueueConfig.load(_write_config(tmp_path, [task])).tasks[0].gate
    assert gate is not None

    assert evaluate_gate(artifact, gate) == (True, None)


def test_state_rejects_changed_passed_task(tmp_path: Path) -> None:
    config = QueueConfig.load(
        _write_config(tmp_path, [_python_write_task("task", "done.txt")])
    )
    with QueueState(tmp_path / "state.sqlite") as state:
        state.register_tasks(config.tasks)
        state.mark_terminal(
            "task", TaskStatus.PASSED, exit_code=0, error=None, output_hashes={}
        )
        changed = _python_write_task("task", "other.txt")
        changed_config = QueueConfig.load(_write_config(tmp_path, [changed]))
        with pytest.raises(ValueError, match="changed after reaching PASSED"):
            state.register_tasks(changed_config.tasks)


def test_queue_run_lock_rejects_second_scheduler(tmp_path: Path) -> None:
    state_path = tmp_path / "state.sqlite"

    with (
        QueueRunLock(state_path),
        pytest.raises(RuntimeError, match="another scheduler"),
        QueueRunLock(state_path),
    ):
        pass


def test_explicit_retry_preserves_attempt_number(tmp_path: Path) -> None:
    config = QueueConfig.load(
        _write_config(tmp_path, [_python_write_task("task", "done.txt")])
    )
    with QueueState(tmp_path / "state.sqlite") as state:
        state.register_tasks(config.tasks)
        state.mark_running(
            "task",
            gpu_index=None,
            worker_pid=999_999_999,
            worker_pgid=999_999_999,
            run_dir=tmp_path / "attempt-001",
            command=config.tasks[0].command,
            commit_sha=None,
        )
        state.mark_terminal("task", TaskStatus.FAILED, exit_code=1, error="failed")
        state.retry("task")
        record = state.record("task")

    assert record.status is TaskStatus.PENDING
    assert record.attempts == 1


def test_scheduler_runs_cpu_dependencies_and_hashes_outputs(tmp_path: Path) -> None:
    config = QueueConfig.load(
        _write_config(
            tmp_path,
            [
                _python_write_task("first", "first.txt"),
                _python_write_task("second", "second.txt", depends_on=["first"]),
            ],
        )
    )
    with QueueState(tmp_path / "state.sqlite") as state:
        scheduler = QueueScheduler(config, state, sleep=lambda _seconds: None)
        assert scheduler.run() == 0
        records = state.records()

    assert tuple(record.status for record in records) == (
        TaskStatus.PASSED,
        TaskStatus.PASSED,
    )
    assert json.loads(records[0].output_hashes_json or "{}")


def test_scheduler_atomically_writes_private_markdown_report(tmp_path: Path) -> None:
    report_path = tmp_path / "GPU_EXPERIMENT_STATUS.md"
    config = QueueConfig.load(
        _write_config(
            tmp_path,
            [_python_write_task("experiment", "result.json")],
            report_path=report_path,
        )
    )
    with QueueState(tmp_path / "state.sqlite") as state:
        scheduler = QueueScheduler(config, state, sleep=lambda _seconds: None)
        initial_report = report_path.read_text(encoding="utf-8")
        assert "**WAITING**" in initial_report
        assert "Run directory: not created yet" in initial_report

        assert scheduler.run() == 0

    final_report = report_path.read_text(encoding="utf-8")
    assert "**PASSED**" in final_report
    assert "| experiment | - | - | - | PASSED | 1 |" in final_report
    assert "allocation.json" in final_report
    assert "stdout.log" in final_report
    assert "result.json" in final_report
    assert "SHA256" in final_report
    assert "write_text('ok')" not in final_report
    assert oct(report_path.stat().st_mode & 0o777) == "0o600"


def test_scheduler_assigns_physical_gpu_in_environment(tmp_path: Path) -> None:
    output = "assigned-gpu.txt"
    task = {
        "id": "gpu-task",
        "command": [
            sys.executable,
            "-c",
            (
                "import os; from pathlib import Path; "
                f"Path({output!r}).write_text(os.environ['CUDA_VISIBLE_DEVICES'])"
            ),
        ],
        "cwd": ".",
        "gpu_count": 1,
        "required_outputs": [output],
        "timeout_seconds": 10,
    }
    config = QueueConfig.load(_write_config(tmp_path, [task]))
    with QueueState(tmp_path / "state.sqlite") as state:
        scheduler = QueueScheduler(
            config,
            state,
            gpu_probe=lambda: (_idle_gpu(2),),
            sleep=lambda _seconds: None,
            random_uniform=lambda _low, _high: 0,
        )
        assert scheduler.run() == 0
        record = state.record("gpu-task")

    assert record.gpu_index == 2
    assert (tmp_path / output).read_text(encoding="utf-8") == "2"


def test_scheduler_runs_shared_and_exclusive_comparison_separately(
    tmp_path: Path,
) -> None:
    tasks: list[dict[str, object]] = []
    command = [
        sys.executable,
        "-c",
        (
            "import os; from pathlib import Path; "
            "Path(os.environ['RESEARCHCLAW_RUN_DIR'], 'result.txt').write_text("
            "os.environ['RESEARCHCLAW_GPU_ALLOCATION_MODE'])"
        ),
    ]
    for mode in ("shared", "exclusive"):
        task = {
            "id": f"experiment-{mode}",
            "command": command,
            "cwd": ".",
            "gpu_count": 1,
            "allocation_mode": mode,
            "memory_required_mib": 1024,
            "comparison_group": "experiment",
            "run_outputs": ["result.txt"],
            "timeout_seconds": 10,
        }
        tasks.append(task)
    config = QueueConfig.load(_write_config(tmp_path, tasks))
    snapshots = (_busy_gpu(0, memory_free_mib=30000), _idle_gpu(1))
    with QueueState(tmp_path / "state.sqlite") as state:
        scheduler = QueueScheduler(
            config,
            state,
            gpu_probe=lambda: snapshots,
            sleep=lambda _seconds: None,
            random_uniform=lambda _low, _high: 0,
        )
        assert scheduler.run() == 0
        records = {record.task_id: record for record in state.records()}

    assert records["experiment-shared"].gpu_index == 0
    assert records["experiment-exclusive"].gpu_index == 1
    shared_run_dir = Path(records["experiment-shared"].run_dir or "")
    exclusive_run_dir = Path(records["experiment-exclusive"].run_dir or "")
    assert (shared_run_dir / "result.txt").read_text(encoding="utf-8") == "shared"
    assert (exclusive_run_dir / "result.txt").read_text(encoding="utf-8") == "exclusive"
    shared_allocation = json.loads(
        (shared_run_dir / "allocation.json").read_text(encoding="utf-8")
    )
    assert shared_allocation["coexisting_compute_process_count"] == 1
    assert shared_allocation["memory_free_mib"] == 30000
    assert oct(shared_run_dir.stat().st_mode & 0o777) == "0o700"
    for private_file in (
        shared_run_dir / "allocation.json",
        shared_run_dir / "result.txt",
        shared_run_dir / "stdout.log",
        shared_run_dir / "stderr.log",
        shared_run_dir / "completion.json",
    ):
        assert oct(private_file.stat().st_mode & 0o777) == "0o600"


def test_shared_task_waits_when_free_memory_lacks_reserve(tmp_path: Path) -> None:
    task = _python_write_task("shared", "result.txt", gpu_count=1)
    task.update(allocation_mode="shared", memory_required_mib=8192)
    config = QueueConfig.load(_write_config(tmp_path, [task]))
    with QueueState(tmp_path / "state.sqlite") as state:
        scheduler = QueueScheduler(
            config,
            state,
            gpu_probe=lambda: (_busy_gpu(0, memory_free_mib=12000),),
            sleep=lambda _seconds: None,
            random_uniform=lambda _low, _high: 0,
        )
        assert scheduler.tick() is False
        assert state.record("shared").status is TaskStatus.PENDING


def test_scheduler_limits_parallel_gpu_tasks_to_two(tmp_path: Path) -> None:
    tasks = [
        _python_write_task(f"gpu-{index}", f"gpu-{index}.txt", gpu_count=1)
        for index in range(3)
    ]
    config = QueueConfig.load(_write_config(tmp_path, tasks))
    with QueueState(tmp_path / "state.sqlite") as state:
        scheduler = QueueScheduler(
            config,
            state,
            gpu_probe=lambda: (_idle_gpu(0), _idle_gpu(1), _idle_gpu(2)),
            sleep=lambda _seconds: None,
            random_uniform=lambda _low, _high: 0,
        )
        assert scheduler.tick() is False
        statuses = tuple(record.status for record in state.records())
        assert statuses.count(TaskStatus.RUNNING) == 2
        assert statuses.count(TaskStatus.PENDING) == 1
        assert scheduler.run() == 0


def test_failed_gate_blocks_dependant_task(tmp_path: Path) -> None:
    gate_command = (
        "from pathlib import Path; "
        "Path('gate.json').write_text('{\"status\": \"STOP\"}')"
    )
    gate_task: dict[str, object] = {
        "id": "gate",
        "command": [sys.executable, "-c", gate_command],
        "cwd": ".",
        "gpu_count": 0,
        "required_outputs": ["gate.json"],
        "gate": {"artifact": "gate.json", "field": "status", "equals": "PASS"},
    }
    dependent = _python_write_task(
        "dependent", "should-not-exist.txt", depends_on=["gate"]
    )
    config = QueueConfig.load(_write_config(tmp_path, [gate_task, dependent]))
    with QueueState(tmp_path / "state.sqlite") as state:
        scheduler = QueueScheduler(config, state, sleep=lambda _seconds: None)
        assert scheduler.run() == 1
        records = state.records()

    assert records[0].status is TaskStatus.FAILED
    assert records[1].status is TaskStatus.BLOCKED
    assert not (tmp_path / "should-not-exist.txt").exists()


def test_scheduler_recovers_finished_worker_without_relaunch(tmp_path: Path) -> None:
    config = QueueConfig.load(
        _write_config(tmp_path, [_python_write_task("task", "done.txt")])
    )
    run_dir = tmp_path / "runs" / "task" / "attempt-001"
    run_dir.mkdir(parents=True)
    (tmp_path / "done.txt").write_text("ok", encoding="utf-8")
    (run_dir / "completion.json").write_text('{"exit_code": 0}', encoding="utf-8")
    with QueueState(tmp_path / "state.sqlite") as state:
        state.register_tasks(config.tasks)
        state.mark_running(
            "task",
            gpu_index=None,
            worker_pid=999_999_999,
            worker_pgid=999_999_999,
            run_dir=run_dir,
            command=config.tasks[0].command,
            commit_sha=None,
        )
        scheduler = QueueScheduler(config, state, sleep=lambda _seconds: None)
        assert scheduler.tick() is True
        record = state.record("task")

    assert record.status is TaskStatus.PASSED
    assert record.attempts == 1


def test_drain_preserves_pending_tasks(tmp_path: Path) -> None:
    config = QueueConfig.load(
        _write_config(tmp_path, [_python_write_task("task", "done.txt")])
    )
    with QueueState(tmp_path / "state.sqlite") as state:
        scheduler = QueueScheduler(config, state)
        state.request_drain()
        assert scheduler.tick() is True
        assert state.record("task").status is TaskStatus.PENDING


def test_worker_timeout_writes_completion(tmp_path: Path) -> None:
    from researchclaw.gpu_queue.worker import run_worker

    spec = tmp_path / "spec.json"
    completion = tmp_path / "completion.json"
    spec.write_text(
        json.dumps(
            {
                "command": [sys.executable, "-c", "import time; time.sleep(5)"],
                "cwd": str(tmp_path),
                "env": {},
                "timeout_seconds": 1,
            }
        ),
        encoding="utf-8",
    )

    assert run_worker(spec, completion) == 124
    assert json.loads(completion.read_text(encoding="utf-8"))["timed_out"] is True


def test_cli_dry_run_does_not_create_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from researchclaw.cli import main

    config_path = _write_config(tmp_path, [_python_write_task("task", "done.txt")])
    state_path = tmp_path / "missing.sqlite"

    assert (
        main(
            [
                "gpu-queue",
                "run",
                "--config",
                str(config_path),
                "--state",
                str(state_path),
                "--dry-run",
            ]
        )
        == 0
    )
    assert "GPU policy" in capsys.readouterr().out
    assert not state_path.exists()


def test_cli_stop_sets_drain_flag(tmp_path: Path) -> None:
    from researchclaw.cli import main

    state_path = tmp_path / "state.sqlite"
    with QueueState(state_path):
        pass

    assert main(["gpu-queue", "stop", "--state", str(state_path)]) == 0
    with QueueState(state_path) as state:
        assert state.drain_requested() is True


def test_gpu_snapshot_rejects_threshold_boundaries() -> None:
    snapshot = GpuSnapshot(
        index=0,
        uuid="GPU-0",
        memory_used_mib=1024,
        utilization_percent=5,
    )

    assert not snapshot.is_idle(memory_used_limit_mib=1024, utilization_limit_percent=5)


def test_worker_environment_does_not_mutate_parent(tmp_path: Path) -> None:
    output = "worker-env.txt"
    task = _python_write_task("task", output)
    task["env"] = {"GPU_QUEUE_TEST_VARIABLE": "child"}
    config = QueueConfig.load(_write_config(tmp_path, [task]))
    original = os.environ.get("GPU_QUEUE_TEST_VARIABLE")
    with QueueState(tmp_path / "state.sqlite") as state:
        scheduler = QueueScheduler(config, state, sleep=lambda _seconds: None)
        assert scheduler.run() == 0
        run_dir = Path(state.record("task").run_dir or "")

    assert os.environ.get("GPU_QUEUE_TEST_VARIABLE") == original
    worker_spec = json.loads((run_dir / "worker-spec.json").read_text(encoding="utf-8"))
    assert worker_spec["env"] == {}
    assert worker_spec["env_keys"] == [
        "GPU_QUEUE_TEST_VARIABLE",
        "RESEARCHCLAW_RUN_DIR",
    ]
