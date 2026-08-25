"""Configuration models and validation for the GPU queue."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


def _require_mapping(value: object, *, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _require_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a nonempty string")
    return value.strip()


def _string_tuple(value: object, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise TypeError(f"{field_name} must be a list of strings")
    result = tuple(
        _require_string(item, field_name=f"{field_name} item") for item in value
    )
    return result


def _expand_text(value: str) -> str:
    return os.path.expanduser(os.path.expandvars(value))


class GpuAllocationMode(StrEnum):
    """Supported single-GPU allocation contracts."""

    EXCLUSIVE = "exclusive"
    SHARED = "shared"


@dataclass(frozen=True)
class GateCondition:
    """A required value in a JSON artifact."""

    artifact: str
    field: str
    equals: object

    @classmethod
    def from_mapping(cls, value: object, *, task_id: str) -> GateCondition | None:
        """Parse an optional gate condition."""

        if value is None:
            return None
        raw = _require_mapping(value, field_name=f"task {task_id} gate")
        if "equals" not in raw:
            raise ValueError(f"task {task_id} gate.equals is required")
        return cls(
            artifact=_require_string(
                raw.get("artifact"), field_name=f"task {task_id} gate.artifact"
            ),
            field=_require_string(
                raw.get("field"), field_name=f"task {task_id} gate.field"
            ),
            equals=raw["equals"],
        )


@dataclass(frozen=True)
class TaskConfig:
    """One executable task in the dependency graph."""

    task_id: str
    command: tuple[str, ...]
    cwd: str
    env: Mapping[str, str] = field(default_factory=dict)
    gpu_count: int = 0
    depends_on: tuple[str, ...] = ()
    required_outputs: tuple[str, ...] = ()
    run_outputs: tuple[str, ...] = ()
    gate: GateCondition | None = None
    timeout_seconds: int = 0
    max_retries: int = 0
    seed: int | None = None
    allocation_mode: GpuAllocationMode | None = None
    memory_required_mib: int | None = None
    comparison_group: str | None = None
    enabled: bool = True

    @property
    def spec_hash(self) -> str:
        """Return a stable hash of the executable task contract."""

        payload = json.dumps(
            asdict(self), sort_keys=True, separators=(",", ":"), default=str
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def from_mapping(cls, value: object, *, index: int) -> TaskConfig:
        """Parse and validate one task mapping."""

        raw = _require_mapping(value, field_name=f"tasks[{index}]")
        task_id = _require_string(raw.get("id"), field_name=f"tasks[{index}].id")
        command = _string_tuple(
            raw.get("command"), field_name=f"task {task_id} command"
        )
        if not command:
            raise ValueError(f"task {task_id} command must not be empty")
        raw_env = _require_mapping(raw.get("env", {}), field_name=f"task {task_id} env")
        env: dict[str, str] = {}
        for key, item in raw_env.items():
            env[_require_string(key, field_name=f"task {task_id} env key")] = str(item)

        gpu_count = int(raw.get("gpu_count", 0))
        if gpu_count not in {0, 1}:
            raise ValueError(f"task {task_id} gpu_count must be 0 or 1")
        timeout_seconds = int(raw.get("timeout_seconds", 0))
        max_retries = int(raw.get("max_retries", 0))
        if timeout_seconds < 0:
            raise ValueError(f"task {task_id} timeout_seconds must be nonnegative")
        if max_retries < 0:
            raise ValueError(f"task {task_id} max_retries must be nonnegative")
        seed_value = raw.get("seed")
        seed = None if seed_value is None else int(seed_value)
        raw_allocation_mode = raw.get("allocation_mode")
        raw_memory_required = raw.get("memory_required_mib")
        raw_comparison_group = raw.get("comparison_group")
        allocation_mode: GpuAllocationMode | None = None
        memory_required_mib: int | None = None
        comparison_group: str | None = None
        if gpu_count == 0:
            if raw_allocation_mode is not None or raw_memory_required is not None:
                raise ValueError(
                    f"CPU task {task_id} cannot declare GPU allocation settings"
                )
            if raw_comparison_group is not None:
                raise ValueError(f"CPU task {task_id} cannot declare comparison_group")
        else:
            try:
                allocation_mode = GpuAllocationMode(
                    str(raw_allocation_mode or GpuAllocationMode.EXCLUSIVE)
                )
            except ValueError as error:
                raise ValueError(
                    f"task {task_id} allocation_mode must be shared or exclusive"
                ) from error
            if raw_memory_required is not None:
                memory_required_mib = int(raw_memory_required)
                if memory_required_mib <= 0:
                    raise ValueError(
                        f"task {task_id} memory_required_mib must be positive"
                    )
            if (
                allocation_mode is GpuAllocationMode.SHARED
                and memory_required_mib is None
            ):
                raise ValueError(
                    f"shared GPU task {task_id} requires memory_required_mib"
                )
            if raw_comparison_group is not None:
                comparison_group = _require_string(
                    raw_comparison_group,
                    field_name=f"task {task_id} comparison_group",
                )
        enabled = raw.get("enabled", True)
        if not isinstance(enabled, bool):
            raise TypeError(f"task {task_id} enabled must be a boolean")
        run_outputs = _string_tuple(
            raw.get("run_outputs"), field_name=f"task {task_id} run_outputs"
        )
        for run_output in run_outputs:
            output_path = Path(run_output)
            if output_path.is_absolute() or ".." in output_path.parts:
                raise ValueError(
                    f"task {task_id} run_outputs must stay inside its run directory"
                )
        return cls(
            task_id=task_id,
            command=command,
            cwd=_require_string(raw.get("cwd", "."), field_name=f"task {task_id} cwd"),
            env=env,
            gpu_count=gpu_count,
            depends_on=_string_tuple(
                raw.get("depends_on"), field_name=f"task {task_id} depends_on"
            ),
            required_outputs=_string_tuple(
                raw.get("required_outputs"),
                field_name=f"task {task_id} required_outputs",
            ),
            run_outputs=run_outputs,
            gate=GateCondition.from_mapping(raw.get("gate"), task_id=task_id),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            seed=seed,
            allocation_mode=allocation_mode,
            memory_required_mib=memory_required_mib,
            comparison_group=comparison_group,
            enabled=enabled,
        )


@dataclass(frozen=True)
class SchedulerConfig:
    """Resource and polling policy."""

    poll_interval_seconds: float = 30.0
    idle_samples: int = 20
    memory_used_limit_mib: int = 1024
    utilization_limit_percent: int = 5
    max_parallel_gpu_tasks: int = 2
    max_parallel_cpu_tasks: int = 1
    random_backoff_seconds: float = 15.0
    shared_memory_reserve_mib: int = 4096

    @classmethod
    def from_mapping(cls, value: object) -> SchedulerConfig:
        """Parse scheduler settings."""

        raw = _require_mapping(value or {}, field_name="scheduler")
        result = cls(
            poll_interval_seconds=float(raw.get("poll_interval_seconds", 30.0)),
            idle_samples=int(raw.get("idle_samples", 20)),
            memory_used_limit_mib=int(raw.get("memory_used_limit_mib", 1024)),
            utilization_limit_percent=int(raw.get("utilization_limit_percent", 5)),
            max_parallel_gpu_tasks=int(raw.get("max_parallel_gpu_tasks", 2)),
            max_parallel_cpu_tasks=int(raw.get("max_parallel_cpu_tasks", 1)),
            random_backoff_seconds=float(raw.get("random_backoff_seconds", 15.0)),
            shared_memory_reserve_mib=int(raw.get("shared_memory_reserve_mib", 4096)),
        )
        if result.poll_interval_seconds <= 0:
            raise ValueError("scheduler.poll_interval_seconds must be positive")
        if result.idle_samples <= 0:
            raise ValueError("scheduler.idle_samples must be positive")
        if result.memory_used_limit_mib <= 0:
            raise ValueError("scheduler.memory_used_limit_mib must be positive")
        if not 0 <= result.utilization_limit_percent <= 100:
            raise ValueError(
                "scheduler.utilization_limit_percent must be between 0 and 100"
            )
        if not 1 <= result.max_parallel_gpu_tasks <= 2:
            raise ValueError("scheduler.max_parallel_gpu_tasks must be 1 or 2")
        if result.max_parallel_cpu_tasks <= 0:
            raise ValueError("scheduler.max_parallel_cpu_tasks must be positive")
        if result.random_backoff_seconds < 0:
            raise ValueError("scheduler.random_backoff_seconds must be nonnegative")
        if result.shared_memory_reserve_mib < 0:
            raise ValueError("scheduler.shared_memory_reserve_mib must be nonnegative")
        return result


@dataclass(frozen=True)
class QueueConfig:
    """Validated queue configuration."""

    source_path: Path
    scheduler: SchedulerConfig
    tasks: tuple[TaskConfig, ...]
    run_root: Path
    report_path: Path | None

    @classmethod
    def load(cls, path: Path) -> QueueConfig:
        """Load, normalize, and validate a queue YAML file."""

        source_path = path.expanduser().resolve()
        raw_value = yaml.safe_load(source_path.read_text(encoding="utf-8")) or {}
        raw = _require_mapping(raw_value, field_name="queue config")
        version = raw.get("version")
        if version != 1:
            raise ValueError("queue config version must be 1")
        raw_tasks = raw.get("tasks")
        if isinstance(raw_tasks, str) or not isinstance(raw_tasks, Sequence):
            raise TypeError("tasks must be a list")
        all_tasks = tuple(
            TaskConfig.from_mapping(item, index=index)
            for index, item in enumerate(raw_tasks)
        )
        enabled_tasks = tuple(task for task in all_tasks if task.enabled)
        if not enabled_tasks:
            raise ValueError("queue config must contain at least one enabled task")
        run_root_value = _require_string(
            raw.get("run_root", "runs"), field_name="run_root"
        )
        run_root = Path(_expand_text(run_root_value))
        if not run_root.is_absolute():
            run_root = source_path.parent / run_root
        raw_report_path = raw.get("report_path")
        report_path: Path | None = None
        if raw_report_path is not None:
            report_path_value = _require_string(
                raw_report_path, field_name="report_path"
            )
            report_path = Path(_expand_text(report_path_value))
            if not report_path.is_absolute():
                report_path = source_path.parent / report_path
            report_path = report_path.resolve()
        result = cls(
            source_path=source_path,
            scheduler=SchedulerConfig.from_mapping(raw.get("scheduler")),
            tasks=enabled_tasks,
            run_root=run_root.resolve(),
            report_path=report_path,
        )
        result.validate_graph()
        return result

    def validate_graph(self) -> None:
        """Validate unique identifiers, dependencies, and acyclicity."""

        by_id: dict[str, TaskConfig] = {}
        for task in self.tasks:
            if task.task_id in by_id:
                raise ValueError(f"duplicate task id: {task.task_id}")
            by_id[task.task_id] = task
        for task in self.tasks:
            missing = sorted(set(task.depends_on) - set(by_id))
            if missing:
                raise ValueError(
                    f"task {task.task_id} has missing dependencies: {missing}"
                )
            if task.task_id in task.depends_on:
                raise ValueError(f"task {task.task_id} cannot depend on itself")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visiting:
                raise ValueError(f"dependency cycle includes task {task_id}")
            if task_id in visited:
                return
            visiting.add(task_id)
            for dependency in by_id[task_id].depends_on:
                visit(dependency)
            visiting.remove(task_id)
            visited.add(task_id)

        for task in self.tasks:
            visit(task.task_id)

        comparison_tasks: dict[str, list[TaskConfig]] = {}
        for task in self.tasks:
            if task.comparison_group is None or task.allocation_mode is None:
                continue
            comparison_tasks.setdefault(task.comparison_group, []).append(task)
        required_modes = {
            GpuAllocationMode.SHARED,
            GpuAllocationMode.EXCLUSIVE,
        }
        for group, paired_tasks in comparison_tasks.items():
            modes = {task.allocation_mode for task in paired_tasks}
            if len(paired_tasks) != 2 or modes != required_modes:
                observed = ", ".join(sorted(mode.value for mode in modes))
                raise ValueError(
                    f"comparison_group {group} requires exactly one shared and "
                    "one exclusive task; "
                    f"observed: {observed}"
                )
            comparable_contracts = [
                (
                    task.command,
                    task.cwd,
                    tuple(sorted(task.env.items())),
                    task.depends_on,
                    task.required_outputs,
                    task.run_outputs,
                    task.gate,
                    task.timeout_seconds,
                    task.max_retries,
                    task.seed,
                    task.memory_required_mib,
                )
                for task in paired_tasks
            ]
            if comparable_contracts[0] != comparable_contracts[1]:
                raise ValueError(
                    f"comparison_group {group} tasks must share command, inputs, "
                    "outputs, dependencies, limits, seed, and memory request"
                )

    def task_map(self) -> dict[str, TaskConfig]:
        """Return tasks keyed by identifier while preserving config order."""

        return {task.task_id: task for task in self.tasks}

    def resolve_task_cwd(self, task: TaskConfig) -> Path:
        """Resolve a task working directory relative to the queue file."""

        raw = Path(_expand_text(task.cwd))
        if not raw.is_absolute():
            raw = self.source_path.parent / raw
        return raw.resolve()

    def expanded_command(self, task: TaskConfig) -> tuple[str, ...]:
        """Expand environment variables and user markers in command arguments."""

        return tuple(_expand_text(argument) for argument in task.command)

    def expanded_env(self, task: TaskConfig) -> dict[str, str]:
        """Expand task environment values."""

        return {key: _expand_text(value) for key, value in task.env.items()}
