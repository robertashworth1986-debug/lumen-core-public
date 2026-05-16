from __future__ import annotations
import os, json, time, math
from pathlib import Path
from datetime import datetime, timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import numpy as np
import pandas as pd
import yaml

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CFG = yaml.safe_load((ROOT / "config" / "live_hydrator.yaml").read_text(encoding="utf-8"))
CORP = ROOT / "corpus_market"
OUT  = ROOT / "out" / "execution"
TRADER_LANE = "trader_alpha_execution"
TRADER_OUT = OUT / "trader_alpha_lane"
LOG  = ROOT / "logs"
for p in [CORP, OUT, TRADER_OUT, LOG]:
    p.mkdir(parents=True, exist_ok=True)

PROTECTED_SECTOR_PROOF_PATHS = [
    ROOT / "out" / "sector_value_matrix.json",
    ROOT / "out" / "source_truth_table.json",
    ROOT / "out" / "frozen_delta_ledger.jsonl",
    ROOT / "out" / "infra_frozen_deltas.jsonl",
]

TOP_N = int(CFG.get("top_n", 200))
MIN_ROWS = int(CFG.get("min_rows", 150))
COST_BPS = float(CFG.get("cost_bps", 10))
KRAKEN_OHLC_INTERVAL = int(CFG.get("poll_kraken_ohlc_interval", 60))
BINANCEUS_KLINE_INTERVAL = str(CFG.get("binanceus_kline_interval", "1h"))
REQUEST_TIMEOUT_SEC = float(CFG.get("request_timeout_sec", 30))
HTTP_RETRY_TOTAL = int(CFG.get("http_retry_total", 4))
HTTP_RETRY_BACKOFF_SEC = float(CFG.get("http_retry_backoff_sec", 0.5))
PROGRESS_EVERY = int(CFG.get("progress_every", 100))

MAX_KRAKEN_SYMBOLS = int(os.getenv("LUMA_MAX_KRAKEN_SYMBOLS", CFG.get("max_kraken_symbols", 0) or 0))
MAX_BINANCEUS_SYMBOLS = int(os.getenv("LUMA_MAX_BINANCEUS_SYMBOLS", CFG.get("max_binanceus_symbols", 0) or 0))

