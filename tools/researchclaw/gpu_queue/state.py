"""SQLite-backed durable state for the GPU queue."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Self

from researchclaw.gpu_queue.models import TaskConfig

try:
    import fcntl
except ImportError:  # pragma: no cover - queue execution is Linux-only.
    fcntl = None  # type: ignore[assignment]


class TaskStatus(StrEnum):
    """Durable task lifecycle states."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


TERMINAL_STATUSES = frozenset(
    {TaskStatus.PASSED, TaskStatus.FAILED, TaskStatus.BLOCKED}
)


def utc_now() -> str:
    """Return an RFC 3339 UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TaskRecord:
    """One durable task state row."""

    task_id: str
    spec_hash: str
    status: TaskStatus
    attempts: int
    gpu_index: int | None
    worker_pid: int | None
    worker_pgid: int | None
    run_dir: str | None
    started_at: str | None
    ended_at: str | None
    exit_code: int | None
    error: str | None
    command_json: str | None
    commit_sha: str | None
    seed: int | None
    output_hashes_json: str | None


class QueueState:
    """Transactional queue state stored in one SQLite database."""

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the SQLite connection."""

        self._connection.close()

    def _initialize_schema(self) -> None:
        self._connection.executescript("""
            PRAGMA journal_mode = WAL;
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                spec_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                gpu_index INTEGER,
                worker_pid INTEGER,
                worker_pgid INTEGER,
                run_dir TEXT,
                started_at TEXT,
                ended_at TEXT,
                exit_code INTEGER,
                error TEXT,
                command_json TEXT,
                commit_sha TEXT,
                seed INTEGER,
                output_hashes_json TEXT
            );
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)
        self._connection.commit()

    def register_tasks(self, tasks: tuple[TaskConfig, ...]) -> None:
        """Register config tasks and reject unsafe in-place contract changes."""

        with self._connection:
            for task in tasks:
                row = self._connection.execute(
                    "SELECT spec_hash, status FROM tasks WHERE task_id = ?",
                    (task.task_id,),
                ).fetchone()
                if row is None:
                    self._connection.execute(
                        """
                        INSERT INTO tasks (task_id, spec_hash, status, seed)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            task.task_id,
                            task.spec_hash,
                            TaskStatus.PENDING.value,
                            task.seed,
                        ),
                    )
                    continue
                if row["spec_hash"] == task.spec_hash:
                    continue
                status = TaskStatus(row["status"])
                if status in {TaskStatus.RUNNING, TaskStatus.PASSED}:
                    raise ValueError(
                        f"task {task.task_id} changed after reaching {status.value}; "
                        "use a new state database"
                    )
                self._connection.execute(
                    """
                    UPDATE tasks
                    SET spec_hash = ?, status = ?, attempts = 0, gpu_index = NULL,
                        worker_pid = NULL, worker_pgid = NULL, run_dir = NULL,
                        started_at = NULL, ended_at = NULL, exit_code = NULL,
                        error = NULL, command_json = NULL, commit_sha = NULL,
                        seed = ?, output_hashes_json = NULL
                    WHERE task_id = ?
                    """,
                    (
                        task.spec_hash,
                        TaskStatus.PENDING.value,
                        task.seed,
                        task.task_id,
                    ),
                )

    @staticmethod
    def _record(row: sqlite3.Row) -> TaskRecord:
        return TaskRecord(
            task_id=row["task_id"],
            spec_hash=row["spec_hash"],
            status=TaskStatus(row["status"]),
            attempts=int(row["attempts"]),
            gpu_index=row["gpu_index"],
            worker_pid=row["worker_pid"],
            worker_pgid=row["worker_pgid"],
            run_dir=row["run_dir"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            exit_code=row["exit_code"],
            error=row["error"],
            command_json=row["command_json"],
            commit_sha=row["commit_sha"],
            seed=row["seed"],
            output_hashes_json=row["output_hashes_json"],
        )

    def records(
        self, task_ids: tuple[str, ...] | None = None
    ) -> tuple[TaskRecord, ...]:
        """Return state rows, optionally restricted to ordered task identifiers."""

        if task_ids is None:
            rows = self._connection.execute(
                "SELECT * FROM tasks ORDER BY rowid"
            ).fetchall()
            return tuple(self._record(row) for row in rows)
        result: list[TaskRecord] = []
        for task_id in task_ids:
            row = self._connection.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            result.append(self._record(row))
        return tuple(result)

    def record(self, task_id: str) -> TaskRecord:
        """Return one task state row."""

        return self.records((task_id,))[0]

    def mark_running(
        self,
        task_id: str,
        *,
        gpu_index: int | None,
        worker_pid: int,
        worker_pgid: int,
        run_dir: Path,
        command: tuple[str, ...],
        commit_sha: str | None,
    ) -> None:
        """Atomically record a worker launch."""

        with self._connection:
            cursor = self._connection.execute(
                """
                UPDATE tasks
                SET status = ?, attempts = attempts + 1, gpu_index = ?,
                    worker_pid = ?, worker_pgid = ?, run_dir = ?, started_at = ?,
                    ended_at = NULL, exit_code = NULL, error = NULL,
                    command_json = ?, commit_sha = ?, output_hashes_json = NULL
                WHERE task_id = ? AND status = ?
                """,
                (
                    TaskStatus.RUNNING.value,
                    gpu_index,
                    worker_pid,
                    worker_pgid,
                    str(run_dir),
                    utc_now(),
                    json.dumps(command),
                    commit_sha,
                    task_id,
                    TaskStatus.PENDING.value,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"task {task_id} was not pending at launch")

    def mark_terminal(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        exit_code: int | None,
        error: str | None,
        output_hashes: dict[str, str] | None = None,
    ) -> None:
        """Record a terminal task result."""

        if status not in TERMINAL_STATUSES:
            raise ValueError(f"{status.value} is not terminal")
        with self._connection:
            self._connection.execute(
                """
                UPDATE tasks
                SET status = ?, ended_at = ?, exit_code = ?, error = ?,
                    output_hashes_json = ?
                WHERE task_id = ?
                """,
                (
                    status.value,
                    utc_now(),
                    exit_code,
                    error,
                    None if output_hashes is None else json.dumps(output_hashes),
                    task_id,
                ),
            )

    def requeue_failed_attempt(self, task_id: str, *, error: str) -> None:
        """Return a failed attempt to pending while retaining attempt count."""

        with self._connection:
            self._connection.execute(
                """
                UPDATE tasks
                SET status = ?, gpu_index = NULL, worker_pid = NULL,
                    worker_pgid = NULL, ended_at = ?, exit_code = NULL, error = ?
                WHERE task_id = ?
                """,
                (TaskStatus.PENDING.value, utc_now(), error, task_id),
            )

    def retry(self, task_id: str) -> None:
        """Explicitly reset a failed or blocked task for another run."""

        record = self.record(task_id)
        if record.status not in {TaskStatus.FAILED, TaskStatus.BLOCKED}:
            raise ValueError(
                f"task {task_id} is {record.status.value}, not FAILED or BLOCKED"
            )
        with self._connection:
            self._connection.execute(
                """
                UPDATE tasks
                SET status = ?, gpu_index = NULL, worker_pid = NULL,
                    worker_pgid = NULL, run_dir = NULL, started_at = NULL,
                    ended_at = NULL, exit_code = NULL, error = NULL,
                    command_json = NULL, commit_sha = NULL,
                    output_hashes_json = NULL
                WHERE task_id = ?
                """,
                (TaskStatus.PENDING.value, task_id),
            )

    def set_metadata(self, key: str, value: str) -> None:
        """Set one scheduler metadata value."""

        with self._connection:
            self._connection.execute(
                """
                INSERT INTO metadata (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def metadata(self, key: str, default: str = "") -> str:
        """Read one scheduler metadata value."""

        row = self._connection.execute(
            "SELECT value FROM metadata WHERE key = ?", (key,)
        ).fetchone()
        return default if row is None else str(row["value"])

    def request_drain(self) -> None:
        """Prevent new launches while allowing current tasks to finish."""

        self.set_metadata("drain_requested", "1")

    def clear_drain(self) -> None:
        """Allow launches for a newly started scheduler."""

        self.set_metadata("drain_requested", "0")

    def drain_requested(self) -> bool:
        """Return whether a graceful drain was requested."""

        return self.metadata("drain_requested", "0") == "1"


class QueueRunLock:
    """Prevent concurrent schedulers from launching the same account queue."""

    def __init__(self, state_path: Path) -> None:
        self.path = state_path.expanduser().resolve().with_suffix(".lock")
        self._descriptor: int | None = None

    def __enter__(self) -> Self:
        if fcntl is None:
            raise RuntimeError("gpu-queue run locking requires Linux fcntl support")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            os.close(descriptor)
            raise RuntimeError(
                f"another scheduler already holds queue lock: {self.path}"
            ) from error
        os.ftruncate(descriptor, 0)
        os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
        self._descriptor = descriptor
        return self

    def __exit__(self, *_args: object) -> None:
        if self._descriptor is None or fcntl is None:
            return
        fcntl.flock(self._descriptor, fcntl.LOCK_UN)
        os.close(self._descriptor)
        self._descriptor = None


def process_is_alive(pid: int | None) -> bool:
    """Return whether a process exists, including inaccessible live processes."""

    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
