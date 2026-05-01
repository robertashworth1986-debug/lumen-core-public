import argparse
import json
import time
from pathlib import Path


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"
DASH = ROOT / "dashboard"

STATE_FILE = OUT / "paper_trade_state.json"
LEDGER_FILE = OUT / "paper_trade_ledger.jsonl"
STATUS_FILE = EXEC_OUT / "alpaca_paper_status.json"
PROJECTION_FILE = EXEC_OUT / "alpaca_paper_ultra_aggressive_projection.json"
HTML_OUT = DASH / "alpaca_paper_dashboard.html"


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def load_jsonl(path: Path):
    rows = []
    try:
        if path.exists():
            for raw in path.read_text(encoding="utf-8").splitlines():
                raw = raw.strip()
                if raw:
                    rows.append(json.loads(raw))
    except Exception:
        pass
    return rows


def build_html(state: dict, status: dict, ledger: list[dict], projection: dict) -> str:
    build_generated_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    embedded = json.dumps(
        {
            "state": state,
            "status": status,
            "ledger": ledger[-120:],
            "projection": projection,
            "build_generated_utc": build_generated_utc,
        },
        ensure_ascii=True,
    )
    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <meta http-equiv="refresh" content="10" />
  <title>Alpaca Paper Dashboard</title>
  <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
  <style>
    :root {{
      --bg: #0a1117;
      --panel: rgba(15, 30, 42, 0.82);
      --panel-strong: rgba(18, 40, 58, 0.94);
      --line: rgba(110, 190, 220, 0.20);
      --text: #e8f3f7;
      --muted: #8aa6b5;
      --accent: #a3ff12;
      --accent-2: #00c2ff;
      --warn: #ffd166;
      --danger: #ff6b6b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, 'Times New Roman', serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(0, 194, 255, 0.20), transparent 28%),
        radial-gradient(circle at top right, rgba(163, 255, 18, 0.12), transparent 20%),
        linear-gradient(180deg, #071018 0%, #0a1117 100%);
    }}
    .wrap {{ max-width: 1440px; margin: 0 auto; padding: 28px; }}
    .hero {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 20px;
      margin-bottom: 20px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 22px;
      backdrop-filter: blur(8px);
      box-shadow: 0 18px 50px rgba(0,0,0,0.25);
    }}
    h1, h2, h3, p {{ margin: 0; }}
    .eyebrow {{ color: var(--accent-2); font-size: 12px; letter-spacing: 0.18em; text-transform: uppercase; margin-bottom: 10px; }}
    .headline {{ font-size: 42px; line-height: 1.05; margin-bottom: 10px; }}
    .sub {{ color: var(--muted); font-size: 16px; max-width: 60ch; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }}
    .metric-label {{ color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .metric-value {{ font-family: 'Courier New', monospace; font-size: 28px; margin-top: 8px; color: var(--accent); }}
    .metric-note {{ margin-top: 6px; color: var(--muted); font-size: 13px; }}
    .two {{ display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 20px; margin-bottom: 20px; }}
    .three {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
    .single {{ display: grid; grid-template-columns: 1fr; gap: 20px; margin-bottom: 20px; }}
    .live-strip {{
      margin-top: 14px;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--line);
      background: rgba(0, 194, 255, 0.08);
      font-family: 'Courier New', monospace;
      font-size: 12px;
      color: #d7f7ff;
      line-height: 1.5;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px 8px; border-bottom: 1px solid var(--line); text-align: left; font-size: 13px; }}
    th {{ color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; font-size: 11px; }}
    .tag {{ display: inline-block; padding: 4px 8px; border-radius: 999px; font-size: 12px; }}
    .tag-paper {{ background: rgba(255, 209, 102, 0.12); color: var(--warn); }}
    .tag-liveoff {{ background: rgba(255, 107, 107, 0.12); color: var(--danger); }}
    .note {{ color: var(--muted); font-size: 14px; line-height: 1.5; }}
    .txid-row {{ display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--line); }}
    .txid-id {{ font-family: 'Courier New', monospace; font-size: 12px; color: var(--text); word-break: break-all; }}
    .copy-btn {{
      background: rgba(0,194,255,0.15);
      border: 1px solid rgba(0,194,255,0.35);
      color: #d7f7ff;
      border-radius: 10px;
      padding: 6px 10px;
      font-size: 12px;
      cursor: pointer;
    }}
    .copy-btn:hover {{ background: rgba(0,194,255,0.28); }}
    canvas {{ width: 100% !important; height: 320px !important; }}
    @media (max-width: 1100px) {{
      .hero, .two, .three, .grid {{ grid-template-columns: 1fr; }}
      .headline {{ font-size: 32px; }}
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"hero\">
      <section class=\"panel\">
        <div class=\"eyebrow\">Investor Demo Layer</div>
        <h1 class=\"headline\">Alpaca Paper Compounding Dashboard</h1>
        <p class=\"sub\">Dedicated paper-mode view for the $100,000 aggressive compounding demo. Kraken armed false is expected here because runtime mode is paper and live orders are intentionally disabled.</p>
      </section>
      <section class=\"panel\">
        <div class=\"eyebrow\">Execution State</div>
        <p><span class=\"tag tag-paper\">Paper Mode</span> <span class=\"tag tag-liveoff\">Kraken Live Off</span></p>
        <div id=\"status-note\" class=\"note\" style=\"margin-top:14px;\"></div>
        <div class="live-strip" id="live-strip"></div>
      </section>
    </div>

    <section class=\"grid\" id=\"metrics\"></section>

    <div class=\"two\">
      <section class=\"panel\">
        <div class=\"eyebrow\">Equity Curve</div>
        <canvas id=\"equityChart\"></canvas>
      </section>
      <section class=\"panel\">
        <div class=\"eyebrow\">Top Candidate</div>
        <div id=\"candidate\"></div>
      </section>
    </div>

    <div class=\"two\">
      <section class=\"panel\">
        <div class=\"eyebrow\">Projection Ladder</div>
        <canvas id=\"projectionChart\"></canvas>
      </section>
      <section class=\"panel\">
        <div class=\"eyebrow\">Runtime Profile</div>
        <div id=\"runtime\" class=\"note\"></div>
      </section>
    </div>

    <div class=\"three\">
      <section class=\"panel\">
        <div class=\"eyebrow\">Recent Ledger</div>
        <div id=\"ledger\"></div>
      </section>
      <section class=\"panel\">
        <div class=\"eyebrow\">Open Positions</div>
        <div id=\"positions\"></div>
      </section>
      <section class=\"panel\">
        <div class=\"eyebrow\">Scenario Table</div>
        <div id=\"scenarios\"></div>
      </section>
    </div>

    <div class="single">
      <section class="panel">
        <div class="eyebrow">Live TXID Feed</div>
        <div id="txids"></div>
      </section>
    </div>
  </div>

  <script>
    const data = {embedded};
    const state = data.state || {{}};
    const status = data.status || {{}};
    const ledger = data.ledger || [];
    const projection = data.projection || {{}};
    const buildGeneratedUtc = data.build_generated_utc || 'n/a';
    const scenarios = projection.scenarios || [];

    function currency(v) {{
      const n = Number(v || 0);
      return n.toLocaleString(undefined, {{ style: 'currency', currency: 'USD', maximumFractionDigits: 0 }});
    }}

    function pct(v) {{
      return `${{(Number(v || 0) * 100).toFixed(1)}}%`;
    }}

    const account = status.account || {{}};
    const metrics = [
      ['Paper Equity', currency(account.equity), 'Current Alpaca paper account equity'],
      ['Paper Cash', currency(account.cash), 'Current available cash'],
      ['Buying Power', currency(account.buying_power), 'Broker reported buying power'],
      ['Open Positions', String((status.positions || []).length), 'Current open paper positions'],
    ];
    document.getElementById('metrics').innerHTML = metrics.map(([label, value, note]) => `
      <section class="panel">
        <div class="metric-label">${{label}}</div>
        <div class="metric-value">${{value}}</div>
        <div class="metric-note">${{note}}</div>
      </section>
    `).join('');

    document.getElementById('status-note').textContent = status.status_note || 'Paper monitoring ready.';
    const statusGeneratedUtc = status.generated_utc || 'n/a';

    function renderLiveStrip() {{
      const now = new Date();
      document.getElementById('live-strip').innerHTML =
        `LIVE ${{now.toLocaleTimeString()}} | html: ${{buildGeneratedUtc}} | status: ${{statusGeneratedUtc}}`;
    }}
    renderLiveStrip();
    setInterval(renderLiveStrip, 1000);

    // Force periodic hard reload with a cache-busting query parameter.
    setTimeout(() => {{
      const next = new URL(window.location.href);
      next.searchParams.set('_ts', String(Date.now()));
      window.location.replace(next.toString());
    }}, 10000);

    const candidate = status.top_candidate || {{}};
    document.getElementById('candidate').innerHTML = candidate.symbol ? `
      <div class="metric-label">${{candidate.symbol}}</div>
      <div class="metric-value">Score ${{Number(candidate.score || 0).toFixed(2)}}</div>
      <div class="note" style="margin-top:10px;">
        Price: ${{currency(candidate.price)}}<br />
        Edge: ${{Number(candidate.edge_bps || 0).toFixed(1)}} bps<br />
        Confidence: ${{pct(candidate.confidence || 0)}}
      </div>
    ` : '<div class="note">No candidate available yet.</div>';

    const runtime = status.runtime || {{}};
    document.getElementById('runtime').innerHTML = `
      Starting Capital: <strong>${{currency(runtime.starting_capital_usd)}}</strong><br />
      Aggression Mode: <strong>${{runtime.aggression_mode || 'n/a'}}</strong><br />
      Reinvest Fraction: <strong>${{pct(runtime.reinvest_fraction || 0)}}</strong><br />
      Position Size: <strong>${{pct(runtime.position_size_pct || 0)}}</strong><br />
      Max Positions: <strong>${{runtime.max_positions || 0}}</strong><br />
      Universe Count: <strong>${{(runtime.symbols || []).length}}</strong><br />
      Loop Seconds: <strong>${{runtime.loop_seconds || 0}}</strong>
    `;

    document.getElementById('positions').innerHTML = (() => {{
      const positions = status.positions || [];
      if (!positions.length) return '<div class="note">No open paper positions.</div>';
      return `<table><thead><tr><th>Symbol</th><th>Qty</th><th>U P/L</th></tr></thead><tbody>${{positions.map(p => `<tr><td>${{p.symbol}}</td><td>${{Number(p.qty || 0).toFixed(4)}}</td><td>${{pct(p.unrealized_plpc || 0)}}</td></tr>`).join('')}}</tbody></table>`;
    }})();

    function pickOrderId(row) {{
      const result = row.result || {{}};
      if (result.txid) return String(result.txid);
      if (result.id) return String(result.id);
      if (result.client_order_id) return String(result.client_order_id);
      if (row.txid) return String(row.txid);
      if (row.order_id) return String(row.order_id);
      if (row.client_order_id) return String(row.client_order_id);
      return '-';
    }}

    function escapeHtml(value) {{
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }}

    function copyTxid(txid) {{
      if (!txid || txid === '-') return;
      navigator.clipboard.writeText(txid).catch(() => {{}});
    }}

    document.getElementById('ledger').innerHTML = (() => {{
      if (!ledger.length) return '<div class="note">No paper ledger events yet.</div>';
      const rows = ledger.slice(-12).reverse();
      return `<table><thead><tr><th>Time</th><th>Action</th><th>Symbol</th><th>Notional</th><th>Status</th><th>Order ID</th></tr></thead><tbody>${{rows.map(r => {{ const oid = pickOrderId(r); const oidShort = oid === '-' ? '-' : `${{oid.slice(0, 12)}}...`; return `<tr><td>${{String(r.timestamp || '').replace('T',' ').slice(0,19)}}</td><td>${{r.action || r.side || 'event'}}</td><td>${{r.symbol || '-'}}</td><td>${{r.notional_usd ? currency(r.notional_usd) : '-'}}</td><td>${{(r.result && r.result.status) ? r.result.status : '-'}}</td><td title="${{oid}}">${{oidShort}}</td></tr>`; }}).join('')}}</tbody></table>`;
    }})();

    document.getElementById('txids').innerHTML = (() => {{
      const rows = ledger
        .map(r => {{
          const txid = pickOrderId(r);
          return {{
            timestamp: String(r.timestamp || '').replace('T',' ').slice(0,19),
            action: r.action || r.side || 'event',
            symbol: r.symbol || '-',
            txid,
          }};
        }})
        .filter(r => r.txid && r.txid !== '-')
        .slice(-20)
        .reverse();

      if (!rows.length) return '<div class="note">No txids yet.</div>';
      return rows.map((r, i) => `
        <div class="txid-row">
          <div class="txid-id"><strong>${{escapeHtml(r.timestamp)}}</strong> | ${{escapeHtml(r.action)}} | ${{escapeHtml(r.symbol)}}<br />${{escapeHtml(r.txid)}}</div>
          <button class="copy-btn" onclick="copyTxid('${{escapeHtml(r.txid)}}')">Copy</button>
        </div>
      `).join('');
    }})();

    document.getElementById('scenarios').innerHTML = (() => {{
      if (!scenarios.length) return '<div class="note">Projection scenarios unavailable.</div>';
      return `<table><thead><tr><th>Scenario</th><th>Return</th><th>Sharpe</th><th>MDD</th></tr></thead><tbody>${{scenarios.map(s => `<tr><td>${{s.name}}</td><td>${{pct(s.annual_return)}}</td><td>${{Number(s.sharpe || 0).toFixed(2)}}</td><td>${{pct(s.mdd || 0)}}</td></tr>`).join('')}}</tbody></table>`;
    }})();

    const equityPoints = ledger.map((row, index) => ({{
      x: index + 1,
      y: Number(row.equity_usd || state.equity_usd || 0),
    }})).filter(p => Number.isFinite(p.y) && p.y > 0);
    if (!equityPoints.length && state.equity_usd) equityPoints.push({{ x: 1, y: Number(state.equity_usd) }});

    const notionalPoints = ledger
      .map((row, index) => ({{ x: index + 1, y: Number(row.notional_usd || 0) }}))
      .filter(p => Number.isFinite(p.y) && p.y > 0);

    new Chart(document.getElementById('equityChart'), {{
      type: 'line',
      data: {{
        datasets: [{{
          label: 'Paper Equity',
          data: equityPoints,
          borderColor: '#a3ff12',
          backgroundColor: 'rgba(163,255,18,0.12)',
          tension: 0.22,
          fill: true,
          yAxisID: 'y',
        }}, {{
          type: 'bar',
          label: 'Order Notional',
          data: notionalPoints,
          yAxisID: 'y1',
          backgroundColor: 'rgba(0,194,255,0.35)',
          borderColor: 'rgba(0,194,255,0.8)',
          borderWidth: 1,
        }}],
      }},
      options: {{
        plugins: {{ legend: {{ labels: {{ color: '#e8f3f7' }} }} }},
        scales: {{
          x: {{ ticks: {{ color: '#8aa6b5' }}, grid: {{ color: 'rgba(110,190,220,0.08)' }} }},
          y: {{ ticks: {{ color: '#8aa6b5' }}, grid: {{ color: 'rgba(110,190,220,0.08)' }} }},
          y1: {{
            position: 'right',
            ticks: {{ color: '#8aa6b5' }},
            grid: {{ display: false }},
          }},
        }},
      }},
    }});

    const ultra = scenarios.find(s => s.name === 'Ultra Aggressive Paper Case') || scenarios[0] || {{ milestones: [] }};
    new Chart(document.getElementById('projectionChart'), {{
      type: 'bar',
      data: {{
        labels: (ultra.milestones || []).map(m => '$' + Number(m.target || 0).toLocaleString()),
        datasets: [{{
          label: 'Years to target',
          data: (ultra.milestones || []).map(m => Number(m.years || 0)),
          backgroundColor: 'rgba(0,194,255,0.55)',
          borderColor: '#00c2ff',
          borderWidth: 1,
        }}],
      }},
      options: {{
        plugins: {{ legend: {{ labels: {{ color: '#e8f3f7' }} }} }},
        scales: {{
          x: {{ ticks: {{ color: '#8aa6b5' }}, grid: {{ display: false }} }},
          y: {{ ticks: {{ color: '#8aa6b5' }}, grid: {{ color: 'rgba(110,190,220,0.08)' }} }},
        }},
      }},
    }});
  </script>
</body>
</html>
"""


def build_once() -> dict:
  state = load_json(STATE_FILE, {})
  status = load_json(STATUS_FILE, {})
  ledger = load_jsonl(LEDGER_FILE)
  projection = load_json(PROJECTION_FILE, {})
  HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
  HTML_OUT.write_text(build_html(state, status, ledger, projection), encoding="utf-8")
  payload = {
    "dashboard": str(HTML_OUT),
    "ledger_rows": len(ledger),
    "generated_utc": status.get("generated_utc", state.get("generated_utc", "")),
  }
  print(json.dumps(payload, indent=2))
  return payload


def main():
  parser = argparse.ArgumentParser(description="Build Alpaca paper dashboard HTML")
  parser.add_argument("--loop", action="store_true", help="Continuously rebuild dashboard")
  parser.add_argument("--interval", type=int, default=5, help="Seconds between rebuilds in loop mode")
  args = parser.parse_args()

  interval = max(1, int(args.interval or 5))
  if not args.loop:
    build_once()
    return

  while True:
    build_once()
    time.sleep(interval)


if __name__ == "__main__":
    main()