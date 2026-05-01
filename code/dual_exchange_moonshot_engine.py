import argparse
import csv
import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from statistics import median
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import requests

UTC_NOW = datetime.now(timezone.utc).isoformat()
OUT_DIR = os.path.join("C:\\LumaTrader\\INSTITUTIONAL_STACK_V2\\code", "out", "execution")
os.makedirs(OUT_DIR, exist_ok=True)

KR_BASE = "https://api.kraken.com/0/public"
BN_BASE = "https://api.binance.us/api/v3"

HORIZONS_MIN = {
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "3h": 180,
    "8h": 480,
    "1d": 1440,
    "1w": 10080,
    "1m": 43200,
}


@dataclass
class Target:
    exchange: str
    symbol: str
    price: float
    turnover_24h_usd: float
    discount_from_high: float
    discount_from_median: float
    quality_score: float
    returns_now_vs_horizon: Dict[str, Optional[float]]


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def quality_score(discount_high: float, discount_med: float, turnover: float) -> float:
    dis_h = clamp(discount_high, 0.0, 1.0)
    dis_m = clamp(discount_med, -0.5, 1.0)
    dis_m_n = (dis_m + 0.5) / 1.5
    liq = clamp(math.log10(max(turnover, 1.0)) / 8.0, 0.0, 1.0)
    return 100.0 * (0.50 * dis_h + 0.20 * dis_m_n + 0.30 * liq)


