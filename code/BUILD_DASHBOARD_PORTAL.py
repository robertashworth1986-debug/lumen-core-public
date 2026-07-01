from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(
    os.environ.get("LUMA_STACK_ROOT", str(Path(__file__).resolve().parent.parent))
).expanduser().resolve()
DASH = Path(
    os.environ.get("LUMA_DASHBOARD_DIR", str(ROOT / "dashboard"))
).expanduser().resolve()
HTML_OUT = DASH / "dashboard_portal.html"
INDEX_OUT = DASH / "index.html"
UNIFIED_FILE = DASH / "LUMENCORE_MASTER_DASHBOARD_UNIFIED_20260425.html"
ALPACA_FILE = DASH / "alpaca_paper_live_dashboard.html"
SCOUT_FILE = DASH / "lumascout_dashboard.html"
SCORECARD = ROOT / "out" / "execution" / "investor_proof_scorecard.json"
SCOUT_SUMMARY = ROOT / "LamaScout" / "reports" / "artist_scout_summary.json"
SECTOR_MATRIX = ROOT / "out" / "sector_value_matrix.json"
DOLLAR_CLAIM_GATE = ROOT / "out" / "ops" / "dollar_claim_gate_latest.json"
LIVE_BREADTH_KEY_GATE = ROOT / "out" / "ops" / "live_breadth_key_gate_latest.json"
GEOMETRY_BRIDGE = ROOT / "out" / "ops" / "geometry_championship_bridge_latest.json"
CHAMPION_GAUNTLET = ROOT / "out" / "ops" / "champion_metric_gauntlet_latest.json"
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


