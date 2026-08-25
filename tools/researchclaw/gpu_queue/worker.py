"""Crash-tolerant task worker used by the GPU queue scheduler."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    temporary.chmod(0o600)
    temporary.replace(path)
    path.chmod(0o600)


def _terminate_process_group(
    process_group_id: int, *, grace_seconds: float = 30.0
) -> None:
    try:
        os.killpg(process_group_id, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        try:
            os.killpg(process_group_id, 0)
        except ProcessLookupError:
            return
        time.sleep(0.2)
    try:
        os.killpg(process_group_id, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_worker(spec_path: Path, completion_path: Path) -> int:
    """Execute a task and always write a machine-readable completion record."""

    os.umask(0o077)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    command = spec["command"]
    cwd = spec["cwd"]
    environment = os.environ.copy()
    environment.update(spec.get("env", {}))
    timeout_seconds = int(spec.get("timeout_seconds", 0))
    runtime_path = completion_path.with_name("runtime.json")
    started_at = _utc_now()
    child: subprocess.Popen[bytes] | None = None
    stop_requested = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    try:
        child = subprocess.Popen(
            command, cwd=cwd, env=environment, start_new_session=True
        )
        child_pgid = os.getpgid(child.pid)
        _atomic_json(
            runtime_path,
            {"child_pid": child.pid, "child_pgid": child_pgid},
        )
        deadline = None if timeout_seconds == 0 else time.monotonic() + timeout_seconds
        timed_out = False
        while child.poll() is None:
            if stop_requested or (
                deadline is not None and time.monotonic() >= deadline
            ):
                timed_out = not stop_requested
                try:
                    os.killpg(child_pgid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(child_pgid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait()
                break
            time.sleep(0.2)
        raw_exit_code = child.returncode
        _terminate_process_group(child_pgid, grace_seconds=2.0)
        exit_code = 124 if timed_out else 143 if stop_requested else raw_exit_code
        _atomic_json(
            completion_path,
            {
                "started_at": started_at,
                "ended_at": _utc_now(),
                "exit_code": exit_code,
                "raw_exit_code": raw_exit_code,
                "timed_out": timed_out,
                "stop_requested": stop_requested,
            },
        )
        return int(exit_code or 0)
    except BaseException as error:  # noqa: BLE001
        if child is not None and child.poll() is None:
            try:
                os.killpg(os.getpgid(child.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
        _atomic_json(
            completion_path,
            {
                "started_at": started_at,
                "ended_at": _utc_now(),
                "exit_code": 125,
                "error": f"{type(error).__name__}: {error}",
            },
        )
        return 125


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for internal worker launches."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--completion", type=Path, required=True)
    args = parser.parse_args(argv)
    return run_worker(args.spec, args.completion)


if __name__ == "__main__":
    raise SystemExit(main())
