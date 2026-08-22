"""Shared provenance checks for manifest-dependent CoVoL audit gates."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from paper1.experiments.covol.build_vkitti2_source_manifest import (
    ADAPTER_VERSION as VKITTI2_ADAPTER_VERSION,
)
from paper1.experiments.covol.build_vkitti2_source_manifest import (
    ARCHIVE_MD5 as VKITTI2_ARCHIVE_MD5,
)
from paper1.experiments.covol.build_vkitti2_source_manifest import (
    CHECKSUM_SOURCE as VKITTI2_CHECKSUM_SOURCE,
)
from paper1.experiments.covol.build_vkitti2_source_manifest import (
    DATASET_VERSION as VKITTI2_DATASET_VERSION,
)
from paper1.experiments.covol.build_vkitti2_source_manifest import (
    VKITTI2_EVAL_PROTOCOL_SHA256,
)

SPLIT_ORDER = ("train", "dev", "internal_test")
PILOT_SEED = 20260821
PILOT_SPLIT_COUNTS = {"train": 300, "dev": 100, "internal_test": 100}
STEP003_AUTHORIZATION_SCOPE = "STEP003_ONLY_NOT_STEP005_OR_OFFICIAL_TEST"
PREFREEZE_STATUS = "PASS_PREFREEZE_NO_TEST_ACCESS"
PILOT_SELECTION_STAGE = "PILOT_V1"
EXPANDED_SELECTION_STAGE = "EXPANDED_FOR_POWER"
POWER_GRID_CANONICAL_SHA256 = (
    "17686c65c8eacd749f4ef6d9c2a62b10b7af7a71fdfb20d8c1d5b19582d1c55f"
)
NYUV2_ADAPTER_VERSION = "nyuv2-labeled-mat-v1"
NYUV2_LABELED_ARCHIVE_SHA256 = (
    "2d724b0c0ab358aa1ce5df855e5bd14a2279ab7202efe22f32a30d612dcb86aa"
)
NYUV2_OFFICIAL_SPLITS_SHA256 = (
    "6e081404491a8bfba2f066beaa9713ef6046f9007aa5f799f2a350506a580cee"
)
NYUV2_EVAL_PROTOCOL_SHA256 = (
    "a2a39e31819342668e521924a26884faeeec59b687ee9ca75a8a8f21f574ce78"
)
KITTI_ADAPTER_VERSION = "kitti-source-v1"
KITTI_CANONICAL_TRAINING_SPLIT_SHA256 = (
    "3655308ee4a017094dc620402db3fc587d769cfbfa9a16c6d0f8de6dcbe109ec"
)
KITTI_SOURCE_REPOSITORY_ID = "dangth2004/KITTI-Depth-Estimation"
KITTI_SOURCE_REPOSITORY_REVISION = "a35b64295a395d9adc5988beda226f88922364b1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class SplitAuditLink:
    """Verified linkage between a selected manifest and its leakage audit."""

    split_audit_sha256: str
    manifest_sha256: str
    record_count: int
    datasets: tuple[str, ...]
    audit_mode: str
    selection_stage: str
    authorization_scope: str


def _valid_sha256(value: object) -> bool:
    text = str(value).strip().lower()
    return len(text) == 64 and all(
        character in "0123456789abcdef" for character in text
    )


def file_sha256(path: Path) -> str:
    """Return the lowercase SHA256 of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(path: Path) -> str:
    """Hash JSON semantics independently of whitespace and line endings."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mapping_field(
    record: Mapping[str, Any], field: str, *, context: str
) -> Mapping[str, Any]:
    value = record.get(field)
    if not isinstance(value, Mapping):
        raise ValueError(f"{context}: {field} must be a JSON object")
    return value


def validate_trusted_training_source(record: Mapping[str, Any], *, context: str) -> str:
    """Validate one formal Step-003 row against frozen source contracts.

    The returned digest identifies the canonical *full* training-split source,
    not a caller-selected subset.  This prevents a self-consistent manifest
    from substituting arbitrary adapter, archive, or split hashes.
    """

    dataset = str(record.get("dataset", "")).strip()
    if record.get("official_split") != "train":
        raise ValueError(f"{context}: trusted source must use official_split=train")

    if dataset == "NYUv2":
        if record.get("adapter") != NYUV2_ADAPTER_VERSION:
            raise ValueError(f"{context}: untrusted NYUv2 adapter version")
        if record.get("archive_integrity_scope") != "blind_whole_archive_sha256":
            raise ValueError(f"{context}: NYUv2 archive integrity scope is invalid")
        if record.get("semantic_decode_scope") != "official_train_only":
            raise ValueError(f"{context}: NYUv2 semantic decode scope is invalid")
        if (
            str(record.get("annotation_sha256", "")).lower()
            != NYUV2_LABELED_ARCHIVE_SHA256
            or str(record.get("depth_sha256", "")).lower()
            != NYUV2_LABELED_ARCHIVE_SHA256
        ):
            raise ValueError(f"{context}: NYUv2 labeled archive SHA256 is not frozen")
        if (
            str(record.get("eval_protocol_sha256", "")).lower()
            != NYUV2_EVAL_PROTOCOL_SHA256
        ):
            raise ValueError(f"{context}: NYUv2 evaluation protocol is not frozen")
        source_detail = _mapping_field(record, "source_detail", context=context)
        official_split = _mapping_field(
            source_detail,
            "official_split",
            context=f"{context} source_detail",
        )
        split_sha256 = str(official_split.get("sha256", "")).strip().lower()
        if split_sha256 != NYUV2_OFFICIAL_SPLITS_SHA256:
            raise ValueError(f"{context}: NYUv2 official split SHA256 is not frozen")
        return split_sha256

    if dataset == "KITTI":
        if record.get("adapter") != KITTI_ADAPTER_VERSION:
            raise ValueError(f"{context}: untrusted KITTI adapter version")
        canonical_sha256 = (
            str(record.get("canonical_split_source_sha256", "")).strip().lower()
        )
        if canonical_sha256 != KITTI_CANONICAL_TRAINING_SPLIT_SHA256:
            raise ValueError(f"{context}: KITTI canonical split SHA256 is not frozen")
        if record.get("source_repository_id") != KITTI_SOURCE_REPOSITORY_ID:
            raise ValueError(f"{context}: KITTI source repository is not frozen")
        if (
            str(record.get("source_repository_revision", "")).lower()
            != KITTI_SOURCE_REPOSITORY_REVISION
        ):
            raise ValueError(f"{context}: KITTI source revision is not frozen")
        if not _valid_sha256(record.get("source_split_list_sha256")):
            raise ValueError(f"{context}: KITTI selected split SHA256 is invalid")
        if not _valid_sha256(record.get("selection_audit_sha256")):
            raise ValueError(f"{context}: KITTI selection audit SHA256 is invalid")
        return canonical_sha256

    if dataset == "Virtual KITTI 2":
        if record.get("adapter") != VKITTI2_ADAPTER_VERSION:
            raise ValueError(f"{context}: untrusted Virtual KITTI 2 adapter version")
        if record.get("dataset_version") != VKITTI2_DATASET_VERSION:
            raise ValueError(f"{context}: Virtual KITTI 2 version is not frozen")
        if record.get("archive_checksum_source") != VKITTI2_CHECKSUM_SOURCE:
            raise ValueError(
                f"{context}: Virtual KITTI 2 checksum source is not frozen"
            )
        archive_md5 = record.get("archive_md5")
        if not isinstance(archive_md5, Mapping) or dict(archive_md5) != (
            VKITTI2_ARCHIVE_MD5
        ):
            raise ValueError(
                f"{context}: Virtual KITTI 2 official archive MD5 values mismatch"
            )
        if record.get("semantic_decode_scope") != "official_v2.0.3_full_frame":
            raise ValueError(
                f"{context}: Virtual KITTI 2 semantic decode scope is invalid"
            )
        if record.get("source_license") != "CC-BY-NC-SA-3.0-noncommercial":
            raise ValueError(f"{context}: Virtual KITTI 2 license is not frozen")
        if (
            str(record.get("eval_protocol_sha256", "")).lower()
            != VKITTI2_EVAL_PROTOCOL_SHA256
        ):
            raise ValueError(
                f"{context}: Virtual KITTI 2 evaluation protocol is not frozen"
            )
        for field in (
            "archive_checksum_file_sha256",
            "source_split_list_sha256",
            "rgb_sha256",
            "depth_sha256",
        ):
            if not _valid_sha256(record.get(field)):
                raise ValueError(f"{context}: Virtual KITTI 2 {field} is invalid")
        annotation_components = record.get("annotation_components")
        expected_component_fields = {
            "class_segmentation_sha256",
            "colors_sha256",
            "instance_segmentation_sha256",
        }
        if (
            not isinstance(annotation_components, Mapping)
            or set(annotation_components) != expected_component_fields
            or any(
                not _valid_sha256(annotation_components[field])
                for field in expected_component_fields
            )
        ):
            raise ValueError(
                f"{context}: Virtual KITTI 2 annotation components are invalid"
            )
        encoded_components = json.dumps(
            dict(annotation_components),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if (
            str(record.get("annotation_sha256", "")).lower()
            != hashlib.sha256(encoded_components).hexdigest()
        ):
            raise ValueError(
                f"{context}: Virtual KITTI 2 annotation SHA256 is inconsistent"
            )
        return str(record["source_split_list_sha256"]).lower()

    raise ValueError(f"{context}: dataset {dataset!r} has no trusted source contract")


def _resolve_lineage_artifact(audit_path: Path, value: object) -> Path:
    raw_path = Path(str(value).strip())
    if not str(value).strip() or raw_path.is_absolute():
        raise ValueError("lineage artifact paths must be nonempty and relative")
    resolved = (audit_path.resolve().parent / raw_path).resolve(strict=True)
    try:
        resolved.relative_to(REPOSITORY_ROOT)
    except ValueError as error:
        raise ValueError(
            "lineage artifacts must remain inside the repository"
        ) from error
    if not resolved.is_file():
        raise ValueError("lineage artifact must resolve to a regular file")
    return resolved


def _read_manifest_identity(
    path: Path,
) -> tuple[
    set[tuple[str, str, str, str]],
    int,
    dict[str, dict[str, int]],
]:
    records: set[tuple[str, str, str, str]] = set()
    image_keys: set[tuple[str, str]] = set()
    split_counts: dict[str, dict[str, int]] = {}
    record_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, Mapping):
                raise ValueError(f"{path.name}:{line_number} is not a JSON object")
            dataset = str(raw.get("dataset", "")).strip()
            image_id = str(raw.get("image_id", "")).strip()
            rgb_sha256 = str(raw.get("rgb_sha256", "")).strip().lower()
            cluster_id = str(raw.get("cluster_id", "")).strip().lower()
            split = str(raw.get("split", "")).strip()
            selection_hash = str(raw.get("selection_hash", "")).strip().lower()
            if not dataset or not image_id:
                raise ValueError(f"{path.name}:{line_number} lacks dataset or image_id")
            if split not in SPLIT_ORDER:
                raise ValueError(f"{path.name}:{line_number} has invalid split")
            if (
                not _valid_sha256(rgb_sha256)
                or not _valid_sha256(cluster_id)
                or not _valid_sha256(selection_hash)
            ):
                raise ValueError(
                    f"{path.name}:{line_number} has invalid identity SHA256"
                )
            image_key = (dataset, image_id)
            if image_key in image_keys:
                raise ValueError(f"{path.name} contains a duplicate image key")
            image_keys.add(image_key)
            semantic_record = {
                str(key): value
                for key, value in raw.items()
                if key != "selection_stage"
            }
            semantic_sha256 = hashlib.sha256(
                json.dumps(
                    semantic_record,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            identity = (dataset, image_id, split, semantic_sha256)
            records.add(identity)
            counts = split_counts.setdefault(
                dataset,
                {name: 0 for name in SPLIT_ORDER},
            )
            counts[split] += 1
            record_count += 1
    if not records:
        raise ValueError("lineage manifest must not be empty")
    return records, record_count, split_counts


def verify_formal_power_failure(
    path: Path,
    *,
    parent_manifest_sha256: str,
    parent_split_audit_sha256: str | None = None,
) -> None:
    """Verify that an expansion trigger is a complete canonical formal failure."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("trigger power audit must be a JSON object")
    input_payload = payload.get("input")
    split_audit_payload = payload.get("split_audit")
    grid_payload = payload.get("grid")
    simulation_payload = payload.get("simulation")
    formal_conditions = (
        simulation_payload.get("formal_conditions")
        if isinstance(simulation_payload, Mapping)
        else None
    )
    datasets = payload.get("datasets")
    dataset_decision = payload.get("dataset_decision")
    allowed_dataset_sets = {
        frozenset({"KITTI", "NYUv2"}),
        frozenset({"NYUv2", "Virtual KITTI 2"}),
    }
    selected_datasets = (
        frozenset(str(value) for value in dataset_decision.get("selected_datasets", []))
        if isinstance(dataset_decision, Mapping)
        else frozenset()
    )
    expected_decision_name = (
        "GO_LOCAL_CLAIMS_NYUV2_KITTI"
        if selected_datasets == frozenset({"KITTI", "NYUv2"})
        else "GO_LOCAL_CLAIMS_NYUV2_VKITTI2"
    )
    decision_source = (
        str(dataset_decision.get("source", ""))
        if isinstance(dataset_decision, Mapping)
        else ""
    )
    valid_decision_link = (
        isinstance(dataset_decision, Mapping)
        and selected_datasets in allowed_dataset_sets
        and dataset_decision.get("decision") == expected_decision_name
        and (
            (
                decision_source == "preregistered_primary_default"
                and selected_datasets == frozenset({"KITTI", "NYUv2"})
            )
            or (
                decision_source == "frozen_coverage_audit"
                and _valid_sha256(dataset_decision.get("coverage_decision_sha256"))
                and str(dataset_decision.get("coverage_manifest_sha256", "")).lower()
                == parent_manifest_sha256
            )
        )
    )
    expected_implementation_sha256 = file_sha256(
        Path(__file__).with_name("power_analysis.py")
    )
    expected_formal_conditions = {
        "exact_simulations_met",
        "preregistered_grid_matched",
        "split_is_internal_test",
        "seed_is_preregistered",
        "required_power_datasets_present",
        "analysis_datasets_exact",
        "split_audit_linked",
        "minimum_internal_test_scenes_met",
        "minimum_dev_scenes_met",
    }
    if (
        payload.get("schema_version") != "covol-power-analysis-v1"
        or payload.get("status") != "FAIL"
        or payload.get("run_mode") != "FORMAL"
        or not isinstance(input_payload, Mapping)
        or str(input_payload.get("manifest_sha256", "")).lower()
        != parent_manifest_sha256
        or input_payload.get("split") != "internal_test"
        or input_payload.get("selection_stage") != PILOT_SELECTION_STAGE
        or not valid_decision_link
        or not selected_datasets <= set(input_payload.get("datasets", []))
        or set(input_payload.get("power_analysis_datasets", [])) != selected_datasets
        or not isinstance(split_audit_payload, Mapping)
        or str(split_audit_payload.get("manifest_sha256", "")).lower()
        != parent_manifest_sha256
        or split_audit_payload.get("selection_stage") != PILOT_SELECTION_STAGE
        or not selected_datasets <= set(split_audit_payload.get("datasets", []))
        or payload.get("authorization_scope") != STEP003_AUTHORIZATION_SCOPE
        or payload.get("implementation_sha256") != expected_implementation_sha256
        or not isinstance(grid_payload, Mapping)
        or grid_payload.get("matches_preregistered_grid") is not True
        or grid_payload.get("grid_sha256") != POWER_GRID_CANONICAL_SHA256
        or grid_payload.get("preregistered_grid_sha256") != POWER_GRID_CANONICAL_SHA256
        or grid_payload.get("scenario_count") != 20
        or grid_payload.get("primary_scenario_id") != "prev05_icc30_hv20"
        or grid_payload.get("formal_simulations") != 5_000
        or grid_payload.get("minimum_power") != 0.8
        or not isinstance(simulation_payload, Mapping)
        or simulation_payload.get("formal_run") is not True
        or simulation_payload.get("simulations") != 5_000
        or simulation_payload.get("seed") != PILOT_SEED
        or not isinstance(formal_conditions, Mapping)
        or set(formal_conditions) != expected_formal_conditions
        or any(value is not True for value in formal_conditions.values())
        or not isinstance(datasets, list)
        or len(datasets) != 2
        or any(not isinstance(dataset, Mapping) for dataset in datasets)
        or {
            str(dataset.get("dataset", ""))
            for dataset in datasets
            if isinstance(dataset, Mapping)
        }
        != selected_datasets
    ):
        raise ValueError(
            "expansion trigger must be a canonical-grid FORMAL FAIL bound to "
            "the parent manifest"
        )
    if (
        parent_split_audit_sha256 is not None
        and str(split_audit_payload.get("split_audit_sha256", "")).lower()
        != parent_split_audit_sha256
    ):
        raise ValueError("expansion trigger split-audit SHA256 mismatch")
    failed_datasets = 0
    for dataset in datasets:
        assert isinstance(dataset, Mapping)
        scenarios = dataset.get("scenarios")
        if not isinstance(scenarios, list) or len(scenarios) != 20:
            raise ValueError("formal power failure must contain all 20 scenarios")
        primary_rows = [
            scenario
            for scenario in scenarios
            if isinstance(scenario, Mapping)
            and scenario.get("scenario_id") == "prev05_icc30_hv20"
            and scenario.get("is_primary") is True
        ]
        if len(primary_rows) != 1:
            raise ValueError("formal power failure must contain one primary scenario")
        primary_pass = primary_rows[0].get("scenario_power_threshold_pass")
        if not isinstance(primary_pass, bool):
            raise ValueError("primary power decision must be a boolean")
        if dataset.get("primary_power_threshold_pass") is not primary_pass:
            raise ValueError("dataset and primary-scenario power decisions disagree")
        expected_formal_pass = primary_pass
        if dataset.get("formal_gate_pass") is not expected_formal_pass:
            raise ValueError("dataset formal power decision is inconsistent")
        if not primary_pass:
            failed_datasets += 1
    if failed_datasets == 0:
        raise ValueError("formal expansion trigger does not contain a failed dataset")


