#!/usr/bin/env python3
"""
KRAKEN SWING HUNTER - CATCH THE BIGGEST MOVER EVERY CYCLE
Scans ALL Kraken USD pairs, ranks by momentum, rides the top swing.
Converts BTC/crypto dust -> USD, then deploys capital on best opportunity.
"""

import os, sys, json, time, hmac, hashlib, base64, urllib.parse
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import requests

ROOT    = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT_DIR = ROOT / "out" / "execution"
OUT_DIR.mkdir(parents=True, exist_ok=True)
LEDGER  = OUT_DIR / "swing_hunter_ledger.jsonl"
LOCK_FILE = OUT_DIR / ".kraken_swing_hunter.lock"

# ── Keys ────────────────────────────────────────────────────────
def _load_keys():
    p = ROOT / "code" / "execution" / "config" / "luma_live_keys.env"
    k, s = "", ""
    if p.exists():
        for line in p.read_text().splitlines():
            if line.startswith("KRAKEN_API_KEY="):    k = line.split("=",1)[1].strip()
            elif line.startswith("KRAKEN_API_SECRET="): s = line.split("=",1)[1].strip()
    return k, s

KEY, SECRET = _load_keys()
if not KEY or not SECRET:
    print("[ERROR] No Kraken keys found."); sys.exit(1)
print(f"[SWING-HUNTER] Key: {KEY[:8]}... LIVE KRAKEN")

# ── Signing ─────────────────────────────────────────────────────
def _sign(path: str, data: dict) -> str:
    post    = urllib.parse.urlencode(data)
    encoded = (str(data["nonce"]) + post).encode()
    msg     = path.encode() + hashlib.sha256(encoded).digest()
    sig     = hmac.new(base64.b64decode(SECRET), msg, hashlib.sha512).digest()
    return base64.b64encode(sig).decode()

_nonce_counter = int(time.time() * 1000)
def _next_nonce() -> str:
    global _nonce_counter
    _nonce_counter += 1
    return str(_nonce_counter)

def _post(endpoint: str, data: dict = None) -> dict:
    data = dict(data or {})
    data["nonce"] = _next_nonce()
    headers = {"API-Key": KEY, "API-Sign": _sign(endpoint, data)}
    try:
        r = requests.post("https://api.kraken.com" + endpoint,
                          headers=headers, data=data, timeout=12)
        j = r.json()
        if j.get("error"):
            print(f"[ERR] {endpoint}: {j['error']}")
            return {"_error": j["error"]}
        return j.get("result", {})
    except Exception as e:
        print(f"[HTTP-ERR] {e}"); return {}

def _get(endpoint: str, params: dict = None) -> dict:
    try:
        r = requests.get("https://api.kraken.com" + endpoint,
                         params=params or {}, timeout=10)
        j = r.json()
        return j.get("result", {}) if not j.get("error") else {}
    except Exception as e:
        print(f"[GET-ERR] {e}"); return {}

# ── Portfolio ────────────────────────────────────────────────────
ASSET_TO_TICKER = {
    "XXBT": "XBTUSDT", "XETH": "ETHUSDT", "SOL": "SOLUSDT",
    "ADA":  "ADAUSDT", "PEPE": "PEPEUSDT","BABY": "BABYUSDT",
    "BONK": "BONKUSDT","XXDG": "DOGEUSDT","XXRP": "XRPUSDT",
}

def get_price(pair: str) -> Optional[float]:
    r = _get("/0/public/Ticker", {"pair": pair})
    if not r: return None
    data = next(iter(r.values()), {})
    try: return float(data["c"][0])
    except: return None

def get_balances() -> dict:
    """Returns {asset: qty_float} for non-zero balances."""
    raw = _post("/0/private/Balance")
    return {k: float(v) for k, v in raw.items() if float(v) > 0}

def portfolio_usd(balances: dict) -> float:
    total = float(balances.get("ZUSD", 0)) + float(balances.get("USDT", 0))
    for asset, qty in balances.items():
        if asset == "ZUSD": continue
        pair = ASSET_TO_TICKER.get(asset)
        if not pair: continue
        p = get_price(pair)
        if p: total += qty * p
    return total

# ── Convert BTC dust to USD ──────────────────────────────────────
def convert_btc_to_usd(balances: dict) -> bool:
    btc = balances.get("XXBT", 0)
    if btc < 0.0001: return False
    p = get_price("XBTUSDT")
    if not p: return False
    val = btc * p
    if val < 1.0: return False
    print(f"[CONVERT] Selling {btc:.6f} BTC (≈${val:.2f}) -> USD")
    r = _post("/0/private/AddOrder", {
        "pair": "XBTUSDT", "type": "sell",
        "ordertype": "market", "volume": f"{btc:.8f}"
    })
    txid = (r.get("txid") or [""])[0]
    if txid:
        _log({"event": "btc_to_usd", "btc": btc, "est_usd": val, "txid": txid})
        print(f"[CONVERT] Done txid={txid}")
        time.sleep(3)
        return True
    return False

