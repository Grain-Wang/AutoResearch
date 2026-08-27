"""Run the frozen NYUv2 train-only TR2M H-sensitivity diagnostic."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import math
import re
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

try:
    from paper1.experiments.covol.build_nyuv2_source_manifest import (
        _normalize_plane,
        _normalize_rgb_frame,
    )
    from paper1.experiments.covol.step003_authorization import (
        require_action_authorized,
    )
except ModuleNotFoundError:  # Direct script consumers in this directory.
    from build_nyuv2_source_manifest import (  # type: ignore
        _normalize_plane,
        _normalize_rgb_frame,
    )
    from step003_authorization import require_action_authorized  # type: ignore

BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20260827
INPUT_HEIGHT = 434
INPUT_WIDTH = 560
CONFLICT_FAMILIES = (
    "target_deletion",
    "local_entity_conflict",
    "depth_relation_conflict",
)
CONTROL_FAMILY = "semantic_preserving"
ALL_FAMILIES = (CONTROL_FAMILY, *CONFLICT_FAMILIES)
_ENTITY_PATTERN = re.compile(r"^nyuv2:\d+:class-(\d+):instance-(\d+)$")
_CSV_FIELDS = (
    "dataset",
    "image_id",
    "cluster_id",
    "error_type",
    "variant_id",
    "template_id",
    "full_clean_abs_rel",
    "full_variant_abs_rel",
    "full_abs_rel_degradation",
    "full_clean_d1",
    "full_variant_d1",
    "full_d1_degradation",
    "region_clean_abs_rel",
    "region_variant_abs_rel",
    "region_abs_rel_degradation",
    "region_clean_d1",
    "region_variant_d1",
    "region_d1_degradation",
    "full_valid_pixel_count",
    "region_valid_pixel_count",
)


@dataclass(frozen=True)
class EvalProtocol:
    """Frozen NYUv2 evaluation crop and valid-depth interval."""

    image_height: int
    image_width: int
    y_start: int
    y_end: int
    x_start: int
    x_end: int
    minimum_depth: float
    maximum_depth: float
    depth_key: str


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            rows.append(value)
    return rows


def load_eval_protocol(path: Path) -> EvalProtocol:
    """Load the frozen NYUv2 crop without accepting runtime overrides."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    dataset = payload["datasets"]["NYUv2"]
    crop = dataset["crop"]
    protocol = EvalProtocol(
        image_height=int(dataset["image_height"]),
        image_width=int(dataset["image_width"]),
        y_start=int(crop["y_start_inclusive"]),
        y_end=int(crop["y_end_exclusive"]),
        x_start=int(crop["x_start_inclusive"]),
        x_end=int(crop["x_end_exclusive"]),
        minimum_depth=float(dataset["minimum_depth_exclusive_m"]),
        maximum_depth=float(dataset["maximum_depth_exclusive_m"]),
        depth_key=str(dataset["depth_key"]),
    )
    if (
        protocol.image_height != 480
        or protocol.image_width != 640
        or not 0 <= protocol.y_start < protocol.y_end <= protocol.image_height
        or not 0 <= protocol.x_start < protocol.x_end <= protocol.image_width
        or not 0 < protocol.minimum_depth < protocol.maximum_depth
        or protocol.depth_key not in {"rawDepths", "depths"}
    ):
        raise ValueError("invalid frozen NYUv2 evaluation protocol")
    return protocol


def _parse_entity_id(value: str) -> tuple[int, int]:
    match = _ENTITY_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError(f"invalid NYUv2 entity ID: {value!r}")
    return int(match.group(1)), int(match.group(2))


def target_region_mask(
    labels: np.ndarray,
    instances: np.ndarray,
    target_region: Mapping[str, Any],
) -> np.ndarray:
    """Return the union of the frozen near and far entity masks."""

    if labels.shape != instances.shape:
        raise ValueError("NYUv2 labels and instances must share a shape")
    entity_pairs = [
        _parse_entity_id(str(target_region[key]))
        for key in ("near_entity_id", "far_entity_id")
    ]
    mask = np.zeros(labels.shape, dtype=bool)
    for class_id, instance_id in entity_pairs:
        mask |= (labels == class_id) & (instances == instance_id)
    if int(np.count_nonzero(mask)) < 32:
        raise ValueError("target region has fewer than 32 annotated pixels")
    return mask


