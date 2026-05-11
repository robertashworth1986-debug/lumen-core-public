"""
POLYGON + TWELVE DATA fetcher.
Pulls 2 years of hourly bars for ~200 liquid US stocks (Polygon)
and a curated forex/extra-crypto basket (Twelve Data).
Auto-handles rate limiting on both free and paid tiers.
"""
from __future__ import annotations
import os, sys, time, json, pickle
from pathlib import Path
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "backtest"
OUT.mkdir(parents=True, exist_ok=True)
CACHE_POLY = OUT / "ohlc_polygon_stocks.pkl"
CACHE_TD   = OUT / "ohlc_twelvedata.pkl"
CACHE_TD_C = OUT / "ohlc_twelvedata_crypto.pkl"

POLYGON_KEY = os.environ.get("POLYGON_API_KEY")
TD_KEY      = os.environ.get("TWELVE_DATA_API_KEY")

# ~200 most liquid US stocks (mix of mega/large/mid + ETFs)
STOCKS = [
    # Mega caps
    "AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","BRK.B","LLY","AVGO",
    "JPM","V","UNH","XOM","WMT","JNJ","MA","PG","HD","COST",
    "ABBV","ORCL","BAC","NFLX","KO","CRM","CVX","MRK","AMD","PEP",
    "ADBE","TMO","CSCO","ACN","LIN","MCD","ABT","WFC","DHR","DIS",
    "TXN","INTC","VZ","NEE","PM","CAT","INTU","UNP","NKE","AMGN",
    # Tech / growth
    "QCOM","HON","BMY","SPGI","BA","UPS","LOW","RTX","SBUX","T",
    "PFE","BLK","SCHW","DE","PLD","GE","ELV","BKNG","AXP","ISRG",
    "GS","MDLZ","TJX","C","SYK","GILD","MMC","REGN","VRTX","ADI",
    "AMAT","NOW","LMT","CB","ADP","ZTS","SO","PYPL","BSX","CI",
    # Mid caps + ETFs
    "MO","DUK","CMG","PNC","CL","TGT","BDX","NSC","FI","SHW",
    "USB","ITW","FDX","EOG","SLB","APD","MMM","HUM","CVS","WM",
    "MET","TFC","ORLY","BA","PSX","COP","MCO","AON","FCX","NXPI",
    "PXD","ECL","COF","MAR","HCA","TT","DELL","CHTR","D","KMB",
    # Crypto / fintech / beta plays
    "COIN","HOOD","SQ","ROKU","SNAP","SHOP","UBER","ABNB","DASH","RBLX",
    # Semis
    "TSM","ASML","MU","ON","WDC","STX","KLAC","LRCX","MRVL","SWKS",
    # Energy/materials
    "OXY","HAL","BKR","DVN","MPC","VLO","HES","WMB","KMI","ET",
    # ETFs (huge volume, clean signal)
    "SPY","QQQ","IWM","DIA","VTI","XLF","XLE","XLK","XLV","XLI",
    "XLY","XLP","XLB","XLU","XLRE","XLC","SOXL","SOXX","SMH","ARKK",
    "GLD","SLV","TLT","HYG","LQD","USO","UUP","VEA","VWO","EFA",
    "EEM","FXI","EWZ","INDA","EWJ","EWG","EWU","RSP","MGK","VUG",
]
STOCKS = list(dict.fromkeys(STOCKS))  # de-dupe

# Curated forex + extra crypto (Twelve Data)
FOREX = [
    "EUR/USD","GBP/USD","USD/JPY","USD/CHF","AUD/USD","NZD/USD","USD/CAD",
    "EUR/GBP","EUR/JPY","GBP/JPY","AUD/JPY","EUR/AUD","CHF/JPY","EUR/CHF",
    "USD/MXN","USD/SEK","USD/NOK","USD/ZAR","USD/TRY","USD/SGD","USD/HKD",
]
TD_CRYPTO = [
    "BTC/USD","ETH/USD","XRP/USD","SOL/USD","BNB/USD","DOGE/USD","ADA/USD",
    "TRX/USD","AVAX/USD","DOT/USD","LINK/USD","SHIB/USD","TON/USD","MATIC/USD",
]

