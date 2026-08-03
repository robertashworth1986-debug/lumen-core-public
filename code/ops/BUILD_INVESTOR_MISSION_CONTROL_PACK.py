from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = ROOT.parent
OUT_DIR = ROOT / "out" / "ops" / "investor_mission_control"

LIVE_BREADTH_PATH = ROOT / "out" / "ops" / "live_breadth_value_panel_latest.json"
INVESTOR_READINESS_PATH = ROOT / "out" / "ops" / "investor_metric_readiness_latest.json"
GRANT_FIT_PATH = ROOT / "out" / "ops" / "grant_submit_fit_pack" / "grant_submit_fit_pack_latest.json"
GRANT_QUEUE_PATH = ROOT / "out" / "grant_approval_queue.json"
SECTOR_MATRIX_PATH = ROOT / "out" / "sector_value_matrix.json"
ALPHA_EDGE_LOCK_PATH = ROOT / "out" / "ops" / "alpha_edge_lock" / "alpha_edge_lock_engine_latest.json"
BLUEPRINT_VAULT_PATH = ROOT / "out" / "ops" / "gov_blueprint_vault" / "gov_blueprint_vault_latest.json"
SITE_REACH_MISSION_PATH = ROOT / "out" / "ops" / "site_reach_mission" / "site_reach_mission_latest.json"
SLIDES_JSON_PATH = ROOT / "out" / "INSTITUTIONAL_REVIEW_BUNDLE" / "nobel_tier_slides.json"
NOBEL_DASHBOARD_PATH = ROOT / "dashboard" / "nobel_tier_command_center.html"
SOURCE_NATIVE_LEDGER_PATH = (
    ROOT / "out" / "ops" / "source_native_family_baseline_ledger_latest.json"
)
PROSPECTIVE_STATUS_PATH = (
    ROOT / "out" / "ops" / "time_series_source_native_prospective_protocol_status.json"
)

HEARTBEAT_LATEST_PATH = OUT_DIR / "investor_mission_control_pack_heartbeat_latest.json"

ROOT_DASH = WORKSPACE_ROOT / "dashboard"
STACK_DASH = ROOT / "dashboard"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


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


def as_usd(value: Any) -> str:
    amount = safe_float(value, 0.0)
    if abs(amount) >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.2f}B"
    if abs(amount) >= 1_000_000:
        return f"${amount / 1_000_000:.2f}M"
    if abs(amount) >= 1_000:
        return f"${amount / 1_000:.1f}K"
    return f"${amount:,.2f}"


def as_pct(value: Any) -> str:
    return f"{safe_float(value, 0.0):.2f}%"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_powerpoint_mirror_parity() -> dict[str, Any]:
    file_pairs = [
        ("mission_control", ROOT_DASH / "mission_control.html", STACK_DASH / "mission_control.html"),
        ("quant_lab", ROOT_DASH / "quant_lab.html", STACK_DASH / "quant_lab.html"),
        ("investor_command_room", ROOT_DASH / "investor_command_room.html", STACK_DASH / "investor_command_room.html"),
        ("kraken_execution_dashboard", ROOT_DASH / "kraken_execution_dashboard.html", STACK_DASH / "kraken_execution_dashboard.html"),
        ("luma_experience", ROOT_DASH / "luma_experience.html", STACK_DASH / "luma_experience.html"),
        ("scenario_mission", ROOT_DASH / "scenario_mission.html", STACK_DASH / "scenario_mission.html"),
        ("grants", ROOT_DASH / "grants.html", STACK_DASH / "grants.html"),
        ("investor_wallboard", ROOT_DASH / "investor_wallboard.html", STACK_DASH / "investor_wallboard.html"),
        ("nobel_command_center", ROOT_DASH / "nobel_tier_command_center.html", STACK_DASH / "nobel_tier_command_center.html"),
    ]

    rows: list[dict[str, Any]] = []
    drift_count = 0
    missing_count = 0

    for label, root_path, stack_path in file_pairs:
        root_exists = root_path.exists()
        stack_exists = stack_path.exists()

        root_hash = sha256_file(root_path) if root_exists else ""
        stack_hash = sha256_file(stack_path) if stack_exists else ""

        parity = bool(root_exists and stack_exists and root_hash == stack_hash)
        if not root_exists or not stack_exists:
            missing_count += 1
        elif not parity:
            drift_count += 1

        rows.append(
            {
                "label": label,
                "root_path": str(root_path),
                "stack_path": str(stack_path),
                "root_exists": root_exists,
                "stack_exists": stack_exists,
                "root_sha256": root_hash,
                "stack_sha256": stack_hash,
                "parity": parity,
            }
        )

    return {
        "checked_utc": now_iso(),
        "drift_count": drift_count,
        "missing_count": missing_count,
        "parity_ok": drift_count == 0 and missing_count == 0,
        "rows": rows,
    }


