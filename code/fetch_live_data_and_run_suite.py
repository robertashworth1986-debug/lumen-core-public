"""
fetch_live_data_and_run_suite.py
---------------------------------
1. Loads all 20 API keys from luma_live_keys.env
2. Fetches live daily OHLC from every available source:
     Kraken (public)  → crypto + FX pairs
     Twelve Data       → stocks + forex + crypto
     AlphaVantage      → stocks + FX
     Finnhub           → stocks + FX
     Alpaca            → US equities
     FRED              → macro rate/economic series
3. Saves clean CSVs to data/live_fetched/
4. Runs institutional_harmonic_suite.run_engine() against ALL CSVs
   (including pre-existing data/) for the best evidence possible
"""

import sys, os, time, json
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent / "execution"))

ROOT     = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
ENV_FILE = ROOT / "config" / "luma_live_keys.env"
DATA_DIR = ROOT / "data"
LIVE_DIR = DATA_DIR / "live_fetched"
LIVE_DIR.mkdir(parents=True, exist_ok=True)

# ── helpers ──────────────────────────────────────────────────────────────────

def load_keys():
    keys = {}
    if ENV_FILE.exists():
        for raw in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip(); v = v.strip().strip('"').strip("'")
            if k and v:
                keys[k] = v
    # also pick up anything already in env (os.environ)
    for k, v in os.environ.items():
        if k not in keys and v:
            keys[k] = v
    return keys

def save_series(name: str, closes: list):
    """Save a list of floats as a CSV with a 'close' column."""
    if len(closes) < 40:
        return False
    df = pd.DataFrame({"close": closes})
    path = LIVE_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"  saved {path.name}  ({len(closes)} rows)")
    return True

def rate_wait(seconds: float):
    time.sleep(seconds)

# ── SOURCE 1: Kraken public OHLC (no key required) ───────────────────────────
KRAKEN_DAILY_PAIRS = {
    "BTC":  "XBTUSDT",
    "ETH":  "ETHUSDT",
    "SOL":  "SOLUSDT",
    "XRP":  "XRPUSDT",
    "ADA":  "ADAUSDT",
    "DOGE": "DOGEUSD",
    "EUR":  "EURUSD",
    "GBP":  "GBPUSD",
    "AUD":  "AUDUSD",
    "JPY":  "JPYUSD",
    "CHF":  "CHFUSD",
    "GOLD": "XAUUSD",
}

def fetch_kraken():
    print("\n[Kraken public OHLC]")
    sess = requests.Session()
    ok = 0
    for sym, pair in KRAKEN_DAILY_PAIRS.items():
        try:
            r = sess.get(
                "https://api.kraken.com/0/public/OHLC",
                params={"pair": pair, "interval": 1440},  # 1440 = daily
                timeout=12,
            )
            data = r.json()
            if data.get("error"):
                print(f"  {sym}: error {data['error']}")
                continue
            res = data.get("result", {})
            keys = [k for k in res if k != "last"]
            if not keys:
                continue
            # OHLC row: [time, open, high, low, close, vwap, volume, count]
            closes = [float(row[4]) for row in res[keys[0]]]
            if save_series(f"kraken_{sym.lower()}_daily", closes):
                ok += 1
            rate_wait(0.3)
        except Exception as e:
            print(f"  {sym}: {e}")
    print(f"  → {ok}/{len(KRAKEN_DAILY_PAIRS)} symbols fetched")

# ── SOURCE 2: Twelve Data ─────────────────────────────────────────────────────
TWELVE_SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
    "SPY",  "QQQ",  "GLD",  "TLT",  "XLE",  "XLF",  "IWM",
    "EUR/USD", "GBP/USD", "BTC/USD", "ETH/USD", "SOL/USD",
]

def fetch_twelve_data(key: str):
    print("\n[Twelve Data]")
    if not key:
        print("  no key — skipping")
        return
    ok = 0
    for sym in TWELVE_SYMBOLS:
        try:
            r = requests.get(
                "https://api.twelvedata.com/time_series",
                params={
                    "symbol":     sym,
                    "interval":   "1day",
                    "outputsize": 500,
                    "apikey":     key,
                },
                timeout=15,
            )
            d = r.json()
            if d.get("status") == "error" or "values" not in d:
                print(f"  {sym}: {d.get('message','no data')}")
                rate_wait(1.0)
                continue
            closes = [float(v["close"]) for v in reversed(d["values"])]
            slug = sym.lower().replace("/", "_")
            if save_series(f"twelvedata_{slug}", closes):
                ok += 1
            rate_wait(0.8)   # free tier: ~8 req/min
        except Exception as e:
            print(f"  {sym}: {e}")
    print(f"  → {ok}/{len(TWELVE_SYMBOLS)} symbols fetched")

# ── SOURCE 3: AlphaVantage ────────────────────────────────────────────────────
AV_EQUITY_SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "JPM",  "XOM",  "BRK.B",
    "SPY",  "QQQ",  "GLD",  "TLT",  "IWM",
]
AV_FX_PAIRS = [
    ("EUR", "USD"), ("GBP", "USD"), ("AUD", "USD"),
    ("JPY", "USD"), ("CHF", "USD"),
]