def http_json(url, headers=None, timeout=25):
    req = urllib.request.Request(url, headers=headers or {"User-Agent":"luma-multi/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

# ---- POLYGON ----
def fetch_polygon(symbol: str, days: int = 730, retries: int = 4):
    if not POLYGON_KEY: return None
    end = datetime.utcnow().date()
    start = end - timedelta(days=days)
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/hour/{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={POLYGON_KEY}"
    for attempt in range(retries):
        try:
            data = http_json(url)
            if data.get("status") == "ERROR":
                msg = data.get("error","")
                if "exceeded" in msg.lower() or "limit" in msg.lower():
                    time.sleep(15 + attempt*15); continue
                return None
            results = data.get("results") or []
            if len(results) < 100: return None
            df = pd.DataFrame(results)
            df["t"] = pd.to_datetime(df["t"], unit="ms")
            df = df.rename(columns={"c":"c","o":"o","h":"h","l":"l","v":"v"})
            df = df.set_index("t").sort_index()
            df["c"] = df["c"].astype(float); df["v"] = df["v"].astype(float)
            return df[["o","h","l","c","v"]]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15 + attempt*15); continue
            return None
        except Exception:
            time.sleep(2 + attempt); continue
    return None

# ---- TWELVE DATA ----
def fetch_twelve(symbol: str, retries: int = 4):
    if not TD_KEY: return None
    url = f"https://api.twelvedata.com/time_series?symbol={urllib.parse.quote(symbol)}&interval=1h&outputsize=5000&apikey={TD_KEY}"
    for attempt in range(retries):
        try:
            import urllib.parse as up  # noqa
            data = http_json(url)
            if data.get("status") == "error":
                msg = data.get("message","")
                if "credit" in msg.lower() or "limit" in msg.lower() or "rate" in msg.lower():
                    time.sleep(20 + attempt*15); continue
                return None
            vals = data.get("values") or []
            if len(vals) < 100: return None
            df = pd.DataFrame(vals)
            df["t"] = pd.to_datetime(df["datetime"])
            df = df.set_index("t").sort_index()
            df["o"] = df["open"].astype(float)
            df["h"] = df["high"].astype(float)
            df["l"] = df["low"].astype(float)
            df["c"] = df["close"].astype(float)
            df["v"] = df.get("volume","0").astype(float) if "volume" in df.columns else 0.0
            return df[["o","h","l","c","v"]]
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(20 + attempt*10); continue
            return None
        except Exception:
            time.sleep(2 + attempt); continue
    return None
import urllib.parse  # ensure imported

def save_cache(d, path):
    tmp = path.with_suffix(".tmp")
    with open(tmp,"wb") as f: pickle.dump(d, f)
    tmp.replace(path)

def fetch_basket(name, symbols, fetcher, cache_path, max_workers=6, save_every=15):
    existing = {}
    if cache_path.exists():
        try:
            with open(cache_path,"rb") as f: existing = pickle.load(f)
        except: pass
    todo = [s for s in symbols if s not in existing]
    print(f"[{name}] {len(existing)} cached, {len(todo)} to fetch")
    if not todo: return existing
    cache = dict(existing)
    completed = 0; t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {}
        for s in todo:
            futures[ex.submit(fetcher, s)] = s
            time.sleep(0.15)
        for fut in as_completed(futures):
            sym = futures[fut]
            try: df = fut.result()
            except: df = None
            if df is not None and len(df) >= 100:
                cache[sym] = df
            completed += 1
            if completed % save_every == 0:
                save_cache(cache, cache_path)
                print(f"[{name}] {completed}/{len(todo)} | cached={len(cache)} | {time.time()-t0:.0f}s")
    save_cache(cache, cache_path)
    print(f"[{name}] DONE. cached={len(cache)} | {time.time()-t0:.1f}s")
    if cache:
        bars = [len(df) for df in cache.values()]
        print(f"[{name}] bars: min={min(bars)} med={sorted(bars)[len(bars)//2]} max={max(bars)}")
    return cache

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("="*76); print("MULTI-SOURCE FETCH (Polygon + Twelve Data)"); print("="*76)
    print(f"POLYGON key: {'YES' if POLYGON_KEY else 'NO'} | TWELVE_DATA: {'YES' if TD_KEY else 'NO'}")
    print(f"Stocks: {len(STOCKS)} | Forex: {len(FOREX)} | TD-crypto: {len(TD_CRYPTO)}")
    if POLYGON_KEY:
        fetch_basket("POLYGON-STOCKS", STOCKS, fetch_polygon, CACHE_POLY, max_workers=8)
    if TD_KEY:
        fetch_basket("TWELVE-FX", FOREX, fetch_twelve, CACHE_TD, max_workers=4)
        fetch_basket("TWELVE-CRYPTO", TD_CRYPTO, fetch_twelve, CACHE_TD_C, max_workers=4)
    print("[ALL DONE]")

if __name__ == "__main__":
    main()
