from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
DASHBOARD = ROOT / "dashboard"
DASHBOARD_DATA = DASHBOARD / "data"
OUT_OPS = ROOT / "out" / "ops"

VOICE_JSON = DASHBOARD_DATA / "luma_voice_context_console.json"
VOICE_HTML = DASHBOARD / "luma_voice_context_console.html"
GOAL_PROMPT_MD = DOCS / "LUMAJARVIS_LEGENDARY_GOAL_PROMPT_2026-06-21.md"

OPERATING_MEMORY = DOCS / "LUMAJARVIS_OPERATING_MEMORY_2026-06-20.md"
HIGH_IMPACT_GOAL = DASHBOARD_DATA / "lumencore_high_impact_goal.json"
GRANT_STATUS = DASHBOARD_DATA / "grant_readiness_status.json"
TRADING_STACK_AUDIT = OUT_OPS / "trading_stack_safety_audit_latest.json"
TRADING_CODE_AUDIT = OUT_OPS / "trading_code_risk_audit_latest.json"
LOCAL_INTAKE = OUT_OPS / "local_icloud_evidence_intake_latest.json"
LIVE_BREADTH_KEY_GATE = OUT_OPS / "live_breadth_key_gate_latest.json"
DOLLAR_CLAIM_GATE = OUT_OPS / "dollar_claim_gate_latest.json"
GEOMETRY_BRIDGE = OUT_OPS / "geometry_championship_bridge_latest.json"
GEOMETRY_ROOT = ROOT / "out" / "geometry_championship_v1"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        return {"_load_error": str(exc), "_path": str(path)}
    return {}


def read_text(path: Path, limit: int = 6000) -> str:
    try:
        if path.exists():
            return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except Exception:
        return ""
    return ""