def depth_metrics(
    ground_truth: np.ndarray,
    prediction: np.ndarray,
    valid_mask: np.ndarray,
) -> dict[str, float | int]:
    """Compute AbsRel and delta1 on an explicit frozen pixel mask."""

    if not (
        ground_truth.shape == prediction.shape == valid_mask.shape
        and valid_mask.dtype == np.bool_
    ):
        raise ValueError("metric arrays must share shape and use a boolean mask")
    count = int(np.count_nonzero(valid_mask))
    if count < 32:
        raise ValueError("metric mask has fewer than 32 valid pixels")
    target = ground_truth[valid_mask].astype(np.float64, copy=False)
    predicted = prediction[valid_mask].astype(np.float64, copy=False)
    if not np.all(np.isfinite(predicted)) or np.any(predicted <= 0):
        raise ValueError("prediction contains invalid depth")
    ratio = np.maximum(target / predicted, predicted / target)
    return {
        "abs_rel": float(np.mean(np.abs(target - predicted) / target)),
        "d1": float(np.mean(ratio < 1.25)),
        "valid_pixel_count": count,
    }


def _full_valid_mask(ground_truth: np.ndarray, protocol: EvalProtocol) -> np.ndarray:
    valid = (
        np.isfinite(ground_truth)
        & (ground_truth > protocol.minimum_depth)
        & (ground_truth < protocol.maximum_depth)
    )
    crop = np.zeros(ground_truth.shape, dtype=bool)
    crop[protocol.y_start : protocol.y_end, protocol.x_start : protocol.x_end] = True
    return valid & crop


def evaluate_prediction_pair(
    *,
    ground_truth: np.ndarray,
    clean_prediction: np.ndarray,
    variant_prediction: np.ndarray,
    region_mask: np.ndarray,
    protocol: EvalProtocol,
) -> dict[str, float | int]:
    """Compute paired full-crop and target-region degradation metrics."""

    full_mask = _full_valid_mask(ground_truth, protocol)
    local_mask = full_mask & region_mask
    clean_full = depth_metrics(ground_truth, clean_prediction, full_mask)
    variant_full = depth_metrics(ground_truth, variant_prediction, full_mask)
    clean_region = depth_metrics(ground_truth, clean_prediction, local_mask)
    variant_region = depth_metrics(ground_truth, variant_prediction, local_mask)
    return {
        "full_clean_abs_rel": clean_full["abs_rel"],
        "full_variant_abs_rel": variant_full["abs_rel"],
        "full_abs_rel_degradation": (
            float(variant_full["abs_rel"]) - float(clean_full["abs_rel"])
        ),
        "full_clean_d1": clean_full["d1"],
        "full_variant_d1": variant_full["d1"],
        "full_d1_degradation": (float(clean_full["d1"]) - float(variant_full["d1"])),
        "region_clean_abs_rel": clean_region["abs_rel"],
        "region_variant_abs_rel": variant_region["abs_rel"],
        "region_abs_rel_degradation": (
            float(variant_region["abs_rel"]) - float(clean_region["abs_rel"])
        ),
        "region_clean_d1": clean_region["d1"],
        "region_variant_d1": variant_region["d1"],
        "region_d1_degradation": (
            float(clean_region["d1"]) - float(variant_region["d1"])
        ),
        "full_valid_pixel_count": clean_full["valid_pixel_count"],
        "region_valid_pixel_count": clean_region["valid_pixel_count"],
    }


