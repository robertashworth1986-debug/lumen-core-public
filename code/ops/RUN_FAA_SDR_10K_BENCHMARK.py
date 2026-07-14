from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import os
import platform
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, f1_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, OrdinalEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[2]
LOCAL_DATA_DIR = ROOT / "data" / "faa_public" / "sdr"
VAULT_DATA_DIR = Path("E:/LumaProofVault/FAA_PUBLIC_RAW/SDR")
BENCHMARK_VAULT_DIR = Path("E:/LumaProofVault/FAA_PUBLIC_RAW/BENCHMARKS/FAA_SDR_10K_V1")
PROTOCOL_PATH = ROOT / "config" / "faa_sdr_aviation_reliability_10k_protocol_v1.json"
AUDIT_PATH = ROOT / "out" / "ops" / "faa_sdr_source_audit_latest.json"
OUT_JSON = ROOT / "out" / "ops" / "faa_sdr_10k_benchmark_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "faa_sdr_10k_benchmark.json"
OUT_MD = ROOT / "docs" / "FAA_SDR_10K_BENCHMARK_2026-07-13.md"

PROTOCOL_ID = "faa-sdr-triage-10k-v1"
RANDOM_SEED = 20260714
HOLDOUT_TARGET = 10_000
MIN_CLASS_ROWS = 200
MIN_ROUTER_ROWS = 500
MIN_SUBGROUP_ROWS = 200
BOOTSTRAP_RESAMPLES = 10_000
NONINFERIORITY_LOG_LOSS = 0.01
MAX_SUBGROUP_F1_LOSS = 0.03

CATEGORICAL_FEATURES = (
    "AircraftMake",
    "AircraftModel",
    "EngineMake",
    "EngineModel",
    "StageOfOperationCode",
)
NUMERIC_SOURCE_FEATURES = (
    "AircraftTotalTime",
    "AircraftTotalCycles",
    "EngineTotalTime",
    "EngineTotalCycles",
)
NUMERIC_FEATURES = NUMERIC_SOURCE_FEATURES + ("date_month", "date_day_of_year", "date_weekday")
READ_COLUMNS = (
    "OperatorControlNumber",
    "DifficultyDate",
    "JASCCode",
    *CATEGORICAL_FEATURES,
    *NUMERIC_SOURCE_FEATURES,
)

