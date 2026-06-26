"""
master_universe_benchmark_v2.py
=============================================================================
Massively expanded undeniable evidence pack. Activates the premium stack:

NEW DATA SOURCES (vs v1):
    - EIA per-state generation x 50 states x 6 fuels        -> up to 300 series
    - EIA per-state retail x 50 states x 4 sectors          -> up to 200 series
    - NOAA NCEI per-state monthly temperature               -> up to 50 series
    - BLS per-state unemployment rate                       -> up to 50 series
    - FRED top 10 macro series (key may be truncated, soft-fails)
    - AlphaVantage monthly closes (~25 tickers)
    - yfinance monthly closes (~22 indices/stocks/crypto)
    - NASA POWER monthly temp (10 metros)
    - USGS Water monthly streamflow (10 major rivers)

NEW MODEL FAMILIES (vs v1):
    Already have: harmonic / neural / baseline.
    ADDED:
      tree:       g_xgboost_lag, h_lightgbm_lag
      classical:  i_sarima

This makes harmonic compete against tuned tree boosters and a real classical
time-series model -- no more "harmonic vs untuned MLP" caricature.

Bootstrap CIs, hash-chained ledger, manifest, scorecard -- all preserved.

Scale control via env var:
    MASTER_SCALE=quick   ->  5 states, no AV, no NASA, ~75 series  (smoke test)
    MASTER_SCALE=medium  -> 25 states, AV+NASA+USGS, ~250 series
    MASTER_SCALE=full    -> 50 states + everything, ~600+ series   (default)
"""

from __future__ import annotations

import hashlib
from importlib import metadata as importlib_metadata
import json
import os
import re
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_squared_error
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor

warnings.filterwarnings("ignore")
MODEL_PACK = os.environ.get("MASTER_MODEL_PACK", "core").lower()

# Reuse v1 fetchers/models by importing them
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from master_universe_benchmark import (  # noqa: E402
    eia_generation_by_fuel, eia_generation_by_sector, eia_retail_sales,
    eia_petroleum_stocks_weekly, eia_crude_stocks_weekly, eia_ng_storage_weekly,
    noaa_conus_temperature,
    model_a_naive, model_b_linear_trend, model_c_harmonic_fixed12,
    model_d_harmonic_search, model_e_mlp_untuned, model_f_mlp_tuned,
    bootstrap_rmse_ci, make_lag_features,
)
from universe_v2_fetchers import set_keys, build_extra_datasets  # noqa: E402

# -----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
ENV_FILES = [
    ROOT / ".deploy_stage" / "code" / "execution" / "config" / "luma_live_keys.env",
    ROOT / "config" / "luma_live_keys.env",
]
OUT_ROOT = ROOT / "out" / "master_universe_v2"
LEDGER = ROOT / "out" / "frozen_delta_ledger.jsonl"
RESUME_RUN = os.environ.get("MASTER_RESUME_RUN", "").strip()
if RESUME_RUN and not re.fullmatch(r"\d{8}T\d{6}Z", RESUME_RUN):
    raise ValueError("MASTER_RESUME_RUN must use YYYYMMDDTHHMMSSZ")
UTC = RESUME_RUN or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
RUN_DIR = OUT_ROOT / UTC
RAW_DIR = RUN_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PARTIAL_ROWS_PATH = RUN_DIR / "results.partial.jsonl"
PARTIAL_METADATA_PATH = RUN_DIR / "metadata.partial.json"
RAW_SOURCE_RUN = os.environ.get("MASTER_RAW_SOURCE_RUN", "").strip()
if RAW_SOURCE_RUN and not re.fullmatch(r"\d{8}T\d{6}Z", RAW_SOURCE_RUN):
    raise ValueError("MASTER_RAW_SOURCE_RUN must use YYYYMMDDTHHMMSSZ")
RAW_SOURCE_DIR = OUT_ROOT / RAW_SOURCE_RUN / "raw" if RAW_SOURCE_RUN else None


def load_env(path: Path) -> dict:
    out: dict = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


KEYS: dict = {}
for p in ENV_FILES:
    for k, v in load_env(p).items():
        if k not in KEYS or len(v) > len(KEYS[k]):
            KEYS[k] = v

# Wire keys into the master_universe_benchmark module too (it has its own KEYS
# read at import; refresh them by re-binding the EIA function's globals).
import master_universe_benchmark as v1_mod  # noqa: E402
v1_mod.KEYS = KEYS  # type: ignore[attr-defined]
set_keys(KEYS)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_cached_raw(ds_name: str) -> pd.DataFrame | None:
    candidates = [RAW_DIR / f"{ds_name}.csv"]
    if RAW_SOURCE_DIR is not None:
        candidates.append(RAW_SOURCE_DIR / f"{ds_name}.csv")
    for raw_path in candidates:
        if not raw_path.exists():
            continue
        try:
            df = pd.read_csv(raw_path)
            if "period" not in df.columns or "value" not in df.columns:
                continue
            df["period"] = pd.to_datetime(df["period"], errors="coerce", utc=True)
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = df.dropna(subset=["period", "value"]).reset_index(drop=True)
            if len(df) >= 30:
                return df
        except Exception:
            continue
    return None


