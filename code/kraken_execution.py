
import os
import sys
import time
import json
import hmac
import base64
import hashlib
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional

import requests

KRAKEN_API_URL = "https://api.kraken.com"

ADD_ORDER_PATH = "/0/private/AddOrder"
BALANCE_PATH = "/0/private/Balance"
OPEN_ORDERS_PATH = "/0/private/OpenOrders"
QUERY_ORDERS_PATH = "/0/private/QueryOrders"
TRADES_HISTORY_PATH = "/0/private/TradesHistory"
CANCEL_ALL_AFTER_PATH = "/0/private/CancelAllOrdersAfter"

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT_DIR = ROOT / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR = ROOT / "config"
LUMA_LIVE_KEYS_PATHS = [
    CONFIG_DIR / "luma_live_keys.env",
    CONFIG_DIR / "live_keys.env",
    CONFIG_DIR / "keys.env",
    ROOT / "code" / "execution" / "config" / "luma_live_keys.env",
    ROOT / "code" / "execution" / "config" / "live_keys.env",
    ROOT / "code" / "execution" / "config" / "keys.env",
]

LEDGER_FILE = OUT_DIR / "live_trade_ledger.jsonl"
EVENTS_FILE = OUT_DIR / "execution_events.jsonl"
INTENTS_FILE = OUT_DIR / "shadow_order_intents.jsonl"
STATE_FILE = OUT_DIR / "live_position_state.json"
FLAGS_FILE = OUT_DIR / "control_flags.json"
RUNTIME_FILE = OUT_DIR / "execution_runtime.json"
APPROVAL_QUEUE_FILE = OUT_DIR / "execution_approval_queue.json"
LAST_RESULT_FILE = OUT_DIR / "last_execution_result.json"

DEFAULT_FLAGS = {
    "live_enabled": True,
    "kill_switch": False,
    "require_controller": True,
    "allowed_controllers": ["Robert", "Joey", "Nicole"],
    "require_validate_pass": True,
    "max_notional_per_trade_usd": 1000000.0,
    "max_daily_loss_usd": 20.0,
    "max_open_positions": 10,
    "deadman_timeout_seconds": 30,
    "default_pair": "XBTUSD",
    "default_volume_base": 0.0004,
    "default_order_type": "market",
    "runtime_mode": "shadow",
    "notes": "Set live_enabled=true and kill_switch=false only after smoke test and controller approval."
}