def fetch_alphavantage(key: str):
    print("\n[AlphaVantage]")
    if not key:
        print("  no key — skipping")
        return
    ok = 0
    # equities (5 req/min free tier — space them 13s)
    for sym in AV_EQUITY_SYMBOLS:
        try:
            r = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    "function":   "TIME_SERIES_DAILY",
                    "symbol":     sym,
                    "outputsize": "full",
                    "apikey":     key,
                },
                timeout=20,
            )
            d = r.json()
            ts = d.get("Time Series (Daily)", {})
            if not ts:
                print(f"  {sym}: {d.get('Note', d.get('Information','no data'))[:80]}")
                rate_wait(13)
                continue
            closes = [float(ts[dt]["4. close"]) for dt in sorted(ts.keys())]
            if save_series(f"av_{sym.lower().replace('.','_')}", closes):
                ok += 1
            rate_wait(13)   # 5 req/min safely
        except Exception as e:
            print(f"  {sym}: {e}")

    # FX
    for from_c, to_c in AV_FX_PAIRS:
        try:
            r = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    "function":    "FX_DAILY",
                    "from_symbol": from_c,
                    "to_symbol":   to_c,
                    "outputsize":  "full",
                    "apikey":      key,
                },
                timeout=20,
            )
            d = r.json()
            ts = d.get("Time Series FX (Daily)", {})
            if not ts:
                print(f"  {from_c}/{to_c}: no data")
                rate_wait(13)
                continue
            closes = [float(ts[dt]["4. close"]) for dt in sorted(ts.keys())]
            if save_series(f"av_fx_{from_c.lower()}{to_c.lower()}", closes):
                ok += 1
            rate_wait(13)
        except Exception as e:
            print(f"  {from_c}/{to_c}: {e}")

    print(f"  → {ok} series fetched")

# ── SOURCE 4: Finnhub ─────────────────────────────────────────────────────────
FINNHUB_STOCKS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "JPM",  "XOM",  "BRK.B",
    "SPY",  "QQQ",  "GLD",
]
FINNHUB_FOREX = [
    "OANDA:EUR_USD", "OANDA:GBP_USD", "OANDA:AUD_USD",
    "OANDA:USD_JPY", "OANDA:USD_CHF",
]
FINNHUB_CRYPTO = [
    "BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:SOLUSDT",
]

def _finnhub_candles(sym: str, key: str, sess: requests.Session) -> list:
    now_ts  = int(datetime.now(timezone.utc).timestamp())
    from_ts = now_ts - 365 * 2 * 86400  # 2 years
    r = sess.get(
        "https://finnhub.io/api/v1/stock/candle",
        params={"symbol": sym, "resolution": "D",
                "from": from_ts, "to": now_ts, "token": key},
        timeout=15,
    )
    d = r.json()
    if d.get("s") != "ok":
        return []
    return list(d.get("c", []))

def _finnhub_forex(sym: str, key: str, sess: requests.Session) -> list:
    now_ts  = int(datetime.now(timezone.utc).timestamp())
    from_ts = now_ts - 365 * 2 * 86400
    r = sess.get(
        "https://finnhub.io/api/v1/forex/candle",
        params={"symbol": sym, "resolution": "D",
                "from": from_ts, "to": now_ts, "token": key},
        timeout=15,
    )
    d = r.json()
    if d.get("s") != "ok":
        return []
    return list(d.get("c", []))

def _finnhub_crypto(sym: str, key: str, sess: requests.Session) -> list:
    now_ts  = int(datetime.now(timezone.utc).timestamp())
    from_ts = now_ts - 365 * 2 * 86400
    r = sess.get(
        "https://finnhub.io/api/v1/crypto/candle",
        params={"symbol": sym, "resolution": "D",
                "from": from_ts, "to": now_ts, "token": key},
        timeout=15,
    )
    d = r.json()
    if d.get("s") != "ok":
        return []
    return list(d.get("c", []))

def fetch_finnhub(key: str):
    print("\n[Finnhub]")
    if not key:
        print("  no key — skipping")
        return
    ok = 0
    sess = requests.Session()
    for sym in FINNHUB_STOCKS:
        try:
            closes = _finnhub_candles(sym, key, sess)
            slug   = sym.lower().replace(".", "_")
            if save_series(f"finnhub_{slug}", closes):
                ok += 1
            rate_wait(0.25)  # free tier: 60 req/min
        except Exception as e:
            print(f"  {sym}: {e}")
    for sym in FINNHUB_FOREX:
        try:
            closes = _finnhub_forex(sym, key, sess)
            slug   = sym.lower().replace(":", "_").replace("/", "_")
            if save_series(f"finnhub_{slug}", closes):
                ok += 1
            rate_wait(0.25)
        except Exception as e:
            print(f"  {sym}: {e}")
    for sym in FINNHUB_CRYPTO:
        try:
            closes = _finnhub_crypto(sym, key, sess)
            slug   = sym.lower().replace(":", "_").replace("/", "_")
            if save_series(f"finnhub_{slug}", closes):
                ok += 1
            rate_wait(0.25)
        except Exception as e:
            print(f"  {sym}: {e}")
    print(f"  → {ok} series fetched")

