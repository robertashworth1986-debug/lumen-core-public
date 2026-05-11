"""
ALPACA multi-asset fetcher (stocks SIP feed + crypto).
2 years of hourly bars for 200 stocks + 50 crypto pairs.
Handles pagination via next_page_token. ~200 req/min Alpaca paid limit.
"""
from __future__ import annotations
import os, sys, time, json, pickle, urllib.parse, urllib.request, urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "backtest"
OUT.mkdir(parents=True, exist_ok=True)
CACHE_STK = OUT / "ohlc_alpaca_stocks.pkl"
CACHE_CRY = OUT / "ohlc_alpaca_crypto.pkl"

AK   = os.environ["ALPACA_API_KEY"]
ASEC = os.environ["ALPACA_API_SECRET"]
HDR  = {"APCA-API-KEY-ID": AK, "APCA-API-SECRET-KEY": ASEC}

# 200 most liquid US stocks (mega + large + ETFs)
STOCKS = [
    "AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","BRK.B","LLY","AVGO",
    "JPM","V","UNH","XOM","WMT","JNJ","MA","PG","HD","COST",
    "ABBV","ORCL","BAC","NFLX","KO","CRM","CVX","MRK","AMD","PEP",
    "ADBE","TMO","CSCO","ACN","LIN","MCD","ABT","WFC","DHR","DIS",
    "TXN","INTC","VZ","NEE","PM","CAT","INTU","UNP","NKE","AMGN",
    "QCOM","HON","BMY","SPGI","BA","UPS","LOW","RTX","SBUX","T",
    "PFE","BLK","SCHW","DE","PLD","GE","ELV","BKNG","AXP","ISRG",
    "GS","MDLZ","TJX","C","SYK","GILD","MMC","REGN","VRTX","ADI",
    "AMAT","NOW","LMT","CB","ADP","ZTS","SO","PYPL","BSX","CI",
    "MO","DUK","CMG","PNC","CL","TGT","BDX","NSC","FI","SHW",
    "USB","ITW","FDX","EOG","SLB","APD","MMM","HUM","CVS","WM",
    "MET","TFC","ORLY","PSX","COP","MCO","AON","FCX","NXPI",
    "ECL","COF","MAR","HCA","TT","DELL","CHTR","D","KMB",
    "COIN","HOOD","SQ","ROKU","SNAP","SHOP","UBER","ABNB","DASH","RBLX",
    "TSM","ASML","MU","ON","WDC","STX","KLAC","LRCX","MRVL","SWKS",
    "OXY","HAL","BKR","DVN","MPC","VLO","HES","WMB","KMI","ET",
    "SPY","QQQ","IWM","DIA","VTI","XLF","XLE","XLK","XLV","XLI",
    "XLY","XLP","XLB","XLU","XLRE","XLC","SOXL","SOXX","SMH","ARKK",
    "GLD","SLV","TLT","HYG","LQD","USO","UUP","VEA","VWO","EFA",
    "EEM","FXI","EWZ","INDA","EWJ","EWG","EWU","RSP","MGK","VUG",
]
STOCKS = list(dict.fromkeys(STOCKS))

# 50 most liquid USD crypto pairs on Alpaca
CRYPTO = [
    "BTC/USD","ETH/USD","SOL/USD","XRP/USD","DOGE/USD","AVAX/USD","LINK/USD",
    "DOT/USD","LTC/USD","BCH/USD","UNI/USD","AAVE/USD","CRV/USD","MKR/USD",
    "SUSHI/USD","YFI/USD","GRT/USD","BAT/USD","MATIC/USD","SHIB/USD",
    "TRUMP/USD","PEPE/USD","BONK/USD","WIF/USD","FLOKI/USD",
]

YEARS = 2
TIMEFRAME = "1Hour"

def http_json(url, retries=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 + attempt*3); continue
            if e.code in (500,502,503,504):
                time.sleep(2 + attempt); continue
            return {"_err": e.code, "_body": e.read()[:200].decode(errors="ignore")}
        except Exception as ex:
            time.sleep(1 + attempt)
    return None

