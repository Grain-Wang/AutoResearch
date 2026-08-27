"""Audit BAR-Depth v1 for invalid inverse-depth values before metric clipping."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from paper1.experiments.bar_depth.core import robust_affine_fit
from paper1.experiments.bar_depth.io_utils import (
    file_digest,
    read_json,
    read_jsonl,
    write_json_atomic,
)
from paper1.experiments.bar_depth.run_oracle_canary import (
    DepthAnythingV2Backend,
    _load_sample,
    _source_revision,
)


def audit_metric_domain(
    *,
    dataset_root: Path,
    manifest_path: Path,
    config_path: Path,
    source_root: Path,
    weights_path: Path,
    output_path: Path,
    device: str,
) -> dict[str, Any]:
    """Count non-positive aligned inverse-depth values before epsilon clipping."""
    config = read_json(config_path)
    manifest = read_jsonl(manifest_path)
    backend = DepthAnythingV2Backend(
        source_root=source_root,
        weights=weights_path,
        encoder=str(config["model"]["encoder"]),
        input_size=int(config["model"]["input_size"]),
        resize_multiple=int(config["model"]["resize_multiple"]),
        batch_size=int(config["model"]["batch_size"]),
        device=device,
    )
    epsilon = float(config["metric"]["inverse_depth_epsilon"])
    totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "valid_pixel_count": 0.0,
            "nonpositive_pixel_count": 0.0,
            "epsilon_clipped_pixel_count": 0.0,
            "absrel_error_sum_after_clipping": 0.0,
            "image_count": 0.0,
            "images_with_epsilon_clipping": 0.0,
        }
    )
    image_clipped_fractions: dict[str, list[float]] = defaultdict(list)
    for position, record in enumerate(manifest, start=1):
        image, depth, valid = _load_sample(dataset_root, record, config["metric"])
        base_disparity = backend.infer([image])[0][0].astype(np.float64)
        inverse_gt = np.zeros_like(depth)
        inverse_gt[valid] = 1.0 / depth[valid]
        scale, shift = robust_affine_fit(
            base_disparity[valid],
            inverse_gt[valid],
            trim_quantile=float(config["merge"]["affine_trim_quantile"]),
            iterations=int(config["merge"]["affine_iterations"]),
        )
        aligned_inverse = scale * base_disparity + shift
        nonpositive = valid & (aligned_inverse <= 0)
        clipped = valid & (aligned_inverse <= epsilon)
        predicted_depth = 1.0 / np.maximum(aligned_inverse, epsilon)
        absrel = np.zeros_like(depth, dtype=np.float64)
        absrel[valid] = np.abs(predicted_depth[valid] - depth[valid]) / depth[valid]

        domain = str(record["domain"])
        valid_count = int(valid.sum())
        clipped_count = int(clipped.sum())
        totals[domain]["valid_pixel_count"] += valid_count
        totals[domain]["nonpositive_pixel_count"] += int(nonpositive.sum())
        totals[domain]["epsilon_clipped_pixel_count"] += clipped_count
        totals[domain]["absrel_error_sum_after_clipping"] += float(absrel.sum())
        totals[domain]["image_count"] += 1
        totals[domain]["images_with_epsilon_clipping"] += int(clipped_count > 0)
        image_clipped_fractions[domain].append(clipped_count / valid_count)
        if position % 20 == 0:
            print(f"audited {position}/{len(manifest)}", flush=True)

    domain_audit: dict[str, dict[str, float]] = {}
    for domain in sorted(totals):
        row = totals[domain]
        valid_count = row["valid_pixel_count"]
        fractions = np.asarray(image_clipped_fractions[domain], dtype=np.float64)
        domain_audit[domain] = {
            **row,
            "epsilon_clipped_pixel_fraction": (
                row["epsilon_clipped_pixel_count"] / valid_count
            ),
            "mean_absrel_after_clipping": (
                row["absrel_error_sum_after_clipping"] / valid_count
            ),
            "median_image_clipped_fraction": float(np.median(fractions)),
            "max_image_clipped_fraction": float(np.max(fractions)),
        }

    total_clipped = sum(
        row["epsilon_clipped_pixel_count"] for row in domain_audit.values()
    )
    audit: dict[str, Any] = {
        "schema_version": 1,
        "status": (
            "INVALID_METRIC_ALIGNMENT" if total_clipped > 0 else "PASS_METRIC_DOMAIN"
        ),
        "invalidity_rule": (
            "Any valid pixel with aligned inverse depth <= epsilon before metric "
            "clipping invalidates the v1 affine-to-AbsRel evaluation."
        ),
        "sample_count": len(manifest),
        "domain_audit": domain_audit,
        "bindings": {
            "config_sha256": file_digest(config_path),
            "manifest_sha256": file_digest(manifest_path),
            "model_source_revision": _source_revision(source_root),
            "model_weights_sha256": file_digest(weights_path),
        },
    }
    write_json_atomic(output_path, audit)
    return audit


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    audit = audit_metric_domain(
        dataset_root=args.dataset_root,
        manifest_path=args.manifest,
        config_path=args.config,
        source_root=args.source_root,
        weights_path=args.weights,
        output_path=args.output,
        device=args.device,
    )
    print(audit["status"], flush=True)


if __name__ == "__main__":
    main()
