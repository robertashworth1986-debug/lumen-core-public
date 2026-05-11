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
SYMBOL_FLIP_INTEL_FILE = OUT / "symbol_flip_intel_top5.json"
COLLATERAL_CONVERT_LOG_FILE = OUT / "collateral_convert_log.jsonl"
KRAKEN_NONCE_STATE_FILE = OUT / "kraken_nonce_state.json"
KRAKEN_BALANCE_CACHE_FILE = OUT / "kraken_balance_cache.json"
KRAKEN_ASSET_PAIRS_CACHE_FILE = OUT / "kraken_asset_pairs_cache.json"
ROLLING_CAPITAL_BEST_MULTI_FILE = Path(r"C:/LumaTrader/rolling_capital/rolling_capital_best_multi.json")
UNIVERSE_SYMBOL_FILE_CANDIDATES = (
    ROOT / "out" / "adaptive_universe.json",
    ROOT / "adaptive_universe.json",
    OUT / "adaptive_universe.json",
)

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
        self._balance_rate_limit_fallback_sec = 600.0
        self._balance_cache_usd = 0.0
        self._balance_cache_utc = ""
        self._balance_snapshot: dict[str, float] = {}
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

    @staticmethod
    def _normalize_balance_asset(asset_code: str) -> str:
        raw = str(asset_code or "").upper().strip()
        if not raw:
            return ""
        token = raw.split(".", 1)[0].strip()
        alias_map = {
            "ZUSD": "USD",
            "XXBT": "BTC",
            "XBT": "BTC",
            "XETH": "ETH",
            "XDG": "DOGE",
            "XXDG": "DOGE",
            "XXRP": "XRP",
            "XXLM": "XLM",
        }
        normalized = alias_map.get(token, token)
        if normalized and normalized[0] in {"X", "Z"} and len(normalized) == 4 and normalized[1:].isalpha():
            normalized = normalized[1:]
        return normalized

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

    def _fetch_balances(self) -> tuple[dict[str, float], str]:
        try:
            result = self._private("/0/private/Balance", {})
            if "error" in result:
                raw_error = result.get("error", "unknown")
                if isinstance(raw_error, list):
                    raw_error = ",".join(str(x) for x in raw_error)
                return {}, f"kraken_balance_api_error:{raw_error}"
            if not isinstance(result, dict):
                return {}, "kraken_balance_api_error:malformed_payload"

            balances: dict[str, float] = {}
            for asset_code, amount in result.items():
                qty = self._to_float(amount, 0.0)
                if (not math.isfinite(qty)) or qty <= 0.0:
                    continue
                balances[str(asset_code).upper().strip()] = float(qty)

            return balances, ""
        except Exception as e:
            return {}, f"balance_exception:{e}"

    def get_account_balances(self, force_refresh: bool = False) -> dict[str, float]:
        self.last_balance_error = ""
        if not self.api_key or not self.api_secret:
            self.last_balance_error = "missing_credentials"
            return {}

        cache_age_sec = self._cached_balance_age_sec()
        if (not force_refresh) and self._balance_snapshot and cache_age_sec <= self._balance_cache_ttl_sec:
            return dict(self._balance_snapshot)

        balances, error_text = self._fetch_balances()
        if balances:
            zusd = float(balances.get("ZUSD", 0.0) or 0.0)
            if zusd > 0.0:
                self._save_balance_cache(zusd)
            else:
                self._balance_cache_utc = datetime.now(timezone.utc).isoformat()
            self._balance_snapshot = dict(balances)
            return dict(self._balance_snapshot)

        self.last_balance_error = str(error_text or "kraken_balance_api_error:unknown")
        rate_limited = "Rate limit" in self.last_balance_error
        cache_age_sec = self._cached_balance_age_sec()

        if rate_limited and self._balance_snapshot and cache_age_sec <= self._balance_rate_limit_fallback_sec:
            self.last_balance_error += ";using_cached_balance_snapshot"
            return dict(self._balance_snapshot)

        if rate_limited and self._balance_cache_usd > 0.0 and cache_age_sec <= self._balance_rate_limit_fallback_sec:
            self.last_balance_error += ";using_cached_usd_only"
            return {"ZUSD": float(self._balance_cache_usd)}

        return {}

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

    def get_account_balance(self, force_refresh: bool = False) -> float:
        balances = self.get_account_balances(force_refresh=force_refresh)
        if balances:
            zusd = self._to_float(balances.get("ZUSD", 0.0), 0.0)
            if zusd > 0.0:
                return float(zusd)

        cache_age_sec = self._cached_balance_age_sec()
        if self._balance_cache_usd > 0.0 and cache_age_sec <= self._balance_rate_limit_fallback_sec:
            if "using_cached_balance" not in self.last_balance_error:
                suffix = ";" if self.last_balance_error else ""
                self.last_balance_error = f"{self.last_balance_error}{suffix}using_cached_balance"
            return float(self._balance_cache_usd)

        if not self.last_balance_error:
            self.last_balance_error = "zusd_zero_or_missing"
        return 0.0

    def get_asset_balance(self, symbol: str, force_refresh: bool = False) -> float:
        target = str(symbol or "").upper().strip()
        if not target:
            return 0.0

        aliases = {target}
        if target == "BTC":
            aliases.add("XBT")
        elif target == "XBT":
            aliases.add("BTC")

        balances = self.get_account_balances(force_refresh=force_refresh)
        if not balances:
            return 0.0

        total = 0.0
        for asset_code, qty in balances.items():
            normalized = self._normalize_balance_asset(asset_code)
            if normalized in aliases:
                total += max(self._to_float(qty, 0.0), 0.0)
        return float(max(total, 0.0))

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
        self._file_symbol_cache: list[str] = []
        self._file_symbol_cache_utc = 0.0
        self._file_symbol_cache_ttl_sec = 120.0

    @staticmethod
    def _normalize_symbol(raw: Any) -> str:
        token = str(raw or "").upper().strip()
        if not token:
            return ""
        if "/" in token:
            token = token.split("/", 1)[0].strip()
        token = token.replace("-", "").replace("_", "").strip()
        if token.endswith("USDT") and len(token) > 4:
            token = token[:-4]
        elif token.endswith("USD") and len(token) > 3:
            token = token[:-3]
        return token.strip()

    def _load_file_universe_symbols(self) -> list[str]:
        now_ts = time.time()
        if self._file_symbol_cache and (now_ts - self._file_symbol_cache_utc) <= self._file_symbol_cache_ttl_sec:
            return list(self._file_symbol_cache)

        discovered: set[str] = set()
        for path in UNIVERSE_SYMBOL_FILE_CANDIDATES:
            payload = load_json(path, {})
            rows: list[Any] = []
            if isinstance(payload, dict):
                maybe_rows = payload.get("symbols", [])
                if isinstance(maybe_rows, list):
                    rows = maybe_rows
            elif isinstance(payload, list):
                rows = payload

            for row in rows:
                normalized = self._normalize_symbol(row)
                if normalized:
                    discovered.add(normalized)

        self._file_symbol_cache = sorted(discovered)
        self._file_symbol_cache_utc = now_ts
        return list(self._file_symbol_cache)

    def get_symbol_config(self, symbol: str):
        key = str(symbol or "").upper().strip()
        if not key:
            return None
        cfg = SYMBOL_REGISTRY.get(key)
        if cfg:
            return cfg
        return self.kraken.resolve_symbol_config(key)

    def get_candidate_symbols(self, max_symbols: int = 120, extra_symbols: Optional[list[str]] = None) -> list[str]:
        symbols = {str(k).upper() for k in SYMBOL_REGISTRY.keys()}
        known = {str(k).upper() for k in SYMBOL_REGISTRY.keys()}
        dynamic_map = self.kraken.get_asset_pairs_map()
        if isinstance(dynamic_map, dict):
            dynamic_keys = {str(k).upper() for k in dynamic_map.keys()}
            symbols.update(dynamic_keys)
            known.update(dynamic_keys)

        symbols.update(self._load_file_universe_symbols())

        for row in (extra_symbols or []):
            normalized = self._normalize_symbol(row)
            if normalized:
                symbols.add(normalized)

        tradable = sorted(s for s in symbols if s in known)
        if not tradable and known:
            tradable = sorted(known)
        if not tradable:
            return []

        cap = max(int(max_symbols or 0), 1)
        if len(tradable) <= cap:
            return tradable
        return random.sample(tradable, cap)

    def get_ticker(self, symbol: str):
        cfg = self.get_symbol_config(symbol)
        if not cfg:
            return None
        return self.kraken.get_ticker(cfg["pair"])

    def get_balance(self, force_refresh: bool = False):
        return self.kraken.get_account_balance(force_refresh=force_refresh)

    def get_asset_balance(self, symbol: str, force_refresh: bool = False):
        return self.kraken.get_asset_balance(symbol, force_refresh=force_refresh)

    def get_balance_snapshot(self, force_refresh: bool = False):
        return self.kraken.get_account_balances(force_refresh=force_refresh)

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
        self.low_balance_ticker_scan_cap = 120
        self.gate_override_enabled = False
        self.gate_override_min_confidence = 0.58
        self.gate_override_min_edge_bps = 7.5
        self.spot_short_enabled = False
        self.close_balance_buffer_fraction = 0.998
        self.spot_inventory_entry_fraction = 0.35
        self.max_symbol_allocation_pct = 0.52
        self.auto_convert_collateral = True
        self.collateral_sell_fraction = 0.20
        self.collateral_convert_cooldown_sec = 12.0
        self.min_collateral_convert_usd = 4.0
        self.last_collateral_convert_utc = ""
        self.stable_assets = {
            "USDT",
            "USDC",
            "DAI",
            "USDE",
            "USD1",
            "RLUSD",
            "USAT",
            "PYUSD",
            "TUSD",
            "FDUSD",
            "USDS",
        }
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
        self.allow_best_multi_preference = False
        self.symbol_intel_enabled = True
        self.symbol_intel_prefer_top_n = 5
        self.symbol_intel_max_age_sec = 1200.0
        self.symbol_intel_min_alpha_score = 1.5
        self.allow_min_order_cap_breach = True
        self.auto_convert_stable_for_quote = True
        self.stable_convert_allowlist: set[str] = set()
        self.stable_convert_denylist: set[str] = set()
        self._symbol_intel_cache: dict[str, Any] = {}
        self._symbol_intel_cache_utc = 0.0
        self.same_symbol_reentry_cooldown_sec = 90.0
        self.last_entry_symbol = ""
        self.last_entry_time_utc = ""
        self.deliberate_mode_enabled = True
        self.global_entries_window_sec = 3600.0
        self.global_entry_cooldown_sec = 75.0
        self.max_entries_per_hour = 6
        self.per_symbol_entry_cooldown_sec = 900.0
        self.per_symbol_entries_window_sec = 3600.0
        self.max_entries_per_symbol_window = 2
        self.max_consecutive_same_symbol_entries = 2
        self.same_symbol_streak_window_sec = 7200.0
        self.entry_timestamps_utc: list[datetime] = []
        self.symbol_entry_timestamps_utc: dict[str, list[datetime]] = {}
        self.entry_symbol_history: list[tuple[datetime, str]] = []

        self.profit_reinvestment_enabled = True
        self.order_notional_pct = 0.24
        self.max_deployable_capital_pct = 0.70
        self.max_drawdown_pct_limit = 10.0
        self.compounding_growth_sensitivity = 0.75
        self.compounding_boost_ceiling = 1.80
        self.compounding_min_notional_usd = 0.50
        self.compounding_max_notional_usd = 25000.0

        self.adaptive_gate_enabled = True
        self.adaptive_gate_starvation_sec = 45.0
        self.adaptive_gate_adjust_cooldown_sec = 20.0
        self.adaptive_gate_relax_step_score = 0.01
        self.adaptive_gate_relax_max_offset = 0.12
        self.adaptive_gate_recover_step_score = 0.005
        self.gate_relax_offset = 0.0
        self.last_gate_adjust_utc = ""
        self.configured_gate_min_composite_score = float(getattr(self.signal_gate, "min_composite_score", 0.60))

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

    @staticmethod
    def _parse_runtime_symbol_set(raw: Any) -> set[str]:
        rows: list[Any]
        if isinstance(raw, str):
            rows = [s.strip() for s in raw.split(",")]
        elif isinstance(raw, (list, tuple, set)):
            rows = list(raw)
        else:
            return set()

        out: set[str] = set()
        for row in rows:
            token = str(row or "").upper().strip()
            if not token:
                continue
            if "/" in token:
                token = token.split("/", 1)[0].strip()
            token = token.replace("-", "").replace("_", "").strip()
            if token:
                out.add(token)
        return out

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
        self.spot_short_enabled = bool(runtime.get("spot_short_enabled", self.spot_short_enabled))
        self.close_balance_buffer_fraction = self._clamp(
            self._to_float(
                runtime.get("close_balance_buffer_fraction", self.close_balance_buffer_fraction),
                self.close_balance_buffer_fraction,
            ),
            0.95,
            1.0,
        )
        self.spot_inventory_entry_fraction = self._clamp(
            self._to_float(
                runtime.get("spot_inventory_entry_fraction", self.spot_inventory_entry_fraction),
                self.spot_inventory_entry_fraction,
            ),
            0.05,
            1.0,
        )
        self.max_symbol_allocation_pct = self._clamp(
            self._to_float(
                runtime.get("max_symbol_allocation_pct", self.max_symbol_allocation_pct),
                self.max_symbol_allocation_pct,
            ),
            0.10,
            0.95,
        )
        self.auto_convert_collateral = bool(runtime.get("auto_convert_collateral", self.auto_convert_collateral))
        self.auto_convert_stable_for_quote = bool(
            runtime.get("auto_convert_stable_for_quote", self.auto_convert_stable_for_quote)
        )
        self.stable_convert_allowlist = self._parse_runtime_symbol_set(
            runtime.get("stable_convert_allowlist", [])
        )
        self.stable_convert_denylist = self._parse_runtime_symbol_set(
            runtime.get("stable_convert_denylist", [])
        )
        self.collateral_sell_fraction = self._clamp(
            self._to_float(
                runtime.get("collateral_sell_fraction", self.collateral_sell_fraction),
                self.collateral_sell_fraction,
            ),
            0.02,
            0.95,
        )
        self.collateral_convert_cooldown_sec = self._clamp(
            self._to_float(
                runtime.get("collateral_convert_cooldown_sec", self.collateral_convert_cooldown_sec),
                self.collateral_convert_cooldown_sec,
            ),
            0.0,
            86400.0,
        )
        self.min_collateral_convert_usd = self._clamp(
            self._to_float(
                runtime.get("min_collateral_convert_usd", self.min_collateral_convert_usd),
                self.min_collateral_convert_usd,
            ),
            0.5,
            100000.0,
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

        configured_gate_score = self._clamp(
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
        self.configured_gate_min_composite_score = float(configured_gate_score)
        self.signal_gate.min_composite_score = float(configured_gate_score)
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

        self.adaptive_gate_enabled = bool(runtime.get("adaptive_entry_gate_enabled", self.adaptive_gate_enabled))
        self.adaptive_gate_starvation_sec = self._clamp(
            self._to_float(
                runtime.get("adaptive_entry_gate_starvation_sec", self.adaptive_gate_starvation_sec),
                self.adaptive_gate_starvation_sec,
            ),
            5.0,
            3600.0,
        )
        self.adaptive_gate_adjust_cooldown_sec = self._clamp(
            self._to_float(
                runtime.get("adaptive_entry_gate_adjust_cooldown_sec", self.adaptive_gate_adjust_cooldown_sec),
                self.adaptive_gate_adjust_cooldown_sec,
            ),
            1.0,
            3600.0,
        )

        default_relax_score = max(
            self._to_float(runtime.get("adaptive_entry_gate_relax_step_bps", 1.0), 1.0) / 100.0,
            self.adaptive_gate_relax_step_score,
        )
        self.adaptive_gate_relax_step_score = self._clamp(
            self._to_float(runtime.get("adaptive_entry_gate_relax_step_score", default_relax_score), default_relax_score),
            0.001,
            0.05,
        )

        default_recover_score = max(
            self._to_float(runtime.get("adaptive_entry_gate_tighten_step_bps", 1.0), 1.0) / 200.0,
            self.adaptive_gate_recover_step_score,
        )
        self.adaptive_gate_recover_step_score = self._clamp(
            self._to_float(runtime.get("adaptive_entry_gate_recover_step_score", default_recover_score), default_recover_score),
            0.001,
            0.05,
        )

        self.adaptive_gate_relax_max_offset = self._clamp(
            self._to_float(
                runtime.get("adaptive_entry_gate_relax_max_offset", self.adaptive_gate_relax_max_offset),
                self.adaptive_gate_relax_max_offset,
            ),
            0.01,
            0.30,
        )

        if self.adaptive_gate_enabled and self.gate_relax_offset > 0.0:
            self.gate_relax_offset = self._clamp(
                self.gate_relax_offset,
                0.0,
                float(self.adaptive_gate_relax_max_offset),
            )
            self.signal_gate.min_composite_score = max(
                float(self.configured_gate_min_composite_score) - float(self.gate_relax_offset),
                0.35,
            )
        elif not self.adaptive_gate_enabled:
            self.gate_relax_offset = 0.0

        configured_fallback = max(self._to_float(runtime.get("fallback_buying_power_usd", 0.0), 0.0), 0.0)
        if self.degraded_buying_power_usd <= 0.0:
            self.degraded_buying_power_usd = configured_fallback
        else:
            # Never expand above configured ceiling from adaptive value.
            self.degraded_buying_power_usd = min(self.degraded_buying_power_usd, max(configured_fallback, 0.0))

        self.profit_reinvestment_enabled = bool(
            runtime.get("profit_reinvestment_enabled", self.profit_reinvestment_enabled)
        )
        self.order_notional_pct = self._clamp(
            self._to_float(runtime.get("order_notional_pct", self.order_notional_pct), self.order_notional_pct),
            0.02,
            0.95,
        )
        self.max_deployable_capital_pct = self._clamp(
            self._to_float(
                runtime.get("max_deployable_capital_pct", self.max_deployable_capital_pct),
                self.max_deployable_capital_pct,
            ),
            0.05,
            0.99,
        )
        self.max_drawdown_pct_limit = self._clamp(
            self._to_float(runtime.get("max_drawdown_pct", self.max_drawdown_pct_limit), self.max_drawdown_pct_limit),
            1.0,
            95.0,
        )
        self.compounding_growth_sensitivity = self._clamp(
            self._to_float(
                runtime.get("compounding_growth_sensitivity", self.compounding_growth_sensitivity),
                self.compounding_growth_sensitivity,
            ),
            0.0,
            3.0,
        )
        self.compounding_boost_ceiling = self._clamp(
            self._to_float(
                runtime.get("pyramid_reinvestment_multiplier", self.compounding_boost_ceiling),
                self.compounding_boost_ceiling,
            ),
            0.75,
            3.0,
        )
        self.compounding_min_notional_usd = self._clamp(
            self._to_float(
                runtime.get("compounding_min_notional_usd", self.compounding_min_notional_usd),
                self.compounding_min_notional_usd,
            ),
            0.0,
            1000.0,
        )
        self.compounding_max_notional_usd = self._clamp(
            self._to_float(
                runtime.get("compounding_max_notional_usd", self.compounding_max_notional_usd),
                self.compounding_max_notional_usd,
            ),
            1.0,
            1_000_000.0,
        )

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

        configured_risk_fraction = self._clamp(
            self._to_float(runtime.get("base_risk_fraction", self.sizing_engine.max_risk_pct), self.sizing_engine.max_risk_pct),
            0.0005,
            0.03,
        )
        configured_risk_floor = self._clamp(
            self._to_float(
                runtime.get("max_risk_fraction_floor", self.sizing_engine.max_risk_pct_floor),
                self.sizing_engine.max_risk_pct_floor,
            ),
            0.0001,
            configured_risk_fraction,
        )
        configured_risk_ceiling = self._clamp(
            self._to_float(
                runtime.get("max_risk_fraction_ceiling", self.sizing_engine.max_risk_pct_ceiling),
                self.sizing_engine.max_risk_pct_ceiling,
            ),
            configured_risk_fraction,
            0.05,
        )
        self.sizing_engine.max_risk_pct = float(configured_risk_fraction)
        self.sizing_engine.max_risk_pct_floor = float(configured_risk_floor)
        self.sizing_engine.max_risk_pct_ceiling = float(configured_risk_ceiling)
        self.sizing_engine.max_heat = float(self.risk_kernel.max_heat)

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
                256.0,
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
        self.allow_best_multi_preference = bool(
            runtime.get("allow_best_multi_preference", self.allow_best_multi_preference)
        )
        self.symbol_intel_enabled = bool(runtime.get("symbol_intel_enabled", self.symbol_intel_enabled))
        self.symbol_intel_prefer_top_n = int(
            self._clamp(
                self._to_float(
                    runtime.get("symbol_intel_prefer_top_n", self.symbol_intel_prefer_top_n),
                    self.symbol_intel_prefer_top_n,
                ),
                1.0,
                40.0,
            )
        )
        self.symbol_intel_max_age_sec = self._clamp(
            self._to_float(runtime.get("symbol_intel_max_age_sec", self.symbol_intel_max_age_sec), self.symbol_intel_max_age_sec),
            30.0,
            86400.0,
        )
        self.symbol_intel_min_alpha_score = self._clamp(
            self._to_float(
                runtime.get("symbol_intel_min_alpha_score", self.symbol_intel_min_alpha_score),
                self.symbol_intel_min_alpha_score,
            ),
            0.0,
            200.0,
        )
        self.allow_min_order_cap_breach = bool(
            runtime.get("allow_min_order_cap_breach", self.allow_min_order_cap_breach)
        )
        self.same_symbol_reentry_cooldown_sec = self._clamp(
            self._to_float(
                runtime.get("same_symbol_reentry_cooldown_sec", self.same_symbol_reentry_cooldown_sec),
                self.same_symbol_reentry_cooldown_sec,
            ),
            0.0,
            3600.0,
        )
        self.deliberate_mode_enabled = bool(runtime.get("deliberate_mode_enabled", self.deliberate_mode_enabled))
        self.global_entries_window_sec = self._clamp(
            self._to_float(
                runtime.get("global_entries_window_sec", self.global_entries_window_sec),
                self.global_entries_window_sec,
            ),
            60.0,
            86400.0,
        )
        self.global_entry_cooldown_sec = self._clamp(
            self._to_float(
                runtime.get("global_entry_cooldown_sec", self.global_entry_cooldown_sec),
                self.global_entry_cooldown_sec,
            ),
            0.0,
            3600.0,
        )
        self.max_entries_per_hour = int(
            self._clamp(
                self._to_float(runtime.get("max_entries_per_hour", self.max_entries_per_hour), self.max_entries_per_hour),
                1.0,
                240.0,
            )
        )
        self.per_symbol_entry_cooldown_sec = self._clamp(
            self._to_float(
                runtime.get("per_symbol_entry_cooldown_sec", self.per_symbol_entry_cooldown_sec),
                self.per_symbol_entry_cooldown_sec,
            ),
            0.0,
            7200.0,
        )
        self.per_symbol_entries_window_sec = self._clamp(
            self._to_float(
                runtime.get("per_symbol_entries_window_sec", self.per_symbol_entries_window_sec),
                self.per_symbol_entries_window_sec,
            ),
            60.0,
            86400.0,
        )
        self.max_entries_per_symbol_window = int(
            self._clamp(
                self._to_float(
                    runtime.get("max_entries_per_symbol_window", self.max_entries_per_symbol_window),
                    self.max_entries_per_symbol_window,
                ),
                1.0,
                50.0,
            )
        )
        self.max_consecutive_same_symbol_entries = int(
            self._clamp(
                self._to_float(
                    runtime.get("max_consecutive_same_symbol_entries", self.max_consecutive_same_symbol_entries),
                    self.max_consecutive_same_symbol_entries,
                ),
                1.0,
                20.0,
            )
        )
        self.same_symbol_streak_window_sec = self._clamp(
            self._to_float(
                runtime.get("same_symbol_streak_window_sec", self.same_symbol_streak_window_sec),
                self.same_symbol_streak_window_sec,
            ),
            60.0,
            86400.0,
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
        self.low_balance_ticker_scan_cap = int(
            self._clamp(
                self._to_float(
                    runtime.get("low_balance_ticker_scan_cap", self.low_balance_ticker_scan_cap),
                    self.low_balance_ticker_scan_cap,
                ),
                8.0,
                400.0,
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

    def _load_symbol_flip_intel_payload(self) -> dict[str, Any]:
        now_ts = time.time()
        if self._symbol_intel_cache and (now_ts - self._symbol_intel_cache_utc) <= 5.0:
            return dict(self._symbol_intel_cache)

        payload = load_json(SYMBOL_FLIP_INTEL_FILE, {})
        if not isinstance(payload, dict):
            payload = {}

        self._symbol_intel_cache = dict(payload)
        self._symbol_intel_cache_utc = now_ts
        return dict(payload)

    def _symbol_flip_intel_candidates(self) -> tuple[list[str], dict[str, Any]]:
        meta: dict[str, Any] = {
            "symbol_intel_enabled": bool(self.symbol_intel_enabled),
            "symbol_intel_file_exists": bool(SYMBOL_FLIP_INTEL_FILE.exists()),
            "symbol_intel_stale": False,
            "symbol_intel_age_sec": None,
            "symbol_intel_candidate_count": 0,
            "symbol_intel_selected_count": 0,
            "symbol_intel_executable_count": 0,
            "symbol_intel_source": "none",
        }

        if not self.symbol_intel_enabled:
            meta["symbol_intel_source"] = "disabled"
            return [], meta

        payload = self._load_symbol_flip_intel_payload()
        if not payload:
            meta["symbol_intel_source"] = "empty"
            return [], meta

        generated_utc = str(payload.get("generated_utc", "") or "")
        age_sec = float("inf")
        if generated_utc:
            try:
                generated_dt = self._parse_iso_utc(generated_utc)
                age_sec = max((datetime.now(timezone.utc) - generated_dt).total_seconds(), 0.0)
            except Exception:
                age_sec = float("inf")

        if math.isfinite(age_sec):
            meta["symbol_intel_age_sec"] = round(float(age_sec), 3)

        if math.isfinite(age_sec) and age_sec > float(self.symbol_intel_max_age_sec):
            meta["symbol_intel_stale"] = True
            meta["symbol_intel_source"] = "stale"
            return [], meta

        picks: list[str] = []

        long_candidates = payload.get("long_candidates", []) if isinstance(payload, dict) else []
        if isinstance(long_candidates, list):
            ranked = sorted(
                [row for row in long_candidates if isinstance(row, dict)],
                key=lambda row: self._to_float(row.get("alpha_long_score", 0.0), 0.0),
                reverse=True,
            )
            for row in ranked:
                score = self._to_float(row.get("alpha_long_score", 0.0), 0.0)
                if score < float(self.symbol_intel_min_alpha_score):
                    continue
                symbol = str(row.get("symbol", "") or "").upper().strip()
                if symbol:
                    picks.append(symbol)

        focus_symbols = payload.get("focus_symbols", []) if isinstance(payload, dict) else []
        if isinstance(focus_symbols, list):
            for row in focus_symbols:
                symbol = str(row or "").upper().strip()
                if symbol:
                    picks.append(symbol)

        deduped = list(dict.fromkeys(picks))
        limited = deduped[: max(int(self.symbol_intel_prefer_top_n), 1)]

        meta["symbol_intel_candidate_count"] = int(len(deduped))
        meta["symbol_intel_selected_count"] = int(len(limited))
        meta["symbol_intel_executable_count"] = int(len(limited))
        meta["symbol_intel_source"] = "symbol_flip_intel_top5"
        return limited, meta

    def _filter_symbols_by_executable_notional(
        self,
        symbols: list[str],
        affordable_usd_hint: float,
        max_notional_usd_cap: float,
    ) -> tuple[list[str], dict[str, Any]]:
        deduped = list(dict.fromkeys(str(s or "").upper().strip() for s in (symbols or []) if str(s or "").strip()))
        meta: dict[str, Any] = {
            "input_count": int(len(deduped)),
            "evaluated_count": 0,
            "executable_count": 0,
            "rejected_missing_config": 0,
            "rejected_unpriced": 0,
            "rejected_affordable": 0,
            "rejected_cap": 0,
            "limits_applied": False,
        }
        if not deduped:
            return [], meta

        affordable_limit = max(self._to_float(affordable_usd_hint, 0.0), 0.0)
        cap_limit = max(self._to_float(max_notional_usd_cap, 0.0), 0.0)

        if affordable_limit <= 0.0 and cap_limit <= 0.0:
            meta["executable_count"] = int(len(deduped))
            return deduped, meta

        meta["limits_applied"] = True
        filtered: list[str] = []

        for symbol in deduped:
            cfg = self.router.get_symbol_config(symbol) or {}
            static_min_order = self._to_float(cfg.get("min_order", 0.0), 0.0)
            min_order_qty = self._effective_min_order(symbol, static_min_order)
            if min_order_qty <= 0.0:
                meta["rejected_missing_config"] = int(meta["rejected_missing_config"]) + 1
                continue

            ticker = self.router.get_ticker(symbol)
            if not isinstance(ticker, dict):
                meta["rejected_unpriced"] = int(meta["rejected_unpriced"]) + 1
                continue
            last_px = max(self._to_float(ticker.get("last", 0.0), 0.0), 0.0)
            if last_px <= 0.0:
                meta["rejected_unpriced"] = int(meta["rejected_unpriced"]) + 1
                continue

            meta["evaluated_count"] = int(meta["evaluated_count"]) + 1
            min_notional = max(min_order_qty, 0.0) * float(last_px)

            if cap_limit > 0.0 and min_notional > cap_limit:
                meta["rejected_cap"] = int(meta["rejected_cap"]) + 1
                continue
            if affordable_limit > 0.0 and min_notional > affordable_limit:
                meta["rejected_affordable"] = int(meta["rejected_affordable"]) + 1
                continue

            filtered.append(symbol)

        meta["executable_count"] = int(len(filtered))
        return filtered, meta

    def _append_collateral_convert_log(self, now: datetime, context: str, payload: dict[str, Any]) -> None:
        try:
            row = {
                "timestamp_utc": now.isoformat(),
                "context": str(context or "unknown"),
                "payload": payload if isinstance(payload, dict) else {"value": payload},
            }
            with open(COLLATERAL_CONVERT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=True) + "\n")
        except Exception:
            pass

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
            "universe_sample_strategy": "random",
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
        low_balance_mode = bool(
            affordable_usd_hint > 0.0 and affordable_usd_hint <= float(self.low_balance_sample_trigger_usd)
        )
        if low_balance_mode and len(unique) > sample_size:
            sample_size = min(max(sample_size, int(self.low_balance_sample_size)), len(unique))
            meta["universe_sample_escalated"] = True

        if low_balance_mode:
            ranked = sorted(
                unique,
                key=lambda s: self._effective_min_order(
                    s,
                    self._to_float((self.router.get_symbol_config(s) or {}).get("min_order", 1e9), 1e9),
                ),
            )
            ticker_scan_cap = min(max(int(self.low_balance_ticker_scan_cap), 1), len(ranked))
            if affordable_usd_hint > 0.0 and affordable_usd_hint <= 2.0 and len(ranked) > ticker_scan_cap:
                # Rank the full universe by minimum order, but cap ticker lookups to avoid scan stalls.
                sample_size = max(sample_size, ticker_scan_cap)
                meta["universe_sample_escalated"] = True
                meta["universe_sample_strategy"] = "low_balance_ranked_scan"
            sampled = ranked[: min(sample_size, ticker_scan_cap)]
            if meta["universe_sample_strategy"] != "low_balance_ranked_scan":
                meta["universe_sample_strategy"] = "low_balance_min_order"
        else:
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
            min_order_qty = self._effective_min_order(
                symbol,
                self._to_float(cfg.get("min_order", 0.0), 0.0),
            )
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

    def _adaptive_gate_adjust_cooldown_active(self, now: datetime) -> bool:
        if float(self.adaptive_gate_adjust_cooldown_sec) <= 0.0:
            return False
        raw = str(self.last_gate_adjust_utc or "").strip()
        if not raw:
            return False
        try:
            last = self._parse_iso_utc(raw)
        except Exception:
            return False
        return (now - last).total_seconds() < float(self.adaptive_gate_adjust_cooldown_sec)

    def _maybe_relax_gate_threshold(self, now: datetime) -> bool:
        if not self.adaptive_gate_enabled:
            return False
        if self._adaptive_gate_adjust_cooldown_active(now):
            return False

        starvation_sec = float(self.gate_not_armed_streak) * max(float(self.loop_seconds), 1.0)
        if starvation_sec < float(self.adaptive_gate_starvation_sec):
            return False

        old_offset = float(self.gate_relax_offset)
        new_offset = self._clamp(
            old_offset + float(self.adaptive_gate_relax_step_score),
            0.0,
            float(self.adaptive_gate_relax_max_offset),
        )
        if new_offset <= old_offset:
            return False

        self.gate_relax_offset = float(new_offset)
        self.last_gate_adjust_utc = now.isoformat()
        self.signal_gate.min_composite_score = max(
            float(self.configured_gate_min_composite_score) - float(self.gate_relax_offset),
            0.35,
        )
        return True

    def _recover_gate_threshold_after_fill(self, now: datetime) -> bool:
        if not self.adaptive_gate_enabled:
            return False
        if float(self.gate_relax_offset) <= 0.0:
            return False
        if self._adaptive_gate_adjust_cooldown_active(now):
            return False

        old_offset = float(self.gate_relax_offset)
        new_offset = max(old_offset - float(self.adaptive_gate_recover_step_score), 0.0)
        if new_offset >= old_offset:
            return False

        self.gate_relax_offset = float(new_offset)
        self.last_gate_adjust_utc = now.isoformat()
        self.signal_gate.min_composite_score = max(
            float(self.configured_gate_min_composite_score) - float(self.gate_relax_offset),
            0.35,
        )
        return True

    def _compute_compounding_notional_cap(
        self,
        available_usd: float,
        gate_score: float,
        drawdown_pct: float,
        window_fail_rate: float,
        static_cap_usd: float,
    ) -> tuple[float, dict[str, Any]]:
        bankroll = max(float(available_usd), 0.0)
        deployable = max(bankroll * float(self.max_deployable_capital_pct), 0.0)
        pct_target = max(deployable * float(self.order_notional_pct), 0.0)

        static_cap = max(float(static_cap_usd), 0.0)
        if static_cap > 0.0 and pct_target > 0.0:
            base_cap = min(static_cap, pct_target)
        elif static_cap > 0.0:
            base_cap = static_cap
        else:
            base_cap = pct_target

        dd_limit = max(float(self.max_drawdown_pct_limit) / 100.0, 0.01)
        dd_ratio = self._clamp(float(drawdown_pct) / dd_limit, 0.0, 3.0)
        drawdown_throttle = self._clamp(1.0 - (0.65 * dd_ratio), 0.20, 1.00)
        fail_throttle = self._clamp(1.0 - (0.75 * float(window_fail_rate)), 0.30, 1.00)

        initial_capital = max(float(getattr(self.portfolio, "initial_capital", 0.0) or 0.0), 1e-9)
        growth_ratio = bankroll / initial_capital
        growth_boost = 1.0 + max(growth_ratio - 1.0, 0.0) * float(self.compounding_growth_sensitivity)
        quality_boost = self._clamp(0.85 + ((float(gate_score) - 0.50) * 0.90), 0.60, 1.25)

        multiplier = 1.0
        if self.profit_reinvestment_enabled:
            multiplier = growth_boost * quality_boost * drawdown_throttle * fail_throttle
            multiplier = self._clamp(multiplier, 0.25, float(self.compounding_boost_ceiling))

        cap = max(base_cap * multiplier, 0.0)
        if deployable > 0.0:
            cap = min(cap, deployable)
        if static_cap > 0.0:
            cap = min(cap, static_cap)

        cap = min(cap, float(self.compounding_max_notional_usd))
        if cap > 0.0 and bankroll > 0.0:
            min_floor = min(float(self.compounding_min_notional_usd), bankroll)
            cap = max(cap, min_floor)

        meta = {
            "compounding_enabled": bool(self.profit_reinvestment_enabled),
            "compounding_multiplier": round(float(multiplier), 6),
            "compounding_base_cap_usd": round(float(base_cap), 6),
            "compounding_notional_cap_usd": round(float(cap), 6),
            "compounding_deployable_capital_usd": round(float(deployable), 6),
            "compounding_bankroll_growth_ratio": round(float(growth_ratio), 6),
            "compounding_drawdown_throttle": round(float(drawdown_throttle), 6),
            "compounding_fail_throttle": round(float(fail_throttle), 6),
            "compounding_quality_boost": round(float(quality_boost), 6),
        }
        return float(cap), meta

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

    def _resolve_close_qty_for_spot(self, symbol: str, requested_qty: float, close_side: str) -> tuple[float, float, str]:
        desired = max(float(requested_qty), 0.0)
        if close_side != "sell":
            return desired, desired, ""

        available_qty = max(float(self.router.get_asset_balance(symbol, force_refresh=False) or 0.0), 0.0)
        safe_available = max(available_qty * float(self.close_balance_buffer_fraction), 0.0)
        close_qty = min(desired, safe_available)
        balance_error = str(getattr(self.router.kraken, "last_balance_error", "") or "")
        return float(close_qty), float(available_qty), balance_error

    def _normalize_balance_symbol(self, asset_code: str) -> str:
        normalizer = getattr(self.router.kraken, "_normalize_balance_asset", None)
        if callable(normalizer):
            try:
                normalized = str(normalizer(asset_code) or "").upper().strip()
                if normalized:
                    return normalized
            except Exception:
                pass

        raw = str(asset_code or "").upper().strip()
        if not raw:
            return ""
        token = raw.split(".", 1)[0].strip()
        fallback_alias = {
            "ZUSD": "USD",
            "XBT": "BTC",
            "XXBT": "BTC",
            "XETH": "ETH",
            "XXRP": "XRP",
            "XDG": "DOGE",
            "XXDG": "DOGE",
        }
        return fallback_alias.get(token, token)

    def _build_balance_valuation(self, force_refresh: bool = False) -> dict[str, Any]:
        balances = self.router.get_balance_snapshot(force_refresh=force_refresh)
        if not isinstance(balances, dict):
            balances = {}

        usd_cash = 0.0
        stable_cash_usd = 0.0
        holdings_value_usd = 0.0
        unresolved_assets: list[str] = []
        holdings: list[dict[str, Any]] = []
        symbol_values_usd: dict[str, float] = {}

        for asset_code, raw_qty in balances.items():
            qty = max(self._to_float(raw_qty, 0.0), 0.0)
            if qty <= 0.0:
                continue

            symbol = self._normalize_balance_symbol(asset_code)
            if not symbol:
                continue

            if symbol == "USD":
                usd_cash += float(qty)
                continue

            is_stable = symbol in self.stable_assets
            last_px = 1.0 if is_stable else 0.0
            if not is_stable:
                ticker = self.router.get_ticker(symbol)
                if isinstance(ticker, dict):
                    last_px = max(self._to_float(ticker.get("last", 0.0), 0.0), 0.0)

            value_usd = float(qty) * float(last_px)
            if is_stable:
                stable_cash_usd += float(value_usd)
            else:
                holdings_value_usd += float(value_usd)

            symbol_values_usd[symbol] = float(symbol_values_usd.get(symbol, 0.0) + value_usd)
            holdings.append(
                {
                    "asset_code": str(asset_code),
                    "symbol": symbol,
                    "qty": float(qty),
                    "last": float(last_px),
                    "value_usd": float(value_usd),
                    "is_stable": bool(is_stable),
                }
            )

            if (not is_stable) and value_usd <= 0.0:
                unresolved_assets.append(symbol)

        holdings.sort(key=lambda row: float(row.get("value_usd", 0.0) or 0.0), reverse=True)

        cash_usd = float(max(usd_cash + stable_cash_usd, 0.0))
        total_equity_usd = float(max(cash_usd + holdings_value_usd, cash_usd, 0.0))
        largest_symbol = ""
        largest_weight_pct = 0.0
        if holdings and total_equity_usd > 0.0:
            largest_symbol = str(holdings[0].get("symbol", "") or "")
            largest_weight_pct = (float(holdings[0].get("value_usd", 0.0) or 0.0) / total_equity_usd) * 100.0

        return {
            "balances": balances,
            "cash_usd": float(cash_usd),
            "usd_cash_balance": float(max(usd_cash, 0.0)),
            "stable_cash_equivalent_usd": float(max(stable_cash_usd, 0.0)),
            "holdings_value_usd": float(max(holdings_value_usd, 0.0)),
            "total_equity_usd": float(total_equity_usd),
            "symbol_values_usd": symbol_values_usd,
            "holdings": holdings,
            "largest_symbol": largest_symbol,
            "largest_weight_pct": float(max(largest_weight_pct, 0.0)),
            "unresolved_assets": sorted(set(unresolved_assets)),
        }

    def _stable_asset_convertible(self, symbol: str) -> bool:
        token = str(symbol or "").upper().strip()
        if not token:
            return False
        if self.stable_convert_allowlist and token not in self.stable_convert_allowlist:
            return False
        if token in self.stable_convert_denylist:
            return False
        return True

    def _collateral_convert_cooldown_active(self, now: datetime) -> bool:
        if float(self.collateral_convert_cooldown_sec) <= 0.0:
            return False
        raw = str(self.last_collateral_convert_utc or "").strip()
        if not raw:
            return False
        try:
            last = self._parse_iso_utc(raw)
        except Exception:
            return False
        return (now - last).total_seconds() < float(self.collateral_convert_cooldown_sec)

    def _attempt_collateral_convert_for_liquidity(
        self,
        now: datetime,
        reason: str,
        required_usd: float = 0.0,
        preferred_symbol: str = "",
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "attempted": True,
            "executed": False,
            "reason": "none",
        }

        def _finalize(payload: dict[str, Any]) -> dict[str, Any]:
            self._append_collateral_convert_log(now, str(reason or "liquidity"), payload)
            return payload

        if not self.auto_convert_collateral:
            result["reason"] = "disabled"
            return _finalize(result)

        if self._collateral_convert_cooldown_active(now):
            result["reason"] = "cooldown_active"
            result["cooldown_sec"] = round(float(self.collateral_convert_cooldown_sec), 3)
            return _finalize(result)

        valuation = self._build_balance_valuation(force_refresh=False)
        quote_usd_balance = max(
            self._to_float(
                valuation.get("usd_cash_balance", valuation.get("cash_usd", 0.0)),
                0.0,
            ),
            0.0,
        )
        required_usd_hint = max(self._to_float(required_usd, 0.0), 0.0)
        allow_stable_conversion = bool(
            self.auto_convert_stable_for_quote
            and required_usd_hint > 0.0
            and quote_usd_balance + 1e-9 < required_usd_hint
        )
        total_equity_usd = max(self._to_float(valuation.get("total_equity_usd", 0.0), 0.0), 0.0)
        holdings = valuation.get("holdings", [])
        if not isinstance(holdings, list) or not holdings:
            result["reason"] = "no_holdings"
            return _finalize(result)

        preferred = str(preferred_symbol or "").upper().strip()
        candidates: list[dict[str, Any]] = []
        for row in holdings:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol", "") or "").upper().strip()
            if not symbol or symbol == "USD":
                continue
            is_stable = bool(row.get("is_stable", False))
            if is_stable:
                if not allow_stable_conversion:
                    continue
                if not self._stable_asset_convertible(symbol):
                    continue
            qty = max(self._to_float(row.get("qty", 0.0), 0.0), 0.0)
            last_px = max(self._to_float(row.get("last", 0.0), 0.0), 0.0)
            value_usd = max(self._to_float(row.get("value_usd", 0.0), 0.0), 0.0)
            if qty <= 0.0 or last_px <= 0.0 or value_usd < float(self.min_collateral_convert_usd):
                continue

            cfg = self.router.get_symbol_config(symbol) or {}
            static_min_order = self._to_float(cfg.get("min_order", 0.0), 0.0)
            min_order = self._effective_min_order(symbol, static_min_order)
            if min_order <= 0.0:
                continue
            safe_available_qty = max(qty * float(self.close_balance_buffer_fraction), 0.0)
            if safe_available_qty < min_order:
                continue

            weight_pct = ((value_usd / max(total_equity_usd, 1e-9)) * 100.0) if total_equity_usd > 0.0 else 0.0
            overweight_bonus = max(weight_pct - (float(self.max_symbol_allocation_pct) * 100.0), 0.0)
            score = value_usd + (overweight_bonus * value_usd * 0.02)
            if is_stable and allow_stable_conversion:
                score = score * 1.75
            if preferred and symbol == preferred:
                score *= 0.55

            candidates.append(
                {
                    "symbol": symbol,
                    "is_stable": bool(is_stable),
                    "qty": float(qty),
                    "last": float(last_px),
                    "value_usd": float(value_usd),
                    "weight_pct": float(weight_pct),
                    "min_order": float(min_order),
                    "safe_available_qty": float(safe_available_qty),
                    "score": float(score),
                }
            )

        if not candidates:
            result["reason"] = "no_convertible_collateral"
            return _finalize(result)

        if allow_stable_conversion:
            stable_candidates = [row for row in candidates if bool(row.get("is_stable", False))]
            if stable_candidates:
                candidates = stable_candidates

        candidates.sort(key=lambda row: float(row.get("score", 0.0) or 0.0), reverse=True)
        chosen = candidates[0]
        symbol = str(chosen.get("symbol", "") or "").upper().strip()
        last_px = max(self._to_float(chosen.get("last", 0.0), 0.0), 0.0)
        min_order = max(self._to_float(chosen.get("min_order", 0.0), 0.0), 0.0)
        safe_available_qty = max(self._to_float(chosen.get("safe_available_qty", 0.0), 0.0), 0.0)
        if not symbol or last_px <= 0.0 or min_order <= 0.0 or safe_available_qty < min_order:
            result["reason"] = "invalid_candidate"
            return _finalize(result)

        required_usd_effective = max(self._to_float(required_usd, 0.0), self.min_collateral_convert_usd)
        qty_from_required = required_usd_effective / max(last_px, 1e-9)
        qty_from_fraction = max(self._to_float(chosen.get("qty", 0.0), 0.0) * float(self.collateral_sell_fraction), 0.0)
        qty = max(min_order, qty_from_required, qty_from_fraction)
        qty = min(qty, safe_available_qty)
        if qty < min_order:
            result["reason"] = "qty_below_min_order"
            result["symbol"] = symbol
            result["qty"] = round(float(qty), 10)
            result["min_order"] = round(float(min_order), 10)
            return _finalize(result)

        order_result = self.router.place_order(symbol, "sell", float(qty), None)
        if "error" in order_result:
            result["reason"] = "order_failed"
            result["symbol"] = symbol
            result["error"] = str(order_result.get("error"))
            return _finalize(result)

        txid = order_result.get("txid", ["unknown"])
        txid = txid[0] if isinstance(txid, list) else str(txid)
        cfg = self.router.get_symbol_config(symbol) or {}
        pair = str(cfg.get("pair") or "")
        size_usd = float(qty) * float(last_px)

        self.trade_ledger.append(
            {
                "timestamp": now.isoformat(),
                "txid": txid,
                "symbol": symbol,
                "pair": pair,
                "direction": "flat",
                "side": "sell",
                "status": "COLLATERAL_CONVERT_SELL",
                "execution_mode": "collateral_convert",
                "entry_price": round(float(last_px), 6),
                "qty": round(float(qty), 10),
                "size_usd": round(float(size_usd), 6),
                "convert_reason": str(reason or "liquidity"),
            }
        )
        self.audit_chain.append(
            "collateral_convert_sell",
            {
                "symbol": symbol,
                "side": "sell",
                "qty": round(float(qty), 10),
                "size_usd": round(float(size_usd), 6),
                "txid": txid,
                "convert_reason": str(reason or "liquidity"),
                "weight_pct": round(float(chosen.get("weight_pct", 0.0) or 0.0), 6),
            },
        )

        self.last_collateral_convert_utc = now.isoformat()
        result.update(
            {
                "executed": True,
                "reason": "collateral_converted",
                "symbol": symbol,
                "is_stable": bool(chosen.get("is_stable", False)),
                "txid": txid,
                "side": "sell",
                "qty": round(float(qty), 10),
                "size_usd": round(float(size_usd), 6),
                "weight_pct": round(float(chosen.get("weight_pct", 0.0) or 0.0), 6),
                "required_usd": round(float(required_usd_effective), 6),
                "quote_usd_before": round(float(quote_usd_balance), 6),
            }
        )
        return _finalize(result)

    def _reconcile_zero_inventory_positions(self, symbol: str, last: float, now: datetime) -> int:
        available_qty = max(float(self.router.get_asset_balance(symbol, force_refresh=False) or 0.0), 0.0)
        if available_qty > 0.0:
            return 0

        open_positions = self.portfolio.get_open_positions()
        symbol_positions = [
            p for p in open_positions
            if str(p.symbol).upper().startswith(f"{symbol.upper()}/") and str(p.side).lower() == "long"
        ]
        if not symbol_positions:
            return 0

        reconciled = 0
        for pos in symbol_positions:
            self.portfolio.close_position(pos.symbol, float(last), now.isoformat())
            reconciled += 1

        self.audit_chain.append(
            "positions_reconciled_zero_inventory",
            {
                "symbol": symbol,
                "reconciled_count": int(reconciled),
                "available_asset_qty": 0.0,
            },
        )
        _write_live_heartbeat(
            {
                "status": "degraded",
                "reason": "reconciled_zero_inventory_positions",
                "symbol": symbol,
                "reconciled_count": int(reconciled),
                "available_asset_qty": 0.0,
            }
        )
        return int(reconciled)

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
        requested_close_qty = float(pos.qty)
        close_qty = float(requested_close_qty)
        available_close_qty = float(requested_close_qty)
        close_balance_error = ""

        if close_side == "sell":
            close_qty, available_close_qty, close_balance_error = self._resolve_close_qty_for_spot(
                str(best["base_symbol"]),
                requested_close_qty,
                close_side,
            )
            if close_qty <= 0.0:
                if available_close_qty <= 0.0 and not close_balance_error:
                    # Reconcile stale in-memory position when exchange inventory is already flat.
                    self.portfolio.close_position(str(pos.symbol), float(best["last"]), now.isoformat())
                    self.audit_chain.append(
                        "position_reconciled_no_inventory",
                        {
                            "symbol": str(best["base_symbol"]),
                            "requested_qty": round(float(requested_close_qty), 10),
                            "available_qty": 0.0,
                            "reason": "no_exchange_inventory",
                        },
                    )
                    result.update(
                        {
                            "executed": False,
                            "reason": "position_reconciled_no_inventory",
                            "symbol": str(best["base_symbol"]),
                            "requested_qty": round(float(requested_close_qty), 10),
                            "available_qty": 0.0,
                        }
                    )
                    return result

                result.update(
                    {
                        "reason": "no_available_balance_to_close",
                        "symbol": str(best["base_symbol"]),
                        "requested_qty": round(float(requested_close_qty), 10),
                        "available_qty": round(float(available_close_qty), 10),
                        "balance_error": close_balance_error,
                    }
                )
                return result

        order_result = self.router.place_order(str(best["base_symbol"]), close_side, close_qty, None)

        if "error" in order_result:
            result["reason"] = "order_failed"
            result["symbol"] = str(best["base_symbol"])
            result["error"] = str(order_result.get("error"))
            result["requested_qty"] = round(float(requested_close_qty), 10)
            result["available_qty"] = round(float(available_close_qty), 10)
            if close_balance_error:
                result["balance_error"] = close_balance_error
            return result

        txid = order_result.get("txid", ["unknown"])
        txid = txid[0] if isinstance(txid, list) else str(txid)

        if close_qty < requested_close_qty:
            pos.qty = float(close_qty)
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
            requested_close_qty = float(pos.qty)
            close_qty = float(requested_close_qty)
            available_close_qty = float(requested_close_qty)
            close_balance_error = ""

            if close_side == "sell":
                close_qty, available_close_qty, close_balance_error = self._resolve_close_qty_for_spot(
                    symbol,
                    requested_close_qty,
                    close_side,
                )
                if close_qty <= 0.0:
                    if available_close_qty <= 0.0 and not close_balance_error:
                        # Inventory already flat on exchange; reconcile stale local OPEN position.
                        self.portfolio.close_position(pos.symbol, float(last), now.isoformat())
                        self.audit_chain.append(
                            "position_reconciled_no_inventory",
                            {
                                "symbol": symbol,
                                "requested_qty": round(float(requested_close_qty), 10),
                                "available_qty": 0.0,
                                "reason": "no_exchange_inventory",
                            },
                        )
                        _write_live_heartbeat(
                            {
                                "status": "degraded",
                                "reason": "position_reconciled_no_inventory",
                                "symbol": symbol,
                                "requested_qty": round(float(requested_close_qty), 10),
                                "available_qty": 0.0,
                            }
                        )
                        print("  reconciled stale position: no exchange inventory")
                        return True

                    _write_live_heartbeat(
                        {
                            "status": "blocked",
                            "reason": "close_balance_unavailable",
                            "symbol": symbol,
                            "side": close_side,
                            "requested_qty": float(requested_close_qty),
                            "available_qty": float(available_close_qty),
                            "balance_error": close_balance_error,
                        }
                    )
                    continue

            result = self.router.place_order(symbol, close_side, float(close_qty), None)
            if "error" in result and close_side == "sell" and "Insufficient funds" in str(result.get("error")):
                retry_qty, retry_available_qty, retry_balance_error = self._resolve_close_qty_for_spot(
                    symbol,
                    close_qty,
                    close_side,
                )
                if retry_qty > 0.0 and retry_qty < close_qty:
                    close_qty = float(retry_qty)
                    available_close_qty = float(retry_available_qty)
                    close_balance_error = str(retry_balance_error)
                    result = self.router.place_order(symbol, close_side, float(close_qty), None)

            if "error" in result:
                _write_live_heartbeat(
                    {
                        "status": "error",
                        "reason": "close_order_failed",
                        "symbol": symbol,
                        "side": close_side,
                        "qty": float(close_qty),
                        "requested_qty": float(requested_close_qty),
                        "available_qty": float(available_close_qty),
                        "balance_error": close_balance_error,
                        "error": str(result.get("error")),
                    }
                )
                continue

            txid = result.get("txid", ["unknown"])
            txid = txid[0] if isinstance(txid, list) else str(txid)

            if close_qty < requested_close_qty:
                pos.qty = float(close_qty)
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
                    "qty": round(float(close_qty), 10),
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
                    "qty": round(float(close_qty), 10),
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
                    "qty": round(float(close_qty), 10),
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
            gate_relaxed = self._maybe_relax_gate_threshold(now)
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
                    "adaptive_gate_enabled": bool(self.adaptive_gate_enabled),
                    "adaptive_gate_relaxed": bool(gate_relaxed),
                    "adaptive_gate_relax_offset": round(float(self.gate_relax_offset), 6),
                    "adaptive_gate_configured_min": round(float(self.configured_gate_min_composite_score), 6),
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

        reconciled_count = self._reconcile_zero_inventory_positions(symbol, float(last), now)
        if reconciled_count > 0:
            print(f"  reconciled stale positions: {reconciled_count}")

        if self._maybe_close_positions(symbol, float(last), now):
            return

        if decision_direction == "short" and (not self.spot_short_enabled):
            live_usd = max(float(self.router.get_balance(force_refresh=False) or 0.0), 0.0)
            _write_live_heartbeat(
                {
                    "status": "blocked",
                    "reason": "short_disabled_spot",
                    "symbol": symbol,
                    "gate_direction": "short",
                    "spot_short_enabled": bool(self.spot_short_enabled),
                    "available_usd": round(float(live_usd), 6),
                }
            )
            print("  blocked: spot short disabled")
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

        balance_valuation = self._build_balance_valuation(force_refresh=False)
        quote_usd_balance = max(
            self._to_float(
                balance_valuation.get("usd_cash_balance", balance_valuation.get("cash_usd", 0.0)),
                0.0,
            ),
            0.0,
        )
        total_cash_usd = max(
            self._to_float(balance_valuation.get("cash_usd", quote_usd_balance), quote_usd_balance),
            quote_usd_balance,
        )
        stable_cash_equivalent_usd = max(
            self._to_float(
                balance_valuation.get("stable_cash_equivalent_usd", total_cash_usd - quote_usd_balance),
                total_cash_usd - quote_usd_balance,
            ),
            0.0,
        )
        usd_balance = float(quote_usd_balance)
        holdings_value_usd = max(self._to_float(balance_valuation.get("holdings_value_usd", 0.0), 0.0), 0.0)
        portfolio_equity_usd = max(self._to_float(balance_valuation.get("total_equity_usd", usd_balance), usd_balance), usd_balance)
        symbol_values_usd = balance_valuation.get("symbol_values_usd", {})
        if not isinstance(symbol_values_usd, dict):
            symbol_values_usd = {}
        current_symbol_value_usd = max(
            self._to_float(symbol_values_usd.get(str(symbol).upper(), 0.0), 0.0),
            0.0,
        )

        balance_error = str(getattr(self.router.kraken, "last_balance_error", "") or "")
        balance_cache_age_sec = float(getattr(self.router.kraken, "_cached_balance_age_sec", lambda: float("inf"))())
        balance_confirmed_live = bool(quote_usd_balance > 0.0 and (not balance_error))
        balance_source = "live_quote_usd" if balance_confirmed_live else "cached_or_unknown"
        balance_degraded_mode = False

        direction = decision_direction
        side = "buy" if direction == "long" else "sell"
        sell_available_qty = 0.0
        sell_cap_qty = 0.0
        sell_entry_target_qty = 0.0

        if side == "sell":
            sell_available_qty = max(float(self.router.get_asset_balance(symbol, force_refresh=False) or 0.0), 0.0)
            sell_cap_qty = max(float(sell_available_qty) * float(self.close_balance_buffer_fraction), 0.0)
            sell_entry_target_qty = max(float(sell_cap_qty) * float(self.spot_inventory_entry_fraction), 0.0)
            if sell_cap_qty <= 0.0:
                cfg_for_fallback = self.router.get_symbol_config(symbol) or {}
                fallback_min_order = max(self._to_float(cfg_for_fallback.get("min_order", 0.0), 0.0), 0.0)
                fallback_min_order_notional = fallback_min_order * float(last)
                reserve_hint = max(self._to_float(self.runtime_cfg.get("reserve_usd", 0.0), 0.0), 0.0)
                affordable_buy_usd = max(float(usd_balance) - reserve_hint, 0.0)

                if fallback_min_order_notional > 0.0 and affordable_buy_usd >= fallback_min_order_notional:
                    direction = "long"
                    side = "buy"
                    _write_live_heartbeat(
                        {
                            "status": "degraded",
                            "reason": "short_without_inventory_forced_long",
                            "symbol": symbol,
                            "gate_direction": decision_direction,
                            "available_asset_qty": 0.0,
                            "affordable_buy_usd": round(float(affordable_buy_usd), 6),
                            "min_order_notional": round(float(fallback_min_order_notional), 6),
                        }
                    )
                else:
                    _write_live_heartbeat(
                        {
                            "status": "blocked",
                            "reason": "no_spot_inventory",
                            "symbol": symbol,
                            "gate_direction": direction,
                            "side": side,
                            "available_asset_qty": round(float(sell_available_qty), 10),
                        }
                    )
                    print("  blocked: no spot inventory")
                    return

        reserve_usd_runtime = self._to_float(
            self.runtime_cfg.get("reserve_usd", self.live_selection.get("reserve_usd", 0.0)),
            0.0,
        )
        reserve_usd_effective_hint = self._to_float(pick_meta.get("reserve_usd_effective", reserve_usd_runtime), reserve_usd_runtime)
        buy_affordable_usd = max(float(usd_balance) - max(float(reserve_usd_effective_hint), 0.0), 0.0)
        allow_cached_balance_trading = bool(self.runtime_cfg.get("allow_cached_balance_trading", False))
        cached_balance_trading_cap_usd = max(
            self._to_float(self.runtime_cfg.get("cached_balance_trading_cap_usd", 0.0), 0.0),
            0.0,
        )
        cached_balance_mode = False
        if side == "buy" and (not balance_confirmed_live):
            cached_balance_mode = bool(
                allow_cached_balance_trading
                and usd_balance > 0.0
                and (
                    "using_cached" in balance_error
                    or "Rate limit" in balance_error
                    or "EAPI:Rate limit exceeded" in balance_error
                )
            )
            if cached_balance_mode:
                if cached_balance_trading_cap_usd > 0.0:
                    buy_affordable_usd = min(float(buy_affordable_usd), float(cached_balance_trading_cap_usd))
                buy_affordable_usd = max(float(buy_affordable_usd), 0.0)
                if buy_affordable_usd > 0.0:
                    balance_degraded_mode = True

        if side == "buy" and (((not balance_confirmed_live) and (not balance_degraded_mode)) or buy_affordable_usd <= 0.0):
            cfg_for_convert = self.router.get_symbol_config(symbol) or {}
            convert_min_order = max(self._to_float(cfg_for_convert.get("min_order", 0.0), 0.0), 0.0)
            convert_required_usd = max(convert_min_order * float(last), self.min_collateral_convert_usd)
            convert_result = self._attempt_collateral_convert_for_liquidity(
                now,
                reason="no_confirmed_funds",
                required_usd=convert_required_usd,
                preferred_symbol=str(symbol),
            )

            if bool(convert_result.get("executed", False)):
                _write_live_heartbeat(
                    {
                        "status": "degraded",
                        "reason": "collateral_convert_for_buy_liquidity",
                        "symbol": symbol,
                        "side": side,
                        "available_usd": round(float(usd_balance), 6),
                        "reserve_usd": round(float(reserve_usd_effective_hint), 6),
                        "affordable_buy_usd": round(float(buy_affordable_usd), 6),
                        "balance_error": balance_error,
                        "balance_cache_age_sec": round(float(balance_cache_age_sec), 3) if math.isfinite(balance_cache_age_sec) else None,
                        "balance_confirmed_live": bool(balance_confirmed_live),
                        "balance_source": balance_source,
                        "collateral_convert": convert_result,
                    }
                )
                print("  degraded: collateral converted to restore buy liquidity")
                return

            _write_live_heartbeat(
                {
                    "status": "blocked",
                    "reason": "no_confirmed_funds",
                    "symbol": symbol,
                    "side": side,
                    "available_usd": round(float(usd_balance), 6),
                    "reserve_usd": round(float(reserve_usd_effective_hint), 6),
                    "affordable_buy_usd": round(float(buy_affordable_usd), 6),
                    "balance_error": balance_error,
                    "balance_cache_age_sec": round(float(balance_cache_age_sec), 3) if math.isfinite(balance_cache_age_sec) else None,
                    "balance_confirmed_live": bool(balance_confirmed_live),
                    "balance_source": balance_source,
                    "allow_cached_balance_trading": bool(allow_cached_balance_trading),
                    "cached_balance_trading_cap_usd": round(float(cached_balance_trading_cap_usd), 6),
                    "cached_balance_mode": bool(cached_balance_mode),
                    "collateral_convert": convert_result,
                }
            )
            print("  blocked: no confirmed funds")
            return

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

        if side == "buy" and self.deliberate_mode_enabled:
            global_window_start = now - timedelta(seconds=float(self.global_entries_window_sec))
            self.entry_timestamps_utc = [
                ts
                for ts in self.entry_timestamps_utc
                if isinstance(ts, datetime) and ts >= global_window_start
            ]
            recent_entries = int(len(self.entry_timestamps_utc))
            if recent_entries >= int(self.max_entries_per_hour):
                _write_live_heartbeat(
                    {
                        "status": "blocked",
                        "reason": "global_entry_rate_limit",
                        "symbol": symbol,
                        "entries_in_global_window": recent_entries,
                        "global_entries_window_sec": round(float(self.global_entries_window_sec), 6),
                        "max_entries_per_hour": int(self.max_entries_per_hour),
                    }
                )
                print("  blocked: global entry rate limit")
                return

            if self.entry_timestamps_utc and self.global_entry_cooldown_sec > 0.0:
                elapsed_global_sec = max((now - self.entry_timestamps_utc[-1]).total_seconds(), 0.0)
                if elapsed_global_sec < float(self.global_entry_cooldown_sec):
                    _write_live_heartbeat(
                        {
                            "status": "blocked",
                            "reason": "global_entry_cooldown_active",
                            "symbol": symbol,
                            "elapsed_global_sec": round(float(elapsed_global_sec), 6),
                            "global_entry_cooldown_sec": round(float(self.global_entry_cooldown_sec), 6),
                        }
                    )
                    print("  blocked: global entry cooldown")
                    return

            symbol_key = str(symbol or "").upper().strip()
            symbol_history = [
                ts
                for ts in self.symbol_entry_timestamps_utc.get(symbol_key, [])
                if isinstance(ts, datetime)
            ]
            symbol_window_start = now - timedelta(seconds=float(self.per_symbol_entries_window_sec))
            symbol_history = [ts for ts in symbol_history if ts >= symbol_window_start]
            self.symbol_entry_timestamps_utc[symbol_key] = symbol_history

            symbol_streak_window_start = now - timedelta(seconds=float(self.same_symbol_streak_window_sec))
            self.entry_symbol_history = [
                (ts, sym)
                for ts, sym in self.entry_symbol_history
                if isinstance(ts, datetime) and ts >= symbol_streak_window_start
            ]

            streak_count = 0
            for ts, sym in reversed(self.entry_symbol_history):
                if sym == symbol_key:
                    streak_count += 1
                    continue
                break
            if streak_count >= int(self.max_consecutive_same_symbol_entries):
                _write_live_heartbeat(
                    {
                        "status": "blocked",
                        "reason": "same_symbol_streak_limit",
                        "symbol": symbol,
                        "same_symbol_streak_count": int(streak_count),
                        "max_consecutive_same_symbol_entries": int(self.max_consecutive_same_symbol_entries),
                        "same_symbol_streak_window_sec": round(float(self.same_symbol_streak_window_sec), 6),
                    }
                )
                print("  blocked: same symbol streak limit")
                return

            symbol_entries = int(len(symbol_history))
            if symbol_entries >= int(self.max_entries_per_symbol_window):
                _write_live_heartbeat(
                    {
                        "status": "blocked",
                        "reason": "symbol_entry_window_limit",
                        "symbol": symbol,
                        "symbol_entries_window": symbol_entries,
                        "max_entries_per_symbol_window": int(self.max_entries_per_symbol_window),
                        "per_symbol_entries_window_sec": round(float(self.per_symbol_entries_window_sec), 6),
                    }
                )
                print("  blocked: symbol entry window limit")
                return

            if symbol_history and self.per_symbol_entry_cooldown_sec > 0.0:
                elapsed_symbol_sec = max((now - symbol_history[-1]).total_seconds(), 0.0)
                if elapsed_symbol_sec < float(self.per_symbol_entry_cooldown_sec):
                    _write_live_heartbeat(
                        {
                            "status": "blocked",
                            "reason": "symbol_entry_cooldown_active",
                            "symbol": symbol,
                            "elapsed_symbol_sec": round(float(elapsed_symbol_sec), 6),
                            "per_symbol_entry_cooldown_sec": round(float(self.per_symbol_entry_cooldown_sec), 6),
                        }
                    )
                    print("  blocked: symbol entry cooldown")
                    return

        stop_price = last * (0.98 if direction == "long" else 1.02)
        urgency = _resolve_urgency(float(gate_decision.composite_score), spread_bps, direction)
        fee_bps = float(self.live_selection.get("fee_bps", 10.0) or 10.0)
        slippage_bps = float(self.live_selection.get("slippage_bps", max(spread_bps * 0.6, 8.0)) or max(spread_bps * 0.6, 8.0))
        drawdown_pct = abs(float(getattr(self.portfolio, "max_drawdown", 0.0) or 0.0))
        reserve_usd_effective = self._to_float(pick_meta.get("reserve_usd_effective", reserve_usd_runtime), reserve_usd_runtime)
        reserve_usd = min(max(reserve_usd_effective, 0.0), max(usd_balance, 0.0))
        sizing_equity_usd = float(usd_balance)
        sizing_reserve_usd = float(reserve_usd)
        if side == "sell":
            sizing_equity_usd = max(float(usd_balance), float(sell_cap_qty) * float(last), 0.0)
            sizing_reserve_usd = 0.0
        max_notional_usd_config = self._to_float(
            self.runtime_cfg.get("max_notional_per_trade_usd", self.live_selection.get("max_notional_usd", 0.0)),
            0.0,
        )
        compounding_available_usd = float(buy_affordable_usd) if side == "buy" else float(sizing_equity_usd)
        compounding_cap_usd, compounding_meta = self._compute_compounding_notional_cap(
            available_usd=compounding_available_usd,
            gate_score=float(gate_decision.composite_score),
            drawdown_pct=float(drawdown_pct),
            window_fail_rate=float(window_fail_rate),
            static_cap_usd=float(max_notional_usd_config),
        )

        effective_notional_throttle = min(float(self.notional_throttle), float(window_throttle))
        effective_max_notional_usd = float(compounding_cap_usd)
        if effective_max_notional_usd > 0.0:
            effective_max_notional_usd = max(0.5, effective_max_notional_usd * max(float(effective_notional_throttle), 0.05))
        size_decision = self.sizing_engine.size(
            SizeInput(
                equity_usd=sizing_equity_usd,
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
                reserve_usd=sizing_reserve_usd,
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

        if side == "sell":
            if qty <= 0.0:
                qty = float(sell_entry_target_qty)
            qty = min(max(float(qty), 0.0), float(sell_cap_qty))
            notional_usd = float(qty) * float(last)
            risk_usd = max(risk_usd, abs(float(last) - float(stop_price)) * float(qty))

        min_order_promoted = False
        if qty <= 0:
            _write_live_heartbeat(
                {
                    "status": "blocked",
                    "reason": "sizing_zero",
                    "symbol": symbol,
                    "side": side,
                    "urgency": urgency,
                    "available_asset_qty": round(float(sell_available_qty), 10) if side == "sell" else None,
                }
            )
            print("  blocked: sizing qty=0")
            return

        cfg = self.router.get_symbol_config(symbol)
        min_order = self._effective_min_order(symbol, float(cfg["min_order"]))
        if qty < min_order:
            min_notional = min_order * float(last)
            cap_ok = (effective_max_notional_usd <= 0.0) or (min_notional <= effective_max_notional_usd)
            if side == "buy":
                affordable = max(float(usd_balance) - reserve_usd, 0.0)
                cap_breach_applied = False
                if (not cap_ok) and self.allow_min_order_cap_breach and min_notional <= affordable:
                    cap_ok = True
                    cap_breach_applied = True
                if min_notional <= affordable and cap_ok:
                    qty = min_order
                    notional_usd = qty * float(last)
                    risk_usd = max(risk_usd, abs(float(last) - float(stop_price)) * qty)
                    min_order_promoted = True
                    if cap_breach_applied:
                        compounding_meta["min_order_cap_breach_applied"] = True
                else:
                    convert_result: Optional[dict[str, Any]] = None
                    if min_notional > affordable:
                        convert_result = self._attempt_collateral_convert_for_liquidity(
                            now,
                            reason="min_order_quote_shortfall",
                            required_usd=float(min_notional),
                            preferred_symbol=str(symbol),
                        )
                        if isinstance(convert_result, dict) and bool(convert_result.get("executed", False)):
                            _write_live_heartbeat(
                                {
                                    "status": "degraded",
                                    "reason": "collateral_convert_for_min_order",
                                    "symbol": symbol,
                                    "side": side,
                                    "qty": round(float(qty), 10),
                                    "min_order": round(float(min_order), 10),
                                    "min_notional_usd": round(float(min_notional), 6),
                                    "quote_usd_balance": round(float(quote_usd_balance), 6),
                                    "stable_cash_equivalent_usd": round(float(stable_cash_equivalent_usd), 6),
                                    "collateral_convert": convert_result,
                                }
                            )
                            print("  degraded: collateral converted for min_order")
                            return

                    block_reason = "min_order_cap_conflict" if (min_notional <= affordable and (not cap_ok)) else "min_order_insufficient_quote"
                    _write_live_heartbeat(
                        {
                            "status": "blocked",
                            "reason": block_reason,
                            "symbol": symbol,
                            "side": side,
                            "qty": round(float(qty), 10),
                            "min_order": round(float(min_order), 10),
                            "min_notional_usd": round(float(min_notional), 6),
                            "quote_usd_balance": round(float(quote_usd_balance), 6),
                            "total_cash_usd": round(float(total_cash_usd), 6),
                            "stable_cash_equivalent_usd": round(float(stable_cash_equivalent_usd), 6),
                            "affordable_buy_usd": round(float(affordable), 6),
                            "effective_max_notional_usd": round(float(effective_max_notional_usd), 6),
                            "allow_min_order_cap_breach": bool(self.allow_min_order_cap_breach),
                            "collateral_convert": convert_result,
                        }
                    )
                    print(f"  blocked: {block_reason}")
                    return
            else:
                if float(sell_cap_qty) < float(min_order) <= float(sell_available_qty):
                    sell_cap_qty = float(sell_available_qty)
                if float(sell_cap_qty) < float(min_order):
                    _write_live_heartbeat(
                        {
                            "status": "blocked",
                            "reason": "inventory_below_min_order",
                            "symbol": symbol,
                            "side": side,
                            "available_asset_qty": round(float(sell_available_qty), 10),
                            "sell_cap_qty": round(float(sell_cap_qty), 10),
                            "min_order": round(float(min_order), 10),
                        }
                    )
                    print("  blocked: inventory below min_order")
                    return

                promoted_qty = max(float(min_order), float(sell_entry_target_qty))
                if effective_max_notional_usd > 0.0:
                    promoted_qty = min(promoted_qty, float(effective_max_notional_usd) / max(float(last), 1e-9))
                qty = min(promoted_qty, float(sell_cap_qty))
                if qty < float(min_order):
                    _write_live_heartbeat(
                        {
                            "status": "blocked",
                            "reason": "min_order_after_caps",
                            "symbol": symbol,
                            "side": side,
                            "qty": round(float(qty), 10),
                            "min_order": round(float(min_order), 10),
                            "max_notional_usd": round(float(effective_max_notional_usd), 6),
                        }
                    )
                    print("  blocked: min_order after caps")
                    return
                notional_usd = float(qty) * float(last)
                risk_usd = max(risk_usd, abs(float(last) - float(stop_price)) * float(qty))
                min_order_promoted = True

        if side == "buy":
            projected_total_equity_usd = max(float(portfolio_equity_usd), float(usd_balance + holdings_value_usd), 1e-9)
            max_symbol_value_usd = float(self.max_symbol_allocation_pct) * float(projected_total_equity_usd)
            allowed_additional_usd = max(float(max_symbol_value_usd) - float(current_symbol_value_usd), 0.0)
            current_weight_pct = (float(current_symbol_value_usd) / float(projected_total_equity_usd)) * 100.0

            if allowed_additional_usd <= 0.0:
                _write_live_heartbeat(
                    {
                        "status": "blocked",
                        "reason": "symbol_concentration_limit",
                        "symbol": symbol,
                        "side": side,
                        "current_symbol_value_usd": round(float(current_symbol_value_usd), 6),
                        "portfolio_equity_usd": round(float(projected_total_equity_usd), 6),
                        "current_symbol_weight_pct": round(float(current_weight_pct), 6),
                        "max_symbol_allocation_pct": round(float(self.max_symbol_allocation_pct) * 100.0, 6),
                    }
                )
                print("  blocked: symbol concentration cap")
                return

            if float(notional_usd) > float(allowed_additional_usd):
                adjusted_qty = float(allowed_additional_usd) / max(float(last), 1e-9)
                if adjusted_qty >= float(min_order):
                    qty = float(adjusted_qty)
                    notional_usd = float(qty) * float(last)
                    risk_usd = max(risk_usd, abs(float(last) - float(stop_price)) * float(qty))
                else:
                    _write_live_heartbeat(
                        {
                            "status": "blocked",
                            "reason": "symbol_concentration_min_order_conflict",
                            "symbol": symbol,
                            "side": side,
                            "current_symbol_value_usd": round(float(current_symbol_value_usd), 6),
                            "portfolio_equity_usd": round(float(projected_total_equity_usd), 6),
                            "allowed_additional_usd": round(float(allowed_additional_usd), 6),
                            "max_symbol_allocation_pct": round(float(self.max_symbol_allocation_pct) * 100.0, 6),
                            "min_order": round(float(min_order), 10),
                        }
                    )
                    print("  blocked: concentration cap below min_order")
                    return

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
            available_asset_qty = None

            if insufficient_funds and side == "sell":
                available_asset_qty = max(float(self.router.get_asset_balance(symbol, force_refresh=False) or 0.0), 0.0)

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
                unwind_qty, unwind_available_qty, unwind_balance_error = self._resolve_close_qty_for_spot(
                    symbol,
                    unwind_qty,
                    "sell",
                )
                unwind = self.router.place_order(symbol, "sell", unwind_qty, None) if unwind_qty > 0.0 else {"error": "unwind_no_inventory"}
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
                            "available_asset_qty": round(float(unwind_available_qty), 10),
                            "balance_error": unwind_balance_error,
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
                    "balance_error": balance_error,
                    "balance_cache_age_sec": round(float(balance_cache_age_sec), 3) if math.isfinite(balance_cache_age_sec) else None,
                    "balance_confirmed_live": bool(balance_confirmed_live),
                    "balance_source": balance_source,
                    "available_usd": round(float(usd_balance), 6),
                    "affordable_buy_usd": round(float(buy_affordable_usd), 6) if side == "buy" else None,
                    "available_asset_qty": round(float(available_asset_qty), 10) if available_asset_qty is not None else None,
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

        if side == "buy":
            self.last_entry_symbol = str(symbol or "").upper().strip()
            self.last_entry_time_utc = now.isoformat()
            self.entry_timestamps_utc.append(now)
            symbol_key = str(symbol or "").upper().strip()
            symbol_history = [
                ts
                for ts in self.symbol_entry_timestamps_utc.get(symbol_key, [])
                if isinstance(ts, datetime)
            ]
            symbol_history.append(now)
            self.symbol_entry_timestamps_utc[symbol_key] = symbol_history
            self.entry_symbol_history.append((now, symbol_key))

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
                "max_notional_per_trade_usd_config": round(float(max_notional_usd_config), 6),
                "compounding_meta": dict(compounding_meta),
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
                "max_notional_per_trade_usd_config": round(float(max_notional_usd_config), 6),
                "compounding_meta": dict(compounding_meta),
                "effective_min_order": round(float(min_order), 10),
                "edge_score": round(float(gate_decision.composite_score), 6),
                "portfolio_heat": round(portfolio_heat, 6),
                "open_positions": open_positions,
                "max_open_positions": self.max_open_positions,
            }
        )

        self._recover_gate_threshold_after_fill(now)

        print(f"  placed txid={txid}")

    def run_institutional_execution_loop(self):
        print(f"starting live loop (interval={self.loop_seconds:.2f}s, max_open={self.max_open_positions})")
        while True:
            try:
                self._refresh_runtime_config()
                runtime_symbol_raw = str(self.runtime_cfg.get("symbol", "") or "").strip()
                runtime_symbol_upper = runtime_symbol_raw.upper()
                universe_mode = runtime_symbol_upper in {"", "UNIVERSE", "ADAPTIVE_UNIVERSE", "AUTO"}
                preferred = ""
                preferred_source = "none"
                if not universe_mode:
                    preferred = runtime_symbol_upper.split("/")[0].strip()
                    preferred_source = "runtime_symbol"
                elif self.allow_best_multi_preference:
                    preferred = (_preferred_live_symbol() or "").upper().strip()
                    if preferred:
                        preferred_source = "best_multi"

                intel_symbols: list[str] = []
                intel_meta: dict[str, Any] = {
                    "symbol_intel_enabled": bool(self.symbol_intel_enabled),
                    "symbol_intel_file_exists": bool(SYMBOL_FLIP_INTEL_FILE.exists()),
                    "symbol_intel_stale": False,
                    "symbol_intel_age_sec": None,
                    "symbol_intel_candidate_count": 0,
                    "symbol_intel_selected_count": 0,
                    "symbol_intel_executable_count": 0,
                    "symbol_intel_rejected_unpriced": 0,
                    "symbol_intel_rejected_affordable": 0,
                    "symbol_intel_rejected_cap": 0,
                    "symbol_intel_source": "none",
                }
                if universe_mode:
                    intel_symbols, intel_meta = self._symbol_flip_intel_candidates()
                    if (not preferred) and intel_symbols:
                        preferred = str(intel_symbols[0]).upper().strip()
                        preferred_source = "symbol_flip_intel"

                scan_cap = int(
                    self._clamp(
                        self._to_float(self.runtime_cfg.get("scan_top_n", 1200), 1200.0),
                        4.0,
                        5000.0,
                    )
                )
                valuation_hint = self._build_balance_valuation(force_refresh=False)
                quote_usd_hint = max(
                    self._to_float(
                        valuation_hint.get("usd_cash_balance", valuation_hint.get("cash_usd", 0.0)),
                        0.0,
                    ),
                    0.0,
                )
                total_cash_usd_hint = max(
                    self._to_float(valuation_hint.get("cash_usd", quote_usd_hint), quote_usd_hint),
                    quote_usd_hint,
                )
                stable_cash_equivalent_hint = max(
                    self._to_float(
                        valuation_hint.get("stable_cash_equivalent_usd", total_cash_usd_hint - quote_usd_hint),
                        total_cash_usd_hint - quote_usd_hint,
                    ),
                    0.0,
                )
                _write_live_heartbeat(
                    {
                        "status": "running",
                        "reason": "scan_cycle_start",
                        "universe_mode": bool(universe_mode),
                        "preferred_symbol": preferred,
                        "preferred_source": preferred_source,
                        "universe_scan_cap": int(scan_cap),
                        "gate_min_composite_score": round(float(getattr(self.signal_gate, "min_composite_score", 0.60)), 6),
                        "adaptive_gate_enabled": bool(self.adaptive_gate_enabled),
                        "adaptive_gate_relax_offset": round(float(self.gate_relax_offset), 6),
                        "symbol_intel_enabled": bool(intel_meta.get("symbol_intel_enabled", False)),
                        "symbol_intel_source": str(intel_meta.get("symbol_intel_source", "none") or "none"),
                        "symbol_intel_stale": bool(intel_meta.get("symbol_intel_stale", False)),
                        "symbol_intel_age_sec": intel_meta.get("symbol_intel_age_sec"),
                        "symbol_intel_selected_count": int(self._to_float(intel_meta.get("symbol_intel_selected_count", 0), 0.0)),
                        "quote_usd_hint": round(float(quote_usd_hint), 6),
                        "total_cash_usd_hint": round(float(total_cash_usd_hint), 6),
                        "stable_cash_equivalent_usd_hint": round(float(stable_cash_equivalent_hint), 6),
                        "cash_usd_hint": round(float(self._to_float(valuation_hint.get("cash_usd", 0.0), 0.0)), 6),
                        "holdings_value_usd_hint": round(float(self._to_float(valuation_hint.get("holdings_value_usd", 0.0), 0.0)), 6),
                        "total_equity_usd_hint": round(float(self._to_float(valuation_hint.get("total_equity_usd", 0.0), 0.0)), 6),
                        "largest_holding_symbol": str(valuation_hint.get("largest_symbol", "") or ""),
                        "largest_holding_weight_pct": round(float(self._to_float(valuation_hint.get("largest_weight_pct", 0.0), 0.0)), 6),
                    }
                )

                runtime_extra_symbols: list[str] = []
                for field_name in ("symbol_universe_extra", "symbol_whitelist", "symbols"):
                    raw_values = self.runtime_cfg.get(field_name, [])
                    if isinstance(raw_values, str):
                        raw_values = [s.strip() for s in raw_values.split(",") if str(s).strip()]
                    if isinstance(raw_values, list):
                        runtime_extra_symbols.extend(str(s) for s in raw_values if str(s).strip())
                if intel_symbols:
                    runtime_extra_symbols.extend(intel_symbols)

                candidates = self.router.get_candidate_symbols(
                    max_symbols=scan_cap,
                    extra_symbols=runtime_extra_symbols,
                )

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
                allow_cached_balance_trading = bool(self.runtime_cfg.get("allow_cached_balance_trading", False))
                cached_balance_trading_cap_usd = max(
                    self._to_float(
                        self.runtime_cfg.get(
                            "cached_balance_trading_cap_usd",
                            max_notional_usd_cap if max_notional_usd_cap > 0.0 else 0.0,
                        ),
                        max_notional_usd_cap if max_notional_usd_cap > 0.0 else 0.0,
                    ),
                    0.0,
                )
                usd_balance_hint = float(quote_usd_hint)
                holdings_value_hint = max(self._to_float(valuation_hint.get("holdings_value_usd", 0.0), 0.0), 0.0)
                total_equity_hint = max(
                    self._to_float(valuation_hint.get("total_equity_usd", usd_balance_hint), usd_balance_hint),
                    usd_balance_hint,
                )
                largest_holding_symbol_hint = str(valuation_hint.get("largest_symbol", "") or "")
                largest_holding_weight_hint = max(self._to_float(valuation_hint.get("largest_weight_pct", 0.0), 0.0), 0.0)
                balance_error_hint = str(getattr(self.router.kraken, "last_balance_error", "") or "")
                balance_cache_age_sec = float(getattr(self.router.kraken, "_cached_balance_age_sec", lambda: float("inf"))())
                using_cached_balance_hint = (
                    "using_cached_balance" in balance_error_hint
                    or "using_cached_usd_only" in balance_error_hint
                    or "using_cached_balance_snapshot" in balance_error_hint
                )
                rate_limited_balance_hint = "Rate limit" in balance_error_hint or "EAPI:Rate limit exceeded" in balance_error_hint
                balance_confirmed_live = usd_balance_hint > 0.0 and (not balance_error_hint)
                reserve_usd_hint = float(reserve_usd_configured)
                if self.dynamic_reserve_enabled and usd_balance_hint > 0.0:
                    dynamic_cap = max(
                        float(self.dynamic_reserve_floor_usd),
                        float(usd_balance_hint) * float(self.dynamic_reserve_max_balance_fraction),
                    )
                    reserve_usd_hint = min(float(reserve_usd_configured), float(dynamic_cap))
                affordable_usd_hint = max(usd_balance_hint - reserve_usd_hint, 0.0)
                cached_balance_stale = (
                    (using_cached_balance_hint and balance_cache_age_sec > 120.0)
                    or (rate_limited_balance_hint and (not balance_confirmed_live) and balance_cache_age_sec > 120.0)
                )
                if (not balance_confirmed_live) or cached_balance_stale:
                    cached_fallback_allowed = (
                        allow_cached_balance_trading
                        and usd_balance_hint > 0.0
                        and (using_cached_balance_hint or rate_limited_balance_hint)
                    )
                    if cached_fallback_allowed:
                        affordable_usd_hint = max(usd_balance_hint - reserve_usd_hint, 0.0)
                        if cached_balance_trading_cap_usd > 0.0:
                            affordable_usd_hint = min(affordable_usd_hint, cached_balance_trading_cap_usd)
                    else:
                        affordable_usd_hint = 0.0

                    if universe_mode and intel_symbols:
                        intel_symbols, intel_exec_meta = self._filter_symbols_by_executable_notional(
                            intel_symbols,
                            affordable_usd_hint=float(affordable_usd_hint),
                            max_notional_usd_cap=float(max_notional_usd_cap),
                        )
                        intel_meta["symbol_intel_executable_count"] = int(
                            self._to_float(intel_exec_meta.get("executable_count", 0), 0.0)
                        )
                        intel_meta["symbol_intel_rejected_unpriced"] = int(
                            self._to_float(intel_exec_meta.get("rejected_unpriced", 0), 0.0)
                        )
                        intel_meta["symbol_intel_rejected_affordable"] = int(
                            self._to_float(intel_exec_meta.get("rejected_affordable", 0), 0.0)
                        )
                        intel_meta["symbol_intel_rejected_cap"] = int(
                            self._to_float(intel_exec_meta.get("rejected_cap", 0), 0.0)
                        )
                        if preferred_source == "symbol_flip_intel":
                            preferred = str(intel_symbols[0]).upper().strip() if intel_symbols else ""
                            preferred_source = "symbol_flip_intel_executable" if preferred else "none"

                symbol = preferred
                preferred_cfg = self.router.get_symbol_config(symbol) if symbol else None
                preferred_ticker = self.router.get_ticker(symbol) if (symbol and preferred_cfg and symbol not in blocked) else None
                preferred_min_order_notional = 0.0
                preferred_affordable = True
                if preferred_cfg and preferred_ticker:
                    preferred_min_order_qty = self._effective_min_order(
                        symbol,
                        self._to_float(preferred_cfg.get("min_order", 0.0), 0.0),
                    )
                    preferred_min_order_notional = max(
                        preferred_min_order_qty,
                        0.0,
                    ) * max(self._to_float(preferred_ticker.get("last", 0.0), 0.0), 0.0)
                    if cached_balance_stale and not (allow_cached_balance_trading and affordable_usd_hint > 0.0):
                        preferred_affordable = False
                    if affordable_usd_hint <= 0.0:
                        preferred_affordable = False
                    if max_notional_usd_cap > 0.0 and preferred_min_order_notional > max_notional_usd_cap:
                        preferred_affordable = False
                    if preferred_min_order_notional > affordable_usd_hint:
                        preferred_affordable = False

                preloaded_ticker: Optional[dict[str, Any]] = None
                selection_meta: dict[str, Any] = {
                    "preferred_symbol": preferred,
                    "preferred_source": preferred_source,
                    "universe_mode": bool(universe_mode),
                    "preferred_min_order_notional": round(float(preferred_min_order_notional), 6),
                    "blocked_count": len(blocked),
                    "universe_scan_cap": int(scan_cap),
                    "universe_extra_count": int(len(runtime_extra_symbols)),
                    "symbol_intel_source": str(intel_meta.get("symbol_intel_source", "none") or "none"),
                    "symbol_intel_stale": bool(intel_meta.get("symbol_intel_stale", False)),
                    "symbol_intel_age_sec": intel_meta.get("symbol_intel_age_sec"),
                    "symbol_intel_candidate_count": int(self._to_float(intel_meta.get("symbol_intel_candidate_count", 0), 0.0)),
                    "symbol_intel_selected_count": int(self._to_float(intel_meta.get("symbol_intel_selected_count", 0), 0.0)),
                    "symbol_intel_executable_count": int(self._to_float(intel_meta.get("symbol_intel_executable_count", 0), 0.0)),
                    "symbol_intel_rejected_unpriced": int(self._to_float(intel_meta.get("symbol_intel_rejected_unpriced", 0), 0.0)),
                    "symbol_intel_rejected_affordable": int(self._to_float(intel_meta.get("symbol_intel_rejected_affordable", 0), 0.0)),
                    "symbol_intel_rejected_cap": int(self._to_float(intel_meta.get("symbol_intel_rejected_cap", 0), 0.0)),
                    "reserve_usd_configured": round(float(reserve_usd_configured), 6),
                    "reserve_usd_effective": round(float(reserve_usd_hint), 6),
                    "universe_candidate_count": int(len(candidates)),
                    "universe_sample_size": 0,
                    "universe_ticker_hits": 0,
                    "universe_affordability_rejects": 0,
                    "affordable_usd_hint": round(float(affordable_usd_hint), 6),
                    "quote_usd_hint": round(float(quote_usd_hint), 6),
                    "total_cash_usd_hint": round(float(total_cash_usd_hint), 6),
                    "stable_cash_equivalent_usd_hint": round(float(stable_cash_equivalent_hint), 6),
                    "cash_usd_hint": round(float(usd_balance_hint), 6),
                    "holdings_value_usd_hint": round(float(holdings_value_hint), 6),
                    "total_equity_usd_hint": round(float(total_equity_hint), 6),
                    "largest_holding_symbol": largest_holding_symbol_hint,
                    "largest_holding_weight_pct": round(float(largest_holding_weight_hint), 6),
                    "max_symbol_allocation_pct": round(float(self.max_symbol_allocation_pct) * 100.0, 6),
                    "balance_error_hint": balance_error_hint,
                    "balance_cache_age_sec": round(float(balance_cache_age_sec), 3) if math.isfinite(balance_cache_age_sec) else None,
                    "balance_confirmed_live": bool(balance_confirmed_live),
                    "using_cached_balance_hint": bool(using_cached_balance_hint),
                    "rate_limited_balance_hint": bool(rate_limited_balance_hint),
                    "cached_balance_stale": bool(cached_balance_stale),
                    "max_notional_usd_cap": round(float(max_notional_usd_cap), 6),
                    "allow_cached_balance_trading": bool(allow_cached_balance_trading),
                    "cached_balance_trading_cap_usd": round(float(cached_balance_trading_cap_usd), 6),
                    "symbol_source": "preferred" if preferred else "none",
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
                    selection_meta["universe_extra_count"] = int(len(runtime_extra_symbols))
                    selection_meta["symbol_intel_source"] = str(intel_meta.get("symbol_intel_source", "none") or "none")
                    selection_meta["symbol_intel_stale"] = bool(intel_meta.get("symbol_intel_stale", False))
                    selection_meta["symbol_intel_age_sec"] = intel_meta.get("symbol_intel_age_sec")
                    selection_meta["symbol_intel_candidate_count"] = int(self._to_float(intel_meta.get("symbol_intel_candidate_count", 0), 0.0))
                    selection_meta["symbol_intel_selected_count"] = int(self._to_float(intel_meta.get("symbol_intel_selected_count", 0), 0.0))
                    selection_meta["symbol_intel_executable_count"] = int(self._to_float(intel_meta.get("symbol_intel_executable_count", 0), 0.0))
                    selection_meta["symbol_intel_rejected_unpriced"] = int(self._to_float(intel_meta.get("symbol_intel_rejected_unpriced", 0), 0.0))
                    selection_meta["symbol_intel_rejected_affordable"] = int(self._to_float(intel_meta.get("symbol_intel_rejected_affordable", 0), 0.0))
                    selection_meta["symbol_intel_rejected_cap"] = int(self._to_float(intel_meta.get("symbol_intel_rejected_cap", 0), 0.0))
                    selection_meta["reserve_usd_configured"] = round(float(reserve_usd_configured), 6)
                    selection_meta["reserve_usd_effective"] = round(float(reserve_usd_hint), 6)
                    selection_meta["affordable_usd_hint"] = round(float(affordable_usd_hint), 6)
                    selection_meta["quote_usd_hint"] = round(float(quote_usd_hint), 6)
                    selection_meta["total_cash_usd_hint"] = round(float(total_cash_usd_hint), 6)
                    selection_meta["stable_cash_equivalent_usd_hint"] = round(float(stable_cash_equivalent_hint), 6)
                    selection_meta["cash_usd_hint"] = round(float(usd_balance_hint), 6)
                    selection_meta["holdings_value_usd_hint"] = round(float(holdings_value_hint), 6)
                    selection_meta["total_equity_usd_hint"] = round(float(total_equity_hint), 6)
                    selection_meta["largest_holding_symbol"] = largest_holding_symbol_hint
                    selection_meta["largest_holding_weight_pct"] = round(float(largest_holding_weight_hint), 6)
                    selection_meta["max_symbol_allocation_pct"] = round(float(self.max_symbol_allocation_pct) * 100.0, 6)
                    selection_meta["balance_error_hint"] = balance_error_hint
                    selection_meta["balance_cache_age_sec"] = round(float(balance_cache_age_sec), 3) if math.isfinite(balance_cache_age_sec) else None
                    selection_meta["balance_confirmed_live"] = bool(balance_confirmed_live)
                    selection_meta["using_cached_balance_hint"] = bool(using_cached_balance_hint)
                    selection_meta["rate_limited_balance_hint"] = bool(rate_limited_balance_hint)
                    selection_meta["cached_balance_stale"] = bool(cached_balance_stale)
                    selection_meta["max_notional_usd_cap"] = round(float(max_notional_usd_cap), 6)
                    selection_meta["allow_cached_balance_trading"] = bool(allow_cached_balance_trading)
                    selection_meta["cached_balance_trading_cap_usd"] = round(float(cached_balance_trading_cap_usd), 6)
                    selection_meta["preferred_min_order_notional"] = round(float(preferred_min_order_notional), 6)
                    selection_meta["preferred_source"] = preferred_source
                    selection_meta["universe_mode"] = bool(universe_mode)
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

                selected_symbol = str(symbol).upper().strip()
                if (
                    universe_mode
                    and self.same_symbol_reentry_cooldown_sec > 0.0
                    and selected_symbol
                    and selected_symbol == str(self.last_entry_symbol or "").upper().strip()
                ):
                    elapsed_sec = float("inf")
                    last_entry_utc = str(self.last_entry_time_utc or "").strip()
                    if last_entry_utc:
                        try:
                            last_entry_dt = datetime.fromisoformat(last_entry_utc.replace("Z", "+00:00"))
                            if last_entry_dt.tzinfo is None:
                                last_entry_dt = last_entry_dt.replace(tzinfo=timezone.utc)
                            elapsed_sec = max((loop_now - last_entry_dt).total_seconds(), 0.0)
                        except Exception:
                            elapsed_sec = float("inf")

                    if math.isfinite(elapsed_sec) and elapsed_sec < float(self.same_symbol_reentry_cooldown_sec):
                        rotate_candidates = [
                            s for s in candidates if str(s).upper().strip() != selected_symbol
                        ]
                        if rotate_candidates:
                            rotated_symbol, rotated_ticker, rotated_meta = self._select_symbol_from_universe(
                                "",
                                rotate_candidates,
                                affordable_usd_hint=affordable_usd_hint,
                                max_notional_usd_cap=max_notional_usd_cap,
                                allow_preferred_shortcut=False,
                            )
                            if rotated_symbol:
                                symbol = rotated_symbol
                                preloaded_ticker = rotated_ticker
                                selection_meta["rotated_from_symbol"] = selected_symbol
                                selection_meta["symbol_rotation_reason"] = "same_symbol_reentry_cooldown"
                                selection_meta["same_symbol_elapsed_sec"] = round(float(elapsed_sec), 6)
                                if isinstance(rotated_meta, dict):
                                    for field in (
                                        "symbol_source",
                                        "selected_spread_bps",
                                        "selected_min_order_notional",
                                        "universe_sample_size",
                                        "universe_sample_escalated",
                                        "universe_ticker_hits",
                                        "universe_affordability_rejects",
                                    ):
                                        if field in rotated_meta:
                                            selection_meta[field] = rotated_meta[field]

                selection_meta["selected_symbol"] = str(symbol).upper()
                self.last_symbol_selection_meta = dict(selection_meta)

                selected_min_notional = self._to_float(selection_meta.get("selected_min_order_notional", 0.0), 0.0)
                selected_cfg = self.router.get_symbol_config(symbol) or {}
                selected_min_qty_effective = self._effective_min_order(
                    str(symbol or "").upper(),
                    self._to_float(selected_cfg.get("min_order", 0.0), 0.0),
                )
                selected_last_px = 0.0
                if isinstance(preloaded_ticker, dict):
                    selected_last_px = self._to_float(preloaded_ticker.get("last", 0.0), 0.0)
                if selected_last_px <= 0.0:
                    selected_live_ticker = self.router.get_ticker(symbol)
                    if isinstance(selected_live_ticker, dict):
                        preloaded_ticker = selected_live_ticker
                        selected_last_px = self._to_float(selected_live_ticker.get("last", 0.0), 0.0)
                selected_min_notional_effective = max(selected_min_qty_effective, 0.0) * max(selected_last_px, 0.0)
                if selected_min_notional_effective > 0.0:
                    selected_min_notional = max(selected_min_notional, selected_min_notional_effective)
                    selection_meta["selected_min_order_notional"] = round(float(selected_min_notional), 6)
                    selection_meta["selected_min_order_notional_effective"] = round(
                        float(selected_min_notional_effective),
                        6,
                    )

                unaffordable_by_balance = affordable_usd_hint > 0.0 and selected_min_notional > affordable_usd_hint
                unaffordable_by_cap = max_notional_usd_cap > 0.0 and selected_min_notional > max_notional_usd_cap
                if selected_min_notional > 0.0 and (unaffordable_by_balance or unaffordable_by_cap):
                    self.no_affordable_streak += 1
                    recycle_result: Optional[dict[str, Any]] = None
                    collateral_convert_result: Optional[dict[str, Any]] = None
                    if (
                        self.no_affordable_recycle_enabled
                        and self.no_affordable_streak >= int(self.no_affordable_recycle_streak_trigger)
                    ):
                        recycle_result = self._attempt_no_affordable_capital_recycle(loop_now)

                    if not (isinstance(recycle_result, dict) and bool(recycle_result.get("executed", False))):
                        collateral_convert_result = self._attempt_collateral_convert_for_liquidity(
                            loop_now,
                            reason="no_affordable_symbol",
                            required_usd=float(selected_min_notional),
                            preferred_symbol=str(symbol),
                        )

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
                    if isinstance(collateral_convert_result, dict):
                        blocked_payload["collateral_convert"] = collateral_convert_result
                    _write_live_heartbeat(blocked_payload)
                    if (
                        (isinstance(recycle_result, dict) and bool(recycle_result.get("executed", False)))
                        or (isinstance(collateral_convert_result, dict) and bool(collateral_convert_result.get("executed", False)))
                    ):
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