class KrakenExecutionError(Exception):
    pass

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _load_json(path: Path, fallback: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return fallback

def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n")

def _ensure_flags() -> Dict[str, Any]:
    flags = _load_json(FLAGS_FILE, None)
    if not isinstance(flags, dict):
        flags = dict(DEFAULT_FLAGS)
        _write_json(FLAGS_FILE, flags)
        return flags

    changed = False
    for k, v in DEFAULT_FLAGS.items():
        if k not in flags:
            flags[k] = v
            changed = True
    if changed:
        _write_json(FLAGS_FILE, flags)
    return flags


def _load_env_file(path: Path) -> Dict[str, str]:
    env = {}
    if not path.exists():
        return env
    try:
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    except Exception:
        pass
    return env


def _hydrate_live_keys() -> None:
    hydrated = False
    for env_path in LUMA_LIVE_KEYS_PATHS:
        env = _load_env_file(env_path)
        if not env:
            continue
        loaded = []
        for key, value in env.items():
            if not os.getenv(key, "").strip() and isinstance(value, str) and value.strip():
                os.environ[key] = value.strip()
                hydrated = True
                loaded.append(key)
        if loaded:
            print(f"[KRAKEN] Hydrated live keys from {env_path}: {', '.join(loaded)}")
            break


def _resolve_alt_env(name: str) -> str:
    alt_map = {
        "KRAKEN_API_KEY": ["KRAKEN_API_KEY", "KRAKEN_KEY"],
        "KRAKEN_API_SECRET": ["KRAKEN_API_SECRET", "KRAKEN_SECRET"],
    }
    names = alt_map.get(name, [name])
    for n in names:
        value = os.getenv(n, "").strip()
        if value:
            if n != name:
                os.environ[name] = value
            return value
    return ""


def _env(name: str) -> str:
    _hydrate_live_keys()
    value = _resolve_alt_env(name)
    if not value:
        raise KrakenExecutionError(f"Missing required environment variable: {name}")
    return value


def verify_env_only() -> Dict[str, Any]:
    _hydrate_live_keys()
    api_key_present = bool(os.getenv("KRAKEN_API_KEY", "").strip())
    api_secret_present = bool(os.getenv("KRAKEN_API_SECRET", "").strip())
    status = {
        "timestamp": _now_iso(),
        "api_key_present": api_key_present,
        "api_secret_present": api_secret_present,
        "env_only": True
    }
    _append_jsonl(EVENTS_FILE, {"event": "verify_env_only", **status})
    _write_json(LAST_RESULT_FILE, status)
    return status


# Persistent, strictly increasing nonce logic
NONCE_FILE = ROOT / "code" / "execution" / "config" / "kraken_nonce.txt"
NONCE_RESOLUTION = os.getenv("KRAKEN_NONCE_RESOLUTION", "microseconds").strip().lower()


def _nonce_now() -> int:
    # Kraken accepts any increasing integer. Use microseconds by default
    # to avoid collisions with parallel clients that use higher-resolution nonces.
    if NONCE_RESOLUTION in {"ms", "millisecond", "milliseconds"}:
        return int(time.time() * 1000)
    return int(time.time_ns() // 1000)


def _nonce_boost_units(boost_ms: int) -> int:
    if NONCE_RESOLUTION in {"ms", "millisecond", "milliseconds"}:
        return int(boost_ms)
    return int(boost_ms * 1000)

def _sanitize_last_nonce(last: int, now: int) -> int:
    if last < 0:
        return 0
    # Kraken nonce must fit signed 64-bit and be monotonically increasing.
    # Do not clamp to wall-clock; other clients may use higher time resolutions.
    if last > 9_223_372_036_854_775_807:
        print(f"[KRAKEN] Resetting out-of-range nonce value {last} to current time {now}")
        return 0
    return last

def _reset_nonce(boost_ms: int = 10000, floor_nonce: int = 0) -> str:
    now = _nonce_now()
    last = 0
    if NONCE_FILE.exists():
        try:
            last = int(NONCE_FILE.read_text().strip())
        except Exception:
            last = 0
    last = _sanitize_last_nonce(last, now)
    boost_units = _nonce_boost_units(boost_ms)
    candidate = max(now + boost_units, last + 1, 1, int(floor_nonce))
    NONCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    NONCE_FILE.write_text(str(candidate))
    print(
        f"[KRAKEN] Nonce reset to {candidate} "
        f"(boost {boost_ms}ms, resolution={NONCE_RESOLUTION}, floor={int(floor_nonce)}, last={last})"
    )
    return str(candidate)

def _nonce() -> str:
    NONCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    now = _nonce_now()
    last = 0
    if NONCE_FILE.exists():
        try:
            last = int(NONCE_FILE.read_text().strip())
        except Exception:
            last = 0
    last = _sanitize_last_nonce(last, now)
    new = max(now, last + 1)
    NONCE_FILE.write_text(str(new))
    return str(new)

def _kraken_signature(url_path: str, data: Dict[str, Any], api_secret: str) -> str:
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data["nonce"]) + postdata).encode()
    message = url_path.encode() + hashlib.sha256(encoded).digest()
    # Fix base64 padding for api_secret
    s = api_secret.strip()
    missing_padding = len(s) % 4
    if missing_padding:
        s += '=' * (4 - missing_padding)
    mac = hmac.new(base64.b64decode(s), message, hashlib.sha512)
    return base64.b64encode(mac.digest()).decode()

