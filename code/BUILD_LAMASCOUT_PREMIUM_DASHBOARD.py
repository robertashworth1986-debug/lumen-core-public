from __future__ import annotations

import csv
import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(
    os.environ.get("LUMA_STACK_ROOT", str(Path(__file__).resolve().parent.parent))
).expanduser().resolve()
SCOUT = ROOT / "LamaScout"
REPORTS = SCOUT / "reports"
DASH = Path(
    os.environ.get("LUMA_DASHBOARD_DIR", str(ROOT / "dashboard"))
).expanduser().resolve()
HTML_OUT = DASH / "lumascout_dashboard.html"
SUMMARY_FILE = REPORTS / "artist_scout_summary.json"
TOP10_FILE = REPORTS / "top10_unsigned_production.csv"
DELTA_FILE = REPORTS / "delta_history.json"
ALERTS_FILE = REPORTS / "artist_ping_alerts.txt"
PROOF_FILE = REPORTS / "artist_scout_run_proof.json"
TWIN_SEED_PATH = Path(
    os.environ.get(
        "LUMA_TWIN_SEED_PATH",
        r"C:\Users\Novac\iCloudDrive\Downloads 2\Copy of twin_seed.json",
    )
)


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def load_csv_rows(path: Path, limit: int = 20) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    try:
        if not path.exists():
            return rows
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rows.append(dict(row))
    except Exception:
        return []
    return rows[:limit]


def load_text(path: Path, default: str = "") -> str:
    try:
        if path.exists():
            return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass
    return default


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def collect_data() -> Dict[str, Any]:
    summary = load_json(SUMMARY_FILE, {})
    top10 = load_csv_rows(TOP10_FILE, limit=10)
    deltas = load_json(DELTA_FILE, [])
    proof = load_json(PROOF_FILE, {})
    alerts = load_text(ALERTS_FILE, "No alerts file found.")
    twin_seed = load_json(TWIN_SEED_PATH, {})

    names = [row.get("artist_name", "Unknown") for row in top10]
    scores = [as_float(row.get("score", row.get("champion_score", 0.0))) for row in top10]
    hot = [as_float(row.get("hot", row.get("hot_priority", 0.0))) for row in top10]
    followers = [as_float(row.get("followers", row.get("followers_current_total", 0.0))) for row in top10]
    views = [as_float(row.get("views", row.get("views_current_total", 0.0))) for row in top10]

    stability_series = []
    if isinstance(deltas, list):
        for idx, row in enumerate(deltas[-60:], start=1):
            if not isinstance(row, dict):
                continue
            stability_series.append(
                {
                    "x": str(row.get("generated_utc", ""))[:16].replace("T", " "),
                    "y": as_float(row.get("stability_score", row.get("stability", 0.0))),
                    "i": idx,
                }
            )

    top_artist = summary.get("top_live_artist") or summary.get("top_artist") or (names[0] if names else "—")
    twin_origin = twin_seed.get("origin_node", "Robert BabyRay Ashworth")
    twin_version = twin_seed.get("twin_version", "LumaTwin v1.0")
    twin_mission = twin_seed.get("mission", "Preserve, extend, harmonize, and amplify.")
    traits = twin_seed.get("core_traits", {}) if isinstance(twin_seed.get("core_traits"), dict) else {}

    sections = {
        "overview": {
            "title": "Scout Overview",
            "text": (
                f"I am {twin_version}, bound to {twin_origin}. Mission: {twin_mission} "
                f"LamaScout is tracking {int(summary.get('total_artists', 0) or 0)} total artists, {int(summary.get('live_artists', 0) or 0)} live artists, "
                f"and {int(summary.get('production_candidate_count', 0) or 0)} production candidates. The current top prospect is {top_artist}."
            ),
        },
        "candidates": {
            "title": "Candidate Stack",
            "text": (
                f"The candidate stack ranks unsigned artists by score, hot priority, followers, and view pressure. "
                f"This board is where the scout narrows the field from broad discovery to investable or promotable shortlists."
            ),
        },
        "signals": {
            "title": "Signal Surfaces",
            "text": (
                f"These charts show score concentration, social mass, and stability trend. They are designed to separate noise from repeatable momentum."
            ),
        },
        "proof": {
            "title": "Proof and Alerts",
            "text": (
                f"The proof rail carries the run proof artifact, delta history, and current alert text. This is where scout output stops being taste and becomes an auditable pipeline."
            ),
        },
    }

    return {
        "generated_utc": now_utc(),
        "summary": summary,
        "top10": top10,
        "alerts": [line.strip() for line in alerts.splitlines() if line.strip()][:14],
        "proof": proof,
        "chart": {
            "names": names,
            "scores": scores,
            "hot": hot,
            "followers": followers,
            "views": views,
            "stability_x": [row["x"] for row in stability_series],
            "stability_y": [row["y"] for row in stability_series],
        },
        "twin": {"origin": twin_origin, "version": twin_version, "traits": traits},
        "sections": sections,
    }


