import pandas as pd
import json
import time
import os
import sys
from pathlib import Path

ROOT = Path(os.getenv("LUMA_ROOT", str(Path(__file__).resolve().parents[1]))).resolve()
INPUT_PATH = Path(os.getenv("LUMA_ADAPTIVE_INPUT", str(ROOT / "out" / "institutional_top10.csv"))).resolve()
OUTPUT_PATH = Path(os.getenv("LUMA_ADAPTIVE_OUTPUT", str(ROOT / "out" / "adaptive_champion.json"))).resolve()

if not INPUT_PATH.exists():
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
    "vs_baseline": float(best.get("test_vs_baseline", 0.0)),
    "source_path": str(INPUT_PATH),
}

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(deploy, f, indent=2)

print(f"Updated Adaptive Champion -> {OUTPUT_PATH}")
