import json, html
from pathlib import Path
import pandas as pd

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT  = ROOT / "out"
DASH = Path(r"C:\LumaTrader\dashboard")
CFG  = ROOT / "config"

summary_path  = OUT / "live_registry_summary.json"
status_path   = OUT / "live_source_status.json"
registry_path = OUT / "full_beast_registry.json"
proof_path    = OUT / "full_beast_proof.json"
lb_path       = OUT / "credible_top10.csv"

def read_json(p, default=None):
    if default is None:
        default = {}
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def esc(x):
    return html.escape(str(x))

summary = read_json(summary_path, {})
status  = read_json(status_path, {})
registry = read_json(registry_path, {})
proof = read_json(proof_path, {})

# read credible leaderboard if present
try:
    lb = pd.read_csv(lb_path) if lb_path.exists() else pd.DataFrame()
except Exception:
    lb = pd.DataFrame()

sources = (status.get("sources") or {})
eia = sources.get("eia", {})

def yesno(v):
    return "YES" if v else "NO"


def public_probe_state(source):
    """Return a bounded public status without credential or error disclosure."""
    if not isinstance(source, dict):
        return "NOT_REPORTED"
    try:
        rows = int(source.get("rows_written", source.get("rows", 0)) or 0)
    except (TypeError, ValueError):
        rows = 0
    if rows > 0:
        return "MEASURED_ROWS_PRESENT"
    if source.get("error"):
        return "SOURCE_UNAVAILABLE"
    if bool(source.get("enabled")):
        return "AWAITING_MEASUREMENT"
    return "DISABLED"


