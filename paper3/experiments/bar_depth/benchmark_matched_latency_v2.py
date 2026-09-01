"""Run one preregistered exclusive W07-v2 latency session."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from .benchmark_matched_latency import (
    _gpu_compute_pids,
    _load_rgb,
    _physical_gpu_index,
    _selected_regions,
)
from .core import extract_square_context, make_regions
from .io_utils import (
    canonical_json_digest,
    file_digest,
    read_json,
    read_jsonl,
    write_json_atomic,
)
from .merge_variants import patch_refined_core
from .run_oracle_canary import DepthAnythingV2Backend, _source_revision

STAGE_NAMES = (
    "model_preprocess",
    "base_forward",
    "selector",
    "patch_forward",
    "merge",
    "output_resize",
    "orchestration",
)


def validate_latency_config(
    config: dict[str, Any], direct_config: dict[str, Any]
) -> None:
    """Reject a W07-v2 contract that weakens the review-mandated protocol."""
    latency = config["latency"]
    if config["schema_version"] != 2:
        raise ValueError("W07-v2 requires schema version 2")
    if config["independent_sessions"] != ["run1", "run2"]:
        raise ValueError("W07-v2 requires exactly two independent sessions")
    if int(latency["expected_cross_scan_images"]) != 20:
        raise ValueError("W07-v2 requires 20 cross-scan timing images")
    if len(latency["timing_sample_indices"]) != 20:
        raise ValueError("W07-v2 timing indices must contain 20 images")
    if int(latency["timed_repetitions_per_image"]) != 10:
        raise ValueError("W07-v2 requires ten timed repetitions per image")
    if int(latency["warmup_repetitions_per_method"]) < 20:
        raise ValueError("W07-v2 requires at least 20 warm-ups per method")
    if latency["percentiles"] != [50, 90, 95]:
        raise ValueError("W07-v2 must report p50, p90, and p95")
    if tuple(latency["stage_names"]) != STAGE_NAMES:
        raise ValueError("W07-v2 stage schema changed")
    if float(latency["monitor"]["poll_seconds"]) > 1.0:
        raise ValueError("Compute PID polling must occur at least once per second")
    sizes = [int(value) for value in direct_config["whole_image_input_sizes"]]
    if sizes != list(range(518, 2031, 56)):
        raise ValueError("Direct candidate sizes must be 518..2030 in steps of 56")


def _gpu_state(physical_index: int) -> dict[str, Any]:
    fields = (
        "clocks.current.sm",
        "clocks.current.memory",
        "power.draw",
        "power.limit",
        "pstate",
        "persistence_mode",
        "memory.used",
        "utilization.gpu",
    )
    result = subprocess.run(
        [
            "nvidia-smi",
            "-i",
            str(physical_index),
            f"--query-gpu={','.join(fields)}",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    values = [value.strip() for value in result.stdout.strip().split(",")]
    if len(values) != len(fields):
        raise ValueError("Unexpected nvidia-smi telemetry schema")

    def numeric(value: str) -> float | None:
        try:
            return float(value)
        except ValueError:
            return None

    return {
        "sm_clock_mhz": numeric(values[0]),
        "memory_clock_mhz": numeric(values[1]),
        "power_draw_watts": numeric(values[2]),
        "power_limit_watts": numeric(values[3]),
        "pstate": values[4],
        "persistence_mode": values[5],
        "memory_used_mib": numeric(values[6]),
        "gpu_utilization_percent": numeric(values[7]),
    }


class _GpuMonitor:
    def __init__(self, physical_index: int, poll_seconds: float) -> None:
        self.physical_index = physical_index
        self.poll_seconds = poll_seconds
        self.started = time.monotonic()
        self.samples: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        """Start continuous GPU process and hardware-state sampling."""
        self._thread.start()

    def stop(self) -> None:
        """Stop sampling and wait for the monitor thread."""
        self._stop.set()
        self._thread.join(timeout=max(5.0, 2.0 * self.poll_seconds))
        if self._thread.is_alive():
            self.errors.append("monitor_thread_did_not_stop")

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.samples.append(
                    {
                        "elapsed_seconds": time.monotonic() - self.started,
                        "compute_pids": _gpu_compute_pids(self.physical_index),
                        **_gpu_state(self.physical_index),
                    }
                )
            except (OSError, subprocess.SubprocessError, ValueError) as error:
                self.errors.append(type(error).__name__)
            self._stop.wait(self.poll_seconds)


def _profiled_infer(
    backend: DepthAnythingV2Backend, images: list[np.ndarray]
) -> tuple[list[np.ndarray], dict[str, float]]:
    torch = backend.torch
    totals = {
        "model_preprocess": 0.0,
        "model_forward": 0.0,
        "output_resize": 0.0,
    }
    outputs: list[np.ndarray] = []
    if backend.device.type == "cuda":
        torch.cuda.synchronize(backend.device)
    total_started = time.perf_counter()
    for start in range(0, len(images), backend.batch_size):
        batch_images = images[start : start + backend.batch_size]
        started = time.perf_counter()
        batch = backend._prepare(batch_images)
        if backend.device.type == "cuda":
            torch.cuda.synchronize(backend.device)
        totals["model_preprocess"] += (time.perf_counter() - started) * 1000.0

        started = time.perf_counter()
        with torch.inference_mode():
            prediction = backend.model(batch)
        if backend.device.type == "cuda":
            torch.cuda.synchronize(backend.device)
        totals["model_forward"] += (time.perf_counter() - started) * 1000.0

        started = time.perf_counter()
        if prediction.ndim == 4:
            prediction = prediction[:, 0]
        for index, image in enumerate(batch_images):
            resized = torch.nn.functional.interpolate(
                prediction[index][None, None],
                size=image.shape[:2],
                mode="bilinear",
                align_corners=True,
            )[0, 0]
            outputs.append(resized.float().cpu().numpy())
        if backend.device.type == "cuda":
            torch.cuda.synchronize(backend.device)
        totals["output_resize"] += (time.perf_counter() - started) * 1000.0
    totals["end_to_end"] = (time.perf_counter() - total_started) * 1000.0
    totals["orchestration"] = max(
        0.0,
        totals["end_to_end"]
        - totals["model_preprocess"]
        - totals["model_forward"]
        - totals["output_resize"],
    )
    return outputs, totals


def _direct_profile(
    backend: DepthAnythingV2Backend, image: np.ndarray, input_size: int
) -> tuple[np.ndarray, dict[str, float]]:
    backend.input_size = input_size
    outputs, profile = _profiled_infer(backend, [image])
    stages = {name: 0.0 for name in STAGE_NAMES}
    stages["model_preprocess"] = profile["model_preprocess"]
    stages["base_forward"] = profile["model_forward"]
    stages["output_resize"] = profile["output_resize"]
    stages["orchestration"] = profile["orchestration"]
    stages["end_to_end"] = profile["end_to_end"]
    return outputs[0], stages


def _regional_profile(
    *,
    backend: DepthAnythingV2Backend,
    image: np.ndarray,
    base_config: dict[str, Any],
    budget_count: int,
) -> tuple[np.ndarray, dict[str, float]]:
    torch = backend.torch
    if backend.device.type == "cuda":
        torch.cuda.synchronize(backend.device)
    total_started = time.perf_counter()
    backend.input_size = int(base_config["model"]["input_size"])
    base_outputs, base_profile = _profiled_infer(backend, [image])
    base_disparity = base_outputs[0].astype(np.float64)

    started = time.perf_counter()
    regions = make_regions(
        image.shape[0],
        image.shape[1],
        int(base_config["regions"]["rows"]),
        int(base_config["regions"]["columns"]),
        float(base_config["regions"]["context_scale"]),
    )
    selected = _selected_regions(image, base_disparity, regions, budget_count)
    selected_regions = [regions[int(index)] for index in selected]
    patch_images = [
        extract_square_context(image, region) for region in selected_regions
    ]
    selector_milliseconds = (time.perf_counter() - started) * 1000.0

    patch_outputs, patch_profile = _profiled_infer(backend, patch_images)
    started = time.perf_counter()
    refined = base_disparity.copy()
    for region, patch_disparity in zip(selected_regions, patch_outputs, strict=True):
        refined_core, _, _ = patch_refined_core(
            extract_square_context(base_disparity, region),
            patch_disparity.astype(np.float64),
            region,
            variant="highpass_residual",
            sigma_fraction=float(base_config["merge"]["gaussian_sigma_fraction"]),
            feather_fraction=float(base_config["regions"]["feather_fraction"]),
            trim_quantile=float(base_config["merge"]["affine_trim_quantile"]),
            affine_iterations=int(base_config["merge"]["affine_iterations"]),
        )
        refined[region.y0 : region.y1, region.x0 : region.x1] = refined_core
    merge_milliseconds = (time.perf_counter() - started) * 1000.0
    if backend.device.type == "cuda":
        torch.cuda.synchronize(backend.device)
    end_to_end = (time.perf_counter() - total_started) * 1000.0
    stages = {
        "model_preprocess": (
            base_profile["model_preprocess"] + patch_profile["model_preprocess"]
        ),
        "base_forward": base_profile["model_forward"],
        "selector": selector_milliseconds,
        "patch_forward": patch_profile["model_forward"],
        "merge": merge_milliseconds,
        "output_resize": (
            base_profile["output_resize"] + patch_profile["output_resize"]
        ),
        "orchestration": 0.0,
        "end_to_end": end_to_end,
    }
    stages["orchestration"] = max(
        0.0,
        end_to_end - sum(stages[name] for name in STAGE_NAMES[:-1]),
    )
    return refined, stages


def _method_summary(
    rows: list[dict[str, Any]], percentiles: list[float]
) -> dict[str, Any]:
    ok_rows = [row for row in rows if row["status"] == "OK"]
    summary: dict[str, Any] = {
        "status_counts": dict(Counter(str(row["status"]) for row in rows)),
        "raw_row_count": len(rows),
        "ok_row_count": len(ok_rows),
    }
    if not ok_rows:
        return summary
    for field in ("milliseconds", *[f"{name}_milliseconds" for name in STAGE_NAMES]):
        values = np.asarray([float(row[field]) for row in ok_rows])
        summary[field.removesuffix("_milliseconds")] = {
            "mean_milliseconds": float(values.mean()),
            **{
                f"p{int(percentile)}_milliseconds": float(
                    np.percentile(values, percentile)
                )
                for percentile in percentiles
            },
        }
    summary["peak_gpu_memory_mib"] = float(
        max(float(row["peak_gpu_memory_mib"]) for row in ok_rows)
    )
    summary["throughput_images_per_second"] = {
        "mean": float(
            np.mean([float(row["throughput_images_per_second"]) for row in ok_rows])
        ),
        "median": float(
            np.median([float(row["throughput_images_per_second"]) for row in ok_rows])
        ),
    }
    summary["maximum_stage_sum_relative_error"] = float(
        max(float(row["stage_sum_relative_error"]) for row in ok_rows)
    )
    return summary


def benchmark_matched_latency_v2(
    *,
    dataset_root: Path,
    config_path: Path,
    source_root: Path,
    weights_path: Path,
    output_json: Path,
    session_id: str,
    device: str,
) -> dict[str, Any]:
    """Execute and persist one exclusive W07-v2 session."""
    import torch
    import torchvision

    config = read_json(config_path)
    direct_config_path = Path(config["direct_resolution_config"])
    if file_digest(direct_config_path) != config["direct_resolution_config_sha256"]:
        raise ValueError("Frozen direct-resolution contract changed")
    direct_config = read_json(direct_config_path)
    validate_latency_config(config, direct_config)
    if session_id not in config["independent_sessions"]:
        raise ValueError("Unknown W07-v2 session identifier")

    base_config_path = Path(direct_config["base_config"])
    manifest_path = Path(direct_config["manifest"])
    for digest_key, path in (
        ("base_config_sha256", base_config_path),
        ("manifest_sha256", manifest_path),
    ):
        if file_digest(path) != direct_config[digest_key]:
            raise ValueError(f"Frozen binding changed: {path}")
    base_config = read_json(base_config_path)
    manifest = {int(row["sample_index"]): row for row in read_jsonl(manifest_path)}
    timing_indices = [
        int(value) for value in config["latency"]["timing_sample_indices"]
    ]
    if len({str(manifest[index]["scan_id"]) for index in timing_indices}) != 20:
        raise ValueError("Timing images must cover 20 distinct scans")
    images = {
        index: _load_rgb(dataset_root, manifest[index]) for index in timing_indices
    }

    physical_index = _physical_gpu_index()
    precheck_pids = _gpu_compute_pids(physical_index)
    if precheck_pids:
        raise ValueError("Formal W07-v2 GPU is not exclusive before model load")
    source_revision = _source_revision(source_root)
    if source_revision != str(base_config["model"]["source_revision"]):
        raise ValueError("Depth Anything V2 source revision mismatch")
    if file_digest(weights_path) != str(base_config["model"]["weights_sha256"]):
        raise ValueError("Depth Anything V2 weights mismatch")

    monitor = _GpuMonitor(
        physical_index,
        float(config["latency"]["monitor"]["poll_seconds"]),
    )
    monitor.start()
    backend = DepthAnythingV2Backend(
        source_root=source_root,
        weights=weights_path,
        encoder=str(base_config["model"]["encoder"]),
        input_size=int(base_config["model"]["input_size"]),
        resize_multiple=int(base_config["model"]["resize_multiple"]),
        batch_size=int(direct_config["regional_pipeline"]["patch_batch_size"]),
        device=device,
    )
    sizes = [int(value) for value in direct_config["whole_image_input_sizes"]]
    methods = ["regional_k3", *[f"whole_image_{size}" for size in sizes]]

    def execute(method: str, image: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
        if method == "regional_k3":
            return _regional_profile(
                backend=backend,
                image=image,
                base_config=base_config,
                budget_count=int(direct_config["regional_pipeline"]["budget_count"]),
            )
        return _direct_profile(backend, image, int(method.rsplit("_", 1)[1]))

    warmup_count = int(config["latency"]["warmup_repetitions_per_method"])
    oom_methods: set[str] = set()
    for method_index, method in enumerate(methods):
        try:
            for warmup_index in range(warmup_count):
                sample_index = timing_indices[(method_index + warmup_index) % 20]
                execute(method, images[sample_index])
        except torch.cuda.OutOfMemoryError:
            if method == "regional_k3":
                monitor.stop()
                raise
            oom_methods.add(method)
            torch.cuda.empty_cache()

    repetitions = int(config["latency"]["timed_repetitions_per_image"])
    raw_rows: list[dict[str, Any]] = []
    for repeat_index in range(repetitions):
        for position, sample_index in enumerate(timing_indices):
            offset = (repeat_index * len(timing_indices) + position) % len(methods)
            ordered_methods = methods[offset:] + methods[:offset]
            for method in ordered_methods:
                base_row: dict[str, Any] = {
                    "session_id": session_id,
                    "sample_index": sample_index,
                    "scan_id": str(manifest[sample_index]["scan_id"]),
                    "repeat_index": repeat_index,
                    "method": method,
                }
                if method in oom_methods:
                    raw_rows.append({**base_row, "status": "OOM"})
                    continue
                try:
                    torch.cuda.reset_peak_memory_stats(backend.device)
                    output, stages = execute(method, images[sample_index])
                    if output.size == 0 or not np.isfinite(output.flat[0]):
                        raise ValueError(
                            "Timed pipeline returned an invalid prediction"
                        )
                    milliseconds = float(stages["end_to_end"])
                    stage_sum = sum(float(stages[name]) for name in STAGE_NAMES)
                    stage_error = abs(stage_sum - milliseconds) / milliseconds
                    raw_rows.append(
                        {
                            **base_row,
                            "status": "OK",
                            "milliseconds": milliseconds,
                            **{
                                f"{name}_milliseconds": float(stages[name])
                                for name in STAGE_NAMES
                            },
                            "stage_sum_relative_error": stage_error,
                            "peak_gpu_memory_mib": (
                                torch.cuda.max_memory_allocated(backend.device)
                                / (1024.0 * 1024.0)
                            ),
                            "throughput_images_per_second": 1000.0 / milliseconds,
                        }
                    )
                except torch.cuda.OutOfMemoryError:
                    if method == "regional_k3":
                        monitor.stop()
                        raise
                    oom_methods.add(method)
                    torch.cuda.empty_cache()
                    raw_rows.append({**base_row, "status": "OOM"})
    monitor.stop()

    own_pid = os.getpid()
    foreign_pids = sorted(
        {
            int(pid)
            for sample in monitor.samples
            for pid in sample["compute_pids"]
            if int(pid) != own_pid
        }
    )
    maximum_stage_error = float(
        max(
            (
                float(row["stage_sum_relative_error"])
                for row in raw_rows
                if row["status"] == "OK"
            ),
            default=0.0,
        )
    )
    expected_rows = int(config["latency"]["expected_timed_rows_per_method_per_session"])
    row_counts = Counter(str(row["method"]) for row in raw_rows)
    complete_counts = all(row_counts[method] == expected_rows for method in methods)
    stage_pass = maximum_stage_error <= float(
        config["latency"]["maximum_stage_sum_relative_error"]
    )
    valid_exclusive = not foreign_pids and not monitor.errors
    complete = complete_counts and stage_pass and valid_exclusive
    percentiles = [float(value) for value in config["latency"]["percentiles"]]
    summaries = {
        method: _method_summary(
            [row for row in raw_rows if row["method"] == method], percentiles
        )
        for method in methods
    }

    numeric_telemetry = {
        key: [
            float(sample[key])
            for sample in monitor.samples
            if sample.get(key) is not None
        ]
        for key in (
            "sm_clock_mhz",
            "memory_clock_mhz",
            "power_draw_watts",
            "power_limit_watts",
            "memory_used_mib",
            "gpu_utilization_percent",
        )
    }
    telemetry_summary = {
        key: {
            "minimum": min(values),
            "median": float(np.median(values)),
            "maximum": max(values),
        }
        for key, values in numeric_telemetry.items()
        if values
    }
    implementation_files = {
        path.name: file_digest(path)
        for path in (
            Path(__file__),
            Path(__file__).with_name("benchmark_matched_latency.py"),
            Path(__file__).with_name("run_oracle_canary.py"),
            Path(__file__).with_name("merge_variants.py"),
            Path(__file__).with_name("core.py"),
        )
    }
    result = {
        "schema_version": 2,
        "status": (
            "COMPLETE_EXCLUSIVE_MATCHED_LATENCY_V2_SESSION"
            if complete
            else "INVALID_EXCLUSIVE_MATCHED_LATENCY_V2_SESSION"
        ),
        "session_id": session_id,
        "allocation_mode": "exclusive",
        "summaries": summaries,
        "raw_measurements": raw_rows,
        "oom_methods": sorted(oom_methods),
        "session_checks": {
            "expected_rows_per_method": expected_rows,
            "row_counts": dict(row_counts),
            "complete_row_counts": complete_counts,
            "maximum_stage_sum_relative_error": maximum_stage_error,
            "stage_sum_pass": stage_pass,
            "monitor_sample_count": len(monitor.samples),
            "monitor_errors": monitor.errors,
            "foreign_compute_pids": foreign_pids,
            "exclusive_process_audit_pass": valid_exclusive,
        },
        "gpu_monitor": {
            "poll_seconds": monitor.poll_seconds,
            "telemetry_summary": telemetry_summary,
            "pstates": sorted({str(row["pstate"]) for row in monitor.samples}),
            "persistence_modes": sorted(
                {str(row["persistence_mode"]) for row in monitor.samples}
            ),
            "samples": monitor.samples,
        },
        "bindings": {
            "config_sha256": file_digest(config_path),
            "direct_resolution_config_sha256": file_digest(direct_config_path),
            "source_revision": source_revision,
            "weights_sha256": file_digest(weights_path),
            "implementation_files_sha256": implementation_files,
            "implementation_canonical_sha256": canonical_json_digest(
                implementation_files
            ),
        },
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "torch": torch.__version__,
            "torchvision": torchvision.__version__,
            "cuda": torch.version.cuda,
            "device": device,
            "gpu": torch.cuda.get_device_name(torch.device(device)),
        },
    }
    write_json_atomic(output_json, result)
    return result


def parse_args() -> argparse.Namespace:
    """Parse the W07-v2 session command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--session-id", choices=("run1", "run2"), required=True)
    parser.add_argument("--device", default="cuda:0")
    return parser.parse_args()


def main() -> None:
    """Run one exclusive W07-v2 session."""
    args = parse_args()
    result = benchmark_matched_latency_v2(
        dataset_root=args.dataset_root,
        config_path=args.config,
        source_root=args.source_root,
        weights_path=args.weights,
        output_json=args.output_json,
        session_id=args.session_id,
        device=args.device,
    )
    print(result["status"])
    if result["status"] != "COMPLETE_EXCLUSIVE_MATCHED_LATENCY_V2_SESSION":
        raise SystemExit(4)


if __name__ == "__main__":
    main()
