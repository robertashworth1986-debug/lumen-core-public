import os, json, html
from pathlib import Path
import pandas as pd

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT  = ROOT / "out"
CFG  = ROOT / "config"
DASH = Path(r"C:\LumaTrader\dashboard")
DASH.mkdir(parents=True, exist_ok=True)

runtime_path = CFG / "runtime_control.json"
intent_path  = OUT / "kraken_order_intents.csv"
ticket_path  = OUT / "kraken_execution_tickets.csv"
status_path  = OUT / "execution_status.json"
source_path  = OUT / "live_source_status.json"
cred_path    = OUT / "credible_top10.csv"

def read_json(path, default=None):
    if default is None:
        default = {}
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def esc(x):
    return html.escape(str(x))

runtime = read_json(runtime_path, {
    "mode": "SHADOW",
    "kill_switch": "ON",
    "live_arm": "OFF",
    "max_notional_per_trade_usd": 25.0,
    "max_daily_loss_usd": 20.0,
    "max_open_positions": 1
})

source = read_json(source_path, {})
kraken_key_present = bool(os.environ.get("KRAKEN_API_KEY","").strip())
kraken_secret_present = bool(os.environ.get("KRAKEN_API_SECRET","").strip())

try:
    cred = pd.read_csv(cred_path) if cred_path.exists() else pd.DataFrame()
except Exception:
    cred = pd.DataFrame()

if not intent_path.exists():
    cols = ["generated_utc","symbol","side","score","mode","reason","max_notional_usd","status"]
    pd.DataFrame(columns=cols).to_csv(intent_path, index=False)

if not ticket_path.exists():
    cols = ["generated_utc","symbol","side","requested_notional_usd","mode","approval_state","ticket_note"]
    pd.DataFrame(columns=cols).to_csv(ticket_path, index=False)

try:
    intents = pd.read_csv(intent_path)
except Exception:
    intents = pd.DataFrame()

try:
    tickets = pd.read_csv(ticket_path)
except Exception:
    tickets = pd.DataFrame()

# build fresh shadow intents from current credible leaderboard
new_rows = []
if not cred.empty:
    top = cred.head(5).copy()
    for _, row in top.iterrows():
        file_name = str(row.get("file",""))
        symbol = "UNKNOWN"
        if "kraken" in file_name.lower():
            symbol = "KRAKEN_MARKET_PROXY"
        side = "LONG" if float(row.get("test_sharpe_clean", row.get("test_sharpe", 0)) or 0) > 0 else "FLAT"
        score = float(row.get("investor_score_clean", 0) or 0)
        reason = f"{row.get('flow','')} / {row.get('algo','')} / {row.get('strategy','')} / {row.get('metric_profile','')}"
        new_rows.append({
            "generated_utc": pd.Timestamp.now(tz='UTC').isoformat(),
            "symbol": symbol,
            "side": side,
            "score": score,
            "mode": runtime.get("mode","SHADOW"),
            "reason": reason,
            "max_notional_usd": runtime.get("max_notional_per_trade_usd", 25.0),
            "status": "shadow_only"
        })

if new_rows:
    intents = pd.concat([intents, pd.DataFrame(new_rows)], ignore_index=True)
    intents = intents.tail(50)
    intents.to_csv(intent_path, index=False)

exec_status = {
    "generated_utc": pd.Timestamp.now(tz='UTC').isoformat(),
    "execution_mode": runtime.get("mode","SHADOW"),
    "kill_switch": runtime.get("kill_switch","ON"),
    "live_arm": runtime.get("live_arm","OFF"),
    "kraken_api_key_present": kraken_key_present,
    "kraken_api_secret_present": kraken_secret_present,
    "shadow_intents_count": 0 if intents.empty else int(len(intents)),
    "execution_tickets_count": 0 if tickets.empty else int(len(tickets)),
    "note": "Shadow + ticketing only. No autonomous live order submission."
}
status_path.write_text(json.dumps(exec_status, indent=2), encoding="utf-8")

def badge(v, good="YES", bad="NO"):
    ok = str(v).upper() in ["YES","TRUE","ON","SHADOW","ARMED"]
    cls = "good" if ok else "bad"
    return f"<span class='{cls}'>{esc(v)}</span>"

intent_rows = ""
if not intents.empty:
    show = intents.tail(10).iloc[::-1]
    for _, row in show.iterrows():
        intent_rows += f"""
        <tr>
          <td>{esc(row.get('generated_utc',''))}</td>
          <td>{esc(row.get('symbol',''))}</td>
          <td>{esc(row.get('side',''))}</td>
          <td>{esc(row.get('score',''))}</td>
          <td>{esc(row.get('mode',''))}</td>
          <td>{esc(row.get('reason',''))}</td>
          <td>{esc(row.get('max_notional_usd',''))}</td>
          <td>{esc(row.get('status',''))}</td>
        </tr>
        """
else:
    intent_rows = "<tr><td colspan='8'>No shadow intents yet.</td></tr>"

ticket_rows = ""
if not tickets.empty:
    show = tickets.tail(10).iloc[::-1]
    for _, row in show.iterrows():
        ticket_rows += f"""
        <tr>
          <td>{esc(row.get('generated_utc',''))}</td>
          <td>{esc(row.get('symbol',''))}</td>
          <td>{esc(row.get('side',''))}</td>
          <td>{esc(row.get('requested_notional_usd',''))}</td>
          <td>{esc(row.get('mode',''))}</td>
          <td>{esc(row.get('approval_state',''))}</td>
          <td>{esc(row.get('ticket_note',''))}</td>
        </tr>
        """
