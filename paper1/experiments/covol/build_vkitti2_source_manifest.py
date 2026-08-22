"""Build a provenance-bound Virtual KITTI 2 source manifest.

The adapter reads only locally extracted official version-2.0.3 archives.  It
does not download data and it groups every weather/camera clone of one base
``SceneXX`` under the same ``scene_id`` so later split construction cannot
mistake correlated renders for independent scenes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
from PIL import Image

DATASET_NAME = "Virtual KITTI 2"
DATASET_VERSION = "2.0.3"
ADAPTER_VERSION = "vkitti2-source-v1"
CHECKSUM_SOURCE = (
    "https://download.europe.naverlabs.com/virtual_kitti_2.0.3/"
    "vkitti_2.0.3_md5_checksums.txt"
)
ARCHIVE_MD5 = {
    "vkitti_2.0.3_classSegmentation.tar": "e8658ab49250e61f1caa174625563263",
    "vkitti_2.0.3_depth.tar": "1d34a96f870fc5d33b482df87844f5e4",
    "vkitti_2.0.3_instanceSegmentation.tar": "c79684c6344e50663587b8da848535e7",
    "vkitti_2.0.3_rgb.tar": "1e00a143a397c2c53aa9720a868fe34a",
    "vkitti_2.0.3_textgt.tar.gz": "855f7f37746e5508f094e522c9cf41f4",
}
SCENES = frozenset({"Scene01", "Scene02", "Scene06", "Scene18", "Scene20"})
VARIATIONS = frozenset(
    {
        "15-deg-left",
        "15-deg-right",
        "30-deg-left",
        "30-deg-right",
        "clone",
        "fog",
        "morning",
        "overcast",
        "rain",
        "sunset",
    }
)
CAMERAS = frozenset({"Camera_0", "Camera_1"})
EVAL_PROTOCOL = {
    "depth_scale_meters_per_unit": 0.01,
    "depth_validity": "uint16_value_gt_0",
    "mask_definition": "instancegt_value_eq_track_id_plus_one",
    "metric_crop": "full_image",
    "version": "vkitti2-full-frame-v1",
}
VKITTI2_EVAL_PROTOCOL_SHA256 = hashlib.sha256(
    json.dumps(EVAL_PROTOCOL, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()

_SCENE_RE = re.compile(r"^Scene\d{2}$")
_CAMERA_RE = re.compile(r"^Camera_[01]$")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _combined_sha256(values: Mapping[str, str]) -> str:
    payload = json.dumps(values, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_official_checksums(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            fields = stripped.split()
            if len(fields) != 2 or re.fullmatch(r"[0-9a-fA-F]{32}", fields[0]) is None:
                raise ValueError(f"{path}:{line_number}: invalid MD5 checksum row")
            name = fields[1].lstrip("*")
            if name in parsed:
                raise ValueError(f"{path}:{line_number}: duplicate archive {name!r}")
            parsed[name] = fields[0].lower()
    mismatches = {
        name: parsed.get(name)
        for name, expected in ARCHIVE_MD5.items()
        if parsed.get(name) != expected
    }
    if mismatches:
        raise ValueError(
            "Virtual KITTI 2 archive checksums do not match official version 2.0.3: "
            f"{mismatches}"
        )
    return {name: parsed[name] for name in sorted(ARCHIVE_MD5)}


def _read_frame_index(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    identities: set[tuple[str, str, str, int]] = set()
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, Mapping):
                raise ValueError(f"{path}:{line_number}: row must be a JSON object")
            scene = str(value.get("scene", "")).strip()
            variation = str(value.get("variation", "")).strip()
            camera = str(value.get("camera", "")).strip()
            frame_value = value.get("frame_index")
            if isinstance(frame_value, bool):
                raise ValueError(
                    f"{path}:{line_number}: frame_index must be an integer"
                )
            try:
                frame_index = int(frame_value)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"{path}:{line_number}: frame_index must be an integer"
                ) from error
            if frame_index != frame_value or frame_index < 0:
                raise ValueError(f"{path}:{line_number}: invalid frame_index")
            if scene not in SCENES or _SCENE_RE.fullmatch(scene) is None:
                raise ValueError(f"{path}:{line_number}: unknown official scene")
            if variation not in VARIATIONS:
                raise ValueError(f"{path}:{line_number}: unknown official variation")
            if camera not in CAMERAS or _CAMERA_RE.fullmatch(camera) is None:
                raise ValueError(f"{path}:{line_number}: unknown official camera")
            if value.get("official_split", "train") != "train":
                raise ValueError(
                    f"{path}:{line_number}: fallback source is training-only"
                )
            identity = (scene, variation, camera, frame_index)
            if identity in identities:
                raise ValueError(f"{path}:{line_number}: duplicate frame identity")
            identities.add(identity)
            rows.append(
                {
                    "scene": scene,
                    "variation": variation,
                    "camera": camera,
                    "frame_index": frame_index,
                }
            )
    if not rows:
        raise ValueError("Virtual KITTI 2 frame index must not be empty")
    return rows


def _relative_paths(row: Mapping[str, Any]) -> dict[str, Path]:
    scene = str(row["scene"])
    variation = str(row["variation"])
    camera = str(row["camera"])
    frame_index = int(row["frame_index"])
    prefix = Path(scene) / variation
    return {
        "rgb": Path("vkitti_2.0.3_rgb")
        / prefix
        / "frames"
        / "rgb"
        / camera
        / f"rgb_{frame_index:05d}.jpg",
        "depth": Path("vkitti_2.0.3_depth")
        / prefix
        / "frames"
        / "depth"
        / camera
        / f"depth_{frame_index:05d}.png",
        "class": Path("vkitti_2.0.3_classSegmentation")
        / prefix
        / "frames"
        / "classsegmentation"
        / camera
        / f"classgt_{frame_index:05d}.png",
        "instance": Path("vkitti_2.0.3_instanceSegmentation")
        / prefix
        / "frames"
        / "instancesegmentation"
        / camera
        / f"instancegt_{frame_index:05d}.png",
        "colors": Path("vkitti_2.0.3_textgt") / prefix / "colors.txt",
    }


def _read_colors(path: Path) -> dict[tuple[int, int, int], str]:
    colors: dict[tuple[int, int, int], str] = {}
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            fields = line.split()
            if not fields or fields[0].lower() == "category":
                continue
            if len(fields) != 4:
                raise ValueError(f"{path}:{line_number}: invalid colors.txt row")
            try:
                color = tuple(int(value) for value in fields[1:])
            except ValueError as error:
                raise ValueError(
                    f"{path}:{line_number}: invalid colors.txt channel"
                ) from error
            if len(color) != 3 or any(value < 0 or value > 255 for value in color):
                raise ValueError(f"{path}:{line_number}: invalid RGB color")
            colors[color] = fields[0]
    if not colors:
        raise ValueError(f"{path}: colors.txt contains no classes")
    return colors


def _entity_summaries(
    *,
    rgb_path: Path,
    depth_path: Path,
    class_path: Path,
    instance_path: Path,
    colors_path: Path,
) -> list[dict[str, object]]:
    with Image.open(rgb_path) as image:
        rgb_size = image.size
    with Image.open(depth_path) as image:
        depth = np.asarray(image)
    with Image.open(class_path) as image:
        classes = np.asarray(image.convert("RGB"))
    with Image.open(instance_path) as image:
        instances = np.asarray(image)
    expected_shape = (rgb_size[1], rgb_size[0])
    if depth.shape != expected_shape or instances.shape != expected_shape:
        raise ValueError("Virtual KITTI 2 RGB/depth/instance dimensions disagree")
    if classes.shape != (*expected_shape, 3):
        raise ValueError("Virtual KITTI 2 class segmentation dimensions disagree")
    if depth.dtype != np.uint16:
        raise ValueError("Virtual KITTI 2 depth must be uint16 PNG")
    if instances.ndim != 2 or not np.issubdtype(instances.dtype, np.integer):
        raise ValueError("Virtual KITTI 2 instance map must be an indexed PNG")

    color_names = _read_colors(colors_path)
    entities: list[dict[str, object]] = []
    for instance_value in sorted(int(value) for value in np.unique(instances) if value):
        mask = instances == instance_value
        depths_cm = depth[mask]
        valid_depths_cm = depths_cm[depths_cm > 0]
        color_counts = Counter(tuple(map(int, value)) for value in classes[mask])
        dominant_color, _ = color_counts.most_common(1)[0]
        class_name = color_names.get(dominant_color, "Undefined")
        entities.append(
            {
                "class_name": class_name,
                "entity_id": f"track-{instance_value - 1}",
                "eval_mask_area_pixels": int(mask.sum()),
                "eval_median_depth": (
                    float(median(valid_depths_cm.tolist())) / 100.0
                    if valid_depths_cm.size
                    else None
                ),
                "eval_valid_depth_count": int(valid_depths_cm.size),
                "reliable_mask": class_name != "Undefined",
            }
        )
    return entities


def build_vkitti2_source_manifest(
    data_root: Path,
    frame_index_path: Path,
    checksum_path: Path,
    output_path: Path,
) -> list[dict[str, object]]:
    """Build a training-only manifest from extracted official VKITTI2 archives."""

    data_root = data_root.resolve()
    frame_index_path = frame_index_path.resolve()
    checksum_path = checksum_path.resolve()
    output_path = output_path.resolve()
    if not data_root.is_dir():
        raise NotADirectoryError(data_root)
    if not frame_index_path.is_file():
        raise FileNotFoundError(frame_index_path)
    if not checksum_path.is_file():
        raise FileNotFoundError(checksum_path)
    if output_path in {frame_index_path, checksum_path}:
        raise ValueError("output path must not overwrite an input")

    archive_md5 = _read_official_checksums(checksum_path)
    frame_rows = _read_frame_index(frame_index_path)
    frame_index_sha256 = _file_sha256(frame_index_path)
    checksum_file_sha256 = _file_sha256(checksum_path)
    records: list[dict[str, object]] = []
    seen_rgb_hashes: dict[str, str] = {}
    for row in frame_rows:
        relative = _relative_paths(row)
        absolute = {name: data_root / path for name, path in relative.items()}
        missing = [name for name, path in absolute.items() if not path.is_file()]
        if missing:
            raise FileNotFoundError(
                f"{row['scene']}/{row['variation']}/{row['camera']}/"
                f"{row['frame_index']}: missing {missing}"
            )
        file_hashes = {name: _file_sha256(path) for name, path in absolute.items()}
        rgb_hash = file_hashes["rgb"]
        image_id = (
            f"{row['scene']}/{row['variation']}/{row['camera']}/"
            f"{int(row['frame_index']):05d}"
        )
        if rgb_hash in seen_rgb_hashes:
            raise ValueError(
                f"duplicate RGB content hash {rgb_hash!r} for {image_id!r}; "
                f"first seen at {seen_rgb_hashes[rgb_hash]!r}"
            )
        seen_rgb_hashes[rgb_hash] = image_id
        annotation_components = {
            "class_segmentation_sha256": file_hashes["class"],
            "colors_sha256": file_hashes["colors"],
            "instance_segmentation_sha256": file_hashes["instance"],
        }
        records.append(
            {
                "adapter": ADAPTER_VERSION,
                "annotation_available": True,
                "annotation_components": annotation_components,
                "annotation_sha256": _combined_sha256(annotation_components),
                "annotation_source": (
                    f"{relative['instance'].as_posix()}|"
                    f"{relative['class'].as_posix()}|{relative['colors'].as_posix()}"
                ),
                "archive_checksum_file_sha256": checksum_file_sha256,
                "archive_checksum_source": CHECKSUM_SOURCE,
                "archive_md5": archive_md5,
                "camera_id": row["camera"],
                "dataset": DATASET_NAME,
                "dataset_version": DATASET_VERSION,
                "depth_available": True,
                "depth_sha256": file_hashes["depth"],
                "depth_source": relative["depth"].as_posix(),
                "entities": _entity_summaries(
                    rgb_path=absolute["rgb"],
                    depth_path=absolute["depth"],
                    class_path=absolute["class"],
                    instance_path=absolute["instance"],
                    colors_path=absolute["colors"],
                ),
                "eval_protocol": EVAL_PROTOCOL,
                "eval_protocol_sha256": VKITTI2_EVAL_PROTOCOL_SHA256,
                "frame_index": row["frame_index"],
                "frame_index_semantics": "vkitti2_zero_based_frame",
                "identity_resolution": "base_scene_variation_camera_frame",
                "image_id": image_id,
                "official_split": "train",
                "rgb_path": relative["rgb"].as_posix(),
                "rgb_sha256": rgb_hash,
                "scene_id": row["scene"],
                "semantic_decode_scope": "official_v2.0.3_full_frame",
                "sequence_id": (f"{row['scene']}/{row['variation']}/{row['camera']}"),
                "source_license": "CC-BY-NC-SA-3.0-noncommercial",
                "source_split_list_sha256": frame_index_sha256,
                "variation": row["variation"],
            }
        )

    records.sort(key=lambda record: str(record["image_id"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    return records


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--frame-index", type=Path, required=True)
    parser.add_argument("--official-checksums", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    build_vkitti2_source_manifest(
        args.data_root,
        args.frame_index,
        args.official_checksums,
        args.output,
    )


if __name__ == "__main__":
    main()