def verify_split_audit(
    path: Path,
    *,
    manifest_sha256: str,
    manifest_record_count: int,
    manifest_split_counts: Mapping[str, Mapping[str, int]],
    required_datasets: frozenset[str],
    manifest_path: Path | None = None,
) -> SplitAuditLink:
    """Verify PASS status, leakage zeros, counts, and manifest hash linkage."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("split audit must be a JSON object")
    if payload.get("status") != PREFREEZE_STATUS:
        raise ValueError(f"split audit status must be {PREFREEZE_STATUS}")
    if payload.get("audit_mode") != "training_pilot":
        raise ValueError("Step-003 gates require audit_mode=training_pilot")
    if payload.get("authorization_scope") != STEP003_AUTHORIZATION_SCOPE:
        raise ValueError("split audit authorization_scope must remain Step-003-only")
    if payload.get("seed") != PILOT_SEED:
        raise ValueError(f"training-pilot seed must equal {PILOT_SEED}")
    selection_stage = str(payload.get("selection_stage", "")).strip()
    if selection_stage not in {PILOT_SELECTION_STAGE, EXPANDED_SELECTION_STAGE}:
        raise ValueError("selection_stage must be PILOT_V1 or EXPANDED_FOR_POWER")
    if not _valid_sha256(payload.get("config_sha256")):
        raise ValueError("split audit config_sha256 must be a valid SHA256")
    expansion_fields = (
        "parent_manifest_sha256",
        "parent_split_audit_sha256",
        "trigger_power_audit_sha256",
    )
    lineage_artifacts = payload.get("lineage_artifacts")
    if selection_stage == EXPANDED_SELECTION_STAGE:
        if any(not _valid_sha256(payload.get(field)) for field in expansion_fields):
            raise ValueError(
                "expanded power selection requires parent manifest/audit and "
                "trigger power-audit SHA256 values"
            )
        if not isinstance(lineage_artifacts, Mapping) or set(lineage_artifacts) != {
            "parent_manifest",
            "parent_split_audit",
            "trigger_power_audit",
        }:
            raise ValueError(
                "expanded power selection requires exactly three lineage artifacts"
            )
    elif any(field in payload for field in expansion_fields) or lineage_artifacts:
        raise ValueError("PILOT_V1 audit must not contain expansion lineage fields")
    official_test_audit = payload.get("official_test_audit")
    if (
        not isinstance(official_test_audit, Mapping)
        or official_test_audit.get("status") != "DEFERRED_FROZEN"
    ):
        raise ValueError("official test audit must be explicitly DEFERRED_FROZEN")
    if str(payload.get("manifest_sha256", "")).lower() != manifest_sha256:
        raise ValueError("split audit manifest_sha256 does not match input manifest")
    if payload.get("record_count") != manifest_record_count:
        raise ValueError("split audit record_count does not match input manifest")
    raw_datasets = payload.get("datasets")
    if not isinstance(raw_datasets, list) or not raw_datasets:
        raise ValueError("split audit must contain dataset audits")

    audited_datasets: dict[str, Mapping[str, Any]] = {}
    for index, raw_dataset in enumerate(raw_datasets):
        if not isinstance(raw_dataset, Mapping):
            raise ValueError(f"split audit dataset {index} must be a JSON object")
        dataset = str(raw_dataset.get("dataset", "")).strip()
        if not dataset or dataset in audited_datasets:
            raise ValueError("split audit dataset names must be nonempty and unique")
        if raw_dataset.get("status") != PREFREEZE_STATUS:
            raise ValueError(
                f"split audit dataset {dataset!r} must be {PREFREEZE_STATUS}"
            )
        if raw_dataset.get("selection_stage") != selection_stage:
            raise ValueError(
                f"split audit dataset {dataset!r} has wrong selection_stage"
            )
        if "official_test_overlap" in raw_dataset:
            raise ValueError(
                "training-pilot audit must not fabricate official-test overlap zeros"
            )
        if raw_dataset.get("seed") != PILOT_SEED:
            raise ValueError(f"split audit dataset {dataset!r} has wrong seed")
        input_payload = raw_dataset.get("input")
        if not isinstance(input_payload, Mapping) or any(
            not _valid_sha256(input_payload.get(field))
            for field in ("training_manifest_sha256", "split_source_sha256")
        ):
            raise ValueError(
                f"split audit dataset {dataset!r} lacks source/split SHA256"
            )
        if any("test" in str(key).casefold() for key in input_payload):
            raise ValueError("training-pilot audit must not contain test input fields")
        internal_overlap = raw_dataset.get("internal_overlap")
        if not isinstance(internal_overlap, Mapping) or any(
            internal_overlap.get(field) != 0
            for field in (
                "image_count",
                "cluster_count",
                "scene_count",
                "sequence_count",
                "rgb_sha256_count",
            )
        ):
            raise ValueError(
                f"split audit dataset {dataset!r} lacks zero internal overlap"
            )
        audited_datasets[dataset] = raw_dataset

    manifest_datasets = set(manifest_split_counts)
    if set(audited_datasets) != manifest_datasets:
        raise ValueError("split audit datasets do not exactly match input manifest")
    missing = sorted(required_datasets - manifest_datasets)
    if missing:
        raise ValueError(f"input manifest lacks required datasets: {missing}")
    for dataset, counts in manifest_split_counts.items():
        expected_counts = {split: int(counts.get(split, 0)) for split in SPLIT_ORDER}
        valid_counts = expected_counts == PILOT_SPLIT_COUNTS
        if selection_stage == EXPANDED_SELECTION_STAGE:
            valid_counts = (
                expected_counts["train"] == PILOT_SPLIT_COUNTS["train"]
                and expected_counts["dev"] == PILOT_SPLIT_COUNTS["dev"]
                and expected_counts["internal_test"]
                >= PILOT_SPLIT_COUNTS["internal_test"]
            )
        if not valid_counts:
            raise ValueError(
                f"training-pilot counts for {dataset!r} violate "
                f"{selection_stage} constraints"
            )
        audit_counts = audited_datasets[dataset].get("selected_counts")
        if audit_counts != expected_counts:
            raise ValueError(
                f"split audit selected_counts mismatch for dataset {dataset!r}"
            )
    if selection_stage == EXPANDED_SELECTION_STAGE:
        expansion_flags: dict[str, bool] = {}
        for dataset, dataset_audit in audited_datasets.items():
            triggered = dataset_audit.get("expansion_triggered")
            if not isinstance(triggered, bool):
                raise ValueError(
                    f"expanded dataset {dataset!r} requires expansion_triggered"
                )
            expected_trigger = (
                int(manifest_split_counts[dataset].get("internal_test", 0))
                > PILOT_SPLIT_COUNTS["internal_test"]
            )
            if triggered != expected_trigger:
                raise ValueError(
                    f"expanded dataset {dataset!r} has inconsistent trigger flag"
                )
            expansion_flags[dataset] = triggered
        if not any(expansion_flags.values()):
            raise ValueError("EXPANDED_FOR_POWER must expand at least one dataset")
        if manifest_path is None:
            raise ValueError("expanded split audit requires manifest_path verification")
        if file_sha256(manifest_path) != manifest_sha256:
            raise ValueError("expanded manifest_path does not match manifest_sha256")
        assert isinstance(lineage_artifacts, Mapping)
        parent_manifest_path = _resolve_lineage_artifact(
            path,
            lineage_artifacts["parent_manifest"],
        )
        parent_split_audit_path = _resolve_lineage_artifact(
            path,
            lineage_artifacts["parent_split_audit"],
        )
        trigger_power_audit_path = _resolve_lineage_artifact(
            path,
            lineage_artifacts["trigger_power_audit"],
        )
        parent_manifest_sha256 = str(payload["parent_manifest_sha256"]).lower()
        if file_sha256(parent_manifest_path) != parent_manifest_sha256:
            raise ValueError("parent manifest artifact SHA256 mismatch")
        if (
            file_sha256(parent_split_audit_path)
            != str(payload["parent_split_audit_sha256"]).lower()
        ):
            raise ValueError("parent split-audit artifact SHA256 mismatch")
        if (
            file_sha256(trigger_power_audit_path)
            != str(payload["trigger_power_audit_sha256"]).lower()
        ):
            raise ValueError("trigger power-audit artifact SHA256 mismatch")
        parent_records, parent_count, parent_counts = _read_manifest_identity(
            parent_manifest_path
        )
        current_records, current_count, current_counts = _read_manifest_identity(
            manifest_path
        )
        if current_count != manifest_record_count or current_counts != {
            dataset: {split: int(counts.get(split, 0)) for split in SPLIT_ORDER}
            for dataset, counts in manifest_split_counts.items()
        }:
            raise ValueError("expanded manifest identity/count audit mismatch")
        parent_link = verify_split_audit(
            parent_split_audit_path,
            manifest_sha256=parent_manifest_sha256,
            manifest_record_count=parent_count,
            manifest_split_counts=parent_counts,
            required_datasets=required_datasets,
            manifest_path=parent_manifest_path,
        )
        if parent_link.selection_stage != PILOT_SELECTION_STAGE:
            raise ValueError("expanded selection parent must be PILOT_V1")
        parent_audit_payload = json.loads(
            parent_split_audit_path.read_text(encoding="utf-8")
        )
        parent_dataset_audits = {
            str(value.get("dataset", "")): value
            for value in parent_audit_payload["datasets"]
            if isinstance(value, Mapping)
        }
        if set(parent_dataset_audits) != set(audited_datasets):
            raise ValueError("expanded audit datasets must match parent datasets")
        for dataset, current_dataset_audit in audited_datasets.items():
            parent_input = parent_dataset_audits[dataset].get("input")
            current_input = current_dataset_audit.get("input")
            if not isinstance(parent_input, Mapping) or not isinstance(
                current_input,
                Mapping,
            ):
                raise ValueError("expanded dataset provenance must be JSON objects")
            for field in ("training_manifest_sha256", "split_source_sha256"):
                if parent_input.get(field) != current_input.get(field):
                    raise ValueError(
                        f"expanded dataset {dataset!r} changed source provenance"
                    )
        verify_formal_power_failure(
            trigger_power_audit_path,
            parent_manifest_sha256=parent_manifest_sha256,
            parent_split_audit_sha256=str(payload["parent_split_audit_sha256"]).lower(),
        )
        if not parent_records < current_records:
            raise ValueError("expanded manifest must be a strict superset of parent")
        additions = current_records - parent_records
        if any(record[2] != "internal_test" for record in additions):
            raise ValueError("expanded manifest may only append internal_test records")
        parent_train_dev = {
            record for record in parent_records if record[2] in {"train", "dev"}
        }
        current_train_dev = {
            record for record in current_records if record[2] in {"train", "dev"}
        }
        if parent_train_dev != current_train_dev:
            raise ValueError("expanded manifest must preserve parent train/dev exactly")
    return SplitAuditLink(
        split_audit_sha256=file_sha256(path),
        manifest_sha256=manifest_sha256,
        record_count=manifest_record_count,
        datasets=tuple(sorted(manifest_datasets)),
        audit_mode="training_pilot",
        selection_stage=selection_stage,
        authorization_scope=str(payload["authorization_scope"]),
    )


def split_audit_link_payload(link: SplitAuditLink) -> dict[str, Any]:
    """Return a JSON-serializable verified split-audit link."""

    return asdict(link)