def cluster_bootstrap_interval(
    rows: Sequence[Mapping[str, Any]],
    *,
    value_key: str,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, float | int]:
    """Return a cluster-balanced percentile interval for a paired delta."""

    if replicates < 1:
        raise ValueError("bootstrap replicates must be positive")
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        cluster_id = str(row.get("cluster_id", ""))
        value = float(row.get(value_key))
        if not cluster_id or not math.isfinite(value):
            raise ValueError("bootstrap row lacks a finite value or cluster ID")
        grouped[cluster_id].append(value)
    if len(grouped) < 2:
        raise ValueError("cluster bootstrap requires at least two clusters")
    cluster_means = np.asarray(
        [np.mean(grouped[key]) for key in sorted(grouped)], dtype=np.float64
    )
    rng = np.random.default_rng(seed)
    samples = rng.integers(
        0,
        len(cluster_means),
        size=(replicates, len(cluster_means)),
        endpoint=False,
    )
    estimates = np.mean(cluster_means[samples], axis=1)
    return {
        "point": float(np.mean(cluster_means)),
        "ci_lower": float(np.quantile(estimates, 0.025)),
        "ci_upper": float(np.quantile(estimates, 0.975)),
        "cluster_count": len(cluster_means),
        "row_count": len(rows),
        "bootstrap_replicates": replicates,
        "bootstrap_seed": seed,
    }


