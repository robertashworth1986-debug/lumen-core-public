"""
INFRA AUDIT DASHBOARD BUILDER
════════════════════════════════════════════════════════════════════════════════
Reads infra_constraint_status.json + audit_chain.jsonl every few seconds
and produces dashboard/infra_audit_dashboard.html.

Panels:
  1. Header                — Live clock, system title, DoD/DARPA/NSF grade badge
  2. Account KPI row       — Equity, P&L, fill rate, violation count
  3. Financial Impact row  — Loss/sec, capital burn/sec, dead capital, opp cost
  4. Constraint Violations — Every violation: WHAT / WHY / FORMULA / $ IMPACT
  5. Sector Performance    — Sector-by-sector table with P&L, fill rate, trades
  6. Data Feed Health      — All CSV feeds: freshness score, age, staleness
  7. Formula Codex         — Every formula documented (full audit reference)
  8. Audit Chain Events    — Last 50 hash-chained events with SHA-256 hashes
"""

import argparse
import atexit
import json
import os
import time
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"
DASH_STACK = ROOT / "dashboard"
DASH_ROOT = ROOT.parent / "dashboard"

CONSTRAINT_STATUS_FILE = EXEC_OUT / "infra_constraint_status.json"
AUDIT_CHAIN_FILE = OUT / "audit_chain.jsonl"
HTML_OUTS = [
  DASH_STACK / "infra_audit_dashboard.html",
  DASH_ROOT / "infra_audit_dashboard.html",
]


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def load_jsonl_tail(path: Path, n: int = 60) -> list:
    rows: list = []
    try:
        if path.exists():
            for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                raw = raw.strip()
                if raw:
                    try:
                        rows.append(json.loads(raw))
                    except Exception:
                        pass
    except Exception:
        pass
    return rows[-n:]


