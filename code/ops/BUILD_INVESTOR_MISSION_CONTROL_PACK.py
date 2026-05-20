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

    fit_status = str(selected.get("fit_status") or "").upper()
    is_fit_likely = fit_status == "FIT_LIKELY"
    has_ticket = bool(ticket)

    if not selected:
        status = "no_candidate"
    elif is_fit_likely and has_ticket:
        status = "ready_for_live_fill"
    elif is_fit_likely and not has_ticket:
        status = "fit_candidate_missing_ticket_context"
    else:
        status = "manual_review_required"

    organization = ticket.get("organization") if isinstance(ticket, dict) else {}
    contacts = ticket.get("contacts") if isinstance(ticket, dict) else {}

    autofill_payload = {
        "opportunity": {
            "opp_num": selected.get("opp_num"),
            "title": selected.get("title"),
            "agency": selected.get("agency"),
            "close_date": selected.get("close_date"),
            "submit_url": selected.get("submit_url"),
            "fit_status": selected.get("fit_status"),
            "fit_reason": selected.get("fit_reason"),
            "source_channel": selected.get("source_channel"),
        },
        "organization": organization if isinstance(organization, dict) else {},
        "contacts": contacts if isinstance(contacts, dict) else {},
        "answers": {
            "abstract": str(ticket.get("abstract") or "") if isinstance(ticket, dict) else "",
            "statement_of_need": str(ticket.get("statement_of_need") or "") if isinstance(ticket, dict) else "",
            "expected_outcomes": ticket.get("expected_outcomes") if isinstance(ticket.get("expected_outcomes"), list) else [],
            "budget_narrative": ticket.get("budget_narrative") if isinstance(ticket.get("budget_narrative"), dict) else {},
            "budget_totals": ticket.get("budget_totals") if isinstance(ticket.get("budget_totals"), dict) else {},
            "evaluation_criteria_responses": ticket.get("evaluation_criteria_responses") if isinstance(ticket.get("evaluation_criteria_responses"), list) else [],
            "must_answer_fields": selected.get("must_answer_fields") if isinstance(selected.get("must_answer_fields"), list) else [],
            "answer_strategy": selected.get("answer_strategy") if isinstance(selected.get("answer_strategy"), list) else [],
        },
    }

    return {
        "selected_opportunity": selected,
        "queue_ticket_id": str(ticket.get("ticket_id") or "") if isinstance(ticket, dict) else "",
        "status": status,
        "grant_selected_automatically": bool(selected),
        "autofill_packet_ready": has_ticket,
        "human_submission_required": True,
        "selection_policy": "FIT_LIKELY first, then grants_gov preference, then nearest deadline, then highest award ceiling",
        "live_fill_steps": [
            "Open submit_url for the selected opportunity and start the application workspace.",
            "Paste organization, contact, and abstract fields from autofill_payload.",
            "Paste statement_of_need, expected_outcomes, and budget_narrative sections.",
            "Answer must_answer_fields in the same order and map answer_strategy bullets where required.",
            "Capture submission confirmation id, timestamp, and receipt screenshot as evidence artifacts.",
            "Mark submitted state only after confirmation evidence is saved.",
        ],
        "autofill_payload": autofill_payload,
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
    segments = [
        {
            "start_sec": 0,
            "end_sec": 30,
            "title": "Why This Exists",
            "script": (
                f"LumaTrader exists because critical systems still fail reactively. We built a government-grade decision platform that turns live telemetry into pre-failure action. "
                f"Today the platform tracks {enabled_sources} enabled sources with {measured_sources} measured sources and a modeled annual preserved-value surface of {as_usd(annual_value_usd)}."
            ),
        },
        {
            "start_sec": 30,
            "end_sec": 65,
            "title": "What Is Working Now",
            "script": (
                f"The top live economic lane is {top_sector}. Routing edge currently measures {as_pct(router_edge_pct)} and harmonic win-rate telemetry reads {as_pct(harmonic_win_rate_pct)}. "
                "The stack is already producing auditable artifacts, chain-of-custody records, and repeatable operations outputs."
            ),
        },
        {
            "start_sec": 65,
            "end_sec": 100,
            "title": "Why Investors Win",
            "script": (
                f"Investors are not funding an idea slide. They are funding an operating system that now ranks real human problems, led by {top_problem or 'critical infrastructure instability'}. "
                f"The latest alpha-edge run surfaces {grade_a_locks} grade-A lock candidates, so capital compounds into measurable execution edge rather than narrative-only milestones."
            ),
        },
        {
            "start_sec": 100,
            "end_sec": 135,
            "title": "Defensibility and Moat",
            "script": (
                "The moat is execution integrity: lane-isolated pipelines, hash-linked evidence, and deterministic refresh routines. "
                "That combination is difficult to replicate because it requires both technical depth and operational rigor."
            ),
        },
        {
            "start_sec": 135,
            "end_sec": 165,
            "title": "Autonomous Grant Engine",
            "script": (
                f"Our autonomous grant lane already picks high-fit opportunities and prepares submission packets. The current lead candidate is {selected_grant_title or 'the top fit opportunity in queue'}. "
                "That means non-dilutive capital is not a side process - it is integrated into the mission-control loop."
            ),
        },
        {
            "start_sec": 165,
            "end_sec": 180,
            "title": "Close and Ask",
            "script": (
                f"The current readiness state is {readiness_status}. With investor capital, we move from guarded proof mode into scaled live execution with the same governance discipline. "
                "If you want a platform that can prove value before claiming value, this is that platform."
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
    }


def build_3d_graphics_pack(sector_matrix: dict[str, Any], top_n: int) -> dict[str, Any]:
    rows = sector_matrix.get("sector_value_matrix", []) if isinstance(sector_matrix, dict) else []
    if not isinstance(rows, list):
        rows = []

    ranked = [row for row in rows if isinstance(row, dict)]
    ranked.sort(key=lambda row: safe_float(row.get("year", row.get("annual_exposure_usd", 0.0))), reverse=True)
    ranked = ranked[: max(1, top_n)]

    points: list[dict[str, Any]] = []
    for idx, row in enumerate(ranked, start=1):
        points.append(
            {
                "rank": idx,
                "sector": str(row.get("sector") or "unknown"),
                "x_rank": idx,
                "y_hourly_usd": safe_float(row.get("hour"), 0.0),
                "z_annual_usd": safe_float(row.get("year", row.get("annual_exposure_usd")), 0.0),
                "modeled_upside_usd": safe_float(row.get("modeled_annual_upside_usd"), 0.0),
                "basis": str(row.get("basis") or "unknown"),
            }
        )

    return {
        "generated_utc": now_iso(),
        "title": "Mission Control 3D Sector Surface",
        "chart_type": "3d_scatter_orbit",
        "axes": {
            "x": "sector rank",
            "y": "hourly preserved value usd",
            "z": "annual preserved value usd",
        },
        "camera": {"azimuth_deg": 38, "elevation_deg": 26, "distance": 2.4},
        "style": {
            "background": "#060d18",
            "grid": "#2a3f61",
            "accent_primary": "#5df3d0",
            "accent_secondary": "#ffd873",
        },
        "points": points,
        "powerpoint_guidance": [
            "Use one orbit intro shot, one rotation pass, and one static close-up on top 3 sectors.",
            "Annotate each point with sector, hourly usd, and annual usd.",
            "Keep basis label visible to separate measured and estimated values.",
        ],
    }


def render_pack_markdown(payload: dict[str, Any]) -> str:
    pitch = payload.get("three_min_nobel_pitch", {}) if isinstance(payload, dict) else {}
    parity = payload.get("powerpoint_mirror_parity", {}) if isinstance(payload, dict) else {}
    live_fill = payload.get("autonomous_grant_live_fill", {}) if isinstance(payload, dict) else {}
    graphics = payload.get("graphics_3d_pack", {}) if isinstance(payload, dict) else {}
    alpha_edge = payload.get("alpha_edge_lock_engine", {}) if isinstance(payload, dict) else {}
    blueprints = payload.get("government_grade_blueprints", {}) if isinstance(payload, dict) else {}
    site_reach = payload.get("site_reach_mission", {}) if isinstance(payload, dict) else {}
    challenge_stack = payload.get("three_min_challenge_problem_stack", []) if isinstance(payload, dict) else []
    selected = live_fill.get("selected_opportunity", {}) if isinstance(live_fill, dict) else {}

    lines: list[str] = []
    lines.append("# Investor Mission Control Pack")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Scope: {payload.get('scope', '')}")
    lines.append("")
    lines.append("## Three-Minute Nobel Pitch")
    lines.append(f"- Total seconds: {pitch.get('total_seconds', 0)}")
    lines.append("")
    for segment in pitch.get("segments", []) if isinstance(pitch, dict) else []:
        if not isinstance(segment, dict):
            continue
        lines.append(
            f"- {int(segment.get('start_sec', 0)):03d}-{int(segment.get('end_sec', 0)):03d}s | {segment.get('title', '')} | {segment.get('script', '')}"
        )
    lines.append("")
    lines.append("## 3-Minute Challenge Problem Stack")
    lines.append(f"- grade_a_locks: {alpha_edge.get('grade_a_locks', 0)}")
    lines.append(f"- top_problem: {alpha_edge.get('top_problem', '')}")
    for row in challenge_stack[:10] if isinstance(challenge_stack, list) else []:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- rank {row.get('rank')}: {row.get('problem_statement', '')} | sector={row.get('sector', '')} | alpha={row.get('alpha_lock_score', 0)} edge={row.get('edge_lock_score', 0)} conf={row.get('confidence_live_lock_pct', 0)}%"
        )
    lines.append("")
    lines.append("## Government-Grade Blueprint Vault")
    lines.append(f"- asset_count: {blueprints.get('asset_count', 0)}")
    lines.append(f"- focus_term_count: {blueprints.get('focus_term_count', 0)}")
    lines.append(f"- highest_trl_target: {blueprints.get('highest_trl_target', 0)}")
    lines.append(f"- engine_family: {blueprints.get('engine_family', '')}")
    lines.append("- featured_assets:")
    for item in blueprints.get("featured_assets", []) if isinstance(blueprints, dict) else []:
        lines.append(f"  - {item}")
    lines.append("")
    lines.append("## Site Reach and Mission Push")
    lines.append(f"- canonical_visitors_30d: {site_reach.get('canonical_visitors_30d')}")
    lines.append(f"- canonical_source: {site_reach.get('canonical_visitors_source', '')}")
    lines.append(f"- promotion_channels_ready: {site_reach.get('promotion_channels_ready', 0)}")
    lines.append(f"- promotion_channels_blocked: {site_reach.get('promotion_channels_blocked', 0)}")
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
    lines.append("## 3D Graphics Pack")
    lines.append(f"- chart_type: {graphics.get('chart_type', '')}")
    lines.append(f"- point_count: {len(graphics.get('points', [])) if isinstance(graphics, dict) else 0}")
    for point in graphics.get("points", [])[:5] if isinstance(graphics, dict) else []:
        if not isinstance(point, dict):
            continue
        lines.append(
            f"- rank {point.get('rank')}: {point.get('sector')} | hourly={as_usd(point.get('y_hourly_usd'))} | annual={as_usd(point.get('z_annual_usd'))}"
        )
    lines.append("")
    lines.append("## Autonomous Grant Live Fill")
    lines.append(f"- status: {live_fill.get('status', '')}")
    lines.append(f"- selected_opp_num: {selected.get('opp_num', '')}")
    lines.append(f"- selected_title: {selected.get('title', '')}")
    lines.append(f"- submit_url: {selected.get('submit_url', '')}")
    lines.append(f"- queue_ticket_id: {live_fill.get('queue_ticket_id', '')}")
    lines.append(f"- autofill_packet_ready: {live_fill.get('autofill_packet_ready', False)}")
    lines.append(f"- human_submission_required: {live_fill.get('human_submission_required', True)}")
    lines.append("- live_fill_steps:")
    for step in live_fill.get("live_fill_steps", []) if isinstance(live_fill, dict) else []:
        lines.append(f"  - {step}")

    return "\n".join(lines).rstrip() + "\n"


def render_pitch_markdown(pitch: dict[str, Any]) -> str:
    lines = [
        "# Three-Minute Nobel Pitch",
        "",
        f"Generated UTC: {pitch.get('generated_utc', '')}",
        f"Total Seconds: {pitch.get('total_seconds', 180)}",
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
    parser = argparse.ArgumentParser(description="Build investor mission-control pack with pitch, parity, 3D graphics, and autonomous grant live-fill payload.")
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
            "scope": "investor_mission_control_pack",
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
            },
            "headline": {
                "annual_value_signal_usd": annual_value_usd,
                "annual_value_signal_display": as_usd(annual_value_usd),
                "top_sector": top_sector,
                "measured_sources": measured_sources,
                "enabled_sources": enabled_sources,
                "router_edge_pct": router_edge_pct,
                "harmonic_win_rate_pct": harmonic_win_rate_pct,
                "readiness_status": readiness_status,
                "canonical_visitors_30d": (
                    (site_reach_mission.get("summary", {}) or {}).get("canonical_visitors_30d")
                    if isinstance(site_reach_mission, dict)
                    else None
                ),
                "canonical_visitors_source": (
                    (site_reach_mission.get("summary", {}) or {}).get("canonical_visitors_source")
                    if isinstance(site_reach_mission, dict)
                    else None
                ),
            },
            "three_min_nobel_pitch": pitch,
            "alpha_edge_lock_engine": {
                "generated_utc": alpha_edge_lock.get("generated_utc") if isinstance(alpha_edge_lock, dict) else None,
                "grade_a_locks": grade_a_locks,
                "top_problem": top_problem,
                "top_sector": alpha_summary.get("top_sector") if isinstance(alpha_summary, dict) else None,
                "live_posture": alpha_edge_lock.get("live_posture") if isinstance(alpha_edge_lock, dict) else {},
            },
            "three_min_challenge_problem_stack": (
                alpha_edge_lock.get("top_problem_stack", [])[:12]
                if isinstance(alpha_edge_lock, dict) and isinstance(alpha_edge_lock.get("top_problem_stack"), list)
                else []
            ),
            "government_grade_blueprints": {
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
                "highest_trl_target": (
                    (blueprint_vault.get("summary", {}) or {}).get("highest_trl_target")
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
            },
            "site_reach_mission": {
                "generated_utc": (
                    site_reach_mission.get("generated_utc")
                    if isinstance(site_reach_mission, dict)
                    else None
                ),
                "canonical_visitors_30d": (
                    (site_reach_mission.get("summary", {}) or {}).get("canonical_visitors_30d")
                    if isinstance(site_reach_mission, dict)
                    else None
                ),
                "canonical_visitors_source": (
                    (site_reach_mission.get("summary", {}) or {}).get("canonical_visitors_source")
                    if isinstance(site_reach_mission, dict)
                    else None
                ),
                "promotion_channels_ready": (
                    (site_reach_mission.get("summary", {}) or {}).get("promotion_channels_ready")
                    if isinstance(site_reach_mission, dict)
                    else 0
                ),
                "promotion_channels_blocked": (
                    (site_reach_mission.get("summary", {}) or {}).get("promotion_channels_blocked")
                    if isinstance(site_reach_mission, dict)
                    else 0
                ),
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
                "grade_a_locks": safe_int((payload.get("alpha_edge_lock_engine", {}) or {}).get("grade_a_locks"), 0),
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
