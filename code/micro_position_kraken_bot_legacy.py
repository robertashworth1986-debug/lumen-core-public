#!/usr/bin/env python3
"""
KRAKEN PORTFOLIO SCALPER - FLIP WHAT YOU HAVE INTO MORE
Strategy:
  1. Reads actual live balances
  2. Values portfolio in USD
  3. Sells BTC dust -> USD capital
  4. Scalps PEPE/USD (high volatility = most opportunity)
  5. Compounds every win back in
"""

import os
import sys
import json
import time
import hmac
import hashlib
import base64
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import requests
import urllib.parse

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT_DIR = ROOT / "out" / "execution"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LEDGER_FILE  = OUT_DIR / "micro_kraken_ledger.jsonl"
STATE_FILE   = OUT_DIR / "micro_kraken_state.json"

KRAKEN_API_URL = "https://api.kraken.com"

# Load keys
def load_keys():
    env_path = ROOT / "code" / "execution" / "config" / "luma_live_keys.env"
    key, secret = "", ""
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("KRAKEN_API_KEY="):
                key = line.split("=", 1)[1].strip()
            elif line.startswith("KRAKEN_API_SECRET="):
                secret = line.split("=", 1)[1].strip()
    return key, secret

API_KEY, API_SECRET = load_keys()
if not API_KEY or not API_SECRET:
    print("[ERROR] Missing Kraken keys"); sys.exit(1)

print(f"[BOT] Key: {API_KEY[:8]}... | LIVE KRAKEN")

# ── Kraken signing ──────────────────────────────────────────────
def _sign(urlpath: str, data: dict) -> str:
    postdata = urllib.parse.urlencode(data)
    encoded  = (str(data["nonce"]) + postdata).encode()
    message  = urlpath.encode() + hashlib.sha256(encoded).digest()
    sig      = hmac.new(base64.b64decode(API_SECRET), message, hashlib.sha512).digest()
    return base64.b64encode(sig).decode()

def _post(endpoint: str, data: dict = None) -> dict:
    data = data or {}
    data["nonce"] = str(int(time.time() * 1000))
    headers = {"API-Key": API_KEY, "API-Sign": _sign(endpoint, data)}
    try:
        r = requests.post(KRAKEN_API_URL + endpoint, headers=headers, data=data, timeout=10)
        result = r.json()
        errs = result.get("error", [])
        if errs:
            print(f"[KRAKEN-ERR] {endpoint}: {errs}")
            return {"_error": errs}
        return result.get("result", {})
    except Exception as e:
        print(f"[HTTP-ERR] {e}")
        return {"_error": str(e)}

def _public_get(endpoint: str, params: dict = None) -> dict:
    try:
        r = requests.get(KRAKEN_API_URL + endpoint, params=params or {}, timeout=8)
        d = r.json()
        if d.get("error"):
            return {}
        return d.get("result", {})
    except Exception as e:
        print(f"[PUB-ERR] {e}")
        return {}

# ── Market data ─────────────────────────────────────────────────
PAIR_MAP = {
    "BTC":  "XXBTZUSD",
    "ETH":  "XETHZUSD",
    "SOL":  "SOLUSD",
    "ADA":  "ADAUSD",
    "PEPE": "PEPEUSD",
    "BABY": "BABYUSD",
    "BONK": "BONKUSD",
    "XRP":  "XXRPZUSD",
    "DOGE": "XDGEUSD",
}

def get_price(kraken_pair: str) -> Optional[float]:
    result = _public_get("/0/public/Ticker", {"pair": kraken_pair})
    if not result:
        return None
    data = next(iter(result.values()), {})
    try:
        return float(data["c"][0])
    except Exception:
        return None

