"""Run the preregistered independent MDA control-mapping open-set benchmark."""

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
PROTOCOL_PATH = ROOT / "config" / "mda_control_mapping_open_set_protocol_v2.json"
PROTOCOL_PROVENANCE_PATH = ROOT / "config" / "reviewer_protocol_provenance_v1.json"
OUT_DIR = ROOT / "out" / "mda_control_mapping_open_set_v2"
DOC_PATH = ROOT / "docs" / "MDA_CONTROL_MAPPING_OPEN_SET_RESULT_2026-07-13.md"


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
        relative = path.resolve().relative_to(ROOT.resolve())
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", str(relative)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        value = ""
    else:
        value = result.stdout.strip()
    if value:
        return value
    try:
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
        provenance = json.loads(PROTOCOL_PROVENANCE_PATH.read_text(encoding="utf-8"))
        row = next(item for item in provenance["entries"] if item["path"] == relative)
        commit = str(row["last_touch_commit"])
        if file_sha256(path) != row["sha256"]:
            return None
        if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
            return None
        return commit
    except (OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError):
        return None


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    if protocol.get("schema") != "mda_control_mapping_open_set_protocol.v2":
        raise ValueError("unexpected MDA open-set protocol schema")
    fixture = protocol["fixture_contract"]
    supported_total = (
        int(fixture["supported_archetype_count"])
        * int(fixture["supported_records_per_archetype"])
    )
    unsupported_total = (
        int(fixture["unsupported_archetype_count"])
        * int(fixture["unsupported_records_per_archetype"])
    )
    split_total = sum(
        int(fixture[name])
        for name in (
            "development_records",
            "validation_records",
            "blind_holdout_records",
        )
    )
    if supported_total + unsupported_total != int(fixture["total_records"]):
        raise ValueError("v2 archetype totals do not match the fixture contract")
    if split_total != int(fixture["total_records"]):
        raise ValueError("v2 split totals do not match the fixture contract")
    if len(fixture["supported_archetypes"]) != int(fixture["supported_archetype_count"]):
        raise ValueError("v2 supported archetype registry is incomplete")
    if len(fixture["unsupported_archetypes"]) != int(fixture["unsupported_archetype_count"]):
        raise ValueError("v2 unsupported archetype registry is incomplete")
    if protocol["independence"].get("reuse_v1_holdout_for_v2_metrics") is not False:
        raise ValueError("v2 must not reuse the v1 holdout")
    if protocol["candidate"].get("post_holdout_change_allowed") is not False:
        raise ValueError("v2 must remain frozen after holdout execution")
    return protocol


def fixture_text(record: dict[str, Any]) -> str:
    references = " ".join(record.get("references", []))
    return f"{record['title']} {record['description']} {references}".strip()


def _hashed_record(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        **raw,
        "source_record_sha256": canonical_sha256(raw),
        "parser_version": "synthetic_open_set_fixture_parser.v2",
    }