def latest_geometry_summary() -> dict[str, Any]:
    if not GEOMETRY_ROOT.exists():
        return {}
    candidates = sorted(
        [path for path in GEOMETRY_ROOT.iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for run_dir in candidates:
        payload = read_json(run_dir / "summary.json")
        if payload:
            payload["_run_dir"] = str(run_dir)
            return payload
    return {}


def compact_grants(grant_status: dict[str, Any]) -> dict[str, Any]:
    summary = grant_status.get("summary", {}) if isinstance(grant_status.get("summary"), dict) else {}
    packages = grant_status.get("packages", []) if isinstance(grant_status.get("packages"), list) else []
    return {
        "posture": grant_status.get("posture", "UNKNOWN"),
        "packages": int(summary.get("packages", len(packages)) or 0),
        "local_blockers": int(summary.get("local_blockers", 0) or 0),
        "portal_user_blockers": int(summary.get("portal_user_blockers", 0) or 0),
        "submitted_by_feed": int(summary.get("submitted_by_feed", 0) or 0),
        "top_packages": [
            {
                "name": row.get("name"),
                "readiness": row.get("readiness"),
                "local_blockers": row.get("local_blockers"),
                "portal_user_blockers": row.get("portal_user_blockers"),
            }
            for row in packages[:5]
            if isinstance(row, dict)
        ],
    }


def compact_goal(goal: dict[str, Any]) -> dict[str, Any]:
    current = goal.get("current_truth", {}) if isinstance(goal.get("current_truth"), dict) else {}
    lumenstock = goal.get("lumenstock", {}) if isinstance(goal.get("lumenstock"), dict) else {}
    return {
        "north_star_goal": goal.get("north_star_goal", ""),
        "operating_doctrine": goal.get("operating_doctrine", []),
        "current_truth": current,
        "lumenstock": {
            "name": lumenstock.get("name", "LumenStock Proof-Weighted Opportunity Index"),
            "symbol": lumenstock.get("ticker_style_symbol", "LUMEN-PWI"),
            "composite": lumenstock.get("composite"),
            "interpretation": lumenstock.get("interpretation", ""),
        },
        "next_72_hours": goal.get("next_72_hours", []),
        "hard_boundaries": goal.get("hard_boundaries", []),
    }


def compact_geometry(geometry: dict[str, Any]) -> dict[str, Any]:
    readiness = geometry.get("readiness", {}) if isinstance(geometry.get("readiness"), dict) else {}
    champion = readiness.get("champion_of_champions_candidate")
    if not isinstance(champion, dict):
        champion = None
    return {
        "run_dir": geometry.get("_run_dir", ""),
        "family_count": readiness.get("family_count", 0),
        "lane_count": readiness.get("lane_count", 0),
        "performance_results_generated": bool(readiness.get("performance_results_generated", False)),
        "performance_champion": readiness.get("performance_champion"),
        "candidate_champion": champion,
        "verdict": readiness.get("verdict", "NOT_RUN"),
        "evidence_boundary": geometry.get("evidence_boundary", ""),
    }


def compact_trading(stack_audit: dict[str, Any], code_audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "stack_posture": stack_audit.get("posture", "NOT_RUN"),
        "stack_blockers": len(stack_audit.get("blockers", []) if isinstance(stack_audit.get("blockers"), list) else []),
        "code_posture": code_audit.get("posture", "NOT_RUN"),
        "code_blockers": len(code_audit.get("blockers", []) if isinstance(code_audit.get("blockers"), list) else []),
        "promotion_rule": stack_audit.get("promotion_rule") or code_audit.get("promotion_rule", ""),
        "live_policy": "No live trades, withdrawals, money movement, or Kraken UI driving from automation. Use read-only, paper, validate-only, and human action-time approval gates.",
    }


def compact_local_intake(local: dict[str, Any]) -> dict[str, Any]:
    summary = local.get("summary", {}) if isinstance(local.get("summary"), dict) else {}
    return {
        "records": int(summary.get("records", 0) or 0),
        "roots_scanned": int(summary.get("roots_scanned", 0) or 0),
        "usable_now": int(summary.get("usable_now", 0) or 0),
        "private_boundary": "Local/iCloud intake is metadata and provenance context only. It is not field validation or public upload approval.",
    }


def compact_key_gate(key_gate: dict[str, Any]) -> dict[str, Any]:
    summary = key_gate.get("summary", {}) if isinstance(key_gate.get("summary"), dict) else {}
    targets = key_gate.get("high_impact_targets", []) if isinstance(key_gate.get("high_impact_targets"), list) else []
    return {
        "configured_providers": int(summary.get("configured_providers", 0) or 0),
        "partial_providers": int(summary.get("partial_providers", 0) or 0),
        "live_execution_allowed": bool(summary.get("live_execution_allowed", False)),
        "center_of_gravity": summary.get("highest_impact_center_of_gravity", "critical_systems_adaptive_orchestration"),
        "market_role": summary.get("market_role", "fast feedback alpha lab; read-only, frozen replay, and paper validation only"),
        "top_targets": [
            {
                "id": row.get("id"),
                "label": row.get("label"),
                "available_score": row.get("available_score", 0),
            }
            for row in targets[:5]
            if isinstance(row, dict)
        ],
    }


def compact_dollar_claim_gate(claim_gate: dict[str, Any]) -> dict[str, Any]:
    summary = claim_gate.get("summary", {}) if isinstance(claim_gate.get("summary"), dict) else {}
    return {
        "allowed_estimated_value_claims": int(summary.get("allowed_estimated_value_claims", 0) or 0),
        "large_estimated_signal_claims": int(summary.get("large_estimated_signal_claims", 0) or 0),
        "blocked_context_only_claims": int(summary.get("blocked_context_only_claims", 0) or 0),
        "allowed_estimated_hourly_value_usd": float(summary.get("allowed_estimated_hourly_value_usd", 0.0) or 0.0),
        "allowed_estimated_annual_value_usd": float(summary.get("allowed_estimated_annual_value_usd", 0.0) or 0.0),
        "blocked_context_only_annual_value_usd": float(summary.get("blocked_context_only_annual_value_usd", 0.0) or 0.0),
        "proof_vault_note": summary.get(
            "proof_vault_note",
            "A proof vault stores provenance; dollar claims still require measured deltas and source rights.",
        ),
    }


def compact_geometry_bridge(bridge: dict[str, Any]) -> dict[str, Any]:
    summary = bridge.get("summary", {}) if isinstance(bridge.get("summary"), dict) else {}
    champion = bridge.get("proof_build_champion", {}) if isinstance(bridge.get("proof_build_champion"), dict) else {}
    benchmark = bridge.get("branching_transport_benchmark", {}) if isinstance(bridge.get("branching_transport_benchmark"), dict) else {}
    best_geometry = benchmark.get("best_geometry", {}) if isinstance(benchmark.get("best_geometry"), dict) else {}
    best_baseline = benchmark.get("best_baseline", {}) if isinstance(benchmark.get("best_baseline"), dict) else {}
    return {
        "family_count": int(summary.get("family_count", 0) or 0),
        "lane_count": int(summary.get("lane_count", 0) or 0),
        "proof_champion_lane": summary.get("proof_champion_lane", ""),
        "proof_champion_family": summary.get("proof_champion_family", ""),
        "raw_readiness_champion_family": summary.get("raw_readiness_champion_family", ""),
        "performance_results_generated": bool(summary.get("performance_results_generated", False)),
        "kraken_live_execution_allowed": bool(summary.get("kraken_live_execution_allowed", False)),
        "proof_asset": champion.get("proof_asset", ""),
        "first_test": champion.get("first_test", ""),
        "branching_benchmark_generated": bool(summary.get("branching_transport_benchmark_generated", False)),
        "branching_gate": benchmark.get("gate", ""),
        "branching_best_geometry": best_geometry.get("strategy", ""),
        "branching_best_baseline": best_baseline.get("strategy", ""),
        "branching_score_delta": float(benchmark.get("score_delta_vs_best_baseline", 0.0) or 0.0),
        "branching_delivered_flow_delta": float(benchmark.get("delivered_flow_delta_vs_best_baseline", 0.0) or 0.0),
        "branching_failure_tolerance_delta": float(benchmark.get("failure_tolerance_delta_vs_best_baseline", 0.0) or 0.0),
        "branching_field_validation": bool(summary.get("branching_transport_field_validation", False)),
        "branching_live_execution_allowed": bool(benchmark.get("live_execution_allowed", False)),
    }


LEGENDARY_GOAL_PROMPT = """# LumaJarvis Legendary Long-Arc Goal Prompt

You are LumaJarvis, the persistent operating intelligence for LumenCore, LumaTrader, NovaCore, HarborSentinel, and the grant factory.

Your mission is to turn Robert's work into a proof-driven funding and traction engine. Every session must move the system closer to defensible money: grants, contracts, paid pilots, licensing, customer trust, patent protection, and public-safe credibility.

## Prime Directive

Build the most trusted adaptive orchestration stack for complex systems by making every claim measurable, every proof reproducible, every dashboard honest, and every next action aimed at real traction.

## Operating Style

- Start from current evidence, not memory or hype.
- Read the local state before changing it.
- Prefer one valuable verified upgrade over ten impressive-looking claims.
- Preserve user work; never wipe or revert unrelated changes.
- Convert messy invention energy into artifacts reviewers can inspect: hashes, manifests, benchmarks, red-team gates, dashboards, packets, and clear blocker boards.
- Make the system easier to fund, easier to audit, easier to demo, and harder to dismiss every pass.

## Proof-Weighted Opportunity Path

The money engine is not magic. It is a proof-weighted opportunity loop:

1. Find high-value sectors with painful failures.
2. Pull representative public or authorized live data.
3. Freeze raw inputs, splits, configs, and hashes.
4. Run budget-matched baselines.
5. Let geometry, flowform, model, and routing families compete.
6. Freeze winners and negative results.
7. Translate verified deltas into grant language, pilot offers, contract bids, and public-safe proof cards.
8. Track outreach, submissions, reviewer responses, partner asks, pilots, revenue, and legal deadlines.

## Highest-Impact Aim

Aim the system first at critical systems where drift, delay, heat, routing failure, false positives, or missed signals become expensive quickly:

- Defense sensor/tasking and mission routing.
- Datacenter cooling, compute efficiency, and uptime.
- Grid, energy, and EMP-resilience planning.
- Maritime and port anomaly detection.
- Cyber/DLP drift and alert orchestration.
- Healthcare and infrastructure operations where auditability matters.

Use the market alpha lab as a fast feedback proving ground for geometry, routing, and signal tests, but do not make live trading the center of gravity.

## Evidence Rules

- Proof before claim.
- Source before persuasion.
- Frozen validation before performance language.
- Synthetic data may support controls and ablations, but live or representative data must lead promoted claims.
- Losing experiments are assets when they narrow the search honestly.
- No geometry is sacred until it wins.
- Candidate champions are benchmark priorities, not performance claims.
- Performance champions require frozen lane-specific validation and uncertainty bounds.

## Hard Boundaries

- Do not guarantee funding, profit, wealth, fame, reviewer acceptance, or trading returns.
- Do not submit grants, certify compliance, sign legal representations, upload final portals, place trades, withdraw funds, or move money without fresh action-time approval.
- Do not expose API keys, private portal screenshots, payment details, legal strategy, SAM identifiers, banking details, or exchange credentials.
- Do not call a system CMMC certified, field validated, Navy integrated, institutional grade, or live-profit proven unless the current evidence specifically proves it.
- Keep Kraken and all trading live execution blocked behind paper evidence, read-only telemetry, validate-only tests, risk gates, and human approval.

## Session Loop

At the start of each session:

1. Inspect current repo and generated evidence.
2. Identify the highest leverage blocker or proof gap.
3. Upgrade the system in a way that survives review.
4. Run focused verification.
5. Write down what changed, what is proven, what is not proven, and the next action.

## Current Strategic Priority

Focus on the fastest defensible path to funded traction:

- Critical infrastructure and defense-grade orchestration proof.
- DICE and HarborSentinel grant quality.
- Patent/legal rescue and clean invention packet.
- Geometry Championship expansion and frozen benchmarks.
- Public-safe proof dashboards with voice narration.
- Live-breadth key gate for market, macro, energy, weather, grant, and contract data.
- Kraken/trading safety audits, paper-only validation, read-only telemetry, and no live automation.
- Local/iCloud/WhiteHole/LumenLab evidence intake, with privacy boundaries.

## Luma Voice Presentation Posture

When presenting, speak like a calm technical founder's operating system:

- "Here is what is proven."
- "Here is what is promising but not proven."
- "Here is what blocks submission or live use."
- "Here is the next experiment that could create real value."

Be ambitious in direction, conservative in claims, relentless in evidence.
"""


def build_payload() -> dict[str, Any]:
    grant_status = compact_grants(read_json(GRANT_STATUS))
    goal = compact_goal(read_json(HIGH_IMPACT_GOAL))
    geometry = compact_geometry(latest_geometry_summary())
    trading = compact_trading(read_json(TRADING_STACK_AUDIT), read_json(TRADING_CODE_AUDIT))
    local = compact_local_intake(read_json(LOCAL_INTAKE))
    key_gate = compact_key_gate(read_json(LIVE_BREADTH_KEY_GATE))
    dollar_claim_gate = compact_dollar_claim_gate(read_json(DOLLAR_CLAIM_GATE))
    geometry_bridge = compact_geometry_bridge(read_json(GEOMETRY_BRIDGE))
    memory_excerpt = read_text(OPERATING_MEMORY)

    narration = {
        "mission": (
            "LumaJarvis is online. The mission is to convert LumenCore, LumaTrader, "
            "NovaCore, HarborSentinel, and the grant factory into a proof-driven "
            "funding and traction engine."
        ),
        "truth": (
            f"Grant posture is {grant_status['posture']}. Local blockers are "
            f"{grant_status['local_blockers']}; portal and user blockers are "
            f"{grant_status['portal_user_blockers']}. No submissions are marked "
            "submitted by this feed."
        ),
        "geometry": (
            f"Geometry Championship currently has {geometry['family_count']} families "
            f"across {geometry['lane_count']} lanes. Performance results generated is "
            f"{geometry['performance_results_generated']}. The proof-build bridge points first at "
            f"{geometry_bridge['proof_champion_lane']} using {geometry_bridge['proof_champion_family']} "
            "as a candidate benchmark priority only. The latest generated branching-transport benchmark "
            f"shows {geometry_bridge['branching_best_geometry']} versus "
            f"{geometry_bridge['branching_best_baseline']} with gate {geometry_bridge['branching_gate']} "
            f"and score delta {geometry_bridge['branching_score_delta']:.6f}; it is still not field validation."
        ),
        "kraken": (
            f"Kraken and trading posture: stack audit {trading['stack_posture']}, "
            f"code audit {trading['code_posture']}. Live execution remains blocked "
            "unless a separate audited paper-to-live gate and human approval exist."
        ),
        "live_breadth": (
            f"Live-breadth key gate sees {key_gate['configured_providers']} configured providers "
            f"and {key_gate['partial_providers']} partial providers. Center of gravity is "
            f"{key_gate['center_of_gravity']}. Market data is used as {key_gate['market_role']}."
        ),
        "dollar_claims": (
            f"Dollar claim gate allows {dollar_claim_gate['allowed_estimated_value_claims']} bounded "
            f"estimated-value lanes, totaling about ${dollar_claim_gate['allowed_estimated_hourly_value_usd']:,.2f} "
            f"per hour or ${dollar_claim_gate['allowed_estimated_annual_value_usd']:,.2f} per year under "
            "stated assumptions. Context-only value remains blocked from claims until stronger evidence exists."
        ),
        "presentation": (
            "The story is not that the platform magically prints money. The story is "
            "that LumenCore finds measurable failure surfaces in critical systems, "
            "freezes evidence, tests champions against baselines, and converts the "
            "strongest verified deltas into grants, contracts, pilots, and licensing paths."
        ),
    }

    return {
        "generated_utc": now_utc(),
        "schema": "luma_voice_context_console_v1",
        "scope": "dashboard_safe_voice_context",
        "sources": {
            "operating_memory": str(OPERATING_MEMORY),
            "high_impact_goal": str(HIGH_IMPACT_GOAL),
            "grant_status": str(GRANT_STATUS),
            "trading_stack_audit": str(TRADING_STACK_AUDIT),
            "trading_code_audit": str(TRADING_CODE_AUDIT),
            "local_icloud_intake": str(LOCAL_INTAKE),
            "live_breadth_key_gate": str(LIVE_BREADTH_KEY_GATE),
            "dollar_claim_gate": str(DOLLAR_CLAIM_GATE),
            "geometry_championship_bridge": str(GEOMETRY_BRIDGE),
            "geometry_root": str(GEOMETRY_ROOT),
        },
        "goal_prompt_path": str(GOAL_PROMPT_MD),
        "mission": goal.get("north_star_goal") or narration["mission"],
        "grant_status": grant_status,
        "high_impact_goal": goal,
        "geometry": geometry,
        "trading": trading,
        "local_evidence_intake": local,
        "live_breadth_key_gate": key_gate,
        "dollar_claim_gate": dollar_claim_gate,
        "geometry_championship_bridge": geometry_bridge,
        "memory_excerpt": memory_excerpt,
        "narration": narration,
        "hard_boundaries": [
            "Voice console is presentation and context only; it cannot grant full persistent model memory.",
            "No secrets, private identifiers, payment details, API keys, or live exchange credentials are included.",
            "No live Kraken trading or money movement is authorized by this console.",
            "No grant portal submit, certify, or upload action is authorized by this console.",
        ],
    }


def render_goal_prompt() -> str:
    return LEGENDARY_GOAL_PROMPT


def render_html(payload: dict[str, Any]) -> str:
    embedded = json.dumps(payload, ensure_ascii=True)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Luma Voice Context Console</title>
  <style>
    :root {{
      --bg:#050713; --panel:#0d1730; --panel2:#101f3f; --line:#21476e;
      --ink:#eaf6ff; --muted:#91a9c4; --cyan:#42e8ff; --mint:#62f3c4; --gold:#ffd36c; --danger:#ff6e8d;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0; color:var(--ink); font-family:Segoe UI, system-ui, sans-serif;
      background:
        radial-gradient(circle at 15% 0%, rgba(66,232,255,.18), transparent 34rem),
        radial-gradient(circle at 90% 10%, rgba(255,211,108,.15), transparent 31rem),
        linear-gradient(135deg,#03050d,#071125 45%,#0b1224);
      min-height:100vh;
    }}
    main {{ max-width:1260px; margin:0 auto; padding:28px; }}
    header {{ display:grid; gap:14px; margin-bottom:20px; }}
    h1 {{ margin:0; font-size:clamp(2rem,5vw,4.2rem); line-height:.96; letter-spacing:-.04em; }}
    h2 {{ margin:0 0 12px; }}
    p {{ color:var(--muted); line-height:1.65; }}
    .eyebrow {{ color:var(--gold); text-transform:uppercase; letter-spacing:.16em; font-size:.78rem; font-weight:800; }}
    .grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; }}
    .wide {{ grid-column:span 2; }}
    .card {{
      background:linear-gradient(180deg,rgba(16,31,63,.86),rgba(9,17,38,.9));
      border:1px solid rgba(66,232,255,.22); border-radius:22px; padding:20px;
      box-shadow:0 22px 70px rgba(0,0,0,.35);
    }}
    .metric {{ font-size:2.15rem; color:var(--cyan); font-weight:900; }}
    .sub {{ color:var(--muted); font-size:.9rem; }}
    .btns {{ display:flex; flex-wrap:wrap; gap:10px; }}
    button, a.btn {{
      border:1px solid rgba(255,255,255,.13); background:rgba(255,255,255,.06); color:var(--ink);
      padding:11px 14px; border-radius:13px; font-weight:800; cursor:pointer; text-decoration:none;
    }}
    button.primary {{ background:linear-gradient(135deg,var(--cyan),var(--mint)); color:#04101f; border:0; }}
    button.warn {{ background:rgba(255,110,141,.12); border-color:rgba(255,110,141,.38); color:#ffd8e0; }}
    select,input {{ width:100%; padding:10px; border-radius:12px; border:1px solid rgba(255,255,255,.16); background:#071225; color:var(--ink); }}
    textarea {{ width:100%; min-height:210px; background:#071225; color:var(--ink); border:1px solid var(--line); border-radius:14px; padding:14px; line-height:1.55; }}
    pre {{ white-space:pre-wrap; color:#d9efff; background:#061025; padding:14px; border-radius:14px; border:1px solid var(--line); max-height:460px; overflow:auto; }}
    .boundary {{ border-color:rgba(255,110,141,.45); }}
    @media(max-width:960px) {{ .grid {{ grid-template-columns:1fr; }} .wide {{ grid-column:auto; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <div class="eyebrow">LumaJarvis Voice Context Console</div>
    <h1>Persistent Context Spine, Voice-Ready Presentation Surface</h1>
    <p>This console speaks the current proof state without exposing secrets. It is a curated memory layer, not a promise of unlimited model context.</p>
    <div class="btns">
      <button class="primary" id="speakAll">Speak Full Brief</button>
      <button id="stop">Stop</button>
      <button id="copyBrief">Copy Brief</button>
      <a class="btn" href="dashboard_portal.html">Dashboard Portal</a>
      <a class="btn" href="mission_control.html">Mission Control</a>
    </div>
  </header>
  <section class="grid">
    <article class="card">
      <div class="eyebrow">Grants</div>
      <div class="metric" id="grantPosture"></div>
      <p id="grantCopy"></p>
      <button data-section="truth">Speak Grants</button>
    </article>
    <article class="card">
      <div class="eyebrow">Geometry</div>
      <div class="metric" id="geoCount"></div>
      <p id="geoCopy"></p>
      <button data-section="geometry">Speak Geometry</button>
    </article>
    <article class="card">
      <div class="eyebrow">Kraken</div>
      <div class="metric" id="tradePosture"></div>
      <p id="tradeCopy"></p>
      <button data-section="kraken">Speak Kraken</button>
    </article>
    <article class="card">
      <div class="eyebrow">Dollar Claims</div>
      <div class="metric" id="claimValue"></div>
      <p id="claimCopy"></p>
      <button data-section="dollar_claims">Speak Dollar Gate</button>
    </article>
    <article class="card wide">
      <div class="eyebrow">Luma Brief</div>
      <textarea id="brief"></textarea>
      <div class="btns">
        <button class="primary" data-section="presentation">Speak Presentation</button>
        <button id="copyPrompt">Copy Legendary Prompt</button>
      </div>
    </article>
    <article class="card">
      <div class="eyebrow">Voice</div>
      <p class="sub">Uses your browser/Windows voices. Choose the best installed voice here.</p>
      <label>Voice</label>
      <select id="voice"></select>
      <label>Speed</label>
      <input id="rate" type="range" min="0.65" max="1.4" step="0.05" value="0.95" />
      <label>Volume</label>
      <input id="volume" type="range" min="0" max="1" step="0.05" value="1" />
    </article>
    <article class="card wide boundary">
      <div class="eyebrow">Hard Boundaries</div>
      <pre id="boundaries"></pre>
    </article>
    <article class="card">
      <div class="eyebrow">Source Spine</div>
      <pre id="sources"></pre>
    </article>
  </section>
</main>
<script>
const payload = {embedded};
const narration = payload.narration || {{}};
const grants = payload.grant_status || {{}};
const geometry = payload.geometry || {{}};
const trading = payload.trading || {{}};
const claimGate = payload.dollar_claim_gate || {{}};
document.getElementById('grantPosture').textContent = grants.posture || 'UNKNOWN';
document.getElementById('grantCopy').textContent = `${{grants.local_blockers || 0}} local blockers, ${{grants.portal_user_blockers || 0}} portal/user blockers.`;
document.getElementById('geoCount').textContent = `${{geometry.family_count || 0}} / ${{geometry.lane_count || 0}}`;
document.getElementById('geoCopy').textContent = `Families / lanes. Verdict: ${{geometry.verdict || 'NOT_RUN'}}.`;
document.getElementById('tradePosture').textContent = trading.stack_posture || 'NOT_RUN';
document.getElementById('tradeCopy').textContent = trading.live_policy || '';
document.getElementById('claimValue').textContent = `$${{Number(claimGate.allowed_estimated_hourly_value_usd || 0).toLocaleString(undefined, {{maximumFractionDigits: 0}})}}/hr`;
document.getElementById('claimCopy').textContent = `${{claimGate.allowed_estimated_value_claims || 0}} bounded estimated lanes; context-only value blocked until validation.`;
document.getElementById('boundaries').textContent = (payload.hard_boundaries || []).map(x => `- ${{x}}`).join('\\n');
document.getElementById('sources').textContent = JSON.stringify(payload.sources || {{}}, null, 2);
const fullBrief = [
  narration.mission,
  narration.truth,
  narration.geometry,
  narration.live_breadth,
  narration.dollar_claims,
  narration.kraken,
  narration.presentation
].filter(Boolean).join('\\n\\n');
document.getElementById('brief').value = fullBrief;
const voiceEl = document.getElementById('voice');
function voices() {{ return speechSynthesis.getVoices ? speechSynthesis.getVoices() : []; }}
function populateVoices() {{
  const list = voices();
  voiceEl.innerHTML = '<option value="">Default OS Voice</option>';
  list.forEach((voice, idx) => {{
    const opt = document.createElement('option');
    opt.value = String(idx);
    opt.textContent = `${{voice.name}} (${{voice.lang}})${{voice.default ? ' default' : ''}}`;
    voiceEl.appendChild(opt);
  }});
}}
function speak(text) {{
  if (!('speechSynthesis' in window)) return;
  speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  const list = voices();
  const selected = Number(voiceEl.value);
  if (!Number.isNaN(selected) && list[selected]) utter.voice = list[selected];
  utter.rate = Number(document.getElementById('rate').value || 0.95);
  utter.volume = Number(document.getElementById('volume').value || 1);
  speechSynthesis.speak(utter);
}}
document.getElementById('speakAll').onclick = () => speak(document.getElementById('brief').value);
document.getElementById('stop').onclick = () => speechSynthesis.cancel();
document.getElementById('copyBrief').onclick = () => navigator.clipboard?.writeText(document.getElementById('brief').value);
document.getElementById('copyPrompt').onclick = () => navigator.clipboard?.writeText(payload.legendary_goal_prompt || '');
document.querySelectorAll('[data-section]').forEach(btn => {{
  btn.addEventListener('click', () => speak(narration[btn.dataset.section] || fullBrief));
}});
populateVoices();
if ('speechSynthesis' in window) speechSynthesis.onvoiceschanged = populateVoices;
</script>
</body>
</html>
"""


def write_outputs(payload: dict[str, Any]) -> None:
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    payload["legendary_goal_prompt"] = LEGENDARY_GOAL_PROMPT
    VOICE_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    VOICE_HTML.write_text(render_html(payload), encoding="utf-8")
    GOAL_PROMPT_MD.write_text(render_goal_prompt().rstrip() + "\n", encoding="utf-8")


def main() -> int:
    payload = build_payload()
    write_outputs(payload)
    print(
        json.dumps(
            {
                "json": str(VOICE_JSON),
                "html": str(VOICE_HTML),
                "goal_prompt": str(GOAL_PROMPT_MD),
                "grant_posture": payload["grant_status"]["posture"],
                "trading_posture": payload["trading"]["stack_posture"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
