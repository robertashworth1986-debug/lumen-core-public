import os
import atexit
import sys
import json
import time
import random
import math
import subprocess
import hmac
import hashlib
import base64
import requests

from pathlib import Path
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

# Add paths
sys.path.insert(0, r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\execution")

from signal_gate import EvolutionarySignalGate, GateInput
from portfolio_brain import PortfolioBrain, Position
from liquidity_guard import LiquidityGuard, LiquiditySnapshot
from risk_kernel import RiskKernel, RiskState
from sizing_engine import SizingEngine, SizeInput
from order_router import OrderRouter, RouteIntent
from shadow_runner import ShadowRunner, ShadowFill
from trade_ledger import TradeLedger
from audit_chain import AuditChain

try:
    from regime_engine import InstitutionalRegimeEngine
except Exception:
    InstitutionalRegimeEngine = None


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONFIG = ROOT / "config"
OUT = ROOT / "out" / "execution"
DASH = ROOT / "dashboard"
RUNTIME_CONTROL_FILE = CONFIG / "runtime_control.json"
MIN_OPEN_POSITIONS_FLOOR = 10
LIVE_TRADE_LOG_FILE = OUT / "live_trade_log.json"
LIVE_SHADOW_LEDGER_FILE = OUT / "live_shadow_fills.csv"
LIVE_TRADE_LEDGER_CSV_FILE = OUT / "live_trade_ledger.csv"
LIVE_TRADE_LEDGER_JSONL_FILE = OUT / "live_trade_ledger.jsonl"
LIVE_AUDIT_CHAIN_FILE = OUT / "live_execution_audit_chain.jsonl"
LIVE_HEARTBEAT_FILE = OUT / "live_executor_heartbeat.json"
LIVE_HEARTBEAT_SCHEMA_VERSION = "1.0.0"
LIVE_EXECUTOR_LOCK_FILE = OUT / "live_executor.lock"
KRAKEN_NONCE_STATE_FILE = OUT / "kraken_nonce_state.json"
KRAKEN_BALANCE_CACHE_FILE = OUT / "kraken_balance_cache.json"
KRAKEN_ASSET_PAIRS_CACHE_FILE = OUT / "kraken_asset_pairs_cache.json"
ROLLING_CAPITAL_BEST_MULTI_FILE = Path(r"C:/LumaTrader/rolling_capital/rolling_capital_best_multi.json")

OUT.mkdir(parents=True, exist_ok=True)
DASH.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def load_api_keys() -> dict:
    keys = {}
    env_file = CONFIG / "luma_live_keys.env"
    if not env_file.exists():
        return keys
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        keys[k.strip()] = v.strip()
    return keys


def load_institutional_live_selection() -> dict:
    return load_json(
        OUT / "institutional_live_selection.json",
        {"flow": "fallback", "strategy": "harmonic_blend", "edge_multiplier": 1.0, "institutional_score": 0.0},
    )


def _resolve_urgency(edge_score: float, spread_bps: float, direction: str) -> str:
    del direction
    if edge_score >= 0.82 and spread_bps <= 10.0:
        return "aggressive"
    if edge_score >= 0.50 and spread_bps <= 25.0:
        return "normal"
    return "passive"


def _preferred_live_symbol() -> Optional[str]:
    payload = load_json(ROLLING_CAPITAL_BEST_MULTI_FILE, {})
    raw_symbol = str(payload.get("symbol", "")).upper().strip()
    if not raw_symbol:
        return None
    base_symbol = raw_symbol.split("/")[0].strip()
    return base_symbol or None


def _write_live_heartbeat(payload: dict) -> None:
    try:
        payload = dict(payload)
        payload.setdefault("schema_version", LIVE_HEARTBEAT_SCHEMA_VERSION)
        payload.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
        LIVE_HEARTBEAT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass


def _pid_running(pid: int) -> bool:
    if int(pid or 0) <= 0:
        return False
    try:
        probe = subprocess.run(
            ["tasklist", "/FI", f"PID eq {int(pid)}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        out = (probe.stdout or "").strip()
        if not out:
            return False
        if "No tasks are running" in out:
            return False
        return True
    except Exception:
        return False


def _acquire_executor_lock() -> bool:
    now_utc = datetime.now(timezone.utc).isoformat()
    pid = os.getpid()

    lock_payload = {
        "pid": pid,
        "acquired_utc": now_utc,
        "lock_file": str(LIVE_EXECUTOR_LOCK_FILE),
    }

    try:
        fd = os.open(str(LIVE_EXECUTOR_LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(lock_payload, f, indent=2)
        return True
    except FileExistsError:
        pass
    except Exception:
        return False

    existing = load_json(LIVE_EXECUTOR_LOCK_FILE, {})
    owner_pid = int(existing.get("pid") or 0)
    acquired_utc = str(existing.get("acquired_utc") or "")
    lock_age_min = 0.0
    try:
        lock_dt = datetime.fromisoformat(acquired_utc)
        if lock_dt.tzinfo is None:
            lock_dt = lock_dt.replace(tzinfo=timezone.utc)
        lock_age_min = max((datetime.now(timezone.utc) - lock_dt).total_seconds() / 60.0, 0.0)
    except Exception:
        lock_age_min = 0.0

    owner_running = _pid_running(owner_pid) if owner_pid else False

    if owner_pid and owner_pid != pid and owner_running:
        _write_live_heartbeat(
            {
                "status": "blocked",
                "reason": "executor_already_running",
                "owner_pid": owner_pid,
                "this_pid": pid,
                "lock_age_minutes": round(lock_age_min, 3),
            }
        )
        print(f"another live_executor is already running (pid={owner_pid}, lock_age_min={lock_age_min:.2f})")
        return False

    try:
        LIVE_EXECUTOR_LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        return False

    try:
        fd = os.open(str(LIVE_EXECUTOR_LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(lock_payload, f, indent=2)
        return True
    except Exception:
        return False


def _release_executor_lock() -> None:
    pid = os.getpid()
    existing = load_json(LIVE_EXECUTOR_LOCK_FILE, {})
    owner_pid = int(existing.get("pid") or 0)
    if owner_pid and owner_pid != pid:
        return
    try:
        LIVE_EXECUTOR_LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


SYMBOL_REGISTRY = {
    "BTC": {"exchange": "kraken", "pair": "XBTUSD", "min_order": 0.0001},
    "ETH": {"exchange": "kraken", "pair": "ETHUSD", "min_order": 0.001},
    "SOL": {"exchange": "kraken", "pair": "SOLUSD", "min_order": 0.01},
    "XRP": {"exchange": "kraken", "pair": "XRPUSD", "min_order": 1.0},
}


class KrakenClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key or ""
        self.api_secret = api_secret or ""
        self.base_url = "https://api.kraken.com"
        self.session = requests.Session()
        self.last_balance_error = ""
        self._last_nonce = int(time.time_ns())
        self._balance_cache_ttl_sec = 8.0
        self._balance_rate_limit_fallback_sec = 180.0
        self._balance_cache_usd = 0.0
        self._balance_cache_utc = ""
        self._asset_pairs_map: dict[str, dict[str, Any]] = {}
        self._asset_pairs_cache_utc = ""
        self._asset_pairs_cache_ttl_sec = 3600.0
        self._load_balance_cache()
        self._load_asset_pairs_cache()

    def _load_balance_cache(self) -> None:
        try:
            if not KRAKEN_BALANCE_CACHE_FILE.exists():
                return
            payload = json.loads(KRAKEN_BALANCE_CACHE_FILE.read_text(encoding="utf-8"))
            self._balance_cache_usd = float(payload.get("zusd", 0.0) or 0.0)
            self._balance_cache_utc = str(payload.get("timestamp_utc", "") or "")
        except Exception:
            self._balance_cache_usd = 0.0
            self._balance_cache_utc = ""

    def _save_balance_cache(self, zusd: float) -> None:
        try:
            payload = {
                "zusd": float(max(zusd, 0.0)),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }
            KRAKEN_BALANCE_CACHE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self._balance_cache_usd = float(payload["zusd"])
            self._balance_cache_utc = str(payload["timestamp_utc"])
        except Exception:
            pass

    def _load_asset_pairs_cache(self) -> None:
        try:
            if not KRAKEN_ASSET_PAIRS_CACHE_FILE.exists():
                return
            payload = json.loads(KRAKEN_ASSET_PAIRS_CACHE_FILE.read_text(encoding="utf-8"))
            symbols = payload.get("symbols") if isinstance(payload, dict) else {}
            if isinstance(symbols, dict):
                self._asset_pairs_map = symbols
            self._asset_pairs_cache_utc = str(payload.get("timestamp_utc", "") or "")
        except Exception:
            self._asset_pairs_map = {}
            self._asset_pairs_cache_utc = ""

    def _save_asset_pairs_cache(self, symbols: dict[str, dict[str, Any]]) -> None:
        try:
            payload = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "symbols": symbols,
            }
            KRAKEN_ASSET_PAIRS_CACHE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self._asset_pairs_map = symbols
            self._asset_pairs_cache_utc = str(payload["timestamp_utc"])
        except Exception:
            pass

    def _asset_pairs_cache_age_sec(self) -> float:
        ts = str(self._asset_pairs_cache_utc or "").strip()
        if not ts:
            return float("inf")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return max((datetime.now(timezone.utc) - dt).total_seconds(), 0.0)
        except Exception:
            return float("inf")

    @staticmethod
    def _to_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    def _fetch_asset_pairs_map(self) -> dict[str, dict[str, Any]]:
        try:
            r = self.session.get(self.base_url + "/0/public/AssetPairs", timeout=12)
            r.raise_for_status()
            payload = r.json()
            if payload.get("error"):
                return {}
            result = payload.get("result", {})
            if not isinstance(result, dict):
                return {}

            out: dict[str, dict[str, Any]] = {}
            for _, row in result.items():
                if not isinstance(row, dict):
                    continue
                altname = str(row.get("altname", "") or "").upper().strip()
                wsname = str(row.get("wsname", "") or "").upper().strip()
                if not altname or not wsname or "/" not in wsname:
                    continue
                base, quote = wsname.split("/", 1)
                base = base.strip()
                quote = quote.strip()
                if quote != "USD":
                    continue

                min_order = self._to_float(row.get("ordermin", 0.0), 0.0)
                if min_order <= 0.0:
                    # Conservative fallback when ordermin is missing.
                    min_order = 1e-8

                cfg = {
                    "exchange": "kraken",
                    "pair": altname,
                    "min_order": max(float(min_order), 1e-8),
                }
                out[base] = cfg
                if base == "XBT":
                    out["BTC"] = cfg
            return out
        except Exception:
            return {}

    def get_asset_pairs_map(self) -> dict[str, dict[str, Any]]:
        age_sec = self._asset_pairs_cache_age_sec()
        if self._asset_pairs_map and age_sec <= self._asset_pairs_cache_ttl_sec:
            return self._asset_pairs_map

        fetched = self._fetch_asset_pairs_map()
        if fetched:
            self._save_asset_pairs_cache(fetched)
            return fetched

        return self._asset_pairs_map

    def resolve_symbol_config(self, symbol: str) -> Optional[dict[str, Any]]:
        key = str(symbol or "").upper().strip()
        if not key:
            return None
        pairs_map = self.get_asset_pairs_map()
        cfg = pairs_map.get(key)
        if cfg:
            return dict(cfg)
        if key == "XBT" and "BTC" in pairs_map:
            return dict(pairs_map["BTC"])
        if key == "BTC" and "XBT" in pairs_map:
            return dict(pairs_map["XBT"])
        return None

    def _cached_balance_age_sec(self) -> float:
        ts = str(self._balance_cache_utc or "").strip()
        if not ts:
            return float("inf")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return max((datetime.now(timezone.utc) - dt).total_seconds(), 0.0)
        except Exception:
            return float("inf")

    def _read_nonce_state(self) -> int:
        try:
            if KRAKEN_NONCE_STATE_FILE.exists():
                payload = json.loads(KRAKEN_NONCE_STATE_FILE.read_text(encoding="utf-8"))
                return int(payload.get("last_nonce", 0) or 0)
        except Exception:
            pass
        return 0

    def _write_nonce_state(self, nonce: int) -> None:
        try:
            KRAKEN_NONCE_STATE_FILE.write_text(
                json.dumps(
                    {
                        "last_nonce": int(nonce),
                        "updated_utc": datetime.now(timezone.utc).isoformat(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _next_nonce(self) -> str:
        # Kraken requires strictly increasing nonces. Use persisted ns-scale monotonic values.
        persisted = self._read_nonce_state()
        candidate = max(int(time.time_ns()), self._last_nonce + 1, persisted + 1)
        self._last_nonce = candidate
        self._write_nonce_state(candidate)
        return str(candidate)

    def _sign(self, urlpath: str, data: dict) -> str:
        nonce = data["nonce"]
        postdata = urlencode(data)
        encoded = (str(nonce) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        return base64.b64encode(mac.digest()).decode()

    def _private(self, endpoint: str, data: dict) -> dict:
        request_data = dict(data or {})
        for attempt in range(2):
            request_data["nonce"] = self._next_nonce()
            headers = {
                "API-Key": self.api_key,
                "API-Sign": self._sign(endpoint, request_data),
            }
            r = self.session.post(self.base_url + endpoint, data=request_data, headers=headers, timeout=15)
            r.raise_for_status()
            payload = r.json()
            errors = payload.get("error") or []
            if errors and any("Invalid nonce" in str(e) for e in errors) and attempt == 0:
                # Jump forward and retry once when Kraken rejects nonce ordering.
                self._last_nonce = max(self._last_nonce + 10_000_000_000, int(time.time_ns()))
                continue
            if errors:
                return {"error": errors}
            return payload.get("result", {})
        return {"error": ["EAPI:Invalid nonce"]}

    def get_account_balance(self) -> float:
        self.last_balance_error = ""
        if not self.api_key or not self.api_secret:
            self.last_balance_error = "missing_credentials"
            return 0.0

        cache_age_sec = self._cached_balance_age_sec()
        if self._balance_cache_usd > 0.0 and cache_age_sec <= self._balance_cache_ttl_sec:
            return float(self._balance_cache_usd)

        try:
            result = self._private("/0/private/Balance", {})
            if "error" in result:
                raw_error = result.get("error", "unknown")
                if isinstance(raw_error, list):
                    raw_error = ",".join(str(x) for x in raw_error)
                self.last_balance_error = f"kraken_balance_api_error:{raw_error}"
                rate_limited = "Rate limit" in str(raw_error)
                cache_age_sec = self._cached_balance_age_sec()
                if rate_limited and self._balance_cache_usd > 0.0 and cache_age_sec <= self._balance_rate_limit_fallback_sec:
                    self.last_balance_error += ";using_cached_balance"
                    return float(self._balance_cache_usd)
                return 0.0
            zusd = float(result.get("ZUSD", 0.0))
            if zusd <= 0.0:
                self.last_balance_error = "zusd_zero_or_missing"
                cache_age_sec = self._cached_balance_age_sec()
                if self._balance_cache_usd > 0.0 and cache_age_sec <= self._balance_rate_limit_fallback_sec:
                    self.last_balance_error += ";using_cached_balance"
                    return float(self._balance_cache_usd)
            else:
                self._save_balance_cache(zusd)
            return zusd
        except Exception as e:
            self.last_balance_error = f"balance_exception:{e}"
            cache_age_sec = self._cached_balance_age_sec()
            if self._balance_cache_usd > 0.0 and cache_age_sec <= self._balance_rate_limit_fallback_sec:
                self.last_balance_error += ";using_cached_balance"
                return float(self._balance_cache_usd)
            return 0.0

    def send_order(self, pair: str, side: str, qty: float, price: float = None, order_type: str = "limit") -> dict:
        if not self.api_key or not self.api_secret:
            return {"error": "missing kraken credentials"}
        data = {
            "pair": pair,
            "type": side.lower(),
            "ordertype": "limit" if order_type == "limit" else "market",
            "volume": f"{qty:.8f}",
        }
        if order_type == "limit" and price is not None:
            data["price"] = f"{price:.8f}"
        try:
            return self._private("/0/private/AddOrder", data)
        except Exception as e:
            return {"error": str(e)}

    def get_ticker(self, pair: str):
        try:
            r = self.session.get(self.base_url + "/0/public/Ticker", params={"pair": pair}, timeout=10)
            r.raise_for_status()
            payload = r.json()
            if payload.get("error"):
                return None
            result = payload.get("result", {})
            if not result:
                return None
            key = next(iter(result.keys()))
            t = result[key]
            return {
                "bid": float(t["b"][0]),
                "ask": float(t["a"][0]),
                "last": float(t["c"][0]),
                "pair": key,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception:
            return None


class MultiExchangeRouter:
    def __init__(self, api_keys: dict):
        self.kraken = KrakenClient(api_keys.get("KRAKEN_API_KEY", ""), api_keys.get("KRAKEN_API_SECRET", ""))

    def get_symbol_config(self, symbol: str):
        key = str(symbol or "").upper().strip()
        if not key:
            return None
        cfg = SYMBOL_REGISTRY.get(key)
        if cfg:
            return cfg
        return self.kraken.resolve_symbol_config(key)

    def get_candidate_symbols(self, max_symbols: int = 120) -> list[str]:
        symbols = {str(k).upper() for k in SYMBOL_REGISTRY.keys()}
        dynamic_map = self.kraken.get_asset_pairs_map()
        if isinstance(dynamic_map, dict):
            symbols.update(str(k).upper() for k in dynamic_map.keys())
        if not symbols:
            return []
        rows = sorted(symbols)
        cap = max(int(max_symbols or 0), 1)
        return rows[:cap]

    def get_ticker(self, symbol: str):
        cfg = self.get_symbol_config(symbol)
        if not cfg:
            return None
        return self.kraken.get_ticker(cfg["pair"])

    def get_balance(self):
        return self.kraken.get_account_balance()

    def place_order(self, symbol: str, side: str, qty: float, limit_price: float = None):
        cfg = self.get_symbol_config(symbol)
        if not cfg:
            return {"error": f"unknown symbol {symbol}"}
        return self.kraken.send_order(cfg["pair"], side, qty, limit_price, "limit" if limit_price else "market")


class RobustLiveExecutor:
    def __init__(self, api_keys: dict):
        self.router = MultiExchangeRouter(api_keys)
        self.signal_gate = EvolutionarySignalGate(
            min_alignment=0.50,
            min_regime_conf=0.40,
            min_liquidity=0.30,
            min_cross_confirm=0.35,
            min_edge_bps=4.0,
            max_volatility_pct=10.0,
            max_correlation=0.90,
            max_sector_heat=0.60,
            min_orderbook_depth_usd=0.0,
            max_orderbook_spread_bps=18.0,
            max_orderbook_imbalance=1.0,
            min_onchain_tx_volume_usd=0.0,
            max_onchain_gas_fee_usd=500.0,
            min_onchain_whale_tx_count=0,
        )
        self.portfolio = PortfolioBrain(initial_capital=219.0)
        self.liquidity_guard = LiquidityGuard()
        self.risk_kernel = RiskKernel()
        self.sizing_engine = SizingEngine()
        self.order_router = OrderRouter()
        self.shadow_runner = ShadowRunner()
        self.trade_ledger = TradeLedger(str(LIVE_TRADE_LEDGER_CSV_FILE), str(LIVE_TRADE_LEDGER_JSONL_FILE))
        self.audit_chain = AuditChain(LIVE_AUDIT_CHAIN_FILE)

        self.regime_engine = InstitutionalRegimeEngine() if InstitutionalRegimeEngine else None
        self.live_selection = load_institutional_live_selection()
        self.edge_multiplier = max(float(self.live_selection.get("edge_multiplier", 1.0) or 1.0), 0.5)
        self.runtime_cfg: dict[str, Any] = {}
        self.max_open_positions = MIN_OPEN_POSITIONS_FLOOR
        self.loop_seconds = 30.0
        self.aggressive_edge_bonus_bps = 5.0
        self.degraded_buying_power_usd = 0.0
        self.mid_history: dict[str, list[float]] = {}
        self.dynamic_reserve_enabled = True
        self.dynamic_reserve_max_balance_fraction = 0.35
        self.dynamic_reserve_floor_usd = 0.0
        self.low_balance_sample_trigger_usd = 12.0
        self.low_balance_sample_size = 24
        self.gate_override_enabled = False
        self.gate_override_min_confidence = 0.58
        self.gate_override_min_edge_bps = 7.5
        self.gate_not_armed_streak = 0
        self.no_affordable_streak = 0
        self.no_affordable_recycle_enabled = True
        self.no_affordable_recycle_streak_trigger = 2
        self.no_affordable_recycle_min_hold_sec = 45.0
        self.no_affordable_recycle_cooldown_sec = 60.0
        self.no_affordable_last_recycle_utc = ""
        self.buy_cooldown_until_utc = ""
        self.order_fail_streak = 0
        self.notional_throttle = 1.0
        self.failure_notional_decay = 0.75
        self.failure_notional_floor = 0.08
        self.success_notional_recovery_step = 0.03
        self.insufficient_funds_cooldown_step_sec = 20.0
        self.insufficient_funds_cooldown_max_sec = 300.0
        self.recent_order_attempt_utc: list[datetime] = []
        self.recent_order_fail_utc: list[datetime] = []
        self.failure_window_sec = 300.0
        self.failure_rate_min_attempts = 6
        self.failure_rate_threshold = 0.55
        self.failure_rate_hard_block_threshold = 0.85
        self.failure_rate_notional_floor = 0.15
        self.failure_rate_buy_cooldown_sec = 75.0
        self.symbol_min_order_overrides: dict[str, float] = {}
        self.min_order_override_multiplier = 1.8
        self.min_order_volume_error_buy_cooldown_sec = 45.0
        self.max_symbol_min_order = 1_000_000.0
        self.universe_spread_scan_enabled = True
        self.universe_sample_size = 8
        self.universe_max_pick_spread_bps = 55.0
        self.last_symbol_selection_meta: dict[str, Any] = {}

        self.pyramid_level = 1
        self.consecutive_losses = 0
        self.trade_log = []
        self._refresh_runtime_config()

    def _strategy_regime_conflict(self, strategy: str, regime_name: str) -> bool:
        # hard-block matrix
        disallow = {
            "mean_revert": {"trend", "expansion"},
            "breakout": {"chop", "squeeze"},
            "trend": {"chop"},
        }
        blocked = disallow.get(strategy, set())
        return regime_name in blocked

    def _liquidity_score(self, liq_decision) -> float:
        try:
            tier = getattr(liq_decision, "liquidity_tier", None)
            if hasattr(tier, "value"):
                return max(0.0, min(1.0, float(tier.value) / 10.0))
        except Exception:
            pass
        return 0.8

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, float(value)))

    @staticmethod
    def _to_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    def _effective_max_open_positions(self, raw_value: Any) -> int:
        try:
            parsed = int(float(raw_value))
        except Exception:
            parsed = MIN_OPEN_POSITIONS_FLOOR
        if parsed <= 0:
            return MIN_OPEN_POSITIONS_FLOOR
        return max(MIN_OPEN_POSITIONS_FLOOR, parsed)

    def _refresh_runtime_config(self) -> None:
        runtime = load_json(RUNTIME_CONTROL_FILE, {})
        if not isinstance(runtime, dict):
            runtime = {}
        self.runtime_cfg = runtime

        self.live_selection = load_institutional_live_selection()
        self.edge_multiplier = max(self._to_float(self.live_selection.get("edge_multiplier", 1.0), 1.0), 0.5)
        self.max_open_positions = self._effective_max_open_positions(runtime.get("max_open_positions", MIN_OPEN_POSITIONS_FLOOR))
        self.loop_seconds = self._clamp(self._to_float(runtime.get("loop_seconds", 30.0), 30.0), 1.0, 120.0)
        self.aggressive_edge_bonus_bps = self._clamp(
            self._to_float(
                runtime.get("pounce_edge_bps_bonus", runtime.get("aggressive_edge_threshold_bps", 5.0)),
                5.0,
            ),
            0.0,
            35.0,
        )
        self.gate_override_enabled = bool(runtime.get("gate_override_enabled", self.gate_override_enabled))
        self.gate_override_min_confidence = self._clamp(
            self._to_float(
                runtime.get("gate_override_min_confidence", self.gate_override_min_confidence),
                self.gate_override_min_confidence,
            ),
            0.05,
            0.99,
        )
        self.gate_override_min_edge_bps = self._clamp(
            self._to_float(
                runtime.get("gate_override_min_edge_bps", self.gate_override_min_edge_bps),
                self.gate_override_min_edge_bps,
            ),
            0.0,
            200.0,
        )
        self.dynamic_reserve_enabled = bool(runtime.get("dynamic_reserve_enabled", self.dynamic_reserve_enabled))
        self.dynamic_reserve_max_balance_fraction = self._clamp(
            self._to_float(
                runtime.get("dynamic_reserve_max_balance_fraction", self.dynamic_reserve_max_balance_fraction),
                self.dynamic_reserve_max_balance_fraction,
            ),
            0.0,
            0.95,
        )
        self.dynamic_reserve_floor_usd = self._clamp(
            self._to_float(runtime.get("dynamic_reserve_floor_usd", self.dynamic_reserve_floor_usd), self.dynamic_reserve_floor_usd),
            0.0,
            50000.0,
        )
        self.no_affordable_recycle_enabled = bool(
            runtime.get("no_affordable_recycle_enabled", self.no_affordable_recycle_enabled)
        )
        self.no_affordable_recycle_streak_trigger = int(
            self._clamp(
                self._to_float(
                    runtime.get("no_affordable_recycle_streak_trigger", self.no_affordable_recycle_streak_trigger),
                    self.no_affordable_recycle_streak_trigger,
                ),
                1.0,
                100.0,
            )
        )
        self.no_affordable_recycle_min_hold_sec = self._clamp(
            self._to_float(
                runtime.get("no_affordable_recycle_min_hold_sec", self.no_affordable_recycle_min_hold_sec),
                self.no_affordable_recycle_min_hold_sec,
            ),
            0.0,
            86400.0,
        )
        self.no_affordable_recycle_cooldown_sec = self._clamp(
            self._to_float(
                runtime.get("no_affordable_recycle_cooldown_sec", self.no_affordable_recycle_cooldown_sec),
                self.no_affordable_recycle_cooldown_sec,
            ),
            0.0,
            86400.0,
        )

        self.signal_gate.min_composite_score = self._clamp(
            self._to_float(
                runtime.get(
                    "gate_min_composite_score",
                    runtime.get(
                        "min_gate_score_for_entry",
                        runtime.get("signal_gate_min_score", getattr(self.signal_gate, "min_composite_score", 0.60)),
                    ),
                ),
                getattr(self.signal_gate, "min_composite_score", 0.60),
            ),
            0.35,
            0.95,
        )
        gate_thresholds = getattr(self.signal_gate, "base_thresholds", {})
        if isinstance(gate_thresholds, dict):
            gate_thresholds["alignment"] = self._clamp(
                self._to_float(runtime.get("gate_min_alignment", gate_thresholds.get("alignment", 0.50)), gate_thresholds.get("alignment", 0.50)),
                0.05,
                0.99,
            )
            gate_thresholds["regime_conf"] = self._clamp(
                self._to_float(runtime.get("gate_min_regime_conf", gate_thresholds.get("regime_conf", 0.40)), gate_thresholds.get("regime_conf", 0.40)),
                0.05,
                0.99,
            )
            gate_thresholds["liquidity"] = self._clamp(
                self._to_float(runtime.get("gate_min_liquidity", gate_thresholds.get("liquidity", 0.30)), gate_thresholds.get("liquidity", 0.30)),
                0.05,
                0.99,
            )
            gate_thresholds["cross_confirm"] = self._clamp(
                self._to_float(runtime.get("gate_min_cross_confirm", gate_thresholds.get("cross_confirm", 0.35)), gate_thresholds.get("cross_confirm", 0.35)),
                0.05,
                0.99,
            )
            gate_thresholds["edge_bps"] = self._clamp(
                self._to_float(runtime.get("gate_min_edge_bps", gate_thresholds.get("edge_bps", 4.0)), gate_thresholds.get("edge_bps", 4.0)),
                0.0,
                250.0,
            )
            gate_thresholds["volatility"] = self._clamp(
                self._to_float(runtime.get("gate_max_volatility_pct", gate_thresholds.get("volatility", 10.0)), gate_thresholds.get("volatility", 10.0)),
                0.1,
                300.0,
            )
            gate_thresholds["correlation"] = self._clamp(
                self._to_float(runtime.get("gate_max_correlation", gate_thresholds.get("correlation", 0.90)), gate_thresholds.get("correlation", 0.90)),
                0.0,
                1.0,
            )
            gate_thresholds["sector_heat"] = self._clamp(
                self._to_float(runtime.get("gate_max_sector_heat", gate_thresholds.get("sector_heat", 0.60)), gate_thresholds.get("sector_heat", 0.60)),
                0.0,
                1.0,
            )
            gate_thresholds["signal_decay"] = self._clamp(
                self._to_float(runtime.get("gate_max_signal_decay", gate_thresholds.get("signal_decay", 0.60)), gate_thresholds.get("signal_decay", 0.60)),
                0.05,
                1.0,
            )
        configured_fallback = max(self._to_float(runtime.get("fallback_buying_power_usd", 0.0), 0.0), 0.0)
        if self.degraded_buying_power_usd <= 0.0:
            self.degraded_buying_power_usd = configured_fallback
        else:
            # Never expand above configured ceiling from adaptive value.
            self.degraded_buying_power_usd = min(self.degraded_buying_power_usd, max(configured_fallback, 0.0))

        self.risk_kernel.max_daily_loss_usd = max(
            1.0,
            self._to_float(
                runtime.get("max_daily_loss_usd", self.risk_kernel.max_daily_loss_usd),
                self.risk_kernel.max_daily_loss_usd,
            ),
        )
        self.risk_kernel.max_heat = self._clamp(
            self._to_float(runtime.get("max_portfolio_heat", self.risk_kernel.max_heat), self.risk_kernel.max_heat),
            0.02,
            0.95,
        )

        self.failure_notional_decay = self._clamp(
            self._to_float(runtime.get("failure_notional_decay", self.failure_notional_decay), self.failure_notional_decay),
            0.30,
            0.98,
        )
        self.failure_notional_floor = self._clamp(
            self._to_float(runtime.get("failure_notional_floor", self.failure_notional_floor), self.failure_notional_floor),
            0.02,
            1.00,
        )
        self.success_notional_recovery_step = self._clamp(
            self._to_float(
                runtime.get("success_notional_recovery_step", self.success_notional_recovery_step),
                self.success_notional_recovery_step,
            ),
            0.005,
            0.25,
        )
        self.insufficient_funds_cooldown_step_sec = self._clamp(
            self._to_float(
                runtime.get("insufficient_funds_cooldown_step_sec", self.insufficient_funds_cooldown_step_sec),
                self.insufficient_funds_cooldown_step_sec,
            ),
            2.0,
            600.0,
        )
        self.insufficient_funds_cooldown_max_sec = self._clamp(
            self._to_float(
                runtime.get("insufficient_funds_cooldown_max_sec", self.insufficient_funds_cooldown_max_sec),
                self.insufficient_funds_cooldown_max_sec,
            ),
            self.insufficient_funds_cooldown_step_sec,
            1800.0,
        )

        self.failure_window_sec = self._clamp(
            self._to_float(runtime.get("recent_failure_window_sec", self.failure_window_sec), self.failure_window_sec),
            30.0,
            3600.0,
        )
        self.failure_rate_min_attempts = int(
            self._clamp(
                self._to_float(
                    runtime.get("recent_failure_min_attempts", self.failure_rate_min_attempts),
                    self.failure_rate_min_attempts,
                ),
                2.0,
                200.0,
            )
        )
        self.failure_rate_threshold = self._clamp(
            self._to_float(runtime.get("recent_failure_threshold", self.failure_rate_threshold), self.failure_rate_threshold),
            0.10,
            0.95,
        )
        self.failure_rate_hard_block_threshold = self._clamp(
            self._to_float(
                runtime.get("recent_failure_hard_block_threshold", self.failure_rate_hard_block_threshold),
                self.failure_rate_hard_block_threshold,
            ),
            self.failure_rate_threshold,
            0.99,
        )
        self.failure_rate_notional_floor = self._clamp(
            self._to_float(
                runtime.get("recent_failure_notional_floor", self.failure_rate_notional_floor),
                self.failure_rate_notional_floor,
            ),
            0.02,
            1.00,
        )
        self.failure_rate_buy_cooldown_sec = self._clamp(
            self._to_float(
                runtime.get("recent_failure_buy_cooldown_sec", self.failure_rate_buy_cooldown_sec),
                self.failure_rate_buy_cooldown_sec,
            ),
            5.0,
            900.0,
        )

        self.min_order_override_multiplier = self._clamp(
            self._to_float(
                runtime.get("min_order_override_multiplier", self.min_order_override_multiplier),
                self.min_order_override_multiplier,
            ),
            1.05,
            10.0,
        )
        self.min_order_volume_error_buy_cooldown_sec = self._clamp(
            self._to_float(
                runtime.get("min_order_volume_error_buy_cooldown_sec", self.min_order_volume_error_buy_cooldown_sec),
                self.min_order_volume_error_buy_cooldown_sec,
            ),
            0.0,
            1200.0,
        )
        self.max_symbol_min_order = self._clamp(
            self._to_float(runtime.get("max_symbol_min_order", self.max_symbol_min_order), self.max_symbol_min_order),
            0.01,
            10_000_000.0,
        )

        self.universe_spread_scan_enabled = bool(
            runtime.get("universe_spread_scan_enabled", self.universe_spread_scan_enabled)
        )
        self.universe_sample_size = int(
            self._clamp(
                self._to_float(runtime.get("universe_sample_size", self.universe_sample_size), self.universe_sample_size),
                1.0,
                64.0,
            )
        )
        self.universe_max_pick_spread_bps = self._clamp(
            self._to_float(
                runtime.get("universe_max_pick_spread_bps", self.universe_max_pick_spread_bps),
                self.universe_max_pick_spread_bps,
            ),
            5.0,
            250.0,
        )
        self.low_balance_sample_trigger_usd = self._clamp(
            self._to_float(
                runtime.get("low_balance_sample_trigger_usd", self.low_balance_sample_trigger_usd),
                self.low_balance_sample_trigger_usd,
            ),
            0.0,
            1000.0,
        )
        self.low_balance_sample_size = int(
            self._clamp(
                self._to_float(runtime.get("low_balance_sample_size", self.low_balance_sample_size), self.low_balance_sample_size),
                1.0,
                200.0,
            )
        )

    @staticmethod
    def _spread_bps_from_ticker(ticker: Optional[dict[str, Any]]) -> float:
        if not isinstance(ticker, dict):
            return float("inf")
        try:
            bid = float(ticker.get("bid", 0.0) or 0.0)
            ask = float(ticker.get("ask", 0.0) or 0.0)
            if bid <= 0.0 or ask <= 0.0:
                return float("inf")
            mid = max((bid + ask) / 2.0, 1e-9)
            return abs((ask - bid) / mid) * 10000.0
        except Exception:
            return float("inf")

    def _select_symbol_from_universe(
        self,
        preferred: str,
        candidates: list[str],
        affordable_usd_hint: float = 0.0,
        max_notional_usd_cap: float = 0.0,
        allow_preferred_shortcut: bool = True,
    ) -> tuple[Optional[str], Optional[dict[str, Any]], dict[str, Any]]:
        pref = str(preferred or "").upper().strip()
        rows = [str(s).upper().strip() for s in (candidates or []) if str(s).strip()]
        unique = list(dict.fromkeys(rows))
        meta: dict[str, Any] = {
            "preferred_symbol": pref,
            "universe_candidate_count": len(unique),
            "universe_sample_size": 0,
            "universe_sample_escalated": False,
            "universe_ticker_hits": 0,
            "universe_affordability_rejects": 0,
            "symbol_source": "none",
            "selected_spread_bps": None,
            "selected_min_order_notional": None,
        }

        if allow_preferred_shortcut and pref and self.router.get_symbol_config(pref):
            meta["symbol_source"] = "preferred"
            return pref, None, meta

        if not unique:
            return None, None, meta

        if not self.universe_spread_scan_enabled:
            picked = random.choice(unique)
            meta["symbol_source"] = "random_scan_disabled"
            return picked, None, meta

        sample_size = min(max(int(self.universe_sample_size), 1), len(unique))
        if (
            affordable_usd_hint > 0.0
            and affordable_usd_hint <= float(self.low_balance_sample_trigger_usd)
            and len(unique) > sample_size
        ):
            sample_size = min(max(sample_size, int(self.low_balance_sample_size)), len(unique))
            meta["universe_sample_escalated"] = True
        sampled = random.sample(unique, sample_size) if len(unique) > sample_size else list(unique)
        meta["universe_sample_size"] = len(sampled)

        best_symbol: Optional[str] = None
        best_ticker: Optional[dict[str, Any]] = None
        best_spread = float("inf")
        best_min_notional = float("inf")
        ticker_hits = 0
        affordability_rejects = 0
        lowest_reject_symbol: Optional[str] = None
        lowest_reject_ticker: Optional[dict[str, Any]] = None
        lowest_reject_notional = float("inf")
        lowest_reject_spread = float("inf")

        for symbol in sampled:
            ticker = self.router.get_ticker(symbol)
            if not ticker:
                continue
            spread_bps = self._spread_bps_from_ticker(ticker)
            if not math.isfinite(spread_bps):
                continue

            cfg = self.router.get_symbol_config(symbol) or {}
            min_order_qty = self._to_float(cfg.get("min_order", 0.0), 0.0)
            last_px = self._to_float(ticker.get("last", 0.0), 0.0)
            min_order_notional = max(min_order_qty, 0.0) * max(last_px, 0.0)

            if max_notional_usd_cap > 0.0 and min_order_notional > float(max_notional_usd_cap):
                affordability_rejects += 1
                if min_order_notional < lowest_reject_notional:
                    lowest_reject_notional = min_order_notional
                    lowest_reject_symbol = symbol
                    lowest_reject_ticker = ticker
                    lowest_reject_spread = spread_bps
                continue

            if affordable_usd_hint > 0.0 and min_order_notional > float(affordable_usd_hint):
                affordability_rejects += 1
                if min_order_notional < lowest_reject_notional:
                    lowest_reject_notional = min_order_notional
                    lowest_reject_symbol = symbol
                    lowest_reject_ticker = ticker
                    lowest_reject_spread = spread_bps
                continue

            ticker_hits += 1
            if spread_bps < best_spread:
                best_spread = spread_bps
                best_symbol = symbol
                best_ticker = ticker
                best_min_notional = min_order_notional

        meta["universe_ticker_hits"] = ticker_hits
        meta["universe_affordability_rejects"] = affordability_rejects

        if best_symbol is not None:
            meta["selected_spread_bps"] = round(float(best_spread), 6)
            meta["selected_min_order_notional"] = round(float(best_min_notional), 6)
            if best_spread <= float(self.universe_max_pick_spread_bps):
                meta["symbol_source"] = "spread_scan"
                return best_symbol, best_ticker, meta
            meta["symbol_source"] = "spread_scan_wide"
            return best_symbol, best_ticker, meta

        if lowest_reject_symbol is not None and lowest_reject_ticker is not None:
            meta["selected_spread_bps"] = round(float(lowest_reject_spread), 6)
            meta["selected_min_order_notional"] = round(float(lowest_reject_notional), 6)
            meta["symbol_source"] = "affordability_floor_fallback"
            return lowest_reject_symbol, lowest_reject_ticker, meta

        fallback = random.choice(unique)
        meta["symbol_source"] = "random_no_ticker"
        return fallback, None, meta

    def _build_realtime_features(self, symbol: str, ticker: dict[str, float]) -> dict[str, Any]:
        bid = float(ticker.get("bid", 0.0) or 0.0)
        ask = float(ticker.get("ask", 0.0) or 0.0)
        last = float(ticker.get("last", 0.0) or 0.0)
        mid = max((bid + ask) / 2.0, 1e-9)
        spread_bps = abs((ask - bid) / mid) * 10000.0

        history = self.mid_history.setdefault(symbol, [])
        history.append(mid)
        if len(history) > 240:
            history.pop(0)

        returns: list[float] = []
        lookback = history[-60:] if len(history) > 60 else history
        for idx in range(1, len(lookback)):
            prev = lookback[idx - 1]
            if prev <= 0:
                continue
            returns.append((lookback[idx] / prev) - 1.0)

        if returns:
            mean_ret = sum(returns) / len(returns)
            variance = sum((ret - mean_ret) ** 2 for ret in returns) / len(returns)
            vol_pct = math.sqrt(max(variance, 0.0)) * 100.0
        else:
            vol_pct = 0.0

        short_slice = history[-6:] if len(history) >= 6 else history
        long_slice = history[-24:] if len(history) >= 24 else history
        short_ma = sum(short_slice) / max(len(short_slice), 1)
        long_ma = sum(long_slice) / max(len(long_slice), 1)

        micro_ret = (history[-1] / history[-4] - 1.0) if len(history) >= 4 and history[-4] > 0 else 0.0
        swing_ret = (history[-1] / history[-18] - 1.0) if len(history) >= 18 and history[-18] > 0 else micro_ret
        momentum = (0.6 * micro_ret) + (0.4 * swing_ret)

        alignment = self._clamp(0.56 + (momentum * 45.0) - (spread_bps / 220.0), 0.10, 0.99)
        cross_confirm = self._clamp(
            0.54 + (((short_ma / max(long_ma, 1e-9)) - 1.0) * 70.0) - (vol_pct / 85.0),
            0.10,
            0.99,
        )
        liquidity_score = self._clamp(1.0 - (spread_bps / 35.0), 0.10, 1.0)
        regime_confidence = self._clamp(0.55 + (abs(momentum) * 70.0) - (vol_pct / 70.0), 0.10, 0.99)
        signal_decay = self._clamp(0.16 + (spread_bps / 220.0) + (max(vol_pct - 2.0, 0.0) / 50.0), 0.08, 0.95)
        expected_edge_bps = max(
            3.0,
            (
                (abs(momentum) * 10000.0 * 0.55)
                + (abs(micro_ret) * 10000.0 * 0.25)
                - (spread_bps * 0.45)
                + self.aggressive_edge_bonus_bps
            )
            * self.edge_multiplier,
        )

        if vol_pct >= 4.5:
            market_regime = "volatile"
        elif momentum >= 0.002:
            market_regime = "bull"
        elif momentum <= -0.002:
            market_regime = "bear"
        else:
            market_regime = "normal"

        return {
            "bid": bid,
            "ask": ask,
            "last": last,
            "spread_bps": spread_bps,
            "volatility_pct": max(vol_pct, 0.1),
            "alignment_score": alignment,
            "cross_confirm_score": cross_confirm,
            "liquidity_score": liquidity_score,
            "regime_confidence": regime_confidence,
            "signal_decay_score": signal_decay,
            "expected_edge_bps": expected_edge_bps,
            "direction_hint": 1.0 if momentum >= 0 else 0.0,
            "market_regime": market_regime,
            "orderbook_depth_usd": max(20000.0 * liquidity_score, 2500.0),
            "orderbook_spread_bps": spread_bps,
            "orderbook_imbalance": self._clamp(((short_ma / max(long_ma, 1e-9)) - 1.0) * 15.0, -1.0, 1.0),
            "onchain_tx_volume_usd": max(100000.0 * regime_confidence, 0.0),
            "onchain_gas_fee_usd": self._clamp(25.0 + (vol_pct * 5.0), 5.0, 300.0),
            "onchain_whale_tx_count": 1 if abs(momentum) * 10000.0 >= 4.0 else 0,
        }

    @staticmethod
    def _parse_iso_utc(raw: str) -> datetime:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _buy_cooldown_active(self, now: datetime) -> bool:
        raw = str(self.buy_cooldown_until_utc or "").strip()
        if not raw:
            return False
        try:
            until = self._parse_iso_utc(raw)
            return now < until
        except Exception:
            return False

    def _set_buy_cooldown(self, now: datetime, seconds: float) -> None:
        sec = max(float(seconds), 0.0)
        if sec <= 0.0:
            self.buy_cooldown_until_utc = ""
            return
        self.buy_cooldown_until_utc = (now + timedelta(seconds=sec)).isoformat()

    def _prune_recent_order_windows(self, now: datetime) -> None:
        cutoff = now - timedelta(seconds=max(float(self.failure_window_sec), 30.0))
        self.recent_order_attempt_utc = [ts for ts in self.recent_order_attempt_utc if ts >= cutoff]
        self.recent_order_fail_utc = [ts for ts in self.recent_order_fail_utc if ts >= cutoff]

    def _failure_window_metrics(self, now: datetime) -> tuple[int, int, float, float]:
        self._prune_recent_order_windows(now)
        attempts = len(self.recent_order_attempt_utc)
        failures = len(self.recent_order_fail_utc)
        fail_rate = (float(failures) / float(attempts)) if attempts > 0 else 0.0
        throttle = 1.0
        if attempts >= int(self.failure_rate_min_attempts) and fail_rate >= float(self.failure_rate_threshold):
            overflow = max(fail_rate - float(self.failure_rate_threshold), 0.0)
            span = max(1.0 - float(self.failure_rate_threshold), 1e-6)
            penalty = self._clamp(overflow / span, 0.0, 1.0)
            throttle = self._clamp(1.0 - penalty, float(self.failure_rate_notional_floor), 1.0)
        return attempts, failures, fail_rate, throttle

    def _record_order_attempt(self, now: datetime, success: bool) -> tuple[int, int, float, float]:
        self.recent_order_attempt_utc.append(now)
        if not success:
            self.recent_order_fail_utc.append(now)
        return self._failure_window_metrics(now)

    def _effective_min_order(self, symbol: str, static_min_order: float) -> float:
        override = float(self.symbol_min_order_overrides.get(symbol.upper(), 0.0) or 0.0)
        return max(float(static_min_order), override)

    def _raise_min_order_override(self, symbol: str, current_min_order: float) -> tuple[float, float]:
        symbol_key = symbol.upper()
        current = self._effective_min_order(symbol_key, current_min_order)
        boosted = min(max(current * float(self.min_order_override_multiplier), current), float(self.max_symbol_min_order))
        if boosted > current:
            self.symbol_min_order_overrides[symbol_key] = float(boosted)
        return current, boosted

    @staticmethod
    def _position_pnl_pct(pos: Position, last: float) -> float:
        entry = max(float(pos.entry_price), 1e-9)
        side = str(pos.side).strip().lower()
        if side == "short":
            return (entry - float(last)) / entry
        return (float(last) - entry) / entry

    def _no_affordable_recycle_cooldown_active(self, now: datetime) -> bool:
        if float(self.no_affordable_recycle_cooldown_sec) <= 0.0:
            return False
        raw = str(self.no_affordable_last_recycle_utc or "").strip()
        if not raw:
            return False
        try:
            last = self._parse_iso_utc(raw)
        except Exception:
            return False
        return (now - last).total_seconds() < float(self.no_affordable_recycle_cooldown_sec)

    def _attempt_no_affordable_capital_recycle(self, now: datetime) -> dict[str, Any]:
        result: dict[str, Any] = {
            "attempted": True,
            "executed": False,
            "reason": "none",
            "open_positions": 0,
        }

        if not self.no_affordable_recycle_enabled:
            result["attempted"] = False
            result["reason"] = "disabled"
            return result

        if self._no_affordable_recycle_cooldown_active(now):
            result["reason"] = "cooldown_active"
            result["cooldown_sec"] = round(float(self.no_affordable_recycle_cooldown_sec), 3)
            return result

        open_positions = self.portfolio.get_open_positions()
        result["open_positions"] = int(len(open_positions))
        if not open_positions:
            result["reason"] = "no_open_positions"
            return result

        max_hold_sec = self._to_float(self.runtime_cfg.get("position_max_hold_seconds", 240.0), 240.0)
        best: Optional[dict[str, Any]] = None

        for pos in open_positions:
            base_symbol = str(pos.symbol).split("/")[0].upper().strip()
            if not base_symbol:
                continue
            ticker = self.router.get_ticker(base_symbol)
            if not isinstance(ticker, dict):
                continue
            last = self._to_float(ticker.get("last", 0.0), 0.0)
            if last <= 0.0:
                continue

            try:
                entry_dt = self._parse_iso_utc(pos.entry_time_utc)
                hold_sec = max((now - entry_dt).total_seconds(), 0.0)
            except Exception:
                hold_sec = max_hold_sec + 1.0

            pnl_pct = self._position_pnl_pct(pos, last)
            eligible = (
                hold_sec >= float(self.no_affordable_recycle_min_hold_sec)
                or hold_sec >= max_hold_sec
                or pnl_pct >= 0.001
            )
            if not eligible:
                continue

            notional_usd = abs(float(pos.qty) * float(last))
            score = (pnl_pct * 100.0) + min(hold_sec / 180.0, 8.0)

            if best is None or score > float(best["score"]):
                best = {
                    "position": pos,
                    "base_symbol": base_symbol,
                    "last": float(last),
                    "hold_sec": float(hold_sec),
                    "pnl_pct": float(pnl_pct),
                    "notional_usd": float(notional_usd),
                    "score": float(score),
                }

        if best is None:
            result["reason"] = "no_eligible_positions"
            return result

        pos = best["position"]
        close_side = "sell" if str(pos.side).lower() == "long" else "buy"
        close_qty = float(pos.qty)
        order_result = self.router.place_order(str(best["base_symbol"]), close_side, close_qty, None)

        if "error" in order_result:
            result["reason"] = "order_failed"
            result["symbol"] = str(best["base_symbol"])
            result["error"] = str(order_result.get("error"))
            return result

        txid = order_result.get("txid", ["unknown"])
        txid = txid[0] if isinstance(txid, list) else str(txid)

        self.portfolio.close_position(str(pos.symbol), float(best["last"]), now.isoformat())
        self.no_affordable_last_recycle_utc = now.isoformat()
        recycle_cfg = self.router.get_symbol_config(str(best["base_symbol"])) or {}
        recycle_pair = str(recycle_cfg.get("pair") or "")

        self.trade_ledger.append(
            {
                "timestamp": now.isoformat(),
                "txid": txid,
                "symbol": str(best["base_symbol"]),
            "pair": recycle_pair,
                "direction": str(pos.side),
                "side": close_side,
                "status": "CAPITAL_RECYCLE_CLOSED",
                "execution_mode": "capital_recycle",
                "entry_price": round(float(pos.entry_price), 6),
                "exit_price": round(float(best["last"]), 6),
                "qty": round(float(close_qty), 10),
                "size_usd": round(float(best["notional_usd"]), 6),
                "pnl_pct": round(float(best["pnl_pct"]) * 100.0, 6),
                "hold_sec": round(float(best["hold_sec"]), 3),
            }
        )
        self.audit_chain.append(
            "live_order_closed_capital_recycle",
            {
                "symbol": str(best["base_symbol"]),
                "side": close_side,
                "direction": str(pos.side),
                "qty": round(float(close_qty), 10),
                "txid": txid,
                "pnl_pct": round(float(best["pnl_pct"]) * 100.0, 6),
                "hold_sec": round(float(best["hold_sec"]), 3),
            },
        )

        result.update(
            {
                "executed": True,
                "reason": "capital_recycle_executed",
                "symbol": str(best["base_symbol"]),
                "txid": txid,
                "side": close_side,
                "qty": round(float(close_qty), 10),
                "size_usd": round(float(best["notional_usd"]), 6),
                "pnl_pct": round(float(best["pnl_pct"]) * 100.0, 6),
                "hold_sec": round(float(best["hold_sec"]), 3),
            }
        )
        return result

    def _maybe_close_positions(self, symbol: str, last: float, now: datetime) -> bool:
        open_positions = self.portfolio.get_open_positions()
        symbol_positions = [
            p for p in open_positions
            if str(p.symbol).upper().startswith(f"{symbol.upper()}/")
        ]
        if not symbol_positions:
            return False

        tp_bps = self._to_float(self.runtime_cfg.get("position_tp_net_bps", 65.0), 65.0)
        sl_bps = self._to_float(self.runtime_cfg.get("position_sl_net_bps", 40.0), 40.0)
        min_hold_sec = self._to_float(self.runtime_cfg.get("position_min_hold_seconds", 15.0), 15.0)
        max_hold_sec = self._to_float(self.runtime_cfg.get("position_max_hold_seconds", 240.0), 240.0)

        tp_pct = max(tp_bps / 10000.0, 0.0)
        sl_pct = max(sl_bps / 10000.0, 0.0)

        for pos in symbol_positions:
            try:
                entry_dt = self._parse_iso_utc(pos.entry_time_utc)
                hold_sec = max((now - entry_dt).total_seconds(), 0.0)
            except Exception:
                hold_sec = max_hold_sec + 1.0

            pnl_pct = self._position_pnl_pct(pos, float(last))
            should_close = (
                (hold_sec >= min_hold_sec and pnl_pct >= tp_pct)
                or (hold_sec >= min_hold_sec and pnl_pct <= (-sl_pct))
                or (hold_sec >= max_hold_sec)
            )
            if not should_close:
                continue

            close_side = "sell" if str(pos.side).lower() == "long" else "buy"
            result = self.router.place_order(symbol, close_side, float(pos.qty), None)
            if "error" in result:
                _write_live_heartbeat(
                    {
                        "status": "error",
                        "reason": "close_order_failed",
                        "symbol": symbol,
                        "side": close_side,
                        "qty": float(pos.qty),
                        "error": str(result.get("error")),
                    }
                )
                continue

            txid = result.get("txid", ["unknown"])
            txid = txid[0] if isinstance(txid, list) else str(txid)

            self.portfolio.close_position(pos.symbol, float(last), now.isoformat())

            self.trade_ledger.append(
                {
                    "timestamp": now.isoformat(),
                    "txid": txid,
                    "symbol": symbol,
                    "pair": self.router.get_symbol_config(symbol)["pair"],
                    "direction": str(pos.side),
                    "side": close_side,
                    "status": "CLOSED",
                    "execution_mode": "close_cycle",
                    "entry_price": round(float(pos.entry_price), 6),
                    "exit_price": round(float(last), 6),
                    "qty": round(float(pos.qty), 10),
                    "pnl_pct": round(float(pnl_pct) * 100.0, 6),
                    "hold_sec": round(float(hold_sec), 3),
                }
            )
            self.audit_chain.append(
                "live_order_closed",
                {
                    "symbol": symbol,
                    "side": close_side,
                    "direction": str(pos.side),
                    "qty": round(float(pos.qty), 10),
                    "txid": txid,
                    "pnl_pct": round(float(pnl_pct) * 100.0, 6),
                    "hold_sec": round(float(hold_sec), 3),
                },
            )

            _write_live_heartbeat(
                {
                    "status": "ok",
                    "reason": "position_closed",
                    "symbol": symbol,
                    "side": close_side,
                    "txid": txid,
                    "pnl_pct": round(float(pnl_pct) * 100.0, 6),
                    "hold_sec": round(float(hold_sec), 3),
                }
            )
            print(f"  closed txid={txid} side={close_side} pnl_pct={pnl_pct*100.0:.3f}%")
            return True

        return False

    def get_decision_engine_input(self, symbol: str, ticker: dict[str, float]) -> Optional[GateInput]:
        if not ticker:
            return None

        regime_name = "normal"
        if self.regime_engine:
            try:
                r = self.regime_engine.classify(symbol)
                regime_name = getattr(r, "name", "normal")
            except Exception:
                pass

        strategy = self.live_selection.get("strategy", "harmonic_blend")
        if self._strategy_regime_conflict(strategy, regime_name):
            return None  # hard block

        features = self._build_realtime_features(symbol, ticker)
        hist_wr = self.portfolio.win_rate() / 100 if getattr(self.portfolio, "total_trades", 0) > 0 else 0.52
        open_positions = len(self.portfolio.get_open_positions())
        sector_heat = min(open_positions / max(float(self.max_open_positions), 1.0), 0.99)

        return GateInput(
            regime=f"{regime_name}|flow={self.live_selection.get('flow')}|strategy={strategy}",
            regime_confidence=float(features["regime_confidence"]),
            alignment_score=float(features["alignment_score"]),
            liquidity_score=float(features["liquidity_score"]),
            signal_decay_score=float(features["signal_decay_score"]),
            cross_confirm_score=float(features["cross_confirm_score"]),
            expected_edge_bps=float(features["expected_edge_bps"]),
            direction_hint=float(features["direction_hint"]),
            volatility_pct=float(features["volatility_pct"]),
            correlation_to_portfolio=0.1,
            market_regime=str(features["market_regime"]),
            sector_heat=sector_heat,
            historical_win_rate=hist_wr,
            monte_carlo_edge=0.0,
            live_data_freshness=0.98,
            orderbook_spread_bps=float(features["orderbook_spread_bps"]),
            orderbook_depth_usd=float(features["orderbook_depth_usd"]),
            orderbook_imbalance=float(features["orderbook_imbalance"]),
            onchain_tx_volume_usd=float(features["onchain_tx_volume_usd"]),
            onchain_gas_fee_usd=float(features["onchain_gas_fee_usd"]),
            onchain_whale_tx_count=int(features["onchain_whale_tx_count"]),
            onchain_data_freshness=0.9,
        )

    def execute_trade_cycle(
        self,
        symbol: str,
        preloaded_ticker: Optional[dict[str, Any]] = None,
        selection_meta: Optional[dict[str, Any]] = None,
    ):
        self._refresh_runtime_config()
        now = datetime.now(timezone.utc)
        print(f"[{now.strftime('%H:%M:%S')}] cycle {symbol}")

        pick_meta = dict(selection_meta or self.last_symbol_selection_meta or {})
        pick_meta.setdefault("selected_symbol", str(symbol or "").upper())

        base_write_heartbeat = globals().get("_write_live_heartbeat")

        def _emit_heartbeat(payload: dict[str, Any]) -> None:
            merged = dict(pick_meta)
            merged.update(payload or {})
            if callable(base_write_heartbeat):
                base_write_heartbeat(merged)

        _write_live_heartbeat = _emit_heartbeat

        ticker = preloaded_ticker if isinstance(preloaded_ticker, dict) else self.router.get_ticker(symbol)
        if not ticker:
            _write_live_heartbeat({"status": "blocked", "reason": "missing_ticker", "symbol": symbol})
            print("  blocked: no ticker")
            return

        gate_input = self.get_decision_engine_input(symbol, ticker)
        if not gate_input:
            _write_live_heartbeat({"status": "blocked", "reason": "regime_or_data", "symbol": symbol})
            print("  blocked: regime/selection conflict or no data")
            return

        gate_decision = self.signal_gate.decide(gate_input)
        gate_override_applied = False
        decision_armed = bool(gate_decision.armed)
        decision_direction = str(gate_decision.direction)

        if (not decision_armed) and self.gate_override_enabled:
            override_conf_ok = float(gate_decision.composite_score) >= float(self.gate_override_min_confidence)
            override_edge_ok = float(gate_input.expected_edge_bps) >= float(self.gate_override_min_edge_bps)
            if override_conf_ok and override_edge_ok:
                gate_override_applied = True
                decision_armed = True
                if decision_direction not in {"long", "short"}:
                    decision_direction = "long" if float(gate_input.direction_hint) >= 0.5 else "short"

        if not decision_armed:
            self.gate_not_armed_streak += 1
            _write_live_heartbeat(
                {
                    "status": "blocked",
                    "reason": "gate_not_armed",
                    "symbol": symbol,
                    "gate_reason_codes": list(gate_decision.reason_codes or []),
                    "gate_composite_score": round(float(gate_decision.composite_score), 6),
                    "gate_confidence_level": round(float(gate_decision.confidence_level), 6),
                    "gate_expected_edge_bps": round(float(gate_input.expected_edge_bps), 6),
                    "gate_min_composite_score": round(float(getattr(self.signal_gate, "min_composite_score", 0.60)), 6),
                    "gate_override_enabled": bool(self.gate_override_enabled),
                    "gate_override_min_confidence": round(float(self.gate_override_min_confidence), 6),
                    "gate_override_min_edge_bps": round(float(self.gate_override_min_edge_bps), 6),
                    "gate_not_armed_streak": int(self.gate_not_armed_streak),
                }
            )
            print("  blocked: gate not armed")
            return
        self.gate_not_armed_streak = 0

        bid, ask, last = ticker["bid"], ticker["ask"], ticker["last"]
        mid = max((bid + ask) / 2.0, 1e-9)
        spread_bps = abs((ask - bid) / mid) * 10000.0
        if spread_bps > 45.0:
            _write_live_heartbeat({
                "status": "blocked",
                "reason": "spread_too_wide",
                "symbol": symbol,
                "spread_bps": round(spread_bps, 6),
            })
            print("  blocked: spread too wide")
            return

        if self._maybe_close_positions(symbol, float(last), now):
            return

        portfolio_heat = self.portfolio.exposure() / max(self.portfolio.current_equity, 1)
        open_positions = len(self.portfolio.get_open_positions())
        runtime_kill_switch = bool(self.runtime_cfg.get("kill_switch", False))
        runtime_live_mode = str(self.runtime_cfg.get("mode", "paper")).strip().lower() == "live"

        liq = self.liquidity_guard.assess(
            LiquiditySnapshot(
                bid=bid, ask=ask, bid_size=1.0, ask_size=1.0,
                est_sweep_cost_bps=5.0, quote_update_rate=2.0
            )
        )
        if not liq.pass_trade:
            _write_live_heartbeat({"status": "blocked", "reason": "liquidity", "symbol": symbol})
            print("  blocked: liquidity")
            return

        risk_allowed, risk_reasons = self.risk_kernel.allow(
            RiskState(
                day_pnl_usd=self.portfolio.realized_pnl_total,
                open_risk_usd=self.portfolio.exposure(),
                portfolio_heat=portfolio_heat,
                symbol_cooldown_active=False,
                open_positions=open_positions,
                max_open_positions=self.max_open_positions,
                live_mode=runtime_live_mode,
                kill_switch=runtime_kill_switch,
            )
        )
        if not risk_allowed:
            _write_live_heartbeat({"status": "blocked", "reason": "risk", "symbol": symbol, "risk_reasons": list(risk_reasons or [])})
            print("  blocked: risk")
            return

        usd_balance = float(self.router.get_balance() or 0.0)
        balance_degraded_mode = False
        if usd_balance <= 0:
            fallback_equity = float(getattr(self.portfolio, "current_equity", 0.0) or 0.0)
            has_credentials = bool(
                getattr(self.router.kraken, "api_key", "")
                and getattr(self.router.kraken, "api_secret", "")
            )
            balance_error = str(getattr(self.router.kraken, "last_balance_error", "") or "")
            configured_fallback = self._to_float(self.runtime_cfg.get("fallback_buying_power_usd", 0.0), 0.0)
            fallback_buying_power = max(min(self.degraded_buying_power_usd, configured_fallback), 0.0)

            if has_credentials and "Rate limit" in balance_error and fallback_buying_power > 0.0:
                usd_balance = max(min(fallback_buying_power, max(fallback_equity, 0.0)), 0.0)
                if usd_balance > 0.0:
                    balance_degraded_mode = True

            if usd_balance <= 0.0:
                _write_live_heartbeat(
                    {
                        "status": "blocked",
                        "reason": "balance_unavailable",
                        "symbol": symbol,
                        "kraken_credentials_present": has_credentials,
                        "balance_error": balance_error,
                        "portfolio_equity_est_usd": round(fallback_equity, 6),
                    }
                )
                print("  blocked: live balance unavailable")
                return
            _write_live_heartbeat(
                {
                    "status": "degraded",
                    "reason": "balance_rate_limited_using_fallback_buying_power",
                    "symbol": symbol,
                    "balance_error": balance_error,
                    "fallback_buying_power_usd": round(usd_balance, 6),
                    "adaptive_buying_power_usd": round(self.degraded_buying_power_usd, 6),
                }
            )

        direction = decision_direction
        window_attempts, window_failures, window_fail_rate, window_throttle = self._failure_window_metrics(now)

        if (
            direction == "long"
            and self.failure_rate_buy_cooldown_sec > 0.0
            and (not self._buy_cooldown_active(now))
            and window_attempts >= int(self.failure_rate_min_attempts)
            and window_fail_rate >= float(self.failure_rate_hard_block_threshold)
        ):
            self._set_buy_cooldown(now, self.failure_rate_buy_cooldown_sec)
            _write_live_heartbeat(
                {
                    "status": "blocked",
                    "reason": "buy_cooldown_failure_rate",
                    "symbol": symbol,
                    "buy_cooldown_until_utc": self.buy_cooldown_until_utc,
                    "recent_attempts": int(window_attempts),
                    "recent_failures": int(window_failures),
                    "recent_fail_rate_pct": round(float(window_fail_rate) * 100.0, 3),
                    "window_notional_throttle": round(float(window_throttle), 6),
                }
            )
            print("  blocked: buy cooldown due to recent failure rate")
            return

        if direction == "long" and self._buy_cooldown_active(now):
            _write_live_heartbeat(
                {
                    "status": "blocked",
                    "reason": "buy_cooldown_active",
                    "symbol": symbol,
                    "buy_cooldown_until_utc": self.buy_cooldown_until_utc,
                    "fail_streak": int(self.order_fail_streak),
                    "notional_throttle": round(float(self.notional_throttle), 6),
                    "recent_attempts": int(window_attempts),
                    "recent_failures": int(window_failures),
                    "recent_fail_rate_pct": round(float(window_fail_rate) * 100.0, 3),
                    "window_notional_throttle": round(float(window_throttle), 6),
                }
            )
            print("  blocked: buy cooldown active")
            return

        stop_price = last * (0.98 if direction == "long" else 1.02)
        urgency = _resolve_urgency(float(gate_decision.composite_score), spread_bps, direction)
        fee_bps = float(self.live_selection.get("fee_bps", 10.0) or 10.0)
        slippage_bps = float(self.live_selection.get("slippage_bps", max(spread_bps * 0.6, 8.0)) or max(spread_bps * 0.6, 8.0))
        drawdown_pct = abs(float(getattr(self.portfolio, "max_drawdown", 0.0) or 0.0))
        reserve_usd_runtime = self._to_float(
            self.runtime_cfg.get("reserve_usd", self.live_selection.get("reserve_usd", 0.0)),
            0.0,
        )
        reserve_usd_effective = self._to_float(pick_meta.get("reserve_usd_effective", reserve_usd_runtime), reserve_usd_runtime)
        reserve_usd = min(max(reserve_usd_effective, 0.0), max(usd_balance, 0.0))
        max_notional_usd = self._to_float(
            self.runtime_cfg.get("max_notional_per_trade_usd", self.live_selection.get("max_notional_usd", 0.0)),
            0.0,
        )
        effective_notional_throttle = min(float(self.notional_throttle), float(window_throttle))
        effective_max_notional_usd = max_notional_usd
        if max_notional_usd > 0.0:
            effective_max_notional_usd = max(0.5, max_notional_usd * max(float(effective_notional_throttle), 0.05))
        size_decision = self.sizing_engine.size(
            SizeInput(
                equity_usd=usd_balance,
                entry_price=last,
                stop_price=stop_price,
                realized_vol=max(0.0001, gate_input.volatility_pct / 100.0),
                edge_score=float(gate_decision.composite_score),
                portfolio_heat=portfolio_heat,
                liquidity_score=self._liquidity_score(liq),
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
                urgency=urgency,
                dislocation_score=max(float(gate_decision.composite_score) - 0.40, 0.0),
                drawdown_pct=drawdown_pct,
                reserve_usd=reserve_usd,
                max_notional_usd=effective_max_notional_usd,
            )
        )

        qty = float(size_decision.qty)
        notional_usd = float(getattr(size_decision, "notional_usd", 0.0))
        risk_usd = float(getattr(size_decision, "risk_usd", 0.0))
        if effective_notional_throttle < 0.999:
            qty = qty * effective_notional_throttle
            notional_usd = qty * float(last)
            risk_usd = max(risk_usd * effective_notional_throttle, 0.0)
        min_order_promoted = False
        if qty <= 0:
            _write_live_heartbeat({"status": "blocked", "reason": "sizing_zero", "symbol": symbol, "urgency": urgency})
            print("  blocked: sizing qty=0")
            return

        cfg = self.router.get_symbol_config(symbol)
        min_order = self._effective_min_order(symbol, float(cfg["min_order"]))
        if qty < min_order:
            min_notional = min_order * float(last)
            affordable = max(float(usd_balance) - reserve_usd, 0.0)
            cap_ok = (effective_max_notional_usd <= 0.0) or (min_notional <= effective_max_notional_usd)
            if min_notional <= affordable and cap_ok:
                qty = min_order
                notional_usd = qty * float(last)
                risk_usd = max(risk_usd, abs(float(last) - float(stop_price)) * qty)
                min_order_promoted = True
            else:
                _write_live_heartbeat({"status": "blocked", "reason": "min_order", "symbol": symbol, "qty": qty, "min_order": min_order})
                print("  blocked: min_order")
                return

        side = "buy" if direction == "long" else "sell"
        route_intent = RouteIntent(
            symbol=symbol,
            side=side,
            qty=qty,
            urgency=urgency,
            entry_price=last,
            stop_price=stop_price,
            take_profit=(last * (1.02 if direction == "long" else 0.98)),
            reduce_only=False,
        )
        order_template = self.order_router.build_primary(route_intent, validate_only=False)
        close_template = self.order_router.build_close_template(route_intent)
        shadow_fill_px, shadow_slip_bps = self.shadow_runner.simulate_fill(bid, ask, side, urgency)
        self.shadow_runner.append_ledger(
            str(LIVE_SHADOW_LEDGER_FILE),
            ShadowFill(
                ts_utc=now.isoformat(),
                symbol=symbol,
                side=side,
                qty=qty,
                est_fill=shadow_fill_px,
                slip_bps=shadow_slip_bps,
                mode="live_shadow",
            ),
        )

        limit_price = None
        if order_template.get("order_type") == "limit":
            limit_price = float(order_template.get("limit_price") or last)
        result = self.router.place_order(symbol, side, qty, limit_price)
        if "error" in result:
            window_attempts, window_failures, window_fail_rate, window_throttle = self._record_order_attempt(now, success=False)
            err_text = str(result.get("error"))
            err_text_l = err_text.lower()
            insufficient_funds = "Insufficient funds" in err_text
            volume_min_error = "volume minimum not met" in err_text_l

            if volume_min_error or insufficient_funds:
                self.order_fail_streak += 1
                self.notional_throttle = max(self.notional_throttle * self.failure_notional_decay, self.failure_notional_floor)

            raised_min_prev = None
            raised_min_new = None
            if volume_min_error:
                raised_min_prev, raised_min_new = self._raise_min_order_override(symbol, min_order)
                if side == "buy" and self.min_order_volume_error_buy_cooldown_sec > 0.0:
                    self._set_buy_cooldown(now, self.min_order_volume_error_buy_cooldown_sec)

            if balance_degraded_mode and insufficient_funds:
                self.degraded_buying_power_usd = max(self.degraded_buying_power_usd * 0.70, 1.0)

            if insufficient_funds:
                if side == "buy":
                    cooldown_sec = min(
                        self.insufficient_funds_cooldown_step_sec * float(self.order_fail_streak),
                        self.insufficient_funds_cooldown_max_sec,
                    )
                    self._set_buy_cooldown(now, cooldown_sec)

            # If buys fail due insufficient quote balance, attempt a tiny unwind sell
            # to recycle capital when spot inventory exists.
            if insufficient_funds and side == "buy":
                unwind_qty = max(min_order, 0.0)
                unwind = self.router.place_order(symbol, "sell", unwind_qty, None)
                if "error" not in unwind:
                    unwind_txid = unwind.get("txid", ["unknown"])
                    unwind_txid = unwind_txid[0] if isinstance(unwind_txid, list) else str(unwind_txid)
                    self.trade_ledger.append(
                        {
                            "timestamp": now.isoformat(),
                            "txid": unwind_txid,
                            "symbol": symbol,
                            "pair": cfg["pair"],
                            "direction": "flat",
                            "side": "sell",
                            "status": "UNWIND_SELL",
                            "execution_mode": "liquidity_recycle",
                            "entry_price": round(float(last), 6),
                            "qty": round(float(unwind_qty), 10),
                            "size_usd": round(float(unwind_qty) * float(last), 6),
                        }
                    )
                    _write_live_heartbeat(
                        {
                            "status": "degraded",
                            "reason": "insufficient_funds_unwind_sell",
                            "symbol": symbol,
                            "txid": unwind_txid,
                            "qty": round(float(unwind_qty), 10),
                            "fail_streak": int(self.order_fail_streak),
                            "notional_throttle": round(float(self.notional_throttle), 6),
                            "buy_cooldown_until_utc": self.buy_cooldown_until_utc,
                            "recent_attempts": int(window_attempts),
                            "recent_failures": int(window_failures),
                            "recent_fail_rate_pct": round(float(window_fail_rate) * 100.0, 3),
                            "window_notional_throttle": round(float(window_throttle), 6),
                            "effective_min_order": round(float(min_order), 10),
                            "raised_min_order_prev": round(float(raised_min_prev), 10) if raised_min_prev is not None else None,
                            "raised_min_order_new": round(float(raised_min_new), 10) if raised_min_new is not None else None,
                        }
                    )
                    print(f"  unwind sell txid={unwind_txid}")
                    return
            _write_live_heartbeat(
                {
                    "status": "error",
                    "reason": "order_failed",
                    "symbol": symbol,
                    "side": side,
                    "error": str(result.get("error")),
                    "fail_streak": int(self.order_fail_streak),
                    "notional_throttle": round(float(self.notional_throttle), 6),
                    "buy_cooldown_until_utc": self.buy_cooldown_until_utc,
                    "recent_attempts": int(window_attempts),
                    "recent_failures": int(window_failures),
                    "recent_fail_rate_pct": round(float(window_fail_rate) * 100.0, 3),
                    "window_notional_throttle": round(float(window_throttle), 6),
                    "effective_min_order": round(float(min_order), 10),
                    "raised_min_order_prev": round(float(raised_min_prev), 10) if raised_min_prev is not None else None,
                    "raised_min_order_new": round(float(raised_min_new), 10) if raised_min_new is not None else None,
                }
            )
            print(f"  order failed: {result['error']}")
            return

        window_attempts, window_failures, window_fail_rate, window_throttle = self._record_order_attempt(now, success=True)

        if balance_degraded_mode:
            configured_fallback = max(self._to_float(self.runtime_cfg.get("fallback_buying_power_usd", 0.0), 0.0), 0.0)
            self.degraded_buying_power_usd = min(max(self.degraded_buying_power_usd * 1.03, notional_usd), configured_fallback)

        self.order_fail_streak = max(self.order_fail_streak - 1, 0)
        self.notional_throttle = min(self.notional_throttle + self.success_notional_recovery_step, 1.0)
        if self.order_fail_streak == 0:
            self._set_buy_cooldown(now, 0.0)

        txid = result.get("txid", ["unknown"])
        txid = txid[0] if isinstance(txid, list) else str(txid)

        self.portfolio.add_position(
            Position(
                symbol=f"{symbol}/USD",
                side=direction,
                entry_price=last,
                current_price=last,
                qty=qty,
                entry_time_utc=now.isoformat(),
                flowform=self.live_selection.get("flow", "fallback"),
                algo="echo_stack",
                strategy=self.live_selection.get("strategy", "harmonic_blend"),
                order_id=txid,
                status="OPEN",
            )
        )

        ledger_hash = self.trade_ledger.append(
            {
                "timestamp": now.isoformat(),
                "txid": txid,
                "symbol": symbol,
                "pair": cfg["pair"],
                "direction": direction,
                "side": side,
                "status": "PLACED",
                "execution_mode": urgency,
                "gate_score": round(float(gate_decision.composite_score), 6),
                "entry_price": round(float(last), 6),
                "qty": round(qty, 10),
                "size_usd": round(notional_usd, 6),
                "risk_usd": round(risk_usd, 6),
                "round_trip_fee_usd": 0.0,
                "tp_net_bps": round((((float(route_intent.take_profit or last) / max(float(last), 1e-9)) - 1.0) * 10000.0), 6),
                "sl_net_bps": round((((float(route_intent.stop_price or last) / max(float(last), 1e-9)) - 1.0) * 10000.0), 6),
            }
        )
        audit_row = self.audit_chain.append(
            "live_order_placed",
            {
                "symbol": symbol,
                "pair": cfg["pair"],
                "side": side,
                "direction": direction,
                "urgency": urgency,
                "gate_score": round(float(gate_decision.composite_score), 6),
                "txid": txid,
                "ledger_hash": ledger_hash,
            },
        )

        self.trade_log.append(
            {
                "timestamp": now.isoformat(),
                "txid": txid,
                "symbol": symbol,
                "pair": cfg["pair"],
                "direction": direction,
                "side": side,
                "entry_price": last,
                "qty": qty,
                "size_usd": notional_usd,
                "risk_usd": risk_usd,
                "flow": self.live_selection.get("flow"),
                "strategy": self.live_selection.get("strategy"),
                "edge_multiplier": self.edge_multiplier,
                "urgency": urgency,
                "min_order_promoted": bool(min_order_promoted),
                "gate_override_applied": bool(gate_override_applied),
                "gate_reason_codes": list(gate_decision.reason_codes or []),
                "balance_degraded_mode": bool(balance_degraded_mode),
                "notional_throttle": round(float(self.notional_throttle), 6),
                "fail_streak": int(self.order_fail_streak),
                "window_notional_throttle": round(float(window_throttle), 6),
                "effective_notional_throttle": round(float(effective_notional_throttle), 6),
                "recent_attempts": int(window_attempts),
                "recent_failures": int(window_failures),
                "recent_fail_rate_pct": round(float(window_fail_rate) * 100.0, 3),
                "effective_min_order": round(float(min_order), 10),
                "spread_bps": round(spread_bps, 6),
                "shadow_fill": {"est_fill": round(shadow_fill_px, 6), "slip_bps": round(shadow_slip_bps, 6)},
                "order_template": order_template,
                "close_template": close_template,
                "ledger_hash": ledger_hash,
                "audit_hash": audit_row.get("event_hash"),
                "status": "PLACED",
            }
        )

        with open(LIVE_TRADE_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.trade_log, f, indent=2)

        _write_live_heartbeat(
            {
                "status": "ok",
                "symbol": symbol,
                "pair": cfg["pair"],
                "side": side,
                "txid": txid,
                "urgency": urgency,
                "spread_bps": round(spread_bps, 6),
                "size_usd": round(notional_usd, 6),
                "risk_usd": round(risk_usd, 6),
                "min_order_promoted": bool(min_order_promoted),
                "gate_override_applied": bool(gate_override_applied),
                "gate_reason_codes": list(gate_decision.reason_codes or []),
                "balance_degraded_mode": bool(balance_degraded_mode),
                "notional_throttle": round(float(self.notional_throttle), 6),
                "fail_streak": int(self.order_fail_streak),
                "window_notional_throttle": round(float(window_throttle), 6),
                "effective_notional_throttle": round(float(effective_notional_throttle), 6),
                "recent_attempts": int(window_attempts),
                "recent_failures": int(window_failures),
                "recent_fail_rate_pct": round(float(window_fail_rate) * 100.0, 3),
                "effective_min_order": round(float(min_order), 10),
                "edge_score": round(float(gate_decision.composite_score), 6),
                "portfolio_heat": round(portfolio_heat, 6),
                "open_positions": open_positions,
                "max_open_positions": self.max_open_positions,
            }
        )

        print(f"  placed txid={txid}")

    def run_institutional_execution_loop(self):
        print(f"starting live loop (interval={self.loop_seconds:.2f}s, max_open={self.max_open_positions})")
        while True:
            try:
                self._refresh_runtime_config()
                preferred = (_preferred_live_symbol() or "").upper().strip()

                scan_cap = int(self._to_float(self.runtime_cfg.get("scan_top_n", 500), 500.0))
                scan_cap = max(scan_cap, 4)
                candidates = self.router.get_candidate_symbols(max_symbols=scan_cap)

                # Respect runtime blacklists for live symbol selection.
                blacklisted = {
                    str(s).upper().strip()
                    for s in (self.runtime_cfg.get("symbol_blacklist", []) or [])
                    if str(s).strip()
                }
                hard_blacklisted = {
                    str(s).upper().strip()
                    for s in (self.runtime_cfg.get("hard_symbol_blacklist", []) or [])
                    if str(s).strip()
                }
                blocked = blacklisted.union(hard_blacklisted)
                candidates = [s for s in candidates if s not in blocked]
                if not candidates:
                    candidates = [s for s in SYMBOL_REGISTRY.keys() if s.upper() not in blocked]

                loop_now = datetime.now(timezone.utc)
                reserve_usd_configured = max(self._to_float(self.runtime_cfg.get("reserve_usd", 0.0), 0.0), 0.0)
                max_notional_usd_cap = max(
                    self._to_float(self.runtime_cfg.get("max_notional_per_trade_usd", 0.0), 0.0),
                    0.0,
                )
                usd_balance_hint = max(float(self.router.get_balance() or 0.0), 0.0)
                reserve_usd_hint = float(reserve_usd_configured)
                if self.dynamic_reserve_enabled and usd_balance_hint > 0.0:
                    dynamic_cap = max(
                        float(self.dynamic_reserve_floor_usd),
                        float(usd_balance_hint) * float(self.dynamic_reserve_max_balance_fraction),
                    )
                    reserve_usd_hint = min(float(reserve_usd_configured), float(dynamic_cap))
                affordable_usd_hint = max(usd_balance_hint - reserve_usd_hint, 0.0)

                symbol = preferred
                preferred_cfg = self.router.get_symbol_config(symbol) if symbol else None
                preferred_ticker = self.router.get_ticker(symbol) if (symbol and preferred_cfg and symbol not in blocked) else None
                preferred_min_order_notional = 0.0
                preferred_affordable = True
                if preferred_cfg and preferred_ticker:
                    preferred_min_order_notional = max(
                        self._to_float(preferred_cfg.get("min_order", 0.0), 0.0),
                        0.0,
                    ) * max(self._to_float(preferred_ticker.get("last", 0.0), 0.0), 0.0)
                    if max_notional_usd_cap > 0.0 and preferred_min_order_notional > max_notional_usd_cap:
                        preferred_affordable = False
                    if affordable_usd_hint > 0.0 and preferred_min_order_notional > affordable_usd_hint:
                        preferred_affordable = False

                preloaded_ticker: Optional[dict[str, Any]] = None
                selection_meta: dict[str, Any] = {
                    "preferred_symbol": preferred,
                    "preferred_min_order_notional": round(float(preferred_min_order_notional), 6),
                    "blocked_count": len(blocked),
                    "universe_scan_cap": int(scan_cap),
                    "reserve_usd_configured": round(float(reserve_usd_configured), 6),
                    "reserve_usd_effective": round(float(reserve_usd_hint), 6),
                    "universe_candidate_count": int(len(candidates)),
                    "universe_sample_size": 0,
                    "universe_ticker_hits": 0,
                    "universe_affordability_rejects": 0,
                    "affordable_usd_hint": round(float(affordable_usd_hint), 6),
                    "max_notional_usd_cap": round(float(max_notional_usd_cap), 6),
                    "symbol_source": "preferred",
                    "selected_spread_bps": None,
                    "selected_min_order_notional": round(float(preferred_min_order_notional), 6)
                    if preferred_min_order_notional > 0.0
                    else None,
                }

                if (
                    (not symbol)
                    or (symbol in blocked)
                    or (not preferred_cfg)
                    or (preferred_ticker is None)
                    or (not preferred_affordable)
                ):
                    symbol, preloaded_ticker, selection_meta = self._select_symbol_from_universe(
                        preferred,
                        candidates,
                        affordable_usd_hint=affordable_usd_hint,
                        max_notional_usd_cap=max_notional_usd_cap,
                        allow_preferred_shortcut=False,
                    )
                    selection_meta["blocked_count"] = int(len(blocked))
                    selection_meta["universe_scan_cap"] = int(scan_cap)
                    selection_meta["reserve_usd_configured"] = round(float(reserve_usd_configured), 6)
                    selection_meta["reserve_usd_effective"] = round(float(reserve_usd_hint), 6)
                    selection_meta["affordable_usd_hint"] = round(float(affordable_usd_hint), 6)
                    selection_meta["max_notional_usd_cap"] = round(float(max_notional_usd_cap), 6)
                    selection_meta["preferred_min_order_notional"] = round(float(preferred_min_order_notional), 6)
                    if not symbol:
                        blocked_payload = dict(selection_meta)
                        blocked_payload.update(
                            {
                                "status": "blocked",
                                "reason": "no_universe_candidates",
                            }
                        )
                        _write_live_heartbeat(blocked_payload)
                        time.sleep(self.loop_seconds)
                        continue
                else:
                    preloaded_ticker = preferred_ticker

                selection_meta["selected_symbol"] = str(symbol).upper()
                self.last_symbol_selection_meta = dict(selection_meta)

                selected_min_notional = self._to_float(selection_meta.get("selected_min_order_notional", 0.0), 0.0)
                unaffordable_by_balance = affordable_usd_hint > 0.0 and selected_min_notional > affordable_usd_hint
                unaffordable_by_cap = max_notional_usd_cap > 0.0 and selected_min_notional > max_notional_usd_cap
                if selected_min_notional > 0.0 and (unaffordable_by_balance or unaffordable_by_cap):
                    self.no_affordable_streak += 1
                    recycle_result: Optional[dict[str, Any]] = None
                    if (
                        self.no_affordable_recycle_enabled
                        and self.no_affordable_streak >= int(self.no_affordable_recycle_streak_trigger)
                    ):
                        recycle_result = self._attempt_no_affordable_capital_recycle(loop_now)

                    blocked_payload = dict(selection_meta)
                    blocked_payload.update(
                        {
                            "status": "blocked",
                            "reason": "no_affordable_symbol",
                            "selected_symbol": str(symbol).upper(),
                            "selected_min_order_notional": round(float(selected_min_notional), 6),
                            "affordable_usd_hint": round(float(affordable_usd_hint), 6),
                            "max_notional_usd_cap": round(float(max_notional_usd_cap), 6),
                            "no_affordable_streak": int(self.no_affordable_streak),
                        }
                    )
                    if isinstance(recycle_result, dict):
                        blocked_payload["capital_recycle"] = recycle_result
                    _write_live_heartbeat(blocked_payload)
                    if isinstance(recycle_result, dict) and bool(recycle_result.get("executed", False)):
                        time.sleep(max(min(self.loop_seconds * 0.40, 2.0), 0.25))
                    else:
                        time.sleep(self.loop_seconds)
                    continue

                self.no_affordable_streak = 0
                self.execute_trade_cycle(symbol, preloaded_ticker=preloaded_ticker, selection_meta=selection_meta)
                time.sleep(self.loop_seconds)
            except KeyboardInterrupt:
                print("stopped")
                break
            except Exception as e:
                loop_meta = dict(self.last_symbol_selection_meta or {})
                loop_meta.update(
                    {
                        "status": "error",
                        "reason": "loop_exception",
                        "symbol": symbol if "symbol" in locals() else "",
                        "error": str(e),
                    }
                )
                _write_live_heartbeat(loop_meta)
                print(f"loop error: {e}")
                time.sleep(5)


if __name__ == "__main__":
    if not _acquire_executor_lock():
        raise SystemExit(0)
    atexit.register(_release_executor_lock)
    api_keys = load_api_keys()
    executor = RobustLiveExecutor(api_keys)
    try:
        executor.run_institutional_execution_loop()
    finally:
        _release_executor_lock()
