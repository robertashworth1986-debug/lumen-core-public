"""Prospective permutation-calibrated context qualification for FALCON.

This runner qualifies a frozen local language model as an allowlisted
classifier of unstructured data-quality notes. It does not measure hybrid
performance lift and cannot establish field validation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import os
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
V2_PATH = ROOT / "code" / "falcon_constrained_context_router.py"
CORE_PATH = ROOT / "code" / "falcon_hybrid_context_benchmark.py"
DEFAULT_PROTOCOL = (
    ROOT / "config" / "falcon_permutation_calibrated_router_protocol_v3.json"
)
DEFAULT_OUTPUT = ROOT / "out" / "falcon_permutation_calibrated_router_v3"


def _load_v2_module() -> Any:
    module_name = "falcon_constrained_context_router_v2_dependency"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, V2_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen v2 module: {V2_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


v2 = _load_v2_module()
core = v2.core


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    if protocol.get("schema") != "falcon_permutation_calibrated_router_protocol.v3":
        raise ValueError("unexpected permutation-calibrated protocol schema")

    context_classes = protocol.get("context_classes")
    decision = protocol.get("decision_method")
    routing = protocol.get("routing_prompt")
    if not isinstance(context_classes, dict) or len(context_classes) != 3:
        raise ValueError("exactly three context classes are required")
    if not isinstance(decision, dict) or not isinstance(routing, dict):
        raise ValueError("decision method and routing prompt are required")

    allowlisted = decision.get("allowlisted_classes")
    labels = decision.get("label_tokens")
    routing_labels = routing.get("labels")
    if not isinstance(allowlisted, list) or len(set(allowlisted)) != 3:
        raise ValueError("allowlisted_classes must contain three unique classes")
    if set(allowlisted) != set(context_classes):
        raise ValueError("allowlisted classes and context classes must match")
    if not isinstance(labels, list) or len(labels) != 3 or len(set(labels)) != 3:
        raise ValueError("three unique label tokens are required")
    if labels != routing_labels:
        raise ValueError("decision labels and routing labels must match in order")
    if any(not isinstance(label, str) or len(label) != 1 for label in labels):
        raise ValueError("each frozen label must be one ASCII character")
    if not bool(decision.get("use_all_label_permutations")):
        raise ValueError("all label permutations must be enabled")
    permutation_count = math.factorial(len(labels))
    if int(decision.get("required_permutation_count", 0)) != permutation_count:
        raise ValueError("required permutation count does not match label factorial")

    datasets = protocol.get("datasets")
    if not isinstance(datasets, list) or len(datasets) != 2:
        raise ValueError("exactly two qualification domains are required")
    loader_names = {str(row.get("loader")) for row in datasets}
    if not loader_names <= set(core.DATASET_LOADERS):
        raise ValueError("protocol names an unsupported dataset loader")

    evaluation_templates: list[str] = []
    for context_id, context in context_classes.items():
        notes = context.get("evaluation_note_templates")
        if not isinstance(notes, list) or not notes:
            raise ValueError(f"missing evaluation notes for {context_id}")
        evaluation_templates.extend(str(note) for note in notes)
    if len(evaluation_templates) != len(set(evaluation_templates)):
        raise ValueError("evaluation-note templates must be unique")
    decision_count = len(datasets) * len(evaluation_templates)
    required_count = int(protocol["qualification_gate"]["required_decision_count"])
    if decision_count != required_count:
        raise ValueError(
            f"protocol defines {decision_count} decisions but gate requires {required_count}"
        )

    examples = routing.get("few_shot_examples")
    if not isinstance(examples, list) or not examples:
        raise ValueError("frozen few-shot examples are required")
    if any(str(row.get("context_class")) not in context_classes for row in examples):
        raise ValueError("few-shot example uses an unsupported context class")
    if not str(routing.get("calibration_prompt", "")).strip():
        raise ValueError("context-free calibration prompt is required")

    model = protocol.get("model", {})
    if model.get("device") != "cuda" or model.get("dtype") != "float16":
        raise ValueError("v3 is frozen to CUDA float16 execution")

    history = protocol.get("development_history", {})
    prior_relative = history.get("prior_protocol")
    prior_expected_hash = history.get("prior_protocol_sha256")
    if not isinstance(prior_relative, str) or not isinstance(prior_expected_hash, str):
        raise ValueError("prior protocol provenance is required")
    prior_path = ROOT / prior_relative
    if core.file_sha256(prior_path) != prior_expected_hash:
        raise ValueError("prior protocol hash no longer matches frozen v3 provenance")
    return protocol


def build_label_mappings(protocol: dict[str, Any]) -> list[dict[str, str]]:
    labels = [str(value) for value in protocol["decision_method"]["label_tokens"]]
    contexts = sorted(str(value) for value in protocol["context_classes"])
    return [
        dict(zip(labels, permutation, strict=True))
        for permutation in itertools.permutations(contexts)
    ]


def render_note(template: str, channels: list[str]) -> str:
    return template.format(channels=", ".join(channels))


def build_prompt(
    domain: str,
    note: str,
    protocol: dict[str, Any],
    label_to_context: dict[str, str],
) -> str:
    labels = [str(value) for value in protocol["decision_method"]["label_tokens"]]
    context_to_label = {context: label for label, context in label_to_context.items()}
    lines = [
        "CONTEXT_CLASSIFICATION_TASK",
        f"Domain: {domain}",
        "Label definitions:",
    ]
    for label in labels:
        context_id = label_to_context[label]
        definition = protocol["context_classes"][context_id]["definition"]
        lines.append(f"- {label}: {definition}")
    lines.extend(["", "Examples:"])
    for example in protocol["routing_prompt"]["few_shot_examples"]:
        lines.append(f"- Note: {example['note']}")
        lines.append(f"  Label: {context_to_label[str(example['context_class'])]}")
    lines.extend(
        [
            "",
            "EVALUATION_NOTE_START",
            note,
            "EVALUATION_NOTE_END",
            f"Return exactly one label: {', '.join(labels)}.",
        ]
    )
    return "\n".join(lines)


@dataclass(frozen=True)
class CalibratedDecision:
    selected_class: str
    raw_output: str
    aggregate_scores: dict[str, float]
    permutation_records: list[dict[str, Any]]
    calibration_scores: dict[str, float]
    margin: float
    permutation_agreement: float
    latency_seconds: float
    model_forward_pass_count: int
    inference_prompt_count: int


class CalibratedScoringAdapter(Protocol):
    identity: dict[str, Any]

    def score_context(
        self,
        prompt_entries: list[dict[str, Any]],
        system_prompt: str,
        calibration_prompt: str,
        labels: list[str],
    ) -> CalibratedDecision: ...


def aggregate_permutation_scores(
    records: list[dict[str, Any]],
) -> tuple[str, dict[str, float], float, float]:
    if not records:
        return "abstain", {}, 0.0, 0.0
    contexts = sorted(
        {
            str(context)
            for record in records
            for context in record["semantic_scores"]
        }
    )
    aggregate_scores = {
        context: float(
            np.mean([float(record["semantic_scores"][context]) for record in records])
        )
        for context in contexts
    }
    selected, margin = v2.select_candidate(aggregate_scores)
    agreement = float(
        np.mean([record["selected_context_class"] == selected for record in records])
    )
    return selected, aggregate_scores, margin, agreement


class PermutationCalibratedTransformersAdapter:
    """Score six label permutations and one neutral prior in one CUDA batch."""

    def __init__(
        self,
        model_id: str,
        labels: list[str],
        device: str,
        dtype_name: str,
        trust_remote_code: bool = False,
        cache_dir: Path | None = None,
    ) -> None:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "real qualification requires torch and transformers in the active environment"
            ) from exc

        if device != "cuda" or not torch.cuda.is_available():
            raise RuntimeError("v3 real qualification requires an available CUDA device")
        dtype_map = {"float16": torch.float16, "bfloat16": torch.bfloat16}
        if dtype_name not in dtype_map:
            raise ValueError(f"unsupported frozen dtype: {dtype_name}")
        torch_dtype = dtype_map[dtype_name]
        cache_value = str(cache_dir.resolve()) if cache_dir is not None else None
        load_kwargs: dict[str, Any] = {
            "trust_remote_code": trust_remote_code,
        }
        if cache_value is not None:
            load_kwargs["cache_dir"] = cache_value

        started = time.perf_counter()
        self._torch = torch
        self._device = device
        self._labels = list(labels)
        self._tokenizer = AutoTokenizer.from_pretrained(model_id, **load_kwargs)
        self._tokenizer.padding_side = "left"
        if self._tokenizer.pad_token_id is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token
        self._model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            **load_kwargs,
        )
        self._model.to(device)
        self._model.eval()
        self._label_token_ids = self._resolve_single_token_labels(labels)
        resolved_revision = getattr(self._model.config, "_commit_hash", None)
        parameter = next(self._model.parameters())
        self.identity = {
            "kind": "transformers_permutation_calibrated_scoring_model",
            "model_id": model_id,
            "resolved_revision": resolved_revision,
            "device": device,
            "cuda_available": bool(torch.cuda.is_available()),
            "cuda_device_name": torch.cuda.get_device_name(0),
            "cuda_runtime": torch.version.cuda,
            "dtype_requested": dtype_name,
            "parameter_dtype": str(parameter.dtype).replace("torch.", ""),
            "parameter_count": int(sum(value.numel() for value in self._model.parameters())),
            "model_memory_bytes": int(self._model.get_memory_footprint()),
            "trust_remote_code": bool(trust_remote_code),
            "cache_dir": cache_value,
            "load_seconds": time.perf_counter() - started,
            "transformers_version": core.package_version("transformers"),
            "torch_version": core.package_version("torch"),
            "tokenizer_class": type(self._tokenizer).__name__,
            "model_class": type(self._model).__name__,
            "decision_method": (
                "permutation_averaged_context_free_calibrated_single_token_scoring"
            ),
            "single_token_labels": True,
            "label_token_ids": dict(self._label_token_ids),
            "context_free_prior_calibration": True,
            "all_label_permutations": True,
            "required_permutation_count": math.factorial(len(labels)),
            "inference_batching": True,
            "last_token_lm_head_only": True,
        }

    def _resolve_single_token_labels(self, labels: list[str]) -> dict[str, int]:
        resolved: dict[str, int] = {}
        for label in labels:
            ids = self._tokenizer(label, add_special_tokens=False)["input_ids"]
            if len(ids) != 1:
                raise RuntimeError(
                    f"frozen label {label!r} tokenized to {len(ids)} tokens, expected one"
                )
            resolved[label] = int(ids[0])
        if len(set(resolved.values())) != len(labels):
            raise RuntimeError("frozen labels do not resolve to unique token IDs")
        return resolved

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

    def _next_token_label_log_probabilities(
        self,
        prompts: list[str],
        system_prompt: str,
    ) -> tuple[list[dict[str, float]], float]:
        rendered = [self._render_prompt(prompt, system_prompt) for prompt in prompts]
        encoded = self._tokenizer(
            rendered,
            add_special_tokens=False,
            padding=True,
            return_tensors="pt",
        )
        encoded = {key: value.to(self._device) for key, value in encoded.items()}
        label_ids = self._torch.tensor(
            [self._label_token_ids[label] for label in self._labels],
            dtype=self._torch.long,
            device=self._device,
        )
        started = time.perf_counter()
        with self._torch.inference_mode():
            base_outputs = self._model.base_model(
                input_ids=encoded["input_ids"],
                attention_mask=encoded["attention_mask"],
                use_cache=False,
                return_dict=True,
            )
            last_hidden = base_outputs.last_hidden_state[:, -1, :]
            next_token_logits = self._model.get_output_embeddings()(last_hidden)
            label_log_probabilities = self._torch.log_softmax(
                next_token_logits.float(), dim=-1
            ).index_select(1, label_ids)
        elapsed = time.perf_counter() - started
        values = label_log_probabilities.detach().cpu().tolist()
        return [
            {label: float(row[index]) for index, label in enumerate(self._labels)}
            for row in values
        ], elapsed

    def score_context(
        self,
        prompt_entries: list[dict[str, Any]],
        system_prompt: str,
        calibration_prompt: str,
        labels: list[str],
    ) -> CalibratedDecision:
        if labels != self._labels:
            raise ValueError("runtime labels differ from frozen adapter labels")
        expected_count = math.factorial(len(labels))
        if len(prompt_entries) != expected_count:
            raise ValueError("runtime did not provide every label permutation")
        prompts = [str(row["prompt"]) for row in prompt_entries] + [calibration_prompt]
        score_rows, elapsed = self._next_token_label_log_probabilities(
            prompts, system_prompt
        )
        calibration_scores = score_rows[-1]
        permutation_records: list[dict[str, Any]] = []
        for index, (entry, raw_scores) in enumerate(
            zip(prompt_entries, score_rows[:-1], strict=True)
        ):
            label_to_context = {
                str(label): str(context)
                for label, context in entry["label_to_context"].items()
            }
            label_scores = {
                label: {
                    "token_id": int(self._label_token_ids[label]),
                    "evaluation_log_probability": float(raw_scores[label]),
                    "prior_log_probability": float(calibration_scores[label]),
                    "calibrated_log_probability": float(
                        raw_scores[label] - calibration_scores[label]
                    ),
                }
                for label in labels
            }
            semantic_scores = {
                label_to_context[label]: float(
                    label_scores[label]["calibrated_log_probability"]
                )
                for label in labels
            }
            selected, margin = v2.select_candidate(semantic_scores)
            permutation_records.append(
                {
                    "permutation_index": int(index),
                    "label_to_context": label_to_context,
                    "prompt": str(entry["prompt"]),
                    "prompt_sha256": text_sha256(str(entry["prompt"])),
                    "label_scores": label_scores,
                    "semantic_scores": semantic_scores,
                    "selected_context_class": selected,
                    "score_margin": float(margin),
                }
            )
        selected, aggregate_scores, margin, agreement = aggregate_permutation_scores(
            permutation_records
        )
        raw_output = core.canonical_json({"context_class": selected})
        return CalibratedDecision(
            selected_class=selected,
            raw_output=raw_output,
            aggregate_scores=aggregate_scores,
            permutation_records=permutation_records,
            calibration_scores={
                label: float(calibration_scores[label]) for label in labels
            },
            margin=float(margin),
            permutation_agreement=float(agreement),
            latency_seconds=float(elapsed),
            model_forward_pass_count=1,
            inference_prompt_count=len(prompts),
        )


class DeterministicCalibrationFixture:
    """Software-only test double that can never pass the real-model gate."""

    identity = {
        "kind": "deterministic_calibration_test_double",
        "model_id": "fixture-not-an-llm",
        "resolved_revision": None,
        "device": "none",
        "cuda_available": False,
        "decision_method": "keyword_fixture",
        "single_token_labels": True,
        "label_token_ids": {"A": 1, "B": 2, "C": 3},
        "context_free_prior_calibration": True,
        "all_label_permutations": True,
        "required_permutation_count": 6,
        "inference_batching": False,
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
        prompt_entries: list[dict[str, Any]],
        system_prompt: str,
        calibration_prompt: str,
        labels: list[str],
    ) -> CalibratedDecision:
        del system_prompt, calibration_prompt
        note = self._evaluation_note(str(prompt_entries[0]["prompt"]))
        dropout_terms = [
            "explicit nulls",
            "supplied no values",
            "outage removed",
            "remain null",
            "arrived without",
        ]
        noise_terms = [
            "random oscillation",
            "stochastic interference",
            "high-frequency variation",
            "wander unpredictably",
            "excessive jitter",
        ]
        if any(term in note for term in dropout_terms):
            selected = "dropout"
        elif any(term in note for term in noise_terms):
            selected = "noise"
        else:
            selected = "nominal"
        records: list[dict[str, Any]] = []
        for index, entry in enumerate(prompt_entries):
            label_to_context = dict(entry["label_to_context"])
            label_scores = {
                label: {
                    "token_id": self.identity["label_token_ids"][label],
                    "evaluation_log_probability": 1.0
                    if label_to_context[label] == selected
                    else 0.0,
                    "prior_log_probability": 0.0,
                    "calibrated_log_probability": 1.0
                    if label_to_context[label] == selected
                    else 0.0,
                }
                for label in labels
            }
            semantic_scores = {
                label_to_context[label]: float(
                    label_scores[label]["calibrated_log_probability"]
                )
                for label in labels
            }
            records.append(
                {
                    "permutation_index": int(index),
                    "label_to_context": label_to_context,
                    "prompt": str(entry["prompt"]),
                    "prompt_sha256": text_sha256(str(entry["prompt"])),
                    "label_scores": label_scores,
                    "semantic_scores": semantic_scores,
                    "selected_context_class": selected,
                    "score_margin": 1.0,
                }
            )
        aggregate_selected, aggregate_scores, margin, agreement = (
            aggregate_permutation_scores(records)
        )
        return CalibratedDecision(
            selected_class=aggregate_selected,
            raw_output=core.canonical_json({"context_class": aggregate_selected}),
            aggregate_scores=aggregate_scores,
            permutation_records=records,
            calibration_scores={label: 0.0 for label in labels},
            margin=float(margin),
            permutation_agreement=float(agreement),
            latency_seconds=0.0,
            model_forward_pass_count=0,
            inference_prompt_count=0,
        )


def aggregate_rows(
    rows: list[dict[str, Any]], margin_threshold: float
) -> dict[str, Any]:
    valid = [row for row in rows if row["valid"]]
    correct = [row for row in rows if row["correct"]]

    def accuracy(subset: list[dict[str, Any]]) -> float:
        return float(np.mean([row["correct"] for row in subset])) if subset else 0.0

    domains = sorted({str(row["dataset_id"]) for row in rows})
    contexts = sorted({str(row["expected_context_class"]) for row in rows})
    agreements = [float(row["permutation_agreement"]) for row in rows]
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
        "mean_permutation_agreement": float(np.mean(agreements))
        if agreements
        else 0.0,
        "minimum_permutation_agreement": float(min(agreements))
        if agreements
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
        == "transformers_permutation_calibrated_scoring_model",
        "protocol_model_match": model_identity.get("model_id")
        == protocol["model"]["model_id"],
        "resolved_model_revision": bool(model_identity.get("resolved_revision")),
        "cuda_execution": bool(model_identity.get("cuda_available"))
        and str(model_identity.get("device")) == "cuda",
        "single_token_labels": bool(model_identity.get("single_token_labels")),
        "context_free_prior_calibration": bool(
            model_identity.get("context_free_prior_calibration")
        ),
        "all_label_permutations": bool(model_identity.get("all_label_permutations"))
        and int(model_identity.get("required_permutation_count", 0))
        == int(protocol["decision_method"]["required_permutation_count"]),
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
        "mean_permutation_agreement": aggregate["mean_permutation_agreement"]
        >= float(thresholds["minimum_mean_permutation_agreement"]),
        "minimum_permutation_agreement": aggregate["minimum_permutation_agreement"]
        >= float(thresholds["minimum_per_decision_permutation_agreement"]),
        "trace_hash_verification": bool(trace_verified),
    }
    required_checks = {
        "real_model": bool(thresholds["require_real_model"]),
        "protocol_model_match": bool(thresholds["require_protocol_model_match"]),
        "resolved_model_revision": bool(
            thresholds["require_resolved_model_revision"]
        ),
        "cuda_execution": bool(thresholds["require_cuda"]),
        "single_token_labels": bool(thresholds["require_single_token_labels"]),
        "context_free_prior_calibration": bool(
            thresholds["require_context_free_prior_calibration"]
        ),
        "all_label_permutations": bool(
            thresholds["require_all_label_permutations"]
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
        "# FALCON Permutation-Calibrated Context Router Qualification",
        "",
        f"- Run UTC: `{result['run_utc']}`",
        f"- Protocol SHA-256: `{result['protocol_sha256']}`",
        f"- Model: `{result['model']['model_id']}`",
        f"- Resolved revision: `{result['model'].get('resolved_revision')}`",
        f"- Device: `{result['model'].get('device')}`",
        f"- Parameter dtype: `{result['model'].get('parameter_dtype')}`",
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
        f"- Mean permutation agreement: `{aggregate['mean_permutation_agreement']:.6f}`",
        f"- Minimum permutation agreement: `{aggregate['minimum_permutation_agreement']:.6f}`",
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
    adapter: CalibratedScoringAdapter,
    run_timestamp: str | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    system_prompt = str(protocol["routing_prompt"]["system"])
    calibration_prompt = str(protocol["routing_prompt"]["calibration_prompt"])
    labels = [str(value) for value in protocol["decision_method"]["label_tokens"]]
    mappings = build_label_mappings(protocol)
    allowed = set(protocol["decision_method"]["allowlisted_classes"])
    threshold = float(protocol["qualification_gate"]["confidence_margin_threshold"])
    memory_before = core.resident_memory_bytes()
    started = time.perf_counter()
    traces: list[dict[str, Any]] = []
    decision_rows: list[dict[str, Any]] = []
    dataset_receipts: list[dict[str, Any]] = []

    for dataset_cfg in protocol["datasets"]:
        receipt = v2.dataset_note_receipt(dataset_cfg, protocol)
        dataset_receipts.append(receipt)
        channels = receipt["rendered_degraded_features"]
        for expected_context, context_cfg in protocol["context_classes"].items():
            for note_index, template in enumerate(
                context_cfg["evaluation_note_templates"]
            ):
                note = render_note(str(template), channels)
                prompt_entries = [
                    {
                        "label_to_context": mapping,
                        "prompt": build_prompt(
                            str(dataset_cfg["domain"]), note, protocol, mapping
                        ),
                    }
                    for mapping in mappings
                ]
                decision = adapter.score_context(
                    prompt_entries,
                    system_prompt,
                    calibration_prompt,
                    labels,
                )
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
                    "permutation_agreement": float(decision.permutation_agreement),
                    "permutation_count": len(decision.permutation_records),
                    "latency_seconds": float(decision.latency_seconds),
                }
                decision_rows.append(row)
                traces.append(
                    {
                        "schema": "falcon_permutation_calibrated_trace.v3",
                        "trace_type": "context_permutation_calibrated_scoring",
                        **row,
                        "note": note,
                        "note_sha256": text_sha256(note),
                        "system_prompt_sha256": text_sha256(system_prompt),
                        "calibration_prompt": calibration_prompt,
                        "calibration_prompt_sha256": text_sha256(calibration_prompt),
                        "calibration_scores": decision.calibration_scores,
                        "aggregate_scores": decision.aggregate_scores,
                        "permutation_records": decision.permutation_records,
                        "raw_output": decision.raw_output,
                        "raw_output_sha256": text_sha256(decision.raw_output),
                        "model_forward_pass_count": int(
                            decision.model_forward_pass_count
                        ),
                        "inference_prompt_count": int(decision.inference_prompt_count),
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
        "schema": "falcon_permutation_calibrated_router_qualification.v3",
        "run_utc": run_utc,
        "topic": protocol["topic"],
        "protocol_path": str(protocol_path.relative_to(ROOT)).replace("\\", "/"),
        "protocol_sha256": core.file_sha256(protocol_path),
        "runner_path": str(Path(__file__).resolve().relative_to(ROOT)).replace(
            "\\", "/"
        ),
        "runner_sha256": core.file_sha256(Path(__file__).resolve()),
        "v2_dependency_path": str(V2_PATH.relative_to(ROOT)).replace("\\", "/"),
        "v2_dependency_sha256": core.file_sha256(V2_PATH),
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
            "permutation_score_count": len(chained) * len(mappings),
            "model_forward_pass_count": int(
                sum(row["model_forward_pass_count"] for row in chained)
            ),
            "inference_prompt_count": int(
                sum(row["inference_prompt_count"] for row in chained)
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
        "schema": "falcon_permutation_calibrated_router_manifest.v3",
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
            str(V2_PATH.relative_to(ROOT)).replace("\\", "/"): core.file_sha256(
                V2_PATH
            ),
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
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(os.environ["HF_HOME"]) if os.environ.get("HF_HOME") else None,
        help="Hugging Face cache location; use the external drive for large weights.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    protocol = load_protocol(args.protocol)
    if args.fixture_mode:
        adapter: CalibratedScoringAdapter = DeterministicCalibrationFixture()
    else:
        adapter = PermutationCalibratedTransformersAdapter(
            model_id=args.model_id or protocol["model"]["model_id"],
            labels=[
                str(value) for value in protocol["decision_method"]["label_tokens"]
            ],
            device=str(protocol["model"]["device"]),
            dtype_name=str(protocol["model"]["dtype"]),
            trust_remote_code=bool(protocol["model"]["trust_remote_code"]),
            cache_dir=args.cache_dir,
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
                "mean_permutation_agreement": result["aggregate_metrics"][
                    "mean_permutation_agreement"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
