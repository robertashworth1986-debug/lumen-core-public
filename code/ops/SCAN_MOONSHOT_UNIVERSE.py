"""
SCAN_MOONSHOT_UNIVERSE.py
─────────────────────────────────────────────────────────────────────────────
Scans Kraken's live ticker universe for moonshot candidates:
 - Low-price tokens ($0.0001 - $5.00)
 - High 24h range (volatility = opportunity)
 - Positive price momentum (already moving up)
 - Sufficient volume (can fill orders)
 - Low spread (entry cost controlled)

Outputs:
  out/ops/moonshot_candidates.json   — full ranked list
  out/ops/moonshot_watchlist.json    — top 15 for executor priority injection
  out/ops/moonshot_scan_report.md    — human-readable summary

Run standalone or called from RUN_MOONSHOT_SCAN.ps1
"""

import json
import pathlib
import sys
import time
import datetime
import urllib.request
import urllib.error

# ── Paths ───────────────────────────────────────────────────────────────────
REPO_ROOT   = pathlib.Path(__file__).resolve().parent.parent.parent
OUT_DIR     = REPO_ROOT / "out" / "ops"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CANDIDATES_FILE  = OUT_DIR / "moonshot_candidates.json"
WATCHLIST_FILE   = OUT_DIR / "moonshot_watchlist.json"
REPORT_FILE      = OUT_DIR / "moonshot_scan_report.md"

# ── Config ───────────────────────────────────────────────────────────────────
PRICE_MIN        = 0.000001   # floor — dust tokens excluded below this
PRICE_MAX        = 5.00       # ceiling — want small tokens with room to 10x+
VOLUME_MIN_USD   = 25_000     # 24h volume floor — need liquidity to fill
SPREAD_MAX_BPS   = 60         # max bid-ask spread allowed
RANGE_MIN_PCT    = 8.0        # min 24h high/low range %  (volatile = opportunity)
MOMENTUM_MIN     = -99.0      # 24h price change — allow negatives for reversal plays
TOP_N_WATCH      = 20         # watchlist size

# BADGER reference profile (the known moonshot template)
BADGER_REF = {
    "price_usd": 0.41,
    "pnl_pct":   26.3,
    "hold_sec":  30,
    "gate":      1.0,
}


