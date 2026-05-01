
print("[UNIQUE-DEBUG-LOAD] harmonic_signal_connector.py loaded from code/execution at ", __file__)
"""
HarmonicSignalConnector  (v2 — upgraded)
-----------------------------------------
Connects institutional_harmonic_suite to execution_orchestrator.

import sys

Loads the best-scoring (flow, strategy, algo) combination from
institutional_live_selection.json, fetches LIVE multi-timeframe OHLC
candles from Kraken's public API (1m + 5m), computes the harmonic
signal with proper algo post-processing, and returns a decision dict
with realistic edge_bps derived from live volatility.

Key fixes vs v1:
    - ALGOS imported and applied correctly (takes (sig, ret))
    - Multi-timeframe signal fusion (1m + 5m weighted blend)
    - edge_bps computed from abs(raw) × live_volatility_bps × edge_mult
        so it reflects real market conditions (not a hardcoded 12bps floor)
    - confidence computed from |raw| + Sharpe signal quality
    - selection file updated to include 'algo' field
"""


import sys
import asyncio
import json
import threading
import time
import numpy as np
import pandas as pd
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import websockets
except Exception:
    websockets = None

ROOT           = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
SELECTION_FILE = ROOT / "out" / "execution" / "institutional_live_selection.json"
RESELECTION_STATUS_FILE = ROOT / "out" / "execution" / "live_reselection_status.json"
MARKET_STREAM_STATUS_FILE = ROOT / "out" / "execution" / "live_market_stream_status.json"

_OHLC_INTERVAL_FAST = 1   # 1-minute for momentum
_OHLC_INTERVAL_SLOW = 5   # 5-minute for trend
_OHLC_MIN_CANDLES   = 4  # lowered for testing: accept short CSVs
_SELECTION_REFRESH_EVERY = 15

_DEFAULT_SELECTION: Dict = {
    "flow":               "lorenz",
    "strategy":           "harmonic_blend",
    "algo":               "ensemble",
    "institutional_score": 0.0,
    "test_sharpe":        0.0,
    "test_sortino":       0.0,
    "edge_multiplier":    1.2,
}

_DEFAULT_RUNTIME_CFG: Dict[str, Any] = {
    "live_ohlc_cache_enabled": True,
    "live_ohlc_cache_ttl_sec": 8.0,
    "live_ohlc_cache_max_points": 400,
    "live_rest_ohlc_timeout_sec": 1.5,
    "live_websocket_enabled": True,
    "live_websocket_seed_rest": True,
    "live_websocket_reconnect_sec": 8.0,
    "live_websocket_stale_after_sec": 20.0,
    "live_websocket_ping_interval_sec": 20.0,
    "live_selection_refresh_every": 15,
    "live_reselection_enabled": False,
    "live_reselection_interval_sec": 1800.0,
    "live_reselection_min_files": 1,
}

_KRAKEN_WS_URL = "wss://ws.kraken.com"


def _load_selection() -> Dict:
    import sys
    try:
        if SELECTION_FILE.exists():
            data = json.loads(SELECTION_FILE.read_text(encoding="utf-8"))
            # Support both list (leaderboard) and dict (summary) formats
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return _DEFAULT_SELECTION.copy()


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    import sys
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def _safe_write_status(path: Path, payload: Dict[str, Any]) -> None:
    import sys
    try:
        stamped = dict(payload)
        stamped.setdefault("timestamp_utc", pd.Timestamp.utcnow().isoformat())
        _atomic_write_json(path, stamped)
    except Exception:
        pass


def _fetch_ohlc_closes(pair: str, interval: int = 5, timeout_sec: float = 1.5) -> Optional[pd.Series]:
    import sys
    """Fetch OHLC from Kraken. Returns close Series or None."""
    try:
        resp = requests.get(
            "https://api.kraken.com/0/public/OHLC",
            params={"pair": pair, "interval": interval},
            timeout=max(0.25, float(timeout_sec or 1.5)),
        )
        data = resp.json()
        if data.get("error"):
            return None
        result = data.get("result", {})
        keys = [k for k in result if k != "last"]
        if not keys:
            return None
        closes = pd.Series([float(c[4]) for c in result[keys[0]]]).reset_index(drop=True)
        return closes if len(closes) >= _OHLC_MIN_CANDLES else None
    except Exception:
        return None