def _first_match(queue_rows: list[dict[str, Any]], opp_num: str) -> dict[str, Any]:
    needle = str(opp_num or "").strip().upper()
    for row in queue_rows:
        if not isinstance(row, dict):
            continue
        opp = row.get("opportunity", {})
        if not isinstance(opp, dict):
            continue
        cand = str(opp.get("opp_num") or "").strip().upper()
        if cand and cand == needle:
            return row
    return {}


def select_autonomous_grant_live_fill(fit_pack: dict[str, Any], queue_rows: list[dict[str, Any]]) -> dict[str, Any]:
    opportunities = fit_pack.get("opportunities", []) if isinstance(fit_pack, dict) else []
    if not isinstance(opportunities, list):
        opportunities = []

    ranked_candidates: list[tuple[tuple[int, int, int, float], dict[str, Any]]] = []
    for row in opportunities:
        if not isinstance(row, dict):
            continue
        fit_status = str(row.get("fit_status") or "").upper()
        fit_rank = 0 if fit_status == "FIT_LIKELY" else 1 if fit_status == "MANUAL_CHECK" else 2
        source = str(row.get("source_channel") or "").lower()
        source_rank = 0 if source == "grants_gov" else 1
        days_to_close = safe_int(row.get("days_to_close"), 9999)
        award = safe_float(row.get("award_ceiling_usd"), 0.0)
        ranked_candidates.append(((fit_rank, source_rank, days_to_close, -award), row))

    ranked_candidates.sort(key=lambda item: item[0])
    selected = ranked_candidates[0][1] if ranked_candidates else {}

    selected_opp_num = str(selected.get("opp_num") or "")
    ticket = _first_match(queue_rows, selected_opp_num) if selected_opp_num else {}
    safe_selected = {
        "opp_num": selected.get("opp_num"),
        "title": selected.get("title"),
        "agency": selected.get("agency"),
        "close_date": selected.get("close_date"),
        "source_channel": selected.get("source_channel"),
        "local_fit_label": selected.get("fit_status"),
    }
    if not selected:
        status = "NO_CANDIDATE"
    else:
        status = "REVIEW_ONLY_OFFICIAL_SOURCE_REVERIFY_REQUIRED"

    return {
        "selected_opportunity": safe_selected if selected else {},
        "queue_ticket_id": str(ticket.get("ticket_id") or "") if isinstance(ticket, dict) else "",
        "status": status,
        "grant_selected_automatically": False,
        "autofill_packet_ready": False,
        "review_only": True,
        "deadline_actionable": False,
        "submission_authorized": False,
        "human_submission_required": True,
        "selection_policy": (
            "Legacy local ranking only. It cannot establish current status, eligibility, "
            "deadline, responsiveness, or authority."
        ),
        "review_steps": [
            "Open the current official notice and all amendments.",
            "Verify deadline, timezone, status, eligibility, route, and mandatory attachments.",
            "Reconcile the local candidate against the current authority and duplicate ledger.",
            "Draft only after the notice-specific conformance gate passes.",
            "Keep every certification, signature, upload, send, and submission with the authorized human.",
        ],
        "autofill_payload": {},
        "boundary": (
            "No private organization, contact, budget, or proposal answer content is "
            "included. This record is not a submission packet or portal instruction."
        ),
    }


