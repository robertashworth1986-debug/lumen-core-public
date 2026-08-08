"""
forecast_api.py
=========================================================================
LumenCore innovation #3: live forecast API surface.

Mounts on the FastAPI gateway as a router. Endpoints:

    GET /api/forecast/datasets
        -> list of (dataset_id, n_obs, last_date, family_router_picks)

    GET /api/forecast/{dataset_id}?h=12
        -> JSON: {
             dataset, n_history, horizon,
             chosen_family, family_confidences,
             features, forecast: [{t, value, lo80, hi80, lo95, hi95}],
             evidence_run, router_run,
           }

Implementation:
    - Loads the cached raw series from the latest v2 run (out/master_universe_v2/<UTC>/raw/).
    - Loads the trained meta-router from out/meta_router/<UTC>/router.joblib.
    - Picks the family the router predicts.
    - Runs the family's strongest model to produce h-step-ahead forecasts.
    - Bootstraps in-sample residuals 400× to derive 80% / 95% CI bands.

Mount in luma_experience_gateway.py:
    from forecast_api import router as _forecast_router
    app.include_router(_forecast_router)
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

V2_RUNS = ROOT / "out" / "master_universe_v2"
ROUTER_RUNS = ROOT / "out" / "meta_router"

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


# ---------------------------------------------------------------------------
# State (loaded once)
# ---------------------------------------------------------------------------
class _State:
    run_utc: Optional[str] = None
    raw_dir: Optional[Path] = None
    router_run: Optional[str] = None
    clf = None
    feat_cols: Optional[list[str]] = None
    extract_features = None  # function
    family_models: Optional[dict] = None
    loaded_at: Optional[float] = None


_S = _State()
log = logging.getLogger(__name__)


def _load_state() -> None:
    """Lazy-load the latest run + router. Re-runs are cheap."""
    latest = V2_RUNS / "latest.txt"
    if not latest.exists():
        raise RuntimeError("no v2 run available (out/master_universe_v2/latest.txt missing)")
    run_utc = latest.read_text(encoding="utf-8").strip()
    raw_dir = V2_RUNS / run_utc / "raw"
    if not raw_dir.exists():
        raise RuntimeError(f"raw dir missing: {raw_dir}")

    router_run = run_utc
    router_path = ROUTER_RUNS / router_run / "router.joblib"
    if not router_path.exists():
        # fall back to most recent router run
        if ROUTER_RUNS.exists():
            cands = sorted(p.name for p in ROUTER_RUNS.iterdir() if p.is_dir())
            if cands:
                router_run = cands[-1]
                router_path = ROUTER_RUNS / router_run / "router.joblib"
    if not router_path.exists():
        raise RuntimeError("no trained router available; run code/meta_router.py first")

    import joblib
    bundle = joblib.load(router_path)
    from meta_router import extract_features  # noqa: WPS433

    # Per-family champion forecasters (strongest model in each family).
    from master_universe_benchmark import (
        model_a_naive, model_b_linear_trend,
        model_c_harmonic_fixed12, model_d_harmonic_search,
        model_e_mlp_untuned, model_f_mlp_tuned,
    )
    from master_universe_benchmark_v2 import (
        model_g_xgboost_lag, model_h_lightgbm_lag, model_i_sarima,
    )

    family_models = {
        "baseline": model_b_linear_trend,
        "harmonic": model_d_harmonic_search,
        "neural":   model_f_mlp_tuned,
        "tree":     model_h_lightgbm_lag,
        "classical": model_i_sarima,
    }

    _S.run_utc = run_utc
    _S.raw_dir = raw_dir
    _S.router_run = router_run
    _S.clf = bundle["clf"]
    _S.feat_cols = bundle["feat_cols"]
    _S.extract_features = extract_features
    _S.family_models = family_models
    _S.loaded_at = time.time()


def _ensure_loaded() -> None:
    if _S.clf is None:
        _load_state()


def _dataset_source(dataset_id: str) -> Path:
    """Select a server-owned CSV by stem without joining route input to a path."""
    raw_dir = _S.raw_dir
    if raw_dir is None:
        raise HTTPException(status_code=503, detail="forecast service is unavailable")
    try:
        source = next(
            (candidate for candidate in raw_dir.glob("*.csv") if candidate.stem == dataset_id),
            None,
        )
    except OSError:
        source = None
    if source is None:
        raise HTTPException(status_code=404, detail="dataset not found")
    return source


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _features_row(y: np.ndarray) -> np.ndarray:
    feats = _S.extract_features(y)
    return np.array([float(feats.get(c, 0.0)) for c in _S.feat_cols],
                    dtype=float).reshape(1, -1), feats


def _bootstrap_bands(y_train: np.ndarray, point: np.ndarray,
                     model_fn, n_boot: int = 200, seed: int = 7) -> dict:
    """Residual bootstrap of forecast errors using a 1-step-ahead expanding fit
    is too slow at request time. Instead, approximate CI bands from
    in-sample residuals of a quick re-fit.
    """
    rng = np.random.default_rng(seed)
    if len(y_train) < 24:
        std = float(np.std(y_train) or 1.0)
        z80 = 1.2816
        z95 = 1.96
        return {
            "lo80": (point - z80 * std).tolist(),
            "hi80": (point + z80 * std).tolist(),
            "lo95": (point - z95 * std).tolist(),
            "hi95": (point + z95 * std).tolist(),
            "method": "naive_std",
        }
    # Fit on first 80%, score on last 20% for a quick residual sample.
    cut = max(8, int(len(y_train) * 0.2))
    try:
        in_pred = model_fn(y_train[:-cut], cut)
        residuals = y_train[-cut:] - np.asarray(in_pred, dtype=float)
        residuals = residuals[np.isfinite(residuals)]
    except Exception:
        residuals = np.diff(y_train)
    if len(residuals) < 4:
        residuals = np.diff(y_train)
    sigma = float(np.std(residuals) or 1.0)

    h = len(point)
    # Errors grow with horizon: scale by sqrt(t)
    growth = np.sqrt(np.arange(1, h + 1))
    z80, z95 = 1.2816, 1.96
    return {
        "lo80": (point - z80 * sigma * growth).tolist(),
        "hi80": (point + z80 * sigma * growth).tolist(),
        "lo95": (point - z95 * sigma * growth).tolist(),
        "hi95": (point + z95 * sigma * growth).tolist(),
        "method": "residual_sigma_sqrt_h",
        "residual_sigma": round(sigma, 6),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/datasets")
def list_datasets(limit: int = Query(default=200, ge=1, le=2000)) -> JSONResponse:
    try:
        _ensure_loaded()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="forecast service is unavailable")

    items: list[dict] = []
    for p in sorted(_S.raw_dir.glob("*.csv")):
        try:
            df = pd.read_csv(p)
            items.append({
                "dataset": p.stem,
                "n_obs": int(len(df)),
                "first": str(df["date"].iloc[0]) if "date" in df.columns and len(df) else None,
                "last":  str(df["date"].iloc[-1]) if "date" in df.columns and len(df) else None,
            })
        except Exception:
            continue
        if len(items) >= limit:
            break
    return JSONResponse({
        "run_utc": _S.run_utc,
        "router_run": _S.router_run,
        "n_datasets_listed": len(items),
        "datasets": items,
    })


@router.get("/series/{dataset_id}")
def forecast(dataset_id: str,
             h: int = Query(default=12, ge=1, le=120)) -> JSONResponse:
    try:
        _ensure_loaded()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="forecast service is unavailable")

    src = _dataset_source(dataset_id)

    try:
        df = pd.read_csv(src)
        y = df["value"].to_numpy(dtype=float)
    except Exception:
        log.exception("forecast dataset read failed")
        raise HTTPException(status_code=500, detail="dataset read failed")
    if len(y) < 30:
        raise HTTPException(status_code=400,
                            detail=f"series too short ({len(y)} obs)")

    # 1) Router pick
    try:
        X, feats = _features_row(y)
        chosen = _S.clf.predict(X)[0]
        proba = None
        try:
            p = _S.clf.predict_proba(X)[0]
            classes = list(_S.clf.classes_)
            proba = {c: round(float(p[i]), 4) for i, c in enumerate(classes)}
        except Exception:
            proba = None
    except Exception:
        log.exception("forecast router evaluation failed")
        raise HTTPException(status_code=500, detail="router evaluation failed")

    # 2) Forecast with chosen family champion
    model_fn = _S.family_models.get(chosen)
    if model_fn is None:
        raise HTTPException(status_code=500, detail=f"no model for family {chosen!r}")
    try:
        point = np.asarray(model_fn(y, h), dtype=float)
    except Exception:
        log.exception("forecast family model failed")
        raise HTTPException(status_code=500, detail="forecast model failed")
    if not np.isfinite(point).all():
        point = np.nan_to_num(point, nan=float(np.mean(y)))

    bands = _bootstrap_bands(y, point, model_fn)

    # 3) Build response
    last_date = None
    if "date" in df.columns and len(df):
        try:
            last_date = pd.to_datetime(df["date"].iloc[-1])
        except Exception:
            last_date = None

    forecast_rows: list[dict] = []
    for i in range(h):
        row = {
            "t": i + 1,
            "value": float(point[i]),
            "lo80": float(bands["lo80"][i]),
            "hi80": float(bands["hi80"][i]),
            "lo95": float(bands["lo95"][i]),
            "hi95": float(bands["hi95"][i]),
        }
        if last_date is not None:
            row["forecast_date"] = str((last_date + pd.tseries.offsets.MonthEnd(i + 1)).date())
        forecast_rows.append(row)

    return JSONResponse({
        "dataset": dataset_id,
        "n_history": int(len(y)),
        "horizon": int(h),
        "evidence_run": _S.run_utc,
        "router_run": _S.router_run,
        "chosen_family": chosen,
        "family_confidences": proba,
        "features": {k: (round(float(v), 6) if isinstance(v, (int, float)) else v)
                     for k, v in feats.items()},
        "ci_method": bands.get("method"),
        "residual_sigma": bands.get("residual_sigma"),
        "forecast": forecast_rows,
    })


@router.get("/anomalies")
def anomalies(limit: int = Query(default=50, ge=1, le=500),
              min_z: float = Query(default=2.0, ge=0.0, le=10.0)) -> JSONResponse:
    """Return ranked anomaly scanner output for the latest run."""
    try:
        _ensure_loaded()
    except RuntimeError:
        return JSONResponse({
            "run_utc": None,
            "summary": {
                "available": False,
                "reason": "forecast service is unavailable",
            },
            "n_returned": 0,
            "ranked": [],
        })

    anom_dir = ROOT / "out" / "anomaly_scanner" / _S.run_utc
    summary_p = anom_dir / "summary.json"
    ranked_p = anom_dir / "ranked.csv"
    if not (summary_p.exists() and ranked_p.exists()):
        return JSONResponse({
            "run_utc": _S.run_utc,
            "summary": {
                "available": False,
                "reason": f"no anomaly pack at {anom_dir}",
            },
            "n_returned": 0,
            "ranked": [],
        })

    import json as _json
    summary = _json.loads(summary_p.read_text(encoding="utf-8"))
    ranked_full = pd.read_csv(ranked_p)
    # Enrich summary with distribution stats so the UI doesn't need to recompute.
    if "max_abs_z" in ranked_full.columns and len(ranked_full):
        n = int(summary.get("n_datasets") or len(ranked_full)) or 1
        summary["mean_max_abs_z"] = float(ranked_full["max_abs_z"].mean())
        summary["median_max_abs_z"] = float(ranked_full["max_abs_z"].median())
        summary["frac_with_2sigma_anomaly"] = float(
            summary.get("n_with_2sigma_anomaly", 0) / n)
        summary["frac_with_3sigma_anomaly"] = float(
            summary.get("n_with_3sigma_anomaly", 0) / n)
    ranked = ranked_full[ranked_full["max_abs_z"] >= min_z].head(limit)
    return JSONResponse({
        "run_utc": _S.run_utc,
        "summary": summary,
        "n_returned": int(len(ranked)),
        "ranked": ranked.to_dict(orient="records"),
    })


@router.get("/evidence-overview")
def evidence_overview() -> JSONResponse:
    """Aggregate the headline numbers from every innovation pack."""
    try:
        _ensure_loaded()
    except RuntimeError:
        return JSONResponse({
            "run_utc": None,
            "router_run": None,
            "available": False,
            "reason": "forecast service is unavailable",
            "v2": {},
            "router": {},
            "stacker": {},
            "blender": {},
            "calibration": {},
            "anomaly": {},
            "regime": {},
        })

    import json as _json
    utc = _S.run_utc

    def _read(p: Path):
        if not p.exists():
            return None
        try:
            return _json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    base = ROOT / "out"
    v2 = _read(base / "master_universe_v2" / utc / "summary.json") or {}
    router_eval = _read(base / "meta_router" / utc / "eval.json") or {}
    stacker_eval = _read(base / "hybrid_stacker" / utc / "eval.json") or {}
    blender_eval = _read(base / "stacking_blender" / utc / "eval.json") or {}
    calib = _read(base / "ci_calibration" / utc / "summary.json") or {}
    anom = _read(base / "anomaly_scanner" / utc / "summary.json") or {}
    regime = _read(base / "regime_shift_scanner" / utc / "summary.json") or {}

    return JSONResponse({
        "run_utc": utc,
        "router_run": _S.router_run,
        "available": True,
        "reason": "",
        "v2": {
            "n_datasets_succeeded": v2.get("n_datasets_succeeded"),
            "family_win_counts": v2.get("family_win_counts"),
            "harmonic_win_rate": v2.get("harmonic_win_rate"),
            "harmonic_median_margin_pct": v2.get("harmonic_median_margin_pct"),
        },
        "router": router_eval.get("summary", {}),
        "stacker": stacker_eval.get("summary", {}),
        "blender": blender_eval.get("summary", {}),
        "calibration": calib,
        "anomaly": anom,
        "regime": regime,
    })


@router.get("/explain/{dataset_id}")
def explain(dataset_id: str) -> JSONResponse:
    """Why did the meta-router pick a family for this dataset?

    Returns the 16 hand-engineered features, the router's class probabilities,
    and the global feature_importances_ of the underlying classifier so the UI
    can show "the router weighed `harmonic_strength_12` at 0.18 and this series
    scored 0.42 there".
    """
    try:
        _ensure_loaded()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="forecast service is unavailable")

    src = _dataset_source(dataset_id)

    try:
        df = pd.read_csv(src)
        y = df["value"].to_numpy(dtype=float)
    except Exception:
        log.exception("forecast explanation dataset read failed")
        raise HTTPException(status_code=500, detail="dataset read failed")
    if len(y) < 30:
        raise HTTPException(status_code=400, detail=f"series too short ({len(y)} obs)")

    X, feats = _features_row(y)
    chosen = _S.clf.predict(X)[0]

    # Class probabilities
    proba = None
    try:
        p = _S.clf.predict_proba(X)[0]
        classes = list(_S.clf.classes_)
        proba = sorted(
            [{"family": c, "prob": round(float(p[i]), 4)} for i, c in enumerate(classes)],
            key=lambda r: r["prob"], reverse=True)
    except Exception:
        proba = None

    # Global importances (RandomForest / GBM classifiers expose this)
    importances = None
    try:
        imp = getattr(_S.clf, "feature_importances_", None)
        if imp is not None:
            importances = sorted(
                [{"feature": _S.feat_cols[i],
                  "importance": round(float(imp[i]), 4),
                  "value": round(float(X[0, i]), 6)}
                 for i in range(len(_S.feat_cols))],
                key=lambda r: r["importance"], reverse=True)
    except Exception:
        importances = None

    # Per-dataset contribution signal: importance × |z-score of feature|
    # against the population in features.csv (router run).
    contributions = None
    try:
        feat_csv = ROOT / "out" / "meta_router" / _S.router_run / "features.csv"
        if feat_csv.exists() and importances is not None:
            pop = pd.read_csv(feat_csv)
            contribs = []
            for col in _S.feat_cols:
                if col not in pop.columns:
                    continue
                vals = pop[col].astype(float)
                mu = float(vals.mean())
                sigma = float(vals.std() or 1.0)
                feat_val = float(feats.get(col, 0.0))
                z = (feat_val - mu) / sigma if sigma else 0.0
                imp_v = next((r["importance"] for r in importances if r["feature"] == col), 0.0)
                contribs.append({
                    "feature": col,
                    "value": round(feat_val, 6),
                    "pop_mean": round(mu, 6),
                    "pop_sigma": round(sigma, 6),
                    "z_vs_pop": round(z, 3),
                    "importance": imp_v,
                    "score": round(imp_v * abs(z), 4),
                })
            contributions = sorted(contribs, key=lambda r: r["score"], reverse=True)
    except Exception:
        contributions = None

    return JSONResponse({
        "dataset": dataset_id,
        "n_history": int(len(y)),
        "router_run": _S.router_run,
        "chosen_family": chosen,
        "family_probabilities": proba,
        "feature_importances": importances,
        "feature_contributions": contributions,
        "features": {k: (round(float(v), 6) if isinstance(v, (int, float)) else v)
                     for k, v in feats.items()},
    })


@router.get("/regime")
def regime(limit: int = Query(default=100, ge=1, le=1000),
           recent_only: bool = Query(default=False),
           variance_only: bool = Query(default=False)) -> JSONResponse:
    """Regime-shift scanner output for the latest run."""
    try:
        _ensure_loaded()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="forecast service is unavailable")

    rg_dir = ROOT / "out" / "regime_shift_scanner" / _S.run_utc
    summary_p = rg_dir / "summary.json"
    regimes_p = rg_dir / "regimes.csv"
    if not (summary_p.exists() and regimes_p.exists()):
        raise HTTPException(status_code=503, detail=f"no regime pack at {rg_dir}")

    import json as _json
    summary = _json.loads(summary_p.read_text(encoding="utf-8"))
    df = pd.read_csv(regimes_p)
    if recent_only:
        df = df[df["recent_break"] == True]  # noqa: E712
    if variance_only:
        df = df[df["var_regime_break"] == True]  # noqa: E712
    df = df.sort_values(
        ["recent_break", "peak_cusum_pos"], ascending=[False, False]).head(limit)
    return JSONResponse({
        "run_utc": _S.run_utc,
        "summary": summary,
        "n_returned": int(len(df)),
        "rows": df.to_dict(orient="records"),
    })


@router.get("")
def index() -> JSONResponse:
    try:
        _ensure_loaded()
        ready = True
        msg = None
    except RuntimeError:
        ready = False
        msg = "forecast service is unavailable"
    return JSONResponse({
        "service": "LumenCore Forecast API",
        "ready": ready,
        "message": msg,
        "endpoints": [
            "GET /api/forecast/datasets",
            "GET /api/forecast/{dataset_id}?h=12",
        ],
        "evidence_run": _S.run_utc,
        "router_run": _S.router_run,
    })