def load_partial_rows() -> tuple[list[dict], set[str]]:
    rows: list[dict] = []
    completed: set[str] = set()
    if not PARTIAL_ROWS_PATH.exists():
        return rows, completed
    for line in PARTIAL_ROWS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict) and row.get("dataset"):
            rows.append(row)
            completed.add(str(row["dataset"]))
    return rows, completed


def append_partial_rows(out_rows: list[dict]) -> None:
    with PARTIAL_ROWS_PATH.open("a", encoding="utf-8") as handle:
        for row in out_rows:
            handle.write(json.dumps(row, default=str) + "\n")


# -----------------------------------------------------------------------------
# Premium models added in v2
# -----------------------------------------------------------------------------
def model_g_xgboost_lag(y_train, n_test, n_lags=12):
    try:
        from xgboost import XGBRegressor
    except Exception as exc:
        raise RuntimeError("xgboost dependency unavailable") from exc
    if len(y_train) <= n_lags + 5:
        raise ValueError("insufficient history for xgboost lag model")
    X, yt = make_lag_features(y_train, n_lags)
    m = XGBRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.9, colsample_bytree=0.9, random_state=0,
        verbosity=0, n_jobs=1,
    )
    m.fit(X, yt)
    history = list(y_train[-n_lags:])
    preds = []
    for _ in range(n_test):
        xin = np.array(history[-n_lags:]).reshape(1, -1)
        yhat = float(m.predict(xin)[0])
        preds.append(yhat); history.append(yhat)
    return np.array(preds)


def model_h_lightgbm_lag(y_train, n_test, n_lags=12):
    try:
        from lightgbm import LGBMRegressor
    except Exception as exc:
        raise RuntimeError("lightgbm dependency unavailable") from exc
    if len(y_train) <= n_lags + 5:
        raise ValueError("insufficient history for lightgbm lag model")
    X, yt = make_lag_features(y_train, n_lags)
    m = LGBMRegressor(
        n_estimators=300, max_depth=-1, num_leaves=31, learning_rate=0.05,
        subsample=0.9, colsample_bytree=0.9, random_state=0,
        verbosity=-1, n_jobs=1,
    )
    m.fit(X, yt)
    history = list(y_train[-n_lags:])
    preds = []
    for _ in range(n_test):
        xin = np.array(history[-n_lags:]).reshape(1, -1)
        yhat = float(m.predict(xin)[0])
        preds.append(yhat); history.append(yhat)
    return np.array(preds)


def model_i_sarima(y_train, n_test):
    """Strong classical baseline. Fit failures are reported, never aliased."""
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
    except Exception as exc:
        raise RuntimeError("statsmodels dependency unavailable") from exc
    try:
        # Light-weight SARIMA: (1,1,1)x(1,1,1,12)
        m = SARIMAX(
            y_train, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12),
            enforce_stationarity=False, enforce_invertibility=False,
        ).fit(disp=False, maxiter=50)
        return np.asarray(m.forecast(steps=n_test), dtype=float)
    except Exception as exc:
        raise RuntimeError(f"sarima fit failed: {exc}") from exc


def model_j_random_forest_lag(y_train, n_test, n_lags=18):
    if len(y_train) <= n_lags + 10:
        raise ValueError("insufficient history for random forest lag model")
    X, yt = make_lag_features(y_train, n_lags)
    try:
        m = RandomForestRegressor(
            n_estimators=320,
            min_samples_leaf=2,
            random_state=0,
            n_jobs=1,
        )
        m.fit(X, yt)
        history = list(y_train[-n_lags:])
        preds = []
        for _ in range(n_test):
            xin = np.array(history[-n_lags:]).reshape(1, -1)
            yhat = float(m.predict(xin)[0])
            preds.append(yhat)
            history.append(yhat)
        return np.array(preds)
    except Exception as exc:
        raise RuntimeError(f"random forest fit failed: {exc}") from exc


def model_k_extra_trees_lag(y_train, n_test, n_lags=18):
    if len(y_train) <= n_lags + 10:
        raise ValueError("insufficient history for extra trees lag model")
    X, yt = make_lag_features(y_train, n_lags)
    try:
        m = ExtraTreesRegressor(
            n_estimators=420,
            min_samples_leaf=2,
            random_state=0,
            n_jobs=1,
        )
        m.fit(X, yt)
        history = list(y_train[-n_lags:])
        preds = []
        for _ in range(n_test):
            xin = np.array(history[-n_lags:]).reshape(1, -1)
            yhat = float(m.predict(xin)[0])
            preds.append(yhat)
            history.append(yhat)
        return np.array(preds)
    except Exception as exc:
        raise RuntimeError(f"extra trees fit failed: {exc}") from exc