CLAIM_BOUNDARY = (
    "This benchmark evaluates report-level JASC maintenance triage on public FAA SDR records. It is not an FAA or "
    "OEM evaluation, an airworthiness determination, a failure-rate estimate, an engine-health monitor, an "
    "operational decision aid, field validation, or proof of economic savings. The Rolls-Royce-family slice is "
    "descriptive only and does not imply a relationship with or validation by Rolls-Royce."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_text(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .fillna("")
        .str.upper()
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .replace("", "UNKNOWN")
    )


def discover_source_files() -> list[Path]:
    local = sorted(LOCAL_DATA_DIR.glob("SDR-20??.csv"))
    return local or sorted(VAULT_DATA_DIR.glob("SDR-20??.csv"))


def deterministic_holdout_indices(keys: Iterable[str], *, target: int, protocol_id: str) -> list[int]:
    ranked = [
        (hashlib.sha256(f"{protocol_id}:{str(key).upper().strip()}".encode("utf-8")).hexdigest(), index)
        for index, key in enumerate(keys)
    ]
    ranked.sort()
    return [index for _, index in ranked[:target]]


def selected_id_digest(keys: Iterable[str]) -> str:
    normalized = [str(key).upper().strip() for key in keys]
    return hashlib.sha256("\n".join(normalized).encode("utf-8")).hexdigest()


def load_dataset(paths: Iterable[Path] | None = None) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    source_paths = [Path(path) for path in (paths or discover_source_files())]
    if not source_paths:
        raise FileNotFoundError(f"No SDR source files found under {LOCAL_DATA_DIR} or {VAULT_DATA_DIR}")
    for path in source_paths:
        frame = pd.read_csv(
            path,
            usecols=list(READ_COLUMNS),
            dtype=str,
            keep_default_na=False,
            low_memory=False,
            encoding="utf-8-sig",
        )
        frame["source_year"] = int(path.stem.rsplit("-", 1)[-1])
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    data["date"] = pd.to_datetime(data["DifficultyDate"], format="%m/%d/%Y", errors="coerce")
    data["report_key"] = normalize_text(data["OperatorControlNumber"])
    data["jasc_chapter"] = data["JASCCode"].astype(str).str.strip().str.extract(r"^([0-9]{2})[0-9]{2}$", expand=False)
    data = data.loc[data["date"].notna() & data["jasc_chapter"].notna() & data["report_key"].ne("UNKNOWN")].copy()
    for field in CATEGORICAL_FEATURES:
        data[field] = normalize_text(data[field])
    for field in NUMERIC_SOURCE_FEATURES:
        data[field] = pd.to_numeric(data[field].astype(str).str.replace(",", "", regex=False), errors="coerce")
    data["date_month"] = data["date"].dt.month.astype(float)
    data["date_day_of_year"] = data["date"].dt.dayofyear.astype(float)
    data["date_weekday"] = data["date"].dt.weekday.astype(float)
    return data


def split_dataset(data: pd.DataFrame, *, holdout_target: int = HOLDOUT_TARGET) -> dict[str, Any]:
    fit = data.loc[data["date"].dt.year.isin([2023, 2024])].copy()
    router = data.loc[data["date"].dt.year.eq(2025)].copy()
    holdout_pool = data.loc[data["date"].dt.year.eq(2026)].copy()
    if fit.empty or router.empty or len(holdout_pool) < holdout_target:
        raise ValueError("Expected nonempty 2023-2024 fit, 2025 router, and adequate 2026 holdout windows")

    class_counts = fit["jasc_chapter"].value_counts()
    supported = sorted(class_counts[class_counts >= MIN_CLASS_ROWS].index.astype(str))
    if not supported:
        raise ValueError("No JASC chapters satisfy the frozen minimum class support")
    for frame in (fit, router, holdout_pool):
        frame["target"] = frame["jasc_chapter"].where(frame["jasc_chapter"].isin(supported), "OTHER")

    selected_positions = deterministic_holdout_indices(
        holdout_pool["report_key"].tolist(), target=holdout_target, protocol_id=PROTOCOL_ID
    )
    holdout = holdout_pool.iloc[selected_positions].copy().reset_index(drop=True)
    fit = fit.reset_index(drop=True)
    router = router.reset_index(drop=True)

    label_encoder = LabelEncoder()
    label_encoder.fit(np.array(sorted(set(supported) | {"OTHER"}), dtype=object))
    for frame in (fit, router, holdout):
        frame["target_id"] = label_encoder.transform(frame["target"])

    return {
        "fit": fit,
        "router": router,
        "holdout": holdout,
        "label_encoder": label_encoder,
        "supported_chapters": supported,
        "selected_id_set_sha256": selected_id_digest(holdout["report_key"].tolist()),
    }


def feature_frame(data: pd.DataFrame) -> pd.DataFrame:
    return data.loc[:, [*CATEGORICAL_FEATURES, *NUMERIC_FEATURES]].copy()


def align_probabilities(raw: np.ndarray, classes: np.ndarray, n_classes: int) -> np.ndarray:
    aligned = np.zeros((raw.shape[0], n_classes), dtype=np.float64)
    for source_index, class_id in enumerate(classes.astype(int)):
        aligned[:, class_id] = raw[:, source_index]
    return normalize_probabilities(aligned)


def normalize_probabilities(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=np.float64), 1e-12, 1.0)
    return clipped / clipped.sum(axis=1, keepdims=True)


def majority_probabilities(y_fit: np.ndarray, row_count: int, n_classes: int) -> np.ndarray:
    majority = int(np.bincount(y_fit, minlength=n_classes).argmax())
    probabilities = np.full((row_count, n_classes), 1e-6 / max(1, n_classes - 1), dtype=np.float64)
    probabilities[:, majority] = 1.0 - 1e-6
    return normalize_probabilities(probabilities)


def make_frequency_probabilities(
    fit_makes: pd.Series,
    y_fit: np.ndarray,
    query_makes: pd.Series,
    n_classes: int,
    *,
    alpha: float = 0.5,
) -> np.ndarray:
    global_counts = np.bincount(y_fit, minlength=n_classes).astype(float) + alpha
    global_probability = global_counts / global_counts.sum()
    tables: dict[str, np.ndarray] = {}
    normalized_fit = fit_makes.astype(str).tolist()
    for make in sorted(set(normalized_fit)):
        mask = np.fromiter((value == make for value in normalized_fit), dtype=bool, count=len(normalized_fit))
        counts = np.bincount(y_fit[mask], minlength=n_classes).astype(float) + alpha
        tables[make] = counts / counts.sum()
    return np.vstack([tables.get(str(make), global_probability) for make in query_makes.astype(str)])


