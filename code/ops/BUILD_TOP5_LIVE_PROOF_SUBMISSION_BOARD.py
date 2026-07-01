from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "ops"
GRANTS = ROOT / "grant_submissions"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

READINESS_JSON = OUT / "grant_submission_readiness_audit_latest.json"
DEADLINE_TRIAGE_JSON = OUT / "grant_deadline_triage_latest.json"
DICE_LIVE_REPLAY_JSON = OUT / "dice_live_breadth_replay_latest.json"
HARBOR_INJECTION_JSON = OUT / "harbor_ais_injection_benchmark_latest.json"
HARBOR_REVIEW_BURDEN_JSON = OUT / "harbor_ais_review_burden_profile_latest.json"
GEOMETRY_BRIDGE_JSON = OUT / "geometry_championship_bridge_latest.json"

OUT_JSON = OUT / "top5_live_proof_submission_board_latest.json"
OUT_MD = GRANTS / "TOP5_LIVE_PROOF_SUBMISSION_BOARD_2026-06-22.md"
DASHBOARD_JSON = DASHBOARD_DATA / "top5_live_proof_submission_board.json"

ACTION_TIME_APPROVAL = "I approve this exact upload/submit action now."

PACKAGE_META = {
    "DICE": {
        "rank": 1,
        "portal": "DARPA BAAT",
        "opportunity": "HR001126S0010",
        "title": "DARPA DICE abstract",
        "deadline_type": "actual_submission_deadline",
        "primary_deadline_utc": "2026-06-30T18:00:00+00:00",
        "primary_deadline_label": "DICE abstract due June 30, 2026 at 2:00 PM ET / 1:00 PM CT",
        "external_source_url": "https://files.simpler.grants.gov/opportunities/56b71085-ed91-4468-b7eb-3a04bf840794/attachments/428dc8ae-7fec-4e5f-a82f-0ccc24dfcc26/HR001126S0010.pdf",
        "external_source_note": "Grants.gov-hosted BAA PDF shows DICE abstract due June 30, 2026 at 2:00 PM ET and full proposal due August 25, 2026 at 2:00 PM ET.",
        "next_action": "Open BAAT, confirm organization association, DICE visibility, attachment rules, and preview behavior.",
        "proof_needed_next": "Keep DICE live-breadth replay bounded; do not claim DICE metric attainment or field validation.",
    },
    "HarborSentinel": {
        "rank": 2,
        "portal": "DSIP",
        "opportunity": "DON26BZ03-NV063",
        "title": "Anomalous Behavior Detection and Alerting for Congested Maritime Environments",
        "deadline_type": "nearest_action_gate",
        "primary_deadline_utc": "2026-06-24T12:00:00+00:00",
        "primary_deadline_label": "DSIP TPOC Q&A closes June 24, 2026 at 12:00 UTC; proposal due must be verified in DSIP.",
        "external_source_url": "https://www.sbir.gov/topics/12759",
        "external_source_note": "SBIR.gov copy shows open date June 24, 2026 and due/close date July 22, 2026; page says agency server is controlling.",
        "next_action": "Open DSIP, capture topic workspace/forms, proposal window, CMMC language, and any safe TPOC Q&A path.",
        "proof_needed_next": "Preserve public AIS controlled-injection boundaries; do not claim real threat labels or field performance.",
    },
    "NSF Project Pitch": {
        "rank": 3,
        "portal": "NSF Seed Fund Project Pitch portal",
        "opportunity": "NSF Project Pitch",
        "title": "LumenCore Project Pitch",
        "deadline_type": "rolling_or_portal_state",
        "primary_deadline_utc": "",
        "primary_deadline_label": "No fixed near-term official deadline captured locally; verify duplicate/open pitch state in NSF portal.",
        "external_source_url": "",
        "external_source_note": "No current fixed NSF pitch deadline was verified in this pass.",
        "next_action": "Create proposal-specific live proof from a bounded public workflow, customer-discovery, or reproducible market need lane before final submit.",
        "proof_needed_next": "Add proposal-specific live/public evidence beyond draft text and SAM status.",
    },
    "MissionWeave": {
        "rank": 4,
        "portal": "DSIP",
        "opportunity": "DLA26BZ03-NV011",
        "title": "Digital Twin of the Organization for Enhanced Mission Readiness",
        "deadline_type": "nearest_action_gate",
        "primary_deadline_utc": "2026-06-24T12:00:00+00:00",
        "primary_deadline_label": "DSIP TPOC Q&A closes June 24, 2026 at 12:00 UTC; proposal due must be verified in DSIP.",
        "external_source_url": "https://www.sbir.gov/topics/12778",
        "external_source_note": "SBIR.gov copy shows open date June 24, 2026 and due/close date July 22, 2026; page says agency server is controlling.",
        "next_action": "Open DSIP, capture topic workspace/forms and convert the draft into a representative process replay plan.",
        "proof_needed_next": "Run a representative organizational-process replay on frozen public or user-approved data.",
    },
    "NV065": {
        "rank": 5,
        "portal": "DSIP",
        "opportunity": "DON26BZ03-NV065",
        "title": "Adaptive Sensor Management",
        "deadline_type": "nearest_action_gate",
        "primary_deadline_utc": "2026-06-24T12:00:00+00:00",
        "primary_deadline_label": "DSIP TPOC Q&A closes June 24, 2026 at 12:00 UTC; proposal due must be verified in DSIP.",
        "external_source_url": "https://www.sbir.gov/topics/12761",
        "external_source_note": "SBIR.gov copy shows open date June 24, 2026 and due/close date July 22, 2026; page says agency server is controlling.",
        "next_action": "Open DSIP, capture topic workspace/forms and build a live or representative sensor-tasking replay lane.",
        "proof_needed_next": "Run lane-specific live/representative sensor scheduling data against baselines before final submit.",
    },
}


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def package_lookup(readiness: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = readiness.get("packages", [])
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("name")): row
        for row in rows
        if isinstance(row, dict) and row.get("name")
    }


