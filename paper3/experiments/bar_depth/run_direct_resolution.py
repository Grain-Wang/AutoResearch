"""Evaluate frozen whole-image DAV2-S resolution candidates for W07."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import scipy
from PIL import __version__ as pillow_version

from .core import (
    depth_boundary_weights,
    positive_median_scale_fit,
    prediction_error_maps,
)
from .io_utils import (
    canonical_json_digest,
    file_digest,
    read_json,
    read_jsonl,
    write_csv_atomic,
    write_json_atomic,
)
from .run_oracle_canary import DepthAnythingV2Backend, _load_sample, _source_revision


def _implementation_hashes() -> dict[str, str]:
    module_root = Path(__file__).resolve().parent
    names = (
        "core.py",
        "io_utils.py",
        "run_direct_resolution.py",
        "run_oracle_canary.py",
    )
    return {name: file_digest(module_root / name) for name in names}


def _aligned_error(
    disparity: np.ndarray,
    depth: np.ndarray,
    valid: np.ndarray,
    metric: dict[str, Any],
) -> tuple[np.ndarray, float]:
    inverse_gt = np.zeros_like(depth)
    inverse_gt[valid] = 1.0 / depth[valid]
    scale, shift = positive_median_scale_fit(disparity[valid], inverse_gt[valid])
    error, _ = prediction_error_maps(
        disparity,
        depth,
        valid,
        metric_scale=scale,
        metric_shift=shift,
        inverse_depth_epsilon=float(metric["inverse_depth_epsilon"]),
        min_depth=float(metric["min_depth"]),
        max_depth=float(metric["max_depth"]),
    )
    return error, scale


def _process_sample(
    *,
    backend: DepthAnythingV2Backend,
    dataset_root: Path,
    record: dict[str, Any],
    base_config: dict[str, Any],
    input_sizes: list[int],
) -> list[dict[str, Any]]:
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
    for input_size in input_sizes:
        backend.input_size = input_size
        target_height, target_width = backend._target_shape(*image.shape[:2])
        if input_size == base_input_size:
            disparity = base_disparity
            forward_milliseconds = base_milliseconds
            error = base_error
            scale = base_scale
        else:
            outputs, forward_milliseconds = backend.infer([image])
            disparity = outputs[0].astype(np.float64)
            error, scale = _aligned_error(
                disparity, depth, valid, base_config["metric"]
            )
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
    return rows


def run_direct_resolution(
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
    """Run or resume the frozen whole-image resolution accuracy sweep."""
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
    manifest = read_jsonl(manifest_path)
    if len(manifest) != int(config["accuracy"]["expected_sample_count"]):
        raise ValueError("Unexpected direct-resolution manifest size")
    source_revision = _source_revision(source_root)
    if source_revision != str(base_config["model"]["source_revision"]):
        raise ValueError("Depth Anything V2 source revision mismatch")
    if file_digest(weights_path) != str(base_config["model"]["weights_sha256"]):
        raise ValueError("Depth Anything V2 weights mismatch")
    input_sizes = [int(value) for value in config["whole_image_input_sizes"]]
    implementation_hashes = _implementation_hashes()
    contract = {
        "config_sha256": file_digest(config_path),
        "source_revision": source_revision,
        "weights_sha256": file_digest(weights_path),
        "implementation_files_sha256": implementation_hashes,
        "implementation_canonical_sha256": canonical_json_digest(implementation_hashes),
        "device": device,
    }
    contract_sha256 = canonical_json_digest(contract)
    cache_dir.mkdir(parents=True, exist_ok=True)
    contract_path = cache_dir / "run_contract.json"
    if contract_path.exists() and read_json(contract_path) != contract:
        raise ValueError("Resume cache contract does not match direct-resolution run")
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
    for position, record in enumerate(manifest, start=1):
        sample_index = int(record["sample_index"])
        cache_path = cache_dir / f"sample-{sample_index:04d}.json"
        if cache_path.exists():
            cached = read_json(cache_path)
            if cached.get("contract_sha256") != contract_sha256:
                raise ValueError(f"Stale direct-resolution cache in {cache_path}")
            rows = cached["rows"]
        else:
            rows = _process_sample(
                backend=backend,
                dataset_root=dataset_root,
                record=record,
                base_config=base_config,
                input_sizes=input_sizes,
            )
            write_json_atomic(
                cache_path,
                {"contract_sha256": contract_sha256, "rows": rows},
            )
        all_rows.extend(rows)
        if position % 10 == 0 or position == len(manifest):
            print(f"processed {position}/{len(manifest)}", file=sys.stderr)
    write_csv_atomic(output_csv, all_rows)
    provenance = {
        "schema_version": 1,
        "status": "COMPLETE_DIRECT_RESOLUTION_ROWS",
        "sample_count": len(manifest),
        "candidate_count": len(input_sizes),
        "row_count": len(all_rows),
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
    """Parse command-line arguments."""
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
    """Run the frozen direct-resolution accuracy sweep."""
    args = parse_args()
    provenance = run_direct_resolution(
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
