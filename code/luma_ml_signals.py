"""
luma_ml_signals.py
==================
LightGBM + XGBoost ensemble signal generator with SHAP explainability.
Reads institutional leaderboard + rolling performance, trains on-the-fly
from strategy feature vectors, outputs:
  - out/ml_signals/ensemble_signal.json   (live signal + confidence)
  - out/ml_signals/shap_summary.json      (feature importance via SHAP)
  - out/ml_signals/tearsheet_data.json    (quantstats-style metrics)

Run standalone:
    python luma_ml_signals.py --loop --interval 60

Or import and call:
    from luma_ml_signals import get_ensemble_signal
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
OUT  = CODE / "out"
ML_OUT = OUT / "ml_signals"
ML_OUT.mkdir(parents=True, exist_ok=True)

LEADERBOARD_CSV   = ROOT / "institutional_leaderboard.csv"
SCORECARD_FILE    = OUT / "execution" / "investor_proof_scorecard.json"
ROLLING_PERF_FILE = OUT / "rolling_performance.json"

# Features used for the ML model
FEATURE_COLS = [
    "train_sharpe", "test_sharpe", "test_sortino", "test_omega",
    "test_profit_factor", "train_max_dd", "test_max_dd",
    "train_cagr", "test_cagr", "test_win_rate", "test_expectancy",
    "test_vol", "stability",
]
TARGET_COL = "institutional_score"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_leaderboard() -> pd.DataFrame:
    try:
        text = LEADERBOARD_CSV.read_text(encoding="utf-8", errors="ignore")
        df = pd.read_csv(io.StringIO(text))
        for col in FEATURE_COLS + [TARGET_COL]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=FEATURE_COLS + [TARGET_COL])
        return df
    except Exception as e:
        print(f"[ml_signals] leaderboard load error: {e}")
        return pd.DataFrame()


def build_feature_matrix(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    available = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available].values.astype(np.float32)
    y = df[TARGET_COL].values.astype(np.float32)
    return X, y, available


def train_ensemble(X: np.ndarray, y: np.ndarray) -> tuple[Any, Any]:
    """Train LightGBM + XGBoost on strategy features → institutional score."""
    import lightgbm as lgb
    import xgboost as xgb

    lgb_model = lgb.LGBMRegressor(
        n_estimators=200, learning_rate=0.05, max_depth=5,
        num_leaves=31, subsample=0.8, colsample_bytree=0.8,
        random_state=42, verbose=-1,
    )
    xgb_model = xgb.XGBRegressor(
        n_estimators=200, learning_rate=0.05, max_depth=5,
        subsample=0.8, colsample_bytree=0.8,
        random_state=42, verbosity=0,
    )

    lgb_model.fit(X, y)
    xgb_model.fit(X, y)
    return lgb_model, xgb_model


def compute_shap(model: Any, X: np.ndarray, feature_names: list[str]) -> list[dict[str, Any]]:
    """Return top feature importances via SHAP TreeExplainer."""
    try:
        import shap
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        mean_abs = np.abs(shap_values).mean(axis=0)
        ranked = sorted(zip(feature_names, mean_abs.tolist()), key=lambda x: -x[1])
        return [{"feature": f, "mean_abs_shap": round(v, 6)} for f, v in ranked]
    except Exception as e:
        print(f"[ml_signals] SHAP error: {e}")
        return []


def compute_portfolio_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """Compute aggregate portfolio-level stats from strategy returns distribution."""
    try:
        import quantstats as qs
        # Use test_cagr distribution as proxy for strategy returns
        cagr_series = df["test_cagr"].dropna()
        sharpe_series = df["test_sharpe"].dropna()
        return {
            "strategy_count":     int(len(df)),
            "mean_test_sharpe":   round(float(sharpe_series.mean()), 4),
            "median_test_sharpe": round(float(sharpe_series.median()), 4),
            "top_decile_sharpe":  round(float(sharpe_series.quantile(0.9)), 4),
            "mean_test_cagr":     round(float(cagr_series.mean()), 4),
            "median_test_cagr":   round(float(cagr_series.median()), 4),
            "top_decile_cagr":    round(float(cagr_series.quantile(0.9)), 4),
            "pct_profitable":     round(float((cagr_series > 0).mean()), 4),
            "pct_high_sharpe":    round(float((sharpe_series > 5).mean()), 4),
        }
    except Exception as e:
        # quantstats not installed or other error — return basic stats
        try:
            sharpe_series = df["test_sharpe"].dropna()
            cagr_series = df["test_cagr"].dropna()
            return {
                "strategy_count":     int(len(df)),
                "mean_test_sharpe":   round(float(sharpe_series.mean()), 4),
                "median_test_sharpe": round(float(sharpe_series.median()), 4),
                "top_decile_sharpe":  round(float(sharpe_series.quantile(0.9)), 4),
                "mean_test_cagr":     round(float(cagr_series.mean()), 4),
                "pct_profitable":     round(float((cagr_series > 0).mean()), 4),
                "pct_high_sharpe":    round(float((sharpe_series > 5).mean()), 4),
            }
        except Exception:
            return {}


def run_once() -> dict[str, Any]:
    print(f"[ml_signals] {now_utc()} — loading leaderboard …")
    df = load_leaderboard()
    if df.empty or len(df) < 20:
        result = {"status": "insufficient_data", "generated_utc": now_utc()}
        (ML_OUT / "ensemble_signal.json").write_text(json.dumps(result, indent=2))
        return result

    X, y, feature_names = build_feature_matrix(df)
    print(f"[ml_signals] training on {len(df)} strategies × {len(feature_names)} features …")

    lgb_model, xgb_model = train_ensemble(X, y)

    # Ensemble predictions
    lgb_pred = lgb_model.predict(X)
    xgb_pred = xgb_model.predict(X)
    ensemble_pred = (lgb_pred + xgb_pred) / 2.0

    # Identify top strategies by ensemble score
    df = df.copy()
    df["ensemble_score"] = ensemble_pred
    top = df.nlargest(10, "ensemble_score")[
        ["flow", "strategy", "algo", "test_sharpe", "test_cagr",
         "test_win_rate", "institutional_score", "ensemble_score"]
    ].to_dict(orient="records")

    # SHAP on LightGBM
    shap_summary = compute_shap(lgb_model, X, feature_names)

    # Portfolio metrics
    portfolio_metrics = compute_portfolio_metrics(df)

    # Ensemble confidence: correlation between lgb and xgb predictions
    corr = float(np.corrcoef(lgb_pred, xgb_pred)[0, 1])

    result = {
        "generated_utc":     now_utc(),
        "status":            "ok",
        "strategy_count":    int(len(df)),
        "model_agreement":   round(corr, 4),
        "ensemble_top10":    top,
        "portfolio_metrics": portfolio_metrics,
    }

    shap_out = {
        "generated_utc":    now_utc(),
        "model":            "lightgbm",
        "strategy_count":   int(len(df)),
        "feature_importance": shap_summary,
    }

    (ML_OUT / "ensemble_signal.json").write_text(json.dumps(result, indent=2))
    (ML_OUT / "shap_summary.json").write_text(json.dumps(shap_out, indent=2))
    (ML_OUT / "tearsheet_data.json").write_text(json.dumps(portfolio_metrics, indent=2))

    print(f"[ml_signals] done — {len(df)} strategies, model_agreement={corr:.3f}, top: {top[0]['flow']}/{top[0]['strategy']}")
    return result


def get_ensemble_signal() -> dict[str, Any]:
    """Import-safe: return cached result or run fresh."""
    cache = ML_OUT / "ensemble_signal.json"
    if cache.exists():
        try:
            data = json.loads(cache.read_text())
            ts = data.get("generated_utc", "")
            if ts:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds()
                if age < 300:
                    return data
        except Exception:
            pass
    return run_once()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()

    if args.loop:
        print(f"[ml_signals] loop mode — interval {args.interval}s")
        while True:
            try:
                run_once()
            except Exception as e:
                print(f"[ml_signals] error: {e}")
            time.sleep(args.interval)
    else:
        run_once()