def artifact_counts(pkg: dict[str, Any]) -> dict[str, Any]:
    required = pkg.get("required_artifacts", []) if isinstance(pkg.get("required_artifacts"), list) else []
    manifests = pkg.get("evidence_manifests", []) if isinstance(pkg.get("evidence_manifests"), list) else []
    render = pkg.get("render", {}) if isinstance(pkg.get("render"), dict) else {}
    return {
        "required_artifacts_present": sum(1 for row in required if isinstance(row, dict) and row.get("exists")),
        "required_artifacts_total": len(required),
        "manifest_matched": sum(int(row.get("matched", 0) or 0) for row in manifests if isinstance(row, dict)),
        "manifest_expected": sum(int(row.get("expected", 0) or 0) for row in manifests if isinstance(row, dict)),
        "render_ok": render.get("ok") if render else None,
    }


def dice_live_proof(dice: dict[str, Any]) -> dict[str, Any]:
    sources = dice.get("source_manifest", {}).get("sources", [])
    paired = dice.get("paired_metrics", {}) if isinstance(dice.get("paired_metrics"), dict) else {}
    claim_gate = dice.get("claim_gate", {}) if isinstance(dice.get("claim_gate"), dict) else {}
    has_live_rows = (
        dice.get("primary_evidence_source") == "frozen_live_pulled_rows"
        and isinstance(sources, list)
        and len(sources) > 0
    )
    return {
        "proposal_specific_live_proof": bool(has_live_rows),
        "proof_status": "PASS_BOUNDED_LIVE_PROOF_BUT_SUBMIT_BLOCKED" if has_live_rows else "BLOCKED_MISSING_LIVE_REPLAY",
        "live_proof_mode": str(dice.get("evidence_mode", "")),
        "primary_evidence_source": str(dice.get("primary_evidence_source", "")),
        "source_count": len(sources) if isinstance(sources, list) else 0,
        "scenario_count": dice.get("configuration", {}).get("scenario_count"),
        "evidence": [
            f"{len(sources)} live-pulled or previously live-fetched source files frozen for replay.",
            f"{dice.get('configuration', {}).get('scenario_count')} deterministic replay windows.",
            f"Safe-completion mean delta {paired.get('safe_completion_rate', {}).get('mean_delta')}.",
            f"Constraint-violation mean delta {paired.get('constraint_violation_rate', {}).get('mean_delta')}.",
            f"Messages-per-safe-completion mean delta {paired.get('messages_per_safe_completion', {}).get('mean_delta')}.",
        ],
        "claim_boundary": str(dice.get("evidence_boundary", "")),
        "ready_for_portal_upload": bool(claim_gate.get("ready_for_portal_upload", False)),
        "ready_for_submit": bool(claim_gate.get("ready_for_submit", False)),
        "blocked_claims": {
            "live_replay_proves_dice_metric_attainment": bool(claim_gate.get("live_replay_proves_dice_metric_attainment", False)),
            "live_replay_proves_operational_performance": bool(claim_gate.get("live_replay_proves_operational_performance", False)),
            "live_replay_proves_trading_profit": bool(claim_gate.get("live_replay_proves_trading_profit", False)),
        },
    }


