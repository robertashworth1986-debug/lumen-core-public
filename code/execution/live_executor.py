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
from collections import deque

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
MIN_OPEN_POSITIONS_FLOOR = 1
LIVE_TRADE_LOG_FILE = OUT / "live_trade_log.json"
LIVE_SHADOW_LEDGER_FILE = OUT / "live_shadow_fills.csv"
LIVE_TRADE_LEDGER_CSV_FILE = OUT / "live_trade_ledger.csv"
LIVE_TRADE_LEDGER_JSONL_FILE = OUT / "live_trade_ledger.jsonl"
LIVE_AUDIT_CHAIN_FILE = OUT / "live_execution_audit_chain.jsonl"
LIVE_HEARTBEAT_FILE = OUT / "live_executor_heartbeat.json"
LIVE_HEARTBEAT_SCHEMA_VERSION = "1.0.0"
LIVE_EXECUTOR_LOCK_FILE = OUT / "live_executor.lock"
LIVE_PACING_STATE_FILE = OUT / "live_pacing_state.json"
SYMBOL_FLIP_INTEL_FILE = OUT / "symbol_flip_intel_top5.json"
SYMBOL_FLIP_LEARNING_FILE = OUT / "symbol_flip_learning_profile.json"
LIVE_OPERATOR_APPROVAL_QUEUE_FILE = OUT / "live_operator_approval_queue.json"
COLLATERAL_CONVERT_LOG_FILE = OUT / "collateral_convert_log.jsonl"
KRAKEN_NONCE_STATE_FILE = OUT / "kraken_nonce_state.json"
KRAKEN_BALANCE_CACHE_FILE = OUT / "kraken_balance_cache.json"
KRAKEN_ASSET_PAIRS_CACHE_FILE = OUT / "kraken_asset_pairs_cache.json"
CLEAN_OPS_ROSTER_LATEST_FILE = OUT / "clean_ops_roster_latest.json"
DEFAULT_QUOTE_LANES = ("USD", "USDT", "EUR")
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
    # High conviction → always market regardless of spread (avoid IOC limit failures)
    if edge_score >= 0.82:
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


def _process_commandline(pid: int) -> str:
    if int(pid or 0) <= 0:
        return ""
    try:
        probe = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"$p=Get-CimInstance Win32_Process -Filter \"ProcessId={int(pid)}\" -ErrorAction SilentlyContinue; if($p){{$p.CommandLine}}",
            ],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        return str(probe.stdout or "").strip()
    except Exception:
        return ""


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


