from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
MASTER_VAL_DIR = OUT_OPS / "master_valuation"
MASTER_VAL_LATEST = MASTER_VAL_DIR / "master_valuation_latest.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def money(value: Any) -> str:
    return f"${safe_float(value):,.2f}"


def build_scenarios(master_val: dict[str, Any]) -> dict[str, Any]:
    valuation = (master_val.get("valuation", {}) or {}) if isinstance(master_val, dict) else {}
    inputs = (master_val.get("inputs", {}) or {}) if isinstance(master_val, dict) else {}

    grant_license_value = safe_float(valuation.get("grant_finding_and_ranking_system_license_value_usd"), 0.0)
    digital_scout_value = safe_float(valuation.get("digital_scout_value_usd"), 0.0)
    trading_system_value = safe_float(valuation.get("institutional_trading_system_value_usd"), 0.0)
    autonomy_value = safe_float(valuation.get("validated_engine_autonomy_value_usd"), 0.0)
    pipeline_value = safe_float(valuation.get("grant_and_opportunity_pipeline_value_usd"), 0.0)

    licensing_anchor = max(
        1_000_000.0,
        grant_license_value + digital_scout_value + trading_system_value + autonomy_value,
    )

    scenarios = [
        {
            "id": "single_enterprise_license",
            "label": "Single Enterprise License",
            "target_clients": 1,
            "annual_rate_multiplier": 0.090,
            "onboarding_ratio": 0.25,
            "revenue_multiple_low": 4.5,
            "revenue_multiple_high": 6.0,
            "go_to_market": "direct",
            "notes": "One flagship client with full deployment and white-glove onboarding.",
        },
        {
            "id": "portfolio_5_client_expansion",
            "label": "Portfolio Expansion (5 Clients)",
            "target_clients": 5,
            "annual_rate_multiplier": 0.060,
            "onboarding_ratio": 0.20,
            "revenue_multiple_low": 5.0,
            "revenue_multiple_high": 6.8,
            "go_to_market": "direct_plus_partners",
            "notes": "Balanced enterprise rollout with repeatable onboarding playbook.",
        },
        {
            "id": "oem_white_label_channel",
            "label": "OEM / White-Label Channel",
            "target_clients": 12,
            "annual_rate_multiplier": 0.045,
            "onboarding_ratio": 0.15,
            "revenue_multiple_low": 5.8,
            "revenue_multiple_high": 7.2,
            "go_to_market": "oem_channel",
            "notes": "Platform licensing to channel partners with shared branding options.",
        },
        {
            "id": "public_sector_consortium",
            "label": "Public Sector + Infra Consortium",
            "target_clients": 20,
            "annual_rate_multiplier": 0.032,
            "onboarding_ratio": 0.12,
            "revenue_multiple_low": 5.2,
            "revenue_multiple_high": 6.5,
            "go_to_market": "public_sector",
            "notes": "Broader network licensing where reliability and auditability are central.",
        },
    ]

    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        clients = max(1, safe_int(scenario.get("target_clients"), 1))
        annual_rate = max(120_000.0, licensing_anchor * safe_float(scenario.get("annual_rate_multiplier"), 0.05))
        annual_per_client = round(annual_rate, 2)
        onboarding_per_client = round(max(60_000.0, annual_per_client * safe_float(scenario.get("onboarding_ratio"), 0.20)), 2)
        arr = round(annual_per_client * clients, 2)
        year1_total = round((annual_per_client + onboarding_per_client) * clients, 2)
        year3_total = round(year1_total + (arr * 2), 2)
        low_ev = round(arr * safe_float(scenario.get("revenue_multiple_low"), 4.0), 2)
        high_ev = round(arr * safe_float(scenario.get("revenue_multiple_high"), 6.0), 2)

        row = dict(scenario)
        row.update(
            {
                "annual_license_per_client_usd": annual_per_client,
                "onboarding_per_client_usd": onboarding_per_client,
                "arr_usd": arr,
                "year1_total_revenue_usd": year1_total,
                "year3_total_revenue_usd": year3_total,
                "implied_enterprise_value_low_usd": low_ev,
                "implied_enterprise_value_high_usd": high_ev,
            }
        )
        rows.append(row)

    ranked = sorted(rows, key=lambda r: (safe_float(r.get("year3_total_revenue_usd"), 0.0), safe_float(r.get("arr_usd"), 0.0)), reverse=True)
    best = ranked[0] if ranked else {}

    return {
        "generated_utc": now_iso(),
        "schema": "valuation_licensing_scenarios_v1",
        "source_master_valuation_generated_utc": str(master_val.get("generated_utc", "")),
        "licensing_anchor_usd": round(licensing_anchor, 2),
        "component_anchor_breakdown": {
            "grant_finding_and_ranking_system_license_value_usd": round(grant_license_value, 2),
            "digital_scout_value_usd": round(digital_scout_value, 2),
            "institutional_trading_system_value_usd": round(trading_system_value, 2),
            "validated_engine_autonomy_value_usd": round(autonomy_value, 2),
            "grant_and_opportunity_pipeline_value_usd": round(pipeline_value, 2),
        },
        "system_context": {
            "ranked_total_unique": safe_int(inputs.get("ranked_total_unique"), 0),
            "ranked_open_opportunities": safe_int(inputs.get("ranked_open_opportunities"), 0),
            "opportunity_package_count": safe_int(inputs.get("opportunity_package_count"), 0),
            "validated_system_count": safe_int(inputs.get("validated_system_count"), 0),
            "measured_sources": safe_int(inputs.get("measured_sources"), 0),
            "enabled_sources": safe_int(inputs.get("enabled_sources"), 0),
            "measured_coverage_pct": safe_float(inputs.get("measured_coverage_pct"), 0.0),
            "datasets_measured": safe_int(inputs.get("datasets_measured"), 0),
            "runtime_mode": str(inputs.get("runtime_mode", "unknown")),
        },
        "scenarios": ranked,
        "recommended_scenario_id": str(best.get("id", "")),
        "recommended_scenario_label": str(best.get("label", "")),
        "recommended_year1_revenue_usd": round(safe_float(best.get("year1_total_revenue_usd"), 0.0), 2),
        "recommended_arr_usd": round(safe_float(best.get("arr_usd"), 0.0), 2),
        "recommended_implied_ev_low_usd": round(safe_float(best.get("implied_enterprise_value_low_usd"), 0.0), 2),
        "recommended_implied_ev_high_usd": round(safe_float(best.get("implied_enterprise_value_high_usd"), 0.0), 2),
    }


