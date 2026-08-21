from __future__ import annotations

import hashlib
import json
from pathlib import Path

from paper1.experiments.covol.plan_kitti_training_subset import (
    plan_kitti_training_subset,
)


def test_plans_fixed_counts_and_twenty_internal_test_drives(tmp_path: Path) -> None:
    split_path = tmp_path / "canonical-train.txt"
    lines: list[str] = []
    for drive_index in range(33):
        drive = f"2011_09_26_drive_{drive_index:04d}_sync"
        for frame_index in range(70):
            rgb = f"2011_09_26/{drive}/image_02/data/{frame_index:010d}.png"
            lines.append(f"{rgb} depth/{drive}/{frame_index:010d}.png 721.5")
    split_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    selected_split = tmp_path / "selected.txt"
    download_plan = tmp_path / "plan.jsonl"
    audit_path = tmp_path / "audit.json"

    audit = plan_kitti_training_subset(
        split_path,
        selected_split_path=selected_split,
        download_plan_path=download_plan,
        audit_path=audit_path,
        repository_id="example/kitti",
        repository_revision="a" * 40,
    )

    records = [json.loads(line) for line in download_plan.read_text().splitlines()]
    assert len(records) == 500
    assert audit["selection"]["split_counts"] == {
        "train": 300,
        "dev": 100,
        "internal_test": 100,
    }
    assert audit["selection"]["cluster_counts"] == {
        "train": 5,
        "dev": 5,
        "internal_test": 20,
    }
    assert (
        audit["input"]["canonical_training_split_sha256"]
        == hashlib.sha256(split_path.read_bytes()).hexdigest()
    )
    assert {
        record["repository_path"].split("/", maxsplit=1)[0] for record in records
    } == {"raw_data"}