def value_portfolio() -> dict:
    """Get balances and value everything in USD."""
    bal = _post("/0/private/Balance")
    if "_error" in bal:
        return {}

    print(f"\n[PORTFOLIO]")
    portfolio = {}
    total_usd = 0.0

    asset_map = {
        "XXBT": ("BTC",  "XXBTZUSD"),
        "XETH": ("ETH",  "XETHZUSD"),
        "SOL":  ("SOL",  "SOLUSD"),
        "ADA":  ("ADA",  "ADAUSD"),
        "PEPE": ("PEPE", "PEPEUSD"),
        "BABY": ("BABY", "BABYUSD"),
        "BONK": ("BONK", "BONKUSD"),
        "XXDG": ("DOGE", "XDGEUSD"),
        "XXRP": ("XRP",  "XXRPZUSD"),
        "ZUSD": ("USD",  None),
        "SPX":  ("SPX",  None),
    }

    for kraken_key, qty_str in bal.items():
        qty = float(qty_str)
        if qty == 0:
            continue
        info = asset_map.get(kraken_key, (kraken_key, None))
        name, pair = info

        if name == "USD":
            usd_val = qty
        elif pair:
            price = get_price(pair)
            usd_val = qty * price if price else 0.0
        else:
            usd_val = 0.0

        portfolio[name] = {"qty": qty, "usd_value": usd_val, "kraken_key": kraken_key}
        total_usd += usd_val
        print(f"  {name:6s}: {qty:.8f}  ≈ ${usd_val:.4f}")

    print(f"  {'TOTAL':6s}:              ≈ ${total_usd:.4f}")
    portfolio["_total_usd"] = total_usd
    return portfolio

# ── Trading ─────────────────────────────────────────────────────
def place_market_order(pair: str, side: str, volume: float) -> Optional[str]:
    """Market order - fastest fill."""
    data = {
        "pair":      pair,
        "type":      side.lower(),
        "ordertype": "market",
        "volume":    f"{volume:.10f}",
    }
    result = _post("/0/private/AddOrder", data)
    if "_error" in result:
        return None
    txids = result.get("txid", [])
    txid = txids[0] if txids else None
    print(f"[ORDER] {side.upper()} {volume:.8f} {pair} -> txid={txid}")
    return txid

def log_trade(event: dict):
    event["ts"] = datetime.now(timezone.utc).isoformat()
    with LEDGER_FILE.open("a") as f:
        f.write(json.dumps(event) + "\n")

# ── Main strategy: PEPE scalper ──────────────────────────────────
def run_pepe_scalper():
    """
    Core loop:
    - Watch PEPE/USD price every 6 seconds
    - Buy when momentum up (consecutive higher lows)
    - Sell when +1.5% or -0.5%
    - Keep compounding USD balance
    """
    PAIR       = "PEPEUSD"
    TP_PCT     =  0.015   # +1.5% take profit
    SL_PCT     = -0.005   # -0.5% stop loss
    MAX_HOLD   = 240      # 4 min max hold
    RISK_SHARE =  0.80    # use 80% of available USD per trade

    prices     = []
    position   = None  # {"entry": float, "volume": float, "txid": str, "time": float}

    print(f"\n[SCALPER] PEPE/USD | TP={TP_PCT*100:.1f}% SL={SL_PCT*100:.1f}%")
    print("[SCALPER] Running... Ctrl+C to stop\n")

    while True:
        try:
            price = get_price(PAIR)
            if not price:
                time.sleep(3); continue

            prices.append(price)
            if len(prices) > 20:
                prices.pop(0)

            now = time.time()

            # ── Manage open position ──
            if position:
                pct = (price - position["entry"]) / position["entry"]
                age = now - position["time"]
                print(f"[HOLD] PEPE @ ${price:.8f} | {pct*100:+.2f}% | {age:.0f}s")

                if pct >= TP_PCT:
                    print(f"[TP] +{pct*100:.2f}% - SELLING")
                    txid = place_market_order(PAIR, "sell", position["volume"])
                    pnl  = (price - position["entry"]) * position["volume"]
                    log_trade({"event": "take_profit", "pair": PAIR, "entry": position["entry"],
                               "exit": price, "pct": pct, "pnl_usd": pnl, "txid": txid})
                    position = None

                elif pct <= SL_PCT:
                    print(f"[SL] {pct*100:.2f}% - STOP LOSS")
                    txid = place_market_order(PAIR, "sell", position["volume"])
                    pnl  = (price - position["entry"]) * position["volume"]
                    log_trade({"event": "stop_loss", "pair": PAIR, "entry": position["entry"],
                               "exit": price, "pct": pct, "pnl_usd": pnl, "txid": txid})
                    position = None

                elif age > MAX_HOLD:
                    print(f"[TIMEOUT] {age:.0f}s - exiting")
                    txid = place_market_order(PAIR, "sell", position["volume"])
                    pnl  = (price - position["entry"]) * position["volume"]
                    log_trade({"event": "timeout_exit", "pair": PAIR, "entry": position["entry"],
                               "exit": price, "pct": pct, "pnl_usd": pnl, "txid": txid})
                    position = None

            # ── Look for entry ──
            elif len(prices) >= 5:
                # Momentum: last 3 prices trending up AND current > 5-bar average
                avg5  = sum(prices[-5:]) / 5
                trend = prices[-1] > prices[-2] > prices[-3]

                print(f"[SCAN] PEPE=${price:.8f} avg5=${avg5:.8f} trend={'UP' if trend else 'flat'}")

                if trend and price > avg5:
                    # Get current USD balance
                    bal = _post("/0/private/Balance")
                    usd = float(bal.get("ZUSD", 0))

                    if usd >= 0.50:
                        capital = usd * RISK_SHARE
                        volume  = capital / price
                        # Kraken PEPE min order ~10,000 PEPE
                        min_vol = 10000.0
                        if volume >= min_vol:
                            print(f"[ENTRY] Buying {volume:.0f} PEPE @ ${price:.8f} (${capital:.4f})")
                            txid = place_market_order(PAIR, "buy", volume)
                            if txid:
                                position = {"entry": price, "volume": volume,
                                            "txid": txid, "time": now}
                                log_trade({"event": "entry", "pair": PAIR, "price": price,
                                           "volume": volume, "capital_usd": capital, "txid": txid})
                        else:
                            print(f"[SKIP] Volume {volume:.0f} below min 10000 PEPE")
                    else:
                        print(f"[WAIT] USD balance ${usd:.4f} - need $0.50+")

            time.sleep(6)

        except KeyboardInterrupt:
            print("\n[STOP] Shutting down cleanly")
            break
        except Exception as e:
            print(f"[ERR] {e}")
            import traceback; traceback.print_exc()
            time.sleep(5)

# ── Entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 70)
    print("KRAKEN PORTFOLIO SCALPER  |  LIVE MODE  |  $9.45 -> WEALTH")
    print("=" * 70)

    # Step 1: Show full portfolio with USD values
    portfolio = value_portfolio()
    if not portfolio:
        print("[ERROR] Could not load portfolio. Check keys."); sys.exit(1)

    total = portfolio.get("_total_usd", 0)
    btc   = portfolio.get("BTC", {})
    usd   = portfolio.get("USD", {})

    # Step 2: If BTC > $1 and USD < $1, convert BTC dust to USD first
    btc_val = btc.get("usd_value", 0)
    usd_val = usd.get("usd_value", 0)

    if btc_val > 1.0 and usd_val < 1.0:
        print(f"\n[CONVERT] BTC worth ${btc_val:.2f} -> converting to USD for trading capital")
        btc_qty = btc.get("qty", 0)
        # Kraken BTC min order is 0.0001 BTC
        if btc_qty >= 0.0001:
            txid = place_market_order("XXBTZUSD", "sell", btc_qty)
            if txid:
                log_trade({"event": "btc_to_usd_conversion", "btc_qty": btc_qty,
                           "est_usd": btc_val, "txid": txid})
                print(f"[CONVERT] Sold {btc_qty} BTC for ~${btc_val:.2f} USD. Waiting for settlement...")
                time.sleep(4)
        else:
            print(f"[SKIP] BTC qty {btc_qty} below min 0.0001, can't convert")

    # Step 3: Run PEPE scalper
    run_pepe_scalper()

# Target: 1-3% daily compounding on volatile alts
# Risk: $0.10-0.20 max per trade (2-3% of capital)
# Strategy: Rapid entry/exit on momentum spikes + support bounces
# Platform: Real Kraken (LIVE MODE)

import os
import sys
import json
import time
import hmac
import hashlib
import base64
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import requests
import urllib.parse

# Paths
ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT_DIR = ROOT / "out" / "execution"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LEDGER_FILE = OUT_DIR / "micro_kraken_ledger.jsonl"
STATE_FILE = OUT_DIR / "micro_kraken_state.json"
BALANCE_CACHE_FILE = OUT_DIR / "micro_kraken_balance.json"

KRAKEN_API_URL = "https://api.kraken.com"
BALANCE_PATH = "/0/private/Balance"
ADD_ORDER_PATH = "/0/private/AddOrder"
CANCEL_ORDER_PATH = "/0/private/CancelOrder"
OPEN_ORDERS_PATH = "/0/private/OpenOrders"
QUERY_ORDERS_PATH = "/0/private/QueryOrders"
TRADES_HISTORY_PATH = "/0/private/TradesHistory"

