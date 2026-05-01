import argparse
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List

import requests

BASE = "https://api.kraken.com/0/public"


@dataclass
class Candidate:
    pair: str
    price: float
    usd_turnover_24h: float
    max_high_lookback: float
    median_close_lookback: float
    discount_from_high: float
    discount_from_median: float


def kraken_get(path: str, params=None):
    r = requests.get(f"{BASE}/{path}", params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("error"):
        raise RuntimeError(str(data["error"]))
    return data["result"]


def load_usd_pairs() -> List[str]:
    pairs = kraken_get("AssetPairs")
    selected = []
    for _k, v in pairs.items():
        quote = v.get("quote", "")
        status = v.get("status", "")
        wsname = v.get("wsname", "")
        altname = v.get("altname", "")

        if status != "online":
            continue
        if quote not in {"ZUSD", "USD"}:
            continue
        # Ignore dark pool / derivative suffixes for this scan.
        if ".d" in altname or ".d" in wsname:
            continue
        selected.append(altname)
    return sorted(set(selected))


def load_ticker_snapshot(pairs: List[str]):
    result = {}
    batch = 20
    for i in range(0, len(pairs), batch):
        chunk = pairs[i : i + batch]
        r = kraken_get("Ticker", {"pair": ",".join(chunk)})
        result.update(r)
        time.sleep(0.25)
    return result


def parse_price_and_turnover(ticker_item):
    # c[0] = last trade closed price
    # v[1] = volume past 24h in base asset
    price = float(ticker_item["c"][0])
    vol_24h = float(ticker_item["v"][1])
    turnover = price * vol_24h
    return price, turnover


def load_ohlc(pair: str, days: int):
    since = int((datetime.now(timezone.utc) - timedelta(days=days + 2)).timestamp())
    r = kraken_get("OHLC", {"pair": pair, "interval": 1440, "since": since})
    key = next(k for k in r.keys() if k != "last")
    rows = r[key]
    # [time, open, high, low, close, vwap, volume, count]
    closes = [float(x[4]) for x in rows if len(x) >= 5]
    highs = [float(x[2]) for x in rows if len(x) >= 3]
    return closes, highs


def scan(min_turnover_usd: float, lookback_days: int, top_liquid: int):
    pairs = load_usd_pairs()
    ticker = load_ticker_snapshot(pairs)

    liquid = []
    for _k, item in ticker.items():
        try:
            price, turnover = parse_price_and_turnover(item)
            pair = item.get("wsname", "") or _k
            pair = pair.replace("/", "")
            liquid.append((pair, price, turnover))
        except Exception:
            continue

    liquid = [x for x in liquid if x[2] >= min_turnover_usd]
    liquid.sort(key=lambda x: x[2], reverse=True)
    liquid = liquid[:top_liquid]

    out: List[Candidate] = []
    for pair, price, turnover in liquid:
        try:
            closes, highs = load_ohlc(pair, lookback_days)
            if len(closes) < 30 or not highs:
                continue
            max_high = max(highs)
            med_close = statistics.median(closes)
            if max_high <= 0 or med_close <= 0:
                continue
            d_high = 1.0 - (price / max_high)
            d_med = 1.0 - (price / med_close)
            out.append(
                Candidate(
                    pair=pair,
                    price=price,
                    usd_turnover_24h=turnover,
                    max_high_lookback=max_high,
                    median_close_lookback=med_close,
                    discount_from_high=d_high,
                    discount_from_median=d_med,
                )
            )
        except Exception:
            continue
        time.sleep(0.2)

    # "moonshot dislocation" ranking: deep discount + still liquid
    out.sort(key=lambda c: (c.discount_from_high, c.discount_from_median, c.usd_turnover_24h), reverse=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-turnover-usd", type=float, default=250000.0)
    ap.add_argument("--lookback-days", type=int, default=180)
    ap.add_argument("--top-liquid", type=int, default=80)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--min-discount", type=float, default=0.50)
    args = ap.parse_args()

    rows = scan(
        min_turnover_usd=args.min_turnover_usd,
        lookback_days=args.lookback_days,
        top_liquid=args.top_liquid,
    )

    rows = [r for r in rows if r.discount_from_high >= args.min_discount]
    rows = rows[: args.limit]

    print("pair,price,turnover_24h_usd,max_high,median_close,discount_from_high,discount_from_median")
    for r in rows:
        print(
            f"{r.pair},{r.price:.8f},{r.usd_turnover_24h:,.0f},{r.max_high_lookback:.8f},{r.median_close_lookback:.8f},{r.discount_from_high:.3f},{r.discount_from_median:.3f}"
        )


if __name__ == "__main__":
    main()
