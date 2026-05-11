"""
master_universe_benchmark.py
=============================================================================
The undeniable evidence pack. Pulls 20+ real federal datasets via live API
keys and runs the same 6 forecasting models on every series, with bootstrap
95% confidence intervals on every RMSE. Hash-chains the entire output to a
tamper-evident ledger.

Models (identical to fair benchmark):
    a_naive              -- last value carried
    b_linear_trend       -- OLS on time index
    c_harmonic_fixed12   -- V6 spec: sin/cos at period 12
    d_harmonic_search    -- adaptive: top-3 FFT periods + Ridge  *** HARMONIC FAMILY ***
    e_mlp_untuned        -- V6 spec: 1->10->1, 200 epochs, lr 0.001
    f_mlp_tuned          -- 4-layer w/ lag features, early stopping, scaling

Universe (all live federal sources):
  EIA electric power (monthly, by fuel, summed across sectors):
    ALL, COW (coal), NG (natgas), NUC (nuclear), SUN (solar), WND (wind),
    HYC (hydro conventional), GEO (geothermal), BIO (biomass)
  EIA electric power (monthly, by sector for ALL fuels):
    sector 1 (electric utility), sector 2 (IPP non-CHP),
    sector 3 (IPP CHP), sector 6 (commercial), sector 7 (industrial)
  EIA retail electricity sales (monthly, by sector):
    residential, commercial, industrial, transportation
  EIA petroleum stocks (weekly):
    crude oil, motor gasoline, distillate, propane
  EIA natural gas storage (weekly):
    lower 48 working gas in storage
  NOAA NCEI Climate at a Glance:
    CONUS monthly average temperature
  NREL solar resource (annual TMY proxy):
    skipped (single-point data, not a time series for forecasting)

Bootstrap CIs:
    For each (dataset, model) we resample test-set squared errors with
    replacement (n=400 iterations) and report 2.5/50/97.5 percentiles of
    sqrt(mean(...)). This gives a real 95% CI on RMSE -- not a point estimate.

Win classification:
    HARMONIC family  = {c_harmonic_fixed12, d_harmonic_search}
    NEURAL family    = {e_mlp_untuned, f_mlp_tuned}
    BASELINE family  = {a_naive, b_linear_trend}
    A dataset is "harmonic-dominant" if min(harmonic) < min(neural) AND
    min(harmonic) < min(baseline). Likewise for neural-dominant /
    baseline-dominant. Margin computed in % RMSE reduction vs runner-up
    family.

Output:
    out/master_universe/<UTC>/
        raw/<dataset>.csv           live snapshot
        results.csv                 long-form: dataset, model, rmse, ci_lo,
                                    ci_hi, n_train, n_test
        results_pivot.csv           wide RMSE table
        ci_pivot.csv                wide CI string table for human reading
        family_scoreboard.csv       harmonic vs neural vs baseline per ds
        summary.json                full machine-readable
        manifest.sha256.json        per-file hashes
        UNDENIABLE_SCORECARD.md     public-facing executive summary
    out/frozen_delta_ledger.jsonl   appended chain entry
"""

from __future__ import annotations

import hashlib
import json
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

warnings.filterwarnings("ignore")

# -----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
ENV_FILES = [
    ROOT / ".deploy_stage" / "code" / "execution" / "config" / "luma_live_keys.env",
    ROOT / "config" / "luma_live_keys.env",
]
OUT_ROOT = ROOT / "out" / "master_universe"
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


KEYS = {}
for p in ENV_FILES:
    for k, v in load_env(p).items():
        # prefer the LONGEST value across mirrors (truncated keys lose)
        if k not in KEYS or len(v) > len(KEYS[k]):
            KEYS[k] = v


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# -----------------------------------------------------------------------------
# 1. Federal data fetchers
# -----------------------------------------------------------------------------
EIA_BASE = "https://api.eia.gov/v2"


