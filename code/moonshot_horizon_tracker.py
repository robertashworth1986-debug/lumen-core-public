import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean, median

OUT_DIR = os.path.join("C:\\LumaTrader\\INSTITUTIONAL_STACK_V2\\code", "out", "execution")
HISTORY_PATH = os.path.join(OUT_DIR, "moonshot_dual_scan_history.jsonl")
OUT_PATH = os.path.join(OUT_DIR, "moonshot_horizon_performance.json")

HORIZONS_MIN = {
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "3h": 180,
    "8h": 480,
    "1d": 1440,
    "1w": 10080,
    "1m": 43200,
}


def parse_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return []
    rows = []
    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def flatten_events(history):
    events = defaultdict(list)
    for row in history:
        ts = parse_utc(row["generated_utc"])
        for ex in ["kraken", "binanceus"]:
            for t in row.get(ex, {}).get("top_targets", []):
                sym = f"{ex}:{t['symbol']}"
                events[sym].append({"ts": ts, "price": float(t["price"])})

    for sym in events:
        events[sym].sort(key=lambda x: x["ts"])
    return events


def forward_return(events, i, horizon_min):
    src = events[i]
    target_ts = src["ts"].timestamp() + horizon_min * 60
    src_price = src["price"]
    if src_price <= 0:
        return None

    for j in range(i + 1, len(events)):
        if events[j]["ts"].timestamp() >= target_ts:
            return (events[j]["price"] / src_price) - 1.0
    return None


def summarize(vals):
    if not vals:
        return {
            "samples": 0,
            "median_ret": None,
            "mean_ret": None,
            "best_ret": None,
            "worst_ret": None,
        }
    return {
        "samples": len(vals),
        "median_ret": median(vals),
        "mean_ret": mean(vals),
        "best_ret": max(vals),
        "worst_ret": min(vals),
    }


def main():
    history = load_history()
    events = flatten_events(history)

    by_exchange_h = {"kraken": {}, "binanceus": {}}

    for ex in by_exchange_h.keys():
        for h_name, h_min in HORIZONS_MIN.items():
            vals = []
            for sym, ev in events.items():
                if not sym.startswith(ex + ":"):
                    continue
                for i in range(len(ev) - 1):
                    r = forward_return(ev, i, h_min)
                    if r is not None and math.isfinite(r):
                        vals.append(r)
            by_exchange_h[ex][h_name] = summarize(vals)

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "history_rows": len(history),
        "symbols_tracked": len(events),
        "exchange_horizon_summary": by_exchange_h,
        "note": "As scan history grows, horizon sample counts and reliability improve.",
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print("HORIZON_TRACKER_DONE")
    print(f"history_rows={len(history)} symbols_tracked={len(events)} out={OUT_PATH}")


if __name__ == "__main__":
    main()