def summarize_sensitivity(
    rows: Sequence[Mapping[str, Any]],
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Apply the preregistered H-sensitivity decision to paired rows."""

    family_summaries: dict[str, Any] = {}
    for family_index, family in enumerate(ALL_FAMILIES):
        family_rows = [row for row in rows if row.get("error_type") == family]
        if not family_rows:
            raise ValueError(f"sensitivity rows lack family {family}")
        family_summaries[family] = {
            key: cluster_bootstrap_interval(
                family_rows,
                value_key=key,
                replicates=replicates,
                seed=seed + family_index * 10 + metric_index,
            )
            for metric_index, key in enumerate(
                (
                    "region_abs_rel_degradation",
                    "region_d1_degradation",
                    "full_abs_rel_degradation",
                    "full_d1_degradation",
                )
            )
        }
    control = family_summaries[CONTROL_FAMILY]["region_abs_rel_degradation"]
    control_contains_zero = (
        float(control["ci_lower"]) <= 0.0 <= float(control["ci_upper"])
    )
    supported_conflicts = [
        family
        for family in CONFLICT_FAMILIES
        if float(family_summaries[family]["region_abs_rel_degradation"]["ci_lower"])
        > 0.0
    ]
    passed = control_contains_zero and bool(supported_conflicts)
    return {
        "schema_version": "covol-h-sensitivity-summary-v1",
        "status": "PASS_H_SENSITIVITY" if passed else "STOP_H_SENSITIVITY",
        "primary_metric": "REGION_ABS_REL_DEGRADATION",
        "control_family": CONTROL_FAMILY,
        "control_ci_contains_zero": control_contains_zero,
        "supported_conflict_families": supported_conflicts,
        "family_summaries": family_summaries,
        "scientific_evidence": (
            "D1_CAPTION_SENSITIVITY_ONLY_NOT_D0_FALLBACK_OR_ROUTER_EFFECT"
        ),
    }


class Tr2mBatchPredictor:
    """Load released TR2M components once and reuse image features per frame."""

    def __init__(
        self,
        *,
        tr2m_root: Path,
        tr2m_checkpoint: Path,
        depth_checkpoint: Path,
        cache_root: Path,
        device: str,
    ) -> None:
        torch = importlib.import_module("torch")
        self._torch = torch
        self._functional = importlib.import_module("torch.nn.functional")
        sys.path.insert(0, str(tr2m_root.resolve()))
        clip = importlib.import_module("CLIP.clip")
        depth_module = importlib.import_module("depth_anything.dpt")
        scalemap_module = importlib.import_module("scalemap_depth")
        self._clip = clip
        self._device = torch.device(device)
        torch.hub.set_dir(str((cache_root / "torchhub").resolve()))

        depth_config = {
            "encoder": "vits",
            "features": 64,
            "out_channels": [48, 96, 192, 384],
        }
        self._depth = depth_module.DepthAnything(depth_config)
        self._depth.load_state_dict(
            torch.load(depth_checkpoint, map_location="cpu", weights_only=True)
        )
        self._depth.to(self._device).eval()

        self._clip_model, _ = clip.load(
            "ViT-L/14",
            device=self._device,
            download_root=str((cache_root / "clip").resolve()),
        )
        self._clip_model.eval()
        dino_source = tr2m_root / "torchhub" / "facebookresearch_dinov2_main"
        self._image_model = torch.hub.load(
            str(dino_source.resolve()),
            "dinov2_vitl14",
            source="local",
            pretrained=True,
        ).to(self._device)
        self._image_model.eval()

        self._scalemap = scalemap_module.ScaleMapModel(
            1024, 192, 768, 128, 8, 0.01, 0.01
        ).to(self._device)
        checkpoint = torch.load(tr2m_checkpoint, map_location="cpu", weights_only=True)
        state_dict = (
            checkpoint["state_dict"]
            if isinstance(checkpoint, dict) and "state_dict" in checkpoint
            else checkpoint
        )
        self._scalemap.load_state_dict(state_dict)
        self._scalemap.eval()

    def _image_tensor(self, rgb: np.ndarray) -> Any:
        torch = self._torch
        tensor = (
            torch.from_numpy(np.ascontiguousarray(rgb.transpose(2, 0, 1)))
            .to(self._device)
            .float()
            .div_(255.0)
            .unsqueeze(0)
        )
        tensor = self._functional.interpolate(
            tensor,
            size=(INPUT_HEIGHT, INPUT_WIDTH),
            mode="bilinear",
            align_corners=False,
        )
        mean = torch.tensor([0.485, 0.456, 0.406], device=self._device).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225], device=self._device).view(1, 3, 1, 1)
        return (tensor - mean) / std

    def predict(self, rgb: np.ndarray, captions: Sequence[str]) -> np.ndarray:
        """Predict one metric-depth map per caption with shared image features."""

        torch = self._torch
        image = self._image_tensor(rgb)
        with torch.inference_mode():
            text_tokens = self._clip.tokenize(list(captions), truncate=True).to(
                self._device
            )
            text_features = self._clip_model.encode_text(text_tokens).unsqueeze(1)
            image_features = self._image_model.get_intermediate_layers(
                image, n=1, return_class_token=False
            )[0]
            relative_depth = self._depth(image).unsqueeze(1)
            image_features = image_features.expand(len(captions), -1, -1)
            scale, shift, _, _ = self._scalemap(
                image_features.float(),
                text_features.float(),
                patch_h=INPUT_HEIGHT // 14,
                patch_w=INPUT_WIDTH // 14,
            )
            if relative_depth.shape[-2:] != scale.shape[-2:]:
                relative_depth = self._functional.interpolate(
                    relative_depth,
                    size=scale.shape[-2:],
                    mode="bilinear",
                    align_corners=True,
                )
            metric = 1.0 / (
                scale * relative_depth.expand(len(captions), -1, -1, -1) + shift
            )
            metric = self._functional.interpolate(
                metric,
                size=rgb.shape[:2],
                mode="bilinear",
                align_corners=True,
            )
            metric = torch.nan_to_num(metric, nan=0.001, posinf=10.0, neginf=0.001)
            metric = metric.clamp_(0.001, 10.0)
        return metric[:, 0].float().cpu().numpy()


def _validate_corpus(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    if len(rows) != 1_200:
        raise ValueError("H-sensitivity requires exactly 1,200 intervention rows")
    image_ids = sorted({str(row.get("image_id", "")) for row in rows})
    if len(image_ids) != 100:
        raise ValueError("H-sensitivity requires exactly 100 images")
    for image_id in image_ids:
        image_rows = [row for row in rows if row.get("image_id") == image_id]
        if len(image_rows) != 12 or {
            str(row.get("error_type")) for row in image_rows
        } != set(ALL_FAMILIES):
            raise ValueError("each image must contain all twelve frozen variants")
        if any(row.get("source_split") != "train" for row in image_rows):
            raise ValueError("H-sensitivity may only read NYUv2 official train")
    return image_ids


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    with temporary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in _CSV_FIELDS})
    temporary_path.replace(path)


def _load_resume_results(
    path: Path,
    intervention_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Load only complete per-image checkpoints matching the frozen corpus."""

    if not path.exists():
        return []
    expected = {
        (
            str(row["image_id"]),
            str(row["error_type"]),
            str(row["variant_id"]),
            str(row["template_id"]),
        )
        for row in intervention_rows
    }
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != _CSV_FIELDS:
            raise ValueError("resume CSV schema differs from the frozen output schema")
        rows = [dict(row) for row in reader]
    actual = {
        (
            row["image_id"],
            row["error_type"],
            row["variant_id"],
            row["template_id"],
        )
        for row in rows
    }
    if len(actual) != len(rows) or not actual.issubset(expected):
        raise ValueError("resume CSV identities differ from the frozen corpus")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["image_id"]].append(row)
        for field in _CSV_FIELDS[6:18]:
            if not math.isfinite(float(row[field])):
                raise ValueError("resume CSV contains a non-finite metric")
        for field in _CSV_FIELDS[18:]:
            if int(row[field]) < 32:
                raise ValueError("resume CSV contains an invalid pixel count")
    if any(len(image_rows) != 12 for image_rows in grouped.values()):
        raise ValueError("resume CSV contains an incomplete image checkpoint")
    return rows


