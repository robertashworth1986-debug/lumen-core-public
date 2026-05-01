import os
import json
import hashlib
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

from institutional_harmonic_core import (
    FLOWFORMS,
    STRATEGIES,
    get_price_series,
    evaluate_combo,
)

ROOT = r"C:\LumaTrader"
STACK = r"C:\LumaTrader\INSTITUTIONAL_STACK_V2"
OUT_DIR = os.path.join(STACK, "out")
DATA_DIR = os.path.join(ROOT, "data")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

FRED_API_KEY = os.environ.get("FRED_API_KEY", "").strip()
EIA_API_KEY  = os.environ.get("EIA_API_KEY", "").strip()

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

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
        "facets[type][]": "D",
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
    candidates = [
        os.path.join(DATA_DIR, "kraken_live_5000.csv"),
        os.path.join(DATA_DIR, "kraken_ohlc.csv"),
        os.path.join(DATA_DIR, "kraken_live.csv"),
    ]
    for path in candidates:
        if os.path.exists(path):
            df = pd.read_csv(path)
            if "time" in df.columns and "close" in df.columns:
                df["date"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
                df["value"] = pd.to_numeric(df["close"], errors="coerce")
                df = df.dropna(subset=["date","value"]).copy()
                return df, path
    raise RuntimeError("No Kraken CSV found in C:\\LumaTrader\\data")

def institutional_score_from_row(row):
    test_sharpe      = float(row.get("test_sharpe", 0.0))
    test_calmar      = float(row.get("test_calmar", 0.0))
    test_expectancy  = float(row.get("test_expectancy", 0.0))
    test_win_rate    = float(row.get("test_win_rate", 0.0))
    stability        = float(row.get("stability", 0.0))
    test_vs_baseline = float(row.get("test_vs_baseline", 0.0))
    test_max_dd      = abs(float(row.get("test_max_dd", 0.0)))
    test_vol         = float(row.get("test_vol", 0.0))
    return (
        test_sharpe * 4.0
        + test_calmar * 2.0
        + test_expectancy * 150.0
        + test_win_rate * 2.0
        + stability * 1.5
        + test_vs_baseline * 3.0
        - test_max_dd * 5.0
        - test_vol * 0.5
    )

def evaluate_dataset(stack_name, file_path):
    rows = []
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return rows, {"stack": stack_name, "file": file_path, "error": str(e)}

    series = get_price_series(df)
    if series is None:
        if {"date","value"}.issubset(set(df.columns)):
            temp = pd.DataFrame({"close": pd.to_numeric(df["value"], errors="coerce")})
            series = get_price_series(temp)
        else:
            return rows, {"stack": stack_name, "file": file_path, "error": "No usable price/value series"}

    if series is None:
        return rows, {"stack": stack_name, "file": file_path, "error": "Series extraction failed"}

    for flow_name, flow_fn in FLOWFORMS.items():
        for strat_name, strat_fn in STRATEGIES.items():
            try:
                row = evaluate_combo(series, flow_name, flow_fn, strat_name, strat_fn)
                if row is None:
                    continue
                row["stack"] = stack_name
                row["file"] = file_path
                if "institutional_score" not in row:
                    row["institutional_score"] = institutional_score_from_row(row)
                rows.append(row)
            except Exception:
                continue

    return rows, None

def money_ladder():
    hours = [1, 6, 12, 24, 72, 168, 720]
    losses_per_hour = [1000, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000]
    out = []
    for lph in losses_per_hour:
        for h in hours:
            out.append({
                "loss_per_hour_usd": lph,
                "hours": h,
                "avoided_loss_usd": lph * h
            })
    return pd.DataFrame(out)

def save_empty(path):
    cols = [
        "stack","file","flow","strategy",
        "train_sharpe","test_sharpe",
        "train_max_dd","test_max_dd",
        "train_cagr","test_cagr",
        "train_calmar","test_calmar",
        "test_win_rate","test_expectancy","test_vol",
        "test_final","baseline_final","test_vs_baseline",
        "stability","institutional_score"
    ]
    pd.DataFrame(columns=cols).to_csv(path, index=False)

def main():
    artifacts = {}
    all_rows = []
    errors = []

    kraken_df, kraken_path = load_kraken()
    artifacts["kraken_source"] = {"path": kraken_path, "sha256": sha256_file(kraken_path)}
    rows, err = evaluate_dataset("kraken_market", kraken_path)
    all_rows.extend(rows)
    if err:
        errors.append(err)

    fred_targets = {
        "DGS10": "10Y Treasury",
        "UNRATE": "Unemployment",
        "CPIAUCSL": "CPI"
    }

    for sid in fred_targets:
        try:
            fred_df = fetch_fred_series(sid)
            fred_path = os.path.join(DATA_DIR, f"fred_{sid}.csv")
            fred_df.to_csv(fred_path, index=False)
            artifacts[f"fred_{sid}"] = {"path": fred_path, "sha256": sha256_file(fred_path)}

            temp = fred_df.rename(columns={"value": "close"})
            rows, err = evaluate_dataset(f"fred_{sid}", fred_path)
            all_rows.extend(rows)
            if err:
                errors.append(err)
        except Exception as e:
            artifacts[f"fred_{sid}"] = {"error": str(e)}
            errors.append({"stack": f"fred_{sid}", "error": str(e)})

    try:
        eia_df = fetch_eia_rto_daily()
        eia_path = os.path.join(DATA_DIR, "eia_rto_daily.csv")
        eia_df.to_csv(eia_path, index=False)
        artifacts["eia_rto_daily"] = {"path": eia_path, "sha256": sha256_file(eia_path)}
        rows, err = evaluate_dataset("eia_rto_daily", eia_path)
        all_rows.extend(rows)
        if err:
            errors.append(err)
    except Exception as e:
        artifacts["eia_rto_daily"] = {"error": str(e)}
        errors.append({"stack": "eia_rto_daily", "error": str(e)})

    leaderboard_path = os.path.join(OUT_DIR, "institutional_harmonic_infrastructure_leaderboard.csv")
    champs_path      = os.path.join(OUT_DIR, "institutional_harmonic_infrastructure_champions.csv")
    ladder_path      = os.path.join(OUT_DIR, "infrastructure_money_loss_ladder.csv")
    proof_path       = os.path.join(OUT_DIR, "institutional_harmonic_infrastructure_proof.json")

    if len(all_rows) == 0:
        save_empty(leaderboard_path)
        save_empty(champs_path)
        summary = {"timestamp_utc": utc_now(), "rows": 0, "errors": errors}
    else:
        df = pd.DataFrame(all_rows).sort_values(
            ["institutional_score", "test_sharpe", "test_vs_baseline"],
            ascending=False
        )
        df.to_csv(leaderboard_path, index=False)

        champs = df.groupby(["stack","flow","strategy"], as_index=False).first()
        champs.to_csv(champs_path, index=False)

        summary = {
            "timestamp_utc": utc_now(),
            "rows": int(len(df)),
            "top_stack": str(df.iloc[0]["stack"]),
            "top_flow": str(df.iloc[0]["flow"]),
            "top_strategy": str(df.iloc[0]["strategy"]),
            "top_test_sharpe": float(df.iloc[0]["test_sharpe"]),
            "top_test_vs_baseline": float(df.iloc[0]["test_vs_baseline"]),
            "top_institutional_score": float(df.iloc[0]["institutional_score"]),
            "errors": errors,
        }

    money_ladder().to_csv(ladder_path, index=False)

    proof = {
        "timestamp_utc": utc_now(),
        "artifacts": artifacts,
        "summary": summary,
        "core_file": os.path.join(os.path.dirname(__file__), "institutional_harmonic_core.py"),
        "suite_file": os.path.join(os.path.dirname(__file__), "institutional_harmonic_suite.py"),
    }

    with open(proof_path, "w", encoding="utf-8") as f:
        json.dump(proof, f, indent=2)

    print("=== CORE MERGE COMPLETE ===")
    print("Saved:")
    print(leaderboard_path)
    print(champs_path)
    print(ladder_path)
    print(proof_path)

if __name__ == "__main__":
    main()