from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from paper1.experiments.covol.audit_second_dataset_candidates import (
    audit_candidates,
    write_candidate_audit_csv,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _config(tmp_path: Path) -> dict[str, object]:
    candidates = []
    for order, dataset in enumerate(
        ("Cityscapes", "ScanNet_v2", "Matterport3D"), start=1
    ):
        candidates.append(
            {
                "order": order,
                "dataset": dataset,
                "source_revision_lock": "sha256:locked",
                "license_contract": "test-only",
                "dry_run_manifest": None,
            }
        )
    return {
        "frozen_before_method_results": True,
        "dry_run_sample_size": 50,
        "projected_full_pilot_size": 500,
        "minimum_projected_eligible_images": 150,
        "minimum_projected_eligible_pairs": 300,
        "minimum_independent_clusters": 20,
        "minimum_valid_depth_mask_pixels": 32,
        "selection_rule": "FIRST_PASS_IN_FROZEN_ORDER",
        "candidates": candidates,
    }


def _write_manifest(tmp_path: Path, dataset: str, *, eligible: bool) -> Path:
    source = tmp_path / f"{dataset}.bin"
    source.write_bytes(dataset.encode())
    rows = []
    for index in range(50):
        row = {
            "dataset": dataset,
            "image_id": f"image-{index}",
            "cluster_id": f"cluster-{index}",
            "selection_rank": index,
            "rgb_path": source.name,
            "rgb_sha256": _sha256(source),
            "depth_path": source.name,
            "depth_sha256": _sha256(source),
            "mask_path": source.name,
            "mask_sha256": _sha256(source),
            "rgb_available": True,
            "metric_depth_available": eligible,
            "local_mask_available": eligible,
            "rgb_frame_key": f"frame-{index}",
            "depth_frame_key": f"frame-{index}",
            "mask_frame_key": f"frame-{index}",
            "license_pass": True,
            "valid_depth_mask_pixels": 32 if eligible else 0,
            "eligible_pair_count": 1 if eligible else 0,
        }
        rows.append(json.dumps(row, sort_keys=True))
    manifest = tmp_path / f"{dataset}.jsonl"
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return manifest


def test_without_agreed_sources_is_blocked_not_scientific_fail(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")

    result = audit_candidates(_config(tmp_path), config_path=config_path)

    assert result["status"] == "BLOCKED_SOURCE_ACCESS"
    assert result["selected_candidate"] is None
    assert all(row["status"] == "PENDING_SOURCE_ACCESS" for row in result["candidates"])

    csv_path = tmp_path / "audit.csv"
    write_candidate_audit_csv(csv_path, result)
    csv_text = csv_path.read_text(encoding="utf-8")
    assert csv_text.count("PENDING_SOURCE_ACCESS") == 3
    assert "Cityscapes" in csv_text


def test_selects_first_pass_in_frozen_order_and_hashes_real_files(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    manifests = [
        _write_manifest(tmp_path, "Cityscapes", eligible=False),
        _write_manifest(tmp_path, "ScanNet_v2", eligible=True),
        _write_manifest(tmp_path, "Matterport3D", eligible=True),
    ]
    for candidate, manifest in zip(config["candidates"], manifests, strict=True):
        candidate["dry_run_manifest"] = manifest.name
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = audit_candidates(config, config_path=config_path)

    assert result["status"] == "PASS_DRY_RUN"
    assert result["selected_candidate"] == "ScanNet_v2"
    assert result["candidates"][0]["status"] == "FAIL_COVERAGE"
    assert result["candidates"][1]["manifest_sha256"] == _sha256(manifests[1])
    assert "method_result" not in result


def test_tampered_modality_file_is_rejected(tmp_path: Path) -> None:
    config = _config(tmp_path)
    manifest = _write_manifest(tmp_path, "Cityscapes", eligible=True)
    config["candidates"][0]["dry_run_manifest"] = manifest.name
    source = tmp_path / "Cityscapes.bin"
    source.write_bytes(b"tampered")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch"):
        audit_candidates(config, config_path=config_path)