def expected_calibration_error(y_true: np.ndarray, probabilities: np.ndarray, bins: int = 15) -> float:
    predictions = probabilities.argmax(axis=1)
    confidence = probabilities.max(axis=1)
    correct = predictions == y_true
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(y_true)
    ece = 0.0
    for lower, upper in zip(edges[:-1], edges[1:]):
        mask = (confidence > lower) & (confidence <= upper)
        if not mask.any():
            continue
        ece += (mask.sum() / total) * abs(float(correct[mask].mean()) - float(confidence[mask].mean()))
    return float(ece)


def classification_metrics(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, float | int]:
    probabilities = normalize_probabilities(probabilities)
    predictions = probabilities.argmax(axis=1)
    labels = np.unique(y_true)
    top_k = min(3, probabilities.shape[1])
    top_indices = np.argpartition(probabilities, -top_k, axis=1)[:, -top_k:]
    return {
        "rows": int(len(y_true)),
        "accuracy": round(float(accuracy_score(y_true, predictions)), 6),
        "macro_f1": round(float(f1_score(y_true, predictions, labels=labels, average="macro", zero_division=0)), 6),
        "log_loss": round(float(log_loss(y_true, probabilities, labels=np.arange(probabilities.shape[1]))), 6),
        "top_3_accuracy": round(float(np.mean(np.any(top_indices == y_true[:, None], axis=1))), 6),
        "expected_calibration_error": round(expected_calibration_error(y_true, probabilities), 6),
        "coverage": 1.0,
    }


def router_plan(
    y_router: np.ndarray,
    router_makes: pd.Series,
    probabilities: dict[str, np.ndarray],
    *,
    minimum_rows: int = MIN_ROUTER_ROWS,
) -> dict[str, Any]:
    model_metrics = {name: classification_metrics(y_router, values) for name, values in probabilities.items()}
    global_model = min(
        model_metrics,
        key=lambda name: (-float(model_metrics[name]["macro_f1"]), float(model_metrics[name]["log_loss"]), name),
    )
    routes: dict[str, str] = {}
    normalized_makes = router_makes.astype(str).to_numpy()
    for make, count in Counter(normalized_makes.tolist()).items():
        if count < minimum_rows:
            continue
        mask = normalized_makes == make
        group_metrics = {
            name: classification_metrics(y_router[mask], values[mask]) for name, values in probabilities.items()
        }
        routes[make] = min(
            group_metrics,
            key=lambda name: (-float(group_metrics[name]["macro_f1"]), float(group_metrics[name]["log_loss"]), name),
        )
    return {"global_model": global_model, "routes": routes, "router_window_metrics": model_metrics}


def apply_router(
    makes: pd.Series,
    probabilities: dict[str, np.ndarray],
    plan: dict[str, Any],
) -> tuple[np.ndarray, list[str]]:
    first = next(iter(probabilities.values()))
    routed = np.empty_like(first)
    chosen: list[str] = []
    for index, make in enumerate(makes.astype(str)):
        model = plan["routes"].get(make, plan["global_model"])
        routed[index] = probabilities[model][index]
        chosen.append(model)
    return normalize_probabilities(routed), chosen


