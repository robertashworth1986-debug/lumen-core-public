"""
real_data_fair_benchmark.py
-----------------------------------------------------------------------------
Apples-to-apples benchmark of 6 forecasting models on REAL federal data
pulled live via active API keys. Hash-chains the result so the evidence is
tamper-evident.

Models (same as harmonic_vs_backprop_fair.py):
    a_naive              -- last-value carry
    b_linear_trend       -- ordinary least squares on time index
    c_harmonic_fixed12   -- V6's setup: sin/cos at period 12
    d_harmonic_search    -- adaptive: pick top-3 FFT periods, Ridge fit
    e_mlp_untuned        -- V6's MLP (1->10->1, 200 epochs, lr=0.001)
    f_mlp_tuned          -- 4-layer w/ lag features, early stopping, scaling

Datasets (live from federal APIs):
    EIA_TOTAL_NET_GEN     -- US monthly net electricity generation (MWh)
    FRED_INDPRO           -- US industrial production index (monthly)
    FRED_UNRATE           -- US unemployment rate (monthly)
    FRED_DGS10            -- 10-year treasury yield (daily, resampled monthly)

Output:
    out/real_data_fair_benchmark/<UTC>/
        raw/<dataset>.csv           -- live data snapshot
        results.csv                 -- RMSE per model x dataset
        summary.json                -- winners + verdict
        manifest.sha256.json        -- SHA256 of every artifact
        frozen_delta.jsonl          -- appended to ledger

This is reproducible: re-running it on the same date pulls the same
historical data. The hash chain proves nothing was edited after the fact.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_squared_error
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

# -----------------------------------------------------------------------------
# 0. Setup
# -----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
# NOTE: config/luma_live_keys.env has TRUNCATED keys (EIA 39 chars, FRED 31 chars).
# The deploy_stage mirror has the full-length keys. Audit found this mismatch 2026-05-05.
ENV_FILE_PRIMARY = ROOT / ".deploy_stage" / "code" / "execution" / "config" / "luma_live_keys.env"
ENV_FILE_FALLBACK = ROOT / "config" / "luma_live_keys.env"
OUT_ROOT = ROOT / "out" / "real_data_fair_benchmark"
LEDGER = ROOT / "out" / "frozen_delta_ledger.jsonl"

UTC = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
RUN_DIR = OUT_ROOT / UTC
RAW_DIR = RUN_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def load_env(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


KEYS = load_env(ENV_FILE_PRIMARY)
for k, v in load_env(ENV_FILE_FALLBACK).items():
    KEYS.setdefault(k, v)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# -----------------------------------------------------------------------------
# 1. Live data pulls
# -----------------------------------------------------------------------------
def pull_eia_generation_by_fuel(fueltypeid: str) -> pd.DataFrame:
    """US monthly net electricity generation summed across sectors for one fuel type."""
    key = KEYS.get("EIA_API_KEY")
    if not key:
        raise RuntimeError("EIA_API_KEY missing")
    url = "https://api.eia.gov/v2/electricity/electric-power-operational-data/data/"
    params = [
        ("api_key", key),
        ("frequency", "monthly"),
        ("data[0]", "generation"),
        ("facets[location][]", "US"),
        ("facets[fueltypeid][]", fueltypeid),
        ("start", "2010-01"),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "asc"),
        ("offset", "0"),
        ("length", "5000"),
    ]
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    j = r.json()
    rows = j.get("response", {}).get("data", [])
    if not rows:
        raise RuntimeError(f"EIA returned no rows for {fueltypeid}")
    df = pd.DataFrame(rows)
    df["period"] = pd.to_datetime(df["period"])
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    # Sum across sectors per period
    agg = df.groupby("period", as_index=False)["generation"].sum()
    agg = agg.sort_values("period").rename(columns={"generation": "value"})
    agg = agg.dropna(subset=["value"])
    return agg.reset_index(drop=True)


def pull_fred_series(series_id: str) -> pd.DataFrame:
    key = KEYS.get("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY missing")
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": key,
        "file_type": "json",
        "observation_start": "2000-01-01",
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    j = r.json()
    obs = j.get("observations", [])
    if not obs:
        raise RuntimeError(f"FRED returned no rows for {series_id}")
    df = pd.DataFrame(obs)
    df["period"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"]).sort_values("period")
    return df[["period", "value"]].reset_index(drop=True)


DATASETS = {
    # All-fuels US generation -- weak/moderate seasonality (heating + cooling combined)
    "EIA_GEN_ALL_FUELS": lambda: pull_eia_generation_by_fuel("ALL"),
    # Solar -- very strong annual periodicity (textbook seasonal)
    "EIA_GEN_SOLAR": lambda: pull_eia_generation_by_fuel("SUN"),
    # Wind -- weaker, more chaotic seasonality
    "EIA_GEN_WIND": lambda: pull_eia_generation_by_fuel("WND"),
    # Natural gas -- strong seasonal (winter heating + summer peaking)
    "EIA_GEN_NATGAS": lambda: pull_eia_generation_by_fuel("NG"),
    # NOTE: FRED keys are truncated (31 chars vs 32 expected) in all known mirrors.
    # Need to re-fetch from https://fredaccount.stlouisfed.org/apikeys before re-enabling:
    # "FRED_INDPRO": lambda: pull_fred_series("INDPRO"),
    # "FRED_UNRATE": lambda: pull_fred_series("UNRATE"),
}


# -----------------------------------------------------------------------------
# 2. Models (same set as the synthetic fair benchmark)
# -----------------------------------------------------------------------------
def model_a_naive(y_train, n_test):
    return np.full(n_test, y_train[-1], dtype=float)


def model_b_linear_trend(y_train, n_test):
    n = len(y_train)
    x = np.arange(n).reshape(-1, 1)
    m = LinearRegression().fit(x, y_train)
    xt = np.arange(n, n + n_test).reshape(-1, 1)
    return m.predict(xt)


def harmonic_features(t, periods):
    cols = [np.ones_like(t, dtype=float), t.astype(float)]
    for p in periods:
        if p <= 1:
            continue
        cols.append(np.sin(2 * np.pi * t / p))
        cols.append(np.cos(2 * np.pi * t / p))
    return np.column_stack(cols)


def model_c_harmonic_fixed12(y_train, n_test):
    n = len(y_train)
    t_tr = np.arange(n)
    X_tr = harmonic_features(t_tr, [12])
    m = Ridge(alpha=1.0).fit(X_tr, y_train)
    t_te = np.arange(n, n + n_test)
    return m.predict(harmonic_features(t_te, [12]))


def model_d_harmonic_search(y_train, n_test, top_k=3):
    n = len(y_train)
    yz = y_train - y_train.mean()
    fft = np.fft.rfft(yz)
    power = np.abs(fft) ** 2
    freqs = np.fft.rfftfreq(n, d=1.0)
    # ignore DC and ultra-low freq
    mask = freqs > (1.0 / max(n, 4))
    if mask.sum() == 0:
        periods = [12]
    else:
        idx = np.argsort(power[mask])[::-1][:top_k]
        sel_freqs = freqs[mask][idx]
        periods = [max(2.0, 1.0 / f) for f in sel_freqs if f > 0]
        if not periods:
            periods = [12]
    t_tr = np.arange(n)
    X_tr = harmonic_features(t_tr, periods)
    m = Ridge(alpha=1.0).fit(X_tr, y_train)
    t_te = np.arange(n, n + n_test)
    return m.predict(harmonic_features(t_te, periods))


def model_e_mlp_untuned(y_train, n_test):
    n = len(y_train)
    x_tr = np.arange(n).reshape(-1, 1).astype(float)
    m = MLPRegressor(
        hidden_layer_sizes=(10,),
        learning_rate_init=0.001,
        max_iter=200,
        random_state=0,
        n_iter_no_change=200,
    )
    m.fit(x_tr, y_train)
    x_te = np.arange(n, n + n_test).reshape(-1, 1).astype(float)
    return m.predict(x_te)


def make_lag_features(y, n_lags=12):
    """Returns X, y_aligned for a supervised lag-feature problem."""
    rows = []
    targets = []
    for i in range(n_lags, len(y)):
        rows.append(y[i - n_lags : i])
        targets.append(y[i])
    return np.array(rows), np.array(targets)


def model_f_mlp_tuned(y_train, n_test, n_lags=12):
    if len(y_train) <= n_lags + 5:
        return model_a_naive(y_train, n_test)
    X, yt = make_lag_features(y_train, n_lags=n_lags)
    sx = StandardScaler().fit(X)
    sy = StandardScaler().fit(yt.reshape(-1, 1))
    Xs = sx.transform(X)
    ys = sy.transform(yt.reshape(-1, 1)).ravel()
    m = MLPRegressor(
        hidden_layer_sizes=(64, 32, 16),
        learning_rate_init=0.005,
        max_iter=2000,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=20,
        random_state=0,
    )
    m.fit(Xs, ys)
    # iterative forecast
    history = list(y_train[-n_lags:])
    preds = []
    for _ in range(n_test):
        xin = np.array(history[-n_lags:]).reshape(1, -1)
        xin_s = sx.transform(xin)
        yhat_s = m.predict(xin_s)
        yhat = sy.inverse_transform(yhat_s.reshape(-1, 1)).ravel()[0]
        preds.append(yhat)
        history.append(yhat)
    return np.array(preds)


MODELS = {
    "a_naive": model_a_naive,
    "b_linear_trend": model_b_linear_trend,
    "c_harmonic_fixed12": model_c_harmonic_fixed12,
    "d_harmonic_search": model_d_harmonic_search,
    "e_mlp_untuned": model_e_mlp_untuned,
    "f_mlp_tuned": model_f_mlp_tuned,
}


# -----------------------------------------------------------------------------
# 3. Walk-forward eval
# -----------------------------------------------------------------------------
def evaluate(y: np.ndarray, test_frac: float = 0.2) -> dict:
    n = len(y)
    n_test = max(8, int(n * test_frac))
    if n_test >= n - 24:
        n_test = max(8, n // 5)
    y_train = y[: n - n_test]
    y_test = y[n - n_test :]
    out = {}
    for name, fn in MODELS.items():
        try:
            pred = fn(y_train, n_test)
            rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
        except Exception as e:
            rmse = float("nan")
            print(f"  ! {name} failed: {e}")
        out[name] = rmse
    return out, n_test


# -----------------------------------------------------------------------------
# 4. Main
# -----------------------------------------------------------------------------
def main():
    print(f"=== real_data_fair_benchmark @ {UTC} ===")
    print(f"output dir: {RUN_DIR}")
    print()

    rows = []
    metadata = {}
    for ds_name, fetcher in DATASETS.items():
        print(f"[fetch] {ds_name} ...", flush=True)
        try:
            df = fetcher()
        except Exception as e:
            print(f"  ! fetch failed: {e}")
            metadata[ds_name] = {"error": str(e)}
            continue

        # save raw
        raw_path = RAW_DIR / f"{ds_name}.csv"
        df.to_csv(raw_path, index=False)
        y = df["value"].to_numpy(dtype=float)
        n = len(y)
        print(f"  fetched {n} obs, {df['period'].iloc[0].date()} -> {df['period'].iloc[-1].date()}")

        rmses, n_test = evaluate(y)
        for model_name, rmse in rmses.items():
            rows.append({
                "dataset": ds_name,
                "model": model_name,
                "rmse": rmse,
                "n_train": n - n_test,
                "n_test": n_test,
                "y_mean": float(np.mean(y)),
                "y_std": float(np.std(y)),
            })
        metadata[ds_name] = {
            "n_obs": n,
            "n_test": n_test,
            "first": str(df["period"].iloc[0].date()),
            "last": str(df["period"].iloc[-1].date()),
            "raw_sha256": sha256_file(raw_path),
        }

    if not rows:
        print("FATAL: no datasets succeeded")
        sys.exit(1)

    # results table
    res = pd.DataFrame(rows)
    res_path = RUN_DIR / "results.csv"
    res.to_csv(res_path, index=False)

    pivot = res.pivot(index="dataset", columns="model", values="rmse")
    pivot_path = RUN_DIR / "results_pivot.csv"
    pivot.to_csv(pivot_path)

    # winners
    winners = []
    for ds in pivot.index:
        row = pivot.loc[ds].dropna()
        winner = row.idxmin()
        winners.append({"dataset": ds, "winner": winner, "rmse": float(row.min())})

    summary = {
        "run_utc": UTC,
        "test_name": "real_data_fair_benchmark",
        "datasets": metadata,
        "winners_per_dataset": winners,
        "head_to_head_v6_vs_fair": [
            {
                "dataset": ds,
                "v6_harmonic_fixed12": float(pivot.loc[ds, "c_harmonic_fixed12"]) if "c_harmonic_fixed12" in pivot.columns else None,
                "v6_mlp_untuned": float(pivot.loc[ds, "e_mlp_untuned"]) if "e_mlp_untuned" in pivot.columns else None,
                "tuned_mlp": float(pivot.loc[ds, "f_mlp_tuned"]) if "f_mlp_tuned" in pivot.columns else None,
                "harmonic_search": float(pivot.loc[ds, "d_harmonic_search"]) if "d_harmonic_search" in pivot.columns else None,
                "naive": float(pivot.loc[ds, "a_naive"]) if "a_naive" in pivot.columns else None,
            }
            for ds in pivot.index
        ],
        "verdict_template": (
            "On this REAL federal data: compare harmonic_search to tuned_mlp per dataset. "
            "Where harmonic_search wins, periodic structure is real and capturable. "
            "Where tuned_mlp wins, the series is dominated by non-periodic dynamics. "
            "Where naive wins, neither model has predictive signal at this horizon."
        ),
    }
    summary_path = RUN_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    # manifest with hashes
    manifest = {"run_utc": UTC, "files": {}}
    for p in [res_path, pivot_path, summary_path] + list(RAW_DIR.glob("*.csv")):
        manifest["files"][str(p.relative_to(RUN_DIR))] = sha256_file(p)
    manifest_path = RUN_DIR / "manifest.sha256.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    # chain to ledger
    prev_hash = None
    if LEDGER.exists():
        last_line = None
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last_line = line
        if last_line:
            try:
                prev_hash = json.loads(last_line).get("entry_sha256")
            except Exception:
                pass
    entry = {
        "run_utc": UTC,
        "test_name": "real_data_fair_benchmark",
        "manifest_sha256": sha256_file(manifest_path),
        "summary_sha256": sha256_file(summary_path),
        "prev_entry_sha256": prev_hash,
        "files_count": len(manifest["files"]),
    }
    entry_str = json.dumps(entry, sort_keys=True)
    entry["entry_sha256"] = hashlib.sha256(entry_str.encode("utf-8")).hexdigest()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    # print results
    print()
    print("=== RESULTS (RMSE, lower is better) ===")
    print(pivot.round(4).to_string())
    print()
    print("=== WINNERS ===")
    for w in winners:
        print(f"  {w['dataset']:<22} -> {w['winner']:<22} (rmse={w['rmse']:.4f})")
    print()
    print(f"frozen delta entry sha256: {entry['entry_sha256']}")
    print(f"prev entry hash: {prev_hash}")
    print(f"appended to: {LEDGER}")
    print(f"run dir: {RUN_DIR}")


if __name__ == "__main__":
    main()
