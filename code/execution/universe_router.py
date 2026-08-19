import pandas as pd
import numpy as np
import json
import time
from pathlib import Path

UNIVERSE_FILE = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\live_universe_catalog.csv")
SIGNAL_FILE   = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\institutional_top10.csv")
MODE_FILE     = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\config\mode.json")

# -------------------------------------------------
# LOAD MODE (SHADOW / PAPER / LIVE)
# -------------------------------------------------
def load_mode():
    if not MODE_FILE.exists():
        return "SHADOW"
    try:
        mode = str(json.loads(MODE_FILE.read_text(encoding="utf-8")).get("mode", "SHADOW")).strip().upper()
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return "SHADOW"
    return mode if mode in {"SHADOW", "PAPER"} else "SHADOW"

# -------------------------------------------------
# DUMMY SIGNAL ENGINE (HOOK YOUR REAL ONE HERE)
# -------------------------------------------------
def score_symbol(symbol):
    # Replace this with your harmonic scoring engine
    return np.random.randn()

# -------------------------------------------------
# BUILD RANKED UNIVERSE
# -------------------------------------------------
def build_rankings(df):
    scores = []
    for sym in df["symbol"]:
        s = score_symbol(sym)
        scores.append((sym, s))

    ranked = pd.DataFrame(scores, columns=["symbol", "score"])
    ranked = ranked.sort_values("score", ascending=False)
    return ranked

# -------------------------------------------------
# ROUTER (TOP N)
# -------------------------------------------------
def select_top(ranked, n=5):
    return ranked.head(n)

# -------------------------------------------------
# EXECUTION INTERFACE (SAFE — NO LIVE TRADING)
# -------------------------------------------------
def execute_trade(symbol, signal, mode):
    normalized_mode = str(mode or "SHADOW").strip().upper()
    if normalized_mode == "SHADOW":
        print(f"[SHADOW] {symbol} | score={signal:.4f}")
        return {"status": "shadow", "symbol": str(symbol)}

    if normalized_mode == "PAPER":
        print(f"[PAPER] Simulated trade - {symbol}")
        return {"status": "paper", "symbol": str(symbol)}

    # This research router is intentionally non-executing. Live orders must enter
    # through the canonical runtime guard, sizing, approval, audit, and ledger path.
    print(f"[BLOCKED] Unsupported execution mode {normalized_mode!r} for {symbol}")
    return {
        "status": "blocked",
        "symbol": str(symbol),
        "reason": "canonical_live_execution_path_required",
    }

# -------------------------------------------------
# MAIN LOOP
# -------------------------------------------------
def main():
    if not UNIVERSE_FILE.exists():
        print("Universe file missing.")
        return

    df = pd.read_csv(UNIVERSE_FILE)

    print(f"Loaded universe: {len(df)} symbols")

    while True:
        mode = load_mode()

        ranked = build_rankings(df)
        top = select_top(ranked, n=5)

        top.to_csv(SIGNAL_FILE, index=False)

        print("\n=== TOP SYMBOLS ===")
        print(top)

        for _, row in top.iterrows():
            execute_trade(row["symbol"], row["score"], mode)

        time.sleep(10)

if __name__ == "__main__":
    main()