def public_proof_rows(payload):
    """Allow only bounded integrity metadata onto the public dashboard."""
    if not isinstance(payload, dict):
        return []
    allowed = (
        "generated_utc",
        "status",
        "valid",
        "verified",
        "file_count",
        "files_hashed",
        "manifest_sha256",
        "sha256",
    )
    rows = []
    for key in allowed:
        value = payload.get(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            rows.append((key, value))
    return rows

top_html = ""
if not lb.empty:
    cols = [c for c in ["file","flow","algo","strategy","metric_profile","test_sharpe_clean","test_vs_baseline_clean","test_max_dd_clean","investor_score_clean"] if c in lb.columns]
    for _, row in lb.head(10)[cols].iterrows():
        top_html += "<tr>"
        for c in cols:
            val = row[c]
            if c == "file":
                val = Path(str(val)).name
            top_html += f"<td>{esc(val)}</td>"
        top_html += "</tr>"
else:
    top_html = "<tr><td colspan='9'>No credible leaderboard found yet.</td></tr>"

proof_html = ""
for k, v in public_proof_rows(proof):
    proof_html += f"<tr><td>{esc(k)}</td><td class='mono'>{esc(v)}</td></tr>"

eia_files = eia.get("files_written", []) or []
eia_files_html = "".join(f"<li>{esc(Path(str(x)).name)}</li>" for x in eia_files) if eia_files else "<li>None yet</li>"

html_doc = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>LumenCore — Live Sources Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
:root {{
  --bg:#07111f;
  --panel:#0c1830;
  --line:#21365f;
  --text:#e6eefc;
  --muted:#96a7c7;
  --green:#22c55e;
  --red:#ef4444;
  --amber:#f59e0b;
  --cyan:#22d3ee;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  color:var(--text);
  font-family:Inter,Segoe UI,Arial,sans-serif;
  background:
    radial-gradient(circle at 10% 10%, rgba(34,211,238,.10), transparent 30%),
    radial-gradient(circle at 90% 10%, rgba(124,58,237,.12), transparent 28%),
    linear-gradient(180deg, #06101d 0%, #091528 100%);
}}
.wrap {{ max-width:1600px; margin:0 auto; padding:24px; }}
.hero, .card {{
  background:linear-gradient(180deg, rgba(12,24,48,.96), rgba(8,18,36,.94));
  border:1px solid var(--line);
  border-radius:18px;
  box-shadow:0 0 30px rgba(34,211,238,.08);
}}
.hero {{ padding:26px; }}
.hero h1 {{ margin:0 0 8px 0; font-size:38px; }}
.hero p {{ margin:0; color:var(--muted); }}
.grid4 {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; margin-top:16px; }}
.grid3 {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; margin-top:16px; }}
.grid2 {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; margin-top:16px; }}
.card {{ padding:18px; }}
.kicker {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:1px; }}
.big {{ font-size:34px; font-weight:800; margin-top:8px; }}
.sub {{ color:var(--muted); margin-top:8px; font-size:13px; }}
.title {{ font-size:22px; font-weight:800; margin-bottom:12px; }}
.ok {{ color:var(--green); font-weight:800; }}
.bad {{ color:var(--red); font-weight:800; }}
.warn {{ color:var(--amber); font-weight:800; }}
ul {{ margin:0; padding-left:18px; }}
li {{ margin:0 0 6px 0; }}
table {{ width:100%; border-collapse:collapse; }}
th, td {{ padding:10px 8px; border-bottom:1px solid rgba(255,255,255,.08); text-align:left; font-size:13px; vertical-align:top; }}
th {{ color:#bcd0f4; font-size:12px; text-transform:uppercase; }}
.mono {{ font-family:ui-monospace,Consolas,monospace; font-size:12px; word-break:break-all; }}
.badge {{
  display:inline-block; padding:6px 10px; border-radius:999px; margin-right:8px; font-size:12px; font-weight:700;
  border:1px solid rgba(255,255,255,.12);
}}
.green {{ background:rgba(34,197,94,.12); color:#86efac; }}
.red {{ background:rgba(239,68,68,.12); color:#fca5a5; }}
.amber {{ background:rgba(245,158,11,.12); color:#fcd34d; }}
.footer {{ margin-top:16px; color:var(--muted); font-size:12px; }}
@media (max-width:1200px) {{ .grid4,.grid3 {{ grid-template-columns:1fr 1fr; }} }}
@media (max-width:800px) {{
  .grid4,.grid3,.grid2 {{ grid-template-columns:1fr; }}
  .hero h1 {{ font-size:30px; }}
}}
</style>
</head>
<body>
<div class="wrap">

<div class="hero">
  <h1>⚡ LumenCore — Live Sources Dashboard</h1>
  <p>Registry breadth + live-source truth + credibility proof.</p>
  <div style="margin-top:12px;">
    <span class="badge green">Flowforms: {esc(registry.get("flowforms_count", 0))}</span>
    <span class="badge green">Algos: {esc(registry.get("algos_count", 0))}</span>
    <span class="badge green">Strategies: {esc(registry.get("strategies_count", 0))}</span>
    <span class="badge green">Profiles: {esc(registry.get("metric_profiles_count", 0))}</span>
  </div>
</div>

<div class="grid4">
  <div class="card">
    <div class="kicker">EIA Enabled</div>
    <div class="big">{yesno(eia.get("enabled", False))}</div>
    <div class="sub">Config gate</div>
  </div>
  <div class="card">
    <div class="kicker">Credential Boundary</div>
    <div class="big">PRIVATE</div>
    <div class="sub">Credential presence is neither inspected nor published</div>
  </div>
  <div class="card">
    <div class="kicker">EIA Rows Written</div>
    <div class="big">{eia.get("rows_written", 0)}</div>
    <div class="sub">Live operational rows</div>
  </div>
  <div class="card">
    <div class="kicker">Credible Top Rows</div>
    <div class="big">{len(lb) if not lb.empty else 0}</div>
    <div class="sub">From credible_top10.csv</div>
  </div>
</div>

<div class="grid2">
  <div class="card">
    <div class="title">Live source status</div>
    <table>
      <tbody>
        <tr><td>EIA enabled</td><td class="mono">{esc(eia.get("enabled", False))}</td></tr>
        <tr><td>EIA rows written</td><td class="mono">{esc(eia.get("rows_written", 0))}</td></tr>
        <tr><td>EIA public probe state</td><td class="mono">{public_probe_state(eia)}</td></tr>
      </tbody>
    </table>
    <div class="title" style="margin-top:16px;">EIA files written</div>
    <ul>{eia_files_html}</ul>
  </div>

  <div class="card">
    <div class="title">Other source gates</div>
    <table>
      <thead><tr><th>Source</th><th>Enabled</th><th>Rows</th><th>Public Probe State</th></tr></thead>
      <tbody>
        {''.join(
          f"<tr><td>{esc(name)}</td><td>{esc(src.get('enabled', False))}</td><td>{esc(src.get('rows_written', src.get('rows', 0)))}</td><td class='mono'>{public_probe_state(src)}</td></tr>"
          for name, src in sources.items() if name != 'eia'
        )}
      </tbody>
    </table>
  </div>
</div>

<div class="grid2">
  <div class="card">
    <div class="title">Top credible leaderboard</div>
    <table>
      <thead>
        <tr>
          <th>File</th>
          <th>Flow</th>
          <th>Algo</th>
          <th>Strategy</th>
          <th>Profile</th>
          <th>Sharpe</th>
          <th>Vs Baseline</th>
          <th>Max DD</th>
          <th>Investor Score</th>
        </tr>
      </thead>
      <tbody>{top_html}</tbody>
    </table>
  </div>

  <div class="card">
    <div class="title">Proof / integrity</div>
    <table><tbody>{proof_html if proof_html else "<tr><td colspan='2'>No proof file found.</td></tr>"}</tbody></table>
  </div>
</div>

<div class="footer">
  Public projection sources: {esc(status_path.name)} | {esc(summary_path.name)} | {esc(registry_path.name)}. Credential details and raw provider errors are intentionally omitted.
</div>

</div>
</body>
</html>
"""

out_html = DASH / "live_sources_dashboard.html"
out_html.write_text(html_doc, encoding="utf-8")
print(str(out_html))
