"""LEARN_FROM_TRADE_HISTORY.py
Learn from the user's actual trading history and emit:
  - per-pair behavior stats (hold time, win/loss, approx PnL via public OHLC)
  - hour-of-day UTC bias
  - learned runtime overrides the executor & approval guard can use:
      blacklist_pairs, preferred_pairs, min_hold_seconds, max_hold_seconds,
      blocked_hour_window_utc, recommended_max_open_positions
  - a human-readable markdown summary

Read-only against execution_events.jsonl. Hits Kraken PUBLIC OHLC only (no
keys, no private endpoints). Does not submit any orders.
"""
from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
EXEC_LOG = ROOT / "execution_events.jsonl"
OUT_DIR = ROOT / "out" / "ops" / "trader_learnings"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PUBLIC_OHLC = "https://api.kraken.com/0/public/OHLC"


def _http_json(url: str, timeout: float = 10.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "LumaTrader/learn"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="ignore"))


def load_events() -> list[dict]:
    rows = []
    if not EXEC_LOG.exists():
        return rows
    with EXEC_LOG.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def parse_iso(ts: str) -> float:
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


def fetch_close_at(pair: str, epoch: float, _cache: dict = {}) -> float | None:
    """Return Kraken 1-minute close at the bar containing `epoch`."""
    key = (pair, int(epoch // 60))
    if key in _cache:
        return _cache[key]
    since = int(epoch) - 120  # one bar before
    url = f"{PUBLIC_OHLC}?pair={urllib.parse.quote(pair)}&interval=1&since={since}"
    try:
        data = _http_json(url)
        if data.get("error"):
            _cache[key] = None
            return None
        result = data.get("result") or {}
        # result has one key = pair name (with prefixes), and "last"
        bars = []
        for k, v in result.items():
            if k == "last":
                continue
            bars = v
            break
        if not bars:
            _cache[key] = None
            return None
        # find bar whose start <= epoch < start+60
        target = None
        for bar in bars:
            try:
                start = int(bar[0])
            except Exception:
                continue
            if start <= epoch < start + 60:
                target = bar
                break
        if target is None and bars:
            target = bars[-1]
        if target is not None:
            try:
                close = float(target[4])
                _cache[key] = close
                return close
            except Exception:
                pass
    except Exception:
        pass
    _cache[key] = None
    return None


def fifo_match(events: list[dict]) -> list[dict]:
    """Pair each live (validate=False) sell with the earliest matching buy on
    that pair using FIFO. Returns roundtrips with timestamps and qty."""
    by_pair: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        if e.get("event") != "submit_order" or e.get("validate"):
            continue
        side = str(e.get("side") or "").lower()
        pair = str(e.get("pair") or "").upper()
        try:
            vol = float(e.get("volume") or 0.0)
        except Exception:
            vol = 0.0
        if vol <= 0 or side not in ("buy", "sell") or not pair:
            continue
        by_pair[pair].append({
            "ts": e.get("ts"),
            "epoch": parse_iso(e.get("ts") or ""),
            "side": side,
            "volume": vol,
            "txid": (e.get("txid") or [None])[0],
        })
    roundtrips: list[dict] = []
    for pair, fills in by_pair.items():
        fills.sort(key=lambda x: x["epoch"])
        buys: deque = deque()
        for f in fills:
            if f["side"] == "buy":
                buys.append(dict(f))
            else:
                qty_left = f["volume"]
                while qty_left > 1e-12 and buys:
                    b = buys[0]
                    take = min(qty_left, b["volume"])
                    roundtrips.append({
                        "pair": pair,
                        "buy_ts": b["ts"],
                        "sell_ts": f["ts"],
                        "buy_epoch": b["epoch"],
                        "sell_epoch": f["epoch"],
                        "qty": take,
                        "hold_seconds": max(0.0, f["epoch"] - b["epoch"]),
                        "buy_hour_utc": datetime.fromtimestamp(b["epoch"], tz=timezone.utc).hour if b["epoch"] else None,
                        "sell_hour_utc": datetime.fromtimestamp(f["epoch"], tz=timezone.utc).hour if f["epoch"] else None,
                    })
                    b["volume"] -= take
                    qty_left -= take
                    if b["volume"] <= 1e-12:
                        buys.popleft()
    return roundtrips


def enrich_with_prices(roundtrips: list[dict]) -> None:
    for r in roundtrips:
        bp = fetch_close_at(r["pair"], r["buy_epoch"])
        sp = fetch_close_at(r["pair"], r["sell_epoch"])
        time.sleep(0.4)  # gentle on Kraken public rate limit
        r["buy_px"] = bp
        r["sell_px"] = sp
        if bp and sp and bp > 0:
            r["pnl_pct"] = (sp - bp) / bp * 100.0
            r["pnl_usd_approx"] = (sp - bp) * r["qty"]
        else:
            r["pnl_pct"] = None
            r["pnl_usd_approx"] = None


def stats(values: list[float]) -> dict:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    if not vals:
        return {"n": 0}
    vals_sorted = sorted(vals)
    n = len(vals_sorted)
    mid = n // 2
    median = (vals_sorted[mid] if n % 2 else (vals_sorted[mid - 1] + vals_sorted[mid]) / 2)
    mean = sum(vals_sorted) / n
    return {
        "n": n,
        "mean": mean,
        "median": median,
        "min": vals_sorted[0],
        "max": vals_sorted[-1],
        "wins": sum(1 for v in vals_sorted if v > 0),
        "losses": sum(1 for v in vals_sorted if v < 0),
    }


def derive_learnings(roundtrips: list[dict]) -> dict:
    by_pair: dict[str, list[float]] = defaultdict(list)
    by_hour: dict[int, list[float]] = defaultdict(list)
    by_hold_band: dict[str, list[float]] = defaultdict(list)
    holds: list[float] = []
    for r in roundtrips:
        pnl = r.get("pnl_pct")
        if pnl is None:
            continue
        by_pair[r["pair"]].append(pnl)
        if r["buy_hour_utc"] is not None:
            by_hour[r["buy_hour_utc"]].append(pnl)
        h = r.get("hold_seconds") or 0.0
        holds.append(h)
        if h < 300:
            band = "lt_5min"
        elif h < 1800:
            band = "5_to_30min"
        elif h < 3600:
            band = "30_to_60min"
        elif h < 14400:
            band = "1_to_4h"
        elif h < 86400:
            band = "4_to_24h"
        else:
            band = "gt_24h"
        by_hold_band[band].append(pnl)

    pair_stats = {p: stats(v) for p, v in by_pair.items()}
    hour_stats = {h: stats(v) for h, v in by_hour.items()}
    hold_stats = {b: stats(v) for b, v in by_hold_band.items()}

    losers = sorted(
        ((p, s.get("mean", 0.0), s.get("n", 0))
         for p, s in pair_stats.items() if s.get("n", 0) > 0),
        key=lambda x: x[1],
    )
    winners = sorted(
        ((p, s.get("mean", 0.0), s.get("n", 0))
         for p, s in pair_stats.items() if s.get("n", 0) > 0),
        key=lambda x: x[1], reverse=True,
    )
    bad_hours = [h for h, s in hour_stats.items()
                 if s.get("n", 0) >= 2 and s.get("mean", 0.0) <= -0.5]

    blacklist = [p for p, m, n in losers if n >= 1 and m <= -0.75][:25]
    preferred = [p for p, m, n in winners if n >= 1 and m >= 0.75][:25]

    holds_sorted = sorted(holds) if holds else [0.0]
    p25 = holds_sorted[max(0, int(0.25 * len(holds_sorted)) - 1)]
    p75 = holds_sorted[min(len(holds_sorted) - 1, int(0.75 * len(holds_sorted)))]

    overrides = {
        "blacklist_pairs": blacklist,
        "preferred_pairs": preferred,
        "blocked_hours_utc": sorted(bad_hours),
        "min_hold_seconds": int(max(60, p25)),
        "max_hold_seconds": int(max(p75, 600)),
        "recommended_max_open_positions": 3 if len(preferred) < 5 else 5,
    }
    return {
        "n_roundtrips": len(roundtrips),
        "pair_stats": pair_stats,
        "hour_stats": hour_stats,
        "hold_stats": hold_stats,
        "biggest_losers": losers[:10],
        "biggest_winners": winners[:10],
        "runtime_overrides": overrides,
    }


def main():
    events = load_events()
    rts = fifo_match(events)
    print(f"[learn] events={len(events)}  roundtrips={len(rts)}")
    enrich_with_prices(rts)
    learn = derive_learnings(rts)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "generated_utc": stamp,
        "exec_log": str(EXEC_LOG),
        "n_roundtrips": learn["n_roundtrips"],
        "n_roundtrips_with_prices": sum(1 for r in rts if r.get("pnl_pct") is not None),
        "learn": learn,
        "roundtrips": rts,
    }
    (OUT_DIR / f"learnings_{stamp}.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8")
    (OUT_DIR / "learnings_latest.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8")
    (OUT_DIR / "learned_runtime_overrides.json").write_text(
        json.dumps(learn["runtime_overrides"], indent=2), encoding="utf-8")

    lines = [f"# Trader Learnings — {stamp}", ""]
    lines.append(f"- roundtrips: **{learn['n_roundtrips']}** "
                 f"(priced: {payload['n_roundtrips_with_prices']})")
    o = learn["runtime_overrides"]
    lines.append("")
    lines.append("## Recommended runtime overrides")
    lines.append(f"- **blacklist_pairs**: {', '.join(o['blacklist_pairs']) or '(none)'}")
    lines.append(f"- **preferred_pairs**: {', '.join(o['preferred_pairs']) or '(none)'}")
    lines.append(f"- **blocked_hours_utc**: {o['blocked_hours_utc'] or '(none)'}")
    lines.append(f"- **min_hold_seconds**: {o['min_hold_seconds']}  "
                 f"**max_hold_seconds**: {o['max_hold_seconds']}")
    lines.append(f"- **recommended_max_open_positions**: {o['recommended_max_open_positions']}")
    lines.append("")
    lines.append("## Biggest losers (mean pnl% per roundtrip)")
    for p, m, n in learn["biggest_losers"]:
        lines.append(f"- {p}: mean {m:+.2f}%  (n={n})")
    lines.append("")
    lines.append("## Biggest winners (mean pnl% per roundtrip)")
    for p, m, n in learn["biggest_winners"]:
        lines.append(f"- {p}: mean {m:+.2f}%  (n={n})")
    lines.append("")
    lines.append("## Hour-of-day (UTC) — buy hour bias")
    for h in sorted(learn["hour_stats"].keys()):
        s = learn["hour_stats"][h]
        if s.get("n"):
            lines.append(f"- {h:02d}:00Z  n={s['n']}  mean {s['mean']:+.2f}%  "
                         f"wins/losses {s['wins']}/{s['losses']}")
    lines.append("")
    lines.append("## Hold-time bands")
    for band, s in learn["hold_stats"].items():
        if s.get("n"):
            lines.append(f"- {band}: n={s['n']}  mean {s['mean']:+.2f}%  "
                         f"wins/losses {s['wins']}/{s['losses']}")

    md = "\n".join(lines)
    (OUT_DIR / f"learnings_{stamp}.md").write_text(md, encoding="utf-8")
    (OUT_DIR / "learnings_latest.md").write_text(md, encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "n_roundtrips": learn["n_roundtrips"],
        "n_priced": payload["n_roundtrips_with_prices"],
        "learnings_md": str(OUT_DIR / "learnings_latest.md"),
        "overrides_json": str(OUT_DIR / "learned_runtime_overrides.json"),
    }, indent=2))


if __name__ == "__main__":
    main()