# ── Scan ALL pairs for biggest swing ────────────────────────────
def scan_top_movers(min_vol_usd: float = 100_000) -> list:
    """
    Pulls all Kraken USD tickers in one call.
    Scores by RECENT activity: coins where high/low spread is wide AND
    last price is near the high (active upward movement right now).
    Returns list of (pair, score, last_price, volume_usd) sorted best first.
    """
    r = _get("/0/public/Ticker")
    if not r:
        return []

    movers = []
    for pair_name, data in r.items():
        if not (pair_name.endswith("USD") or pair_name.endswith("USDT")):
            continue
        try:
            last     = float(data["c"][0])
            high24   = float(data["h"][1])   # 24h high
            low24    = float(data["l"][1])    # 24h low
            open_    = float(data["o"])
            vol      = float(data["v"][1])
            vol_usd  = vol * last
            num_trades = int(data["t"][1])   # 24h trade count (activity proxy)

            if last <= 0 or high24 <= low24 or vol_usd < min_vol_usd:
                continue

            # Range score: how wide is the 24h range (volatility)
            range_pct = (high24 - low24) / low24 * 100

            # Position in range: 1.0 = at 24h high, 0.0 = at 24h low
            pos_in_range = (last - low24) / (high24 - low24)

            # Recent momentum: last vs open
            mom_pct = (last - open_) / open_ * 100

            # Combined score: favor wide range + currently near high + active
            score = range_pct * pos_in_range * (1 + num_trades / 50000)

            movers.append((pair_name, score, last, vol_usd, range_pct, mom_pct))
        except:
            continue

    # Sort by score descending
    movers.sort(key=lambda x: x[1], reverse=True)
    return movers

# ── Logging ──────────────────────────────────────────────────────
def _log(event: dict):
    event["ts"] = datetime.now(timezone.utc).isoformat()
    with LEDGER.open("a") as f:
        f.write(json.dumps(event) + "\n")
    print(f"[LOG] {event}")


def _acquire_lock() -> None:
    # Prevent multiple bot instances from competing for the same wallet.
    # Use atomic create to avoid races when two processes start simultaneously.
    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        return
    except FileExistsError:
        pass

    try:
        pid = int(LOCK_FILE.read_text().strip() or "0")
    except Exception:
        pid = 0

    if pid > 0:
        try:
            os.kill(pid, 0)
            print(f"[LOCK] swing hunter already running with pid={pid}; exiting")
            sys.exit(1)
        except OSError:
            pass

    # Stale lock fallback.
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass

    fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))


def _release_lock() -> None:
    try:
        if LOCK_FILE.exists() and LOCK_FILE.read_text().strip() == str(os.getpid()):
            LOCK_FILE.unlink()
    except Exception:
        pass