def build_three_minute_pitch(
    annual_value_usd: float,
    top_sector: str,
    measured_sources: int,
    enabled_sources: int,
    router_edge_pct: float,
    harmonic_win_rate_pct: float,
    readiness_status: str,
    selected_grant_title: str,
    top_problem: str,
    grade_a_locks: int,
) -> dict[str, Any]:
    source_native = load_json(SOURCE_NATIVE_LEDGER_PATH, {})
    prospective = load_json(PROSPECTIVE_STATUS_PATH, {})
    source_summary = (
        source_native.get("summary", {}) if isinstance(source_native, dict) else {}
    )
    registered_families = safe_int(source_summary.get("registered_family_count"), 0)
    implemented_families = safe_int(
        source_summary.get("implementation_present_count"), 0
    )
    comparisons = safe_int(
        source_summary.get("executed_direct_source_baseline_comparison_count"), 0
    )
    promotions = safe_int(
        source_summary.get("internal_source_native_promotion_gate_pass_count"), 0
    )
    protocol_status = str(
        prospective.get("protocol_status") or "UNVERIFIED"
    )
    segments = [
        {
            "start_sec": 0,
            "end_sec": 30,
            "title": "The Problem",
            "script": (
                "Technical teams lose trust when source identity, baselines, failure "
                "rules, and decision authority are not preserved. LumenCore is an "
                "evidence-engineering repository built to make those controls visible "
                "and replayable."
            ),
        },
        {
            "start_sec": 30,
            "end_sec": 65,
            "title": "What Exists",
            "script": (
                f"The current source-native ledger registers {registered_families} "
                f"candidate families, records {implemented_families} implementations, "
                f"and contains {comparisons} direct source-baseline comparisons. "
                "Hash-linked receipts and fail-closed claim states preserve both "
                "positive and adverse evidence."
            ),
        },
        {
            "start_sec": 65,
            "end_sec": 100,
            "title": "What The Evidence Says",
            "script": (
                f"The strict promotion count is {promotions}. That means the current "
                "contribution is the governed comparison protocol, not a performance "
                f"champion. The prospective protocol is {protocol_status.lower()} and "
                "will wait for future eligible observations."
            ),
        },
        {
            "start_sec": 100,
            "end_sec": 135,
            "title": "Commercial Wedge",
            "script": (
                "The first bounded offer is ProofLock Opportunity Operations: one "
                "buyer-approved workflow, frozen denominators and thresholds, "
                "evidence-linked review, blocker ledgers, and human-owned final action."
            ),
        },
        {
            "start_sec": 135,
            "end_sec": 165,
            "title": "Government And Prime Fit",
            "script": (
                "The credible federal posture is a bounded evidence-readiness sprint "
                "or a specialized workstream under a qualified prime. Current notices, "
                "eligibility, representations, pricing, certifications, and submissions "
                "remain action-time human decisions."
            ),
        },
        {
            "start_sec": 165,
            "end_sec": 180,
            "title": "Close and Ask",
            "script": (
                "The ask is specific: an independent protocol reviewer, one scoped "
                "pilot buyer, or one qualified-prime teaming review. No valuation, "
                "savings, award, or performance result is asserted."
            ),
        },
    ]

    lines: list[str] = []
    for segment in segments:
        start = int(segment["start_sec"])
        end = int(segment["end_sec"])
        lines.append(
            f"[{start // 60:02d}:{start % 60:02d}-{end // 60:02d}:{end % 60:02d}] {segment['title']}: {segment['script']}"
        )

    full_script = "\n\n".join(lines)

    return {
        "generated_utc": now_iso(),
        "total_seconds": 180,
        "segments": segments,
        "full_script": full_script,
        "external_share_ready": False,
        "recipient_selected": False,
        "legacy_value_inputs_suppressed": True,
        "boundary": (
            "Internal draft. Source counts and local receipts do not establish "
            "freshness, field performance, customer acceptance, value, or authority."
        ),
    }


def build_3d_graphics_pack(sector_matrix: dict[str, Any], top_n: int) -> dict[str, Any]:
    return {
        "generated_utc": now_iso(),
        "title": "Legacy Modeled Value Surface",
        "status": "BLOCKED_FROM_INVESTOR_AND_REVIEWER_USE",
        "chart_type": None,
        "points": [],
        "legacy_row_count": len(
            sector_matrix.get("sector_value_matrix", [])
            if isinstance(sector_matrix, dict)
            and isinstance(sector_matrix.get("sector_value_matrix"), list)
            else []
        ),
        "boundary": (
            "Modeled sector-value rows are suppressed because they are not audited "
            "realized outcomes, accepted counterfactuals, or enterprise valuation."
        ),
    }