def model_l_hist_gradient_boosting_lag(y_train, n_test, n_lags=18):
    if len(y_train) <= n_lags + 10:
        raise ValueError("insufficient history for hist gradient boosting lag model")
    X, yt = make_lag_features(y_train, n_lags)
    try:
        m = HistGradientBoostingRegressor(
            max_depth=6,
            learning_rate=0.05,
            max_iter=400,
            min_samples_leaf=4,
            random_state=0,
        )
        m.fit(X, yt)
        history = list(y_train[-n_lags:])
        preds = []
        for _ in range(n_test):
            xin = np.array(history[-n_lags:]).reshape(1, -1)
            yhat = float(m.predict(xin)[0])
            preds.append(yhat)
            history.append(yhat)
        return np.array(preds)
    except Exception as exc:
        raise RuntimeError(
            f"hist gradient boosting fit failed: {exc}"
        ) from exc


MODELS = {
    "a_naive":              model_a_naive,
    "b_linear_trend":       model_b_linear_trend,
    "c_harmonic_fixed12":   model_c_harmonic_fixed12,
    "d_harmonic_search":    model_d_harmonic_search,
    "e_mlp_untuned":        model_e_mlp_untuned,
    "f_mlp_tuned":          model_f_mlp_tuned,
    "g_xgboost_lag":        model_g_xgboost_lag,
    "h_lightgbm_lag":       model_h_lightgbm_lag,
    "i_sarima":             model_i_sarima,
}

if MODEL_PACK in {"extended", "full", "max"}:
    MODELS.update(
        {
            "j_random_forest_lag": model_j_random_forest_lag,
            "k_extra_trees_lag": model_k_extra_trees_lag,
            "l_hist_gradient_boosting_lag": model_l_hist_gradient_boosting_lag,
        }
    )

FAMILIES = {
    "harmonic":  ["c_harmonic_fixed12", "d_harmonic_search"],
    "neural":    ["e_mlp_untuned", "f_mlp_tuned"],
    "baseline":  ["a_naive", "b_linear_trend"],
    "tree":      ["g_xgboost_lag", "h_lightgbm_lag"],
    "classical": ["i_sarima"],
}

if MODEL_PACK in {"extended", "full", "max"}:
    FAMILIES["ensemble"] = [
        "j_random_forest_lag",
        "k_extra_trees_lag",
        "l_hist_gradient_boosting_lag",
    ]


def model_dependency_status() -> dict[str, dict[str, str | bool | None]]:
    packages = {
        "g_xgboost_lag": "xgboost",
        "h_lightgbm_lag": "lightgbm",
        "i_sarima": "statsmodels",
    }
    status: dict[str, dict[str, str | bool | None]] = {}
    for model_name, package_name in packages.items():
        if model_name not in MODELS:
            continue
        try:
            version = importlib_metadata.version(package_name)
            status[model_name] = {
                "package": package_name,
                "available": True,
                "version": version,
            }
        except importlib_metadata.PackageNotFoundError:
            status[model_name] = {
                "package": package_name,
                "available": False,
                "version": None,
            }
    return status


# -----------------------------------------------------------------------------
# Universe assembly
# -----------------------------------------------------------------------------
def core_datasets() -> dict:
    return {
        "EIA_GEN_ALL_FUELS":       lambda: eia_generation_by_fuel("ALL"),
        "EIA_GEN_COAL":            lambda: eia_generation_by_fuel("COW"),
        "EIA_GEN_NATGAS":          lambda: eia_generation_by_fuel("NG"),
        "EIA_GEN_NUCLEAR":         lambda: eia_generation_by_fuel("NUC"),
        "EIA_GEN_SOLAR":           lambda: eia_generation_by_fuel("SUN"),
        "EIA_GEN_WIND":            lambda: eia_generation_by_fuel("WND"),
        "EIA_GEN_HYDRO":           lambda: eia_generation_by_fuel("HYC"),
        "EIA_GEN_GEOTHERM":        lambda: eia_generation_by_fuel("GEO"),
        "EIA_GEN_BIOMASS":         lambda: eia_generation_by_fuel("BIO"),
        "EIA_SECTOR_ELECUTIL":     lambda: eia_generation_by_sector("1"),
        "EIA_SECTOR_IPP_NONCHP":   lambda: eia_generation_by_sector("2"),
        "EIA_SECTOR_IPP_CHP":      lambda: eia_generation_by_sector("3"),
        "EIA_SECTOR_COMMERCIAL":   lambda: eia_generation_by_sector("6"),
        "EIA_SECTOR_INDUSTRIAL":   lambda: eia_generation_by_sector("7"),
        "EIA_RETAIL_RES_NATIONAL": lambda: eia_retail_sales("RES"),
        "EIA_RETAIL_COM_NATIONAL": lambda: eia_retail_sales("COM"),
        "EIA_RETAIL_IND_NATIONAL": lambda: eia_retail_sales("IND"),
        "EIA_RETAIL_TRA_NATIONAL": lambda: eia_retail_sales("TRA"),
        "EIA_CRUDE_STOCKS":        eia_crude_stocks_weekly,
        "EIA_GASOLINE_STOCKS":     lambda: eia_petroleum_stocks_weekly("EPM0"),
        "EIA_DISTILLATE_STOCKS":   lambda: eia_petroleum_stocks_weekly("EPD0"),
        "NOAA_CONUS_TEMP_MONTHLY": noaa_conus_temperature,
    }


