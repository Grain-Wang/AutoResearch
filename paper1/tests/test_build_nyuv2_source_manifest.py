from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from paper1.experiments.covol import build_nyuv2_source_manifest as nyuv2


def _provenance() -> nyuv2._SourceProvenance:
    return nyuv2._SourceProvenance(
        labeled_path="paper1/data/raw/nyu_depth_v2_labeled.mat",
        labeled_sha256="a" * 64,
        splits_path="paper1/data/raw/splits.mat",
        splits_sha256="b" * 64,
        depth_key="rawDepths",
    )


def _eval_protocol() -> dict[str, object]:
    return {
        "image_height": 2,
        "image_width": 2,
        "crop": {
            "y_start_inclusive": 0,
            "y_end_exclusive": 2,
            "x_start_inclusive": 0,
            "x_end_exclusive": 2,
        },
        "minimum_depth_exclusive_m": 0.001,
        "maximum_depth_exclusive_m": 10.0,
        "depth_key": "rawDepths",
    }


def test_maps_raw_scene_sequence_and_chronological_frame_index() -> None:
    locations = nyuv2._derive_frame_locations(
        ["office_0001", "office_0001", "kitchen_0002"],
        [
            "office_0001/r-130.200000-20.ppm",
            "office_0001/r-129.900000-10.ppm",
            "kitchen_0002/r-200.000000-30.ppm",
        ],
    )

    assert locations == [
        ("office_0001", 1),
        ("office_0001", 0),
        ("kitchen_0002", 0),
    ]


def test_preserves_distinct_official_scene_and_raw_capture_sequence() -> None:
    assert nyuv2._derive_frame_locations(
        ["living_room_0000"],
        ["bedroom_0010/r-129.900000-10.ppm"],
    ) == [("bedroom_0010", 0)]


def test_entity_summary_uses_only_positive_finite_raw_depth() -> None:
    entities = nyuv2._summarize_entities_from_values(
        labels=[1, 1, 1, 2, 2, 0],
        instances=[1, 1, 1, 1, 1, 0],
        depths=[1.0, 0.0, float("nan"), 2.0, 4.0, 9.0],
        matlab_index=7,
        class_names={1: "chair", 2: "table"},
    )

    assert entities == [
        {
            "entity_id": "nyuv2:0007:class-1:instance-1",
            "class_id": 1,
            "class_name": "chair",
            "instance_id": 1,
            "reliable_mask": True,
            "mask_area_pixels": 3,
            "valid_depth_count": 1,
            "median_depth": 1.0,
        },
        {
            "entity_id": "nyuv2:0007:class-2:instance-1",
            "class_id": 2,
            "class_name": "table",
            "instance_id": 1,
            "reliable_mask": True,
            "mask_area_pixels": 2,
            "valid_depth_count": 2,
            "median_depth": 3.0,
        },
    ]


def test_entity_summary_keeps_class_with_zero_instance_id() -> None:
    entities = nyuv2._summarize_entities_from_values(
        labels=[3, 3, 0],
        instances=[0, 0, 0],
        depths=[2.0, 4.0, 8.0],
        matlab_index=8,
        class_names={3: "wall"},
    )

    assert entities == [
        {
            "entity_id": "nyuv2:0008:class-3:instance-0",
            "class_id": 3,
            "class_name": "wall",
            "instance_id": 0,
            "reliable_mask": True,
            "mask_area_pixels": 2,
            "valid_depth_count": 2,
            "median_depth": 3.0,
        }
    ]


def test_entity_summary_rejects_negative_annotation_ids() -> None:
    with pytest.raises(ValueError, match="must be nonnegative"):
        nyuv2._summarize_entities_from_values(
            labels=[1],
            instances=[-1],
            depths=[1.0],
            matlab_index=9,
            class_names={1: "object"},
        )


def test_entity_summary_rejects_missing_languageable_class_name() -> None:
    with pytest.raises(ValueError, match="lacks a languageable class name"):
        nyuv2._summarize_entities_from_values(
            labels=[1],
            instances=[1],
            depths=[1.0],
            matlab_index=9,
            class_names={},
        )


def test_numpy_entity_summary_applies_frozen_eval_depth_range() -> None:
    numpy = pytest.importorskip("numpy")
    entities = nyuv2._summarize_entities_numpy(
        numpy.ones((2, 2), dtype=numpy.uint16),
        numpy.ones((2, 2), dtype=numpy.uint16),
        numpy.asarray([[0.0, 2.0], [11.0, 4.0]], dtype=numpy.float32),
        matlab_index=10,
        class_names={1: "object"},
        eval_protocol=_eval_protocol(),
        numpy=numpy,
    )

    assert entities[0]["mask_area_pixels"] == 4
    assert entities[0]["valid_depth_count"] == 3
    assert entities[0]["median_depth"] == 4.0
    assert entities[0]["eval_mask_area_pixels"] == 4
    assert entities[0]["eval_valid_depth_count"] == 2
    assert entities[0]["eval_median_depth"] == 3.0


