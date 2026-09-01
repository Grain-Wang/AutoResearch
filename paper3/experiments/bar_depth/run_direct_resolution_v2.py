"""Run the closed-range W07-v2 whole-image accuracy sweep with OOM records."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import scipy
from PIL import __version__ as pillow_version

from .core import depth_boundary_weights
from .io_utils import (
    canonical_json_digest,
    file_digest,
    read_json,
    read_jsonl,
    write_csv_atomic,
    write_json_atomic,
)
from .run_direct_resolution import _aligned_error
from .run_oracle_canary import DepthAnythingV2Backend, _load_sample, _source_revision


def _empty_candidate_row(
    record: dict[str, Any], input_size: int, status: str
) -> dict[str, Any]:
    return {
        "sample_index": int(record["sample_index"]),
        "domain": str(record["domain"]),
        "scene_id": str(record["scene_id"]),
        "scan_id": str(record["scan_id"]),
        "image_relpath": str(record["image_relpath"]),
        "input_size": input_size,
        "status": status,
        "target_height": None,
        "target_width": None,
        "valid_pixel_count": None,
        "boundary_pixel_count": None,
        "weight_sum": None,
        "base_primary_error_sum": None,
        "primary_error_sum": None,
        "primary_utility_sum": None,
        "base_absrel_error_sum": None,
        "absrel_error_sum": None,
        "absrel_utility_sum": None,
        "metric_scale": None,
        "forward_milliseconds": None,
    }


def _process_sample_v2(
    *,
    backend: DepthAnythingV2Backend,
    dataset_root: Path,
    record: dict[str, Any],
    base_config: dict[str, Any],
    input_sizes: list[int],
    known_oom_sizes: set[int],
) -> tuple[list[dict[str, Any]], set[int]]:
    torch = backend.torch
    image, depth, valid = _load_sample(dataset_root, record, base_config["metric"])
    weights, boundary = depth_boundary_weights(
        depth,
        valid,
        gradient_quantile=float(base_config["metric"]["boundary_gradient_quantile"]),
        boundary_weight=float(base_config["metric"]["boundary_weight"]),
    )
    base_input_size = int(base_config["model"]["input_size"])
    backend.input_size = base_input_size
    base_outputs, base_milliseconds = backend.infer([image])
    base_disparity = base_outputs[0].astype(np.float64)
    base_error, base_scale = _aligned_error(
        base_disparity, depth, valid, base_config["metric"]
    )
    base_primary = float(np.sum(weights * base_error))
    base_absrel = float(np.sum(valid * base_error))

    rows: list[dict[str, Any]] = []
    newly_oom: set[int] = set()
    for input_size in input_sizes:
        if input_size in known_oom_sizes:
            rows.append(_empty_candidate_row(record, input_size, "OOM"))
            continue
        backend.input_size = input_size
        target_height, target_width = backend._target_shape(*image.shape[:2])
        try:
            if input_size == base_input_size:
                disparity = base_disparity
                forward_milliseconds = base_milliseconds
                error = base_error
                scale = base_scale
            else:
                try:
                    outputs, forward_milliseconds = backend.infer([image])
                except torch.cuda.OutOfMemoryError:
                    torch.cuda.empty_cache()
                    outputs, forward_milliseconds = backend.infer([image])
                disparity = outputs[0].astype(np.float64)
                error, scale = _aligned_error(
                    disparity, depth, valid, base_config["metric"]
                )
        except torch.cuda.OutOfMemoryError:
            if input_size == base_input_size:
                raise
            torch.cuda.empty_cache()
            newly_oom.add(input_size)
            rows.append(_empty_candidate_row(record, input_size, "OOM"))
            continue
        primary_error = float(np.sum(weights * error))
        absrel_error = float(np.sum(valid * error))
        rows.append(
            {
                "sample_index": int(record["sample_index"]),
                "domain": str(record["domain"]),
                "scene_id": str(record["scene_id"]),
                "scan_id": str(record["scan_id"]),
                "image_relpath": str(record["image_relpath"]),
                "input_size": input_size,
                "status": "OK",
                "target_height": target_height,
                "target_width": target_width,
                "valid_pixel_count": int(valid.sum()),
                "boundary_pixel_count": int(boundary.sum()),
                "weight_sum": float(weights.sum()),
                "base_primary_error_sum": base_primary,
                "primary_error_sum": primary_error,
                "primary_utility_sum": base_primary - primary_error,
                "base_absrel_error_sum": base_absrel,
                "absrel_error_sum": absrel_error,
                "absrel_utility_sum": base_absrel - absrel_error,
                "metric_scale": scale,
                "forward_milliseconds": forward_milliseconds,
            }
        )
    return rows, newly_oom


def run_direct_resolution_v2(
    *,
    dataset_root: Path,
    config_path: Path,
    source_root: Path,
    weights_path: Path,
    cache_dir: Path,
    output_csv: Path,
    output_provenance: Path,
    device: str,
) -> dict[str, Any]:
    """Run or resume all 28 frozen direct-resolution candidates."""
    import torch
    import torchvision

    config = read_json(config_path)
    if config["schema_version"] != 2:
        raise ValueError("Direct-resolution v2 requires schema version 2")
    input_sizes = [int(value) for value in config["whole_image_input_sizes"]]
    if input_sizes != list(range(518, 2031, 56)):
        raise ValueError("Direct-resolution v2 grid must be 518..2030 by 56")
    base_config_path = Path(config["base_config"])
    merge_config_path = Path(config["merge_config"])
    manifest_path = Path(config["manifest"])
    for digest_key, path in (
        ("base_config_sha256", base_config_path),
        ("merge_config_sha256", merge_config_path),
        ("manifest_sha256", manifest_path),
    ):
        if file_digest(path) != config[digest_key]:
            raise ValueError(f"Frozen binding changed: {path}")
    base_config = read_json(base_config_path)
    manifest = read_jsonl(manifest_path)
    if len(manifest) != int(config["accuracy"]["expected_sample_count"]):
        raise ValueError("Unexpected direct-resolution manifest size")
    source_revision = _source_revision(source_root)
    if source_revision != str(base_config["model"]["source_revision"]):
        raise ValueError("Depth Anything V2 source revision mismatch")
    if file_digest(weights_path) != str(base_config["model"]["weights_sha256"]):
        raise ValueError("Depth Anything V2 weights mismatch")

    implementation_files = {
        path.name: file_digest(path)
        for path in (
            Path(__file__),
            Path(__file__).with_name("run_direct_resolution.py"),
            Path(__file__).with_name("run_oracle_canary.py"),
            Path(__file__).with_name("core.py"),
        )
    }
    contract = {
        "config_sha256": file_digest(config_path),
        "source_revision": source_revision,
        "weights_sha256": file_digest(weights_path),
        "implementation_files_sha256": implementation_files,
        "implementation_canonical_sha256": canonical_json_digest(implementation_files),
        "device": device,
    }
    contract_sha256 = canonical_json_digest(contract)
    cache_dir.mkdir(parents=True, exist_ok=True)
    contract_path = cache_dir / "run_contract.json"
    if contract_path.exists() and read_json(contract_path) != contract:
        raise ValueError("Resume cache contract does not match v2 sweep")
    write_json_atomic(contract_path, contract)

    backend = DepthAnythingV2Backend(
        source_root=source_root,
        weights=weights_path,
        encoder=str(base_config["model"]["encoder"]),
        input_size=int(base_config["model"]["input_size"]),
        resize_multiple=int(base_config["model"]["resize_multiple"]),
        batch_size=1,
        device=device,
    )
    all_rows: list[dict[str, Any]] = []
    oom_sizes: set[int] = set()
    for position, record in enumerate(manifest, start=1):
        sample_index = int(record["sample_index"])
        cache_path = cache_dir / f"sample-{sample_index:04d}.json"
        if cache_path.exists():
            cached = read_json(cache_path)
            if cached.get("contract_sha256") != contract_sha256:
                raise ValueError(f"Stale direct-resolution cache in {cache_path}")
            rows = list(cached["rows"])
            cached_oom = {int(value) for value in cached.get("newly_oom_sizes", [])}
        else:
            rows, cached_oom = _process_sample_v2(
                backend=backend,
                dataset_root=dataset_root,
                record=record,
                base_config=base_config,
                input_sizes=input_sizes,
                known_oom_sizes=oom_sizes,
            )
            write_json_atomic(
                cache_path,
                {
                    "contract_sha256": contract_sha256,
                    "newly_oom_sizes": sorted(cached_oom),
                    "rows": rows,
                },
            )
        oom_sizes.update(cached_oom)
        all_rows.extend(rows)
        if position % 10 == 0 or position == len(manifest):
            print(f"processed {position}/{len(manifest)}", file=sys.stderr)
    expected_rows = len(manifest) * len(input_sizes)
    if len(all_rows) != expected_rows:
        raise ValueError("Direct-resolution v2 output matrix is incomplete")
    write_csv_atomic(output_csv, all_rows)
    status_by_size = {
        str(input_size): (
            "OOM"
            if any(
                row["status"] == "OOM" and int(row["input_size"]) == input_size
                for row in all_rows
            )
            else "OK"
        )
        for input_size in input_sizes
    }
    provenance = {
        "schema_version": 2,
        "status": "COMPLETE_DIRECT_RESOLUTION_V2_MATRIX",
        "sample_count": len(manifest),
        "candidate_count": len(input_sizes),
        "row_count": len(all_rows),
        "candidate_status": status_by_size,
        "oom_sizes": sorted(oom_sizes),
        "output_csv_sha256": file_digest(output_csv),
        "contract": contract,
        "contract_sha256": contract_sha256,
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "opencv": cv2.__version__,
            "pillow": pillow_version,
            "torch": torch.__version__,
            "torchvision": torchvision.__version__,
            "cuda": torch.version.cuda,
            "device": device,
            "gpu": torch.cuda.get_device_name(torch.device(device)),
        },
    }
    write_json_atomic(output_provenance, provenance)
    return provenance


def parse_args() -> argparse.Namespace:
    """Parse the direct-resolution v2 command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-provenance", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    return parser.parse_args()


def main() -> None:
    """Run the frozen 28-candidate accuracy sweep."""
    args = parse_args()
    provenance = run_direct_resolution_v2(
        dataset_root=args.dataset_root,
        config_path=args.config,
        source_root=args.source_root,
        weights_path=args.weights,
        cache_dir=args.cache_dir,
        output_csv=args.output_csv,
        output_provenance=args.output_provenance,
        device=args.device,
    )
    print(provenance["status"])


if __name__ == "__main__":
    main()
