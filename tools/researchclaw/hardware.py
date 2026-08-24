"""Small, dependency-free helpers for local hardware and metric output."""

from __future__ import annotations

import platform
import subprocess
from dataclasses import asdict, dataclass

_LOG_WORDS = frozenset(
    {
        "completed",
        "debug",
        "downloading",
        "error",
        "evaluating",
        "experiment",
        "finished",
        "info",
        "loading",
        "processing",
        "running",
        "saving",
        "starting",
        "training",
        "warning",
    }
)


@dataclass(frozen=True)
class HardwareProfile:
    """Detected local accelerator capabilities."""

    has_gpu: bool
    gpu_type: str
    gpu_name: str
    vram_mb: int | None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""

        return asdict(self)


def detect_hardware() -> HardwareProfile:
    """Detect local NVIDIA or Apple-Silicon acceleration without mutation."""

    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            name, memory, *_ = (
                item.strip() for item in completed.stdout.splitlines()[0].split(",")
            )
            return HardwareProfile(True, "cuda", name, int(float(memory)))
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired, ValueError):
        pass
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return HardwareProfile(True, "mps", "Apple Silicon GPU", None)
    return HardwareProfile(False, "cpu", "CPU only", None)


def is_metric_name(name: str) -> bool:
    """Return whether a token looks like a metric rather than a log label."""

    words = name.lower().split()
    return (
        bool(words)
        and len(words) <= 6
        and not any(word in _LOG_WORDS for word in words)
    )
