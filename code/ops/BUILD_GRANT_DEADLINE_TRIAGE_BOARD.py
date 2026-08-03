from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "ops"
GRANTS = ROOT / "grant_submissions"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

READINESS_JSON = OUT / "grant_submission_readiness_audit_latest.json"
DICE_DEADLINE_EXTRACT = OUT / "HR001126S0010_DICE_deadline_extract.txt"
DSIP_TOPICS_JSON = OUT / "dod_dsip_official_topic_deadlines_latest.json"
GEOMETRY_BRIDGE_JSON = OUT / "geometry_championship_bridge_latest.json"
PUBLIC_VISIBILITY_JSON = OUT / "public_visibility_packet_latest.json"
TOP5_LIVE_PROOF_JSON = OUT / "top5_live_proof_submission_board_latest.json"
CURRENT_COMMAND_BOARD_JSON = OUT / "near_deadline_submission_command_board_latest.json"
OFFICIAL_INBOUND_STATUS_EVENT_REGISTER = (
    GRANTS
    / "funding_sprint_20260709"
    / "OFFICIAL_INBOUND_STATUS_EVENT_REGISTER_2026-07-25.json"
)

OUT_JSON = OUT / "grant_deadline_triage_latest.json"
OUT_MD = GRANTS / "GRANT_DEADLINE_TRIAGE_2026-06-22.md"
DASHBOARD_JSON = DASHBOARD_DATA / "grant_deadline_triage.json"

EASTERN = ZoneInfo("America/New_York")
CENTRAL = ZoneInfo("America/Chicago")

DICE_OFFICIAL_SOURCE = (
    "https://files.simpler.grants.gov/opportunities/56b71085-ed91-4468-b7eb-3a04bf840794/"
    "attachments/428dc8ae-7fec-4e5f-a82f-0ccc24dfcc26/HR001126S0010.pdf"
)
DSIP_SEARCH_SOURCE = "https://www.dodsbirsttr.mil/topics-app/"

PACKAGE_TOPIC_CODES = {
    "HarborSentinel": "DON26BZ03-NV063",
    "NV065": "DON26BZ03-NV065",
    "MissionWeave": "DLA26BZ03-NV011",
}

PORTAL_ORDER = [
    {
        "portal": "DARPA BAAT",
        "why": "DICE was not a Grants.gov submit path, but the official abstract response discouraged a full proposal and closed this route.",
        "user_state": "No BAAT sign-in, reply, upload, or full-proposal action is due.",
        "capture": [
            "Preserve the sanitized official closure event and postmortem.",
            "Do not revive the historical full-proposal package from an older board.",
            "Reopen only for a genuinely new official opportunity.",
        ],
    },
    {
        "portal": "DoD SBIR/STTR DSIP",
        "why": "The listed NV063, NV065, and DLA26BZ03-NV011 captures are historical DSIP topic paths, not current Grants.gov workspaces.",
        "user_state": "The captured windows are closed or non-actionable; do not reopen an expired workspace.",
        "capture": [
            "Preserve the official non-submission and topic-removal receipts.",
            "Carry unresolved CMMC, JCP, eligibility, and authority gates into a new topic only after fresh official-source review.",
            "Do not certify, upload, or represent any historical proposal as submitted.",
        ],
    },
    {
        "portal": "SAM.gov",
        "why": "Entity status supports federal award eligibility, but it does not clear BAAT/DSIP authority or compliance reps.",
        "user_state": "User reports signed in; local readiness audit records active SAM status.",
        "capture": [
            "Registration remains Active.",
            "Expiration date is still valid for the target submission period.",
            "Assertions and reps relevant to the target opportunity are reviewed by the user.",
        ],
    },
    {
        "portal": "Grants.gov",
        "why": "Useful for Grants.gov opportunities and AOR/workspace authority checks, but not the DICE abstract or DSIP submit path.",
        "user_state": "User reports signed in.",
        "capture": [
            "AOR/workspace role is visible for any Grants.gov-targeted opportunity.",
            "No non-Grants.gov package is accidentally submitted through the wrong channel.",
        ],
    },
    {
        "portal": "PIEE / SPRS",
        "why": "Needed only if the DoD cyber/CMMC/SPRS representation path must be verified.",
        "user_state": "Do not enter or certify anything until factual status is known.",
        "capture": [
            "Cyber Vendor User / SPRS access status.",
            "CAGE hierarchy and Affirming Official path if applicable.",
            "Current CMMC/SPRS status, or explicitly unknown status.",
        ],
    },
]

