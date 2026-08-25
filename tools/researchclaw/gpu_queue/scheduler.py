"""Gate-aware cooperative scheduler for unattended GPU experiments."""

from __future__ import annotations

import hashlib
import json
import os
import random
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path

from researchclaw.gpu_queue.gpu import GpuSnapshot, IdleTracker, probe_gpus
from researchclaw.gpu_queue.models import (
    GateCondition,
    GpuAllocationMode,
    QueueConfig,
    TaskConfig,
)
from researchclaw.gpu_queue.report import write_queue_report
from researchclaw.gpu_queue.state import (
    TERMINAL_STATUSES,
    QueueState,
    TaskRecord,
    TaskStatus,
    process_is_alive,
)

GpuProbe = Callable[[], tuple[GpuSnapshot, ...]]


def render_queue_plan(config: QueueConfig) -> str:
    """Render an executable DAG without creating scheduler state."""

    lines = [
        f"Queue: {config.source_path}",
        f"Run root: {config.run_root}",
        (
            "GPU policy: "
            f"{config.scheduler.idle_samples} samples x "
            f"{config.scheduler.poll_interval_seconds:g}s, "
            f"max {config.scheduler.max_parallel_gpu_tasks} tasks"
        ),
    ]
    if config.report_path is not None:
        lines.append(f"Report: {config.report_path}")
    for task in config.tasks:
        if task.gpu_count == 0:
            resource = "CPU"
        else:
            mode = task.allocation_mode or GpuAllocationMode.EXCLUSIVE
            memory = (
                ""
                if task.memory_required_mib is None
                else f", {task.memory_required_mib} MiB requested"
            )
            resource = f"1 GPU ({mode.value}{memory})"
        dependencies = ",".join(task.depends_on) or "none"
        command = " ".join(config.expanded_command(task))
        lines.append(
            f"- {task.task_id}: {resource}; depends={dependencies}; command={command}"
        )
    return "\n".join(lines)


def sha256_path(path: Path) -> str:
    """Hash a file or a directory tree deterministically."""

    digest = hashlib.sha256()
    if path.is_file():
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    if path.is_dir():
        for item in sorted(
            candidate for candidate in path.rglob("*") if candidate.is_file()
        ):
            digest.update(str(item.relative_to(path)).encode("utf-8"))
            digest.update(b"\0")
            with item.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
        return digest.hexdigest()
    raise FileNotFoundError(path)


def _dotted_value(payload: object, field: str) -> object:
    current = payload
    for component in field.split("."):
        if not isinstance(current, Mapping) or component not in current:
            raise KeyError(field)
        current = current[component]
    return current


def evaluate_gate(path: Path, gate: GateCondition) -> tuple[bool, str | None]:
    """Evaluate a JSON gate artifact against its frozen expected value."""

    if not path.is_file():
        return False, f"gate artifact is missing: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        actual = _dotted_value(payload, gate.field)
    except (OSError, ValueError, KeyError) as error:
        return False, f"gate artifact is invalid: {error}"
    if actual != gate.equals:
        return (
            False,
            f"gate {gate.field} expected {gate.equals!r}, observed {actual!r}",
        )
    return True, None