def render_pack_markdown(payload: dict[str, Any]) -> str:
    pitch = payload.get("three_min_nobel_pitch", {}) if isinstance(payload, dict) else {}
    parity = payload.get("powerpoint_mirror_parity", {}) if isinstance(payload, dict) else {}
    live_fill = payload.get("autonomous_grant_live_fill", {}) if isinstance(payload, dict) else {}
    graphics = payload.get("graphics_3d_pack", {}) if isinstance(payload, dict) else {}
    selected = live_fill.get("selected_opportunity", {}) if isinstance(live_fill, dict) else {}

    lines: list[str] = []
    lines.append("# Investor Mission Control Pack")
    lines.append("")
    lines.append("**DRAFT ONLY - RECIPIENT NOT SELECTED - EXTERNAL CLAIM REVIEW REQUIRED**")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Scope: {payload.get('scope', '')}")
    lines.append(f"Boundary: {payload.get('boundary', '')}")
    lines.append("")
    lines.append("## Three-Minute Evidence Pitch")
    lines.append(f"- Total seconds: {pitch.get('total_seconds', 0)}")
    lines.append("")
    for segment in pitch.get("segments", []) if isinstance(pitch, dict) else []:
        if not isinstance(segment, dict):
            continue
        lines.append(
            f"- {int(segment.get('start_sec', 0)):03d}-{int(segment.get('end_sec', 0)):03d}s | {segment.get('title', '')} | {segment.get('script', '')}"
        )
    lines.append("")
    lines.append("## PowerPoint Mirror Parity")
    lines.append(f"- parity_ok: {parity.get('parity_ok', False)}")
    lines.append(f"- drift_count: {parity.get('drift_count', 0)}")
    lines.append(f"- missing_count: {parity.get('missing_count', 0)}")
    for row in parity.get("rows", []) if isinstance(parity, dict) else []:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('label', '')}: parity={row.get('parity', False)} root_exists={row.get('root_exists', False)} stack_exists={row.get('stack_exists', False)}"
        )
    lines.append("")
    lines.append("## Legacy Modeled-Value Graphic")
    lines.append(f"- status: {graphics.get('status', '')}")
    lines.append(f"- rendered point count: {len(graphics.get('points', [])) if isinstance(graphics, dict) else 0}")
    lines.append(f"- boundary: {graphics.get('boundary', '')}")
    lines.append("")
    lines.append("## Review-Only Opportunity Candidate")
    lines.append(f"- status: {live_fill.get('status', '')}")
    lines.append(f"- selected_opp_num: {selected.get('opp_num', '')}")
    lines.append(f"- selected_title: {selected.get('title', '')}")
    lines.append(f"- queue_ticket_id: {live_fill.get('queue_ticket_id', '')}")
    lines.append(f"- autofill_packet_ready: {live_fill.get('autofill_packet_ready', False)}")
    lines.append(f"- submission_authorized: {live_fill.get('submission_authorized', False)}")
    lines.append(f"- human_submission_required: {live_fill.get('human_submission_required', True)}")
    lines.append(f"- boundary: {live_fill.get('boundary', '')}")
    lines.append("- review_steps:")
    for step in live_fill.get("review_steps", []) if isinstance(live_fill, dict) else []:
        lines.append(f"  - {step}")

    return "\n".join(lines).rstrip() + "\n"


def render_pitch_markdown(pitch: dict[str, Any]) -> str:
    lines = [
        "# Three-Minute LumenCore Evidence Pitch",
        "",
        "**DRAFT ONLY - RECIPIENT NOT SELECTED - EXTERNAL CLAIM REVIEW REQUIRED**",
        "",
        f"Generated UTC: {pitch.get('generated_utc', '')}",
        f"Total Seconds: {pitch.get('total_seconds', 180)}",
        f"Boundary: {pitch.get('boundary', '')}",
        "",
    ]
    for segment in pitch.get("segments", []):
        if not isinstance(segment, dict):
            continue
        start = int(segment.get("start_sec", 0))
        end = int(segment.get("end_sec", 0))
        lines.append(f"## {start // 60:02d}:{start % 60:02d} - {end // 60:02d}:{end % 60:02d} | {segment.get('title', '')}")
        lines.append(str(segment.get("script", "")))
        lines.append("")
    lines.append("## Full Script")
    lines.append(str(pitch.get("full_script", "")))
    lines.append("")
    return "\n".join(lines)


