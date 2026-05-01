import os
import json
import math
import hashlib
from datetime import datetime, timezone

import requests
import numpy as np
import pandas as pd

ROOT = r"C:\LumaTrader"
STACK = r"C:\LumaTrader\INSTITUTIONAL_STACK_V2"
OUT_DIR = os.path.join(STACK, "out")
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

FRED_API_KEY = os.environ.get("FRED_API_KEY", "").strip()
EIA_API_KEY = os.environ.get("EIA_API_KEY", "").strip()

ANNUALIZATION = 252.0

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sharpe(r):
    r = pd.Series(r).dropna()
    if len(r) < 2:
        return 0.0
    s = float(r.std(ddof=0))
    if s <= 1e-12:
        return 0.0
    return float((r.mean() / s) * np.sqrt(ANNUALIZATION))

def max_dd(eq):
    eq = pd.Series(eq).dropna()
    if len(eq) < 2:
        return 0.0
    peak = eq.cummax()
    dd = eq / peak - 1.0
    return float(dd.min())

def cagr(eq):
    eq = pd.Series(eq).dropna()
    if len(eq) < 2:
        return 0.0
    start = float(eq.iloc[0])
    end = float(eq.iloc[-1])
    if start <= 0 or end <= 0:
        return 0.0
    years = len(eq) / ANNUALIZATION
    if years <= 0:
        return 0.0
    return float((end / start) ** (1.0 / years) - 1.0)

def calmar(eq):
    dd = abs(max_dd(eq))
    if dd <= 1e-12:
        return 0.0
    return float(cagr(eq) / dd)

def win_rate(r):
    r = pd.Series(r).dropna()
    if len(r) == 0:
        return 0.0
    return float((r > 0).mean())

def expectancy(r):
    r = pd.Series(r).dropna()
    if len(r) == 0:
        return 0.0
    w = r[r > 0]
    l = r[r < 0]
    pw = float((r > 0).mean())
    pl = float((r < 0).mean())
    aw = float(w.mean()) if len(w) else 0.0
    al = float(l.mean()) if len(l) else 0.0
    return float((pw * aw) + (pl * al))

def annual_vol(r):
    r = pd.Series(r).dropna()
    if len(r) < 2:
        return 0.0
    return float(r.std(ddof=0) * np.sqrt(ANNUALIZATION))

def stability(eq):
    eq = pd.Series(eq).dropna()
    if len(eq) < 10:
        return 0.0
    x = np.arange(len(eq), dtype=float)
    y = np.log(eq.clip(lower=1e-9).values)
    if len(np.unique(y)) < 2:
        return 0.0
    corr = np.corrcoef(x, y)[0, 1]
    if np.isnan(corr):
        return 0.0
    return float(max(corr, 0.0))

def metric_score(m):
    return float(
        m["test_sharpe"] * 4.0
        + m["test_calmar"] * 2.0
        + m["test_expectancy"] * 150.0
        + m["test_win_rate"] * 2.0
        + m["stability"] * 1.5
        + m["test_vs_baseline"] * 3.0
        - abs(m["test_max_dd"]) * 5.0
        - m["test_vol"] * 0.5
    )