def harbor_live_proof(injection: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    result = injection.get("controlled_injection_benchmark", {})
    if not isinstance(result, dict):
        result = {}
    review_queue = review.get("review_queue", {}) if isinstance(review.get("review_queue"), dict) else {}
    claim_gate = review.get("claim_gate", {}) if isinstance(review.get("claim_gate"), dict) else {}
    has_public_ais = injection.get("posture") == "PUBLIC_AIS_INJECTION_BENCHMARK_READY"
    source = injection.get("raw_source", {}) if isinstance(injection.get("raw_source"), dict) else {}
    return {
        "proposal_specific_live_proof": bool(has_public_ais),
        "proof_status": "PASS_BOUNDED_PUBLIC_DATA_PROOF_BUT_SUBMIT_BLOCKED" if has_public_ais else "BLOCKED_MISSING_PUBLIC_AIS_BENCHMARK",
        "live_proof_mode": "public_noaa_ais_heldout_split_controlled_injection",
        "primary_evidence_source": "NOAA public AIS raw file, hashed held-out splits, controlled validation injections",
        "source_count": 1 if source.get("source_url") else 0,
        "scenario_count": result.get("total_injected_segments", 0),
        "evidence": [
            f"NOAA AIS raw source hashed: {source.get('sha256', '')}.",
            f"{result.get('total_injected_segments', 0)} controlled injected validation segments.",
            f"Motion-consistency recall {result.get('motion_consistency_recall')} vs speed-only baseline {result.get('speed_only_baseline_recall')}.",
            f"Recall lift vs speed-only {result.get('recall_lift_vs_speed_only')}.",
            f"Held-out validation candidate queue: {review_queue.get('validation_candidates')} candidates across {review_queue.get('validation_hours')} hours.",
        ],
        "claim_boundary": " ".join(
            item
            for item in [
                str(injection.get("claim_boundary", "")),
                str(review.get("claim_boundary", "")),
            ]
            if item
        ),
        "ready_for_portal_upload": bool(claim_gate.get("ready_for_portal_upload", False)),
        "ready_for_submit": bool(claim_gate.get("ready_for_submit", False)),
        "blocked_claims": {
            "measures_false_positive_rate": bool(claim_gate.get("measures_false_positive_rate", False)),
            "proves_field_performance": bool(claim_gate.get("proves_field_performance", False)),
            "proves_operational_suitability": bool(claim_gate.get("proves_operational_suitability", False)),
        },
    }


def missing_live_proof(package: str) -> dict[str, Any]:
    meta = PACKAGE_META[package]
    return {
        "proposal_specific_live_proof": False,
        "proof_status": "BLOCKED_MISSING_PROPOSAL_SPECIFIC_LIVE_PROOF",
        "live_proof_mode": "local_draft_or_synthetic_evidence_only",
        "primary_evidence_source": "",
        "source_count": 0,
        "scenario_count": 0,
        "evidence": [
            "Local package artifacts exist, but no proposal-specific live/public data replay or held-out benchmark is recorded for this package.",
            meta["proof_needed_next"],
        ],
        "claim_boundary": (
            "Do not final-submit this package as evidence-backed until its exact proposal has a frozen input manifest, "
            "baseline comparison, leakage controls, and proposal-specific live or representative data proof."
        ),
        "ready_for_portal_upload": False,
        "ready_for_submit": False,
        "blocked_claims": {
            "proposal_specific_live_proof": False,
            "field_validation": False,
            "real_dollar_claim": False,
        },
    }


def live_proof_for(package: str, dice: dict[str, Any], injection: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    if package == "DICE":
        return dice_live_proof(dice)
    if package == "HarborSentinel":
        return harbor_live_proof(injection, review)
    return missing_live_proof(package)


def package_row(
    name: str,
    pkg: dict[str, Any],
    dice: dict[str, Any],
    injection: dict[str, Any],
    review: dict[str, Any],
) -> dict[str, Any]:
    meta = PACKAGE_META[name]
    live = live_proof_for(name, dice, injection, review)
    local_blockers = pkg.get("local_blockers", []) if isinstance(pkg.get("local_blockers"), list) else []
    portal_user_blockers = pkg.get("portal_user_blockers", []) if isinstance(pkg.get("portal_user_blockers"), list) else []
    return {
        "rank": meta["rank"],
        "package": name,
        "portal": str(pkg.get("portal") or meta["portal"]),
        "opportunity": meta["opportunity"],
        "title": meta["title"],
        "readiness": str(pkg.get("readiness", "UNKNOWN")),
        "deadline_type": meta["deadline_type"],
        "primary_deadline_utc": meta["primary_deadline_utc"],
        "primary_deadline_label": meta["primary_deadline_label"],
        "external_source_url": meta["external_source_url"],
        "external_source_note": meta["external_source_note"],
        "artifact_counts": artifact_counts(pkg),
        "local_blockers": len(local_blockers),
        "portal_user_blockers": len(portal_user_blockers),
        "next_action": meta["next_action"],
        "live_proof": live,
        "ready_for_final_submit": False,
        "final_submit_blocker": (
            "Final submit is blocked by policy until portal authority, compliance/cost facts, upload preview, "
            "fresh action-time approval, and proposal-specific live proof all pass."
        ),
    }


def geometry_gate(geometry: dict[str, Any]) -> dict[str, Any]:
    summary = geometry.get("summary", {}) if isinstance(geometry.get("summary"), dict) else {}
    return {
        "generated_lane_benchmark_count": int(summary.get("generated_lane_benchmark_count", 0) or 0),
        "live_breadth_backed_generated_lanes": int(summary.get("live_breadth_backed_generated_lanes", 0) or 0),
        "synthetic_only_generated_lanes": int(summary.get("synthetic_only_generated_lanes", 0) or 0),
        "ready_for_commit_push_as_live_benchmark": bool(summary.get("ready_for_commit_push_as_live_benchmark", False)),
        "kraken_live_execution_allowed": bool(summary.get("kraken_live_execution_allowed", False)),
        "boundary": (
            "Geometry generated lanes can support research direction only. They are not live-breadth proof until "
            "lane-specific frozen input manifests, replay windows, leakage controls, and baselines pass."
        ),
    }


def build_board() -> dict[str, Any]:
    readiness = read_json(READINESS_JSON)
    deadline = read_json(DEADLINE_TRIAGE_JSON)
    dice = read_json(DICE_LIVE_REPLAY_JSON)
    injection = read_json(HARBOR_INJECTION_JSON)
    review = read_json(HARBOR_REVIEW_BURDEN_JSON)
    geometry = read_json(GEOMETRY_BRIDGE_JSON)

    packages = package_lookup(readiness)
    rows = [
        package_row(name, packages.get(name, {}), dice, injection, review)
        for name in PACKAGE_META
    ]
    rows.sort(key=lambda row: row["rank"])

    live_pass = [row["package"] for row in rows if row["live_proof"]["proposal_specific_live_proof"]]
    missing_live = [row["package"] for row in rows if not row["live_proof"]["proposal_specific_live_proof"]]
    dsip_action = [
        row["package"]
        for row in rows
        if row["deadline_type"] == "nearest_action_gate"
        and row["primary_deadline_utc"] == "2026-06-24T12:00:00+00:00"
    ]

    return {
        "generated_utc": now_utc(),
        "schema": "top5_live_proof_submission_board_v1",
        "purpose": "Start the closest-deadline grant package while enforcing proposal-specific live-proof gates.",
        "source_posture": readiness.get("posture", "UNKNOWN"),
        "readiness_summary": readiness.get("summary", {}),
        "active_start_package": {
            "package": "DICE",
            "portal": "DARPA BAAT",
            "opportunity": "HR001126S0010",
            "reason": "Closest actual submission deadline and already has bounded proposal-specific live-pulled replay evidence.",
            "abstract_due_utc": "2026-06-30T18:00:00+00:00",
            "abstract_due_central": "2026-06-30T13:00:00-05:00",
            "next_action": PACKAGE_META["DICE"]["next_action"],
        },
        "closest_action_gate": {
            "portal": "DSIP",
            "action": "Capture selected topic workspaces, proposal-window dates, forms, and safe TPOC Q&A status.",
            "deadline_utc": "2026-06-24T12:00:00+00:00",
            "packages": dsip_action,
            "boundary": "This is an action cutoff, not a captured final proposal due date.",
        },
        "global_live_proof_gate": {
            "proposal_specific_live_proof_count": len(live_pass),
            "proposal_specific_live_proof_total": len(rows),
            "packages_with_live_proof": live_pass,
            "packages_missing_live_proof": missing_live,
            "all_five_have_proposal_specific_live_proof": len(missing_live) == 0,
            "ready_for_any_final_submit": False,
            "rule": "No final grant submit until the exact proposal has proposal-specific live proof and portal/compliance/action-time gates pass.",
            "required_user_phrase": ACTION_TIME_APPROVAL,
        },
        "packages": rows,
        "discarded_workspaces": [
            {
                "workspace_id": "WS01676964",
                "opportunity": "PDR-2600-DC-029Q",
                "package": "PKG00292984",
                "agency": "HUD",
                "title": "Mass Market Solutions for Leveraging Robotics and AI Technologies for Home Construction Demonstration",
                "status": "DISCARD_NO_SUBMIT",
                "reason": "Not part of the top-five funding path and appears to require housing/manufacturing/demo-site fit that is not currently verified.",
                "destructive_action_boundary": "Do not delete or withdraw this cloud workspace unless the user gives exact action-time confirmation.",
            }
        ],
        "geometry_live_breadth_gate": geometry_gate(geometry),
        "deadline_triage_source": str(DEADLINE_TRIAGE_JSON.relative_to(ROOT)).replace("\\", "/") if deadline else "",
        "source_files": {
            "readiness": "out/ops/grant_submission_readiness_audit_latest.json",
            "deadline_triage": "out/ops/grant_deadline_triage_latest.json",
            "dice_live_breadth_replay": "out/ops/dice_live_breadth_replay_latest.json",
            "harbor_ais_injection_benchmark": "out/ops/harbor_ais_injection_benchmark_latest.json",
            "harbor_ais_review_burden_profile": "out/ops/harbor_ais_review_burden_profile_latest.json",
            "geometry_championship_bridge": "out/ops/geometry_championship_bridge_latest.json",
        },
    }


def render_markdown(board: dict[str, Any]) -> str:
    gate = board["global_live_proof_gate"]
    active = board["active_start_package"]
    action = board["closest_action_gate"]
    lines = [
        "# Top 5 Live-Proof Submission Board",
        "",
        f"Generated UTC: {board['generated_utc']}",
        "",
        "## Start Here",
        "",
        f"- Active start package: **{active['package']} / `{active['opportunity']}`**",
        f"- Portal: {active['portal']}",
        f"- Why: {active['reason']}",
        f"- Abstract due: {active['abstract_due_utc']} UTC / {active['abstract_due_central']} Central",
        f"- Next action: {active['next_action']}",
        "",
        "## Closest Action Gate",
        "",
        f"- Portal: {action['portal']}",
        f"- Deadline: {action['deadline_utc']}",
        f"- Packages: {', '.join(action['packages'])}",
        f"- Boundary: {action['boundary']}",
        "",
        "## Live-Proof Gate",
        "",
        f"- Proposal-specific live proof: {gate['proposal_specific_live_proof_count']}/{gate['proposal_specific_live_proof_total']}",
        f"- Passing: {', '.join(gate['packages_with_live_proof']) or 'none'}",
        f"- Missing: {', '.join(gate['packages_missing_live_proof']) or 'none'}",
        f"- Ready for any final submit: `{gate['ready_for_any_final_submit']}`",
        f"- Rule: {gate['rule']}",
        "",
        "## Packages",
        "",
    ]
    for row in board["packages"]:
        proof = row["live_proof"]
        lines.extend(
            [
                f"### {row['rank']}. {row['package']} / `{row['opportunity']}`",
                "",
                f"- Portal: {row['portal']}",
                f"- Deadline type: {row['deadline_type']}",
                f"- Primary deadline: {row['primary_deadline_label']}",
                f"- External source: {row['external_source_url'] or 'not captured'}",
                f"- External source note: {row['external_source_note']}",
                f"- Readiness: `{row['readiness']}`",
                f"- Local blockers: {row['local_blockers']}",
                f"- Portal/user blockers: {row['portal_user_blockers']}",
                f"- Proposal-specific live proof: `{proof['proposal_specific_live_proof']}`",
                f"- Proof status: `{proof['proof_status']}`",
                f"- Evidence mode: {proof['live_proof_mode']}",
                f"- Ready for final submit: `{row['ready_for_final_submit']}`",
                "- Evidence:",
            ]
        )
        lines.extend(f"  - {item}" for item in proof["evidence"])
        lines.extend(
            [
                f"- Boundary: {proof['claim_boundary']}",
                f"- Next action: {row['next_action']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Discarded Workspaces",
            "",
        ]
    )
    for row in board["discarded_workspaces"]:
        lines.extend(
            [
                f"- `{row['opportunity']}` / workspace `{row['workspace_id']}`: `{row['status']}`",
                f"  - Title: {row['title']}",
                f"  - Reason: {row['reason']}",
                f"  - Boundary: {row['destructive_action_boundary']}",
            ]
        )
    geometry = board["geometry_live_breadth_gate"]
    lines.extend(
        [
            "",
            "## Geometry Boundary",
            "",
            f"- Generated lanes: {geometry['generated_lane_benchmark_count']}",
            f"- Live-breadth-backed generated lanes: {geometry['live_breadth_backed_generated_lanes']}",
            f"- Ready as live benchmark: `{geometry['ready_for_commit_push_as_live_benchmark']}`",
            f"- Kraken live execution allowed: `{geometry['kraken_live_execution_allowed']}`",
            f"- Boundary: {geometry['boundary']}",
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
                "active_start_package": board["active_start_package"]["package"],
                "closest_action_gate": board["closest_action_gate"]["deadline_utc"],
                "proposal_specific_live_proof": (
                    f"{board['global_live_proof_gate']['proposal_specific_live_proof_count']}/"
                    f"{board['global_live_proof_gate']['proposal_specific_live_proof_total']}"
                ),
                "ready_for_any_final_submit": board["global_live_proof_gate"]["ready_for_any_final_submit"],
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
