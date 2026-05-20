from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def first_leader_row(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if isinstance(row, dict):
                    return dict(row)
    except Exception:
        return {}

    return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip("\r\n") + "\n", encoding="utf-8")


def as_money(value: float) -> str:
    return f"${value:,.2f}"


def resolve_logo_assets(stack_root: Path) -> dict[str, str]:
    logo_dir = stack_root / "out" / "ops" / "linkedin_oauth_setup"
    if not logo_dir.exists():
        return {}

    preferred = {
        "logo_512": logo_dir / "luma_logo_fintech_cursive_512.png",
        "logo_1024": logo_dir / "luma_logo_fintech_cursive_1024.png",
        "logo_2048": logo_dir / "luma_logo_fintech_cursive_2048.png",
        "logo_upload_ready_5mb": logo_dir / "luma_logo_fintech_cursive_5mb.png",
        "logo_alias_512": logo_dir / "luma_linkedin_logo_512.png",
        "logo_alias_5mb": logo_dir / "luma_linkedin_logo_5mb.png",
    }

    found: dict[str, str] = {}
    for key, path in preferred.items():
        if path.exists():
            found[key] = str(path)
    return found


def build_payload(stack_root: Path) -> dict[str, Any]:
    investor_path = stack_root / "out" / "ops" / "investor_metric_readiness_latest.json"
    panel_path = stack_root / "out" / "ops" / "live_breadth_value_panel_latest.json"
    sector_path = stack_root / "out" / "sector_energy" / "sector_energy_investor_bridge_latest.json"
    vps_path = stack_root / "out" / "execution" / "vps_growth_proof.json"
    runtime_path = stack_root / "config" / "runtime_control.json"
    leaderboard_path = stack_root / "out" / "execution" / "institutional_leaderboard.csv"

    investor = load_json(investor_path)
    panel = load_json(panel_path)
    sector = load_json(sector_path)
    vps = load_json(vps_path)
    runtime = load_json(runtime_path)
    leader = first_leader_row(leaderboard_path)
    logo_assets = resolve_logo_assets(stack_root)

    investor_summary = investor.get("summary", {}) if isinstance(investor, dict) else {}
    signal = investor_summary.get("signal_evidence", {}) if isinstance(investor_summary, dict) else {}
    gates = investor_summary.get("capital_and_risk_gate_evidence", {}) if isinstance(investor_summary, dict) else {}
    provisional = investor_summary.get("provisional_live_metrics", {}) if isinstance(investor_summary, dict) else {}

    headline = panel.get("headline", {}) if isinstance(panel, dict) else {}
    top_sectors = panel.get("top_sectors", []) if isinstance(panel, dict) else []
    if not isinstance(top_sectors, list):
        top_sectors = []

    vps_perf = vps.get("live_trade_performance", {}) if isinstance(vps, dict) else {}
    if not isinstance(vps_perf, dict):
        vps_perf = {}

    annual_value = to_float(signal.get("annual_value_usd"), to_float(headline.get("total_estimated_annual_value_usd")))
    top_sector = str(signal.get("top_sector") or headline.get("top_sector") or "financial_market_infra")
    top_sector_hour = to_float(signal.get("top_sector_hourly_value_usd"), to_float(headline.get("top_sector_hourly_value_usd")))
    router_edge = to_float(signal.get("router_edge_pct"), to_float(headline.get("router_edge_pct")))
    kalisha = to_float(signal.get("kalisha_prediction_score"), to_float(headline.get("kalisha_prediction_score")))
    harmonic_win = to_float(signal.get("harmonic_win_rate_pct"), to_float(headline.get("harmonic_win_rate_pct")))
    avoided_cost = to_float(headline.get("cross_sector_recommended_avoided_cost_usd"), 0.0)

    leader_flow = str(leader.get("flow") or "geom_gaussian")
    leader_strategy = str(leader.get("strategy") or "regime_switch")
    leader_algo = str(leader.get("algo") or "confidence_weighted")
    leader_sharpe = to_float(leader.get("test_sharpe"), 0.0)
    leader_score = to_float(leader.get("institutional_score"), 0.0)

    use_of_funds = {
        "grant_1000": {
            "compute_and_data_refresh_usd": 350,
            "grant_application_ops_usd": 250,
            "dashboard_and_evidence_packaging_usd": 250,
            "operator_time_usd": 150,
        },
        "grant_10000": {
            "compute_and_data_refresh_usd": 3000,
            "execution_and_risk_instrumentation_usd": 2400,
            "federal_grade_evidence_and_reporting_usd": 2200,
            "go_to_market_and_customer_validation_usd": 1700,
            "legal_and_compliance_support_usd": 700,
        },
        "grant_25000": {
            "compute_and_data_refresh_usd": 7000,
            "execution_and_risk_instrumentation_usd": 6200,
            "federal_grade_evidence_and_reporting_usd": 5400,
            "go_to_market_and_customer_validation_usd": 4400,
            "legal_and_compliance_support_usd": 2000,
        },
    }

    autofill_fields = {
        "business_name": "LumaTrader / LumenCore",
        "founder_name": "Robert Ashworth",
        "business_stage": "operational and revenue-readiness",
        "business_location": "United States",
        "industry": "AI + quant infrastructure + operational intelligence",
        "website": "https://lumen-core.ai",
        "one_line_pitch": (
            "LumaTrader turns live multi-sector data into auditable, risk-gated execution decisions that reduce operational loss and accelerate small-business growth."
        ),
        "problem_statement": (
            "Small teams lose money from delayed decisions, fragmented signals, and poor execution guardrails across finance, energy, and operations."
        ),
        "solution_statement": (
            "Our harmonic flowform engine converts live signals into ranked actions with proof-grade evidence, making funding and operations decisions faster and safer."
        ),
        "traction_metrics": {
            "annual_value_signal_usd": annual_value,
            "top_sector": top_sector,
            "top_sector_hourly_value_usd": top_sector_hour,
            "cross_sector_avoided_cost_usd": avoided_cost,
            "router_edge_pct": router_edge,
            "harmonic_win_rate_pct": harmonic_win,
            "kalisha_prediction_score": kalisha,
            "top_model": {
                "flow": leader_flow,
                "strategy": leader_strategy,
                "algo": leader_algo,
                "test_sharpe": leader_sharpe,
                "institutional_score": leader_score,
            },
        },
        "why_now": (
            "We have validated signal-value capture, but risk-adjusted financial metrics are still intentionally constrained by micro-capital safety gates."
        ),
        "funding_need": (
            "Grant capital is used to move from constrained proof mode into funded scaling mode, increasing execution depth and publishing stable risk-adjusted performance metrics."
        ),
        "use_of_funds_short": (
            "Data/compute expansion, execution guardrail hardening, evidence-pack automation, and customer-validation pilots."
        ),
        "90_day_outcomes": [
            "Increase closed-trade sample depth and publish stable Sharpe/MDD/CAGR confidence bands",
            "Expand measured sector evidence and maintain lane-boundary compliance",
            "Ship repeatable investor and grant evidence packs with hash-linked artifacts",
        ],
    }

    narrative_short = (
        "LumaTrader is an AI-powered execution and operations platform that converts live signals into auditable actions. "
        f"Current modeled annual value signal is {as_money(annual_value)} with top impact in {top_sector}. "
        "Grant funding lets us scale from guarded micro-cap proof mode into measurable growth mode."
    )

    narrative_long = (
        "We built LumaTrader/LumenCore to reduce avoidable operational and execution loss using real-time signal fusion, "
        "strict risk controls, and proof-grade reporting. The system currently indicates large preserved-value potential while "
        "remaining in deliberate safety mode with constrained capital. This is exactly where grant capital creates leverage: "
        "it unlocks deeper run-time coverage, stronger market validation, and statistically stable performance reporting. "
        "We will use funding to harden execution infrastructure, expand measured evidence lanes, and accelerate customer-facing outcomes."
    )

    opportunities = [
        {
            "opportunity_id": "skip_instant_1k",
            "title": "Skip $1k Instant Grants",
            "deadline_note": "Rolling live windows; listed due example: May 19, 2026",
            "fit": "high",
            "eligibility_required_tags": ["US-based", "18+", "watch-live requirement may apply"],
            "autofill_angle": "quick traction + immediate micro-experiment milestones",
            "recommended_budget_template": "grant_1000",
            "paste_ready_answer": (
                "We will use this micro-grant to accelerate one sprint of measurable execution improvements: data refresh coverage, "
                "grant-ops automation, and evidence dashboard updates. In 30 days we will ship a reproducible proof packet with "
                "updated metrics and operator-ready documentation."
            ),
        },
        {
            "opportunity_id": "skip_10k_growth",
            "title": "Skip $10k Growth Grants",
            "deadline_note": "Recent listing example: May 16, 2026",
            "fit": "very_high",
            "eligibility_required_tags": ["US-based entrepreneur"],
            "autofill_angle": "transition from guarded proof mode to funded growth mode",
            "recommended_budget_template": "grant_10000",
            "paste_ready_answer": (
                "A $10k grant bridges the exact gap between validated signal quality and scaled execution depth. "
                "We will allocate capital across compute/data, risk-instrumentation, evidence automation, and pilot execution to "
                "publish stable performance metrics while maintaining strict safety controls."
            ),
        },
        {
            "opportunity_id": "skip_10k_ai_builder",
            "title": "Skip $10k AI Builder Grant",
            "deadline_note": "Recent listing example: May 19, 2026",
            "fit": "very_high",
            "eligibility_required_tags": ["AI product builder"],
            "autofill_angle": "AI infrastructure hardening and deployment readiness",
            "recommended_budget_template": "grant_10000",
            "paste_ready_answer": (
                "This grant funds AI product hardening: improving model routing reliability, expanding live evidence capture, "
                "and shipping production-grade operator workflows. The result is faster customer deployment with transparent proof of impact."
            ),
        },
        {
            "opportunity_id": "dream_makers_25k",
            "title": "Dream Makers Founder Grant ($25k)",
            "deadline_note": "Recent listing example: May 30, 2026",
            "fit": "conditional",
            "eligibility_required_tags": ["female founder requirement"],
            "autofill_angle": "apply only if eligibility is met",
            "recommended_budget_template": "grant_25000",
            "paste_ready_answer": (
                "If eligibility is met, this larger grant enables full-cycle scale-up: infrastructure, validation, and go-to-market execution "
                "while preserving a strict risk and evidence discipline."
            ),
        },
    ]

    payload = {
        "generated_utc": now_iso(),
        "scope": "skips_grant_autofill_pack",
        "program": "Hello Skip grants and partner opportunities",
        "source_artifacts": {
            "investor_metric_readiness_latest_json": str(investor_path),
            "live_breadth_value_panel_latest_json": str(panel_path),
            "sector_energy_investor_bridge_latest_json": str(sector_path),
            "vps_growth_proof_json": str(vps_path),
            "runtime_control_json": str(runtime_path),
            "institutional_leaderboard_csv": str(leaderboard_path),
        },
        "business_profile": {
            "name": "LumaTrader / LumenCore",
            "founder": "Robert Ashworth",
            "website": "https://lumen-core.ai",
            "location": "United States",
            "stage": "operational, grant-funded scale transition",
            "short_narrative": narrative_short,
            "long_narrative": narrative_long,
            "logo_assets": logo_assets,
        },
        "evidence_snapshot": {
            "annual_value_signal_usd": annual_value,
            "top_sector": top_sector,
            "top_sector_hourly_value_usd": top_sector_hour,
            "router_edge_pct": router_edge,
            "harmonic_win_rate_pct": harmonic_win,
            "kalisha_prediction_score": kalisha,
            "cross_sector_avoided_cost_usd": avoided_cost,
            "runtime_mode": str(gates.get("runtime_mode") or runtime.get("mode") or "paper"),
            "allow_live_orders": bool(gates.get("allow_live_orders", runtime.get("allow_live_orders", False))),
            "hard_safety_only_mode": bool(gates.get("hard_safety_only_mode", runtime.get("hard_safety_only_mode", False))),
            "max_notional_per_trade_usd": to_float(gates.get("max_notional_per_trade_usd"), to_float(runtime.get("max_notional_per_trade_usd"))),
            "max_daily_loss_usd": to_float(gates.get("max_daily_loss_usd"), to_float(runtime.get("max_daily_loss_usd"))),
            "closed_live_trades": to_float(provisional.get("closed_live_trades"), to_float(vps_perf.get("closed_live_count"))),
            "win_rate_pct": to_float(provisional.get("win_rate_pct"), to_float(vps_perf.get("win_rate_pct"))),
            "realized_net_usd": to_float(provisional.get("realized_net_usd"), to_float(vps_perf.get("realized_net_usd"))),
            "sector_energy_pipeline_status": str(sector.get("status") or "unknown"),
        },
        "autofill_fields": autofill_fields,
        "use_of_funds_templates": use_of_funds,
        "opportunity_variants": opportunities,
        "submission_checklist": [
            "Confirm opportunity-specific eligibility tags before submit",
            "Use the matching recommended_budget_template for that opportunity",
            "Keep core narrative consistent, only swap opportunity angle paragraph",
            "Submit before deadline and archive confirmation in evidence folder",
        ],
    }

    if top_sectors:
        payload["top_sector_table"] = top_sectors[:8]

    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    profile = payload.get("business_profile", {}) if isinstance(payload, dict) else {}
    if not isinstance(profile, dict):
        profile = {}

    evidence = payload.get("evidence_snapshot", {}) if isinstance(payload, dict) else {}
    if not isinstance(evidence, dict):
        evidence = {}

    autofill = payload.get("autofill_fields", {}) if isinstance(payload, dict) else {}
    if not isinstance(autofill, dict):
        autofill = {}

    opportunities = payload.get("opportunity_variants", []) if isinstance(payload, dict) else []
    if not isinstance(opportunities, list):
        opportunities = []

    lines: list[str] = []
    lines.append("# SKIPS Grant Autofill Pack")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Program: {payload.get('program', '')}")
    lines.append("")

    lines.append("## Core Identity")
    lines.append("")
    lines.append(f"- Business: {profile.get('name', '')}")
    lines.append(f"- Founder: {profile.get('founder', '')}")
    lines.append(f"- Website: {profile.get('website', '')}")
    lines.append(f"- Stage: {profile.get('stage', '')}")
    lines.append("")

    logo_assets = profile.get("logo_assets", {}) if isinstance(profile, dict) else {}
    if isinstance(logo_assets, dict) and logo_assets:
        lines.append("## Logo Assets")
        lines.append("")
        for key, value in logo_assets.items():
            lines.append(f"- {key}: {value}")
        lines.append("")

    lines.append("## Copy-Paste Short Pitch")
    lines.append("")
    lines.append(str(autofill.get("one_line_pitch", "")))
    lines.append("")

    lines.append("## Copy-Paste Problem")
    lines.append("")
    lines.append(str(autofill.get("problem_statement", "")))
    lines.append("")

    lines.append("## Copy-Paste Solution")
    lines.append("")
    lines.append(str(autofill.get("solution_statement", "")))
    lines.append("")

    lines.append("## Evidence Highlights")
    lines.append("")
    lines.append(f"- Annual value signal: {as_money(to_float(evidence.get('annual_value_signal_usd')))}")
    lines.append(f"- Top sector: {evidence.get('top_sector', '')}")
    lines.append(f"- Top sector hourly value: {as_money(to_float(evidence.get('top_sector_hourly_value_usd')))}")
    lines.append(f"- Router edge: {to_float(evidence.get('router_edge_pct')):.2f}%")
    lines.append(f"- Harmonic win rate: {to_float(evidence.get('harmonic_win_rate_pct')):.2f}%")
    lines.append(f"- Kalisha score: {to_float(evidence.get('kalisha_prediction_score')):.2f}")
    lines.append(f"- Avoided cost estimate: {as_money(to_float(evidence.get('cross_sector_avoided_cost_usd')))}")
    lines.append("")

    lines.append("## Opportunity Variants")
    lines.append("")
    for item in opportunities:
        if not isinstance(item, dict):
            continue
        lines.append(f"### {item.get('title', '')}")
        lines.append(f"- Opportunity ID: {item.get('opportunity_id', '')}")
        lines.append(f"- Deadline: {item.get('deadline_note', '')}")
        lines.append(f"- Fit: {item.get('fit', '')}")
        tags = item.get("eligibility_required_tags", [])
        if isinstance(tags, list) and tags:
            lines.append(f"- Eligibility tags: {', '.join(str(t) for t in tags)}")
        lines.append(f"- Budget template: {item.get('recommended_budget_template', '')}")
        lines.append("")
        lines.append(str(item.get("paste_ready_answer", "")))
        lines.append("")

    lines.append("## Generic Use of Funds (Short)")
    lines.append("")
    lines.append(str(autofill.get("use_of_funds_short", "")))
    lines.append("")

    outcomes = autofill.get("90_day_outcomes", [])
    if isinstance(outcomes, list) and outcomes:
        lines.append("## 90-Day Outcomes")
        lines.append("")
        for idx, outcome in enumerate(outcomes, start=1):
            lines.append(f"{idx}. {outcome}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SKIPS grant autofill pack from latest stack evidence.")
    parser.add_argument(
        "--stack-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Path to INSTITUTIONAL_STACK_V2 root",
    )
    args = parser.parse_args()

    stack_root = Path(args.stack_root).resolve()
    out_dir = stack_root / "out" / "ops" / "skips_grant_autofill"
    tag = now_tag()

    payload = build_payload(stack_root)
    markdown = render_markdown(payload)

    tagged_json = out_dir / f"skips_grant_autofill_{tag}.json"
    tagged_md = out_dir / f"skips_grant_autofill_{tag}.md"
    latest_json = out_dir / "skips_grant_autofill_latest.json"
    latest_md = out_dir / "skips_grant_autofill_latest.md"
    manifest = out_dir / f"skips_grant_autofill_manifest_{tag}.json"

    write_json(tagged_json, payload)
    write_text(tagged_md, markdown)
    write_json(latest_json, payload)
    write_text(latest_md, markdown)

    manifest_payload = {
        "generated_utc": payload.get("generated_utc"),
        "scope": payload.get("scope"),
        "artifacts": {
            "tagged_json": str(tagged_json),
            "tagged_md": str(tagged_md),
            "latest_json": str(latest_json),
            "latest_md": str(latest_md),
        },
    }
    write_json(manifest, manifest_payload)

    print(json.dumps({**manifest_payload, "manifest": str(manifest)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