def test_frame_record_hashes_canonical_rgb_bytes_and_records_sources() -> None:
    rgb_bytes = bytes(range(12))
    record = nyuv2._build_frame_record(
        matlab_index=4,
        official_split="train",
        scene_id="bedroom_0001",
        sequence_id="bedroom_0001",
        frame_index=2,
        raw_rgb_filename="bedroom_0001/r-100.25-4.ppm",
        scene_type="bedroom",
        rgb_bytes=rgb_bytes,
        height=2,
        width=2,
        entities=[],
        provenance=_provenance(),
    )

    assert record["image_id"] == "nyuv2_labeled_0004"
    assert record["rgb_sha256"] == hashlib.sha256(rgb_bytes).hexdigest()
    assert record["rgb_byte_encoding"] == "uint8_hwc_c_order"
    assert record["annotation_available"] is True
    assert record["annotation_source"] == ("paper1/data/raw/nyu_depth_v2_labeled.mat")
    assert record["annotation_sha256"] == "a" * 64
    assert record["depth_available"] is True
    assert record["depth_source"] == "paper1/data/raw/nyu_depth_v2_labeled.mat"
    assert record["depth_sha256"] == "a" * 64
    assert record["source_detail"]["depth"]["dataset_key"] == "rawDepths"
    assert record["source_detail"]["official_split"]["sha256"] == "b" * 64


def test_rejects_official_train_test_scene_overlap() -> None:
    with pytest.raises(ValueError, match="scene_id overlap"):
        nyuv2._validate_official_metadata_isolation(
            {1: "train", 2: "test"},
            ["office_0001", "office_0001"],
            [("office_0001", 0), ("office_0001", 1)],
        )


def test_split_indices_must_be_one_based_disjoint_complete_partition() -> None:
    assert nyuv2._split_lookup([1, 3], [2], frame_count=3) == {
        1: "train",
        2: "test",
        3: "train",
    }
    with pytest.raises(ValueError, match="partition every labeled frame"):
        nyuv2._split_lookup([1], [2], frame_count=3)
    with pytest.raises(ValueError, match="split overlap"):
        nyuv2._split_lookup([1, 2], [2, 3], frame_count=3)


def test_missing_matlab_dependencies_has_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_import(name: str) -> object:
        raise ImportError(name)

    monkeypatch.setattr(nyuv2, "_import_dependency", missing_import)

    with pytest.raises(
        nyuv2.Nyuv2DependencyError,
        match="requires h5py, numpy, and scipy",
    ):
        nyuv2._load_dependencies()


def test_train_dense_reader_never_indexes_official_test_frames() -> None:
    numpy = pytest.importorskip("numpy")

    class RecordingDataset:
        def __init__(self, values: list[object]) -> None:
            self.values = values
            self.accessed: list[int] = []

        def __getitem__(self, index: int) -> object:
            self.accessed.append(index)
            return self.values[index]

    images = RecordingDataset(
        [numpy.full((3, 2, 2), value, dtype=numpy.uint8) for value in range(4)]
    )
    labels = RecordingDataset(
        [numpy.ones((2, 2), dtype=numpy.uint16) for _ in range(4)]
    )
    instances = RecordingDataset(
        [numpy.ones((2, 2), dtype=numpy.uint16) for _ in range(4)]
    )
    depths = RecordingDataset(
        [numpy.ones((2, 2), dtype=numpy.float32) for _ in range(4)]
    )

    records = nyuv2._records_from_selected_indices(
        selected_indices=[1, 3],
        official_split="train",
        images=images,
        labels=labels,
        instances=instances,
        depths=depths,
        scenes={1: "train_0001", 3: "train_0002"},
        raw_rgb_filenames={
            1: "train_0001/r-1.0-1.ppm",
            3: "train_0002/r-3.0-3.ppm",
        },
        scene_types={1: "office", 3: "kitchen"},
        frame_locations={1: ("train_0001", 0), 3: ("train_0002", 0)},
        class_names={1: "object"},
        provenance=_provenance(),
        eval_protocol_sha256="c" * 64,
        eval_protocol=_eval_protocol(),
        numpy=numpy,
    )

    assert [record["image_id"] for record in records] == [
        "nyuv2_labeled_0001",
        "nyuv2_labeled_0003",
    ]
    for dataset in (images, labels, instances, depths):
        assert dataset.accessed == [0, 2]


def test_official_test_requires_explicit_post_freeze_permission(
    tmp_path: Path,
) -> None:
    with pytest.raises(PermissionError, match="frozen until Step 008"):
        nyuv2.build_nyuv2_source_manifest(
            tmp_path / "missing-labeled.mat",
            tmp_path / "missing-splits.mat",
            tmp_path / "test.jsonl",
            official_split="test",
            source_root=tmp_path,
        )


def test_source_paths_must_be_portable_beneath_explicit_root(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "data"
    source_root.mkdir()
    source_path = source_root / "nyuv2" / "labeled.mat"
    source_path.parent.mkdir()
    source_path.write_bytes(b"mat")

    assert nyuv2._portable_source_path(source_path, source_root) == "nyuv2/labeled.mat"
    with pytest.raises(ValueError, match="outside source root"):
        nyuv2._portable_source_path(tmp_path / "elsewhere.mat", source_root)
