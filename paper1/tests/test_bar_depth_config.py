from __future__ import annotations

import json
from pathlib import Path


def test_v2_only_repairs_metric_alignment() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    config_root = repository_root / "paper1/configs/bar_depth"
    v1 = json.loads((config_root / "oracle_canary_v1.json").read_text())
    v2 = json.loads((config_root / "oracle_canary_v2.json").read_text())

    v1["experiment_id"] = v2["experiment_id"]
    v1["metric"]["alignment_variant"] = "positive_median_scale"
    v1["metric"]["clip_prediction_to_evaluation_range"] = True
    assert v1 == v2