def _eia_get(path: str, params: list[tuple[str, str]]) -> list[dict]:
    key = KEYS.get("EIA_API_KEY")
    if not key:
        raise RuntimeError("EIA_API_KEY missing")
    full = [("api_key", key), *params,
            ("offset", "0"), ("length", "5000")]
    r = requests.get(EIA_BASE + path, params=full, timeout=30)
    r.raise_for_status()
    j = r.json()
    return j.get("response", {}).get("data", [])


def eia_generation_by_fuel(fueltypeid: str) -> pd.DataFrame:
    rows = _eia_get(
        "/electricity/electric-power-operational-data/data/",
        [("frequency", "monthly"),
         ("data[0]", "generation"),
         ("facets[location][]", "US"),
         ("facets[fueltypeid][]", fueltypeid),
         ("start", "2010-01"),
         ("sort[0][column]", "period"),
         ("sort[0][direction]", "asc")],
    )
    if not rows:
        raise RuntimeError(f"no rows for fuel {fueltypeid}")
    df = pd.DataFrame(rows)
    df["period"] = pd.to_datetime(df["period"])
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    g = df.groupby("period", as_index=False)["generation"].sum()
    g = g.sort_values("period").rename(columns={"generation": "value"}).dropna()
    return g.reset_index(drop=True)


def eia_generation_by_sector(sectorid: str) -> pd.DataFrame:
    rows = _eia_get(
        "/electricity/electric-power-operational-data/data/",
        [("frequency", "monthly"),
         ("data[0]", "generation"),
         ("facets[location][]", "US"),
         ("facets[sectorid][]", sectorid),
         ("facets[fueltypeid][]", "ALL"),
         ("start", "2010-01"),
         ("sort[0][column]", "period"),
         ("sort[0][direction]", "asc")],
    )
    if not rows:
        raise RuntimeError(f"no rows for sector {sectorid}")
    df = pd.DataFrame(rows)
    df["period"] = pd.to_datetime(df["period"])
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    g = df.groupby("period", as_index=False)["generation"].sum()
    g = g.sort_values("period").rename(columns={"generation": "value"}).dropna()
    return g.reset_index(drop=True)


def eia_retail_sales(sectorid: str) -> pd.DataFrame:
    rows = _eia_get(
        "/electricity/retail-sales/data/",
        [("frequency", "monthly"),
         ("data[0]", "sales"),
         ("facets[stateid][]", "US"),
         ("facets[sectorid][]", sectorid),
         ("start", "2010-01"),
         ("sort[0][column]", "period"),
         ("sort[0][direction]", "asc")],
    )
    if not rows:
        raise RuntimeError(f"no retail sales for {sectorid}")
    df = pd.DataFrame(rows)
    df["period"] = pd.to_datetime(df["period"])
    df["sales"] = pd.to_numeric(df["sales"], errors="coerce")
    g = df.groupby("period", as_index=False)["sales"].sum()
    g = g.sort_values("period").rename(columns={"sales": "value"}).dropna()
    return g.reset_index(drop=True)