def render_scenarios_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Valuation Licensing Scenarios")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Source valuation UTC: {payload.get('source_master_valuation_generated_utc', '')}")
    lines.append(f"Licensing anchor USD: {money(payload.get('licensing_anchor_usd'))}")
    lines.append("")

    lines.append("## Anchor Components")
    lines.append("")
    breakdown = payload.get("component_anchor_breakdown", {}) if isinstance(payload, dict) else {}
    for key, value in breakdown.items():
        lines.append(f"- {key}: {money(value)}")
    lines.append("")

    lines.append("## Scenarios")
    lines.append("")
    for row in payload.get("scenarios", []):
        if not isinstance(row, dict):
            continue
        lines.append(f"### {row.get('label', '')}")
        lines.append("")
        lines.append(f"- ID: {row.get('id', '')}")
        lines.append(f"- Target clients: {safe_int(row.get('target_clients'))}")
        lines.append(f"- Annual license per client: {money(row.get('annual_license_per_client_usd'))}")
        lines.append(f"- Onboarding per client: {money(row.get('onboarding_per_client_usd'))}")
        lines.append(f"- ARR: {money(row.get('arr_usd'))}")
        lines.append(f"- Year 1 total revenue: {money(row.get('year1_total_revenue_usd'))}")
        lines.append(f"- Year 3 total revenue: {money(row.get('year3_total_revenue_usd'))}")
        lines.append(
            f"- Implied EV range: {money(row.get('implied_enterprise_value_low_usd'))} to {money(row.get('implied_enterprise_value_high_usd'))}"
        )
        lines.append(f"- GTM: {row.get('go_to_market', '')}")
        lines.append(f"- Notes: {row.get('notes', '')}")
        lines.append("")

    lines.append("## Recommendation")
    lines.append("")
    lines.append(f"- Scenario: {payload.get('recommended_scenario_label', '')}")
    lines.append(f"- Recommended Year 1 revenue: {money(payload.get('recommended_year1_revenue_usd'))}")
    lines.append(f"- Recommended ARR: {money(payload.get('recommended_arr_usd'))}")
    lines.append(
        f"- Recommended EV range: {money(payload.get('recommended_implied_ev_low_usd'))} to {money(payload.get('recommended_implied_ev_high_usd'))}"
    )
    lines.append("")
    return "\n".join(lines)