def _git_commit(cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


class QueueScheduler:
    """Run a durable dependency graph on conservatively selected GPUs."""

    def __init__(
        self,
        config: QueueConfig,
        state: QueueState,
        *,
        gpu_probe: GpuProbe = probe_gpus,
        sleep: Callable[[float], None] = time.sleep,
        random_uniform: Callable[[float, float], float] = random.uniform,
    ) -> None:
        self.config = config
        self.state = state
        self.gpu_probe = gpu_probe
        self.sleep = sleep
        self.random_uniform = random_uniform
        self.tasks = config.task_map()
        self.task_order = tuple(self.tasks)
        self.idle_tracker = IdleTracker(config.scheduler.idle_samples)
        self._workers: dict[int, subprocess.Popen[bytes]] = {}
        self.state.register_tasks(config.tasks)
        self._write_report()

    def render_plan(self) -> str:
        """Render the executable DAG without launching tasks."""

        return render_queue_plan(self.config)

    def _record_map(self) -> dict[str, TaskRecord]:
        return {
            record.task_id: record for record in self.state.records(self.task_order)
        }

    def _write_report(self) -> None:
        if self.config.report_path is None:
            return
        write_queue_report(
            self.config.report_path,
            self.config,
            self.state.path,
            self.state.records(self.task_order),
        )

    def _completion_path(self, record: TaskRecord) -> Path | None:
        if record.run_dir is None:
            return None
        return Path(record.run_dir) / "completion.json"

    def _worker_is_alive(self, record: TaskRecord) -> bool:
        if record.worker_pid is None:
            return False
        local_worker = self._workers.get(record.worker_pid)
        if local_worker is not None:
            return local_worker.poll() is None
        return process_is_alive(record.worker_pid)

    def _task_path(self, task: TaskConfig, raw_path: str) -> Path:
        path = Path(os.path.expanduser(os.path.expandvars(raw_path)))
        if not path.is_absolute():
            path = self.config.resolve_task_cwd(task) / path
        return path.resolve()

    def _validate_success(
        self, task: TaskConfig, record: TaskRecord
    ) -> tuple[bool, str | None, dict[str, str]]:
        output_hashes: dict[str, str] = {}
        for raw_output in task.required_outputs:
            output = self._task_path(task, raw_output)
            if not output.exists():
                return False, f"required output is missing: {output}", {}
            output_hashes[str(output)] = sha256_path(output)
        if task.run_outputs:
            if record.run_dir is None:
                return False, "run directory is missing from queue state", {}
            run_root = Path(record.run_dir).resolve()
            for raw_output in task.run_outputs:
                output = (run_root / raw_output).resolve()
                try:
                    output.relative_to(run_root)
                except ValueError:
                    return False, f"run output escapes run directory: {output}", {}
                if not output.exists():
                    return False, f"run output is missing: {output}", {}
                output_hashes[str(output)] = sha256_path(output)
        if task.gate is not None:
            gate_path = self._task_path(task, task.gate.artifact)
            gate_passed, gate_error = evaluate_gate(gate_path, task.gate)
            if not gate_passed:
                return False, gate_error, output_hashes
        return True, None, output_hashes

    def _finalize_running(self) -> None:
        for record in self.state.records(self.task_order):
            if record.status is not TaskStatus.RUNNING:
                continue
            completion_path = self._completion_path(record)
            if completion_path is not None and completion_path.is_file():
                local_worker = self._workers.pop(record.worker_pid or -1, None)
                if local_worker is not None:
                    try:
                        local_worker.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        pass
                try:
                    completion = json.loads(completion_path.read_text(encoding="utf-8"))
                    exit_code = int(completion["exit_code"])
                    completion_error = completion.get("error")
                except (OSError, ValueError, KeyError, TypeError) as error:
                    exit_code = 125
                    completion_error = f"invalid completion record: {error}"
                task = self.tasks[record.task_id]
                passed = exit_code == 0
                output_hashes: dict[str, str] = {}
                validation_error: str | None = None
                if passed:
                    passed, validation_error, output_hashes = self._validate_success(
                        task, record
                    )
                error_text = completion_error or validation_error
                if passed:
                    self.state.mark_terminal(
                        record.task_id,
                        TaskStatus.PASSED,
                        exit_code=0,
                        error=None,
                        output_hashes=output_hashes,
                    )
                    print(f"[PASSED] {record.task_id}", flush=True)
                elif record.attempts <= task.max_retries:
                    detail = error_text or f"exit code {exit_code}"
                    self.state.requeue_failed_attempt(record.task_id, error=detail)
                    print(
                        f"[RETRY] {record.task_id}: {detail} "
                        f"({record.attempts}/{task.max_retries})",
                        flush=True,
                    )
                else:
                    detail = error_text or f"exit code {exit_code}"
                    self.state.mark_terminal(
                        record.task_id,
                        TaskStatus.FAILED,
                        exit_code=exit_code,
                        error=detail,
                    )
                    print(f"[FAILED] {record.task_id}: {detail}", flush=True)
            elif not self._worker_is_alive(record):
                self._workers.pop(record.worker_pid or -1, None)
                task = self.tasks[record.task_id]
                detail = "worker exited without a completion record"
                if record.attempts <= task.max_retries:
                    self.state.requeue_failed_attempt(record.task_id, error=detail)
                    print(f"[RETRY] {record.task_id}: {detail}", flush=True)
                else:
                    self.state.mark_terminal(
                        record.task_id,
                        TaskStatus.FAILED,
                        exit_code=125,
                        error=detail,
                    )
                    print(f"[FAILED] {record.task_id}: {detail}", flush=True)

    def _block_failed_dependants(self) -> None:
        changed = True
        while changed:
            changed = False
            records = self._record_map()
            for task in self.config.tasks:
                record = records[task.task_id]
                if record.status is not TaskStatus.PENDING:
                    continue
                failed_dependencies = [
                    dependency
                    for dependency in task.depends_on
                    if records[dependency].status
                    in {TaskStatus.FAILED, TaskStatus.BLOCKED}
                ]
                if not failed_dependencies:
                    continue
                detail = "blocked by: " + ", ".join(failed_dependencies)
                self.state.mark_terminal(
                    task.task_id,
                    TaskStatus.BLOCKED,
                    exit_code=None,
                    error=detail,
                )
                print(f"[BLOCKED] {task.task_id}: {detail}", flush=True)
                changed = True

    def _ready_tasks(self) -> tuple[TaskConfig, ...]:
        records = self._record_map()
        ready: list[TaskConfig] = []
        for task in self.config.tasks:
            if records[task.task_id].status is not TaskStatus.PENDING:
                continue
            if all(
                records[dependency].status is TaskStatus.PASSED
                for dependency in task.depends_on
            ):
                ready.append(task)
        return tuple(ready)

    def _launch_task(
        self, task: TaskConfig, *, gpu_snapshot: GpuSnapshot | None
    ) -> None:
        cwd = self.config.resolve_task_cwd(task)
        if not cwd.is_dir():
            raise FileNotFoundError(f"task {task.task_id} cwd does not exist: {cwd}")
        current = self.state.record(task.task_id)
        attempt = current.attempts + 1
        run_dir = (
            self.config.run_root
            / task.task_id
            / f"attempt-{attempt:03d}-{time.time_ns()}"
        )
        run_dir.mkdir(parents=True, exist_ok=False)
        run_dir.chmod(0o700)
        command = self.config.expanded_command(task)
        environment = self.config.expanded_env(task)
        gpu_index = None if gpu_snapshot is None else gpu_snapshot.index
        if task.seed is not None:
            environment["RESEARCHCLAW_SEED"] = str(task.seed)
        if gpu_index is not None:
            environment["CUDA_VISIBLE_DEVICES"] = str(gpu_index)
            environment["RESEARCHCLAW_ASSIGNED_GPU"] = str(gpu_index)
            environment["RESEARCHCLAW_GPU_ALLOCATION_MODE"] = str(
                task.allocation_mode or GpuAllocationMode.EXCLUSIVE
            )
            if task.memory_required_mib is not None:
                environment["RESEARCHCLAW_MEMORY_REQUIRED_MIB"] = str(
                    task.memory_required_mib
                )
            if task.comparison_group is not None:
                environment["RESEARCHCLAW_COMPARISON_GROUP"] = task.comparison_group
        environment["RESEARCHCLAW_RUN_DIR"] = str(run_dir)
        worker_environment = os.environ.copy()
        worker_environment.update(environment)
        spec_path = run_dir / "worker-spec.json"
        completion_path = run_dir / "completion.json"
        allocation_path = run_dir / "allocation.json"
        allocation_payload: dict[str, object] = {"resource": "cpu"}
        if gpu_snapshot is not None:
            allocation_payload = {
                "resource": "gpu",
                "allocation_mode": str(
                    task.allocation_mode or GpuAllocationMode.EXCLUSIVE
                ),
                "comparison_group": task.comparison_group,
                "gpu_index": gpu_snapshot.index,
                "gpu_uuid": gpu_snapshot.uuid,
                "memory_total_mib": gpu_snapshot.memory_total_mib,
                "memory_used_mib": gpu_snapshot.memory_used_mib,
                "memory_free_mib": gpu_snapshot.memory_free_mib,
                "memory_required_mib": task.memory_required_mib,
                "shared_memory_reserve_mib": (
                    self.config.scheduler.shared_memory_reserve_mib
                    if task.allocation_mode is GpuAllocationMode.SHARED
                    else None
                ),
                "utilization_percent": gpu_snapshot.utilization_percent,
                "coexisting_compute_process_count": len(gpu_snapshot.compute_pids),
            }
        allocation_path.write_text(
            json.dumps(allocation_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        allocation_path.chmod(0o600)
        spec_path.write_text(
            json.dumps(
                {
                    "task_id": task.task_id,
                    "command": command,
                    "cwd": str(cwd),
                    "env": {},
                    "env_keys": sorted(environment),
                    "timeout_seconds": task.timeout_seconds,
                    "gpu_index": gpu_index,
                    "allocation_mode": (
                        None
                        if task.allocation_mode is None
                        else task.allocation_mode.value
                    ),
                    "comparison_group": task.comparison_group,
                    "memory_required_mib": task.memory_required_mib,
                    "seed": task.seed,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        spec_path.chmod(0o600)
        stdout_path = run_dir / "stdout.log"
        stderr_path = run_dir / "stderr.log"
        with (
            stdout_path.open("ab") as stdout_handle,
            stderr_path.open("ab") as stderr_handle,
        ):
            os.fchmod(stdout_handle.fileno(), 0o600)
            os.fchmod(stderr_handle.fileno(), 0o600)
            worker = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(__file__).with_name("worker.py")),
                    "--spec",
                    str(spec_path),
                    "--completion",
                    str(completion_path),
                ],
                cwd=cwd,
                env=worker_environment,
                stdout=stdout_handle,
                stderr=stderr_handle,
                start_new_session=True,
            )
        self._workers[worker.pid] = worker
        self.state.mark_running(
            task.task_id,
            gpu_index=gpu_index,
            worker_pid=worker.pid,
            worker_pgid=os.getpgid(worker.pid),
            run_dir=run_dir,
            command=command,
            commit_sha=_git_commit(cwd),
        )
        resource = (
            "CPU"
            if gpu_index is None
            else f"GPU {gpu_index} ({task.allocation_mode.value})"
        )
        print(f"[RUNNING] {task.task_id} on {resource}; logs={run_dir}", flush=True)

    def _launch_cpu_tasks(self, ready: tuple[TaskConfig, ...]) -> None:
        records = self._record_map()
        running_cpu = sum(
            record.status is TaskStatus.RUNNING and record.gpu_index is None
            for record in records.values()
        )
        capacity = self.config.scheduler.max_parallel_cpu_tasks - running_cpu
        for task in (candidate for candidate in ready if candidate.gpu_count == 0):
            if capacity <= 0 or self.state.drain_requested():
                return
            try:
                self._launch_task(task, gpu_snapshot=None)
            except (OSError, TypeError, ValueError) as error:
                self.state.mark_terminal(
                    task.task_id,
                    TaskStatus.FAILED,
                    exit_code=125,
                    error=f"launch failed: {error}",
                )
                print(f"[FAILED] {task.task_id}: launch failed: {error}", flush=True)
            capacity -= 1

    def _strictly_idle(self, snapshot: GpuSnapshot) -> bool:
        policy = self.config.scheduler
        return snapshot.is_idle(
            memory_used_limit_mib=policy.memory_used_limit_mib,
            utilization_limit_percent=policy.utilization_limit_percent,
        )

    def _has_shared_capacity(self, task: TaskConfig, snapshot: GpuSnapshot) -> bool:
        if task.memory_required_mib is None:
            raise ValueError(f"shared task {task.task_id} has no memory_required_mib")
        return snapshot.has_capacity(
            memory_required_mib=task.memory_required_mib,
            reserve_mib=self.config.scheduler.shared_memory_reserve_mib,
        )

    def _eligible_snapshots(
        self,
        task: TaskConfig,
        snapshots: tuple[GpuSnapshot, ...],
        *,
        excluded_indices: set[int],
        strictly_idle_indices: set[int],
    ) -> tuple[GpuSnapshot, ...]:
        candidates = [
            snapshot
            for snapshot in snapshots
            if snapshot.index not in excluded_indices
            and (
                snapshot.index in strictly_idle_indices
                if task.allocation_mode is GpuAllocationMode.EXCLUSIVE
                else self._has_shared_capacity(task, snapshot)
            )
        ]
        if task.allocation_mode is GpuAllocationMode.SHARED:
            candidates.sort(
                key=lambda snapshot: (-snapshot.memory_free_mib, snapshot.index)
            )
        else:
            candidates.sort(key=lambda snapshot: snapshot.index)
        return tuple(candidates)

    def _still_eligible(self, task: TaskConfig, snapshot: GpuSnapshot) -> bool:
        if task.allocation_mode is GpuAllocationMode.SHARED:
            return self._has_shared_capacity(task, snapshot)
        return self._strictly_idle(snapshot)

    def _launch_gpu_tasks(self, ready: tuple[TaskConfig, ...]) -> None:
        gpu_ready_tasks = [task for task in ready if task.gpu_count == 1]
        if not gpu_ready_tasks or self.state.drain_requested():
            return
        records = self._record_map()
        allocated = {
            record.gpu_index
            for record in records.values()
            if record.status is TaskStatus.RUNNING and record.gpu_index is not None
        }
        capacity = self.config.scheduler.max_parallel_gpu_tasks - len(allocated)
        if capacity <= 0:
            return
        snapshots = self.gpu_probe()
        policy = self.config.scheduler
        strictly_idle_indices = set(
            self.idle_tracker.observe(
                snapshots,
                memory_used_limit_mib=policy.memory_used_limit_mib,
                utilization_limit_percent=policy.utilization_limit_percent,
                excluded_indices={int(index) for index in allocated},
            )
        )
        ordered_tasks = sorted(
            gpu_ready_tasks,
            key=lambda task: (
                task.allocation_mode is GpuAllocationMode.SHARED,
                self.task_order.index(task.task_id),
            ),
        )
        for task in ordered_tasks:
            if capacity <= 0:
                break
            candidates = self._eligible_snapshots(
                task,
                snapshots,
                excluded_indices={int(index) for index in allocated},
                strictly_idle_indices=strictly_idle_indices,
            )
            if not candidates:
                continue
            gpu_index = candidates[0].index
            delay = self.random_uniform(0.0, policy.random_backoff_seconds)
            if delay > 0:
                self.sleep(delay)
            second_snapshots = {
                snapshot.index: snapshot for snapshot in self.gpu_probe()
            }
            second = second_snapshots.get(gpu_index)
            if second is None or not self._still_eligible(task, second):
                self.idle_tracker.reset(gpu_index)
                print(
                    f"[WAITING] GPU {gpu_index} no longer satisfies "
                    f"{task.allocation_mode.value} allocation",
                    flush=True,
                )
                continue
            try:
                self._launch_task(task, gpu_snapshot=second)
            except (OSError, TypeError, ValueError) as error:
                self.state.mark_terminal(
                    task.task_id,
                    TaskStatus.FAILED,
                    exit_code=125,
                    error=f"launch failed: {error}",
                )
                print(f"[FAILED] {task.task_id}: launch failed: {error}", flush=True)
            self.idle_tracker.reset(gpu_index)
            allocated.add(gpu_index)
            capacity -= 1

    def tick(self) -> bool:
        """Advance the queue once; return true when no work remains."""

        self._finalize_running()
        self._block_failed_dependants()
        records = self._record_map()
        if all(record.status in TERMINAL_STATUSES for record in records.values()):
            self._write_report()
            return True
        if self.state.drain_requested():
            finished = not any(
                record.status is TaskStatus.RUNNING for record in records.values()
            )
            self._write_report()
            return finished
        ready = self._ready_tasks()
        self._launch_cpu_tasks(ready)
        ready = self._ready_tasks()
        self._launch_gpu_tasks(ready)
        self._write_report()
        return False

    def run(self) -> int:
        """Run until the graph finishes or a requested drain completes."""

        self.state.clear_drain()
        print(self.render_plan(), flush=True)
        try:
            while True:
                if self.tick():
                    break
                self.sleep(self.config.scheduler.poll_interval_seconds)
        except KeyboardInterrupt:
            print(
                "[DRAINING] interrupt received; waiting for running tasks", flush=True
            )
            self.state.request_drain()
            while not self.tick():
                self.sleep(self.config.scheduler.poll_interval_seconds)
        records = self._record_map()
        if self.state.drain_requested() and any(
            record.status is TaskStatus.PENDING for record in records.values()
        ):
            print(
                "[DRAINED] running tasks finished; pending work preserved", flush=True
            )
            return 0
        failed = [
            record.task_id
            for record in records.values()
            if record.status in {TaskStatus.FAILED, TaskStatus.BLOCKED}
        ]
        if failed:
            print(f"[QUEUE FAILED] {', '.join(failed)}", flush=True)
            return 1
        print("[QUEUE PASSED] all tasks completed", flush=True)
        return 0


def stop_worker(record: TaskRecord) -> None:
    """Request graceful termination of one scheduler-owned worker group."""

    if record.status is not TaskStatus.RUNNING or record.worker_pgid is None:
        raise ValueError(f"task {record.task_id} has no running worker group")
    os.killpg(record.worker_pgid, signal.SIGTERM)