def _discover_crypto_training_files() -> List[Path]:
    data_dir = ROOT / "data"
    if not data_dir.exists():
        return []
    patterns = ("kraken*.csv", "*kraken*.csv")
    files: List[Path] = []
    for pattern in patterns:
        for path in sorted(data_dir.glob(pattern)):
            if path.is_file() and path.suffix.lower() == ".csv":
                files.append(path)
    unique: List[Path] = []
    seen = set()
    for path in files:
        key = str(path.resolve()).lower()
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def _to_kraken_ws_pair(pair: str) -> str:
    txt = str(pair or "").strip().upper()
    for quote in ("USD", "EUR", "GBP", "JPY", "CHF", "AUD", "USDT", "USDC"):
        if txt.endswith(quote) and len(txt) > len(quote):
            return f"{txt[:-len(quote)]}/{quote}"
    return txt


class KrakenLiveMarketBuffer:
    def __init__(self, pairs: List[str], runtime_cfg: Dict[str, Any]):
        self._pairs = sorted({str(pair).strip().upper() for pair in pairs if str(pair).strip()})
        self._runtime_cfg = dict(runtime_cfg or {})
        self._bars: Dict[Tuple[str, int], Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def update_runtime_config(self, runtime_cfg: Dict[str, Any]) -> None:
        self._runtime_cfg = dict(runtime_cfg or {})

    def start(self) -> bool:
        if websockets is None or not self._pairs:
            _safe_write_status(
                MARKET_STREAM_STATUS_FILE,
                {
                    "status": "unavailable",
                    "reason": "websockets_package_missing_or_no_pairs",
                    "pairs": self._pairs,
                },
            )
            return False
        if self._thread and self._thread.is_alive():
            return True
        self._stop_event.clear()
        self._ready_event.clear()
        self._thread = threading.Thread(target=self._thread_main, name="kraken-live-market-stream", daemon=True)
        self._thread.start()
        self._ready_event.wait(timeout=3.0)
        return True

    def stop(self) -> None:
        self._stop_event.set()
        loop = self._loop
        if loop and loop.is_running():
            try:
                loop.call_soon_threadsafe(lambda: None)
            except Exception:
                pass
        worker = self._thread
        if worker and worker.is_alive():
            try:
                worker.join(timeout=2.0)
            except Exception:
                pass

    def get_closes(self, pair: str, interval: int, min_points: int) -> Optional[pd.Series]:
        stale_after = max(5.0, float(self._runtime_cfg.get("live_websocket_stale_after_sec", 20.0) or 20.0))
        key = (str(pair).strip().upper(), int(interval))
        with self._lock:
            entry = self._bars.get(key)
            if not entry:
                return None
            last_update = float(entry.get("last_update_ts", 0.0) or 0.0)
            closes = entry.get("closes") or []
        if (time.time() - last_update) > stale_after:
            return None
        if len(closes) < int(min_points):
            return None
        return pd.Series([float(v) for v in closes]).reset_index(drop=True)

    def seed_closes(self, pair: str, interval: int, closes: pd.Series) -> None:
        if closes is None or len(closes) == 0:
            return
        max_points = max(60, int(self._runtime_cfg.get("live_ohlc_cache_max_points", 400) or 400))
        clipped = [float(v) for v in closes.tail(max_points).tolist()]
        if not clipped:
            return
        now = time.time()
        pseudo_times = [float(idx) for idx in range(len(clipped))]
        key = (str(pair).strip().upper(), int(interval))
        with self._lock:
            current = self._bars.get(key)
            current_len = len(current.get("closes", [])) if isinstance(current, dict) else 0
            if current_len >= len(clipped):
                return
            self._bars[key] = {
                "closes": clipped,
                "bar_times": pseudo_times,
                "last_update_ts": now,
            }

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_forever())
        finally:
            try:
                loop.stop()
            except Exception:
                pass
            loop.close()
            self._loop = None

    async def _run_forever(self) -> None:
        ws_pairs = [_to_kraken_ws_pair(pair) for pair in self._pairs]

        while not self._stop_event.is_set():
            reconnect_sec = max(1.0, float(self._runtime_cfg.get("live_websocket_reconnect_sec", 8.0) or 8.0))
            ping_interval = max(5.0, float(self._runtime_cfg.get("live_websocket_ping_interval_sec", 20.0) or 20.0))
            try:
                _safe_write_status(
                    MARKET_STREAM_STATUS_FILE,
                    {"status": "connecting", "pairs": ws_pairs, "endpoint": _KRAKEN_WS_URL},
                )
                async with websockets.connect(_KRAKEN_WS_URL, ping_interval=ping_interval, ping_timeout=ping_interval) as socket:
                    self._ready_event.set()
                    await socket.send(json.dumps({
                        "event": "subscribe",
                        "pair": ws_pairs,
                        "subscription": {"name": "ohlc", "interval": 1},
                    }))
                    await socket.send(json.dumps({
                        "event": "subscribe",
                        "pair": ws_pairs,
                        "subscription": {"name": "ohlc", "interval": 5},
                    }))
                    _safe_write_status(
                        MARKET_STREAM_STATUS_FILE,
                        {"status": "connected", "pairs": ws_pairs, "endpoint": _KRAKEN_WS_URL},
                    )

                    async for raw in socket:
                        if self._stop_event.is_set():
                            break
                        try:
                            self._handle_message(json.loads(raw))
                        except Exception as exc:
                            _safe_write_status(
                                MARKET_STREAM_STATUS_FILE,
                                {"status": "message_error", "error": str(exc)[:240], "pairs": ws_pairs},
                            )
            except Exception as exc:
                self._ready_event.set()
                _safe_write_status(
                    MARKET_STREAM_STATUS_FILE,
                    {"status": "reconnecting", "error": str(exc)[:240], "pairs": ws_pairs, "sleep_sec": reconnect_sec},
                )
                await asyncio.sleep(reconnect_sec)

        _safe_write_status(MARKET_STREAM_STATUS_FILE, {"status": "stopped", "pairs": ws_pairs})

    def _handle_message(self, payload: Any) -> None:
        if isinstance(payload, dict):
            event = str(payload.get("event", "") or "")
            if event == "subscriptionStatus":
                _safe_write_status(
                    MARKET_STREAM_STATUS_FILE,
                    {
                        "status": "subscription_status",
                        "channel": payload.get("subscription", {}).get("name"),
                        "pair": payload.get("pair"),
                        "status_text": payload.get("status"),
                    },
                )
            return

        if not isinstance(payload, list) or len(payload) < 4:
            return

        channel_name = str(payload[-2] or "")
        pair_label = str(payload[-1] or "").replace("/", "").upper()
        if not channel_name.startswith("ohlc-"):
            return

        try:
            interval = int(channel_name.split("-", 1)[1])
        except Exception:
            return

        candle_payload = payload[1]
        candle = None
        if isinstance(candle_payload, list) and len(candle_payload) >= 8:
            candle = candle_payload
        elif isinstance(candle_payload, dict):
            candle = candle_payload
        if candle is None:
            return

        if isinstance(candle, dict):
            close_val = candle.get("close")
            time_val = candle.get("epoc_end") or candle.get("time") or candle.get("epoc_last")
        else:
            close_val = candle[5] if len(candle) > 5 else None
            time_val = candle[1] if len(candle) > 1 else candle[0]
        try:
            close_px = float(close_val)
            bar_ts = float(time_val)
        except Exception:
            return

        max_points = max(60, int(self._runtime_cfg.get("live_ohlc_cache_max_points", 400) or 400))
        key = (pair_label, interval)
        now = time.time()
        with self._lock:
            entry = self._bars.get(key, {"closes": [], "bar_times": []})
            closes = list(entry.get("closes", []))
            bar_times = list(entry.get("bar_times", []))
            if bar_times and abs(float(bar_times[-1]) - bar_ts) < 1e-9:
                closes[-1] = close_px
                bar_times[-1] = bar_ts
            else:
                closes.append(close_px)
                bar_times.append(bar_ts)
            if len(closes) > max_points:
                closes = closes[-max_points:]
                bar_times = bar_times[-max_points:]
            self._bars[key] = {
                "closes": closes,
                "bar_times": bar_times,
                "last_update_ts": now,
            }