def generate_fixtures(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    fixture = protocol["fixture_contract"]
    seed = int(protocol["random_seed"])
    supported = fixture["supported_archetypes"]
    unsupported = fixture["unsupported_archetypes"]
    supported_tokens = sorted({token for row in supported for token in row["tokens"]})
    unsupported_tokens = sorted({token for row in unsupported for token in row["tokens"]})
    records: list[dict[str, Any]] = []

    for archetype_index, archetype in enumerate(supported):
        next_archetype = supported[(archetype_index + 1) % len(supported)]
        group: list[dict[str, Any]] = []
        for local_index in range(int(fixture["supported_records_per_archetype"])):
            fixture_id = f"V2-SUP-{archetype_index:02d}-{local_index:02d}"
            source_kind = fixture["source_kinds"][local_index % len(fixture["source_kinds"])]
            ambiguous = local_index >= (
                int(fixture["supported_records_per_archetype"])
                - int(fixture["ambiguous_supported_records_per_archetype"])
            )
            if ambiguous:
                label_status = "ambiguous"
                expected = sorted(
                    set(archetype["expected_controls"] + next_archetype["expected_controls"])
                )
                signal_tokens = list(archetype["tokens"][:3]) + list(next_archetype["tokens"][:3])
            else:
                label_status = "supported"
                expected = list(archetype["expected_controls"])
                signal_tokens = list(archetype["tokens"])

            record_rng = random.Random(seed + archetype_index * 1000 + local_index)
            excluded = set(archetype["tokens"]) | set(next_archetype["tokens"])
            candidates = [token for token in supported_tokens if token not in excluded]
            noise = record_rng.sample(candidates, k=int(fixture["noise_tokens_per_record"]))
            tokens = signal_tokens + noise
            record_rng.shuffle(tokens)

            references: list[str] = []
            if local_index % 3 != 0:
                references.append(f"V2-SYNTH-STIG-{archetype['id'].upper()}")
            if ambiguous and local_index % 2 == 0:
                references.append(f"V2-SYNTH-STIG-{next_archetype['id'].upper()}")

            raw = {
                "fixture_id": fixture_id,
                "source_kind": source_kind,
                "finding_id": f"FINDING-{fixture_id}",
                "title": f"Synthetic supported security observation {local_index}",
                "description": " ".join(tokens),
                "references": references,
                "expected_controls": expected,
                "label_status": label_status,
                "archetype_id": archetype["id"],
            }
            group.append(_hashed_record(raw))

        random.Random(seed + 10_000 + archetype_index).shuffle(group)
        for index, record in enumerate(group):
            record["split"] = (
                "development" if index < 6 else "validation" if index < 9 else "blind_holdout"
            )
            records.append(record)

    for archetype_index, archetype in enumerate(unsupported):
        group = []
        for local_index in range(int(fixture["unsupported_records_per_archetype"])):
            fixture_id = f"V2-OOD-{archetype_index:02d}-{local_index:02d}"
            source_kind = fixture["source_kinds"][local_index % len(fixture["source_kinds"])]
            record_rng = random.Random(seed + 100_000 + archetype_index * 1000 + local_index)
            excluded = set(archetype["tokens"])
            candidates = [token for token in unsupported_tokens if token not in excluded]
            noise = record_rng.sample(candidates, k=int(fixture["noise_tokens_per_record"]))
            tokens = list(archetype["tokens"]) + noise
            record_rng.shuffle(tokens)
            raw = {
                "fixture_id": fixture_id,
                "source_kind": source_kind,
                "finding_id": f"FINDING-{fixture_id}",
                "title": (
                    f"Synthetic unsupported {archetype['id'].replace('_', ' ')} observation "
                    f"{local_index}"
                ),
                "description": " ".join(tokens),
                "references": [f"V2-SYNTH-UNKNOWN-{archetype_index:02d}"],
                "expected_controls": [],
                "label_status": "unsupported",
                "archetype_id": archetype["id"],
            }
            group.append(_hashed_record(raw))

        random.Random(seed + 200_000 + archetype_index).shuffle(group)
        for index, record in enumerate(group):
            record["split"] = (
                "development" if index < 2 else "validation" if index < 5 else "blind_holdout"
            )
            records.append(record)

    records.sort(key=lambda row: row["fixture_id"])
    if len(records) != int(fixture["total_records"]):
        raise ValueError("generated v2 fixture count does not match the protocol")
    expected_splits = {
        "development": int(fixture["development_records"]),
        "validation": int(fixture["validation_records"]),
        "blind_holdout": int(fixture["blind_holdout_records"]),
    }
    actual_splits = {
        split: sum(row["split"] == split for row in records) for split in expected_splits
    }
    if actual_splits != expected_splits:
        raise ValueError(f"generated v2 split counts differ: {actual_splits}")
    return records


def validate_fixture(record: dict[str, Any], protocol: dict[str, Any]) -> list[str]:
    errors = []
    for field in protocol["record_contract"]["required_fields"]:
        if field not in record:
            errors.append(f"missing:{field}")
        elif field not in {"expected_controls", "references"} and record[field] in (
            None,
            "",
            [],
        ):
            errors.append(f"empty:{field}")
    allowed_controls = set(protocol["fixture_contract"]["control_ids"])
    unknown = set(record.get("expected_controls", [])) - allowed_controls
    if unknown:
        errors.append(f"unknown_controls:{','.join(sorted(unknown))}")
    if record.get("label_status") == "unsupported" and record.get("expected_controls"):
        errors.append("unsupported_record_has_expected_controls")
    if record.get("label_status") != "unsupported" and not record.get("expected_controls"):
        errors.append("supported_record_has_no_expected_controls")

    raw_fields = (
        "fixture_id",
        "source_kind",
        "finding_id",
        "title",
        "description",
        "references",
        "expected_controls",
        "label_status",
        "archetype_id",
    )
    if all(field in record for field in raw_fields):
        expected_hash = canonical_sha256({key: record[key] for key in raw_fields})
        if record.get("source_record_sha256") != expected_hash:
            errors.append("source_record_sha256_mismatch")

    if record.get("label_status") == "unsupported":
        title = str(record.get("title", "")).lower()
        prohibited = {
            row["id"].replace("_", " ").lower()
            for row in protocol["fixture_contract"]["supported_archetypes"]
        } | {control.lower() for control in allowed_controls}
        if any(token in title for token in prohibited):
            errors.append("unsupported_title_leaks_supported_class")
    return errors


def static_crosswalk(protocol: dict[str, Any]) -> dict[str, list[str]]:
    return {
        f"V2-SYNTH-STIG-{row['id'].upper()}": list(row["expected_controls"])
        for row in protocol["fixture_contract"]["supported_archetypes"]
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
            if row["label_status"] != "unsupported" and control in row["expected_controls"]
        ]
        if not texts:
            raise ValueError(f"no v2 development prototype records for {control}")
        prototypes.append(" ".join(texts))
    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), sublinear_tf=True)
    prototype_matrix = vectorizer.fit_transform(prototypes)
    return vectorizer, prototype_matrix


