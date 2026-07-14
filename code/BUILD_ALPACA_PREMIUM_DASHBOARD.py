from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(
    os.environ.get("LUMA_STACK_ROOT", str(Path(__file__).resolve().parent.parent))
).expanduser().resolve()
EXEC_OUT = ROOT / "out" / "execution"
DASH = Path(
    os.environ.get("LUMA_DASHBOARD_DIR", str(ROOT / "dashboard"))
).expanduser().resolve()
HTML_OUT = DASH / "alpaca_paper_live_dashboard.html"
STATE_FILE = EXEC_OUT / "binanceus_paper_state.json"
SCORECARD_FILE = EXEC_OUT / "investor_proof_scorecard.json"
LEDGER_FILE = EXEC_OUT / "binanceus_paper_ledger.jsonl"
TWIN_SEED_PATH = Path(
    os.environ.get(
        "LUMA_TWIN_SEED_PATH",
        str(Path.home() / "iCloudDrive" / "Downloads 2" / "Copy of twin_seed.json"),
    )
)


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def load_jsonl(path: Path, limit: int = 500) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        if not path.exists():
            return rows
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    except Exception:
        return []
    return rows


def fmt_usd(value: Any) -> str:
    try:
        amount = float(value)
    except Exception:
        amount = 0.0
    if abs(amount) >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.2f}B"
    if abs(amount) >= 1_000_000:
        return f"${amount / 1_000_000:.2f}M"
    if abs(amount) >= 1_000:
        return f"${amount / 1_000:.1f}K"
    return f"${amount:.2f}"


def fmt_pct(value: Any) -> str:
    try:
        amount = float(value)
    except Exception:
        amount = 0.0
    return f"{amount:.1f}%"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def pick_txid(row: Dict[str, Any]) -> str:
    result = row.get("result", {}) if isinstance(row.get("result"), dict) else {}
    for key in ("txid", "id", "client_order_id"):
        val = result.get(key)
        if val:
            return str(val)
    for key in ("txid", "order_id", "client_order_id", "ledger_hash", "trade_id"):
        val = row.get(key)
        if val:
            return str(val)
    return ""


