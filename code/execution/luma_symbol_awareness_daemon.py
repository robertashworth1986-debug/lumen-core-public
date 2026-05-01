from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List

CODE_ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\code")
EXEC_ROOT = CODE_ROOT / "execution"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))
if str(EXEC_ROOT) not in sys.path:
    sys.path.insert(0, str(EXEC_ROOT))

from harmonic_signal_connector import HarmonicSignalConnector


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out" / "execution"
RUNTIME_FILE = ROOT / "config" / "runtime_control.json"
AWARENESS_FILE = OUT / "symbol_watchdog_hierarchy.json"
REGISTRY_FILE = ROOT / "symbol_registry_auto.py"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_runtime_config() -> Dict[str, Any]:
    try:
        if RUNTIME_FILE.exists():
            data = json.loads(RUNTIME_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def load_symbol_registry() -> Dict[str, Dict[str, str]]:
    namespace: Dict[str, Any] = {}
    code = REGISTRY_FILE.read_text(encoding="utf-8")
    exec(code, namespace)  # trusted local file from this repo
    registry = namespace.get("SYMBOL_REGISTRY", {})
    if not isinstance(registry, dict):
        return {}
    return {
        str(k): v
        for k, v in registry.items()
        if isinstance(k, str) and isinstance(v, dict) and "pair" in v
    }


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


class RollingStats:
    def __init__(self, maxlen: int = 120) -> None:
        self.edges: Deque[float] = deque(maxlen=maxlen)
        self.prices: Deque[float] = deque(maxlen=maxlen)

    def push(self, edge_bps: float, price: float) -> None:
        self.edges.append(float(edge_bps))
        if price > 0.0:
            self.prices.append(float(price))

    def edge_mean_std(self) -> tuple[float, float]:
        if not self.edges:
            return 0.0, 0.0
        vals = list(self.edges)
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / max(1, len(vals) - 1)
        return mean, math.sqrt(max(var, 0.0))

    def local_bounds(self) -> tuple[float, float, float]:
        if not self.prices:
            return 0.0, 0.0, 0.0
        vals = list(self.prices)
        lo = min(vals)
        hi = max(vals)
        last = vals[-1]
        return last, lo, hi


def build_hierarchy(
    ranked: List[Dict[str, Any]],
    state: Dict[str, RollingStats],
    loop_seconds: float,
) -> Dict[str, Any]:
    watchdog_rows: List[Dict[str, Any]] = []
    eval_rows: List[Dict[str, Any]] = []
    entry_candidates: List[Dict[str, Any]] = []
    exit_candidates: List[Dict[str, Any]] = []

    for row in ranked:
        symbol = str(row.get("symbol", "") or "").upper()
        closes = row.get("recent_closes") or []
        price = float(closes[-1]) if isinstance(closes, list) and closes else 0.0
        edge_bps = float(row.get("edge_bps", 0.0) or 0.0)
        confidence = float(row.get("confidence", 0.0) or 0.0)
        signal = float(row.get("signal", 0.0) or 0.0)

        stats = state.setdefault(symbol, RollingStats())
        stats.push(edge_bps, price)

        mean_edge, std_edge = stats.edge_mean_std()
        edge_z = 0.0 if std_edge <= 1e-9 else (edge_bps - mean_edge) / std_edge
        last_px, lo_px, hi_px = stats.local_bounds()

        dip_ratio = 0.0
        spike_ratio = 0.0
        span = hi_px - lo_px
        if span > 1e-9:
            dip_ratio = (last_px - lo_px) / span
            spike_ratio = (hi_px - last_px) / span

        strange_steady = abs(edge_z) >= 2.0 and std_edge <= max(2.0, abs(mean_edge) * 0.35)
        dip_setup = dip_ratio <= 0.18 and signal >= 0.0 and edge_bps >= 8.0
        spike_setup = spike_ratio <= 0.12 and signal > 0.0 and edge_bps >= 10.0

        score = (edge_bps * confidence) + (max(0.0, 2.0 - dip_ratio) * 3.0)
        eval_rows.append(
            {
                "symbol": symbol,
                "score": round(score, 4),
                "edge_bps": round(edge_bps, 4),
                "confidence": round(confidence, 4),
                "signal": round(signal, 4),
                "edge_zscore": round(edge_z, 4),
                "dip_ratio": round(dip_ratio, 4),
                "spike_ratio": round(spike_ratio, 4),
                "market_data_mode": row.get("market_data_mode", "none"),
            }
        )

        if strange_steady:
            watchdog_rows.append(
                {
                    "symbol": symbol,
                    "type": "strange_but_steady",
                    "edge_zscore": round(edge_z, 4),
                    "edge_bps": round(edge_bps, 4),
                    "confidence": round(confidence, 4),
                }
            )

        if dip_setup:
            entry_candidates.append(
                {
                    "symbol": symbol,
                    "action": "buy_dip",
                    "edge_bps": round(edge_bps, 4),
                    "confidence": round(confidence, 4),
                    "dip_ratio": round(dip_ratio, 4),
                    "reason": "near_local_low_with_positive_signal",
                }
            )

        if spike_setup:
            exit_candidates.append(
                {
                    "symbol": symbol,
                    "action": "sell_spike",
                    "edge_bps": round(edge_bps, 4),
                    "confidence": round(confidence, 4),
                    "spike_ratio": round(spike_ratio, 4),
                    "reason": "near_local_high_with_positive_momentum",
                }
            )

    eval_rows.sort(key=lambda r: float(r.get("score", 0.0)), reverse=True)
    entry_candidates.sort(key=lambda r: (float(r.get("edge_bps", 0.0)) * float(r.get("confidence", 0.0))), reverse=True)
    exit_candidates.sort(key=lambda r: (float(r.get("edge_bps", 0.0)) * float(r.get("confidence", 0.0))), reverse=True)

    return {
        "generated_utc": now_utc(),
        "loop_seconds": loop_seconds,
        "watchdog_count": len(watchdog_rows),
        "evaluated_count": len(eval_rows),
        "hierarchy": {
            "watchdog": watchdog_rows[:120],
            "evaluator": eval_rows[:250],
            "executor_entry_queue": entry_candidates[:40],
            "executor_exit_queue": exit_candidates[:40],
        },
        "summary": {
            "top_watchdog": watchdog_rows[0] if watchdog_rows else None,
            "top_entry": entry_candidates[0] if entry_candidates else None,
            "top_exit": exit_candidates[0] if exit_candidates else None,
            "top_eval": eval_rows[0] if eval_rows else None,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Luma full-universe symbol awareness daemon")
    parser.add_argument("--loop-seconds", type=float, default=1.0, help="Loop cadence in seconds")
    parser.add_argument("--min-loop-seconds", type=float, default=0.25, help="Safety floor for loop cadence")
    parser.add_argument("--batch-size", type=int, default=120, help="How many symbols to advance per loop")
    args = parser.parse_args()

    loop_seconds = max(float(args.min_loop_seconds), float(args.loop_seconds))
    batch_size = max(1, int(args.batch_size))
    runtime_cfg = load_runtime_config()
    registry = load_symbol_registry()
    if not registry:
        print("[AWARENESS] symbol registry empty, exiting")
        return 2

    connector = HarmonicSignalConnector(registry, runtime_cfg)
    symbol_state: Dict[str, RollingStats] = {}
    latest_by_symbol: Dict[str, Dict[str, Any]] = {}

    # Emit a bootstrap artifact immediately so downstream consumers have a stable schema.
    bootstrap = build_hierarchy(ranked=[], state=symbol_state, loop_seconds=loop_seconds)
    atomic_write_json(AWARENESS_FILE, bootstrap)

    print(f"[AWARENESS] started | symbols={len(registry)} | loop_seconds={loop_seconds} | batch_size={batch_size}")
    while True:
        cycle_start = time.time()
        runtime_cfg = load_runtime_config()
        connector.update_runtime_config(runtime_cfg)

        for _ in range(batch_size):
            try:
                decision = connector.get_decision()
                symbol = str(decision.get("symbol", "") or "").upper()
                if symbol:
                    latest_by_symbol[symbol] = decision
            except Exception:
                continue

        ranked = list(latest_by_symbol.values())
        payload = build_hierarchy(ranked=ranked, state=symbol_state, loop_seconds=loop_seconds)
        atomic_write_json(AWARENESS_FILE, payload)

        elapsed = time.time() - cycle_start
        sleep_for = max(0.01, loop_seconds - elapsed)
        time.sleep(sleep_for)


if __name__ == "__main__":
    raise SystemExit(main())