def lexical_scores(
    record: dict[str, Any],
    vectorizer: TfidfVectorizer,
    prototype_matrix: Any,
    control_ids: list[str],
) -> dict[str, Any]:
    vector = vectorizer.transform([fixture_text(record)])
    similarities = cosine_similarity(vector, prototype_matrix)[0]
    ranked = sorted(
        zip(control_ids, similarities, strict=True),
        key=lambda item: (-float(item[1]), item[0]),
    )
    top_control, top_score = ranked[0]
    second_score = float(ranked[1][1]) if len(ranked) > 1 else 0.0
    return {
        "top_control": top_control,
        "top_score": float(top_score),
        "second_score": second_score,
        "margin": float(top_score) - second_score,
    }


def lexical_prediction(score: dict[str, Any], score_threshold: float) -> list[str]:
    return [score["top_control"]] if score["top_score"] >= score_threshold else []


def open_set_prediction(
    record: dict[str, Any],
    crosswalk: dict[str, list[str]],
    score: dict[str, Any],
    score_threshold: float,
    margin_threshold: float,
) -> list[str]:
    exact = static_prediction(record, crosswalk)
    if exact:
        return exact
    if score["top_score"] < score_threshold or score["margin"] < margin_threshold:
        return []
    return [score["top_control"]]


def set_metrics(expected: set[str], predicted: set[str]) -> tuple[int, int, int]:
    return len(expected & predicted), len(predicted - expected), len(expected - predicted)


