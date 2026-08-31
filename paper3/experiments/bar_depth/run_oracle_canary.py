"""Run the frozen BAR-Depth oracle patch-utility canary."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import scipy
from PIL import Image
from PIL import __version__ as pillow_version

from .core import (
    depth_boundary_weights,
    extract_square_context,
    gradient_score,
    highpass_refined_core,
    make_regions,
    positive_median_scale_fit,
    prediction_error_maps,
    robust_affine_fit,
)
from .io_utils import (
    canonical_json_digest,
    file_digest,
    read_json,
    read_jsonl,
    write_csv_atomic,
    write_json_atomic,
)


class DepthAnythingV2Backend:
    """Minimal frozen Depth Anything V2 inference backend."""

    def __init__(
        self,
        *,
        source_root: Path,
        weights: Path,
        encoder: str,
        input_size: int,
        resize_multiple: int,
        batch_size: int,
        device: str,
    ) -> None:
        import torch

        sys.path.insert(0, str(source_root))
        from depth_anything_v2.dpt import DepthAnythingV2

        model_configs: dict[str, dict[str, Any]] = {
            "vits": {
                "encoder": "vits",
                "features": 64,
                "out_channels": [48, 96, 192, 384],
            },
            "vitb": {
                "encoder": "vitb",
                "features": 128,
                "out_channels": [96, 192, 384, 768],
            },
            "vitl": {
                "encoder": "vitl",
                "features": 256,
                "out_channels": [256, 512, 1024, 1024],
            },
        }
        if encoder not in model_configs:
            raise ValueError(f"Unsupported Depth Anything V2 encoder: {encoder}")
        self.torch = torch
        self.device = torch.device(device)
        self.input_size = input_size
        self.resize_multiple = resize_multiple
        self.batch_size = batch_size
        self.model = DepthAnythingV2(**model_configs[encoder])
        state = torch.load(weights, map_location="cpu", weights_only=True)
        self.model.load_state_dict(state)
        self.model = self.model.to(self.device).eval()

    def _target_shape(self, height: int, width: int) -> tuple[int, int]:
        scale = self.input_size / min(height, width)
        target_height = max(
            self.resize_multiple,
            int(round(height * scale / self.resize_multiple)) * self.resize_multiple,
        )
        target_width = max(
            self.resize_multiple,
            int(round(width * scale / self.resize_multiple)) * self.resize_multiple,
        )
        return target_height, target_width

    def _prepare(self, images: list[np.ndarray]) -> Any:
        torch = self.torch
        tensors = []
        target_shapes = {self._target_shape(*image.shape[:2]) for image in images}
        if len(target_shapes) != 1:
            raise ValueError("A model batch must have a shared resized shape")
        target_shape = next(iter(target_shapes))
        mean = np.asarray([0.485, 0.456, 0.406], dtype=np.float64)
        std = np.asarray([0.229, 0.224, 0.225], dtype=np.float64)
        for image in images:
            resized = cv2.resize(
                image,
                (target_shape[1], target_shape[0]),
                interpolation=cv2.INTER_CUBIC,
            )
            normalized = ((resized - mean) / std).astype(np.float32)
            tensor = torch.from_numpy(
                np.ascontiguousarray(normalized.transpose(2, 0, 1))
            )
            tensors.append(tensor.unsqueeze(0))
        return torch.cat(tensors, dim=0).to(self.device)

    def infer(self, images: list[np.ndarray]) -> tuple[list[np.ndarray], float]:
        """Infer relative disparities and return synchronized forward milliseconds."""
        torch = self.torch
        outputs: list[np.ndarray] = []
        total_milliseconds = 0.0
        for start in range(0, len(images), self.batch_size):
            batch_images = images[start : start + self.batch_size]
            batch = self._prepare(batch_images)
            if self.device.type == "cuda":
                torch.cuda.synchronize(self.device)
            started = time.perf_counter()
            with torch.inference_mode():
                prediction = self.model(batch)
            if self.device.type == "cuda":
                torch.cuda.synchronize(self.device)
            total_milliseconds += (time.perf_counter() - started) * 1000.0
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
        return outputs, total_milliseconds


def _source_revision(source_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    revision = result.stdout.strip()
    status = subprocess.run(
        [
            "git",
            "-C",
            str(source_root),
            "status",
            "--porcelain",
            "--untracked-files=no",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        raise ValueError("Depth Anything V2 source tree must be clean")
    return revision


def _implementation_hashes() -> dict[str, str]:
    """Hash the complete BAR-Depth implementation used by this run."""
    module_root = Path(__file__).resolve().parent
    return {
        path.name: file_digest(path)
        for path in sorted(module_root.glob("*.py"), key=lambda item: item.name)
    }


def _load_sample(
    dataset_root: Path, record: dict[str, Any], metric_config: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with Image.open(dataset_root / record["image_relpath"]) as image_file:
        image = np.asarray(image_file.convert("RGB"), dtype=np.float64) / 255.0
    depth = np.asarray(
        np.load(dataset_root / record["depth_relpath"]), dtype=np.float64
    )
    mask = np.asarray(np.load(dataset_root / record["mask_relpath"]), dtype=bool)
    depth = np.squeeze(depth)
    mask = np.squeeze(mask)
    if depth.shape != image.shape[:2] or mask.shape != image.shape[:2]:
        raise ValueError(f"Shape mismatch for {record['image_relpath']}")
    valid = (
        mask
        & np.isfinite(depth)
        & (depth >= float(metric_config["min_depth"]))
        & (depth <= float(metric_config["max_depth"]))
    )
    return image, depth, valid


def _process_sample(
    *,
    backend: DepthAnythingV2Backend,
    dataset_root: Path,
    record: dict[str, Any],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    image, depth, valid = _load_sample(dataset_root, record, config["metric"])
    height, width = image.shape[:2]
    regions = make_regions(
        height,
        width,
        int(config["regions"]["rows"]),
        int(config["regions"]["columns"]),
        float(config["regions"]["context_scale"]),
    )
    base_outputs, base_milliseconds = backend.infer([image])
    base_disparity = base_outputs[0].astype(np.float64)
    inverse_gt = np.zeros_like(depth)
    inverse_gt[valid] = 1.0 / depth[valid]
    alignment_variant = str(config["metric"].get("alignment_variant", "robust_affine"))
    if alignment_variant == "robust_affine":
        metric_scale, metric_shift = robust_affine_fit(
            base_disparity[valid],
            inverse_gt[valid],
            trim_quantile=float(config["merge"]["affine_trim_quantile"]),
            iterations=int(config["merge"]["affine_iterations"]),
        )
    elif alignment_variant == "positive_median_scale":
        metric_scale, metric_shift = positive_median_scale_fit(
            base_disparity[valid], inverse_gt[valid]
        )
    else:
        raise ValueError(f"Unsupported metric alignment: {alignment_variant}")
    if not bool(config["metric"].get("clip_prediction_to_evaluation_range", False)):
        raise ValueError("Prediction depth range clipping must be explicitly enabled")
    aligned_base_inverse = metric_scale * base_disparity + metric_shift
    min_depth = float(config["metric"]["min_depth"])
    max_depth = float(config["metric"]["max_depth"])
    base_metric_clipped = valid & (
        (aligned_base_inverse < 1.0 / max_depth)
        | (aligned_base_inverse > 1.0 / min_depth)
    )
    base_clipped_fraction = float(base_metric_clipped.sum() / valid.sum())
    base_error, _ = prediction_error_maps(
        base_disparity,
        depth,
        valid,
        metric_scale=metric_scale,
        metric_shift=metric_shift,
        inverse_depth_epsilon=float(config["metric"]["inverse_depth_epsilon"]),
        min_depth=min_depth,
        max_depth=max_depth,
    )
    weights, boundary = depth_boundary_weights(
        depth,
        valid,
        gradient_quantile=float(config["metric"]["boundary_gradient_quantile"]),
        boundary_weight=float(config["metric"]["boundary_weight"]),
    )
    patch_images = [extract_square_context(image, region) for region in regions]
    patch_outputs, patch_milliseconds = backend.infer(patch_images)

    rows: list[dict[str, Any]] = []
    for region, patch_disparity in zip(regions, patch_outputs, strict=True):
        base_context = extract_square_context(base_disparity, region)
        refined_core, patch_scale, patch_shift = highpass_refined_core(
            base_context,
            patch_disparity.astype(np.float64),
            region,
            sigma_fraction=float(config["merge"]["gaussian_sigma_fraction"]),
            feather_fraction=float(config["regions"]["feather_fraction"]),
            trim_quantile=float(config["merge"]["affine_trim_quantile"]),
            affine_iterations=int(config["merge"]["affine_iterations"]),
        )
        core_slice = np.s_[region.y0 : region.y1, region.x0 : region.x1]
        core_valid = valid[core_slice]
        refined_error, _ = prediction_error_maps(
            refined_core,
            depth[core_slice],
            core_valid,
            metric_scale=metric_scale,
            metric_shift=metric_shift,
            inverse_depth_epsilon=float(config["metric"]["inverse_depth_epsilon"]),
            min_depth=min_depth,
            max_depth=max_depth,
        )
        base_core_error = base_error[core_slice]
        core_weights = weights[core_slice]
        primary_utility = float(
            np.sum(core_weights * (base_core_error - refined_error))
        )
        absrel_utility = float(np.sum(core_valid * (base_core_error - refined_error)))
        rows.append(
            {
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
                "base_primary_error_sum": float(np.sum(core_weights * base_core_error)),
                "refined_primary_error_sum": float(
                    np.sum(core_weights * refined_error)
                ),
                "primary_utility_sum": primary_utility,
                "base_absrel_error_sum": float(np.sum(core_valid * base_core_error)),
                "refined_absrel_error_sum": float(np.sum(core_valid * refined_error)),
                "absrel_utility_sum": absrel_utility,
                "rgb_gradient_score": gradient_score(image, region),
                "base_gradient_score": gradient_score(base_disparity, region),
                "patch_affine_scale": patch_scale,
                "patch_affine_shift": patch_shift,
            }
        )
    diagnostics = {
        "sample_index": int(record["sample_index"]),
        "base_forward_milliseconds": base_milliseconds,
        "patch_forward_milliseconds": patch_milliseconds,
        "valid_pixel_count": int(valid.sum()),
        "boundary_pixel_count": int(boundary.sum()),
        "metric_scale": metric_scale,
        "metric_shift": metric_shift,
        "base_metric_clipped_pixel_count": int(base_metric_clipped.sum()),
        "base_metric_clipped_pixel_fraction": base_clipped_fraction,
    }
    return rows, diagnostics


def run_canary(
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
    """Run or resume all frozen model evaluations."""
    import torch
    import torchvision

    config = read_json(config_path)
    manifest = read_jsonl(manifest_path)
    expected_count = int(config["dataset"]["expected_sample_count"])
    if len(manifest) != expected_count:
        raise ValueError(
            f"Expected {expected_count} manifest rows, found {len(manifest)}"
        )
    source_revision = _source_revision(source_root)
    expected_source_revision = str(config["model"]["source_revision"])
    if source_revision != expected_source_revision:
        raise ValueError(
            f"Expected model source {expected_source_revision}, got {source_revision}"
        )
    weights_sha256 = file_digest(weights_path)
    expected_weights_sha256 = str(config["model"]["weights_sha256"])
    if weights_sha256 != expected_weights_sha256:
        raise ValueError(
            f"Expected model weights {expected_weights_sha256}, got {weights_sha256}"
        )
    implementation_hashes = _implementation_hashes()
    contract = {
        "config_sha256": file_digest(config_path),
        "manifest_sha256": file_digest(manifest_path),
        "source_revision": source_revision,
        "weights_sha256": weights_sha256,
        "implementation_files_sha256": implementation_hashes,
        "implementation_canonical_sha256": canonical_json_digest(implementation_hashes),
        "device": device,
    }
    contract_sha256 = canonical_json_digest(contract)
    cache_dir.mkdir(parents=True, exist_ok=True)
    contract_path = cache_dir / "run_contract.json"
    if contract_path.exists() and read_json(contract_path) != contract:
        raise ValueError("Resume cache contract does not match this run")
    write_json_atomic(contract_path, contract)

    backend = DepthAnythingV2Backend(
        source_root=source_root,
        weights=weights_path,
        encoder=str(config["model"]["encoder"]),
        input_size=int(config["model"]["input_size"]),
        resize_multiple=int(config["model"]["resize_multiple"]),
        batch_size=int(config["model"]["batch_size"]),
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
                raise ValueError(f"Stale cache contract in {cache_path}")
            rows = cached["rows"]
            sample_diagnostics = cached["diagnostics"]
        else:
            rows, sample_diagnostics = _process_sample(
                backend=backend,
                dataset_root=dataset_root,
                record=record,
                config=config,
            )
            write_json_atomic(
                cache_path,
                {
                    "contract_sha256": contract_sha256,
                    "rows": rows,
                    "diagnostics": sample_diagnostics,
                },
            )
        if len(rows) != int(config["regions"]["expected_region_count"]):
            raise ValueError(f"Unexpected region count for sample {sample_index}")
        all_rows.extend(rows)
        diagnostics.append(sample_diagnostics)
        if position % 10 == 0 or position == len(manifest):
            print(f"processed {position}/{len(manifest)}", flush=True)

    all_rows.sort(key=lambda row: (int(row["sample_index"]), int(row["region_id"])))
    write_csv_atomic(output_csv, all_rows)
    runtime = {
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "opencv": cv2.__version__,
        "pillow": pillow_version,
        "cuda": torch.version.cuda,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "device": device,
        "gpu": (
            torch.cuda.get_device_name(torch.device(device))
            if torch.device(device).type == "cuda"
            else None
        ),
    }
    provenance: dict[str, Any] = {
        "schema_version": 1,
        "status": "COMPLETE_RAW_ORACLE_ROWS",
        "contract": contract,
        "contract_sha256": contract_sha256,
        "runtime": runtime,
        "sample_count": len(manifest),
        "region_row_count": len(all_rows),
        "base_forward_milliseconds_total": float(
            sum(float(row["base_forward_milliseconds"]) for row in diagnostics)
        ),
        "patch_forward_milliseconds_total": float(
            sum(float(row["patch_forward_milliseconds"]) for row in diagnostics)
        ),
        "base_metric_clipped_pixel_count_total": int(
            sum(int(row["base_metric_clipped_pixel_count"]) for row in diagnostics)
        ),
        "timing_interpretation": "shared_gpu_diagnostic_only",
        "output_csv_sha256": file_digest(output_csv),
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
    """CLI entry point."""
    args = parse_args()
    provenance = run_canary(
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
    print(
        f"{provenance['status']}: {provenance['region_row_count']} region rows",
        flush=True,
    )


if __name__ == "__main__":
    main()
