"""ANALYZE_TRADER_BLEED.py
Snapshot the live executor's recent buys/sells and compute realized P&L by
pair from Kraken TXIDs. Reports holding times, win/loss counts, biggest
losers, and a "bleed cause" diagnosis.

Read-only. No live runtime side effects.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
EXEC_LOG = ROOT / "execution_events.jsonl"
OUT_DIR = ROOT / "out" / "ops" / "trader_bleed_snapshot"
OUT_DIR.mkdir(parents=True, exist_ok=True)

KRAKEN_TRADES = ROOT / "kraken_trades_history.json"  # optional


def load_events():
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


def load_kraken_fills():
    """Optional: real Kraken fills (price + cost) keyed by txid."""
    fills = {}
    if KRAKEN_TRADES.exists():
        try:
            data = json.loads(KRAKEN_TRADES.read_text(encoding="utf-8"))
            trades = data.get("trades") or data.get("result", {}).get("trades") or {}
            for tid, t in trades.items():
                otxid = t.get("ordertxid") or tid
                fills.setdefault(otxid, []).append(t)
        except Exception:
            pass
    return fills


def fifo_pair_pnl(events, fills):
    """FIFO match buys with sells per pair using volume; price from fills if
    available, else None. Returns per-pair stats."""
    by_pair = defaultdict(list)
    for e in events:
        if e.get("event") != "submit_order":
            continue
        if e.get("validate"):
            continue  # paper/preflight
        txids = e.get("txid") or []
        if not txids:
            continue
        side = e.get("side")
        pair = e.get("pair")
        try:
            vol = float(e.get("volume") or 0.0)
        except Exception:
            vol = 0.0
        if vol <= 0 or side not in ("buy", "sell"):
            continue
        # Try to extract real fill price/cost
        price, cost = None, None
        for tx in txids:
            for fill in fills.get(tx, []):
                try:
                    p = float(fill.get("price"))
                    c = float(fill.get("cost"))
                    price = p
                    cost = c
                except Exception:
                    pass
        by_pair[pair].append({
            "ts": e.get("ts"),
            "side": side,
            "volume": vol,
            "txid": txids[0] if txids else None,
            "price": price,
            "cost": cost,
        })

    results = {}
    for pair, fills_list in by_pair.items():
        fills_list.sort(key=lambda x: x.get("ts") or "")
        buys = deque()
        realized = 0.0
        roundtrips = []
        for f in fills_list:
            if f["side"] == "buy":
                buys.append(f)
            else:
                qty_left = f["volume"]
                while qty_left > 1e-12 and buys:
                    b = buys[0]
                    take = min(qty_left, b["volume"])
                    if b.get("price") is not None and f.get("price") is not None:
                        pnl = (f["price"] - b["price"]) * take
                        realized += pnl
                        roundtrips.append({
                            "pair": pair,
                            "buy_ts": b["ts"],
                            "sell_ts": f["ts"],
                            "qty": take,
                            "buy_px": b["price"],
                            "sell_px": f["price"],
                            "pnl_usd": pnl,
                        })
                    b["volume"] -= take
                    qty_left -= take
                    if b["volume"] <= 1e-12:
                        buys.popleft()
        results[pair] = {
            "n_orders": len(fills_list),
            "realized_pnl_usd": realized,
            "open_buys_qty": sum(b["volume"] for b in buys),
            "roundtrips": roundtrips,
        }
    return results


def summarize(events):
    n_buy = n_sell = n_validate = 0
    pair_counts = defaultdict(lambda: {"buy": 0, "sell": 0})
    first_ts = last_ts = None
    for e in events:
        if e.get("event") != "submit_order":
            continue
        ts = e.get("ts")
        if ts:
            first_ts = ts if first_ts is None or ts < first_ts else first_ts
            last_ts = ts if last_ts is None or ts > last_ts else last_ts
        if e.get("validate"):
            n_validate += 1
            continue
        if e.get("side") == "buy":
            n_buy += 1
        elif e.get("side") == "sell":
            n_sell += 1
        pair_counts[e.get("pair")][e.get("side")] += 1
    return {
        "n_live_buys": n_buy,
        "n_live_sells": n_sell,
        "n_validate_only": n_validate,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "pairs_traded": len(pair_counts),
        "pair_counts": dict(pair_counts),
    }


def diagnose(summary, pair_results):
    findings = []
    closed = [p for p, r in pair_results.items() if r["roundtrips"]]
    open_only = [p for p, r in pair_results.items() if r["open_buys_qty"] > 0 and not r["roundtrips"]]
    losers = sorted(
        ((p, r["realized_pnl_usd"]) for p, r in pair_results.items() if r["roundtrips"]),
        key=lambda x: x[1],
    )
    winners = sorted(
        ((p, r["realized_pnl_usd"]) for p, r in pair_results.items() if r["roundtrips"]),
        key=lambda x: x[1], reverse=True,
    )
    pair_counts = summary.get("pair_counts") or {}
    sells_no_buys = [p for p, c in pair_counts.items() if c["sell"] > 0 and c["buy"] == 0]
    buys_no_sells = [p for p, c in pair_counts.items() if c["buy"] > 0 and c["sell"] == 0]

    if sells_no_buys:
        findings.append({
            "severity": "high",
            "issue": "sells with no recorded buys",
            "detail": (
                "These pairs sold without a matching prior buy in the log "
                "(positions opened before this log started, or buy logging gap)."
            ),
            "pairs": sells_no_buys,
            "fix": "Reconstruct cost basis from Kraken trades history before next sell, "
                   "or pin sells to flatten-only mode for these pairs.",
        })
    if buys_no_sells and len(buys_no_sells) >= 5:
        findings.append({
            "severity": "high",
            "issue": "many buys with no sells (basket bleed)",
            "detail": (
                f"{len(buys_no_sells)} pairs opened and never closed. "
                "Drift / fees / spread quietly drain capital while held."
            ),
            "pairs": buys_no_sells[:20],
            "fix": "Enforce a max-open-positions cap and force a flatten cycle for "
                   "pairs older than max-hold; or block new buys until open count drops.",
        })
    if losers:
        findings.append({
            "severity": "med",
            "issue": "biggest realized losers",
            "pairs_pnl": losers[:10],
            "fix": "Add per-pair stop-loss and a daily loss cutoff in live_executor.py.",
        })
    if not pair_results:
        findings.append({
            "severity": "info",
            "issue": "no roundtrips computable",
            "detail": "Kraken fill prices not joined; PnL is qualitative only. "
                      "Drop kraken_trades_history.json next to execution log for $ PnL.",
        })
    return {
        "n_pairs_with_roundtrips": len(closed),
        "n_pairs_open_only": len(open_only),
        "biggest_losers_top10": losers[:10],
        "biggest_winners_top10": winners[:10],
        "open_only_pairs": open_only,
        "findings": findings,
    }


def main():
    events = load_events()
    fills = load_kraken_fills()
    summary = summarize(events)
    pair_results = fifo_pair_pnl(events, fills)
    diag = diagnose(summary, pair_results)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snap = {
        "generated_utc": stamp,
        "exec_log": str(EXEC_LOG),
        "summary": summary,
        "diagnosis": diag,
        "pair_results_compact": {
            p: {
                "n_orders": r["n_orders"],
                "realized_pnl_usd": r["realized_pnl_usd"],
                "open_buys_qty": r["open_buys_qty"],
                "n_roundtrips": len(r["roundtrips"]),
            } for p, r in pair_results.items()
        },
    }
    out_json = OUT_DIR / f"trader_bleed_snapshot_{stamp}.json"
    out_json.write_text(json.dumps(snap, indent=2, default=str), encoding="utf-8")
    latest = OUT_DIR / "trader_bleed_snapshot_latest.json"
    latest.write_text(json.dumps(snap, indent=2, default=str), encoding="utf-8")

    # Human-readable
    lines = []
    lines.append(f"# Trader Bleed Snapshot — {stamp}")
    lines.append("")
    lines.append(f"- exec log: `{EXEC_LOG}`")
    lines.append(f"- live buys: **{summary['n_live_buys']}**, "
                 f"live sells: **{summary['n_live_sells']}**, "
                 f"validate-only: {summary['n_validate_only']}")
    lines.append(f"- pairs touched: {summary['pairs_traded']}")
    lines.append(f"- window: {summary['first_ts']} → {summary['last_ts']}")
    lines.append("")
    lines.append("## Findings")
    for f in diag["findings"]:
        lines.append(f"### [{f['severity'].upper()}] {f['issue']}")
        if f.get("detail"):
            lines.append(f["detail"])
        if f.get("pairs"):
            lines.append("- pairs: " + ", ".join(f["pairs"][:25]))
        if f.get("pairs_pnl"):
            for p, v in f["pairs_pnl"]:
                lines.append(f"  - {p}: ${v:,.2f}")
        if f.get("fix"):
            lines.append(f"- **fix:** {f['fix']}")
        lines.append("")
    lines.append("## Open-only pairs (positions held, never closed in log)")
    for p in diag["open_only_pairs"]:
        lines.append(f"- {p} (qty {pair_results[p]['open_buys_qty']:.6f})")

    out_md = OUT_DIR / f"trader_bleed_snapshot_{stamp}.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")
    (OUT_DIR / "trader_bleed_snapshot_latest.md").write_text(
        "\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "snapshot_md": str(out_md),
        "snapshot_json": str(out_json),
        "n_findings": len(diag["findings"]),
        "summary": summary,
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
