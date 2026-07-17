"""Bounded FALCON benchmark for validated LLM routing of ML experts.

The benchmark compares a context-blind ML expert, an LLM-only classifier, an
LLM-routed hybrid, and a deterministic context router on the same held-out
rows. Fixture mode exists only for software tests and can never pass the
promotion gate.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from sklearn.datasets import load_breast_cancer, load_wine
from sklearn.feature_selection import f_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "config" / "falcon_hybrid_context_protocol_v1.json"
DEFAULT_OUTPUT = ROOT / "out" / "falcon_hybrid_context_benchmark"
ZERO_HASH = "0" * 64


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "falcon_hybrid_context_protocol.v1":
        raise ValueError("unexpected FALCON benchmark protocol schema")
    routes = payload.get("routes")
    if not isinstance(routes, list) or sorted(routes) != sorted(
        ["full", "dropout_robust", "noise_robust", "abstain"]
    ):
        raise ValueError("protocol route allowlist is incomplete")
    contexts = payload.get("contexts", {})
    expected = {value.get("expected_route") for value in contexts.values()}
    if expected != {"full", "dropout_robust", "noise_robust"}:
        raise ValueError("protocol contexts do not cover all structured experts")
    if payload.get("promotion_gate", {}).get("require_real_model") is not True:
        raise ValueError("v1 protocol must require a real model")
    return payload


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def resident_memory_bytes() -> int | None:
    try:
        import psutil  # type: ignore

        return int(psutil.Process(os.getpid()).memory_info().rss)
    except (ImportError, OSError):
        return None


class TextAdapter(Protocol):
    identity: dict[str, Any]

    def generate(self, prompt: str, max_new_tokens: int) -> tuple[str, float]: ...


class TransformersAdapter:
    """Small, local Hugging Face causal-language-model adapter."""

    def __init__(self, model_id: str, trust_remote_code: bool = False) -> None:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "real-model run requires torch and transformers in the active environment"
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
            "kind": "transformers_real_model",
            "model_id": model_id,
            "resolved_revision": resolved_revision,
            "device": "cpu",
            "trust_remote_code": bool(trust_remote_code),
            "load_seconds": time.perf_counter() - started,
            "transformers_version": package_version("transformers"),
            "torch_version": package_version("torch"),
            "tokenizer_class": type(self._tokenizer).__name__,
            "model_class": type(self._model).__name__,
        }

    def generate(self, prompt: str, max_new_tokens: int) -> tuple[str, float]:
        messages = [
            {
                "role": "system",
                "content": (
                    "Return only the requested JSON object. Do not add markdown, code, "
                    "instructions, or unsupported identifiers."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        if hasattr(self._tokenizer, "apply_chat_template"):
            rendered = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            rendered = messages[0]["content"] + "\n\n" + prompt
        inputs = self._tokenizer(rendered, return_tensors="pt")
        started = time.perf_counter()
        with self._torch.inference_mode():
            output = self._model.generate(
                **inputs,
                max_new_tokens=int(max_new_tokens),
                do_sample=False,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        elapsed = time.perf_counter() - started
        new_tokens = output[0][inputs["input_ids"].shape[1] :]
        return self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip(), elapsed


class DeterministicFixtureAdapter:
    """Test double. Its identity permanently prevents evidence promotion."""

    identity = {
        "kind": "deterministic_test_double",
        "model_id": "fixture-not-an-llm",
        "resolved_revision": None,
        "device": "none",
        "trust_remote_code": False,
    }

    def generate(self, prompt: str, max_new_tokens: int) -> tuple[str, float]:
        del max_new_tokens
        if "ROUTE_TASK" in prompt:
            match = re.search(r"EXPECTED_CONTEXT_CLASS:([a-z_]+)", prompt)
            mapping = {
                "nominal": "full",
                "declared_dropout": "dropout_robust",
                "declared_noise": "noise_robust",
            }
            route = mapping.get(match.group(1) if match else "", "abstain")
            return json.dumps({"route_id": route}), 0.0
        return json.dumps({"class_id": 0}), 0.0


def extract_json_object(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    candidate = raw.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*```$", "", candidate)
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start < 0 or end < start:
        return None, "no_json_object"
    candidate = candidate[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(parsed, dict):
        return None, "json_not_object"
    return parsed, None


def parse_route(raw: str, allowed_routes: set[str]) -> tuple[str, bool, str | None]:
    parsed, error = extract_json_object(raw)
    if parsed is None:
        return "abstain", False, error
    if set(parsed) != {"route_id"}:
        return "abstain", False, "unexpected_route_schema"
    route = parsed.get("route_id")
    if not isinstance(route, str) or route not in allowed_routes - {"abstain"}:
        return "abstain", False, "route_not_allowlisted"
    return route, True, None


def parse_label(raw: str, allowed_classes: set[int]) -> tuple[int, bool, str | None]:
    parsed, error = extract_json_object(raw)
    if parsed is None:
        return -1, False, error
    if set(parsed) != {"class_id"}:
        return -1, False, "unexpected_label_schema"
    value = parsed.get("class_id")
    if isinstance(value, bool):
        return -1, False, "class_not_allowlisted"
    try:
        label = int(value)
    except (TypeError, ValueError):
        return -1, False, "class_not_allowlisted"
    if label not in allowed_classes:
        return -1, False, "class_not_allowlisted"
    return label, True, None


@dataclass
class Expert:
    name: str
    feature_indices: np.ndarray
    pipeline: Pipeline

    def predict(self, values: np.ndarray) -> np.ndarray:
        return self.pipeline.predict(values[:, self.feature_indices]).astype(int)


@dataclass
class DatasetRun:
    dataset_id: str
    domain: str
    feature_names: list[str]
    target_names: list[str]
    x: np.ndarray
    y: np.ndarray
    train_indices: np.ndarray
    validation_indices: np.ndarray
    test_indices: np.ndarray
    degraded_feature_indices: np.ndarray
    training_mean: np.ndarray
    training_std: np.ndarray
    experts: dict[str, Expert]
    fixed_expert: str
    validation_scores: dict[str, float]


DATASET_LOADERS = {
    "load_breast_cancer": load_breast_cancer,
    "load_wine": load_wine,
}


def split_indices(y: np.ndarray, split: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    indices = np.arange(len(y), dtype=int)
    train_validation, test = train_test_split(
        indices,
        test_size=float(split["test_fraction"]),
        random_state=int(split["random_state"]),
        stratify=y,
    )
    train, validation = train_test_split(
        train_validation,
        test_size=float(split["validation_fraction_of_remaining"]),
        random_state=int(split["random_state"]) + 1,
        stratify=y[train_validation],
    )
    return np.sort(train), np.sort(validation), np.sort(test)


def degraded_features(x_train: np.ndarray, y_train: np.ndarray, fraction: float) -> np.ndarray:
    scores, _ = f_classif(x_train, y_train)
    scores = np.nan_to_num(scores, nan=-np.inf, posinf=np.finfo(float).max)
    count = max(1, int(math.ceil(x_train.shape[1] * fraction)))
    ranked = np.argsort(-scores, kind="stable")
    return np.sort(ranked[:count].astype(int))


def make_pipeline(protocol: dict[str, Any]) -> Pipeline:
    expert_cfg = protocol["experts"]
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    max_iter=int(expert_cfg["max_iter"]),
                    C=float(expert_cfg["regularization_c"]),
                    random_state=int(protocol["split"]["random_state"]),
                ),
            ),
        ]
    )


def transform_context(
    values: np.ndarray,
    context_id: str,
    degraded: np.ndarray,
    training_std: np.ndarray,
    protocol: dict[str, Any],
    seed: int,
) -> np.ndarray:
    transformed = np.array(values, dtype=float, copy=True)
    context = protocol["contexts"][context_id]
    if context_id == "declared_dropout":
        transformed[:, degraded] = np.nan
    elif context_id == "declared_noise":
        rng = np.random.default_rng(seed)
        sigma = float(context["noise_sigma"])
        noise = rng.normal(
            0.0,
            np.maximum(training_std[degraded], 1e-12) * sigma,
            size=(len(transformed), len(degraded)),
        )
        transformed[:, degraded] += noise
    return transformed


def balanced_accuracy_with_invalid(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    recalls: list[float] = []
    for label in sorted(int(value) for value in np.unique(y_true)):
        mask = y_true == label
        recalls.append(float(np.mean(y_pred[mask] == label)))
    return float(np.mean(recalls)) if recalls else 0.0


def score_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    labels = sorted(int(value) for value in np.unique(y_true))
    return {
        "balanced_accuracy": balanced_accuracy_with_invalid(y_true, y_pred),
        "macro_f1": float(
            f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
        ),
        "accuracy": float(np.mean(y_true == y_pred)),
    }


def prepare_dataset(dataset_cfg: dict[str, Any], protocol: dict[str, Any]) -> DatasetRun:
    loader = DATASET_LOADERS.get(dataset_cfg["loader"])
    if loader is None:
        raise ValueError(f"unsupported dataset loader: {dataset_cfg['loader']}")
    bunch = loader()
    x = np.asarray(bunch.data, dtype=float)
    y = np.asarray(bunch.target, dtype=int)
    feature_names = [str(value) for value in bunch.feature_names]
    target_names = [str(value) for value in bunch.target_names]
    train_idx, validation_idx, test_idx = split_indices(y, protocol["split"])
    x_train = x[train_idx]
    y_train = y[train_idx]
    fraction = max(
        float(value["degraded_feature_fraction"])
        for value in protocol["contexts"].values()
    )
    degraded = degraded_features(x_train, y_train, fraction)
    kept = np.array([index for index in range(x.shape[1]) if index not in set(degraded)])
    training_mean = np.nanmean(x_train, axis=0)
    training_std = np.nanstd(x_train, axis=0)

    full_pipeline = make_pipeline(protocol)
    full_pipeline.fit(x_train, y_train)
    dropout_pipeline = make_pipeline(protocol)
    dropout_pipeline.fit(x_train[:, kept], y_train)

    rng = np.random.default_rng(int(protocol["split"]["random_state"]) + len(y))
    augmented_x = [x_train]
    augmented_y = [y_train]
    noise_sigma = float(protocol["contexts"]["declared_noise"]["noise_sigma"])
    for _ in range(int(protocol["experts"]["noise_augmentation_copies"])):
        copy_x = np.array(x_train, copy=True)
        copy_x[:, degraded] += rng.normal(
            0.0,
            np.maximum(training_std[degraded], 1e-12) * noise_sigma,
            size=(len(copy_x), len(degraded)),
        )
        augmented_x.append(copy_x)
        augmented_y.append(y_train)
    noise_pipeline = make_pipeline(protocol)
    noise_pipeline.fit(np.vstack(augmented_x), np.concatenate(augmented_y))

    experts = {
        "full": Expert("full", np.arange(x.shape[1], dtype=int), full_pipeline),
        "dropout_robust": Expert("dropout_robust", kept, dropout_pipeline),
        "noise_robust": Expert(
            "noise_robust", np.arange(x.shape[1], dtype=int), noise_pipeline
        ),
    }

    validation_scores: dict[str, float] = {}
    for expert_name, expert in experts.items():
        context_scores: list[float] = []
        for offset, context_id in enumerate(protocol["contexts"]):
            x_context = transform_context(
                x[validation_idx],
                context_id,
                degraded,
                training_std,
                protocol,
                int(protocol["split"]["random_state"]) + 100 + offset,
            )
            prediction = expert.predict(x_context)
            context_scores.append(
                balanced_accuracy_with_invalid(y[validation_idx], prediction)
            )
        validation_scores[expert_name] = float(np.mean(context_scores))
    fixed_expert = sorted(
        validation_scores, key=lambda name: (-validation_scores[name], name)
    )[0]

    return DatasetRun(
        dataset_id=str(dataset_cfg["id"]),
        domain=str(dataset_cfg["domain"]),
        feature_names=feature_names,
        target_names=target_names,
        x=x,
        y=y,
        train_indices=train_idx,
        validation_indices=validation_idx,
        test_indices=test_idx,
        degraded_feature_indices=degraded,
        training_mean=training_mean,
        training_std=training_std,
        experts=experts,
        fixed_expert=fixed_expert,
        validation_scores=validation_scores,
    )


def context_notes(run: DatasetRun, context_id: str) -> list[str]:
    names = [run.feature_names[index] for index in run.degraded_feature_indices]
    channels = ", ".join(names)
    notes = {
        "nominal": [
            "Quality bulletin: all measurement channels passed calibration and are present.",
            "Operator note: no missing channels or abnormal telemetry noise was detected.",
            "Data status: the complete feature panel is available under normal conditions.",
        ],
        "declared_dropout": [
            f"Incident report: these channels are offline and will be missing: {channels}.",
            f"Data-quality alert: unavailable measurements are {channels}; use a dropout-tolerant route.",
            f"Operator note: the following fields have no readings: {channels}.",
        ],
        "declared_noise": [
            f"Calibration advisory: stochastic high-amplitude noise affects {channels}.",
            f"Telemetry warning: these channels are present but noisy: {channels}.",
            f"Operator note: unstable calibration increases variance in {channels}.",
        ],
    }
    return notes[context_id]


def route_prompt(run: DatasetRun, context_id: str, note: str) -> str:
    return "\n".join(
        [
            "ROUTE_TASK",
            f"Domain: {run.domain}",
            "Choose exactly one route from this catalog:",
            "- full: calibrated complete feature panel",
            "- dropout_robust: declared missing or unavailable channels",
            "- noise_robust: declared noisy or unstable channels",
            f"Context note: {note}",
            f"EXPECTED_CONTEXT_CLASS:{context_id}",
            'Return only: {"route_id":"full|dropout_robust|noise_robust"}',
        ]
    )


def label_prompt(
    run: DatasetRun, context_id: str, note: str, values: np.ndarray
) -> str:
    class_catalog = ", ".join(
        f"{index}={name}" for index, name in enumerate(run.target_names)
    )
    rows: list[str] = []
    for name, value in zip(run.feature_names, values, strict=True):
        rendered = "missing" if not np.isfinite(value) else f"{float(value):.6g}"
        rows.append(f"{name}={rendered}")
    return "\n".join(
        [
            "LABEL_TASK",
            f"Domain: {run.domain}",
            f"Classes: {class_catalog}",
            f"Context: {context_id}",
            f"Context note: {note}",
            "Measurements: " + "; ".join(rows),
            'Return only: {"class_id":<one allowed integer>}',
        ]
    )


def stratified_eval_indices(y: np.ndarray, maximum: int, seed: int) -> np.ndarray:
    if maximum >= len(y):
        return np.arange(len(y), dtype=int)
    rng = np.random.default_rng(seed)
    selected: list[int] = []
    labels = sorted(int(value) for value in np.unique(y))
    base = maximum // len(labels)
    remainder = maximum % len(labels)
    for position, label in enumerate(labels):
        candidates = np.flatnonzero(y == label)
        count = base + (1 if position < remainder else 0)
        chosen = rng.choice(candidates, size=min(count, len(candidates)), replace=False)
        selected.extend(int(value) for value in chosen)
    if len(selected) < maximum:
        remaining = np.array(
            [index for index in range(len(y)) if index not in set(selected)], dtype=int
        )
        extra = rng.choice(remaining, size=maximum - len(selected), replace=False)
        selected.extend(int(value) for value in extra)
    return np.array(sorted(selected), dtype=int)


def chain_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    prior = ZERO_HASH
    chained: list[dict[str, Any]] = []
    for record in records:
        row = dict(record)
        row["prior_record_sha256"] = prior
        row["record_sha256"] = canonical_sha256(row)
        prior = row["record_sha256"]
        chained.append(row)
    return chained, prior


def verify_chain(records: list[dict[str, Any]]) -> tuple[bool, str]:
    prior = ZERO_HASH
    for record in records:
        if record.get("prior_record_sha256") != prior:
            return False, prior
        material = {key: value for key, value in record.items() if key != "record_sha256"}
        expected = canonical_sha256(material)
        if record.get("record_sha256") != expected:
            return False, prior
        prior = expected
    return True, prior


def append_trace(
    traces: list[dict[str, Any]],
    *,
    trace_type: str,
    dataset_id: str,
    context_id: str,
    prompt: str,
    raw_output: str,
    parsed_value: Any,
    valid: bool,
    validation_error: str | None,
    latency_seconds: float,
    row_id: str | None = None,
) -> None:
    traces.append(
        {
            "schema": "falcon_hybrid_context_trace.v1",
            "trace_type": trace_type,
            "dataset_id": dataset_id,
            "context_id": context_id,
            "row_id": row_id,
            "prompt": prompt,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "raw_output": raw_output,
            "raw_output_sha256": hashlib.sha256(raw_output.encode("utf-8")).hexdigest(),
            "parsed_value": parsed_value,
            "valid": bool(valid),
            "validation_error": validation_error,
            "latency_seconds": float(latency_seconds),
        }
    )


def evaluate_dataset(
    run: DatasetRun,
    dataset_cfg: dict[str, Any],
    protocol: dict[str, Any],
    adapter: TextAdapter,
    traces: list[dict[str, Any]],
) -> dict[str, Any]:
    allowed_routes = set(protocol["routes"])
    allowed_classes = set(int(value) for value in np.unique(run.y))
    route_rows: list[dict[str, Any]] = []
    selected_routes: dict[str, str] = {}
    route_max_tokens = int(protocol["model"]["max_new_tokens_route"])

    for context_id in protocol["contexts"]:
        decisions: list[str] = []
        for note_index, note in enumerate(context_notes(run, context_id)):
            prompt = route_prompt(run, context_id, note)
            raw, latency = adapter.generate(prompt, route_max_tokens)
            route, valid, error = parse_route(raw, allowed_routes)
            decisions.append(route)
            expected = protocol["contexts"][context_id]["expected_route"]
            route_rows.append(
                {
                    "context_id": context_id,
                    "note_index": note_index,
                    "route_id": route,
                    "expected_route": expected,
                    "valid": valid,
                    "correct": valid and route == expected,
                    "latency_seconds": latency,
                }
            )
            append_trace(
                traces,
                trace_type="route",
                dataset_id=run.dataset_id,
                context_id=context_id,
                prompt=prompt,
                raw_output=raw,
                parsed_value=route,
                valid=valid,
                validation_error=error,
                latency_seconds=latency,
                row_id=f"note-{note_index}",
            )
        valid_decisions = [value for value in decisions if value != "abstain"]
        counts = {route: valid_decisions.count(route) for route in sorted(set(valid_decisions))}
        ranked = sorted(counts, key=lambda route: (-counts[route], route))
        if not ranked or (len(ranked) > 1 and counts[ranked[0]] == counts[ranked[1]]):
            selected_routes[context_id] = "abstain"
        else:
            selected_routes[context_id] = ranked[0]

    local_test_positions = stratified_eval_indices(
        run.y[run.test_indices],
        int(dataset_cfg["evaluation_rows_per_context"]),
        int(protocol["split"]["random_state"]) + len(run.y),
    )
    selected_test_indices = run.test_indices[local_test_positions]
    y_test = run.y[selected_test_indices]
    slice_rows: list[dict[str, Any]] = []
    label_max_tokens = int(protocol["model"]["max_new_tokens_label"])

    for context_offset, context_id in enumerate(protocol["contexts"]):
        seed = int(protocol["split"]["random_state"]) + 1000 + context_offset + len(run.y)
        x_context = transform_context(
            run.x[selected_test_indices],
            context_id,
            run.degraded_feature_indices,
            run.training_std,
            protocol,
            seed,
        )
        fixed_prediction = run.experts[run.fixed_expert].predict(x_context)
        routed = selected_routes[context_id]
        hybrid_expert = run.fixed_expert if routed == "abstain" else routed
        hybrid_prediction = run.experts[hybrid_expert].predict(x_context)
        expected_expert = protocol["contexts"][context_id]["expected_route"]
        deterministic_prediction = run.experts[expected_expert].predict(x_context)

        llm_predictions: list[int] = []
        note = context_notes(run, context_id)[0]
        for position, (source_index, values) in enumerate(
            zip(selected_test_indices, x_context, strict=True)
        ):
            prompt = label_prompt(run, context_id, note, values)
            raw, latency = adapter.generate(prompt, label_max_tokens)
            label, valid, error = parse_label(raw, allowed_classes)
            llm_predictions.append(label)
            append_trace(
                traces,
                trace_type="label",
                dataset_id=run.dataset_id,
                context_id=context_id,
                prompt=prompt,
                raw_output=raw,
                parsed_value=label,
                valid=valid,
                validation_error=error,
                latency_seconds=latency,
                row_id=f"test-{int(source_index)}-{position}",
            )
        strategies = {
            "fixed_ml_only": fixed_prediction,
            "llm_only": np.asarray(llm_predictions, dtype=int),
            "llm_routed_hybrid": hybrid_prediction,
            "deterministic_context_router": deterministic_prediction,
        }
        for strategy, prediction in strategies.items():
            metrics = score_predictions(y_test, prediction)
            slice_rows.append(
                {
                    "dataset_id": run.dataset_id,
                    "context_id": context_id,
                    "strategy": strategy,
                    "row_count": int(len(y_test)),
                    "selected_route": routed if strategy == "llm_routed_hybrid" else None,
                    "effective_expert": hybrid_expert if strategy == "llm_routed_hybrid" else None,
                    **metrics,
                }
            )

    return {
        "dataset_id": run.dataset_id,
        "domain": run.domain,
        "dataset_receipt": {
            "row_count": int(len(run.y)),
            "feature_count": int(run.x.shape[1]),
            "class_count": int(len(np.unique(run.y))),
            "content_sha256": canonical_sha256(
                {
                    "feature_names": run.feature_names,
                    "target_names": run.target_names,
                    "x": run.x.tolist(),
                    "y": run.y.tolist(),
                }
            ),
        },
        "split_receipt": {
            "train_count": int(len(run.train_indices)),
            "validation_count": int(len(run.validation_indices)),
            "test_count": int(len(run.test_indices)),
            "train_indices_sha256": canonical_sha256(run.train_indices.tolist()),
            "validation_indices_sha256": canonical_sha256(run.validation_indices.tolist()),
            "test_indices_sha256": canonical_sha256(run.test_indices.tolist()),
            "pairwise_disjoint": bool(
                not set(run.train_indices) & set(run.validation_indices)
                and not set(run.train_indices) & set(run.test_indices)
                and not set(run.validation_indices) & set(run.test_indices)
            ),
        },
        "degraded_features": [
            {
                "index": int(index),
                "name": run.feature_names[int(index)],
            }
            for index in run.degraded_feature_indices
        ],
        "fixed_ml_expert": run.fixed_expert,
        "validation_balanced_accuracy": run.validation_scores,
        "selected_hybrid_routes": selected_routes,
        "route_rows": route_rows,
        "test_row_indices_sha256": canonical_sha256(selected_test_indices.tolist()),
        "slice_metrics": slice_rows,
    }


def aggregate_results(dataset_results: list[dict[str, Any]]) -> dict[str, Any]:
    strategies = sorted(
        {
            row["strategy"]
            for result in dataset_results
            for row in result["slice_metrics"]
        }
    )
    aggregate: dict[str, Any] = {}
    for strategy in strategies:
        rows = [
            row
            for result in dataset_results
            for row in result["slice_metrics"]
            if row["strategy"] == strategy
        ]
        aggregate[strategy] = {
            "macro_slice_balanced_accuracy": float(
                np.mean([row["balanced_accuracy"] for row in rows])
            ),
            "macro_slice_f1": float(np.mean([row["macro_f1"] for row in rows])),
            "macro_slice_accuracy": float(np.mean([row["accuracy"] for row in rows])),
            "slice_count": len(rows),
        }
    domain_scores: dict[str, dict[str, float]] = {}
    for result in dataset_results:
        domain_scores[result["dataset_id"]] = {}
        for strategy in strategies:
            rows = [
                row for row in result["slice_metrics"] if row["strategy"] == strategy
            ]
            domain_scores[result["dataset_id"]][strategy] = float(
                np.mean([row["balanced_accuracy"] for row in rows])
            )
    route_rows = [row for result in dataset_results for row in result["route_rows"]]
    return {
        "strategies": aggregate,
        "per_domain_balanced_accuracy": domain_scores,
        "route_accuracy": float(np.mean([row["correct"] for row in route_rows])),
        "unsupported_route_output_rate": float(
            np.mean([not row["valid"] for row in route_rows])
        ),
        "route_call_count": len(route_rows),
    }


def evaluate_gate(
    protocol: dict[str, Any],
    aggregate: dict[str, Any],
    dataset_results: list[dict[str, Any]],
    model_identity: dict[str, Any],
    chain_verified: bool,
) -> dict[str, Any]:
    gate = protocol["promotion_gate"]
    strategies = aggregate["strategies"]
    hybrid = strategies["llm_routed_hybrid"]["macro_slice_balanced_accuracy"]
    fixed = strategies["fixed_ml_only"]["macro_slice_balanced_accuracy"]
    llm_only = strategies["llm_only"]["macro_slice_balanced_accuracy"]
    domain_deltas = {
        dataset_id: values["llm_routed_hybrid"] - values["fixed_ml_only"]
        for dataset_id, values in aggregate["per_domain_balanced_accuracy"].items()
    }
    checks = {
        "real_model": model_identity.get("kind") == "transformers_real_model",
        "resolved_model_revision": bool(model_identity.get("resolved_revision")),
        "two_completed_domains": len(dataset_results) >= 2,
        "hybrid_delta_over_fixed_ml": hybrid - fixed
        >= float(gate["minimum_hybrid_delta_over_fixed_ml"]),
        "hybrid_delta_over_llm_only": hybrid - llm_only
        >= float(gate["minimum_hybrid_delta_over_llm_only"]),
        "per_domain_regression_limit": all(
            delta >= -float(gate["maximum_per_domain_regression_vs_fixed_ml"])
            for delta in domain_deltas.values()
        ),
        "route_accuracy": aggregate["route_accuracy"]
        >= float(gate["minimum_route_accuracy"]),
        "unsupported_route_output_rate": aggregate["unsupported_route_output_rate"]
        <= float(gate["maximum_unsupported_route_output_rate"]),
        "trace_hash_verification": bool(chain_verified),
        "leakage_audit": all(
            result["split_receipt"]["pairwise_disjoint"] for result in dataset_results
        ),
    }
    return {
        "promotion_gate_passed": all(checks.values()),
        "checks": checks,
        "observed": {
            "hybrid_delta_over_fixed_ml": hybrid - fixed,
            "hybrid_delta_over_llm_only": hybrid - llm_only,
            "per_domain_hybrid_delta_over_fixed_ml": domain_deltas,
        },
        "thresholds": gate,
    }


def render_report(result: dict[str, Any]) -> str:
    aggregate = result["aggregate_metrics"]
    lines = [
        "# FALCON Hybrid Context Benchmark",
        "",
        f"- Run UTC: `{result['run_utc']}`",
        f"- Protocol SHA-256: `{result['protocol_sha256']}`",
        f"- Model kind: `{result['model']['kind']}`",
        f"- Model ID: `{result['model'].get('model_id')}`",
        f"- Resolved revision: `{result['model'].get('resolved_revision')}`",
        f"- Promotion gate passed: `{str(result['promotion_gate']['promotion_gate_passed']).lower()}`",
        f"- Trace chain verified: `{str(result['trace_chain']['verified']).lower()}`",
        "",
        "## Aggregate Results",
        "",
        "| Strategy | Macro slice balanced accuracy | Macro slice F1 | Slices |",
        "| --- | ---: | ---: | ---: |",
    ]
    for strategy, metrics in aggregate["strategies"].items():
        lines.append(
            f"| `{strategy}` | {metrics['macro_slice_balanced_accuracy']:.6f} | "
            f"{metrics['macro_slice_f1']:.6f} | {metrics['slice_count']} |"
        )
    lines.extend(
        [
            "",
            "## Routing",
            "",
            f"- Route accuracy: `{aggregate['route_accuracy']:.6f}`",
            f"- Unsupported route-output rate: `{aggregate['unsupported_route_output_rate']:.6f}`",
            f"- Route calls: `{aggregate['route_call_count']}`",
            "",
            "## Gate Checks",
            "",
        ]
    )
    for name, passed in result["promotion_gate"]["checks"].items():
        lines.append(f"- `{name}`: `{str(passed).lower()}`")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            result["claim_boundary"],
            "",
            "Fixture-mode output is a software test only and is never LLM evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def run_benchmark(
    protocol_path: Path,
    output_dir: Path,
    adapter: TextAdapter,
    run_timestamp: str | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    traces: list[dict[str, Any]] = []
    memory_before = resident_memory_bytes()
    started = time.perf_counter()
    dataset_results: list[dict[str, Any]] = []
    for dataset_cfg in protocol["datasets"]:
        prepared = prepare_dataset(dataset_cfg, protocol)
        dataset_results.append(
            evaluate_dataset(prepared, dataset_cfg, protocol, adapter, traces)
        )
    chained_traces, terminal_hash = chain_records(traces)
    chain_verified, verified_terminal = verify_chain(chained_traces)
    aggregate = aggregate_results(dataset_results)
    gate = evaluate_gate(
        protocol, aggregate, dataset_results, adapter.identity, chain_verified
    )
    memory_after = resident_memory_bytes()
    label_rows = [row for row in chained_traces if row["trace_type"] == "label"]
    result: dict[str, Any] = {
        "schema": "falcon_hybrid_context_benchmark.v1",
        "run_utc": run_timestamp or now_utc(),
        "topic": protocol["topic"],
        "protocol_path": str(protocol_path.relative_to(ROOT)).replace("\\", "/"),
        "protocol_sha256": file_sha256(protocol_path),
        "code_path": str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"),
        "code_sha256": file_sha256(Path(__file__).resolve()),
        "git_commit": git_commit(),
        "model": dict(adapter.identity),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": package_version("numpy"),
            "scikit_learn": package_version("scikit-learn"),
            "transformers": package_version("transformers"),
            "torch": package_version("torch"),
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
            "llm_call_count": len(chained_traces),
            "llm_total_generation_seconds": float(
                sum(row["latency_seconds"] for row in chained_traces)
            ),
            "unsupported_label_output_rate": float(
                np.mean([not row["valid"] for row in label_rows])
            )
            if label_rows
            else 0.0,
        },
        "datasets": dataset_results,
        "aggregate_metrics": aggregate,
        "trace_chain": {
            "record_count": len(chained_traces),
            "terminal_sha256": terminal_hash,
            "verified_terminal_sha256": verified_terminal,
            "verified": chain_verified,
        },
        "promotion_gate": gate,
        "claim_boundary": protocol["claim_boundary"],
    }

    traces_path = output_dir / "traces.jsonl"
    traces_path.write_text(
        "".join(canonical_json(row) + "\n" for row in chained_traces), encoding="utf-8"
    )
    result_path = output_dir / "benchmark_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path = output_dir / "BENCHMARK_REPORT.md"
    report_path.write_text(render_report(result), encoding="utf-8")
    manifest = {
        "schema": "falcon_hybrid_context_manifest.v1",
        "generated_utc": result["run_utc"],
        "files": {
            path.name: {"bytes": path.stat().st_size, "sha256": file_sha256(path)}
            for path in [traces_path, result_path, report_path]
        },
        "source_files": {
            str(protocol_path.relative_to(ROOT)).replace("\\", "/"): file_sha256(
                protocol_path
            ),
            str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"): file_sha256(
                Path(__file__).resolve()
            ),
        },
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
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
        help="Run a deterministic software test double; never produces LLM evidence.",
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help="Override the frozen Hugging Face model ID for an exploratory run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    protocol = load_protocol(args.protocol)
    if args.fixture_mode:
        adapter: TextAdapter = DeterministicFixtureAdapter()
    else:
        model_id = args.model_id or protocol["model"]["model_id"]
        adapter = TransformersAdapter(
            model_id=model_id,
            trust_remote_code=bool(protocol["model"]["trust_remote_code"]),
        )
    result = run_benchmark(args.protocol, args.output_dir, adapter)
    print(
        json.dumps(
            {
                "result": str(args.output_dir / "benchmark_result.json"),
                "model_kind": result["model"]["kind"],
                "promotion_gate_passed": result["promotion_gate"][
                    "promotion_gate_passed"
                ],
                "trace_chain_verified": result["trace_chain"]["verified"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