def _encoder_weight_provenance(cache_root: Path) -> list[dict[str, Any]]:
    """Hash downloaded frozen encoder weights without recording machine paths."""

    assets = sorted(
        path
        for path in cache_root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".pt", ".pth"}
    )
    names = [path.name.lower() for path in assets]
    if not any("vit-l-14" in name for name in names):
        raise ValueError("CLIP ViT-L/14 weight was not found in the cache")
    if not any("dinov2_vitl14" in name for name in names):
        raise ValueError("DINOv2 ViT-L/14 weight was not found in the cache")
    return [
        {
            "path_within_cache": path.relative_to(cache_root).as_posix(),
            "byte_count": path.stat().st_size,
            "sha256": _file_sha256(path),
        }
        for path in assets
    ]


def run_diagnostic(args: argparse.Namespace) -> dict[str, Any]:
    """Execute released TR2M on the frozen 100-image training-only corpus."""

    require_action_authorized(args.authorization, action="nyuv2_h_sensitivity")
    rows = _read_jsonl(args.interventions)
    image_ids = _validate_corpus(rows)
    protocol = load_eval_protocol(args.eval_protocol)
    release = json.loads(args.release_audit.read_text(encoding="utf-8"))
    expected_tr2m = release["tr2m_checkpoint"]["sha256"]
    expected_depth = release["depth_anything_checkpoint"]["sha256"]
    if _file_sha256(args.tr2m_checkpoint) != expected_tr2m:
        raise ValueError("TR2M checkpoint does not match the release audit")
    if _file_sha256(args.depth_checkpoint) != expected_depth:
        raise ValueError("Depth Anything checkpoint does not match the release audit")
    predictor = Tr2mBatchPredictor(
        tr2m_root=args.tr2m_root,
        tr2m_checkpoint=args.tr2m_checkpoint,
        depth_checkpoint=args.depth_checkpoint,
        cache_root=args.cache_root,
        device=args.device,
    )
    h5py = importlib.import_module("h5py")
    results = (
        []
        if args.restart
        else _load_resume_results(args.output, intervention_rows=rows)
    )
    completed_images = {str(row["image_id"]) for row in results}
    with h5py.File(args.nyuv2_labeled, "r") as handle:
        for image_position, image_id in enumerate(image_ids, start=1):
            if image_id in completed_images:
                print(
                    f"[{image_position:03d}/{len(image_ids):03d}] {image_id} resumed",
                    flush=True,
                )
                continue
            image_rows = sorted(
                [row for row in rows if row["image_id"] == image_id],
                key=lambda row: (str(row["error_type"]), int(row["variant_id"])),
            )
            matlab_index = int(image_id.rsplit("_", maxsplit=1)[1])
            zero_based_index = matlab_index - 1
            rgb = _normalize_rgb_frame(handle["images"][zero_based_index], np)
            if hashlib.sha256(rgb.tobytes()).hexdigest() != image_rows[0]["rgb_sha256"]:
                raise ValueError(f"{image_id}: RGB hash differs from the frozen corpus")
            ground_truth = _normalize_plane(
                handle[protocol.depth_key][zero_based_index],
                height=protocol.image_height,
                width=protocol.image_width,
                name=protocol.depth_key,
                numpy=np,
            ).astype(np.float32, copy=False)
            labels = _normalize_plane(
                handle["labels"][zero_based_index],
                height=protocol.image_height,
                width=protocol.image_width,
                name="labels",
                numpy=np,
            )
            instances = _normalize_plane(
                handle["instances"][zero_based_index],
                height=protocol.image_height,
                width=protocol.image_width,
                name="instances",
                numpy=np,
            )
            captions = [str(image_rows[0]["predicate_clean_caption"])] + [
                str(row["intervention"]) for row in image_rows
            ]
            predictions = predictor.predict(rgb, captions)
            clean_prediction = predictions[0]
            for row, variant_prediction in zip(
                image_rows, predictions[1:], strict=True
            ):
                region = target_region_mask(labels, instances, row["target_region"])
                metrics = evaluate_prediction_pair(
                    ground_truth=ground_truth,
                    clean_prediction=clean_prediction,
                    variant_prediction=variant_prediction,
                    region_mask=region,
                    protocol=protocol,
                )
                results.append(
                    {
                        "dataset": "NYUv2",
                        "image_id": image_id,
                        "cluster_id": row["cluster_id"],
                        "error_type": row["error_type"],
                        "variant_id": row["variant_id"],
                        "template_id": row["template_id"],
                        **metrics,
                    }
                )
            _write_csv(args.output, results)
            print(
                f"[{image_position:03d}/{len(image_ids):03d}] {image_id}",
                flush=True,
            )
    results.sort(
        key=lambda row: (
            str(row["image_id"]),
            str(row["error_type"]),
            int(row["variant_id"]),
        )
    )
    _write_csv(args.output, results)
    summary = summarize_sensitivity(results)
    summary.update(
        {
            "dataset": "NYUv2",
            "source_split": "official_train_diagnostic_only",
            "image_count": len(image_ids),
            "row_count": len(results),
            "cluster_count": len({row["cluster_id"] for row in results}),
            "intervention_sha256": _file_sha256(args.interventions),
            "eval_protocol_sha256": _file_sha256(args.eval_protocol),
            "nyuv2_labeled_sha256": _file_sha256(args.nyuv2_labeled),
            "tr2m_checkpoint_sha256": expected_tr2m,
            "depth_checkpoint_sha256": expected_depth,
            "encoder_weights": _encoder_weight_provenance(args.cache_root),
            "output_sha256": _file_sha256(args.output),
        }
    )
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--interventions", type=Path, required=True)
    parser.add_argument("--eval-protocol", type=Path, required=True)
    parser.add_argument("--release-audit", type=Path, required=True)
    parser.add_argument("--nyuv2-labeled", type=Path, required=True)
    parser.add_argument("--tr2m-root", type=Path, required=True)
    parser.add_argument("--tr2m-checkpoint", type=Path, required=True)
    parser.add_argument("--depth-checkpoint", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument(
        "--restart",
        action="store_true",
        help="ignore an existing complete-image checkpoint CSV",
    )
    return parser.parse_args()


def main() -> None:
    summary = run_diagnostic(_parse_args())
    if summary["status"] == "STOP_H_SENSITIVITY":
        raise SystemExit(4)


if __name__ == "__main__":
    main()