def render_investor_brief(master_val: dict[str, Any], scenarios: dict[str, Any]) -> str:
    valuation = (master_val.get("valuation", {}) or {}) if isinstance(master_val, dict) else {}
    inputs = (master_val.get("inputs", {}) or {}) if isinstance(master_val, dict) else {}

    lines: list[str] = []
    lines.append("# Investor Valuation Brief")
    lines.append("")
    lines.append(f"Generated UTC: {now_iso()}")
    lines.append(f"Master valuation generated UTC: {master_val.get('generated_utc', '')}")
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append(f"- Master valuation proxy: {money(valuation.get('master_valuation_proxy_usd'))}")
    lines.append(f"- Valuation increment: {money(valuation.get('valuation_increment_usd'))}")
    lines.append("")

    lines.append("## System Value Breakdown")
    lines.append("")
    keys = [
        "autonomous_grant_execution_value_usd",
        "grant_and_opportunity_pipeline_value_usd",
        "grant_finding_and_ranking_system_license_value_usd",
        "digital_scout_value_usd",
        "institutional_trading_system_value_usd",
        "validated_engine_autonomy_value_usd",
        "institutional_signal_link_value_usd",
        "chain_of_custody_value_usd",
        "pass_momentum_value_usd",
    ]
    for key in keys:
        lines.append(f"- {key}: {money(valuation.get(key))}")
    lines.append("")

    lines.append("## Commercialization View")
    lines.append("")
    lines.append(f"- Licensing anchor: {money(scenarios.get('licensing_anchor_usd'))}")
    lines.append(f"- Recommended scenario: {scenarios.get('recommended_scenario_label', '')}")
    lines.append(f"- Recommended Year 1 revenue: {money(scenarios.get('recommended_year1_revenue_usd'))}")
    lines.append(f"- Recommended ARR: {money(scenarios.get('recommended_arr_usd'))}")
    lines.append(
        f"- Recommended EV range: {money(scenarios.get('recommended_implied_ev_low_usd'))} to {money(scenarios.get('recommended_implied_ev_high_usd'))}"
    )
    lines.append("")

    lines.append("## Operational Evidence")
    lines.append("")
    lines.append(f"- Ranked opportunities tracked: {safe_int(inputs.get('ranked_total_unique'))}")
    lines.append(f"- Open opportunities tracked: {safe_int(inputs.get('ranked_open_opportunities'))}")
    lines.append(f"- Opportunity package count: {safe_int(inputs.get('opportunity_package_count'))}")
    lines.append(f"- Validated systems counted: {safe_int(inputs.get('validated_system_count'))}")
    lines.append(
        f"- Live source coverage: {safe_int(inputs.get('measured_sources'))}/{safe_int(inputs.get('enabled_sources'))} ({safe_float(inputs.get('measured_coverage_pct')):.2f}%)"
    )
    lines.append(f"- Dataset breadth measured: {safe_int(inputs.get('datasets_measured'))} datasets")
    lines.append("")

    lines.append("## Positioning")
    lines.append("")
    lines.append(
        "- This valuation model separates pipeline outcome value from platform licensing value, so the grant/opportunity engine is valued as a standalone asset."
    )
    lines.append(
        "- Digital Scout, institutional trading intelligence, and validated autonomous operations are priced as independent modules that can be bundled or licensed separately."
    )
    lines.append(
        "- All values are assumption-based commercialization proxies and should be paired with legal/accounting diligence for formal financing use."
    )
    lines.append("")

    return "\n".join(lines)