def paired_macro_f1_bootstrap(
    y_true: np.ndarray,
    candidate_prediction: np.ndarray,
    baseline_prediction: np.ndarray,
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    labels = np.unique(y_true)
    label_to_position = {int(label): position for position, label in enumerate(labels)}
    n_labels = len(labels)
    rng = np.random.default_rng(seed)
    candidate_predicted = np.zeros((resamples, n_labels), dtype=np.int32)
    baseline_predicted = np.zeros((resamples, n_labels), dtype=np.int32)
    candidate_true_positive = np.zeros((resamples, n_labels), dtype=np.int32)
    baseline_true_positive = np.zeros((resamples, n_labels), dtype=np.int32)
    actual = np.zeros(n_labels, dtype=np.int32)

    for true_label in labels:
        true_position = label_to_position[int(true_label)]
        mask = y_true == true_label
        actual[true_position] = int(mask.sum())
        pairs = np.column_stack((candidate_prediction[mask], baseline_prediction[mask]))
        unique_pairs, counts = np.unique(pairs, axis=0, return_counts=True)
        draws = rng.multinomial(int(mask.sum()), counts / counts.sum(), size=resamples)
        for pair_index, (candidate_label, baseline_label) in enumerate(unique_pairs):
            sampled = draws[:, pair_index]
            if int(candidate_label) in label_to_position:
                candidate_position = label_to_position[int(candidate_label)]
                candidate_predicted[:, candidate_position] += sampled
                if int(candidate_label) == int(true_label):
                    candidate_true_positive[:, true_position] += sampled
            if int(baseline_label) in label_to_position:
                baseline_position = label_to_position[int(baseline_label)]
                baseline_predicted[:, baseline_position] += sampled
                if int(baseline_label) == int(true_label):
                    baseline_true_positive[:, true_position] += sampled

    candidate_f1 = np.divide(
        2.0 * candidate_true_positive,
        actual[None, :] + candidate_predicted,
        out=np.zeros_like(candidate_true_positive, dtype=np.float64),
        where=(actual[None, :] + candidate_predicted) > 0,
    ).mean(axis=1)
    baseline_f1 = np.divide(
        2.0 * baseline_true_positive,
        actual[None, :] + baseline_predicted,
        out=np.zeros_like(baseline_true_positive, dtype=np.float64),
        where=(actual[None, :] + baseline_predicted) > 0,
    ).mean(axis=1)
    deltas = candidate_f1 - baseline_f1
    observed = float(
        f1_score(y_true, candidate_prediction, labels=labels, average="macro", zero_division=0)
        - f1_score(y_true, baseline_prediction, labels=labels, average="macro", zero_division=0)
    )
    return {
        "observed_delta": round(observed, 6),
        "bootstrap_mean_delta": round(float(deltas.mean()), 6),
        "ci95": [round(float(np.quantile(deltas, 0.025)), 6), round(float(np.quantile(deltas, 0.975)), 6)],
        "one_sided_p_candidate_not_better": round(float((1 + np.sum(deltas <= 0.0)) / (resamples + 1)), 8),
        "resamples": resamples,
        "delta_samples": deltas,
    }


def holm_adjust(raw_p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(raw_p_values.items(), key=lambda item: (item[1], item[0]))
    total = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, value) in enumerate(ordered):
        running = max(running, min(1.0, (total - rank) * float(value)))
        adjusted[name] = round(running, 8)
    return adjusted


def fit_and_predict_models(
    fit: pd.DataFrame,
    router: pd.DataFrame,
    holdout: pd.DataFrame,
    *,
    n_classes: int,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, Any]]:
    from lightgbm import LGBMClassifier
    from xgboost import XGBClassifier

    fit_x = feature_frame(fit)
    router_x = feature_frame(router)
    holdout_x = feature_frame(holdout)
    y_fit = fit["target_id"].to_numpy(dtype=int)
    timing: dict[str, float] = {}
    router_probabilities: dict[str, np.ndarray] = {}
    holdout_probabilities: dict[str, np.ndarray] = {}

    router_probabilities["training_majority"] = majority_probabilities(y_fit, len(router), n_classes)
    holdout_probabilities["training_majority"] = majority_probabilities(y_fit, len(holdout), n_classes)
    router_probabilities["aircraft_make_frequency"] = make_frequency_probabilities(
        fit["AircraftMake"], y_fit, router["AircraftMake"], n_classes
    )
    holdout_probabilities["aircraft_make_frequency"] = make_frequency_probabilities(
        fit["AircraftMake"], y_fit, holdout["AircraftMake"], n_classes
    )

    one_hot = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore", min_frequency=20, dtype=np.float32), list(CATEGORICAL_FEATURES)),
            (
                "numeric",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler(with_mean=False)),
                    ]
                ),
                list(NUMERIC_FEATURES),
            ),
        ]
    )
    started = time.perf_counter()
    fit_one_hot = one_hot.fit_transform(fit_x)
    router_one_hot = one_hot.transform(router_x)
    holdout_one_hot = one_hot.transform(holdout_x)
    logistic = SGDClassifier(
        loss="log_loss",
        max_iter=200,
        tol=1e-4,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=8,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    logistic.fit(fit_one_hot, y_fit)
    router_probabilities["linear_logistic_sgd"] = align_probabilities(
        logistic.predict_proba(router_one_hot), logistic.classes_, n_classes
    )
    holdout_probabilities["linear_logistic_sgd"] = align_probabilities(
        logistic.predict_proba(holdout_one_hot), logistic.classes_, n_classes
    )
    timing["linear_logistic_sgd"] = round(time.perf_counter() - started, 3)

    ordinal = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1, encoded_missing_value=-1),
                list(CATEGORICAL_FEATURES),
            ),
            ("numeric", SimpleImputer(strategy="median"), list(NUMERIC_FEATURES)),
        ]
    )
    ordinal_columns = [f"feature_{index}" for index in range(len(CATEGORICAL_FEATURES) + len(NUMERIC_FEATURES))]
    fit_ordinal = pd.DataFrame(
        np.asarray(ordinal.fit_transform(fit_x), dtype=np.float32),
        columns=ordinal_columns,
    )
    router_ordinal = pd.DataFrame(
        np.asarray(ordinal.transform(router_x), dtype=np.float32),
        columns=ordinal_columns,
    )
    holdout_ordinal = pd.DataFrame(
        np.asarray(ordinal.transform(holdout_x), dtype=np.float32),
        columns=ordinal_columns,
    )

    models = {
        "random_forest": RandomForestClassifier(
            n_estimators=160,
            max_depth=24,
            min_samples_leaf=3,
            max_features="sqrt",
            n_jobs=-1,
            random_state=RANDOM_SEED,
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_iter=80,
            max_leaf_nodes=31,
            learning_rate=0.08,
            l2_regularization=0.1,
            early_stopping=True,
            random_state=RANDOM_SEED,
        ),
        "lightgbm": LGBMClassifier(
            objective="multiclass",
            n_estimators=250,
            num_leaves=31,
            learning_rate=0.07,
            subsample=0.85,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            n_jobs=-1,
            verbosity=-1,
            random_state=RANDOM_SEED,
        ),
        "xgboost": XGBClassifier(
            objective="multi:softprob",
            n_estimators=180,
            max_depth=7,
            learning_rate=0.07,
            subsample=0.85,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            tree_method="hist",
            eval_metric="mlogloss",
            n_jobs=max(1, min(12, os.cpu_count() or 1)),
            random_state=RANDOM_SEED,
        ),
    }
    for name, model in models.items():
        started = time.perf_counter()
        model.fit(fit_ordinal, y_fit)
        router_probabilities[name] = align_probabilities(model.predict_proba(router_ordinal), model.classes_, n_classes)
        holdout_probabilities[name] = align_probabilities(model.predict_proba(holdout_ordinal), model.classes_, n_classes)
        timing[name] = round(time.perf_counter() - started, 3)

    timing["feature_matrix"] = {
        "one_hot_columns": int(fit_one_hot.shape[1]),
        "ordinal_columns": int(fit_ordinal.shape[1]),
    }
    return router_probabilities, holdout_probabilities, timing