def score_predictions(
    records: list[dict[str, Any]],
    predictions: dict[str, list[str]],
    control_ids: list[str],
) -> dict[str, Any]:
    micro_tp = micro_fp = micro_fn = 0
    label_counts = {control: {"tp": 0, "fp": 0, "fn": 0} for control in control_ids}
    exact = covered = 0
    supported_total = supported_covered = 0
    unsupported_total = unsupported_mapped = 0
    supported_row_f1 = []
    for row in records:
        expected = set(row["expected_controls"])
        predicted = set(predictions[row["fixture_id"]])
        tp, fp, fn = set_metrics(expected, predicted)
        micro_tp += tp
        micro_fp += fp
        micro_fn += fn
        exact += expected == predicted
        covered += bool(predicted)
        if row["label_status"] == "unsupported":
            unsupported_total += 1
            unsupported_mapped += bool(predicted)
        else:
            supported_total += 1
            supported_covered += bool(predicted)
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            supported_row_f1.append(
                2 * precision * recall / (precision + recall) if precision + recall else 0.0
            )
        for control in control_ids:
            label_counts[control]["tp"] += control in expected and control in predicted
            label_counts[control]["fp"] += control not in expected and control in predicted
            label_counts[control]["fn"] += control in expected and control not in predicted

    precision = micro_tp / (micro_tp + micro_fp) if micro_tp + micro_fp else 0.0
    recall = micro_tp / (micro_tp + micro_fn) if micro_tp + micro_fn else 0.0
    micro_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    per_control_f1 = {}
    for control, counts in label_counts.items():
        control_precision = (
            counts["tp"] / (counts["tp"] + counts["fp"])
            if counts["tp"] + counts["fp"]
            else 0.0
        )
        control_recall = (
            counts["tp"] / (counts["tp"] + counts["fn"])
            if counts["tp"] + counts["fn"]
            else 0.0
        )
        per_control_f1[control] = (
            2 * control_precision * control_recall / (control_precision + control_recall)
            if control_precision + control_recall
            else 0.0
        )
    overall_coverage = covered / len(records) if records else 0.0
    return {
        "record_count": len(records),
        "supported_record_count": supported_total,
        "unsupported_record_count": unsupported_total,
        "precision": precision,
        "recall": recall,
        "micro_f1": micro_f1,
        "macro_f1": mean(per_control_f1.values()),
        "mean_supported_record_f1": mean(supported_row_f1) if supported_row_f1 else 0.0,
        "exact_set_match": exact / len(records) if records else 0.0,
        "supported_coverage": supported_covered / supported_total if supported_total else 0.0,
        "overall_coverage": overall_coverage,
        "abstention_rate": 1.0 - overall_coverage,
        "unsupported_mapping_rate": (
            unsupported_mapped / unsupported_total if unsupported_total else 0.0
        ),
        "micro_counts": {"tp": micro_tp, "fp": micro_fp, "fn": micro_fn},
        "per_control_f1": per_control_f1,
    }


def choose_baseline_threshold(
    records: list[dict[str, Any]],
    thresholds: list[float],
    predictor: Callable[[dict[str, Any], float], list[str]],
    control_ids: list[str],
) -> tuple[float, list[dict[str, Any]]]:
    trials = []
    for threshold in thresholds:
        predictions = {row["fixture_id"]: predictor(row, threshold) for row in records}
        trials.append(
            {
                "score_threshold": threshold,
                "metrics": score_predictions(records, predictions, control_ids),
            }
        )
    selected = sorted(
        trials,
        key=lambda row: (
            -row["metrics"]["macro_f1"],
            -row["metrics"]["micro_f1"],
            row["metrics"]["unsupported_mapping_rate"],
            -row["metrics"]["supported_coverage"],
            -row["score_threshold"],
        ),
    )[0]
    return float(selected["score_threshold"]), trials


