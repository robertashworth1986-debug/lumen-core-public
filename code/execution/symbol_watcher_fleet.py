"""
symbol_watcher_fleet.py
-----------------------
Per-symbol watcher agent fleet for LumaTrader.

Every symbol in the registry gets its own lightweight watcher thread that:
  - Polls Kraken public ticker on a fast cycle
  - Maintains a rolling price window tracking peak_high, peak_low, and timestamps
  - Detects REAL vs FAKE price spikes using z-score + reversal confirmation
  - Writes per-symbol state JSON to  out/symbol_states/{SYMBOL}_state.json
  - Publishes a fleet summary (top-ranked signals) to
      out/symbol_states/_fleet_summary.json

The execution_orchestrator reads _fleet_summary.json to get a pre-ranked,
pre-filtered candidate list instead of brute-forcing all 1,693 symbols
every loop.  This means the orchestrator sees signals faster and wastes zero
time on quiet symbols.

Real-spike detection logic
  - z-score of (current_price - rolling_mean) / rolling_std
  - A spike is flagged when abs(z) >= SPIKE_Z_THRESHOLD (default 2.5)
  - It is only marked REAL after SPIKE_SUSTAIN_TICKS consecutive ticks
    above that threshold in the same direction
  - If the price immediately reverses direction within REVERSAL_TICKS ticks,
    the spike is marked FAKE and discarded
  - spike_score = abs(z) * confirmation_ratio  (higher = stronger + confirmed)

Usage — standalone daemon:
    python code/execution/symbol_watcher_fleet.py

Usage — import into orchestrator:
    from symbol_watcher_fleet import SymbolWatcherFleet, get_real_spike_alerts, get_top_fleet_signals
    fleet = SymbolWatcherFleet(SYMBOL_REGISTRY, runtime_cfg)
    fleet.start()
    ...
    top_signals = fleet.get_top_signals(n=20)
    real_spikes = fleet.get_real_spike_alerts()
"""

from __future__ import annotations

import json
import math
import os
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "symbol_states"
OUT.mkdir(parents=True, exist_ok=True)

FLEET_SUMMARY_FILE = OUT / "_fleet_summary.json"
FLEET_ALERT_FILE   = OUT / "_real_spike_alerts.json"

# ─── Tuning constants — adjust via env vars or runtime_cfg ───────────────────
POLL_SEC_DEFAULT     = 2.5    # seconds between ticker polls per worker cycle
ROLLING_WINDOW       = 80     # price samples to keep per symbol (rolling history)
SPIKE_Z_THRESHOLD    = 2.5    # z-score threshold to flag a potential spike
SPIKE_SUSTAIN_TICKS  = 2      # consecutive above-threshold ticks to confirm REAL
REVERSAL_TICKS       = 3      # ticks to watch before calling a spike fake/resolved
WORKER_THREADS       = 8      # parallel polling worker threads
SUMMARY_WRITE_SEC    = 4.0    # how often to write fleet summary
KRAKEN_TICKER_URL    = "https://api.kraken.com/0/public/Ticker"
HTTP_TIMEOUT         = 6.0    # per-request timeout


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


# ─────────────────────────────────────────────────────────────────────────────
# SymbolWatcherState
# ─────────────────────────────────────────────────────────────────────────────