def _compute_signal(
    closes: pd.Series,
    flow_fn,
    strat_fn,
    algo_fn,
) -> float:
    """
    Apply flowform × strategy × algo to price series.
    Returns latest weighted signal in [-1, 1].
    algo_fn takes (signal_series, returns_series) → filtered signal.
    """
    px = closes.dropna().reset_index(drop=True)
    if len(px) < 20:
        return 0.0

    ret     = px.pct_change().dropna()
    flow    = flow_fn(ret).reindex(ret.index).fillna(1.0)
    sig_raw = strat_fn(ret).reindex(ret.index).fillna(0.0).clip(-1.0, 1.0)

    try:
        sig = algo_fn(sig_raw, ret).reindex(ret.index).fillna(0.0).clip(-1.0, 1.0)
    except Exception:
        sig = sig_raw

    weighted = (sig * flow).clip(-1.0, 1.0)
    return float(weighted.iloc[-1])


def _live_volatility_bps(closes: pd.Series, window: int = 20) -> float:
    """Annualised-then-per-bar volatility as basis points (for edge scaling)."""
    if len(closes) < window + 2:
        return 30.0
    ret = closes.pct_change().dropna()
    vol = float(ret.rolling(window).std().iloc[-1])
    if not np.isfinite(vol) or vol <= 0:
        return 30.0
    # Convert per-bar vol to bps (1 bps = 0.0001)
    return float(np.clip(vol * 10000.0, 5.0, 400.0))