def build_html(status: dict, audit_events: list) -> str:
    build_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    embedded_status = json.dumps(status, ensure_ascii=True)
    embedded_audit = json.dumps(audit_events[-50:], ensure_ascii=True)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="refresh" content="30" />
  <title>LumenTrace Infra Audit Dashboard</title>
  <script src="js/luma_design_system.js"></script>
  <style>
    :root {{
      --bg: #060c12;
      --panel: rgba(8, 22, 34, 0.90);
      --panel-bright: rgba(10, 28, 44, 0.96);
      --line: rgba(0, 200, 255, 0.15);
      --line2: rgba(163, 255, 18, 0.12);
      --text: #dff0f6;
      --muted: #7a9bac;
      --accent: #a3ff12;
      --cyan: #00c2ff;
      --warn: #ffd166;
      --danger: #ff5555;
      --danger2: #ff8c42;
      --ok: #44d9a2;
      --mono: 'Courier New', Courier, monospace;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: Georgia, 'Times New Roman', serif;
      color: var(--text);
      background:
        radial-gradient(circle at 0% 0%, rgba(0,194,255,0.14) 0%, transparent 35%),
        radial-gradient(circle at 100% 0%, rgba(163,255,18,0.09) 0%, transparent 30%),
        radial-gradient(circle at 50% 100%, rgba(255,85,85,0.06) 0%, transparent 40%),
        linear-gradient(180deg, #050b10 0%, #060c12 100%);
      min-height: 100vh;
    }}

    /* ── layout ──────────────────────────────────────────────────────── */
    .wrap {{ max-width: 1560px; margin: 0 auto; padding: 24px 28px; }}
    .row {{ display: grid; gap: 16px; margin-bottom: 16px; }}
    .col-4 {{ grid-template-columns: repeat(4, 1fr); }}
    .col-3 {{ grid-template-columns: repeat(3, 1fr); }}
    .col-2 {{ grid-template-columns: 1.4fr 0.6fr; }}
    .col-2-eq {{ grid-template-columns: 1fr 1fr; }}
    .col-1 {{ grid-template-columns: 1fr; }}

    /* ── panels ──────────────────────────────────────────────────────── */
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 18px 20px;
      backdrop-filter: blur(10px);
      box-shadow: 0 12px 40px rgba(0,0,0,0.35);
    }}
    .panel-danger {{ border-color: rgba(255,85,85,0.35); }}
    .panel-warn   {{ border-color: rgba(255,209,102,0.25); }}
    .panel-ok     {{ border-color: rgba(68,217,162,0.25); }}

    /* ── type ────────────────────────────────────────────────────────── */
    .eyebrow {{
      font-family: var(--mono);
      font-size: 10px;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--cyan);
      margin-bottom: 8px;
    }}
    .headline {{ font-size: 38px; line-height: 1.05; }}
    .sub {{ color: var(--muted); font-size: 14px; max-width: 70ch; line-height: 1.5; }}
    h2 {{ font-size: 18px; margin-bottom: 10px; color: var(--text); }}
    h3 {{ font-size: 14px; font-weight: normal; color: var(--muted); margin-bottom: 6px; }}

    /* ── KPI metrics ─────────────────────────────────────────────────── */
    .kpi-label {{
      font-family: var(--mono);
      font-size: 11px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .kpi-value {{
      font-family: var(--mono);
      font-size: 30px;
      margin: 6px 0 4px;
      color: var(--accent);
    }}
    .kpi-sub {{ font-size: 12px; color: var(--muted); }}
    .kpi-value.danger {{ color: var(--danger); }}
    .kpi-value.warn   {{ color: var(--warn); }}
    .kpi-value.ok     {{ color: var(--ok); }}
    .kpi-value.cyan   {{ color: var(--cyan); }}

    /* ── severity badges ─────────────────────────────────────────────── */
    .badge {{
      display: inline-block;
      padding: 3px 9px;
      border-radius: 999px;
      font-family: var(--mono);
      font-size: 11px;
      font-weight: bold;
      text-transform: uppercase;
    }}
    .badge-CRITICAL {{ background: rgba(255,85,85,0.18); color: var(--danger); border: 1px solid rgba(255,85,85,0.4); }}
    .badge-HIGH     {{ background: rgba(255,140,66,0.15); color: var(--danger2); border: 1px solid rgba(255,140,66,0.35); }}
    .badge-MEDIUM   {{ background: rgba(255,209,102,0.15); color: var(--warn); border: 1px solid rgba(255,209,102,0.3); }}
    .badge-OK       {{ background: rgba(68,217,162,0.12); color: var(--ok); border: 1px solid rgba(68,217,162,0.3); }}
    .badge-INFO     {{ background: rgba(0,194,255,0.12); color: var(--cyan); border: 1px solid rgba(0,194,255,0.3); }}

    /* ── violation cards ─────────────────────────────────────────────── */
    .viol {{
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 10px;
      background: rgba(10,22,34,0.6);
    }}
    .viol-CRITICAL {{ border-left: 3px solid var(--danger); }}
    .viol-HIGH     {{ border-left: 3px solid var(--danger2); }}
    .viol-MEDIUM   {{ border-left: 3px solid var(--warn); }}
    .viol-id {{
      font-family: var(--mono);
      font-size: 11px;
      color: var(--cyan);
      margin-bottom: 4px;
    }}
    .viol-what {{ font-size: 14px; margin-bottom: 6px; }}
    .viol-why  {{ font-size: 13px; color: var(--muted); margin-bottom: 6px; line-height: 1.45; }}
    .formula-box {{
      background: rgba(0,0,0,0.45);
      border: 1px solid var(--line2);
      border-radius: 7px;
      padding: 8px 10px;
      font-family: var(--mono);
      font-size: 12px;
      color: var(--accent);
      margin-top: 6px;
      word-break: break-all;
    }}
    .impact-line {{
      font-family: var(--mono);
      font-size: 12px;
      color: var(--warn);
      margin-top: 6px;
    }}

    /* ── tables ──────────────────────────────────────────────────────── */
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{
      padding: 9px 8px;
      font-size: 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      font-family: var(--mono);
      font-size: 10px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    td.mono {{ font-family: var(--mono); }}
    .pos {{ color: var(--ok); }}
    .neg {{ color: var(--danger); }}
    .neutral {{ color: var(--muted); }}

    /* ── freshness bar ───────────────────────────────────────────────── */
    .fresh-bar-wrap {{
      height: 5px;
      background: rgba(255,255,255,0.08);
      border-radius: 99px;
      margin-top: 4px;
    }}
    .fresh-bar {{
      height: 5px;
      border-radius: 99px;
      transition: width 0.4s;
    }}

    /* ── audit chain ─────────────────────────────────────────────────── */
    .chain-row {{
      padding: 8px 0;
      border-bottom: 1px solid var(--line);
      font-size: 12px;
    }}
    .chain-hash {{
      font-family: var(--mono);
      font-size: 10px;
      color: var(--muted);
      word-break: break-all;
    }}
    .chain-type {{
      font-family: var(--mono);
      font-size: 11px;
      color: var(--cyan);
      margin-bottom: 2px;
    }}

    /* ── formula codex ───────────────────────────────────────────────── */
    .formula-entry {{
      padding: 12px 0;
      border-bottom: 1px solid var(--line);
    }}
    .formula-key {{
      font-family: var(--mono);
      font-size: 11px;
      color: var(--accent);
      margin-bottom: 4px;
    }}
    .formula-expr {{
      font-family: var(--mono);
      font-size: 13px;
      color: #eef5ff;
      background: rgba(0,0,0,0.4);
      border-radius: 6px;
      padding: 6px 10px;
      margin: 4px 0;
    }}
    .formula-desc {{ font-size: 13px; color: var(--muted); line-height: 1.45; }}
    .formula-src  {{
      font-family: var(--mono);
      font-size: 10px;
      color: rgba(0,194,255,0.6);
      margin-top: 3px;
    }}

    /* ── live strip ──────────────────────────────────────────────────── */
    #live-strip {{
      font-family: var(--mono);
      font-size: 11px;
      color: rgba(0,194,255,0.8);
      padding: 8px 12px;
      border-top: 1px solid var(--line);
      margin-top: 12px;
    }}

    /* ── scrollable boxes ────────────────────────────────────────────── */
    .scroll-box {{ max-height: 480px; overflow-y: auto; padding-right: 4px; }}
    .scroll-chain {{ max-height: 520px; overflow-y: auto; padding-right: 4px; }}

    @media (max-width: 1100px) {{
      .col-4, .col-3, .col-2, .col-2-eq {{ grid-template-columns: 1fr; }}
      .headline {{ font-size: 26px; }}
    }}

    .infra-premium-band {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 18px;
    }}
    .infra-premium-card {{
      background: rgba(8, 22, 34, 0.86);
      border: 1px solid rgba(86, 215, 203, 0.18);
      border-radius: 14px;
      padding: 18px 20px;
      box-shadow: 0 12px 40px rgba(0,0,0,0.22);
    }}
    .infra-premium-title {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 14px;
      font-weight: 600;
      color: #dfbb6b;
      margin-bottom: 4px;
    }}
    .infra-premium-sub {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px;
      color: #8cb4db;
      margin-bottom: 12px;
    }}
    .infra-premium-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }}
    .infra-mini {{
      background: rgba(0,0,0,0.22);
      border: 1px solid rgba(126,172,214,0.16);
      border-radius: 10px;
      padding: 10px 12px;
    }}
    .infra-mini-label {{
      font-family: var(--mono);
      font-size: 10px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 6px;
    }}
    .infra-mini-value {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 20px;
      font-weight: 700;
      color: #56d7cb;
    }}
    .infra-premium-list {{
      font-family: var(--mono);
      font-size: 11px;
      color: #a8c4e4;
      line-height: 1.6;
      max-height: 116px;
      overflow-y: auto;
    }}
    .infra-explainer-panel {{
      min-height: 88px;
    }}
    #infra-helmier-proof-panel {{
      margin-top: 14px;
    }}
    @media (max-width: 1100px) {{
      .infra-premium-band {{ grid-template-columns: 1fr; }}
      .infra-premium-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 640px) {{
      .infra-premium-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
<div class="wrap">

  <!-- ══════════════════════════ HEADER ═══════════════════════════════════ -->
  <div class="row col-2" style="margin-bottom:20px;">
    <section class="panel">
      <div class="eyebrow">LumenTrace · Government-Grade Institutional Audit System</div>
      <h1 class="headline">Infrastructure Constraint<br>Monitor &amp; Audit Trail</h1>
      <p class="sub" style="margin-top:10px;">
        Real-time constraint detection · Formula-documented financial impact ·
        SHA-256 tamper-evident audit chain · Sector comparison ·
        Every decision explained — suitable for DoD / DARPA / NSF review.
      </p>
      <div id="live-strip">Loading...</div>
    </section>
    <section class="panel">
      <div class="eyebrow">Audit Standard</div>
      <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;">
        <span class="badge badge-INFO">SHA-256 Chain</span>
        <span class="badge badge-INFO">Formula Codex</span>
        <span class="badge badge-INFO">Impact Quantified</span>
        <span class="badge badge-INFO">Tamper-Evident</span>
        <span class="badge badge-INFO">Sector Attribution</span>
      </div>
      <div class="eyebrow" style="margin-top:14px;">Violation Summary</div>
      <div id="violation-summary" style="font-family:var(--mono);font-size:13px;line-height:2.0;"></div>
      <div class="eyebrow" style="margin-top:14px;">API Coverage</div>
      <div id="api-coverage" style="font-family:var(--mono);font-size:12px;line-height:1.8;"></div>
      <div class="eyebrow" style="margin-top:14px;">Truth Hardening</div>
      <div id="truth-hardening" style="font-family:var(--mono);font-size:12px;line-height:1.8;"></div>
    </section>
  </div>

  <div class="infra-premium-band">
    <section class="infra-premium-card">
      <div class="infra-premium-title">Live Gateway Intelligence</div>
      <div class="infra-premium-sub">Institutional bridge across execution, infra, proof, and harmonic edge</div>
      <div class="infra-premium-grid">
        <div class="infra-mini"><div class="infra-mini-label">Equity</div><div class="infra-mini-value" id="infraSnapEquity">—</div></div>
        <div class="infra-mini"><div class="infra-mini-label">PnL</div><div class="infra-mini-value" id="infraSnapPnl">—</div></div>
        <div class="infra-mini"><div class="infra-mini-label">Win Rate</div><div class="infra-mini-value" id="infraSnapWinRate">—</div></div>
        <div class="infra-mini"><div class="infra-mini-label">Closed Trades</div><div class="infra-mini-value" id="infraSnapClosedTrades">—</div></div>
      </div>
      <div id="infra-helmier-proof-panel"></div>
    </section>
    <section class="infra-premium-card">
      <div class="infra-premium-title">Node-RED, Unity, and Luma Explainer</div>
      <div class="infra-premium-sub">Live feed bus, XR edge graph, and investor-grade reasoning layer</div>
      <div class="infra-premium-grid" style="margin-bottom:12px;">
        <div class="infra-mini"><div class="infra-mini-label">Unity Nodes</div><div class="infra-mini-value" id="infraUnityNodeCount">—</div></div>
        <div class="infra-mini"><div class="infra-mini-label">Infra Lane</div><div class="infra-mini-value" id="infraTopLane">—</div></div>
        <div class="infra-mini"><div class="infra-mini-label">Active Surface</div><div class="infra-mini-value" id="infraActiveSurface">—</div></div>
        <div class="infra-mini"><div class="infra-mini-label">Gateway Stamp</div><div class="infra-mini-value" id="infraSnapshotStamp">—</div></div>
      </div>
      <div id="infra-nr-main" style="margin-bottom:10px;"></div>
      <div id="infra-unity-top" class="infra-premium-list">Awaiting Unity edge data...</div>
      <div id="infra-luma-explainer-panel" class="infra-explainer-panel"></div>
    </section>
  </div>

  <!-- ══════════════════════ ACCOUNT KPI ROW ══════════════════════════════ -->
  <div class="row col-4" id="kpi-row">
  </div>

  <!-- ══════════════════════ FINANCIAL IMPACT ROW ═════════════════════════ -->
  <div class="row col-4" id="impact-row">
  </div>

  <!-- ══════════════════════ CONSTRAINT VIOLATIONS ════════════════════════ -->
  <div class="row col-2" style="align-items:start;">
    <section class="panel panel-danger">
      <div class="eyebrow">Constraint Violations — Live</div>
      <h2 id="viol-count-title">Loading violations...</h2>
      <div class="scroll-box" id="violations-panel"></div>
    </section>
    <section class="panel">
      <div class="eyebrow">Sector Performance</div>
      <h2>P&amp;L · Fill Rate · Trades by Sector</h2>
      <div class="scroll-box">
        <table id="sector-table">
          <thead>
            <tr>
              <th>Sector</th><th>Trades</th><th>Fill%</th>
              <th>Notional</th><th>Net P&amp;L</th><th>Open</th>
            </tr>
          </thead>
          <tbody id="sector-tbody"></tbody>
        </table>
      </div>
      <div class="formula-box" style="margin-top:10px;font-size:11px;">
        sector_pnl = Σ(realized_pnl in sector) + Σ(unrealized_pl in sector)
      </div>
    </section>
  </div>

  <!-- ══════════════════════ DATA FEED HEALTH ══════════════════════════════ -->
  <div class="row col-1">
    <section class="panel">
      <div class="eyebrow">Live Data Feed Health — Freshness Monitor</div>
      <h2>Every feed scored by: freshness = max(0, 1 − age / max_acceptable_age)</h2>
      <div class="scroll-box" style="max-height:320px;">
        <table id="feeds-table">
          <thead>
            <tr>
              <th>File</th><th>Sector</th><th>Type</th>
              <th>Age (s)</th><th>Max Age (s)</th><th>Freshness</th>
              <th>Stale?</th><th>Opp. Cost</th>
            </tr>
          </thead>
          <tbody id="feeds-tbody"></tbody>
        </table>
      </div>
    </section>
  </div>

  <!-- ══════════════════════ FORMULA CODEX ════════════════════════════════ -->
  <div class="row col-2-eq" style="align-items:start;">
    <section class="panel">
      <div class="eyebrow">Formula Codex — Audit Reference</div>
      <h2>Every formula used by this system, documented for audit</h2>
      <div class="scroll-box" id="formula-codex"></div>
    </section>
    <section class="panel">
      <div class="eyebrow">Execution Metrics — Full Breakdown</div>
      <h2>Order Submission, Fill Rate &amp; Capital Efficiency</h2>
      <div id="exec-panel" style="font-size:13px;line-height:1.8;"></div>
    </section>
  </div>

  <!-- ══════════════════════ AUDIT CHAIN ══════════════════════════════════ -->
  <div class="row col-1">
    <section class="panel">
      <div class="eyebrow">SHA-256 Hash Chain — Tamper-Evident Audit Trail</div>
      <h2>Every constraint violation and monitor cycle is hashed and chained</h2>
      <p class="sub" style="margin-bottom:12px;">
        Each event includes <code style="font-size:11px;color:var(--accent);">prev_hash</code>
        → <code style="font-size:11px;color:var(--accent);">event_hash</code>.
        Altering any prior record breaks all subsequent hashes — mathematically
        tamper-evident without a trusted third party.
      </p>
      <div class="scroll-chain" id="audit-chain-panel"></div>
    </section>
  </div>

</div><!-- /.wrap -->

<script>
// ── embedded data ────────────────────────────────────────────────────────────
const STATUS  = {embedded_status};
const AUDIT   = {embedded_audit};
const BUILD_TS = "{build_ts}";

// Persist scroll position across timed refreshes so reading position is not lost.
window.addEventListener('beforeunload', function() {{
  sessionStorage.setItem('infraAuditScrollY', String(window.scrollY || 0));
}});

window.addEventListener('load', function() {{
  const y = Number(sessionStorage.getItem('infraAuditScrollY') || '0');
  if (!Number.isNaN(y) && y > 0) {{
    window.scrollTo(0, y);
  }}
}});

// ── helpers ──────────────────────────────────────────────────────────────────
function fmt(v, decimals=2) {{
  if (v === null || v === undefined) return '—';
  return Number(v).toFixed(decimals);
}}
function fmtUsd(v) {{
  const n = Number(v);
  const sign = n < 0 ? '-' : (n > 0 ? '+' : '');
  return sign + '$' + Math.abs(n).toLocaleString('en-US', {{minimumFractionDigits:2, maximumFractionDigits:2}});
}}
function fmtUsdAbs(v) {{
  return '$' + Number(Math.abs(v)).toLocaleString('en-US', {{minimumFractionDigits:2, maximumFractionDigits:2}});
}}
function colorClass(v) {{
  if (Number(v) > 0) return 'pos';
  if (Number(v) < 0) return 'neg';
  return 'neutral';
}}
function severityClass(s) {{
  if (s === 'CRITICAL') return 'badge-CRITICAL';
  if (s === 'HIGH') return 'badge-HIGH';
  if (s === 'MEDIUM') return 'badge-MEDIUM';
  return 'badge-INFO';
}}
function freshColor(score) {{
  if (score >= 0.75) return '#44d9a2';
  if (score >= 0.40) return '#ffd166';
  return '#ff5555';
}}
function esc(s) {{
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

// ── live strip ────────────────────────────────────────────────────────────────
function updateStrip() {{
  const el = document.getElementById('live-strip');
  if (!el) return;
  const browserNow = new Date().toISOString();
  const genUtc     = STATUS.generated_utc || '—';
  el.textContent   = `Browser clock: ${{browserNow}}  |  Last monitor cycle: ${{genUtc}}  |  HTML built: ${{BUILD_TS}}`;
}}
setInterval(updateStrip, 1000);
updateStrip();

// ── violation summary ─────────────────────────────────────────────────────────
(function() {{
  const sev = STATUS.violations_by_severity || {{}};
  const cat = STATUS.violations_by_category || {{}};
  const el = document.getElementById('violation-summary');
  if (!el) return;
  el.innerHTML = [
    `<span class="badge badge-CRITICAL">CRITICAL: ${{sev.CRITICAL||0}}</span>  `,
    `<span class="badge badge-HIGH">HIGH: ${{sev.HIGH||0}}</span>  `,
    `<span class="badge badge-MEDIUM">MEDIUM: ${{sev.MEDIUM||0}}</span>`,
    '<br><br>',
    Object.entries(cat).map(([c,n]) => `${{c}}: ${{n}}`).join('<br>'),
  ].join('');
}})();

// ── api coverage summary ───────────────────────────────────────────────────────
(function() {{
  const cov = STATUS.api_source_coverage || {{}};
  const el = document.getElementById('api-coverage');
  if (!el) return;
  const configured = Number(cov.provider_count_configured || 0);
  const live = Number(cov.provider_count_with_live_rows || 0);
  const pct = Number(cov.live_data_coverage_pct || 0);
  const keys = Number(cov.env_key_count_populated || 0);
  const color = pct >= 90 ? 'var(--ok)' : (pct >= 70 ? 'var(--warn)' : 'var(--danger)');
  el.innerHTML = `
    ENV keys populated: ${{keys}}<br>
    Providers live now: ${{live}} / ${{configured}}<br>
    Coverage: <span style="color:${{color}};font-weight:bold;">${{fmt(pct,2)}}%</span>
  `;
}})();

// ── truth hardening summary ───────────────────────────────────────────────────
(function() {{
  const truth = STATUS.truth_hardening || {{}};
  const chain = truth.audit_chain || {{}};
  const execTrust = truth.executive_trust_report || {{}};
  const el = document.getElementById('truth-hardening');
  if (!el) return;
  const score = Number(truth.truth_score || 0);
  const grade = truth.truth_grade || 'D';
  const scoreColor = score >= 90 ? 'var(--ok)' : (score >= 75 ? 'var(--warn)' : 'var(--danger)');
  const chainOk = chain.ok === true;
  const fp = String(STATUS.reproducibility_fingerprint_sha256 || '').slice(0, 24);
  const slaOk = execTrust.coverage_sla_compliant === true;
  el.innerHTML = `
    Truth Score: <span style="color:${{scoreColor}};font-weight:bold;">${{fmt(score,2)}} (${{grade}})</span><br>
    Chain Integrity: <span style="color:${{chainOk ? 'var(--ok)' : 'var(--danger)'}};font-weight:bold;">${{chainOk ? 'PASS' : 'FAIL'}}</span>
    (events=${{chain.events||0}}, broken=${{chain.broken_links||0}}, tailBroken=${{chain.tail_broken_links||0}})<br>
    24h Chain Tail Pass Rate: <span style="color:var(--cyan);">${{fmt(execTrust.chain_tail_pass_rate_24h_pct||0,2)}}%</span><br>
    24h Fingerprint Change Rate: <span style="color:var(--cyan);">${{fmt(execTrust.fingerprint_change_rate_24h_pct||0,2)}}%</span><br>
    Coverage SLA: <span style="color:${{slaOk ? 'var(--ok)' : 'var(--warn)'}};font-weight:bold;">${{slaOk ? 'COMPLIANT' : 'BELOW TARGET'}}</span>
    (${{fmt(execTrust.coverage_current_pct||0,2)}}% / target ${{fmt(execTrust.coverage_sla_target_pct||0,2)}}%)<br>
    Repro Fingerprint: <span style="color:var(--cyan);">${{esc(fp)}}...</span>
  `;
}})();

// ── KPI row ───────────────────────────────────────────────────────────────────
(function() {{
  const acct   = STATUS.account_metrics || {{}};
  const exec   = STATUS.execution_metrics || {{}};
  const fi     = STATUS.financial_impact_summary || {{}};
  const kpis   = [
    {{
      label: 'Account Equity',
      val: fmtUsdAbs(acct.equity_usd||0),
      cls: 'cyan',
      sub: `P&L: ${{fmtUsd(acct.pnl_usd||0)}}  (${{fmt(acct.pnl_pct||0,4)}}%)`,
    }},
    {{
      label: 'Fill Rate',
      val: fmt(exec.fill_rate_pct||0,1) + '%',
      cls: (exec.fill_rate_pct||0) < 50 ? 'danger' : (exec.fill_rate_pct||0) < 90 ? 'warn' : 'ok',
      sub: `${{exec.filled_orders||0}} fills / ${{exec.total_orders_submitted||0}} orders`,
    }},
    {{
      label: 'Active Violations',
      val: String(STATUS.violation_count||0),
      cls: (STATUS.violation_count||0) > 0 ? 'danger' : 'ok',
      sub: `CRIT:${{(STATUS.violations_by_severity||{{}}).CRITICAL||0}} HIGH:${{(STATUS.violations_by_severity||{{}}).HIGH||0}} MED:${{(STATUS.violations_by_severity||{{}}).MEDIUM||0}}`,
    }},
    {{
      label: 'Data Feed Health',
      val: String(STATUS.fresh_feed_count||0) + '/' + String(STATUS.total_feed_count||0),
      cls: (STATUS.stale_feed_count||0) > 0 ? 'warn' : 'ok',
      sub: `${{STATUS.stale_feed_count||0}} stale · ${{STATUS.fresh_feed_count||0}} fresh`,
    }},
  ];
  const wrap = document.getElementById('kpi-row');
  if (!wrap) return;
  wrap.innerHTML = kpis.map(k => `
    <section class="panel">
      <div class="kpi-label">${{k.label}}</div>
      <div class="kpi-value ${{k.cls}}">${{k.val}}</div>
      <div class="kpi-sub">${{k.sub}}</div>
    </section>
  `).join('');
}})();

// ── Impact row ────────────────────────────────────────────────────────────────
(function() {{
  const exec = STATUS.execution_metrics || {{}};
  const fi   = STATUS.financial_impact_summary || {{}};
  const impacts = [
    {{
      label: 'Loss Per Second (Positions)',
      val: '$' + fmt(fi.total_loss_per_second_usd||0, 8),
      cls: (fi.total_loss_per_second_usd||0) > 0 ? 'danger' : 'ok',
      sub: 'loss/sec = |unrealized_loss| / position_age_secs',
    }},
    {{
      label: 'Capital Burn Per Second',
      val: '$' + fmt(fi.total_capital_burn_per_sec_usd||0, 6),
      cls: (fi.total_capital_burn_per_sec_usd||0) > 0.001 ? 'warn' : 'ok',
      sub: exec.capital_burn_formula || 'burn = reserved_capital / session_secs',
    }},
    {{
      label: 'Dead Capital (Reserved)',
      val: fmtUsdAbs(fi.total_dead_capital_usd||0),
      cls: (fi.total_dead_capital_usd||0) > 500 ? 'warn' : 'ok',
      sub: 'Capital in unfilled orders — cannot compound',
    }},
    {{
      label: 'Opportunity Cost (Stale Data)',
      val: fmtUsdAbs(fi.total_opportunity_cost_usd||0),
      cls: (fi.total_opportunity_cost_usd||0) > 1 ? 'warn' : 'ok',
      sub: 'opp_cost = equity × pos_pct × edge_bps/10000 × stale_hrs',
    }},
    {{
      label: 'Execution Opp Cost (24h)',
      val: fmtUsdAbs(fi.execution_opportunity_cost_24h_usd||0),
      cls: (fi.execution_opportunity_cost_24h_usd||0) > 1 ? 'warn' : 'ok',
      sub: 'unfilled_notional_24h × baseline_edge_bps/10,000',
    }},
  ];
  const wrap = document.getElementById('impact-row');
  if (!wrap) return;
  wrap.innerHTML = impacts.map(i => `
    <section class="panel">
      <div class="kpi-label">${{i.label}}</div>
      <div class="kpi-value ${{i.cls}}" style="font-size:24px;">${{i.val}}</div>
      <div class="kpi-sub" style="font-size:11px;font-family:var(--mono);">${{esc(i.sub)}}</div>
    </section>
  `).join('');
}})();

// ── constraint violations ─────────────────────────────────────────────────────
(function() {{
  const viols = STATUS.constraint_violations || [];
  const panel = document.getElementById('violations-panel');
  const title = document.getElementById('viol-count-title');
  if (!panel) return;
  if (title) title.textContent = `${{viols.length}} Active Constraint${{viols.length !== 1 ? 's' : ''}} Detected`;

  if (viols.length === 0) {{
    panel.innerHTML = '<div class="viol" style="color:var(--ok);">✓ No constraint violations detected this cycle.</div>';
    return;
  }}

  const order = {{ CRITICAL:0, HIGH:1, MEDIUM:2 }};
  const sorted = [...viols].sort((a,b) => (order[a.severity]||9) - (order[b.severity]||9));

  panel.innerHTML = sorted.map(v => `
    <div class="viol viol-${{v.severity||'MEDIUM'}}">
      <div class="viol-id">
        <span class="badge ${{severityClass(v.severity)}}">${{v.severity||'?'}}</span>
        &nbsp; ${{esc(v.constraint_id)}}
        &nbsp; <span style="color:var(--muted);font-size:10px;">${{esc(v.category||'')}}</span>
        &nbsp; <span style="color:var(--muted);font-size:10px;">sector: ${{esc(v.sector||'')}}</span>
      </div>
      <div class="viol-what"><strong>WHAT:</strong> ${{esc(v.what_happened||'')}}</div>
      <div class="viol-why"><strong>WHY:</strong> ${{esc(v.why_it_matters||'')}}</div>
      <div class="formula-box">
        FORMULA: ${{esc(v.formula_applied||v.formula_key||'—')}}
      </div>
      <div class="impact-line">
        $ IMPACT: ${{v.financial_impact_usd !== undefined ? fmtUsdAbs(v.financial_impact_usd) : '—'}}
        &nbsp;·&nbsp; ${{esc(v.financial_impact_explanation||'')}}
      </div>
      <div style="font-family:var(--mono);font-size:10px;color:var(--muted);margin-top:4px;">
        Detected: ${{esc(v.detected_utc||'')}}
      </div>
    </div>
  `).join('');
}})();

// ── sector table ──────────────────────────────────────────────────────────────
(function() {{
  const sectors = STATUS.sector_metrics || {{}};
  const tbody = document.getElementById('sector-tbody');
  if (!tbody) return;
  const rows = Object.values(sectors).sort((a,b) => b.trade_count - a.trade_count);
  if (rows.length === 0) {{
    tbody.innerHTML = '<tr><td colspan="6" class="neutral" style="text-align:center;">No sector data yet — waiting for fills</td></tr>';
    return;
  }}
  tbody.innerHTML = rows.map(s => `
    <tr>
      <td class="mono">${{esc(s.sector)}}</td>
      <td>${{s.trade_count}}</td>
      <td class="${{s.fill_rate_pct >= 80 ? 'pos' : s.fill_rate_pct >= 30 ? '' : 'neg'}}">${{fmt(s.fill_rate_pct,1)}}%</td>
      <td class="mono">${{fmtUsdAbs(s.total_notional_usd)}}</td>
      <td class="mono ${{colorClass(s.net_pnl_usd)}}">${{fmtUsd(s.net_pnl_usd)}}</td>
      <td>${{s.open_positions}}</td>
    </tr>
  `).join('');
}})();

// ── feeds table ───────────────────────────────────────────────────────────────
(function() {{
  const feeds = STATUS.data_feed_metrics || {{}};
  const tbody = document.getElementById('feeds-tbody');
  if (!tbody) return;
  const entries = Object.values(feeds).sort((a,b) => a.freshness_score - b.freshness_score);
  tbody.innerHTML = entries.map(f => {{
    const fs = Number(f.freshness_score||0);
    const barW = Math.round(fs * 100);
    const barColor = freshColor(fs);
    return `
      <tr>
        <td class="mono" style="font-size:11px;">${{esc(f.file)}}</td>
        <td class="mono">${{esc(f.sector)}}</td>
        <td class="mono">${{esc(f.feed_type)}}</td>
        <td class="mono ${{f.is_stale ? 'neg' : 'pos'}}">${{fmt(f.age_secs,0)}}</td>
        <td class="mono">${{fmt(f.max_acceptable_age_secs,0)}}</td>
        <td>
          <div style="font-family:var(--mono);font-size:11px;">${{fmt(fs*100,1)}}%</div>
          <div class="fresh-bar-wrap"><div class="fresh-bar" style="width:${{barW}}%;background:${{barColor}};"></div></div>
        </td>
        <td class="${{f.is_stale ? 'neg' : 'pos'}}">${{f.is_stale ? 'STALE' : 'OK'}}</td>
        <td class="mono ${{Number(f.opportunity_cost_usd)>0 ? 'warn' : 'neutral'}}">${{fmtUsdAbs(f.opportunity_cost_usd||0)}}</td>
      </tr>
    `;
  }}).join('');
}})();

// ── formula codex ─────────────────────────────────────────────────────────────
(function() {{
  const codex = STATUS.formula_registry || {{}};
  const el = document.getElementById('formula-codex');
  if (!el) return;
  el.innerHTML = Object.entries(codex).map(([key, f]) => `
    <div class="formula-entry">
      <div class="formula-key">${{esc(key)}}</div>
      <div class="formula-expr">${{esc(f.formula||'—')}}</div>
      <div class="formula-desc">${{esc(f.description||'')}}</div>
      ${{f.source_file ? `<div class="formula-src">↳ ${{esc(f.source_file)}} :: ${{esc(f.source_function||'')}}</div>` : ''}}
    </div>
  `).join('');
}})();

// ── execution metrics panel ───────────────────────────────────────────────────
(function() {{
  const exec = STATUS.execution_metrics || {{}};
  const acct = STATUS.account_metrics || {{}};
  const el = document.getElementById('exec-panel');
  if (!el) return;
  const rows = [
    ['Orders Submitted',      exec.total_orders_submitted||0, ''],
    ['Orders Filled',         exec.filled_orders||0, ''],
    ['Unfilled (Historical)', exec.unfilled_orders_historical||0, 'Lifetime ledger count'],
    ['Open Unfilled (Now)',   exec.current_open_unfilled_orders_count||0, 'Live Alpaca open queue right now'],
    ['Open Orders (Now)',     exec.current_open_orders_count||0, 'Live open orders count'],
    ['Fill Rate',             fmt(exec.fill_rate_pct||0,2)+'%',  exec.fill_rate_formula||''],
    ['Submitted (Last 24h)',  exec.orders_submitted_last_24h||0, 'Rolling 24h'],
    ['Filled (Last 24h)',     exec.filled_orders_last_24h||0, 'Rolling 24h'],
    ['Fill Rate (Last 24h)',  fmt(exec.fill_rate_last_24h_pct||0,2)+'%', 'Rolling 24h fill quality'],
    ['Unfilled Notional (24h)', fmtUsdAbs(exec.unfilled_notional_24h_usd||0), 'Rolling 24h unfilled notional'],
    ['Exec Opp Cost (24h)', fmtUsdAbs(exec.execution_opportunity_cost_24h_usd||0), exec.execution_opportunity_cost_formula||''],
    ['Exec Opp Cost (Historical)', fmtUsdAbs(exec.execution_opportunity_cost_historical_usd||0), 'Cumulative execution drag estimate'],
    ['Signal Sharpe (Proxy)', exec.signal_sharpe_proxy !== null && exec.signal_sharpe_proxy !== undefined ? fmt(exec.signal_sharpe_proxy,3) : 'N/A', (exec.signal_sharpe_proxy_formula||'') + `  [N=${{exec.signal_sharpe_proxy_samples||0}}]`],
    ['Realized Sharpe (Trades)', exec.realized_trade_sharpe !== null && exec.realized_trade_sharpe !== undefined ? fmt(exec.realized_trade_sharpe,3) : 'N/A', (exec.realized_trade_sharpe_formula||'') + `  [N=${{exec.realized_trade_sharpe_samples||0}}]`],
    ['Total Notional',        fmtUsdAbs(exec.total_notional_submitted_usd||0), ''],
    ['Buying Power',          fmtUsdAbs(exec.buying_power_usd||0), ''],
    ['Reserved (Pending)',    fmtUsdAbs(exec.reserved_capital_usd||0), exec.capital_burn_formula||''],
    ['Session Elapsed',       fmt(exec.session_elapsed_secs||0,0)+'s', ''],
    ['Capital Burn /sec',     '$'+fmt(exec.capital_burn_rate_per_sec_usd||0,8), ''],
    ['Open Loss Total',       fmtUsd(-(exec.open_loss_total_usd||0)), ''],
    ['Loss /sec (Positions)', '$'+fmt(exec.total_loss_per_second_usd||0,8), exec.losses_per_second?.length ? exec.losses_per_second.map(l=>l.symbol+':'+fmt(l.loss_per_second_usd,8)+'/s').join('  ') : 'no open losses'],
    ['Capital Utilization',  fmt(acct.capital_utilization_pct||0,2)+'%', acct.capital_utilization_formula||''],
    ['CAGR (if sustained)',   fmt(acct.cagr_if_sustained_1day||0,4)+'%', acct.cagr_formula||''],
  ];
  el.innerHTML = `
    <table>
      <thead><tr><th>Metric</th><th>Value</th></tr></thead>
      <tbody>
        ${{rows.map(([label, val, note]) => `
          <tr>
            <td class="mono" style="font-size:11px;color:var(--muted);">${{esc(label)}}</td>
            <td>
              <span class="mono">${{esc(String(val))}}</span>
              ${{note ? `<div style="font-size:10px;color:rgba(0,194,255,0.6);font-family:var(--mono);">${{esc(note)}}</div>` : ''}}
            </td>
          </tr>
        `).join('')}}
      </tbody>
    </table>
  `;
}})();

// ── audit chain ───────────────────────────────────────────────────────────────
(function() {{
  const events = [...AUDIT].reverse();
  const panel = document.getElementById('audit-chain-panel');
  if (!panel) return;
  if (events.length === 0) {{
    panel.innerHTML = '<p class="neutral" style="padding:12px;">No audit chain events yet. Monitor must run at least one cycle.</p>';
    return;
  }}
  panel.innerHTML = events.map((e,i) => {{
    const payload = e.payload || {{}};
    const payloadStr = Object.entries(payload)
      .filter(([,v]) => v !== null && v !== undefined && v !== '')
      .map(([k,v]) => `${{k}}: ${{typeof v === 'object' ? JSON.stringify(v) : v}}`)
      .join(' · ');
    return `
      <div class="chain-row">
        <div class="chain-type">
          [${{i === 0 ? 'LATEST' : '#'+i}}] ${{esc(e.event_type||'')}}
          <span style="color:var(--muted);font-size:10px;margin-left:8px;">${{esc(e.event_time_utc||'')}}</span>
        </div>
        <div style="font-size:12px;color:var(--text);margin:2px 0;">${{esc(payloadStr.slice(0,240))}}</div>
        <div class="chain-hash">
          prev: ${{esc((e.prev_hash||'').slice(0,32))}}…
          &nbsp;→&nbsp;
          hash: ${{esc((e.event_hash||'').slice(0,32))}}…
        </div>
      </div>
    `;
  }}).join('');
}})();

// ── shared gateway bridge ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {{
  if (!window.LumaDS) return;
  LumaDS.mount({{ intervalSec: 20, particleCount: 14 }});
  LumaDS.mountNodeRedStatus('infra-nr-main');
  LumaDS.mountExplainer('infra-luma-explainer-panel', 'analyst');
  if (LumaDS.mountHelmier) {{
    LumaDS.mountHelmier('infra-helmier-proof-panel', {{ intervalSec: 45 }});
  }}

  async function loadInfraSnapshot() {{
    const d = await LumaDS.gwSnapshot();
    if (!d) return;
    const paper = d.paper || {{}};
    const infra = d.infra || {{}};
    const harmonic = d.harmonic || {{}};
    LumaDS.setText('infraSnapEquity', paper.equity_text || '—');
    LumaDS.setText('infraSnapPnl', paper.net_pnl_text || '—');
    LumaDS.setText('infraSnapWinRate', paper.win_rate_pct !== undefined ? String(Number(paper.win_rate_pct || 0).toFixed(1)) + '%' : '—');
    LumaDS.setText('infraSnapClosedTrades', String(paper.closed_trades || 0));
    LumaDS.setText('infraTopLane', infra.top_lane || harmonic.top_domain || '—');
    LumaDS.setText('infraActiveSurface', infra.active_surface_text || '—');
    LumaDS.setText('infraSnapshotStamp', (d.generated_utc || '—').replace('T', ' ').slice(0, 19));
  }}

  async function loadInfraUnity() {{
    const d = await LumaDS.gwUnityEdge();
    if (!d) return;
    LumaDS.setText('infraUnityNodeCount', String(d.node_count || 0));
    const top = document.getElementById('infra-unity-top');
    if (top && d.nodes && d.nodes.length) {{
      top.innerHTML = d.nodes.slice(0, 4).map(function (node) {{
        return '<div>' + String(node.label || node.name || node.id || 'node') + ' · score ' + String(node.score || node.weight || 'n/a') + '</div>';
      }}).join('');
    }}
  }}

  loadInfraSnapshot();
  loadInfraUnity();
  setInterval(loadInfraSnapshot, 30000);
  setInterval(loadInfraUnity, 30000);
}});

</script>
</body>
</html>"""


def build_and_save() -> None:
    status = load_json(CONSTRAINT_STATUS_FILE, {})
    audit_events = load_jsonl_tail(AUDIT_CHAIN_FILE, 60)
    html = build_html(status, audit_events)
    for html_out in HTML_OUTS:
        html_out.parent.mkdir(parents=True, exist_ok=True)
        html_out.write_text(html, encoding="utf-8")


def main() -> None:
    # Singleton lock
    _lock = ROOT / "run" / "build_infra_audit_dashboard.lock"
    _lock.parent.mkdir(parents=True, exist_ok=True)
    if _lock.exists():
        try:
            _pid = int(_lock.read_text().strip())
            if _pid != os.getpid():
                os.kill(_pid, 0)
                print(f"[singleton] build_infra_audit_dashboard already running as PID {_pid} — exiting.")
                raise SystemExit(0)
        except (ValueError, OSError, SystemError):
            pass
    _lock.write_text(str(os.getpid()))
    atexit.register(lambda: _lock.unlink(missing_ok=True))

    parser = argparse.ArgumentParser(description="Infra audit dashboard builder")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=float, default=4.0, help="Rebuild interval (seconds)")
    args = parser.parse_args()

    print("INFRA AUDIT DASHBOARD BUILDER")
    print(f"Input : {CONSTRAINT_STATUS_FILE}")
    for html_out in HTML_OUTS:
      print(f"Output: {html_out}")
    print(f"Loop  : {args.loop}  |  Interval: {args.interval}s")

    while True:
      try:
        build_and_save()
        print(f"[{time.strftime('%H:%M:%S')}] Dashboard rebuilt -> {HTML_OUTS[0]} (+ root mirror)")
      except Exception as exc:
        print(f"[ERROR] {exc}")
      if not args.loop:
        break
      time.sleep(args.interval)


if __name__ == "__main__":
    main()