# Load API keys
def load_keys() -> tuple:
    env_path = ROOT / "code" / "execution" / "config" / "luma_live_keys.env"
    key, secret = None, None
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("KRAKEN_API_KEY="):
                key = line.split("=", 1)[1].strip()
            elif line.startswith("KRAKEN_API_SECRET="):
                secret = line.split("=", 1)[1].strip()
    return key, secret

KRAKEN_API_KEY, KRAKEN_API_SECRET = load_keys()

if not KRAKEN_API_KEY or not KRAKEN_API_SECRET:
    print("[ERROR] KRAKEN_API_KEY or KRAKEN_API_SECRET not found in luma_live_keys.env")
    sys.exit(1)

print(f"[MICRO-BOT] Kraken API Key loaded: {KRAKEN_API_KEY[:8]}...")
print(f"[MICRO-BOT] Running on REAL Kraken (LIVE MODE)")

# Configuration
CONFIG = {
    "max_capital_per_trade_usd": 0.20,  # risk $0.20 per trade max
    "target_profit_pct": 0.015,  # 1.5% target
    "stop_loss_pct": -0.005,  # -0.5% stop
    "trading_pairs": ["SHIBUSD", "DOGEUSD", "XLMUSD", "ADAUSD", "MATICUSD", "AVAXUSD"],
    "scan_interval_sec": 8,
    "position_hold_max_sec": 300,  # 5 min max hold
    "min_volume_check_usd": 50.0,  # minimum orderbook volume
    "max_positions": 3,
}

def _kraken_sign(urlpath: str, data: Dict, secret: str) -> str:
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data.get("nonce", "")) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    signature = base64.b64encode(
        hmac.new(
            base64.b64decode(secret),
            message,
            hashlib.sha512
        ).digest()
    ).decode()
    return signature

