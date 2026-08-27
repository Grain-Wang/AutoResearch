from __future__ import annotations

from paper1.experiments.covol.analyze_sensitivity_postmortem import (
    ANALYSIS_STATUS,
    analyze_sensitivity_postmortem,
)


def _rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    effects = {
        "semantic_preserving": 0.01,
        "target_deletion": 0.02,
        "local_entity_conflict": 0.04,
        "depth_relation_conflict": 0.0,
    }
    for cluster_index in range(3):
        for variant_id in range(3):
            for family, effect in effects.items():
                rows.append(
                    {
                        "image_id": f"image-{cluster_index}",
                        "cluster_id": f"cluster-{cluster_index}",
                        "error_type": family,
                        "variant_id": str(variant_id),
                        "region_abs_rel_degradation": str(
                            effect + cluster_index * 0.001
                        ),
                        "region_clean_abs_rel": "0.2",
                        "full_abs_rel_degradation": str(effect / 10),
                        "full_valid_pixel_count": "1000",
                        "region_valid_pixel_count": "100",
                    }
                )
    return rows


def test_postmortem_reports_matched_difference_and_irreversible_stop() -> None:
    differences, practical = analyze_sensitivity_postmortem(
        _rows(), replicates=200, seed=17
    )

    assert differences["analysis_status"] == ANALYSIS_STATUS
    assert differences["cannot_reverse_preregistered_stop"] is True
    local = next(
        row
        for row in differences["rows"]
        if row["analysis_level"] == "family"
        and row["family"] == "local_entity_conflict"
    )
    assert abs(local["point"] - 0.03) < 1e-12
    assert "holm_adjusted_p_value" in local
    mass = next(
        row
        for row in practical["rows"]
        if row["family"] == "semantic_preserving"
        and row["metric"] == "target_pixel_mass"
    )
    assert mass["median"] == 0.1
    assert "maximum_leave_one_cluster_out_influence" in mass