def _get(url: str, timeout: int = 8):
    req = urllib.request.Request(url, headers={"User-Agent": "LumaTrader/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def fetch_kraken_tickers():
    """Pull all USD spot pairs from Kraken public ticker endpoint."""
    print("[scan] fetching Kraken asset pairs…")
    pairs_data = _get("https://api.kraken.com/0/public/AssetPairs")
    if pairs_data.get("error"):
        raise RuntimeError(f"AssetPairs error: {pairs_data['error']}")

    usd_pairs = [
        k for k, v in pairs_data["result"].items()
        if v.get("quote") in ("ZUSD", "USD")
        and v.get("status") == "online"
        and not k.endswith(".d")   # skip dark-pool pairs
    ]
    print(f"[scan] {len(usd_pairs)} live USD pairs found")
    return usd_pairs, pairs_data["result"]


def fetch_tickers_bulk(pairs: list[str]) -> dict:
    """Fetch ticker info for all pairs in chunks."""
    results = {}
    chunk_size = 100
    chunks = [pairs[i:i+chunk_size] for i in range(0, len(pairs), chunk_size)]
    for i, chunk in enumerate(chunks):
        query = ",".join(chunk)
        try:
            data = _get(f"https://api.kraken.com/0/public/Ticker?pair={query}")
            if not data.get("error") or data["error"] == []:
                results.update(data.get("result", {}))
        except Exception as e:
            print(f"[scan] chunk {i+1} error: {e}")
        if i < len(chunks) - 1:
            time.sleep(0.3)
    return results


def score_candidate(pair_name: str, tk: dict, pair_meta: dict) -> dict | None:
    """Score a single ticker. Returns None if it doesn't pass filters."""
    try:
        ask   = float(tk["a"][0])
        bid   = float(tk["b"][0])
        last  = float(tk["c"][0])
        high  = float(tk["h"][1])   # 24h high
        low   = float(tk["l"][1])   # 24h low
        vol   = float(tk["v"][1])   # 24h volume in base asset
        open_ = float(tk["o"])      # 24h open
        vwap  = float(tk["p"][1])   # 24h VWAP
    except (KeyError, IndexError, ValueError):
        return None

    if last <= 0 or bid <= 0:
        return None

    # Price filter
    if not (PRICE_MIN <= last <= PRICE_MAX):
        return None

    # Volume in USD
    vol_usd = vol * vwap
    if vol_usd < VOLUME_MIN_USD:
        return None

    # Spread
    spread_bps = (ask - bid) / max(bid, 1e-12) * 10000
    if spread_bps > SPREAD_MAX_BPS:
        return None

    # 24h range
    if low <= 0:
        return None
    range_pct = (high - low) / low * 100.0
    if range_pct < RANGE_MIN_PCT:
        return None

    # 24h momentum (last vs open)
    momentum_pct = (last - open_) / max(open_, 1e-12) * 100.0
    if momentum_pct < MOMENTUM_MIN:
        return None

    # Position within 24h range (0=at low, 1=at high)
    range_position = (last - low) / max(high - low, 1e-12)

    # Moonshot score formula:
    # Higher score = bigger range, higher position in range, lower price, more volume
    range_score      = min(range_pct / 100.0, 3.0)              # cap at 300% range
    position_score   = range_position                             # 0-1 where in range
    price_score      = max(0, 1.0 - (last / PRICE_MAX))          # cheaper = higher score
    volume_score     = min(vol_usd / 1_000_000, 2.0)             # cap at 2M volume
    momentum_score   = max(0, momentum_pct / 100.0)              # positive momentum bonus

    moonshot_score = (
        range_score      * 3.0 +
        position_score   * 2.0 +
        price_score      * 1.5 +
        volume_score     * 1.0 +
        momentum_score   * 2.5
    )

    # Extract base symbol
    meta = pair_meta.get(pair_name, {})
    base = meta.get("base", pair_name.replace("USD", "").replace("ZUSD", ""))

    return {
        "pair":           pair_name,
        "symbol":         base,
        "price_usd":      round(last, 8),
        "bid":            round(bid, 8),
        "ask":            round(ask, 8),
        "spread_bps":     round(spread_bps, 2),
        "high_24h":       round(high, 8),
        "low_24h":        round(low, 8),
        "range_24h_pct":  round(range_pct, 2),
        "range_position": round(range_position, 4),
        "volume_usd_24h": round(vol_usd, 0),
        "momentum_pct":   round(momentum_pct, 4),
        "moonshot_score": round(moonshot_score, 4),
        "potential_5x":   round(last * 5, 8),
        "potential_10x":  round(last * 10, 8),
        "potential_100x": round(last * 100, 8),
    }


def run_scan():
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[scan] moonshot universe scan — {ts}")

    # Fetch pairs
    pairs, pair_meta = fetch_kraken_tickers()

    # Fetch all tickers
    print("[scan] fetching live ticker data…")
    raw_tickers = fetch_tickers_bulk(pairs)
    print(f"[scan] {len(raw_tickers)} tickers received")

    # Score all
    candidates = []
    for pair_name, tk in raw_tickers.items():
        result = score_candidate(pair_name, tk, pair_meta)
        if result:
            candidates.append(result)

    candidates.sort(key=lambda x: -x["moonshot_score"])
    print(f"[scan] {len(candidates)} candidates passed filters")

    # Save full list
    payload = {
        "generated_utc": ts,
        "total_candidates": len(candidates),
        "filters": {
            "price_min": PRICE_MIN,
            "price_max": PRICE_MAX,
            "volume_min_usd": VOLUME_MIN_USD,
            "spread_max_bps": SPREAD_MAX_BPS,
            "range_min_pct": RANGE_MIN_PCT,
        },
        "candidates": candidates,
    }
    CANDIDATES_FILE.write_text(json.dumps(payload, indent=2))

    # Watchlist — top N
    watchlist_symbols = [c["symbol"] for c in candidates[:TOP_N_WATCH]]
    watchlist = {
        "generated_utc": ts,
        "watchlist": watchlist_symbols,
        "top_candidates": candidates[:TOP_N_WATCH],
        "instruction": "Executor should prioritize entries on these symbols when gate_score >= 0.7",
    }
    WATCHLIST_FILE.write_text(json.dumps(watchlist, indent=2))

    # Human report
    lines = [
        f"# Moonshot Universe Scan — {ts}",
        "",
        f"**Passed filters:** {len(candidates)} symbols",
        f"**Watchlist size:** {TOP_N_WATCH}",
        "",
        "## Top 20 Moonshot Candidates",
        "",
        "| # | Symbol | Price | Range24h% | Position | Vol24h(USD) | Momentum% | Score | 10x Target |",
        "|---|--------|-------|-----------|----------|-------------|-----------|-------|------------|",
    ]
    for i, c in enumerate(candidates[:20], 1):
        lines.append(
            f"| {i} | **{c['symbol']}** | ${c['price_usd']} | {c['range_24h_pct']}% | "
            f"{c['range_position']*100:.0f}% | ${c['volume_usd_24h']:,.0f} | "
            f"{c['momentum_pct']:+.2f}% | {c['moonshot_score']:.2f} | ${c['potential_10x']} |"
        )

    lines += [
        "",
        "## BADGER Reference Profile (known moonshot template)",
        f"- Price: ${BADGER_REF['price_usd']} | Gain: +{BADGER_REF['pnl_pct']}% in {BADGER_REF['hold_sec']}s",
        "",
        "## Scanner Logic",
        "- `moonshot_score = range*3 + position*2 + cheap_price*1.5 + volume*1 + momentum*2.5`",
        "- High score = big 24h range, near 24h high, cheap price, strong positive momentum",
        "",
        f"*Generated: {ts}*",
    ]
    REPORT_FILE.write_text("\n".join(lines))

    # Print top 10 to console
    print("\n=== TOP 10 MOONSHOT CANDIDATES ===")
    print(f"{'#':<3} {'Symbol':<10} {'Price':>10} {'Range%':>8} {'Pos%':>6} {'Vol$':>12} {'Mom%':>8} {'Score':>7}")
    print("-" * 70)
    for i, c in enumerate(candidates[:10], 1):
        print(f"{i:<3} {c['symbol']:<10} ${c['price_usd']:>9.6f} {c['range_24h_pct']:>7.1f}% "
              f"{c['range_position']*100:>5.0f}% ${c['volume_usd_24h']:>10,.0f} "
              f"{c['momentum_pct']:>+7.2f}% {c['moonshot_score']:>6.2f}")

    print(f"\n[scan] watchlist written → {WATCHLIST_FILE}")
    print(f"[scan] full report → {REPORT_FILE}")
    return candidates


if __name__ == "__main__":
    run_scan()