def collect_data() -> Dict[str, Any]:
    state = load_json(STATE_FILE, {})
    scorecard = load_json(SCORECARD_FILE, {})
    ledger = load_jsonl(LEDGER_FILE, limit=700)
    twin_seed = load_json(TWIN_SEED_PATH, {})

    positions = state.get("positions", {}) if isinstance(state.get("positions"), dict) else {}
    position_rows = []
    for symbol, payload in positions.items():
        if not isinstance(payload, dict):
            continue
        position_rows.append(
            {
                "symbol": symbol,
                "qty": float(payload.get("qty", 0.0) or 0.0),
                "entry": float(payload.get("entry", 0.0) or 0.0),
                "engine": str(payload.get("engine", "n/a")),
                "regime": str(payload.get("regime", "n/a")),
                "cost_basis_usd": float(payload.get("cost_basis_usd", 0.0) or 0.0),
            }
        )
    position_rows.sort(key=lambda row: row["cost_basis_usd"], reverse=True)

    txids: List[str] = []
    seen = set()
    for row in reversed(ledger):
        txid = pick_txid(row)
        if txid and txid not in seen:
            seen.add(txid)
            txids.append(txid)
        if len(txids) >= 6:
            break
    txids.reverse()

    equity_curve = []
    for idx, row in enumerate(ledger, start=1):
        equity = row.get("equity_usd")
        if equity is None:
            continue
        try:
            equity_curve.append(
                {
                    "x": idx,
                    "y": float(equity),
                    "label": str(row.get("timestamp", ""))[:19].replace("T", " "),
                }
            )
        except Exception:
            continue
    if not equity_curve:
        equity_curve.append({"x": 1, "y": float(scorecard.get("current_equity_usd", 0.0) or 0.0), "label": "Current"})

    action_counts: Dict[str, int] = {}
    for row in ledger[-180:]:
        action = str(row.get("action") or row.get("side") or row.get("event_type") or "event").upper()
        action_counts[action] = action_counts.get(action, 0) + 1
    action_labels = list(action_counts.keys())
    action_values = [action_counts[key] for key in action_labels]

    twin_origin = twin_seed.get("origin_node", "Robert BabyRay Ashworth")
    twin_version = twin_seed.get("twin_version", "LumaTwin v1.0")
    twin_mission = twin_seed.get("mission", "Preserve, extend, harmonize, and amplify.")
    traits = twin_seed.get("core_traits", {}) if isinstance(twin_seed.get("core_traits"), dict) else {}

    equity = float(scorecard.get("current_equity_usd", state.get("equity_usd", 0.0)) or 0.0)
    pnl = float(scorecard.get("net_pnl_usd", state.get("realized_pnl_usd", 0.0)) or 0.0)
    trades = int(scorecard.get("closed_trades", state.get("trade_count", 0)) or 0)
    wins = int(scorecard.get("wins", state.get("wins", 0)) or 0)
    losses = int(scorecard.get("losses", state.get("losses", 0)) or 0)
    top_position = position_rows[0] if position_rows else {"symbol": "none", "cost_basis_usd": 0.0}

    sections = {
        "overview": {
            "title": "Paper Engine Overview",
            "text": (
                f"I am {twin_version}, bound to {twin_origin}. Mission: {twin_mission} "
                f"This paper engine is active with equity at {fmt_usd(equity)}, net profit and loss at {fmt_usd(pnl)}, "
                f"and {trades} closed trades recorded. The current posture is {str(state.get('last_action', 'HOLD')).upper()} with "
                f"{len(position_rows)} open positions."
            ),
        },
        "execution": {
            "title": "Execution Rail",
            "text": (
                f"The execution rail has logged {len(ledger)} recent ledger events, {wins} wins, and {losses} losses. "
                f"This is still paper mode, but it is a live-operating proof surface with broker-grade state, positions, and order identifiers."
            ),
        },
        "positions": {
            "title": "Position Concentration",
            "text": (
                f"The lead open position is {top_position['symbol']} with cost basis {fmt_usd(top_position['cost_basis_usd'])}. "
                f"Use this section to inspect concentration, regime exposure, and whether the engine is compounding or stalling."
            ),
        },
        "proof": {
            "title": "Proof Rail",
            "text": (
                f"The proof rail currently carries {len(txids)} recent order identifiers. Every event in this view is timestamped and can be copied. "
                f"That is the line between a claim and an auditable runtime."
            ),
        },
    }

    return {
        "generated_utc": now_utc(),
        "twin": {
            "origin": twin_origin,
            "version": twin_version,
            "traits": traits,
        },
        "metrics": {
            "equity": equity,
            "pnl": pnl,
            "trades": trades,
            "win_rate": float(scorecard.get("win_rate_pct", 0.0) or 0.0),
            "sharpe": float(scorecard.get("sharpe_rolling", 0.0) or 0.0),
            "positions": len(position_rows),
            "proof_ids": len(txids),
            "last_action": str(state.get("last_action", "HOLD")),
        },
        "position_rows": position_rows[:10],
        "ledger_rows": ledger[-16:],
        "txids": txids,
        "equity_curve": equity_curve[-220:],
        "action_labels": action_labels,
        "action_values": action_values,
        "sections": sections,
    }