def choose_open_set_thresholds(
    records: list[dict[str, Any]],
    score_thresholds: list[float],
    margin_thresholds: list[float],
    predictor: Callable[[dict[str, Any], float, float], list[str]],
    control_ids: list[str],
    constraints: dict[str, Any],
) -> tuple[float, float, list[dict[str, Any]], bool]:
    trials = []
    for score_threshold in score_thresholds:
        for margin_threshold in margin_thresholds:
            predictions = {
                row["fixture_id"]: predictor(row, score_threshold, margin_threshold)
                for row in records
            }
            metrics = score_predictions(records, predictions, control_ids)
            feasible = (
                metrics["unsupported_mapping_rate"]
                <= float(constraints["maximum_unsupported_mapping_rate"])
                and metrics["supported_coverage"]
                >= float(constraints["minimum_supported_coverage"])
            )
            trials.append(
                {
                    "score_threshold": score_threshold,
                    "margin_threshold": margin_threshold,
                    "feasible": feasible,
                    "metrics": metrics,
                }
            )
    feasible_trials = [row for row in trials if row["feasible"]]
    if feasible_trials:
        selected = sorted(
            feasible_trials,
            key=lambda row: (
                -row["metrics"]["macro_f1"],
                -row["metrics"]["micro_f1"],
                row["metrics"]["unsupported_mapping_rate"],
                -row["metrics"]["supported_coverage"],
                -row["score_threshold"],
                -row["margin_threshold"],
            ),
        )[0]
        feasible_selection = True
    else:
        selected = sorted(
            trials,
            key=lambda row: (
                row["metrics"]["unsupported_mapping_rate"],
                -row["metrics"]["supported_coverage"],
                -row["metrics"]["macro_f1"],
                -row["score_threshold"],
                -row["margin_threshold"],
            ),
        )[0]
        feasible_selection = False
    return (
        float(selected["score_threshold"]),
        float(selected["margin_threshold"]),
        trials,
        feasible_selection,
    )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def render_markdown(result: dict[str, Any]) -> str:
    selected = result["thresholds"]["candidate"]
    lines = [
        "# MDA Control-Mapping Open-Set Synthetic Result",
        "",
        f"Generated UTC: `{result['generated_utc']}`",
        "",
        "## Verdict",
        "",
        f"- Synthetic open-set gate passed: `{str(result['gate']['passed']).lower()}`",
        f"- Candidate validation constraints feasible: `{str(selected['feasible_selection']).lower()}`",
        f"- Candidate score threshold: `{selected['score_threshold']}`",
        f"- Candidate margin threshold: `{selected['margin_threshold']}`",
        f"- Best baseline: `{result['gate']['best_baseline']}`",
        f"- Candidate micro-F1 delta: `{result['gate']['micro_f1_delta_over_best_baseline']:.6f}`",
        f"- Preregistration commit: `{result['protocol_commit']}`",
        f"- Protocol SHA-256: `{result['protocol_sha256']}`",
        f"- Fixture-chain SHA-256: `{result['fixture_chain_sha256']}`",
        "",
        "## Blind Holdout",
        "",
        "| Strategy | Precision | Recall | Micro F1 | Macro F1 | Supported coverage | Overall coverage | Unsupported mapping |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for strategy in (
        "static_identifier_crosswalk",
        "tfidf_lexical_retrieval",
        "hybrid_static_then_open_set_lexical_v2",
    ):
        metrics = result["holdout_metrics"][strategy]
        lines.append(
            f"| `{strategy}` | {metrics['precision']:.4f} | {metrics['recall']:.4f} | "
            f"{metrics['micro_f1']:.4f} | {metrics['macro_f1']:.4f} | "
            f"{metrics['supported_coverage']:.4f} | {metrics['overall_coverage']:.4f} | "
            f"{metrics['unsupported_mapping_rate']:.4f} |"
        )
    lines.extend(["", "## Gate Detail", ""])
    for name, value in result["gate"]["checks"].items():
        lines.append(f"- `{name}`: `{str(value).lower()}`")
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            result["claim_boundary"],
            "",
            "V1 remains a separate negative result. V2 uses a new seed and new fixtures; neither experiment establishes operational cyber accuracy or Government validation.",
            "",
            "## Next Evidence Gate",
            "",
            result["next_evidence_gate"],
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
    validation_failures = [
        {"fixture_id": row.get("fixture_id"), "errors": validate_fixture(row, protocol)}
        for row in fixtures
    ]
    validation_failures = [row for row in validation_failures if row["errors"]]
    valid = [row for row in fixtures if not validate_fixture(row, protocol)]
    development = [row for row in valid if row["split"] == "development"]
    validation = [row for row in valid if row["split"] == "validation"]
    holdout = [row for row in valid if row["split"] == "blind_holdout"]
    controls = list(protocol["fixture_contract"]["control_ids"])
    crosswalk = static_crosswalk(protocol)
    vectorizer, prototypes = fit_lexical_model(development, controls)
    score_cache = {
        row["fixture_id"]: lexical_scores(row, vectorizer, prototypes, controls)
        for row in valid
    }

    def lexical(row: dict[str, Any], score_threshold: float) -> list[str]:
        return lexical_prediction(score_cache[row["fixture_id"]], score_threshold)

    def candidate(
        row: dict[str, Any], score_threshold: float, margin_threshold: float
    ) -> list[str]:
        return open_set_prediction(
            row,
            crosswalk,
            score_cache[row["fixture_id"]],
            score_threshold,
            margin_threshold,
        )

    score_thresholds = [float(value) for value in protocol["candidate"]["score_threshold_grid"]]
    margin_thresholds = [float(value) for value in protocol["candidate"]["margin_threshold_grid"]]
    baseline_threshold, baseline_trials = choose_baseline_threshold(
        validation, score_thresholds, lexical, controls
    )
    candidate_score, candidate_margin, candidate_trials, feasible_selection = (
        choose_open_set_thresholds(
            validation,
            score_thresholds,
            margin_thresholds,
            candidate,
            controls,
            protocol["candidate"]["validation_constraints"],
        )
    )

    prediction_maps = {
        "static_identifier_crosswalk": {
            row["fixture_id"]: static_prediction(row, crosswalk) for row in holdout
        },
        "tfidf_lexical_retrieval": {
            row["fixture_id"]: lexical(row, baseline_threshold) for row in holdout
        },
        "hybrid_static_then_open_set_lexical_v2": {
            row["fixture_id"]: candidate(row, candidate_score, candidate_margin)
            for row in holdout
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
    candidate_id = "hybrid_static_then_open_set_lexical_v2"
    candidate_metrics = holdout_metrics[candidate_id]
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
        "validation_constraints_feasible": feasible_selection,
        "minimum_holdout_supported_coverage": candidate_metrics["supported_coverage"]
        >= float(gates["minimum_holdout_supported_coverage"]),
        "maximum_holdout_unsupported_mapping_rate": candidate_metrics[
            "unsupported_mapping_rate"
        ]
        <= float(gates["maximum_holdout_unsupported_mapping_rate"]),
        "minimum_micro_f1_delta_over_best_baseline": delta
        >= float(gates["minimum_micro_f1_delta_over_best_baseline"]),
        "all_baselines_present": all(name in holdout_metrics for name in baselines),
    }

    full_predictions = []
    for row in holdout:
        score = score_cache[row["fixture_id"]]
        static_available = bool(static_prediction(row, crosswalk))
        for strategy, predictions in prediction_maps.items():
            predicted = predictions[row["fixture_id"]]
            if strategy == "static_identifier_crosswalk":
                route = "static" if predicted else "abstain"
                score_threshold = None
                margin_threshold = None
            elif strategy == "tfidf_lexical_retrieval":
                route = "lexical" if predicted else "abstain"
                score_threshold = baseline_threshold
                margin_threshold = None
            else:
                route = "static" if static_available else "lexical" if predicted else "abstain"
                score_threshold = candidate_score
                margin_threshold = candidate_margin
            full_predictions.append(
                {
                    "fixture_id": row["fixture_id"],
                    "split": row["split"],
                    "label_status": row["label_status"],
                    "archetype_id": row["archetype_id"],
                    "strategy": strategy,
                    "expected_controls": row["expected_controls"],
                    "predicted_controls": predicted,
                    "top_control": score["top_control"],
                    "top_score": score["top_score"],
                    "second_score": score["second_score"],
                    "margin": score["margin"],
                    "score_threshold": score_threshold,
                    "margin_threshold": margin_threshold,
                    "static_route_available": static_available,
                    "route": route,
                }
            )

    evaluation_events = []
    for row in full_predictions:
        expected = set(row["expected_controls"])
        predicted = set(row["predicted_controls"])
        reason_codes = []
        if not predicted:
            reason_codes.append("ABSTAIN")
            if row["strategy"] == "static_identifier_crosswalk":
                reason_codes.append("NO_STATIC_IDENTIFIER")
            elif row["score_threshold"] is not None and row["top_score"] < row["score_threshold"]:
                reason_codes.append("LOW_SCORE")
            if (
                row["margin_threshold"] is not None
                and row["margin"] < row["margin_threshold"]
            ):
                reason_codes.append("LOW_MARGIN")
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
        for row in validation_failures
    )

    generated = now_utc()
    result = {
        "schema": "mda_control_mapping_open_set_result.v2",
        "generated_utc": generated,
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": file_sha256(protocol_path),
        "protocol_commit": protocol_commit(protocol_path),
        "independence": protocol["independence"],
        "fixture_counts": {
            "total": len(fixtures),
            "development": len(development),
            "validation": len(validation),
            "blind_holdout": len(holdout),
            "supported": sum(row["label_status"] != "unsupported" for row in fixtures),
            "unsupported": sum(row["label_status"] == "unsupported" for row in fixtures),
            "parser_rejections": len(validation_failures),
        },
        "fixture_chain_sha256": canonical_sha256(fixtures),
        "thresholds": {
            "fit_split": "development",
            "selection_split": "validation",
            "baseline": {
                "score_threshold": baseline_threshold,
                "trials": baseline_trials,
            },
            "candidate": {
                "score_threshold": candidate_score,
                "margin_threshold": candidate_margin,
                "feasible_selection": feasible_selection,
                "feasible_trial_count": sum(row["feasible"] for row in candidate_trials),
                "trials": candidate_trials,
            },
            "holdout_used_for_selection": False,
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
        "schema": "mda_control_mapping_open_set_fixture_manifest.v2",
        "generated_utc": generated,
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": result["protocol_sha256"],
        "fixture_count": len(fixtures),
        "fixture_chain_sha256": result["fixture_chain_sha256"],
        "fixtures": [
            {
                "fixture_id": row["fixture_id"],
                "source_record_sha256": row["source_record_sha256"],
                "label_status": row["label_status"],
            }
            for row in fixtures
        ],
    }
    split_rows = [
        {"fixture_id": row["fixture_id"], "split": row["split"]}
        for row in fixtures
    ]
    split_manifest = {
        "schema": "mda_control_mapping_open_set_split_manifest.v2",
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
        "schema": "mda_control_mapping_open_set_threshold_selection_receipt.v2",
        "generated_utc": generated,
        "protocol_id": protocol["protocol_id"],
        "fit_split": "development",
        "selection_split": "validation",
        "holdout_used_for_selection": False,
        "baseline_selection_order": protocol["baselines"][1]["selection_order"],
        "candidate_validation_constraints": protocol["candidate"]["validation_constraints"],
        "candidate_feasible_selection_order": protocol["candidate"]["feasible_selection_order"],
        "candidate_infeasible_fallback_order": protocol["candidate"][
            "infeasible_fallback_order"
        ],
        "selected": {
            "tfidf_lexical_retrieval": {"score_threshold": baseline_threshold},
            candidate_id: {
                "score_threshold": candidate_score,
                "margin_threshold": candidate_margin,
                "feasible_selection": feasible_selection,
            },
        },
        "trials": {
            "tfidf_lexical_retrieval": baseline_trials,
            candidate_id: candidate_trials,
        },
    }

    fixtures_path = output_dir / "synthetic_open_set_fixtures_latest.jsonl"
    fixture_manifest_path = output_dir / "fixture_manifest_latest.json"
    split_manifest_path = output_dir / "split_manifest_latest.json"
    threshold_receipt_path = output_dir / "threshold_selection_receipt_latest.json"
    predictions_path = output_dir / "holdout_predictions_latest.jsonl"
    failures_path = output_dir / "failure_and_abstention_log_latest.jsonl"
    result_path = output_dir / "mda_control_mapping_open_set_latest.json"
    write_jsonl(fixtures_path, fixtures)
    write_json(fixture_manifest_path, fixture_manifest)
    write_json(split_manifest_path, split_manifest)
    write_json(threshold_receipt_path, threshold_receipt)
    write_jsonl(predictions_path, full_predictions)
    write_jsonl(failures_path, evaluation_events)
    write_json(result_path, result)
    manifest = {
        "schema": "mda_control_mapping_open_set_manifest.v2",
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
    write_json(output_dir / "mda_control_mapping_open_set_manifest_latest.json", manifest)
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