class SymbolWatcherState:
    """
    Mutable, thread-safe state object for a single symbol.
    One of these exists for every symbol in the registry.
    """

    __slots__ = (
        "symbol", "pair",
        "prices", "timestamps",
        "peak_high", "peak_high_ts",
        "peak_low",  "peak_low_ts",
        "last_price", "last_bid", "last_ask",
        "last_tick_ts",
        "rolling_mean", "rolling_std",
        "spike_z_score",
        "spike_active", "spike_real",
        "spike_score",  "spike_direction",
        "spike_start_ts",
        "spike_confirm_ticks",
        "reversal_watch_ticks",
        "tick_count", "error_count", "last_error",
        "_lock",
    )

    def __init__(self, symbol: str, pair: str) -> None:
        self.symbol     = symbol
        self.pair       = pair
        self.prices: deque     = deque(maxlen=ROLLING_WINDOW)
        self.timestamps: deque = deque(maxlen=ROLLING_WINDOW)

        # Peak tracking
        self.peak_high:    Optional[float] = None
        self.peak_high_ts: Optional[str]   = None
        self.peak_low:     Optional[float] = None
        self.peak_low_ts:  Optional[str]   = None

        # Last tick
        self.last_price: Optional[float] = None
        self.last_bid:   Optional[float] = None
        self.last_ask:   Optional[float] = None
        self.last_tick_ts: Optional[str] = None

        # Rolling stats
        self.rolling_mean: float = 0.0
        self.rolling_std:  float = 0.0

        # Spike state
        self.spike_z_score:        float = 0.0
        self.spike_active:         bool  = False
        self.spike_real:           bool  = False
        self.spike_score:          float = 0.0
        self.spike_direction:      str   = ""      # "up" | "down" | ""
        self.spike_start_ts:       Optional[str] = None
        self.spike_confirm_ticks:  int   = 0
        self.reversal_watch_ticks: int   = 0

        # Health
        self.tick_count:  int = 0
        self.error_count: int = 0
        self.last_error:  str = ""

        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def update(self, price: float, bid: float, ask: float) -> None:
        """Ingest one new price tick and update all derived state."""
        now_str = _now_utc()
        with self._lock:
            self.prices.append(price)
            self.timestamps.append(time.time())
            self.last_price   = price
            self.last_bid     = bid
            self.last_ask     = ask
            self.last_tick_ts = now_str
            self.tick_count  += 1

            # ── Peak tracking ─────────────────────────────────────────
            if self.peak_high is None or price > self.peak_high:
                self.peak_high    = price
                self.peak_high_ts = now_str
            if self.peak_low is None or price < self.peak_low:
                self.peak_low    = price
                self.peak_low_ts = now_str

            # ── Rolling statistics ────────────────────────────────────
            prices_list = list(self.prices)
            n = len(prices_list)

            if n >= 3:
                mean     = sum(prices_list) / n
                variance = sum((p - mean) ** 2 for p in prices_list) / max(n - 1, 1)
                std      = math.sqrt(variance) if variance > 1e-18 else 1e-9
                self.rolling_mean = mean
                self.rolling_std  = std

                z = (price - mean) / max(std, 1e-9)
                self.spike_z_score = z
                abs_z = abs(z)

                # ── Spike detection ───────────────────────────────────
                if abs_z >= SPIKE_Z_THRESHOLD:
                    direction = "up" if z > 0 else "down"

                    if not self.spike_active:
                        # Fresh spike candidate
                        self.spike_active         = True
                        self.spike_real           = False
                        self.spike_direction      = direction
                        self.spike_start_ts       = now_str
                        self.spike_confirm_ticks  = 1
                        self.reversal_watch_ticks = 0
                    else:
                        if direction == self.spike_direction:
                            # Sustained in same direction — confirm
                            self.spike_confirm_ticks += 1
                        else:
                            # Immediate direction reversal → FAKE spike
                            self.spike_active         = False
                            self.spike_real           = False
                            self.spike_confirm_ticks  = 0
                            self.reversal_watch_ticks = 0
                            self.spike_score          = 0.0
                            self.spike_direction      = ""

                    # Mark REAL once we have enough confirming ticks
                    if self.spike_confirm_ticks >= SPIKE_SUSTAIN_TICKS:
                        self.spike_real = True

                    confirm_ratio   = min(1.0, self.spike_confirm_ticks / max(SPIKE_SUSTAIN_TICKS, 1))
                    self.spike_score = round(abs_z * confirm_ratio, 4)

                else:
                    # z is below threshold
                    if self.spike_active:
                        self.reversal_watch_ticks += 1
                        if self.reversal_watch_ticks >= REVERSAL_TICKS:
                            # Spike has faded — resolved
                            self.spike_active         = False
                            self.spike_real           = False
                            self.spike_confirm_ticks  = 0
                            self.reversal_watch_ticks = 0
                            self.spike_direction      = ""
                            self.spike_score          = 0.0
                    else:
                        # Background signal strength even without active spike
                        self.spike_score = round(abs_z, 4)

            else:
                # Not enough data yet — just store
                self.rolling_mean  = price
                self.rolling_std   = 0.0
                self.spike_z_score = 0.0
                self.spike_score   = 0.0

    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Thread-safe snapshot for JSON output."""
        with self._lock:
            prices_list = list(self.prices)
            peak_range_pct = 0.0
            if self.peak_high and self.peak_low and self.peak_low > 0:
                peak_range_pct = round(
                    ((self.peak_high - self.peak_low) / self.peak_low) * 100.0, 4
                )

            spread_bps = 0.0
            if self.last_bid and self.last_ask and self.last_bid > 0:
                spread_bps = round(
                    ((self.last_ask - self.last_bid) / self.last_bid) * 10_000.0, 2
                )

            # Time since last peak high/low (for staleness awareness)
            now_ts = time.time()
            ts_list = list(self.timestamps)
            age_sec = round(now_ts - ts_list[-1], 1) if ts_list else None

            return {
                "symbol":                self.symbol,
                "pair":                  self.pair,
                "last_price":            self.last_price,
                "last_bid":              self.last_bid,
                "last_ask":              self.last_ask,
                "spread_bps":            spread_bps,
                "last_tick_ts":          self.last_tick_ts,
                "age_sec":               age_sec,
                "tick_count":            self.tick_count,
                "error_count":           self.error_count,
                "last_error":            self.last_error,
                # Peak tracking
                "peak_high":             self.peak_high,
                "peak_high_ts":          self.peak_high_ts,
                "peak_low":              self.peak_low,
                "peak_low_ts":           self.peak_low_ts,
                "peak_range_pct":        peak_range_pct,
                # Rolling statistics
                "rolling_mean":          round(self.rolling_mean, 8),
                "rolling_std":           round(self.rolling_std, 8),
                "rolling_window_n":      len(prices_list),
                # Spike state
                "spike_z_score":         round(self.spike_z_score, 4),
                "spike_active":          self.spike_active,
                "spike_real":            self.spike_real,
                "spike_score":           self.spike_score,
                "spike_direction":       self.spike_direction,
                "spike_start_ts":        self.spike_start_ts,
                "spike_confirm_ticks":   self.spike_confirm_ticks,
                "updated_utc":           _now_utc(),
            }


# ─────────────────────────────────────────────────────────────────────────────
# SymbolWatcherFleet
# ─────────────────────────────────────────────────────────────────────────────

class SymbolWatcherFleet:
    """
    Manages per-symbol watcher agents across the full Kraken symbol universe.

    Architecture:
      - N worker threads share the symbol list (each worker owns a stripe)
      - Each worker polls its slice of symbols in a tight loop
      - A dedicated summary thread writes _fleet_summary.json every few seconds
      - The orchestrator reads _fleet_summary.json for pre-ranked signals

    This replaces the brute-force get_ranked_decisions(scan_size=1693) loop
    with a continuously-updated, stateful signal surface.
    """

    def __init__(
        self,
        symbol_registry: Dict[str, Any],
        runtime_cfg: Optional[Dict[str, Any]] = None,
        poll_sec: float = POLL_SEC_DEFAULT,
        worker_threads: int = WORKER_THREADS,
    ) -> None:
        self._registry  = dict(symbol_registry or {})
        self._cfg       = dict(runtime_cfg or {})
        self._poll_sec  = max(0.5, float(poll_sec))
        self._n_workers = max(1, int(worker_threads))

        self._states: Dict[str, SymbolWatcherState] = {}
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "LumaTrader-WatcherFleet/1.0"})

        self._stop_event   = threading.Event()
        self._workers: List[threading.Thread]         = []
        self._summary_thread: Optional[threading.Thread] = None

        # Build one state object per symbol
        for symbol, config in self._registry.items():
            sym  = str(symbol).upper().strip()
            if not sym:
                continue
            pair = (
                str(config.get("pair", sym + "USD"))
                if isinstance(config, dict)
                else sym + "USD"
            )
            self._states[sym] = SymbolWatcherState(sym, pair)

        print(
            f"[FLEET] Initialized {len(self._states)} symbol watchers | "
            f"workers={self._n_workers} | poll={self._poll_sec}s"
        )

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Launch all worker threads and the summary writer."""
        self._stop_event.clear()
        self._workers = []

        symbols = list(self._states.keys())
        for i in range(self._n_workers):
            # Each worker owns a stripe: [i, i+N, i+2N, ...]
            my_symbols = symbols[i :: self._n_workers]
            t = threading.Thread(
                target=self._worker_loop,
                args=(i, my_symbols),
                name=f"watcher-{i}",
                daemon=True,
            )
            t.start()
            self._workers.append(t)

        self._summary_thread = threading.Thread(
            target=self._summary_writer_loop,
            name="watcher-summary",
            daemon=True,
        )
        self._summary_thread.start()

        print(
            f"[FLEET] Started {len(self._workers)} worker threads "
            f"+ summary writer. Monitoring {len(self._states)} symbols."
        )

    # ------------------------------------------------------------------
    def stop(self) -> None:
        self._stop_event.set()
        print("[FLEET] Stop signal sent to all workers.")

    # ------------------------------------------------------------------
    def get_top_signals(self, n: int = 20, real_spikes_only: bool = False) -> List[Dict[str, Any]]:
        """
        Return top-N symbols ranked by spike_score.
        Called by the orchestrator to pick candidates for deep analysis.
        real_spikes_only=True → only symbols with spike_real=True
        """
        results = []
        for state in self._states.values():
            if real_spikes_only and not state.spike_real:
                continue
            if state.last_price is None:
                continue
            results.append(state.to_dict())
        results.sort(key=lambda x: float(x.get("spike_score", 0.0)), reverse=True)
        return results[:n]

    def get_real_spike_alerts(self, n: int = 10) -> List[Dict[str, Any]]:
        """Only symbols with confirmed real spikes — highest priority for orchestrator."""
        return self.get_top_signals(n=n, real_spikes_only=True)

    def get_state(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current watcher state for a specific symbol."""
        state = self._states.get(str(symbol).upper())
        return state.to_dict() if state else None

    def alive_count(self) -> int:
        """Count of symbols that have received at least one price tick."""
        return sum(1 for s in self._states.values() if s.last_price is not None)

    # ------------------------------------------------------------------
    def _worker_loop(self, worker_id: int, symbols: List[str]) -> None:
        """Worker: poll assigned symbols in a loop, respecting poll_sec budget."""
        per_symbol_budget = max(0.05, self._poll_sec / max(len(symbols), 1))
        print(f"[FLEET-W{worker_id}] Assigned {len(symbols)} symbols | budget={per_symbol_budget:.3f}s/symbol")

        while not self._stop_event.is_set():
            loop_start = time.time()

            for symbol in symbols:
                if self._stop_event.is_set():
                    break
                self._poll_symbol(symbol)
                # Tiny yield between symbols to avoid burst throttling
                time.sleep(max(0.0, per_symbol_budget - 0.01))

            elapsed = time.time() - loop_start
            remaining = max(0.01, self._poll_sec - elapsed)
            self._stop_event.wait(timeout=remaining)

    # ------------------------------------------------------------------
    def _poll_symbol(self, symbol: str) -> None:
        """Fetch Kraken public ticker for one symbol and update its state."""
        state = self._states.get(symbol)
        if state is None:
            return

        try:
            response = self._session.get(
                KRAKEN_TICKER_URL,
                params={"pair": state.pair},
                timeout=HTTP_TIMEOUT,
            )
            response.raise_for_status()
            data   = response.json()
            result = data.get("result", {})
            if not result:
                return

            ticker = next(iter(result.values()))
            last   = _safe_float(ticker.get("c", [0])[0])
            bid    = _safe_float(ticker.get("b", [0])[0])
            ask    = _safe_float(ticker.get("a", [0])[0])

            if last > 0:
                state.update(last, bid, ask)
                self._write_state_file(symbol, state)

        except Exception as exc:
            with state._lock:
                state.error_count += 1
                state.last_error   = str(exc)[:200]

    # ------------------------------------------------------------------
    def _write_state_file(self, symbol: str, state: SymbolWatcherState) -> None:
        """Atomically write per-symbol state JSON."""
        try:
            payload = state.to_dict()
            path    = OUT / f"{symbol}_state.json"
            tmp     = path.with_name(f"{symbol}_state.json.tmp")
            tmp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
            os.replace(str(tmp), str(path))
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _summary_writer_loop(self) -> None:
        """Periodically write the fleet summary and alert files."""
        while not self._stop_event.is_set():
            try:
                top_50       = self.get_top_signals(n=50)
                real_spikes  = [s for s in top_50 if s.get("spike_real")]
                active_count = sum(1 for s in self._states.values() if s.spike_active)
                real_count   = sum(1 for s in self._states.values() if s.spike_real)

                summary = {
                    "updated_utc":          _now_utc(),
                    "total_watched":        len(self._states),
                    "symbols_with_data":    self.alive_count(),
                    "active_spikes":        active_count,
                    "real_spikes":          real_count,
                    "top_signals":          top_50,
                    "real_spike_alerts":    real_spikes[:10],
                }

                # Atomic write of fleet summary
                tmp = FLEET_SUMMARY_FILE.with_name("_fleet_summary.json.tmp")
                tmp.write_text(json.dumps(summary, indent=2), encoding="utf-8")
                os.replace(str(tmp), str(FLEET_SUMMARY_FILE))

                # Separate alert file for fast reads in orchestrator
                if real_spikes:
                    tmp2 = FLEET_ALERT_FILE.with_name("_real_spike_alerts.json.tmp")
                    tmp2.write_text(json.dumps(real_spikes, indent=2), encoding="utf-8")
                    os.replace(str(tmp2), str(FLEET_ALERT_FILE))

            except Exception:
                pass

            self._stop_event.wait(timeout=SUMMARY_WRITE_SEC)


# ─────────────────────────────────────────────────────────────────────────────
# Lightweight read-only helpers for the orchestrator
# (no fleet instance needed — just reads the JSON files)
# ─────────────────────────────────────────────────────────────────────────────

def load_fleet_summary() -> Dict[str, Any]:
    """Read current fleet summary. Callable from orchestrator without fleet instance."""
    try:
        if FLEET_SUMMARY_FILE.exists():
            return json.loads(FLEET_SUMMARY_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def get_top_fleet_signals(n: int = 20) -> List[Dict[str, Any]]:
    """Top-N signals from fleet summary file — no dep on fleet instance."""
    return load_fleet_summary().get("top_signals", [])[:n]


def get_real_spike_alerts() -> List[Dict[str, Any]]:
    """Only confirmed real-spike symbols from fleet summary — highest priority."""
    return load_fleet_summary().get("real_spike_alerts", [])


def fleet_is_fresh(max_age_sec: float = 30.0) -> bool:
    """Returns True if fleet summary was written within max_age_sec seconds."""
    try:
        if not FLEET_SUMMARY_FILE.exists():
            return False
        age = time.time() - FLEET_SUMMARY_FILE.stat().st_mtime
        return age <= max_age_sec
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Standalone daemon entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "code"))
    sys.path.insert(0, str(ROOT / "code" / "execution"))

    try:
        from symbol_registry_auto import SYMBOL_REGISTRY  # type: ignore
    except ImportError as e:
        print(f"[FLEET] ERROR: Could not import SYMBOL_REGISTRY: {e}")
        print(f"[FLEET] Make sure symbol_registry_auto.py exists at {ROOT}")
        sys.exit(1)

    _poll  = float(os.environ.get("WATCHER_POLL_SEC",  str(POLL_SEC_DEFAULT)))
    _works = int(os.environ.get("WATCHER_WORKERS",     str(WORKER_THREADS)))

    print(f"[FLEET] Starting SymbolWatcherFleet")
    print(f"[FLEET] Symbols : {len(SYMBOL_REGISTRY)}")
    print(f"[FLEET] Workers : {_works}")
    print(f"[FLEET] Poll    : {_poll}s")
    print(f"[FLEET] Output  : {OUT}")

    fleet = SymbolWatcherFleet(SYMBOL_REGISTRY, poll_sec=_poll, worker_threads=_works)
    fleet.start()

    try:
        loop_n = 0
        while True:
            time.sleep(15)
            loop_n += 1
            summary    = load_fleet_summary()
            n_alive    = summary.get("symbols_with_data", 0)
            n_real     = summary.get("real_spikes", 0)
            n_active   = summary.get("active_spikes", 0)
            top        = summary.get("top_signals", [])[:5]
            top_str    = "  ".join(
                f"{s['symbol']}(z={s.get('spike_z_score', 0.0):.2f} real={s.get('spike_real', False)})"
                for s in top
            )
            print(
                f"[FLEET] loop={loop_n} | alive={n_alive}/{len(SYMBOL_REGISTRY)} "
                f"| active_spikes={n_active} | REAL={n_real} "
                f"| top5=[{top_str}]"
            )

    except KeyboardInterrupt:
        print("\n[FLEET] KeyboardInterrupt — shutting down...")
        fleet.stop()
        sys.exit(0)