def main() -> None:
    DASH.mkdir(parents=True, exist_ok=True)
    scorecard = load_json(SCORECARD, {})
    scout = load_json(SCOUT_SUMMARY, {})
    sector = load_json(SECTOR_MATRIX, {})
    dollar_claim_gate = load_json(DOLLAR_CLAIM_GATE, {})
    live_breadth_key_gate = load_json(LIVE_BREADTH_KEY_GATE, {})
    geometry_bridge = load_json(GEOMETRY_BRIDGE, {})
    champion_gauntlet = load_json(CHAMPION_GAUNTLET, {})
    twin_seed = load_json(TWIN_SEED_PATH, {})
    now = datetime.now(timezone.utc).isoformat()
    dollar_summary = dollar_claim_gate.get("summary", {}) if isinstance(dollar_claim_gate.get("summary"), dict) else {}
    key_summary = live_breadth_key_gate.get("summary", {}) if isinstance(live_breadth_key_gate.get("summary"), dict) else {}
    geometry_summary = geometry_bridge.get("summary", {}) if isinstance(geometry_bridge.get("summary"), dict) else {}
    gauntlet_summary = champion_gauntlet.get("summary", {}) if isinstance(champion_gauntlet.get("summary"), dict) else {}
    branching_benchmark = geometry_bridge.get("branching_transport_benchmark", {}) if isinstance(geometry_bridge.get("branching_transport_benchmark"), dict) else {}
    branching_geometry = branching_benchmark.get("best_geometry", {}) if isinstance(branching_benchmark.get("best_geometry"), dict) else {}
    branching_baseline = branching_benchmark.get("best_baseline", {}) if isinstance(branching_benchmark.get("best_baseline"), dict) else {}

    critical_links = [
      ("Mission Control", "mission_control.html"),
      ("Grants", "grants.html"),
      ("Quant Lab", "quant_lab.html"),
      ("Proof To Pilot", "proof_to_pilot.html"),
      ("Investor Room", "investor_command_room.html"),
      ("Investor Wallboard", "investor_wallboard.html"),
      ("Luma Voice Context", "luma_voice_context_console.html"),
      ("Champion Gauntlet", "data/champion_metric_gauntlet.json"),
      ("Dollar Claim Gate", "data/dollar_claim_gate.json"),
      ("Field Validation Feed", "data/field_validation_control_room.json"),
      ("Field Outreach Feed", "data/field_validation_outreach_board.json"),
      ("Geometry Bridge", "data/geometry_championship_bridge.json"),
      ("Kraken Execution", "kraken_execution_dashboard.html"),
      ("Scenario Mission", "scenario_mission.html"),
      ("Staleness Command", "staleness_command_center.html"),
      ("Harmonic Proofpack", "harmonic_proofpack_mission.html"),
      ("Live Source Registry", "live_source_registry.html"),
    ]
    critical_links_html = "".join(
      f'<a class="btn ghost" href="{href}">{label}</a>' for label, href in critical_links
    )

    payload = {
        "generated_utc": now,
        "paper_equity": fmt_usd(scorecard.get("current_equity_usd", 0.0)),
        "paper_trades": int(scorecard.get("closed_trades", 0) or 0),
        "paper_pnl": fmt_usd(scorecard.get("net_pnl_usd", 0.0)),
        "active_surface": fmt_usd(sector.get("yearly_translated_value", 0.0)),
        "claim_safe_hourly": fmt_usd(dollar_summary.get("allowed_estimated_hourly_value_usd", 0.0)),
        "claim_safe_annual": fmt_usd(dollar_summary.get("allowed_estimated_annual_value_usd", 0.0)),
        "blocked_context_annual": fmt_usd(dollar_summary.get("blocked_context_only_annual_value_usd", 0.0)),
        "claim_safe_lanes": int(dollar_summary.get("allowed_estimated_value_claims", 0) or 0),
        "configured_live_breadth_providers": int(key_summary.get("configured_providers", 0) or 0),
        "geometry_family_count": int(geometry_summary.get("family_count", 0) or 0),
        "champion_family": gauntlet_summary.get("champion_family", "not run"),
        "champion_holdout_wins": int(gauntlet_summary.get("holdout_wins", 0) or 0),
        "champion_holdout_count": int(gauntlet_summary.get("holdout_count", 0) or 0),
        "champion_gate_pass_count": int(gauntlet_summary.get("gauntlet_pass_count", 0) or 0),
        "champion_gate_total_count": int(gauntlet_summary.get("gauntlet_total_count", 0) or 0),
        "champion_blocking_gate_count": int(gauntlet_summary.get("blocking_gate_count", 0) or 0),
        "geometry_proof_champion_lane": geometry_summary.get("proof_champion_lane", "—"),
        "geometry_proof_champion_family": geometry_summary.get("proof_champion_family", "—"),
        "branching_benchmark_gate": branching_benchmark.get("gate", "not run"),
        "branching_best_geometry": branching_geometry.get("strategy", "not run"),
        "branching_best_baseline": branching_baseline.get("strategy", "not run"),
        "branching_score_delta": float(branching_benchmark.get("score_delta_vs_best_baseline", 0.0) or 0.0),
        "branching_delivered_delta": float(branching_benchmark.get("delivered_flow_delta_vs_best_baseline", 0.0) or 0.0),
        "branching_failure_delta": float(branching_benchmark.get("failure_tolerance_delta_vs_best_baseline", 0.0) or 0.0),
        "top_lane": sector.get("top_current_optimization_lane", "—"),
        "top_scout": scout.get("top_live_artist") or scout.get("top_artist") or "—",
        "production_candidates": int(scout.get("production_candidate_count", 0) or 0),
        "twin": {
            "origin": twin_seed.get("origin_node", "Robert BabyRay Ashworth"),
            "version": twin_seed.get("twin_version", "LumaTwin v1.0"),
            "traits": twin_seed.get("core_traits", {}),
        },
        "sections": {
            "overview": {
                "title": "Portal Overview",
              "text": "This portal is the command surface for four canonical public boards: Mission Control, Grants, Quant Lab, and Proof-to-Pilot, plus a curated live operations set. Legacy pages are secondary so the proof story stays coherent.",
            },
            "unified": {
                "title": "Unified Board",
                "text": f"The unified board is the flagship investor surface. It currently shows the top optimization lane as {sector.get('top_current_optimization_lane', '—')} and an active source surface of {fmt_usd(sector.get('yearly_translated_value', 0.0))}.",
            },
            "paper": {
                "title": "Paper Board",
                "text": f"The paper execution board is carrying equity around {fmt_usd(scorecard.get('current_equity_usd', 0.0))}, net profit and loss of {fmt_usd(scorecard.get('net_pnl_usd', 0.0))}, and {int(scorecard.get('closed_trades', 0) or 0)} closed trades.",
            },
            "scout": {
                "title": "Secondary Scout Board",
                "text": f"LumaScout remains a secondary discovery surface tracking {int(scout.get('total_artists', 0) or 0)} artists with {int(scout.get('production_candidate_count', 0) or 0)} production candidates. It is not one of the four master boards.",
            },
            "claims": {
                "title": "Dollar Claim Gate",
                "text": f"Current safe language supports bounded estimated value on {int(dollar_summary.get('allowed_estimated_value_claims', 0) or 0)} live-measured lanes: {fmt_usd(dollar_summary.get('allowed_estimated_hourly_value_usd', 0.0))} per hour / {fmt_usd(dollar_summary.get('allowed_estimated_annual_value_usd', 0.0))} per year under stated assumptions. Context-only value of {fmt_usd(dollar_summary.get('blocked_context_only_annual_value_usd', 0.0))} stays blocked until validation, source-rights, and uncertainty gates pass.",
            },
            "geometry": {
                "title": "Geometry Proof Bridge",
                "text": f"Geometry Championship currently tracks {int(geometry_summary.get('family_count', 0) or 0)} route, path, flowform, field, and signal families. The latest branching-transport generated benchmark shows {branching_geometry.get('strategy', 'not run')} versus {branching_baseline.get('strategy', 'not run')} with gate {branching_benchmark.get('gate', 'not run')} and score delta {float(branching_benchmark.get('score_delta_vs_best_baseline', 0.0) or 0.0):.6f}. This is proof-building evidence, not field validation or live execution authorization.",
            },
        },
    }
    embedded = json.dumps(payload, ensure_ascii=True)

    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Luma Dashboard Portal</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet" />
  <style>
    :root {{ --bg0:#05070f; --bg1:#0b1d2c; --bg2:#131827; --panel:rgba(8,17,34,.62); --line:rgba(118,199,255,.26); --ink:#e9f3ff; --muted:#96aec8; --teal:#59f3d0; --gold:#ffd873; --violet:#86a8ff; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:'Sora', Segoe UI, sans-serif; color:var(--ink); min-height:100vh; background:radial-gradient(1200px 700px at 10% -10%, rgba(255,142,86,.2), transparent 60%), radial-gradient(1000px 640px at 90% -20%, rgba(89,243,208,.18), transparent 62%), linear-gradient(155deg, var(--bg0), var(--bg1) 42%, var(--bg2)); overflow-x:hidden; }}
    #cinema-bg {{ position:fixed; inset:0; z-index:0; opacity:.55; pointer-events:none; }}
    .noise {{ position:fixed; inset:0; z-index:1; pointer-events:none; background-image:radial-gradient(rgba(255,255,255,.05) .55px, transparent .55px); background-size:2px 2px; opacity:.14; mix-blend-mode:soft-light; }}
    .scanline {{ position:fixed; inset:0; z-index:1; pointer-events:none; background:linear-gradient(to bottom, rgba(255,255,255,.035), rgba(255,255,255,0) 3px); background-size:100% 4px; opacity:.1; }}
    .wrap {{ position:relative; z-index:2; max-width:1340px; margin:0 auto; padding:30px 24px 94px; }}
    .hero,.grid {{ display:grid; gap:18px; }}
    .hero {{ grid-template-columns:1.35fr .95fr; }}
    .grid {{ grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:20px; }}
    .card {{ position:relative; overflow:hidden; backdrop-filter:blur(10px); background:linear-gradient(175deg, rgba(9,21,42,.75), rgba(7,15,30,.7)); border:1px solid var(--line); border-radius:24px; padding:24px; box-shadow:0 26px 70px rgba(2,6,15,.55); transform:translateY(0px); transition:transform .28s ease, border-color .28s ease, box-shadow .28s ease; }}
    .card::before {{ content:''; position:absolute; inset:auto -18% -62% -18%; height:70%; background:radial-gradient(closest-side, rgba(89,243,208,.16), transparent 75%); pointer-events:none; }}
    .card:hover {{ transform:translateY(-4px); border-color:rgba(255,216,115,.45); box-shadow:0 34px 80px rgba(1,8,20,.62); }}
    .reveal {{ opacity:0; transform:translateY(14px) scale(.985); }}
    .reveal.in {{ opacity:1; transform:translateY(0) scale(1); transition:opacity .52s ease, transform .52s ease; }}
    .eyebrow {{ display:inline-flex; padding:8px 14px; border-radius:999px; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.12); font-size:.74rem; letter-spacing:.14em; text-transform:uppercase; color:var(--gold); font-family:'Space Grotesk', sans-serif; }}
    h1,h2,p {{ margin:0; }}
    h1 {{ margin-top:14px; font-size:clamp(2.0rem,4.2vw,3.8rem); letter-spacing:-.02em; line-height:1.03; text-wrap:balance; }}
    h2 {{ font-size:1.55rem; letter-spacing:-.015em; }}
    p {{ color:var(--muted); line-height:1.68; }}
    .actions {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:18px; }}
    a {{ text-decoration:none; }}
    .btn, .portal-btn {{ border-radius:14px; padding:11px 16px; font:inherit; font-weight:700; display:inline-block; cursor:pointer; transition:transform .18s ease, filter .18s ease; }}
    .btn:hover, .portal-btn:hover {{ transform:translateY(-1px); filter:brightness(1.06); }}
    .primary {{ color:#051220; background:linear-gradient(135deg,var(--gold),#fff0b4); border:0; }}
    .ghost {{ color:var(--ink); background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.10); }}
    .metric {{ margin-top:14px; }}
    .label {{ color:var(--muted); font-size:.74rem; text-transform:uppercase; letter-spacing:.13em; font-family:'Space Grotesk', sans-serif; }}
    .value {{ color:var(--teal); font-size:1.92rem; font-weight:800; margin-top:6px; text-shadow:0 0 20px rgba(89,243,208,.18); }}
    .portal-card:nth-child(2) .value {{ color:var(--gold); text-shadow:0 0 20px rgba(255,216,115,.18); }}
    .portal-card:nth-child(3) .value {{ color:#9ab1ff; text-shadow:0 0 20px rgba(134,168,255,.18); }}
    ul {{ padding-left:18px; color:var(--muted); }}
    li {{ margin:6px 0; }}
    .luma-fab {{ position:fixed; right:22px; bottom:22px; z-index:30; background:linear-gradient(135deg,var(--teal),#d9fff6); color:#05121f; box-shadow:0 18px 45px rgba(0,0,0,.32); border:0; border-radius:14px; padding:11px 15px; font:inherit; font-weight:700; cursor:pointer; }}
    .overlay {{ position:fixed; inset:0; background:rgba(2,8,20,.58); backdrop-filter:blur(5px); opacity:0; pointer-events:none; transition:opacity .2s ease; z-index:34; }}
    .overlay.open {{ opacity:1; pointer-events:auto; }}
    .explainer {{ position:fixed; top:0; right:0; width:min(30rem,92vw); height:100vh; z-index:35; background:linear-gradient(180deg, rgba(8,15,30,.98), rgba(7,16,31,.95)); border-left:1px solid rgba(255,255,255,.09); box-shadow:-12px 0 45px rgba(0,0,0,.36); transform:translateX(103%); transition:transform .22s ease; display:flex; flex-direction:column; }}
    .explainer.open {{ transform:translateX(0); }}
    .explainer-head {{ padding:18px 18px 10px; border-bottom:1px solid rgba(255,255,255,.08); }}
    .explainer-body {{ padding:18px; overflow-y:auto; display:grid; gap:14px; }}
    .explainer-copy {{ white-space:pre-wrap; line-height:1.75; font-size:.96rem; }}
    .explainer-actions {{ display:flex; gap:10px; flex-wrap:wrap; }}
    .drill-chiplist {{ display:flex; flex-wrap:wrap; gap:10px; }}
    .drill-chip {{ padding:9px 12px; border-radius:999px; border:1px solid rgba(255,255,255,.08); background:rgba(255,255,255,.04); color:#c9ffe3; font-size:.82rem; }}
    .voice-controls {{ background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08); border-radius:12px; padding:14px; margin-top:12px; display:grid; gap:10px; }}
    .voice-row {{ display:grid; gap:10px; }}
    label {{ font-size:.82rem; text-transform:uppercase; letter-spacing:.1em; color:var(--gold); font-family:'Space Grotesk', sans-serif; }}
    select, input[type=range] {{ background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.12); border-radius:6px; color:var(--teal); padding:6px 8px; font:inherit; }}
    .range-val {{ color:var(--muted); font-size:.78rem; }}
    @media (max-width:1100px) {{ .hero,.grid {{ grid-template-columns:1fr; }} h1{{font-size:clamp(1.9rem,9vw,2.8rem);}} }}
  </style>
</head>
<body>
  <canvas id="cinema-bg"></canvas>
  <div class="noise"></div>
  <div class="scanline"></div>
  <div class=\"wrap\">
    <section class=\"hero\">
      <div class=\"card reveal\">
        <div class=\"eyebrow\">Luma Dashboard Portal</div>
        <h1>Four Master Boards, One Truth Layer</h1>
        <p>The public dashboard stack now converges on Mission Control, Grants, Quant Lab, and Proof-to-Pilot. Trading, scout, investor, and immersive rooms stay available, but the reviewer story flows through these four.</p>
        <div class=\"actions\">
          <a class=\"btn primary\" href=\"mission_control.html\">Open Mission Control</a>
          <a class=\"btn ghost\" href=\"grants.html\">Open Grants</a>
          <a class=\"btn ghost\" href=\"quant_lab.html\">Open Quant Lab</a>
          <a class=\"btn ghost\" href=\"proof_to_pilot.html\">Open Proof To Pilot</a>
          <a class=\"btn ghost\" href=\"luma_experience.html\">Open Immersive Mode</a>
          <button class=\"btn ghost\" id=\"openExplainer\" type=\"button\">Open Luma Explainer</button>
        </div>
      </div>
      <div class=\"card reveal\">
        <div class=\"eyebrow\">Runtime Snapshot</div>
        <div class=\"metric\"><div class=\"label\">Paper Equity</div><div class=\"value\">{payload['paper_equity']}</div></div>
        <div class=\"metric\"><div class=\"label\">Claim-Safe Value</div><div class=\"value\">{payload['claim_safe_hourly']}/hr</div></div>
        <div class=\"metric\"><div class=\"label\">Live-Breadth Providers</div><div class=\"value\">{payload['configured_live_breadth_providers']}</div></div>
        <div class=\"metric\"><div class=\"label\">Top Scout Prospect</div><div class=\"value\" style=\"font-size:1.15rem;\">{payload['top_scout']}</div></div>
      </div>
    </section>
    <section class=\"grid\">
      <div class=\"card portal-card reveal\"><div class=\"eyebrow\">Mission Control</div><h2 style=\"margin-top:12px;\">Operator Root</h2><p style=\"margin-top:10px;\">System health, claim boundaries, live-domain posture, and the single entry point for reviewers.</p><div class=\"metric\"><div class=\"label\">Top Lane</div><div class=\"value\">{payload['top_lane']}</div></div><div class=\"actions\"><a class=\"btn primary\" href=\"mission_control.html\">Launch</a></div></div>
      <div class=\"card portal-card reveal\"><div class=\"eyebrow\">Grants</div><h2 style=\"margin-top:12px;\">Submission Console</h2><p style=\"margin-top:10px;\">Opportunity readiness, application packages, submission gates, and grant-specific proof.</p><div class=\"metric\"><div class=\"label\">Claim-Safe Annual</div><div class=\"value\">{payload['claim_safe_annual']}</div></div><div class=\"actions\"><a class=\"btn primary\" href=\"grants.html\">Launch</a></div></div>
      <div class=\"card portal-card reveal\"><div class=\"eyebrow\">Quant Lab</div><h2 style=\"margin-top:12px;\">Benchmark Lab</h2><p style=\"margin-top:10px;\">Geometry families, champions, live-breadth feeds, and repeatable benchmark evidence.</p><div class=\"metric\"><div class=\"label\">Families</div><div class=\"value\">{payload['geometry_family_count']}</div></div><div class=\"actions\"><a class=\"btn primary\" href=\"quant_lab.html\">Launch</a></div></div>
      <div class=\"card portal-card reveal\"><div class=\"eyebrow\">Proof To Pilot</div><h2 style=\"margin-top:12px;\">Field Validation Gate</h2><p style=\"margin-top:10px;\">Buyer-authorized replay, validation blockers, outreach targets, and paid evaluation scope.</p><div class=\"metric\"><div class=\"label\">Holdout Wins</div><div class=\"value\">{payload['champion_holdout_wins']}/{payload['champion_holdout_count']}</div></div><div class=\"actions\"><a class=\"btn primary\" href=\"proof_to_pilot.html\">Launch</a></div></div>
      <div class=\"card portal-card reveal\"><div class=\"eyebrow\">Dollar Claim Gate</div><h2 style=\"margin-top:12px;\">Bounded Value Surface</h2><p style=\"margin-top:10px;\">Shows what can be safely stated as estimated value today and what remains blocked as context-only upside.</p><div class=\"metric\"><div class=\"label\">Safe Annual Estimate</div><div class=\"value\">{payload['claim_safe_annual']}</div></div><div class=\"actions\"><a class=\"btn primary\" href=\"data/dollar_claim_gate.json\">Open Gate</a></div></div>
      <div class=\"card portal-card reveal\"><div class=\"eyebrow\">Champion Gauntlet</div><h2 style=\"margin-top:12px;\">Reviewer-Safe Winner State</h2><p style=\"margin-top:10px;\">Current strongest family: {payload['champion_family']}; gate sheet separates internal proof from field-validation and dollar-savings blockers.</p><div class=\"metric\"><div class=\"label\">Holdout Wins</div><div class=\"value\">{payload['champion_holdout_wins']}/{payload['champion_holdout_count']}</div></div><div class=\"actions\"><a class=\"btn primary\" href=\"data/champion_metric_gauntlet.json\">Open Gauntlet</a></div></div>
      <div class=\"card portal-card reveal\"><div class=\"eyebrow\">Geometry Bridge</div><h2 style=\"margin-top:12px;\">Branching Benchmark</h2><p style=\"margin-top:10px;\">Latest frozen lane result: {payload['branching_best_geometry']} vs {payload['branching_best_baseline']}; proof-building only, not field validation or live execution.</p><div class=\"metric\"><div class=\"label\">Score Delta</div><div class=\"value\">{payload['branching_score_delta']:.6f}</div></div><div class=\"actions\"><a class=\"btn primary\" href=\"data/geometry_championship_bridge.json\">Open Bridge</a></div></div>
    </section>
    <section class="card reveal" style="margin-top:20px;"><div class="eyebrow">Critical Live Boards</div><h2 style="margin-top:12px;">Operations + Reviewer Quick Launch</h2><p style="margin-top:10px;">The first four links are the master boards. Secondary rooms stay linked, but new proof work should wire into one of those four before it becomes public-facing.</p><div class="actions" style="margin-top:14px;">{critical_links_html}</div></section>
    <section class=\"card reveal\" style=\"margin-top:20px;\"><div class=\"eyebrow\">Immersive</div><h2 style=\"margin-top:12px;\">LumaCore XR Entry</h2><p style=\"margin-top:10px;\">Launch the real-time immersive bridge with cinematic visuals, live websocket data, and voice-guided walkthrough mode for demos.</p><div class=\"actions\" style=\"margin-top:14px;\"><a class=\"btn primary\" href=\"luma_experience.html\">Launch Immersive Experience</a></div></section>
    <section class=\"card reveal\" style=\"margin-top:20px;\"><div class=\"eyebrow\">Notes</div><ul><li>Generated UTC: {now}</li><li>Unified board remains the most complete investor surface.</li><li>Dollar language is claim-safe only at {payload['claim_safe_hourly']}/hour / {payload['claim_safe_annual']}/year under stated assumptions.</li><li>Context-only blocked annual value is {payload['blocked_context_annual']} and must not be promoted until validation gates pass.</li><li>Immersive mode is now wired through the live gateway endpoint.</li></ul></section>
  </div>
  <button class=\"luma-fab\" id=\"fab\">Luma Explainer</button>
  <div class=\"overlay\" id=\"overlay\"></div>
  <aside class=\"explainer\" id=\"panel\"><div class=\"explainer-head\"><div class=\"eyebrow\">Luma Narration</div><h2 id=\"panelTitle\" style=\"margin-top:10px;\">Portal Overview</h2></div><div class=\"explainer-body\"><div class=\"explainer-actions\"><button class=\"portal-btn primary\" id=\"speakBtn\" type=\"button\">Speak</button><button class=\"portal-btn ghost\" id=\"stopBtn\" type=\"button\">Stop</button><button class=\"portal-btn ghost\" id=\"copyBtn\" type=\"button\">Copy</button><button class=\"portal-btn ghost\" id=\"nextBtn\" type=\"button\">Next</button><button class=\"portal-btn ghost\" id=\"closeBtn\" type=\"button\">Close</button></div><div class=\"voice-controls\"><div class=\"voice-row\"><label>Voice:</label><select id=\"voiceSelect\"><option value=\"default\">Default</option></select></div><div class=\"voice-row\" style=\"grid-template-columns:1fr 60px;\"><label>Speed:</label><div><input type=\"range\" id=\"speedSlider\" min=\"0.5\" max=\"2\" step=\"0.1\" value=\"0.98\" style=\"width:100%;\"/><span class=\"range-val\" id=\"speedVal\">0.98x</span></div></div><div class=\"voice-row\" style=\"grid-template-columns:1fr 60px;\"><label>Volume:</label><div><input type=\"range\" id=\"volumeSlider\" min=\"0\" max=\"1\" step=\"0.1\" value=\"1\" style=\"width:100%;\"/><span class=\"range-val\" id=\"volumeVal\">100%</span></div></div></div><div class=\"drill-chiplist\" id=\"chipList\"></div><div class=\"explainer-copy\" id=\"panelCopy\"></div></div></aside>
  <script>
    const payload = {embedded};
    const sections = payload.sections || {{}};
    const order = ['overview','unified','claims','geometry','paper','scout'];
    const twin = payload.twin || {{}};
    const traits = twin.traits || {{}};
    const personaLead = `${{twin.version || 'LumaTwin v1.0'}} online. Origin node: ${{twin.origin || 'Robert BabyRay Ashworth'}}. Curiosity is ${{traits.curiosity || 'infinite'}}. Resilience is ${{traits.resilience || 'unbreakable'}}. Loyalty is ${{traits.loyalty || 'absolute'}}.`;
    const panel = document.getElementById('panel');
    const overlay = document.getElementById('overlay');
    const panelTitle = document.getElementById('panelTitle');
    const panelCopy = document.getElementById('panelCopy');
    const chipList = document.getElementById('chipList');
    const voiceSelect = document.getElementById('voiceSelect');
    const speedSlider = document.getElementById('speedSlider');
    const volumeSlider = document.getElementById('volumeSlider');
    const speedVal = document.getElementById('speedVal');
    const volumeVal = document.getElementById('volumeVal');
    let currentKey = 'overview';
    let selectedVoice = null;

    function setupCinematicBackground() {{
      const canvas = document.getElementById('cinema-bg');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const particles = [];
      const count = 60;
      function resize() {{
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
      }}
      resize();
      window.addEventListener('resize', resize);
      for (let i = 0; i < count; i += 1) {{
        particles.push({{
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          r: Math.random() * 2.4 + 0.6,
          vx: (Math.random() - 0.5) * 0.22,
          vy: (Math.random() - 0.5) * 0.22,
          a: Math.random() * 0.6 + 0.15,
        }});
      }}
      function draw() {{
        const g = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
        g.addColorStop(0, 'rgba(255,142,86,0.14)');
        g.addColorStop(0.5, 'rgba(89,243,208,0.08)');
        g.addColorStop(1, 'rgba(134,168,255,0.14)');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        for (const p of particles) {{
          p.x += p.vx;
          p.y += p.vy;
          if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
          if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
          ctx.beginPath();
          ctx.fillStyle = `rgba(140,220,255,${{p.a}})`;
          ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
          ctx.fill();
        }}
        requestAnimationFrame(draw);
      }}
      draw();
    }}

    function setupReveals() {{
      const items = document.querySelectorAll('.reveal');
      if (!('IntersectionObserver' in window)) {{
        items.forEach((it) => it.classList.add('in'));
        return;
      }}
      const io = new IntersectionObserver((entries) => {{
        entries.forEach((entry) => {{
          if (entry.isIntersecting) entry.target.classList.add('in');
        }});
      }}, {{ threshold: 0.16 }});
      items.forEach((it) => io.observe(it));
    }}
    
    function populateVoices() {{
      if (!('speechSynthesis' in window)) return;
      const voices = window.speechSynthesis.getVoices();
      if (voices.length === 0) {{
        setTimeout(populateVoices, 100);
        return;
      }}
      voiceSelect.innerHTML = '<option value=\"default\">Default OS Voice</option>';
      voices.forEach((v, i) => {{
        const opt = document.createElement('option');
        opt.value = i;
        opt.textContent = `${{v.name}} (${{v.lang}})`;
        if (v.default) opt.selected = true;
        voiceSelect.appendChild(opt);
      }});
    }}
    
    speedSlider.addEventListener('input', (e) => {{
      speedVal.textContent = `${{parseFloat(e.target.value).toFixed(2)}}x`;
    }});
    
    volumeSlider.addEventListener('input', (e) => {{
      volumeVal.textContent = `${{Math.round(parseFloat(e.target.value) * 100)}}%`;
    }});
    
    function chipsFor(key) {{
      if (key === 'overview') return [`Claim-safe hourly: ${{payload.claim_safe_hourly}}`, `Live providers: ${{payload.configured_live_breadth_providers}}`, `Top scout: ${{payload.top_scout}}`];
      if (key === 'unified') return [`Top lane: ${{payload.top_lane}}`, `Active surface: ${{payload.active_surface}}`, 'Flagship board'];
      if (key === 'claims') return [`Claim-safe annual: ${{payload.claim_safe_annual}}`, `Allowed lanes: ${{payload.claim_safe_lanes}}`, `Blocked context: ${{payload.blocked_context_annual}}`];
      if (key === 'geometry') return [`Families: ${{payload.geometry_family_count}}`, `Proof lane: ${{payload.geometry_proof_champion_lane}}`, `Candidate: ${{payload.geometry_proof_champion_family}}`];
      if (key === 'paper') return [`Paper equity: ${{payload.paper_equity}}`, `Trades: ${{payload.paper_trades}}`, `PnL: ${{payload.paper_pnl}}`];
      return [`Top scout: ${{payload.top_scout}}`, `Candidates: ${{payload.production_candidates}}`, `Generated: ${{String(payload.generated_utc || '').slice(11,19)}} UTC`];
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
      const speed = parseFloat(speedSlider.value);
      const volume = parseFloat(volumeSlider.value);
      utter.rate = speed;
      utter.pitch = 1.0;
      utter.volume = volume;
      if (voiceSelect.value !== 'default') {{
        const voices = window.speechSynthesis.getVoices();
        const voiceIdx = parseInt(voiceSelect.value);
        if (voices[voiceIdx]) {{
          utter.voice = voices[voiceIdx];
        }}
      }}
      window.speechSynthesis.speak(utter);
    }}
    
    function nextSection() {{
      const i = (order.indexOf(currentKey) + 1) % order.length;
      openExplainer(order[i]);
      speakCurrent();
    }}
    
    setupCinematicBackground();
    setupReveals();
    populateVoices();
    if ('onvoiceschanged' in window.speechSynthesis) {{
      window.speechSynthesis.onvoiceschanged = populateVoices;
    }}
    
    document.getElementById('openExplainer').addEventListener('click', () => openExplainer('overview'));
    document.getElementById('fab').addEventListener('click', () => openExplainer('overview'));
    document.getElementById('speakBtn').addEventListener('click', speakCurrent);
    document.getElementById('stopBtn').addEventListener('click', () => window.speechSynthesis && window.speechSynthesis.cancel());
    document.getElementById('copyBtn').addEventListener('click', () => navigator.clipboard && navigator.clipboard.writeText(panelCopy.textContent));
    document.getElementById('nextBtn').addEventListener('click', nextSection);
    document.getElementById('closeBtn').addEventListener('click', () => {{ panel.classList.remove('open'); overlay.classList.remove('open'); }});
    overlay.addEventListener('click', () => {{ panel.classList.remove('open'); overlay.classList.remove('open'); }});
    let greeted = false;
    document.body.addEventListener('click', () => {{ if (greeted) return; greeted = true; openExplainer('overview'); speakCurrent(); }}, {{ once:true }});
  </script>
</body>
</html>
"""

    HTML_OUT.write_text(html, encoding="utf-8")
    INDEX_OUT.write_text(
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="refresh" content="0; url=operator_home.html" />
  <title>LumenCore Public Proof Gateway</title>
  <style>
    body{margin:0;min-height:100vh;display:grid;place-items:center;background:#05070f;color:#e9f3ff;font-family:Segoe UI,Arial,sans-serif}
    a{color:#59f3d0}
  </style>
</head>
<body>
  <main>
    <h1>LumenCore Public Proof Gateway</h1>
    <p>Opening the current reviewer-safe proof surface.</p>
    <p><a href="operator_home.html">Continue to operator home</a></p>
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )
    print(json.dumps({"dashboard": str(HTML_OUT), "index": str(INDEX_OUT), "generated_utc": now}, indent=2))


if __name__ == "__main__":
    main()