def fetch_stock(symbol: str):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=YEARS*365)
    s = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    e = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    sym_enc = urllib.parse.quote(symbol)
    bars = []
    page_token = None
    while True:
        url = (f"https://data.alpaca.markets/v2/stocks/{sym_enc}/bars"
               f"?timeframe={TIMEFRAME}&start={s}&end={e}&limit=10000"
               f"&adjustment=split&feed=sip")
        if page_token:
            url += f"&page_token={urllib.parse.quote(page_token)}"
        d = http_json(url)
        if not d or "_err" in d: return None
        bars.extend(d.get("bars") or [])
        page_token = d.get("next_page_token")
        if not page_token: break
    if len(bars) < 200: return None
    df = pd.DataFrame(bars)
    df["t"] = pd.to_datetime(df["t"])
    df = df.set_index("t").sort_index()
    df = df.rename(columns={"o":"o","h":"h","l":"l","c":"c","v":"v"})
    return df[["o","h","l","c","v"]].astype(float)

def fetch_crypto(symbol: str):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=YEARS*365)
    s = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    e = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    sym_enc = urllib.parse.quote(symbol)
    bars = []
    page_token = None
    while True:
        url = (f"https://data.alpaca.markets/v1beta3/crypto/us/bars"
               f"?symbols={sym_enc}&timeframe={TIMEFRAME}&start={s}&end={e}&limit=10000")
        if page_token:
            url += f"&page_token={urllib.parse.quote(page_token)}"
        d = http_json(url)
        if not d or "_err" in d: return None
        sym_bars = (d.get("bars") or {}).get(symbol, [])
        bars.extend(sym_bars)
        page_token = d.get("next_page_token")
        if not page_token: break
    if len(bars) < 200: return None
    df = pd.DataFrame(bars)
    df["t"] = pd.to_datetime(df["t"])
    df = df.set_index("t").sort_index()
    return df[["o","h","l","c","v"]].astype(float)

def save_cache(d, path):
    tmp = path.with_suffix(".tmp")
    with open(tmp,"wb") as f: pickle.dump(d, f)
    tmp.replace(path)

def fetch_basket(name, symbols, fetcher, cache_path, max_workers=8, save_every=10):
    existing = {}
    if cache_path.exists():
        try:
            with open(cache_path,"rb") as f: existing = pickle.load(f)
        except: pass
    todo = [s for s in symbols if s not in existing]
    print(f"[{name}] {len(existing)} cached, {len(todo)} to fetch", flush=True)
    if not todo: return existing
    cache = dict(existing)
    completed = 0; t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(fetcher, s): s for s in todo}
        for fut in as_completed(futures):
            sym = futures[fut]
            try: df = fut.result()
            except Exception as e: df = None; print(f"[{name}] {sym} EXC {e}", flush=True)
            if df is not None and len(df) >= 200:
                cache[sym] = df
            completed += 1
            if completed % save_every == 0:
                save_cache(cache, cache_path)
                print(f"[{name}] {completed}/{len(todo)} | cached={len(cache)} | {time.time()-t0:.0f}s", flush=True)
    save_cache(cache, cache_path)
    print(f"[{name}] DONE. cached={len(cache)}/{len(symbols)} | {time.time()-t0:.1f}s", flush=True)
    if cache:
        bars = sorted([len(df) for df in cache.values()])
        print(f"[{name}] bars: min={bars[0]} med={bars[len(bars)//2]} max={bars[-1]}", flush=True)
    return cache

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("="*76, flush=True)
    print(f"ALPACA MULTI-ASSET FETCH | {YEARS}y hourly | {len(STOCKS)} stocks + {len(CRYPTO)} crypto", flush=True)
    print("="*76, flush=True)
    fetch_basket("ALPACA-STOCKS", STOCKS, fetch_stock, CACHE_STK, max_workers=8)
    fetch_basket("ALPACA-CRYPTO", CRYPTO, fetch_crypto, CACHE_CRY, max_workers=4)
    print("[ALL DONE]", flush=True)

if __name__ == "__main__":
    main()