def fetch_fred_series(series_id):
    if not FRED_API_KEY:
        raise RuntimeError("Missing FRED_API_KEY in environment")
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "asc"
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    j = r.json()
    obs = j.get("observations", [])
    df = pd.DataFrame(obs)
    if len(df) == 0:
        return pd.DataFrame(columns=["date","value"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date","value"]).copy()
    return df[["date","value"]]

def fetch_eia_rto_daily():
    if not EIA_API_KEY:
        raise RuntimeError("Missing EIA_API_KEY in environment")
    url = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
    params = {
        "api_key": EIA_API_KEY,
        "frequency": "daily",
        "data[0]": "value",
        "facets[type][]" : "D",
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000
    }
    r = requests.get(url, params=params, timeout=45)
    r.raise_for_status()
    j = r.json()
    data = j.get("response", {}).get("data", [])
    df = pd.DataFrame(data)
    if len(df) == 0:
        return pd.DataFrame(columns=["date","value"])
    df["date"] = pd.to_datetime(df["period"], errors="coerce", utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date","value"]).copy()
    return df[["date","value"]]

def load_kraken():
    path = os.path.join(DATA_DIR, "kraken_live_5000.csv")
    if not os.path.exists(path):
        raise RuntimeError(f"Missing {path}")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
    df["value"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["date","value"]).copy()
    return df[["date","value"]], path

def normalize_series(df):
    s = pd.Series(pd.to_numeric(df["value"], errors="coerce").values).dropna().reset_index(drop=True)
    return s

def split_series(s, ratio=0.70):
    split = int(len(s) * ratio)
    return s.iloc[:split], s.iloc[split:]

def flow_identity(x): return pd.Series(1.0, index=x.index)
def flow_golden_ratio(x): return pd.Series(1.618, index=x.index)
def flow_fibonacci(x):
    fib = np.array([1,1,2,3,5,8,13,21], dtype=float)
    vals = np.resize(fib / fib.max(), len(x))
    return pd.Series(vals, index=x.index)
def flow_log_spiral(x):
    t = np.arange(len(x), dtype=float)
    vals = np.exp(0.002 * t)
    vals = vals / max(vals.mean(), 1e-9)
    return pd.Series(vals, index=x.index)
def flow_helix(x):
    t = np.linspace(0, 8 * np.pi, len(x))
    return pd.Series(1.0 + 0.25 * np.sin(t), index=x.index)
def flow_sine(x):
    t = np.linspace(0, 6 * np.pi, len(x))
    return pd.Series(1.0 + 0.3 * np.sin(t), index=x.index)
def flow_cosine(x):
    t = np.linspace(0, 6 * np.pi, len(x))
    return pd.Series(1.0 + 0.3 * np.cos(t), index=x.index)
def flow_gaussian(x):
    z = (x - x.rolling(20).mean()) / (x.rolling(20).std() + 1e-9)
    vals = np.exp(-0.5 * z.fillna(0.0) ** 2)
    vals = vals / max(vals.mean(), 1e-9)
    return pd.Series(vals, index=x.index)
def flow_power_law(x):
    t = np.arange(1, len(x) + 1, dtype=float)
    vals = 1.0 / np.power(t, 0.15)
    vals = vals / max(vals.mean(), 1e-9)
    return pd.Series(vals, index=x.index)
def flow_interference(x):
    t = np.linspace(0, 6 * np.pi, len(x))
    vals = 1.0 + 0.2 * (np.sin(t) + np.sin(1.618 * t))
    return pd.Series(vals, index=x.index)

FLOWS = {
    "identity": flow_identity,
    "golden_ratio": flow_golden_ratio,
    "fibonacci": flow_fibonacci,
    "log_spiral": flow_log_spiral,
    "helix": flow_helix,
    "sine": flow_sine,
    "cosine": flow_cosine,
    "gaussian": flow_gaussian,
    "power_law": flow_power_law,
    "interference": flow_interference,
}

def strat_trend(r):
    fast = r.rolling(5).mean()
    slow = r.rolling(20).mean()
    sig = np.where(fast > slow, 1.0, -1.0)
    return pd.Series(sig, index=r.index).shift(1).fillna(0.0)

def strat_mean_revert(r):
    z = (r - r.rolling(20).mean()) / (r.rolling(20).std() + 1e-9)
    sig = np.where(z < -1.0, 1.0, np.where(z > 1.0, -1.0, 0.0))
    return pd.Series(sig, index=r.index).shift(1).fillna(0.0)

def strat_breakout(r):
    hi = r.rolling(20).max()
    lo = r.rolling(20).min()
    sig = np.where(r >= hi, 1.0, np.where(r <= lo, -1.0, 0.0))
    return pd.Series(sig, index=r.index).shift(1).fillna(0.0)

def strat_regime_switch(r):
    fast_vol = r.rolling(5).std()
    slow_vol = r.rolling(20).std()
    a = strat_trend(r)
    b = strat_mean_revert(r)
    return pd.Series(np.where(fast_vol > slow_vol, a, b), index=r.index).fillna(0.0)

def strat_harmonic_blend(r):
    a = strat_trend(r)
    b = strat_mean_revert(r)
    c = strat_breakout(r)
    return pd.Series(np.sign(a + b + c), index=r.index).fillna(0.0)

STRATS = {
    "trend": strat_trend,
    "mean_revert": strat_mean_revert,
    "breakout": strat_breakout,
    "regime_switch": strat_regime_switch,
    "harmonic_blend": strat_harmonic_blend,
}

def evaluate_stack(name, s):
    s = pd.to_numeric(s, errors="coerce").dropna().reset_index(drop=True)
    if len(s) < 180:
        return []

    r = s.pct_change().dropna()
    if len(r) < 120:
        return []

    tr_r, te_r = split_series(r)

    if len(tr_r) < 40 or len(te_r) < 40:
        return []

    rows = []

    for flow_name, flow_fn in FLOWS.items():
        tr_flow = flow_fn(tr_r).reindex(tr_r.index).fillna(1.0)
        te_flow = flow_fn(te_r).reindex(te_r.index).fillna(1.0)

        for strat_name, strat_fn in STRATS.items():
            tr_sig = strat_fn(tr_r).reindex(tr_r.index).fillna(0.0)
            te_sig = strat_fn(te_r).reindex(te_r.index).fillna(0.0)

            tr_ret = tr_sig * tr_r * tr_flow
            te_ret = te_sig * te_r * te_flow

            tr_eq = (1.0 + tr_ret).cumprod()
            te_eq = (1.0 + te_ret).cumprod()
            te_base = (1.0 + te_r).cumprod()

            m = {
                "stack": name,
                "flow": flow_name,
                "strategy": strat_name,
                "train_sharpe": sharpe(tr_ret),
                "test_sharpe": sharpe(te_ret),
                "train_max_dd": max_dd(tr_eq),
                "test_max_dd": max_dd(te_eq),
                "train_cagr": cagr(tr_eq),
                "test_cagr": cagr(te_eq),
                "train_calmar": calmar(tr_eq),
                "test_calmar": calmar(te_eq),
                "test_win_rate": win_rate(te_ret),
                "test_expectancy": expectancy(te_ret),
                "test_vol": annual_vol(te_ret),
                "test_final": float(te_eq.iloc[-1]) if len(te_eq) else 0.0,
                "baseline_final": float(te_base.iloc[-1]) if len(te_base) else 0.0,
                "test_vs_baseline": float(te_eq.iloc[-1] - te_base.iloc[-1]) if len(te_eq) and len(te_base) else 0.0,
                "stability": stability(te_eq),
            }
            m["institutional_score"] = metric_score(m)
            rows.append(m)

    return rows

def money_ladder():
    hours = [1, 6, 12, 24, 72, 168, 720]
    losses_per_hour = [1000, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000]
    rows = []
    for lph in losses_per_hour:
        for h in hours:
            rows.append({
                "loss_per_hour_usd": lph,
                "hours": h,
                "avoided_loss_usd": lph * h
            })
    return pd.DataFrame(rows)

def main():
    artifacts = {}

    kraken_df, kraken_path = load_kraken()
    artifacts["kraken_source"] = {"path": kraken_path, "sha256": sha256_file(kraken_path)}

    fred_targets = {
        "DGS10": "10Y Treasury",
        "UNRATE": "Unemployment",
        "CPIAUCSL": "CPI"
    }

    fred_frames = {}
    for sid in fred_targets:
        try:
            fred_frames[sid] = fetch_fred_series(sid)
            outp = os.path.join(DATA_DIR, f"fred_{sid}.csv")
            fred_frames[sid].to_csv(outp, index=False)
            artifacts[f"fred_{sid}"] = {"path": outp, "sha256": sha256_file(outp)}
        except Exception as e:
            fred_frames[sid] = pd.DataFrame(columns=["date","value"])
            artifacts[f"fred_{sid}"] = {"error": str(e)}

    try:
        eia_df = fetch_eia_rto_daily()
        eia_path = os.path.join(DATA_DIR, "eia_rto_daily.csv")
        eia_df.to_csv(eia_path, index=False)
        artifacts["eia_rto_daily"] = {"path": eia_path, "sha256": sha256_file(eia_path)}
    except Exception as e:
        eia_df = pd.DataFrame(columns=["date","value"])
        artifacts["eia_rto_daily"] = {"error": str(e)}

    all_rows = []
    all_rows.extend(evaluate_stack("kraken_market", normalize_series(kraken_df)))

    for sid, df in fred_frames.items():
        if len(df):
            all_rows.extend(evaluate_stack(f"fred_{sid}", normalize_series(df)))

    if len(eia_df):
        all_rows.extend(evaluate_stack("eia_rto_daily", normalize_series(eia_df)))

    leaderboard = pd.DataFrame(all_rows)
    if len(leaderboard):
        leaderboard = leaderboard.sort_values(
            ["institutional_score", "test_sharpe", "test_vs_baseline"],
            ascending=False
        )
        leaderboard_path = os.path.join(OUT_DIR, "institutional_harmonic_infrastructure_leaderboard.csv")
        leaderboard.to_csv(leaderboard_path, index=False)

        champs = leaderboard.groupby(["stack","flow","strategy"], as_index=False).first()
        champs_path = os.path.join(OUT_DIR, "institutional_harmonic_infrastructure_champions.csv")
        champs.to_csv(champs_path, index=False)

        summary = {
            "timestamp_utc": utc_now(),
            "rows": int(len(leaderboard)),
            "top_stack": str(leaderboard.iloc[0]["stack"]),
            "top_flow": str(leaderboard.iloc[0]["flow"]),
            "top_strategy": str(leaderboard.iloc[0]["strategy"]),
            "top_test_sharpe": float(leaderboard.iloc[0]["test_sharpe"]),
            "top_test_vs_baseline": float(leaderboard.iloc[0]["test_vs_baseline"]),
            "top_institutional_score": float(leaderboard.iloc[0]["institutional_score"]),
        }
    else:
        leaderboard_path = os.path.join(OUT_DIR, "institutional_harmonic_infrastructure_leaderboard.csv")
        pd.DataFrame(columns=[
            "stack","flow","strategy","train_sharpe","test_sharpe","train_max_dd","test_max_dd",
            "train_cagr","test_cagr","train_calmar","test_calmar","test_win_rate","test_expectancy",
            "test_vol","test_final","baseline_final","test_vs_baseline","stability","institutional_score"
        ]).to_csv(leaderboard_path, index=False)
        champs_path = os.path.join(OUT_DIR, "institutional_harmonic_infrastructure_champions.csv")
        pd.DataFrame().to_csv(champs_path, index=False)
        summary = {"timestamp_utc": utc_now(), "rows": 0}

    ladder = money_ladder()
    ladder_path = os.path.join(OUT_DIR, "infrastructure_money_loss_ladder.csv")
    ladder.to_csv(ladder_path, index=False)

    proof = {
        "timestamp_utc": utc_now(),
        "artifacts": artifacts,
        "summary": summary
    }
    proof_path = os.path.join(OUT_DIR, "institutional_harmonic_infrastructure_proof.json")
    with open(proof_path, "w", encoding="utf-8") as f:
        json.dump(proof, f, indent=2)

    print("=== INFRASTRUCTURE STACK COMPLETE ===")
    print("Saved:")
    print(leaderboard_path)
    print(champs_path)
    print(ladder_path)
    print(proof_path)

if __name__ == "__main__":
    main()