_retry = Retry(
    total=HTTP_RETRY_TOTAL,
    read=HTTP_RETRY_TOTAL,
    connect=HTTP_RETRY_TOTAL,
    backoff_factor=HTTP_RETRY_BACKOFF_SEC,
    status_forcelist=[408, 429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True,
    raise_on_status=False,
)
SESSION = requests.Session()
_adapter = HTTPAdapter(max_retries=_retry, pool_connections=64, pool_maxsize=64)
SESSION.mount("https://", _adapter)
SESSION.mount("http://", _adapter)

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def log(msg: str):
    line = f"[{utc_now()}] {msg}"
    print(line)
    with open(LOG / "all_symbol_hydrator.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get_json(url, params=None, headers=None, timeout=None):
    timeout = REQUEST_TIMEOUT_SEC if timeout is None else timeout
    r = SESSION.get(url, params=params, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()

def _normalized(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").lower()

def assert_lane_boundary(write_paths: list[Path]):
    protected = {_normalized(p) for p in PROTECTED_SECTOR_PROOF_PATHS}
    for p in write_paths:
        if _normalized(p) in protected:
            raise RuntimeError(f"lane boundary violation: attempted write to protected sector/frozen proof path: {p}")

# ------------------------
# Symbol discovery
# ------------------------
def fetch_kraken_pairs():
    j = get_json("https://api.kraken.com/0/public/AssetPairs")
    res = j.get("result", {})
    rows = []
    for pair_key, rec in res.items():
        alt = rec.get("altname", pair_key)
        ws = rec.get("wsname", "")
        status = rec.get("status", "")
        base = rec.get("base", "")
        quote = rec.get("quote", "")
        if status and status not in ("online", "cancel_only", "post_only", "limit_only", "reduce_only"):
            continue
        rows.append({
            "exchange": "kraken",
            "pair_key": pair_key,
            "symbol": alt,
            "wsname": ws,
            "base": base,
            "quote": quote,
            "status": status
        })
    df = pd.DataFrame(rows).sort_values("symbol").reset_index(drop=True)
    if MAX_KRAKEN_SYMBOLS > 0:
        df = df.head(MAX_KRAKEN_SYMBOLS).reset_index(drop=True)
    df.to_csv(TRADER_OUT / "kraken_pairs_registry.csv", index=False)
    df.to_csv(OUT / "kraken_pairs_registry.csv", index=False)
    return df

def fetch_binanceus_symbols():
    j = get_json("https://api.binance.us/api/v3/exchangeInfo")
    syms = j.get("symbols", [])
    rows = []
    for rec in syms:
        if rec.get("status") != "TRADING":
            continue
        rows.append({
            "exchange": "binanceus",
            "symbol": rec.get("symbol"),
            "base": rec.get("baseAsset"),
            "quote": rec.get("quoteAsset"),
            "status": rec.get("status")
        })
    df = pd.DataFrame(rows).sort_values("symbol").reset_index(drop=True)
    if MAX_BINANCEUS_SYMBOLS > 0:
        df = df.head(MAX_BINANCEUS_SYMBOLS).reset_index(drop=True)
    df.to_csv(TRADER_OUT / "binanceus_symbols_registry.csv", index=False)
    df.to_csv(OUT / "binanceus_symbols_registry.csv", index=False)
    return df

# ------------------------
# Market data hydration
# ------------------------
def fetch_kraken_ohlc(symbol: str):
    try:
        j = get_json("https://api.kraken.com/0/public/OHLC", params={"pair": symbol, "interval": KRAKEN_OHLC_INTERVAL})
        res = j.get("result", {})
        key = next((k for k in res.keys() if k != "last"), None)
        if not key:
            return None
        rows = res.get(key, [])
        if not rows:
            return None
        df = pd.DataFrame(rows, columns=["time","open","high","low","close","vwap","volume","count"])
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        for c in ["open","high","low","close","vwap","volume","count"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["exchange"] = "kraken"
        df["symbol"] = symbol
        return df
    except Exception as e:
        log(f"kraken OHLC fail {symbol}: {e}")
        return None

def fetch_binanceus_klines(symbol: str):
    try:
        j = get_json("https://api.binance.us/api/v3/klines", params={"symbol": symbol, "interval": BINANCEUS_KLINE_INTERVAL, "limit": 1000})
        if not j:
            return None
        df = pd.DataFrame(j, columns=[
            "open_time","open","high","low","close","volume",
            "close_time","quote_asset_volume","num_trades",
            "taker_buy_base","taker_buy_quote","ignore"
        ])
        df["time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        for c in ["open","high","low","close","volume","quote_asset_volume","num_trades","taker_buy_base","taker_buy_quote"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["exchange"] = "binanceus"
        df["symbol"] = symbol
        return df[["time","open","high","low","close","volume","num_trades","exchange","symbol"]].copy()
    except Exception as e:
        log(f"binanceus klines fail {symbol}: {e}")
        return None

# ------------------------
# Validation / scoring
# ------------------------
def perf_stats(returns: pd.Series):
    x = pd.Series(returns).replace([np.inf,-np.inf], np.nan).dropna()
    if len(x) < 20:
        return {"sharpe": np.nan, "max_dd": np.nan, "final": np.nan}
    eq = (1 + x).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    mean = x.mean()
    std = x.std()
    sharpe = float((mean / std) * np.sqrt(252)) if std and np.isfinite(std) and std > 0 else np.nan
    final = float(eq.iloc[-1])
    return {"sharpe": sharpe, "max_dd": float(dd), "final": final}

def run_suite(df: pd.DataFrame):
    d = df.sort_values("time").copy()
    d["ret1"] = d["close"].pct_change().fillna(0.0)
    d["ma20"] = d["close"].rolling(20).mean()
    d["ma50"] = d["close"].rolling(50).mean()
    d["std20"] = d["close"].rolling(20).std()
    d["z20"] = (d["close"] - d["ma20"]) / d["std20"].replace(0, np.nan)

    strategies = {}

    # trend
    sig = np.where(d["ma20"] > d["ma50"], 1, -1)
    strat = pd.Series(sig, index=d.index).shift(1).fillna(0) * d["ret1"]
    turn_cost = pd.Series(sig, index=d.index).diff().abs().fillna(0) * (COST_BPS/10000.0)
    strategies["trend"] = perf_stats(strat - turn_cost)

    # regime switch
    sig = np.where(d["z20"] > 0.75, 1, np.where(d["z20"] < -0.75, -1, 0))
    strat = pd.Series(sig, index=d.index).shift(1).fillna(0) * d["ret1"]
    turn_cost = pd.Series(sig, index=d.index).diff().abs().fillna(0) * (COST_BPS/10000.0)
    strategies["regime_switch"] = perf_stats(strat - turn_cost)

    # breakout
    hh = d["high"].rolling(20).max().shift(1)
    ll = d["low"].rolling(20).min().shift(1)
    sig = np.where(d["close"] > hh, 1, np.where(d["close"] < ll, -1, 0))
    strat = pd.Series(sig, index=d.index).shift(1).fillna(0) * d["ret1"]
    turn_cost = pd.Series(sig, index=d.index).diff().abs().fillna(0) * (COST_BPS/10000.0)
    strategies["breakout"] = perf_stats(strat - turn_cost)

    # hybrid
    sig = np.where((d["ma20"] > d["ma50"]) & (d["z20"] > 0), 1,
                   np.where((d["ma20"] < d["ma50"]) & (d["z20"] < 0), -1, 0))
    strat = pd.Series(sig, index=d.index).shift(1).fillna(0) * d["ret1"]
    turn_cost = pd.Series(sig, index=d.index).diff().abs().fillna(0) * (COST_BPS/10000.0)
    strategies["hybrid"] = perf_stats(strat - turn_cost)

    # buy-hold baseline
    buyhold = perf_stats(d["ret1"])
    return strategies, buyhold

def suspicious_flag(sharpe, max_dd, final, rows):
    if not np.isfinite(sharpe): return True
    if rows < MIN_ROWS: return True
    if sharpe > 8 and final > 10: return True
    if max_dd > -0.01 and sharpe > 4 and rows < 400: return True
    return False

# ------------------------
# Main
# ------------------------
def main():
    log("discovering symbols")
    log(
        f"http tuning timeout={REQUEST_TIMEOUT_SEC}s retries={HTTP_RETRY_TOTAL} backoff={HTTP_RETRY_BACKOFF_SEC}s "
        f"cap_kraken={MAX_KRAKEN_SYMBOLS} cap_binanceus={MAX_BINANCEUS_SYMBOLS}"
    )
    kraken_df = fetch_kraken_pairs()
    binance_df = fetch_binanceus_symbols()

    all_ranked = []
    champion_rows = []

    # Kraken
    log(f"kraken symbols: {len(kraken_df)}")
    for idx, r in kraken_df.iterrows():
        sym = str(r["symbol"])
        df = fetch_kraken_ohlc(sym)
        if df is None or len(df) < MIN_ROWS:
            continue
        df.to_csv(CORP / f"{sym}.csv", index=False)
        suites, bh = run_suite(df)
        for strat, st in suites.items():
            sharpe = st["sharpe"]
            max_dd = st["max_dd"]
            final = st["final"]
            vs_bh = (final / bh["final"]) if (np.isfinite(final) and np.isfinite(bh["final"]) and bh["final"] not in (0, np.nan)) else np.nan
            suspicious = suspicious_flag(sharpe, max_dd, final, len(df))
            validation_score = float((0 if np.isnan(sharpe) else max(sharpe,0))*8 + max(0, vs_bh if np.isfinite(vs_bh) else 0)*10 + (1 + max_dd)*5)
            all_ranked.append({
                "pair": sym,
                "exchange": "kraken",
                "strategy": strat,
                "sharpe": sharpe,
                "max_dd": max_dd,
                "final": final,
                "vs_buyhold": vs_bh,
                "suspicious": suspicious,
                "validation_score": validation_score,
                "rows": int(len(df))
            })
        if PROGRESS_EVERY > 0 and (idx + 1) % PROGRESS_EVERY == 0:
            log(f"kraken progress {idx + 1}/{len(kraken_df)} symbols")

    # Binance.US
    log(f"binanceus symbols: {len(binance_df)}")
    for idx, r in binance_df.iterrows():
        sym = str(r["symbol"])
        df = fetch_binanceus_klines(sym)
        if df is None or len(df) < MIN_ROWS:
            continue
        df.to_csv(CORP / f"{sym}.csv", index=False)
        suites, bh = run_suite(df)
        for strat, st in suites.items():
            sharpe = st["sharpe"]
            max_dd = st["max_dd"]
            final = st["final"]
            vs_bh = (final / bh["final"]) if (np.isfinite(final) and np.isfinite(bh["final"]) and bh["final"] not in (0, np.nan)) else np.nan
            suspicious = suspicious_flag(sharpe, max_dd, final, len(df))
            validation_score = float((0 if np.isnan(sharpe) else max(sharpe,0))*8 + max(0, vs_bh if np.isfinite(vs_bh) else 0)*10 + (1 + max_dd)*5)
            all_ranked.append({
                "pair": sym,
                "exchange": "binanceus",
                "strategy": strat,
                "sharpe": sharpe,
                "max_dd": max_dd,
                "final": final,
                "vs_buyhold": vs_bh,
                "suspicious": suspicious,
                "validation_score": validation_score,
                "rows": int(len(df))
            })
        if PROGRESS_EVERY > 0 and (idx + 1) % PROGRESS_EVERY == 0:
            log(f"binanceus progress {idx + 1}/{len(binance_df)} symbols")

    ranked = pd.DataFrame(all_ranked)
    if len(ranked) == 0:
        log("no ranked rows")
        return

    ranked["consistency_score"] = ranked["validation_score"] / (1 + ranked["suspicious"].astype(int))
    ranked["gen_all_score"] = ranked["consistency_score"]
    ranked["data_domain"] = TRADER_LANE
    ranked = ranked.sort_values(["suspicious","validation_score","sharpe"], ascending=[True,False,False]).reset_index(drop=True)

    lane_gen_all = TRADER_OUT / "gen_all_ranked_trader_alpha.csv"
    lane_topn = TRADER_OUT / "institutional_topn_trader_alpha.csv"
    lane_champion = TRADER_OUT / "gen_champion_trader_alpha.json"
    lane_summary = TRADER_OUT / "live_key_routing_summary_trader_alpha.json"
    lane_matrix = TRADER_OUT / "trader_exchange_strategy_matrix.csv"
    lane_filtered = TRADER_OUT / "filtered_proof_trader_alpha.json"
    lane_manifest = TRADER_OUT / "lane_boundary_manifest.json"

    legacy_gen_all = OUT / "gen_all_ranked.csv"
    legacy_topn = OUT / "institutional_topn.csv"
    legacy_champion = OUT / "gen_champion.json"
    legacy_summary = OUT / "live_key_routing_summary.json"
    legacy_filtered = OUT / "filtered_proof.json"
    legacy_trader_matrix = OUT / "trader_exchange_strategy_matrix.csv"

    planned_writes = [
        lane_gen_all,
        lane_topn,
        lane_champion,
        lane_summary,
        lane_matrix,
        lane_filtered,
        lane_manifest,
        legacy_gen_all,
        legacy_topn,
        legacy_champion,
        legacy_summary,
        legacy_filtered,
        legacy_trader_matrix,
    ]
    assert_lane_boundary(planned_writes)

    ranked.to_csv(lane_gen_all, index=False)
    ranked.to_csv(legacy_gen_all, index=False)
    ranked.head(TOP_N).to_csv(lane_topn, index=False)
    ranked.head(TOP_N).to_csv(legacy_topn, index=False)

    # best non-suspicious champion
    filt = ranked[ranked["suspicious"] == False].copy()
    if len(filt) == 0:
        filt = ranked.copy()
    champ = filt.iloc[0].to_dict()
    champ["data_domain"] = TRADER_LANE
    lane_champion.write_text(json.dumps(champ, indent=2), encoding="utf-8")
    legacy_champion.write_text(json.dumps(champ, indent=2), encoding="utf-8")

    # summaries
    live_key_routing_summary = {
        "utc": utc_now(),
        "kraken_pairs_discovered": int(len(kraken_df)),
        "binanceus_symbols_discovered": int(len(binance_df)),
        "request_timeout_sec": REQUEST_TIMEOUT_SEC,
        "http_retry_total": HTTP_RETRY_TOTAL,
        "http_retry_backoff_sec": HTTP_RETRY_BACKOFF_SEC,
        "data_domain": TRADER_LANE,
        "lane_output_root": str(TRADER_OUT),
        "market_files_written": int(len(list(CORP.glob("*.csv")))),
        "ranked_rows": int(len(ranked)),
        "top_pair": champ.get("pair"),
        "top_exchange": champ.get("exchange"),
        "top_strategy": champ.get("strategy")
    }
    lane_summary.write_text(json.dumps(live_key_routing_summary, indent=2), encoding="utf-8")
    legacy_summary.write_text(json.dumps(live_key_routing_summary, indent=2), encoding="utf-8")

    trader_exchange_strategy_matrix = ranked.groupby(["exchange","strategy"]).agg(
        mean_sharpe=("sharpe","mean"),
        mean_validation_score=("validation_score","mean"),
        count=("pair","count")
    ).reset_index()
    trader_exchange_strategy_matrix.insert(0, "data_domain", TRADER_LANE)
    trader_exchange_strategy_matrix.to_csv(lane_matrix, index=False)
    trader_exchange_strategy_matrix.to_csv(legacy_trader_matrix, index=False)

    filtered_proof = ranked[(ranked["suspicious"] == False) & (ranked["rows"] >= MIN_ROWS)].head(50)
    lane_filtered.write_text(filtered_proof.to_json(orient="records", indent=2), encoding="utf-8")
    legacy_filtered.write_text(filtered_proof.to_json(orient="records", indent=2), encoding="utf-8")

    legacy_collision = OUT / "sector_value_matrix.csv"
    if legacy_collision.exists():
        log(f"lane guard: legacy {legacy_collision.name} exists and is intentionally not updated by trader alpha run")

    lane_manifest_payload = {
        "generated_utc": utc_now(),
        "lane": TRADER_LANE,
        "lane_output_root": str(TRADER_OUT),
        "protected_sector_proof_paths": [str(p) for p in PROTECTED_SECTOR_PROOF_PATHS],
        "writes": [str(p) for p in planned_writes],
        "notes": [
            "Trader alpha run is isolated from frozen delta and sector-proof canonical paths.",
            "Legacy trader compatibility outputs under out/execution remain enabled.",
            "Deprecated ambiguous file name sector_value_matrix.csv is not updated by this script.",
        ],
    }
    lane_manifest.write_text(json.dumps(lane_manifest_payload, indent=2), encoding="utf-8")

    log("done")
    print(str(lane_gen_all))
    print(str(lane_champion))
    print(str(lane_summary))
    print(str(lane_matrix))
    print(str(lane_filtered))
    print(str(lane_manifest))

if __name__ == "__main__":
    main()