def write_heartbeat(
    *,
    status: str,
    reason: str,
    run_tag: str,
    top_sectors: int,
    summary: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "generated_utc": now_iso(),
        "scope": "investor_mission_control_pack",
        "mode": "export",
        "status": str(status),
        "reason": str(reason),
        "run_tag": run_tag,
        "config": {
            "top_sectors": int(top_sectors),
        },
        "summary": summary if isinstance(summary, dict) else {},
        "artifacts": artifacts if isinstance(artifacts, dict) else {},
    }
    if error:
        payload["error"] = str(error)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    heartbeat_ts_path = OUT_DIR / f"investor_mission_control_pack_heartbeat_{run_tag}.json"
    heartbeat_text = json.dumps(payload, indent=2)
    heartbeat_ts_path.write_text(heartbeat_text, encoding="utf-8")
    HEARTBEAT_LATEST_PATH.write_text(heartbeat_text, encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build an internal claim-bounded investor mission-control pack with "
            "a review-only opportunity candidate."
        )
    )
    parser.add_argument("--top-sectors", type=int, default=10, help="Number of sectors to include in 3D graphics pack")
    args = parser.parse_args()

    top_sectors = int(args.top_sectors)
    run_tag = now_tag()
    write_heartbeat(
        status="running",
        reason="build_started",
        run_tag=run_tag,
        top_sectors=top_sectors,
    )

    try:
        live_breadth = load_json(LIVE_BREADTH_PATH, {})
        readiness = load_json(INVESTOR_READINESS_PATH, {})
        fit_pack = load_json(GRANT_FIT_PATH, {})
        grant_queue = load_json(GRANT_QUEUE_PATH, [])
        sector_matrix = load_json(SECTOR_MATRIX_PATH, {})
        alpha_edge_lock = load_json(ALPHA_EDGE_LOCK_PATH, {})
        blueprint_vault = load_json(BLUEPRINT_VAULT_PATH, {})
        site_reach_mission = load_json(SITE_REACH_MISSION_PATH, {})
        slides = load_json(SLIDES_JSON_PATH, {})
        source_native = load_json(SOURCE_NATIVE_LEDGER_PATH, {})
        prospective = load_json(PROSPECTIVE_STATUS_PATH, {})

        queue_rows = grant_queue if isinstance(grant_queue, list) else []

        summary = readiness.get("summary", {}) if isinstance(readiness, dict) else {}
        signal = summary.get("signal_evidence", {}) if isinstance(summary, dict) else {}
        headline = live_breadth.get("headline", {}) if isinstance(live_breadth, dict) else {}

        annual_value_usd = safe_float(signal.get("annual_value_usd"), safe_float(headline.get("total_estimated_annual_value_usd"), 0.0))
        top_sector = str(signal.get("top_sector") or headline.get("top_sector") or "unknown")
        measured_sources = safe_int(signal.get("measured_sources"), safe_int(headline.get("measured_sources"), 0))
        enabled_sources = safe_int(signal.get("enabled_sources"), safe_int(headline.get("enabled_sources"), 0))
        router_edge_pct = safe_float(signal.get("router_edge_pct"), safe_float(headline.get("router_edge_pct"), 0.0))
        harmonic_win_rate_pct = safe_float(signal.get("harmonic_win_rate_pct"), safe_float(headline.get("harmonic_win_rate_pct"), 0.0))
        readiness_status = str(summary.get("status") or headline.get("performance_metrics_status") or "unknown")

        live_fill = select_autonomous_grant_live_fill(fit_pack=fit_pack, queue_rows=queue_rows)
        selected_title = str((live_fill.get("selected_opportunity") or {}).get("title") or "")
        alpha_summary = alpha_edge_lock.get("summary", {}) if isinstance(alpha_edge_lock, dict) else {}
        top_problem = str(alpha_summary.get("top_problem") or "")
        grade_a_locks = safe_int(alpha_summary.get("grade_a_locks"), 0)

        pitch = build_three_minute_pitch(
            annual_value_usd=annual_value_usd,
            top_sector=top_sector,
            measured_sources=measured_sources,
            enabled_sources=enabled_sources,
            router_edge_pct=router_edge_pct,
            harmonic_win_rate_pct=harmonic_win_rate_pct,
            readiness_status=readiness_status,
            selected_grant_title=selected_title,
            top_problem=top_problem,
            grade_a_locks=grade_a_locks,
        )

        parity = build_powerpoint_mirror_parity()
        graphics_3d_pack = build_3d_graphics_pack(sector_matrix=sector_matrix, top_n=top_sectors)

        payload = {
            "generated_utc": now_iso(),
            "scope": "internal_claim_bounded_investor_mission_control_pack",
            "status": "INTERNAL_DRAFT_RECIPIENT_AND_CLAIM_REVIEW_REQUIRED",
            "external_share_ready": False,
            "recipient_selected": False,
            "boundary": (
                "Local artifacts can establish software, custody, protocol, and gate "
                "behavior only. No valuation, savings, field performance, trading "
                "alpha, customer acceptance, agency endorsement, award, or external "
                "action is authorized."
            ),
            "source_artifacts": {
                "live_breadth_value_panel_latest": str(LIVE_BREADTH_PATH),
                "investor_metric_readiness_latest": str(INVESTOR_READINESS_PATH),
                "grant_submit_fit_pack_latest": str(GRANT_FIT_PATH),
                "grant_approval_queue": str(GRANT_QUEUE_PATH),
                "sector_value_matrix": str(SECTOR_MATRIX_PATH),
                "alpha_edge_lock_engine_latest": str(ALPHA_EDGE_LOCK_PATH),
                "gov_blueprint_vault_latest": str(BLUEPRINT_VAULT_PATH),
                "site_reach_mission_latest": str(SITE_REACH_MISSION_PATH),
                "nobel_slides_json": str(SLIDES_JSON_PATH),
                "nobel_dashboard_html": str(NOBEL_DASHBOARD_PATH),
                "source_native_family_baseline_ledger": str(
                    SOURCE_NATIVE_LEDGER_PATH
                ),
                "source_native_prospective_status": str(
                    PROSPECTIVE_STATUS_PATH
                ),
            },
            "headline": {
                "message": (
                    "Evidence engineering for source-native technical review, "
                    "replayable receipts, and human-authorized decisions."
                ),
                "legacy_value_metrics_suppressed": True,
                "legacy_performance_metrics_suppressed": True,
                "current_promotion_count": safe_int(
                    (
                        source_native.get("summary", {})
                        if isinstance(source_native, dict)
                        else {}
                    ).get("internal_source_native_promotion_gate_pass_count"),
                    0,
                ),
                "prospective_protocol_status": (
                    prospective.get("protocol_status")
                    if isinstance(prospective, dict)
                    else None
                ),
                "prospective_promotion_decision": (
                    prospective.get("promotion_decision")
                    if isinstance(prospective, dict)
                    else None
                ),
            },
            "three_min_nobel_pitch": pitch,
            "alpha_edge_lock_engine": {
                "status": "LEGACY_RESEARCH_SCORE_SUPPRESSED",
                "promotion_claim_allowed": False,
                "field_performance_claim_allowed": False,
                "boundary": (
                    "Legacy alpha, edge, lock, and confidence labels are not "
                    "external performance evidence."
                ),
            },
            "three_min_challenge_problem_stack": [],
            "bounded_blueprint_inventory": {
                "generated_utc": (
                    blueprint_vault.get("generated_utc")
                    if isinstance(blueprint_vault, dict)
                    else None
                ),
                "asset_count": (
                    (blueprint_vault.get("summary", {}) or {}).get("asset_count")
                    if isinstance(blueprint_vault, dict)
                    else 0
                ),
                "focus_term_count": (
                    (blueprint_vault.get("summary", {}) or {}).get("focus_term_count")
                    if isinstance(blueprint_vault, dict)
                    else 0
                ),
                "engine_family": (
                    (blueprint_vault.get("engine_binding", {}) or {}).get("family")
                    if isinstance(blueprint_vault, dict)
                    else ""
                ),
                "featured_assets": (
                    [
                        str(row.get("asset_name") or "")
                        for row in (blueprint_vault.get("assets", []) or [])[:6]
                        if isinstance(row, dict)
                    ]
                    if isinstance(blueprint_vault, dict)
                    else []
                ),
                "government_grade_claim_allowed": False,
                "trl_claim_allowed": False,
                "boundary": (
                    "Local blueprint inventory does not establish agency acceptance, "
                    "technical readiness level, certification, or deployment readiness."
                ),
            },
            "site_reach_mission": {
                "status": "LEGACY_PROMOTION_METRICS_SUPPRESSED",
                "external_promotion_authorized": False,
            },
            "powerpoint_mirror_parity": parity,
            "graphics_3d_pack": graphics_3d_pack,
            "autonomous_grant_live_fill": live_fill,
            "powerpoint_assets": {
                "slides_present": bool(slides),
                "slides_count": safe_int(slides.get("slide_count"), 0) if isinstance(slides, dict) else 0,
                "slides_deck_name": str(slides.get("deck_name") or "") if isinstance(slides, dict) else "",
                "root_dashboard_dir": str(ROOT_DASH),
                "institutional_dashboard_dir": str(STACK_DASH),
            },
            "claim_controls": {
                "valuation_claim_allowed": False,
                "savings_claim_allowed": False,
                "performance_claim_allowed": False,
                "autonomous_grant_claim_allowed": False,
                "external_action_allowed": False,
            },
        }

        OUT_DIR.mkdir(parents=True, exist_ok=True)

        pack_json_ts = OUT_DIR / f"investor_mission_control_pack_{run_tag}.json"
        pack_md_ts = OUT_DIR / f"investor_mission_control_pack_{run_tag}.md"
        pitch_md_ts = OUT_DIR / f"investor_3min_nobel_pitch_{run_tag}.md"

        pack_json_latest = OUT_DIR / "investor_mission_control_pack_latest.json"
        pack_md_latest = OUT_DIR / "investor_mission_control_pack_latest.md"
        pitch_md_latest = OUT_DIR / "investor_3min_nobel_pitch_latest.md"

        pack_json_ts.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        pack_json_latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        pack_md = render_pack_markdown(payload)
        pack_md_ts.write_text(pack_md, encoding="utf-8")
        pack_md_latest.write_text(pack_md, encoding="utf-8")

        pitch_md = render_pitch_markdown(pitch)
        pitch_md_ts.write_text(pitch_md, encoding="utf-8")
        pitch_md_latest.write_text(pitch_md, encoding="utf-8")

        write_heartbeat(
            status="ok",
            reason="build_complete",
            run_tag=run_tag,
            top_sectors=top_sectors,
            summary={
                "parity_ok": bool((payload.get("powerpoint_mirror_parity", {}) or {}).get("parity_ok", False)),
                "selected_opp_num": str(((payload.get("autonomous_grant_live_fill", {}) or {}).get("selected_opportunity", {}) or {}).get("opp_num") or ""),
                "grant_live_fill_status": str((payload.get("autonomous_grant_live_fill", {}) or {}).get("status") or ""),
                "external_share_ready": False,
                "current_promotion_count": safe_int(
                    (payload.get("headline", {}) or {}).get(
                        "current_promotion_count"
                    ),
                    0,
                ),
            },
            artifacts={
                "json_latest": str(pack_json_latest),
                "json_timestamped": str(pack_json_ts),
                "md_latest": str(pack_md_latest),
                "md_timestamped": str(pack_md_ts),
                "pitch_md_latest": str(pitch_md_latest),
                "pitch_md_timestamped": str(pitch_md_ts),
            },
        )

        print("BUILD_INVESTOR_MISSION_CONTROL_PACK")
        print(f"status={payload['autonomous_grant_live_fill'].get('status', 'unknown')}")
        print(f"selected_opp={((payload['autonomous_grant_live_fill'].get('selected_opportunity') or {}).get('opp_num') or '')}")
        print(f"parity_ok={payload['powerpoint_mirror_parity'].get('parity_ok', False)}")
        print(f"json={pack_json_latest}")
        print(f"md={pack_md_latest}")
        print(f"pitch_md={pitch_md_latest}")
        return 0
    except Exception as exc:
        write_heartbeat(
            status="error",
            reason="build_failed",
            run_tag=run_tag,
            top_sectors=top_sectors,
            error=str(exc),
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
