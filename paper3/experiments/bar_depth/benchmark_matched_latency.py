"""Benchmark frozen regional and whole-image W07 pipelines on one GPU."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .analyze_budget_baselines import _rank_sum
from .core import extract_square_context, gradient_score, make_regions
from .io_utils import (
    canonical_json_digest,
    file_digest,
    read_json,
    read_jsonl,
    write_json_atomic,
)
from .merge_variants import patch_refined_core
from .run_oracle_canary import DepthAnythingV2Backend, _source_revision


def _implementation_hashes() -> dict[str, str]:
    module_root = Path(__file__).resolve().parent
    names = (
        "analyze_budget_baselines.py",
        "benchmark_matched_latency.py",
        "core.py",
        "io_utils.py",
        "merge_variants.py",
        "run_oracle_canary.py",
    )
    return {name: file_digest(module_root / name) for name in names}


def _load_rgb(dataset_root: Path, record: dict[str, Any]) -> np.ndarray:
    with Image.open(dataset_root / record["image_relpath"]) as image_file:
        return np.asarray(image_file.convert("RGB"), dtype=np.float64) / 255.0


def _gpu_compute_pids(physical_index: int) -> list[int]:
    result = subprocess.run(
        [
            "nvidia-smi",
            "-i",
            str(physical_index),
            "--query-compute-apps=pid",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted(
        int(line.strip())
        for line in result.stdout.splitlines()
        if line.strip().isdigit()
    )


def _physical_gpu_index() -> int:
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    pieces = [piece.strip() for piece in visible.split(",") if piece.strip()]
    if len(pieces) != 1 or not pieces[0].isdigit():
        raise ValueError(
            "Formal timing requires one numeric CUDA_VISIBLE_DEVICES entry"
        )
    return int(pieces[0])


def _selected_regions(
    image: np.ndarray,
    base_disparity: np.ndarray,
    regions: list[Any],
    budget_count: int,
) -> np.ndarray:
    rgb_scores = [gradient_score(image, region) for region in regions]
    base_scores = [gradient_score(base_disparity, region) for region in regions]
    scores = _rank_sum(rgb_scores) + _rank_sum(base_scores)
    return np.argsort(-scores, kind="stable")[:budget_count]


def _regional_pipeline(
    *,
    backend: DepthAnythingV2Backend,
    image: np.ndarray,
    base_config: dict[str, Any],
    budget_count: int,
) -> np.ndarray:
    backend.input_size = int(base_config["model"]["input_size"])
    base_disparity = backend.infer([image])[0][0].astype(np.float64)
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
    patch_outputs = backend.infer(patch_images)[0]
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
    return refined


def _direct_pipeline(
    backend: DepthAnythingV2Backend, image: np.ndarray, input_size: int
) -> np.ndarray:
    backend.input_size = input_size
    return backend.infer([image])[0][0]


def _milliseconds(call: Callable[[], np.ndarray]) -> float:
    started = time.perf_counter()
    output = call()
    elapsed = (time.perf_counter() - started) * 1000.0
    if output.size == 0 or not np.isfinite(output.flat[0]):
        raise ValueError("Timed pipeline returned an invalid prediction")
    return elapsed


def benchmark_matched_latency(
    *,
    dataset_root: Path,
    config_path: Path,
    source_root: Path,
    weights_path: Path,
    output_json: Path,
    device: str,
    allocation_mode: str,
) -> dict[str, Any]:
    """Benchmark W07 methods under an explicit exclusive or diagnostic mode."""
    import torch
    import torchvision

    config = read_json(config_path)
    base_config_path = Path(config["base_config"])
    merge_config_path = Path(config["merge_config"])
    manifest_path = Path(config["manifest"])
    for path_key, digest_key, path in (
        ("base_config", "base_config_sha256", base_config_path),
        ("merge_config", "merge_config_sha256", merge_config_path),
        ("manifest", "manifest_sha256", manifest_path),
    ):
        if file_digest(path) != str(config[digest_key]):
            raise ValueError(f"Frozen {path_key} binding changed")
    base_config = read_json(base_config_path)
    manifest = {int(row["sample_index"]): row for row in read_jsonl(manifest_path)}
    timing_indices = [
        int(value) for value in config["latency"]["timing_sample_indices"]
    ]
    images = {
        index: _load_rgb(dataset_root, manifest[index]) for index in timing_indices
    }
    if allocation_mode not in {"exclusive", "shared_diagnostic"}:
        raise ValueError("Unknown latency allocation mode")
    physical_index = _physical_gpu_index()
    precheck_pids = _gpu_compute_pids(physical_index)
    if allocation_mode == "exclusive" and precheck_pids:
        raise ValueError(
            f"Timing GPU is not exclusive before model load: {precheck_pids}"
        )
    source_revision = _source_revision(source_root)
    if source_revision != str(base_config["model"]["source_revision"]):
        raise ValueError("Depth Anything V2 source revision mismatch")
    if file_digest(weights_path) != str(base_config["model"]["weights_sha256"]):
        raise ValueError("Depth Anything V2 weights mismatch")
    backend = DepthAnythingV2Backend(
        source_root=source_root,
        weights=weights_path,
        encoder=str(base_config["model"]["encoder"]),
        input_size=int(base_config["model"]["input_size"]),
        resize_multiple=int(base_config["model"]["resize_multiple"]),
        batch_size=int(config["regional_pipeline"]["patch_batch_size"]),
        device=device,
    )
    input_sizes = [int(value) for value in config["whole_image_input_sizes"]]
    methods = ["regional_k3", *[f"whole_image_{value}" for value in input_sizes]]

    def execute(method: str, image: np.ndarray) -> np.ndarray:
        if method == "regional_k3":
            return _regional_pipeline(
                backend=backend,
                image=image,
                base_config=base_config,
                budget_count=int(config["regional_pipeline"]["budget_count"]),
            )
        return _direct_pipeline(backend, image, int(method.rsplit("_", 1)[1]))

    warmup_count = int(config["latency"]["warmup_images"])
    warmup_indices = timing_indices[:warmup_count]
    for method in methods:
        for sample_index in warmup_indices:
            execute(method, images[sample_index])

    raw_rows: list[dict[str, Any]] = []
    for position, sample_index in enumerate(timing_indices):
        ordered_methods = (
            methods[position % len(methods) :] + methods[: position % len(methods)]
        )
        for method in ordered_methods:
            elapsed = _milliseconds(
                lambda method=method, sample_index=sample_index: execute(
                    method, images[sample_index]
                )
            )
            raw_rows.append(
                {
                    "sample_index": sample_index,
                    "scan_id": str(manifest[sample_index]["scan_id"]),
                    "method": method,
                    "milliseconds": elapsed,
                }
            )
    postcheck_pids = _gpu_compute_pids(physical_index)
    unexpected_pids = [pid for pid in postcheck_pids if pid != os.getpid()]
    if allocation_mode == "exclusive" and unexpected_pids:
        raise ValueError(f"Timing GPU lost exclusivity: {unexpected_pids}")

    percentiles = [float(value) for value in config["latency"]["percentiles"]]
    summaries: dict[str, dict[str, float]] = {}
    for method in methods:
        values = np.asarray(
            [row["milliseconds"] for row in raw_rows if row["method"] == method],
            dtype=np.float64,
        )
        summaries[method] = {
            "mean_milliseconds": float(values.mean()),
            **{
                f"p{int(percentile)}_milliseconds": float(
                    np.percentile(values, percentile)
                )
                for percentile in percentiles
            },
        }
    implementation_hashes = _implementation_hashes()
    result = {
        "schema_version": 1,
        "status": (
            "COMPLETE_EXCLUSIVE_MATCHED_LATENCY"
            if allocation_mode == "exclusive"
            else "COMPLETE_SHARED_DIAGNOSTIC_MATCHED_LATENCY"
        ),
        "allocation_mode": allocation_mode,
        "summaries": summaries,
        "raw_measurements": raw_rows,
        "exclusive_gpu_audit": {
            "physical_index": physical_index,
            "precheck_compute_pids": precheck_pids,
            "postcheck_compute_pids": postcheck_pids,
            "foreign_postcheck_compute_pids": unexpected_pids,
            "own_pid": os.getpid(),
        },
        "bindings": {
            "config_sha256": file_digest(config_path),
            "source_revision": source_revision,
            "weights_sha256": file_digest(weights_path),
            "implementation_files_sha256": implementation_hashes,
            "implementation_canonical_sha256": canonical_json_digest(
                implementation_hashes
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
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument(
        "--allocation-mode",
        choices=("exclusive", "shared_diagnostic"),
        default="exclusive",
    )
    return parser.parse_args()


def main() -> None:
    """Run the exclusive W07 latency benchmark."""
    args = parse_args()
    result = benchmark_matched_latency(
        dataset_root=args.dataset_root,
        config_path=args.config,
        source_root=args.source_root,
        weights_path=args.weights,
        output_json=args.output_json,
        device=args.device,
        allocation_mode=args.allocation_mode,
    )
    print(result["status"])


if __name__ == "__main__":
    main()