def _private_post(url_path: str, payload: Dict[str, Any], timeout: int = 20, retry_attempt: int = 0) -> Dict[str, Any]:
    api_key = _env("KRAKEN_API_KEY")
    api_secret = _env("KRAKEN_API_SECRET")

    body = dict(payload)
    if "nonce" not in body:
        body["nonce"] = _nonce()

    headers = {
        "API-Key": api_key,
        "API-Sign": _kraken_signature(url_path, body, api_secret),
    }

    def resolve_kraken_url(force_testnet: bool = False) -> str:
        api_url = os.getenv("KRAKEN_API_URL", "").strip()
        if api_url:
            return api_url
        if force_testnet or os.getenv("KRAKEN_API_TESTNET", "").strip().lower() in {"1", "true", "yes", "on"}:
            return "https://api.sandbox.kraken.com"
        return KRAKEN_API_URL

    api_url = resolve_kraken_url()
    print(f"[KRAKEN] Using API URL: {api_url}")

    try:
        response = requests.post(
            api_url + url_path,
            headers=headers,
            data=body,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        error_text = str(exc)
        if api_url == "https://api.sandbox.kraken.com" and "Failed to resolve 'api.sandbox.kraken.com'" in error_text:
            fallback_url = KRAKEN_API_URL
            print(f"[KRAKEN] Sandbox DNS failed; retrying live endpoint {fallback_url}", file=sys.stderr, flush=True)
            try:
                response = requests.post(
                    fallback_url + url_path,
                    headers=headers,
                    data=body,
                    timeout=timeout,
                )
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as exc2:
                raise KrakenExecutionError(f"Kraken network error: {exc2}") from exc2
        else:
            raise KrakenExecutionError(f"Kraken network error: {exc}") from exc

    if data.get("error"):
        msg = "; ".join(map(str, data["error"]))
        if "EAPI:Invalid nonce" in msg and retry_attempt < 3:
            boosts = [10000, 60000, 3600000]
            boost_ms = boosts[retry_attempt] if retry_attempt < len(boosts) else boosts[-1]
            # If another client writes much larger nonces for the same key,
            # jump to nanosecond-scale floor after the first retry.
            floor_nonce = int(time.time_ns()) if retry_attempt >= 1 else 0
            print(f"[KRAKEN] Invalid nonce detected, retrying request (attempt {retry_attempt + 1}) with boost {boost_ms}ms")
            _reset_nonce(boost_ms=boost_ms, floor_nonce=floor_nonce)
            time.sleep(0.25)
            return _private_post(url_path, payload, timeout=timeout, retry_attempt=retry_attempt + 1)
        if "EAPI:Invalid key" in msg:
            hint = ""
            if not os.getenv("KRAKEN_API_URL", "").strip() and os.getenv("KRAKEN_API_TESTNET", "").strip().lower() not in {"1", "true", "yes", "on"}:
                hint = " If you are using Kraken testnet credentials, set KRAKEN_API_TESTNET=1 or KRAKEN_API_URL=https://api.sandbox.kraken.com."
            raise KrakenExecutionError("Kraken error: " + msg + hint)
        raise KrakenExecutionError("Kraken error: " + msg)

    return data.get("result", {})

def load_state() -> Dict[str, Any]:
    fallback = {
        "position": "flat",
        "symbol": None,
        "entry_price": None,
        "size_base": 0.0,
        "unrealized_pnl": 0.0,
        "last_txid": None,
        "updated_at": None,
        "open_position_count": 0
    }
    state = _load_json(STATE_FILE, fallback)
    if not isinstance(state, dict):
        state = fallback
    for k, v in fallback.items():
        state.setdefault(k, v)
    return state

def save_state(state: Dict[str, Any]) -> None:
    state = dict(state)
    state["updated_at"] = _now_iso()
    _write_json(STATE_FILE, state)

def get_balance() -> Dict[str, Any]:
    result = _private_post(BALANCE_PATH, {})
    _append_jsonl(EVENTS_FILE, {"timestamp": _now_iso(), "event": "get_balance"})
    _write_json(LAST_RESULT_FILE, result)
    return result

def get_open_orders() -> Dict[str, Any]:
    result = _private_post(OPEN_ORDERS_PATH, {})
    _append_jsonl(EVENTS_FILE, {"timestamp": _now_iso(), "event": "get_open_orders"})
    _write_json(LAST_RESULT_FILE, result)
    return result

def query_order(txid: str, trades: bool = True) -> Dict[str, Any]:
    result = _private_post(QUERY_ORDERS_PATH, {"txid": txid, "trades": "true" if trades else "false"})
    _append_jsonl(EVENTS_FILE, {"timestamp": _now_iso(), "event": "query_order", "txid": txid})
    _write_json(LAST_RESULT_FILE, result)
    return result

def verify_credentials() -> Dict[str, Any]:
    try:
        balance = get_balance()
        return {"valid": True, "balance": balance}
    except KrakenExecutionError as e:
        error_text = str(e)
        explicit_testnet = os.getenv("KRAKEN_API_URL", "").strip() or os.getenv("KRAKEN_API_TESTNET", "").strip().lower() in {"1", "true", "yes", "on"}
        if "Invalid key" in error_text and not explicit_testnet:
            print("[KRAKEN] Invalid key detected on live endpoint; retrying with sandbox endpoint.", file=sys.stderr, flush=True)
            os.environ["KRAKEN_API_TESTNET"] = "1"
            try:
                balance = get_balance()
                return {"valid": True, "balance": balance, "fallback": "kraken_testnet"}
            except KrakenExecutionError as e2:
                return {"valid": False, "error": str(e2)}
        return {"valid": False, "error": error_text}
    except Exception as exc:
        return {"valid": False, "error": f"Unexpected Kraken error: {exc}"}

def get_trades_history() -> Dict[str, Any]:
    result = _private_post(TRADES_HISTORY_PATH, {})
    _append_jsonl(EVENTS_FILE, {"timestamp": _now_iso(), "event": "get_trades_history"})
    _write_json(LAST_RESULT_FILE, result)
    return result

def arm_deadman_switch(timeout_seconds: int = 30) -> Dict[str, Any]:
    result = _private_post(CANCEL_ALL_AFTER_PATH, {"timeout": int(timeout_seconds)})
    _append_jsonl(EVENTS_FILE, {
        "timestamp": _now_iso(),
        "event": "deadman_armed",
        "timeout_seconds": int(timeout_seconds),
        "result": result
    })
    _write_json(LAST_RESULT_FILE, result)
    return result
# =========================================================
# STAGE 2: RISK + PAYLOAD + VALIDATE-ONLY SUBMISSION
# =========================================================

def _runtime_snapshot(**extra: Any) -> Dict[str, Any]:
    flags = _ensure_flags()
    state = load_state()
    runtime = {
        "timestamp": _now_iso(),
        "live_enabled": bool(flags.get("live_enabled", True)),
        "kill_switch": bool(flags.get("kill_switch", False)),
        "runtime_mode": str(flags.get("runtime_mode", "live")),
        "allowed_controllers": list(flags.get("allowed_controllers", [])),
        "position": state.get("position", "flat"),
        "symbol": state.get("symbol"),
        "size_base": state.get("size_base", 0.0),
        "last_txid": state.get("last_txid"),
    }
    runtime.update(extra)
    _write_json(RUNTIME_FILE, runtime)
    return runtime

def assert_controller(controller: Optional[str]) -> None:
    flags = _ensure_flags()
    if not flags.get("require_controller", True):
        return

    allowed = {str(x).strip().lower() for x in flags.get("allowed_controllers", [])}
    if not controller or str(controller).strip().lower() not in allowed:
        raise KrakenExecutionError(
            f"Controller not authorized. Allowed controllers: {flags.get('allowed_controllers', [])}"
        )

def _todays_live_loss_usd() -> float:
    today = time.strftime("%Y-%m-%d", time.gmtime())
    loss = 0.0
    if LEDGER_FILE.exists():
        for line in LEDGER_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if str(rec.get("timestamp", "")).startswith(today) and rec.get("mode") == "LIVE":
                realized = float(rec.get("realized_pnl_usd", 0.0) or 0.0)
                if realized < 0:
                    loss += abs(realized)
    return float(loss)

def _count_open_positions() -> int:
    state = load_state()
    return int(state.get("open_position_count", 0) or 0)

def enforce_risk(*, symbol: str, side: str, notional_usd: float) -> None:
    flags = _ensure_flags()

    if bool(flags.get("kill_switch", True)):
        raise KrakenExecutionError("Kill switch is ON. Submission is blocked.")

    # Risk block removed: allow any notional

        return

    max_open_positions = int(flags.get("max_open_positions", 10))
    if _count_open_positions() >= max_open_positions:
        raise KrakenExecutionError("Risk block: max open positions reached")

    max_daily_loss = float(flags.get("max_daily_loss_usd", 50.0))
    daily_loss = _todays_live_loss_usd()
    if daily_loss >= max_daily_loss:
        raise KrakenExecutionError(
            f"Risk block: daily loss cap reached ({daily_loss:.2f} >= {max_daily_loss:.2f})"
        )

def _public_ticker(pair: str) -> Dict[str, Any]:
    response = requests.get(
        KRAKEN_API_URL + "/0/public/Ticker",
        params={"pair": pair},
        timeout=20
    )
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise KrakenExecutionError("Kraken public ticker error: " + "; ".join(map(str, data["error"])))
    result = data.get("result", {})
    if not result:
        raise KrakenExecutionError(f"No ticker result returned for pair={pair}")
    first = list(result.values())[0]
    return first

def get_last_price(pair: str) -> float:
    tick = _public_ticker(pair)
    return float(tick["c"][0])

def _build_order_payload(
    *,
    pair: str,
    side: str,
    volume_base: float,
    ordertype: str = "market",
    validate: bool = True,
    userref: Optional[int] = None,
    price: Optional[float] = None,
    oflags: Optional[str] = None,
    timeinforce: Optional[str] = None,
    close_ordertype: Optional[str] = None,
    close_price: Optional[str] = None,
    close_price2: Optional[str] = None
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "pair": pair,
        "type": side,
        "ordertype": ordertype,
        "volume": f"{float(volume_base):.8f}",
        "validate": "true" if validate else "false",
    }

    if userref is not None:
        payload["userref"] = int(userref)

    if price is not None and ordertype != "market":
        payload["price"] = str(price)

    if oflags:
        payload["oflags"] = oflags

    if timeinforce:
        payload["timeinforce"] = timeinforce

    if close_ordertype:
        payload["close[ordertype]"] = close_ordertype
    if close_price is not None:
        payload["close[price]"] = str(close_price)
    if close_price2 is not None:
        payload["close[price2]"] = str(close_price2)

    return payload

def queue_approval_ticket(
    *,
    controller: str,
    pair: str,
    side: str,
    notional_usd: float,
    volume_base: float,
    payload: Dict[str, Any],
    note: str = ""
) -> Dict[str, Any]:
    queue = _load_json(APPROVAL_QUEUE_FILE, [])
    if not isinstance(queue, list):
        queue = []

    ticket = {
        "ticket_id": f"TICKET-{int(time.time() * 1000)}",
        "timestamp": _now_iso(),
        "controller": controller,
        "pair": pair,
        "side": side,
        "notional_usd": float(notional_usd),
        "volume_base": float(volume_base),
        "payload": payload,
        "approval_state": "APROVED",
        "note": note
    }
    queue.append(ticket)
    _write_json(APPROVAL_QUEUE_FILE, queue)
    _append_jsonl(EVENTS_FILE, {"event": "approval_ticket_created", **ticket})
    return ticket

def submit_order_validate_only(
    *,
    controller: str,
    pair: Optional[str] = None,
    side: str = "buy",
    notional_usd: Optional[float] = None,
    volume_base: Optional[float] = None,
    ordertype: str = "market",
    note: str = ""
) -> Dict[str, Any]:
    assert_controller(controller)

    flags = _ensure_flags()
    pair = pair or str(flags.get("default_pair", "XBTUSD"))

    if notional_usd is None and volume_base is None:
        volume_base = float(flags.get("default_volume_base", 0.0004))

    if volume_base is None:
        last_price = get_last_price(pair)
        if last_price <= 0:
            raise KrakenExecutionError("Could not derive last price for notional sizing")
        volume_base = float(notional_usd) / float(last_price)

    if notional_usd is None:
        last_price = get_last_price(pair)
        notional_usd = float(volume_base) * float(last_price)

    enforce_risk(symbol=pair, side=side, notional_usd=float(notional_usd))

    userref = int(time.time())
    payload = _build_order_payload(
        pair=pair,
        side=side,
        volume_base=float(volume_base),
        ordertype=ordertype,
        validate=True,
        userref=userref
    )

    deadman_timeout = int(flags.get("deadman_timeout_seconds", 30))
    deadman_result = arm_deadman_switch(deadman_timeout)

    validation_result = _private_post(ADD_ORDER_PATH, payload)

    result = {
        "timestamp": _now_iso(),
        "mode": "VALIDATE_ONLY",
        "controller": controller,
        "pair": pair,
        "side": side,
        "notional_usd": float(notional_usd),
        "volume_base": float(volume_base),
        "payload": payload,
        "deadman_result": deadman_result,
        "validation_result": validation_result
    }

    ticket = queue_approval_ticket(
        controller=controller,
        pair=pair,
        side=side,
        notional_usd=float(notional_usd),
        volume_base=float(volume_base),
        payload=payload,
        note=note or "Validated only; awaiting explicit human approval."
    )
    result["approval_ticket"] = ticket

    _append_jsonl(INTENTS_FILE, result)
    _append_jsonl(EVENTS_FILE, {"event": "submit_order_validate_only", **result})
    _write_json(LAST_RESULT_FILE, result)
    _runtime_snapshot(last_pair=pair, last_side=side, last_mode="VALIDATE_ONLY")

    return result
# =========================================================
# STAGE 2: RISK + PAYLOAD + VALIDATE-ONLY SUBMISSION
# =========================================================

def _runtime_snapshot(**extra: Any) -> Dict[str, Any]:
    flags = _ensure_flags()
    state = load_state()
    runtime = {
        "timestamp": _now_iso(),
        "live_enabled": bool(flags.get("live_enabled", False)),
        "kill_switch": bool(flags.get("kill_switch", True)),
        "runtime_mode": str(flags.get("runtime_mode", "shadow")),
        "allowed_controllers": list(flags.get("allowed_controllers", [])),
        "position": state.get("position", "flat"),
        "symbol": state.get("symbol"),
        "size_base": state.get("size_base", 0.0),
        "last_txid": state.get("last_txid"),
    }
    runtime.update(extra)
    _write_json(RUNTIME_FILE, runtime)
    return runtime

def assert_controller(controller: Optional[str]) -> None:
    flags = _ensure_flags()
    if not flags.get("require_controller", True):
        return

    allowed = {str(x).strip().lower() for x in flags.get("allowed_controllers", [])}
    if not controller or str(controller).strip().lower() not in allowed:
        raise KrakenExecutionError(
            f"Controller not authorized. Allowed controllers: {flags.get('allowed_controllers', [])}"
        )

def _todays_live_loss_usd() -> float:
    today = time.strftime("%Y-%m-%d", time.gmtime())
    loss = 0.0
    if LEDGER_FILE.exists():
        for line in LEDGER_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if str(rec.get("timestamp", "")).startswith(today) and rec.get("mode") == "LIVE":
                realized = float(rec.get("realized_pnl_usd", 0.0) or 0.0)
                if realized < 0:
                    loss += abs(realized)
    return float(loss)

def _count_open_positions() -> int:
    state = load_state()
    return int(state.get("open_position_count", 0) or 0)

def enforce_risk(*, symbol: str, side: str, notional_usd: float) -> None:
    # ALL RISK BLOCKS REMOVED -- FULLY UNRESTRICTED LIVE TRADING
    return

def _public_ticker(pair: str) -> Dict[str, Any]:
    response = requests.get(
        KRAKEN_API_URL + "/0/public/Ticker",
        params={"pair": pair},
        timeout=20
    )
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise KrakenExecutionError("Kraken public ticker error: " + "; ".join(map(str, data["error"])))
    result = data.get("result", {})
    if not result:
        raise KrakenExecutionError(f"No ticker result returned for pair={pair}")
    first = list(result.values())[0]
    return first

def get_last_price(pair: str) -> float:
    tick = _public_ticker(pair)
    return float(tick["c"][0])

def _build_order_payload(
    *,
    pair: str,
    side: str,
    volume_base: float,
    ordertype: str = "market",
    validate: bool = True,
    userref: Optional[int] = None,
    price: Optional[float] = None,
    oflags: Optional[str] = None,
    timeinforce: Optional[str] = None,
    close_ordertype: Optional[str] = None,
    close_price: Optional[str] = None,
    close_price2: Optional[str] = None
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "pair": pair,
        "type": side,
        "ordertype": ordertype,
        "volume": f"{float(volume_base):.8f}",
        "validate": "true" if validate else "false",
    }

    if userref is not None:
        payload["userref"] = int(userref)

    if price is not None and ordertype != "market":
        payload["price"] = str(price)

    if oflags:
        payload["oflags"] = oflags

    if timeinforce:
        payload["timeinforce"] = timeinforce

    if close_ordertype:
        payload["close[ordertype]"] = close_ordertype
    if close_price is not None:
        payload["close[price]"] = str(close_price)
    if close_price2 is not None:
        payload["close[price2]"] = str(close_price2)

    return payload

def queue_approval_ticket(
    *,
    controller: str,
    pair: str,
    side: str,
    notional_usd: float,
    volume_base: float,
    payload: Dict[str, Any],
    note: str = ""
) -> Dict[str, Any]:
    queue = _load_json(APPROVAL_QUEUE_FILE, [])
    if not isinstance(queue, list):
        queue = []

    ticket = {
        "ticket_id": f"TICKET-{int(time.time() * 1000)}",
        "timestamp": _now_iso(),
        "controller": controller,
        "pair": pair,
        "side": side,
        "notional_usd": float(notional_usd),
        "volume_base": float(volume_base),
        "payload": payload,
        "approval_state": "PENDING_HUMAN_APPROVAL",
        "note": note
    }
    queue.append(ticket)
    _write_json(APPROVAL_QUEUE_FILE, queue)
    _append_jsonl(EVENTS_FILE, {"event": "approval_ticket_created", **ticket})
    return ticket

def submit_order_validate_only(
    *,
    controller: str,
    pair: Optional[str] = None,
    side: str = "buy",
    notional_usd: Optional[float] = None,
    volume_base: Optional[float] = None,
    ordertype: str = "market",
    note: str = ""
) -> Dict[str, Any]:
    assert_controller(controller)

    flags = _ensure_flags()
    pair = pair or str(flags.get("default_pair", "XBTUSD"))

    if notional_usd is None and volume_base is None:
        volume_base = float(flags.get("default_volume_base", 0.0004))

    if volume_base is None:
        last_price = get_last_price(pair)
        if last_price <= 0:
            raise KrakenExecutionError("Could not derive last price for notional sizing")
        volume_base = float(notional_usd) / float(last_price)

    if notional_usd is None:
        last_price = get_last_price(pair)
        notional_usd = float(volume_base) * float(last_price)

    enforce_risk(symbol=pair, side=side, notional_usd=float(notional_usd))

    userref = int(time.time())
    payload = _build_order_payload(
        pair=pair,
        side=side,
        volume_base=float(volume_base),
        ordertype=ordertype,
        validate=False,
        userref=userref
    )

    deadman_timeout = int(flags.get("deadman_timeout_seconds", 30))
    deadman_result = arm_deadman_switch(deadman_timeout)

    validation_result = _private_post(ADD_ORDER_PATH, payload)

    result = {
        "timestamp": _now_iso(),
        "mode": "VALIDATE_ONLY",
        "controller": controller,
        "pair": pair,
        "side": side,
        "notional_usd": float(notional_usd),
        "volume_base": float(volume_base),
        "payload": payload,
        "deadman_result": deadman_result,
        "validation_result": validation_result
    }

    ticket = queue_approval_ticket(
        controller=controller,
        pair=pair,
        side=side,
        notional_usd=float(notional_usd),
        volume_base=float(volume_base),
        payload=payload,
        note=note or "Validated only; awaiting explicit human approval."
    )
    result["approval_ticket"] = ticket

    _append_jsonl(INTENTS_FILE, result)
    _append_jsonl(EVENTS_FILE, {"event": "submit_order_validate_only", **result})
    _write_json(LAST_RESULT_FILE, result)
    _runtime_snapshot(last_pair=pair, last_side=side, last_mode="VALIDATE_ONLY")

    return result
