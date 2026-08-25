"""Private Markdown status reports for unattended GPU queues."""

from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from researchclaw.gpu_queue.models import QueueConfig
from researchclaw.gpu_queue.state import TaskRecord, TaskStatus


def _markdown_cell(value: object | None) -> str:
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _markdown_code(value: object) -> str:
    sanitized = str(value).replace("`", "'")
    return f"`{sanitized}`"


def _overall_status(records: tuple[TaskRecord, ...]) -> str:
    statuses = {record.status for record in records}
    if statuses & {TaskStatus.FAILED, TaskStatus.BLOCKED}:
        return "ATTENTION"
    if statuses == {TaskStatus.PASSED}:
        return "PASSED"
    if TaskStatus.RUNNING in statuses:
        return "RUNNING"
    return "WAITING"


def render_queue_report(
    config: QueueConfig,
    state_path: Path,
    records: tuple[TaskRecord, ...],
    *,
    generated_at: datetime | None = None,
) -> str:
    """Render a bounded queue report without copying arbitrary task output."""

    timestamp = generated_at or datetime.now(timezone.utc)
    counts = Counter(record.status.value for record in records)
    count_text = ", ".join(f"{status}={counts.get(status, 0)}" for status in TaskStatus)
    policy = config.scheduler
    tasks = config.task_map()
    lines = [
        "# GPU Experiment Status",
        "",
        f"- Generated (UTC): {timestamp.isoformat()}",
        f"- Overall: **{_overall_status(records)}**",
        f"- Tasks: {count_text}",
        f"- Queue config: {_markdown_code(config.source_path)}",
        f"- Queue state: {_markdown_code(state_path.resolve())}",
        f"- Run root: {_markdown_code(config.run_root)}",
        (
            "- Exclusive policy: "
            f"{policy.idle_samples} consecutive samples × "
            f"{policy.poll_interval_seconds:g}s; no compute PID; "
            f"memory < {policy.memory_used_limit_mib} MiB; "
            f"utilization < {policy.utilization_limit_percent}%"
        ),
        (
            "- Shared policy: reported free memory ≥ task requirement + "
            f"{policy.shared_memory_reserve_mib} MiB reserve; foreign compute "
            "processes and utilization do not block allocation"
        ),
        "",
        "This file is updated atomically by the queue scheduler. It records "
        "execution metadata and artifact hashes, but never copies task commands, "
        "environment values, or raw stdout/stderr into Markdown.",
        "",
        "## Tasks",
        "",
        "| Task | Group | Mode | Memory MiB | Status | Attempts | GPU | Started (UTC) | Ended (UTC) | Exit |",
        "|---|---|---:|---:|---:|---:|---:|---|---|---:|",
    ]
    for record in records:
        task = tasks[record.task_id]
        lines.append(
            "| "
            + " | ".join(
                (
                    _markdown_cell(record.task_id),
                    _markdown_cell(task.comparison_group),
                    _markdown_cell(task.allocation_mode),
                    _markdown_cell(task.memory_required_mib),
                    _markdown_cell(record.status.value),
                    _markdown_cell(record.attempts),
                    _markdown_cell(record.gpu_index),
                    _markdown_cell(record.started_at),
                    _markdown_cell(record.ended_at),
                    _markdown_cell(record.exit_code),
                )
            )
            + " |"
        )

    for record in records:
        lines.extend(("", f"### {record.task_id}", ""))
        if record.run_dir is None:
            lines.append("- Run directory: not created yet")
        else:
            run_dir = Path(record.run_dir)
            lines.extend(
                (
                    f"- Run directory: {_markdown_code(run_dir)}",
                    f"- Allocation record: {_markdown_code(run_dir / 'allocation.json')}",
                    f"- Standard output: {_markdown_code(run_dir / 'stdout.log')}",
                    f"- Standard error: {_markdown_code(run_dir / 'stderr.log')}",
                    f"- Completion record: {_markdown_code(run_dir / 'completion.json')}",
                )
            )
        if record.commit_sha:
            lines.append(f"- Git commit: {_markdown_code(record.commit_sha)}")
        if record.seed is not None:
            lines.append(f"- Seed: {record.seed}")
        if record.error:
            lines.append(f"- Error: {_markdown_code(record.error)}")
        try:
            output_hashes = json.loads(record.output_hashes_json or "{}")
        except (TypeError, ValueError):
            output_hashes = {}
            lines.append("- Output hashes: invalid state entry")
        if isinstance(output_hashes, dict) and output_hashes:
            lines.extend(("- Required outputs:", ""))
            for output_path, digest in sorted(output_hashes.items()):
                lines.append(
                    f"  - {_markdown_code(output_path)} — SHA256 "
                    f"{_markdown_code(digest)}"
                )
        elif record.status is TaskStatus.PASSED:
            lines.append("- Required outputs: none declared")

    return "\n".join(lines) + "\n"


def write_queue_report(
    path: Path,
    config: QueueConfig,
    state_path: Path,
    records: tuple[TaskRecord, ...],
) -> None:
    """Atomically replace a mode-0600 Markdown queue report."""

    output = path.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output.parent,
            prefix=f".{output.name}.",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            os.fchmod(handle.fileno(), 0o600)
            handle.write(render_queue_report(config, state_path, records))
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(output)
        output.chmod(0o600)
    except BaseException:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
