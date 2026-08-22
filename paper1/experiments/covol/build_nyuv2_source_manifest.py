"""Adapt the official NYUv2 labeled archive to CoVoL source JSONL files.

The adapter reads ``nyu_depth_v2_labeled.mat`` (MATLAB v7.3/HDF5) together
with the official ``splits.mat`` containing ``trainNdxs`` and ``testNdxs``.
It never trusts a precomputed RGB digest: every digest is computed from the
canonical uint8 HWC pixels stored in the labeled archive.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any

from paper1.experiments.covol.build_image_manifest import _file_sha256

DATASET_NAME = "NYUv2"
ADAPTER_VERSION = "nyuv2-labeled-mat-v1"
NYUV2_EVAL_PROTOCOL_SHA256 = (
    "a2a39e31819342668e521924a26884faeeec59b687ee9ca75a8a8f21f574ce78"
)
DEFAULT_EVAL_PROTOCOL_PATH = (
    Path(__file__).resolve().parents[2]
    / "configs"
    / "covol"
    / "depth_eval_protocol_v1.json"
)
_RAW_RGB_PATTERN = re.compile(
    r"^r-(?P<timestamp>[0-9]+(?:\.[0-9]+)?)-(?P<counter>[0-9]+)\.[^.]+$"
)


class Nyuv2DependencyError(RuntimeError):
    """Raised when optional packages required for MATLAB input are absent."""


@dataclass(frozen=True)
class _SourceProvenance:
    labeled_path: str
    labeled_sha256: str
    splits_path: str
    splits_sha256: str
    depth_key: str


def _import_dependency(name: str) -> Any:
    return importlib.import_module(name)


def _load_dependencies() -> tuple[Any, Any, Any]:
    modules: dict[str, Any] = {}
    missing: list[str] = []
    for name in ("h5py", "numpy", "scipy.io"):
        try:
            modules[name] = _import_dependency(name)
        except ImportError:
            missing.append(name)
    if missing:
        packages = ", ".join(missing)
        raise Nyuv2DependencyError(
            "NYUv2 MATLAB input requires h5py, numpy, and scipy; "
            f"missing: {packages}. Install them in the declared Python 3.12 "
            "research environment before running this adapter."
        )
    return modules["h5py"], modules["numpy"], modules["scipy.io"]


def _portable_source_path(path: Path, source_root: Path) -> str:
    resolved_path = path.resolve()
    resolved_root = source_root.resolve()
    try:
        relative = resolved_path.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(
            f"source file {resolved_path} is outside source root {resolved_root}"
        ) from error
    return relative.as_posix()


def _decode_matlab_chars(value: Any, numpy: Any) -> str:
    codepoints = numpy.asarray(value).reshape(-1).tolist()
    return "".join(chr(int(codepoint)) for codepoint in codepoints if int(codepoint))


def _matlab_cell_length(dataset: Any) -> int:
    shape = tuple(int(value) for value in dataset.shape)
    if len(shape) != 2 or min(shape) != 1:
        raise ValueError(f"MATLAB cell array must be a row or column vector: {shape}")
    return max(shape)


def _read_matlab_cell_strings_at_indices(
    handle: Any,
    key: str,
    zero_based_indices: Sequence[int],
    numpy: Any,
) -> list[str]:
    if key not in handle:
        raise ValueError(f"labeled MAT archive lacks required variable {key!r}")
    dataset = handle[key]
    cell_count = _matlab_cell_length(dataset)
    values: list[str] = []
    for index in zero_based_indices:
        if index < 0 or index >= cell_count:
            raise ValueError(f"{key!r} cell index {index} lies outside the archive")
        reference = dataset[0, index] if dataset.shape[0] == 1 else dataset[index, 0]
        try:
            target = handle[reference][()]
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"could not dereference {key!r} MATLAB cell") from error
        values.append(_decode_matlab_chars(target, numpy))
    return values


def _read_matlab_cell_strings(handle: Any, key: str, numpy: Any) -> list[str]:
    if key not in handle:
        raise ValueError(f"labeled MAT archive lacks required variable {key!r}")
    return _read_matlab_cell_strings_at_indices(
        handle,
        key,
        tuple(range(_matlab_cell_length(handle[key]))),
        numpy,
    )


def _normalized_raw_path(value: str) -> PurePosixPath:
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("rawRgbFilenames contains an empty path")
    return PurePosixPath(normalized)


def _raw_rgb_sort_key(raw_rgb_filename: str) -> tuple[Decimal, int, str]:
    name = _normalized_raw_path(raw_rgb_filename).name
    match = _RAW_RGB_PATTERN.fullmatch(name)
    if match is None:
        raise ValueError(
            f"NYUv2 raw RGB filename {raw_rgb_filename!r} does not match "
            "r-<timestamp>-<counter>.<extension>"
        )
    try:
        timestamp = Decimal(match.group("timestamp"))
    except InvalidOperation as error:
        raise ValueError(
            f"invalid timestamp in NYUv2 RGB filename {raw_rgb_filename!r}"
        ) from error
    return timestamp, int(match.group("counter")), name


def _derive_frame_locations(
    scenes: Sequence[str], raw_rgb_filenames: Sequence[str]
) -> list[tuple[str, int]]:
    if len(scenes) != len(raw_rgb_filenames):
        raise ValueError("scenes and rawRgbFilenames have different lengths")

    by_sequence: dict[str, list[tuple[int, str]]] = defaultdict(list)
    sequence_by_index: list[str] = []
    for index, (scene_value, raw_rgb_filename) in enumerate(
        zip(scenes, raw_rgb_filenames, strict=True)
    ):
        scene = scene_value.strip()
        if not scene:
            raise ValueError(f"NYUv2 frame {index + 1} has an empty scene")
        raw_path = _normalized_raw_path(raw_rgb_filename)
        sequence = raw_path.parent.name
        if sequence in {"", "."}:
            raise ValueError(
                f"NYUv2 raw RGB path {raw_rgb_filename!r} lacks a scene directory"
            )
        _raw_rgb_sort_key(raw_rgb_filename)
        sequence_by_index.append(sequence)
        by_sequence[sequence].append((index, raw_rgb_filename))

    frame_index_by_index: dict[int, int] = {}
    for members in by_sequence.values():
        ordered = sorted(members, key=lambda item: _raw_rgb_sort_key(item[1]))
        for frame_index, (source_index, _) in enumerate(ordered):
            frame_index_by_index[source_index] = frame_index

    return [
        (sequence_by_index[index], frame_index_by_index[index])
        for index in range(len(scenes))
    ]


def _split_lookup(
    train_indices: Iterable[int], test_indices: Iterable[int], *, frame_count: int
) -> dict[int, str]:
    train_values = [int(value) for value in train_indices]
    test_values = [int(value) for value in test_indices]
    train = set(train_values)
    test = set(test_values)
    if len(train) != len(train_values) or len(test) != len(test_values):
        raise ValueError("official NYUv2 split contains duplicate indices")
    if not train or not test:
        raise ValueError("official NYUv2 train and test splits must both be non-empty")
    if train & test:
        raise ValueError(f"official NYUv2 split overlap: {sorted(train & test)[:5]}")
    expected = set(range(1, frame_count + 1))
    observed = train | test
    if observed != expected:
        missing = sorted(expected - observed)[:5]
        unexpected = sorted(observed - expected)[:5]
        raise ValueError(
            "official NYUv2 split must partition every labeled frame; "
            f"missing={missing}, unexpected={unexpected}"
        )
    return {
        index: ("train" if index in train else "test") for index in sorted(observed)
    }


def _normalize_rgb_frame(value: Any, numpy: Any) -> Any:
    frame = numpy.asarray(value)
    if frame.ndim != 3:
        raise ValueError(f"NYUv2 RGB frame must be rank 3, got shape {frame.shape}")
    if frame.shape[0] == 3:
        frame = frame.transpose(2, 1, 0)
    elif frame.shape[-1] != 3:
        raise ValueError(
            f"NYUv2 RGB frame has no channel axis of length 3: {frame.shape}"
        )
    if frame.dtype != numpy.uint8:
        raise ValueError(f"NYUv2 RGB frame must be uint8, got {frame.dtype}")
    return numpy.ascontiguousarray(frame)


def _normalize_plane(
    value: Any, *, height: int, width: int, name: str, numpy: Any
) -> Any:
    plane = numpy.asarray(value)
    if plane.ndim != 2:
        raise ValueError(f"NYUv2 {name} frame must be rank 2, got {plane.shape}")
    if plane.shape == (width, height):
        plane = plane.T
    elif plane.shape != (height, width):
        raise ValueError(
            f"NYUv2 {name} shape {plane.shape} is incompatible with "
            f"RGB shape {(height, width)}"
        )
    return numpy.ascontiguousarray(plane)


def _entity_record(
    *,
    matlab_index: int,
    class_id: int,
    instance_id: int,
    class_name: str | None,
    mask_area_pixels: int,
    valid_depth_count: int,
    median_depth: float | None,
    eval_mask_area_pixels: int | None = None,
    eval_valid_depth_count: int | None = None,
    eval_median_depth: float | None = None,
) -> dict[str, Any]:
    normalized_class_name = str(class_name or "").strip()
    if not normalized_class_name:
        raise ValueError(f"NYUv2 class ID {class_id} lacks a languageable class name")
    record = {
        "entity_id": (
            f"nyuv2:{matlab_index:04d}:class-{class_id}:instance-{instance_id}"
        ),
        "class_id": class_id,
        "class_name": normalized_class_name,
        "instance_id": instance_id,
        "reliable_mask": True,
        "mask_area_pixels": mask_area_pixels,
        "valid_depth_count": valid_depth_count,
        "median_depth": median_depth,
    }
    if eval_mask_area_pixels is not None:
        record.update(
            {
                "eval_mask_area_pixels": eval_mask_area_pixels,
                "eval_valid_depth_count": eval_valid_depth_count,
                "eval_median_depth": eval_median_depth,
            }
        )
    return record


def _summarize_entities_from_values(
    labels: Sequence[int],
    instances: Sequence[int],
    depths: Sequence[float],
    *,
    matlab_index: int,
    class_names: Mapping[int, str],
) -> list[dict[str, Any]]:
    if not (len(labels) == len(instances) == len(depths)):
        raise ValueError("labels, instances, and depths have different pixel counts")
    areas: dict[tuple[int, int], int] = defaultdict(int)
    depth_values: dict[tuple[int, int], list[float]] = defaultdict(list)
    for label_value, instance_value, depth_value in zip(
        labels, instances, depths, strict=True
    ):
        class_id = int(label_value)
        instance_id = int(instance_value)
        if class_id < 0 or instance_id < 0:
            raise ValueError("NYUv2 class and instance IDs must be nonnegative")
        if class_id == 0:
            continue
        key = (class_id, instance_id)
        areas[key] += 1
        numeric_depth = float(depth_value)
        if math.isfinite(numeric_depth) and numeric_depth > 0:
            depth_values[key].append(numeric_depth)

    return [
        _entity_record(
            matlab_index=matlab_index,
            class_id=class_id,
            instance_id=instance_id,
            class_name=class_names.get(class_id),
            mask_area_pixels=areas[(class_id, instance_id)],
            valid_depth_count=len(depth_values[(class_id, instance_id)]),
            median_depth=_median(depth_values[(class_id, instance_id)]),
        )
        for class_id, instance_id in sorted(areas)
    ]


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _summarize_entities_numpy(
    labels: Any,
    instances: Any,
    depths: Any,
    *,
    matlab_index: int,
    class_names: Mapping[int, str],
    eval_protocol: Mapping[str, Any],
    numpy: Any,
) -> list[dict[str, Any]]:
    label_values = numpy.asarray(labels).reshape(-1)
    instance_values = numpy.asarray(instances).reshape(-1)
    depth_values = numpy.asarray(depths).reshape(-1)
    if not (label_values.size == instance_values.size == depth_values.size):
        raise ValueError("labels, instances, and depths have different pixel counts")

    if bool(numpy.any(label_values < 0)) or bool(numpy.any(instance_values < 0)):
        raise ValueError("NYUv2 class and instance IDs must be nonnegative")
    annotated = (label_values > 0) & (instance_values >= 0)
    if not bool(numpy.any(annotated)):
        return []
    pairs = numpy.stack(
        (label_values[annotated], instance_values[annotated]), axis=1
    ).astype(numpy.int64, copy=False)
    unique_pairs, inverse, area_counts = numpy.unique(
        pairs, axis=0, return_inverse=True, return_counts=True
    )
    annotated_depths = depth_values[annotated]
    valid_depth = numpy.isfinite(annotated_depths) & (annotated_depths > 0)
    height, width = (int(labels.shape[0]), int(labels.shape[1]))
    if (
        int(eval_protocol["image_height"]) != height
        or int(eval_protocol["image_width"]) != width
    ):
        raise ValueError("NYUv2 eval protocol dimensions do not match source frame")
    crop = eval_protocol["crop"]
    y_start = int(crop["y_start_inclusive"])
    y_end = int(crop["y_end_exclusive"])
    x_start = int(crop["x_start_inclusive"])
    x_end = int(crop["x_end_exclusive"])
    if not (0 <= y_start < y_end <= height and 0 <= x_start < x_end <= width):
        raise ValueError("NYUv2 eval crop lies outside the source frame")
    eval_region = numpy.zeros(labels.shape, dtype=bool)
    eval_region[y_start:y_end, x_start:x_end] = True
    eval_region_annotated = eval_region.reshape(-1)[annotated]
    minimum_depth = float(eval_protocol["minimum_depth_exclusive_m"])
    maximum_depth = float(eval_protocol["maximum_depth_exclusive_m"])
    eval_valid_depth = (
        eval_region_annotated
        & numpy.isfinite(annotated_depths)
        & (annotated_depths > minimum_depth)
        & (annotated_depths < maximum_depth)
    )

    entities: list[dict[str, Any]] = []
    for entity_index, pair in enumerate(unique_pairs):
        class_id = int(pair[0])
        instance_id = int(pair[1])
        member_depths = annotated_depths[valid_depth & (inverse == entity_index)]
        member_mask = inverse == entity_index
        eval_member_depths = annotated_depths[eval_valid_depth & member_mask]
        valid_depth_count = int(member_depths.size)
        entities.append(
            _entity_record(
                matlab_index=matlab_index,
                class_id=class_id,
                instance_id=instance_id,
                class_name=class_names.get(class_id),
                mask_area_pixels=int(area_counts[entity_index]),
                valid_depth_count=valid_depth_count,
                median_depth=(
                    float(numpy.median(member_depths)) if valid_depth_count else None
                ),
                eval_mask_area_pixels=int(
                    numpy.count_nonzero(eval_region_annotated & member_mask)
                ),
                eval_valid_depth_count=int(eval_member_depths.size),
                eval_median_depth=(
                    float(numpy.median(eval_member_depths))
                    if eval_member_depths.size
                    else None
                ),
            )
        )
    return entities


def _build_frame_record(
    *,
    matlab_index: int,
    official_split: str,
    scene_id: str,
    sequence_id: str,
    frame_index: int,
    raw_rgb_filename: str,
    scene_type: str | None,
    rgb_bytes: bytes,
    height: int,
    width: int,
    entities: list[dict[str, Any]],
    provenance: _SourceProvenance,
    eval_protocol_sha256: str | None = None,
    eval_protocol: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rgb_sha256 = hashlib.sha256(rgb_bytes).hexdigest()
    common_source = {
        "path": provenance.labeled_path,
        "sha256": provenance.labeled_sha256,
        "matlab_index": matlab_index,
    }
    record = {
        "dataset": DATASET_NAME,
        "image_id": f"nyuv2_labeled_{matlab_index:04d}",
        "scene_id": scene_id,
        "sequence_id": sequence_id,
        "frame_index": frame_index,
        "official_split": official_split,
        "rgb_sha256": rgb_sha256,
        "rgb_height": height,
        "rgb_width": width,
        "rgb_byte_encoding": "uint8_hwc_c_order",
        "raw_rgb_filename": raw_rgb_filename.replace("\\", "/"),
        "scene_type": scene_type,
        "entities": entities,
        "annotation_available": True,
        "annotation_source": provenance.labeled_path,
        "annotation_sha256": provenance.labeled_sha256,
        "depth_available": True,
        "depth_source": provenance.labeled_path,
        "depth_sha256": provenance.labeled_sha256,
        "adapter": ADAPTER_VERSION,
        "archive_integrity_scope": "blind_whole_archive_sha256",
        "semantic_decode_scope": f"official_{official_split}_only",
        "source_detail": {
            "rgb": {**common_source, "dataset_key": "images"},
            "annotation": {
                **common_source,
                "labels_key": "labels",
                "instances_key": "instances",
            },
            "depth": {
                **common_source,
                "dataset_key": provenance.depth_key,
                "valid_rule": "finite_and_gt_zero_meters",
            },
            "official_split": {
                "path": provenance.splits_path,
                "sha256": provenance.splits_sha256,
                "train_key": "trainNdxs",
                "test_key": "testNdxs",
                "matlab_index_base": 1,
            },
        },
    }
    if eval_protocol_sha256 is not None and eval_protocol is not None:
        record["eval_protocol_sha256"] = eval_protocol_sha256
        record["source_detail"]["evaluation"] = dict(eval_protocol)
    return record


def _validate_split_records(
    records: Sequence[Mapping[str, Any]], *, official_split: str
) -> None:
    if not records:
        raise ValueError(
            f"NYUv2 source adapter produced an empty {official_split} split"
        )
    image_ids = [str(record["image_id"]) for record in records]
    rgb_hashes = [str(record["rgb_sha256"]) for record in records]
    if len(set(image_ids)) != len(image_ids):
        raise ValueError("NYUv2 source adapter produced duplicate image IDs")
    if len(set(rgb_hashes)) != len(rgb_hashes):
        raise ValueError("NYUv2 source adapter detected duplicate RGB content")
    if any(record["official_split"] != official_split for record in records):
        raise ValueError(
            f"NYUv2 {official_split} output contains a frame from another split"
        )


def _validate_official_metadata_isolation(
    official_splits: Mapping[int, str],
    scenes: Sequence[str],
    frame_locations: Sequence[tuple[str, int]],
) -> None:
    groups: dict[str, dict[str, set[str]]] = {
        "scene_id": {"train": set(), "test": set()},
        "sequence_id": {"train": set(), "test": set()},
    }
    for zero_based_index, scene_value in enumerate(scenes):
        matlab_index = zero_based_index + 1
        official_split = official_splits[matlab_index]
        sequence_id, _ = frame_locations[zero_based_index]
        groups["scene_id"][official_split].add(scene_value.strip())
        groups["sequence_id"][official_split].add(sequence_id)

    for group_key in ("scene_id", "sequence_id"):
        overlap = groups[group_key]["train"] & groups[group_key]["test"]
        if overlap:
            raise ValueError(
                f"official NYUv2 train/test {group_key} overlap: "
                f"{sorted(overlap)[:5]}"
            )


def _records_from_selected_indices(
    *,
    selected_indices: Sequence[int],
    official_split: str,
    images: Any,
    labels: Any,
    instances: Any,
    depths: Any,
    scenes: Mapping[int, str],
    raw_rgb_filenames: Mapping[int, str],
    scene_types: Mapping[int, str | None],
    frame_locations: Mapping[int, tuple[str, int]],
    class_names: Mapping[int, str],
    provenance: _SourceProvenance,
    eval_protocol_sha256: str,
    eval_protocol: Mapping[str, Any],
    numpy: Any,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for matlab_index in selected_indices:
        zero_based_index = matlab_index - 1
        rgb = _normalize_rgb_frame(images[zero_based_index], numpy)
        height, width = (int(rgb.shape[0]), int(rgb.shape[1]))
        label_frame = _normalize_plane(
            labels[zero_based_index],
            height=height,
            width=width,
            name="labels",
            numpy=numpy,
        )
        instance_frame = _normalize_plane(
            instances[zero_based_index],
            height=height,
            width=width,
            name="instances",
            numpy=numpy,
        )
        depth_frame = _normalize_plane(
            depths[zero_based_index],
            height=height,
            width=width,
            name=provenance.depth_key,
            numpy=numpy,
        )
        entities = _summarize_entities_numpy(
            label_frame,
            instance_frame,
            depth_frame,
            matlab_index=matlab_index,
            class_names=class_names,
            eval_protocol=eval_protocol,
            numpy=numpy,
        )
        sequence_id, frame_index = frame_locations[matlab_index]
        records.append(
            _build_frame_record(
                matlab_index=matlab_index,
                official_split=official_split,
                scene_id=scenes[matlab_index].strip(),
                sequence_id=sequence_id,
                frame_index=frame_index,
                raw_rgb_filename=raw_rgb_filenames[matlab_index],
                scene_type=scene_types[matlab_index],
                rgb_bytes=rgb.tobytes(order="C"),
                height=height,
                width=width,
                entities=entities,
                provenance=provenance,
                eval_protocol_sha256=eval_protocol_sha256,
                eval_protocol=eval_protocol,
            )
        )
    records.sort(key=lambda record: str(record["image_id"]))
    _validate_split_records(records, official_split=official_split)
    return records


def _extract_records(
    labeled_mat_path: Path,
    splits_mat_path: Path,
    *,
    official_split: str,
    provenance: _SourceProvenance,
    eval_protocol_sha256: str,
    eval_protocol: Mapping[str, Any],
) -> list[dict[str, Any]]:
    h5py, numpy, scipy_io = _load_dependencies()
    split_data = scipy_io.loadmat(
        str(splits_mat_path), variable_names=("trainNdxs", "testNdxs")
    )
    for key in ("trainNdxs", "testNdxs"):
        if key not in split_data:
            raise ValueError(f"official split MAT lacks required variable {key!r}")

    with h5py.File(labeled_mat_path, "r") as handle:
        required_keys = {
            "images",
            "names",
            "scenes",
            "rawRgbFilenames",
            "labels",
            "instances",
            provenance.depth_key,
        }
        missing_keys = sorted(required_keys - set(handle.keys()))
        if missing_keys:
            raise ValueError(
                f"labeled MAT archive lacks variables: {', '.join(missing_keys)}"
            )

        class_name_values = _read_matlab_cell_strings(handle, "names", numpy)
        class_names = {
            index: name for index, name in enumerate(class_name_values, start=1)
        }

        images = handle["images"]
        labels = handle["labels"]
        instances = handle["instances"]
        depths = handle[provenance.depth_key]
        frame_count = int(images.shape[0])
        for key in ("scenes", "rawRgbFilenames"):
            if _matlab_cell_length(handle[key]) != frame_count:
                raise ValueError(
                    f"NYUv2 {key} count does not match the dense frame count"
                )
        if "sceneTypes" in handle and (
            _matlab_cell_length(handle["sceneTypes"]) != frame_count
        ):
            raise ValueError(
                "NYUv2 sceneTypes count does not match the dense frame count"
            )
        for key, dataset in (
            ("images", images),
            ("labels", labels),
            ("instances", instances),
            (provenance.depth_key, depths),
        ):
            if int(dataset.shape[0]) != frame_count:
                raise ValueError(
                    f"NYUv2 {key} frame count {dataset.shape[0]} does not match "
                    f"scene count {frame_count}"
                )

        train_indices = numpy.asarray(split_data["trainNdxs"]).reshape(-1).tolist()
        test_indices = numpy.asarray(split_data["testNdxs"]).reshape(-1).tolist()
        official_splits = _split_lookup(
            train_indices, test_indices, frame_count=frame_count
        )
        selected_indices = sorted(
            index
            for index, split_name in official_splits.items()
            if split_name == official_split
        )
        selected_zero_based = [index - 1 for index in selected_indices]
        selected_scenes = _read_matlab_cell_strings_at_indices(
            handle,
            "scenes",
            selected_zero_based,
            numpy,
        )
        selected_raw_rgb_filenames = _read_matlab_cell_strings_at_indices(
            handle,
            "rawRgbFilenames",
            selected_zero_based,
            numpy,
        )
        selected_scene_types: list[str | None] = (
            _read_matlab_cell_strings_at_indices(
                handle,
                "sceneTypes",
                selected_zero_based,
                numpy,
            )
            if "sceneTypes" in handle
            else [None] * len(selected_indices)
        )
        selected_frame_locations = _derive_frame_locations(
            selected_scenes,
            selected_raw_rgb_filenames,
        )
        scenes_by_index = dict(zip(selected_indices, selected_scenes, strict=True))
        raw_rgb_by_index = dict(
            zip(selected_indices, selected_raw_rgb_filenames, strict=True)
        )
        scene_types_by_index = dict(
            zip(selected_indices, selected_scene_types, strict=True)
        )
        frame_locations_by_index = dict(
            zip(selected_indices, selected_frame_locations, strict=True)
        )
        return _records_from_selected_indices(
            selected_indices=selected_indices,
            official_split=official_split,
            images=images,
            labels=labels,
            instances=instances,
            depths=depths,
            scenes=scenes_by_index,
            raw_rgb_filenames=raw_rgb_by_index,
            scene_types=scene_types_by_index,
            frame_locations=frame_locations_by_index,
            class_names=class_names,
            provenance=provenance,
            eval_protocol_sha256=eval_protocol_sha256,
            eval_protocol=eval_protocol,
            numpy=numpy,
        )


def _load_eval_protocol(path: Path, *, depth_key: str) -> tuple[dict[str, Any], str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
        raise ValueError("depth eval protocol must use schema_version=1")
    datasets = payload.get("datasets")
    if not isinstance(datasets, Mapping) or not isinstance(
        datasets.get(DATASET_NAME), Mapping
    ):
        raise ValueError("depth eval protocol lacks NYUv2 settings")
    protocol = dict(datasets[DATASET_NAME])
    if protocol.get("depth_key") != depth_key:
        raise ValueError("NYUv2 depth key conflicts with the eval protocol")
    protocol_sha256 = _file_sha256(path)
    if protocol_sha256 != NYUV2_EVAL_PROTOCOL_SHA256:
        raise ValueError("NYUv2 eval protocol does not match the frozen SHA256")
    return protocol, protocol_sha256


def _write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def build_nyuv2_source_manifest(
    labeled_mat_path: Path,
    splits_mat_path: Path,
    output_path: Path,
    *,
    official_split: str,
    allow_official_test_read: bool = False,
    source_root: Path,
    depth_key: str = "rawDepths",
    eval_protocol_path: Path = DEFAULT_EVAL_PROTOCOL_PATH,
) -> None:
    """Build one split without decoding dense arrays from the other split."""
    if official_split not in {"train", "test"}:
        raise ValueError("official_split must be 'train' or 'test'")
    if official_split == "test" and not allow_official_test_read:
        raise PermissionError(
            "official NYUv2 test dense arrays are frozen until Step 008; "
            "pass --allow-official-test-read only after the method is frozen"
        )
    if depth_key not in {"rawDepths", "depths"}:
        raise ValueError("depth_key must be 'rawDepths' or 'depths'")
    for path in (labeled_mat_path, splits_mat_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    if output_path.resolve() in {
        labeled_mat_path.resolve(),
        splits_mat_path.resolve(),
    }:
        raise ValueError("output path must not overwrite a source MAT file")

    provenance = _SourceProvenance(
        labeled_path=_portable_source_path(labeled_mat_path, source_root),
        labeled_sha256=_file_sha256(labeled_mat_path),
        splits_path=_portable_source_path(splits_mat_path, source_root),
        splits_sha256=_file_sha256(splits_mat_path),
        depth_key=depth_key,
    )
    eval_protocol, eval_protocol_sha256 = _load_eval_protocol(
        eval_protocol_path,
        depth_key=depth_key,
    )
    records = _extract_records(
        labeled_mat_path,
        splits_mat_path,
        official_split=official_split,
        provenance=provenance,
        eval_protocol_sha256=eval_protocol_sha256,
        eval_protocol=eval_protocol,
    )
    _write_jsonl(output_path, records)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labeled-mat", type=Path, required=True)
    parser.add_argument("--splits-mat", type=Path, required=True)
    parser.add_argument("--official-split", choices=("train", "test"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-official-test-read",
        action="store_true",
        help="required for test only after the Step-008 method freeze",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path.cwd(),
        help="root used to store portable source paths (default: current directory)",
    )
    parser.add_argument(
        "--depth-key",
        choices=("rawDepths", "depths"),
        default="rawDepths",
        help="rawDepths is the conservative default for valid-depth coverage",
    )
    parser.add_argument(
        "--eval-protocol",
        type=Path,
        default=DEFAULT_EVAL_PROTOCOL_PATH,
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    build_nyuv2_source_manifest(
        args.labeled_mat,
        args.splits_mat,
        args.output,
        official_split=args.official_split,
        allow_official_test_read=args.allow_official_test_read,
        source_root=args.source_root,
        depth_key=args.depth_key,
        eval_protocol_path=args.eval_protocol,
    )


if __name__ == "__main__":
    main()
