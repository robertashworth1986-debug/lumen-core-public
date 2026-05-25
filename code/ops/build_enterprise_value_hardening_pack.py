from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = ROOT.parent
OUT_DIR = ROOT / "out" / "ops" / "enterprise_value_hardening"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def parse_iso(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def age_seconds_from_iso(value: Any) -> float | None:
    dt = parse_iso(value)
    if dt is None:
        return None
    return max((datetime.now(timezone.utc) - dt).total_seconds(), 0.0)


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


@dataclass
class Paths:
    live_breadth: Path
    readiness: Path
    grant_fit: Path
    site_reach: Path
    pilots: Path
    key_audit: Path
    vps_controller: Path
    live_executor_hb: Path
    approval_hb: Path
    execution_status: Path
    investor_packet_latest: Path


def locate_paths() -> Paths:
    return Paths(
        live_breadth=ROOT / "out" / "ops" / "live_breadth_value_panel_latest.json",
        readiness=ROOT / "out" / "ops" / "investor_metric_readiness_latest.json",
        grant_fit=ROOT / "out" / "ops" / "grant_submit_fit_pack" / "grant_submit_fit_pack_latest.json",
        site_reach=ROOT / "out" / "ops" / "site_reach_mission" / "site_reach_mission_latest.json",
        pilots=ROOT / "out" / "ops" / "pilot_site_opportunity_pack_latest.json",
        key_audit=ROOT / "out" / "ops" / "live_key_measurement_audit_latest.json",
        vps_controller=ROOT / "out" / "execution" / "vps_growth_controller_status.json",
        live_executor_hb=ROOT / "out" / "execution" / "live_executor_heartbeat.json",
        approval_hb=ROOT / "out" / "execution" / "approval_autofire_heartbeat.json",
        execution_status=ROOT / "out" / "execution_status.json",
        investor_packet_latest=ROOT / "out" / "ops" / "investor_packet_refresh_latest.json",
    )


def locate_latest_proof_summary() -> Path | None:
    ops_root = WORKSPACE_ROOT / "out" / "ops"
    if not ops_root.exists():
        return None

    candidates = list(ops_root.glob("investor_proof_sweep_*/proof_summary.json"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def top_sector_rows(panel_payload: dict[str, Any], top_n: int = 8) -> list[dict[str, Any]]:
    top_sectors = panel_payload.get("top_sectors", []) if isinstance(panel_payload, dict) else []
    rows: list[dict[str, Any]] = []

    if isinstance(top_sectors, list) and top_sectors:
        for row in top_sectors[:top_n]:
            if not isinstance(row, dict):
                continue
            rows.append(
                {
                    "sector": str(row.get("sector", "")),
                    "hourly_value_usd": to_float(row.get("total_estimated_hourly_value_usd", 0.0)),
                    "annual_value_usd": to_float(row.get("total_estimated_annual_value_usd", 0.0)),
                    "coverage_pct": to_float(row.get("measured_coverage_pct", 0.0)),
                }
            )
        return rows

    headline = panel_payload.get("headline", {}) if isinstance(panel_payload, dict) else {}
    return [
        {
            "sector": str(headline.get("top_sector", "unknown")),
            "hourly_value_usd": to_float(headline.get("top_sector_hourly_value_usd", 0.0)),
            "annual_value_usd": to_float(headline.get("total_estimated_annual_value_usd", 0.0)),
            "coverage_pct": to_float(headline.get("measured_coverage_pct", 0.0)),
        }
    ]


def build_test_innovation_methods() -> list[dict[str, Any]]:
    return [
        {
            "name": "Regime-Split Walkforward",
            "priority": "P0",
            "value_driver": "Proves strategy robustness across macro regimes and reduces model-risk discounts in enterprise due diligence.",
            "execution": "pwsh -NoProfile -ExecutionPolicy Bypass -File INSTITUTIONAL_STACK_V2/code/ops/RUN_INVESTOR_PROOF_SWEEP.ps1",
            "success_signal": "positive_sharpe_count stable and long_horizon_series_count_20y non-decreasing across refreshes",
        },
        {
            "name": "Outage Value Counterfactual Replay",
            "priority": "P0",
            "value_driver": "Converts outage data into avoided-loss counterfactuals that buyers can map to EBITDA and SLA impact.",
            "execution": "pwsh -NoProfile -ExecutionPolicy Bypass -File INSTITUTIONAL_STACK_V2/code/ops/RUN_SECTOR_ENERGY_EVIDENCE_PIPELINE.ps1",
            "success_signal": "site-level hourly and annual preserved-value tracks remain consistent with measured source coverage",
        },
        {
            "name": "Execution Quality Stress Replay",
            "priority": "P1",
            "value_driver": "Demonstrates stability under spread/fee shock conditions for trading and market-infra buyers.",
            "execution": "python INSTITUTIONAL_STACK_V2/code/execution/kraken_live_growth_controller.py --cached --controller Robert",
            "success_signal": "controller maintains guarded mode with bounded pending queue and no fatal heartbeat statuses",
        },
        {
            "name": "Cross-Source Consistency Validation",
            "priority": "P1",
            "value_driver": "Improves trust by proving independent feeds converge on similar anomaly and risk signals.",
            "execution": "pwsh -NoProfile -ExecutionPolicy Bypass -File INSTITUTIONAL_STACK_V2/code/ops/RUN_LIVE_KEY_MEASUREMENT_AUDIT.ps1",
            "success_signal": "runtime_bound_keys_total > 0, unbound_keys_total = 0, measured_coverage_pct near 100",
        },
        {
            "name": "Commercial Pilot Conversion Tests",
            "priority": "P2",
            "value_driver": "Raises close-rate by testing outreach templates and sector-specific ROI narratives.",
            "execution": "Use out/ops/outreach_execution_bundle/outreach_execution_bundle_latest.json drafts with tracked response cohorts",
            "success_signal": "increasing reply-rate and pilot kickoff ratio by sector and message variant",
        },
    ]


def build_backlog(
    *,
    proof_payload: dict[str, Any],
    site_reach_payload: dict[str, Any],
    readiness_payload: dict[str, Any],
    key_audit_payload: dict[str, Any],
    controller_payload: dict[str, Any],
    execution_status_age_sec: float | None,
) -> list[dict[str, Any]]:
    backlog: list[dict[str, Any]] = []

    node_red = proof_payload.get("node_red_unity", {}) if isinstance(proof_payload, dict) else {}
    if str(node_red.get("ingest", "")).lower() == "failed":
        backlog.append(
            {
                "priority": "P0",
                "title": "Restore Node-RED Proof Ingestion",
                "impact": "Re-enables real-time external proof routing for enterprise demo workflows.",
                "owner_lane": "runtime_ops",
                "evidence": str(node_red.get("ingest_detail", ""))[:220],
            }
        )

    site_summary = site_reach_payload.get("summary", {}) if isinstance(site_reach_payload, dict) else {}
    if to_int(site_summary.get("providers_reporting", 0)) == 0:
        backlog.append(
            {
                "priority": "P0",
                "title": "Enable At Least One Analytics Provider",
                "impact": "Unblocks provable traffic/reach metrics required by enterprise and investor procurement checks.",
                "owner_lane": "growth_ops",
                "evidence": "site_reach_mission providers_reporting=0",
            }
        )

    readiness_summary = readiness_payload.get("summary", {}) if isinstance(readiness_payload, dict) else {}
    readiness_status = str(readiness_summary.get("status", ""))
    if "limited_live" in readiness_status:
        backlog.append(
            {
                "priority": "P0",
                "title": "Graduate From Limited Live Safety Mode",
                "impact": "Unlocks full institutional metrics (Sharpe/CAGR/Sortino) and improves valuation confidence.",
                "owner_lane": "execution_quant",
                "evidence": readiness_status,
            }
        )

    if execution_status_age_sec is not None and execution_status_age_sec > 3600:
        backlog.append(
            {
                "priority": "P1",
                "title": "Refresh execution_status.json on cadence",
                "impact": "Removes stale-state ambiguity across downstream dashboards and automation lanes.",
                "owner_lane": "platform_reliability",
                "evidence": f"execution_status_age_sec={round(execution_status_age_sec, 1)}",
            }
        )

    key_summary = key_audit_payload.get("summary", {}) if isinstance(key_audit_payload, dict) else {}
    if to_int(key_summary.get("unbound_keys_total", 0)) > 0:
        backlog.append(
            {
                "priority": "P1",
                "title": "Clear remaining unbound env keys",
                "impact": "Improves source reliability confidence and reduces silent data outages.",
                "owner_lane": "data_platform",
                "evidence": f"unbound_keys_total={to_int(key_summary.get('unbound_keys_total', 0))}",
            }
        )

    mode = str(controller_payload.get("mode", ""))
    if mode == "SAFE_DRY_RUN":
        backlog.append(
            {
                "priority": "P2",
                "title": "Define SAFE_DRY_RUN to guarded-live promotion gate",
                "impact": "Creates explicit commercialization milestone from proof mode to production buyer mode.",
                "owner_lane": "trading_ops",
                "evidence": "vps_growth_controller_status.mode=SAFE_DRY_RUN",
            }
        )

    return backlog


def render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Enterprise Value Hardening Pack")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append("")

    snapshot = payload.get("snapshot", {})
    lines.append("## Snapshot")
    lines.append(f"- Annual value signal USD: {to_float(snapshot.get('annual_value_signal_usd', 0.0)):.2f}")
    lines.append(f"- Runtime readiness: {snapshot.get('runtime_readiness_status', '')}")
    lines.append(f"- Live executor heartbeat fresh: {snapshot.get('live_executor_heartbeat_fresh', False)}")
    lines.append(f"- Approval heartbeat fresh: {snapshot.get('approval_heartbeat_fresh', False)}")
    lines.append("")

    lines.append("## Commercial Sector Priorities")
    lines.append("| Sector | Hourly Value USD | Annual Value USD | Coverage % |")
    lines.append("|---|---:|---:|---:|")
    for row in payload.get("commercial_sector_priorities", []):
        lines.append(
            f"| {row.get('sector','')} | {to_float(row.get('hourly_value_usd', 0.0)):.2f} | {to_float(row.get('annual_value_usd', 0.0)):.2f} | {to_float(row.get('coverage_pct', 0.0)):.2f} |"
        )
    lines.append("")

    lines.append("## Grant Priorities")
    for row in payload.get("grant_priorities", []):
        lines.append(
            f"- [{row.get('opp_num','')}] {row.get('title','')} | fit={row.get('fit_status','')} | days_to_close={to_int(row.get('days_to_close', 0))}"
        )
    lines.append("")

    lines.append("## Pilot Site Priorities")
    for row in payload.get("pilot_site_priorities", []):
        lines.append(
            f"- #{to_int(row.get('rank', 0))} {row.get('site','')} | outage_mw={to_float(row.get('outage_mw', 0.0)):.2f} | est_annual_usd={to_float(row.get('estimated_annual_value_usd', 0.0)):.2f}"
        )
    lines.append("")

    lines.append("## P0/P1/P2 Backlog")
    for row in payload.get("prioritized_backlog", []):
        lines.append(
            f"- {row.get('priority','P2')} | {row.get('title','')} | owner={row.get('owner_lane','')} | impact={row.get('impact','')}"
        )
    lines.append("")

    lines.append("## New Test Methods")
    for row in payload.get("test_innovation_methods", []):
        lines.append(
            f"- {row.get('priority','P2')} | {row.get('name','')} | success_signal={row.get('success_signal','')}"
        )
        lines.append(f"  execution: {row.get('execution','')}")
    lines.append("")

    lines.append("## Evidence Paths")
    evidence_paths = payload.get("evidence_paths", {}) if isinstance(payload.get("evidence_paths"), dict) else {}
    for key, value in evidence_paths.items():
        lines.append(f"- {key}: {value}")

    return "\n".join(lines)


def main() -> int:
    paths = locate_paths()

    panel = load_json(paths.live_breadth, {})
    readiness = load_json(paths.readiness, {})
    grants = load_json(paths.grant_fit, {})
    site_reach = load_json(paths.site_reach, {})
    pilots = load_json(paths.pilots, {})
    key_audit = load_json(paths.key_audit, {})
    controller = load_json(paths.vps_controller, {})
    live_hb = load_json(paths.live_executor_hb, {})
    approval_hb = load_json(paths.approval_hb, {})
    execution_status = load_json(paths.execution_status, {})
    packet_latest = load_json(paths.investor_packet_latest, {})

    proof_summary_path = locate_latest_proof_summary()
    proof_summary = load_json(proof_summary_path, {}) if proof_summary_path else {}

    live_hb_age = age_seconds_from_iso(live_hb.get("timestamp_utc"))
    approval_hb_age = age_seconds_from_iso(approval_hb.get("generated_utc"))
    execution_status_age = age_seconds_from_iso(execution_status.get("generated_utc"))

    grant_rows = grants.get("opportunities", []) if isinstance(grants, dict) else []
    if not isinstance(grant_rows, list):
        grant_rows = []
    grant_rows = sorted(
        [r for r in grant_rows if isinstance(r, dict)],
        key=lambda r: (
            0 if str(r.get("fit_status", "")).upper() == "FIT_LIKELY" else 1,
            to_int(r.get("days_to_close", 9999)),
        ),
    )[:8]

    pilot_rows = pilots.get("top_targets", []) if isinstance(pilots, dict) else []
    if not isinstance(pilot_rows, list):
        pilot_rows = []
    pilot_rows = [r for r in pilot_rows if isinstance(r, dict)][:10]

    annual_signal = to_float(
        (panel.get("headline", {}) if isinstance(panel, dict) else {}).get("total_estimated_annual_value_usd", 0.0)
    )

    payload = {
        "generated_utc": now_iso(),
        "scope": "enterprise_value_hardening_pack",
        "snapshot": {
            "annual_value_signal_usd": annual_signal,
            "runtime_readiness_status": str((readiness.get("summary", {}) if isinstance(readiness, dict) else {}).get("status", "")),
            "controller_mode": str(controller.get("mode", "")),
            "live_executor_heartbeat_status": str(live_hb.get("status", "")),
            "live_executor_heartbeat_age_sec": live_hb_age,
            "live_executor_heartbeat_fresh": (live_hb_age is not None and live_hb_age <= 180.0),
            "approval_heartbeat_status": str(approval_hb.get("status", "")),
            "approval_heartbeat_age_sec": approval_hb_age,
            "approval_heartbeat_fresh": (approval_hb_age is not None and approval_hb_age <= 180.0),
            "execution_status_age_sec": execution_status_age,
            "key_measured_coverage_pct": to_float((key_audit.get("summary", {}) if isinstance(key_audit, dict) else {}).get("measured_coverage_pct", 0.0)),
            "packet_refresh_generated_utc": packet_latest.get("generated_utc", "") if isinstance(packet_latest, dict) else "",
        },
        "commercial_sector_priorities": top_sector_rows(panel, top_n=8),
        "grant_priorities": grant_rows,
        "pilot_site_priorities": pilot_rows,
        "test_innovation_methods": build_test_innovation_methods(),
        "prioritized_backlog": build_backlog(
            proof_payload=proof_summary,
            site_reach_payload=site_reach,
            readiness_payload=readiness,
            key_audit_payload=key_audit,
            controller_payload=controller,
            execution_status_age_sec=execution_status_age,
        ),
        "evidence_paths": {
            "live_breadth": str(paths.live_breadth),
            "readiness": str(paths.readiness),
            "grants": str(paths.grant_fit),
            "site_reach": str(paths.site_reach),
            "pilots": str(paths.pilots),
            "key_audit": str(paths.key_audit),
            "vps_controller": str(paths.vps_controller),
            "live_executor_heartbeat": str(paths.live_executor_hb),
            "approval_heartbeat": str(paths.approval_hb),
            "execution_status": str(paths.execution_status),
            "proof_summary": str(proof_summary_path) if proof_summary_path else "",
        },
    }

    tag = now_tag()
    run_json = OUT_DIR / f"enterprise_value_hardening_pack_{tag}.json"
    run_md = OUT_DIR / f"enterprise_value_hardening_pack_{tag}.md"
    latest_json = OUT_DIR / "enterprise_value_hardening_pack_latest.json"
    latest_md = OUT_DIR / "enterprise_value_hardening_pack_latest.md"

    write_json(run_json, payload)
    write_json(latest_json, payload)
    write_md(run_md, render_markdown(payload))
    write_md(latest_md, render_markdown(payload))

    manifest = {
        "generated_utc": payload["generated_utc"],
        "scope": payload["scope"],
        "artifacts": {
            "run_json": str(run_json),
            "run_md": str(run_md),
            "latest_json": str(latest_json),
            "latest_md": str(latest_md),
        },
        "backlog_items": len(payload.get("prioritized_backlog", [])),
        "test_methods": len(payload.get("test_innovation_methods", [])),
    }

    manifest_path = OUT_DIR / f"enterprise_value_hardening_manifest_{tag}.json"
    latest_manifest = OUT_DIR / "enterprise_value_hardening_manifest_latest.json"
    write_json(manifest_path, manifest)
    write_json(latest_manifest, manifest)

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
