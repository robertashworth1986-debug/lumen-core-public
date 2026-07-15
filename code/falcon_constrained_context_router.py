"""Prospective constrained-context qualification for the DARPA FALCON lane.

This runner does not measure hybrid performance lift. It qualifies a frozen
local language model as an allowlisted classifier of unstructured data-quality
notes before a separate full comparative protocol may be run.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "code" / "falcon_hybrid_context_benchmark.py"
DEFAULT_PROTOCOL = ROOT / "config" / "falcon_constrained_context_router_protocol_v2.json"
DEFAULT_OUTPUT = ROOT / "out" / "falcon_constrained_context_router_v2"


def _load_core_module() -> Any:
    module_name = "falcon_hybrid_context_benchmark_v1_core"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, CORE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen core module: {CORE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


core = _load_core_module()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    if protocol.get("schema") != "falcon_constrained_context_router_protocol.v2":
        raise ValueError("unexpected constrained-router protocol schema")

    context_classes = protocol.get("context_classes")
    decision = protocol.get("decision_method")
    candidates = protocol.get("routing_prompt", {}).get("candidate_completions")
    if not isinstance(context_classes, dict) or not context_classes:
        raise ValueError("context_classes must be a non-empty object")
    if not isinstance(decision, dict) or not isinstance(candidates, dict):
        raise ValueError("decision method and candidate completions are required")

    allowlisted = decision.get("allowlisted_classes")
    if not isinstance(allowlisted, list) or len(set(allowlisted)) != len(allowlisted):
        raise ValueError("allowlisted_classes must be a unique list")
    expected = set(context_classes)
    if set(allowlisted) != expected or set(candidates) != expected:
        raise ValueError("contexts, allowlist, and candidate completions must match")

    dataset_rows = protocol.get("datasets")
    if not isinstance(dataset_rows, list) or len(dataset_rows) != 2:
        raise ValueError("exactly two qualification domains are required")
    loader_names = {str(row.get("loader")) for row in dataset_rows}
    if not loader_names <= set(core.DATASET_LOADERS):
        raise ValueError("protocol names an unsupported dataset loader")

    note_counts = []
    for context_id, context in context_classes.items():
        notes = context.get("evaluation_note_templates")
        if not isinstance(notes, list) or not notes:
            raise ValueError(f"missing evaluation notes for {context_id}")
        note_counts.append(len(notes))
    decision_count = len(dataset_rows) * sum(note_counts)
    required_count = int(protocol["qualification_gate"]["required_decision_count"])
    if decision_count != required_count:
        raise ValueError(
            f"protocol defines {decision_count} decisions but gate requires {required_count}"
        )
    return protocol


@dataclass(frozen=True)
class CandidateDecision:
    selected_class: str
    raw_output: str
    candidate_scores: dict[str, dict[str, Any]]
    margin: float
    latency_seconds: float
    model_forward_pass_count: int


class ContextScoringAdapter(Protocol):
    identity: dict[str, Any]

    def score_context(
        self,
        prompt: str,
        system_prompt: str,
        candidates: dict[str, str],
    ) -> CandidateDecision: ...


def select_candidate(scores: dict[str, float]) -> tuple[str, float]:
    finite = [
        (context_id, float(score))
        for context_id, score in scores.items()
        if math.isfinite(float(score))
    ]
    if not finite:
        return "abstain", 0.0
    ranked = sorted(finite, key=lambda row: (-row[1], row[0]))
    margin = ranked[0][1] - ranked[1][1] if len(ranked) > 1 else math.inf
    return ranked[0][0], float(margin)


class CandidateScoringTransformersAdapter:
    """Score allowlisted answer completions in one deterministic model batch."""

    def __init__(self, model_id: str, trust_remote_code: bool = False) -> None:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "real qualification requires torch and transformers in the active environment"
            ) from exc

        started = time.perf_counter()
        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(
            model_id, trust_remote_code=trust_remote_code
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            model_id,
            trust_remote_code=trust_remote_code,
            torch_dtype="auto",
        )
        self._model.eval()
        resolved_revision = getattr(self._model.config, "_commit_hash", None)
        self.identity = {
            "kind": "transformers_candidate_scoring_model",
            "model_id": model_id,
            "resolved_revision": resolved_revision,
            "device": "cpu",
            "trust_remote_code": bool(trust_remote_code),
            "load_seconds": time.perf_counter() - started,
            "transformers_version": core.package_version("transformers"),
            "torch_version": core.package_version("torch"),
            "tokenizer_class": type(self._tokenizer).__name__,
            "model_class": type(self._model).__name__,
            "decision_method": "candidate_completion_mean_log_probability",
            "candidate_batching": True,
        }

    def _render_prompt(self, prompt: str, system_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        if hasattr(self._tokenizer, "apply_chat_template"):
            return self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        return system_prompt + "\n\n" + prompt + "\n\nAnswer:\n"

    def score_context(
        self,
        prompt: str,
        system_prompt: str,
        candidates: dict[str, str],
    ) -> CandidateDecision:
        rendered = self._render_prompt(prompt, system_prompt)
        prefix_ids = self._tokenizer(
            rendered, add_special_tokens=False
        )["input_ids"]
        if not prefix_ids:
            raise RuntimeError("tokenized routing prompt is empty")

        candidate_ids: dict[str, list[int]] = {}
        for context_id, completion in candidates.items():
            ids = self._tokenizer(completion, add_special_tokens=False)["input_ids"]
            if not ids:
                raise RuntimeError(f"empty candidate completion: {context_id}")
            candidate_ids[context_id] = [int(value) for value in ids]

        ordered = sorted(candidate_ids)
        sequences = [prefix_ids + candidate_ids[context_id] for context_id in ordered]
        maximum = max(len(row) for row in sequences)
        pad_id = self._tokenizer.pad_token_id
        if pad_id is None:
            pad_id = self._tokenizer.eos_token_id
        if pad_id is None:
            pad_id = 0
        input_ids = self._torch.full(
            (len(sequences), maximum), int(pad_id), dtype=self._torch.long
        )
        attention_mask = self._torch.zeros_like(input_ids)
        for row_index, values in enumerate(sequences):
            length = len(values)
            input_ids[row_index, :length] = self._torch.tensor(
                values, dtype=self._torch.long
            )
            attention_mask[row_index, :length] = 1

        started = time.perf_counter()
        with self._torch.inference_mode():
            logits = self._model(
                input_ids=input_ids, attention_mask=attention_mask
            ).logits
            log_probabilities = self._torch.log_softmax(logits, dim=-1)
        elapsed = time.perf_counter() - started

        prefix_length = len(prefix_ids)
        audit_scores: dict[str, dict[str, Any]] = {}
        selection_scores: dict[str, float] = {}
        for row_index, context_id in enumerate(ordered):
            targets = candidate_ids[context_id]
            start = prefix_length - 1
            stop = start + len(targets)
            positions = log_probabilities[row_index, start:stop, :]
            target_tensor = self._torch.tensor(targets, dtype=self._torch.long)
            token_scores = positions.gather(1, target_tensor.unsqueeze(1)).squeeze(1)
            score_sum = float(token_scores.sum().item())
            score_mean = float(token_scores.mean().item())
            selection_scores[context_id] = score_mean
            completion = candidates[context_id]
            audit_scores[context_id] = {
                "completion": completion,
                "completion_sha256": text_sha256(completion),
                "token_count": len(targets),
                "sum_log_probability": score_sum,
                "mean_log_probability": score_mean,
            }

        selected, margin = select_candidate(selection_scores)
        raw_output = core.canonical_json({"context_class": selected})
        return CandidateDecision(
            selected_class=selected,
            raw_output=raw_output,
            candidate_scores=audit_scores,
            margin=margin,
            latency_seconds=elapsed,
            model_forward_pass_count=1,
        )


class DeterministicQualificationFixture:
    """Software-only test double that can never pass the real-model gate."""

    identity = {
        "kind": "deterministic_qualification_test_double",
        "model_id": "fixture-not-an-llm",
        "resolved_revision": None,
        "device": "none",
        "trust_remote_code": False,
        "decision_method": "keyword_fixture",
        "candidate_batching": False,
    }

    @staticmethod
    def _evaluation_note(prompt: str) -> str:
        marker = "EVALUATION_NOTE_START\n"
        end_marker = "\nEVALUATION_NOTE_END"
        if marker not in prompt or end_marker not in prompt:
            return ""
        return prompt.split(marker, 1)[1].split(end_marker, 1)[0].lower()

    def score_context(
        self,
        prompt: str,
        system_prompt: str,
        candidates: dict[str, str],
    ) -> CandidateDecision:
        del system_prompt
        note = self._evaluation_note(prompt)
        dropout_terms = [
            "no observations",
            "omits",
            "offline",
            "blank values",
            "no readings",
        ]
        noise_terms = [
            "random jitter",
            "calibration drift",
            "stochastic measurement noise",
            "variance exceeds",
            "fluctuate unpredictably",
        ]
        nominal_terms = [
            "every measurement field arrived",
            "complete sensor panel is populated",
            "all requested channels are available",
            "quality control accepted every feature",
            "no channel outage or calibration drift is reported",
        ]
        if any(term in note for term in nominal_terms):
            selected = "nominal"
        elif any(term in note for term in dropout_terms):
            selected = "dropout"
        elif any(term in note for term in noise_terms):
            selected = "noise"
        else:
            selected = "nominal"
        scores = {
            context_id: {
                "completion": completion,
                "completion_sha256": text_sha256(completion),
                "token_count": 1,
                "sum_log_probability": -0.1 if context_id == selected else -1.0,
                "mean_log_probability": -0.1 if context_id == selected else -1.0,
            }
            for context_id, completion in candidates.items()
        }
        return CandidateDecision(
            selected_class=selected,
            raw_output=core.canonical_json({"context_class": selected}),
            candidate_scores=scores,
            margin=0.9,
            latency_seconds=0.0,
            model_forward_pass_count=0,
        )


def dataset_note_receipt(
    dataset_cfg: dict[str, Any], protocol: dict[str, Any]
) -> dict[str, Any]:
    loader = core.DATASET_LOADERS[str(dataset_cfg["loader"])]
    bunch = loader()
    x = np.asarray(bunch.data, dtype=float)
    y = np.asarray(bunch.target, dtype=int)
    feature_names = [str(value) for value in bunch.feature_names]
    target_names = [str(value) for value in bunch.target_names]
    train, validation, test = core.split_indices(y, protocol["development_split"])
    degraded = core.degraded_features(
        x[train], y[train], float(protocol["degraded_feature_fraction"])
    )
    return {
        "dataset_id": str(dataset_cfg["id"]),
        "domain": str(dataset_cfg["domain"]),
        "loader": str(dataset_cfg["loader"]),
        "row_count": int(len(y)),
        "feature_count": int(x.shape[1]),
        "class_count": int(len(np.unique(y))),
        "content_sha256": core.canonical_sha256(
            {
                "feature_names": feature_names,
                "target_names": target_names,
                "x": x.tolist(),
                "y": y.tolist(),
            }
        ),
        "development_split_receipt": {
            "train_indices_sha256": core.canonical_sha256(train.tolist()),
            "validation_indices_sha256": core.canonical_sha256(validation.tolist()),
            "test_indices_sha256": core.canonical_sha256(test.tolist()),
            "pairwise_disjoint": bool(
                not set(train) & set(validation)
                and not set(train) & set(test)
                and not set(validation) & set(test)
            ),
        },
        "rendered_degraded_feature_count": int(len(degraded)),
        "rendered_degraded_features": [feature_names[index] for index in degraded],
        "rendered_degraded_feature_indices_sha256": core.canonical_sha256(
            degraded.tolist()
        ),
    }


def render_note(template: str, channels: list[str]) -> str:
    return template.format(channels=", ".join(channels))


def build_prompt(domain: str, note: str, protocol: dict[str, Any]) -> str:
    lines = [
        "CONTEXT_CLASSIFICATION_TASK",
        f"Domain: {domain}",
        "Class definitions:",
    ]
    for context_id in protocol["decision_method"]["allowlisted_classes"]:
        definition = protocol["context_classes"][context_id]["definition"]
        lines.append(f"- {context_id}: {definition}")
    lines.extend(["", "Examples:"])
    for example in protocol["routing_prompt"]["few_shot_examples"]:
        lines.append(f"- Note: {example['note']}")
        lines.append(f"  Class: {example['context_class']}")
    lines.extend(
        [
            "",
            "EVALUATION_NOTE_START",
            note,
            "EVALUATION_NOTE_END",
            "Select the candidate completion that best matches this note.",
        ]
    )
    return "\n".join(lines)


def aggregate_rows(
    rows: list[dict[str, Any]], margin_threshold: float
) -> dict[str, Any]:
    valid = [row for row in rows if row["valid"]]
    correct = [row for row in rows if row["correct"]]

    def accuracy(subset: list[dict[str, Any]]) -> float:
        return float(np.mean([row["correct"] for row in subset])) if subset else 0.0

    domains = sorted({str(row["dataset_id"]) for row in rows})
    contexts = sorted({str(row["expected_context_class"]) for row in rows})
    return {
        "decision_count": len(rows),
        "valid_decision_count": len(valid),
        "correct_decision_count": len(correct),
        "overall_accuracy": accuracy(rows),
        "unsupported_output_rate": float(np.mean([not row["valid"] for row in rows]))
        if rows
        else 1.0,
        "mean_score_margin": float(np.mean([row["score_margin"] for row in rows]))
        if rows
        else 0.0,
        "confidence_margin_threshold": float(margin_threshold),
        "confident_decision_rate": float(
            np.mean([row["score_margin"] >= margin_threshold for row in rows])
        )
        if rows
        else 0.0,
        "per_domain_accuracy": {
            domain: accuracy([row for row in rows if row["dataset_id"] == domain])
            for domain in domains
        },
        "per_context_accuracy": {
            context: accuracy(
                [row for row in rows if row["expected_context_class"] == context]
            )
            for context in contexts
        },
    }


def evaluate_gate(
    protocol: dict[str, Any],
    aggregate: dict[str, Any],
    model_identity: dict[str, Any],
    trace_verified: bool,
    completed_domain_count: int,
) -> dict[str, Any]:
    thresholds = protocol["qualification_gate"]
    checks = {
        "real_model": model_identity.get("kind")
        == "transformers_candidate_scoring_model",
        "protocol_model_match": model_identity.get("model_id")
        == protocol["model"]["model_id"],
        "resolved_model_revision": bool(model_identity.get("resolved_revision")),
        "two_completed_domains": completed_domain_count == 2,
        "required_decision_count": aggregate["decision_count"]
        == int(thresholds["required_decision_count"]),
        "overall_accuracy": aggregate["overall_accuracy"]
        >= float(thresholds["minimum_overall_accuracy"]),
        "per_domain_accuracy": all(
            value >= float(thresholds["minimum_per_domain_accuracy"])
            for value in aggregate["per_domain_accuracy"].values()
        ),
        "per_context_accuracy": all(
            value >= float(thresholds["minimum_per_context_accuracy"])
            for value in aggregate["per_context_accuracy"].values()
        ),
        "unsupported_output_rate": aggregate["unsupported_output_rate"]
        <= float(thresholds["maximum_unsupported_output_rate"]),
        "confident_decision_rate": aggregate["confident_decision_rate"]
        >= float(thresholds["minimum_confident_decision_rate"]),
        "trace_hash_verification": bool(trace_verified),
    }
    required_checks = {
        "real_model": bool(thresholds["require_real_model"]),
        "protocol_model_match": bool(thresholds["require_protocol_model_match"]),
        "resolved_model_revision": bool(
            thresholds["require_resolved_model_revision"]
        ),
        "two_completed_domains": bool(thresholds["require_two_completed_domains"]),
        "trace_hash_verification": bool(
            thresholds["require_trace_hash_verification"]
        ),
    }
    effective = dict(checks)
    for name, required in required_checks.items():
        if not required:
            effective[name] = True
    return {
        "thresholds": thresholds,
        "observed": aggregate,
        "checks": checks,
        "qualification_gate_passed": all(effective.values()),
    }


def render_report(result: dict[str, Any]) -> str:
    aggregate = result["aggregate_metrics"]
    gate = result["qualification_gate"]
    lines = [
        "# FALCON Constrained Context Router Qualification",
        "",
        f"- Run UTC: `{result['run_utc']}`",
        f"- Protocol SHA-256: `{result['protocol_sha256']}`",
        f"- Model: `{result['model']['model_id']}`",
        f"- Resolved revision: `{result['model'].get('resolved_revision')}`",
        f"- Qualification gate passed: `{str(gate['qualification_gate_passed']).lower()}`",
        f"- Trace chain verified: `{str(result['trace_chain']['verified']).lower()}`",
        "",
        "## Aggregate Results",
        "",
        f"- Decisions: `{aggregate['decision_count']}`",
        f"- Overall accuracy: `{aggregate['overall_accuracy']:.6f}`",
        f"- Unsupported output rate: `{aggregate['unsupported_output_rate']:.6f}`",
        f"- Mean score margin: `{aggregate['mean_score_margin']:.6f}`",
        f"- Confident decision rate: `{aggregate['confident_decision_rate']:.6f}`",
        "",
        "### Per Domain",
        "",
        "| Domain | Accuracy |",
        "| --- | ---: |",
    ]
    for domain, accuracy in aggregate["per_domain_accuracy"].items():
        lines.append(f"| `{domain}` | {accuracy:.6f} |")
    lines.extend(["", "### Per Context", "", "| Context | Accuracy |", "| --- | ---: |"])
    for context, accuracy in aggregate["per_context_accuracy"].items():
        lines.append(f"| `{context}` | {accuracy:.6f} |")
    lines.extend(["", "## Gate Checks", ""])
    for name, passed in gate["checks"].items():
        lines.append(f"- `{name}`: `{str(passed).lower()}`")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            result["claim_boundary"],
            "",
            "Fixture-mode output is software evidence only and can never qualify the real model.",
            "",
        ]
    )
    return "\n".join(lines)


def run_qualification(
    protocol_path: Path,
    output_dir: Path,
    adapter: ContextScoringAdapter,
    run_timestamp: str | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    system_prompt = str(protocol["routing_prompt"]["system"])
    candidates = {
        str(key): str(value)
        for key, value in protocol["routing_prompt"]["candidate_completions"].items()
    }
    allowed = set(protocol["decision_method"]["allowlisted_classes"])
    threshold = float(protocol["qualification_gate"]["confidence_margin_threshold"])
    memory_before = core.resident_memory_bytes()
    started = time.perf_counter()
    traces: list[dict[str, Any]] = []
    decision_rows: list[dict[str, Any]] = []
    dataset_receipts: list[dict[str, Any]] = []

    for dataset_cfg in protocol["datasets"]:
        receipt = dataset_note_receipt(dataset_cfg, protocol)
        dataset_receipts.append(receipt)
        channels = receipt["rendered_degraded_features"]
        for expected_context, context_cfg in protocol["context_classes"].items():
            for note_index, template in enumerate(
                context_cfg["evaluation_note_templates"]
            ):
                note = render_note(str(template), channels)
                prompt = build_prompt(str(dataset_cfg["domain"]), note, protocol)
                decision = adapter.score_context(prompt, system_prompt, candidates)
                valid = decision.selected_class in allowed
                correct = valid and decision.selected_class == expected_context
                row = {
                    "dataset_id": str(dataset_cfg["id"]),
                    "domain": str(dataset_cfg["domain"]),
                    "expected_context_class": str(expected_context),
                    "note_index": int(note_index),
                    "selected_context_class": decision.selected_class,
                    "valid": bool(valid),
                    "correct": bool(correct),
                    "score_margin": float(decision.margin),
                    "confident": bool(decision.margin >= threshold),
                    "latency_seconds": float(decision.latency_seconds),
                }
                decision_rows.append(row)
                traces.append(
                    {
                        "schema": "falcon_constrained_context_trace.v2",
                        "trace_type": "context_candidate_scoring",
                        **row,
                        "note": note,
                        "note_sha256": text_sha256(note),
                        "prompt": prompt,
                        "prompt_sha256": text_sha256(prompt),
                        "system_prompt_sha256": text_sha256(system_prompt),
                        "candidate_scores": decision.candidate_scores,
                        "raw_output": decision.raw_output,
                        "raw_output_sha256": text_sha256(decision.raw_output),
                        "model_forward_pass_count": int(
                            decision.model_forward_pass_count
                        ),
                    }
                )

    chained, terminal = core.chain_records(traces)
    trace_verified, verified_terminal = core.verify_chain(chained)
    aggregate = aggregate_rows(decision_rows, threshold)
    gate = evaluate_gate(
        protocol,
        aggregate,
        adapter.identity,
        trace_verified,
        len(dataset_receipts),
    )
    memory_after = core.resident_memory_bytes()
    run_utc = run_timestamp or core.now_utc()
    result: dict[str, Any] = {
        "schema": "falcon_constrained_context_router_qualification.v2",
        "run_utc": run_utc,
        "topic": protocol["topic"],
        "protocol_path": str(protocol_path.relative_to(ROOT)).replace("\\", "/"),
        "protocol_sha256": core.file_sha256(protocol_path),
        "runner_path": str(Path(__file__).resolve().relative_to(ROOT)).replace(
            "\\", "/"
        ),
        "runner_sha256": core.file_sha256(Path(__file__).resolve()),
        "core_dependency_path": str(CORE_PATH.relative_to(ROOT)).replace("\\", "/"),
        "core_dependency_sha256": core.file_sha256(CORE_PATH),
        "git_commit": core.git_commit(),
        "model": dict(adapter.identity),
        "decision_method": protocol["decision_method"],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": core.package_version("numpy"),
            "scikit_learn": core.package_version("scikit-learn"),
            "transformers": core.package_version("transformers"),
            "torch": core.package_version("torch"),
        },
        "runtime": {
            "elapsed_seconds": time.perf_counter() - started,
            "rss_before_bytes": memory_before,
            "rss_after_bytes": memory_after,
            "peak_rss_proxy_bytes": max(
                value for value in [memory_before, memory_after] if value is not None
            )
            if memory_before is not None or memory_after is not None
            else None,
            "route_decision_count": len(chained),
            "candidate_completion_count": len(chained) * len(candidates),
            "model_forward_pass_count": int(
                sum(row["model_forward_pass_count"] for row in chained)
            ),
            "model_scoring_seconds": float(
                sum(row["latency_seconds"] for row in chained)
            ),
        },
        "dataset_receipts": dataset_receipts,
        "aggregate_metrics": aggregate,
        "decision_rows": decision_rows,
        "trace_chain": {
            "record_count": len(chained),
            "terminal_sha256": terminal,
            "verified_terminal_sha256": verified_terminal,
            "verified": bool(trace_verified),
        },
        "qualification_gate": gate,
        "claim_boundary": protocol["claim_boundary"],
    }

    traces_path = output_dir / "traces.jsonl"
    traces_path.write_text(
        "".join(core.canonical_json(row) + "\n" for row in chained),
        encoding="utf-8",
    )
    result_path = output_dir / "router_qualification_result.json"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report_path = output_dir / "ROUTER_QUALIFICATION_REPORT.md"
    report_path.write_text(render_report(result), encoding="utf-8")
    manifest = {
        "schema": "falcon_constrained_context_router_manifest.v2",
        "generated_utc": run_utc,
        "files": {
            path.name: {"bytes": path.stat().st_size, "sha256": core.file_sha256(path)}
            for path in [traces_path, result_path, report_path]
        },
        "source_files": {
            str(protocol_path.relative_to(ROOT)).replace("\\", "/"): core.file_sha256(
                protocol_path
            ),
            str(Path(__file__).resolve().relative_to(ROOT)).replace(
                "\\", "/"
            ): core.file_sha256(Path(__file__).resolve()),
            str(CORE_PATH.relative_to(ROOT)).replace("\\", "/"): core.file_sha256(
                CORE_PATH
            ),
        },
    }
    manifest["manifest_sha256"] = core.canonical_sha256(manifest)
    (output_dir / "manifest.sha256.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--fixture-mode",
        action="store_true",
        help="Run a deterministic software test double; never qualifies the model.",
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help="Exploratory override; a mismatch fails the protocol-model gate.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    protocol = load_protocol(args.protocol)
    if args.fixture_mode:
        adapter: ContextScoringAdapter = DeterministicQualificationFixture()
    else:
        adapter = CandidateScoringTransformersAdapter(
            model_id=args.model_id or protocol["model"]["model_id"],
            trust_remote_code=bool(protocol["model"]["trust_remote_code"]),
        )
    result = run_qualification(args.protocol, args.output_dir, adapter)
    print(
        json.dumps(
            {
                "result": str(args.output_dir / "router_qualification_result.json"),
                "qualification_gate_passed": result["qualification_gate"][
                    "qualification_gate_passed"
                ],
                "overall_accuracy": result["aggregate_metrics"]["overall_accuracy"],
                "trace_chain_verified": result["trace_chain"]["verified"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
