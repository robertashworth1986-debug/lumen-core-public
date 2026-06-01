"""BUILD_INVESTOR_ONE_PAGER.py

Single, shareable investor artifact for handheld viewing in a meeting.
Pulls latest:
  - frozen_delta_truth_chain_latest.json (anchored metrics + entry SHA)
  - infra_frozen_deltas.jsonl (multi-asset signal totals)
  - grant_submit_now SUBMIT_NOW.json (active grant lanes + bundle SHAs)
  - grant_evidence_packs EVIDENCE_INDEX_latest.json (per-ticket bundle status)

Emits:
  out/ops/investor_one_pager/INVESTOR_ONE_PAGER.md
  out/ops/investor_one_pager/INVESTOR_ONE_PAGER.json
  out/ops/investor_one_pager/INVESTOR_ONE_PAGER.html  (printable / phone-friendly)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
OUT_OPS = OUT / "ops"

TRUTH_CHAIN = OUT_OPS / "frozen_delta_truth_chain" / "frozen_delta_truth_chain_latest.json"
INFRA_DELTAS = OUT / "infra_frozen_deltas.jsonl"
SUBMIT_NOW = OUT_OPS / "grant_submit_now" / "SUBMIT_NOW.json"
EVIDENCE_INDEX = OUT_OPS / "grant_evidence_packs" / "EVIDENCE_INDEX_latest.json"
MEMO = ROOT / "evidence" / "agency_alignment_memo.md"

DEST = OUT_OPS / "investor_one_pager"


def _load_json(p: Path) -> dict:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def _fmt_usd(x) -> str:
    try:
        return f"${float(x):,.0f}"
    except Exception:
        return str(x)


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)

    chain = _load_json(TRUTH_CHAIN)
    metrics = chain.get("metrics", {}) if chain else {}
    deltas = _load_jsonl(INFRA_DELTAS)

    # Per-sector latest
    by_key: dict[str, dict] = {}
    for r in deltas:
        k = f"{r.get('sector','')}|{r.get('source','')}"
        prior = by_key.get(k)
        if prior is None or str(r.get("generated_utc", "")) >= str(prior.get("generated_utc", "")):
            by_key[k] = r
    by_sector = sorted(
        by_key.values(),
        key=lambda r: float(r.get("estimated_hourly_value_usd") or 0.0),
        reverse=True,
    )
    total_hourly = sum(float(r.get("estimated_hourly_value_usd") or 0.0) for r in by_sector)
    total_avoided = sum(float(r.get("estimated_avoided_loss_usd") or 0.0) for r in by_sector)
    sectors = sorted({r.get("sector", "") for r in by_sector if r.get("sector")})

    submit = _load_json(SUBMIT_NOW)
    evidence = _load_json(EVIDENCE_INDEX)
    actionable = submit.get("actionable", []) if isinstance(submit, dict) else []
    evidence_results = evidence.get("results", []) if isinstance(evidence, dict) else []
    by_tid = {r.get("ticket_id"): r for r in evidence_results}

    payload = {
        "schema": "lumen.investor_one_pager/v1",
        "generated_utc": now.isoformat(),
        "truth_chain": {
            "run_tag": chain.get("run_tag"),
            "entry_sha256": chain.get("entry_sha256"),
            "previous_entry_sha256": chain.get("previous_entry_sha256"),
            "generated_utc": chain.get("generated_utc"),
        },
        "headline_metrics": {
            "annual_value_signal_usd": metrics.get("annual_value_signal_usd"),
            "valuation_proxy_usd": metrics.get("valuation_proxy_usd"),
            "router_edge_pct": metrics.get("router_edge_pct"),
            "harmonic_win_rate_pct": metrics.get("harmonic_win_rate_pct"),
            "benchmark_prevented_pct": metrics.get("benchmark_prevented_pct"),
            "measured_coverage_pct": metrics.get("measured_coverage_pct"),
            "measured_sources": metrics.get("measured_sources"),
            "enabled_sources": metrics.get("enabled_sources"),
            "top_sector": metrics.get("top_sector"),
            "top_sector_hourly_value_usd": metrics.get("top_sector_hourly_value_usd"),
            "grants_queue_total": metrics.get("grants_queue_total"),
            "public_truth_status": metrics.get("public_truth_status"),
        },
        "multi_asset_signal": {
            "rows": len(deltas),
            "sector_source_keys": len(by_key),
            "sectors": sectors,
            "total_hourly_value_usd": round(total_hourly, 2),
            "total_avoided_loss_usd": round(total_avoided, 2),
            "top10_per_sector": by_sector[:10],
        },
        "active_grant_lanes": [
            {
                "ticket_id": a.get("ticket_id"),
                "title": a.get("title"),
                "agency_match": (by_tid.get(a.get("ticket_id")) or {}).get("memo_label"),
                "freshness": ((by_tid.get(a.get("ticket_id")) or {}).get("freshness") or {}).get("state"),
                "bundle_sha256": (by_tid.get(a.get("ticket_id")) or {}).get("bundle_sha256"),
                "days_left": a.get("days_left"),
                "submit_url": a.get("submit_url"),
            }
            for a in actionable
        ],
    }

    # Markdown
    md = []
    md.append("# LumenCore™ — Investor One-Pager")
    md.append("")
    md.append(f"**As of (UTC):** {now.isoformat(timespec='seconds')}")
    if chain:
        md.append(f"**Truth-chain anchor SHA:** `{chain.get('entry_sha256','')}`")
        md.append(f"**Previous anchor SHA:** `{chain.get('previous_entry_sha256','')}`")
    md.append("")
    md.append("## Headline Metrics (anchored)")
    md.append("")
    hm = payload["headline_metrics"]
    md.append(f"- **Annual value signal:** {_fmt_usd(hm.get('annual_value_signal_usd'))}")
    md.append(f"- **Valuation proxy:** {_fmt_usd(hm.get('valuation_proxy_usd'))}")
    md.append(f"- **Router edge:** {hm.get('router_edge_pct','—')}%  |  **Harmonic win rate:** {hm.get('harmonic_win_rate_pct','—')}%")
    md.append(f"- **Benchmark prevented:** {hm.get('benchmark_prevented_pct','—')}%  |  **Measured coverage:** {hm.get('measured_coverage_pct','—')}%")
    md.append(f"- **Measured sources:** {hm.get('measured_sources','—')}/{hm.get('enabled_sources','—')}")
    md.append(f"- **Top sector:** {hm.get('top_sector','—')}  ({_fmt_usd(hm.get('top_sector_hourly_value_usd'))}/hr)")
    md.append(f"- **Grants queue:** {hm.get('grants_queue_total','—')}  |  **Public truth:** {hm.get('public_truth_status','—')}")
    md.append("")
    md.append("## Live Multi-Asset Signal")
    md.append("")
    md.append(f"- **Rows:** {payload['multi_asset_signal']['rows']}  |  **Unique sector|source keys:** {payload['multi_asset_signal']['sector_source_keys']}")
    md.append(f"- **Sectors covered:** {', '.join(sectors) or '—'}")
    md.append(f"- **Aggregate hourly value:** {_fmt_usd(payload['multi_asset_signal']['total_hourly_value_usd'])}")
    md.append(f"- **Aggregate avoided loss:** {_fmt_usd(payload['multi_asset_signal']['total_avoided_loss_usd'])}")
    md.append("")
    md.append("| Sector | Source | Constraint | Hourly Value | Avoided Loss |")
    md.append("| --- | --- | --- | ---: | ---: |")
    for r in by_sector[:10]:
        md.append(
            f"| {r.get('sector','')} | {r.get('source','')} | {r.get('constraint','')} "
            f"| {_fmt_usd(r.get('estimated_hourly_value_usd',0))} "
            f"| {_fmt_usd(r.get('estimated_avoided_loss_usd',0))} |"
        )
    md.append("")
    md.append("## Active Federal Grant Lanes (with hash-chained evidence packs)")
    md.append("")
    md.append("| T- | Ticket | Agency | Freshness | Bundle SHA | Title |")
    md.append("| --- | --- | --- | --- | --- | --- |")
    for a in payload["active_grant_lanes"]:
        days = a.get("days_left")
        days_s = f"{days}d" if isinstance(days, int) else "?"
        sha = (a.get("bundle_sha256") or "")[:16]
        title = (a.get("title") or "")[:60].replace("|", "\\|")
        md.append(
            f"| {days_s} | `{a.get('ticket_id','')}` | {a.get('agency_match') or '—'} "
            f"| {a.get('freshness') or '—'} | `{sha}` | {title} |"
        )
    md.append("")
    md.append("## Architecture Position")
    md.append("")
    md.append("LumenCore™ is a measurement-first architecture: detect instability earlier, "
              "quantify drift and coherence loss, translate behavior into operational and "
              "economic impact, simulate recovery before failure. Aligned to current priorities "
              "across DoD, DARPA, DOE, DHS/CISA, NSF, NIST, and NASA.")
    md.append("")
    md.append("_See `evidence/agency_alignment_memo.md` and per-ticket evidence packs under "
              "`out/ops/grant_evidence_packs/<TICKET>/EVIDENCE_latest.md` for full chain-of-custody._")
    md.append("")
    md_text = "\n".join(md)

    (DEST / "INVESTOR_ONE_PAGER.md").write_text(md_text, encoding="utf-8")
    (DEST / "INVESTOR_ONE_PAGER.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    # Phone-friendly HTML
    html = [
        "<!doctype html><meta charset=utf-8>",
        "<meta name=viewport content='width=device-width,initial-scale=1'>",
        "<title>LumenCore Investor One-Pager</title>",
        "<style>",
        "body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;",
        "padding:14px;max-width:760px;margin:auto;color:#111;background:#fff;line-height:1.45}",
        "h1{font-size:22px;margin:0 0 6px}h2{font-size:17px;margin:18px 0 6px;color:#0a4}",
        "code{background:#f3f3f3;padding:1px 5px;border-radius:3px;font-size:12px}",
        "table{border-collapse:collapse;width:100%;font-size:13px;margin:6px 0 12px}",
        "th,td{border:1px solid #ddd;padding:5px 7px;text-align:left;vertical-align:top}",
        "th{background:#fafafa}",
        ".kpi{display:grid;grid-template-columns:1fr 1fr;gap:6px}",
        ".kpi div{padding:6px 8px;background:#f7faf7;border-left:3px solid #0a4;border-radius:3px}",
        "</style>",
        f"<h1>LumenCore™ — Investor One-Pager</h1>",
        f"<div><b>As of UTC:</b> {now.isoformat(timespec='seconds')}</div>",
    ]
    if chain:
        html.append(f"<div><b>Truth-chain anchor:</b> <code>{chain.get('entry_sha256','')[:32]}…</code></div>")
    html.append("<h2>Headline Metrics</h2><div class=kpi>")
    kpi_pairs = [
        ("Annual value signal", _fmt_usd(hm.get("annual_value_signal_usd"))),
        ("Valuation proxy", _fmt_usd(hm.get("valuation_proxy_usd"))),
        ("Router edge", f"{hm.get('router_edge_pct','—')}%"),
        ("Harmonic win rate", f"{hm.get('harmonic_win_rate_pct','—')}%"),
        ("Benchmark prevented", f"{hm.get('benchmark_prevented_pct','—')}%"),
        ("Measured coverage", f"{hm.get('measured_coverage_pct','—')}%"),
        ("Top sector", f"{hm.get('top_sector','—')} ({_fmt_usd(hm.get('top_sector_hourly_value_usd'))}/hr)"),
        ("Public truth", str(hm.get("public_truth_status", "—"))),
    ]
    for label, val in kpi_pairs:
        html.append(f"<div><b>{label}</b><br>{val}</div>")
    html.append("</div>")

    html.append("<h2>Live Multi-Asset Signal</h2>")
    html.append(
        f"<div><b>{payload['multi_asset_signal']['rows']}</b> rows · "
        f"<b>{payload['multi_asset_signal']['sector_source_keys']}</b> sector|source keys · "
        f"aggregate <b>{_fmt_usd(payload['multi_asset_signal']['total_hourly_value_usd'])}/hr</b>, "
        f"avoided <b>{_fmt_usd(payload['multi_asset_signal']['total_avoided_loss_usd'])}</b></div>"
    )
    html.append("<table><tr><th>Sector</th><th>Source</th><th>Constraint</th><th>Hourly</th><th>Avoided</th></tr>")
    for r in by_sector[:10]:
        html.append(
            f"<tr><td>{r.get('sector','')}</td><td>{r.get('source','')}</td>"
            f"<td>{r.get('constraint','')}</td>"
            f"<td>{_fmt_usd(r.get('estimated_hourly_value_usd',0))}</td>"
            f"<td>{_fmt_usd(r.get('estimated_avoided_loss_usd',0))}</td></tr>"
        )
    html.append("</table>")

    html.append("<h2>Active Federal Grant Lanes</h2>")
    html.append("<table><tr><th>T-</th><th>Ticket</th><th>Agency</th><th>Fresh</th><th>Bundle SHA</th><th>Title</th></tr>")
    for a in payload["active_grant_lanes"]:
        days = a.get("days_left")
        days_s = f"{days}d" if isinstance(days, int) else "?"
        sha = (a.get("bundle_sha256") or "")[:12]
        html.append(
            f"<tr><td>{days_s}</td><td><code>{a.get('ticket_id','')[:18]}</code></td>"
            f"<td>{a.get('agency_match') or '—'}</td>"
            f"<td>{a.get('freshness') or '—'}</td>"
            f"<td><code>{sha}</code></td>"
            f"<td>{(a.get('title') or '')[:60]}</td></tr>"
        )
    html.append("</table>")
    html.append("<h2>Architecture Position</h2>")
    html.append(
        "<p>LumenCore™ is a measurement-first architecture: detect instability earlier, "
        "quantify drift and coherence loss, translate behavior into operational and economic "
        "impact, simulate recovery before failure. Aligned across DoD, DARPA, DOE, DHS/CISA, "
        "NSF, NIST, and NASA priorities.</p>"
    )
    (DEST / "INVESTOR_ONE_PAGER.html").write_text("\n".join(html), encoding="utf-8")

    print(f"OK  one-pager written:")
    print(f"  {DEST / 'INVESTOR_ONE_PAGER.md'}")
    print(f"  {DEST / 'INVESTOR_ONE_PAGER.html'}")
    print(f"  {DEST / 'INVESTOR_ONE_PAGER.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
