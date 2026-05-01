import pandas as pd
import json
import time
import os
import sys

INPUT_PATH = r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\institutional_top10.csv"
OUTPUT_PATH = r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\adaptive_champion.json"

if not os.path.exists(INPUT_PATH):
    print("Adaptive engine: input file missing, skipping update.")
    sys.exit(0)

try:
    df = pd.read_csv(INPUT_PATH)
except Exception as exc:
    print(f"Adaptive engine: failed to read input file: {exc}")
    sys.exit(0)

if "test_sharpe" not in df.columns:
    print("Adaptive engine: required column 'test_sharpe' not found, skipping update.")
    sys.exit(0)

if df.empty:
    print("Adaptive engine: no rows found in institutional_top10.csv, skipping update.")
    sys.exit(0)

best = df.sort_values("test_sharpe", ascending=False).iloc[0]

deploy = {
    "timestamp": time.time(),
    "flow": best.get("flow", "unknown"),
    "strategy": best.get("strategy", "unknown"),
    "sharpe": float(best["test_sharpe"]),
    "vs_baseline": float(best.get("test_vs_baseline", 0.0))
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(deploy, f, indent=2)

print("Updated Adaptive Champion")