def subgroup_gate(
    holdout: pd.DataFrame,
    y_true: np.ndarray,
    candidate_probability: np.ndarray,
    baseline_probability: np.ndarray,
) -> dict[str, Any]:
    makes = holdout["AircraftMake"].astype(str).to_numpy()
    candidate_prediction = candidate_probability.argmax(axis=1)
    baseline_prediction = baseline_probability.argmax(axis=1)
    rows: list[dict[str, Any]] = []
    for make, count in Counter(makes.tolist()).items():
        if count < MIN_SUBGROUP_ROWS:
            continue
        mask = makes == make
        labels = np.unique(y_true[mask])
        candidate_f1 = float(f1_score(y_true[mask], candidate_prediction[mask], labels=labels, average="macro", zero_division=0))
        baseline_f1 = float(f1_score(y_true[mask], baseline_prediction[mask], labels=labels, average="macro", zero_division=0))
        rows.append(
            {
                "aircraft_make": make,
                "rows": int(count),
                "candidate_macro_f1": round(candidate_f1, 6),
                "baseline_macro_f1": round(baseline_f1, 6),
                "delta": round(candidate_f1 - baseline_f1, 6),
            }
        )
    rows.sort(key=lambda row: (row["delta"], row["aircraft_make"]))
    worst = rows[0]["delta"] if rows else None
    return {
        "minimum_rows": MIN_SUBGROUP_ROWS,
        "supported_subgroups": len(rows),
        "worst_delta": worst,
        "passes": worst is not None and float(worst) >= -MAX_SUBGROUP_F1_LOSS,
        "rows": rows,
    }


def is_rolls_royce(data: pd.DataFrame) -> np.ndarray:
    make = data["EngineMake"].astype(str)
    model = data["EngineModel"].astype(str)
    return (
        make.eq("RROYCE")
        | make.str.contains("ROLLS ROYCE", regex=False)
        | make.str.contains("ROLLS-ROYCE", regex=False)
        | model.str.contains(
            r"(?:^|[^A-Z0-9])(?:RB211|TRENT|AE3007|TAY6|TAYMK|BR700|BR710|BR715|BR725)",
            regex=True,
        )
    ).to_numpy()