# ── SOURCE 5: Alpaca (broker, US equities) ────────────────────────────────────
ALPACA_STOCKS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "JPM",  "XOM",  "SPY",  "QQQ",
]

def fetch_alpaca(key: str, secret: str):
    print("\n[Alpaca]")
    if not key or not secret:
        print("  no key/secret — skipping")
        return
    ok = 0
    headers = {
        "APCA-API-KEY-ID":     key,
        "APCA-API-SECRET-KEY": secret,
    }
    end   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = (datetime.now(timezone.utc) - timedelta(days=730)).strftime("%Y-%m-%d")
    sess  = requests.Session()
    for sym in ALPACA_STOCKS:
        try:
            r = sess.get(
                f"https://data.alpaca.markets/v2/stocks/{sym}/bars",
                params={
                    "timeframe": "1Day",
                    "start":     start,
                    "end":       end,
                    "limit":     1000,
                    "adjustment": "all",
                },
                headers=headers,
                timeout=15,
            )
            d = r.json()
            bars = d.get("bars", [])
            if not bars:
                print(f"  {sym}: no bars")
                continue
            closes = [float(b["c"]) for b in bars]
            if save_series(f"alpaca_{sym.lower()}", closes):
                ok += 1
            rate_wait(0.2)
        except Exception as e:
            print(f"  {sym}: {e}")
    print(f"  → {ok}/{len(ALPACA_STOCKS)} symbols fetched")

# ── SOURCE 6: FRED (macro series → rate/economic price series) ───────────────
FRED_SERIES = {
    "DGS10":    "10yr_yield",
    "DGS2":     "2yr_yield",
    "CPIAUCSL": "cpi",
    "UNRATE":   "unemployment",
    "DCOILWTICO": "oil_wti",
    "GOLDAMGBD228NLBM": "gold_price",
    "DEXUSEU":  "fx_eurusd",
    "DEXUSUK":  "fx_gbpusd",
    "SP500":    "sp500",
    "NASDAQCOM":"nasdaq",
    "VIXCLS":   "vix",
    "BAMLH0A0HYM2": "hy_spread",
    "T10YIE":   "breakeven_10yr",
    "MORTGAGE30US": "mortgage30",
}

def fetch_fred(key: str):
    print("\n[FRED]")
    if not key:
        print("  no key — skipping")
        return
    ok = 0
    for series_id, label in FRED_SERIES.items():
        try:
            r = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id":         series_id,
                    "api_key":           key,
                    "file_type":         "json",
                    "observation_start": "2018-01-01",
                    "sort_order":        "asc",
                },
                timeout=15,
            )
            d = r.json()
            obs = d.get("observations", [])
            closes = []
            for o in obs:
                try:
                    v = float(o["value"])
                    closes.append(v)
                except (ValueError, KeyError):
                    pass  # skip "." missing values
            if save_series(f"fred_{label}", closes):
                ok += 1
            rate_wait(0.3)
        except Exception as e:
            print(f"  {series_id}: {e}")
    print(f"  → {ok}/{len(FRED_SERIES)} series fetched")

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    t_start = time.time()
    print("=" * 70)
    print("LUMA LIVE DATA FETCH + INSTITUTIONAL HARMONIC SUITE RUNNER")
    print("=" * 70)

    keys = load_keys()

    fetch_kraken()
    fetch_finnhub(keys.get("FINNHUB_API_KEY", ""))
    fetch_fred(keys.get("FRED_API_KEY", ""))
    fetch_twelve_data(keys.get("TWELVE_DATA_API_KEY", ""))
    fetch_alpaca(keys.get("ALPACA_API_KEY", ""), keys.get("ALPACA_API_SECRET", ""))

    # AlphaVantage last — slowest (13s/req rate limit)
    fetch_alphavantage(keys.get("ALPHAVANTAGE_API_KEY", ""))

    # Collect ALL csvs: pre-existing data/ + freshly fetched live_fetched/
    all_csvs = sorted(
        [p for p in DATA_DIR.rglob("*.csv") if p.stat().st_size > 100],
        key=lambda p: p.stat().st_size,
        reverse=True,
    )

    print(f"\n{'='*70}")
    print(f"RUNNING INSTITUTIONAL HARMONIC SUITE")
    print(f"  CSV files found : {len(all_csvs)}")
    print(f"{'='*70}\n")

    from institutional_harmonic_suite import run_engine
    run_engine(all_csvs)

    elapsed = time.time() - t_start
    print(f"\n{'='*70}")
    print(f"DONE  ({elapsed/60:.1f} min)")
    print(f"Best selection written to:")
    print(f"  {ROOT / 'out' / 'execution' / 'institutional_live_selection.json'}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
