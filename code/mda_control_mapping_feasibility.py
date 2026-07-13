"""Run the preregistered synthetic MDA control-mapping feasibility benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Callable

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "mda_control_mapping_feasibility_protocol_v1.json"
OUT_DIR = ROOT / "out" / "mda_control_mapping_feasibility"
DOC_PATH = ROOT / "docs" / "MDA_CONTROL_MAPPING_FEASIBILITY_RESULT_2026-07-13.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protocol_commit(path: Path = PROTOCOL_PATH) -> str | None:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    if protocol.get("schema") != "mda_control_mapping_feasibility_protocol.v1":
        raise ValueError("unexpected MDA feasibility protocol schema")
    fixture = protocol["fixture_contract"]
    if fixture["total_records"] != 96:
        raise ValueError("v1 fixture contract requires 96 records")
    if len(fixture["archetypes"]) != len(fixture["control_ids"]):
        raise ValueError("each v1 control must have one synthetic archetype")
    return protocol


def fixture_text(record: dict[str, Any]) -> str:
    references = " ".join(record.get("references", []))
    return f"{record['title']} {record['description']} {references}".strip()


def generate_fixtures(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    fixture = protocol["fixture_contract"]
    seed = int(protocol["random_seed"])
    archetypes = fixture["archetypes"]
    all_tokens = sorted({token for row in archetypes for token in row["tokens"]})
    records: list[dict[str, Any]] = []

    for archetype_index, archetype in enumerate(archetypes):
        next_archetype = archetypes[(archetype_index + 1) % len(archetypes)]
        group: list[dict[str, Any]] = []
        for local_index in range(12):
            fixture_id = f"SYN-{archetype_index:02d}-{local_index:02d}"
            source_kind = fixture["source_kinds"][local_index % len(fixture["source_kinds"])]
            if local_index < 9:
                label_status = "supported"
                expected = list(archetype["expected_controls"])
                signal_tokens = list(archetype["tokens"])
            elif local_index < 11:
                label_status = "ambiguous"
                expected = sorted(
                    set(archetype["expected_controls"] + next_archetype["expected_controls"])
                )
                signal_tokens = list(archetype["tokens"][:3]) + list(next_archetype["tokens"][:3])
            else:
                label_status = "unsupported"
                expected = []
                signal_tokens = ["inventory", "checksum", "widget", "telemetry", "unrelated"]

            record_rng = random.Random(seed + archetype_index * 100 + local_index)
            if label_status == "unsupported":
                noise = ["package", "observation", "catalog"]
            else:
                excluded = set(archetype["tokens"]) | set(next_archetype["tokens"])
                candidates = [token for token in all_tokens if token not in excluded]
                noise = record_rng.sample(candidates, k=int(fixture["noise_tokens_per_record"]))
            tokens = signal_tokens + noise
            record_rng.shuffle(tokens)

            references: list[str] = []
            if label_status != "unsupported" and local_index % 3 != 0:
                references.append(f"SYNTH-STIG-{archetype['id'].upper()}")
            if label_status == "ambiguous" and local_index % 2 == 0:
                references.append(f"SYNTH-STIG-{next_archetype['id'].upper()}")
            if label_status == "unsupported":
                references.append(f"SYNTH-UNKNOWN-{archetype_index:02d}")

            raw = {
                "fixture_id": fixture_id,
                "source_kind": source_kind,
                "finding_id": f"FINDING-{fixture_id}",
                "title": f"Synthetic {archetype['id'].replace('_', ' ')} observation {local_index}",
                "description": " ".join(tokens),
                "references": references,
                "expected_controls": expected,
                "label_status": label_status,
            }
            record = {
                **raw,
                "source_record_sha256": canonical_sha256(raw),
                "parser_version": "synthetic_fixture_parser.v1",
            }
            group.append(record)

        random.Random(seed + archetype_index).shuffle(group)
        for index, record in enumerate(group):
            record["split"] = "development" if index < 6 else "validation" if index < 9 else "blind_holdout"
            records.append(record)

    records.sort(key=lambda row: row["fixture_id"])
    if len(records) != int(fixture["total_records"]):
        raise ValueError("generated fixture count does not match protocol")
    return records


def validate_fixture(record: dict[str, Any], protocol: dict[str, Any]) -> list[str]:
    errors = []
    required = protocol["record_contract"]["required_fields"]
    for field in required:
        if field not in record:
            errors.append(f"missing:{field}")
        elif field not in {"expected_controls", "references"} and record[field] in (
            None,
            "",
            [],
        ):
            errors.append(f"empty:{field}")
    allowed = set(protocol["fixture_contract"]["control_ids"])
    unknown = set(record.get("expected_controls", [])) - allowed
    if unknown:
        errors.append(f"unknown_controls:{','.join(sorted(unknown))}")
    expected_hash = canonical_sha256(
        {
            key: record[key]
            for key in (
                "fixture_id",
                "source_kind",
                "finding_id",
                "title",
                "description",
                "references",
                "expected_controls",
                "label_status",
            )
        }
    )
    if record.get("source_record_sha256") != expected_hash:
        errors.append("source_record_sha256_mismatch")
    return errors


def static_crosswalk(protocol: dict[str, Any]) -> dict[str, list[str]]:
    return {
        f"SYNTH-STIG-{row['id'].upper()}": list(row["expected_controls"])
        for row in protocol["fixture_contract"]["archetypes"]
    }


def static_prediction(record: dict[str, Any], crosswalk: dict[str, list[str]]) -> list[str]:
    controls = {
        control
        for reference in record.get("references", [])
        for control in crosswalk.get(reference, [])
    }
    return sorted(controls)


def fit_lexical_model(
    development: list[dict[str, Any]], control_ids: list[str]
) -> tuple[TfidfVectorizer, Any]:
    prototypes = []
    for control in control_ids:
        texts = [
            fixture_text(row)
            for row in development
            if control in row["expected_controls"] and row["label_status"] != "unsupported"
        ]
        if not texts:
            raise ValueError(f"no development prototype records for {control}")
        prototypes.append(" ".join(texts))
    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), sublinear_tf=True)
    prototype_matrix = vectorizer.fit_transform(prototypes)
    return vectorizer, prototype_matrix


def lexical_prediction(
    record: dict[str, Any],
    vectorizer: TfidfVectorizer,
    prototype_matrix: Any,
    control_ids: list[str],
    threshold: float,
) -> tuple[list[str], float]:
    vector = vectorizer.transform([fixture_text(record)])
    similarities = cosine_similarity(vector, prototype_matrix)[0]
    ranked = sorted(
        zip(control_ids, similarities, strict=True),
        key=lambda item: (-float(item[1]), item[0]),
    )
    control, score = ranked[0]
    return ([control] if float(score) >= threshold else []), float(score)


def set_metrics(expected: set[str], predicted: set[str]) -> tuple[int, int, int]:
    return len(expected & predicted), len(predicted - expected), len(expected - predicted)


def score_predictions(
    records: list[dict[str, Any]],
    predictions: dict[str, list[str]],
    control_ids: list[str],
) -> dict[str, Any]:
    micro_tp = micro_fp = micro_fn = 0
    label_counts = {control: {"tp": 0, "fp": 0, "fn": 0} for control in control_ids}
    exact = covered = unsupported_total = unsupported_mapped = 0
    row_f1 = []
    for row in records:
        expected = set(row["expected_controls"])
        predicted = set(predictions[row["fixture_id"]])
        tp, fp, fn = set_metrics(expected, predicted)
        micro_tp += tp
        micro_fp += fp
        micro_fn += fn
        if expected:
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            row_f1.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
        exact += expected == predicted
        covered += bool(predicted)
        if row["label_status"] == "unsupported":
            unsupported_total += 1
            unsupported_mapped += bool(predicted)
        for control in control_ids:
            label_counts[control]["tp"] += control in expected and control in predicted
            label_counts[control]["fp"] += control not in expected and control in predicted
            label_counts[control]["fn"] += control in expected and control not in predicted

    precision = micro_tp / (micro_tp + micro_fp) if micro_tp + micro_fp else 0.0
    recall = micro_tp / (micro_tp + micro_fn) if micro_tp + micro_fn else 0.0
    micro_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    label_f1 = {}
    for control, counts in label_counts.items():
        label_precision = counts["tp"] / (counts["tp"] + counts["fp"]) if counts["tp"] + counts["fp"] else 0.0
        label_recall = counts["tp"] / (counts["tp"] + counts["fn"]) if counts["tp"] + counts["fn"] else 0.0
        label_f1[control] = (
            2 * label_precision * label_recall / (label_precision + label_recall)
            if label_precision + label_recall
            else 0.0
        )
    return {
        "record_count": len(records),
        "precision": precision,
        "recall": recall,
        "micro_f1": micro_f1,
        "macro_f1": mean(label_f1.values()),
        "mean_supported_record_f1": mean(row_f1) if row_f1 else 0.0,
        "exact_set_match": exact / len(records) if records else 0.0,
        "coverage": covered / len(records) if records else 0.0,
        "abstention_rate": 1.0 - (covered / len(records) if records else 0.0),
        "unsupported_mapping_rate": unsupported_mapped / unsupported_total if unsupported_total else 0.0,
        "micro_counts": {"tp": micro_tp, "fp": micro_fp, "fn": micro_fn},
        "per_control_f1": label_f1,
    }


def choose_threshold(
    records: list[dict[str, Any]],
    thresholds: list[float],
    predictor: Callable[[dict[str, Any], float], list[str]],
    control_ids: list[str],
) -> tuple[float, list[dict[str, Any]]]:
    trials = []
    for threshold in thresholds:
        predictions = {row["fixture_id"]: predictor(row, threshold) for row in records}
        metrics = score_predictions(records, predictions, control_ids)
        trials.append({"threshold": threshold, "metrics": metrics})
    selected = sorted(
        trials,
        key=lambda row: (
            -row["metrics"]["macro_f1"],
            row["metrics"]["unsupported_mapping_rate"],
            -row["metrics"]["coverage"],
            -row["threshold"],
        ),
    )[0]
    return float(selected["threshold"]), trials


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# MDA Control-Mapping Synthetic Feasibility Result",
        "",
        f"Generated UTC: `{result['generated_utc']}`",
        "",
        "## Verdict",
        "",
        f"- Synthetic feasibility gate passed: `{str(result['gate']['passed']).lower()}`",
        f"- Selected lexical threshold: `{result['thresholds']['lexical']}`",
        f"- Selected hybrid threshold: `{result['thresholds']['hybrid']}`",
        f"- Best baseline: `{result['gate']['best_baseline']}`",
        f"- Candidate micro-F1 delta: `{result['gate']['micro_f1_delta_over_best_baseline']:.6f}`",
        "",
        "## Blind Holdout",
        "",
        "| Strategy | Precision | Recall | Micro F1 | Macro F1 | Coverage | Unsupported mapping |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for strategy in (
        "static_identifier_crosswalk",
        "tfidf_lexical_retrieval",
        "hybrid_static_then_lexical_v1",
    ):
        metrics = result["holdout_metrics"][strategy]
        lines.append(
            f"| `{strategy}` | {metrics['precision']:.4f} | {metrics['recall']:.4f} | "
            f"{metrics['micro_f1']:.4f} | {metrics['macro_f1']:.4f} | "
            f"{metrics['coverage']:.4f} | {metrics['unsupported_mapping_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Gate Detail",
            "",
        ]
    )
    for name, value in result["gate"]["checks"].items():
        lines.append(f"- `{name}`: `{str(value).lower()}`")
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            result["claim_boundary"],
            "",
            "The fixtures deliberately use synthetic identifiers and text. This result tests software mechanics and cannot be presented as operational cyber accuracy or Government validation.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_benchmark(
    protocol_path: Path = PROTOCOL_PATH,
    output_dir: Path = OUT_DIR,
    doc_path: Path = DOC_PATH,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    fixtures = generate_fixtures(protocol)
    failures = [
        {"fixture_id": row.get("fixture_id"), "errors": validate_fixture(row, protocol)}
        for row in fixtures
    ]
    failures = [row for row in failures if row["errors"]]
    valid = [row for row in fixtures if not validate_fixture(row, protocol)]
    development = [row for row in valid if row["split"] == "development"]
    validation = [row for row in valid if row["split"] == "validation"]
    holdout = [row for row in valid if row["split"] == "blind_holdout"]
    controls = list(protocol["fixture_contract"]["control_ids"])
    crosswalk = static_crosswalk(protocol)
    vectorizer, prototypes = fit_lexical_model(development, controls)

    def lexical(row: dict[str, Any], threshold: float) -> list[str]:
        return lexical_prediction(row, vectorizer, prototypes, controls, threshold)[0]

    def hybrid(row: dict[str, Any], threshold: float) -> list[str]:
        exact = static_prediction(row, crosswalk)
        return exact if exact else lexical(row, threshold)

    thresholds = [float(value) for value in protocol["candidate"]["threshold_grid"]]
    lexical_threshold, lexical_trials = choose_threshold(validation, thresholds, lexical, controls)
    hybrid_threshold, hybrid_trials = choose_threshold(validation, thresholds, hybrid, controls)

    prediction_maps = {
        "static_identifier_crosswalk": {
            row["fixture_id"]: static_prediction(row, crosswalk) for row in holdout
        },
        "tfidf_lexical_retrieval": {
            row["fixture_id"]: lexical(row, lexical_threshold) for row in holdout
        },
        "hybrid_static_then_lexical_v1": {
            row["fixture_id"]: hybrid(row, hybrid_threshold) for row in holdout
        },
    }
    holdout_metrics = {
        strategy: score_predictions(holdout, predictions, controls)
        for strategy, predictions in prediction_maps.items()
    }
    baselines = ["static_identifier_crosswalk", "tfidf_lexical_retrieval"]
    best_baseline = sorted(
        baselines,
        key=lambda name: (-holdout_metrics[name]["micro_f1"], name),
    )[0]
    candidate_metrics = holdout_metrics["hybrid_static_then_lexical_v1"]
    delta = candidate_metrics["micro_f1"] - holdout_metrics[best_baseline]["micro_f1"]
    parser_rate = len(valid) / len(fixtures)
    provenance_complete = sum(
        not validate_fixture(row, protocol) for row in fixtures
    ) / len(fixtures)
    gates = protocol["promotion_gates"]
    checks = {
        "parser_conformance": parser_rate >= float(gates["parser_conformance_rate"]),
        "provenance_completeness": provenance_complete
        >= float(gates["provenance_completeness"]),
        "minimum_holdout_coverage": candidate_metrics["coverage"]
        >= float(gates["minimum_holdout_coverage"]),
        "maximum_unsupported_mapping_rate": candidate_metrics["unsupported_mapping_rate"]
        <= float(gates["maximum_holdout_unsupported_mapping_rate"]),
        "minimum_micro_f1_delta_over_best_baseline": delta
        >= float(gates["minimum_micro_f1_delta_over_best_baseline"]),
        "all_baselines_present": all(name in holdout_metrics for name in baselines),
    }

    full_predictions = []
    for row in holdout:
        for strategy, predictions in prediction_maps.items():
            predicted = predictions[row["fixture_id"]]
            lexical_controls, lexical_score = lexical_prediction(
                row,
                vectorizer,
                prototypes,
                controls,
                lexical_threshold if strategy != "hybrid_static_then_lexical_v1" else hybrid_threshold,
            )
            full_predictions.append(
                {
                    "fixture_id": row["fixture_id"],
                    "split": row["split"],
                    "label_status": row["label_status"],
                    "strategy": strategy,
                    "expected_controls": row["expected_controls"],
                    "predicted_controls": predicted,
                    "lexical_top_score": lexical_score,
                    "static_route_available": bool(static_prediction(row, crosswalk)),
                    "route": (
                        "static" if strategy == "static_identifier_crosswalk" and predicted
                        else "static"
                        if strategy == "hybrid_static_then_lexical_v1" and static_prediction(row, crosswalk)
                        else "lexical"
                        if strategy != "static_identifier_crosswalk" and lexical_controls
                        else "abstain"
                    ),
                }
            )

    evaluation_events = []
    for row in full_predictions:
        expected = set(row["expected_controls"])
        predicted = set(row["predicted_controls"])
        reason_codes = []
        if not predicted:
            reason_codes.append("ABSTAIN")
        if row["label_status"] == "unsupported" and predicted:
            reason_codes.append("UNSUPPORTED_MAPPING")
        if expected != predicted:
            reason_codes.append("SET_MISMATCH")
        if reason_codes:
            evaluation_events.append({**row, "reason_codes": reason_codes})
    evaluation_events.extend(
        {
            "fixture_id": row["fixture_id"],
            "strategy": "parser",
            "reason_codes": ["PARSER_REJECTION"],
            "errors": row["errors"],
        }
        for row in failures
    )

    generated = now_utc()
    result = {
        "schema": "mda_control_mapping_feasibility_result.v1",
        "generated_utc": generated,
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": file_sha256(protocol_path),
        "protocol_commit": protocol_commit(protocol_path),
        "fixture_counts": {
            "total": len(fixtures),
            "development": len(development),
            "validation": len(validation),
            "blind_holdout": len(holdout),
            "parser_rejections": len(failures),
        },
        "fixture_chain_sha256": canonical_sha256(fixtures),
        "thresholds": {
            "lexical": lexical_threshold,
            "hybrid": hybrid_threshold,
            "selection_split": "validation",
            "lexical_trials": lexical_trials,
            "hybrid_trials": hybrid_trials,
        },
        "holdout_metrics": holdout_metrics,
        "gate": {
            "passed": all(checks.values()),
            "best_baseline": best_baseline,
            "micro_f1_delta_over_best_baseline": delta,
            "checks": checks,
            "operational_or_field_claim_allowed": False,
        },
        "next_evidence_gate": protocol["next_evidence_gate"],
        "claim_boundary": protocol["claim_boundary"],
    }

    fixture_manifest = {
        "schema": "mda_control_mapping_fixture_manifest.v1",
        "generated_utc": generated,
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": result["protocol_sha256"],
        "fixture_count": len(fixtures),
        "fixture_chain_sha256": result["fixture_chain_sha256"],
        "fixtures": [
            {
                "fixture_id": row["fixture_id"],
                "source_record_sha256": row["source_record_sha256"],
            }
            for row in fixtures
        ],
    }
    split_rows = [
        {"fixture_id": row["fixture_id"], "split": row["split"]}
        for row in fixtures
    ]
    split_manifest = {
        "schema": "mda_control_mapping_split_manifest.v1",
        "generated_utc": generated,
        "protocol_id": protocol["protocol_id"],
        "split_rule": protocol["fixture_contract"]["split_rule"],
        "split_counts": {
            "development": len(development),
            "validation": len(validation),
            "blind_holdout": len(holdout),
        },
        "split_rows": split_rows,
        "split_chain_sha256": canonical_sha256(split_rows),
    }
    threshold_receipt = {
        "schema": "mda_control_mapping_threshold_selection_receipt.v1",
        "generated_utc": generated,
        "protocol_id": protocol["protocol_id"],
        "selection_split": "validation",
        "selection_metric": protocol["candidate"]["threshold_selection_metric"],
        "grid": thresholds,
        "selected": {
            "tfidf_lexical_retrieval": lexical_threshold,
            "hybrid_static_then_lexical_v1": hybrid_threshold,
        },
        "trials": {
            "tfidf_lexical_retrieval": lexical_trials,
            "hybrid_static_then_lexical_v1": hybrid_trials,
        },
        "holdout_used_for_selection": False,
    }

    fixtures_path = output_dir / "synthetic_fixtures_latest.jsonl"
    fixture_manifest_path = output_dir / "fixture_manifest_latest.json"
    split_manifest_path = output_dir / "split_manifest_latest.json"
    threshold_receipt_path = output_dir / "threshold_selection_receipt_latest.json"
    predictions_path = output_dir / "holdout_predictions_latest.jsonl"
    failures_path = output_dir / "failure_and_abstention_log_latest.jsonl"
    result_path = output_dir / "mda_control_mapping_feasibility_latest.json"
    write_jsonl(fixtures_path, fixtures)
    write_json(fixture_manifest_path, fixture_manifest)
    write_json(split_manifest_path, split_manifest)
    write_json(threshold_receipt_path, threshold_receipt)
    write_jsonl(predictions_path, full_predictions)
    write_jsonl(failures_path, evaluation_events)
    write_json(result_path, result)
    manifest = {
        "schema": "mda_control_mapping_feasibility_manifest.v1",
        "generated_utc": generated,
        "protocol_sha256": result["protocol_sha256"],
        "protocol_commit": result["protocol_commit"],
        "artifacts": {
            path.name: {"bytes": path.stat().st_size, "sha256": file_sha256(path)}
            for path in (
                fixtures_path,
                fixture_manifest_path,
                split_manifest_path,
                threshold_receipt_path,
                predictions_path,
                failures_path,
                result_path,
            )
        },
        "claim_boundary": result["claim_boundary"],
    }
    manifest["artifact_chain_sha256"] = canonical_sha256(manifest["artifacts"])
    write_json(output_dir / "mda_control_mapping_feasibility_manifest_latest.json", manifest)
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(render_markdown(result), encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=PROTOCOL_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--doc", type=Path, default=DOC_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_benchmark(args.protocol, args.output_dir, args.doc)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