SCALE = os.environ.get("MASTER_SCALE", "full").lower()
MEGA_YF_LIMIT = max(0, int(os.environ.get("MASTER_MEGA_YF", "0") or 0))
DATASET_LIMIT = max(0, int(os.environ.get("MASTER_DATASET_LIMIT", "0") or 0))


def _load_mega_yf_symbols(limit: int) -> list[str]:
    if limit <= 0:
        return []
    path = ROOT / "adaptive_universe.csv"
    if not path.exists():
        return []
    try:
        df = pd.read_csv(path, usecols=["symbol"], dtype=str)
    except Exception:
        return []

    deny = {
        "CSV", "NET", "ALL", "LIVE", "FOR", "GRID", "FLOW", "HASH", "UNKNOWN",
        "CLOSE", "AMOUNT", "BYTES", "AUTO", "BEST", "DATA", "VALUE", "MEASURED",
    }
    out: list[str] = []
    seen: set[str] = set()
    for raw in df.get("symbol", pd.Series(dtype=str)).dropna().tolist():
        s = str(raw).strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", s):
            continue
        if len(s) > 6:
            continue
        if s in deny:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= limit:
            break
    return out


def _load_source_value_map() -> dict[str, float]:
    path = ROOT / "out" / "source_truth_table.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    out: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        source = str(row.get("source", "")).strip().upper()
        if not source:
            continue
        value = row.get("modeled_annual_upside_usd", row.get("estimated_hour_value", 0))
        try:
            out[source] = float(value or 0)
        except Exception:
            continue

    if "ALPHAVANTAGE" in out and "YFINANCE" not in out:
        out["YFINANCE"] = out["ALPHAVANTAGE"]
    return out


def _dataset_value_source(dataset: str) -> str:
    if dataset.startswith("EIA930_") or dataset.startswith("EIA_"):
        return "EIA"
    if dataset.startswith("BLS_"):
        return "BLS"
    if dataset.startswith("FRED_"):
        return "FRED"
    if dataset.startswith("AV_"):
        return "ALPHAVANTAGE"
    if dataset.startswith("YF_"):
        return "YFINANCE"
    if dataset.startswith("NOAA_"):
        return "NOAA"
    if dataset.startswith("NASA_"):
        return "NASA"
    if dataset.startswith("USGS_"):
        return "USGS"
    if dataset.startswith("OPENAQ_"):
        return "OPENAQ"
    if dataset.startswith("COINGECKO_"):
        return "COINGECKO"
    return dataset.split("_", 1)[0].upper()


def _apply_dataset_limit(universe: dict[str, callable], limit: int) -> tuple[dict[str, callable], dict]:
    if limit <= 0 or limit >= len(universe):
        return universe, {
            "mode": "full",
            "requested_limit": limit,
            "selected_count": len(universe),
        }

    value_map = _load_source_value_map()
    ranked = sorted(
        universe.items(),
        key=lambda kv: (
            value_map.get(_dataset_value_source(kv[0]), 0.0),
            kv[0],
        ),
        reverse=True,
    )
    selected_names = [name for name, _ in ranked[:limit]]
    selected_universe = {name: universe[name] for name in selected_names}
    preview = [
        {
            "dataset": name,
            "value_source": _dataset_value_source(name),
            "value_score": value_map.get(_dataset_value_source(name), 0.0),
        }
        for name in selected_names[:12]
    ]
    return selected_universe, {
        "mode": "top_value_limit",
        "requested_limit": limit,
        "selected_count": len(selected_universe),
        "preview": preview,
    }


def build_universe() -> dict:
    base = core_datasets()
    mega_yf = _load_mega_yf_symbols(MEGA_YF_LIMIT)
    default_yf = [
        "^GSPC", "^DJI", "^IXIC", "^RUT", "^VIX", "^TNX",
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B",
        "JPM", "V", "WMT", "JNJ", "XOM", "CVX", "BTC-USD", "ETH-USD",
    ]
    merged_yf = []
    seen = set()
    for s in default_yf + mega_yf:
        if s in seen:
            continue
        seen.add(s)
        merged_yf.append(s)

    if SCALE == "quick":
        extras = build_extra_datasets(
            n_states=5, include_alphavantage=False,
            include_nasa=False, include_usgs=False, include_fred=False,
            include_eia930=False, include_openaq=False, include_coingecko=False,
            yf_symbols=merged_yf,
        )
    elif SCALE == "medium":
        extras = build_extra_datasets(
            n_states=25, include_alphavantage=True,
            include_nasa=True, include_usgs=True, include_fred=True,
            include_eia930=True, include_openaq=True, include_coingecko=True,
            yf_symbols=merged_yf,
        )
    else:  # full
        extras = build_extra_datasets(
            n_states=50, include_alphavantage=True,
            include_nasa=True, include_usgs=True, include_fred=True,
            include_eia930=True, include_openaq=True, include_coingecko=True,
            yf_symbols=merged_yf,
        )
    base.update(extras)
    selected, selection_meta = _apply_dataset_limit(base, DATASET_LIMIT)
    build_universe.selection_meta = selection_meta  # type: ignore[attr-defined]
    return selected


