from dataclasses import dataclass
from datetime import datetime, timezone
import csv
import os

@dataclass
class ShadowFill:
    ts_utc: str
    symbol: str
    side: str
    qty: float
    est_fill: float
    slip_bps: float
    mode: str = "shadow"

class ShadowRunner:
    def simulate_fill(self, bid: float, ask: float, side: str, urgency: str) -> tuple:
        mid = (bid + ask) / 2
        if side == "buy":
            px = ask if urgency != "passive" else mid + (ask - bid) * 0.25
        else:
            px = bid if urgency != "passive" else mid - (ask - bid) * 0.25
        slip_bps = ((px - mid) / max(mid, 1e-9)) * 10000
        return float(px), float(slip_bps)

    def append_ledger(self, path: str, fill: ShadowFill) -> None:
        exists = os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["ts_utc","symbol","side","qty","est_fill","slip_bps","mode"])
            w.writerow([fill.ts_utc, fill.symbol, fill.side, fill.qty, fill.est_fill, fill.slip_bps, fill.mode])
