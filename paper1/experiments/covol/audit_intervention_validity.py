"""Audit diagnostic predicates, text artifacts, and caption surface form."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

try:
    from paper1.experiments.covol.audit_diagnostic_interventions import (
        FAMILIES,
        audit_diagnostic_predicates,
        independently_verify_predicate,
        select_predicate_audit_rows,
    )
except ModuleNotFoundError:  # Direct script consumers in this directory.
    from audit_diagnostic_interventions import (  # type: ignore
        FAMILIES,
        audit_diagnostic_predicates,
        independently_verify_predicate,
        select_predicate_audit_rows,
    )

MAX_TEXT_ARTIFACT_MACRO_F1 = 0.60
MIN_SURFACE_FORM_PASS_RATE = 0.99
_TOKEN_PATTERN = re.compile(r"[a-z]+(?:-[a-z]+)?")
_VALID_SENTENCE_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9 ,'-]+\.$")


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


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(_TOKEN_PATTERN.findall(text.casefold()))


def _train_multinomial_nb(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[Counter[str], dict[str, Counter[str]], Counter[str], set[str]]:
    label_documents: Counter[str] = Counter()
    token_counts = {family: Counter() for family in FAMILIES}
    label_token_totals: Counter[str] = Counter()
    vocabulary: set[str] = set()
    for row in rows:
        label = str(row.get("error_type", ""))
        if label not in token_counts:
            raise ValueError(f"unknown intervention family: {label!r}")
        tokens = _tokens(str(row.get("intervention", "")))
        if not tokens:
            raise ValueError("text artifact row has an empty intervention")
        label_documents[label] += 1
        token_counts[label].update(tokens)
        label_token_totals[label] += len(tokens)
        vocabulary.update(tokens)
    if set(label_documents) != set(FAMILIES):
        raise ValueError("text artifact training fold must contain every family")
    return label_documents, token_counts, label_token_totals, vocabulary


def _predict_multinomial_nb(
    model: tuple[Counter[str], dict[str, Counter[str]], Counter[str], set[str]],
    text: str,
) -> str:
    label_documents, token_counts, label_token_totals, vocabulary = model
    document_count = sum(label_documents.values())
    text_counts = Counter(_tokens(text))
    scores: dict[str, float] = {}
    for family in FAMILIES:
        score = math.log(label_documents[family] / document_count)
        denominator = label_token_totals[family] + len(vocabulary)
        for token, count in text_counts.items():
            score += count * math.log((token_counts[family][token] + 1) / denominator)
        scores[family] = score
    return max(FAMILIES, key=lambda family: (scores[family], family))


def _classification_metrics(
    pairs: Sequence[tuple[str, str]],
) -> dict[str, Any]:
    confusion = Counter(pairs)
    per_family: dict[str, dict[str, float | int]] = {}
    f1_values = []
    for family in FAMILIES:
        true_positive = confusion[(family, family)]
        false_positive = sum(
            confusion[(other, family)] for other in FAMILIES if other != family
        )
        false_negative = sum(
            confusion[(family, other)] for other in FAMILIES if other != family
        )
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else 0.0
        )
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        f1_values.append(f1)
        per_family[family] = {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    return {
        "macro_f1": sum(f1_values) / len(f1_values),
        "accuracy": sum(actual == predicted for actual, predicted in pairs)
        / len(pairs),
        "per_family": per_family,
        "confusion": {
            f"{actual}->{predicted}": confusion[(actual, predicted)]
            for actual in FAMILIES
            for predicted in FAMILIES
        },
    }


def audit_text_artifacts(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Run a raw-caption unigram classifier with held-out template variants."""

    variants = sorted({int(row.get("variant_id", -1)) for row in rows})
    if variants != [0, 1, 2]:
        raise ValueError("text artifact audit requires template variants 0, 1, and 2")
    all_pairs: list[tuple[str, str]] = []
    folds = []
    for held_out_variant in variants:
        training = [
            row for row in rows if int(row.get("variant_id", -1)) != held_out_variant
        ]
        testing = [
            row for row in rows if int(row.get("variant_id", -1)) == held_out_variant
        ]
        model = _train_multinomial_nb(training)
        pairs = [
            (
                str(row["error_type"]),
                _predict_multinomial_nb(model, str(row["intervention"])),
            )
            for row in testing
        ]
        metrics = _classification_metrics(pairs)
        folds.append(
            {
                "held_out_variant": held_out_variant,
                "training_row_count": len(training),
                "test_row_count": len(testing),
                **metrics,
            }
        )
        all_pairs.extend(pairs)
    aggregate = _classification_metrics(all_pairs)
    macro_f1 = float(aggregate["macro_f1"])
    return {
        "schema_version": "covol-text-artifact-control-v1",
        "status": (
            "PASS_TEXT_ARTIFACT_CONTROL"
            if macro_f1 <= MAX_TEXT_ARTIFACT_MACRO_F1
            else "STOP_TEXT_TEMPLATE_ARTIFACT"
        ),
        "model": "MULTINOMIAL_NB_WORD_UNIGRAM_LAPLACE_1",
        "input_features": "RAW_INTERVENTION_TEXT_ONLY",
        "split": "LEAVE_ONE_VARIANT_TEMPLATE_PER_FAMILY_OUT",
        "row_count": len(rows),
        "folds": folds,
        "aggregate": aggregate,
        "maximum_macro_f1": MAX_TEXT_ARTIFACT_MACRO_F1,
        "scientific_evidence": (
            "TEMPLATE_ARTIFACT_CONTROL_NOT_CAPTION_NATURALNESS_OR_MODEL_EFFECT"
        ),
    }


