from __future__ import annotations

from copy import deepcopy

import pytest
from paper1.experiments.covol.build_interventions import (
    build_diagnostic_interventions,
    validate_diagnostic_interventions,
    write_diagnostic_audit,
)


def _source_rows() -> list[dict[str, object]]:
    return [
        {
            "dataset": "NYUv2",
            "image_id": f"image-{index}",
            "scene_id": f"scene-{index}",
            "sequence_id": f"sequence-{index}",
            "cluster_id": f"{index:064x}",
            "rgb_sha256": f"{index + 1000:064x}",
            "official_split": "train",
            "split": "train",
            "entities": [
                {
                    "entity_id": f"entity-near-{index}",
                    "class_name": "chair",
                    "reliable_mask": True,
                    "eval_mask_area_pixels": 64,
                    "eval_valid_depth_count": 64,
                    "eval_median_depth": 1.0,
                },
                {
                    "entity_id": f"entity-far-{index}",
                    "class_name": "table",
                    "reliable_mask": True,
                    "eval_mask_area_pixels": 64,
                    "eval_valid_depth_count": 64,
                    "eval_median_depth": 2.0,
                },
            ],
        }
        for index in range(105)
    ]


def test_builds_exact_train_only_100_by_four_by_three_diagnostic() -> None:
    first = build_diagnostic_interventions(_source_rows())
    second = build_diagnostic_interventions(_source_rows())
    local, null, global_rows = first

    assert first == second
    assert len(local) == 1_200
    assert len(null) == 100
    assert len(global_rows) == 100
    assert {row["source_split"] for row in local} == {"train"}
    assert {row["diagnostic_split"] for row in local} == {
        "diagnostic_only_never_formal"
    }
    assert all(row["machine_check"]["passed"] for row in local)


def test_rejects_machine_check_failure_and_non_train_pool() -> None:
    local, _, _ = build_diagnostic_interventions(_source_rows())
    corrupted = deepcopy(local)
    corrupted[0]["machine_check"]["passed"] = False
    with pytest.raises(ValueError, match="machine check"):
        validate_diagnostic_interventions(corrupted)

    source = _source_rows()
    for row in source[:6]:
        row["split"] = "dev"
    with pytest.raises(ValueError, match="fewer than 100"):
        build_diagnostic_interventions(source[:100])


def test_audit_keeps_construction_separate_from_scientific_effect(tmp_path) -> None:
    source_path = tmp_path / "source.jsonl"
    source_path.write_text("{}\n", encoding="utf-8")
    local, null, global_rows = build_diagnostic_interventions(_source_rows())
    output_paths = [tmp_path / f"output-{index}.jsonl" for index in range(3)]
    for path, rows in zip(output_paths, (local, null, global_rows), strict=True):
        path.write_text(
            "\n".join(str(index) for index, _ in enumerate(rows)) + "\n",
            encoding="utf-8",
        )

    audit = write_diagnostic_audit(
        local,
        null,
        global_rows,
        source_manifest_path=source_path,
        local_output_path=output_paths[0],
        null_output_path=output_paths[1],
        global_output_path=output_paths[2],
        json_output_path=tmp_path / "audit.json",
        csv_output_path=tmp_path / "audit.csv",
    )

    assert audit["local_row_count"] == 1_200
    assert audit["machine_check_pass_rate"] == 1.0
    assert audit["independent_precision_status"] == "PENDING"
    assert audit["scientific_evidence"] == "CORPUS_CONSTRUCTION_NOT_MODEL_EFFECT"