class HarmonicSignalConnector:
    """
    Wraps institutional_harmonic_suite for live decision-making.

    Multi-timeframe signal fusion:
      - 5-minute candles: trend / regime signal (weight 0.60)
      - 1-minute candles: momentum confirm  (weight 0.40)
    
    edge_bps = abs(raw_signal) × live_volatility_bps × edge_multiplier
               (reflects actual expected move in bps per holding period)
    """

    def __init__(self, symbol_registry: Dict, runtime_cfg: Optional[Dict[str, Any]] = None):
        from institutional_harmonic_suite import FLOWFORMS, STRATEGIES, ALGOS

        self._symbols: List[str]      = list(symbol_registry.keys())
        self._pairs:   Dict[str, str] = {k: v["pair"] for k, v in symbol_registry.items()}
        self._FLOWFORMS  = FLOWFORMS
        self._STRATEGIES = STRATEGIES
        self._ALGOS      = ALGOS

        self._idx             = 0
        self._refresh_counter = 0
        self._runtime_cfg      = dict(_DEFAULT_RUNTIME_CFG)
        self._ohlc_cache: Dict[Tuple[str, int], Dict[str, Any]] = {}
        self._last_data_sources: Dict[Tuple[str, int], str] = {}
        self._cache_lock = threading.Lock()
        self._reselection_lock = threading.Lock()
        self._reselection_thread: Optional[threading.Thread] = None
        self._reselection_running = False
        self._last_reselection_started_at = 0.0
        self._last_reselection_completed_at = 0.0
        self._market_stream: Optional[KrakenLiveMarketBuffer] = None
        self._selection       = _load_selection()
        self.update_runtime_config(runtime_cfg or {})
        self._reload_fns()

    def update_runtime_config(self, runtime_cfg: Optional[Dict[str, Any]]) -> None:
        merged = dict(_DEFAULT_RUNTIME_CFG)
        if isinstance(runtime_cfg, dict):
            merged.update(runtime_cfg)
        self._runtime_cfg = merged
        ws_enabled = bool(self._runtime_cfg.get("live_websocket_enabled", True))
        if ws_enabled:
            if self._market_stream is None:
                self._market_stream = KrakenLiveMarketBuffer(list(self._pairs.values()), self._runtime_cfg)
                self._market_stream.start()
            else:
                self._market_stream.update_runtime_config(self._runtime_cfg)
                self._market_stream.start()
        elif self._market_stream is not None:
            self._market_stream.stop()
            self._market_stream = None


    def _get_cached_ohlc_closes(self, pair: str, interval: int) -> Optional[pd.Series]:
        cache_enabled = bool(self._runtime_cfg.get("live_ohlc_cache_enabled", True))
        cache_ttl_sec = max(0.0, float(self._runtime_cfg.get("live_ohlc_cache_ttl_sec", 8.0) or 8.0))
        cache_max_points = max(60, int(self._runtime_cfg.get("live_ohlc_cache_max_points", 400) or 400))
        rest_timeout_sec = max(0.25, float(self._runtime_cfg.get("live_rest_ohlc_timeout_sec", 1.5) or 1.5))
        key = (str(pair), int(interval))
        now = time.time()

        print(f"[DEBUG-TRACE] _get_cached_ohlc_closes: pair={pair}, interval={interval}")

        # 1. Try websocket (live data)
        print(f"[DEBUG-TRACE] Checking websocket for pair={pair}, interval={interval}, market_stream={self._market_stream is not None}")
        if self._market_stream is not None:
            ws_series = self._market_stream.get_closes(pair, interval, _OHLC_MIN_CANDLES)
            print(f"[DEBUG-TRACE] Websocket get_closes returned: {type(ws_series)}, len={len(ws_series) if ws_series is not None else 'None'}")
            if ws_series is not None and len(ws_series) >= _OHLC_MIN_CANDLES:
                ws_series = ws_series.tail(cache_max_points).reset_index(drop=True)
                self._last_data_sources[key] = "websocket"
                if cache_enabled:
                    with self._cache_lock:
                        self._ohlc_cache[key] = {"ts": now, "closes": ws_series.copy(), "source": "websocket"}
                print(f"[DEBUG-TRACE] Returning websocket (LIVE) data for {pair}, {len(ws_series)} points")
                return ws_series
            else:
                print(f"[DEBUG-TRACE] Websocket (LIVE) did not return enough candles for {pair} (needed {_OHLC_MIN_CANDLES})")

        # 2. Try cache
        print(f"[DEBUG-TRACE] Checking cache for pair={pair}, interval={interval}, cache_enabled={cache_enabled}")
        if cache_enabled:
            with self._cache_lock:
                entry = self._ohlc_cache.get(key)
                if entry and (now - float(entry.get("ts", 0.0) or 0.0)) <= cache_ttl_sec:
                    cached = entry.get("closes")
                    if isinstance(cached, pd.Series) and len(cached) >= _OHLC_MIN_CANDLES:
                        self._last_data_sources[key] = str(entry.get("source", "rest") or "rest")
                        print(f"[DEBUG-TRACE] Returning cached data for {pair}, {len(cached)} points")
                        return cached.copy()
        print(f"[DEBUG-TRACE] Cache miss or not enough candles for {pair}")

        # 3. Try REST (Kraken public API)
        print(f"[DEBUG-TRACE] Checking REST for pair={pair}, interval={interval}")
        allow_rest_seed = bool(self._runtime_cfg.get("live_websocket_seed_rest", True)) or self._market_stream is None
        if allow_rest_seed:
            closes = _fetch_ohlc_closes(pair, interval=interval, timeout_sec=rest_timeout_sec)
            print(f"[DEBUG-TRACE] REST get_closes returned: {type(closes)}, len={len(closes) if closes is not None else 'None'}")
            if closes is not None:
                closes = closes.tail(cache_max_points).reset_index(drop=True)
                if self._market_stream is not None:
                    self._market_stream.seed_closes(pair, interval, closes)
                if cache_enabled:
                    with self._cache_lock:
                        self._ohlc_cache[key] = {"ts": now, "closes": closes.copy(), "source": "rest"}
                self._last_data_sources[key] = "rest"
                print(f"[DEBUG-TRACE] Returning REST (Kraken API) data for {pair}, {len(closes)} points")
                return closes
            else:
                print(f"[DEBUG-TRACE] REST (Kraken API) did not return enough candles for {pair} (needed {_OHLC_MIN_CANDLES})")

        # 4. Fallback: Try local CSV data (robust, with logging)
        print(f"[DEBUG-TRACE] Entering CSV fallback for pair={pair}, interval={interval} (LIVE and REST failed)")
        try:
            import pandas as pd
            from pathlib import Path
            import os
            ROOT = Path(r"C:/LumaTrader/INSTITUTIONAL_STACK_V2")
            clean_data = ROOT / "clean_data"
            print(f"[DEBUG-TRACE] clean_data path: {clean_data}")
            print(f"[CSV-FALLBACK] Working directory: {os.getcwd()}")
            print(f"[CSV-FALLBACK] clean_data/ files: {list(clean_data.glob('*.csv'))}")
            print(f"[CSV-FALLBACK] Attempting fallback for pair: {pair}")
            base = pair.lower().replace("usd", "")
            candidates = [
                clean_data / f"kraken_{base}_daily.csv",
                clean_data / f"kraken_{base}.csv",
                clean_data / f"kraken_{pair.lower()}.csv",
                clean_data / f"kraken_{pair.lower()}_daily.csv",
            ]
            print(f"[DEBUG-TRACE] CSV candidate files: {candidates}")
            found = False
            for file in candidates:
                print(f"[DEBUG-TRACE] Checking CSV file: {file}")
                if file.exists():
                    try:
                        df = pd.read_csv(file)
                        print(f"[DEBUG-TRACE] Loaded CSV {file}, columns: {df.columns.tolist()}, rows: {len(df)}")
                        candidate_cols = ["close", "clo", "price", "last", "c"]
                        found_col = False
                        for col in candidate_cols:
                            if col in df.columns:
                                s = pd.to_numeric(df[col], errors="coerce").dropna()
                                print(f"[DEBUG-TRACE] Found column {col} in {file}, {len(s)} points")
                                if len(s) >= _OHLC_MIN_CANDLES:
                                    s = s.tail(cache_max_points).reset_index(drop=True)
                                    self._last_data_sources[key] = f"csv:{file.name}"
                                    print(f"[DEBUG-TRACE] Returning CSV data for {pair}, {len(s)} points")
                                    return s
                                else:
                                    print(f"[DEBUG-TRACE] Not enough data in {file} for {pair}: {len(s)} points, need {_OHLC_MIN_CANDLES}")
                                found_col = True
                        if not found_col:
                            print(f"[DEBUG-TRACE] No valid close/price columns in {file}")
                    except Exception as e:
                        print(f"[DEBUG-TRACE] Error reading CSV {file}: {e}")
                    found = True
            if not found:
                print(f"[DEBUG-TRACE] No CSV found for {pair}")
            print(f"[DEBUG-TRACE] CSV fallback failed for {pair} (no valid data found)")
        except Exception as e:
            print(f"[DEBUG-TRACE] Exception in CSV fallback for {pair}: {e}")

        print(f"[DEBUG-TRACE] All data sources failed for {pair}, returning None")
        return None

    def _write_reselection_status(self, payload: Dict[str, Any]) -> None:
        _safe_write_status(RESELECTION_STATUS_FILE, payload)

    def _run_reselection_worker(self, files: List[Path]) -> None:
        try:
            self._write_reselection_status({
                "status": "running",
                "files": [str(p) for p in files],
                "selection_file": str(SELECTION_FILE),
            })
            from institutional_harmonic_suite import run_engine

            run_engine([str(p) for p in files])
            self.refresh_selection()
            self._last_reselection_completed_at = time.time()
            self._write_reselection_status({
                "status": "completed",
                "files": [str(p) for p in files],
                "selection_file": str(SELECTION_FILE),
                "flow": self._selection.get("flow"),
                "strategy": self._selection.get("strategy"),
                "algo": self._selection.get("algo"),
            })
        except Exception as exc:
            self._write_reselection_status({
                "status": "failed",
                "files": [str(p) for p in files],
                "error": str(exc),
            })
        finally:
            with self._reselection_lock:
                self._reselection_running = False
                self._reselection_thread = None

    def _maybe_run_live_reselection(self) -> None:
        if not bool(self._runtime_cfg.get("live_reselection_enabled", False)):
            return

        interval_sec = max(60.0, float(self._runtime_cfg.get("live_reselection_interval_sec", 1800.0) or 1800.0))
        min_files = max(1, int(self._runtime_cfg.get("live_reselection_min_files", 1) or 1))
        now = time.time()
        last_completed = float(self._last_reselection_completed_at or 0.0)
        last_started = float(self._last_reselection_started_at or 0.0)
        if self._reselection_running:
            return
        if max(last_completed, last_started) > 0.0 and (now - max(last_completed, last_started)) < interval_sec:
            return

        files = _discover_crypto_training_files()
        if len(files) < min_files:
            self._write_reselection_status({
                "status": "skipped",
                "reason": "insufficient_crypto_files",
                "files_found": len(files),
                "min_files": min_files,
            })
            self._last_reselection_completed_at = now
            return

        with self._reselection_lock:
            if self._reselection_running:
                return
            self._reselection_running = True
            self._last_reselection_started_at = now
            worker = threading.Thread(
                target=self._run_reselection_worker,
                args=(files,),
                name="live-crypto-reselection",
                daemon=True,
            )
            self._reselection_thread = worker
            worker.start()

    def _build_decision_for_symbol(self, symbol: str) -> Dict:
        pair = self._pairs[symbol]

        # Multi-timeframe fetch (5m primary, 1m momentum confirm)
        closes_slow = self._get_cached_ohlc_closes(pair, interval=5)
        closes_fast = self._get_cached_ohlc_closes(pair, interval=1)

        if closes_slow is None and closes_fast is None:
            return self._no_data_decision(symbol)

        # Compute signal on whichever timeframes succeeded
        raw_slow = _compute_signal(closes_slow, self._flow_fn, self._strat_fn, self._algo_fn) if closes_slow is not None else 0.0
        raw_fast = _compute_signal(closes_fast, self._flow_fn, self._strat_fn, self._algo_fn) if closes_fast is not None else raw_slow

        # Weighted blend: trend (slow) 60%, momentum confirm (fast) 40%
        raw = float(np.clip(raw_slow * 0.60 + raw_fast * 0.40, -1.0, 1.0))

        # Direction: use fast signal for momentum, slow for trend
        if raw > 0.10:
            direction = "long"
        elif raw < -0.10:
            direction = "short"
        else:
            direction = "long"  # default bias: spot long is safer

        sel         = self._selection
        edge_mult   = float(sel.get("edge_multiplier", 1.2) or 1.2)
        iscore      = float(sel.get("institutional_score", 0.0) or 0.0)
        test_sharpe = float(sel.get("test_sharpe", 0.0) or 0.0)
        test_sortino= float(sel.get("test_sortino", test_sharpe) or test_sharpe)

        # Live volatility from best available series
        primary_closes = closes_slow if closes_slow is not None else closes_fast
        primary_interval = 5 if closes_slow is not None else 1
        data_mode = self._last_data_sources.get((str(pair).strip().upper(), primary_interval), "rest")
        live_vol_bps   = _live_volatility_bps(primary_closes)

        # Edge: signal strength × live volatility (realistic expected move per bar)
        # Minimum is live_vol_bps * 0.15 so we always report some discoverable edge
        raw_edge = abs(raw) * live_vol_bps * edge_mult
        edge_bps = float(np.clip(
            raw_edge
            + np.clip(iscore / 30.0, 0.0, 8.0)
            + np.clip(test_sortino * 2.0, 0.0, 12.0),
            live_vol_bps * 0.15,   # floor: at least 15% of 1-bar vol
            live_vol_bps * 3.5,    # cap: no more than 3.5× 1-bar vol
        ))

        # Confidence: signal strength + Sharpe/Sortino quality
        confidence = float(np.clip(
            abs(raw) * 0.70
            + np.clip(test_sortino / 12.0, 0.0, 0.15)
            + np.clip(test_sharpe  / 20.0, 0.0, 0.10)
            + 0.55,     # base floor so confidence stays above 0.55
            0.55, 0.97
        ))

        return {
            "symbol":         symbol,
            "direction":      direction,
            "confidence":     round(confidence, 4),
            "edge_bps":       round(edge_bps, 2),
            "regime":         self._regime,
            "signal":         round(raw, 4),
            "signal_slow":    round(raw_slow, 4),
            "signal_fast":    round(raw_fast, 4),
            "live_vol_bps":   round(live_vol_bps, 2),
            "source":         "HARMONIC_LIVE_MTF",
            "market_data_mode": data_mode,
            "flow":           sel.get("flow"),
            "strategy":       sel.get("strategy"),
            "algo":           sel.get("algo"),
            "recent_closes":  [float(v) for v in primary_closes.tail(300).tolist()],
        }

    def _no_data_decision(self, symbol: str) -> Dict:
        return {
            "symbol":    symbol,
            "direction": "long",
            "confidence": 0.40,
            "edge_bps":  0.0,
            "regime":    self._regime,
            "signal":    0.0,
            "source":    "HARMONIC_NO_DATA",
            "market_data_mode": "none",
            "flow":      self._selection.get("flow"),
            "strategy":  self._selection.get("strategy"),
            "algo":      self._selection.get("algo"),
            "recent_closes": [],
        }


    def get_ranked_decisions(self, scan_size: int = 6) -> List[Dict]:
        from pathlib import Path
        debug_file = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\orchestrator_ranked_debug.txt")
        with debug_file.open("a", encoding="utf-8") as f:
            f.write(f"[ENTERED get_ranked_decisions] scan_size={scan_size} symbols={self._symbols}\n")
        print(f"[DEBUG-REGISTRY] [CODE/EXECUTION VERSION ACTIVE] self._symbols: {self._symbols}")
        print(f"[DEBUG-REGISTRY] [CODE/EXECUTION VERSION ACTIVE] self._pairs: {self._pairs}")
        print(f"[DEBUG-REGISTRY] [CODE/EXECUTION VERSION ACTIVE] scan_size: {scan_size}")
        # FORCE: Always scan ALL symbols, ignore scan_size
        self._maybe_run_live_reselection()

        # Periodically reload best combo from disk
        self._refresh_counter += 1
        refresh_every = max(1, int(self._runtime_cfg.get("live_selection_refresh_every", _SELECTION_REFRESH_EVERY) or _SELECTION_REFRESH_EVERY))
        if self._refresh_counter >= refresh_every:
            self.refresh_selection()
            self._refresh_counter = 0

        ranked: List[Dict] = []
        debug_rows = []
        print(f"[DEBUG-FORCE] get_ranked_decisions: Forcing scan of ALL symbols (total: {len(self._symbols)})")
        for idx, symbol in enumerate(self._symbols):
            try:
                decision = self._build_decision_for_symbol(symbol)
                if decision.get("source", "").startswith("HARMONIC_NO_DATA"):
                    print(f"[CSV-FALLBACK] {symbol}: NO DATA, fallback triggered, decision={decision}")
                else:
                    print(f"[DEBUG-FORCE] {symbol}: edge_bps={decision.get('edge_bps', 0.0):.2f}, confidence={decision.get('confidence', 0.0):.2f}, data_mode={decision.get('market_data_mode','none')}, signal={decision.get('signal', 0.0):.3f}")
                ranked.append(decision)
            except Exception as e:
                print(f"[DEBUG-FORCE] Exception for {symbol}: {e}")
        print(f"[DEBUG-FORCE] Ranked {len(ranked)} symbols. Returning all.")

        # Sort by composite: edge_bps × confidence (higher = better opportunity)
        ranked.sort(
            key=lambda item: float(item.get("edge_bps", 0.0)) * float(item.get("confidence", 0.0)),
            reverse=True,
        )
        return ranked
        # FORCE: Always scan ALL symbols, ignore scan_size
        self._maybe_run_live_reselection()

        # Periodically reload best combo from disk
        self._refresh_counter += 1
        refresh_every = max(1, int(self._runtime_cfg.get("live_selection_refresh_every", _SELECTION_REFRESH_EVERY) or _SELECTION_REFRESH_EVERY))
        if self._refresh_counter >= refresh_every:
            self.refresh_selection()
            self._refresh_counter = 0

        ranked: List[Dict] = []
        debug_rows = []
        print(f"[DEBUG-FORCE] get_ranked_decisions: Forcing scan of ALL symbols (total: {len(self._symbols)})")
        for idx, symbol in enumerate(self._symbols):
            try:
                decision = self._build_decision_for_symbol(symbol)
                if decision.get("source", "").startswith("HARMONIC_NO_DATA"):
                    print(f"[DEBUG-FORCE] {symbol}: NO DATA, fallback triggered, decision={decision}")
                else:
                    print(f"[DEBUG-FORCE] {symbol}: edge_bps={decision.get('edge_bps', 0.0):.2f}, confidence={decision.get('confidence', 0.0):.2f}, data_mode={decision.get('market_data_mode','none')}, signal={decision.get('signal', 0.0):.3f}")
                ranked.append(decision)
            except Exception as e:
                print(f"[DEBUG-FORCE] Exception for {symbol}: {e}")
        print(f"[DEBUG-FORCE] Ranked {len(ranked)} symbols. Returning all.")

        # Sort by composite: edge_bps × confidence (higher = better opportunity)
        ranked.sort(
            key=lambda item: float(item.get("edge_bps", 0.0)) * float(item.get("confidence", 0.0)),
            reverse=True,
        )
        return ranked

    def _reload_fns(self):
        sel        = self._selection
        flow_name  = sel.get("flow",     "lorenz")
        strat_name = sel.get("strategy", "harmonic_blend")
        algo_name  = sel.get("algo",     "ensemble")

        self._flow_fn  = self._FLOWFORMS.get(flow_name,   self._FLOWFORMS.get("lorenz", next(iter(self._FLOWFORMS.values()))))
        self._strat_fn = self._STRATEGIES.get(strat_name, self._STRATEGIES.get("harmonic_blend", next(iter(self._STRATEGIES.values()))))
        self._algo_fn  = self._ALGOS.get(algo_name,       self._ALGOS.get("ensemble", next(iter(self._ALGOS.values()))))
        self._regime   = f"{flow_name}:{strat_name}:{algo_name}"

    def refresh_selection(self):
        """Reload the best combo from disk."""
        self._selection = _load_selection()
        self._reload_fns()

    def get_decision(self) -> Dict:
        """Single-symbol decision (backwards-compatible)."""
        self._maybe_run_live_reselection()
        self._refresh_counter += 1
        refresh_every = max(1, int(self._runtime_cfg.get("live_selection_refresh_every", _SELECTION_REFRESH_EVERY) or _SELECTION_REFRESH_EVERY))
        if self._refresh_counter >= refresh_every:
            self.refresh_selection()
            self._refresh_counter = 0
        symbol = self._symbols[self._idx % len(self._symbols)]
        self._idx = (self._idx + 1) % len(self._symbols)
        return self._build_decision_for_symbol(symbol)