def write_prediction_receipt(
    holdout: pd.DataFrame,
    label_encoder: LabelEncoder,
    probabilities: dict[str, np.ndarray],
    chosen_models: list[str],
) -> dict[str, Any]:
    BENCHMARK_VAULT_DIR.mkdir(parents=True, exist_ok=True)
    path = BENCHMARK_VAULT_DIR / "faa_sdr_10k_predictions.csv.gz"
    model_names = sorted(probabilities)
    fieldnames = [
        "report_key_sha256",
        "true_jasc_chapter",
        "aircraft_make",
        "rolls_royce_exploratory",
        "router_selected_model",
    ]
    for name in model_names:
        fieldnames.extend((f"{name}_prediction", f"{name}_confidence"))
    rolls_mask = is_rolls_royce(holdout)
    with path.open("wb") as compressed:
        gzip_stream = gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0)
        handle = io.TextIOWrapper(gzip_stream, encoding="utf-8", newline="")
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index in range(len(holdout)):
            row: dict[str, Any] = {
                "report_key_sha256": hashlib.sha256(holdout.iloc[index]["report_key"].encode("utf-8")).hexdigest(),
                "true_jasc_chapter": holdout.iloc[index]["target"],
                "aircraft_make": holdout.iloc[index]["AircraftMake"],
                "rolls_royce_exploratory": str(bool(rolls_mask[index])).lower(),
                "router_selected_model": chosen_models[index],
            }
            for name in model_names:
                probability = probabilities[name][index]
                prediction_id = int(probability.argmax())
                row[f"{name}_prediction"] = label_encoder.inverse_transform([prediction_id])[0]
                row[f"{name}_confidence"] = f"{float(probability.max()):.8f}"
            writer.writerow(row)
        handle.flush()
        handle.detach()
        gzip_stream.close()
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "rows": len(holdout),
        "contains_raw_report_ids": False,
    }


