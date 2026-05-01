import requests, json, os
import sys
import glob
import pandas as pd
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(__file__))
CFG_PATH = os.path.join(ROOT, "data", "config.json")
OUT = os.path.join(ROOT, "output")

os.makedirs(OUT, exist_ok=True)

def now():
    return datetime.utcnow().strftime("%H:%M:%S")

def safe(x, default=0.0):
    try:
        return float(x)
    except:
        return default

def load_cfg():
    with open(CFG_PATH) as f:
        cfg = json.load(f)
    return cfg if isinstance(cfg, dict) else {}

def api(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        if not isinstance(data, dict):
            print(f"[FALLBACK] API returned non-dict for {url}", file=sys.stderr, flush=True)
            return {}
        if data.get("error"):
            print(f"[FALLBACK] API error for {url}: {data.get('error')}", file=sys.stderr, flush=True)
            return {}
        return data.get("result", {})
    except Exception as e:
        print(f"[FALLBACK] API exception for {url}: {e}", file=sys.stderr, flush=True)
        return {}

def get_pairs():
    data = api("https://api.kraken.com/0/public/AssetPairs")
    out = []
    if data:
        for k,v in data.items():
            if not isinstance(v, dict): continue
            if v.get("quote") != "ZUSD": continue
            if v.get("status") != "online": continue
            out.append(k)
    if not out:
        print("[FALLBACK] No live pairs, falling back to local CSVs", file=sys.stderr, flush=True)
        csvs = glob.glob(os.path.join(ROOT, "clean_data", "kraken_*.csv"))
        for csv in csvs:
            sym = os.path.basename(csv).replace("kraken_","").replace("_daily.csv","").replace(".csv","").upper()
            if sym:
                out.append(sym)
        print(f"[FALLBACK] Local pairs: {out}", file=sys.stderr, flush=True)
    return out

def get_ticker(pairs):
    if not pairs: return {}
    data = api("https://api.kraken.com/0/public/Ticker", {"pair": ",".join(pairs)})
    if data:
        return data
    # fallback: try to load from local CSVs
    print("[FALLBACK] No live ticker, loading from local CSVs", file=sys.stderr, flush=True)
    tickers = {}
    for sym in pairs:
        csv_path = os.path.join(ROOT, "clean_data", f"kraken_{sym.lower()}_daily.csv")
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                last = float(df.iloc[-1][df.columns[-1]]) if not df.empty else 0.0
                vol = df["vol"].iloc[-1] if "vol" in df.columns else 0
                # Calculate 7-day SMA, price change, and volume change for moonshot/trend
                sma7 = float(df.iloc[-7:][df.columns[-1]].mean()) if len(df) >= 7 else None
                pchg7 = (last / float(df.iloc[-7][df.columns[-1]]) - 1) if len(df) >= 7 and float(df.iloc[-7][df.columns[-1]]) > 0 else None
                vchg7 = (vol / float(df["vol"].iloc[-7]) if "vol" in df.columns and len(df) >= 7 and float(df["vol"].iloc[-7]) > 0 else None)
                tickers[sym] = {"c": [last], "a": [last*1.001], "b": [last*0.999], "v": [vol], "sma7": sma7, "pchg7": pchg7, "vchg7": vchg7}
            except Exception as e:
                print(f"[FALLBACK] Failed to load {csv_path}: {e}", file=sys.stderr, flush=True)
    return tickers

def score(t):
    if not isinstance(t, dict): return None

    ask = safe((t.get("a") or [0])[0])
    bid = safe((t.get("b") or [0])[0])
    last = safe((t.get("c") or [0])[0])
    vlist = t.get("v") or [0, 0]
    vol = safe(vlist[1] if len(vlist) > 1 else vlist[0])
    moonshot = False

    if last <= 0 or vol < 50000 or (ask-bid)/last > 0.02:
        return None

    spread = (ask - bid) / last if last else 1
    s = 0.1
    # Sharpe/Return-Optimized scoring
    if spread < 0.005:
        s += 0.5
    elif spread < 0.01:
        s += 0.3
    if vol > 250000:
        s += 0.5
    elif vol > 100000:
        s += 0.3
    if last > 0:
        s += 0.2

    # Trend filter: price above 7-day SMA
    sma7 = t.get("sma7")
    if sma7 is not None and last > sma7:
        s += 0.2

    # Moonshot detection: 7-day price change or volume spike
    pchg7 = t.get("pchg7")
    vchg7 = t.get("vchg7")
    if pchg7 is not None and pchg7 > 0.3:
        s += 0.5
        moonshot = True
    if vchg7 is not None and vchg7 > 2.0:
        s += 0.5
        moonshot = True

    return {
        "price": round(last,6),
        "spread": round(spread,6),
        "vol": vol,
        "score": round(s,3),
        "moonshot": moonshot
    }

def main():
    cfg = load_cfg()
    print(f"[{now()}] START — Robust LumaTrader v2.0", file=sys.stderr, flush=True)
    pairs = get_pairs()
    print(f"[DEBUG] Pairs to scan: {pairs}", file=sys.stderr, flush=True)
    ticker = get_ticker(pairs)
    print(f"[DEBUG] Ticker keys: {list(ticker.keys())}", file=sys.stderr, flush=True)
    results = []
    moonshots = []
    for p in pairs:
        t = ticker.get(p)
        if t is None:
            print(f"[DEBUG] No ticker data for symbol: {p}", file=sys.stderr, flush=True)
            continue
        s = score(t)
        if not s:
            print(f"[DEBUG] Invalid or missing score for symbol: {p} (ticker: {t})", file=sys.stderr, flush=True)
            continue
        s["pair"] = p
        if s.get("moonshot"):
            moonshots.append(s)
        results.append(s)
    results.sort(key=lambda x: x["score"], reverse=True)
    top = results[:cfg.get("top_n",10)]
    out_file = os.path.join(OUT, "signals.txt")
    with open(out_file, "w") as f:
        for r in top:
            f.write(str(r) + "\n")
    print(f"[{now()}] DONE — signals written", file=sys.stderr, flush=True)
    if top:
        print("[TOP]", file=sys.stderr, flush=True)
        for r in top:
            print(r, file=sys.stderr, flush=True)
        print("[BEST]", top[0], file=sys.stderr, flush=True)
    if moonshots:
        print("[MOONSHOTS]", file=sys.stderr, flush=True)
        for m in moonshots:
            print(m, file=sys.stderr, flush=True)

if __name__ == "__main__":
    main()
