"""Run frozen BAR-Depth merge and no-extra-forward controls."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import scipy
from PIL import __version__ as pillow_version

from .core import (
    depth_boundary_weights,
    extract_square_context,
    gradient_score,
    make_regions,
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
from .merge_variants import (
    base_depth_unsharp_mask,
    patch_refined_cores,
    rgb_guided_bilateral_sharpening,
)
from .run_oracle_canary import (
    DepthAnythingV2Backend,
    _load_sample,
    _source_revision,
)

PATCH_VARIANTS = {
    "highpass_residual",
    "aligned_patch_replacement",
    "patch_high_frequency_without_base_subtraction",
}
NO_FORWARD_VARIANTS = {
    "rgb_guided_bilateral_sharpening",
    "base_depth_unsharp_mask",
}


def _implementation_hashes() -> dict[str, str]:
    module_root = Path(__file__).resolve().parent
    names = (
        "core.py",
        "io_utils.py",
        "merge_variants.py",
        "run_merge_ablation.py",
        "run_oracle_canary.py",
    )
    return {name: file_digest(module_root / name) for name in names}


def _process_sample(
    *,
    backend: DepthAnythingV2Backend,
    dataset_root: Path,
    record: dict[str, Any],
    base_config: dict[str, Any],
    ablation_config: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    image, depth, valid = _load_sample(dataset_root, record, base_config["metric"])
    height, width = image.shape[:2]
    regions = make_regions(
        height,
        width,
        int(base_config["regions"]["rows"]),
        int(base_config["regions"]["columns"]),
        float(base_config["regions"]["context_scale"]),
    )
    base_outputs, base_milliseconds = backend.infer([image])
    base_disparity = base_outputs[0].astype(np.float64)
    inverse_gt = np.zeros_like(depth)
    inverse_gt[valid] = 1.0 / depth[valid]
    metric_scale, metric_shift = positive_median_scale_fit(
        base_disparity[valid], inverse_gt[valid]
    )
    min_depth = float(base_config["metric"]["min_depth"])
    max_depth = float(base_config["metric"]["max_depth"])
    base_error, _ = prediction_error_maps(
        base_disparity,
        depth,
        valid,
        metric_scale=metric_scale,
        metric_shift=metric_shift,
        inverse_depth_epsilon=float(base_config["metric"]["inverse_depth_epsilon"]),
        min_depth=min_depth,
        max_depth=max_depth,
    )
    weights, boundary = depth_boundary_weights(
        depth,
        valid,
        gradient_quantile=float(base_config["metric"]["boundary_gradient_quantile"]),
        boundary_weight=float(base_config["metric"]["boundary_weight"]),
    )
    patch_images = [extract_square_context(image, region) for region in regions]
    patch_outputs, patch_milliseconds = backend.infer(patch_images)

    cheap_started = time.perf_counter()
    rgb_parameters = ablation_config["rgb_guided_bilateral_sharpening"]
    unsharp_parameters = ablation_config["base_depth_unsharp_mask"]
    cheap_maps = {
        "rgb_guided_bilateral_sharpening": rgb_guided_bilateral_sharpening(
            base_disparity,
            image,
            radius=int(rgb_parameters["radius"]),
            spatial_sigma=float(rgb_parameters["spatial_sigma"]),
            color_sigma=float(rgb_parameters["color_sigma"]),
            amount=float(rgb_parameters["amount"]),
        ),
        "base_depth_unsharp_mask": base_depth_unsharp_mask(
            base_disparity,
            sigma_pixels=float(unsharp_parameters["sigma_pixels"]),
            amount=float(unsharp_parameters["amount"]),
        ),
    }
    cheap_control_milliseconds = (time.perf_counter() - cheap_started) * 1000.0

    variants = [str(value) for value in ablation_config["variants"]]
    if set(variants) != PATCH_VARIANTS | NO_FORWARD_VARIANTS:
        raise ValueError(
            "Merge-ablation variant set does not match the frozen contract"
        )
    rows: list[dict[str, Any]] = []
    for region, patch_disparity in zip(regions, patch_outputs, strict=True):
        base_context = extract_square_context(base_disparity, region)
        patch_refinements, patch_scale, patch_shift = patch_refined_cores(
            base_context,
            patch_disparity.astype(np.float64),
            region,
            sigma_fraction=float(base_config["merge"]["gaussian_sigma_fraction"]),
            feather_fraction=float(base_config["regions"]["feather_fraction"]),
            trim_quantile=float(base_config["merge"]["affine_trim_quantile"]),
            affine_iterations=int(base_config["merge"]["affine_iterations"]),
        )
        core_slice = np.s_[region.y0 : region.y1, region.x0 : region.x1]
        core_valid = valid[core_slice]
        base_core_error = base_error[core_slice]
        core_weights = weights[core_slice]
        for variant in variants:
            if variant in PATCH_VARIANTS:
                refined_core = patch_refinements[variant]
            else:
                refined_core = cheap_maps[variant][core_slice]
                patch_scale, patch_shift = 1.0, 0.0
            refined_error, _ = prediction_error_maps(
                refined_core,
                depth[core_slice],
                core_valid,
                metric_scale=metric_scale,
                metric_shift=metric_shift,
                inverse_depth_epsilon=float(
                    base_config["metric"]["inverse_depth_epsilon"]
                ),
                min_depth=min_depth,
                max_depth=max_depth,
            )
            primary_utility = float(
                np.sum(core_weights * (base_core_error - refined_error))
            )
            absrel_utility = float(
                np.sum(core_valid * (base_core_error - refined_error))
            )
            rows.append(
                {
                    "variant": variant,
                    "sample_index": int(record["sample_index"]),
                    "domain": record["domain"],
                    "scene_id": record["scene_id"],
                    "scan_id": record["scan_id"],
                    "image_relpath": record["image_relpath"],
                    "region_id": region.region_id,
                    "row": region.row,
                    "column": region.column,
                    "x0": region.x0,
                    "y0": region.y0,
                    "x1": region.x1,
                    "y1": region.y1,
                    "valid_pixel_count": int(core_valid.sum()),
                    "boundary_pixel_count": int(boundary[core_slice].sum()),
                    "weight_sum": float(core_weights.sum()),
                    "base_primary_error_sum": float(
                        np.sum(core_weights * base_core_error)
                    ),
                    "refined_primary_error_sum": float(
                        np.sum(core_weights * refined_error)
                    ),
                    "primary_utility_sum": primary_utility,
                    "base_absrel_error_sum": float(
                        np.sum(core_valid * base_core_error)
                    ),
                    "refined_absrel_error_sum": float(
                        np.sum(core_valid * refined_error)
                    ),
                    "absrel_utility_sum": absrel_utility,
                    "rgb_gradient_score": gradient_score(image, region),
                    "base_gradient_score": gradient_score(base_disparity, region),
                    "patch_affine_scale": patch_scale,
                    "patch_affine_shift": patch_shift,
                    "uses_patch_forward": variant in PATCH_VARIANTS,
                }
            )
    diagnostics = {
        "sample_index": int(record["sample_index"]),
        "base_forward_milliseconds": base_milliseconds,
        "patch_forward_milliseconds": patch_milliseconds,
        "cheap_control_milliseconds": cheap_control_milliseconds,
        "valid_pixel_count": int(valid.sum()),
        "boundary_pixel_count": int(boundary.sum()),
        "metric_scale": metric_scale,
        "metric_shift": metric_shift,
    }
    return rows, diagnostics


def run_merge_ablation(
    *,
    dataset_root: Path,
    manifest_path: Path,
    config_path: Path,
    source_root: Path,
    weights_path: Path,
    cache_dir: Path,
    output_csv: Path,
    output_provenance: Path,
    device: str,
) -> dict[str, Any]:
    """Run or resume all frozen merge-ablation model evaluations."""
    import torch
    import torchvision

    ablation_config = read_json(config_path)
    base_config_path = Path(ablation_config["base_config"])
    if file_digest(base_config_path) != ablation_config["base_config_sha256"]:
        raise ValueError("Frozen v2 base config binding changed")
    base_config = read_json(base_config_path)
    manifest = read_jsonl(manifest_path)
    if len(manifest) != int(base_config["dataset"]["expected_sample_count"]):
        raise ValueError("Unexpected merge-ablation manifest size")
    source_revision = _source_revision(source_root)
    if source_revision != base_config["model"]["source_revision"]:
        raise ValueError("Depth Anything V2 source revision mismatch")
    if file_digest(weights_path) != base_config["model"]["weights_sha256"]:
        raise ValueError("Depth Anything V2 weights mismatch")
    implementation_hashes = _implementation_hashes()
    contract = {
        "config_sha256": file_digest(config_path),
        "base_config_sha256": file_digest(base_config_path),
        "manifest_sha256": file_digest(manifest_path),
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
        raise ValueError("Resume cache contract does not match merge ablation")
    write_json_atomic(contract_path, contract)
    backend = DepthAnythingV2Backend(
        source_root=source_root,
        weights=weights_path,
        encoder=str(base_config["model"]["encoder"]),
        input_size=int(base_config["model"]["input_size"]),
        resize_multiple=int(base_config["model"]["resize_multiple"]),
        batch_size=int(base_config["model"]["batch_size"]),
        device=device,
    )
    all_rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for position, record in enumerate(manifest, start=1):
        sample_index = int(record["sample_index"])
        cache_path = cache_dir / f"sample-{sample_index:04d}.json"
        if cache_path.exists():
            cached = read_json(cache_path)
            if cached.get("contract_sha256") != contract_sha256:
                raise ValueError(f"Stale merge cache contract in {cache_path}")
            rows = cached["rows"]
            sample_diagnostics = cached["diagnostics"]
        else:
            rows, sample_diagnostics = _process_sample(
                backend=backend,
                dataset_root=dataset_root,
                record=record,
                base_config=base_config,
                ablation_config=ablation_config,
            )
            write_json_atomic(
                cache_path,
                {
                    "contract_sha256": contract_sha256,
                    "rows": rows,
                    "diagnostics": sample_diagnostics,
                },
            )
        all_rows.extend(rows)
        diagnostics.append(sample_diagnostics)
        if position % 10 == 0 or position == len(manifest):
            print(f"processed {position}/{len(manifest)}", file=sys.stderr)
    write_csv_atomic(output_csv, all_rows)
    runtime = {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "opencv": cv2.__version__,
        "pillow": pillow_version,
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "cuda": torch.version.cuda,
        "device": device,
        "gpu": (
            torch.cuda.get_device_name(torch.device(device))
            if torch.device(device).type == "cuda"
            else None
        ),
    }
    provenance = {
        "schema_version": 1,
        "status": "COMPLETE_MERGE_ABLATION_ROWS",
        "sample_count": len(manifest),
        "variant_count": len(ablation_config["variants"]),
        "region_row_count": len(all_rows),
        "base_forward_milliseconds_total": float(
            sum(row["base_forward_milliseconds"] for row in diagnostics)
        ),
        "patch_forward_milliseconds_total": float(
            sum(row["patch_forward_milliseconds"] for row in diagnostics)
        ),
        "cheap_control_milliseconds_total": float(
            sum(row["cheap_control_milliseconds"] for row in diagnostics)
        ),
        "output_csv_sha256": file_digest(output_csv),
        "contract": contract,
        "contract_sha256": contract_sha256,
        "runtime": runtime,
    }
    write_json_atomic(output_provenance, provenance)
    return provenance


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-provenance", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    return parser.parse_args()


def main() -> None:
    """Run the merge ablation from the command line."""
    args = parse_args()
    provenance = run_merge_ablation(
        dataset_root=args.dataset_root,
        manifest_path=args.manifest,
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