def _kraken_request(endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    if data is None:
        data = {}
    
    nonce = str(int(time.time() * 1000))
    data["nonce"] = nonce
    
    signature = _kraken_sign(endpoint, data, KRAKEN_API_SECRET)
    
    headers = {
        "API-Sign": signature,
        "API-Key": KRAKEN_API_KEY,
    }
    
    try:
        resp = requests.post(
            KRAKEN_API_URL + endpoint,
            headers=headers,
            data=data,
            timeout=10
        )
        result = resp.json()
        if result.get("error"):
            print(f"[KRAKEN-ERROR] {endpoint}: {result['error']}")
            return {"error": result["error"]}
        return result.get("result", {})
    except Exception as e:
        print(f"[REQUEST-ERROR] {endpoint}: {e}")
        return {"error": str(e)}

def get_balance() -> Dict[str, float]:
    """Fetch current USD balance"""
    result = _kraken_request(BALANCE_PATH)
    if "error" in result:
        return {}
    
    # Extract USD balance - Kraken uses ZUSD for US dollars
    usd_balance = float(result.get("ZUSD", result.get("ZXUSD", result.get("USD", 0))))
    
    print(f"[BALANCE-RAW] {result}")  # show all assets so we can debug
    
    # Cache it
    cache = {
        "timestamp": time.time(),
        "usd_balance": usd_balance,
        "full_balance": result,
    }
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BALANCE_CACHE_FILE.write_text(json.dumps(cache, indent=2))
    
    return {"ZUSD": usd_balance, **result}

def get_last_price(pair: str) -> Optional[float]:
    """Get last trade price from Kraken public API"""
    try:
        # Normalize pair (e.g., SHIBUSD -> SHIB/USD for Kraken)
        kraken_pair = pair.replace("USD", "/USD") if "/" not in pair else pair
        
        resp = requests.get(
            "https://api.kraken.com/0/public/Ticker",
            params={"pair": kraken_pair},
            timeout=5
        )
        data = resp.json()
        if data.get("error"):
            print(f"[TICKER-ERROR] {pair}: {data['error']}")
            return None
        
        # Get the first (only) result
        result = next(iter(data.get("result", {}).values()), {})
        last_price = float(result.get("c", [None])[0])
        return last_price
    except Exception as e:
        print(f"[PRICE-ERROR] {pair}: {e}")
        return None

def place_order(
    pair: str,
    side: str,
    price: float,
    volume: float,
    order_type: str = "limit"
) -> Optional[Dict]:
    """Place a limit order on Kraken"""
    kraken_pair = pair.replace("USD", "/USD") if "/" not in pair else pair
    
    data = {
        "pair": kraken_pair,
        "type": side.lower(),  # buy / sell
        "ordertype": order_type,
        "price": str(price),
        "volume": str(volume),
        "flags": "post",  # post-only to avoid immediate fills on bad timing
    }
    
    result = _kraken_request(ADD_ORDER_PATH, data)
    
    if "error" in result or not result.get("txid"):
        print(f"[ORDER-ERROR] {side} {volume} {pair} @ {price}: {result}")
        return None
    
    order_id = result["txid"][0] if isinstance(result["txid"], list) else result["txid"]
    return {
        "pair": pair,
        "side": side.upper(),
        "price": price,
        "volume": volume,
        "txid": order_id,
        "timestamp": time.time(),
    }

def cancel_order(txid: str) -> bool:
    """Cancel an open order"""
    data = {"txid": txid}
    result = _kraken_request(CANCEL_ORDER_PATH, data)
    return "error" not in result or len(result) > 0

def get_open_orders() -> List[Dict]:
    """Get all open orders"""
    result = _kraken_request(OPEN_ORDERS_PATH)
    if "error" in result:
        return []
    
    orders = []
    for txid, order_data in (result.get("open", {}) or {}).items():
        orders.append({
            "txid": txid,
            "pair": order_data.get("descr", {}).get("pair", ""),
            "side": order_data.get("descr", {}).get("type", "").upper(),
            "volume": float(order_data.get("vol", 0)),
            "price": float(order_data.get("descr", {}).get("price", 0)),
            "opened": float(order_data.get("opentm", 0)),
            "status": order_data.get("status", "open"),
        })
    return orders

def get_closed_orders() -> Dict:
    """Get trade history"""
    result = _kraken_request(TRADES_HISTORY_PATH)
    if "error" in result:
        return {}
    return result.get("trades", {})

def log_trade(trade_event: Dict) -> None:
    """Append trade to ledger"""
    trade_event["timestamp"] = time.time()
    trade_event["datetime"] = datetime.now(timezone.utc).isoformat()
    
    with LEDGER_FILE.open("a") as f:
        f.write(json.dumps(trade_event, separators=(",", ":")) + "\n")
    
    print(f"[TRADE-LOG] {trade_event}")

def scan_and_trade():
    """Main trading loop - scan pairs and place micro positions"""
    print(f"\n[SCAN] {datetime.now(timezone.utc).isoformat()}")
    
    # Get current balance
    balance = get_balance()
    usd_balance = balance.get("ZUSD", 0)
    
    print(f"[BALANCE] USD: ${usd_balance:.4f}")
    
    if usd_balance < 0.05:
        print("[WARN] Balance too low, skipping scan")
        return
    
    # Get open orders (positions)
    open_orders = get_open_orders()
    print(f"[OPEN-POSITIONS] {len(open_orders)} open")
    
    if len(open_orders) >= CONFIG["max_positions"]:
        print(f"[LIMIT] Already at max {CONFIG['max_positions']} positions, skipping new entries")
        return
    
    # Scan each pair
    for pair in CONFIG["trading_pairs"]:
        price = get_last_price(pair)
        if price is None or price <= 0:
            continue
        
        print(f"[{pair}] ${price:.8f}")
        
        # Simple momentum check: if price moved in last few seconds (would need order book)
        # For now, just random entry on volatile pairs (SHIB, DOGE, XLM move daily)
        
        max_risk_usd = min(CONFIG["max_capital_per_trade_usd"], usd_balance * 0.03)
        
        if max_risk_usd < 0.01:
            continue
        
        volume = max_risk_usd / price
        entry_price = price * 0.998  # Buy slightly below last price
        
        print(f"[ENTRY] Placing buy order for {volume:.6f} {pair} @ ${entry_price:.8f}")
        
        order = place_order(pair, "buy", entry_price, volume)
        if order:
            log_trade({
                "event": "entry_order_placed",
                "pair": pair,
                "side": "BUY",
                "volume": volume,
                "price": entry_price,
                "risk_usd": max_risk_usd,
                "txid": order["txid"],
            })
            break  # Only place one order per scan interval

def manage_positions():
    """Check open orders for profit/loss targets"""
    print(f"[MANAGE] Checking positions...")
    
    open_orders = get_open_orders()
    
    for order in open_orders:
        pair = order["pair"]
        entry_price = order["price"]
        volume = order["volume"]
        txid = order["txid"]
        opened_sec = time.time() - order["opened"]
        
        # Get current price
        price = get_last_price(pair)
        if price is None:
            continue
        
        pct_change = (price - entry_price) / entry_price
        realized_pnl = (price - entry_price) * volume
        
        print(f"[{pair}] {pct_change*100:+.2f}% | ${realized_pnl:+.4f} | age: {opened_sec:.0f}s")
        
        # Take profit target
        if pct_change >= CONFIG["target_profit_pct"]:
            print(f"[TP] Taking profit on {pair} at +{pct_change*100:.2f}%")
            cancel_order(txid)
            
            # Place sell at market (slightly above)
            sell_price = price * 1.002
            sell_order = place_order(pair, "sell", sell_price, volume)
            
            if sell_order:
                log_trade({
                    "event": "exit_take_profit",
                    "pair": pair,
                    "side": "SELL",
                    "volume": volume,
                    "entry_price": entry_price,
                    "exit_price": sell_price,
                    "pct_gain": pct_change * 100,
                    "pnl_usd": realized_pnl,
                    "txid": sell_order["txid"],
                })
        
        # Stop loss
        elif pct_change <= CONFIG["stop_loss_pct"]:
            print(f"[SL] Stopping loss on {pair} at {pct_change*100:.2f}%")
            cancel_order(txid)
            
            sell_price = price * 0.998
            sell_order = place_order(pair, "sell", sell_price, volume)
            
            if sell_order:
                log_trade({
                    "event": "exit_stop_loss",
                    "pair": pair,
                    "side": "SELL",
                    "volume": volume,
                    "entry_price": entry_price,
                    "exit_price": sell_price,
                    "pct_loss": pct_change * 100,
                    "pnl_usd": realized_pnl,
                    "txid": sell_order["txid"],
                })
        
        # Time-based exit (5 min max)
        elif opened_sec > CONFIG["position_hold_max_sec"]:
            print(f"[TIMEOUT] Exiting {pair} after {opened_sec:.0f}s")
            cancel_order(txid)
            
            sell_price = price
            sell_order = place_order(pair, "sell", sell_price * 0.999, volume)
            
            if sell_order:
                log_trade({
                    "event": "exit_timeout",
                    "pair": pair,
                    "side": "SELL",
                    "volume": volume,
                    "entry_price": entry_price,
                    "exit_price": sell_price,
                    "pct_change": pct_change * 100,
                    "pnl_usd": realized_pnl,
                    "hold_sec": opened_sec,
                    "txid": sell_order["txid"],
                })

def main():
    print(f"\n{'='*80}")
    print(f"MICRO-POSITION KRAKEN BOT - LIVE MODE")
    print(f"Start Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"Capital per trade: ${CONFIG['max_capital_per_trade_usd']}")
    print(f"Target: +{CONFIG['target_profit_pct']*100:.1f}% | Stop: {CONFIG['stop_loss_pct']*100:.1f}%")
    print(f"Pairs: {', '.join(CONFIG['trading_pairs'])}")
    print(f"Scan interval: {CONFIG['scan_interval_sec']}s")
    print(f"{'='*80}\n")
    
    # Initial balance check
    balance = get_balance()
    usd_balance = float(balance.get("ZUSD", 0))
    print(f"[INIT] Starting USD balance: ${usd_balance:.4f}")
    
    if usd_balance < 0.10:
        print("[ERROR] Insufficient balance (< $0.10). Fund your account first.")
        sys.exit(1)
    
    cycle = 0
    while True:
        try:
            cycle += 1
            
            if cycle % 10 == 0:  # Every 10 cycles, scan for new entries
                scan_and_trade()
            
            manage_positions()  # Always check existing positions
            
            time.sleep(CONFIG["scan_interval_sec"])
        
        except KeyboardInterrupt:
            print("\n[EXIT] Shutting down...")
            break
        except Exception as e:
            print(f"[EXCEPTION] {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    main()
