"""NVIDIA GPU discovery and conservative idle tracking."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class GpuSnapshot:
    """One point-in-time GPU observation."""

    index: int
    uuid: str
    memory_used_mib: int
    utilization_percent: int
    compute_pids: tuple[int, ...] = ()

    def is_idle(
        self,
        *,
        memory_used_limit_mib: int,
        utilization_limit_percent: int,
    ) -> bool:
        """Return whether the observation satisfies the strict idle contract."""

        return (
            not self.compute_pids
            and self.memory_used_mib < memory_used_limit_mib
            and self.utilization_percent < utilization_limit_percent
        )


def _run_nvidia_smi(arguments: list[str]) -> str:
    result = subprocess.run(
        ["nvidia-smi", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"nvidia-smi failed with exit {result.returncode}: {detail}")
    return result.stdout


def probe_gpus() -> tuple[GpuSnapshot, ...]:
    """Query GPU utilization and compute processes with ``nvidia-smi``."""

    gpu_output = _run_nvidia_smi(
        [
            "--query-gpu=index,uuid,memory.used,utilization.gpu",
            "--format=csv,noheader,nounits",
        ]
    )
    process_output = _run_nvidia_smi(
        [
            "--query-compute-apps=gpu_uuid,pid",
            "--format=csv,noheader,nounits",
        ]
    )
    pids_by_uuid: dict[str, list[int]] = {}
    for line in process_output.splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 2:
            raise RuntimeError(f"unexpected nvidia-smi compute row: {line!r}")
        try:
            pid = int(parts[1])
        except ValueError as error:
            raise RuntimeError(f"invalid compute PID in row: {line!r}") from error
        pids_by_uuid.setdefault(parts[0], []).append(pid)

    snapshots: list[GpuSnapshot] = []
    for line in gpu_output.splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 4:
            raise RuntimeError(f"unexpected nvidia-smi GPU row: {line!r}")
        try:
            index = int(parts[0])
            memory_used = int(parts[2])
            utilization = int(parts[3])
        except ValueError as error:
            raise RuntimeError(f"invalid numeric GPU row: {line!r}") from error
        snapshots.append(
            GpuSnapshot(
                index=index,
                uuid=parts[1],
                memory_used_mib=memory_used,
                utilization_percent=utilization,
                compute_pids=tuple(sorted(pids_by_uuid.get(parts[1], ()))),
            )
        )
    if not snapshots:
        raise RuntimeError("nvidia-smi returned no GPUs")
    return tuple(sorted(snapshots, key=lambda snapshot: snapshot.index))


class IdleTracker:
    """Count consecutive qualifying observations for each GPU."""

    def __init__(self, required_samples: int) -> None:
        if required_samples <= 0:
            raise ValueError("required_samples must be positive")
        self.required_samples = required_samples
        self._counts: dict[int, int] = {}

    def observe(
        self,
        snapshots: tuple[GpuSnapshot, ...],
        *,
        memory_used_limit_mib: int,
        utilization_limit_percent: int,
        excluded_indices: set[int] | None = None,
    ) -> tuple[int, ...]:
        """Update counters and return GPUs that reached the idle threshold."""

        excluded = excluded_indices or set()
        seen: set[int] = set()
        ready: list[int] = []
        for snapshot in snapshots:
            seen.add(snapshot.index)
            if snapshot.index in excluded:
                self._counts[snapshot.index] = 0
                continue
            if snapshot.is_idle(
                memory_used_limit_mib=memory_used_limit_mib,
                utilization_limit_percent=utilization_limit_percent,
            ):
                self._counts[snapshot.index] = self._counts.get(snapshot.index, 0) + 1
            else:
                self._counts[snapshot.index] = 0
            if self._counts[snapshot.index] >= self.required_samples:
                ready.append(snapshot.index)
        for missing_index in set(self._counts) - seen:
            self._counts[missing_index] = 0
        return tuple(sorted(ready))

    def reset(self, gpu_index: int) -> None:
        """Reset a GPU after allocation or a failed second check."""

        self._counts[gpu_index] = 0
