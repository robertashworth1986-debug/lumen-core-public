"""
UNIVERSE FETCHER — pulls hourly OHLC for EVERY Kraken USD pair.
- Discovers all USD-quoted pairs via /0/public/AssetPairs
- Concurrent fetches (8 workers) with rate-limit backoff
- Caches everything to out/backtest/ohlc_universe.pkl
- Resumable: skips pairs already cached
"""
from __future__ import annotations
import sys, os, time, json, pickle, traceback
from pathlib import Path
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "backtest"
OUT.mkdir(parents=True, exist_ok=True)
CACHE = OUT / "ohlc_universe.pkl"
PARTIAL = OUT / "ohlc_universe.partial.pkl"

KRAKEN_PAIRS = "https://api.kraken.com/0/public/AssetPairs"
KRAKEN_OHLC  = "https://api.kraken.com/0/public/OHLC"

def get_usd_pairs() -> list[str]:
    req = urllib.request.Request(KRAKEN_PAIRS, headers={"User-Agent":"luma-univ/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    res = data.get("result", {})
    out = []
    for k, v in res.items():
        quote = v.get("quote", "")
        # USD-quoted pairs (ZUSD or USD), exclude perp/dark/index
        if quote in ("ZUSD","USD") and v.get("status") == "online":
            # use the altname or wsname or k itself; fallback to k
            out.append(k)
    return sorted(set(out))

def fetch_ohlc(pair: str, interval: int = 60, retries: int = 3) -> tuple[str, pd.DataFrame | None]:
    for attempt in range(retries):
        try:
            url = f"{KRAKEN_OHLC}?pair={pair}&interval={interval}"
            req = urllib.request.Request(url, headers={"User-Agent":"luma-univ/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode("utf-8"))
            if data.get("error"):
                err = " ".join(data["error"])
                if "Rate limit" in err or "Too many" in err:
                    time.sleep(3 + attempt*2); continue
                return pair, None
            result = data.get("result", {})
            key = next((k for k in result.keys() if k != "last"), None)
            if not key: return pair, None
            rows = result[key]
            if len(rows) < 100: return pair, None
            df = pd.DataFrame(rows, columns=["t","o","h","l","c","vwap","v","trades"])
            df["c"] = df["c"].astype(float)
            df["v"] = df["v"].astype(float)
            df["t"] = pd.to_datetime(df["t"].astype(int), unit="s")
            df = df.set_index("t").sort_index()
            return pair, df
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(5 + attempt*3); continue
            return pair, None
        except Exception:
            time.sleep(1 + attempt); continue
    return pair, None

def save(cache_dict):
    with open(PARTIAL, "wb") as f: pickle.dump(cache_dict, f)
    PARTIAL.replace(CACHE)

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.time()
    # load existing cache to resume
    existing = {}
    if CACHE.exists():
        try:
            with open(CACHE, "rb") as f: existing = pickle.load(f)
            print(f"[UNIV] Loaded {len(existing)} pairs from cache.")
        except Exception: pass
    print("[UNIV] Discovering USD pairs...")
    pairs = get_usd_pairs()
    print(f"[UNIV] Discovered {len(pairs)} USD pairs from Kraken.")
    todo = [p for p in pairs if p not in existing]
    print(f"[UNIV] {len(todo)} new pairs to fetch.")
    if not todo:
        print(f"[UNIV] Cache complete: {len(existing)} pairs."); return

    # Kraken public limit: ~15-20 calls in burst then 1/s sustained.
    # Use 6 threads, sleep 0.2s between submits. Save every 25 fetches.
    cache = dict(existing)
    completed = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {}
        for i, p in enumerate(todo):
            futures[ex.submit(fetch_ohlc, p, 60)] = p
            time.sleep(0.18)
        for fut in as_completed(futures):
            pair = futures[fut]
            try:
                _, df = fut.result()
            except Exception:
                df = None
            if df is not None and len(df) >= 100:
                cache[pair] = df
            completed += 1
            if completed % 25 == 0:
                save(cache)
                el = time.time()-t0
                print(f"[UNIV] {completed}/{len(todo)} done | cached={len(cache)} | {el:.0f}s elapsed")
    save(cache)
    print(f"[UNIV] DONE. Total cached: {len(cache)} | took {time.time()-t0:.1f}s")
    # quick stats
    if cache:
        bars = [len(df) for df in cache.values()]
        print(f"[UNIV] bars per pair: min={min(bars)} median={sorted(bars)[len(bars)//2]} max={max(bars)}")

if __name__ == "__main__":
    main()