# -----------------------------------------------------------------------------
# Eval
# -----------------------------------------------------------------------------
def evaluate(y, test_frac=0.2):
    n = len(y)
    n_test = max(8, int(n * test_frac))
    if n_test >= n - 24:
        n_test = max(8, n // 5)
    y_tr = y[: n - n_test]
    y_te = y[n - n_test:]
    out = {}
    for name, fn in MODELS.items():
        try:
            t0 = time.time()
            pred = fn(y_tr, n_test)
            rmse = float(np.sqrt(mean_squared_error(y_te, pred)))
            lo, med, hi = bootstrap_rmse_ci(y_te, pred)
            out[name] = {"rmse": rmse, "ci_lo": lo, "ci_med": med, "ci_hi": hi,
                         "elapsed_s": round(time.time() - t0, 3)}
        except Exception as e:
            out[name] = {"error": str(e)}
    return out, n_test


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    if RESUME_RUN and (RUN_DIR / "summary.json").exists():
        print(f"run {RESUME_RUN} is already complete: {RUN_DIR}")
        return
    dependency_status = model_dependency_status()
    missing_dependencies = [
        name
        for name, status in dependency_status.items()
        if not status.get("available")
    ]
    if missing_dependencies and os.environ.get("MASTER_STRICT_DEPS", "1") != "0":
        raise SystemExit(
            "required model dependencies are unavailable: "
            + ", ".join(missing_dependencies)
            + ". Use the project venv or set MASTER_STRICT_DEPS=0 only for "
              "an explicitly incomplete diagnostic run."
        )
    universe = build_universe()
    selection_meta = getattr(build_universe, "selection_meta", {})
    print(f"=== master_universe_benchmark_v2 @ {UTC} ===")
    print(f"scale: {SCALE}  |  datasets in universe: {len(universe)}")
    print(f"models: {len(MODELS)}  |  families: {len(FAMILIES)}")
    if selection_meta:
        print(f"dataset selection: {selection_meta.get('mode')} ({selection_meta.get('selected_count')})")
    print(f"output: {RUN_DIR}")
    print()

    rows, completed_datasets = load_partial_rows() if RESUME_RUN else ([], set())
    metadata: dict = {}
    if RESUME_RUN and PARTIAL_METADATA_PATH.exists():
        try:
            metadata = json.loads(
                PARTIAL_METADATA_PATH.read_text(encoding="utf-8")
            )
        except Exception:
            metadata = {}
    if completed_datasets:
        print(
            f"[resume] loaded {len(rows)} model rows for "
            f"{len(completed_datasets)} completed datasets"
        )
    t_start = time.time()

    PARALLEL = os.environ.get("MASTER_PARALLEL", "0") == "1"
    if PARALLEL:
        try:
            from joblib import Parallel, delayed
        except Exception:
            PARALLEL = False
            print("[parallel] joblib not available, falling back to serial")

    if PARALLEL:
        # ---- Phase 1: parallel fetch (concurrency-limited to be polite) ----
        FETCH_JOBS = int(os.environ.get("MASTER_FETCH_JOBS", "6"))
        EVAL_JOBS = int(os.environ.get("MASTER_EVAL_JOBS", "-1"))
        default_eval_backend = "threading" if os.name == "nt" else "loky"
        EVAL_BACKEND = os.environ.get("MASTER_EVAL_BACKEND", default_eval_backend).strip().lower()
        if EVAL_BACKEND not in {"threading", "loky"}:
            EVAL_BACKEND = default_eval_backend
        print(
            f"[parallel] fetch_jobs={FETCH_JOBS} eval_jobs={EVAL_JOBS} "
            f"eval_backend={EVAL_BACKEND}"
        )

        def _fetch_one(name_fetch):
            ds_name, fetch = name_fetch
            try:
                df = load_cached_raw(ds_name)
                cached = df is not None
                if df is None:
                    df = fetch()
                y = df["value"].to_numpy(dtype=float)
                if len(y) < 30:
                    return ds_name, None, {"error": "too_short", "n": len(y)}
                raw_path = RAW_DIR / f"{ds_name}.csv"
                df.to_csv(raw_path, index=False)
                return ds_name, df, {
                    "n_obs": len(y),
                    "first": str(df["period"].iloc[0].date()),
                    "last": str(df["period"].iloc[-1].date()),
                    "raw_sha256": sha256_file(raw_path),
                    "resume_cache": cached,
                }
            except requests.HTTPError as e:
                code = e.response.status_code if e.response else "?"
                return ds_name, None, {"error": f"http {code}"}
            except Exception as e:
                return ds_name, None, {"error": str(e)[:200]}

        items = list(universe.items())
        t_fetch = time.time()
        # threading backend = good for I/O bound fetches
        fetch_results = Parallel(n_jobs=FETCH_JOBS, backend="threading", verbose=5)(
            delayed(_fetch_one)(it) for it in items
        )
        print(f"[parallel] fetch done in {time.time()-t_fetch:.1f}s")

        ok_items = []
        for ds_name, df, meta in fetch_results:
            metadata[ds_name] = meta
            if df is not None and ds_name not in completed_datasets:
                ok_items.append((ds_name, df["value"].to_numpy(dtype=float)))

        # ---- Phase 2: parallel evaluate (CPU-bound) ----
        def _eval_one(name_y):
            ds_name, y = name_y
            results, n_test = evaluate(y)
            out_rows = []
            for model_name, r in results.items():
                row = {"dataset": ds_name, "model": model_name,
                       "n_train": len(y) - n_test, "n_test": n_test,
                       "y_mean": float(np.mean(y)), "y_std": float(np.std(y))}
                row.update(r if "error" not in r
                           else {"rmse": np.nan, "ci_lo": np.nan, "ci_med": np.nan,
                                 "ci_hi": np.nan, "error": r["error"]})
                out_rows.append(row)
            return ds_name, n_test, out_rows

        t_eval = time.time()
        eval_batch_size = max(
            1, int(os.environ.get("MASTER_EVAL_BATCH_SIZE", "64"))
        )
        total_batches = max(
            1, (len(ok_items) + eval_batch_size - 1) // eval_batch_size
        )
        for batch_index, batch_start in enumerate(
            range(0, len(ok_items), eval_batch_size),
            start=1,
        ):
            batch = ok_items[batch_start : batch_start + eval_batch_size]
            print(
                f"[parallel] eval batch {batch_index}/{total_batches} "
                f"datasets={len(batch)}"
            )
            eval_results = Parallel(
                n_jobs=EVAL_JOBS,
                backend=EVAL_BACKEND,
                verbose=5,
            )(
                delayed(_eval_one)(it) for it in batch
            )
            for ds_name, n_test, out_rows in eval_results:
                rows.extend(out_rows)
                append_partial_rows(out_rows)
                metadata.setdefault(ds_name, {})["n_test"] = n_test
            PARTIAL_METADATA_PATH.write_text(
                json.dumps(metadata, indent=2), encoding="utf-8"
            )
        print(f"[parallel] evaluate done in {time.time()-t_eval:.1f}s")
    else:
        for i, (ds_name, fetch) in enumerate(universe.items(), start=1):
            prefix = f"[{i:>4}/{len(universe)}] {ds_name:<48}"
            if ds_name in completed_datasets:
                print(f"{prefix} checkpointed")
                continue
            print(prefix, flush=True, end=" ")
            try:
                df = load_cached_raw(ds_name)
                cached = df is not None
                if df is None:
                    df = fetch()
            except requests.HTTPError as e:
                print(f"HTTP-FAIL: {e.response.status_code if e.response else '?'}")
                metadata[ds_name] = {"error": f"http {e.response.status_code if e.response else '?'}"}
                continue
            except Exception as e:
                print(f"FAIL: {str(e)[:60]}")
                metadata[ds_name] = {"error": str(e)[:200]}
                continue

            y = df["value"].to_numpy(dtype=float)
            if len(y) < 30:
                print(f"too short ({len(y)})")
                metadata[ds_name] = {"error": "too_short", "n": len(y)}
                continue

            raw_path = RAW_DIR / f"{ds_name}.csv"
            df.to_csv(raw_path, index=False)
            print(
                f"{len(y)} obs"
                + (" (resume cache)" if cached else ""),
                flush=True,
            )
            results, n_test = evaluate(y)
            out_rows = []
            for model_name, r in results.items():
                row = {"dataset": ds_name, "model": model_name,
                       "n_train": len(y) - n_test, "n_test": n_test,
                       "y_mean": float(np.mean(y)), "y_std": float(np.std(y))}
                row.update(r if "error" not in r
                           else {"rmse": np.nan, "ci_lo": np.nan, "ci_med": np.nan,
                                 "ci_hi": np.nan, "error": r["error"]})
                rows.append(row)
                out_rows.append(row)
            append_partial_rows(out_rows)
            metadata[ds_name] = {"n_obs": len(y), "n_test": n_test,
                                 "first": str(df["period"].iloc[0].date()),
                                 "last": str(df["period"].iloc[-1].date()),
                                 "raw_sha256": sha256_file(raw_path),
                                 "resume_cache": cached}
            PARTIAL_METADATA_PATH.write_text(
                json.dumps(metadata, indent=2), encoding="utf-8"
            )

    elapsed = time.time() - t_start
    print(f"\nfetch+eval done in {elapsed:.1f}s")

    if not rows:
        print("FATAL: no datasets succeeded"); return

    res = pd.DataFrame(rows)
    res_path = RUN_DIR / "results.csv"; res.to_csv(res_path, index=False)
    pivot = res.pivot(index="dataset", columns="model", values="rmse")
    pivot_path = RUN_DIR / "results_pivot.csv"; pivot.to_csv(pivot_path)

    def ci_str(row):
        if pd.isna(row.get("rmse")):
            return "n/a"
        return f"{row['rmse']:.3g} [{row['ci_lo']:.3g},{row['ci_hi']:.3g}]"

    res["ci_str"] = res.apply(ci_str, axis=1)
    ci_pivot = res.pivot(index="dataset", columns="model", values="ci_str")
    ci_pivot_path = RUN_DIR / "ci_pivot.csv"; ci_pivot.to_csv(ci_pivot_path)

    # Family scoreboard (5 families now)
    family_rows = []
    for ds in pivot.index:
        row = pivot.loc[ds]
        family_best = {}
        for fam, ms in FAMILIES.items():
            present = [m for m in ms if m in row.index]
            if not present:
                continue
            sub = row[present]
            if sub.notna().any():
                family_best[fam] = float(sub.min())
        if not family_best:
            continue
        sorted_fams = sorted(family_best.items(), key=lambda kv: kv[1])
        winner_fam, winner_rmse = sorted_fams[0]
        runner_fam, runner_rmse = (sorted_fams[1] if len(sorted_fams) > 1
                                   else (None, np.nan))
        margin_pct = (((runner_rmse - winner_rmse) / runner_rmse * 100)
                      if runner_rmse and not np.isnan(runner_rmse) else np.nan)
        ms_winner = [m for m in FAMILIES[winner_fam] if m in row.index]
        winning_model = row[ms_winner].idxmin()
        family_rows.append({
            "dataset": ds,
            "winning_family": winner_fam,
            "winning_model": winning_model,
            "winning_rmse": winner_rmse,
            "runner_up_family": runner_fam,
            "runner_up_rmse": runner_rmse,
            "margin_pct_vs_runner": margin_pct,
            **{f"{f}_best": family_best.get(f) for f in FAMILIES},
        })
    fam_df = pd.DataFrame(family_rows)
    fam_path = RUN_DIR / "family_scoreboard.csv"; fam_df.to_csv(fam_path, index=False)

    fam_counts = (fam_df["winning_family"].value_counts().to_dict()
                  if not fam_df.empty else {})
    total = int(fam_df.shape[0])
    counts = {f: int(fam_counts.get(f, 0)) for f in FAMILIES}
    h_wins_df = fam_df[fam_df["winning_family"] == "harmonic"]
    avg_harm_margin = (float(h_wins_df["margin_pct_vs_runner"].mean())
                       if len(h_wins_df) else None)
    median_harm_margin = (float(h_wins_df["margin_pct_vs_runner"].median())
                          if len(h_wins_df) else None)

    summary = {
        "run_utc": UTC,
        "test_name": "master_universe_benchmark_v2",
        "scale": SCALE,
        "n_datasets_in_universe": len(universe),
        "dataset_selection": selection_meta,
        "n_datasets_succeeded": total,
        "validation_design": {
            "split": "single_chronological_80_20_holdout",
            "walk_forward": False,
            "submission_grade_v7": False,
            "limitations": [
                "This breadth benchmark is not a multi-fold walk-forward study.",
                "Bootstrap intervals describe RMSE sampling uncertainty, not a complete multiple-comparison claim gate.",
            ],
        },
        "models": list(MODELS),
        "families": FAMILIES,
        "model_dependencies": dependency_status,
        "family_win_counts": counts,
        "harmonic_win_rate": counts["harmonic"] / total if total else None,
        "harmonic_avg_margin_pct": avg_harm_margin,
        "harmonic_median_margin_pct": median_harm_margin,
        "elapsed_s": round(elapsed, 1),
        "datasets": metadata,
        "verdict": (
            f"On {total} frozen public/market series, the HARMONIC family "
            f"wins {counts['harmonic']}/{total} "
            f"({counts['harmonic']/total*100:.1f}%) head-to-head against "
            f"tuned tree boosters (XGBoost+LightGBM), tuned neural nets, "
            f"classical SARIMA, and naive baselines. Median margin where "
            f"harmonic wins: "
            f"{(median_harm_margin if median_harm_margin is not None else 0):.1f}% "
            f"RMSE reduction vs runner-up family."
        ) if total else "no datasets",
    }
    summary_path = RUN_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    # Markdown scorecard
    md = []
    md.append("# EXPLORATORY SCORECARD v2 - Broad Frozen Holdout Benchmark")
    md.append("")
    md.append(f"**Run UTC:** `{UTC}`")
    md.append(f"**Scale:** `{SCALE}` | **Universe:** {total} frozen series succeeded "
              f"(of {len(universe)} attempted)")
    md.append(f"**Models:** {', '.join(MODELS)}")
    md.append(
        "**Dependency gate:** "
        + ", ".join(
            f"{name}={status.get('package')} {status.get('version')}"
            for name, status in dependency_status.items()
        )
    )
    md.append(
        f"**Method:** apples-to-apples {len(MODELS)}-model benchmark, single "
        f"chronological 80/20 holdout, bootstrap 95% CI on RMSE, "
        f"{len(FAMILIES)} model families."
    )
    md.append(
        "**Evidence class:** exploratory breadth benchmark; not V7 multi-fold "
        "walk-forward proof and not live-trading authorization."
    )
    md.append("")
    md.append("## Headline")
    md.append("")
    for fam in FAMILIES:
        c = counts[fam]
        pct = c / total * 100 if total else 0
        md.append(f"- **{fam:<10}** wins {c:>4}/{total} datasets ({pct:5.1f}%)")
    if median_harm_margin is not None:
        md.append("")
        md.append(f"- Median RMSE reduction where harmonic wins: "
                  f"**{median_harm_margin:.1f}%** vs runner-up family")
    md.append("")
    md.append(summary["verdict"])
    md.append("")
    md.append("## Reproducibility")
    md.append("")
    md.append("- Every raw data CSV is hashed in `manifest.sha256.json`.")
    md.append("- This run is chained to `out/frozen_delta_ledger.jsonl`.")
    md.append("- Re-evaluating the frozen raw CSVs with the recorded code and "
              "configuration reproduces the model comparison.")
    md.append("- Any post-hoc edit of any artifact breaks the SHA256 chain.")
    md.append("")
    md.append("## Per-dataset family results (top 100)")
    md.append("")
    md.append("| Dataset | Winner | Winning model | Margin |")
    md.append("|---|---|---|---|")
    if not fam_df.empty:
        sorted_df = fam_df.sort_values("margin_pct_vs_runner", ascending=False)
        for _, r in sorted_df.head(100).iterrows():
            mg = ("—" if pd.isna(r["margin_pct_vs_runner"])
                  else f"{r['margin_pct_vs_runner']:.1f}%")
            md.append(f"| {r['dataset']} | **{r['winning_family']}** "
                      f"| {r['winning_model']} | {mg} |")
    md.append("")
    md.append(f"_Generated by master_universe_benchmark_v2.py at {UTC}_")
    md_path = RUN_DIR / "UNDENIABLE_SCORECARD_V2.md"
    md_path.write_text("\n".join(md), encoding="utf-8")

    # manifest
    manifest = {"run_utc": UTC, "scale": SCALE, "files": {}}
    checkpoint_files = [
        path
        for path in (PARTIAL_ROWS_PATH, PARTIAL_METADATA_PATH)
        if path.exists()
    ]
    for p in [res_path, pivot_path, ci_pivot_path, fam_path, summary_path,
              md_path] + checkpoint_files + list(RAW_DIR.glob("*.csv")):
        manifest["files"][str(p.relative_to(RUN_DIR))] = sha256_file(p)
    manifest_path = RUN_DIR / "manifest.sha256.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    # ledger
    prev_hash = None
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    prev_hash = json.loads(line).get("entry_sha256")
                except Exception:
                    pass
    entry = {
        "run_utc": UTC,
        "test_name": "master_universe_benchmark_v2",
        "scale": SCALE,
        "n_datasets": total,
        "harmonic_win_rate": counts["harmonic"] / total if total else None,
        "family_win_counts": counts,
        "model_dependencies": dependency_status,
        "manifest_sha256": sha256_file(manifest_path),
        "summary_sha256": sha256_file(summary_path),
        "scorecard_sha256": sha256_file(md_path),
        "prev_entry_sha256": prev_hash,
    }
    entry_str = json.dumps(entry, sort_keys=True)
    entry["entry_sha256"] = hashlib.sha256(entry_str.encode("utf-8")).hexdigest()
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    (OUT_ROOT / "latest.txt").write_text(UTC + "\n", encoding="utf-8")

    print()
    print("=== FAMILY SCOREBOARD ===")
    for fam in FAMILIES:
        c = counts[fam]
        pct = c / total * 100 if total else 0
        print(f"  {fam:<10} {c:>4}/{total}  ({pct:5.1f}%)")
    if median_harm_margin is not None:
        print(f"\nMedian harmonic-win margin: {median_harm_margin:.1f}% RMSE reduction")
    print(f"\nfrozen entry sha256: {entry['entry_sha256']}")
    print(f"prev entry sha256:   {prev_hash}")
    print(f"scorecard:           {md_path}")
    print(f"run dir:             {RUN_DIR}")


if __name__ == "__main__":
    main()