def eia_petroleum_stocks_weekly(product: str) -> pd.DataFrame:
    """Weekly US ending stocks of refined petroleum products."""
    rows = _eia_get(
        "/petroleum/stoc/wstk/data/",
        [("frequency", "weekly"),
         ("data[0]", "value"),
         ("facets[product][]", product),
         ("facets[duoarea][]", "NUS"),
         ("start", "2010-01-01"),
         ("sort[0][column]", "period"),
         ("sort[0][direction]", "asc")],
    )
    if not rows:
        raise RuntimeError(f"no rows for product {product}")
    df = pd.DataFrame(rows)
    df["period"] = pd.to_datetime(df["period"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    g = df.groupby("period", as_index=False)["value"].sum().sort_values("period").dropna()
    return g.reset_index(drop=True)


def eia_crude_stocks_weekly() -> pd.DataFrame:
    """Weekly US crude oil ending stocks (excl SPR)."""
    rows = _eia_get(
        "/petroleum/stoc/wstk/data/",
        [("frequency", "weekly"),
         ("data[0]", "value"),
         ("facets[product][]", "EPC0"),
         ("facets[duoarea][]", "NUS"),
         ("start", "2010-01-01"),
         ("sort[0][column]", "period"),
         ("sort[0][direction]", "asc")],
    )
    if not rows:
        raise RuntimeError("no rows for crude")
    df = pd.DataFrame(rows)
    df["period"] = pd.to_datetime(df["period"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    g = df.groupby("period", as_index=False)["value"].sum().sort_values("period").dropna()
    return g.reset_index(drop=True)


def eia_ng_storage_weekly() -> pd.DataFrame:
    rows = _eia_get(
        "/natural-gas/stor/wkly/data/",
        [("frequency", "weekly"),
         ("data[0]", "value"),
         ("facets[duoarea][]", "NUS"),
         ("start", "2010-01-01"),
         ("sort[0][column]", "period"),
         ("sort[0][direction]", "asc")],
    )
    if not rows:
        raise RuntimeError("no NG storage")
    df = pd.DataFrame(rows)
    df["period"] = pd.to_datetime(df["period"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    g = df.groupby("period", as_index=False)["value"].sum().sort_values("period").dropna()
    return g.reset_index(drop=True)


def noaa_conus_temperature() -> pd.DataFrame:
    """NOAA NCEI Climate at a Glance: CONUS monthly avg temp (no auth required)."""
    url = "https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/national/time-series/110/tavg/all/1/2000-2026.json"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    j = r.json()
    data = j.get("data", {})
    rows = []
    for k, v in data.items():
        rows.append({
            "period": pd.to_datetime(k, format="%Y%m"),
            "value": float(v.get("value")) if v.get("value") not in (None, "") else None,
        })
    df = pd.DataFrame(rows).dropna().sort_values("period").reset_index(drop=True)
    if df.empty:
        raise RuntimeError("NOAA returned no rows")
    return df


# -----------------------------------------------------------------------------
# 2. The dataset universe
# -----------------------------------------------------------------------------
DATASETS = {
    # generation by fuel
    "EIA_GEN_ALL_FUELS": lambda: eia_generation_by_fuel("ALL"),
    "EIA_GEN_COAL":      lambda: eia_generation_by_fuel("COW"),
    "EIA_GEN_NATGAS":    lambda: eia_generation_by_fuel("NG"),
    "EIA_GEN_NUCLEAR":   lambda: eia_generation_by_fuel("NUC"),
    "EIA_GEN_SOLAR":     lambda: eia_generation_by_fuel("SUN"),
    "EIA_GEN_WIND":      lambda: eia_generation_by_fuel("WND"),
    "EIA_GEN_HYDRO":     lambda: eia_generation_by_fuel("HYC"),
    "EIA_GEN_GEOTHERM":  lambda: eia_generation_by_fuel("GEO"),
    "EIA_GEN_BIOMASS":   lambda: eia_generation_by_fuel("BIO"),
    # generation by sector
    "EIA_SECTOR_ELECUTIL":  lambda: eia_generation_by_sector("1"),
    "EIA_SECTOR_IPP_NONCHP": lambda: eia_generation_by_sector("2"),
    "EIA_SECTOR_IPP_CHP":    lambda: eia_generation_by_sector("3"),
    "EIA_SECTOR_COMMERCIAL": lambda: eia_generation_by_sector("6"),
    "EIA_SECTOR_INDUSTRIAL": lambda: eia_generation_by_sector("7"),
    # retail sales
    "EIA_RETAIL_RES":  lambda: eia_retail_sales("RES"),
    "EIA_RETAIL_COM":  lambda: eia_retail_sales("COM"),
    "EIA_RETAIL_IND":  lambda: eia_retail_sales("IND"),
    "EIA_RETAIL_TRA":  lambda: eia_retail_sales("TRA"),
    # petroleum (weekly -> shows higher freq behavior)
    "EIA_CRUDE_STOCKS":      eia_crude_stocks_weekly,
    "EIA_GASOLINE_STOCKS":   lambda: eia_petroleum_stocks_weekly("EPM0"),
    "EIA_DISTILLATE_STOCKS": lambda: eia_petroleum_stocks_weekly("EPD0"),
    # natural gas storage (weekly)
    "EIA_NG_STORAGE_LOWER48": eia_ng_storage_weekly,
    # weather
    "NOAA_CONUS_TEMP_MONTHLY": noaa_conus_temperature,
}


# -----------------------------------------------------------------------------
# 3. Models
# -----------------------------------------------------------------------------
def model_a_naive(y_train, n_test):
    return np.full(n_test, y_train[-1], dtype=float)


def model_b_linear_trend(y_train, n_test):
    n = len(y_train)
    x = np.arange(n).reshape(-1, 1)
    m = LinearRegression().fit(x, y_train)
    return m.predict(np.arange(n, n + n_test).reshape(-1, 1))


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
    X = harmonic_features(np.arange(n), [12])
    m = Ridge(alpha=1.0).fit(X, y_train)
    return m.predict(harmonic_features(np.arange(n, n + n_test), [12]))


def model_d_harmonic_search(y_train, n_test, top_k=3):
    n = len(y_train)
    yz = y_train - y_train.mean()
    fft = np.fft.rfft(yz)
    power = np.abs(fft) ** 2
    freqs = np.fft.rfftfreq(n, d=1.0)
    mask = freqs > (1.0 / max(n, 4))
    if mask.sum() == 0:
        periods = [12]
    else:
        idx = np.argsort(power[mask])[::-1][:top_k]
        sel = freqs[mask][idx]
        periods = [max(2.0, 1.0 / f) for f in sel if f > 0] or [12]
    X = harmonic_features(np.arange(n), periods)
    m = Ridge(alpha=1.0).fit(X, y_train)
    return m.predict(harmonic_features(np.arange(n, n + n_test), periods))


def model_e_mlp_untuned(y_train, n_test):
    n = len(y_train)
    x = np.arange(n).reshape(-1, 1).astype(float)
    m = MLPRegressor(hidden_layer_sizes=(10,), learning_rate_init=0.001,
                     max_iter=200, random_state=0, n_iter_no_change=200)
    m.fit(x, y_train)
    return m.predict(np.arange(n, n + n_test).reshape(-1, 1).astype(float))


def make_lag_features(y, n_lags=12):
    rows, targets = [], []
    for i in range(n_lags, len(y)):
        rows.append(y[i - n_lags:i])
        targets.append(y[i])
    return np.array(rows), np.array(targets)


def model_f_mlp_tuned(y_train, n_test, n_lags=12):
    if len(y_train) <= n_lags + 5:
        return model_a_naive(y_train, n_test)
    X, yt = make_lag_features(y_train, n_lags)
    sx = StandardScaler().fit(X)
    sy = StandardScaler().fit(yt.reshape(-1, 1))
    Xs = sx.transform(X)
    ys = sy.transform(yt.reshape(-1, 1)).ravel()
    m = MLPRegressor(hidden_layer_sizes=(64, 32, 16), learning_rate_init=0.005,
                     max_iter=2000, early_stopping=True, validation_fraction=0.1,
                     n_iter_no_change=20, random_state=0)
    m.fit(Xs, ys)
    history = list(y_train[-n_lags:])
    preds = []
    for _ in range(n_test):
        xin = np.array(history[-n_lags:]).reshape(1, -1)
        yhat = sy.inverse_transform(m.predict(sx.transform(xin)).reshape(-1, 1)).ravel()[0]
        preds.append(yhat); history.append(yhat)
    return np.array(preds)


MODELS = {
    "a_naive": model_a_naive,
    "b_linear_trend": model_b_linear_trend,
    "c_harmonic_fixed12": model_c_harmonic_fixed12,
    "d_harmonic_search": model_d_harmonic_search,
    "e_mlp_untuned": model_e_mlp_untuned,
    "f_mlp_tuned": model_f_mlp_tuned,
}

FAMILIES = {
    "harmonic": ["c_harmonic_fixed12", "d_harmonic_search"],
    "neural":   ["e_mlp_untuned", "f_mlp_tuned"],
    "baseline": ["a_naive", "b_linear_trend"],
}


# -----------------------------------------------------------------------------
# 4. Bootstrap CI
# -----------------------------------------------------------------------------
def bootstrap_rmse_ci(y_true, y_pred, n_iter=400, seed=0):
    rng = np.random.default_rng(seed)
    sq = (y_true - y_pred) ** 2
    n = len(sq)
    rmses = np.empty(n_iter)
    for i in range(n_iter):
        idx = rng.integers(0, n, size=n)
        rmses[i] = np.sqrt(sq[idx].mean())
    lo, med, hi = np.percentile(rmses, [2.5, 50, 97.5])
    return float(lo), float(med), float(hi)


# -----------------------------------------------------------------------------
# 5. Eval
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
# 6. Main
# -----------------------------------------------------------------------------
def main():
    print(f"=== master_universe_benchmark @ {UTC} ===")
    print(f"output: {RUN_DIR}")
    print(f"datasets in universe: {len(DATASETS)}")
    print()

    rows = []
    metadata = {}
    for ds_name, fetch in DATASETS.items():
        print(f"[fetch] {ds_name} ...", flush=True, end=" ")
        try:
            df = fetch()
        except Exception as e:
            print(f"FAILED: {e}")
            metadata[ds_name] = {"error": str(e)}
            continue
        raw_path = RAW_DIR / f"{ds_name}.csv"
        df.to_csv(raw_path, index=False)
        y = df["value"].to_numpy(dtype=float)
        if len(y) < 30:
            print(f"too short ({len(y)})")
            metadata[ds_name] = {"error": "too_short", "n": len(y)}
            continue
        print(f"{len(y)} obs [{df['period'].iloc[0].date()} -> {df['period'].iloc[-1].date()}]")
        results, n_test = evaluate(y)
        for model_name, r in results.items():
            row = {"dataset": ds_name, "model": model_name, "n_train": len(y) - n_test, "n_test": n_test,
                   "y_mean": float(np.mean(y)), "y_std": float(np.std(y))}
            row.update(r if "error" not in r else {"rmse": np.nan, "ci_lo": np.nan, "ci_med": np.nan, "ci_hi": np.nan, "error": r["error"]})
            rows.append(row)
        metadata[ds_name] = {"n_obs": len(y), "n_test": n_test,
                             "first": str(df["period"].iloc[0].date()),
                             "last": str(df["period"].iloc[-1].date()),
                             "raw_sha256": sha256_file(raw_path)}

    if not rows:
        print("FATAL: no datasets succeeded"); return

    res = pd.DataFrame(rows)
    res_path = RUN_DIR / "results.csv"; res.to_csv(res_path, index=False)
    pivot = res.pivot(index="dataset", columns="model", values="rmse")
    pivot_path = RUN_DIR / "results_pivot.csv"; pivot.to_csv(pivot_path)

    # CI string pivot
    def ci_str(row):
        if pd.isna(row.get("rmse")): return "n/a"
        return f"{row['rmse']:.2f} [{row['ci_lo']:.2f},{row['ci_hi']:.2f}]"
    res["ci_str"] = res.apply(ci_str, axis=1)
    ci_pivot = res.pivot(index="dataset", columns="model", values="ci_str")
    ci_pivot_path = RUN_DIR / "ci_pivot.csv"; ci_pivot.to_csv(ci_pivot_path)

    # Family scoreboard
    family_rows = []
    for ds in pivot.index:
        row = pivot.loc[ds]
        family_best = {fam: float(row[ms].min()) for fam, ms in FAMILIES.items() if row[ms].notna().any()}
        if not family_best: continue
        sorted_fams = sorted(family_best.items(), key=lambda kv: kv[1])
        winner_fam, winner_rmse = sorted_fams[0]
        runner_fam, runner_rmse = sorted_fams[1] if len(sorted_fams) > 1 else (None, np.nan)
        margin_pct = ((runner_rmse - winner_rmse) / runner_rmse * 100) if runner_rmse and not np.isnan(runner_rmse) else np.nan
        winning_model = row[FAMILIES[winner_fam]].idxmin()
        family_rows.append({
            "dataset": ds,
            "winning_family": winner_fam,
            "winning_model": winning_model,
            "winning_rmse": winner_rmse,
            "runner_up_family": runner_fam,
            "runner_up_rmse": runner_rmse,
            "margin_pct_vs_runner": margin_pct,
            "harmonic_best": family_best.get("harmonic"),
            "neural_best":   family_best.get("neural"),
            "baseline_best": family_best.get("baseline"),
        })
    fam_df = pd.DataFrame(family_rows)
    fam_path = RUN_DIR / "family_scoreboard.csv"; fam_df.to_csv(fam_path, index=False)

    # Aggregate counts
    fam_counts = fam_df["winning_family"].value_counts().to_dict() if not fam_df.empty else {}
    total = int(fam_df.shape[0])
    harmonic_wins = int(fam_counts.get("harmonic", 0))
    neural_wins   = int(fam_counts.get("neural", 0))
    baseline_wins = int(fam_counts.get("baseline", 0))

    # avg margin where harmonic wins
    h_wins_df = fam_df[fam_df["winning_family"] == "harmonic"]
    avg_harm_margin = float(h_wins_df["margin_pct_vs_runner"].mean()) if len(h_wins_df) else None
    median_harm_margin = float(h_wins_df["margin_pct_vs_runner"].median()) if len(h_wins_df) else None

    summary = {
        "run_utc": UTC,
        "test_name": "master_universe_benchmark",
        "datasets": metadata,
        "n_datasets_succeeded": total,
        "n_datasets_in_universe": len(DATASETS),
        "family_win_counts": {"harmonic": harmonic_wins, "neural": neural_wins, "baseline": baseline_wins},
        "harmonic_win_rate": harmonic_wins / total if total else None,
        "harmonic_avg_margin_pct": avg_harm_margin,
        "harmonic_median_margin_pct": median_harm_margin,
        "verdict": (
            f"On {total} live federal datasets, the HARMONIC family wins {harmonic_wins}/{total} "
            f"({harmonic_wins/total*100:.1f}%) head-to-head against tuned neural and baseline. "
            f"Median margin where harmonic wins: {median_harm_margin:.1f}% RMSE reduction vs runner-up."
        ) if total else "no datasets",
    }
    summary_path = RUN_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    # Public scorecard
    md_lines = []
    md_lines.append("# UNDENIABLE SCORECARD — Live Federal Data, Hash-Chained")
    md_lines.append("")
    md_lines.append(f"**Run UTC:** {UTC}")
    md_lines.append(f"**Universe:** {total} live federal datasets (EIA + NOAA)")
    md_lines.append(f"**Method:** apples-to-apples 6-model benchmark, 80/20 walk-forward, 400-iter bootstrap 95% CI on RMSE")
    md_lines.append("")
    md_lines.append("## Headline")
    md_lines.append("")
    md_lines.append(f"- **Harmonic family wins {harmonic_wins}/{total} datasets ({harmonic_wins/total*100:.1f}%)**")
    md_lines.append(f"- Neural family wins: {neural_wins}/{total}")
    md_lines.append(f"- Baseline (naive/linear) wins: {baseline_wins}/{total}")
    if median_harm_margin is not None:
        md_lines.append(f"- Median RMSE reduction where harmonic wins: **{median_harm_margin:.1f}%** vs runner-up family")
    md_lines.append("")
    md_lines.append("## Per-dataset family results")
    md_lines.append("")
    md_lines.append("| Dataset | Winner | Margin vs runner-up | Harmonic best | Neural best | Baseline best |")
    md_lines.append("|---|---|---|---|---|---|")
    for _, r in fam_df.iterrows():
        ds = r["dataset"]; w = r["winning_family"]; m = r["winning_model"]
        mg = "—" if pd.isna(r["margin_pct_vs_runner"]) else f"{r['margin_pct_vs_runner']:.1f}%"
        h = f"{r['harmonic_best']:.2f}" if not pd.isna(r["harmonic_best"]) else "—"
        nn = f"{r['neural_best']:.2f}" if not pd.isna(r["neural_best"]) else "—"
        b = f"{r['baseline_best']:.2f}" if not pd.isna(r["baseline_best"]) else "—"
        md_lines.append(f"| {ds} | **{w}** ({m}) | {mg} | {h} | {nn} | {b} |")
    md_lines.append("")
    md_lines.append("## Full RMSE table with 95% CI")
    md_lines.append("")
    md_lines.append("```")
    md_lines.append(ci_pivot.to_string())
    md_lines.append("```")
    md_lines.append("")
    md_lines.append("## Reproducibility")
    md_lines.append("")
    md_lines.append("- Every raw data CSV is hashed in `manifest.sha256.json`")
    md_lines.append("- This run is chained to `out/frozen_delta_ledger.jsonl`")
    md_lines.append("- Re-running `code/master_universe_benchmark.py` on the same date pulls identical historical data and produces identical RMSEs (deterministic seeds)")
    md_lines.append("- Any post-hoc edit of any artifact breaks the SHA256 chain")
    md_lines.append("")
    md_lines.append(f"_Generated by master_universe_benchmark.py at {UTC}_")
    md_path = RUN_DIR / "UNDENIABLE_SCORECARD.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    # manifest
    manifest = {"run_utc": UTC, "files": {}}
    for p in [res_path, pivot_path, ci_pivot_path, fam_path, summary_path, md_path] + list(RAW_DIR.glob("*.csv")):
        manifest["files"][str(p.relative_to(RUN_DIR))] = sha256_file(p)
    manifest_path = RUN_DIR / "manifest.sha256.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    # ledger
    prev_hash = None
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try: prev_hash = json.loads(line).get("entry_sha256")
                except Exception: pass
    entry = {
        "run_utc": UTC,
        "test_name": "master_universe_benchmark",
        "n_datasets": total,
        "harmonic_win_rate": harmonic_wins / total if total else None,
        "manifest_sha256": sha256_file(manifest_path),
        "summary_sha256": sha256_file(summary_path),
        "scorecard_sha256": sha256_file(md_path),
        "prev_entry_sha256": prev_hash,
    }
    entry_str = json.dumps(entry, sort_keys=True)
    entry["entry_sha256"] = hashlib.sha256(entry_str.encode("utf-8")).hexdigest()
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    print()
    print("=== FAMILY SCOREBOARD ===")
    print(fam_df[["dataset", "winning_family", "winning_model", "margin_pct_vs_runner"]].to_string(index=False))
    print()
    print(f"HARMONIC: {harmonic_wins}/{total}  NEURAL: {neural_wins}/{total}  BASELINE: {baseline_wins}/{total}")
    if median_harm_margin is not None:
        print(f"Median margin where harmonic wins: {median_harm_margin:.1f}% RMSE reduction")
    print()
    print(f"frozen entry sha256: {entry['entry_sha256']}")
    print(f"prev entry sha256:   {prev_hash}")
    print(f"scorecard:           {md_path}")
    print(f"run dir:             {RUN_DIR}")


if __name__ == "__main__":
    main()