# ── Main scalper loop ────────────────────────────────────────────
def run():
    TP_PCT      =  0.015    # +1.5% take profit
    SL_PCT      = -0.005    # -0.5% stop loss
    MAX_HOLD_S  =  300      # 5 min max hold
    RISK_SHARE  =  0.80     # use 80% of USD per trade
    SCAN_SEC    =  6        # price check interval
    RESCAN_SEC  =  60       # how often to re-rank top movers

    position    = None      # active trade
    last_scan   = 0
    top_pair    = None
    prices      = []

    print(f"\n{'='*65}")
    print(f"  SWING HUNTER | TP={TP_PCT*100:.1f}% | SL={SL_PCT*100:.1f}% | 24/7 LIVE")
    print(f"{'='*65}\n")

    while True:
        try:
            now = time.time()

            # ── Re-rank movers periodically ──
            if now - last_scan > RESCAN_SEC and not position:
                print(f"\n[SCAN] Ranking all Kraken pairs by swing size...")
                movers = scan_top_movers()
                if movers:
                    print(f"  TOP 5 ACTIVE MOVERS (range × position × activity):")
                    for pair, score, price, vol, rng, mom in movers[:5]:
                        print(f"    {pair:20s} score={score:7.1f}  range={rng:+6.1f}%  mom={mom:+6.1f}%  ${price:.6f}")
                    top_pair = movers[0][0]
                    prices   = []
                    print(f"\n  >> Targeting: {top_pair} (score={movers[0][1]:.1f}  mom={movers[0][5]:+.1f}%)\n")
                last_scan = now

            if not top_pair:
                time.sleep(SCAN_SEC); continue

            # ── Price tick ──
            price = get_price(top_pair)
            if not price:
                time.sleep(SCAN_SEC); continue

            prices.append(price)
            if len(prices) > 20: prices.pop(0)

            # ── Manage open position ──
            if position:
                pct = (price - position["entry"]) / position["entry"]
                age = now  - position["opened"]
                print(f"[HOLD] {top_pair} @ ${price:.6f}  {pct*100:+.2f}%  {age:.0f}s")

                exit_reason = None
                if   pct >= TP_PCT:      exit_reason = "take_profit"
                elif pct <= SL_PCT:      exit_reason = "stop_loss"
                elif age > MAX_HOLD_S:   exit_reason = "timeout"

                if exit_reason:
                    print(f"[EXIT] {exit_reason}  pct={pct*100:+.2f}%")
                    r = _post("/0/private/AddOrder", {
                        "pair": top_pair, "type": "sell",
                        "ordertype": "market",
                        "volume": f"{position['volume']:.10f}"
                    })
                    txid = (r.get("txid") or [""])[0]
                    pnl  = (price - position["entry"]) * position["volume"]
                    _log({"event": exit_reason, "pair": top_pair,
                          "entry": position["entry"], "exit": price,
                          "pct": round(pct*100, 3), "pnl_usd": round(pnl, 6), "txid": txid})
                    position  = None
                    top_pair  = None   # force re-rank next cycle
                    last_scan = 0

            # ── Look for entry ──
            elif len(prices) >= 4:
                # Entry signal: 3 consecutive rising prices (short-term momentum)
                trend_up   = prices[-1] > prices[-2] > prices[-3]
                trend_down = prices[-1] < prices[-2] < prices[-3]
                avg        = sum(prices[-5:]) / min(len(prices), 5)
                signal     = (trend_up and price > avg) or (trend_down and price < avg)

                direction  = "buy" if (trend_up and price > avg) else None
                # Only go long for now (no short on spot)
                if signal and direction == "buy":
                    bal = _post("/0/private/Balance")
                    if bal.get("_error"):
                        print(f"[WAIT] Balance check failed: {bal['_error']}")
                        time.sleep(SCAN_SEC)
                        continue

                    usdt_bal = float(bal.get("USDT", 0))
                    zusd_bal = float(bal.get("ZUSD", 0))
                    usd = usdt_bal + zusd_bal
                    print(f"[ENTRY-CHECK] total=${usd:.4f} usdt=${usdt_bal:.4f} zusd=${zusd_bal:.4f} signal=UP pair={top_pair}")

                    if usd >= 1.0:
                        # Use USDT pair if available (we have USDT balance)
                        trade_pair = top_pair
                        if usdt_bal > zusd_bal and top_pair.endswith("USD") and not top_pair.endswith("USDT"):
                            trade_pair = top_pair.replace("USD", "USDT")

                        # Spend from the actual quote wallet for the selected pair only.
                        quote_capital = usdt_bal if trade_pair.endswith("USDT") else zusd_bal
                        capital = quote_capital * RISK_SHARE * 0.98  # fee/slippage buffer
                        volume  = capital / price if price > 0 else 0

                        # Kraken has minimum order sizes — skip if too small
                        min_notional = 0.50  # 50 cents
                        if capital >= min_notional:
                            print(f"[ENTRY] BUY {volume:.6f} {trade_pair} @ ${price:.6f}  (${capital:.4f})")
                            r = _post("/0/private/AddOrder", {
                                "pair": trade_pair, "type": "buy",
                                "ordertype": "market",
                                "volume": f"{volume:.10f}"
                            })
                            if r.get("_error"):
                                print(f"[SKIP] Order rejected by Kraken: {r['_error']}")
                                time.sleep(SCAN_SEC)
                                continue
                            txid = (r.get("txid") or [""])[0]
                            if txid:
                                position = {"entry": price, "volume": volume,
                                            "opened": now, "txid": txid}
                                top_pair = trade_pair  # track the actual pair used
                                _log({"event": "entry", "pair": top_pair, "price": price,
                                      "volume": volume, "capital_usd": capital, "txid": txid})
                            else:
                                print(f"[SKIP] Order rejected (check min order size for {top_pair})")
                        else:
                            print(f"[SKIP] Capital ${capital:.4f} below $0.50 min")
                    else:
                        print(f"[WAIT] Need $1.00+ in USD/USDT. Have ${usd:.4f}.")
                else:
                    print(f"[WATCH] {top_pair} @ ${price:.6f}  (waiting for momentum)")

            time.sleep(SCAN_SEC)

        except KeyboardInterrupt:
            print("\n[STOP] Shutting down."); break
        except Exception as e:
            import traceback; traceback.print_exc()
            time.sleep(5)

# ── Boot ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    _acquire_lock()
    print("="*65)
    print(" KRAKEN SWING HUNTER  |  LIVE  |  ALL PAIRS")
    print("="*65)

    bals = get_balances()
    total = portfolio_usd(bals)
    print(f"\n[PORTFOLIO]")
    for k, v in bals.items():
        print(f"  {k}: {v:.8f}")
    print(f"  TOTAL ~= ${total:.4f}\n")

    # Convert BTC dust to USD if needed
    usd = float(bals.get("ZUSD", 0)) + float(bals.get("USDT", 0))
    if usd < 1.0:
        print("[INIT] Low USD - attempting BTC->USD conversion...")
        convert_btc_to_usd(bals)
    else:
        print(f"[INIT] Trading capital: ${usd:.4f} ready")

    try:
        run()
    finally:
        _release_lock()