def write_scenario_csv(path: Path, scenarios: dict[str, Any]) -> None:
    rows = scenarios.get("scenarios", []) if isinstance(scenarios, dict) else []
    if not isinstance(rows, list):
        rows = []

    headers = [
        "id",
        "label",
        "target_clients",
        "annual_license_per_client_usd",
        "onboarding_per_client_usd",
        "arr_usd",
        "year1_total_revenue_usd",
        "year3_total_revenue_usd",
        "implied_enterprise_value_low_usd",
        "implied_enterprise_value_high_usd",
        "go_to_market",
        "notes",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            if not isinstance(row, dict):
                continue
            writer.writerow({k: row.get(k) for k in headers})


def main() -> int:
    master_val = load_json(MASTER_VAL_LATEST)
    if not isinstance(master_val, dict):
        raise SystemExit(f"Missing or invalid master valuation payload: {MASTER_VAL_LATEST}")

    scenarios = build_scenarios(master_val)
    brief_markdown = render_investor_brief(master_val, scenarios)

    tag = utc_tag()
    scenario_json = MASTER_VAL_DIR / f"valuation_licensing_scenarios_{tag}.json"
    scenario_md = MASTER_VAL_DIR / f"valuation_licensing_scenarios_{tag}.md"
    scenario_csv = MASTER_VAL_DIR / f"valuation_licensing_scenarios_{tag}.csv"
    scenario_json_latest = MASTER_VAL_DIR / "valuation_licensing_scenarios_latest.json"
    scenario_md_latest = MASTER_VAL_DIR / "valuation_licensing_scenarios_latest.md"
    scenario_csv_latest = MASTER_VAL_DIR / "valuation_licensing_scenarios_latest.csv"

    brief_md = MASTER_VAL_DIR / f"investor_valuation_brief_{tag}.md"
    brief_json = MASTER_VAL_DIR / f"investor_valuation_brief_{tag}.json"
    brief_md_latest = MASTER_VAL_DIR / "investor_valuation_brief_latest.md"
    brief_json_latest = MASTER_VAL_DIR / "investor_valuation_brief_latest.json"

    write_json(scenario_json, scenarios)
    write_text(scenario_md, render_scenarios_markdown(scenarios))
    write_scenario_csv(scenario_csv, scenarios)
    write_json(scenario_json_latest, scenarios)
    write_text(scenario_md_latest, render_scenarios_markdown(scenarios))
    write_scenario_csv(scenario_csv_latest, scenarios)

    brief_payload = {
        "generated_utc": now_iso(),
        "schema": "investor_valuation_brief_v1",
        "source_master_valuation_generated_utc": str(master_val.get("generated_utc", "")),
        "source_scenarios_generated_utc": str(scenarios.get("generated_utc", "")),
        "master_valuation_proxy_usd": safe_float((master_val.get("valuation", {}) or {}).get("master_valuation_proxy_usd"), 0.0),
        "valuation_increment_usd": safe_float((master_val.get("valuation", {}) or {}).get("valuation_increment_usd"), 0.0),
        "recommended_scenario_id": str(scenarios.get("recommended_scenario_id", "")),
        "recommended_scenario_label": str(scenarios.get("recommended_scenario_label", "")),
        "recommended_year1_revenue_usd": safe_float(scenarios.get("recommended_year1_revenue_usd"), 0.0),
        "recommended_arr_usd": safe_float(scenarios.get("recommended_arr_usd"), 0.0),
        "recommended_implied_ev_low_usd": safe_float(scenarios.get("recommended_implied_ev_low_usd"), 0.0),
        "recommended_implied_ev_high_usd": safe_float(scenarios.get("recommended_implied_ev_high_usd"), 0.0),
        "paths": {
            "scenarios_json_latest": str(scenario_json_latest),
            "scenarios_md_latest": str(scenario_md_latest),
            "scenarios_csv_latest": str(scenario_csv_latest),
            "brief_md_latest": str(brief_md_latest),
        },
    }

    write_text(brief_md, brief_markdown)
    write_json(brief_json, brief_payload)
    write_text(brief_md_latest, brief_markdown)
    write_json(brief_json_latest, brief_payload)

    print(f"LICENSING_SCENARIOS_JSON={scenario_json_latest}")
    print(f"LICENSING_SCENARIOS_MD={scenario_md_latest}")
    print(f"LICENSING_SCENARIOS_CSV={scenario_csv_latest}")
    print(f"INVESTOR_VALUATION_BRIEF_MD={brief_md_latest}")
    print(f"INVESTOR_VALUATION_BRIEF_JSON={brief_json_latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