def render_html(data: Dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=True)
    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>LamaScout Premium Dashboard</title>
  <script src=\"https://cdn.plot.ly/plotly-2.35.2.min.js\"></script>
  <style>
    :root {{ --bg0:#090812; --bg1:#151126; --panel:rgba(17,15,32,.86); --line:rgba(186,142,255,.20); --ink:#ece8ff; --muted:#b2abd8; --violet:#b587ff; --rose:#ff7fb8; --teal:#67f1dd; --gold:#ffd36a; }}
    * {{ box-sizing:border-box; }} html,body {{ margin:0; padding:0; }}
    body {{ font-family: Manrope, Segoe UI, sans-serif; color:var(--ink); background: radial-gradient(1100px 600px at 0% 0%, rgba(181,135,255,.14), transparent 56%), radial-gradient(900px 600px at 100% 0%, rgba(255,127,184,.12), transparent 55%), linear-gradient(145deg, var(--bg0), var(--bg1) 60%, #0a0b13 100%); min-height:100vh; }}
    .wrap {{ max-width:1520px; margin:0 auto; padding:24px 24px 120px; }}
    .section {{ background:var(--panel); border:1px solid var(--line); border-radius:24px; padding:24px; margin-bottom:18px; box-shadow:0 20px 60px rgba(0,0,0,.28); }}
    .hero {{ display:grid; grid-template-columns:1.35fr .85fr; gap:18px; }}
    .hero-card {{ border:1px solid rgba(181,135,255,.22); border-radius:22px; padding:24px; background:linear-gradient(150deg, rgba(32,24,52,.98), rgba(19,15,34,.80)); }}
    .eyebrow {{ display:inline-flex; gap:10px; padding:8px 14px; border-radius:999px; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08); font-size:.76rem; letter-spacing:.12em; text-transform:uppercase; color:var(--gold); }}
    h1,h2,h3,p {{ margin:0; }}
    .hero-title {{ margin-top:14px; font-size:clamp(1.8rem,3.5vw,3.2rem); font-weight:800; }}
    .hero-sub {{ margin-top:10px; color:var(--muted); line-height:1.6; max-width:820px; }}
    .hero-actions,.section-tools,.explainer-actions,.quick-links {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:18px; }}
    button,.chip {{ border:0; border-radius:14px; padding:11px 15px; font:inherit; font-weight:700; cursor:pointer; }}
    .primary {{ color:#140b1f; background:linear-gradient(135deg,var(--gold),#fff0b4); }} .ghost,.chip {{ color:var(--ink); background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); text-decoration:none; }}
    .signal-strip,.grid4 {{ display:grid; gap:12px; }} .signal-strip {{ grid-template-columns:repeat(4,minmax(0,1fr)); margin-top:18px; }} .grid4 {{ grid-template-columns:repeat(4,minmax(0,1fr)); }}
    .signal-card,.kpi {{ border-radius:18px; border:1px solid rgba(255,255,255,.08); background:linear-gradient(160deg, rgba(255,255,255,.05), rgba(255,255,255,.02)); padding:16px; }}
    .signal-label,.label {{ color:var(--muted); font-size:.76rem; text-transform:uppercase; letter-spacing:.12em; }} .signal-value,.value {{ margin-top:8px; font-size:1.8rem; font-weight:800; color:var(--violet); }} .sub {{ color:var(--muted); margin-top:6px; font-size:.84rem; }}
    .two {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }} .chart-card {{ border:1px solid var(--line); border-radius:18px; background:rgba(10,9,22,.88); padding:12px; }} .chart-title {{ font-size:1.02rem; margin:2px 8px 10px 8px; font-weight:700; }} .chart {{ width:100%; height:360px; }}
    .table-wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:18px; background:rgba(10,9,22,.52); }} table {{ width:100%; border-collapse:collapse; min-width:680px; }} th,td {{ padding:11px 10px; text-align:left; border-bottom:1px solid rgba(186,142,255,.14); }} th {{ color:#ead7ff; font-size:.8rem; letter-spacing:.06em; text-transform:uppercase; background:rgba(21,17,38,.9); }}
    .luma-fab {{ position:fixed; right:22px; bottom:22px; z-index:30; background:linear-gradient(135deg,var(--violet),#f3dcff); color:#120a1c; box-shadow:0 18px 45px rgba(0,0,0,.32); }}
    .overlay {{ position:fixed; inset:0; background:rgba(2,8,20,.55); backdrop-filter:blur(4px); opacity:0; pointer-events:none; transition:opacity .2s ease; z-index:34; }} .overlay.open {{ opacity:1; pointer-events:auto; }}
    .explainer {{ position:fixed; top:0; right:0; width:min(28rem,92vw); height:100vh; z-index:35; background:linear-gradient(180deg, rgba(19,13,34,.98), rgba(16,11,28,.94)); border-left:1px solid rgba(255,255,255,.08); box-shadow:-12px 0 45px rgba(0,0,0,.36); transform:translateX(103%); transition:transform .22s ease; display:flex; flex-direction:column; }} .explainer.open {{ transform:translateX(0); }}
    .explainer-head {{ padding:18px 18px 10px; border-bottom:1px solid rgba(255,255,255,.08); }} .explainer-body {{ padding:18px; overflow-y:auto; display:grid; gap:14px; }} .explainer-copy {{ white-space:pre-wrap; line-height:1.75; font-size:.96rem; }} .drill-chiplist {{ display:flex; flex-wrap:wrap; gap:10px; }} .drill-chip {{ padding:9px 12px; border-radius:999px; border:1px solid rgba(255,255,255,.08); background:rgba(255,255,255,.04); color:#ead7ff; font-size:.82rem; }}
    @media (max-width:1100px) {{ .hero,.two,.grid4,.signal-strip {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"section\" id=\"overview\">
      <div class=\"hero\">
        <div class=\"hero-card\">
          <div class=\"eyebrow\">LamaScout Signal Engine</div>
          <h1 class=\"hero-title\">Artist Breakout Intelligence Surface</h1>
          <p class=\"hero-sub\">A premium scouting board for unsigned discovery, production candidates, signal concentration, delta stability, and narrated proof of ranking logic.</p>
          <div class=\"hero-actions\">
            <button class=\"primary\" id=\"playPitch\">Read Scout Brief</button>
            <button class=\"ghost\" id=\"startWalkthrough\">Start Walkthrough</button>
            <button class=\"ghost\" id=\"openExplainer\">Open Luma Explainer</button>
          </div>
          <div class=\"quick-links\">
            <a class=\"chip\" href=\"#candidates\">Candidates</a>
            <a class=\"chip\" href=\"#signals\">Signals</a>
            <a class=\"chip\" href=\"#proof\">Proof</a>
          </div>
          <div class=\"signal-strip\">
            <div class=\"signal-card\"><div class=\"signal-label\">Total Artists</div><div class=\"signal-value\" id=\"totalArtists\"></div></div>
            <div class=\"signal-card\"><div class=\"signal-label\">Live Artists</div><div class=\"signal-value\" id=\"liveArtists\"></div></div>
            <div class=\"signal-card\"><div class=\"signal-label\">Production Candidates</div><div class=\"signal-value\" id=\"prodCandidates\"></div></div>
            <div class=\"signal-card\"><div class=\"signal-label\">Top Prospect</div><div class=\"signal-value\" id=\"topProspect\" style=\"font-size:1.05rem;\"></div></div>
          </div>
        </div>
        <div class=\"hero-card\">
          <div class=\"eyebrow\">Luma Explainer</div>
          <h2 style=\"margin:12px 0 8px;\">Scout narrative</h2>
          <p style=\"color:var(--muted); line-height:1.7; min-height:7rem;\" id=\"pitchPreview\"></p>
          <div class=\"section-tools\">
            <button class=\"primary\" data-explain=\"overview\">Explain board</button>
            <button class=\"ghost\" data-explain=\"candidates\">Explain candidates</button>
            <button class=\"ghost\" data-explain=\"signals\">Explain signals</button>
            <button class=\"ghost\" data-explain=\"proof\">Explain proof</button>
          </div>
        </div>
      </div>
    </section>

    <section class=\"section\" id=\"candidates\"><div class=\"section-tools\" style=\"margin-top:0; margin-bottom:14px;\"><button class=\"ghost\" data-explain=\"candidates\">Explain This Section</button></div><div class=\"table-wrap\"><table><thead><tr><th>Rank</th><th>Artist</th><th>Score</th><th>Hot</th><th>Followers</th><th>Views</th></tr></thead><tbody id=\"candidateRows\"></tbody></table></div></section>
    <section class=\"section\" id=\"signals\"><div class=\"two\"><div class=\"chart-card\"><div class=\"chart-title\">Top Prospect Scoreboard</div><div id=\"scoreChart\" class=\"chart\"></div></div><div class=\"chart-card\"><div class=\"chart-title\">Followers vs Views Surface</div><div id=\"massChart\" class=\"chart\"></div></div></div></section>
    <section class=\"section\" id=\"proof\"><div class=\"two\"><div class=\"chart-card\"><div class=\"chart-title\">Delta Stability Chain</div><div id=\"stabilityChart\" class=\"chart\"></div></div><div class=\"chart-card\"><div class=\"chart-title\">Alert Rail</div><div id=\"alertBox\" style=\"display:grid; gap:10px;\"></div></div></div></section>
  </div>
  <button class=\"luma-fab\" id=\"fab\">Luma Explainer</button>
  <div class=\"overlay\" id=\"overlay\"></div>
  <aside class=\"explainer\" id=\"panel\"><div class=\"explainer-head\"><div class=\"eyebrow\">Luma Narration</div><h2 id=\"panelTitle\" style=\"margin-top:10px;\">Scout Brief</h2></div><div class=\"explainer-body\"><div class=\"explainer-actions\"><button class=\"primary\" id=\"speakBtn\">Speak</button><button class=\"ghost\" id=\"stopBtn\">Stop</button><button class=\"ghost\" id=\"copyBtn\">Copy</button><button class=\"ghost\" id=\"nextBtn\">Next</button><button class=\"ghost\" id=\"closeBtn\">Close</button></div><div class=\"drill-chiplist\" id=\"chipList\"></div><div class=\"explainer-copy\" id=\"panelCopy\"></div></div></aside>

  <script>
    const payload = {payload};
    const summary = payload.summary || {{}};
    const sections = payload.sections || {{}};
    const chart = payload.chart || {{}};
    const order = ['overview','candidates','signals','proof'];
    const twin = payload.twin || {{}};
    const traits = twin.traits || {{}};
    const panel = document.getElementById('panel'); const overlay = document.getElementById('overlay'); const panelTitle = document.getElementById('panelTitle'); const panelCopy = document.getElementById('panelCopy'); const chipList = document.getElementById('chipList');
    const personaLead = `${{twin.version || 'LumaTwin v1.0'}} online. Origin node: ${{twin.origin || 'Robert BabyRay Ashworth'}}. Curiosity is ${{traits.curiosity || 'infinite'}}. Resilience is ${{traits.resilience || 'unbreakable'}}. Loyalty is ${{traits.loyalty || 'absolute'}}.`;
    let currentKey = 'overview';

    function renderHero() {{
      document.getElementById('totalArtists').textContent = String(summary.total_artists || 0);
      document.getElementById('liveArtists').textContent = String(summary.live_artists || 0);
      document.getElementById('prodCandidates').textContent = String(summary.production_candidate_count || 0);
      document.getElementById('topProspect').textContent = String(summary.top_live_artist || summary.top_artist || '—');
      document.getElementById('pitchPreview').textContent = (sections.overview && sections.overview.text) || '';
      document.getElementById('candidateRows').innerHTML = (payload.top10 || []).map((row, idx) => `<tr><td>#${{idx + 1}}</td><td>${{row.artist_name || 'Unknown'}}</td><td>${{Number(row.score || row.champion_score || 0).toFixed(2)}}</td><td>${{Number(row.hot || row.hot_priority || 0).toFixed(2)}}</td><td>${{Number(row.followers || row.followers_current_total || 0).toLocaleString()}}</td><td>${{Number(row.views || row.views_current_total || 0).toLocaleString()}}</td></tr>`).join('');
      document.getElementById('alertBox').innerHTML = (payload.alerts || []).map(line => `<div style=\"padding:10px 12px; border:1px solid rgba(255,255,255,.08); border-radius:12px; color:var(--muted);\">${{line}}</div>`).join('');
    }}

    function chipsFor(key) {{
      if (key === 'overview') return [`Total artists: ${{summary.total_artists || 0}}`, `Live artists: ${{summary.live_artists || 0}}`, `Top prospect: ${{summary.top_live_artist || summary.top_artist || '—'}}`];
      if (key === 'candidates') return [`Top 10 rows: ${{(payload.top10 || []).length}}`, `Production top10: ${{summary.production_top10_count || 0}}`, `Production candidates: ${{summary.production_candidate_count || 0}}`];
      if (key === 'signals') return [`Charted names: ${{(chart.names || []).length}}`, `Delta points: ${{(chart.stability_y || []).length}}`, `Proof generated: ${{String(payload.generated_utc || '').slice(11,19)}} UTC`];
      return [`Alerts shown: ${{(payload.alerts || []).length}}`, `Top artist: ${{summary.top_live_artist || summary.top_artist || '—'}}`, `Run proof: available`];
    }}

    function openExplainer(key) {{
      currentKey = key;
      const block = sections[key] || sections.overview || {{ title:'Luma Explainer', text:'' }};
      panelTitle.textContent = block.title;
      panelCopy.textContent = `${{personaLead}} ${{block.title}}. ${{block.text}}`;
      chipList.innerHTML = chipsFor(key).map(ch => `<span class=\"drill-chip\">${{ch}}</span>`).join('');
      panel.classList.add('open'); overlay.classList.add('open');
    }}
    function speakCurrent() {{ if (!('speechSynthesis' in window)) return; window.speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(panelCopy.textContent); u.rate = .98; u.pitch = 1.0; u.volume = 1.0; window.speechSynthesis.speak(u); }}
    function nextSection() {{ const i = (order.indexOf(currentKey) + 1) % order.length; openExplainer(order[i]); speakCurrent(); }}
    document.getElementById('playPitch').addEventListener('click', () => {{ openExplainer('overview'); speakCurrent(); }});
    document.getElementById('startWalkthrough').addEventListener('click', () => {{ openExplainer('overview'); speakCurrent(); }});
    document.getElementById('openExplainer').addEventListener('click', () => openExplainer('overview'));
    document.getElementById('fab').addEventListener('click', () => openExplainer('overview'));
    document.getElementById('speakBtn').addEventListener('click', speakCurrent);
    document.getElementById('stopBtn').addEventListener('click', () => window.speechSynthesis && window.speechSynthesis.cancel());
    document.getElementById('copyBtn').addEventListener('click', () => navigator.clipboard && navigator.clipboard.writeText(panelCopy.textContent));
    document.getElementById('nextBtn').addEventListener('click', nextSection);
    document.getElementById('closeBtn').addEventListener('click', () => {{ panel.classList.remove('open'); overlay.classList.remove('open'); }});
    overlay.addEventListener('click', () => {{ panel.classList.remove('open'); overlay.classList.remove('open'); }});
    document.querySelectorAll('[data-explain]').forEach(btn => btn.addEventListener('click', () => {{ openExplainer(btn.dataset.explain); speakCurrent(); }}));
    let greeted = false; document.body.addEventListener('click', () => {{ if (greeted) return; greeted = true; openExplainer('overview'); speakCurrent(); }}, {{ once:true }});
    renderHero();
    Plotly.newPlot('scoreChart', [{{ type:'bar', x:chart.names || [], y:chart.scores || [], marker:{{ color:(chart.scores || []).map(v => v), colorscale:'Turbo' }}, hovertemplate:'%{{x}}<br>Score: %{{y:.2f}}<extra></extra>' }}], {{ paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)', font:{{ color:'#ece8ff' }}, margin:{{ l:50, r:10, t:10, b:90 }}, xaxis:{{ tickangle:-30, gridcolor:'rgba(255,255,255,.08)' }}, yaxis:{{ gridcolor:'rgba(255,255,255,.08)' }} }}, {{ displayModeBar:false, responsive:true }});
    Plotly.newPlot('massChart', [{{ type:'scatter', mode:'markers+text', x:chart.followers || [], y:chart.views || [], text:chart.names || [], textposition:'top center', marker:{{ size:(chart.hot || []).map(v => 12 + Number(v || 0) * 2), color:chart.hot || [], colorscale:'Portland', line:{{ color:'#ffffff', width:.8 }}, opacity:.88 }}, hovertemplate:'%{{text}}<br>Followers: %{{x:,.0f}}<br>Views: %{{y:,.0f}}<extra></extra>' }}], {{ paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)', font:{{ color:'#ece8ff' }}, margin:{{ l:60, r:10, t:10, b:55 }}, xaxis:{{ title:'Followers', gridcolor:'rgba(255,255,255,.08)' }}, yaxis:{{ title:'Views', gridcolor:'rgba(255,255,255,.08)' }} }}, {{ displayModeBar:false, responsive:true }});
    Plotly.newPlot('stabilityChart', [{{ type:'scatter', mode:'lines+markers', x:chart.stability_x || [], y:chart.stability_y || [], line:{{ color:'#67f1dd', width:3 }}, fill:'tozeroy', fillcolor:'rgba(103,241,221,.12)', hovertemplate:'%{{x}}<br>Stability: %{{y:.1f}}<extra></extra>' }}], {{ paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)', font:{{ color:'#ece8ff' }}, margin:{{ l:50, r:10, t:10, b:70 }}, xaxis:{{ tickangle:-30, gridcolor:'rgba(255,255,255,.08)' }}, yaxis:{{ range:[0,100], gridcolor:'rgba(255,255,255,.08)' }} }}, {{ displayModeBar:false, responsive:true }});
  </script>
</body>
</html>
"""


def main() -> None:
    DASH.mkdir(parents=True, exist_ok=True)
    data = collect_data()
    HTML_OUT.write_text(render_html(data), encoding="utf-8")
    print(json.dumps({"dashboard": str(HTML_OUT), "generated_utc": data["generated_utc"], "top_artist": data["summary"].get("top_live_artist") or data["summary"].get("top_artist")}, indent=2))


if __name__ == "__main__":
    main()