def _is_duplicate_child_executor() -> tuple[bool, int]:
    """Detect recursive child launches of this script from a parent live executor.

    A healthy launch starts from shell/task runner and has no inherited root PID marker.
    If a child process is spawned by the active executor, it inherits the marker and this
    guard exits the child early to avoid lock/heartbeat races.
    """

    # Only block when: env marker is set AND the marked PID is our parent AND that parent
    # is actually still running live_executor.py (guards against PID recycling / stale markers).
    marker = str(os.environ.get("LUMA_LIVE_EXECUTOR_ROOT_PID", "") or "").strip()

    if not marker:
        return False, 0

    try:
        root_pid = int(marker)
    except Exception:
        return False, 0

    if root_pid <= 0:
        return False, 0

    pid = os.getpid()
    if root_pid == pid:
        return False, 0  # We are the root executor

    parent_pid = os.getppid()
    if parent_pid == root_pid:
        # Verify the parent is actually live_executor.py and not a recycled PID.
        root_cmd = _process_commandline(root_pid).replace("\\", "/").lower()
        if "code/execution/live_executor.py" in root_cmd:
            return True, int(root_pid)
    return False, 0


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
        self._open_order_locked_usd: float = 0.0   # USD locked in open limit buy orders
        self._asset_pairs_map: dict[str, dict[str, Any]] = {}
        self._asset_pairs_cache_utc = ""
        self._asset_pairs_cache_ttl_sec = 3600.0
        self._default_quote_order = list(DEFAULT_QUOTE_LANES)
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

    @staticmethod
    def _normalize_quote_symbol(quote_code: str) -> str:
        token = str(quote_code or "").upper().strip()
        if not token:
            return ""
        alias_map = {
            "ZUSD": "USD",
            "ZEUR": "EUR",
            "XUSDT": "USDT",
            "ZUSDT": "USDT",
        }
        return alias_map.get(token, token)

    @staticmethod
    def _quote_rank(quote: str, quote_order: list[str]) -> int:
        token = str(quote or "").upper().strip()
        try:
            return quote_order.index(token)
        except ValueError:
            return len(quote_order) + 1

    def _select_config_by_quote(
        self,
        cfg: dict[str, Any],
        quote_order: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        selected = dict(cfg)
        candidates = cfg.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            return selected

        order: list[str] = []
        for row in (quote_order or self._default_quote_order):
            token = self._normalize_quote_symbol(str(row))
            if token and token not in order:
                order.append(token)
        if not order:
            order = list(self._default_quote_order)

        ranked = sorted(
            [dict(c) for c in candidates if isinstance(c, dict)],
            key=lambda c: (
                self._quote_rank(str(c.get("quote", "USD")), order),
                float(self._to_float(c.get("min_order", 1e-8), 1e-8)),
                str(c.get("pair", "")),
            ),
        )
        if not ranked:
            return selected

        selected = dict(ranked[0])
        selected["candidates"] = ranked
        return selected

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

            allowed_quotes = {"USD", "USDT", "EUR"}
            candidates_by_symbol: dict[str, dict[str, dict[str, Any]]] = {}

            for _, row in result.items():
                if not isinstance(row, dict):
                    continue
                altname = str(row.get("altname", "") or "").upper().strip()
                wsname = str(row.get("wsname", "") or "").upper().strip()
                if not altname or not wsname or "/" not in wsname:
                    continue
                base, quote = wsname.split("/", 1)
                base = base.strip()
                quote = self._normalize_quote_symbol(quote.strip())
                if quote not in allowed_quotes:
                    continue

                min_order = self._to_float(row.get("ordermin", 0.0), 0.0)
                if min_order <= 0.0:
                    # Conservative fallback when ordermin is missing.
                    min_order = 1e-8

                cfg = {
                    "exchange": "kraken",
                    "pair": altname,
                    "min_order": max(float(min_order), 1e-8),
                    "base": base,
                    "quote": quote,
                    "pair_decimals": int(self._to_float(row.get("pair_decimals", 8), 8.0)),
                }

                symbol_keys = {base}
                if base == "XBT":
                    symbol_keys.add("BTC")
                elif base == "BTC":
                    symbol_keys.add("XBT")

                for symbol_key in symbol_keys:
                    per_symbol = candidates_by_symbol.setdefault(symbol_key, {})
                    per_symbol[altname] = dict(cfg)

            out: dict[str, dict[str, Any]] = {}
            for symbol_key, by_pair in candidates_by_symbol.items():
                rows = [dict(v) for v in by_pair.values() if isinstance(v, dict)]
                if not rows:
                    continue
                rows.sort(
                    key=lambda c: (
                        self._quote_rank(str(c.get("quote", "USD")), self._default_quote_order),
                        float(self._to_float(c.get("min_order", 1e-8), 1e-8)),
                        str(c.get("pair", "")),
                    )
                )
                chosen = dict(rows[0])
                chosen["candidates"] = rows
                out[symbol_key] = chosen
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

    def resolve_symbol_config(
        self,
        symbol: str,
        quote_order: Optional[list[str]] = None,
    ) -> Optional[dict[str, Any]]:
        key = str(symbol or "").upper().strip()
        if not key:
            return None
        pairs_map = self.get_asset_pairs_map()
        cfg = pairs_map.get(key)
        if cfg:
            return self._select_config_by_quote(cfg, quote_order=quote_order)
        if key == "XBT" and "BTC" in pairs_map:
            return self._select_config_by_quote(pairs_map["BTC"], quote_order=quote_order)
        if key == "BTC" and "XBT" in pairs_map:
            return self._select_config_by_quote(pairs_map["XBT"], quote_order=quote_order)
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
            # Subtract capital locked in open limit buy orders so sizing reflects
            # truly available balance (not total including locked-but-unfilled orders).
            locked = max(float(self._open_order_locked_usd or 0.0), 0.0)
            if locked > 0.0 and zusd > 0.0:
                balances["ZUSD"] = max(zusd - locked, 0.0)
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
        # Also include the canonical normalized form so that Kraken internal codes
        # (e.g. XXDG for XDG/DOGE) resolve correctly when the target is the
        # exchange-facing ticker rather than the canonical name.
        target_canonical = self._normalize_balance_asset(target)
        if target_canonical and target_canonical != target:
            aliases.add(target_canonical)

        balances = self.get_account_balances(force_refresh=force_refresh)
        if not balances:
            return 0.0

        total = 0.0
        for asset_code, qty in balances.items():
            normalized = self._normalize_balance_asset(asset_code)
            if normalized in aliases:
                total += max(self._to_float(qty, 0.0), 0.0)
        return float(max(total, 0.0))

    def get_open_orders(self, trades: bool = True) -> dict[str, Any]:
        if not self.api_key or not self.api_secret:
            return {"error": "missing kraken credentials"}

        try:
            payload = self._private("/0/private/OpenOrders", {"trades": bool(trades)})
        except Exception as e:
            return {"error": str(e)}

        if "error" in payload:
            return {"error": payload.get("error")}

        open_map = payload.get("open", {}) if isinstance(payload, dict) else {}
        if not isinstance(open_map, dict):
            return {"orders": [], "count": 0}

        orders: list[dict[str, Any]] = []
        for txid, row in open_map.items():
            if not isinstance(row, dict):
                continue
            descr = row.get("descr", {}) if isinstance(row.get("descr", {}), dict) else {}
            orders.append(
                {
                    "txid": str(txid),
                    "pair": str(descr.get("pair", "") or "").upper().strip(),
                    "type": str(descr.get("type", "") or "").lower().strip(),
                    "ordertype": str(descr.get("ordertype", "") or "").lower().strip(),
                    "status": str(row.get("status", "") or "").lower().strip(),
                    "vol": self._to_float(row.get("vol", 0.0), 0.0),
                    "vol_exec": self._to_float(row.get("vol_exec", 0.0), 0.0),
                    "price": self._to_float(descr.get("price", 0.0), 0.0),
                    "opentm": self._to_float(row.get("opentm", 0.0), 0.0),
                }
            )

        return {
            "orders": orders,
            "count": int(len(orders)),
        }

    def cancel_order(self, txid: str) -> dict[str, Any]:
        token = str(txid or "").strip()
        if not token:
            return {"error": "missing_txid"}
        if not self.api_key or not self.api_secret:
            return {"error": "missing kraken credentials"}

        try:
            payload = self._private("/0/private/CancelOrder", {"txid": token})
        except Exception as e:
            return {"error": str(e)}

        if "error" in payload:
            return {"error": payload.get("error")}

        out = dict(payload) if isinstance(payload, dict) else {"result": payload}
        out["txid"] = token
        return out

    def cancel_all_orders(self) -> dict[str, Any]:
        if not self.api_key or not self.api_secret:
            return {"error": "missing kraken credentials"}

        try:
            payload = self._private("/0/private/CancelAll", {})
        except Exception as e:
            return {"error": str(e)}

        if "error" in payload:
            return {"error": payload.get("error")}

        return dict(payload) if isinstance(payload, dict) else {"result": payload}

    def send_order(
        self,
        pair: str,
        side: str,
        qty: float,
        price: float = None,
        order_type: str = "limit",
        close_template: Optional[dict[str, Any]] = None,
        pair_decimals: Optional[int] = None,
    ) -> dict:
        if not self.api_key or not self.api_secret:
            return {"error": "missing kraken credentials"}

        def _fmt_price(raw: float) -> str:
            decimals = 8
            if pair_decimals is not None:
                try:
                    decimals = int(pair_decimals)
                except Exception:
                    decimals = 8
            decimals = max(min(decimals, 10), 0)
            return f"{round(float(raw), decimals):.{decimals}f}"

        data = {
            "pair": pair,
            "type": side.lower(),
            "ordertype": "limit" if order_type == "limit" else "market",
            "volume": f"{qty:.8f}",
        }
        if order_type == "limit" and price is not None:
            data["price"] = _fmt_price(float(price))

        if isinstance(close_template, dict):
            # Prefer protective stop close first; fallback to take-profit when stop is unavailable.
            tp_leg = close_template.get("take_profit")
            stop_leg = close_template.get("stop")
            selected_leg = stop_leg if isinstance(stop_leg, dict) else tp_leg if isinstance(tp_leg, dict) else None
            if isinstance(selected_leg, dict):
                close_ordertype = str(selected_leg.get("order_type", "")).strip().lower()
                close_price = self._to_float(selected_leg.get("trigger_price", 0.0), 0.0)
                if close_ordertype in {
                    "stop-loss",
                    "stop-loss-limit",
                    "take-profit",
                    "take-profit-limit",
                } and close_price > 0.0:
                    data["close[ordertype]"] = close_ordertype
                    data["close[price]"] = _fmt_price(float(close_price))

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

            def _series_value(field: str, idx: int = 1) -> float:
                raw = t.get(field, [])
                if isinstance(raw, (list, tuple)):
                    if len(raw) > idx:
                        return float(raw[idx] or 0.0)
                    if raw:
                        return float(raw[-1] or 0.0)
                    return 0.0
                return float(raw or 0.0)

            return {
                "bid": float(t["b"][0]),
                "ask": float(t["a"][0]),
                "bid_qty": float(t["b"][1]) if len(t.get("b", [])) > 1 else 0.0,
                "ask_qty": float(t["a"][1]) if len(t.get("a", [])) > 1 else 0.0,
                "last": float(t["c"][0]),
                "last_trade_qty": float(t["c"][1]) if len(t.get("c", [])) > 1 else 0.0,
                "open": float(t.get("o", t["c"][0]) or 0.0),
                "high_24h": _series_value("h", 1),
                "low_24h": _series_value("l", 1),
                "volume_24h": _series_value("v", 1),
                "vwap_24h": _series_value("p", 1),
                "trade_count_24h": int(_series_value("t", 1)),
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

    @staticmethod
    def _runtime_quote_order() -> list[str]:
        runtime = load_json(RUNTIME_CONTROL_FILE, {})
        raw = runtime.get("clean_ops_quote_allow", list(DEFAULT_QUOTE_LANES)) if isinstance(runtime, dict) else list(DEFAULT_QUOTE_LANES)
        rows: list[Any]
        if isinstance(raw, str):
            rows = [r.strip() for r in raw.split(",")]
        elif isinstance(raw, (list, tuple, set)):
            rows = list(raw)
        else:
            rows = list(DEFAULT_QUOTE_LANES)

        out: list[str] = []
        for row in rows:
            token = KrakenClient._normalize_quote_symbol(str(row))
            if token and token not in out:
                out.append(token)
        if not out:
            out = list(DEFAULT_QUOTE_LANES)
        return out

    @staticmethod
    def _quote_balance_from_snapshot(snapshot: dict[str, float], quote: str) -> float:
        if not isinstance(snapshot, dict):
            return 0.0
        token = KrakenClient._normalize_quote_symbol(str(quote or ""))
        key_map = {
            "USD": ("ZUSD", "USD"),
            "USDT": ("USDT", "XUSDT", "ZUSDT"),
            "EUR": ("ZEUR", "EUR"),
        }
        keys = key_map.get(token, (token,))
        total = 0.0
        for key in keys:
            try:
                total += max(float(snapshot.get(key, 0.0) or 0.0), 0.0)
            except Exception:
                continue
        return float(max(total, 0.0))

    def _select_order_cfg_for_execution(self, symbol: str, side: str) -> Optional[dict[str, Any]]:
        quote_order = self._runtime_quote_order()
        cfg = self.get_symbol_config(symbol, quote_order=quote_order)
        if not cfg:
            return None

        candidates = cfg.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            return cfg

        ranked = sorted(
            [dict(c) for c in candidates if isinstance(c, dict)],
            key=lambda c: (
                KrakenClient._quote_rank(str(c.get("quote", "USD")), quote_order),
                float(c.get("min_order", 1e-8) or 1e-8),
                str(c.get("pair", "")),
            ),
        )
        if not ranked:
            return cfg

        if str(side or "buy").lower() != "buy":
            out = dict(ranked[0])
            out["candidates"] = ranked
            return out

        balances = self.kraken.get_account_balances(force_refresh=False)
        for cand in ranked:
            quote = str(cand.get("quote", "USD") or "USD")
            quote_balance = self._quote_balance_from_snapshot(balances, quote)
            if quote_balance <= 0.0:
                continue

            ticker = self.kraken.get_ticker(str(cand.get("pair", "")))
            last_px = 0.0
            if isinstance(ticker, dict):
                last_px = max(float(ticker.get("last", 0.0) or 0.0), 0.0)
            min_notional_quote = max(float(cand.get("min_order", 0.0) or 0.0), 0.0) * max(last_px, 0.0)
            if min_notional_quote <= 0.0 or quote_balance + 1e-9 >= min_notional_quote:
                out = dict(cand)
                out["candidates"] = ranked
                out["quote_balance_hint"] = round(float(quote_balance), 8)
                return out

        out = dict(ranked[0])
        out["candidates"] = ranked
        return out

    def get_symbol_config(self, symbol: str, quote_order: Optional[list[str]] = None):
        key = str(symbol or "").upper().strip()
        if not key:
            return None
        static_cfg = SYMBOL_REGISTRY.get(key)
        dynamic_cfg = self.kraken.resolve_symbol_config(key, quote_order=quote_order)

        if static_cfg:
            merged = dict(static_cfg)
            if isinstance(dynamic_cfg, dict):
                if "pair_decimals" in dynamic_cfg and "pair_decimals" not in merged:
                    merged["pair_decimals"] = int(self.kraken._to_float(dynamic_cfg.get("pair_decimals", 8), 8.0))
                if "base" in dynamic_cfg and "base" not in merged:
                    merged["base"] = dynamic_cfg.get("base")
                if "quote" in dynamic_cfg and "quote" not in merged:
                    merged["quote"] = dynamic_cfg.get("quote")
                if "candidates" in dynamic_cfg and "candidates" not in merged:
                    merged["candidates"] = dynamic_cfg.get("candidates")
            return merged

        return dynamic_cfg

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

        try:
            cap = int(float(max_symbols))
        except Exception:
            cap = 0

        # Explicit runtime convention: cap <= 0 means "scan all available symbols".
        if cap <= 0 or len(tradable) <= cap:
            return tradable
        return random.sample(tradable, cap)

    def get_ticker(self, symbol: str, quote_order: Optional[list[str]] = None):
        cfg = self.get_symbol_config(symbol, quote_order=quote_order)
        if not cfg:
            return None
        return self.kraken.get_ticker(cfg["pair"])

    def get_balance(self, force_refresh: bool = False):
        return self.kraken.get_account_balance(force_refresh=force_refresh)

    def get_asset_balance(self, symbol: str, force_refresh: bool = False):
        return self.kraken.get_asset_balance(symbol, force_refresh=force_refresh)

    def get_balance_snapshot(self, force_refresh: bool = False):
        return self.kraken.get_account_balances(force_refresh=force_refresh)

    def get_open_orders(self, trades: bool = True):
        return self.kraken.get_open_orders(trades=trades)

    def cancel_order(self, txid: str):
        return self.kraken.cancel_order(txid)

    def cancel_all_orders(self):
        return self.kraken.cancel_all_orders()

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        limit_price: float = None,
        close_template: Optional[dict[str, Any]] = None,
    ):
        runtime = load_json(RUNTIME_CONTROL_FILE, {})
        runtime_mode = str(runtime.get("mode", "paper") or "paper").strip().lower()
        allow_live_orders = bool(runtime.get("allow_live_orders", False))
        kill_switch = bool(runtime.get("kill_switch", False))

        if runtime_mode != "live" or (not allow_live_orders) or kill_switch:
            return {
                "error": "live_orders_disabled",
                "runtime_mode": runtime_mode,
                "allow_live_orders": bool(allow_live_orders),
                "kill_switch": bool(kill_switch),
            }

        cfg = self._select_order_cfg_for_execution(symbol, side)
        if not cfg:
            return {"error": f"unknown symbol {symbol}"}

        result = self.kraken.send_order(
            cfg["pair"],
            side,
            qty,
            limit_price,
            "limit" if limit_price else "market",
            close_template=close_template,
            pair_decimals=cfg.get("pair_decimals"),
        )
        if isinstance(result, dict) and "error" not in result:
            result["_router_pair"] = str(cfg.get("pair", ""))
            result["_router_quote"] = str(cfg.get("quote", "USD") or "USD")
            result["_router_min_order"] = float(cfg.get("min_order", 0.0) or 0.0)
        return result


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
        self.hybrid_swing_selector_enabled = True
        self.hybrid_swing_min_range_pct = 0.25
        self.hybrid_swing_min_momentum_pct = -0.75
        self.hybrid_swing_spread_guard_bps = 85.0
        self.hybrid_swing_range_weight = 1.25
        self.hybrid_swing_momentum_weight = 1.0
        self.hybrid_swing_position_weight = 0.75
        self.hybrid_swing_activity_weight = 0.15
        self.hybrid_swing_spread_penalty = 0.18
        self.hybrid_swing_max_entry_range_position = 0.65  # hard cap: don't buy in top 35% of 24h range
        self.hybrid_swing_whitelist_relax_enabled = True
        self.hybrid_swing_min_candidates = 64
        self.hybrid_swing_relax_cap = 240
        self.hybrid_swing_long_bias_enabled = True
        self.hybrid_swing_long_bias_min_momentum_pct = 0.05
        self.hybrid_swing_long_bias_penalty_per_pct = 18.0
        # ── INSTITUTIONAL SWING HUNTER / TRAILING STOP ENGINE ────────────────
        self.trailing_stop_enabled = True
        self.trailing_stop_activation_bps = 80.0    # arm trail once peak gain >= this (bps)
        self.trailing_stop_trail_bps = 40.0         # trail this many bps below peak (locks in profit)
        self.trailing_stop_dynamic_scaling = True   # widen activation on high-amplitude assets
        self.trailing_stop_dynamic_multiplier = 0.08  # activation_bps += amplitude_pct * mult * 100
        self._position_peaks: dict[str, float] = {}   # pos_key -> best price seen while position open
        self._alpha_score_cache: dict[str, float] = {}  # symbol -> alpha_long_score from intel file
        self._alpha_score_cache_mtime: float = 0.0      # file mtime when cache was last loaded
        # ─────────────────────────────────────────────────────────────────────
        # ── Velocity Reversal Exit ────────────────────────────────────────────
        self._position_prev_price: dict[str, float] = {}  # pos_key -> price at start of last cycle
        self.trailing_stop_vel_exit_enabled = True         # fast exit when momentum reverses sharply
        self.trailing_stop_vel_exit_threshold_pct = 0.30  # single-cycle drop >= this triggers exit
        # ── VWAP Entry Filter ─────────────────────────────────────────────────
        self.hybrid_swing_vwap_filter_enabled = True
        self.hybrid_swing_vwap_max_deviation_pct = 2.0    # only enter within 2% above VWAP
        # ── Quarter-Kelly Position Sizing ─────────────────────────────────────
        self.kelly_sizing_enabled = True
        self.kelly_fraction = 0.25                        # 25% Kelly (quarter-Kelly)
        self.kelly_min_sample_trades = 6                  # min confirmed trades before sizing boost
        # ── Order Book Imbalance (OBI) Entry Filter ────────────────────────────
        self.hybrid_swing_obi_filter_enabled = True       # require net buy pressure to enter
        self.hybrid_swing_min_obi = 0.0                   # minimum OBI score (0 = any net bid pressure)
        self.hybrid_swing_obi_weight = 1.0                # OBI contribution multiplier in hybrid score
        # ── Volume Conviction Score ────────────────────────────────────────────
        self.hybrid_swing_conviction_weight = 1.0         # conviction score multiplier in hybrid score
        # ── Break-Even Ratchet ─────────────────────────────────────────────────
        self.trailing_stop_breakeven_enabled = True        # floor trailing stop to entry once ratchet fires
        self.trailing_stop_breakeven_ratchet_mult = 1.5   # peak gain must be >= activation × mult to ratchet
        # ── Market Regime Filter ───────────────────────────────────────────────
        self.hybrid_swing_regime_filter_enabled = True       # block entries in confirmed bear regime
        self.hybrid_swing_regime_bear_momentum_pct = -1.0    # 24h momentum below this = bear regime
        self.hybrid_swing_regime_bull_bonus = 5.0            # extra hybrid_score pts in confirmed bull regime
        # ── Adaptive Post-Loss Cooldown ────────────────────────────────────────
        self.adaptive_loss_cooldown_enabled = True          # scale up reentry cooldown on loss
        self.adaptive_loss_cooldown_scale = 10.0            # loss_pct (decimal) * scale added to base multiplier
        self.adaptive_loss_cooldown_cap_sec = 1800.0        # max cooldown cap (30 min)
        # ── Innovation 12: Session-Level Symbol Win-Rate Filter ────────────────
        # Track consecutive wins/losses per symbol in this session.
        # Consistent losers get escalating cooldown; hot streaks get priority.
        self.session_loss_streak_threshold = 3       # losses in a row → extended cooldown
        self.session_loss_streak_cooldown_sec = 900.0  # 15 min extended cooldown per streak hit
        self.session_loss_hard_block_threshold = 5   # 5 consecutive losses → session block
        self.session_win_streak_threshold = 3        # wins in a row → symbol flagged as hot
        self._session_symbol_consecutive_wins: dict[str, int] = {}   # symbol → consecutive win count
        self._session_symbol_consecutive_losses: dict[str, int] = {} # symbol → consecutive loss count
        self._session_hot_symbols: set = set()       # symbols on win streak this session
        # ─────────────────────────────────────────────────────────────────────
        # ── Innovation 14: Age-Pressure TP Ladder ─────────────────────────────
        # Converts flat-timeout trades into micro-wins by lowering the TP bar as
        # hold time approaches max_hold_sec.  At 70% hold: exit if PnL >= 5 bps.
        # At 85% hold: exit with any positive PnL.  Reclaims capital faster than
        # waiting for a full timeout at near-zero.
        self.age_pressure_tp_enabled = True
        self.age_pressure_tp_early_pct = 0.70    # 70% of max_hold → early gate activates
        self.age_pressure_tp_early_min_bps = 5.0 # early gate: exit if PnL >= this (bps)
        self.age_pressure_tp_late_pct  = 0.85    # 85% of max_hold → late gate: any gain exits
        # ─────────────────────────────────────────────────────────────────────
        # ── Innovation 15: Age-Pressure SL Tightener ────────────────────────
        # Mirror of Inn14: as a losing position ages, dynamically tighten the SL
        # so it exits before timeout eats the full loss.
        # At 50% of max_hold: SL narrows to sl_mid_fraction × sl_bps.
        # At 75% of max_hold: SL narrows to sl_late_fraction × sl_bps.
        # Example at sl=55bps: 50%→33bps gate, 75%→19bps gate.
        self.age_pressure_sl_enabled = True
        self.age_pressure_sl_mid_pct = 0.50       # 50% of max_hold → mid-gate activates
        self.age_pressure_sl_mid_fraction = 0.60  # mid-gate: SL = 60% of original (~33 bps)
        self.age_pressure_sl_late_pct = 0.75      # 75% of max_hold → late-gate activates
        self.age_pressure_sl_late_fraction = 0.35 # late-gate: SL = 35% of original (~19 bps)
        # ─────────────────────────────────────────────────────────────────────

        # ── Innovation 16: Flat-Exit Reentry Dampener ─────────────────────────
        # After a dead_weight_purge OR any exit where |pnl| < flat_exit_dampener_min_bps,
        # apply an extended symbol skip to prevent repeatedly entering frozen symbols.
        # A "flat exit" means zero alpha was generated — the symbol should rest longer.
        self.flat_exit_dampener_enabled = True
        self.flat_exit_dampener_min_bps = 5.0        # |pnl| below this → counted as flat
        self.flat_exit_dampener_cooldown_sec = 900.0  # 15-min skip after flat close
        # ─────────────────────────────────────────────────────────────────────

        # ── Innovation 17: Flat-Cluster Regime Pause ──────────────────────────
        # When the recent N closes are dominated by flat/zero-alpha exits,
        # the market is in a low-alpha regime.  Pause ALL new entries for
        # cluster_flat_pause_sec seconds to avoid burning more capital.
        # "Flat close" = |pnl_pct| < cluster_flat_max_bps.
        self.cluster_flat_pause_enabled = True
        self.cluster_flat_recent_n = 6          # sliding window of last N closes
        self.cluster_flat_threshold_frac = 0.67 # 4/6 flat → regime pause
        self.cluster_flat_max_bps = 10.0        # flat = |pnl| < 10 bps
        self.cluster_flat_pause_sec = 240.0     # 4-min global entry pause
        self._recent_close_pnl_abs_bps: deque = deque(maxlen=6)  # rolling |pnl| in bps
        # ─────────────────────────────────────────────────────────────────────

        # ── Innovation 18: Dead-Weight Strike Escalator ───────────────────────
        # Each time the SAME symbol is dead_weight_purged again, escalate the
        # re-entry cooldown exponentially: 2nd purge = 30 min, 3rd = 1 hour,
        # 4th+ = capped at 4 hours.  Strike 1 is already handled by Inn16 (900s).
        self.dw_strike_escalator_enabled = True
        self.dw_strike_escalator_base_sec = 900.0    # base (Inn16 level; escalation starts at 2x)
        self.dw_strike_escalator_multiplier = 2.0    # doubles each additional strike
        self.dw_strike_escalator_max_sec = 14400.0   # cap at 4 hours
        self._dw_strike_count: dict[str, int] = {}   # symbol → cumulative dead_weight count
        # ─────────────────────────────────────────────────────────────────────

        # ── Innovation 19: Moonshot Size Amplifier ────────────────────────────
        # When a symbol is on the live moonshot watchlist AND the gate score is
        # strong, boost the effective notional cap so we ride BADGER/PORTAL-class
        # pumps with more firepower.  Watchlist is refreshed every 5 minutes from
        # out/ops/moonshot_watchlist.json (written by SCAN_MOONSHOT_UNIVERSE.py).
        self.moonshot_amplifier_enabled = True
        self.moonshot_amplifier_min_gate_score = 0.85   # only boost high-conviction entries
        self.moonshot_amplifier_multiplier = 1.60        # 60% more size on watchlist symbols
        self.moonshot_amplifier_max_cap_pct = 0.42       # hard cap: never >42% of available cash
        self.moonshot_watchlist_path = "out/ops/moonshot_watchlist.json"
        self._moonshot_watchlist_cache: list = []
        self._moonshot_watchlist_cache_ts: float = 0.0
        self._moonshot_watchlist_cache_ttl: float = 300.0  # refresh every 5 minutes
        # ─────────────────────────────────────────────────────────────────────
        # Innovation 20: Throttle Reset Command + Preferred Symbol Fast Lane
        self.fail_streak_reset_nonce: int = 0             # bump in config to reset throttle
        self._last_fail_streak_reset_nonce: int = 0       # tracks last applied nonce
        self.preferred_symbol_fast_lane_enabled: bool = True  # force preferred into candidates
        self.preferred_symbol_fast_lane_min_alpha: float = 0.0  # min alpha score to force (0=always)
        # Innovation 21: Equity-Scaled Compounding Cap
        self.inn21_equity_scale_enabled: bool = True       # auto-scale position cap with equity
        self.inn21_equity_scale_pct: float = 0.085         # position = 8.5% of equity
        self.inn21_equity_scale_min_cap: float = 12.0      # floor cap (USD)
        self.inn21_equity_scale_hard_max: float = 5000.0   # ceiling cap (USD)
        # Innovation 22: Moonshot Long-Hold TP Amplifier
        self.inn22_moonshot_tp_enabled: bool = True         # widen TP/hold for watchlist symbols
        self.inn22_moonshot_tp_bps: float = 500.0           # 5% TP for moonshot symbols
        self.inn22_moonshot_max_hold_sec: float = 14400.0   # 4-hour max hold for moonshots
        self.inn22_moonshot_trail_activation_bps: float = 250.0  # 2.5% before trail arms
        self.inn22_moonshot_trail_bps: float = 60.0         # 0.6% trail for moonshots
        # ─────────────────────────────────────────────────────────────────────

        # ══════════════════════════════════════════════════════════════════════
        # SELL LOGIC INNOVATIONS  (10-feature suite)
        # ══════════════════════════════════════════════════════════════════════

        # Innovation 1: Profit Lock ────────────────────────────────────────────
        # Immediately close the position the instant PnL hits a hard profit target.
        # Overrides trailing-stop logic so gains are guaranteed.
        self.profit_lock_enabled = True
        self.profit_lock_pct = 0.08            # close instantly at +8% PnL

        # Innovation 2: Dead-Weight Purge ─────────────────────────────────────
        # Positions that have been open too long without meaningful price movement
        # are tying up heat uselessly.  Exit them to free capital.
        self.dead_weight_purge_enabled = True
        self.dead_weight_max_age_sec = 1800.0  # 30 min stale hold triggers purge
        self.dead_weight_max_drift_pct = 0.005 # must have moved < 0.5% (either way)

        # Innovation 3: Age-Tightened Trailing Stop ───────────────────────────
        # The longer we hold, the tighter the trail becomes.  Prevents giving back
        # hard-earned gains on slow, aging positions.
        self.age_trail_tighten_enabled = True
        self.age_trail_tighten_start_sec = 120.0  # begin tightening after 2 min
        self.age_trail_tighten_rate = 0.005        # subtract 0.5% from trail per extra 60 sec of hold

        # Innovation 4: Cascade Loss Guard ────────────────────────────────────
        # When multiple positions are simultaneously underwater, exit the worst one
        # before losses compound portfolio-wide.
        self.cascade_guard_enabled = True
        self.cascade_guard_min_positions = 3   # need >= 3 positions simultaneously underwater
        self.cascade_guard_threshold_pct = 0.02  # positions must be down >= 2%

        # Innovation 5: Short-Signal Force Exit Timer ─────────────────────────
        # If the executor has been holding a bearish-flagged position (short_signal_forced_long)
        # for > N seconds, force close the largest such position regardless of PnL.
        self.short_signal_force_exit_enabled = True
        self.short_signal_force_exit_sec = 600.0  # 10 min of bearish pressure = forced exit
        self._short_signal_flagged_since_utc: dict[str, str] = {}  # pos_key -> first_flagged_utc

        # Innovation 6: Velocity Reversal on Small Loss ───────────────────────
        # Extend velocity-reversal exits to positions that are at a small loss AND
        # price is dropping sharply — don't wait for stop-loss; cut early.
        self.vel_exit_on_loss_enabled = True
        self.vel_exit_on_loss_max_pnl_pct = -0.005   # fires when PnL <= -0.5%
        self.vel_exit_on_loss_vel_threshold_pct = 0.50  # price must drop >= 0.5% in one cycle

        # Innovation 7: Conviction-Tiered Take-Profit ─────────────────────────
        # Positions entered with a lower gate score exit sooner (tighter TP).
        # High-conviction positions (strong gate score) are allowed to run further.
        self.conviction_tiered_tp_enabled = True
        self.conviction_tiered_tp_low_score = 0.65     # gate scores below this get tighter TP
        self.conviction_tiered_tp_low_tp_pct = 0.004   # low-conviction TP: +0.4%

        # Innovation 8: Moonshot Slot Reserve ────────────────────────────────
        # When a preferred symbol is queued and has been blocked by heat for
        # >= N seconds, lower the exit threshold for the LOWEST-alpha current position
        # so it exits faster and frees the slot.
        self.moonshot_slot_reserve_enabled = True
        self.moonshot_slot_reserve_blocked_sec = 120.0   # position has been heat-blocked for 2+ min
        self.moonshot_slot_reserve_tp_override_pct = 0.002  # exit lowest-alpha at +0.2% to free slot
        self._heat_blocked_since_utc: str = ""  # tracks when heat-block started

        # Innovation 9: PnL Drawdown Accelerator ─────────────────────────────
        # When position PnL drops from its intra-position peak by more than X%,
        # close immediately even if trailing stop hasn't fired yet.
        self.pnl_drawdown_accel_enabled = True
        self.pnl_drawdown_accel_peak_drop_pct = 0.035   # exit if PnL drops 3.5% from its peak

        # Innovation 10: Heat-Triggered Capital Recycle ───────────────────────
        # THE KEY INNOVATION: when the buy is blocked by heat AND a preferred symbol
        # is queued, score all open positions and exit the weakest one to free heat.
        # Runs directly in the main cycle when risk check fails with heat reason.
        self.heat_recycle_enabled = True
        self.heat_recycle_min_hold_sec = 60.0     # don't recycle a position we just entered (1 min min)
        self.heat_recycle_cooldown_sec = 45.0      # wait 45s between heat-recycle sells
        self._heat_recycle_last_utc: str = ""      # last time heat-recycle fired
        self._phantom_skip_symbols: dict = {}      # symbol → UTC when phantom-flagged (skip re-inject for 300s)
        # ══════════════════════════════════════════════════════════════════════
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
        self.collateral_convert_avoid_open_positions = True
        self.collateral_convert_protect_open_positions_sec = 180.0
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
        self.stale_buy_order_ttl_sec = 60.0            # cancel limit buys unfilled after 60s (IOC should cancel immediately)
        self._last_stale_order_cleanup_utc: Optional[str] = None  # ISO str of last sweep
        self.stale_order_cleanup_interval_sec = 300.0  # periodic sweep every 5 min
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
        self.live_operator_queue_enabled = True
        self.live_operator_queue_max_candidates = 6
        self.allow_best_multi_preference = False
        self.symbol_intel_enabled = True
        self.symbol_intel_prefer_top_n = 5
        self.symbol_intel_max_age_sec = 1200.0
        self.symbol_intel_min_alpha_score = 1.5
        self.symbol_intel_learning_enabled = True
        self.symbol_intel_learning_weight = 0.30
        self.symbol_intel_learning_max_bonus = 18.0
        self.symbol_intel_learning_max_age_sec = 21600.0
        self.edge_proof_enabled = True
        self.edge_proof_recent_closed_trades = 6
        self.edge_proof_min_win_rate_pct = 52.0
        self.edge_proof_min_avg_pnl_pct = 0.05
        self.edge_proof_max_last_close_age_min = 360.0
        self.edge_proof_require_symbol_intel_fresh = True
        self.edge_proof_hybrid_fallback_for_symbol_intel = True
        self.edge_proof_bootstrap_enabled = True
        self.edge_proof_bootstrap_max_entries_per_hour = 1
        self.edge_proof_bootstrap_min_gate_score = 0.74
        self.edge_proof_bootstrap_min_expected_edge_bps = 24.0
        self.edge_proof_bootstrap_min_hybrid_score = 14.0
        self.edge_proof_bootstrap_min_momentum_pct = 0.20
        self.edge_proof_bootstrap_max_spread_bps = 14.0
        self.edge_proof_bootstrap_hybrid_edge_scale = 0.35
        self.edge_proof_bootstrap_require_hybrid_candidates = False
        self.edge_proof_cost_floor_enabled = True
        self.edge_proof_cost_floor_fee_roundtrip_bps = 52.0
        self.edge_proof_cost_floor_spread_weight = 1.0
        self.edge_proof_cost_floor_slippage_roundtrip_bps = 10.0
        self.edge_proof_cost_floor_buffer_bps = 25.0
        self.edge_proof_cost_floor_min_bps = 60.0
        self.edge_proof_cost_floor_max_bps = 300.0
        self.edge_proof_cost_floor_adaptive_enabled = True
        self.edge_proof_cost_floor_adaptive_min_closed_trades = 6
        self.edge_proof_cost_floor_adaptive_loss_threshold_bps = -8.0
        self.edge_proof_cost_floor_adaptive_gain_threshold_bps = 18.0
        self.edge_proof_cost_floor_adaptive_loss_adjust_bps = 20.0
        self.edge_proof_cost_floor_adaptive_gain_adjust_bps = 10.0
        self.edge_proof_cost_floor_adaptive_win_rate_floor_pct = 42.0
        self.edge_proof_cost_floor_adaptive_win_rate_relax_pct = 62.0
        self.alpha_lock_enabled = True
        self.alpha_lock_min_gate_score = 0.60
        self.alpha_lock_min_expected_edge_bps = 20.0
        self.alpha_lock_min_score = 4.5
        self.alpha_lock_learning_bonus_weight = 0.35
        self.alpha_lock_hybrid_score_weight = 1.0
        self.alpha_lock_allow_hybrid_fallback = True
        self.alpha_lock_allow_gate_only_fallback = False
        self.edge_proof_cache_ttl_sec = 8.0
        self._edge_proof_cache: dict[str, Any] = {}
        self._edge_proof_cache_utc = 0.0
        self.allow_min_order_cap_breach = True
        self.auto_convert_stable_for_quote = True
        self.stable_convert_allowlist: set[str] = set()
        self.stable_convert_denylist: set[str] = set()
        self.hard_safety_only_mode = False
        self.max_trap_rate_pct = 48.0
        self._trap_rate_cache: dict[str, float] = {}
        self._trap_rate_cache_utc = 0.0
        self._trap_rate_cache_ttl_sec = 300.0
        self._symbol_intel_cache: dict[str, Any] = {}
        self._symbol_intel_cache_utc = 0.0
        self._symbol_learning_cache: dict[str, Any] = {}
        self._symbol_learning_cache_utc = 0.0
        self.same_symbol_reentry_cooldown_sec = 90.0
        self.last_entry_symbol = ""
        self.last_entry_time_utc = ""
        self.last_selected_symbol = ""
        self.low_balance_rotation_cursor = 0
        self.symbol_skip_cooldown_sec = 12.0
        self.missing_ticker_skip_cooldown_sec = 120.0
        self.spread_too_wide_skip_cooldown_sec = 90.0
        self.universe_hard_reject_spread_bps = 120.0
        self.preferred_symbol_max_spread_bps = 35.0
        self._symbol_skip_until_utc: dict[str, datetime] = {}
        self._symbol_skip_reasons: dict[str, str] = {}
        self.edge_proof_bootstrap_entry_utc: list[datetime] = []
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
        self.global_close_sweep_enabled = True
        self.global_close_sweep_max_symbols = 12
        self.global_close_sweep_interval_sec = 20.0
        self.last_global_close_sweep_utc = ""
        self.auto_trip_kill_switch_on_inventory_discrepancy = True
        self.auto_kill_switch_trip_cooldown_sec = 300.0
        self.auto_kill_switch_last_trip_utc = ""

        self.profit_reinvestment_enabled = True
        self.order_notional_pct = 0.24
        self.max_deployable_capital_pct = 0.70
        self.max_drawdown_pct_limit = 10.0
        self.compounding_growth_sensitivity = 0.75
        self.compounding_boost_ceiling = 1.80
        self.compounding_min_notional_usd = 0.50
        self.compounding_max_notional_usd = 25000.0

        self.capital_preservation_mode = True
        self.capital_preservation_min_recent_closed = 4
        self.capital_preservation_min_win_rate_pct = 42.0
        self.capital_preservation_min_avg_pnl_pct = 0.0
        self.capital_preservation_max_consecutive_losses = 3
        self.capital_preservation_pause_sec = 900.0
        self.capital_preservation_pause_until_utc = ""

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
        self._load_pacing_state()

    def _load_pacing_state(self) -> None:
        payload = load_json(LIVE_PACING_STATE_FILE, {})
        if not isinstance(payload, dict):
            return

        def _parse_dt(raw: Any) -> Optional[datetime]:
            try:
                return self._parse_iso_utc(str(raw))
            except Exception:
                return None

        entry_rows = payload.get("entry_timestamps_utc", [])
        loaded_entries: list[datetime] = []
        if isinstance(entry_rows, list):
            for raw in entry_rows:
                parsed = _parse_dt(raw)
                if isinstance(parsed, datetime):
                    loaded_entries.append(parsed)
        self.entry_timestamps_utc = loaded_entries[-4096:]

        symbol_rows = payload.get("symbol_entry_timestamps_utc", {})
        loaded_symbol_entries: dict[str, list[datetime]] = {}
        if isinstance(symbol_rows, dict):
            for key, values in symbol_rows.items():
                symbol = str(key or "").upper().strip()
                if not symbol or not isinstance(values, list):
                    continue
                parsed_rows: list[datetime] = []
                for raw in values:
                    parsed = _parse_dt(raw)
                    if isinstance(parsed, datetime):
                        parsed_rows.append(parsed)
                if parsed_rows:
                    loaded_symbol_entries[symbol] = parsed_rows[-1024:]
        self.symbol_entry_timestamps_utc = loaded_symbol_entries

        history_rows = payload.get("entry_symbol_history", [])
        loaded_history: list[tuple[datetime, str]] = []
        if isinstance(history_rows, list):
            for row in history_rows:
                if not isinstance(row, dict):
                    continue
                parsed = _parse_dt(row.get("ts"))
                symbol = str(row.get("symbol", "") or "").upper().strip()
                if isinstance(parsed, datetime) and symbol:
                    loaded_history.append((parsed, symbol))
        self.entry_symbol_history = loaded_history[-4096:]

        skip_rows = payload.get("symbol_skip_until_utc", {})
        loaded_skip: dict[str, datetime] = {}
        if isinstance(skip_rows, dict):
            for key, raw_until in skip_rows.items():
                symbol = str(key or "").upper().strip()
                parsed = _parse_dt(raw_until)
                if symbol and isinstance(parsed, datetime):
                    loaded_skip[symbol] = parsed
        self._symbol_skip_until_utc = loaded_skip

        skip_reason_rows = payload.get("symbol_skip_reasons", {})
        loaded_skip_reasons: dict[str, str] = {}
        if isinstance(skip_reason_rows, dict):
            for key, reason in skip_reason_rows.items():
                symbol = str(key or "").upper().strip()
                if symbol:
                    loaded_skip_reasons[symbol] = str(reason or "symbol_skip")
        self._symbol_skip_reasons = loaded_skip_reasons

        bootstrap_rows = payload.get("edge_proof_bootstrap_entry_utc", [])
        loaded_bootstrap: list[datetime] = []
        if isinstance(bootstrap_rows, list):
            for raw in bootstrap_rows:
                parsed = _parse_dt(raw)
                if isinstance(parsed, datetime):
                    loaded_bootstrap.append(parsed)
        self.edge_proof_bootstrap_entry_utc = loaded_bootstrap[-1024:]

        self.last_entry_symbol = str(payload.get("last_entry_symbol", self.last_entry_symbol) or "").upper().strip()
        self.last_entry_time_utc = str(payload.get("last_entry_time_utc", self.last_entry_time_utc) or "").strip()
        self.last_global_close_sweep_utc = str(
            payload.get("last_global_close_sweep_utc", self.last_global_close_sweep_utc) or ""
        ).strip()
        pause_until = _parse_dt(payload.get("capital_preservation_pause_until_utc"))
        if isinstance(pause_until, datetime):
            self.capital_preservation_pause_until_utc = pause_until.isoformat()

        try:
            self._prune_symbol_skip_map(datetime.now(timezone.utc))
        except Exception:
            pass

    def _save_pacing_state(self) -> None:
        try:
            symbol_entry_rows = {
                str(symbol): [ts.isoformat() for ts in values[-1024:] if isinstance(ts, datetime)]
                for symbol, values in self.symbol_entry_timestamps_utc.items()
                if str(symbol).strip() and isinstance(values, list)
            }
            payload = {
                "entry_timestamps_utc": [ts.isoformat() for ts in self.entry_timestamps_utc[-4096:] if isinstance(ts, datetime)],
                "symbol_entry_timestamps_utc": symbol_entry_rows,
                "entry_symbol_history": [
                    {"ts": ts.isoformat(), "symbol": str(symbol)}
                    for ts, symbol in self.entry_symbol_history[-4096:]
                    if isinstance(ts, datetime) and str(symbol).strip()
                ],
                "symbol_skip_until_utc": {
                    str(symbol): until.isoformat()
                    for symbol, until in self._symbol_skip_until_utc.items()
                    if str(symbol).strip() and isinstance(until, datetime)
                },
                "symbol_skip_reasons": {
                    str(symbol): str(reason or "symbol_skip")
                    for symbol, reason in self._symbol_skip_reasons.items()
                    if str(symbol).strip()
                },
                "edge_proof_bootstrap_entry_utc": [
                    ts.isoformat()
                    for ts in self.edge_proof_bootstrap_entry_utc[-1024:]
                    if isinstance(ts, datetime)
                ],
                "last_entry_symbol": str(self.last_entry_symbol or "").upper().strip(),
                "last_entry_time_utc": str(self.last_entry_time_utc or "").strip(),
                "last_global_close_sweep_utc": str(self.last_global_close_sweep_utc or "").strip(),
                "capital_preservation_pause_until_utc": str(self.capital_preservation_pause_until_utc or "").strip(),
                "updated_utc": datetime.now(timezone.utc).isoformat(),
            }
            LIVE_PACING_STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

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

    def _refresh_trap_rate_cache(self, force_refresh: bool = False) -> None:
        now_ts = time.time()
        if (
            (not force_refresh)
            and self._trap_rate_cache
            and (now_ts - float(self._trap_rate_cache_utc)) <= float(self._trap_rate_cache_ttl_sec)
        ):
            return

        payload = load_json(CLEAN_OPS_ROSTER_LATEST_FILE, {})
        rows = payload.get("candidates", []) if isinstance(payload, dict) else []
        trap_map: dict[str, float] = {}
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                symbol = str(row.get("symbol", "") or "").upper().strip()
                trap_rate = self._to_float(row.get("trap_rate_pct", -1.0), -1.0)
                if (not symbol) or trap_rate < 0.0:
                    continue
                prev = trap_map.get(symbol)
                trap_map[symbol] = float(trap_rate) if prev is None else min(float(prev), float(trap_rate))

        self._trap_rate_cache = trap_map
        self._trap_rate_cache_utc = now_ts

    def _symbol_trap_rate_pct(self, symbol: str) -> Optional[float]:
        token = str(symbol or "").upper().strip()
        if not token:
            return None
        self._refresh_trap_rate_cache(force_refresh=False)
        if token not in self._trap_rate_cache:
            return None
        return float(self._trap_rate_cache.get(token, 0.0))

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

        # Merge symbol_skip_until_utc from runtime_control.json into the
        # in-memory skip map so hot-reload of runtime_control takes effect
        # without a restart.  Only *extend* existing entries; never shorten a
        # skip that was dynamically added by the executor's own logic.
        _rc_skip_rows = runtime.get("symbol_skip_until_utc", {})
        if isinstance(_rc_skip_rows, dict):
            _now_utc = datetime.now(timezone.utc)
            for _rc_key, _rc_raw in _rc_skip_rows.items():
                _rc_sym = str(_rc_key or "").upper().strip()
                if not _rc_sym:
                    continue
                try:
                    _rc_until = self._parse_iso_utc(str(_rc_raw))
                except Exception:
                    continue
                if _rc_until <= _now_utc:
                    continue  # already expired — don't inject
                _existing = self._symbol_skip_until_utc.get(_rc_sym)
                if not isinstance(_existing, datetime) or _rc_until > _existing:
                    self._symbol_skip_until_utc[_rc_sym] = _rc_until

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
        self.hard_safety_only_mode = bool(runtime.get("hard_safety_only_mode", self.hard_safety_only_mode))
        self.max_trap_rate_pct = self._clamp(
            self._to_float(
                runtime.get(
                    "max_trap_rate_pct",
                    runtime.get("approval_max_trap_rate_pct", self.max_trap_rate_pct),
                ),
                self.max_trap_rate_pct,
            ),
            0.0,
            100.0,
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
        self.collateral_convert_avoid_open_positions = bool(
            runtime.get("collateral_convert_avoid_open_positions", self.collateral_convert_avoid_open_positions)
        )
        self.collateral_convert_protect_open_positions_sec = self._clamp(
            self._to_float(
                runtime.get(
                    "collateral_convert_protect_open_positions_sec",
                    self.collateral_convert_protect_open_positions_sec,
                ),
                self.collateral_convert_protect_open_positions_sec,
            ),
            0.0,
            86400.0,
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

            if self.hard_safety_only_mode:
                # In hard-safety mode, keep spread/liquidity/min-notional/trap gates authoritative
                # and avoid over-blocking on softer regime/alignment features.
                gate_thresholds["alignment"] = 0.05
                gate_thresholds["regime_conf"] = 0.05
                gate_thresholds["cross_confirm"] = 0.05
                gate_thresholds["correlation"] = 1.0
                gate_thresholds["sector_heat"] = 1.0
                gate_thresholds["signal_decay"] = 1.0
                self.signal_gate.min_composite_score = min(float(self.signal_gate.min_composite_score), 0.35)

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
        self.capital_preservation_mode = bool(
            runtime.get("capital_preservation_mode", self.capital_preservation_mode)
        )
        self.capital_preservation_min_recent_closed = int(
            self._clamp(
                self._to_float(
                    runtime.get(
                        "capital_preservation_min_recent_closed",
                        self.capital_preservation_min_recent_closed,
                    ),
                    self.capital_preservation_min_recent_closed,
                ),
                1.0,
                200.0,
            )
        )
        self.capital_preservation_min_win_rate_pct = self._clamp(
            self._to_float(
                runtime.get(
                    "capital_preservation_min_win_rate_pct",
                    self.capital_preservation_min_win_rate_pct,
                ),
                self.capital_preservation_min_win_rate_pct,
            ),
            0.0,
            100.0,
        )
        self.capital_preservation_min_avg_pnl_pct = self._clamp(
            self._to_float(
                runtime.get(
                    "capital_preservation_min_avg_pnl_pct",
                    self.capital_preservation_min_avg_pnl_pct,
                ),
                self.capital_preservation_min_avg_pnl_pct,
            ),
            -100.0,
            100.0,
        )
        self.capital_preservation_max_consecutive_losses = int(
            self._clamp(
                self._to_float(
                    runtime.get(
                        "capital_preservation_max_consecutive_losses",
                        self.capital_preservation_max_consecutive_losses,
                    ),
                    self.capital_preservation_max_consecutive_losses,
                ),
                1.0,
                25.0,
            )
        )
        self.capital_preservation_pause_sec = self._clamp(
            self._to_float(
                runtime.get("capital_preservation_pause_sec", self.capital_preservation_pause_sec),
                self.capital_preservation_pause_sec,
            ),
            30.0,
            86400.0,
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
        self.global_close_sweep_enabled = bool(
            runtime.get("global_close_sweep_enabled", self.global_close_sweep_enabled)
        )
        self.global_close_sweep_max_symbols = int(
            self._clamp(
                self._to_float(
                    runtime.get("global_close_sweep_max_symbols", self.global_close_sweep_max_symbols),
                    self.global_close_sweep_max_symbols,
                ),
                0.0,
                5000.0,
            )
        )
        self.global_close_sweep_interval_sec = self._clamp(
            self._to_float(
                runtime.get("global_close_sweep_interval_sec", self.global_close_sweep_interval_sec),
                self.global_close_sweep_interval_sec,
            ),
            1.0,
            3600.0,
        )
        self.auto_trip_kill_switch_on_inventory_discrepancy = bool(
            runtime.get(
                "auto_trip_kill_switch_on_inventory_discrepancy",
                self.auto_trip_kill_switch_on_inventory_discrepancy,
            )
        )
        self.auto_kill_switch_trip_cooldown_sec = self._clamp(
            self._to_float(
                runtime.get(
                    "auto_kill_switch_trip_cooldown_sec",
                    self.auto_kill_switch_trip_cooldown_sec,
                ),
                self.auto_kill_switch_trip_cooldown_sec,
            ),
            0.0,
            86400.0,
        )
        self.auto_kill_switch_last_trip_utc = str(
            runtime.get("safety_auto_kill_trip_utc", self.auto_kill_switch_last_trip_utc) or ""
        ).strip()

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
                0.0,
                5000.0,
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
        self.universe_hard_reject_spread_bps = self._clamp(
            self._to_float(
                runtime.get("universe_hard_reject_spread_bps", self.universe_hard_reject_spread_bps),
                self.universe_hard_reject_spread_bps,
            ),
            0.0,
            5000.0,
        )
        self.preferred_symbol_max_spread_bps = self._clamp(
            self._to_float(
                runtime.get("preferred_symbol_max_spread_bps", self.preferred_symbol_max_spread_bps),
                self.preferred_symbol_max_spread_bps,
            ),
            1.0,
            500.0,
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
                0.0,
                5000.0,
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
        self.symbol_intel_learning_enabled = bool(
            runtime.get("symbol_intel_learning_enabled", self.symbol_intel_learning_enabled)
        )
        self.symbol_intel_learning_weight = self._clamp(
            self._to_float(
                runtime.get("symbol_intel_learning_weight", self.symbol_intel_learning_weight),
                self.symbol_intel_learning_weight,
            ),
            0.0,
            2.0,
        )
        self.symbol_intel_learning_max_bonus = self._clamp(
            self._to_float(
                runtime.get("symbol_intel_learning_max_bonus", self.symbol_intel_learning_max_bonus),
                self.symbol_intel_learning_max_bonus,
            ),
            0.0,
            60.0,
        )
        self.symbol_intel_learning_max_age_sec = self._clamp(
            self._to_float(
                runtime.get("symbol_intel_learning_max_age_sec", self.symbol_intel_learning_max_age_sec),
                self.symbol_intel_learning_max_age_sec,
            ),
            30.0,
            172800.0,
        )
        self.edge_proof_enabled = bool(runtime.get("edge_proof_enabled", self.edge_proof_enabled))
        self.edge_proof_recent_closed_trades = int(
            self._clamp(
                self._to_float(
                    runtime.get("edge_proof_recent_closed_trades", self.edge_proof_recent_closed_trades),
                    self.edge_proof_recent_closed_trades,
                ),
                1.0,
                200.0,
            )
        )
        self.edge_proof_min_win_rate_pct = self._clamp(
            self._to_float(
                runtime.get("edge_proof_min_win_rate_pct", self.edge_proof_min_win_rate_pct),
                self.edge_proof_min_win_rate_pct,
            ),
            0.0,
            100.0,
        )
        self.edge_proof_min_avg_pnl_pct = self._clamp(
            self._to_float(
                runtime.get("edge_proof_min_avg_pnl_pct", self.edge_proof_min_avg_pnl_pct),
                self.edge_proof_min_avg_pnl_pct,
            ),
            -100.0,
            100.0,
        )
        self.edge_proof_max_last_close_age_min = self._clamp(
            self._to_float(
                runtime.get("edge_proof_max_last_close_age_min", self.edge_proof_max_last_close_age_min),
                self.edge_proof_max_last_close_age_min,
            ),
            1.0,
            1440.0,
        )
        self.edge_proof_require_symbol_intel_fresh = bool(
            runtime.get("edge_proof_require_symbol_intel_fresh", self.edge_proof_require_symbol_intel_fresh)
        )
        self.edge_proof_hybrid_fallback_for_symbol_intel = bool(
            runtime.get(
                "edge_proof_hybrid_fallback_for_symbol_intel",
                self.edge_proof_hybrid_fallback_for_symbol_intel,
            )
        )
        self.edge_proof_bootstrap_enabled = bool(
            runtime.get("edge_proof_bootstrap_enabled", self.edge_proof_bootstrap_enabled)
        )
        self.edge_proof_bootstrap_max_entries_per_hour = int(
            self._clamp(
                self._to_float(
                    runtime.get(
                        "edge_proof_bootstrap_max_entries_per_hour",
                        self.edge_proof_bootstrap_max_entries_per_hour,
                    ),
                    self.edge_proof_bootstrap_max_entries_per_hour,
                ),
                0.0,
                24.0,
            )
        )
        self.edge_proof_bootstrap_min_gate_score = self._clamp(
            self._to_float(
                runtime.get("edge_proof_bootstrap_min_gate_score", self.edge_proof_bootstrap_min_gate_score),
                self.edge_proof_bootstrap_min_gate_score,
            ),
            0.0,
            0.99,
        )
        self.edge_proof_bootstrap_min_expected_edge_bps = self._clamp(
            self._to_float(
                runtime.get(
                    "edge_proof_bootstrap_min_expected_edge_bps",
                    self.edge_proof_bootstrap_min_expected_edge_bps,
                ),
                self.edge_proof_bootstrap_min_expected_edge_bps,
            ),
            0.0,
            500.0,
        )
        self.edge_proof_bootstrap_min_hybrid_score = self._clamp(
            self._to_float(
                runtime.get("edge_proof_bootstrap_min_hybrid_score", self.edge_proof_bootstrap_min_hybrid_score),
                self.edge_proof_bootstrap_min_hybrid_score,
            ),
            -500.0,
            500.0,
        )
        self.edge_proof_bootstrap_min_momentum_pct = self._clamp(
            self._to_float(
                runtime.get("edge_proof_bootstrap_min_momentum_pct", self.edge_proof_bootstrap_min_momentum_pct),
                self.edge_proof_bootstrap_min_momentum_pct,
            ),
            -10.0,
            10.0,
        )
        self.edge_proof_bootstrap_max_spread_bps = self._clamp(
            self._to_float(
                runtime.get("edge_proof_bootstrap_max_spread_bps", self.edge_proof_bootstrap_max_spread_bps),
                self.edge_proof_bootstrap_max_spread_bps,
            ),
            0.0,
            250.0,
        )
        self.edge_proof_bootstrap_hybrid_edge_scale = self._clamp(
            self._to_float(
                runtime.get("edge_proof_bootstrap_hybrid_edge_scale", self.edge_proof_bootstrap_hybrid_edge_scale),
                self.edge_proof_bootstrap_hybrid_edge_scale,
            ),
            0.0,
            10.0,
        )
        self.edge_proof_bootstrap_require_hybrid_candidates = bool(
            runtime.get(
                "edge_proof_bootstrap_require_hybrid_candidates",
                self.edge_proof_bootstrap_require_hybrid_candidates,
            )
        )
        self.edge_proof_cost_floor_enabled = bool(
            runtime.get("edge_proof_cost_floor_enabled", self.edge_proof_cost_floor_enabled)
        )
        self.edge_proof_cost_floor_fee_roundtrip_bps = self._clamp(
            self._to_float(
                runtime.get(
                    "edge_proof_cost_floor_fee_roundtrip_bps",
                    self.edge_proof_cost_floor_fee_roundtrip_bps,
                ),
                self.edge_proof_cost_floor_fee_roundtrip_bps,
            ),
            0.0,
            500.0,
        )
        self.edge_proof_cost_floor_spread_weight = self._clamp(
            self._to_float(
                runtime.get(
                    "edge_proof_cost_floor_spread_weight",
                    self.edge_proof_cost_floor_spread_weight,
                ),
                self.edge_proof_cost_floor_spread_weight,
            ),
            0.0,
            3.0,
        )
        self.edge_proof_cost_floor_slippage_roundtrip_bps = self._clamp(
            self._to_float(
                runtime.get(
                    "edge_proof_cost_floor_slippage_roundtrip_bps",
                    self.edge_proof_cost_floor_slippage_roundtrip_bps,
                ),
                self.edge_proof_cost_floor_slippage_roundtrip_bps,
            ),
            0.0,
            250.0,
        )
        self.edge_proof_cost_floor_buffer_bps = self._clamp(
            self._to_float(
                runtime.get(
                    "edge_proof_cost_floor_buffer_bps",
                    self.edge_proof_cost_floor_buffer_bps,
                ),
                self.edge_proof_cost_floor_buffer_bps,
            ),
            0.0,
            250.0,
        )
        self.edge_proof_cost_floor_min_bps = self._clamp(
            self._to_float(
                runtime.get(
                    "edge_proof_cost_floor_min_bps",
                    self.edge_proof_cost_floor_min_bps,
                ),
                self.edge_proof_cost_floor_min_bps,
            ),
            0.0,
            500.0,
        )
        self.edge_proof_cost_floor_max_bps = self._clamp(
            self._to_float(
                runtime.get(
                    "edge_proof_cost_floor_max_bps",
                    self.edge_proof_cost_floor_max_bps,
                ),
                self.edge_proof_cost_floor_max_bps,
            ),
            0.0,
            1000.0,
        )
        self.edge_proof_cost_floor_adaptive_enabled = bool(
            runtime.get("edge_proof_cost_floor_adaptive_enabled", self.edge_proof_cost_floor_adaptive_enabled)
        )
        self.edge_proof_cost_floor_adaptive_min_closed_trades = int(
            self._clamp(
                self._to_float(
                    runtime.get(
                        "edge_proof_cost_floor_adaptive_min_closed_trades",
                        self.edge_proof_cost_floor_adaptive_min_closed_trades,
                    ),
                    self.edge_proof_cost_floor_adaptive_min_closed_trades,
                ),
                1.0,
                200.0,
            )
        )
        self.edge_proof_cost_floor_adaptive_loss_threshold_bps = self._clamp(
            self._to_float(
                runtime.get(
                    "edge_proof_cost_floor_adaptive_loss_threshold_bps",
                    self.edge_proof_cost_floor_adaptive_loss_threshold_bps,
                ),
                self.edge_proof_cost_floor_adaptive_loss_threshold_bps,
            ),
            -500.0,
            500.0,
        )
        self.edge_proof_cost_floor_adaptive_gain_threshold_bps = self._clamp(
            self._to_float(
                runtime.get(
                    "edge_proof_cost_floor_adaptive_gain_threshold_bps",
                    self.edge_proof_cost_floor_adaptive_gain_threshold_bps,
                ),
                self.edge_proof_cost_floor_adaptive_gain_threshold_bps,
            ),
            -500.0,
            500.0,
        )
        self.edge_proof_cost_floor_adaptive_loss_adjust_bps = self._clamp(
            self._to_float(
                runtime.get(
                    "edge_proof_cost_floor_adaptive_loss_adjust_bps",
                    self.edge_proof_cost_floor_adaptive_loss_adjust_bps,
                ),
                self.edge_proof_cost_floor_adaptive_loss_adjust_bps,
            ),
            0.0,
            500.0,
        )
        self.edge_proof_cost_floor_adaptive_gain_adjust_bps = self._clamp(
            self._to_float(
                runtime.get(
                    "edge_proof_cost_floor_adaptive_gain_adjust_bps",
                    self.edge_proof_cost_floor_adaptive_gain_adjust_bps,
                ),
                self.edge_proof_cost_floor_adaptive_gain_adjust_bps,
            ),
            0.0,
            500.0,
        )
        self.edge_proof_cost_floor_adaptive_win_rate_floor_pct = self._clamp(
            self._to_float(
                runtime.get(
                    "edge_proof_cost_floor_adaptive_win_rate_floor_pct",
                    self.edge_proof_cost_floor_adaptive_win_rate_floor_pct,
                ),
                self.edge_proof_cost_floor_adaptive_win_rate_floor_pct,
            ),
            0.0,
            100.0,
        )
        self.edge_proof_cost_floor_adaptive_win_rate_relax_pct = self._clamp(
            self._to_float(
                runtime.get(
                    "edge_proof_cost_floor_adaptive_win_rate_relax_pct",
                    self.edge_proof_cost_floor_adaptive_win_rate_relax_pct,
                ),
                self.edge_proof_cost_floor_adaptive_win_rate_relax_pct,
            ),
            0.0,
            100.0,
        )
        self.alpha_lock_enabled = bool(runtime.get("alpha_lock_enabled", self.alpha_lock_enabled))
        self.alpha_lock_min_gate_score = self._clamp(
            self._to_float(
                runtime.get("alpha_lock_min_gate_score", self.alpha_lock_min_gate_score),
                self.alpha_lock_min_gate_score,
            ),
            0.0,
            0.99,
        )
        self.alpha_lock_min_expected_edge_bps = self._clamp(
            self._to_float(
                runtime.get("alpha_lock_min_expected_edge_bps", self.alpha_lock_min_expected_edge_bps),
                self.alpha_lock_min_expected_edge_bps,
            ),
            0.0,
            500.0,
        )
        self.alpha_lock_min_score = self._clamp(
            self._to_float(
                runtime.get("alpha_lock_min_score", self.alpha_lock_min_score),
                self.alpha_lock_min_score,
            ),
            -500.0,
            1000.0,
        )
        self.alpha_lock_learning_bonus_weight = self._clamp(
            self._to_float(
                runtime.get("alpha_lock_learning_bonus_weight", self.alpha_lock_learning_bonus_weight),
                self.alpha_lock_learning_bonus_weight,
            ),
            0.0,
            5.0,
        )
        self.alpha_lock_hybrid_score_weight = self._clamp(
            self._to_float(
                runtime.get("alpha_lock_hybrid_score_weight", self.alpha_lock_hybrid_score_weight),
                self.alpha_lock_hybrid_score_weight,
            ),
            0.0,
            5.0,
        )
        self.alpha_lock_allow_hybrid_fallback = bool(
            runtime.get("alpha_lock_allow_hybrid_fallback", self.alpha_lock_allow_hybrid_fallback)
        )
        self.alpha_lock_allow_gate_only_fallback = bool(
            runtime.get("alpha_lock_allow_gate_only_fallback", self.alpha_lock_allow_gate_only_fallback)
        )
        self.missing_ticker_skip_cooldown_sec = self._clamp(
            self._to_float(
                runtime.get("missing_ticker_skip_cooldown_sec", self.missing_ticker_skip_cooldown_sec),
                self.missing_ticker_skip_cooldown_sec,
            ),
            1.0,
            3600.0,
        )
        self.spread_too_wide_skip_cooldown_sec = self._clamp(
            self._to_float(
                runtime.get("spread_too_wide_skip_cooldown_sec", self.spread_too_wide_skip_cooldown_sec),
                self.spread_too_wide_skip_cooldown_sec,
            ),
            1.0,
            3600.0,
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
        self.symbol_skip_cooldown_sec = self._clamp(
            self._to_float(
                runtime.get("symbol_skip_cooldown_sec", self.symbol_skip_cooldown_sec),
                self.symbol_skip_cooldown_sec,
            ),
            0.0,
            3600.0,
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
                0.0,
                5000.0,
            )
        )
        self.hybrid_swing_selector_enabled = bool(
            runtime.get("hybrid_swing_selector_enabled", self.hybrid_swing_selector_enabled)
        )
        self.hybrid_swing_min_range_pct = self._clamp(
            self._to_float(
                runtime.get("hybrid_swing_min_range_pct", self.hybrid_swing_min_range_pct),
                self.hybrid_swing_min_range_pct,
            ),
            0.0,
            250.0,
        )
        self.hybrid_swing_min_momentum_pct = self._clamp(
            self._to_float(
                runtime.get("hybrid_swing_min_momentum_pct", self.hybrid_swing_min_momentum_pct),
                self.hybrid_swing_min_momentum_pct,
            ),
            -100.0,
            100.0,
        )
        self.hybrid_swing_spread_guard_bps = self._clamp(
            self._to_float(
                runtime.get("hybrid_swing_spread_guard_bps", self.hybrid_swing_spread_guard_bps),
                self.hybrid_swing_spread_guard_bps,
            ),
            5.0,
            500.0,
        )
        self.hybrid_swing_range_weight = self._clamp(
            self._to_float(
                runtime.get("hybrid_swing_range_weight", self.hybrid_swing_range_weight),
                self.hybrid_swing_range_weight,
            ),
            0.0,
            10.0,
        )
        self.hybrid_swing_momentum_weight = self._clamp(
            self._to_float(
                runtime.get("hybrid_swing_momentum_weight", self.hybrid_swing_momentum_weight),
                self.hybrid_swing_momentum_weight,
            ),
            0.0,
            10.0,
        )
        self.hybrid_swing_position_weight = self._clamp(
            self._to_float(
                runtime.get("hybrid_swing_position_weight", self.hybrid_swing_position_weight),
                self.hybrid_swing_position_weight,
            ),
            0.0,
            10.0,
        )
        self.hybrid_swing_activity_weight = self._clamp(
            self._to_float(
                runtime.get("hybrid_swing_activity_weight", self.hybrid_swing_activity_weight),
                self.hybrid_swing_activity_weight,
            ),
            0.0,
            10.0,
        )
        self.hybrid_swing_spread_penalty = self._clamp(
            self._to_float(
                runtime.get("hybrid_swing_spread_penalty", self.hybrid_swing_spread_penalty),
                self.hybrid_swing_spread_penalty,
            ),
            0.0,
            2.0,
        )
        self.hybrid_swing_max_entry_range_position = self._clamp(
            self._to_float(
                runtime.get("hybrid_swing_max_entry_range_position", self.hybrid_swing_max_entry_range_position),
                self.hybrid_swing_max_entry_range_position,
            ),
            0.1,
            1.0,
        )
        self.hybrid_swing_whitelist_relax_enabled = bool(
            runtime.get("hybrid_swing_whitelist_relax_enabled", self.hybrid_swing_whitelist_relax_enabled)
        )
        self.hybrid_swing_min_candidates = int(
            self._clamp(
                self._to_float(
                    runtime.get("hybrid_swing_min_candidates", self.hybrid_swing_min_candidates),
                    self.hybrid_swing_min_candidates,
                ),
                1.0,
                1000.0,
            )
        )
        self.hybrid_swing_relax_cap = int(
            self._clamp(
                self._to_float(runtime.get("hybrid_swing_relax_cap", self.hybrid_swing_relax_cap), self.hybrid_swing_relax_cap),
                8.0,
                5000.0,
            )
        )
        self.hybrid_swing_long_bias_enabled = bool(
            runtime.get("hybrid_swing_long_bias_enabled", self.hybrid_swing_long_bias_enabled)
        )
        self.hybrid_swing_long_bias_min_momentum_pct = self._clamp(
            self._to_float(
                runtime.get("hybrid_swing_long_bias_min_momentum_pct", self.hybrid_swing_long_bias_min_momentum_pct),
                self.hybrid_swing_long_bias_min_momentum_pct,
            ),
            -5.0,
            5.0,
        )
        self.hybrid_swing_long_bias_penalty_per_pct = self._clamp(
            self._to_float(
                runtime.get("hybrid_swing_long_bias_penalty_per_pct", self.hybrid_swing_long_bias_penalty_per_pct),
                self.hybrid_swing_long_bias_penalty_per_pct,
            ),
            0.0,
            100.0,
        )
        # ── Institutional Swing Hunter / Trailing Stop Engine ─────────────────
        self.trailing_stop_enabled = bool(
            runtime.get("trailing_stop_enabled", self.trailing_stop_enabled)
        )
        self.trailing_stop_activation_bps = self._clamp(
            self._to_float(
                runtime.get("trailing_stop_activation_bps", self.trailing_stop_activation_bps),
                self.trailing_stop_activation_bps,
            ),
            10.0,
            5000.0,
        )
        self.trailing_stop_trail_bps = self._clamp(
            self._to_float(
                runtime.get("trailing_stop_trail_bps", self.trailing_stop_trail_bps),
                self.trailing_stop_trail_bps,
            ),
            5.0,
            2000.0,
        )
        self.trailing_stop_dynamic_scaling = bool(
            runtime.get("trailing_stop_dynamic_scaling", self.trailing_stop_dynamic_scaling)
        )
        self.trailing_stop_dynamic_multiplier = self._clamp(
            self._to_float(
                runtime.get("trailing_stop_dynamic_multiplier", self.trailing_stop_dynamic_multiplier),
                self.trailing_stop_dynamic_multiplier,
            ),
            0.0,
            2.0,
        )
        self.trailing_stop_vel_exit_enabled = bool(
            runtime.get("trailing_stop_vel_exit_enabled", self.trailing_stop_vel_exit_enabled)
        )
        self.trailing_stop_vel_exit_threshold_pct = self._clamp(
            self._to_float(
                runtime.get("trailing_stop_vel_exit_threshold_pct", self.trailing_stop_vel_exit_threshold_pct),
                self.trailing_stop_vel_exit_threshold_pct,
            ),
            0.05,
            5.0,
        )
        self.hybrid_swing_vwap_filter_enabled = bool(
            runtime.get("hybrid_swing_vwap_filter_enabled", self.hybrid_swing_vwap_filter_enabled)
        )
        self.hybrid_swing_vwap_max_deviation_pct = self._clamp(
            self._to_float(
                runtime.get("hybrid_swing_vwap_max_deviation_pct", self.hybrid_swing_vwap_max_deviation_pct),
                self.hybrid_swing_vwap_max_deviation_pct,
            ),
            0.0,
            20.0,
        )
        self.kelly_sizing_enabled = bool(
            runtime.get("kelly_sizing_enabled", self.kelly_sizing_enabled)
        )
        self.kelly_fraction = self._clamp(
            self._to_float(
                runtime.get("kelly_fraction", self.kelly_fraction),
                self.kelly_fraction,
            ),
            0.05,
            1.0,
        )
        self.kelly_min_sample_trades = max(1, int(
            self._to_float(
                runtime.get("kelly_min_sample_trades", self.kelly_min_sample_trades),
                self.kelly_min_sample_trades,
            )
        ))
        # ── OBI + Conviction + Break-Even Ratchet hot-reload ──────────────────
        self.hybrid_swing_obi_filter_enabled = bool(
            runtime.get("hybrid_swing_obi_filter_enabled", self.hybrid_swing_obi_filter_enabled)
        )
        self.hybrid_swing_min_obi = self._clamp(
            self._to_float(runtime.get("hybrid_swing_min_obi", self.hybrid_swing_min_obi), self.hybrid_swing_min_obi),
            -1.0, 1.0,
        )
        self.hybrid_swing_obi_weight = self._clamp(
            self._to_float(runtime.get("hybrid_swing_obi_weight", self.hybrid_swing_obi_weight), self.hybrid_swing_obi_weight),
            0.0, 20.0,
        )
        self.hybrid_swing_conviction_weight = self._clamp(
            self._to_float(runtime.get("hybrid_swing_conviction_weight", self.hybrid_swing_conviction_weight), self.hybrid_swing_conviction_weight),
            0.0, 10.0,
        )
        self.trailing_stop_breakeven_enabled = bool(
            runtime.get("trailing_stop_breakeven_enabled", self.trailing_stop_breakeven_enabled)
        )
        self.trailing_stop_breakeven_ratchet_mult = self._clamp(
            self._to_float(runtime.get("trailing_stop_breakeven_ratchet_mult", self.trailing_stop_breakeven_ratchet_mult), self.trailing_stop_breakeven_ratchet_mult),
            1.0, 5.0,
        )
        # ── Market Regime Filter hot-reload ───────────────────────────────────
        self.hybrid_swing_regime_filter_enabled = bool(
            runtime.get("hybrid_swing_regime_filter_enabled", self.hybrid_swing_regime_filter_enabled)
        )
        self.hybrid_swing_regime_bear_momentum_pct = self._clamp(
            self._to_float(runtime.get("hybrid_swing_regime_bear_momentum_pct", self.hybrid_swing_regime_bear_momentum_pct), self.hybrid_swing_regime_bear_momentum_pct),
            -20.0, 0.0,
        )
        self.hybrid_swing_regime_bull_bonus = self._clamp(
            self._to_float(runtime.get("hybrid_swing_regime_bull_bonus", self.hybrid_swing_regime_bull_bonus), self.hybrid_swing_regime_bull_bonus),
            0.0, 30.0,
        )
        # ── Adaptive Post-Loss Cooldown hot-reload ─────────────────────────────
        self.adaptive_loss_cooldown_enabled = bool(
            runtime.get("adaptive_loss_cooldown_enabled", self.adaptive_loss_cooldown_enabled)
        )
        self.adaptive_loss_cooldown_scale = self._clamp(
            self._to_float(runtime.get("adaptive_loss_cooldown_scale", self.adaptive_loss_cooldown_scale), self.adaptive_loss_cooldown_scale),
            0.0, 100.0,
        )
        self.adaptive_loss_cooldown_cap_sec = self._clamp(
            self._to_float(runtime.get("adaptive_loss_cooldown_cap_sec", self.adaptive_loss_cooldown_cap_sec), self.adaptive_loss_cooldown_cap_sec),
            0.0, 86400.0,
        )
        # ─────────────────────────────────────────────────────────────────────

        # ══ Sell Logic Innovations hot-reload ═════════════════════════════════
        # Innovation 1: Profit Lock
        self.profit_lock_enabled = bool(runtime.get("profit_lock_enabled", self.profit_lock_enabled))
        self.profit_lock_pct = self._clamp(
            self._to_float(runtime.get("profit_lock_pct", self.profit_lock_pct), self.profit_lock_pct), 0.001, 2.0)
        # Innovation 2: Dead-Weight Purge
        self.dead_weight_purge_enabled = bool(runtime.get("dead_weight_purge_enabled", self.dead_weight_purge_enabled))
        self.dead_weight_max_age_sec = self._clamp(
            self._to_float(runtime.get("dead_weight_max_age_sec", self.dead_weight_max_age_sec), self.dead_weight_max_age_sec), 60.0, 86400.0)
        self.dead_weight_max_drift_pct = self._clamp(
            self._to_float(runtime.get("dead_weight_max_drift_pct", self.dead_weight_max_drift_pct), self.dead_weight_max_drift_pct), 0.0, 0.20)
        # Innovation 3: Age-Tightened Trailing Stop
        self.age_trail_tighten_enabled = bool(runtime.get("age_trail_tighten_enabled", self.age_trail_tighten_enabled))
        self.age_trail_tighten_start_sec = self._clamp(
            self._to_float(runtime.get("age_trail_tighten_start_sec", self.age_trail_tighten_start_sec), self.age_trail_tighten_start_sec), 30.0, 3600.0)
        self.age_trail_tighten_rate = self._clamp(
            self._to_float(runtime.get("age_trail_tighten_rate", self.age_trail_tighten_rate), self.age_trail_tighten_rate), 0.0, 0.05)
        # Innovation 4: Cascade Loss Guard
        self.cascade_guard_enabled = bool(runtime.get("cascade_guard_enabled", self.cascade_guard_enabled))
        self.cascade_guard_min_positions = max(2, int(self._to_float(runtime.get("cascade_guard_min_positions", self.cascade_guard_min_positions), self.cascade_guard_min_positions)))
        self.cascade_guard_threshold_pct = self._clamp(
            self._to_float(runtime.get("cascade_guard_threshold_pct", self.cascade_guard_threshold_pct), self.cascade_guard_threshold_pct), 0.001, 0.50)
        # Innovation 5: Short-Signal Force Exit Timer
        self.short_signal_force_exit_enabled = bool(runtime.get("short_signal_force_exit_enabled", self.short_signal_force_exit_enabled))
        self.short_signal_force_exit_sec = self._clamp(
            self._to_float(runtime.get("short_signal_force_exit_sec", self.short_signal_force_exit_sec), self.short_signal_force_exit_sec), 30.0, 86400.0)
        # Innovation 6: Velocity Reversal on Small Loss
        self.vel_exit_on_loss_enabled = bool(runtime.get("vel_exit_on_loss_enabled", self.vel_exit_on_loss_enabled))
        self.vel_exit_on_loss_max_pnl_pct = self._clamp(
            self._to_float(runtime.get("vel_exit_on_loss_max_pnl_pct", self.vel_exit_on_loss_max_pnl_pct), self.vel_exit_on_loss_max_pnl_pct), -0.20, 0.0)
        self.vel_exit_on_loss_vel_threshold_pct = self._clamp(
            self._to_float(runtime.get("vel_exit_on_loss_vel_threshold_pct", self.vel_exit_on_loss_vel_threshold_pct), self.vel_exit_on_loss_vel_threshold_pct), 0.05, 10.0)
        # Innovation 7: Conviction-Tiered Take-Profit
        self.conviction_tiered_tp_enabled = bool(runtime.get("conviction_tiered_tp_enabled", self.conviction_tiered_tp_enabled))
        self.conviction_tiered_tp_low_score = self._clamp(
            self._to_float(runtime.get("conviction_tiered_tp_low_score", self.conviction_tiered_tp_low_score), self.conviction_tiered_tp_low_score), 0.0, 1.0)
        self.conviction_tiered_tp_low_tp_pct = self._clamp(
            self._to_float(runtime.get("conviction_tiered_tp_low_tp_pct", self.conviction_tiered_tp_low_tp_pct), self.conviction_tiered_tp_low_tp_pct), 0.0001, 0.20)
        # Innovation 8: Moonshot Slot Reserve
        self.moonshot_slot_reserve_enabled = bool(runtime.get("moonshot_slot_reserve_enabled", self.moonshot_slot_reserve_enabled))
        self.moonshot_slot_reserve_blocked_sec = self._clamp(
            self._to_float(runtime.get("moonshot_slot_reserve_blocked_sec", self.moonshot_slot_reserve_blocked_sec), self.moonshot_slot_reserve_blocked_sec), 10.0, 3600.0)
        self.moonshot_slot_reserve_tp_override_pct = self._clamp(
            self._to_float(runtime.get("moonshot_slot_reserve_tp_override_pct", self.moonshot_slot_reserve_tp_override_pct), self.moonshot_slot_reserve_tp_override_pct), 0.0, 0.10)
        # Innovation 9: PnL Drawdown Accelerator
        self.pnl_drawdown_accel_enabled = bool(runtime.get("pnl_drawdown_accel_enabled", self.pnl_drawdown_accel_enabled))
        self.pnl_drawdown_accel_peak_drop_pct = self._clamp(
            self._to_float(runtime.get("pnl_drawdown_accel_peak_drop_pct", self.pnl_drawdown_accel_peak_drop_pct), self.pnl_drawdown_accel_peak_drop_pct), 0.001, 0.50)
        # Innovation 10: Heat-Triggered Capital Recycle
        self.heat_recycle_enabled = bool(runtime.get("heat_recycle_enabled", self.heat_recycle_enabled))
        self.heat_recycle_min_hold_sec = self._clamp(
            self._to_float(runtime.get("heat_recycle_min_hold_sec", self.heat_recycle_min_hold_sec), self.heat_recycle_min_hold_sec), 0.0, 3600.0)
        self.heat_recycle_cooldown_sec = self._clamp(
            self._to_float(runtime.get("heat_recycle_cooldown_sec", self.heat_recycle_cooldown_sec), self.heat_recycle_cooldown_sec), 5.0, 3600.0)
        # Innovation 14: Age-Pressure TP Ladder
        self.age_pressure_tp_enabled = bool(runtime.get("age_pressure_tp_enabled", self.age_pressure_tp_enabled))
        self.age_pressure_tp_early_pct = self._clamp(
            self._to_float(runtime.get("age_pressure_tp_early_pct", self.age_pressure_tp_early_pct), self.age_pressure_tp_early_pct), 0.50, 0.95)
        self.age_pressure_tp_early_min_bps = self._clamp(
            self._to_float(runtime.get("age_pressure_tp_early_min_bps", self.age_pressure_tp_early_min_bps), self.age_pressure_tp_early_min_bps), 0.0, 200.0)
        self.age_pressure_tp_late_pct = self._clamp(
            self._to_float(runtime.get("age_pressure_tp_late_pct", self.age_pressure_tp_late_pct), self.age_pressure_tp_late_pct), 0.51, 0.99)
        # Innovation 15: Age-Pressure SL Tightener
        self.age_pressure_sl_enabled = bool(runtime.get("age_pressure_sl_enabled", self.age_pressure_sl_enabled))
        self.age_pressure_sl_mid_pct = self._clamp(
            self._to_float(runtime.get("age_pressure_sl_mid_pct", self.age_pressure_sl_mid_pct), self.age_pressure_sl_mid_pct), 0.30, 0.80)
        self.age_pressure_sl_mid_fraction = self._clamp(
            self._to_float(runtime.get("age_pressure_sl_mid_fraction", self.age_pressure_sl_mid_fraction), self.age_pressure_sl_mid_fraction), 0.10, 1.00)
        self.age_pressure_sl_late_pct = self._clamp(
            self._to_float(runtime.get("age_pressure_sl_late_pct", self.age_pressure_sl_late_pct), self.age_pressure_sl_late_pct), 0.50, 0.95)
        self.age_pressure_sl_late_fraction = self._clamp(
            self._to_float(runtime.get("age_pressure_sl_late_fraction", self.age_pressure_sl_late_fraction), self.age_pressure_sl_late_fraction), 0.05, 0.95)
        # Innovation 16: Flat-Exit Reentry Dampener
        self.flat_exit_dampener_enabled = bool(runtime.get("flat_exit_dampener_enabled", self.flat_exit_dampener_enabled))
        self.flat_exit_dampener_min_bps = self._clamp(
            self._to_float(runtime.get("flat_exit_dampener_min_bps", self.flat_exit_dampener_min_bps), self.flat_exit_dampener_min_bps), 0.0, 50.0)
        self.flat_exit_dampener_cooldown_sec = self._clamp(
            self._to_float(runtime.get("flat_exit_dampener_cooldown_sec", self.flat_exit_dampener_cooldown_sec), self.flat_exit_dampener_cooldown_sec), 60.0, 7200.0)
        # Innovation 17: Flat-Cluster Regime Pause
        self.cluster_flat_pause_enabled = bool(runtime.get("cluster_flat_pause_enabled", self.cluster_flat_pause_enabled))
        _new_n = int(self._clamp(
            self._to_float(runtime.get("cluster_flat_recent_n", self.cluster_flat_recent_n), self.cluster_flat_recent_n), 3.0, 20.0))
        if _new_n != self._recent_close_pnl_abs_bps.maxlen:
            self._recent_close_pnl_abs_bps = deque(list(self._recent_close_pnl_abs_bps)[-_new_n:], maxlen=_new_n)
        self.cluster_flat_recent_n = _new_n
        self.cluster_flat_threshold_frac = self._clamp(
            self._to_float(runtime.get("cluster_flat_threshold_frac", self.cluster_flat_threshold_frac), self.cluster_flat_threshold_frac), 0.50, 1.00)
        self.cluster_flat_max_bps = self._clamp(
            self._to_float(runtime.get("cluster_flat_max_bps", self.cluster_flat_max_bps), self.cluster_flat_max_bps), 0.0, 100.0)
        self.cluster_flat_pause_sec = self._clamp(
            self._to_float(runtime.get("cluster_flat_pause_sec", self.cluster_flat_pause_sec), self.cluster_flat_pause_sec), 30.0, 3600.0)
        # Innovation 18: Dead-Weight Strike Escalator
        self.dw_strike_escalator_enabled = bool(runtime.get("dw_strike_escalator_enabled", self.dw_strike_escalator_enabled))
        self.dw_strike_escalator_base_sec = self._clamp(
            self._to_float(runtime.get("dw_strike_escalator_base_sec", self.dw_strike_escalator_base_sec), self.dw_strike_escalator_base_sec), 60.0, 7200.0)
        self.dw_strike_escalator_multiplier = self._clamp(
            self._to_float(runtime.get("dw_strike_escalator_multiplier", self.dw_strike_escalator_multiplier), self.dw_strike_escalator_multiplier), 1.0, 8.0)
        self.dw_strike_escalator_max_sec = self._clamp(
            self._to_float(runtime.get("dw_strike_escalator_max_sec", self.dw_strike_escalator_max_sec), self.dw_strike_escalator_max_sec), 600.0, 86400.0)
        # Innovation 19: Moonshot Size Amplifier
        self.moonshot_amplifier_enabled = bool(runtime.get("moonshot_amplifier_enabled", self.moonshot_amplifier_enabled))
        self.moonshot_amplifier_min_gate_score = self._clamp(
            self._to_float(runtime.get("moonshot_amplifier_min_gate_score", self.moonshot_amplifier_min_gate_score), self.moonshot_amplifier_min_gate_score), 0.60, 1.00)
        self.moonshot_amplifier_multiplier = self._clamp(
            self._to_float(runtime.get("moonshot_amplifier_multiplier", self.moonshot_amplifier_multiplier), self.moonshot_amplifier_multiplier), 1.10, 3.00)
        self.moonshot_amplifier_max_cap_pct = self._clamp(
            self._to_float(runtime.get("moonshot_amplifier_max_cap_pct", self.moonshot_amplifier_max_cap_pct), self.moonshot_amplifier_max_cap_pct), 0.25, 0.60)
        self.moonshot_watchlist_path = str(runtime.get("moonshot_watchlist_path", self.moonshot_watchlist_path))
        # Innovation 20: Throttle Reset Command + Preferred Symbol Fast Lane
        new_nonce = int(self._to_float(runtime.get("fail_streak_reset_nonce", 0), 0))
        if new_nonce != self._last_fail_streak_reset_nonce and new_nonce > 0:
            self._last_fail_streak_reset_nonce = new_nonce
            self.order_fail_streak = 0
            self.notional_throttle = 1.0
            self._set_buy_cooldown(datetime.now(timezone.utc), 0.0)
            print(f"[Inn20] throttle reset via nonce={new_nonce}: fail_streak=0, throttle=1.0")
        self.preferred_symbol_fast_lane_enabled = bool(runtime.get("preferred_symbol_fast_lane_enabled", self.preferred_symbol_fast_lane_enabled))
        self.preferred_symbol_fast_lane_min_alpha = self._clamp(
            self._to_float(runtime.get("preferred_symbol_fast_lane_min_alpha", self.preferred_symbol_fast_lane_min_alpha), self.preferred_symbol_fast_lane_min_alpha), 0.0, 50.0)
        # Innovation 21: Equity-Scaled Compounding Cap
        self.inn21_equity_scale_enabled = bool(runtime.get("inn21_equity_scale_enabled", self.inn21_equity_scale_enabled))
        self.inn21_equity_scale_pct = self._clamp(
            self._to_float(runtime.get("inn21_equity_scale_pct", self.inn21_equity_scale_pct), self.inn21_equity_scale_pct), 0.02, 0.50)
        self.inn21_equity_scale_min_cap = self._clamp(
            self._to_float(runtime.get("inn21_equity_scale_min_cap", self.inn21_equity_scale_min_cap), self.inn21_equity_scale_min_cap), 1.0, 500.0)
        self.inn21_equity_scale_hard_max = self._clamp(
            self._to_float(runtime.get("inn21_equity_scale_hard_max", self.inn21_equity_scale_hard_max), self.inn21_equity_scale_hard_max), 10.0, 50000.0)
        # Innovation 22: Moonshot Long-Hold TP Amplifier
        self.inn22_moonshot_tp_enabled = bool(runtime.get("inn22_moonshot_tp_enabled", self.inn22_moonshot_tp_enabled))
        self.inn22_moonshot_tp_bps = self._clamp(
            self._to_float(runtime.get("inn22_moonshot_tp_bps", self.inn22_moonshot_tp_bps), self.inn22_moonshot_tp_bps), 50.0, 50000.0)
        self.inn22_moonshot_max_hold_sec = self._clamp(
            self._to_float(runtime.get("inn22_moonshot_max_hold_sec", self.inn22_moonshot_max_hold_sec), self.inn22_moonshot_max_hold_sec), 60.0, 86400.0)
        self.inn22_moonshot_trail_activation_bps = self._clamp(
            self._to_float(runtime.get("inn22_moonshot_trail_activation_bps", self.inn22_moonshot_trail_activation_bps), self.inn22_moonshot_trail_activation_bps), 10.0, 5000.0)
        self.inn22_moonshot_trail_bps = self._clamp(
            self._to_float(runtime.get("inn22_moonshot_trail_bps", self.inn22_moonshot_trail_bps), self.inn22_moonshot_trail_bps), 5.0, 2000.0)
        # ══════════════════════════════════════════════════════════════════════
        self.live_operator_queue_enabled = bool(
            runtime.get("live_operator_queue_enabled", self.live_operator_queue_enabled)
        )
        self.live_operator_queue_max_candidates = int(
            self._clamp(
                self._to_float(
                    runtime.get("live_operator_queue_max_candidates", self.live_operator_queue_max_candidates),
                    self.live_operator_queue_max_candidates,
                ),
                1.0,
                20.0,
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

    def _hybrid_swing_metrics_from_ticker(self, ticker: Optional[dict[str, Any]], spread_bps: float) -> dict[str, float | bool]:
        if not isinstance(ticker, dict):
            return {
                "eligible": False,
                "hybrid_score": -float("inf"),
                "range_pct": 0.0,
                "momentum_pct": 0.0,
                "position_in_range": 0.0,
                "activity_score": 0.0,
                "trade_count_24h": 0.0,
                "long_bias_pass": False,
                "long_bias_penalty_bps": 0.0,
                "vwap_deviation_pct": 0.0,
                "obi": 0.0,
                "conviction_score": 0.0,
                "regime_bull": False,
                "regime_bear": False,
            }

        last_px = max(self._to_float(ticker.get("last", 0.0), 0.0), 0.0)
        open_px = max(self._to_float(ticker.get("open", last_px), last_px), 0.0)
        high_24h = max(self._to_float(ticker.get("high_24h", last_px), last_px), 0.0)
        low_24h = max(self._to_float(ticker.get("low_24h", last_px), last_px), 0.0)
        trade_count_24h = max(self._to_float(ticker.get("trade_count_24h", 0.0), 0.0), 0.0)
        vwap_24h = max(self._to_float(ticker.get("vwap_24h", 0.0), 0.0), 0.0)
        bid_qty = max(self._to_float(ticker.get("bid_qty", 0.0), 0.0), 0.0)
        ask_qty = max(self._to_float(ticker.get("ask_qty", 0.0), 0.0), 0.0)
        volume_24h = max(self._to_float(ticker.get("volume_24h", 0.0), 0.0), 0.0)

        if last_px <= 0.0 or low_24h <= 0.0:
            return {
                "eligible": False,
                "hybrid_score": -float("inf"),
                "range_pct": 0.0,
                "momentum_pct": 0.0,
                "position_in_range": 0.0,
                "activity_score": 0.0,
                "trade_count_24h": trade_count_24h,
                "long_bias_pass": False,
                "long_bias_penalty_bps": 0.0,
                "vwap_deviation_pct": 0.0,
                "obi": 0.0,
                "conviction_score": 0.0,
                "regime_bull": False,
                "regime_bear": False,
            }

        high_24h = max(high_24h, low_24h)
        range_span = max(high_24h - low_24h, 1e-9)
        range_pct = ((high_24h - low_24h) / max(low_24h, 1e-9)) * 100.0
        momentum_pct = ((last_px - open_px) / max(open_px, 1e-9)) * 100.0 if open_px > 0.0 else 0.0
        position_in_range = max(min((last_px - low_24h) / range_span, 1.0), 0.0)
        activity_score = max(min(math.log10(trade_count_24h + 1.0) / 4.5, 1.0), 0.0)

        # ── Order Book Imbalance (OBI) — microstructure buy/sell pressure ─────
        # OBI ∈ [-1, +1]: +1 = pure bid pressure, -1 = pure ask pressure
        _obi_total = bid_qty + ask_qty
        obi = (bid_qty - ask_qty) / max(_obi_total, 1e-9) if _obi_total > 0.0 else 0.0
        obi_filter_pass = (
            not self.hybrid_swing_obi_filter_enabled
            or _obi_total <= 0.0   # skip filter if qty data unavailable
            or obi >= float(self.hybrid_swing_min_obi)
        )
        # ── Volume Conviction Score — per-trade institutional size proxy ───────
        # avg_trade_size_usd: larger = more institutional activity per trade
        # Log-normalize: [10 USD .. 10M USD] → [0.0 .. 1.0]
        avg_trade_usd = (volume_24h * last_px) / max(trade_count_24h, 1.0)
        conviction_score = max(min((math.log10(max(avg_trade_usd, 1.0)) - 1.0) / 6.0, 1.0), 0.0)

        # ── Market Regime Filter ──────────────────────────────────────────────
        # Uses 24h price structure (no external data needed)
        # Bull: price above 24h midpoint AND positive session momentum
        # Bear: price below 24h midpoint AND momentum below bear threshold
        _mid_24h = (high_24h + low_24h) / 2.0
        _regime_bull = bool(last_px >= _mid_24h and momentum_pct >= 0.0)
        _regime_bear = bool(last_px < _mid_24h and momentum_pct < float(self.hybrid_swing_regime_bear_momentum_pct))
        regime_filter_pass = (
            not self.hybrid_swing_regime_filter_enabled
            or not _regime_bear
        )
        _regime_bull_bonus = float(self.hybrid_swing_regime_bull_bonus) if _regime_bull else 0.0

        long_bias_enabled = bool(self.hybrid_swing_long_bias_enabled and (not self.spot_short_enabled))
        momentum_deficit = (
            max(float(self.hybrid_swing_long_bias_min_momentum_pct) - float(momentum_pct), 0.0)
            if long_bias_enabled
            else 0.0
        )
        long_bias_penalty_bps = momentum_deficit * float(self.hybrid_swing_long_bias_penalty_per_pct)
        long_bias_pass = (not long_bias_enabled) or momentum_deficit <= 0.0

        # ── VWAP institutional entry filter ────────────────────────────────────
        vwap_deviation_pct = 0.0
        vwap_filter_pass = True
        if vwap_24h > 0.0 and self.hybrid_swing_vwap_filter_enabled:
            vwap_deviation_pct = ((last_px - vwap_24h) / vwap_24h) * 100.0
            vwap_filter_pass = vwap_deviation_pct <= float(self.hybrid_swing_vwap_max_deviation_pct)

        eligible = bool(
            spread_bps <= float(self.hybrid_swing_spread_guard_bps)
            and range_pct >= float(self.hybrid_swing_min_range_pct)
            and momentum_pct >= float(self.hybrid_swing_min_momentum_pct)
            and position_in_range <= float(self.hybrid_swing_max_entry_range_position)  # don't buy in top of range
            and long_bias_pass
            and vwap_filter_pass   # institutional: only enter near/below VWAP
            and obi_filter_pass    # microstructure: only enter when bid pressure >= ask pressure
            and regime_filter_pass # macro: block entries in confirmed bear regime
        )
        # VWAP score penalty: decays the more price overshoots VWAP above tolerance
        vwap_score_adj = -max(vwap_deviation_pct, 0.0) * 2.0 if vwap_24h > 0.0 else 0.0
        hybrid_score = (
            (range_pct * float(self.hybrid_swing_range_weight))
            + (momentum_pct * float(self.hybrid_swing_momentum_weight))
            + (((1.0 - position_in_range) * 10.0) * float(self.hybrid_swing_position_weight))  # inverted: reward buying near LOW of range
            + ((activity_score * 10.0) * float(self.hybrid_swing_activity_weight))
            - (spread_bps * float(self.hybrid_swing_spread_penalty))
            - float(long_bias_penalty_bps)
            + vwap_score_adj
            + (obi * 3.0 * float(self.hybrid_swing_obi_weight))          # +3 pts at max bid pressure
            + (conviction_score * 5.0 * float(self.hybrid_swing_conviction_weight))  # +5 pts at max institutional conviction
            + _regime_bull_bonus               # +bull_bonus pts in confirmed bull regime
        )

        return {
            "eligible": bool(eligible),
            "hybrid_score": float(hybrid_score),
            "range_pct": float(range_pct),
            "momentum_pct": float(momentum_pct),
            "position_in_range": float(position_in_range),
            "activity_score": float(activity_score),
            "trade_count_24h": float(trade_count_24h),
            "long_bias_pass": bool(long_bias_pass),
            "long_bias_penalty_bps": float(long_bias_penalty_bps),
            "vwap_deviation_pct": float(vwap_deviation_pct),
            "obi": float(obi),
            "conviction_score": float(conviction_score),
            "regime_bull": _regime_bull,
            "regime_bear": _regime_bear,
        }

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

    def _symbol_alpha_score_for_symbol(self, symbol: str, direction: str = "long") -> tuple[Optional[float], str]:
        symbol_key = str(symbol or "").upper().strip()
        if not symbol_key:
            return None, "missing_symbol"

        payload = self._load_symbol_flip_intel_payload()
        if not isinstance(payload, dict):
            return None, "missing_payload"

        direction_key = str(direction or "").strip().lower()
        if direction_key == "short":
            preferred_fields = ("alpha_short_score", "alpha_long_score")
        else:
            preferred_fields = ("alpha_long_score", "alpha_short_score")

        best_score = -float("inf")
        best_source = "not_found"
        candidate_sets = (
            ("long_candidates", payload.get("long_candidates", [])),
            ("short_candidates", payload.get("short_candidates", [])),
            ("focus_symbols", payload.get("focus_symbols", [])),
        )
        for source_name, rows in candidate_sets:
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                row_symbol = str(row.get("symbol", "") or "").upper().strip()
                if row_symbol != symbol_key:
                    continue

                for field in preferred_fields:
                    score = self._to_float(row.get(field, float("nan")), float("nan"))
                    if math.isfinite(score):
                        return float(score), f"{source_name}.{field}"

                fallback = self._to_float(row.get("alpha_score", float("nan")), float("nan"))
                if math.isfinite(fallback) and float(fallback) > float(best_score):
                    best_score = float(fallback)
                    best_source = f"{source_name}.alpha_score"

        if math.isfinite(best_score):
            return float(best_score), best_source
        return None, "not_found"

    def _load_symbol_learning_payload(self) -> dict[str, Any]:
        now_ts = time.time()
        if self._symbol_learning_cache and (now_ts - self._symbol_learning_cache_utc) <= 10.0:
            return dict(self._symbol_learning_cache)

        payload = load_json(SYMBOL_FLIP_LEARNING_FILE, {})
        if not isinstance(payload, dict):
            payload = {}

        self._symbol_learning_cache = dict(payload)
        self._symbol_learning_cache_utc = now_ts
        return dict(payload)

    def _symbol_learning_bonus_map(self) -> tuple[dict[str, float], dict[str, Any]]:
        meta: dict[str, Any] = {
            "symbol_learning_enabled": bool(self.symbol_intel_learning_enabled),
            "symbol_learning_file_exists": bool(SYMBOL_FLIP_LEARNING_FILE.exists()),
            "symbol_learning_stale": False,
            "symbol_learning_age_sec": None,
            "symbol_learning_profile_count": 0,
            "symbol_learning_bonus_count": 0,
            "symbol_learning_source": "none",
        }

        if not self.symbol_intel_learning_enabled:
            meta["symbol_learning_source"] = "disabled"
            return {}, meta

        payload = self._load_symbol_learning_payload()
        if not payload:
            meta["symbol_learning_source"] = "empty"
            return {}, meta

        generated_utc = str(payload.get("generated_utc", "") or "")
        age_sec = float("inf")
        if generated_utc:
            try:
                generated_dt = self._parse_iso_utc(generated_utc)
                age_sec = max((datetime.now(timezone.utc) - generated_dt).total_seconds(), 0.0)
            except Exception:
                age_sec = float("inf")

        if math.isfinite(age_sec):
            meta["symbol_learning_age_sec"] = round(float(age_sec), 3)

        if math.isfinite(age_sec) and age_sec > float(self.symbol_intel_learning_max_age_sec):
            meta["symbol_learning_stale"] = True
            meta["symbol_learning_source"] = "stale"
            return {}, meta

        rows = payload.get("symbol_profiles", []) if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            rows = []

        bonus_map: dict[str, float] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue

            symbol = str(row.get("symbol", "") or "").upper().strip()
            if not symbol:
                continue

            learned_long = self._to_float(row.get("learned_long_score", 0.0), 0.0)
            learned_short = self._to_float(row.get("learned_short_score", 0.0), 0.0)
            dominant_bias = str(row.get("dominant_bias", "long") or "long").strip().lower()
            dominant_score = max(learned_long, learned_short)
            if dominant_score <= 0.0:
                continue

            effective_score = float(dominant_score)
            if dominant_bias == "short" and (not self.spot_short_enabled):
                # Keep some signal value for volatility awareness but dampen short-only alpha on spot.
                effective_score = max(float(learned_long), float(dominant_score) * 0.25)

            bonus = min(
                max(float(effective_score), 0.0) * float(self.symbol_intel_learning_weight),
                float(self.symbol_intel_learning_max_bonus),
            )
            if bonus <= 0.0:
                continue
            existing = bonus_map.get(symbol, 0.0)
            if bonus > existing:
                bonus_map[symbol] = float(bonus)

        meta["symbol_learning_profile_count"] = int(len(rows))
        meta["symbol_learning_bonus_count"] = int(len(bonus_map))
        meta["symbol_learning_source"] = "learning_profile"
        return bonus_map, meta

    def _symbol_flip_intel_candidates(self) -> tuple[list[str], dict[str, Any]]:
        meta: dict[str, Any] = {
            "symbol_intel_enabled": bool(self.symbol_intel_enabled),
            "symbol_intel_file_exists": bool(SYMBOL_FLIP_INTEL_FILE.exists()),
            "symbol_intel_stale": False,
            "symbol_intel_age_sec": None,
            "symbol_intel_candidate_count": 0,
            "symbol_intel_selected_count": 0,
            "symbol_intel_executable_count": 0,
            "symbol_intel_short_candidate_count": 0,
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

        short_candidates = payload.get("short_candidates", []) if isinstance(payload, dict) else []
        if bool(self.spot_short_enabled) and isinstance(short_candidates, list):
            ranked_short = sorted(
                [row for row in short_candidates if isinstance(row, dict)],
                key=lambda row: self._to_float(row.get("alpha_short_score", 0.0), 0.0),
                reverse=True,
            )
            short_added = 0
            for row in ranked_short:
                score = self._to_float(row.get("alpha_short_score", 0.0), 0.0)
                if score < float(self.symbol_intel_min_alpha_score):
                    continue
                symbol = str(row.get("symbol", "") or "").upper().strip()
                if symbol:
                    picks.append(symbol)
                    short_added += 1
            meta["symbol_intel_short_candidate_count"] = int(short_added)

        focus_symbols = payload.get("focus_symbols", []) if isinstance(payload, dict) else []
        if isinstance(focus_symbols, list):
            for row in focus_symbols:
                symbol = str(row or "").upper().strip()
                if symbol:
                    picks.append(symbol)

        deduped = list(dict.fromkeys(picks))
        if int(self.symbol_intel_prefer_top_n) <= 0:
            limited = list(deduped)
        else:
            limited = deduped[: int(self.symbol_intel_prefer_top_n)]

        meta["symbol_intel_candidate_count"] = int(len(deduped))
        meta["symbol_intel_selected_count"] = int(len(limited))
        meta["symbol_intel_executable_count"] = int(len(limited))
        meta["symbol_intel_source"] = "symbol_flip_intel_top5"
        return limited, meta

    @staticmethod
    def _read_jsonl_tail(path: Path, max_rows: int) -> list[dict[str, Any]]:
        limit = max(int(max_rows), 1)
        if not path.exists():
            return []

        lines: deque[str] = deque(maxlen=limit)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    raw = line.strip()
                    if raw:
                        lines.append(raw)
        except Exception:
            return []

        out: list[dict[str, Any]] = []
        for raw in reversed(lines):
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            if isinstance(payload, dict):
                out.append(payload)
        return out

    def _edge_proof_recent_quality(self, now: datetime) -> dict[str, Any]:
        now_ts = time.time()
        if self._edge_proof_cache and (now_ts - float(self._edge_proof_cache_utc)) <= float(self.edge_proof_cache_ttl_sec):
            return dict(self._edge_proof_cache)

        target = max(int(self.edge_proof_recent_closed_trades), 1)
        scan_rows = int(self._clamp(float(target * 60), 120.0, 8000.0))
        rows = self._read_jsonl_tail(LIVE_TRADE_LEDGER_JSONL_FILE, scan_rows)

        close_statuses = {
            "CLOSED",
            "CAPITAL_RECYCLE_CLOSED",
            "TP_FILLED",
            "SL_FILLED",
        }
        closed_rows: list[dict[str, Any]] = []
        for row in rows:
            status = str(row.get("status", "") or "").upper().strip()
            if status not in close_statuses:
                continue
            closed_rows.append(row)
            if len(closed_rows) >= target:
                break

        pnl_values: list[float] = []
        wins = 0
        for row in closed_rows:
            pnl_pct = self._to_float(row.get("pnl_pct", float("nan")), float("nan"))
            if not math.isfinite(pnl_pct):
                entry_px = self._to_float(row.get("entry_price", 0.0), 0.0)
                exit_px = self._to_float(row.get("exit_price", 0.0), 0.0)
                if entry_px > 0.0 and exit_px > 0.0:
                    direction = str(row.get("direction", "long") or "long").strip().lower()
                    if direction == "short":
                        pnl_pct = ((entry_px - exit_px) / entry_px) * 100.0
                    else:
                        pnl_pct = ((exit_px - entry_px) / entry_px) * 100.0
                else:
                    pnl_pct = 0.0
            pnl_values.append(float(pnl_pct))
            if float(pnl_pct) > 0.0:
                wins += 1

        recent_closed_count = int(len(closed_rows))
        win_rate_pct = (float(wins) / float(recent_closed_count) * 100.0) if recent_closed_count > 0 else 0.0
        avg_pnl_pct = (sum(float(v) for v in pnl_values) / float(recent_closed_count)) if recent_closed_count > 0 else 0.0

        last_close_age_min: Optional[float] = None
        if closed_rows:
            newest = closed_rows[0]
            newest_ts = str(newest.get("timestamp") or newest.get("logged_utc") or "").strip()
            if newest_ts:
                try:
                    ts = self._parse_iso_utc(newest_ts)
                    last_close_age_min = max((now - ts).total_seconds() / 60.0, 0.0)
                except Exception:
                    last_close_age_min = None

        pass_recent_closes = recent_closed_count >= target
        pass_win_rate = float(win_rate_pct) >= float(self.edge_proof_min_win_rate_pct)
        pass_avg_pnl = float(avg_pnl_pct) >= float(self.edge_proof_min_avg_pnl_pct)
        pass_freshness = (
            (last_close_age_min is not None)
            and (float(last_close_age_min) <= float(self.edge_proof_max_last_close_age_min))
        )

        payload = {
            "recent_closed_count": int(recent_closed_count),
            "target_closed_count": int(target),
            "win_rate_pct": round(float(win_rate_pct), 6),
            "avg_pnl_pct": round(float(avg_pnl_pct), 6),
            "last_close_age_min": round(float(last_close_age_min), 6) if last_close_age_min is not None else None,
            "pass_recent_closes": bool(pass_recent_closes),
            "pass_win_rate": bool(pass_win_rate),
            "pass_avg_pnl": bool(pass_avg_pnl),
            "pass_freshness": bool(pass_freshness),
        }

        self._edge_proof_cache = dict(payload)
        self._edge_proof_cache_utc = now_ts
        return payload

    def _capital_preservation_snapshot(
        self,
        now: datetime,
        quality: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        payload_quality = quality if isinstance(quality, dict) else self._edge_proof_recent_quality(now)

        required_recent_closed = max(int(self.capital_preservation_min_recent_closed), 1)
        recent_closed_count = int(self._to_float(payload_quality.get("recent_closed_count", 0), 0.0))
        win_rate_pct = self._to_float(payload_quality.get("win_rate_pct", 0.0), 0.0)
        avg_pnl_pct = self._to_float(payload_quality.get("avg_pnl_pct", 0.0), 0.0)

        scan_rows = int(self._clamp(float(required_recent_closed * 45), 120.0, 8000.0))
        rows = self._read_jsonl_tail(LIVE_TRADE_LEDGER_JSONL_FILE, scan_rows)
        close_statuses = {
            "CLOSED",
            "CAPITAL_RECYCLE_CLOSED",
            "TP_FILLED",
            "SL_FILLED",
        }
        consecutive_losses = 0
        for row in rows:
            status = str(row.get("status", "") or "").upper().strip()
            if status not in close_statuses:
                continue

            pnl_pct = self._to_float(row.get("pnl_pct", float("nan")), float("nan"))
            if not math.isfinite(pnl_pct):
                entry_px = self._to_float(row.get("entry_price", 0.0), 0.0)
                exit_px = self._to_float(row.get("exit_price", 0.0), 0.0)
                if entry_px > 0.0 and exit_px > 0.0:
                    direction = str(row.get("direction", "long") or "long").strip().lower()
                    if direction == "short":
                        pnl_pct = ((entry_px - exit_px) / entry_px) * 100.0
                    else:
                        pnl_pct = ((exit_px - entry_px) / entry_px) * 100.0
                else:
                    pnl_pct = 0.0

            if float(pnl_pct) > 0.0:
                break
            consecutive_losses += 1
            if consecutive_losses >= int(self.capital_preservation_max_consecutive_losses):
                break

        pause_until_dt: Optional[datetime] = None
        pause_raw = str(self.capital_preservation_pause_until_utc or "").strip()
        if pause_raw:
            try:
                pause_until_dt = self._parse_iso_utc(pause_raw)
            except Exception:
                pause_until_dt = None

        if isinstance(pause_until_dt, datetime) and now >= pause_until_dt:
            self.capital_preservation_pause_until_utc = ""
            pause_until_dt = None

        breach_codes: list[str] = []
        if recent_closed_count >= required_recent_closed:
            if float(win_rate_pct) < float(self.capital_preservation_min_win_rate_pct):
                breach_codes.append("low_recent_win_rate")
            if float(avg_pnl_pct) < float(self.capital_preservation_min_avg_pnl_pct):
                breach_codes.append("low_recent_avg_pnl")
        if consecutive_losses >= int(self.capital_preservation_max_consecutive_losses):
            breach_codes.append("loss_streak")

        if breach_codes and (pause_until_dt is None):
            pause_until_dt = now + timedelta(seconds=float(self.capital_preservation_pause_sec))
            self.capital_preservation_pause_until_utc = pause_until_dt.isoformat()

        pause_active = isinstance(pause_until_dt, datetime)
        allow_buy = (not pause_active) and (len(breach_codes) == 0)

        return {
            "enabled": bool(self.capital_preservation_mode),
            "recent_closed_count": int(recent_closed_count),
            "required_recent_closed": int(required_recent_closed),
            "win_rate_pct": round(float(win_rate_pct), 6),
            "avg_pnl_pct": round(float(avg_pnl_pct), 6),
            "consecutive_losses": int(consecutive_losses),
            "max_consecutive_losses": int(self.capital_preservation_max_consecutive_losses),
            "min_win_rate_pct": round(float(self.capital_preservation_min_win_rate_pct), 6),
            "min_avg_pnl_pct": round(float(self.capital_preservation_min_avg_pnl_pct), 6),
            "pause_sec": round(float(self.capital_preservation_pause_sec), 6),
            "pause_until_utc": pause_until_dt.isoformat() if isinstance(pause_until_dt, datetime) else None,
            "pause_active": bool(pause_active),
            "breach_codes": list(breach_codes),
            "allow_buy": bool(allow_buy),
        }

    def _edge_proof_cost_floor_adaptive_adjustment(self, quality: dict[str, Any]) -> dict[str, Any]:
        avg_pnl_pct = self._to_float(quality.get("avg_pnl_pct", 0.0), 0.0)
        win_rate_pct = self._to_float(quality.get("win_rate_pct", 0.0), 0.0)
        recent_closed_count = int(self._to_float(quality.get("recent_closed_count", 0), 0.0))
        avg_net_pnl_bps = float(avg_pnl_pct) * 100.0

        out: dict[str, Any] = {
            "enabled": bool(self.edge_proof_cost_floor_adaptive_enabled),
            "recent_closed_count": int(recent_closed_count),
            "avg_net_pnl_bps": round(float(avg_net_pnl_bps), 6),
            "win_rate_pct": round(float(win_rate_pct), 6),
            "adjust_bps": 0.0,
            "reason": "disabled",
        }

        if not bool(self.edge_proof_cost_floor_adaptive_enabled):
            return out

        min_closed = max(int(self.edge_proof_cost_floor_adaptive_min_closed_trades), 1)
        if recent_closed_count < min_closed:
            out["reason"] = "insufficient_samples"
            return out

        tighten = (
            float(avg_net_pnl_bps) <= float(self.edge_proof_cost_floor_adaptive_loss_threshold_bps)
            or float(win_rate_pct) < float(self.edge_proof_cost_floor_adaptive_win_rate_floor_pct)
        )
        relax = (
            float(avg_net_pnl_bps) >= float(self.edge_proof_cost_floor_adaptive_gain_threshold_bps)
            and float(win_rate_pct) >= float(self.edge_proof_cost_floor_adaptive_win_rate_relax_pct)
        )

        if tighten:
            out["adjust_bps"] = round(float(self.edge_proof_cost_floor_adaptive_loss_adjust_bps), 6)
            out["reason"] = "tighten"
            return out
        if relax:
            out["adjust_bps"] = round(-abs(float(self.edge_proof_cost_floor_adaptive_gain_adjust_bps)), 6)
            out["reason"] = "relax"
            return out

        out["reason"] = "hold"
        return out

    def _edge_proof_decision(self, now: datetime, selection_meta: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        quality = self._edge_proof_recent_quality(now)
        payload = dict(quality)
        payload["enabled"] = bool(self.edge_proof_enabled)
        adaptive_adjust_meta = self._edge_proof_cost_floor_adaptive_adjustment(quality)
        adaptive_adjust_bps = self._to_float(adaptive_adjust_meta.get("adjust_bps", 0.0), 0.0)
        payload["edge_proof_cost_floor_adaptive_enabled"] = bool(adaptive_adjust_meta.get("enabled", False))
        payload["edge_proof_cost_floor_adaptive_reason"] = str(adaptive_adjust_meta.get("reason", "disabled") or "disabled")
        payload["edge_proof_cost_floor_adaptive_adjust_bps"] = round(float(adaptive_adjust_bps), 6)
        payload["edge_proof_cost_floor_adaptive_avg_net_pnl_bps"] = round(
            float(self._to_float(adaptive_adjust_meta.get("avg_net_pnl_bps", 0.0), 0.0)),
            6,
        )
        payload["edge_proof_cost_floor_adaptive_recent_closed_count"] = int(
            self._to_float(adaptive_adjust_meta.get("recent_closed_count", 0), 0.0)
        )
        payload["edge_proof_cost_floor_adaptive_win_rate_pct"] = round(
            float(self._to_float(adaptive_adjust_meta.get("win_rate_pct", 0.0), 0.0)),
            6,
        )

        meta = selection_meta if isinstance(selection_meta, dict) else {}
        intel_source = str(meta.get("symbol_intel_source", "none") or "none")
        intel_stale = bool(meta.get("symbol_intel_stale", False))
        intel_selected_count = int(self._to_float(meta.get("symbol_intel_selected_count", 0), 0.0))
        symbol_source = str(meta.get("symbol_source", "none") or "none")
        approval_candidate_count = int(self._to_float(meta.get("approval_candidate_count", 0), 0.0))
        gate_score = self._to_float(meta.get("gate_composite_score", 0.0), 0.0)
        gate_expected_edge_bps = self._to_float(meta.get("gate_expected_edge_bps", 0.0), 0.0)
        selected_hybrid_score = self._to_float(meta.get("selected_hybrid_score", -float("inf")), -float("inf"))
        selected_momentum_pct = self._to_float(meta.get("selected_momentum_pct", -999.0), -999.0)
        selected_spread_bps = self._to_float(meta.get("selected_spread_bps", float("inf")), float("inf"))
        selected_symbol = str(meta.get("selected_symbol", "") or "").upper().strip()
        gate_direction = str(meta.get("gate_direction", "long") or "long").strip().lower()
        selected_learning_bonus = max(self._to_float(meta.get("selected_learning_bonus", 0.0), 0.0), 0.0)

        alpha_symbol_score, alpha_symbol_source = self._symbol_alpha_score_for_symbol(selected_symbol, gate_direction)
        alpha_learning_component = float(selected_learning_bonus) * float(self.alpha_lock_learning_bonus_weight)
        alpha_intel_score = None
        if alpha_symbol_score is not None and math.isfinite(float(alpha_symbol_score)):
            alpha_intel_score = max(float(alpha_symbol_score), 0.0) + float(alpha_learning_component)

        alpha_hybrid_score = None
        if bool(self.alpha_lock_allow_hybrid_fallback) and math.isfinite(selected_hybrid_score):
            alpha_hybrid_score = max(float(selected_hybrid_score), 0.0) * float(self.alpha_lock_hybrid_score_weight)

        alpha_candidates: list[float] = []
        if alpha_intel_score is not None:
            alpha_candidates.append(float(alpha_intel_score))
        if alpha_hybrid_score is not None:
            alpha_candidates.append(float(alpha_hybrid_score))

        alpha_effective_score = max(alpha_candidates) if alpha_candidates else -float("inf")
        alpha_hybrid_fallback_used = alpha_intel_score is None and alpha_hybrid_score is not None
        pass_alpha_gate_score = float(gate_score) >= float(self.alpha_lock_min_gate_score)
        pass_alpha_expected_edge = float(gate_expected_edge_bps) >= float(self.alpha_lock_min_expected_edge_bps)
        pass_alpha_score = math.isfinite(alpha_effective_score) and float(alpha_effective_score) >= float(
            self.alpha_lock_min_score
        )

        alpha_lock_reason_codes: list[str] = []
        alpha_gate_only_fallback_applied = False
        pass_alpha_lock = True
        if bool(self.alpha_lock_enabled):
            if not pass_alpha_gate_score:
                alpha_lock_reason_codes.append("alpha_gate_score_too_low")
            if not pass_alpha_expected_edge:
                alpha_lock_reason_codes.append("alpha_expected_edge_too_low")
            if not pass_alpha_score:
                alpha_lock_reason_codes.append("alpha_score_too_low")

            pass_alpha_lock = len(alpha_lock_reason_codes) == 0
            if (
                (not pass_alpha_lock)
                and bool(self.alpha_lock_allow_gate_only_fallback)
                and pass_alpha_gate_score
                and pass_alpha_expected_edge
            ):
                pass_alpha_lock = True
                alpha_gate_only_fallback_applied = True
                alpha_lock_reason_codes = []

        self.edge_proof_bootstrap_entry_utc = [
            ts
            for ts in self.edge_proof_bootstrap_entry_utc
            if isinstance(ts, datetime) and (now - ts).total_seconds() <= 3600.0
        ]
        bootstrap_recent_entries_1h = int(len(self.edge_proof_bootstrap_entry_utc))

        pass_symbol_intel = True
        if self.edge_proof_require_symbol_intel_fresh:
            pass_symbol_intel = (
                intel_source not in {"none", "disabled", "empty", "stale"}
                and (not intel_stale)
                and intel_selected_count > 0
            )

        intel_fallback_applied = False
        if (
            (not pass_symbol_intel)
            and bool(self.edge_proof_hybrid_fallback_for_symbol_intel)
            and symbol_source.startswith("hybrid_swing")
            and approval_candidate_count > 0
        ):
            pass_symbol_intel = True
            intel_fallback_applied = True

        payload["pass_symbol_intel"] = bool(pass_symbol_intel)
        payload["symbol_intel_source"] = intel_source
        payload["symbol_intel_selected_count"] = int(intel_selected_count)
        payload["symbol_intel_stale"] = bool(intel_stale)
        payload["symbol_source"] = symbol_source
        payload["approval_candidate_count"] = int(approval_candidate_count)
        payload["edge_proof_hybrid_fallback_for_symbol_intel"] = bool(self.edge_proof_hybrid_fallback_for_symbol_intel)
        payload["edge_proof_symbol_intel_fallback_applied"] = bool(intel_fallback_applied)
        payload["edge_proof_bootstrap_enabled"] = bool(self.edge_proof_bootstrap_enabled)
        payload["edge_proof_bootstrap_recent_entries_1h"] = int(bootstrap_recent_entries_1h)
        payload["edge_proof_bootstrap_max_entries_per_hour"] = int(self.edge_proof_bootstrap_max_entries_per_hour)
        payload["edge_proof_bootstrap_gate_score"] = round(float(gate_score), 6)
        payload["edge_proof_bootstrap_expected_edge_bps"] = round(float(gate_expected_edge_bps), 6)
        payload["edge_proof_bootstrap_selected_hybrid_score"] = (
            round(float(selected_hybrid_score), 6) if math.isfinite(selected_hybrid_score) else None
        )
        payload["edge_proof_bootstrap_selected_momentum_pct"] = round(float(selected_momentum_pct), 6)
        payload["edge_proof_bootstrap_selected_spread_bps"] = (
            round(float(selected_spread_bps), 6) if math.isfinite(selected_spread_bps) else None
        )
        payload["edge_proof_bootstrap_hybrid_edge_scale"] = round(float(self.edge_proof_bootstrap_hybrid_edge_scale), 6)
        payload["edge_proof_bootstrap_require_hybrid_candidates"] = bool(
            self.edge_proof_bootstrap_require_hybrid_candidates
        )
        payload["alpha_lock_enabled"] = bool(self.alpha_lock_enabled)
        payload["alpha_lock_selected_symbol"] = selected_symbol
        payload["alpha_lock_direction"] = gate_direction
        payload["alpha_lock_gate_score"] = round(float(gate_score), 6)
        payload["alpha_lock_expected_edge_bps"] = round(float(gate_expected_edge_bps), 6)
        payload["alpha_lock_symbol_alpha_source"] = str(alpha_symbol_source or "not_found")
        payload["alpha_lock_symbol_alpha_score"] = (
            round(float(alpha_symbol_score), 6) if alpha_symbol_score is not None else None
        )
        payload["alpha_lock_learning_bonus"] = round(float(selected_learning_bonus), 6)
        payload["alpha_lock_learning_component"] = round(float(alpha_learning_component), 6)
        payload["alpha_lock_hybrid_score"] = round(float(alpha_hybrid_score), 6) if alpha_hybrid_score is not None else None
        payload["alpha_lock_effective_score"] = (
            round(float(alpha_effective_score), 6) if math.isfinite(alpha_effective_score) else None
        )
        payload["alpha_lock_min_gate_score"] = round(float(self.alpha_lock_min_gate_score), 6)
        payload["alpha_lock_min_expected_edge_bps"] = round(float(self.alpha_lock_min_expected_edge_bps), 6)
        payload["alpha_lock_min_score"] = round(float(self.alpha_lock_min_score), 6)
        payload["alpha_lock_allow_hybrid_fallback"] = bool(self.alpha_lock_allow_hybrid_fallback)
        payload["alpha_lock_allow_gate_only_fallback"] = bool(self.alpha_lock_allow_gate_only_fallback)
        payload["alpha_lock_hybrid_fallback_used"] = bool(alpha_hybrid_fallback_used)
        payload["alpha_lock_gate_only_fallback_applied"] = bool(alpha_gate_only_fallback_applied)
        payload["pass_alpha_lock"] = bool(pass_alpha_lock)
        payload["alpha_lock_reason_codes"] = list(alpha_lock_reason_codes)

        reason_codes: list[str] = []
        if not bool(payload.get("pass_recent_closes", False)):
            reason_codes.append("insufficient_recent_closes")
        if not bool(payload.get("pass_win_rate", False)):
            reason_codes.append("low_recent_win_rate")
        if not bool(payload.get("pass_avg_pnl", False)):
            reason_codes.append("low_recent_avg_pnl")
        if not bool(payload.get("pass_freshness", False)):
            reason_codes.append("stale_recent_closes")
        if not bool(payload.get("pass_symbol_intel", True)):
            reason_codes.append("symbol_intel_not_fresh")
        if not bool(payload.get("pass_alpha_lock", True)):
            reason_codes.append("alpha_lock_not_armed")

        if not self.edge_proof_enabled:
            payload["armed"] = True
            payload["reason"] = "edge_proof_disabled"
            payload["reason_codes"] = []
            payload["bootstrap_applied"] = False
            payload["bootstrap_reason_codes"] = []
            return payload

        armed = len(reason_codes) == 0
        bootstrap_applied = False
        bootstrap_reason_codes: list[str] = []

        if (not armed) and bool(self.edge_proof_bootstrap_enabled):
            soft_reasons = {
                "insufficient_recent_closes",
                "low_recent_win_rate",
                "low_recent_avg_pnl",
                "stale_recent_closes",
                "symbol_intel_not_fresh",
            }
            has_hybrid_context = symbol_source.startswith("hybrid_swing") and approval_candidate_count > 0
            hybrid_edge_bps = 0.0
            if math.isfinite(selected_hybrid_score):
                hybrid_edge_bps = max(float(selected_hybrid_score), 0.0) * float(self.edge_proof_bootstrap_hybrid_edge_scale)
            effective_edge_bps = max(float(gate_expected_edge_bps), float(hybrid_edge_bps))

            spread_for_cost_bps = float(selected_spread_bps) if math.isfinite(selected_spread_bps) else float(
                self.edge_proof_bootstrap_max_spread_bps
            )
            required_edge_bps = float(self.edge_proof_bootstrap_min_expected_edge_bps)
            raw_cost_floor_bps = None
            cost_floor_bps = None
            if bool(self.edge_proof_cost_floor_enabled):
                raw_cost_floor_bps = (
                    float(self.edge_proof_cost_floor_fee_roundtrip_bps)
                    + (float(self.edge_proof_cost_floor_spread_weight) * float(spread_for_cost_bps))
                    + float(self.edge_proof_cost_floor_slippage_roundtrip_bps)
                    + float(self.edge_proof_cost_floor_buffer_bps)
                )
                floor_low = min(float(self.edge_proof_cost_floor_min_bps), float(self.edge_proof_cost_floor_max_bps))
                floor_high = max(float(self.edge_proof_cost_floor_min_bps), float(self.edge_proof_cost_floor_max_bps))
                cost_floor_bps = self._clamp(raw_cost_floor_bps, floor_low, floor_high)
                if adaptive_adjust_bps != 0.0:
                    cost_floor_bps = self._clamp(float(cost_floor_bps) + float(adaptive_adjust_bps), floor_low, floor_high)
                required_edge_bps = max(float(required_edge_bps), float(cost_floor_bps))
            elif adaptive_adjust_bps != 0.0:
                required_edge_bps = max(0.0, float(required_edge_bps) + float(adaptive_adjust_bps))

            payload["edge_proof_bootstrap_hybrid_edge_bps"] = round(float(hybrid_edge_bps), 6)
            payload["edge_proof_bootstrap_effective_edge_bps"] = round(float(effective_edge_bps), 6)
            payload["edge_proof_bootstrap_required_edge_bps"] = round(float(required_edge_bps), 6)
            payload["edge_proof_cost_floor_enabled"] = bool(self.edge_proof_cost_floor_enabled)
            payload["edge_proof_bootstrap_cost_floor_raw_bps"] = (
                round(float(raw_cost_floor_bps), 6) if raw_cost_floor_bps is not None else None
            )
            payload["edge_proof_bootstrap_cost_floor_bps"] = (
                round(float(cost_floor_bps), 6) if cost_floor_bps is not None else None
            )
            if any(code not in soft_reasons for code in reason_codes):
                bootstrap_reason_codes.append("bootstrap_non_soft_reason")
            if bootstrap_recent_entries_1h >= int(self.edge_proof_bootstrap_max_entries_per_hour):
                bootstrap_reason_codes.append("bootstrap_rate_limited")
            if gate_score < float(self.edge_proof_bootstrap_min_gate_score):
                bootstrap_reason_codes.append("bootstrap_gate_score_too_low")
            if effective_edge_bps < float(required_edge_bps):
                bootstrap_reason_codes.append("bootstrap_expected_edge_too_low")
            if has_hybrid_context and selected_hybrid_score < float(self.edge_proof_bootstrap_min_hybrid_score):
                bootstrap_reason_codes.append("bootstrap_hybrid_score_too_low")
            if has_hybrid_context and selected_momentum_pct < float(self.edge_proof_bootstrap_min_momentum_pct):
                bootstrap_reason_codes.append("bootstrap_momentum_too_low")
            if has_hybrid_context and selected_spread_bps > float(self.edge_proof_bootstrap_max_spread_bps):
                bootstrap_reason_codes.append("bootstrap_spread_too_wide")
            if bool(self.edge_proof_bootstrap_require_hybrid_candidates) and (not has_hybrid_context):
                bootstrap_reason_codes.append("bootstrap_missing_hybrid_candidates")

            if len(bootstrap_reason_codes) == 0:
                armed = True
                bootstrap_applied = True

        payload["armed"] = bool(armed)
        if bootstrap_applied:
            payload["reason"] = "edge_proof_bootstrap_override"
        else:
            payload["reason"] = "edge_proof_armed" if armed else "edge_proof_not_armed"
        payload["reason_codes"] = reason_codes
        payload["bootstrap_applied"] = bool(bootstrap_applied)
        payload["bootstrap_reason_codes"] = list(bootstrap_reason_codes)
        return payload

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
            "universe_rotation_cursor": None,
            "universe_ticker_hits": 0,
            "universe_affordability_rejects": 0,
            "universe_hard_spread_rejects": 0,
            "universe_hard_reject_spread_bps": round(float(self.universe_hard_reject_spread_bps), 6),
            "universe_same_symbol_penalty_bps": 0.0,
            "universe_same_symbol_penalty_hits": 0,
            "symbol_source": "none",
            "selected_spread_bps": None,
            "selected_min_order_notional": None,
            "hybrid_swing_enabled": bool(self.hybrid_swing_selector_enabled),
            "selected_hybrid_score": None,
            "selected_momentum_pct": None,
            "selected_range_pct": None,
            "selected_position_in_range": None,
            "selected_trade_count_24h": None,
            "selected_long_bias_penalty_bps": None,
            "hybrid_long_bias_enabled": bool(self.hybrid_swing_long_bias_enabled and (not self.spot_short_enabled)),
            "hybrid_long_bias_min_momentum_pct": round(float(self.hybrid_swing_long_bias_min_momentum_pct), 6),
            "bootstrap_candidate_count": 0,
            "selected_bootstrap_ready": False,
            "approval_candidate_count": 0,
            "approval_candidates": [],
            "symbol_learning_enabled": bool(self.symbol_intel_learning_enabled),
            "symbol_learning_file_exists": bool(SYMBOL_FLIP_LEARNING_FILE.exists()),
            "symbol_learning_source": "none",
            "symbol_learning_stale": False,
            "symbol_learning_age_sec": None,
            "symbol_learning_profile_count": 0,
            "symbol_learning_bonus_count": 0,
            "symbol_learning_bonus_applied_count": 0,
            "selected_learning_bonus": 0.0,
        }

        learning_bonus_map, learning_meta = self._symbol_learning_bonus_map()
        meta["symbol_learning_enabled"] = bool(learning_meta.get("symbol_learning_enabled", False))
        meta["symbol_learning_file_exists"] = bool(learning_meta.get("symbol_learning_file_exists", False))
        meta["symbol_learning_source"] = str(learning_meta.get("symbol_learning_source", "none") or "none")
        meta["symbol_learning_stale"] = bool(learning_meta.get("symbol_learning_stale", False))
        meta["symbol_learning_age_sec"] = learning_meta.get("symbol_learning_age_sec")
        meta["symbol_learning_profile_count"] = int(
            self._to_float(learning_meta.get("symbol_learning_profile_count", 0), 0.0)
        )
        meta["symbol_learning_bonus_count"] = int(
            self._to_float(learning_meta.get("symbol_learning_bonus_count", 0), 0.0)
        )

        if allow_preferred_shortcut and pref and self.router.get_symbol_config(pref):
            meta["symbol_source"] = "preferred"
            return pref, None, meta

        if not unique:
            return None, None, meta

        if not self.universe_spread_scan_enabled:
            picked = random.choice(unique)
            meta["symbol_source"] = "random_scan_disabled"
            return picked, None, meta

        configured_sample_size = int(self.universe_sample_size)
        full_universe_scan = configured_sample_size <= 0
        if full_universe_scan:
            sample_size = len(unique)
            meta["universe_sample_strategy"] = "full_universe"
        else:
            sample_size = min(max(configured_sample_size, 1), len(unique))

        low_balance_mode = bool(
            affordable_usd_hint > 0.0 and affordable_usd_hint <= float(self.low_balance_sample_trigger_usd)
        )
        if (not full_universe_scan) and low_balance_mode and len(unique) > sample_size:
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
            if ranked:
                cursor = int(self.low_balance_rotation_cursor % len(ranked))
                if cursor > 0:
                    ranked = ranked[cursor:] + ranked[:cursor]
                self.low_balance_rotation_cursor = (cursor + 1) % len(ranked)
                meta["universe_rotation_cursor"] = int(cursor)
            configured_ticker_scan_cap = int(self.low_balance_ticker_scan_cap)
            if configured_ticker_scan_cap <= 0:
                ticker_scan_cap = len(ranked)
                meta["universe_sample_strategy"] = "low_balance_full_scan"
            else:
                ticker_scan_cap = min(max(configured_ticker_scan_cap, 1), len(ranked))
                if affordable_usd_hint > 0.0 and affordable_usd_hint <= 2.0 and len(ranked) > ticker_scan_cap:
                    # Rank the full universe by minimum order, but cap ticker lookups to avoid scan stalls.
                    sample_size = max(sample_size, ticker_scan_cap)
                    meta["universe_sample_escalated"] = True
                    meta["universe_sample_strategy"] = "low_balance_ranked_scan"
            sampled = ranked[: min(sample_size, ticker_scan_cap)]
            if meta["universe_sample_strategy"] not in {"low_balance_ranked_scan", "low_balance_full_scan"}:
                meta["universe_sample_strategy"] = "low_balance_min_order"
        else:
            if full_universe_scan:
                sampled = list(unique)
            else:
                sampled = random.sample(unique, sample_size) if len(unique) > sample_size else list(unique)

        # Inn20: Preferred Symbol Fast Lane — guarantee pref is always in the sampled pool
        # when fast lane is enabled AND it qualifies by alpha score.  This prevents the
        # random sample from accidentally excluding the top intel candidate every cycle.
        if (
            pref
            and pref in unique
            and pref not in sampled
            and bool(self.preferred_symbol_fast_lane_enabled)
        ):
            _fast_lane_ok = False
            try:
                _intel = self._load_symbol_flip_intel_payload()
                if isinstance(_intel, dict):
                    _longs = _intel.get("long_candidates", []) or []
                    if isinstance(_longs, list) and _longs:
                        _top = _longs[0] if isinstance(_longs[0], dict) else {}
                        if str(_top.get("symbol", "")).upper().strip() == pref:
                            _alpha = self._to_float(_top.get("alpha_long_score", 0.0), 0.0)
                            if _alpha >= float(self.preferred_symbol_fast_lane_min_alpha):
                                _fast_lane_ok = True
            except Exception:
                pass
            if _fast_lane_ok:
                sampled.insert(0, pref)
                meta["universe_sample_strategy"] = meta.get("universe_sample_strategy", "random") + "+fast_lane"

        hard_reject_spread_bps = max(self._to_float(self.universe_hard_reject_spread_bps, 0.0), 0.0)

        meta["universe_sample_size"] = len(sampled)
        hybrid_enabled = bool(self.hybrid_swing_selector_enabled)

        best_symbol: Optional[str] = None
        best_ticker: Optional[dict[str, Any]] = None
        best_score = float("inf")
        best_spread = float("inf")
        best_min_notional = float("inf")
        best_hybrid_symbol: Optional[str] = None
        best_hybrid_ticker: Optional[dict[str, Any]] = None
        best_hybrid_score = -float("inf")
        best_hybrid_spread = float("inf")
        best_hybrid_notional = float("inf")
        best_hybrid_meta: dict[str, Any] = {}
        bootstrap_ready_rows: list[dict[str, Any]] = []
        approval_rows: list[dict[str, Any]] = []
        approval_by_symbol: dict[str, dict[str, Any]] = {}
        ticker_hits = 0
        affordability_rejects = 0
        same_symbol_penalty_hits = 0
        same_symbol_penalty_bps = 6.0 if low_balance_mode else 0.0
        last_selected = str(self.last_selected_symbol or "").upper().strip()
        learning_bonus_applied_count = 0
        hard_spread_rejects = 0
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
            if hard_reject_spread_bps > 0.0 and spread_bps > hard_reject_spread_bps:
                hard_spread_rejects += 1
                continue

            cfg = self.router.get_symbol_config(symbol) or {}
            min_order_qty = self._effective_min_order(
                symbol,
                self._to_float(cfg.get("min_order", 0.0), 0.0),
            )
            last_px = self._to_float(ticker.get("last", 0.0), 0.0)
            open_px = max(self._to_float(ticker.get("open", last_px), last_px), 0.0)
            momentum_pct = ((last_px - open_px) / max(open_px, 1e-9)) * 100.0 if open_px > 0.0 else 0.0
            long_bias_penalty_bps = 0.0
            if self.hybrid_swing_long_bias_enabled and (not self.spot_short_enabled):
                momentum_deficit = max(
                    float(self.hybrid_swing_long_bias_min_momentum_pct) - float(momentum_pct),
                    0.0,
                )
                long_bias_penalty_bps = momentum_deficit * float(self.hybrid_swing_long_bias_penalty_per_pct)
            learning_bonus = float(self._to_float(learning_bonus_map.get(str(symbol).upper(), 0.0), 0.0))
            if learning_bonus > 0.0:
                learning_bonus_applied_count += 1
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
            score = float(spread_bps) + float(long_bias_penalty_bps) - float(learning_bonus)
            if same_symbol_penalty_bps > 0.0 and last_selected and symbol == last_selected:
                score += float(same_symbol_penalty_bps)
                same_symbol_penalty_hits += 1

            hybrid_metrics: Optional[dict[str, float | bool]] = None

            if score < best_score:
                best_score = score
                best_spread = spread_bps
                best_symbol = symbol
                best_ticker = ticker
                best_min_notional = min_order_notional

            if hybrid_enabled:
                hybrid_metrics = self._hybrid_swing_metrics_from_ticker(ticker, spread_bps)
                if isinstance(hybrid_metrics, dict):
                    hybrid_metrics["learning_bonus"] = float(learning_bonus)
                if bool(hybrid_metrics.get("eligible", False)):
                    hybrid_score = float(hybrid_metrics.get("hybrid_score", -float("inf")) or -float("inf"))
                    hybrid_score += float(learning_bonus)
                    momentum_pct_hybrid = float(self._to_float(hybrid_metrics.get("momentum_pct", 0.0), 0.0))
                    if same_symbol_penalty_bps > 0.0 and last_selected and symbol == last_selected:
                        hybrid_score -= float(same_symbol_penalty_bps)
                    if hybrid_score > best_hybrid_score:
                        best_hybrid_score = hybrid_score
                        best_hybrid_symbol = symbol
                        best_hybrid_ticker = ticker
                        best_hybrid_spread = spread_bps
                        best_hybrid_notional = min_order_notional
                        best_hybrid_meta = dict(hybrid_metrics)

                    if bool(self.edge_proof_bootstrap_enabled):
                        bootstrap_ready = (
                            hybrid_score >= float(self.edge_proof_bootstrap_min_hybrid_score)
                            and momentum_pct_hybrid >= float(self.edge_proof_bootstrap_min_momentum_pct)
                            and spread_bps <= float(self.edge_proof_bootstrap_max_spread_bps)
                        )
                        if bootstrap_ready:
                            bootstrap_ready_rows.append(
                                {
                                    "symbol": symbol,
                                    "ticker": ticker,
                                    "hybrid_score": float(hybrid_score),
                                    "spread_bps": float(spread_bps),
                                    "min_order_notional": float(min_order_notional),
                                    "hybrid_meta": dict(hybrid_metrics),
                                }
                            )

            candidate_row: dict[str, Any] = {
                "symbol": str(symbol),
                "spread_bps": round(float(spread_bps), 6),
                "selection_score_bps": round(float(score), 6),
                "min_order_notional": round(float(min_order_notional), 6),
                "momentum_pct": round(float(momentum_pct), 6),
                "long_bias_penalty_bps": round(float(long_bias_penalty_bps), 6),
                "learning_bonus": round(float(learning_bonus), 6),
            }
            if isinstance(hybrid_metrics, dict):
                candidate_row["hybrid_eligible"] = bool(hybrid_metrics.get("eligible", False))
                candidate_row["hybrid_score"] = round(
                    float(self._to_float(hybrid_metrics.get("hybrid_score", -float("inf")), -float("inf"))),
                    6,
                )
                candidate_row["range_pct"] = round(
                    float(self._to_float(hybrid_metrics.get("range_pct", 0.0), 0.0)),
                    6,
                )
                candidate_row["position_in_range"] = round(
                    float(self._to_float(hybrid_metrics.get("position_in_range", 0.0), 0.0)),
                    6,
                )
                candidate_row["trade_count_24h"] = int(
                    self._to_float(hybrid_metrics.get("trade_count_24h", 0.0), 0.0)
                )
            approval_rows.append(candidate_row)
            approval_by_symbol[str(symbol)] = candidate_row

        meta["universe_ticker_hits"] = ticker_hits
        meta["universe_affordability_rejects"] = affordability_rejects
        meta["universe_hard_spread_rejects"] = int(hard_spread_rejects)
        meta["universe_same_symbol_penalty_bps"] = round(float(same_symbol_penalty_bps), 6)
        meta["universe_same_symbol_penalty_hits"] = int(same_symbol_penalty_hits)
        meta["symbol_learning_bonus_applied_count"] = int(learning_bonus_applied_count)
        meta["bootstrap_candidate_count"] = int(len(bootstrap_ready_rows))
        if approval_rows:
            if hybrid_enabled:
                ranked_candidates = sorted(
                    approval_rows,
                    key=lambda row: (
                        0 if bool(row.get("hybrid_eligible", False)) else 1,
                        -float(self._to_float(row.get("hybrid_score", -float("inf")), -float("inf"))),
                        float(self._to_float(row.get("selection_score_bps", row.get("spread_bps", 1e9)), 1e9)),
                    ),
                )
            else:
                ranked_candidates = sorted(
                    approval_rows,
                    key=lambda row: float(
                        self._to_float(row.get("selection_score_bps", row.get("spread_bps", 1e9)), 1e9)
                    ),
                )
            max_candidates = max(int(self.live_operator_queue_max_candidates), 1)
            meta["approval_candidates"] = ranked_candidates[:max_candidates]
            meta["approval_candidate_count"] = int(len(meta["approval_candidates"]))

        if hybrid_enabled and bool(self.edge_proof_bootstrap_enabled) and bootstrap_ready_rows:
            bootstrap_ready_rows.sort(
                key=lambda row: (
                    -float(self._to_float(row.get("hybrid_score", -float("inf")), -float("inf"))),
                    float(self._to_float(row.get("spread_bps", float("inf")), float("inf"))),
                )
            )
            top_bootstrap = bootstrap_ready_rows[0]
            best_hybrid_symbol = str(top_bootstrap.get("symbol", "") or "").upper().strip()
            best_hybrid_ticker = top_bootstrap.get("ticker") if isinstance(top_bootstrap.get("ticker"), dict) else None
            best_hybrid_score = float(self._to_float(top_bootstrap.get("hybrid_score", -float("inf")), -float("inf")))
            best_hybrid_spread = float(self._to_float(top_bootstrap.get("spread_bps", float("inf")), float("inf")))
            best_hybrid_notional = float(self._to_float(top_bootstrap.get("min_order_notional", float("inf")), float("inf")))
            best_hybrid_meta = dict(top_bootstrap.get("hybrid_meta") or {})
            meta["selected_bootstrap_ready"] = True

        if hybrid_enabled and best_hybrid_symbol is not None:
            meta["selected_spread_bps"] = round(float(best_hybrid_spread), 6)
            meta["selected_min_order_notional"] = round(float(best_hybrid_notional), 6)
            meta["selected_hybrid_score"] = round(float(best_hybrid_score), 6)
            meta["selected_momentum_pct"] = round(float(self._to_float(best_hybrid_meta.get("momentum_pct", 0.0), 0.0)), 6)
            meta["selected_range_pct"] = round(float(self._to_float(best_hybrid_meta.get("range_pct", 0.0), 0.0)), 6)
            meta["selected_position_in_range"] = round(
                float(self._to_float(best_hybrid_meta.get("position_in_range", 0.0), 0.0)),
                6,
            )
            meta["selected_trade_count_24h"] = int(self._to_float(best_hybrid_meta.get("trade_count_24h", 0.0), 0.0))
            meta["selected_long_bias_penalty_bps"] = round(
                float(self._to_float(best_hybrid_meta.get("long_bias_penalty_bps", 0.0), 0.0)),
                6,
            )
            meta["selected_learning_bonus"] = round(
                float(self._to_float(best_hybrid_meta.get("learning_bonus", 0.0), 0.0)),
                6,
            )
            if best_hybrid_spread <= float(self.universe_max_pick_spread_bps):
                if bool(meta.get("selected_bootstrap_ready", False)):
                    meta["symbol_source"] = "hybrid_swing_bootstrap_ready"
                else:
                    meta["symbol_source"] = "hybrid_swing_spike_scan"
                return best_hybrid_symbol, best_hybrid_ticker, meta
            if bool(meta.get("selected_bootstrap_ready", False)):
                meta["symbol_source"] = "hybrid_swing_bootstrap_ready_wide"
            else:
                meta["symbol_source"] = "hybrid_swing_spike_scan_wide"
            return best_hybrid_symbol, best_hybrid_ticker, meta

        if best_symbol is not None:
            meta["selected_spread_bps"] = round(float(best_spread), 6)
            meta["selected_min_order_notional"] = round(float(best_min_notional), 6)
            selected_row = approval_by_symbol.get(str(best_symbol), {})
            if isinstance(selected_row, dict):
                meta["selected_momentum_pct"] = selected_row.get("momentum_pct")
                meta["selected_long_bias_penalty_bps"] = selected_row.get("long_bias_penalty_bps")
                meta["selected_learning_bonus"] = selected_row.get("learning_bonus", 0.0)
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

        if hard_spread_rejects > 0:
            meta["symbol_source"] = "hard_spread_reject_no_candidate"
            return None, None, meta

        fallback = random.choice(unique)
        meta["symbol_source"] = "random_no_ticker"
        return fallback, None, meta

    def _write_live_operator_approval_queue(
        self,
        now: datetime,
        selected_symbol: str,
        selection_meta: Optional[dict[str, Any]] = None,
    ) -> None:
        if not bool(self.live_operator_queue_enabled):
            return

        meta = dict(selection_meta or {})
        rows = meta.get("approval_candidates", [])
        if not isinstance(rows, list):
            rows = []

        selected = str(selected_symbol or "").upper().strip()
        max_candidates = max(int(self.live_operator_queue_max_candidates), 1)
        rows = rows[:max_candidates]

        tickets: list[dict[str, Any]] = []
        ts_compact = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        for idx, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol", "") or "").upper().strip()
            if not symbol:
                continue

            cfg = self.router.get_symbol_config(symbol) or {}
            pair = str(cfg.get("pair", "") or "").strip()
            if not pair:
                pair = f"{symbol}USD"

            min_notional = max(self._to_float(row.get("min_order_notional", 0.0), 0.0), 0.0)
            long_bias_penalty = max(self._to_float(row.get("long_bias_penalty_bps", 0.0), 0.0), 0.0)

            tickets.append(
                {
                    "ticket_id": f"LIVE-OP-{ts_compact}-{symbol}-{idx:02d}",
                    "timestamp_utc": now.isoformat(),
                    "symbol": symbol,
                    "pair": pair,
                    "rank": int(idx),
                    "decision_state": "PENDING_OPERATOR_REVIEW",
                    "action_hint": "APPROVE_LONG_IF_CONFIRMED",
                    "notional_hint_usd": round(float(min_notional), 6),
                    "scanner_meta": {
                        "spread_bps": row.get("spread_bps"),
                        "selection_score_bps": row.get("selection_score_bps"),
                        "hybrid_score": row.get("hybrid_score"),
                        "hybrid_eligible": bool(row.get("hybrid_eligible", False)),
                        "momentum_pct": row.get("momentum_pct"),
                        "range_pct": row.get("range_pct"),
                        "position_in_range": row.get("position_in_range"),
                        "trade_count_24h": row.get("trade_count_24h"),
                        "long_bias_penalty_bps": round(float(long_bias_penalty), 6),
                        "selected_symbol": bool(symbol == selected),
                    },
                }
            )

        if (not tickets) and selected:
            cfg = self.router.get_symbol_config(selected) or {}
            pair = str(cfg.get("pair", "") or f"{selected}USD")
            tickets.append(
                {
                    "ticket_id": f"LIVE-OP-{ts_compact}-{selected}-01",
                    "timestamp_utc": now.isoformat(),
                    "symbol": selected,
                    "pair": pair,
                    "rank": 1,
                    "decision_state": "PENDING_OPERATOR_REVIEW",
                    "action_hint": "APPROVE_LONG_IF_CONFIRMED",
                    "notional_hint_usd": round(
                        float(self._to_float(meta.get("selected_min_order_notional", 0.0), 0.0)),
                        6,
                    ),
                    "scanner_meta": {
                        "spread_bps": meta.get("selected_spread_bps"),
                        "selection_score_bps": meta.get("selected_spread_bps"),
                        "hybrid_score": meta.get("selected_hybrid_score"),
                        "hybrid_eligible": bool(meta.get("selected_hybrid_score") is not None),
                        "momentum_pct": meta.get("selected_momentum_pct"),
                        "range_pct": meta.get("selected_range_pct"),
                        "position_in_range": meta.get("selected_position_in_range"),
                        "trade_count_24h": meta.get("selected_trade_count_24h"),
                        "long_bias_penalty_bps": meta.get("selected_long_bias_penalty_bps"),
                        "selected_symbol": True,
                    },
                }
            )

        payload = {
            "generated_utc": now.isoformat(),
            "schema": "luma_live_operator_queue_v1",
            "source": "live_executor",
            "scope": "execution_cycle",
            "selected_symbol": selected,
            "symbol_source": str(meta.get("symbol_source", "none") or "none"),
            "queue_count": int(len(tickets)),
            "evidence_paths": {
                "runtime_control": str(RUNTIME_CONTROL_FILE),
                "heartbeat": str(LIVE_HEARTBEAT_FILE),
                "queue_file": str(LIVE_OPERATOR_APPROVAL_QUEUE_FILE),
            },
            "tickets": tickets,
        }

        try:
            LIVE_OPERATOR_APPROVAL_QUEUE_FILE.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

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

    def _prune_symbol_skip_map(self, now: datetime) -> None:
        expired: list[str] = []
        for symbol, until in self._symbol_skip_until_utc.items():
            if not isinstance(until, datetime):
                expired.append(symbol)
                continue
            if now >= until:
                expired.append(symbol)

        for symbol in expired:
            self._symbol_skip_until_utc.pop(symbol, None)
            self._symbol_skip_reasons.pop(symbol, None)

        if expired:
            self._save_pacing_state()

    def _symbol_skip_active(self, symbol: str, now: datetime) -> bool:
        key = str(symbol or "").upper().strip()
        if not key:
            return False
        self._prune_symbol_skip_map(now)
        until = self._symbol_skip_until_utc.get(key)
        return isinstance(until, datetime) and now < until

    def _mark_symbol_skip(
        self,
        symbol: str,
        now: datetime,
        reason: str,
        cooldown_sec: float = 0.0,
    ) -> None:
        key = str(symbol or "").upper().strip()
        if not key:
            return

        sec = max(self._to_float(cooldown_sec, 0.0), self._to_float(self.symbol_skip_cooldown_sec, 0.0))
        if sec <= 0.0:
            return

        until = now + timedelta(seconds=float(sec))
        self._symbol_skip_until_utc[key] = until
        self._symbol_skip_reasons[key] = str(reason or "symbol_skip")
        self._save_pacing_state()

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

    def _auto_kill_switch_cooldown_active(self, now: datetime) -> bool:
        cooldown_sec = max(float(self.auto_kill_switch_trip_cooldown_sec), 0.0)
        if cooldown_sec <= 0.0:
            return False
        raw = str(self.auto_kill_switch_last_trip_utc or "").strip()
        if not raw:
            return False
        try:
            last_trip = self._parse_iso_utc(raw)
        except Exception:
            return False
        return (now - last_trip).total_seconds() < cooldown_sec

    def _trip_runtime_kill_switch(
        self,
        now: datetime,
        *,
        reason: str,
        symbol: str,
        details: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "attempted": bool(self.auto_trip_kill_switch_on_inventory_discrepancy),
            "applied": False,
            "already_on": False,
            "cooldown_active": False,
            "reason": str(reason or "inventory_discrepancy"),
            "symbol": str(symbol or "").upper().strip(),
            "runtime_control": str(RUNTIME_CONTROL_FILE),
        }

        if not self.auto_trip_kill_switch_on_inventory_discrepancy:
            result["disabled"] = True
            return result

        runtime = load_json(RUNTIME_CONTROL_FILE, {})
        if not isinstance(runtime, dict):
            runtime = {}

        runtime_kill_switch = bool(runtime.get("kill_switch", False))
        result["already_on"] = runtime_kill_switch
        if runtime_kill_switch:
            self.auto_kill_switch_last_trip_utc = str(
                runtime.get("safety_auto_kill_trip_utc", self.auto_kill_switch_last_trip_utc) or ""
            ).strip()
            return result

        if self._auto_kill_switch_cooldown_active(now):
            result["cooldown_active"] = True
            return result

        runtime["kill_switch"] = True
        runtime["safety_auto_kill_source"] = "live_executor_inventory_discrepancy"
        runtime["safety_auto_kill_reason"] = str(reason or "inventory_discrepancy")
        runtime["safety_auto_kill_symbol"] = str(symbol or "").upper().strip()
        runtime["safety_auto_kill_trip_utc"] = now.isoformat()

        context: dict[str, Any] = {}
        if isinstance(details, dict):
            for key, value in details.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    context[str(key)] = value
        if context:
            runtime["safety_auto_kill_context"] = context

        try:
            RUNTIME_CONTROL_FILE.write_text(json.dumps(runtime, indent=2), encoding="utf-8")
            self.runtime_cfg = dict(runtime)
            self.auto_kill_switch_last_trip_utc = str(runtime.get("safety_auto_kill_trip_utc", "") or "").strip()
            result["applied"] = True
            result["kill_switch"] = True
            result["trip_utc"] = self.auto_kill_switch_last_trip_utc
        except Exception as exc:
            result["error"] = str(exc)

        return result

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

    def _moonshot_size_boost(self, symbol: str, gate_score: float) -> float:
        """Innovation 19: Return size multiplier when symbol is on the moonshot watchlist."""
        if not self.moonshot_amplifier_enabled:
            return 1.0
        if gate_score < float(self.moonshot_amplifier_min_gate_score):
            return 1.0
        import time as _time
        _now_m = _time.monotonic()
        if _now_m - self._moonshot_watchlist_cache_ts > float(self._moonshot_watchlist_cache_ttl):
            try:
                import pathlib as _pathlib, json as _json
                _wl_path = _pathlib.Path(self.moonshot_watchlist_path)
                if not _wl_path.is_absolute():
                    _wl_path = _pathlib.Path(__file__).resolve().parent.parent.parent / _wl_path
                _wl_data = _json.loads(_wl_path.read_text())
                self._moonshot_watchlist_cache = [str(s).upper() for s in _wl_data.get("watchlist", [])]
                self._moonshot_watchlist_cache_ts = _now_m
            except Exception:
                return 1.0
        _sym_clean = str(symbol).upper().split("/")[0]
        if _sym_clean in self._moonshot_watchlist_cache:
            return float(self.moonshot_amplifier_multiplier)
        return 1.0

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

        # ── Quarter-Kelly adaptive sizing ──────────────────────────────────────
        # Boosts position cap when recent win rate confirms strong edge.
        # Floor at 1.0× ensures this never shrinks cap (drawdown_throttle + fail_throttle cover downside).
        _kelly_cap_mult = 1.0
        try:
            _eq = dict(self._edge_proof_cache or {})
            _n_trades = int(_eq.get("recent_closed_count", 0) or 0)
            if _n_trades >= int(self.kelly_min_sample_trades) and bool(self.kelly_sizing_enabled):
                _wr = self._clamp(self._to_float(_eq.get("win_rate_pct", 50.0), 50.0) / 100.0, 0.0, 1.0)
                _f_star = max(2.0 * _wr - 1.0, 0.0)  # simplified Kelly for binary outcomes
                _kelly_cap_mult = self._clamp(
                    1.0 + _f_star * float(self.kelly_fraction),
                    1.0,   # never shrinks cap — drawdown_throttle / fail_throttle handle downside
                    1.40,  # max 40% size boost on confirmed high win-rate edge
                )
        except Exception:
            pass
        cap = max(cap * _kelly_cap_mult, 0.0)

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
            "kelly_fraction_multiplier": round(float(_kelly_cap_mult), 6),
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

    # ── Innovation 4: Cascade Loss Guard ──────────────────────────────────────
    def _cascade_guard_check(self, now: datetime) -> bool:
        """
        When >= cascade_guard_min_positions are simultaneously underwater by >= threshold,
        exit the worst-performing one immediately to prevent correlated portfolio bleed.
        Returns True if a position was closed.
        """
        if not self.cascade_guard_enabled:
            return False
        try:
            open_positions = self.portfolio.get_open_positions()
            threshold = float(self.cascade_guard_threshold_pct)
            underwater: list[tuple[float, Any, str, float]] = []  # (pnl_pct, pos, base, last)
            for pos in open_positions:
                base = str(getattr(pos, "symbol", "") or "").split("/")[0].upper().strip()
                if not base:
                    continue
                ticker = self.router.get_ticker(base)
                if not isinstance(ticker, dict):
                    continue
                last = self._to_float(ticker.get("last", 0.0), 0.0)
                if last <= 0.0:
                    continue
                pnl = self._position_pnl_pct(pos, last)
                if pnl <= -threshold:
                    underwater.append((pnl, pos, base, last))
            if len(underwater) < int(self.cascade_guard_min_positions):
                return False
            # Sort: worst PnL first
            underwater.sort(key=lambda x: x[0])
            worst_pnl, worst_pos, worst_base, worst_last = underwater[0]
            close_qty, _, _ = self._resolve_close_qty_for_spot(worst_base, float(worst_pos.qty), "sell")
            if close_qty <= 0.0:
                return False
            if float(close_qty) * float(worst_last) < 9.5:  # below Kraken minimum notional
                return False
            order = self.router.place_order(worst_base, "sell", close_qty)
            if not isinstance(order, dict) or not order.get("txid"):
                return False
            txid = str(order.get("txid", ""))
            self.portfolio.close_position(str(worst_pos.symbol), worst_last, now.isoformat())
            _pos_key = str(worst_pos.order_id) if str(worst_pos.order_id) else f"{worst_pos.symbol}|{worst_pos.entry_time_utc}"
            self._position_peaks.pop(_pos_key, None)
            self._position_prev_price.pop(_pos_key, None)
            self.audit_chain.append("cascade_guard_exit", {
                "symbol": worst_base, "txid": txid,
                "pnl_pct": round(worst_pnl * 100.0, 4),
                "underwater_count": len(underwater),
            })
            return True
        except Exception as exc:
            self.audit_chain.append("cascade_guard_error", {"error": str(exc)})
            return False

    # ── Innovation 5: Short-Signal Force Exit Timer ────────────────────────────
    def _short_signal_force_exit_check(self, now: datetime) -> bool:
        """
        If the executor has been flagged short_signal_forced_long for longer than
        short_signal_force_exit_sec, find the largest-valued position that is
        currently bearish (based on 24h momentum) and force-close it.
        Returns True if a position was closed.
        """
        if not self.short_signal_force_exit_enabled:
            return False
        try:
            open_positions = self.portfolio.get_open_positions()
            if not open_positions:
                return False
            threshold_sec = float(self.short_signal_force_exit_sec)
            best_candidate = None
            best_value = 0.0
            for pos in open_positions:
                base = str(getattr(pos, "symbol", "") or "").split("/")[0].upper().strip()
                if not base:
                    continue
                ticker = self.router.get_ticker(base)
                if not isinstance(ticker, dict):
                    continue
                last = self._to_float(ticker.get("last", 0.0), 0.0)
                if last <= 0.0:
                    continue
                # Check for bearish signal via negative 24h momentum
                r24 = self._to_float(ticker.get("change_pct_24h", ticker.get("vwap", 0.0)), 0.0)
                # Use absolute value of qty for value calc; only consider negative momentum
                value_usd = abs(float(pos.qty)) * last
                _pos_key = str(pos.order_id) if str(pos.order_id) else f"{pos.symbol}|{pos.entry_time_utc}"
                # Track when bearish signal was first detected
                if r24 < 0.0:
                    if _pos_key not in self._short_signal_flagged_since_utc:
                        self._short_signal_flagged_since_utc[_pos_key] = now.isoformat()
                    try:
                        flagged_dt = self._parse_iso_utc(self._short_signal_flagged_since_utc[_pos_key])
                        flagged_dur = (now - flagged_dt).total_seconds()
                    except Exception:
                        flagged_dur = 0.0
                    if flagged_dur >= threshold_sec and value_usd > best_value:
                        best_value = value_usd
                        best_candidate = (pos, base, last)
                else:
                    # Signal cleared — reset timer
                    self._short_signal_flagged_since_utc.pop(_pos_key, None)
            if best_candidate is None:
                return False
            worst_pos, worst_base, worst_last = best_candidate
            close_qty, _, _ = self._resolve_close_qty_for_spot(worst_base, float(worst_pos.qty), "sell")
            if close_qty <= 0.0:
                return False
            if float(close_qty) * float(worst_last) < 9.5:  # below Kraken minimum notional
                return False
            order = self.router.place_order(worst_base, "sell", close_qty)
            if not isinstance(order, dict) or not order.get("txid"):
                return False
            txid = str(order.get("txid", ""))
            pnl = self._position_pnl_pct(worst_pos, worst_last)
            self.portfolio.close_position(str(worst_pos.symbol), worst_last, now.isoformat())
            _pos_key2 = str(worst_pos.order_id) if str(worst_pos.order_id) else f"{worst_pos.symbol}|{worst_pos.entry_time_utc}"
            self._position_peaks.pop(_pos_key2, None)
            self._position_prev_price.pop(_pos_key2, None)
            self._short_signal_flagged_since_utc.pop(_pos_key2, None)
            self.audit_chain.append("short_signal_force_exit", {
                "symbol": worst_base, "txid": txid,
                "pnl_pct": round(pnl * 100.0, 4),
                "forced_hold_sec": round(float(self.short_signal_force_exit_sec), 1),
            })
            return True
        except Exception as exc:
            self.audit_chain.append("short_signal_force_exit_error", {"error": str(exc)})
            return False

    # ── Innovation 10: Heat-Triggered Capital Recycle ──────────────────────────
    def _heat_recycle_attempt(self, now: datetime, preferred_symbol: str = "") -> bool:
        """
        When a buy is blocked purely by heat AND a preferred symbol is queued,
        score all open positions and sell the weakest one to reduce heat.
        Scores by: PnL% contribution + hold time bonus — lowest score exits first.
        Respects a minimum hold time and cooldown to prevent thrashing.
        Returns True if a position was closed.
        """
        if not self.heat_recycle_enabled:
            return False
        # Cooldown guard
        if self._heat_recycle_last_utc:
            try:
                _last_dt = self._parse_iso_utc(self._heat_recycle_last_utc)
                if (now - _last_dt).total_seconds() < float(self.heat_recycle_cooldown_sec):
                    return False
            except Exception:
                pass
        try:
            open_positions = self.portfolio.get_open_positions()
            if not open_positions:
                return False
            min_hold = float(self.heat_recycle_min_hold_sec)
            worst: Optional[dict] = None
            for pos in open_positions:
                base = str(getattr(pos, "symbol", "") or "").split("/")[0].upper().strip()
                if not base:
                    continue
                # Don't recycle the preferred symbol itself
                if base == str(preferred_symbol or "").upper().strip():
                    continue
                # Inn22: never recycle a moonshot position — let it hold to 500bps TP
                if self.inn22_moonshot_tp_enabled and base in self._moonshot_watchlist_cache:
                    continue
                ticker = self.router.get_ticker(base)
                if not isinstance(ticker, dict):
                    continue
                last = self._to_float(ticker.get("last", 0.0), 0.0)
                if last <= 0.0:
                    continue
                try:
                    entry_dt = self._parse_iso_utc(pos.entry_time_utc)
                    hold_sec = max((now - entry_dt).total_seconds(), 0.0)
                except Exception:
                    hold_sec = min_hold + 1.0
                if hold_sec < min_hold:
                    continue
                pnl_pct = self._position_pnl_pct(pos, last)
                notional_usd = abs(float(pos.qty)) * last
                # Score: high PnL + long hold = KEEP.  Low PnL + big notional = RECYCLE.
                # Lowest score = first to recycle.
                score = (pnl_pct * 200.0) + (hold_sec / 300.0) - (notional_usd / 50.0)
                if worst is None or score < float(worst["score"]):
                    worst = {
                        "pos": pos, "base": base, "last": last,
                        "hold_sec": hold_sec, "pnl_pct": pnl_pct,
                        "notional_usd": notional_usd, "score": score,
                    }
            if worst is None:
                self.audit_chain.append("heat_recycle_no_candidate", {"min_hold_sec": float(self.heat_recycle_min_hold_sec), "positions_checked": len(open_positions)})
                return False
            pos = worst["pos"]
            base = worst["base"]
            last_px = worst["last"]
            close_qty, avail_qty, bal_err = self._resolve_close_qty_for_spot(base, float(pos.qty), "sell")
            if close_qty <= 0.0:
                # Balance not available — try raw qty from position record directly
                raw_qty = float(pos.qty)
                if raw_qty * float(last_px) >= 9.5:
                    close_qty = raw_qty
                else:
                    self.audit_chain.append("heat_recycle_skip_qty", {"symbol": base, "avail_qty": float(avail_qty), "raw_qty": raw_qty, "bal_err": str(bal_err)})
                    return False
            if float(close_qty) * float(last_px) < 9.5:  # below Kraken minimum notional
                self.audit_chain.append("heat_recycle_skip_notional", {"symbol": base, "notional_usd": round(float(close_qty) * float(last_px), 4)})
                return False
            order = self.router.place_order(base, "sell", float(close_qty))
            if not isinstance(order, dict) or not order.get("txid"):
                resp_str = str(order)[:300]
                is_insufficient = "insufficient funds" in resp_str.lower() or "EOrder:Insufficient" in resp_str
                # If Insufficient Funds, try cancelling stale open sell orders for this symbol
                # (leftover stop-loss orders from previous sessions lock the balance)
                _release_result: Optional[dict] = None
                if is_insufficient:
                    try:
                        _release_result = self._release_reserved_inventory_for_symbol(base, max_cancel_orders=5)
                        _released = int(_release_result.get("canceled", 0) if isinstance(_release_result, dict) else 0)
                        if _released > 0:
                            # Retry the sell now that stale orders are cancelled
                            order = self.router.place_order(base, "sell", float(close_qty))
                            resp_str = str(order)[:300]
                            is_insufficient = "insufficient funds" in resp_str.lower() or "EOrder:Insufficient" in resp_str
                    except Exception:
                        pass
                if isinstance(order, dict) and order.get("txid"):
                    # Retry succeeded — fall through to the success path below
                    pass
                else:
                    is_phantom = is_insufficient
                    self.audit_chain.append("heat_recycle_order_failed", {"symbol": base, "qty": float(close_qty), "response": resp_str, "phantom_reconciled": is_phantom, "release_result": _release_result})
                    if is_phantom:
                        # Position doesn't exist on exchange — reconcile it out so heat corrects
                        self.portfolio.close_position(str(pos.symbol), float(last_px), now.isoformat())
                        _pos_key_pr = str(pos.order_id) if str(pos.order_id) else f"{pos.symbol}|{pos.entry_time_utc}"
                        self._position_peaks.pop(_pos_key_pr, None)
                        self._position_prev_price.pop(_pos_key_pr, None)
                        self._phantom_skip_symbols[base] = now.isoformat()  # Suppress re-injection for 5 min
                        self.audit_chain.append("phantom_position_reconciled", {"symbol": base, "qty": float(close_qty), "notional_usd": round(float(close_qty) * float(last_px), 4)})
                    return False
            txid = str(order.get("txid", ""))
            pnl = worst["pnl_pct"]
            self.portfolio.close_position(str(pos.symbol), last_px, now.isoformat())
            _pos_key3 = str(pos.order_id) if str(pos.order_id) else f"{pos.symbol}|{pos.entry_time_utc}"
            self._position_peaks.pop(_pos_key3, None)
            self._position_prev_price.pop(_pos_key3, None)
            self._heat_recycle_last_utc = now.isoformat()
            self.audit_chain.append("heat_recycle_exit", {
                "symbol": base, "txid": txid,
                "pnl_pct": round(pnl * 100.0, 4),
                "notional_usd": round(float(worst["notional_usd"]), 4),
                "hold_sec": round(float(worst["hold_sec"]), 1),
                "preferred_queued": str(preferred_symbol or ""),
                "recycle_score": round(float(worst["score"]), 4),
            })
            return True
        except Exception as exc:
            self.audit_chain.append("heat_recycle_error", {"error": str(exc)})
            return False

    def _cancel_stale_buy_orders(self, now: datetime, force: bool = False) -> dict[str, Any]:
        """Cancel unfilled limit BUY orders older than stale_buy_order_ttl_sec.

        Called periodically and on every EOrder:Insufficient funds hit to free
        locked capital before the executor gives up and throttles notional size.
        """
        result: dict[str, Any] = {"checked": 0, "cancelled": 0, "freed_usd": 0.0, "errors": 0}
        try:
            # Rate-limit: only run once per stale_order_cleanup_interval_sec unless forced
            if not force and self._last_stale_order_cleanup_utc:
                try:
                    last_dt = self._parse_iso_utc(self._last_stale_order_cleanup_utc)
                    if (now - last_dt).total_seconds() < float(self.stale_order_cleanup_interval_sec):
                        result["skipped"] = "cooldown"
                        return result
                except Exception:
                    pass

            self._last_stale_order_cleanup_utc = now.isoformat()
            open_payload = self.router.get_open_orders(trades=True)
            if isinstance(open_payload, dict) and "error" in open_payload:
                result["errors"] += 1
                return result

            orders = open_payload.get("orders", []) if isinstance(open_payload, dict) else []
            ttl = float(self.stale_buy_order_ttl_sec)
            now_ts = now.timestamp()

            # Update open-order locked USD on the Kraken client so balance reflects reality
            total_locked = 0.0
            stale: list[dict[str, Any]] = []
            for row in orders:
                if not isinstance(row, dict):
                    continue
                if str(row.get("type", "")).lower() != "buy":
                    continue
                opentm = self._to_float(row.get("opentm", 0.0), 0.0)
                vol_rem = max(self._to_float(row.get("vol"), 0.0) - self._to_float(row.get("vol_exec"), 0.0), 0.0)
                price = self._to_float(row.get("price", 0.0), 0.0)
                total_locked += vol_rem * price
                if opentm <= 0.0:
                    continue
                age_sec = now_ts - opentm
                if age_sec >= ttl:
                    stale.append(row)

            # Inform the Kraken client about currently locked capital
            try:
                self.router.kraken._open_order_locked_usd = float(total_locked)
            except Exception:
                pass

            result["checked"] = len(orders)
            if not stale:
                return result

            # Cancel stale buy orders one by one (preserve good orders)
            for row in stale:
                txid = str(row.get("txid", "") or "").strip()
                if not txid:
                    continue
                try:
                    cancel_resp = self.router.cancel_order(txid)
                    if isinstance(cancel_resp, dict) and "error" not in cancel_resp:
                        vol_remaining = max(
                            self._to_float(row.get("vol"), 0.0) - self._to_float(row.get("vol_exec"), 0.0), 0.0
                        )
                        price = self._to_float(row.get("price", 0.0), 0.0)
                        freed = vol_remaining * price
                        result["cancelled"] += 1
                        result["freed_usd"] += freed
                        self.audit_chain.append(
                            "stale_buy_order_cancelled",
                            {
                                "txid": txid,
                                "pair": str(row.get("pair", "")),
                                "age_sec": round(now_ts - self._to_float(row.get("opentm"), 0.0), 1),
                                "freed_usd": round(freed, 4),
                            },
                        )
                    else:
                        result["errors"] += 1
                except Exception:
                    result["errors"] += 1

            # If we freed capital, force-refresh the balance cache
            if result["cancelled"] > 0:
                try:
                    # Clear locked amount proportionally
                    freed = float(result["freed_usd"])
                    prev_locked = max(float(self.router.kraken._open_order_locked_usd), 0.0)
                    self.router.kraken._open_order_locked_usd = max(prev_locked - freed, 0.0)
                    self.router.get_balance_snapshot(force_refresh=True)
                    # Reset fail streak — capital is now available again
                    self.order_fail_streak = max(self.order_fail_streak - result["cancelled"] * 3, 0)
                    self.notional_throttle = min(
                        self.notional_throttle * (1.0 + self.success_notional_recovery_step * result["cancelled"]),
                        1.0,
                    )
                    print(
                        f"  stale_buy_cancel: freed ${result['freed_usd']:.2f} from "
                        f"{result['cancelled']} order(s), fail_streak → {self.order_fail_streak}, "
                        f"throttle → {self.notional_throttle:.3f}"
                    )
                except Exception:
                    pass
        except Exception as exc:
            self.audit_chain.append("stale_buy_cancel_error", {"error": str(exc)})
            result["errors"] += 1
        return result

    def _stale_order_cleanup_due(self, now: datetime) -> bool:
        """True if the periodic stale-order cleanup sweep should run this loop."""
        if not self._last_stale_order_cleanup_utc:
            return True
        try:
            last_dt = self._parse_iso_utc(self._last_stale_order_cleanup_utc)
            return (now - last_dt).total_seconds() >= float(self.stale_order_cleanup_interval_sec)
        except Exception:
            return True

    def _global_close_sweep_due(self, now: datetime) -> bool:
        if not bool(self.global_close_sweep_enabled):
            return False
        if float(self.global_close_sweep_interval_sec) <= 0.0:
            return True
        last_raw = str(self.last_global_close_sweep_utc or "").strip()
        if not last_raw:
            return True
        try:
            last_dt = self._parse_iso_utc(last_raw)
        except Exception:
            return True
        return (now - last_dt).total_seconds() >= float(self.global_close_sweep_interval_sec)

    _STABLECOIN_SKIP = frozenset({
        "USD", "USDT", "USDC", "RLUSD", "DAI", "BUSD", "USDP", "TUSD", "FRAX",
        "EUR", "GBP", "CHF", "ZUSD", "ZEUR", "ZGBP",
    })

    def _inject_orphaned_balance_positions(self, now: datetime) -> int:
        """
        When the bot restarts, the in-memory portfolio is empty but Kraken may still hold
        crypto bought in prior sessions.  This method reads the live balance, finds non-USD /
        non-stablecoin holdings worth more than $1 USD, and injects synthetic 'timed-out'
        OPEN positions into the portfolio so the global close sweep can close them normally.

        Safe-guards:
        - Per-symbol duplicate check prevents double-inject for any symbol already in portfolio.
        - Sets entry_time_utc two hours in the past so timeout close fires immediately.
        - Entry price is set to current ticker price (bot closes at ~breakeven on the recorded side).
        - Skips anything below the $1 minimum value threshold.
        """
        injected = 0
        try:
            balances = self.router.get_balance_snapshot(force_refresh=True)
            if not isinstance(balances, dict):
                return 0

            two_hours_ago = (now - timedelta(hours=2)).isoformat()

            for asset_code, raw_qty in balances.items():
                qty = max(self._to_float(raw_qty, 0.0), 0.0)
                if qty <= 0.0:
                    continue

                base = self._normalize_balance_symbol(str(asset_code))
                if not base or base in self._STABLECOIN_SKIP:
                    continue

                # Skip symbols recently phantom-flagged (sell failed with Insufficient Funds)
                _phantom_ts = self._phantom_skip_symbols.get(base)
                if _phantom_ts:
                    try:
                        _phantom_age = (now - self._parse_iso_utc(str(_phantom_ts))).total_seconds()
                        if _phantom_age < 300.0:
                            continue  # Still within 5-min cooldown — don't re-inject
                        else:
                            del self._phantom_skip_symbols[base]  # Expired — allow retry
                    except Exception:
                        pass

                ticker = self.router.get_ticker(base)
                if not isinstance(ticker, dict):
                    ticker = {}
                last = self._to_float(ticker.get("last", 0.0), 0.0)
                if last <= 0.0:
                    # Fallback: scan trade ledger for the last known fill price for this asset.
                    try:
                        ledger_rows = self._read_jsonl_tail(LIVE_TRADE_LEDGER_JSONL_FILE, 200)
                        for _row in reversed(ledger_rows):
                            _sym = str(_row.get("symbol", "")).upper().strip()
                            _side = str(_row.get("side", "")).lower()
                            _ep = self._to_float(_row.get("entry_price", 0.0), 0.0)
                            if _sym == base and _side == "buy" and _ep > 0.0:
                                last = _ep
                                break
                    except Exception:
                        pass
                if last <= 0.0:
                    continue

                value_usd = qty * last
                # Skip balances below $15 — Kraken minimum sell notional is ~$10,
                # injecting sub-$15 dust creates phantom positions that can never be
                # closed, consuming heat and blocking real entries indefinitely.
                if value_usd < 15.0:
                    continue

                # Determine the quote currency this asset was most likely traded against.
                sym_cfg = self.router.get_symbol_config(base) or {}
                quote = str(sym_cfg.get("quote", "USD")).upper().strip() or "USD"
                full_symbol = f"{base}/{quote}"

                # Check we haven't already injected this symbol.
                already_there = any(
                    str(getattr(p, "symbol", "")).upper().startswith(f"{base}/")
                    for p in self.portfolio.get_open_positions()
                )
                if already_there:
                    continue

                self.portfolio.add_position(
                    Position(
                        symbol=full_symbol,
                        side="long",
                        entry_price=float(last),
                        current_price=float(last),
                        qty=float(qty),
                        entry_time_utc=two_hours_ago,
                        flowform="recovery",
                        algo="balance_recovery",
                        strategy="orphan_drain",
                        order_id="RECOVERY",
                        status="OPEN",
                    )
                )
                injected += 1

                self.audit_chain.append(
                    "orphaned_position_injected",
                    {
                        "symbol": full_symbol,
                        "qty": round(float(qty), 10),
                        "last_price": round(float(last), 6),
                        "value_usd": round(float(value_usd), 4),
                        "entry_time_utc": two_hours_ago,
                    },
                )
        except Exception as exc:
            self.audit_chain.append("orphaned_position_inject_error", {"error": str(exc)})

        if injected > 0:
            _write_live_heartbeat(
                {
                    "status": "recovering",
                    "reason": "orphaned_balance_positions_injected",
                    "injected_count": int(injected),
                }
            )
        return int(injected)

    def _run_global_close_sweep(self, now: datetime, preferred_symbol: str = "") -> dict[str, Any]:
        result = {
            "executed": False,
            "symbols_scanned": 0,
            "symbols_with_ticker": 0,
            "closed_count": 0,
            "reconciled_count": 0,
            "checked_symbols": [],
        }
        if not self._global_close_sweep_due(now):
            return result

        open_positions = self.portfolio.get_open_positions()

        # --- Orphaned position recovery ---
        # After a bot restart the in-memory portfolio may be partially populated from the ledger
        # (e.g. old XMR lots) while Kraken still holds other tokens bought in prior cycles.
        # Run the injector unconditionally — per-symbol duplicate checks prevent double-inject.
        self._inject_orphaned_balance_positions(now)
        open_positions = self.portfolio.get_open_positions()

        symbol_candidates: list[str] = []
        for pos in open_positions:
            raw = str(getattr(pos, "symbol", "") or "").upper().strip()
            if not raw:
                continue
            base = raw.split("/", 1)[0].strip()
            if base and base not in symbol_candidates:
                symbol_candidates.append(base)

        preferred = str(preferred_symbol or "").upper().strip()
        if preferred and preferred in symbol_candidates:
            symbol_candidates = [preferred] + [s for s in symbol_candidates if s != preferred]

        max_symbols = int(self.global_close_sweep_max_symbols)
        if max_symbols > 0:
            symbol_candidates = symbol_candidates[:max_symbols]
        result["executed"] = True
        result["symbols_scanned"] = int(len(symbol_candidates))
        result["checked_symbols"] = list(symbol_candidates)

        closed_count = 0
        reconciled_count = 0
        symbols_with_ticker = 0
        for sym in symbol_candidates:
            ticker = self.router.get_ticker(sym)
            if not isinstance(ticker, dict):
                ticker = {}
            last = self._to_float(ticker.get("last", 0.0), 0.0)
            if last <= 0.0:
                # Fallback: use entry price for timed-out positions so the close sweep
                # can still close positions whose ticker price is unavailable.
                for _fp in self.portfolio.get_open_positions():
                    _base = str(getattr(_fp, "symbol", "") or "").split("/")[0].upper()
                    if _base == sym:
                        _ep = self._to_float(getattr(_fp, "entry_price", 0.0), 0.0)
                        if _ep > 0.0:
                            last = _ep
                        break
            if last <= 0.0:
                continue
            symbols_with_ticker += 1
            reconciled_count += int(self._reconcile_zero_inventory_positions(sym, float(last), now))
            if self._maybe_close_positions(sym, float(last), now):
                closed_count += 1

        self.last_global_close_sweep_utc = now.isoformat()
        result["symbols_with_ticker"] = int(symbols_with_ticker)
        result["closed_count"] = int(closed_count)
        result["reconciled_count"] = int(reconciled_count)

        # Innovation 4: Cascade Loss Guard — run after per-symbol sweep
        if not closed_count:
            if self._cascade_guard_check(now):
                result["closed_count"] = closed_count + 1

        # Innovation 5: Short-Signal Force Exit Timer — run after close sweep
        if not closed_count:
            if self._short_signal_force_exit_check(now):
                result["closed_count"] = closed_count + 1

        return result

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

    def _compute_live_risk_snapshot(self, balance_valuation: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        valuation = (
            balance_valuation
            if isinstance(balance_valuation, dict)
            else self._build_balance_valuation(force_refresh=False)
        )

        holdings = valuation.get("holdings", [])
        if not isinstance(holdings, list):
            holdings = []

        live_open_positions = 0
        for row in holdings:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol", "") or "").upper().strip()
            if not symbol or symbol == "USD":
                continue
            is_stable = bool(row.get("is_stable", False)) or (symbol in self.stable_assets)
            if is_stable:
                continue
            value_usd = max(self._to_float(row.get("value_usd", 0.0), 0.0), 0.0)
            if value_usd >= max(float(self.min_collateral_convert_usd), 0.50):
                live_open_positions += 1

        local_open_positions = int(len(self.portfolio.get_open_positions()))
        effective_open_positions = int(max(local_open_positions, live_open_positions))

        local_exposure_usd = max(self._to_float(self.portfolio.exposure(), 0.0), 0.0)
        live_exposure_usd = max(self._to_float(valuation.get("holdings_value_usd", 0.0), 0.0), 0.0)
        effective_exposure_usd = max(local_exposure_usd, live_exposure_usd)

        local_equity_usd = max(self._to_float(getattr(self.portfolio, "current_equity", 0.0), 0.0), 0.0)
        live_equity_usd = max(self._to_float(valuation.get("total_equity_usd", 0.0), 0.0), 0.0)

        local_heat = local_exposure_usd / max(local_equity_usd, 1.0)
        live_heat = live_exposure_usd / max(live_equity_usd, 1.0)
        effective_heat = max(local_heat, live_heat)

        return {
            "local_open_positions": int(local_open_positions),
            "live_open_positions": int(live_open_positions),
            "effective_open_positions": int(effective_open_positions),
            "local_exposure_usd": float(local_exposure_usd),
            "live_exposure_usd": float(live_exposure_usd),
            "effective_exposure_usd": float(effective_exposure_usd),
            "local_portfolio_heat": float(local_heat),
            "live_portfolio_heat": float(live_heat),
            "effective_portfolio_heat": float(effective_heat),
            "local_equity_usd": float(local_equity_usd),
            "live_equity_usd": float(live_equity_usd),
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

    def _open_long_hold_seconds_by_symbol(self, now: datetime) -> dict[str, float]:
        holds: dict[str, float] = {}
        open_positions = self.portfolio.get_open_positions()
        for pos in open_positions:
            if str(pos.side).lower() != "long":
                continue
            base_symbol = str(pos.symbol).split("/")[0].upper().strip()
            if not base_symbol:
                continue
            try:
                entry_dt = self._parse_iso_utc(pos.entry_time_utc)
                hold_sec = max((now - entry_dt).total_seconds(), 0.0)
            except Exception:
                hold_sec = float("inf")
            prev = holds.get(base_symbol)
            holds[base_symbol] = float(hold_sec) if prev is None else min(float(prev), float(hold_sec))
        return holds

    def _release_reserved_inventory_for_symbol(
        self,
        symbol: str,
        max_cancel_orders: int = 3,
    ) -> dict[str, Any]:
        symbol_key = str(symbol or "").upper().strip()
        result: dict[str, Any] = {
            "attempted": True,
            "symbol": symbol_key,
            "reason": "none",
            "canceled": 0,
            "failed": 0,
            "txids": [],
        }
        if not symbol_key:
            result["reason"] = "invalid_symbol"
            return result

        cfg = self.router.get_symbol_config(symbol_key) or {}
        candidate_pairs: set[str] = set()
        pair = str(cfg.get("pair", "") or "").upper().strip()
        if pair:
            candidate_pairs.add(pair)
        candidates = cfg.get("candidates", []) if isinstance(cfg.get("candidates", []), list) else []
        for row in candidates:
            if not isinstance(row, dict):
                continue
            p = str(row.get("pair", "") or "").upper().strip()
            if p:
                candidate_pairs.add(p)

        if not candidate_pairs:
            result["reason"] = "no_symbol_pair"
            return result

        open_orders_payload = self.router.get_open_orders(trades=True)
        if isinstance(open_orders_payload, dict) and "error" in open_orders_payload:
            result["reason"] = "open_orders_error"
            result["error"] = str(open_orders_payload.get("error"))
            return result

        orders = []
        if isinstance(open_orders_payload, dict):
            raw_orders = open_orders_payload.get("orders", [])
            if isinstance(raw_orders, list):
                orders = raw_orders

        matches: list[dict[str, Any]] = []
        for row in orders:
            if not isinstance(row, dict):
                continue
            row_pair = str(row.get("pair", "") or "").upper().strip()
            row_type = str(row.get("type", "") or "").lower().strip()
            row_status = str(row.get("status", "") or "").lower().strip()
            if row_pair not in candidate_pairs:
                continue
            if row_type != "sell" or row_status != "open":
                continue
            matches.append(row)

        if not matches:
            result["reason"] = "no_conflicting_open_sells"
            return result

        matches.sort(key=lambda row: self._to_float(row.get("opentm", 0.0), 0.0))
        cancel_cap = max(int(max_cancel_orders or 0), 1)
        for row in matches[:cancel_cap]:
            txid = str(row.get("txid", "") or "").strip()
            if not txid:
                continue
            cancel_result = self.router.cancel_order(txid)
            if isinstance(cancel_result, dict) and "error" in cancel_result:
                result["failed"] = int(result.get("failed", 0) or 0) + 1
                continue
            result["canceled"] = int(result.get("canceled", 0) or 0) + 1
            result["txids"].append(txid)

        canceled = int(result.get("canceled", 0) or 0)
        failed = int(result.get("failed", 0) or 0)
        if canceled > 0:
            result["reason"] = "released"
        elif failed > 0:
            result["reason"] = "cancel_failed"
        else:
            result["reason"] = "cancel_not_attempted"
        return result

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

        protect_window_sec = max(float(self.collateral_convert_protect_open_positions_sec), 0.0)
        open_long_holds: dict[str, float] = {}
        if bool(self.collateral_convert_avoid_open_positions) and protect_window_sec > 0.0:
            open_long_holds = self._open_long_hold_seconds_by_symbol(now)
        protected_open_position_skips: list[dict[str, Any]] = []

        preferred = str(preferred_symbol or "").upper().strip()
        candidates: list[dict[str, Any]] = []
        for row in holdings:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol", "") or "").upper().strip()
            if not symbol or symbol == "USD":
                continue

            hold_sec = open_long_holds.get(symbol)
            if hold_sec is not None and hold_sec < protect_window_sec:
                protected_open_position_skips.append(
                    {
                        "symbol": symbol,
                        "hold_sec": round(float(hold_sec), 3),
                    }
                )
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
            live_available_qty = max(
                self._to_float(self.router.get_asset_balance(symbol, force_refresh=True), 0.0),
                0.0,
            )
            if live_available_qty > 0.0:
                safe_available_qty = min(
                    safe_available_qty,
                    max(live_available_qty * float(self.close_balance_buffer_fraction), 0.0),
                )
            else:
                safe_available_qty = 0.0
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
                    "live_available_qty": float(live_available_qty),
                    "score": float(score),
                }
            )

        if protected_open_position_skips:
            result["protected_open_positions_skipped"] = int(len(protected_open_position_skips))
            result["collateral_convert_protect_open_positions_sec"] = round(float(protect_window_sec), 3)

        if not candidates:
            result["reason"] = "no_convertible_collateral"
            if protected_open_position_skips:
                result["protected_open_positions"] = protected_open_position_skips[:8]
            return _finalize(result)

        if allow_stable_conversion:
            stable_candidates = [row for row in candidates if bool(row.get("is_stable", False))]
            if stable_candidates:
                candidates = stable_candidates

        candidates.sort(key=lambda row: float(row.get("score", 0.0) or 0.0), reverse=True)
        required_usd_effective = max(self._to_float(required_usd, 0.0), self.min_collateral_convert_usd)
        attempt_failures: list[dict[str, Any]] = []

        for chosen in candidates:
            symbol = str(chosen.get("symbol", "") or "").upper().strip()
            last_px = max(self._to_float(chosen.get("last", 0.0), 0.0), 0.0)
            min_order = max(self._to_float(chosen.get("min_order", 0.0), 0.0), 0.0)
            safe_available_qty = max(self._to_float(chosen.get("safe_available_qty", 0.0), 0.0), 0.0)
            if not symbol or last_px <= 0.0 or min_order <= 0.0 or safe_available_qty < min_order:
                attempt_failures.append(
                    {
                        "symbol": symbol,
                        "reason": "invalid_candidate",
                    }
                )
                continue

            qty_from_required = required_usd_effective / max(last_px, 1e-9)
            qty_from_fraction = max(self._to_float(chosen.get("qty", 0.0), 0.0) * float(self.collateral_sell_fraction), 0.0)
            qty = max(min_order, qty_from_required, qty_from_fraction)
            qty = min(qty, safe_available_qty)
            if qty < min_order:
                attempt_failures.append(
                    {
                        "symbol": symbol,
                        "reason": "qty_below_min_order",
                        "qty": round(float(qty), 10),
                        "min_order": round(float(min_order), 10),
                    }
                )
                continue

            qty_attempts: list[float] = []
            for factor in (1.00, 0.85, 0.70, 0.55, 0.40):
                candidate_qty = min(float(qty) * float(factor), float(safe_available_qty))
                if candidate_qty + 1e-12 < float(min_order):
                    continue
                dedupe_key = round(float(candidate_qty), 10)
                if any(abs(dedupe_key - existing) < 1e-10 for existing in qty_attempts):
                    continue
                qty_attempts.append(float(dedupe_key))

            if not qty_attempts:
                attempt_failures.append(
                    {
                        "symbol": symbol,
                        "reason": "no_qty_attempts",
                        "qty": round(float(qty), 10),
                        "min_order": round(float(min_order), 10),
                    }
                )
                continue

            order_result: dict[str, Any] = {"error": "order_not_attempted"}
            qty_error_trace: list[dict[str, Any]] = []
            executed_qty = 0.0
            reserve_release_result: Optional[dict[str, Any]] = None
            reserve_release_attempted = False
            for attempted_qty in qty_attempts:
                order_result = self.router.place_order(symbol, "sell", float(attempted_qty), None)
                if "error" not in order_result:
                    executed_qty = float(attempted_qty)
                    break

                error_text = str(order_result.get("error"))
                qty_error_trace.append(
                    {
                        "qty": round(float(attempted_qty), 10),
                        "error": error_text,
                    }
                )

                if ("Insufficient funds" in error_text) and (not reserve_release_attempted):
                    reserve_release_attempted = True
                    reserve_release_result = self._release_reserved_inventory_for_symbol(symbol, max_cancel_orders=3)
                    if isinstance(reserve_release_result, dict):
                        released_count = int(reserve_release_result.get("canceled", 0) or 0)
                        if released_count > 0:
                            retry_result = self.router.place_order(symbol, "sell", float(attempted_qty), None)
                            if "error" not in retry_result:
                                order_result = retry_result
                                executed_qty = float(attempted_qty)
                                break

                            retry_error = str(retry_result.get("error"))
                            qty_error_trace.append(
                                {
                                    "qty": round(float(attempted_qty), 10),
                                    "error": retry_error,
                                    "phase": "post_release_retry",
                                }
                            )
                            order_result = retry_result
                            if "Insufficient funds" not in retry_error:
                                break

                if "Insufficient funds" not in error_text:
                    break

            if "error" in order_result:
                failure_payload: dict[str, Any] = {
                    "symbol": symbol,
                    "reason": "order_failed",
                    "error": str(order_result.get("error")),
                    "qty_attempts": qty_error_trace[:5],
                }
                if isinstance(reserve_release_result, dict):
                    failure_payload["reserve_release"] = reserve_release_result
                attempt_failures.append(failure_payload)
                continue

            qty = float(executed_qty)

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
            if isinstance(reserve_release_result, dict):
                result["reserve_release"] = reserve_release_result
            return _finalize(result)

        if attempt_failures:
            result["reason"] = "order_failed_all_candidates"
            result["attempt_failures"] = attempt_failures[:5]
            first = attempt_failures[0]
            result["symbol"] = str(first.get("symbol", ""))
            if "error" in first:
                result["error"] = str(first.get("error", ""))
            return _finalize(result)

        result["reason"] = "invalid_candidate"
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

        # Grace period: skip reconciliation for positions opened within the last 90 seconds.
        # This prevents a race condition where a freshly placed order hasn't settled on the
        # exchange yet (or the balance cache hasn't refreshed) and the zero-inventory check
        # would incorrectly close/auto-kill a perfectly valid new position.
        grace_sec = 90.0
        fresh_positions = []
        for p in symbol_positions:
            entry_raw = str(getattr(p, "entry_time_utc", "") or getattr(p, "entry_time", "") or "").strip()
            if entry_raw:
                try:
                    from datetime import timezone as _tz
                    entry_dt = datetime.fromisoformat(entry_raw)
                    if entry_dt.tzinfo is None:
                        entry_dt = entry_dt.replace(tzinfo=_tz.utc)
                    now_aware = now if now.tzinfo is not None else now.replace(tzinfo=_tz.utc)
                    age_sec = (now_aware - entry_dt).total_seconds()
                    if age_sec < grace_sec:
                        continue  # too new — skip this position in the reconcile pass
                except Exception:
                    pass
            fresh_positions.append(p)

        symbol_positions = fresh_positions
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

        kill_trip = self._trip_runtime_kill_switch(
            now,
            reason="inventory_discrepancy_zero_exchange_inventory",
            symbol=symbol,
            details={
                "reconciled_count": int(reconciled),
                "available_asset_qty": 0.0,
            },
        )
        self.audit_chain.append(
            "inventory_discrepancy_detected",
            {
                "symbol": symbol,
                "reconciled_count": int(reconciled),
                "available_asset_qty": 0.0,
                "auto_kill_switch": dict(kill_trip),
            },
        )

        _write_live_heartbeat(
            {
                "status": "critical",
                "reason": "inventory_discrepancy_detected",
                "symbol": symbol,
                "reconciled_count": int(reconciled),
                "available_asset_qty": 0.0,
                "auto_kill_switch": dict(kill_trip),
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

    def _get_symbol_alpha_score(self, symbol: str) -> Optional[float]:
        """Return the alpha_long_score for *symbol* from the symbol-flip intel file.
        Refreshes the in-memory cache whenever the file changes on disk.
        Returns None when the file is absent or the symbol is not in the intel."""
        try:
            p = SYMBOL_FLIP_INTEL_FILE
            if not p.exists():
                return None
            mtime = p.stat().st_mtime
            if mtime != self._alpha_score_cache_mtime:
                data = json.loads(p.read_text(encoding="utf-8"))
                candidates = data.get("long_candidates") or []
                self._alpha_score_cache = {
                    str(c.get("symbol", "")).upper(): self._to_float(c.get("alpha_long_score", 0.0), 0.0)
                    for c in candidates
                    if c.get("symbol")
                }
                self._alpha_score_cache_mtime = mtime
            return self._alpha_score_cache.get(str(symbol or "").upper())
        except Exception:
            return None

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

        # ── Alpha-Adaptive Exit Scaling (Innovation 11) ──────────────────────
        # High alpha_long_score signals get a wider TP and longer max-hold to let
        # momentum winners run.  Low-score signals get tighter TP/SL to exit
        # quickly and preserve capital.  Can be disabled via runtime_control.json.
        if self.runtime_cfg.get("alpha_adaptive_exit_enabled", True):
            _alpha = self._get_symbol_alpha_score(symbol)
            if _alpha is not None:
                if _alpha >= 20.0:              # momentum_snipe tier — let it run
                    tp_bps = max(tp_bps, 100.0)
                    max_hold_sec = min(max_hold_sec * 2.0, 480.0)
                elif _alpha >= 12.0:            # trend_follow_swing — moderate extension
                    tp_bps = max(tp_bps, 80.0)
                    max_hold_sec = min(max_hold_sec * 1.5, 360.0)
                elif _alpha < 8.0:              # low conviction — tighten and exit fast
                    tp_bps = min(tp_bps, 45.0)
                    sl_bps = min(sl_bps, 28.0)
                    max_hold_sec = min(max_hold_sec, 150.0)
        # ─────────────────────────────────────────────────────────────────────

        # ── Innovation 22: Moonshot Long-Hold TP Amplifier ───────────────────
        # Symbols on the moonshot watchlist get a dramatically wider TP target
        # and a 4-hour max hold, letting genuine rocket-movers capture 5-50%
        # moves instead of being force-closed at the base 0.8% scalp target.
        # Trailing stop activation is also widened to 2.5% so the stop doesn't
        # prematurely fire at 0.45% peak on a symbol targeting +5%.
        _inn22_is_moonshot = False
        if self.inn22_moonshot_tp_enabled:
            import time as _t22
            _now22 = _t22.monotonic()
            if _now22 - self._moonshot_watchlist_cache_ts > float(self._moonshot_watchlist_cache_ttl):
                try:
                    import pathlib as _p22, json as _j22
                    _wl22 = _p22.Path(self.moonshot_watchlist_path)
                    if not _wl22.is_absolute():
                        _wl22 = _p22.Path(__file__).resolve().parent.parent.parent / _wl22
                    _wd22 = _j22.loads(_wl22.read_text())
                    self._moonshot_watchlist_cache = [str(s).upper() for s in _wd22.get("watchlist", [])]
                    self._moonshot_watchlist_cache_ts = _now22
                except Exception:
                    pass
            _sym22 = str(symbol).upper().split("/")[0]
            if _sym22 in self._moonshot_watchlist_cache:
                _inn22_is_moonshot = True
                _inn22_tp = float(self.inn22_moonshot_tp_bps)
                _inn22_hold = float(self.inn22_moonshot_max_hold_sec)
                if tp_bps < _inn22_tp:
                    print(f"  [inn22] moonshot-tp: {_sym22} tp {tp_bps:.0f}→{_inn22_tp:.0f}bps hold {max_hold_sec:.0f}→{_inn22_hold:.0f}s")
                    tp_bps = _inn22_tp
                    max_hold_sec = max(max_hold_sec, _inn22_hold)
                # Inn22: Widen SL for moonshot positions so volatile 5%+ runners
                # aren't stopped out on normal dips before reaching the moonshot TP.
                _inn22_sl_override = self._to_float(self.runtime_cfg.get("inn22_moonshot_sl_bps", 0.0), 0.0)
                if _inn22_sl_override > 0.0 and sl_bps < _inn22_sl_override:
                    print(f"  [inn22] moonshot-sl: {_sym22} sl {sl_bps:.0f}→{_inn22_sl_override:.0f}bps")
                    sl_bps = _inn22_sl_override
        # ─────────────────────────────────────────────────────────────────────

        tp_pct = max(tp_bps / 10000.0, 0.0)
        sl_pct = max(sl_bps / 10000.0, 0.0)

        for pos in symbol_positions:
            try:
                entry_dt = self._parse_iso_utc(pos.entry_time_utc)
                hold_sec = max((now - entry_dt).total_seconds(), 0.0)
            except Exception:
                hold_sec = max_hold_sec + 1.0

            pnl_pct = self._position_pnl_pct(pos, float(last))

            # ── INSTITUTIONAL SWING HUNTER / TRAILING STOP ENGINE ────────────
            trail_hit = False
            _vel_exit_hit = False  # velocity reversal sub-flag for granular close reason
            _uses_trail = self.trailing_stop_enabled and str(pos.side).strip().lower() == "long"
            if _uses_trail:
                _activation_bps = float(self.trailing_stop_activation_bps)
                _trail_bps = float(self.trailing_stop_trail_bps)
                # Inn22: Widen trailing stop thresholds for moonshot positions so the
                # stop doesn't arm at +0.45% and cut a 5% moonshot run short.
                if _inn22_is_moonshot:
                    _activation_bps = max(_activation_bps, float(self.inn22_moonshot_trail_activation_bps))
                    _trail_bps = max(_trail_bps, float(self.inn22_moonshot_trail_bps))
                # Dynamic amplitude scaling: high-vol assets earn a wider activation buffer
                if self.trailing_stop_dynamic_scaling:
                    try:
                        _tk = self.router.get_ticker(symbol) or {}
                        _h24 = self._to_float(_tk.get("high_24h", 0.0), 0.0)
                        _l24 = self._to_float(_tk.get("low_24h", 0.0), 0.0)
                        if _l24 > 0.0 and _h24 > _l24:
                            _amp_pct = (_h24 - _l24) / _l24 * 100.0
                            _atr_mult = float(self.trailing_stop_dynamic_multiplier)
                            # Activation: widen for high-vol assets
                            _activation_bps = max(
                                _activation_bps,
                                _amp_pct * _atr_mult * 100.0,
                            )
                            # Trail: also scale by ATR proxy (half mult) — prevents noise stop-outs
                            _trail_bps = max(
                                _trail_bps,
                                _amp_pct * (_atr_mult * 0.5) * 100.0,
                            )
                    except Exception:
                        pass
                _activation_pct = _activation_bps / 10000.0
                _trail_pct = _trail_bps / 10000.0
                # Per-position peak price tracked in executor dict (no dataclass change needed)
                _pos_key = str(pos.order_id) if str(pos.order_id) else f"{pos.symbol}|{pos.entry_time_utc}"
                _cur_peak = self._position_peaks.get(_pos_key, float(pos.entry_price))
                if float(last) > _cur_peak:
                    _cur_peak = float(last)
                    self._position_peaks[_pos_key] = _cur_peak
                # Arm once cumulative peak gain >= activation threshold; trail bps below peak
                _entry_px = max(float(pos.entry_price), 1e-9)
                _peak_gain_pct = (_cur_peak - _entry_px) / _entry_px
                if _peak_gain_pct >= _activation_pct and _cur_peak > 0.0:
                    _trail_price = _cur_peak * (1.0 - _trail_pct)
                    # ── Innovation 7: Break-Even Ratchet ───────────────────────────
                    # Once peak gain >= activation × ratchet_mult, floor stop to entry.
                    # Guarantees we NEVER exit at a loss once sufficiently in profit.
                    if self.trailing_stop_breakeven_enabled:
                        _be_threshold = _activation_pct * float(self.trailing_stop_breakeven_ratchet_mult)
                        if _peak_gain_pct >= _be_threshold:
                            _trail_price = max(_trail_price, _entry_px)  # floor: stop can never be below entry
                    trail_hit = float(last) <= _trail_price
                # ── Velocity Reversal Exit ──────────────────────────────────────
                # Inter-cycle price velocity: detects sharp momentum flip before trailing stop fires
                _prev_px = self._position_prev_price.get(_pos_key, float(last))
                _vel_pct = (float(last) - _prev_px) / max(_prev_px, 1e-9) * 100.0
                self._position_prev_price[_pos_key] = float(last)
                if (
                    self.trailing_stop_vel_exit_enabled
                    and pnl_pct > 0.0
                    and _peak_gain_pct >= _activation_pct
                    and _vel_pct <= -float(self.trailing_stop_vel_exit_threshold_pct)
                ):
                    trail_hit = True
                    _vel_exit_hit = True
            # ─────────────────────────────────────────────────────────────────

            # For long positions with trailing stop active: suppress flat TP so momentum rides
            tp_hit = (not _uses_trail) and hold_sec >= min_hold_sec and pnl_pct >= tp_pct
            # Protective stops should fire immediately; do not wait for min hold.
            sl_hit = sl_pct > 0.0 and pnl_pct <= (-sl_pct)
            timeout_hit = hold_sec >= max_hold_sec

            # ══ Sell Innovations 1–9 (evaluated per-position in close sweep) ═══

            # Innovation 1: Profit Lock ─ hard ceiling; guarantee the gain
            profit_lock_hit = (
                self.profit_lock_enabled
                and pnl_pct >= float(self.profit_lock_pct)
            )

            # Innovation 2: Dead-Weight Purge ─ exit positions wasting heat
            # Inn22 moonshot positions are exempt: they need up to 4 hours to develop.
            dead_weight_hit = (
                self.dead_weight_purge_enabled
                and hold_sec >= float(self.dead_weight_max_age_sec)
                and abs(pnl_pct) < float(self.dead_weight_max_drift_pct)
                and not _inn22_is_moonshot
            )

            # Innovation 3: Age-Tightened Trailing Stop ─ trail tightens as position ages
            # Modifies trail_bps used above; applied here as a post-pass tighter re-check
            # Moonshot positions are exempt: they have their own 250bps activation + 60bps trail
            age_trail_hit = False
            if (
                self.age_trail_tighten_enabled
                and _uses_trail
                and hold_sec > float(self.age_trail_tighten_start_sec)
                and not trail_hit
                and not _inn22_is_moonshot
            ):
                _extra_hold = hold_sec - float(self.age_trail_tighten_start_sec)
                _tighten_factor = float(self.age_trail_tighten_rate) * (_extra_hold / 60.0)
                _tighter_trail_pct = max(float(self.trailing_stop_trail_bps) / 10000.0 - _tighten_factor, 0.0005)
                _pos_key_local = str(pos.order_id) if str(pos.order_id) else f"{pos.symbol}|{pos.entry_time_utc}"
                _cur_peak_local = self._position_peaks.get(_pos_key_local, float(pos.entry_price))
                _activation_pct_local = float(self.trailing_stop_activation_bps) / 10000.0
                _peak_gain_local = (_cur_peak_local - max(float(pos.entry_price), 1e-9)) / max(float(pos.entry_price), 1e-9)
                if _peak_gain_local >= _activation_pct_local and _cur_peak_local > 0.0:
                    _tight_trail_price = _cur_peak_local * (1.0 - _tighter_trail_pct)
                    age_trail_hit = float(last) <= _tight_trail_price

            # Innovation 6: Velocity Reversal on Small Loss ─ cut quickly on downside momentum
            vel_loss_hit = False
            if self.vel_exit_on_loss_enabled and not _uses_trail:
                _pos_key_vl = str(pos.order_id) if str(pos.order_id) else f"{pos.symbol}|{pos.entry_time_utc}"
                _prev_px_vl = self._position_prev_price.get(_pos_key_vl, float(last))
                _vel_vl = (float(last) - _prev_px_vl) / max(_prev_px_vl, 1e-9) * 100.0
                self._position_prev_price[_pos_key_vl] = float(last)
                vel_loss_hit = (
                    hold_sec >= min_hold_sec
                    and pnl_pct <= float(self.vel_exit_on_loss_max_pnl_pct)
                    and _vel_vl <= -float(self.vel_exit_on_loss_vel_threshold_pct)
                )

            # Innovation 7: Conviction-Tiered TP ─ low-confidence positions exit sooner
            conviction_tp_hit = False
            if self.conviction_tiered_tp_enabled and (not _uses_trail):
                _gate_score = self._to_float(getattr(pos, "gate_score", 1.0), 1.0)
                if _gate_score < float(self.conviction_tiered_tp_low_score):
                    conviction_tp_hit = (
                        hold_sec >= min_hold_sec
                        and pnl_pct >= float(self.conviction_tiered_tp_low_tp_pct)
                    )

            # Innovation 8: Moonshot Slot Reserve ─ loosen exit if heat-blocked for too long
            moonshot_tp_hit = False
            if self.moonshot_slot_reserve_enabled and self._heat_blocked_since_utc:
                try:
                    _blocked_dt = self._parse_iso_utc(self._heat_blocked_since_utc)
                    _blocked_dur = (now - _blocked_dt).total_seconds()
                except Exception:
                    _blocked_dur = 0.0
                if _blocked_dur >= float(self.moonshot_slot_reserve_blocked_sec) and (not _uses_trail):
                    moonshot_tp_hit = (
                        hold_sec >= min_hold_sec
                        and pnl_pct >= float(self.moonshot_slot_reserve_tp_override_pct)
                    )

            # Innovation 9: PnL Drawdown Accelerator ─ exit when PnL falls hard from its peak
            pnl_drawdown_hit = False
            if self.pnl_drawdown_accel_enabled and pnl_pct > 0.0:
                _pos_key_pd = str(pos.order_id) if str(pos.order_id) else f"{pos.symbol}|{pos.entry_time_utc}"
                _intra_peak_pnl = self._position_peaks.get(f"pnl_peak_{_pos_key_pd}", pnl_pct)
                if pnl_pct > _intra_peak_pnl:
                    _intra_peak_pnl = pnl_pct
                    self._position_peaks[f"pnl_peak_{_pos_key_pd}"] = _intra_peak_pnl
                _pnl_drop = _intra_peak_pnl - pnl_pct
                pnl_drawdown_hit = (
                    hold_sec >= min_hold_sec
                    and _intra_peak_pnl >= float(self.trailing_stop_activation_bps) / 10000.0
                    and _pnl_drop >= float(self.pnl_drawdown_accel_peak_drop_pct)
                    and not _inn22_is_moonshot  # moonshots use 250bps trail activation
                )

            # ── Innovation 14: Age-Pressure TP Ladder ─────────────────────────
            # As position ages toward max_hold_sec, progressively lower the TP bar.
            # At 70% hold: exit if PnL >= age_pressure_tp_early_min_bps.
            # At 85% hold: exit with any positive PnL — micro-win vs timeout @ zero.
            age_pressure_tp_hit = False
            if self.age_pressure_tp_enabled and not _uses_trail and not _inn22_is_moonshot and hold_sec >= min_hold_sec and pnl_pct > 0.0:
                _hold_util = hold_sec / max(max_hold_sec, 1.0)
                _early_min_pct = float(self.age_pressure_tp_early_min_bps) / 10000.0
                if _hold_util >= float(self.age_pressure_tp_late_pct):
                    age_pressure_tp_hit = True   # late gate: any positive PnL is enough
                elif _hold_util >= float(self.age_pressure_tp_early_pct):
                    age_pressure_tp_hit = pnl_pct >= _early_min_pct
                if age_pressure_tp_hit:
                    print(f"  [inn14] age-pressure TP {symbol}  hold={hold_sec:.0f}s/{max_hold_sec:.0f}s  pnl={pnl_pct*100:.3f}%")

            # ── Innovation 15: Age-Pressure SL Tightener ─────────────────────────
            # As a losing position ages, tighten the effective SL threshold to
            # cut the loss before timeout.  Fractions of base sl_pct are applied:
            # At 50% hold: exit if |loss| >= sl_mid_fraction × sl_pct
            # At 75% hold: exit if |loss| >= sl_late_fraction × sl_pct
            age_pressure_sl_hit = False
            if self.age_pressure_sl_enabled and not _inn22_is_moonshot and hold_sec >= min_hold_sec and pnl_pct < 0.0 and sl_pct > 0.0:
                _hold_util_sl = hold_sec / max(max_hold_sec, 1.0)
                if _hold_util_sl >= float(self.age_pressure_sl_late_pct):
                    _late_sl = sl_pct * float(self.age_pressure_sl_late_fraction)
                    age_pressure_sl_hit = pnl_pct <= -_late_sl
                elif _hold_util_sl >= float(self.age_pressure_sl_mid_pct):
                    _mid_sl = sl_pct * float(self.age_pressure_sl_mid_fraction)
                    age_pressure_sl_hit = pnl_pct <= -_mid_sl
                if age_pressure_sl_hit:
                    _gate_lbl = 'late' if _hold_util_sl >= float(self.age_pressure_sl_late_pct) else 'mid'
                    print(f"  [inn15] age-pressure SL {symbol}  {_gate_lbl}  hold={hold_sec:.0f}s/{max_hold_sec:.0f}s  pnl={pnl_pct*100:.3f}%")

            # ══════════════════════════════════════════════════════════════════

            should_close = (
                tp_hit
                or sl_hit
                or timeout_hit
                or trail_hit
                or profit_lock_hit
                or dead_weight_hit
                or age_trail_hit
                or vel_loss_hit
                or conviction_tp_hit
                or moonshot_tp_hit
                or pnl_drawdown_hit
                or age_pressure_tp_hit
                or age_pressure_sl_hit
            )
            if _vel_exit_hit:
                _close_reason = "velocity_reversal"
            elif profit_lock_hit:
                _close_reason = "profit_lock"
            elif pnl_drawdown_hit:
                _close_reason = "pnl_drawdown_accel"
            elif age_trail_hit:
                _close_reason = "age_trail_tighten"
            elif trail_hit:
                _close_reason = "trailing_stop"
            elif tp_hit:
                _close_reason = "take_profit"
            elif conviction_tp_hit:
                _close_reason = "conviction_tiered_tp"
            elif age_pressure_tp_hit:
                _close_reason = "age_pressure_tp"
            elif age_pressure_sl_hit:
                _close_reason = "age_pressure_sl"
            elif moonshot_tp_hit:
                _close_reason = "moonshot_slot_reserve"
            elif vel_loss_hit:
                _close_reason = "vel_exit_loss"
            elif dead_weight_hit:
                _close_reason = "dead_weight_purge"
            elif sl_hit:
                _close_reason = "stop_loss"
            elif timeout_hit:
                _close_reason = "timeout"
            else:
                _close_reason = "unknown"
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
                        _recon_pos_key = str(pos.order_id) if str(pos.order_id) else f"{pos.symbol}|{pos.entry_time_utc}"
                        self._position_peaks.pop(_recon_pos_key, None)
                        self._position_prev_price.pop(_recon_pos_key, None)
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
                        kill_trip = self._trip_runtime_kill_switch(
                            now,
                            reason="inventory_discrepancy_close_path_no_inventory",
                            symbol=symbol,
                            details={
                                "requested_qty": round(float(requested_close_qty), 10),
                                "available_qty": 0.0,
                            },
                        )
                        self.audit_chain.append(
                            "inventory_discrepancy_detected",
                            {
                                "symbol": symbol,
                                "requested_qty": round(float(requested_close_qty), 10),
                                "available_qty": 0.0,
                                "path": "close_cycle",
                                "auto_kill_switch": dict(kill_trip),
                            },
                        )
                        _write_live_heartbeat(
                            {
                                "status": "critical",
                                "reason": "inventory_discrepancy_detected",
                                "symbol": symbol,
                                "requested_qty": round(float(requested_close_qty), 10),
                                "available_qty": 0.0,
                                "auto_kill_switch": dict(kill_trip),
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

            # Pre-flight: skip positions too small to meet Kraken's minimum notional (~$10)
            _close_notional_usd = float(close_qty) * float(last)
            if _close_notional_usd < 9.5:
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
                _err_str = str(result.get("error"))
                _is_phantom = "insufficient funds" in _err_str.lower()
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
                        "error": _err_str,
                        "phantom_reconciled": _is_phantom,
                    }
                )
                if _is_phantom:
                    # Position not on exchange — reconcile it out so heat resets correctly
                    _pos_key_ph = str(pos.order_id) if str(pos.order_id) else f"{pos.symbol}|{pos.entry_time_utc}"
                    self._position_peaks.pop(_pos_key_ph, None)
                    self._position_prev_price.pop(_pos_key_ph, None)
                    self.portfolio.close_position(pos.symbol, float(last), now.isoformat())
                    self._phantom_skip_symbols[symbol] = now.isoformat()  # Suppress re-injection for 5 min
                    self.audit_chain.append("phantom_position_reconciled", {"symbol": symbol, "qty": float(close_qty), "notional_usd": round(float(close_qty) * float(last), 4)})
                continue

            txid = result.get("txid", ["unknown"])
            txid = txid[0] if isinstance(txid, list) else str(txid)
            close_cfg = self.router.get_symbol_config(symbol) or {}
            close_pair = str(result.get("_router_pair") or close_cfg.get("pair") or "")
            close_quote = str(result.get("_router_quote") or "").upper().strip()

            if close_qty < requested_close_qty:
                pos.qty = float(close_qty)
            # ── Trailing stop / velocity tracker cleanup ──────────────────────
            _close_pos_key = str(pos.order_id) if str(pos.order_id) else f"{pos.symbol}|{pos.entry_time_utc}"
            self._position_peaks.pop(_close_pos_key, None)
            self._position_prev_price.pop(_close_pos_key, None)
            self.portfolio.close_position(pos.symbol, float(last), now.isoformat())

            self.trade_ledger.append(
                {
                    "timestamp": now.isoformat(),
                    "txid": txid,
                    "symbol": symbol,
                    "pair": close_pair,
                    "quote_lane": close_quote,
                    "direction": str(pos.side),
                    "side": close_side,
                    "status": "CLOSED",
                    "execution_mode": "close_cycle",
                    "close_reason": _close_reason,
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
                    "close_reason": _close_reason,
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
            # ── Adaptive Post-Loss Cooldown ───────────────────────────────────
            # Scale symbol re-entry cooldown proportionally to loss magnitude
            if self.adaptive_loss_cooldown_enabled and float(pnl_pct) < 0.0:
                _loss_frac = abs(float(pnl_pct))  # decimal form, e.g. 0.02 for 2% loss
                _base_cd = max(float(self.same_symbol_reentry_cooldown_sec), 0.0)
                _adaptive_cd = min(
                    _base_cd * (1.0 + _loss_frac * float(self.adaptive_loss_cooldown_scale)),
                    float(self.adaptive_loss_cooldown_cap_sec),
                )
                if _adaptive_cd > _base_cd:
                    self._mark_symbol_skip(str(symbol), now, f"adaptive_loss_cooldown_{_close_reason}", _adaptive_cd)
            # ── Innovation 12: Session Symbol Win-Rate Filter ─────────────────
            # Track consecutive W/L streaks per symbol.  Consistent losers get
            # escalating cooldowns; hot win streaks are flagged for preference.
            _sym_key = str(symbol).upper().strip()
            if float(pnl_pct) > 0.0:
                _wins = self._session_symbol_consecutive_wins.get(_sym_key, 0) + 1
                self._session_symbol_consecutive_wins[_sym_key] = _wins
                self._session_symbol_consecutive_losses[_sym_key] = 0
                if _wins >= int(self.session_win_streak_threshold):
                    self._session_hot_symbols.add(_sym_key)
            else:
                _losses = self._session_symbol_consecutive_losses.get(_sym_key, 0) + 1
                self._session_symbol_consecutive_losses[_sym_key] = _losses
                self._session_symbol_consecutive_wins[_sym_key] = 0
                self._session_hot_symbols.discard(_sym_key)
                if _losses >= int(self.session_loss_hard_block_threshold):
                    # 5+ consecutive losses: session-block for the rest of the hour
                    _hard_cd = 3600.0
                    self._mark_symbol_skip(_sym_key, now, "session_loss_hard_block", _hard_cd)
                    print(f"  [inn12] session hard-block {_sym_key}: {_losses} consecutive losses")
                elif _losses >= int(self.session_loss_streak_threshold):
                    # 3+ losses: extended cooldown, stacks per extra loss
                    _streak_cd = float(self.session_loss_streak_cooldown_sec) * (_losses - int(self.session_loss_streak_threshold) + 1)
                    self._mark_symbol_skip(_sym_key, now, "session_loss_streak", _streak_cd)
                    print(f"  [inn12] loss streak cooldown {_sym_key}: {_losses} losses → {_streak_cd:.0f}s skip")
            # ── Innovation 16: Flat-Exit Reentry Dampener ─────────────────────
            # dead_weight_purge or any exit with |pnl| < flat_exit_dampener_min_bps
            # means zero alpha — extend the symbol skip to 15 min to let it rest.
            if self.flat_exit_dampener_enabled:
                _flat_min_pct = float(self.flat_exit_dampener_min_bps) / 10000.0
                _is_flat_close = (
                    _close_reason == "dead_weight_purge"
                    or abs(float(pnl_pct)) < _flat_min_pct
                )
                if _is_flat_close:
                    _damp_cd = float(self.flat_exit_dampener_cooldown_sec)
                    self._mark_symbol_skip(_sym_key, now, "flat_exit_dampener", _damp_cd)
                    print(f"  [inn16] flat-exit dampener {_sym_key}  |pnl|={abs(float(pnl_pct))*10000:.1f}bps  skip={_damp_cd:.0f}s  reason={_close_reason}")
            # ─────────────────────────────────────────────────────────────────
            # ── Innovation 17: Flat-Cluster Regime Pause ──────────────────────
            # Push this close's |pnl| into the rolling window.  If enough
            # recent closes are flat (zero-alpha), trigger a global buy pause.
            if self.cluster_flat_pause_enabled:
                self._recent_close_pnl_abs_bps.append(abs(float(pnl_pct)) * 10000.0)
                _n = len(self._recent_close_pnl_abs_bps)
                if _n >= int(self.cluster_flat_recent_n):
                    _flat_max = float(self.cluster_flat_max_bps)
                    _flat_count = sum(1 for v in self._recent_close_pnl_abs_bps if v < _flat_max)
                    _flat_frac = _flat_count / max(_n, 1)
                    if _flat_frac >= float(self.cluster_flat_threshold_frac):
                        _pause = float(self.cluster_flat_pause_sec)
                        self._set_buy_cooldown(now, _pause)
                        print(f"  [inn17] flat-cluster pause: {_flat_count}/{_n} closes flat (<{_flat_max}bps)  pause={_pause:.0f}s")
            # ─────────────────────────────────────────────────────────────────
            # ── Innovation 18: Dead-Weight Strike Escalator ───────────────────
            # Track how many times this symbol has been dead_weight_purged.
            # From 2nd purge onwards, escalate the skip duration exponentially.
            # Strike 1 = 900s (handled by Inn16).  Strike 2 = 1800s.  3 = 3600s. etc.
            if self.dw_strike_escalator_enabled and _close_reason == "dead_weight_purge":
                _dw_strike = self._dw_strike_count.get(_sym_key, 0) + 1
                self._dw_strike_count[_sym_key] = _dw_strike
                if _dw_strike >= 2:
                    _esc_cd = min(
                        float(self.dw_strike_escalator_base_sec) * (float(self.dw_strike_escalator_multiplier) ** (_dw_strike - 1)),
                        float(self.dw_strike_escalator_max_sec),
                    )
                    self._mark_symbol_skip(_sym_key, now, f"dw_strike_{_dw_strike}", _esc_cd)
                    print(f"  [inn18] dw-strike-escalator {_sym_key}  strike={_dw_strike}  skip={_esc_cd:.0f}s")
            # ─────────────────────────────────────────────────────────────────
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
        if (not self.hard_safety_only_mode) and self._strategy_regime_conflict(strategy, regime_name):
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

        global_close_sweep = self._run_global_close_sweep(now, preferred_symbol=str(symbol))
        pick_meta["global_close_sweep_executed"] = bool(global_close_sweep.get("executed", False))
        pick_meta["global_close_sweep_symbols_scanned"] = int(
            self._to_float(global_close_sweep.get("symbols_scanned", 0), 0.0)
        )
        pick_meta["global_close_sweep_symbols_with_ticker"] = int(
            self._to_float(global_close_sweep.get("symbols_with_ticker", 0), 0.0)
        )
        pick_meta["global_close_sweep_closed_count"] = int(
            self._to_float(global_close_sweep.get("closed_count", 0), 0.0)
        )
        pick_meta["global_close_sweep_reconciled_count"] = int(
            self._to_float(global_close_sweep.get("reconciled_count", 0), 0.0)
        )

        runtime_quote_order_raw = self.runtime_cfg.get("clean_ops_quote_allow", list(DEFAULT_QUOTE_LANES))
        if isinstance(runtime_quote_order_raw, str):
            runtime_quote_order = [s.strip().upper() for s in runtime_quote_order_raw.split(",") if s.strip()]
        elif isinstance(runtime_quote_order_raw, (list, tuple, set)):
            runtime_quote_order = [str(s).upper().strip() for s in runtime_quote_order_raw if str(s).strip()]
        else:
            runtime_quote_order = list(DEFAULT_QUOTE_LANES)
        if not runtime_quote_order:
            runtime_quote_order = list(DEFAULT_QUOTE_LANES)

        ticker = (
            preloaded_ticker
            if isinstance(preloaded_ticker, dict)
            else self.router.get_ticker(symbol, quote_order=runtime_quote_order)
        )
        if not ticker:
            missing_ticker_cooldown_sec = max(
                float(self.missing_ticker_skip_cooldown_sec),
                float(self.loop_seconds) * 2.0,
            )
            self._mark_symbol_skip(
                str(symbol),
                now,
                "missing_ticker",
                cooldown_sec=missing_ticker_cooldown_sec,
            )
            _write_live_heartbeat(
                {
                    "status": "blocked",
                    "reason": "missing_ticker",
                    "symbol": symbol,
                    "symbol_skip_cooldown_sec": round(float(missing_ticker_cooldown_sec), 6),
                    "symbol_skip_active_count": int(len(self._symbol_skip_until_utc)),
                }
            )
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
        hard_safety_bypass_applied = False

        if (not decision_armed) and self.hard_safety_only_mode:
            hard_safety_bypass_applied = True
            decision_armed = True
            if decision_direction not in {"long", "short"}:
                decision_direction = "long" if float(gate_input.direction_hint) >= 0.5 else "short"

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
                    "hard_safety_only_mode": bool(self.hard_safety_only_mode),
                }
            )
            print("  blocked: gate not armed")
            return
        self.gate_not_armed_streak = 0

        bid, ask, last = ticker["bid"], ticker["ask"], ticker["last"]
        mid = max((bid + ask) / 2.0, 1e-9)
        spread_bps = abs((ask - bid) / mid) * 10000.0
        if spread_bps > float(self.hybrid_swing_spread_guard_bps):
            spread_block_cooldown_sec = max(
                float(self.spread_too_wide_skip_cooldown_sec),
                float(self.loop_seconds) * 2.0,
            )
            self._mark_symbol_skip(
                str(symbol),
                now,
                "spread_too_wide",
                cooldown_sec=spread_block_cooldown_sec,
            )
            _write_live_heartbeat({
                "status": "blocked",
                "reason": "spread_too_wide",
                "symbol": symbol,
                "spread_bps": round(spread_bps, 6),
                "symbol_skip_cooldown_sec": round(float(spread_block_cooldown_sec), 6),
                "symbol_skip_active_count": int(len(self._symbol_skip_until_utc)),
            })
            print("  blocked: spread too wide")
            return

        trap_rate_pct = self._symbol_trap_rate_pct(symbol)
        if trap_rate_pct is not None and float(trap_rate_pct) > float(self.max_trap_rate_pct):
            _write_live_heartbeat(
                {
                    "status": "blocked",
                    "reason": "trap_rate",
                    "symbol": symbol,
                    "trap_rate_pct": round(float(trap_rate_pct), 6),
                    "max_trap_rate_pct": round(float(self.max_trap_rate_pct), 6),
                }
            )
            print("  blocked: trap rate")
            return

        reconciled_count = self._reconcile_zero_inventory_positions(symbol, float(last), now)
        if reconciled_count > 0:
            print(f"  reconciled stale positions: {reconciled_count}")

        if self._maybe_close_positions(symbol, float(last), now):
            return

        if decision_direction == "short" and (not self.spot_short_enabled):
            cfg_for_short_probe = self.router.get_symbol_config(symbol) or {}
            probe_min_order = max(self._to_float(cfg_for_short_probe.get("min_order", 0.0), 0.0), 0.0)
            probe_inventory_qty = max(float(self.router.get_asset_balance(symbol, force_refresh=False) or 0.0), 0.0)
            probe_sell_cap_qty = max(probe_inventory_qty * float(self.close_balance_buffer_fraction), 0.0)

            if probe_min_order > 0.0 and probe_sell_cap_qty + 1e-12 >= probe_min_order:
                pick_meta["short_signal_inventory_sell_allowed"] = True
            else:
                live_usd = max(float(self.router.get_balance(force_refresh=False) or 0.0), 0.0)
                reserve_hint = max(self._to_float(self.runtime_cfg.get("reserve_usd", 0.0), 0.0), 0.0)
                affordable_buy_usd = max(float(live_usd) - reserve_hint, 0.0)
                min_order_notional = probe_min_order * float(last)

                if min_order_notional > 0.0 and affordable_buy_usd + 1e-9 >= min_order_notional:
                    decision_direction = "long"
                    pick_meta["short_signal_forced_long"] = True
                    _write_live_heartbeat(
                        {
                            "status": "degraded",
                            "reason": "short_signal_forced_long",
                            "symbol": symbol,
                            "gate_direction": "short",
                            "spot_short_enabled": bool(self.spot_short_enabled),
                            "available_usd": round(float(live_usd), 6),
                            "affordable_buy_usd": round(float(affordable_buy_usd), 6),
                            "min_order_notional": round(float(min_order_notional), 6),
                        }
                    )
                else:
                    short_block_cooldown_sec = max(float(self.symbol_skip_cooldown_sec), float(self.loop_seconds))
                    self._mark_symbol_skip(
                        str(symbol),
                        now,
                        "short_signal_spot_disabled",
                        cooldown_sec=short_block_cooldown_sec,
                    )
                    _write_live_heartbeat(
                        {
                            "status": "blocked",
                            "reason": "short_disabled_spot",
                            "symbol": symbol,
                            "gate_direction": "short",
                            "spot_short_enabled": bool(self.spot_short_enabled),
                            "available_usd": round(float(live_usd), 6),
                            "affordable_buy_usd": round(float(affordable_buy_usd), 6),
                            "min_order_notional": round(float(min_order_notional), 6),
                            "symbol_skip_cooldown_sec": round(float(short_block_cooldown_sec), 6),
                            "symbol_skip_active_count": int(len(self._symbol_skip_until_utc)),
                        }
                    )
                    print("  blocked: spot short disabled (symbol skip armed)")
                    return

        balance_valuation = self._build_balance_valuation(force_refresh=False)
        risk_snapshot = self._compute_live_risk_snapshot(balance_valuation)
        portfolio_heat = float(risk_snapshot.get("effective_portfolio_heat", 0.0))
        open_positions = int(risk_snapshot.get("effective_open_positions", 0))
        open_risk_usd = float(risk_snapshot.get("effective_exposure_usd", 0.0))
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
                open_risk_usd=open_risk_usd,
                portfolio_heat=portfolio_heat,
                symbol_cooldown_active=False,
                open_positions=open_positions,
                max_open_positions=self.max_open_positions,
                live_mode=runtime_live_mode,
                kill_switch=runtime_kill_switch,
            )
        )
        if not risk_allowed:
            # Track how long we've been heat-blocked (feeds Innovation 8: Moonshot Slot Reserve)
            _heat_blocked = any("heat" in str(r).lower() for r in (risk_reasons or []))
            if _heat_blocked:
                if not self._heat_blocked_since_utc:
                    self._heat_blocked_since_utc = now.isoformat()
                # Innovation 10: Heat-Triggered Capital Recycle
                # If heat is the ONLY blocker and we have a preferred symbol queued,
                # sell the weakest position right now so next cycle the buy fires.
                self._heat_recycle_attempt(now, preferred_symbol=str(symbol or ""))
            else:
                self._heat_blocked_since_utc = ""
            _write_live_heartbeat(
                {
                    "status": "blocked",
                    "reason": "risk",
                    "symbol": symbol,
                    "risk_reasons": list(risk_reasons or []),
                    "risk_portfolio_heat_local": round(float(risk_snapshot.get("local_portfolio_heat", 0.0)), 6),
                    "risk_portfolio_heat_live": round(float(risk_snapshot.get("live_portfolio_heat", 0.0)), 6),
                    "risk_portfolio_heat_effective": round(float(risk_snapshot.get("effective_portfolio_heat", 0.0)), 6),
                    "risk_open_positions_local": int(self._to_float(risk_snapshot.get("local_open_positions", 0), 0.0)),
                    "risk_open_positions_live": int(self._to_float(risk_snapshot.get("live_open_positions", 0), 0.0)),
                    "risk_open_positions_effective": int(self._to_float(risk_snapshot.get("effective_open_positions", 0), 0.0)),
                    "risk_exposure_local_usd": round(float(risk_snapshot.get("local_exposure_usd", 0.0)), 6),
                    "risk_exposure_live_usd": round(float(risk_snapshot.get("live_exposure_usd", 0.0)), 6),
                    "risk_exposure_effective_usd": round(float(risk_snapshot.get("effective_exposure_usd", 0.0)), 6),
                    "risk_max_heat": round(float(self.risk_kernel.max_heat), 6),
                    "risk_max_open_positions": int(self.max_open_positions),
                }
            )
            print("  blocked: risk")
            return

        pick_meta["gate_composite_score"] = round(float(gate_decision.composite_score), 6)
        pick_meta["gate_confidence_level"] = round(float(gate_decision.confidence_level), 6)
        pick_meta["gate_expected_edge_bps"] = round(float(gate_input.expected_edge_bps), 6)
        pick_meta["gate_direction"] = str(decision_direction)

        edge_proof = self._edge_proof_decision(now, pick_meta)
        if bool(edge_proof.get("enabled", False)) and (not bool(edge_proof.get("armed", True))):
            _write_live_heartbeat(
                {
                    "status": "blocked",
                    "reason": "edge_proof_not_armed",
                    "symbol": symbol,
                    "edge_proof_reason_codes": list(edge_proof.get("reason_codes", [])),
                    "edge_proof_recent_closed_count": int(self._to_float(edge_proof.get("recent_closed_count", 0), 0.0)),
                    "edge_proof_target_closed_count": int(self._to_float(edge_proof.get("target_closed_count", 0), 0.0)),
                    "edge_proof_win_rate_pct": round(self._to_float(edge_proof.get("win_rate_pct", 0.0), 0.0), 6),
                    "edge_proof_avg_pnl_pct": round(self._to_float(edge_proof.get("avg_pnl_pct", 0.0), 0.0), 6),
                    "edge_proof_last_close_age_min": edge_proof.get("last_close_age_min"),
                    "edge_proof_pass_symbol_intel": bool(edge_proof.get("pass_symbol_intel", True)),
                    "symbol_intel_source": str(edge_proof.get("symbol_intel_source", "none") or "none"),
                    "edge_proof_bootstrap_enabled": bool(edge_proof.get("edge_proof_bootstrap_enabled", False)),
                    "edge_proof_bootstrap_recent_entries_1h": int(self._to_float(edge_proof.get("edge_proof_bootstrap_recent_entries_1h", 0), 0.0)),
                    "edge_proof_bootstrap_max_entries_per_hour": int(self._to_float(edge_proof.get("edge_proof_bootstrap_max_entries_per_hour", 0), 0.0)),
                    "edge_proof_bootstrap_reason_codes": list(edge_proof.get("bootstrap_reason_codes", [])),
                    "edge_proof_bootstrap_gate_score": round(self._to_float(edge_proof.get("edge_proof_bootstrap_gate_score", 0.0), 0.0), 6),
                    "edge_proof_bootstrap_expected_edge_bps": round(self._to_float(edge_proof.get("edge_proof_bootstrap_expected_edge_bps", 0.0), 0.0), 6),
                    "edge_proof_bootstrap_selected_hybrid_score": edge_proof.get("edge_proof_bootstrap_selected_hybrid_score"),
                    "edge_proof_bootstrap_selected_momentum_pct": round(self._to_float(edge_proof.get("edge_proof_bootstrap_selected_momentum_pct", 0.0), 0.0), 6),
                    "edge_proof_bootstrap_selected_spread_bps": edge_proof.get("edge_proof_bootstrap_selected_spread_bps"),
                    "edge_proof_alpha_lock_enabled": bool(edge_proof.get("alpha_lock_enabled", False)),
                    "edge_proof_alpha_lock_pass": bool(edge_proof.get("pass_alpha_lock", True)),
                    "edge_proof_alpha_lock_reason_codes": list(edge_proof.get("alpha_lock_reason_codes", [])),
                    "edge_proof_alpha_lock_selected_symbol": str(edge_proof.get("alpha_lock_selected_symbol", "") or ""),
                    "edge_proof_alpha_lock_direction": str(edge_proof.get("alpha_lock_direction", "") or ""),
                    "edge_proof_alpha_lock_effective_score": edge_proof.get("alpha_lock_effective_score"),
                    "edge_proof_alpha_lock_symbol_alpha_score": edge_proof.get("alpha_lock_symbol_alpha_score"),
                    "edge_proof_alpha_lock_symbol_alpha_source": str(edge_proof.get("alpha_lock_symbol_alpha_source", "not_found") or "not_found"),
                    "edge_proof_alpha_lock_gate_score": round(self._to_float(edge_proof.get("alpha_lock_gate_score", 0.0), 0.0), 6),
                    "edge_proof_alpha_lock_expected_edge_bps": round(self._to_float(edge_proof.get("alpha_lock_expected_edge_bps", 0.0), 0.0), 6),
                }
            )
            print("  blocked: edge proof not armed")
            return

        balance_valuation = balance_valuation if isinstance(balance_valuation, dict) else self._build_balance_valuation(force_refresh=False)
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

        capital_preservation = self._capital_preservation_snapshot(now, quality=edge_proof)
        if (
            side == "buy"
            and bool(capital_preservation.get("enabled", False))
            and (not bool(capital_preservation.get("allow_buy", True)))
        ):
            _write_live_heartbeat(
                {
                    "status": "blocked",
                    "reason": "capital_preservation_hold",
                    "symbol": symbol,
                    "side": side,
                    "capital_preservation_enabled": bool(capital_preservation.get("enabled", False)),
                    "capital_preservation_breach_codes": list(capital_preservation.get("breach_codes", [])),
                    "capital_preservation_recent_closed_count": int(
                        self._to_float(capital_preservation.get("recent_closed_count", 0), 0.0)
                    ),
                    "capital_preservation_required_recent_closed": int(
                        self._to_float(capital_preservation.get("required_recent_closed", 0), 0.0)
                    ),
                    "capital_preservation_win_rate_pct": round(
                        self._to_float(capital_preservation.get("win_rate_pct", 0.0), 0.0),
                        6,
                    ),
                    "capital_preservation_avg_pnl_pct": round(
                        self._to_float(capital_preservation.get("avg_pnl_pct", 0.0), 0.0),
                        6,
                    ),
                    "capital_preservation_consecutive_losses": int(
                        self._to_float(capital_preservation.get("consecutive_losses", 0), 0.0)
                    ),
                    "capital_preservation_pause_until_utc": capital_preservation.get("pause_until_utc"),
                    "capital_preservation_pause_active": bool(capital_preservation.get("pause_active", False)),
                }
            )
            self._save_pacing_state()
            print("  blocked: capital preservation hold")
            return
        capital_reference_usd = max(
            self._to_float(
                self.runtime_cfg.get("initial_capital", getattr(self.portfolio, "initial_capital", 0.0)),
                self._to_float(getattr(self.portfolio, "initial_capital", 0.0), 0.0),
            ),
            0.0,
        )
        live_drawdown_pct = 0.0
        if capital_reference_usd > 0.0:
            live_drawdown_pct = max(
                ((float(capital_reference_usd) - float(portfolio_equity_usd)) / float(capital_reference_usd)) * 100.0,
                0.0,
            )

        if side == "buy" and live_drawdown_pct >= float(self.max_drawdown_pct_limit):
            _write_live_heartbeat(
                {
                    "status": "blocked",
                    "reason": "live_drawdown_limit_hit",
                    "symbol": symbol,
                    "side": side,
                    "live_drawdown_pct": round(float(live_drawdown_pct), 6),
                    "max_drawdown_pct": round(float(self.max_drawdown_pct_limit), 6),
                    "capital_reference_usd": round(float(capital_reference_usd), 6),
                    "portfolio_equity_usd": round(float(portfolio_equity_usd), 6),
                    "quote_usd_balance": round(float(quote_usd_balance), 6),
                    "holdings_value_usd": round(float(holdings_value_usd), 6),
                }
            )
            print("  blocked: live drawdown limit")
            return

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
            self._mark_symbol_skip(str(symbol), now, "no_confirmed_funds")
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
        # ── Innovation 19: Moonshot Size Amplifier ────────────────────────────
        if self.moonshot_amplifier_enabled and side == "buy" and effective_max_notional_usd > 0.0:
            _ms_mult = self._moonshot_size_boost(symbol, float(gate_decision.composite_score))
            if _ms_mult > 1.0:
                _ms_raw = effective_max_notional_usd
                _ms_hard_cap = float(compounding_available_usd) * float(self.moonshot_amplifier_max_cap_pct)
                effective_max_notional_usd = min(effective_max_notional_usd * _ms_mult, _ms_hard_cap)
                print(f"  [inn19] moonshot-amplifier: {symbol} notional {_ms_raw:.2f}→{effective_max_notional_usd:.2f} ({_ms_mult:.2f}x cap={_ms_hard_cap:.2f})")
        # ── Innovation 21: Equity-Scaled Compounding Cap ──────────────────────
        # Automatically scales the per-trade notional cap as equity grows so
        # position sizes compound upward (8.5% of equity by default).
        # This drives the $274 → $10,000 compounding trajectory.
        if self.inn21_equity_scale_enabled and side == "buy":
            _inn21_equity = max(float(portfolio_equity_usd), float(usd_balance), 0.0)
            if _inn21_equity > 0.0:
                _inn21_cap = self._clamp(
                    _inn21_equity * self.inn21_equity_scale_pct,
                    self.inn21_equity_scale_min_cap,
                    self.inn21_equity_scale_hard_max,
                )
                _inn21_affordable_cap = min(_inn21_cap, float(compounding_available_usd) * 0.80)
                if _inn21_affordable_cap > effective_max_notional_usd:
                    print(f"  [inn21] equity-scale: {effective_max_notional_usd:.2f}→{_inn21_affordable_cap:.2f} ({self.inn21_equity_scale_pct*100:.1f}% of ${_inn21_equity:.0f})")
                effective_max_notional_usd = max(effective_max_notional_usd, _inn21_affordable_cap)
        # ─────────────────────────────────────────────────────────────────────
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

        cfg = self.router.get_symbol_config(symbol, quote_order=runtime_quote_order)
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
                    self._mark_symbol_skip(str(symbol), now, str(block_reason))
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
                self._mark_symbol_skip(str(symbol), now, "symbol_concentration_limit")
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
                    self._mark_symbol_skip(str(symbol), now, "symbol_concentration_min_order_conflict")
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
        # Disable Kraken close_template (conditional stop-loss on buy orders).
        # The executor manages all exits via heat-recycle, close-sweep, and timeout.
        # Kraken stop-loss orders created by close_template lock up the full asset
        # balance, causing every subsequent sell attempt to fail with EOrder:Insufficient funds.
        close_template = None
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
        result = self.router.place_order(symbol, side, qty, limit_price, close_template=close_template)
        if "error" in result:
            err_text = str(result.get("error"))
            err_text_l = err_text.lower()
            if "live_orders_disabled" in err_text_l:
                _write_live_heartbeat(
                    {
                        "status": "dry_run",
                        "reason": "live_orders_disabled",
                        "symbol": symbol,
                        "side": side,
                        "urgency": urgency,
                        "spread_bps": round(spread_bps, 6),
                        "size_usd": round(notional_usd, 6),
                        "risk_usd": round(risk_usd, 6),
                        "gate_score": round(float(gate_decision.composite_score), 6),
                        "order_template": order_template,
                        "close_template": close_template,
                        "close_template_armed": bool(close_template),
                    }
                )
                print("  dry-run: live orders disabled")
                return

            window_attempts, window_failures, window_fail_rate, window_throttle = self._record_order_attempt(now, success=False)
            insufficient_funds = "Insufficient funds" in err_text
            volume_min_error = "volume minimum not met" in err_text_l
            available_asset_qty = None

            if insufficient_funds and side == "sell":
                available_asset_qty = max(float(self.router.get_asset_balance(symbol, force_refresh=False) or 0.0), 0.0)

            # On EOrder:Insufficient funds for a BUY, attempt to free capital by
            # cancelling any stale unfilled limit buy orders before escalating throttle.
            if insufficient_funds and side == "buy":
                try:
                    _stale_result = self._cancel_stale_buy_orders(now, force=True)
                    if _stale_result.get("cancelled", 0) > 0:
                        # Capital freed — do NOT escalate fail_streak or throttle
                        self.audit_chain.append("insufficient_funds_stale_release", _stale_result)
                        return
                except Exception:
                    pass

            if volume_min_error or insufficient_funds:
                self.order_fail_streak += 1
                self.notional_throttle = max(self.notional_throttle * self.failure_notional_decay, self.failure_notional_floor)
                if side == "buy":
                    skip_reason = "order_insufficient_funds" if insufficient_funds else "order_volume_minimum"
                    self._mark_symbol_skip(str(symbol), now, skip_reason)

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
        placed_pair = str(result.get("_router_pair") or cfg.get("pair") or "")
        placed_quote = str(result.get("_router_quote") or cfg.get("quote") or "USD").upper().strip()
        if not placed_quote:
            placed_quote = "USD"

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
            self._save_pacing_state()

        self.portfolio.add_position(
            Position(
                symbol=f"{symbol}/{placed_quote}",
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
                "pair": placed_pair,
                "quote_lane": placed_quote,
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
                "pair": placed_pair,
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
                "pair": placed_pair,
                "quote_lane": placed_quote,
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
                "edge_proof": {
                    "enabled": bool(edge_proof.get("enabled", False)),
                    "armed": bool(edge_proof.get("armed", True)),
                    "reason_codes": list(edge_proof.get("reason_codes", [])),
                    "recent_closed_count": int(self._to_float(edge_proof.get("recent_closed_count", 0), 0.0)),
                    "target_closed_count": int(self._to_float(edge_proof.get("target_closed_count", 0), 0.0)),
                    "win_rate_pct": round(self._to_float(edge_proof.get("win_rate_pct", 0.0), 0.0), 6),
                    "avg_pnl_pct": round(self._to_float(edge_proof.get("avg_pnl_pct", 0.0), 0.0), 6),
                    "alpha_lock_enabled": bool(edge_proof.get("alpha_lock_enabled", False)),
                    "pass_alpha_lock": bool(edge_proof.get("pass_alpha_lock", True)),
                    "alpha_lock_reason_codes": list(edge_proof.get("alpha_lock_reason_codes", [])),
                    "alpha_lock_selected_symbol": str(edge_proof.get("alpha_lock_selected_symbol", "") or ""),
                    "alpha_lock_direction": str(edge_proof.get("alpha_lock_direction", "") or ""),
                    "alpha_lock_effective_score": edge_proof.get("alpha_lock_effective_score"),
                    "alpha_lock_symbol_alpha_score": edge_proof.get("alpha_lock_symbol_alpha_score"),
                    "alpha_lock_symbol_alpha_source": str(edge_proof.get("alpha_lock_symbol_alpha_source", "not_found") or "not_found"),
                },
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
                "close_template_armed": bool(close_template),
                "hard_safety_bypass_applied": bool(hard_safety_bypass_applied),
                "ledger_hash": ledger_hash,
                "audit_hash": audit_row.get("event_hash"),
                "status": "PLACED",
            }
        )

        with open(LIVE_TRADE_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.trade_log, f, indent=2)

        # Clear heat-block timer on successful order — the slot is now filled
        self._heat_blocked_since_utc = ""

        _write_live_heartbeat(
            {
                "status": "ok",
                "symbol": symbol,
                "pair": placed_pair,
                "quote_lane": placed_quote,
                "side": side,
                "txid": txid,
                "urgency": urgency,
                "spread_bps": round(spread_bps, 6),
                "size_usd": round(notional_usd, 6),
                "risk_usd": round(risk_usd, 6),
                "min_order_promoted": bool(min_order_promoted),
                "gate_override_applied": bool(gate_override_applied),
                "gate_reason_codes": list(gate_decision.reason_codes or []),
                "edge_proof_enabled": bool(edge_proof.get("enabled", False)),
                "edge_proof_armed": bool(edge_proof.get("armed", True)),
                "edge_proof_reason_codes": list(edge_proof.get("reason_codes", [])),
                "edge_proof_bootstrap_applied": bool(edge_proof.get("bootstrap_applied", False)),
                "edge_proof_bootstrap_reason_codes": list(edge_proof.get("bootstrap_reason_codes", [])),
                "edge_proof_bootstrap_applied": bool(edge_proof.get("bootstrap_applied", False)),
                "edge_proof_bootstrap_reason_codes": list(edge_proof.get("bootstrap_reason_codes", [])),
                "edge_proof_recent_closed_count": int(self._to_float(edge_proof.get("recent_closed_count", 0), 0.0)),
                "edge_proof_win_rate_pct": round(self._to_float(edge_proof.get("win_rate_pct", 0.0), 0.0), 6),
                "edge_proof_avg_pnl_pct": round(self._to_float(edge_proof.get("avg_pnl_pct", 0.0), 0.0), 6),
                "edge_proof_alpha_lock_enabled": bool(edge_proof.get("alpha_lock_enabled", False)),
                "edge_proof_alpha_lock_pass": bool(edge_proof.get("pass_alpha_lock", True)),
                "edge_proof_alpha_lock_reason_codes": list(edge_proof.get("alpha_lock_reason_codes", [])),
                "edge_proof_alpha_lock_effective_score": edge_proof.get("alpha_lock_effective_score"),
                "edge_proof_alpha_lock_symbol_alpha_score": edge_proof.get("alpha_lock_symbol_alpha_score"),
                "edge_proof_alpha_lock_symbol_alpha_source": str(edge_proof.get("alpha_lock_symbol_alpha_source", "not_found") or "not_found"),
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
                "risk_open_positions_local": int(self._to_float(risk_snapshot.get("local_open_positions", 0), 0.0)),
                "risk_open_positions_live": int(self._to_float(risk_snapshot.get("live_open_positions", 0), 0.0)),
                "risk_exposure_effective_usd": round(float(risk_snapshot.get("effective_exposure_usd", 0.0)), 6),
                "live_drawdown_pct": round(float(live_drawdown_pct), 6),
                "max_drawdown_pct": round(float(self.max_drawdown_pct_limit), 6),
                "close_template_armed": bool(close_template),
                "hard_safety_bypass_applied": bool(hard_safety_bypass_applied),
            }
        )

        if bool(edge_proof.get("bootstrap_applied", False)):
            self.edge_proof_bootstrap_entry_utc = [
                ts
                for ts in self.edge_proof_bootstrap_entry_utc
                if isinstance(ts, datetime) and (now - ts).total_seconds() <= 3600.0
            ]
            self.edge_proof_bootstrap_entry_utc.append(now)
            self._save_pacing_state()

        self._recover_gate_threshold_after_fill(now)

        print(f"  placed txid={txid}")

    def run_institutional_execution_loop(self):
        print(f"starting live loop (interval={self.loop_seconds:.2f}s, max_open={self.max_open_positions})")
        # Startup: cancel any stale open orders from previous sessions that may be
        # locking reserved crypto balances and blocking new sell orders.
        try:
            _startup_cancel = self.router.cancel_all_orders()
            _cancelled_count = int(_startup_cancel.get("count", 0) if isinstance(_startup_cancel, dict) else 0)
            if _cancelled_count > 0:
                self.audit_chain.append("startup_stale_orders_cancelled", {"count": _cancelled_count})
                print(f"startup: cancelled {_cancelled_count} stale open order(s) to release reserved balance")
        except Exception as _startup_cancel_err:
            print(f"startup: cancel_all_orders error (non-fatal): {_startup_cancel_err}")
        while True:
            try:
                self._refresh_runtime_config()
                runtime_symbol_raw = str(self.runtime_cfg.get("symbol", "") or "").strip()
                runtime_symbol_upper = runtime_symbol_raw.upper()
                force_universe_mode = bool(self.runtime_cfg.get("force_universe_mode", False))
                runtime_symbol_requested = runtime_symbol_upper
                runtime_symbol_overridden = False
                if force_universe_mode and runtime_symbol_upper not in {"", "UNIVERSE", "ADAPTIVE_UNIVERSE", "AUTO"}:
                    runtime_symbol_upper = "UNIVERSE"
                    runtime_symbol_overridden = True

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
                    "symbol_intel_short_candidate_count": 0,
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

                scan_top_n_raw = self._to_float(self.runtime_cfg.get("scan_top_n", 1200), 1200.0)
                if scan_top_n_raw <= 0.0:
                    # Explicit runtime convention: scan_top_n <= 0 means "scan entire tradable universe".
                    scan_cap = 0
                else:
                    scan_cap = int(self._clamp(scan_top_n_raw, 4.0, 50000.0))
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
                loop_now = datetime.now(timezone.utc)
                self._prune_symbol_skip_map(loop_now)
                # Periodic stale buy-order sweep — frees locked capital every 5 min
                if self._stale_order_cleanup_due(loop_now):
                    try:
                        self._cancel_stale_buy_orders(loop_now, force=False)
                    except Exception:
                        pass
                symbol_skip_active_count = int(len(self._symbol_skip_until_utc))
                _write_live_heartbeat(
                    {
                        "status": "running",
                        "reason": "scan_cycle_start",
                        "universe_mode": bool(universe_mode),
                        "runtime_symbol_requested": runtime_symbol_requested,
                        "runtime_symbol_overridden": bool(runtime_symbol_overridden),
                        "force_universe_mode": bool(force_universe_mode),
                        "preferred_symbol": preferred,
                        "preferred_source": preferred_source,
                        "universe_scan_cap": int(scan_cap),
                        "universe_scan_uncapped": bool(scan_cap <= 0),
                        "gate_min_composite_score": round(float(getattr(self.signal_gate, "min_composite_score", 0.60)), 6),
                        "adaptive_gate_enabled": bool(self.adaptive_gate_enabled),
                        "adaptive_gate_relax_offset": round(float(self.gate_relax_offset), 6),
                        "symbol_intel_enabled": bool(intel_meta.get("symbol_intel_enabled", False)),
                        "symbol_intel_source": str(intel_meta.get("symbol_intel_source", "none") or "none"),
                        "symbol_intel_stale": bool(intel_meta.get("symbol_intel_stale", False)),
                        "symbol_intel_age_sec": intel_meta.get("symbol_intel_age_sec"),
                        "symbol_intel_selected_count": int(self._to_float(intel_meta.get("symbol_intel_selected_count", 0), 0.0)),
                        "symbol_intel_short_candidate_count": int(self._to_float(intel_meta.get("symbol_intel_short_candidate_count", 0), 0.0)),
                        "quote_usd_hint": round(float(quote_usd_hint), 6),
                        "total_cash_usd_hint": round(float(total_cash_usd_hint), 6),
                        "stable_cash_equivalent_usd_hint": round(float(stable_cash_equivalent_hint), 6),
                        "cash_usd_hint": round(float(self._to_float(valuation_hint.get("cash_usd", 0.0), 0.0)), 6),
                        "holdings_value_usd_hint": round(float(self._to_float(valuation_hint.get("holdings_value_usd", 0.0), 0.0)), 6),
                        "total_equity_usd_hint": round(float(self._to_float(valuation_hint.get("total_equity_usd", 0.0), 0.0)), 6),
                        "largest_holding_symbol": str(valuation_hint.get("largest_symbol", "") or ""),
                        "largest_holding_weight_pct": round(float(self._to_float(valuation_hint.get("largest_weight_pct", 0.0), 0.0)), 6),
                        "symbol_skip_active_count": int(symbol_skip_active_count),
                    }
                )

                runtime_whitelist: set[str] = set()
                for field_name in ("symbol_whitelist", "symbol_allowlist"):
                    raw_values = self.runtime_cfg.get(field_name, [])
                    if isinstance(raw_values, str):
                        raw_values = [s.strip() for s in raw_values.split(",") if str(s).strip()]
                    if isinstance(raw_values, list):
                        runtime_whitelist.update(
                            str(s).upper().strip() for s in raw_values if str(s).strip()
                        )

                runtime_extra_symbols: list[str] = []
                for field_name in ("symbol_universe_extra", "symbols"):
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
                runtime_whitelist_size = int(len(runtime_whitelist))
                whitelist_enforced_count = int(len(candidates))
                hybrid_whitelist_relaxed_added = 0
                hybrid_whitelist_relax_target = 0

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
                if preferred and str(preferred).upper().strip() in blocked:
                    preferred = ""
                    preferred_source = "runtime_blocked"
                if not candidates:
                    candidates = [s for s in SYMBOL_REGISTRY.keys() if s.upper() not in blocked]

                # When an explicit runtime whitelist is provided, enforce it first.
                if runtime_whitelist:
                    all_candidates_pre_whitelist = list(candidates)
                    candidates = [s for s in candidates if str(s).upper().strip() in runtime_whitelist]
                    if not candidates:
                        candidates = [
                            s
                            for s in sorted(runtime_whitelist)
                            if s not in blocked and self.router.get_symbol_config(s) is not None
                        ]
                    whitelist_enforced_count = int(len(candidates))

                    # Hybrid swing mode can widen beyond strict whitelist when breadth is too low.
                    if universe_mode and self.hybrid_swing_whitelist_relax_enabled:
                        hybrid_whitelist_relax_target = int(
                            min(
                                max(int(self.hybrid_swing_min_candidates), int(whitelist_enforced_count)),
                                int(self.hybrid_swing_relax_cap),
                            )
                        )
                        if len(candidates) < hybrid_whitelist_relax_target:
                            expansion_pool = [
                                s
                                for s in all_candidates_pre_whitelist
                                if str(s).upper().strip() not in runtime_whitelist
                            ]
                            if expansion_pool:
                                random.shuffle(expansion_pool)
                                needed = max(hybrid_whitelist_relax_target - len(candidates), 0)
                                if needed > 0:
                                    before_len = len(candidates)
                                    candidates = list(dict.fromkeys(list(candidates) + expansion_pool[:needed]))
                                    hybrid_whitelist_relaxed_added = max(len(candidates) - before_len, 0)

                if candidates and symbol_skip_active_count > 0:
                    non_skipped_candidates = [
                        s for s in candidates if not self._symbol_skip_active(str(s), loop_now)
                    ]
                    if non_skipped_candidates:
                        candidates = non_skipped_candidates

                symbol_skip_active_count = int(len(self._symbol_skip_until_utc))

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
                preferred_skipped = bool(self._symbol_skip_active(symbol, loop_now)) if symbol else False
                preferred_spread_bps = float("inf")
                preferred_spread_limit_bps = float(self.preferred_symbol_max_spread_bps)
                if float(self.universe_hard_reject_spread_bps) > 0.0:
                    preferred_spread_limit_bps = min(
                        float(preferred_spread_limit_bps),
                        float(self.universe_hard_reject_spread_bps),
                    )
                preferred_rejected_reason = "preferred_symbol_skip_active" if preferred_skipped else ""
                preferred_ticker = self.router.get_ticker(symbol) if (symbol and preferred_cfg and symbol not in blocked and (not preferred_skipped)) else None
                if preferred_ticker:
                    preferred_spread_bps = self._spread_bps_from_ticker(preferred_ticker)
                    if (not math.isfinite(preferred_spread_bps)) or preferred_spread_bps > float(preferred_spread_limit_bps):
                        preferred_rejected_reason = "preferred_spread_too_wide"
                        self._mark_symbol_skip(
                            symbol,
                            loop_now,
                            preferred_rejected_reason,
                            cooldown_sec=max(float(self.spread_too_wide_skip_cooldown_sec), float(self.symbol_skip_cooldown_sec)),
                        )
                        preferred_skipped = True
                        preferred_ticker = None
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
                    "preferred_symbol_skipped": bool(preferred_skipped),
                    "preferred_spread_bps": round(float(preferred_spread_bps), 6) if math.isfinite(preferred_spread_bps) else None,
                    "preferred_spread_limit_bps": round(float(preferred_spread_limit_bps), 6),
                    "preferred_rejected_reason": preferred_rejected_reason,
                    "universe_mode": bool(universe_mode),
                    "preferred_min_order_notional": round(float(preferred_min_order_notional), 6),
                    "blocked_count": len(blocked),
                    "universe_scan_cap": int(scan_cap),
                    "universe_extra_count": int(len(runtime_extra_symbols)),
                    "symbol_skip_active_count": int(symbol_skip_active_count),
                    "symbol_intel_source": str(intel_meta.get("symbol_intel_source", "none") or "none"),
                    "symbol_intel_stale": bool(intel_meta.get("symbol_intel_stale", False)),
                    "symbol_intel_age_sec": intel_meta.get("symbol_intel_age_sec"),
                    "symbol_intel_candidate_count": int(self._to_float(intel_meta.get("symbol_intel_candidate_count", 0), 0.0)),
                    "symbol_intel_selected_count": int(self._to_float(intel_meta.get("symbol_intel_selected_count", 0), 0.0)),
                    "symbol_intel_executable_count": int(self._to_float(intel_meta.get("symbol_intel_executable_count", 0), 0.0)),
                    "symbol_intel_short_candidate_count": int(self._to_float(intel_meta.get("symbol_intel_short_candidate_count", 0), 0.0)),
                    "symbol_intel_rejected_unpriced": int(self._to_float(intel_meta.get("symbol_intel_rejected_unpriced", 0), 0.0)),
                    "symbol_intel_rejected_affordable": int(self._to_float(intel_meta.get("symbol_intel_rejected_affordable", 0), 0.0)),
                    "symbol_intel_rejected_cap": int(self._to_float(intel_meta.get("symbol_intel_rejected_cap", 0), 0.0)),
                    "reserve_usd_configured": round(float(reserve_usd_configured), 6),
                    "reserve_usd_effective": round(float(reserve_usd_hint), 6),
                    "universe_candidate_count": int(len(candidates)),
                    "runtime_whitelist_size": int(runtime_whitelist_size),
                    "runtime_whitelist_enforced_count": int(whitelist_enforced_count),
                    "hybrid_whitelist_relax_enabled": bool(self.hybrid_swing_whitelist_relax_enabled),
                    "hybrid_whitelist_relax_target": int(hybrid_whitelist_relax_target),
                    "hybrid_whitelist_relaxed_added": int(hybrid_whitelist_relaxed_added),
                    "hybrid_swing_selector_enabled": bool(self.hybrid_swing_selector_enabled),
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
                    selection_meta["symbol_skip_active_count"] = int(symbol_skip_active_count)
                    selection_meta["symbol_intel_source"] = str(intel_meta.get("symbol_intel_source", "none") or "none")
                    selection_meta["symbol_intel_stale"] = bool(intel_meta.get("symbol_intel_stale", False))
                    selection_meta["symbol_intel_age_sec"] = intel_meta.get("symbol_intel_age_sec")
                    selection_meta["symbol_intel_candidate_count"] = int(self._to_float(intel_meta.get("symbol_intel_candidate_count", 0), 0.0))
                    selection_meta["symbol_intel_selected_count"] = int(self._to_float(intel_meta.get("symbol_intel_selected_count", 0), 0.0))
                    selection_meta["symbol_intel_executable_count"] = int(self._to_float(intel_meta.get("symbol_intel_executable_count", 0), 0.0))
                    selection_meta["symbol_intel_short_candidate_count"] = int(self._to_float(intel_meta.get("symbol_intel_short_candidate_count", 0), 0.0))
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
                    selection_meta["runtime_whitelist_size"] = int(runtime_whitelist_size)
                    selection_meta["runtime_whitelist_enforced_count"] = int(whitelist_enforced_count)
                    selection_meta["hybrid_whitelist_relax_enabled"] = bool(self.hybrid_swing_whitelist_relax_enabled)
                    selection_meta["hybrid_whitelist_relax_target"] = int(hybrid_whitelist_relax_target)
                    selection_meta["hybrid_whitelist_relaxed_added"] = int(hybrid_whitelist_relaxed_added)
                    selection_meta["hybrid_swing_selector_enabled"] = bool(self.hybrid_swing_selector_enabled)
                    selection_meta["universe_scan_cap"] = int(scan_cap)
                    selection_meta["universe_scan_uncapped"] = bool(scan_cap <= 0)
                    selection_meta["preferred_min_order_notional"] = round(float(preferred_min_order_notional), 6)
                    selection_meta["preferred_source"] = preferred_source
                    selection_meta["universe_mode"] = bool(universe_mode)
                    if not symbol:
                        self._write_live_operator_approval_queue(loop_now, "", selection_meta)
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

                selection_meta["universe_scan_cap"] = int(scan_cap)
                selection_meta["universe_scan_uncapped"] = bool(scan_cap <= 0)

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
                self.last_selected_symbol = str(symbol).upper().strip()
                self.last_symbol_selection_meta = dict(selection_meta)
                self._write_live_operator_approval_queue(loop_now, str(symbol), selection_meta)

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

                hard_zero_buying_power = (
                    affordable_usd_hint <= 0.0
                    and quote_usd_hint <= 0.0
                    and total_cash_usd_hint <= 0.0
                    and holdings_value_hint <= 0.0
                )
                unaffordable_by_balance = (
                    (affordable_usd_hint > 0.0 and selected_min_notional > affordable_usd_hint)
                    or (hard_zero_buying_power and selected_min_notional > 0.0)
                )
                unaffordable_by_cap = max_notional_usd_cap > 0.0 and selected_min_notional > max_notional_usd_cap
                if selected_min_notional > 0.0 and (unaffordable_by_balance or unaffordable_by_cap):
                    self.no_affordable_streak += 1
                    self._mark_symbol_skip(
                        str(symbol),
                        loop_now,
                        "no_affordable_symbol",
                        cooldown_sec=max(float(self.symbol_skip_cooldown_sec), float(self.loop_seconds)),
                    )
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
                            "hard_zero_buying_power": bool(hard_zero_buying_power),
                            "symbol_skip_cooldown_sec": round(float(self.symbol_skip_cooldown_sec), 6),
                            "symbol_skip_active_count": int(len(self._symbol_skip_until_utc)),
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
    duplicate_child, root_pid = _is_duplicate_child_executor()
    if duplicate_child:
        _write_live_heartbeat(
            {
                "status": "blocked",
                "reason": "duplicate_child_executor",
                "root_pid": int(root_pid),
                "pid": int(os.getpid()),
            }
        )
        print(f"duplicate child live_executor detected (root_pid={root_pid}, pid={os.getpid()})")
        raise SystemExit(0)

    os.environ["LUMA_LIVE_EXECUTOR_ROOT_PID"] = str(os.getpid())

    if not _acquire_executor_lock():
        raise SystemExit(0)
    atexit.register(_release_executor_lock)
    api_keys = load_api_keys()
    executor = RobustLiveExecutor(api_keys)
    try:
        executor.run_institutional_execution_loop()
    finally:
        _release_executor_lock()