def build_payload(paths: Iterable[Path] | None = None) -> dict[str, Any]:
    generated = now_utc()
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    protocol_sha = sha256_file(PROTOCOL_PATH)
    if audit["ten_thousand_protocol_readiness"]["protocol_sha256"] != protocol_sha:
        raise ValueError("Source audit does not reference the current frozen protocol hash")
    if protocol["status"] != "preregistered_not_executed":
        raise ValueError("Protocol must be frozen in preregistered_not_executed state before execution")

    data = load_dataset(paths)
    split = split_dataset(data)
    fit = split["fit"]
    router = split["router"]
    holdout = split["holdout"]
    label_encoder: LabelEncoder = split["label_encoder"]
    n_classes = len(label_encoder.classes_)
    expected_selection_digest = audit["ten_thousand_protocol_readiness"]["selected_id_set_sha256"]
    if split["selected_id_set_sha256"] != expected_selection_digest:
        raise ValueError("Holdout ID digest does not match the pre-execution source audit")

    router_probabilities, holdout_probabilities, timing = fit_and_predict_models(
        fit, router, holdout, n_classes=n_classes
    )
    y_router = router["target_id"].to_numpy(dtype=int)
    y_holdout = holdout["target_id"].to_numpy(dtype=int)
    plan = router_plan(y_router, router["AircraftMake"], router_probabilities)
    candidate_probability, chosen_models = apply_router(holdout["AircraftMake"], holdout_probabilities, plan)
    all_probabilities = dict(holdout_probabilities)
    all_probabilities["hybrid_router_candidate"] = candidate_probability
    leaderboard = [
        {"model": name, **classification_metrics(y_holdout, probability), "candidate": name == "hybrid_router_candidate"}
        for name, probability in all_probabilities.items()
    ]
    leaderboard.sort(key=lambda row: (-float(row["macro_f1"]), float(row["log_loss"]), row["model"]))

    baseline_names = sorted(holdout_probabilities)
    strongest_baseline = min(
        baseline_names,
        key=lambda name: (
            -float(classification_metrics(y_holdout, holdout_probabilities[name])["macro_f1"]),
            float(classification_metrics(y_holdout, holdout_probabilities[name])["log_loss"]),
            name,
        ),
    )
    candidate_prediction = candidate_probability.argmax(axis=1)
    bootstrap_results: dict[str, Any] = {}
    raw_p_values: dict[str, float] = {}
    family_size = len(baseline_names)
    for index, name in enumerate(baseline_names):
        comparison = paired_macro_f1_bootstrap(
            y_holdout,
            candidate_prediction,
            holdout_probabilities[name].argmax(axis=1),
            resamples=BOOTSTRAP_RESAMPLES,
            seed=RANDOM_SEED + index,
        )
        delta_samples = comparison.pop("delta_samples")
        comparison["fwer95_bonferroni_ci"] = [
            round(float(np.quantile(delta_samples, 0.025 / family_size)), 6),
            round(float(np.quantile(delta_samples, 1.0 - 0.025 / family_size)), 6),
        ]
        raw_p_values[name] = float(comparison["one_sided_p_candidate_not_better"])
        bootstrap_results[name] = comparison
    adjusted = holm_adjust(raw_p_values)
    for name in bootstrap_results:
        bootstrap_results[name]["holm_adjusted_p"] = adjusted[name]

    strongest_metrics = classification_metrics(y_holdout, holdout_probabilities[strongest_baseline])
    candidate_metrics = classification_metrics(y_holdout, candidate_probability)
    subgroup = subgroup_gate(holdout, y_holdout, candidate_probability, holdout_probabilities[strongest_baseline])
    strongest_comparison = bootstrap_results[strongest_baseline]
    exact_holdout_gate = len(holdout) == HOLDOUT_TARGET and holdout["report_key"].nunique() == HOLDOUT_TARGET
    statistical_gate = (
        float(strongest_comparison["fwer95_bonferroni_ci"][0]) > 0.0
        and float(strongest_comparison["holm_adjusted_p"]) < 0.05
    )
    log_loss_gate = float(candidate_metrics["log_loss"]) <= float(strongest_metrics["log_loss"]) + NONINFERIORITY_LOG_LOSS
    promotion = bool(exact_holdout_gate and statistical_gate and log_loss_gate and subgroup["passes"])

    rolls_mask = is_rolls_royce(holdout)
    rolls_rows = int(rolls_mask.sum())
    rolls_profile: dict[str, Any] = {
        "rows": rolls_rows,
        "confirmatory": False,
        "metrics_allowed": rolls_rows > 0,
    }
    if rolls_rows:
        rolls_profile["candidate_metrics"] = classification_metrics(y_holdout[rolls_mask], candidate_probability[rolls_mask])
        rolls_profile["strongest_baseline_metrics"] = classification_metrics(
            y_holdout[rolls_mask], holdout_probabilities[strongest_baseline][rolls_mask]
        )

    prediction_receipt = write_prediction_receipt(
        holdout, label_encoder, all_probabilities, chosen_models
    )
    source_files = [Path(path) for path in (paths or discover_source_files())]
    source_receipts = [
        {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in source_files
    ]
    route_counts = Counter(chosen_models)
    package_versions = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit_learn": __import__("sklearn").__version__,
        "lightgbm": __import__("lightgbm").__version__,
        "xgboost": __import__("xgboost").__version__,
    }
    payload: dict[str, Any] = {
        "schema": "faa_sdr_10k_benchmark_v1",
        "generated_utc": generated,
        "status": "completed",
        "protocol": {
            "path": PROTOCOL_PATH.relative_to(ROOT).as_posix(),
            "sha256": protocol_sha,
            "protocol_id": PROTOCOL_ID,
            "random_seed": RANDOM_SEED,
        },
        "source_receipts": source_receipts,
        "splits": {
            "base_model_fit_rows": len(fit),
            "router_selection_rows": len(router),
            "holdout_pool_rows": int((data["date"].dt.year == 2026).sum()),
            "holdout_rows": len(holdout),
            "holdout_unique_keys": int(holdout["report_key"].nunique()),
            "holdout_id_set_sha256": split["selected_id_set_sha256"],
            "base_holdout_key_overlap": int(len(set(fit["report_key"]) & set(holdout["report_key"]))),
            "router_holdout_key_overlap": int(len(set(router["report_key"]) & set(holdout["report_key"]))),
        },
        "target": {
            "classes": label_encoder.classes_.tolist(),
            "class_count": n_classes,
            "supported_jasc_chapters": split["supported_chapters"],
            "rare_class_mapping": "OTHER",
        },
        "execution": {
            "independent_holdout_scenarios": len(holdout),
            "strategies_scored": len(all_probabilities),
            "scenario_model_evaluations": len(holdout) * len(all_probabilities),
            "paired_bootstrap_resamples_per_comparison": BOOTSTRAP_RESAMPLES,
            "paired_confirmatory_comparisons": len(baseline_names),
            "model_timing_seconds": timing,
            "package_versions": package_versions,
        },
        "router": {
            "selection_window_global_model": plan["global_model"],
            "group_route_count": len(plan["routes"]),
            "group_routes": dict(sorted(plan["routes"].items())),
            "holdout_route_counts": dict(sorted(route_counts.items())),
            "router_window_metrics": plan["router_window_metrics"],
        },
        "holdout_leaderboard": leaderboard,
        "strongest_approved_baseline": strongest_baseline,
        "paired_inference": bootstrap_results,
        "subgroup_guardrail": subgroup,
        "rolls_royce_exploratory": rolls_profile,
        "promotion_gate": {
            "exact_unique_10k_holdout": exact_holdout_gate,
            "multiplicity_adjusted_primary_improvement": statistical_gate,
            "log_loss_noninferiority": log_loss_gate,
            "supported_aircraft_make_guardrail": subgroup["passes"],
            "candidate_promoted": promotion,
        },
        "prediction_receipt": prediction_receipt,
        "claim_matrix": {
            "report_level_benchmark_completed": True,
            "ten_thousand_independent_holdout_scenarios_completed": exact_holdout_gate,
            "candidate_promoted": promotion,
            "engine_specific_validation_claim_allowed": False,
            "rolls_royce_validation_claim_allowed": False,
            "faa_validation_claim_allowed": False,
            "oem_validation_claim_allowed": False,
            "airworthiness_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "economic_savings_claim_allowed": False,
        },
        "claim_boundary": CLAIM_BOUNDARY,
    }
    payload["receipt_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    execution = payload["execution"]
    splits = payload["splits"]
    gate = payload["promotion_gate"]
    lines = [
        "# FAA SDR Frozen 10,000-Scenario Benchmark",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Result",
        "",
        f"- Independent frozen holdout reports: `{execution['independent_holdout_scenarios']:,}`.",
        f"- Strategies scored per report: `{execution['strategies_scored']}`.",
        f"- Scenario-model evaluations: `{execution['scenario_model_evaluations']:,}`.",
        f"- Holdout unique keys: `{splits['holdout_unique_keys']:,}`; development overlap: `{splits['base_holdout_key_overlap']}`.",
        f"- Strongest approved baseline: `{payload['strongest_approved_baseline']}`.",
        f"- Candidate promoted: `{str(gate['candidate_promoted']).lower()}`.",
        "",
        "## Holdout Leaderboard",
        "",
        "| Model | Candidate | Macro F1 | Log loss | Top-3 accuracy | ECE |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in payload["holdout_leaderboard"]:
        lines.append(
            f"| {row['model']} | {str(row['candidate']).lower()} | {row['macro_f1']:.6f} | "
            f"{row['log_loss']:.6f} | {row['top_3_accuracy']:.6f} | {row['expected_calibration_error']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Promotion Gate",
            "",
            f"- Exact unique 10,000 holdout: `{str(gate['exact_unique_10k_holdout']).lower()}`.",
            f"- Multiplicity-adjusted primary improvement: `{str(gate['multiplicity_adjusted_primary_improvement']).lower()}`.",
            f"- Log-loss noninferiority: `{str(gate['log_loss_noninferiority']).lower()}`.",
            f"- Supported aircraft-make guardrail: `{str(gate['supported_aircraft_make_guardrail']).lower()}`.",
            f"- Final candidate promotion: `{str(gate['candidate_promoted']).lower()}`.",
            "",
            "Every non-win remains part of the evidence record; run volume does not override the declared gates.",
            "",
            "## Rolls-Royce Exploratory Slice",
            "",
            f"The frozen holdout contains `{payload['rolls_royce_exploratory']['rows']}` rows matching the transparent "
            "Rolls-Royce-family rule. This count is descriptive and is not a confirmatory OEM or engine-health study.",
            "",
            "## Reproducibility",
            "",
            f"- Protocol SHA-256: `{payload['protocol']['sha256']}`.",
            f"- Holdout ID-set SHA-256: `{splits['holdout_id_set_sha256']}`.",
            f"- Prediction file SHA-256: `{payload['prediction_receipt']['sha256']}`.",
            f"- Receipt SHA-256: `{payload['receipt_sha256']}`.",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
        ]
    )
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    BENCHMARK_VAULT_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("JOBLIB_TEMP_FOLDER", str(BENCHMARK_VAULT_DIR / "joblib_tmp"))
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(OUT_JSON),
                "scenario_model_evaluations": payload["execution"]["scenario_model_evaluations"],
                "strongest_baseline": payload["strongest_approved_baseline"],
                "promotion_gate": payload["promotion_gate"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