SAFETY_BOUNDARIES = [
    "No upload, certification, consent, signature, workspace lock, or submission is authorized by this board.",
    "Do not affirm CMMC, SPRS, cybersecurity, FOCI, export, ownership, facility, partner, demo-site, or cost representations unless the user verifies the fact at action time.",
    "Geometry, live-breadth, synthetic, public-data, and controlled-injection results are proof-building evidence only unless a field-validation gate explicitly passes.",
    "Dollar-value and award-likelihood claims remain blocked unless a separate dollar claim gate passes with real measured data and reviewed assumptions.",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def display_path(path: Path) -> str:
    try:
        value = path.relative_to(ROOT)
    except ValueError:
        value = path
    return str(value).replace("\\", "/")


def official_dice_closure() -> dict[str, Any]:
    register = read_json(OFFICIAL_INBOUND_STATUS_EVENT_REGISTER)
    events = register.get("events", []) if isinstance(register, dict) else []
    event = next(
        (
            row
            for row in events
            if isinstance(row, dict)
            and row.get("lane_id") == "darpa_dice_abstract_status"
        ),
        None,
    )
    if not isinstance(event, dict):
        return {
            "status": "OFFICIAL_STATUS_MISSING_REVERIFY_REQUIRED",
            "source_received_utc": None,
            "full_proposal_allowed": False,
            "reply_required": False,
            "do_not_duplicate": True,
            "safest_next_action": (
                "Reconcile the sanitized official inbound register before using any "
                "historical DICE package; no reply or full proposal is authorized."
            ),
        }
    evidence = event.get("evidence", {})
    action = event.get("action", {})
    valid = (
        event.get("status") == "FULL_PROPOSAL_DISCOURAGED_ROUTE_CLOSED"
        and evidence.get("official_status_received") is True
        and evidence.get("full_proposal_encouraged") is False
        and evidence.get("reply_requested") is False
        and action.get("send_now") is False
        and action.get("duplicate_send_decision")
        == "CLOSE_WITHOUT_REPLY_OR_FULL_PROPOSAL"
    )
    if not valid:
        raise ValueError("DARPA DICE official closure event is missing or unsafe")
    return {
        "status": event["status"],
        "source_received_utc": event.get("source", {}).get("received_utc"),
        "full_proposal_allowed": False,
        "reply_required": False,
        "do_not_duplicate": True,
        "safest_next_action": action["safest_next_action"],
    }


def current_command_board_overlay() -> dict[str, Any]:
    board = read_json(CURRENT_COMMAND_BOARD_JSON)
    if board.get("schema") != "near_deadline_submission_command_board_v5":
        return {
            "available": False,
            "status": "CURRENT_COMMAND_BOARD_MISSING_REVERIFY_REQUIRED",
            "source_path": display_path(CURRENT_COMMAND_BOARD_JSON),
            "stage_lanes": [],
            "stage_candidate_count": 0,
            "stage_ready_count": 0,
            "all_final_actions_blocked_without_human": True,
        }
    summary = board.get("summary", {})
    stage_lanes = []
    for lane in board.get("stage_now", []):
        if not isinstance(lane, dict):
            continue
        today_work = lane.get("today_work", [])
        stage_lanes.append(
            {
                "opportunity_number": lane.get("opportunity_number"),
                "title": lane.get("title"),
                "deadline_date": lane.get("deadline_date"),
                "deadline_utc": lane.get("deadline_utc"),
                "command": lane.get("command"),
                "first_safe_action": (
                    today_work[0]
                    if isinstance(today_work, list) and today_work
                    else "Reverify the current official source before action."
                ),
                "submission_ready": lane.get("submission_ready") is True,
                "human_gate_count": len(lane.get("human_gate", [])),
            }
        )
    return {
        "available": True,
        "status": "CURRENT_COMMAND_BOARD_OVERLAY_APPLIED",
        "source_path": display_path(CURRENT_COMMAND_BOARD_JSON),
        "source_generated_utc": board.get("generated_utc"),
        "source_sha256": board.get("command_board_sha256"),
        "lane_count": summary.get("lane_count", 0),
        "stage_candidate_count": summary.get("stage_candidate_count", 0),
        "stage_ready_count": summary.get("stage_ready_count", 0),
        "stage_lanes": stage_lanes,
        "all_final_actions_blocked_without_human": (
            summary.get("all_final_actions_blocked_without_human") is True
        ),
    }


def current_action_order(overlay: dict[str, Any]) -> list[str]:
    if overlay.get("available") is not True:
        return [
            "Rebuild and verify the current near-deadline command board before any portal or package action.",
            "Do not use the historical June deadline extracts as current action authority.",
        ]
    actions = [
        (
            f"{lane['opportunity_number']}: {lane['first_safe_action']} "
            f"Current command `{lane['command']}`; submission-ready `{lane['submission_ready']}`."
        )
        for lane in overlay.get("stage_lanes", [])
    ]
    actions.append(
        "Stop at the complete human-review gate. No workspace creation, upload, "
        "certification, signature, payment, or final submission is authorized by this board."
    )
    return actions


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def parse_eastern_due(text: str, label: str) -> dict[str, Any]:
    pattern = re.compile(
        rf"{re.escape(label)}:\s+([A-Za-z]+\s+\d{{1,2}},\s+\d{{4}})\s+at\s+(\d{{1,2}}:\d{{2}}\s+[AP]M)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return {
            "label": label,
            "found": False,
            "source_text": "",
            "eastern_iso": "",
            "central_iso": "",
            "utc_iso": "",
        }
    dt = datetime.strptime(f"{match.group(1)} {match.group(2)}", "%B %d, %Y %I:%M %p").replace(tzinfo=EASTERN)
    return {
        "label": label,
        "found": True,
        "source_text": match.group(0),
        "eastern_iso": dt.isoformat(),
        "central_iso": dt.astimezone(CENTRAL).isoformat(),
        "utc_iso": dt.astimezone(timezone.utc).isoformat(),
    }


def dice_deadlines() -> dict[str, Any]:
    text = DICE_DEADLINE_EXTRACT.read_text(encoding="utf-8", errors="ignore") if DICE_DEADLINE_EXTRACT.exists() else ""
    closure = official_dice_closure()
    return {
        "opportunity": "DARPA DICE",
        "funding_opportunity_number": "HR001126S0010",
        "official_source_url": DICE_OFFICIAL_SOURCE,
        "local_extract": str(DICE_DEADLINE_EXTRACT.relative_to(ROOT)).replace("\\", "/") if DICE_DEADLINE_EXTRACT.exists() else "",
        "all_times": "Eastern Time Zone (ET)",
        "posting_date": parse_eastern_due(text, "Posting Date") if "Posting Date" in text else {
            "label": "Posting Date",
            "found": True,
            "source_text": "Posting Date: June 10, 2026",
            "eastern_iso": "2026-06-10T00:00:00-04:00",
            "central_iso": "2026-06-09T23:00:00-05:00",
            "utc_iso": "2026-06-10T04:00:00+00:00",
        },
        "abstract_due": parse_eastern_due(text, "Proposal Abstract Due Date"),
        "question_submittal_closed": parse_eastern_due(text, "Question Submittal Closed"),
        "proposal_due": parse_eastern_due(text, "Proposal Due Date"),
        "submission_channel": "DARPA BAAT",
        "channel_boundary": "The extract says abstracts must be submitted to BAAT and other channels/late submissions will not be accepted.",
        "historical_deadline_record_only": True,
        "current_route_status": closure["status"],
        "current_status_received_utc": closure["source_received_utc"],
        "full_proposal_allowed": closure["full_proposal_allowed"],
        "reply_required": closure["reply_required"],
        "do_not_duplicate": closure["do_not_duplicate"],
        "immediate_action": closure["safest_next_action"],
    }


def flatten_dsip_topics(payload: dict[str, Any]) -> list[dict[str, Any]]:
    topics: list[dict[str, Any]] = []
    for query_key, block in payload.items():
        if not isinstance(block, dict):
            continue
        for row in block.get("data", []) or []:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            item["query_key"] = query_key
            topics.append(item)
    return topics


def dsip_topics() -> dict[str, Any]:
    payload = read_json(DSIP_TOPICS_JSON)
    all_topics = flatten_dsip_topics(payload)
    by_code = {str(row.get("topicCode", "")): row for row in all_topics if row.get("topicCode")}
    selected = []
    for package, topic_code in PACKAGE_TOPIC_CODES.items():
        row = by_code.get(topic_code, {})
        selected.append(
            {
                "package": package,
                "topic_code": topic_code,
                "found": bool(row),
                "topic_title": row.get("topicTitle", ""),
                "component": row.get("component", ""),
                "program": row.get("program", ""),
                "solicitation_number": row.get("solicitationNumber", ""),
                "topic_status": row.get("topicStatus", ""),
                "cmmc_level": row.get("cmmcLevel", ""),
                "topic_qa_start_utc": row.get("topicQAStartDate_iso", ""),
                "tpoc_qa_end_utc": row.get("topicQATpocEndDate_iso", ""),
                "public_qa_end_utc": row.get("topicQAEndDate_iso", ""),
                "proposal_due_utc": row.get("proposalDueDate_iso", ""),
                "details_url": row.get("details_url", ""),
                "source_search_url": row.get("url", "") or payload.get(row.get("query_key", ""), {}).get("url", ""),
                "portal_action": (
                    "Because this topic is pre-release in the public feed, confirm proposal-window dates and forms "
                    "inside the authenticated DSIP portal before treating it as submit-ready."
                ),
            }
        )
    watchlist = []
    for row in all_topics:
        code = str(row.get("topicCode", ""))
        if row.get("topicStatus") == "Pre-Release" and code not in PACKAGE_TOPIC_CODES.values():
            watchlist.append(
                {
                    "topic_code": code,
                    "topic_title": row.get("topicTitle", ""),
                    "component": row.get("component", ""),
                    "program": row.get("program", ""),
                    "cmmc_level": row.get("cmmcLevel", ""),
                    "tpoc_qa_end_utc": row.get("topicQATpocEndDate_iso", ""),
                    "details_url": row.get("details_url", ""),
                }
            )
    return {
        "official_source_url": DSIP_SEARCH_SOURCE,
        "local_capture": str(DSIP_TOPICS_JSON.relative_to(ROOT)).replace("\\", "/") if DSIP_TOPICS_JSON.exists() else "",
        "selected_topics": selected,
        "near_term_window": "Historical capture: TPOC Q&A closed June 24, 2026 at 12:00 UTC for the selected pre-release topics.",
        "proposal_window_boundary": "The captured topic rows are historical and do not authorize reopening an expired DSIP workspace; use a fresh official topic source for any new cycle.",
        "watchlist_pre_release_topics": watchlist,
    }


def package_summary(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for pkg in readiness.get("packages", []) or []:
        if not isinstance(pkg, dict):
            continue
        required = pkg.get("required_artifacts", []) if isinstance(pkg.get("required_artifacts"), list) else []
        manifests = pkg.get("evidence_manifests", []) if isinstance(pkg.get("evidence_manifests"), list) else []
        render = pkg.get("render", {}) if isinstance(pkg.get("render"), dict) else {}
        rows.append(
            {
                "package": pkg.get("name", ""),
                "portal": pkg.get("portal", ""),
                "readiness": pkg.get("readiness", ""),
                "required_artifacts_present": sum(1 for item in required if isinstance(item, dict) and item.get("exists")),
                "required_artifacts_total": len(required),
                "manifest_matched": sum(int(item.get("matched", 0) or 0) for item in manifests if isinstance(item, dict)),
                "manifest_expected": sum(int(item.get("expected", 0) or 0) for item in manifests if isinstance(item, dict)),
                "render_ok": render.get("ok") if render else None,
                "local_blockers": len(pkg.get("local_blockers", []) or []),
                "portal_user_blockers": len(pkg.get("portal_user_blockers", []) or []),
                "verified_portal_facts": pkg.get("verified_portal_facts", []) or [],
                "portal_user_blocker_examples": (pkg.get("portal_user_blockers", []) or [])[:4],
            }
        )
    return rows


def geometry_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    return {
        "family_count": summary.get("family_count", 0),
        "generated_lane_benchmark_count": summary.get("generated_lane_benchmark_count", 0),
        "proof_champion_lane": summary.get("proof_champion_lane", ""),
        "proof_champion_family": summary.get("proof_champion_family", ""),
        "generated_champion_lane": summary.get("generated_champion_lane", ""),
        "generated_champion_family": summary.get("generated_champion_family", ""),
        "generated_champion_score_delta_vs_best_baseline": summary.get("generated_champion_score_delta_vs_best_baseline", 0),
        "claim_gate_passed": bool(summary.get("claim_gate_passed", False)),
        "kraken_live_execution_allowed": bool(summary.get("kraken_live_execution_allowed", False)),
        "boundary": (
            "Use as bounded proof-building support for reviewers. Do not present generated geometry winners as "
            "field validation, safety validation, or dollar-value proof."
        ),
    }


def live_proof_submission_gate(
    payload: dict[str, Any], *, dice_closed: bool = False
) -> dict[str, Any]:
    if not payload:
        return {
            "available": False,
            "active_start_package": "",
            "closest_action_gate_utc": "",
            "proposal_specific_live_proof_count": 0,
            "proposal_specific_live_proof_total": 0,
            "packages_with_live_proof": [],
            "packages_missing_live_proof": [],
            "ready_for_any_final_submit": False,
            "rule": "No top-five live-proof board is available.",
        }
    gate = payload.get("global_live_proof_gate", {})
    if not isinstance(gate, dict):
        gate = {}
    active = payload.get("active_start_package", {})
    if not isinstance(active, dict):
        active = {}
    action = payload.get("closest_action_gate", {})
    if not isinstance(action, dict):
        action = {}
    result = {
        "available": True,
        "active_start_package": str(active.get("package", "")),
        "active_start_deadline_utc": str(active.get("abstract_due_utc", "")),
        "closest_action_gate_portal": str(action.get("portal", "")),
        "closest_action_gate_utc": str(action.get("deadline_utc", "")),
        "proposal_specific_live_proof_count": int(gate.get("proposal_specific_live_proof_count", 0) or 0),
        "proposal_specific_live_proof_total": int(gate.get("proposal_specific_live_proof_total", 0) or 0),
        "packages_with_live_proof": gate.get("packages_with_live_proof", []) or [],
        "packages_missing_live_proof": gate.get("packages_missing_live_proof", []) or [],
        "ready_for_any_final_submit": bool(gate.get("ready_for_any_final_submit", False)),
        "rule": str(gate.get("rule", "")),
    }
    if dice_closed:
        result.update(
            {
                "status": "HISTORICAL_ACTIVE_START_SUPERSEDED_BY_OFFICIAL_CLOSURE",
                "legacy_active_start_package": result["active_start_package"],
                "legacy_active_start_deadline_utc": result[
                    "active_start_deadline_utc"
                ],
                "active_start_package": "",
                "active_start_deadline_utc": "",
                "closest_action_gate_portal": "",
                "closest_action_gate_utc": "",
                "ready_for_any_final_submit": False,
                "rule": (
                    "The historical top-five proof board is retained for provenance only. "
                    "Official DICE feedback closed the full-proposal route, and the captured "
                    "DSIP gates have elapsed; use the current near-deadline command board."
                ),
            }
        )
    return result


def discarded_workspaces(payload: dict[str, Any]) -> list[dict[str, str]]:
    rows = payload.get("discarded_workspaces", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return []
    return [
        {
            "workspace_id": str(row.get("workspace_id", "")),
            "opportunity": str(row.get("opportunity", "")),
            "status": str(row.get("status", "")),
            "reason": str(row.get("reason", "")),
            "boundary": str(row.get("destructive_action_boundary", "")),
        }
        for row in rows
        if isinstance(row, dict)
    ]


def build_board() -> dict[str, Any]:
    readiness = read_json(READINESS_JSON)
    geometry = read_json(GEOMETRY_BRIDGE_JSON)
    visibility = read_json(PUBLIC_VISIBILITY_JSON)
    live_proof = read_json(TOP5_LIVE_PROOF_JSON)
    overlay = current_command_board_overlay()
    dice = dice_deadlines()
    return {
        "generated_utc": now_utc(),
        "schema": "grant_deadline_triage_board_v1",
        "purpose": (
            "Preserve historical deadline evidence while routing every current action "
            "through the fail-closed near-deadline command board."
        ),
        "readiness_source": str(READINESS_JSON.relative_to(ROOT)).replace("\\", "/"),
        "source_posture": overlay["status"],
        "legacy_source_posture": readiness.get("posture", "UNKNOWN"),
        "readiness_summary": readiness.get("summary", {}),
        "current_command_board": overlay,
        "official_deadlines": {
            "dice": dice,
            "dsip": dsip_topics(),
        },
        "package_readiness": package_summary(readiness),
        "portal_sequence": PORTAL_ORDER,
        "evidence_to_use": {
            "public_visibility_packet_available": bool(visibility),
            "public_visibility_packet_claims": len(visibility.get("proof_claims", []) or []),
            "geometry_championship": geometry_summary(geometry),
        },
        "live_proof_submission_gate": live_proof_submission_gate(
            live_proof,
            dice_closed=(
                dice["current_route_status"]
                == "FULL_PROPOSAL_DISCOURAGED_ROUTE_CLOSED"
            ),
        ),
        "discarded_workspaces": discarded_workspaces(live_proof),
        "tonight_action_order": current_action_order(overlay),
        "safety_boundaries": SAFETY_BOUNDARIES,
        "submit_gate": {
            "ready_for_submit": False,
            "why": (
                "The current command board reports zero submission-ready lanes. "
                "Applicant authority, eligibility, package, preview, certification, and "
                "action-time approval gates remain open."
            ),
            "required_user_phrase": "I approve this exact upload/submit action now.",
        },
    }


def render_markdown(board: dict[str, Any]) -> str:
    dice = board["official_deadlines"]["dice"]
    dsip = board["official_deadlines"]["dsip"]
    geometry = board["evidence_to_use"]["geometry_championship"]
    live_gate = board.get("live_proof_submission_gate", {})
    summary = board.get("readiness_summary", {})
    overlay = board.get("current_command_board", {})
    active_start_package = str(live_gate.get("active_start_package", "")).strip() or "N/A"
    active_start_deadline = str(live_gate.get("active_start_deadline_utc", "")).strip() or "N/A"
    closest_action_portal = str(live_gate.get("closest_action_gate_portal", "")).strip() or "N/A"
    closest_action_deadline = str(live_gate.get("closest_action_gate_utc", "")).strip() or "N/A"
    lines = [
        "# Grant Deadline Triage Board",
        "",
        f"Generated UTC: {board['generated_utc']}",
        "",
        f"Source posture: `{board.get('source_posture', 'UNKNOWN')}`",
        "",
        "## Executive Read",
        "",
        "- DICE is not a Grants.gov submit path, and official feedback discouraged a full proposal; the route is closed with no reply or BAAT action due.",
        "- The listed DSIP rows and June deadlines are historical evidence only; do not reopen an expired workspace.",
        f"- The current command board tracks {overlay.get('lane_count', 0)} lanes, {overlay.get('stage_candidate_count', 0)} staging candidates, and {overlay.get('stage_ready_count', 0)} submission-ready lanes.",
        "- We can use the proof packets to strengthen reviewer confidence, but we cannot turn them into field, dollar, compliance, or award-guarantee claims.",
        "",
        "## Current Counts",
        "",
        f"- Packages tracked: {summary.get('packages', 0)}",
        f"- Local blockers: {summary.get('local_blockers', 0)}",
        f"- Portal/user blockers: {summary.get('portal_user_blockers', 0)}",
        f"- Current overlay: `{overlay.get('status', 'UNKNOWN')}`",
        f"- Current command-board source: `{overlay.get('source_path', '')}`",
        "",
        "## Official Deadlines",
        "",
        "### DICE / HR001126S0010",
        "",
        f"- Source: `{dice['official_source_url']}`",
        f"- Timescale: {dice['all_times']}",
        f"- Abstract due: {dice['abstract_due']['source_text']} ({dice['abstract_due']['central_iso']} Central / {dice['abstract_due']['utc_iso']} UTC)",
        f"- Full proposal due: {dice['proposal_due']['source_text']} ({dice['proposal_due']['central_iso']} Central / {dice['proposal_due']['utc_iso']} UTC)",
        f"- Submission channel: {dice['submission_channel']}",
        f"- Historical deadline record only: `{dice['historical_deadline_record_only']}`",
        f"- Current route status: `{dice['current_route_status']}`",
        f"- Full proposal allowed: `{dice['full_proposal_allowed']}`",
        f"- Boundary: {dice['channel_boundary']}",
        f"- Immediate action: {dice['immediate_action']}",
        "",
        "### DSIP Selected Topics",
        "",
        f"- Source: `{dsip['official_source_url']}`",
        f"- Near-term window: {dsip['near_term_window']}",
        f"- Boundary: {dsip['proposal_window_boundary']}",
        "",
    ]
    for row in dsip["selected_topics"]:
        lines.extend(
            [
                f"- {row['package']} / `{row['topic_code']}`: {row['topic_title']}",
                f"  - Status: {row['topic_status']} | Component: {row['component']} | Program: {row['program']} | CMMC: {row['cmmc_level']}",
                f"  - TPOC Q&A closes: {row['tpoc_qa_end_utc'] or 'not published in capture'}",
                f"  - Public Q&A closes: {row['public_qa_end_utc'] or 'not published in capture'}",
                f"  - Proposal due: {row['proposal_due_utc'] or 'blank in public pre-release capture; verify in authenticated DSIP'}",
                f"  - Details: `{row['details_url']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Portal Sequence",
            "",
        ]
    )
    for item in board["portal_sequence"]:
        lines.extend(
            [
                f"### {item['portal']}",
                "",
                f"- Why it matters: {item['why']}",
                f"- Current state: {item['user_state']}",
                "- Capture next:",
            ]
        )
        lines.extend(f"  - {capture}" for capture in item["capture"])
        lines.append("")
    lines.extend(
        [
            "## Package Readiness",
            "",
        ]
    )
    for pkg in board["package_readiness"]:
        lines.extend(
            [
                f"### {pkg['package']} ({pkg['portal']})",
                "",
                f"- Readiness: `{pkg['readiness']}`",
                f"- Required artifacts: {pkg['required_artifacts_present']}/{pkg['required_artifacts_total']}",
                f"- Evidence manifest matches: {pkg['manifest_matched']}/{pkg['manifest_expected']}",
                f"- Render QA: {pkg['render_ok']}",
                f"- Local blockers: {pkg['local_blockers']}",
                f"- Portal/user blockers: {pkg['portal_user_blockers']}",
            ]
        )
        if pkg["verified_portal_facts"]:
            lines.append("- Verified facts:")
            lines.extend(f"  - {fact}" for fact in pkg["verified_portal_facts"])
        if pkg["portal_user_blocker_examples"]:
            lines.append("- First portal/user blockers:")
            lines.extend(f"  - {item}" for item in pkg["portal_user_blocker_examples"])
        lines.append("")
    lines.extend(
        [
            "## Evidence To Use",
            "",
            f"- Public visibility packet available: {board['evidence_to_use']['public_visibility_packet_available']}",
            f"- Public visibility proof claims: {board['evidence_to_use']['public_visibility_packet_claims']}",
            f"- Geometry families tracked: {geometry['family_count']}",
            f"- Generated benchmark lanes: {geometry['generated_lane_benchmark_count']}",
            f"- Proof-build champion: {geometry['proof_champion_lane']} / {geometry['proof_champion_family']}",
            f"- Generated-lane champion: {geometry['generated_champion_lane']} / {geometry['generated_champion_family']} (score delta {geometry['generated_champion_score_delta_vs_best_baseline']})",
            f"- Geometry boundary: {geometry['boundary']}",
            "",
            "## Live-Proof Submission Gate",
            "",
            f"- Available: {live_gate.get('available', False)}",
            f"- Status: `{live_gate.get('status', 'CURRENT')}`",
            f"- Active start package: {active_start_package}",
            f"- Legacy active start package: {live_gate.get('legacy_active_start_package', '')}",
            f"- Active start deadline UTC: {active_start_deadline}",
            f"- Closest action gate: {closest_action_portal} / {closest_action_deadline}",
            f"- Proposal-specific live proof: {live_gate.get('proposal_specific_live_proof_count', 0)}/{live_gate.get('proposal_specific_live_proof_total', 0)}",
            f"- Missing live proof: {', '.join(live_gate.get('packages_missing_live_proof', []) or []) or 'none'}",
            f"- Ready for any final submit: `{live_gate.get('ready_for_any_final_submit', False)}`",
            f"- Rule: {live_gate.get('rule', '')}",
            "",
            "## Discarded Workspaces",
            "",
        ]
    )
    if board.get("discarded_workspaces"):
        for row in board["discarded_workspaces"]:
            lines.extend(
                [
                    f"- `{row['opportunity']}` / `{row['workspace_id']}`: `{row['status']}`",
                    f"  - Reason: {row['reason']}",
                    f"  - Boundary: {row['boundary']}",
                ]
            )
    else:
        lines.append("- None recorded.")
    lines.extend(
        [
            "",
            "## Current Action Order",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in board["tonight_action_order"])
    lines.extend(
        [
            "",
            "## Safety Boundaries",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in board["safety_boundaries"])
    lines.extend(
        [
            "",
            "## Submit Gate",
            "",
            f"- Ready for submit: `{board['submit_gate']['ready_for_submit']}`",
            f"- Why: {board['submit_gate']['why']}",
            f"- Required user phrase at action time: `{board['submit_gate']['required_user_phrase']}`",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    board = build_board()
    write_json(OUT_JSON, board)
    write_json(DASHBOARD_JSON, board)
    write_text(OUT_MD, render_markdown(board))
    print(
        json.dumps(
            {
                "schema": board["schema"],
                "source_posture": board["source_posture"],
                "local_blockers": board.get("readiness_summary", {}).get("local_blockers", 0),
                "portal_user_blockers": board.get("readiness_summary", {}).get("portal_user_blockers", 0),
                "dice_current_route_status": board["official_deadlines"]["dice"][
                    "current_route_status"
                ],
                "dice_historical_abstract_due_utc": board["official_deadlines"][
                    "dice"
                ]["abstract_due"]["utc_iso"],
                "current_stage_candidates": board["current_command_board"][
                    "stage_candidate_count"
                ],
                "current_stage_ready": board["current_command_board"][
                    "stage_ready_count"
                ],
                "dsip_selected_topics": len(board["official_deadlines"]["dsip"]["selected_topics"]),
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "dashboard": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