def _surface_form_passes(text: str) -> bool:
    tokens = _tokens(text)
    return (
        bool(_VALID_SENTENCE_PATTERN.fullmatch(text))
        and 4 <= len(tokens) <= 20
        and "  " not in text
        and "{" not in text
        and "}" not in text
        and all(left != right for left, right in zip(tokens, tokens[1:], strict=False))
        and any(token in {"shows", "contains", "is"} for token in tokens)
    )


def audit_caption_surface_form(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Measure deterministic caption-form checks without claiming human naturalness."""

    captions = [str(row.get("intervention", "")) for row in rows]
    passed = [_surface_form_passes(caption) for caption in captions]
    pass_count = sum(passed)
    normalized = {" ".join(_tokens(caption)) for caption in captions}
    pass_rate = pass_count / len(captions)
    return {
        "status": (
            "PASS_AUTOMATED_SURFACE_FORM_HUMAN_NATURALNESS_UNASSESSED"
            if pass_rate >= MIN_SURFACE_FORM_PASS_RATE
            else "STOP_AUTOMATED_SURFACE_FORM"
        ),
        "row_count": len(captions),
        "pass_count": pass_count,
        "pass_rate": pass_rate,
        "minimum_pass_rate": MIN_SURFACE_FORM_PASS_RATE,
        "unique_normalized_caption_count": len(normalized),
        "unique_normalized_caption_rate": len(normalized) / len(captions),
        "human_naturalness_status": "NOT_ASSESSED",
    }


def audit_intervention_validity(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Combine independent predicates with pre-model text controls."""

    predicate = audit_diagnostic_predicates(rows)
    text_artifact = audit_text_artifacts(rows)
    surface_form = audit_caption_surface_form(rows)
    passed = (
        float(predicate["predicate_precision"]) >= float(predicate["minimum_precision"])
        and text_artifact["status"] == "PASS_TEXT_ARTIFACT_CONTROL"
        and surface_form["status"].startswith("PASS_")
    )
    return {
        "schema_version": "covol-intervention-validity-v1",
        "status": (
            "PASS_AUTOMATED_VALIDITY_HUMAN_NATURALNESS_UNASSESSED"
            if passed
            else "STOP_INTERVENTION_VALIDITY"
        ),
        "predicate": predicate,
        "text_artifact": text_artifact,
        "surface_form": surface_form,
        "scientific_evidence": (
            "PRE_MODEL_AUTOMATED_VALIDITY_ONLY_NOT_HUMAN_NATURALNESS_OR_MODEL_EFFECT"
        ),
    }


def _write_precision_csv(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("image_id", "error_type", "variant_id", "passed"),
            lineterminator="\n",
        )
        writer.writeheader()
        for row in select_predicate_audit_rows(rows):
            writer.writerow(
                {
                    "image_id": row["image_id"],
                    "error_type": row["error_type"],
                    "variant_id": row["variant_id"],
                    "passed": independently_verify_predicate(row),
                }
            )


def _write_text_artifact_csv(path: Path, result: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "held_out_variant",
                "training_row_count",
                "test_row_count",
                "macro_f1",
                "accuracy",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        folds = result.get("folds")
        if not isinstance(folds, list):
            raise ValueError("text artifact result lacks fold rows")
        for fold in folds:
            writer.writerow(
                {
                    key: fold[key]
                    for key in (
                        "held_out_variant",
                        "training_row_count",
                        "test_row_count",
                        "macro_f1",
                        "accuracy",
                    )
                }
            )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--precision-output", type=Path, required=True)
    parser.add_argument("--text-artifact-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    rows = _read_jsonl(args.input)
    result = audit_intervention_validity(rows)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_precision_csv(args.precision_output, rows)
    _write_text_artifact_csv(args.text_artifact_output, result["text_artifact"])
    if result["status"].startswith("STOP_"):
        raise SystemExit(4)


if __name__ == "__main__":
    main()