def kr_get(path: str, params=None):
    r = requests.get(f"{KR_BASE}/{path}", params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("error"):
        raise RuntimeError(str(data["error"]))
    return data["result"]


def bn_get(path: str, params=None):
    r = requests.get(f"{BN_BASE}/{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def kr_tradable_usd_pairs() -> List[str]:
    pairs = kr_get("AssetPairs")
    out = []
    for _, v in pairs.items():
        if v.get("status") != "online":
            continue
        if v.get("quote") not in {"ZUSD", "USD"}:
            continue
        alt = v.get("altname")
        if not alt:
            continue
        out.append(alt)
    return sorted(set(out))


def bn_tradable_usd_pairs() -> List[str]:
    info = bn_get("exchangeInfo")
    out = []
    for s in info.get("symbols", []):
        if s.get("status") != "TRADING":
            continue
        if s.get("quoteAsset") not in {"USD", "USDT", "USDC"}:
            continue
        out.append(s["symbol"])
    return sorted(set(out))


def kr_ticker_all(pairs: List[str]) -> Dict[str, dict]:
    out = {}
    batch = 25
    for i in range(0, len(pairs), batch):
        chunk = pairs[i : i + batch]
        res = kr_get("Ticker", {"pair": ",".join(chunk)})
        out.update(res)
    return out


def kr_price_turnover_map(pairs: List[str]) -> Dict[str, tuple]:
    raw = kr_ticker_all(pairs)
    out = {}
    for key, item in raw.items():
        try:
            price = float(item["c"][0])
            vol = float(item["v"][1])
            symbol = key.replace("/", "")
            out[symbol] = (price, price * vol)
        except Exception:
            continue
    # fallback direct per pair for symbol names that did not map cleanly
    for p in pairs:
        if p in out:
            continue
        try:
            r = kr_get("Ticker", {"pair": p})
            k = next(iter(r.keys()))
            item = r[k]
            price = float(item["c"][0])
            vol = float(item["v"][1])
            out[p] = (price, price * vol)
        except Exception:
            continue
    return out


def bn_price_turnover_map(pairs: List[str]) -> Dict[str, tuple]:
    stats = bn_get("ticker/24hr")
    allowed = set(pairs)
    out = {}
    for x in stats:
        s = x.get("symbol")
        if s not in allowed:
            continue
        try:
            price = float(x["lastPrice"])
            qvol = float(x["quoteVolume"])
            out[s] = (price, qvol)
        except Exception:
            continue
    return out


def kr_daily_series(pair: str, lookback_days: int):
    r = kr_get("OHLC", {"pair": pair, "interval": 1440})
    key = next(k for k in r.keys() if k != "last")
    rows = r[key][-max(lookback_days + 5, 40) :]
    closes = [float(x[4]) for x in rows]
    highs = [float(x[2]) for x in rows]
    return closes, highs


def bn_daily_series(pair: str, lookback_days: int):
    rows = bn_get("klines", {"symbol": pair, "interval": "1d", "limit": max(lookback_days + 5, 40)})
    closes = [float(x[4]) for x in rows]
    highs = [float(x[2]) for x in rows]
    return closes, highs


def kr_recent_closes(pair: str, interval_min: int, limit: int):
    r = kr_get("OHLC", {"pair": pair, "interval": interval_min})
    key = next(k for k in r.keys() if k != "last")
    rows = r[key][-limit:]
    return [float(x[4]) for x in rows]


def bn_recent_closes(pair: str, interval: str, limit: int):
    rows = bn_get("klines", {"symbol": pair, "interval": interval, "limit": limit})
    return [float(x[4]) for x in rows]


def return_from_horizon(closes: List[float], step_min: int, horizon_min: int) -> Optional[float]:
    if len(closes) < 3:
        return None
    steps = math.ceil(horizon_min / step_min)
    if steps >= len(closes):
        return None
    now = closes[-1]
    then = closes[-1 - steps]
    if then <= 0:
        return None
    return (now / then) - 1.0


def horizon_returns(exchange: str, symbol: str) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    try:
        if exchange == "kraken":
            closes_5m = kr_recent_closes(symbol, 5, 1000)
            closes_1h = kr_recent_closes(symbol, 60, 1000)
        else:
            closes_5m = bn_recent_closes(symbol, "5m", 1000)
            closes_1h = bn_recent_closes(symbol, "1h", 1000)

        for label, mins in HORIZONS_MIN.items():
            if mins <= 30:
                out[label] = return_from_horizon(closes_5m, 5, mins)
            else:
                out[label] = return_from_horizon(closes_1h, 60, mins)
    except Exception:
        for label in HORIZONS_MIN:
            out[label] = None
    return out


def scan_exchange(exchange: str, min_turnover_usd: float, lookback_days: int, discount_threshold: float, max_targets: int):
    if exchange == "kraken":
        pairs = kr_tradable_usd_pairs()
        pt = kr_price_turnover_map(pairs)
        get_daily = kr_daily_series
    else:
        pairs = bn_tradable_usd_pairs()
        pt = bn_price_turnover_map(pairs)
        get_daily = bn_daily_series

    scanned = 0
    targets: List[Target] = []

    liquid = [(s, p, t) for s, (p, t) in pt.items() if t >= min_turnover_usd]
    liquid.sort(key=lambda x: x[2], reverse=True)

    for symbol, price, turnover in liquid:
        scanned += 1
        try:
            closes, highs = get_daily(symbol, lookback_days)
            if len(closes) < 30 or len(highs) < 30:
                continue
            high_ref = max(highs)
            med_ref = median(closes)
            if high_ref <= 0 or med_ref <= 0:
                continue
            d_high = 1.0 - (price / high_ref)
            d_med = 1.0 - (price / med_ref)
            score = quality_score(d_high, d_med, turnover)

            if d_high < discount_threshold:
                continue

            rets = horizon_returns(exchange, symbol)
            targets.append(
                Target(
                    exchange=exchange,
                    symbol=symbol,
                    price=price,
                    turnover_24h_usd=turnover,
                    discount_from_high=d_high,
                    discount_from_median=d_med,
                    quality_score=score,
                    returns_now_vs_horizon=rets,
                )
            )
        except Exception:
            continue

    targets.sort(key=lambda t: (t.quality_score, t.discount_from_high, t.turnover_24h_usd), reverse=True)
    return {
        "exchange": exchange,
        "tradable_pairs": len(pairs),
        "liquid_pairs_scanned": scanned,
        "targets": targets[:max_targets],
    }


def update_memory(targets: List[Target], path: str):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            mem = json.load(f)
    else:
        mem = {"created_utc": UTC_NOW, "symbols": {}}

    symbols = mem.setdefault("symbols", {})
    for t in targets:
        key = f"{t.exchange}:{t.symbol}"
        if key not in symbols:
            symbols[key] = {
                "exchange": t.exchange,
                "symbol": t.symbol,
                "first_seen_utc": UTC_NOW,
                "last_seen_utc": UTC_NOW,
                "hits": 1,
                "best_quality": t.quality_score,
                "best_discount_from_high": t.discount_from_high,
            }
        else:
            row = symbols[key]
            row["last_seen_utc"] = UTC_NOW
            row["hits"] = int(row.get("hits", 0)) + 1
            row["best_quality"] = max(float(row.get("best_quality", 0.0)), t.quality_score)
            row["best_discount_from_high"] = max(
                float(row.get("best_discount_from_high", 0.0)), t.discount_from_high
            )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(mem, f, indent=2)


def write_targets_csv(targets: List[Target], path: str):
    fields = [
        "exchange",
        "symbol",
        "price",
        "turnover_24h_usd",
        "discount_from_high",
        "discount_from_median",
        "quality_score",
    ] + [f"ret_{k}" for k in HORIZONS_MIN.keys()]

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for t in targets:
            row = {
                "exchange": t.exchange,
                "symbol": t.symbol,
                "price": f"{t.price:.8f}",
                "turnover_24h_usd": f"{t.turnover_24h_usd:.2f}",
                "discount_from_high": f"{t.discount_from_high:.4f}",
                "discount_from_median": f"{t.discount_from_median:.4f}",
                "quality_score": f"{t.quality_score:.2f}",
            }
            for k in HORIZONS_MIN:
                v = t.returns_now_vs_horizon.get(k)
                row[f"ret_{k}"] = "" if v is None else f"{v:.5f}"
            w.writerow(row)


def plot_chart(scan_kr, scan_bn, targets: List[Target], out_png: str):
    ex_names = ["kraken", "binanceus"]
    counts = [len(scan_kr["targets"]), len(scan_bn["targets"])]

    avg_q = []
    for ex in ex_names:
        vals = [t.quality_score for t in targets if t.exchange == ex]
        avg_q.append(sum(vals) / len(vals) if vals else 0.0)

    horizon_labels = list(HORIZONS_MIN.keys())
    med_rows = []
    for ex in ex_names:
        row = []
        ex_targets = [t for t in targets if t.exchange == ex]
        for h in horizon_labels:
            vals = [t.returns_now_vs_horizon[h] for t in ex_targets if t.returns_now_vs_horizon[h] is not None]
            row.append((median(vals) * 100.0) if vals else 0.0)
        med_rows.append(row)

    fig = plt.figure(figsize=(13, 8))
    gs = fig.add_gridspec(2, 2)

    ax1 = fig.add_subplot(gs[0, 0])
    ax1.bar(ex_names, counts)
    ax1.set_title("Target Count (Dislocation Qualified)")
    ax1.set_ylabel("count")

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.bar(ex_names, avg_q)
    ax2.set_title("Average Quality Score")
    ax2.set_ylabel("score")

    ax3 = fig.add_subplot(gs[1, :])
    im = ax3.imshow(med_rows, aspect="auto")
    ax3.set_xticks(range(len(horizon_labels)))
    ax3.set_xticklabels(horizon_labels)
    ax3.set_yticks(range(len(ex_names)))
    ax3.set_yticklabels(ex_names)
    ax3.set_title("Median Return % vs Horizon (Current Target Set)")
    fig.colorbar(im, ax=ax3, shrink=0.8)

    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-turnover-usd", type=float, default=200000.0)
    ap.add_argument("--discount-threshold", type=float, default=0.60)
    ap.add_argument("--kr-min-turnover-usd", type=float, default=None)
    ap.add_argument("--bn-min-turnover-usd", type=float, default=None)
    ap.add_argument("--kr-discount-threshold", type=float, default=None)
    ap.add_argument("--bn-discount-threshold", type=float, default=None)
    ap.add_argument("--lookback-days", type=int, default=180)
    ap.add_argument("--max-targets-per-exchange", type=int, default=40)
    args = ap.parse_args()

    kr_min_turnover = args.kr_min_turnover_usd if args.kr_min_turnover_usd is not None else args.min_turnover_usd
    bn_min_turnover = args.bn_min_turnover_usd if args.bn_min_turnover_usd is not None else args.min_turnover_usd
    kr_discount = (
        args.kr_discount_threshold if args.kr_discount_threshold is not None else args.discount_threshold
    )
    bn_discount = (
        args.bn_discount_threshold if args.bn_discount_threshold is not None else args.discount_threshold
    )

    scan_kr = scan_exchange(
        "kraken",
        min_turnover_usd=kr_min_turnover,
        lookback_days=args.lookback_days,
        discount_threshold=kr_discount,
        max_targets=args.max_targets_per_exchange,
    )
    scan_bn = scan_exchange(
        "binanceus",
        min_turnover_usd=bn_min_turnover,
        lookback_days=args.lookback_days,
        discount_threshold=bn_discount,
        max_targets=args.max_targets_per_exchange,
    )

    targets = scan_kr["targets"] + scan_bn["targets"]

    latest = {
        "generated_utc": UTC_NOW,
        "params": vars(args),
        "effective_profile": {
            "kraken": {
                "min_turnover_usd": kr_min_turnover,
                "discount_threshold": kr_discount,
            },
            "binanceus": {
                "min_turnover_usd": bn_min_turnover,
                "discount_threshold": bn_discount,
            },
        },
        "kraken": {
            "tradable_pairs": scan_kr["tradable_pairs"],
            "liquid_pairs_scanned": scan_kr["liquid_pairs_scanned"],
            "target_count": len(scan_kr["targets"]),
            "top_targets": [asdict(t) for t in scan_kr["targets"][:15]],
        },
        "binanceus": {
            "tradable_pairs": scan_bn["tradable_pairs"],
            "liquid_pairs_scanned": scan_bn["liquid_pairs_scanned"],
            "target_count": len(scan_bn["targets"]),
            "top_targets": [asdict(t) for t in scan_bn["targets"][:15]],
        },
        "total_targets": len(targets),
    }

    latest_path = os.path.join(OUT_DIR, "moonshot_dual_scan_latest.json")
    csv_path = os.path.join(OUT_DIR, "moonshot_dual_targets.csv")
    memory_path = os.path.join(OUT_DIR, "high_potential_symbol_memory.json")
    chart_path = os.path.join(OUT_DIR, "moonshot_dual_scan_chart.png")
    history_path = os.path.join(OUT_DIR, "moonshot_dual_scan_history.jsonl")

    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(latest, f, indent=2)

    write_targets_csv(targets, csv_path)
    update_memory(targets, memory_path)
    plot_chart(scan_kr, scan_bn, targets, chart_path)

    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(latest) + "\n")

    print("SCAN_DONE")
    print(f"kraken_profile=min_turnover:{kr_min_turnover} discount:{kr_discount}")
    print(f"binanceus_profile=min_turnover:{bn_min_turnover} discount:{bn_discount}")
    print(f"kraken_targets={len(scan_kr['targets'])} scanned={scan_kr['liquid_pairs_scanned']} tradable={scan_kr['tradable_pairs']}")
    print(f"binanceus_targets={len(scan_bn['targets'])} scanned={scan_bn['liquid_pairs_scanned']} tradable={scan_bn['tradable_pairs']}")
    print(f"total_targets={len(targets)}")
    print(f"latest_json={latest_path}")
    print(f"targets_csv={csv_path}")
    print(f"memory_json={memory_path}")
    print(f"chart_png={chart_path}")


if __name__ == "__main__":
    main()
