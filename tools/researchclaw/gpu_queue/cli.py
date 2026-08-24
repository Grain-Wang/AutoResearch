"""Command-line interface for the cooperative GPU queue."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from researchclaw.gpu_queue.models import QueueConfig
from researchclaw.gpu_queue.scheduler import QueueScheduler, render_queue_plan
from researchclaw.gpu_queue.state import QueueRunLock, QueueState


def _required_path(value: str | None, *, flag: str) -> Path:
    if not value:
        raise ValueError(f"{flag} is required for this action")
    return Path(value)


def _existing_state(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"queue state does not exist: {path}")
    return path


def cmd_gpu_queue(args: argparse.Namespace) -> int:
    """Dispatch the ``researchclaw gpu-queue`` command family."""

    action = str(args.gpu_queue_action)
    try:
        if action == "validate":
            config = QueueConfig.load(_required_path(args.config, flag="--config"))
            print(f"Validated {len(config.tasks)} enabled tasks")
            print(render_queue_plan(config))
            return 0
        if action == "run":
            config = QueueConfig.load(_required_path(args.config, flag="--config"))
            if args.dry_run:
                print(render_queue_plan(config))
                return 0
            state_path = Path(args.state)
            with QueueRunLock(state_path), QueueState(state_path) as state:
                scheduler = QueueScheduler(config, state)
                return scheduler.run()
        if action == "status":
            with QueueState(_existing_state(args.state)) as state:
                records = state.records()
                if args.json:
                    print(
                        json.dumps(
                            [
                                {
                                    "task_id": record.task_id,
                                    "status": record.status.value,
                                    "attempts": record.attempts,
                                    "gpu_index": record.gpu_index,
                                    "worker_pid": record.worker_pid,
                                    "run_dir": record.run_dir,
                                    "exit_code": record.exit_code,
                                    "error": record.error,
                                }
                                for record in records
                            ],
                            indent=2,
                        )
                    )
                else:
                    print("TASK\tSTATUS\tATTEMPTS\tGPU\tPID")
                    for record in records:
                        print(
                            f"{record.task_id}\t{record.status.value}\t"
                            f"{record.attempts}\t"
                            f"{record.gpu_index if record.gpu_index is not None else '-'}\t"
                            f"{record.worker_pid if record.worker_pid is not None else '-'}"
                        )
                return 0
        if action == "stop":
            with QueueState(_existing_state(args.state)) as state:
                state.request_drain()
            print("Drain requested; no new tasks will launch")
            return 0
        if action == "retry":
            if not args.task_id:
                raise ValueError("TASK_ID is required for retry")
            with QueueState(_existing_state(args.state)) as state:
                state.retry(str(args.task_id))
            print(f"Reset {args.task_id} to PENDING")
            return 0
        raise ValueError(f"unknown gpu-queue action: {action}")
    except (FileNotFoundError, OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