else:
    ticket_rows = "<tr><td colspan='7'>No execution tickets yet.</td></tr>"

html_doc = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>LumenCore — Kraken Execution Layer</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
:root {{
  --bg:#07111f; --panel:#0c1830; --line:#21365f; --text:#e6eefc; --muted:#96a7c7;
  --good:#22c55e; --bad:#ef4444; --warn:#f59e0b;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; color:var(--text); font-family:Inter,Segoe UI,Arial,sans-serif;
  background:
    radial-gradient(circle at 15% 20%, rgba(34,211,238,.10), transparent 30%),
    radial-gradient(circle at 85% 10%, rgba(124,58,237,.10), transparent 28%),
    linear-gradient(180deg,#06101d 0%,#091528 100%);
}}
.wrap {{ max-width:1600px; margin:0 auto; padding:24px; }}
.hero,.card {{
  background:linear-gradient(180deg, rgba(12,24,48,.96), rgba(8,18,36,.94));
  border:1px solid var(--line); border-radius:18px; padding:18px;
}}
.hero h1 {{ margin:0 0 8px 0; font-size:38px; }}
.hero p {{ margin:0; color:var(--muted); }}
.grid4 {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; margin-top:16px; }}
.grid2 {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; margin-top:16px; }}
.kicker {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:1px; }}
.big {{ font-size:34px; font-weight:800; margin-top:8px; }}
.sub {{ color:var(--muted); margin-top:8px; font-size:13px; }}
.title {{ font-size:22px; font-weight:800; margin-bottom:12px; }}
table {{ width:100%; border-collapse:collapse; }}
th, td {{ padding:10px 8px; border-bottom:1px solid rgba(255,255,255,.08); text-align:left; font-size:13px; vertical-align:top; }}
th {{ color:#bcd0f4; font-size:12px; text-transform:uppercase; }}
.good {{ color:var(--good); font-weight:800; }}
.bad {{ color:var(--bad); font-weight:800; }}
.warn {{ color:var(--warn); font-weight:800; }}
.callout {{ line-height:1.6; }}
@media (max-width:1000px) {{ .grid4,.grid2 {{ grid-template-columns:1fr; }} .hero h1 {{ font-size:30px; }} }}
</style>
</head>
<body>
<div class="wrap">

<div class="hero">
  <h1>⚡ LumenCore — Kraken Execution Layer</h1>
  <p>Institutional shadow execution, intent generation, human approval queue, and kill-switch visibility.</p>
</div>

<div class="grid4">
  <div class="card">
    <div class="kicker">Execution Mode</div>
    <div class="big">{esc(exec_status['execution_mode'])}</div>
    <div class="sub">Current runtime mode</div>
  </div>
  <div class="card">
    <div class="kicker">Kill Switch</div>
    <div class="big">{esc(exec_status['kill_switch'])}</div>
    <div class="sub">Must remain ON for shadow-only</div>
  </div>
  <div class="card">
    <div class="kicker">Live Arm</div>
    <div class="big">{esc(exec_status['live_arm'])}</div>
    <div class="sub">Human gate only</div>
  </div>
  <div class="card">
    <div class="kicker">Shadow Intents</div>
    <div class="big">{esc(exec_status['shadow_intents_count'])}</div>
    <div class="sub">Generated from credible leaders</div>
  </div>
</div>

<div class="grid4">
  <div class="card">
    <div class="kicker">Kraken API Key</div>
    <div class="big">{'YES' if kraken_key_present else 'NO'}</div>
    <div class="sub">Environment presence only</div>
  </div>
  <div class="card">
    <div class="kicker">Kraken Secret</div>
    <div class="big">{'YES' if kraken_secret_present else 'NO'}</div>
    <div class="sub">Environment presence only</div>
  </div>
  <div class="card">
    <div class="kicker">Execution Tickets</div>
    <div class="big">{esc(exec_status['execution_tickets_count'])}</div>
    <div class="sub">Awaiting human approval</div>
  </div>
  <div class="card">
    <div class="kicker">Max Notional / Trade</div>
    <div class="big">{esc(runtime.get('max_notional_per_trade_usd',25.0))}</div>
    <div class="sub">Runtime control</div>
  </div>
</div>

<div class="grid2">
  <div class="card">
    <div class="title">Shadow order intents</div>
    <table>
      <thead>
        <tr>
          <th>UTC</th><th>Symbol</th><th>Side</th><th>Score</th><th>Mode</th><th>Reason</th><th>Notional</th><th>Status</th>
        </tr>
      </thead>
      <tbody>{intent_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <div class="title">Execution approval queue</div>
    <table>
      <thead>
        <tr>
          <th>UTC</th><th>Symbol</th><th>Side</th><th>Requested Notional</th><th>Mode</th><th>Approval</th><th>Note</th>
        </tr>
      </thead>
      <tbody>{ticket_rows}</tbody>
    </table>
  </div>
</div>

<div class="card" style="margin-top:16px;">
  <div class="title">What this proves</div>
  <div class="callout">
    <div><span class="good">Working:</span> signal-to-intent generation, runtime gates, key-presence detection, ticket queue, audit trail files.</div>
    <div><span class="warn">Next step:</span> human-reviewed ticket flow and paper P&amp;L reconciliation.</div>
    <div><span class="bad">Not included:</span> autonomous live order submission.</div>
  </div>
</div>

</div>
</body>
</html>
"""

out_html = DASH / "kraken_execution_dashboard.html"
out_html.write_text(html_doc, encoding="utf-8")
print(str(out_html))