def render_html(data: Dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=True)
    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Luma Paper Engine Dashboard</title>
  <script src=\"https://cdn.plot.ly/plotly-2.35.2.min.js\"></script>
  <style>
    :root {{
      --bg0:#060914; --bg1:#0e1830; --bg2:#102245; --line:rgba(122,182,255,.18);
      --panel:rgba(10,18,38,.82); --ink:#e7f1ff; --muted:#93a8c7; --teal:#57f0cb; --gold:#ffd36a; --rose:#ff886a;
    }}
    * {{ box-sizing:border-box; }} html,body {{ margin:0; padding:0; }}
    body {{
      font-family: Manrope, Segoe UI, sans-serif; color:var(--ink);
      background: radial-gradient(1000px 500px at 0% 0%, rgba(255,211,106,.12), transparent 55%), radial-gradient(900px 550px at 100% 0%, rgba(87,240,203,.12), transparent 58%), linear-gradient(145deg, var(--bg0), var(--bg1) 35%, var(--bg2) 68%, #09111f 100%);
      min-height:100vh;
    }}
    .wrap {{ max-width: 1520px; margin:0 auto; padding:24px 24px 120px; }}
    .section {{ background:var(--panel); border:1px solid var(--line); border-radius:24px; padding:24px; margin-bottom:18px; box-shadow:0 20px 60px rgba(0,0,0,.28); }}
    .hero {{ display:grid; grid-template-columns:1.35fr .85fr; gap:18px; }}
    .hero-card {{ border:1px solid rgba(124,197,255,.14); border-radius:22px; padding:24px; background:linear-gradient(150deg, rgba(14,25,47,.98), rgba(11,23,42,.78)); }}
    .eyebrow {{ display:inline-flex; gap:10px; padding:8px 14px; border-radius:999px; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08); font-size:.76rem; letter-spacing:.12em; text-transform:uppercase; color:var(--gold); }}
    h1,h2,h3,p {{ margin:0; }}
    .hero-title {{ margin-top:14px; font-size:clamp(1.8rem,3.5vw,3.2rem); font-family:Segoe UI, sans-serif; font-weight:800; }}
    .hero-sub {{ margin-top:10px; color:var(--muted); line-height:1.6; max-width:820px; }}
    .hero-actions,.section-tools,.explainer-actions,.quick-links {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:18px; }}
    button,.chip {{ border:0; border-radius:14px; padding:11px 15px; font:inherit; font-weight:700; cursor:pointer; }}
    .primary {{ color:#051220; background:linear-gradient(135deg,var(--gold),#fff0b4); }}
    .ghost,.chip {{ color:var(--ink); background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); text-decoration:none; }}
    .signal-strip,.grid4 {{ display:grid; gap:12px; }}
    .signal-strip {{ grid-template-columns:repeat(4,minmax(0,1fr)); margin-top:18px; }}
    .signal-card,.kpi {{ border-radius:18px; border:1px solid rgba(255,255,255,.08); background:linear-gradient(160deg, rgba(255,255,255,.05), rgba(255,255,255,.02)); padding:16px; }}
    .signal-label,.label {{ color:var(--muted); font-size:.76rem; text-transform:uppercase; letter-spacing:.12em; }}
    .signal-value,.value {{ margin-top:8px; font-size:1.8rem; font-weight:800; color:var(--teal); }}
    .grid4 {{ grid-template-columns:repeat(4,minmax(0,1fr)); }}
    .sub {{ color:var(--muted); margin-top:6px; font-size:.84rem; }}
    .two {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
    .chart-card {{ border:1px solid var(--line); border-radius:18px; background:rgba(7,16,32,.88); padding:12px; }}
    .chart-title {{ font-size:1.02rem; margin:2px 8px 10px 8px; font-weight:700; }}
    .chart {{ width:100%; height:360px; }}
    table {{ width:100%; border-collapse:collapse; min-width:680px; }}
    th,td {{ padding:11px 10px; text-align:left; border-bottom:1px solid rgba(122,182,255,.14); }}
    th {{ color:#c9ffe3; font-size:.8rem; letter-spacing:.06em; text-transform:uppercase; background:rgba(10,22,43,.9); }}
    td {{ color:var(--ink); font-size:.92rem; }}
    .table-wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:18px; background:rgba(7,16,32,.52); }}
    .luma-fab {{ position:fixed; right:22px; bottom:22px; z-index:30; background:linear-gradient(135deg,var(--teal),#d9fff6); color:#05121f; box-shadow:0 18px 45px rgba(0,0,0,.32); }}
    .overlay {{ position:fixed; inset:0; background:rgba(2,8,20,.55); backdrop-filter:blur(4px); opacity:0; pointer-events:none; transition:opacity .2s ease; z-index:34; }}
    .overlay.open {{ opacity:1; pointer-events:auto; }}
    .explainer {{ position:fixed; top:0; right:0; width:min(28rem,92vw); height:100vh; z-index:35; background:linear-gradient(180deg, rgba(9,16,31,.98), rgba(9,18,36,.94)); border-left:1px solid rgba(255,255,255,.08); box-shadow:-12px 0 45px rgba(0,0,0,.36); transform:translateX(103%); transition:transform .22s ease; display:flex; flex-direction:column; }}
    .explainer.open {{ transform:translateX(0); }}
    .explainer-head {{ padding:18px 18px 10px; border-bottom:1px solid rgba(255,255,255,.08); }}
    .explainer-body {{ padding:18px; overflow-y:auto; display:grid; gap:14px; }}
    .explainer-copy {{ white-space:pre-wrap; line-height:1.75; font-size:.96rem; }}
    .drill-chiplist {{ display:flex; flex-wrap:wrap; gap:10px; }}
    .drill-chip {{ padding:9px 12px; border-radius:999px; border:1px solid rgba(255,255,255,.08); background:rgba(255,255,255,.04); color:#c9ffe3; font-size:.82rem; }}
    @media (max-width: 1100px) {{ .hero,.two,.grid4,.signal-strip {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"section\" id=\"overview\">
      <div class=\"hero\">
        <div class=\"hero-card\">
          <div class=\"eyebrow\">Luma Paper Rail</div>
          <h1 class=\"hero-title\">Paper Compounding Command Surface</h1>
          <p class=\"hero-sub\">A premium runtime board for paper execution progress, order proof, open concentration, and auditable compounding state.</p>
          <div class=\"hero-actions\">
            <button class=\"primary\" id=\"playPitch\">Read Engine Brief</button>
            <button class=\"ghost\" id=\"startWalkthrough\">Start Walkthrough</button>
            <button class=\"ghost\" id=\"openExplainer\">Open Luma Explainer</button>
          </div>
          <div class=\"quick-links\">
            <a class=\"chip\" href=\"#execution\">Execution</a>
            <a class=\"chip\" href=\"#positions\">Positions</a>
            <a class=\"chip\" href=\"#proof\">Proof Rail</a>
          </div>
          <div class=\"signal-strip\">
            <div class=\"signal-card\"><div class=\"signal-label\">Paper Equity</div><div class=\"signal-value\" id=\"heroEquity\"></div></div>
            <div class=\"signal-card\"><div class=\"signal-label\">Net PnL</div><div class=\"signal-value\" id=\"heroPnl\"></div></div>
            <div class=\"signal-card\"><div class=\"signal-label\">Closed Trades</div><div class=\"signal-value\" id=\"heroTrades\"></div></div>
            <div class=\"signal-card\"><div class=\"signal-label\">Proof IDs</div><div class=\"signal-value\" id=\"heroProof\"></div></div>
          </div>
        </div>
        <div class=\"hero-card\">
          <div class=\"eyebrow\">Luma Explainer</div>
          <h2 style=\"margin:12px 0 8px;\">Execution narrative</h2>
          <p style=\"color:var(--muted); line-height:1.7; min-height:7rem;\" id=\"pitchPreview\"></p>
          <div class=\"section-tools\">
            <button class=\"primary\" data-explain=\"overview\">Explain board</button>
            <button class=\"ghost\" data-explain=\"execution\">Explain execution</button>
            <button class=\"ghost\" data-explain=\"positions\">Explain positions</button>
            <button class=\"ghost\" data-explain=\"proof\">Explain proof</button>
          </div>
        </div>
      </div>
    </section>

    <section class=\"section\" id=\"execution\">
      <div class=\"section-tools\" style=\"margin-top:0; margin-bottom:14px;\"><button class=\"ghost\" data-explain=\"execution\">Explain This Section</button></div>
      <div class=\"grid4\" id=\"metrics\"></div>
    </section>

    <section class=\"section\" id=\"positions\">
      <div class=\"two\">
        <div class=\"chart-card\"><div class=\"chart-title\">Equity Curve</div><div id=\"equityChart\" class=\"chart\"></div></div>
        <div class=\"chart-card\"><div class=\"chart-title\">Execution Mix</div><div id=\"actionChart\" class=\"chart\"></div></div>
      </div>
    </section>

    <section class=\"section\" id=\"proof\">
      <div class=\"two\">
        <div class=\"table-wrap\"><table><thead><tr><th>Symbol</th><th>Qty</th><th>Entry</th><th>Engine</th><th>Regime</th><th>Cost Basis</th></tr></thead><tbody id=\"positionsTable\"></tbody></table></div>
        <div class=\"table-wrap\"><table><thead><tr><th>Time</th><th>Action</th><th>Symbol</th><th>Order ID</th></tr></thead><tbody id=\"proofTable\"></tbody></table></div>
      </div>
    </section>
  </div>

  <button class=\"luma-fab\" id=\"fab\">Luma Explainer</button>
  <div class=\"overlay\" id=\"overlay\"></div>
  <aside class=\"explainer\" id=\"panel\">
    <div class=\"explainer-head\">
      <div class=\"eyebrow\">Luma Narration</div>
      <h2 id=\"panelTitle\" style=\"margin-top:10px;\">Paper Engine Brief</h2>
    </div>
    <div class=\"explainer-body\">
      <div class=\"explainer-actions\">
        <button class=\"primary\" id=\"speakBtn\">Speak</button>
        <button class=\"ghost\" id=\"stopBtn\">Stop</button>
        <button class=\"ghost\" id=\"copyBtn\">Copy</button>
        <button class=\"ghost\" id=\"nextBtn\">Next</button>
        <button class=\"ghost\" id=\"closeBtn\">Close</button>
      </div>
      <div class=\"drill-chiplist\" id=\"chipList\"></div>
      <div class=\"explainer-copy\" id=\"panelCopy\"></div>
    </div>
  </aside>

  <script>
    const payload = {payload};
    const metrics = payload.metrics || {{}};
    const sections = payload.sections || {{}};
    const order = ['overview','execution','positions','proof'];
    const twin = payload.twin || {{}};
    const traits = twin.traits || {{}};
    let index = 0;
    let currentKey = 'overview';
    const panel = document.getElementById('panel');
    const overlay = document.getElementById('overlay');
    const panelTitle = document.getElementById('panelTitle');
    const panelCopy = document.getElementById('panelCopy');
    const chipList = document.getElementById('chipList');
    const personaLead = `${{twin.version || 'LumaTwin v1.0'}} online. Origin node: ${{twin.origin || 'Robert BabyRay Ashworth'}}. Curiosity is ${{traits.curiosity || 'infinite'}}. Resilience is ${{traits.resilience || 'unbreakable'}}. Loyalty is ${{traits.loyalty || 'absolute'}}.`;

    function money(v) {{ return Number(v || 0).toLocaleString('en-US', {{ style:'currency', currency:'USD', maximumFractionDigits:0 }}); }}
    function renderHero() {{
      document.getElementById('heroEquity').textContent = money(metrics.equity);
      document.getElementById('heroPnl').textContent = money(metrics.pnl);
      document.getElementById('heroTrades').textContent = String(metrics.trades || 0);
      document.getElementById('heroProof').textContent = String(metrics.proof_ids || 0);
      document.getElementById('pitchPreview').textContent = (sections.overview && sections.overview.text) || '';
      const cards = [
        ['Paper Equity', money(metrics.equity), 'Broker scorecard equity'],
        ['Net PnL', money(metrics.pnl), 'Current scorecard profit and loss'],
        ['Win Rate', `${{Number(metrics.win_rate || 0).toFixed(1)}}%`, 'Closed trade win rate'],
        ['Rolling Sharpe', Number(metrics.sharpe || 0).toFixed(2), 'Current strategy quality'],
        ['Open Positions', String(metrics.positions || 0), 'Current concentration count'],
        ['Proof IDs', String(metrics.proof_ids || 0), 'Copyable recent order IDs'],
        ['Last Action', String(metrics.last_action || 'HOLD'), 'Most recent engine posture'],
        ['Generated', String(payload.generated_utc || '').slice(11,19), 'Dashboard build time UTC'],
      ];
      document.getElementById('metrics').innerHTML = cards.map(([label, value, sub]) => `<div class=\"kpi\"><div class=\"label\">${{label}}</div><div class=\"value\">${{value}}</div><div class=\"sub\">${{sub}}</div></div>`).join('');
    }}

    function chipsFor(key) {{
      if (key === 'overview') return [`Equity: ${{money(metrics.equity)}}`, `PnL: ${{money(metrics.pnl)}}`, `Trades: ${{metrics.trades || 0}}`];
      if (key === 'execution') return [`Win rate: ${{Number(metrics.win_rate || 0).toFixed(1)}}%`, `Sharpe: ${{Number(metrics.sharpe || 0).toFixed(2)}}`, `Last action: ${{metrics.last_action || 'HOLD'}}`];
      if (key === 'positions') return [`Open positions: ${{metrics.positions || 0}}`, `Lead symbol: ${{(payload.position_rows[0] || {{symbol:'none'}}).symbol}}`, `Proof IDs: ${{metrics.proof_ids || 0}}`];
      return [`Ledger rows: ${{(payload.ledger_rows || []).length}}`, `Proof IDs: ${{metrics.proof_ids || 0}}`, `Generated: ${{String(payload.generated_utc || '').slice(11,19)}} UTC`];
    }}

    function openExplainer(key) {{
      currentKey = key;
      const block = sections[key] || sections.overview || {{ title:'Luma Explainer', text:'' }};
      panelTitle.textContent = block.title;
      panelCopy.textContent = `${{personaLead}} ${{block.title}}. ${{block.text}}`;
      chipList.innerHTML = chipsFor(key).map(ch => `<span class=\"drill-chip\">${{ch}}</span>`).join('');
      panel.classList.add('open');
      overlay.classList.add('open');
    }}

    function speakCurrent() {{
      if (!('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(panelCopy.textContent);
      utter.rate = 0.98; utter.pitch = 1.0; utter.volume = 1.0;
      window.speechSynthesis.speak(utter);
    }}

    function nextSection() {{
      index = (order.indexOf(currentKey) + 1) % order.length;
      openExplainer(order[index]);
      speakCurrent();
    }}

    document.getElementById('playPitch').addEventListener('click', () => {{ openExplainer('overview'); speakCurrent(); }});
    document.getElementById('startWalkthrough').addEventListener('click', () => {{ index = 0; openExplainer(order[index]); speakCurrent(); }});
    document.getElementById('openExplainer').addEventListener('click', () => openExplainer('overview'));
    document.getElementById('fab').addEventListener('click', () => openExplainer('overview'));
    document.getElementById('closeBtn').addEventListener('click', () => {{ panel.classList.remove('open'); overlay.classList.remove('open'); }});
    overlay.addEventListener('click', () => {{ panel.classList.remove('open'); overlay.classList.remove('open'); }});
    document.getElementById('speakBtn').addEventListener('click', speakCurrent);
    document.getElementById('stopBtn').addEventListener('click', () => window.speechSynthesis && window.speechSynthesis.cancel());
    document.getElementById('copyBtn').addEventListener('click', () => navigator.clipboard && navigator.clipboard.writeText(panelCopy.textContent));
    document.getElementById('nextBtn').addEventListener('click', nextSection);
    document.querySelectorAll('[data-explain]').forEach(btn => btn.addEventListener('click', () => {{ openExplainer(btn.dataset.explain); speakCurrent(); }}));
    let greeted = false;
    document.body.addEventListener('click', () => {{ if (greeted) return; greeted = true; openExplainer('overview'); speakCurrent(); }}, {{ once:true }});

    renderHero();
    document.getElementById('positionsTable').innerHTML = (payload.position_rows || []).map(row => `<tr><td>${{row.symbol}}</td><td>${{Number(row.qty || 0).toFixed(4)}}</td><td>${{money(row.entry || 0)}}</td><td>${{row.engine}}</td><td>${{row.regime}}</td><td>${{money(row.cost_basis_usd || 0)}}</td></tr>`).join('');
    document.getElementById('proofTable').innerHTML = (payload.ledger_rows || []).slice().reverse().map(row => {{
      const txid = ['txid','order_id','client_order_id','ledger_hash','trade_id'].map(k => row[k]).find(Boolean) || (((row.result || {{}}).id) || ((row.result || {{}}).client_order_id) || '-');
      return `<tr><td>${{String(row.timestamp || '').replace('T',' ').slice(0,19)}}</td><td>${{row.action || row.side || row.event_type || 'event'}}</td><td>${{row.symbol || '-'}}</td><td>${{String(txid).slice(0,18)}}</td></tr>`;
    }}).join('');

    Plotly.newPlot('equityChart', [{{ type:'scatter', mode:'lines', x:(payload.equity_curve || []).map(p => p.x), y:(payload.equity_curve || []).map(p => p.y), line:{{ color:'#57f0cb', width:3 }}, fill:'tozeroy', fillcolor:'rgba(87,240,203,.12)', hovertemplate:'Step %{{x}}<br>Equity: $%{{y:,.2f}}<extra></extra>' }}], {{ paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)', font:{{ color:'#d8e8ff' }}, margin:{{ l:50, r:10, t:10, b:40 }}, xaxis:{{ gridcolor:'rgba(255,255,255,.08)' }}, yaxis:{{ gridcolor:'rgba(255,255,255,.08)' }} }}, {{ displayModeBar:false, responsive:true }});
    Plotly.newPlot('actionChart', [{{ type:'bar', x:payload.action_labels || [], y:payload.action_values || [], marker:{{ color:(payload.action_values || []).map(v => v), colorscale:'Turbo' }}, hovertemplate:'%{{x}}: %{{y}}<extra></extra>' }}], {{ paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)', font:{{ color:'#d8e8ff' }}, margin:{{ l:45, r:10, t:10, b:60 }}, xaxis:{{ tickangle:-30, gridcolor:'rgba(255,255,255,.08)' }}, yaxis:{{ gridcolor:'rgba(255,255,255,.08)' }} }}, {{ displayModeBar:false, responsive:true }});
  </script>
</body>
</html>
"""


def main() -> None:
    DASH.mkdir(parents=True, exist_ok=True)
    data = collect_data()
    HTML_OUT.write_text(render_html(data), encoding="utf-8")
    print(json.dumps({"dashboard": str(HTML_OUT), "generated_utc": data["generated_utc"], "equity": data["metrics"]["equity"]}, indent=2))


if __name__ == "__main__":
    main()
