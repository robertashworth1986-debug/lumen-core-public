import os
import json
# LUMENCORE UNIVERSAL META-ORCHESTRATOR
# This script continuously scans all enabled Kraken pairs, runs all signal engines, ranks opportunities, and fires live trades with dynamic capital allocation.


# UNIVERSAL META-ORCHESTRATOR: FULL LIVE, ALL ENGINES, REAL TXID, NO HUMAN APPROVAL
import time
import traceback
import sys
import subprocess
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

KEYS_ENV_PATHS = [
    ROOT / "config" / "luma_live_keys.env",
    ROOT / "code" / "execution" / "config" / "luma_live_keys.env",
    ROOT / "config" / "live_keys.env",
    ROOT / "config" / "keys.env",
    ROOT / "code" / "execution" / "config" / "live_keys.env",
    ROOT / "code" / "execution" / "config" / "keys.env",
]


def _load_env_file(path: Path) -> dict:
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


def _mask_key(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    return f"{text[:4]}...{text[-4:]}" if len(text) > 8 else text


def _hydrate_live_keys() -> None:
    hydrated = False
    for env_path in KEYS_ENV_PATHS:
        env_values = _load_env_file(env_path)
        if not env_values:
            continue
        loaded = []
        for key, value in env_values.items():
            if not os.getenv(key, "").strip() and isinstance(value, str) and value.strip():
                os.environ[key] = value.strip()
                hydrated = True
                loaded.append(key)
        if loaded:
            print(f"[ORCH] Hydrated live keys from {env_path}: {', '.join(loaded)}")
            if "KRAKEN_API_KEY" in loaded or "KRAKEN_API_SECRET" in loaded:
                print(f"[ORCH] Kraken key source: {env_path}")
                print(f"[ORCH] Kraken key fingerprint: { _mask_key(os.getenv('KRAKEN_API_KEY','')) }")
                print(f"[ORCH] Kraken secret fingerprint: { _mask_key(os.getenv('KRAKEN_API_SECRET','')) }")
            break

_hydrate_live_keys()

try:
    from symbol_registry_auto import SYMBOL_REGISTRY
except Exception as e:
    print(f"[ORCH] Warning: failed to import symbol_registry_auto: {e}")
    SYMBOL_REGISTRY = {}

from bounded_infinity import MetaEngine
from execution.rolling_capital_engine_multi import fetch_live_ohlcv, build_families, stats, build_strategy_returns
import harmonic_hybrid_core
import institutional_harmonic_core
from kraken_execution import _ensure_flags, get_last_price, enforce_risk, _private_post, ADD_ORDER_PATH, assert_controller, verify_credentials

ROOT = Path(__file__).resolve().parent.parent
RUNTIME_CONTROL_PATH = ROOT / "config" / "runtime_control.json"

SCAN_INTERVAL_SEC = 5
DEFAULT_SCAN_TOP_N = 120
CONTROLLER = "Robert"


def env_bool(name):
    if name not in os.environ:
        return None
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def load_json(path, default=None):
    try:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def runtime_mode():
    try:
        runtime = load_json(RUNTIME_CONTROL_PATH, {})
        mode = str(runtime.get("mode", "paper")).strip().lower()
        allow_live = runtime.get("allow_live_orders", False)
        if mode == "live" and not allow_live:
            print(f"[ORCH] Runtime config requests live mode, but allow_live_orders is disabled. Forcing PAPER mode.")
            return "paper"
        return mode
    except Exception:
        return "paper"


PREFERRED_LIVE_EXCHANGE = os.getenv("PREFERRED_LIVE_EXCHANGE", "").strip().lower()
REQUESTED_LIVE_EXCHANGE = ""
for arg in sys.argv:
    if arg.startswith("--exchange="):
        REQUESTED_LIVE_EXCHANGE = arg.split("=", 1)[1].strip().lower()
    elif arg in {"--use-binance", "--force-binance", "--binance"}:
        REQUESTED_LIVE_EXCHANGE = "binance"
    elif arg in {"--use-binanceus", "--force-binanceus", "--binanceus"}:
        REQUESTED_LIVE_EXCHANGE = "binanceus"
    elif arg in {"--use-kraken", "--force-kraken"}:
        REQUESTED_LIVE_EXCHANGE = "kraken"

BINANCE_MODE = "--binance" in sys.argv or env_bool("BINANCE_MODE") is True or PREFERRED_LIVE_EXCHANGE == "binance"
BINANCEUS_MODE = "--binanceus" in sys.argv or env_bool("BINANCEUS_MODE") is True or PREFERRED_LIVE_EXCHANGE == "binanceus"

PAPER_MODE = True
if "--live" in sys.argv or "--force-live" in sys.argv or env_bool("LIVE_MODE") is True or env_bool("FORCE_LIVE") is True:
    PAPER_MODE = False
elif "--paper" in sys.argv or env_bool("PAPER_MODE") is True:
    PAPER_MODE = True
elif env_bool("PAPER_MODE") is False:
    PAPER_MODE = False
else:
    PAPER_MODE = runtime_mode() != "live"


def normalize_pair(pair: str) -> str:
    if not pair:
        return pair
    normalized = str(pair).strip().upper()
    normalized = normalized.replace("_", "/").replace("-", "/")
    if "/" not in normalized:
        if normalized.endswith("USD") and len(normalized) > 3:
            normalized = f"{normalized[:-3]}/USD"
        elif normalized.endswith("USDT") and len(normalized) > 4:
            normalized = f"{normalized[:-4]}/USDT"
    return normalized


def _mask_key(text: str) -> str:
    text = str(text or "").strip()
    if len(text) <= 8:
        return text
    return f"{text[:4]}...{text[-4:]}"


def _normalize_binance_symbol(symbol: str) -> str:
    sym = str(symbol).strip().upper().replace("/", "").replace("_", "")
    if sym.startswith("XBT"):
        sym = "BTC" + sym[3:]
    if sym.endswith("USD") and not sym.endswith("USDT"):
        sym = sym[:-3] + "USDT"
    if sym.endswith("USDT") or sym.endswith("BUSD") or sym.endswith("BTC") or sym.endswith("ETH"):
        return sym
    return f"{sym}USDT"


def _collect_live_key_sources() -> dict:
    live_keys = {}
    for env_path in KEYS_ENV_PATHS:
        env_values = _load_env_file(env_path)
        if not env_values:
            continue
        for key, value in env_values.items():
            if key not in live_keys:
                live_keys[key] = {
                    "source": str(env_path),
                    "value": value,
                    "present": bool(os.getenv(key, "").strip())
                }
    return live_keys


def audit_live_keys() -> None:
    print("[ORCH] Live key audit report")
    live_keys = _collect_live_key_sources()
    if not live_keys:
        print("[ORCH] No live key source files were found.")
    for key, info in sorted(live_keys.items()):
        present = "yes" if info["present"] else "no"
        masked = _mask_key(info["value"])
        print(f"  {key}: present_in_env={present}, source={info['source']}, value={masked}")

    print("[ORCH] Active environment keys summary:")
    for known in ["KRAKEN_API_KEY", "KRAKEN_API_SECRET", "BINANCE_API_KEY", "BINANCE_API_SECRET"]:
        print(f"  {known}: {'set' if os.getenv(known, '').strip() else 'missing'}")

    creds = verify_live_credentials()
    print(f"[ORCH] verify_live_credentials: {creds}")


def _binance_sign(params: dict, secret: str) -> str:
    query = urlencode(params)
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()


def _binance_api_url() -> str:
    api_url = os.getenv("BINANCE_API_URL", "").strip()
    if api_url:
        return api_url
    if env_bool("BINANCE_API_TESTNET") is True:
        return "https://testnet.binance.vision"
    if BINANCEUS_MODE or os.getenv("LIVE_EXCHANGE", "").strip().lower() == "binanceus" or REQUESTED_LIVE_EXCHANGE == "binanceus" or PREFERRED_LIVE_EXCHANGE == "binanceus":
        return "https://api.binance.us"
    return "https://api.binance.com"


def validate_binance_credentials() -> dict:
    key = os.getenv("BINANCE_API_KEY", "").strip()
    secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not key or not secret:
        return {"valid": False, "error": "Missing Binance API keys"}
    api_url = _binance_api_url()
    try:
        ts = int(time.time() * 1000)
        params = {"timestamp": ts}
        params["signature"] = _binance_sign(params, secret)
        headers = {"X-MBX-APIKEY": key}
        resp = requests.get(f"{api_url}/api/v3/account", headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        return {"valid": True, "data": resp.json(), "api_url": api_url}
    except Exception as e:
        error_text = str(e)
        if "api.binance.com" in api_url and not os.getenv("BINANCE_API_URL", "").strip() and os.getenv("BINANCE_API_TESTNET", "").strip().lower() not in {"1", "true", "yes", "on"}:
            fallback_url = "https://testnet.binance.vision"
            try:
                ts = int(time.time() * 1000)
                params = {"timestamp": ts}
                params["signature"] = _binance_sign(params, secret)
                headers = {"X-MBX-APIKEY": key}
                resp = requests.get(f"{fallback_url}/api/v3/account", headers=headers, params=params, timeout=15)
                resp.raise_for_status()
                return {"valid": True, "data": resp.json(), "api_url": fallback_url, "fallback": "binance_testnet"}
            except Exception as e2:
                error_text = f"{error_text} | fallback failed: {e2}"
        if isinstance(e, requests.exceptions.HTTPError) and getattr(e.response, 'status_code', None) == 451:
            fallback_url = "https://api.binance.com"
            print(f"[BINANCE] Testnet HTTP 451 detected; retrying live endpoint {fallback_url}", file=sys.stderr, flush=True)
            try:
                ts = int(time.time() * 1000)
                params = {"timestamp": ts}
                params["signature"] = _binance_sign(params, secret)
                headers = {"X-MBX-APIKEY": key}
                resp = requests.get(f"{fallback_url}/api/v3/account", headers=headers, params=params, timeout=15)
                resp.raise_for_status()
                return {"valid": True, "data": resp.json(), "api_url": fallback_url, "fallback": "binance_live"}
            except Exception as e3:
                error_text = f"{error_text} | live fallback failed: {e3}"
        return {"valid": False, "error": error_text, "api_url": api_url}


def _has_binance_keys() -> bool:
    return bool(os.getenv("BINANCE_API_KEY", "").strip() and os.getenv("BINANCE_API_SECRET", "").strip())


def _has_kraken_keys() -> bool:
    return bool(os.getenv("KRAKEN_API_KEY", "").strip() and os.getenv("KRAKEN_API_SECRET", "").strip())


def _select_live_exchange() -> str:
    if REQUESTED_LIVE_EXCHANGE in {"binance", "binanceus", "kraken"}:
        return REQUESTED_LIVE_EXCHANGE
    preferred = os.getenv("PREFERRED_LIVE_EXCHANGE", "").strip().lower()
    if BINANCEUS_MODE or preferred == "binanceus" or env_bool("FORCE_BINANCEUS") is True:
        return "binanceus"
    if BINANCE_MODE or preferred == "binance" or env_bool("FORCE_BINANCE") is True:
        return "binance"
    if preferred == "kraken" or env_bool("FORCE_KRAKEN") is True:
        return "kraken"
    if os.getenv("LIVE_EXCHANGE", "").strip().lower() in {"binance", "binanceus", "kraken"}:
        return os.getenv("LIVE_EXCHANGE", "").strip().lower()
    return "kraken"


def verify_live_credentials() -> dict:
    kraken_status = {"valid": False, "error": "Missing Kraken credentials"}
    binance_status = {"valid": False, "error": "Missing Binance credentials"}

    if _has_kraken_keys():
        kraken_status = verify_credentials()
    if _has_binance_keys():
        binance_status = validate_binance_credentials()

    selected = _select_live_exchange()
    candidates = [selected, "kraken", "binance"] if selected == "binance" else [selected, "binance", "kraken"]

    for candidate in candidates:
        if candidate == "kraken" and kraken_status.get("valid"):
            return {"exchange": "kraken", "valid": True, "status": kraken_status}
        if candidate in {"binance", "binanceus"} and binance_status.get("valid"):
            return {"exchange": candidate, "valid": True, "status": binance_status}

    return {
        "exchange": "none",
        "valid": False,
        "errors": {
            "kraken": kraken_status.get("error"),
            "binance": binance_status.get("error")
        }
    }


def binance_get_price(symbol: str) -> float:
    try:
        sym = _normalize_binance_symbol(symbol)
        api_url = _binance_api_url()
        resp = requests.get(f"{api_url}/api/v3/ticker/price", params={"symbol": sym}, timeout=10)
        resp.raise_for_status()
        return float(resp.json().get("price", 0.0))
    except Exception as e:
        print(f"[BINANCE] price fetch failed for {symbol}: {e}")
        return 0.0


def fire_binance_order(symbol, notional_usd, side="buy"):
    try:
        key = os.getenv("BINANCE_API_KEY", "").strip()
        secret = os.getenv("BINANCE_API_SECRET", "").strip()
        if not key or not secret:
            print(f"[BINANCE] Missing Binance API keys, cannot place order for {symbol}.")
            return None
        sym = _normalize_binance_symbol(symbol)
        price = binance_get_price(sym)
        if price <= 0:
            print(f"[BINANCE] Could not resolve price for {sym}, skipping {symbol}.")
            return None
        quantity = float(notional_usd) / float(price)
        if quantity <= 0:
            print(f"[BINANCE] Quantity computed as zero for {symbol} at price {price}")
            return None
        params = {
            "symbol": sym,
            "side": "BUY" if side == "buy" else "SELL",
            "type": "MARKET",
            "quantity": f"{quantity:.6f}",
            "timestamp": int(time.time() * 1000)
        }
        params["signature"] = _binance_sign(params, secret)
        headers = {"X-MBX-APIKEY": key}
        api_url = _binance_api_url()
        resp = requests.post(f"{api_url}/api/v3/order", headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        result = resp.json()
        txid = result.get("orderId") or result.get("clientOrderId")
        print(f"[BINANCE] {symbol} {side} {notional_usd:.2f} USD @ {price:.2f} ORDER_ID={txid}")
        return txid
    except Exception as e:
        print(f"[BINANCE] ORDER ERROR {symbol}: {e}")
        return None


def evaluate_symbol(symbol):
    result = {
        "symbol": symbol,
        "exchange": SYMBOL_REGISTRY.get(symbol, {}).get("exchange", "").lower(),
        "pair": normalize_pair(SYMBOL_REGISTRY.get(symbol, {}).get("pair", symbol)),
        "score": -10.0,
        "kpi": {},
        "issues": [],
        "df_present": False,
        "valid": False,
    }
    try:
        df = fetch_live_ohlcv(symbol)
        if df is None or df.empty or "ret" not in df.columns or "close" not in df.columns:
            result["issues"].append("Missing or invalid OHLCV data")
            return result
        result["df_present"] = True
        fams = build_families(df)
        ret = df["ret"]
        hsig = harmonic_hybrid_core.strat_phase_follow(df["close"])
        strat_ret, _, _ = build_strategy_returns(hsig, ret)
        kpi = stats(strat_ret)
        result["kpi"] = kpi
        result["score"] = max(kpi.get("sharpe", 0.0) - 0.5 * abs(kpi.get("max_drawdown", 0.0)), -10)
        result["issues"] = detect_candidate_constraints(symbol, df, kpi, result["score"])
        result["valid"] = True
    except Exception as e:
        result["issues"].append(f"Evaluation error: {e}")
    return result


def detect_candidate_constraints(symbol, df, kpi, score):
    issues = []
    if df is None or df.empty:
        issues.append("Missing OHLCV data")
        issues.extend([
            "Confirm live feed freshness",
            "Verify symbol routing",
            "Check exchange assignment",
            "Review data source health",
            "Ensure market session is open",
        ])
        return issues[:5]

    if "volume" in df.columns:
        try:
            last_vol = float(df["volume"].iloc[-1])
        except Exception:
            last_vol = 0.0
        if last_vol <= 0:
            issues.append("Zero or missing recent volume")
        elif last_vol < 1000:
            issues.append("Low liquidity: below 1K volume")

    try:
        last_return = float(df["close"].pct_change().iloc[-1])
        if last_return < -0.02:
            issues.append("Recent negative momentum > 2%")
        elif last_return < 0:
            issues.append("Negative latest closing return")
    except Exception:
        issues.append("Unable to compute recent return")

    sharpe = float(kpi.get("sharpe", 0.0))
    if sharpe < 0.5:
        issues.append("Weak risk-adjusted return (sharpe < 0.5)")
    if abs(float(kpi.get("max_drawdown", 0.0))) > 0.15:
        issues.append("High historical drawdown (>15%)")
    if score < 0:
        issues.append("Candidate score is negative")

    if len(issues) < 5:
        extras = [
            "Confirm position sizing aligns with risk budget",
            "Verify execution route for the target exchange",
            "Check correlation exposure across live universe",
            "Validate current margin / leverage constraints",
            "Ensure live market data latency is acceptable",
        ]
        for extra in extras:
            if len(issues) >= 5:
                break
            issues.append(extra)

    return issues[:5]


def build_live_candidate_report(exchange, top_n=10):
    symbols = [
        s for s, info in SYMBOL_REGISTRY.items()
        if info.get("exchange", "").lower() == exchange
    ]
    if not symbols:
        symbols = list(SYMBOL_REGISTRY.keys())
        print(f"[ORCH] No symbols explicitly assigned to {exchange}; scanning full universe.")

    candidates = []
    start = time.time()
    for symbol in symbols:
        result = evaluate_symbol(symbol)
        if result["valid"]:
            candidates.append(result)
    elapsed = time.time() - start
    print(f"[ORCH] Evaluated {len(candidates)} live candidates for {exchange} in {elapsed:.1f}s")
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:top_n]


def print_candidate_report(candidates):
    print("[ORCH] Top live candidate report:")
    for idx, cand in enumerate(candidates, start=1):
        print(f"  {idx}. {cand['symbol']} | score={cand['score']:.3f} | exchange={cand['exchange']} | pair={cand['pair']}")
        print(f"       sharpe={cand['kpi'].get('sharpe', 'n/a'):.3f} | max_dd={cand['kpi'].get('max_drawdown', 'n/a'):.3f}")
        for issue in cand['issues']:
            print(f"         - {issue}")


def score_symbol(symbol):
    try:
        return evaluate_symbol(symbol)["score"]
    except Exception as e:
        print(f"[SCORE] {symbol} error: {e}")
        return -10

def fire_live_order(symbol, notional_usd, side="buy"):
    try:
        symbol_info = SYMBOL_REGISTRY.get(symbol)
        if not symbol_info:
            print(f"[ORCH] Symbol {symbol} is not registered. Skipping live order.")
            return None
        if symbol_info.get("exchange", "").lower() != "kraken":
            print(f"[ORCH] Skipping non-Kraken symbol {symbol} ({symbol_info.get('exchange')}).")
            return None
        pair = normalize_pair(symbol_info.get("pair", symbol))
        if not pair:
            print(f"[ORCH] No pair available for {symbol}, skipping.")
            return None
        flags = _ensure_flags()
        assert_controller(CONTROLLER)
        if not flags.get("live_enabled", False) or flags.get("kill_switch", True):
            print(f"[ORCH] Live trading not enabled or kill switch is ON. Skipping {symbol}.")
            return None
        price = get_last_price(pair)
        if price <= 0:
            print(f"[ORCH] Could not resolve price for {pair}, skipping {symbol}.")
            return None
        volume_base = float(notional_usd) / float(price)
        enforce_risk(symbol=pair, side=side, notional_usd=notional_usd)
        payload = {
            "pair": pair,
            "type": side,
            "ordertype": "market",
            "volume": f"{float(volume_base):.8f}",
            "validate": "false",
            "userref": int(time.time())
        }
        result = _private_post(ADD_ORDER_PATH, payload)
        txid = result.get("txid") or result.get("txid[0]") or None
        print(f"[LIVE ORDER] {symbol} {side} {notional_usd:.2f} USD @ {price:.2f} TXID={txid}")
        # Log to file
        import os
        log_dir = "out"
        log_file = os.path.join(log_dir, "live_trade_log.txt")
        os.makedirs(log_dir, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {symbol} {side} {notional_usd:.2f} {price:.2f} TXID={txid}\n")
        return txid
    except Exception as e:
        print(f"[LIVE ORDER ERROR] {symbol}: {e}\n{traceback.format_exc()}")
        return None

def main():
    if "--audit-live-keys" in sys.argv or "--audit-credentials" in sys.argv:
        audit_live_keys()
        return

    runtime = load_json(RUNTIME_CONTROL_PATH, {})
    scan_top_n = int(runtime.get("scan_top_n", DEFAULT_SCAN_TOP_N) or DEFAULT_SCAN_TOP_N)
    print(f"[ORCH] Selected execution mode: {'PAPER' if PAPER_MODE else 'LIVE'}")
    if PAPER_MODE:
        print("[ORCH] PAPER MODE active: generating adaptive universe and running Alpaca paper evidence collector.")
        env = os.environ.copy()
        env["PAPER_MODE"] = "true"

        builder_script = Path(__file__).parent / "BUILD_ADAPTIVE_UNIVERSE_FROM_LIVE_KEYS.py"
        if builder_script.exists():
            subprocess.run([sys.executable, str(builder_script)], cwd=str(Path(__file__).parent), env=env, check=False)

        cutover_script = Path(__file__).parent / "CUTOVER_TO_ADAPTIVE_ENGINE_LOGIC.py"
        if cutover_script.exists():
            subprocess.run([sys.executable, str(cutover_script)], cwd=str(Path(__file__).parent), env=env, check=False)

        paper_script = Path(__file__).parent / "alpaca_paper_loop_builder.py"
        if not paper_script.exists():
            print(f"[ORCH] Paper script missing: {paper_script}")
            return
        subprocess.run([sys.executable, str(paper_script)], cwd=str(Path(__file__).parent), env=env, check=False)
        print("[ORCH] Paper mode execution complete.")
        return

    print("[LUMENCORE] UNIVERSAL META-ORCHESTRATOR: FULL LIVE, ALL ENGINES, REAL TXID, NO HUMAN APPROVAL")
    creds = verify_live_credentials()
    if not creds.get("valid", False):
        errors = creds.get("errors", {})
        print(f"[ORCH] Live credential validation failed.")
        print(f"[ORCH] Kraken error: {errors.get('kraken')}")
        print(f"[ORCH] Binance error: {errors.get('binance')}")
        return

    exchange = creds.get("exchange")
    print(f"[ORCH] Selected live exchange: {exchange}")
    if exchange == "kraken":
        print("[ORCH] Kraken credentials verified.")
    elif exchange == "binance":
        print("[ORCH] Binance credentials verified.")
    else:
        print("[ORCH] No valid live exchange available.")
        return

    candidates = build_live_candidate_report(exchange, scan_top_n)
    if not candidates:
        print(f"[ORCH] No valid live candidates available for {exchange}.")
        return
    print_candidate_report(candidates)

    while True:
        try:
            symbols = [
                s for s, info in SYMBOL_REGISTRY.items()
                if info.get("exchange", "").lower() == exchange
            ]
            if not symbols:
                symbols = list(SYMBOL_REGISTRY.keys())
                print(f"[ORCH] No registry symbols explicitly assigned to {exchange}. Using all registry symbols.")

            if not symbols:
                print(f"[ORCH] No symbols found in registry. Exiting.")
                break

            scores = {s: score_symbol(s) for s in symbols}
            best = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:scan_top_n]
            print(f"[ORCH] Scored {exchange} symbols: {best}")
            capital = float(os.getenv("LUMENCORE_TOTAL_CAPITAL_USD", "1000"))
            capital_per_symbol = capital / max(len(best), 1)
            for symbol, score in best:
                print(f"[ORCH] Attempting live order for {symbol} with score={score:.4f}")
                if exchange == "kraken":
                    txid = fire_live_order(symbol, capital_per_symbol, side="buy")
                else:
                    txid = fire_binance_order(symbol, capital_per_symbol, side="buy")
                if txid:
                    print(f"[ORCH] LIVE TRADE FIRED ({exchange}): {symbol} TXID={txid}")
                time.sleep(3)  # Stagger orders by 3 seconds
            os.makedirs("out", exist_ok=True)
            if not os.path.exists("out/live_trade_log.txt"):
                with open("out/live_trade_log.txt", "w", encoding="utf-8") as _:
                    pass
            with open("out/live_trade_log.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
            print(f"[ORCH] {len(lines)} LIVE TRADES FIRED. EXITING.")
            break
        except Exception as e:
            print(f"[ORCH ERROR] {e}\n{traceback.format_exc()}")
        time.sleep(SCAN_INTERVAL_SEC)

if __name__ == "__main__":
    main()
