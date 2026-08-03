from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

CURRENT_PROOF = OUT_OPS / "current_luma_proof_state_latest.json"
CHAMPION = OUT_OPS / "geometry_champion_of_champions_latest.json"
MANIFEST = OUT_OPS / "data_room_manifest_latest.json"
SAM_SUBMISSION = OUT_OPS / "sam_submission_and_today_opportunity_push_latest.json"
WIRING_MATRIX = DASHBOARD_DATA / "geometry_live_wiring_matrix.json"
READY_REPLAY = DASHBOARD_DATA / "geometry_ready_source_replay.json"
LOCKED_SWEEP = DASHBOARD_DATA / "locked_source_baseline_replay_sweep.json"

OUT_JSON = OUT_OPS / "technical_gov_reviewer_approval_stack_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "technical_gov_reviewer_approval_stack.json"
OUT_MD = SPRINT_DIR / "TECHNICAL_GOV_REVIEWER_APPROVAL_STACK_2026-07-09.md"

SENSITIVE_MARKERS = [
    "password",
    "zoom.us",
    "meeting id",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "sk-",
    "xox",
]

OFFICIAL_DATA_SOURCES = [
    {
        "source_id": "faa_data_portal",
        "name": "FAA Data Portal",
        "official_url": "https://www.faa.gov/data",
        "reviewer_value": "Public FAA clearinghouse for datasets and APIs, including aviation and NAS-related data.",
        "luma_use": "Target aviation delay, routing, weather, and operational proof routes after source terms are reviewed.",
        "integration_posture": "public_source_watch",
    },
    {
        "source_id": "aviation_weather_center_api",
        "name": "Aviation Weather Center Data API",
        "official_url": "https://aviationweather.gov/data/api/",
        "reviewer_value": "Machine-to-machine aviation weather access with recent historical coverage.",
        "luma_use": "Use as a live measured source for turbulence, weather timing, route-risk, and delay-risk replay experiments.",
        "integration_posture": "candidate_fast_adapter",
    },
    {
        "source_id": "faa_swim",
        "name": "FAA System Wide Information Management",
        "official_url": "https://www.faa.gov/air_traffic/technology/swim",
        "reviewer_value": "Near-real-time aeronautical, flight, weather, and surveillance information backbone for the NAS.",
        "luma_use": "Use as a higher-bar aviation operations source after access, terms, and message transport are approved.",
        "integration_posture": "access_required",
    },
    {
        "source_id": "faa_swift_portal",
        "name": "FAA SWIFT Portal for SWIM access",
        "official_url": "https://www.faa.gov/air_traffic/technology/swim/products/get_connected",
        "reviewer_value": "Publicly accessible cloud system for obtaining near-real-time SWIM data access.",
        "luma_use": "Candidate route for official aviation operations data once account/access rules are accepted by the user.",
        "integration_posture": "human_account_required",
    },
    {
        "source_id": "faa_nasr_subscription",
        "name": "FAA 28 Day NASR Subscription",
        "official_url": "https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/",
        "reviewer_value": "Authoritative aeronautical data releases on a 28-day cycle.",
        "luma_use": "Use as stable public reference geometry for airport, airspace, route, and facility graph replay.",
        "integration_posture": "candidate_batch_adapter",
    },
    {
        "source_id": "faa_adip",
        "name": "FAA Airport Data and Information Portal",
        "official_url": "https://adip.faa.gov/",
        "reviewer_value": "Centralized airport data collection, validation, and management portal.",
        "luma_use": "Candidate source for airport-data validation workflows after access boundaries are reviewed.",
        "integration_posture": "human_account_required",
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def metric_snapshot(
    current: dict[str, Any],
    champion: dict[str, Any],
    manifest: dict[str, Any],
    wiring: dict[str, Any],
    ready: dict[str, Any],
    sweep: dict[str, Any],
) -> dict[str, Any]:
    current_kuramoto = as_dict(current.get("kuramoto_holdout_expansion"))
    current_gates = as_dict(current.get("gates"))
    champ_summary = as_dict(champion.get("summary"))
    data_room_summary = as_dict(manifest.get("summary"))
    wiring_summary = as_dict(wiring.get("summary"))
    ready_summary = as_dict(ready.get("summary"))
    sweep_summary = as_dict(sweep.get("summary"))

    return {
        "registered_geometry_family_count": as_dict(current.get("registry")).get(
            "family_count", 0
        ),
        "internal_performance_champion_present": bool(
            champ_summary.get("internal_performance_champion_present")
        ),
        "compatible_adapter_route_count": ready_summary.get("routes_replayed", 0),
        "direct_measured_route_count": ready_summary.get(
            "direct_measured_replay_count", 0
        ),
        "conditioned_synthetic_route_count": ready_summary.get(
            "source_conditioned_synthetic_stress_count", 0
        ),
        "baseline_comparison_count": sweep_summary.get(
            "baseline_comparison_count", 0
        ),
        "direct_all_baseline_global_holm_positive_count": ready_summary.get(
            "direct_all_baseline_global_holm_positive_count", 0
        ),
        "performance_rows_reviewed": ready_summary.get(
            "performance_rows_reviewed", 0
        ),
        "legacy_ready_rows_excluded": ready_summary.get(
            "legacy_ready_for_benchmark_rows_excluded", 0
        ),
        "numeric_fallback_count": ready_summary.get(
            "numeric_fallback_profile_count", 0
        ),
        "source_inventory_measured_count": wiring_summary.get(
            "live_source_measured_count", 0
        ),
        "source_inventory_measured_rows": wiring_summary.get(
            "total_measured_rows", 0
        ),
        "source_inventory_is_performance_evidence": False,
        "kuramoto_candidate_was_protocol_selected": bool(
            current_kuramoto.get("candidate_was_protocol_selected")
        ),
        "kuramoto_development_selected_candidate": current_kuramoto.get(
            "development_selected_candidate", ""
        ),
        "kuramoto_holdout_count": current_kuramoto.get("holdout_count", 0),
        "kuramoto_wins_vs_kalman": current_kuramoto.get("wins_vs_kalman", 0),
        "kuramoto_losses_or_ties_vs_kalman": current_kuramoto.get(
            "losses_or_ties_vs_kalman", 0
        ),
        "kuramoto_mean_delta_vs_kalman": current_kuramoto.get(
            "mean_delta_vs_kalman", 0
        ),
        "kuramoto_estimated_rows_replayed": current_kuramoto.get(
            "estimated_rows_replayed", 0
        ),
        "kuramoto_registered_baseline_count": current_kuramoto.get(
            "registered_baseline_count", 0
        ),
        "kuramoto_registered_baseline_mean_win_count": current_kuramoto.get(
            "registered_baseline_mean_win_count", 0
        ),
        "kuramoto_all_baseline_holm_gate_passed": bool(
            current_kuramoto.get(
                "candidate_beats_all_registered_baselines_after_holm"
            )
        ),
        "kuramoto_one_sided_sign_test_p": current_kuramoto.get(
            "one_sided_sign_test_p_value"
        ),
        "data_room_markdown_artifacts": data_room_summary.get("manifested_markdown_count", 0),
        "data_room_control_artifacts": data_room_summary.get("control_artifact_count", 0),
        "field_validation_claim_allowed": bool(current_gates.get("field_validation_claim_allowed")),
        "real_dollar_savings_claim_allowed": bool(current_gates.get("real_dollar_savings_claim_allowed")),
        "live_trading_allowed": bool(current_gates.get("live_trading_or_autonomous_execution_allowed")),
    }


def reviewer_tracks(
    metrics: dict[str, Any], historical_sam_receipt_present: bool
) -> list[dict[str, Any]]:
    agency_status = "CURRENT_SAM_STATUS_REVERIFY_BEFORE_ELIGIBILITY_CLAIM"
    agency_why = (
        "A historical July 9 SAM submission and confirmation receipt is present, "
        "but this artifact does not verify the entity's current active status."
        if historical_sam_receipt_present
        else "No historical SAM submission receipt was resolved by this builder."
    )
    agency_next = (
        "Verify current entity status in SAM.gov read-only, then use the current "
        "official opportunity queue; do not infer eligibility from the July 9 receipt."
    )
    return [
        {
            "track_id": "national_lab_or_technical_reviewer",
            "name": "National lab or independent technical reviewer",
            "why_this_is_real": (
                "A historical LANL VISION licensing reply identified a routing "
                "contact. Current mailbox state and routing freshness must be "
                "reconciled before any follow-up."
            ),
            "proof_to_show": [
                "Kuramoto direct measured nonpromotion: 482/1,525 paired-day wins and negative mean skill versus Kalman.",
                "Zero complete source-specific all-baseline globally corrected promotions.",
                "Four compatible routes: two direct measured and two conditioned-synthetic.",
                "Current proof-state hash and data-room manifest hash.",
                "Failure boundaries showing field validation and real-dollar claims are still locked.",
            ],
            "next_action": (
                "Keep a no-hype technical review packet ready; reconcile the full "
                "mail thread and duplicate-send history before proposing a bounded "
                "protocol review."
            ),
            "human_gate": "Human approves any LANL reply, licensing request, NDA, or disclosure.",
            "status": "REAL_TECHNICAL_REVIEW_ROUTE",
        },
        {
            "track_id": "patent_counsel_and_pro_bono",
            "name": "Historical patent counsel / pro bono route",
            "why_this_is_real": (
                "The prior Georgia PATENTS route is closed under the current "
                "routing controls and must not be reopened by this packet."
            ),
            "proof_to_show": [
                "Claim-boundary register.",
                "IP counsel diligence packet.",
                "Technical invention map and proof-state boundaries.",
                "No public expansion of claims until counsel review.",
            ],
            "next_action": (
                "No outreach on the closed Georgia PATENTS route. Use current "
                "official USPTO or licensed-counsel guidance for any live deadline."
            ),
            "human_gate": "Human and licensed counsel decide all filings, claims, deadlines, continuations, PCT, and disclosures.",
            "status": "CLOSED_ROUTE_DO_NOT_REOPEN",
        },
        {
            "track_id": "agency_reviewer",
            "name": "Agency reviewer / contracting technical evaluator",
            "why_this_is_real": agency_why,
            "proof_to_show": [
                "SAM submission and same-day opportunity push receipt.",
                "Federal submission protocol packet.",
                "Submission authority matrix.",
                "Immediate federal AI opportunity radar.",
                "Reviewer diligence QA matrix.",
            ],
            "next_action": agency_next,
            "human_gate": "Human signs SAM terms, reps/certs, entity renewal, and portal submissions.",
            "status": agency_status,
        },
        {
            "track_id": "aviation_faa_live_data",
            "name": "FAA / aviation live-data expansion",
            "why_this_is_real": "FAA and NWS aviation sources expose official weather, NAS, airport, and SWIM data routes that map to noisy live-system replay.",
            "proof_to_show": [
                "Live-breadth source manifest.",
                "Geometry live systems frontier.",
                "Candidate aviation adapters from AWC, NASR, ADIP, and SWIM.",
                "No aviation safety or FAA validation claim until official access and replay pass.",
            ],
            "next_action": "Build AWC Data API and NASR batch adapter first; treat SWIM/ADIP as human-account gated.",
            "human_gate": "Human accepts any FAA account terms or access agreements.",
            "status": "NEW_LIVE_SOURCE_ROUTE",
        },
        {
            "track_id": "trading_alpha_reviewer",
            "name": "Trading/noisy-market proof reviewer",
            "why_this_is_real": "The trading lane is useful as a noisy proof laboratory, but live execution and profit claims remain blocked.",
            "proof_to_show": [
                "Market-signal geometry candidates.",
                "Live breadth replay reports.",
                "Sharpe/edge score artifacts only where backed by frozen walk-forward tests.",
                "Explicit no-live-trading gate.",
            ],
            "next_action": "Use trading data as a stress-test substrate and proof-deck strengthening layer, not as an investor promise.",
            "human_gate": "Human runtime approval is required for any live trading, brokerage action, or capital movement.",
            "status": "NOISY_PROOF_LAB_NOT_LIVE_EXECUTION",
        },
    ]


def build_payload() -> dict[str, Any]:
    current = read_json(CURRENT_PROOF)
    champion = read_json(CHAMPION)
    manifest = read_json(MANIFEST)
    sam_submission = read_json(SAM_SUBMISSION)
    wiring = read_json(WIRING_MATRIX)
    ready = read_json(READY_REPLAY)
    sweep = read_json(LOCKED_SWEEP)
    required_schemas = {
        "current_luma_proof_state.v2": current.get("schema"),
        "geometry_champion_of_champions_v3": champion.get("schema"),
        "geometry_live_wiring_matrix_v3": wiring.get("schema"),
        "geometry_ready_source_replay_v2": ready.get("schema"),
        "locked_source_baseline_replay_sweep_v2": sweep.get("schema"),
    }
    for expected, actual in required_schemas.items():
        if actual != expected:
            raise ValueError(f"{expected} is required; found {actual!r}")

    sam_summary = as_dict(sam_submission.get("summary"))
    historical_sam_receipt_present = bool(
        sam_summary.get("sam_registration_submitted")
    ) and bool(
        sam_summary.get("sam_confirmation_email_received")
    )
    historical_sam_receipt_generated_utc = sam_submission.get("generated_utc")
    current_sam_active_status_verified = False
    metrics = metric_snapshot(current, champion, manifest, wiring, ready, sweep)
    tracks = reviewer_tracks(
        metrics,
        historical_sam_receipt_present=historical_sam_receipt_present,
    )

    payload = {
        "schema": "technical_gov_reviewer_approval_stack_v2",
        "generated_utc": now_utc(),
        "status": "TECHNICAL_GOV_REVIEWER_APPROVAL_STACK_READY_HUMAN_ACTION_REQUIRED",
        "summary": {
            "reviewer_track_count": len(tracks),
            "official_data_source_count": len(OFFICIAL_DATA_SOURCES),
            "sam_historical_submission_receipt_present": historical_sam_receipt_present,
            "sam_historical_submission_receipt_generated_utc": historical_sam_receipt_generated_utc,
            "sam_current_active_status_verified": current_sam_active_status_verified,
            "sam_current_status": (
                "historical_submission_receipt_present_current_active_status_not_verified"
                if historical_sam_receipt_present
                else "no_historical_submission_receipt_resolved_current_status_not_verified"
            ),
            "venture_studio_deprioritized": True,
            "technical_reviewer_first": True,
            "human_action_required": True,
            "external_send_allowed_without_human": False,
            "portal_submission_allowed_without_human": False,
            "legal_or_ip_action_allowed_without_human": False,
            "live_trading_allowed": False,
        },
        "core_truth": {
            "plain_english": (
                "LumenCore currently has a governed benchmark and evidence stack, "
                "not a promoted performance champion. The strongest scientific "
                "asset is the source-specific protocol, including preserved negative "
                "results and explicit locks against unsupported field, savings, "
                "award, or trading claims."
            ),
            "metrics": metrics,
            "safe_technical_claim": (
                "Kuramoto phase coupling was measured directly on the frozen EIA "
                "panel but was not development-selected, won 482 of 1,525 paired "
                "days versus the named Kalman baseline, had mean skill delta "
                "-0.508190706, and cleared zero registered-baseline promotion gates. "
                "This supports a bounded source-native protocol review, not a "
                "performance, field-replay, or savings claim."
            ),
            "blocked_claims": [
                "external field-validation approval",
                "realized government savings",
                "guaranteed ROI",
                "live trading profit",
                "FAA validation",
                "agency approval",
                "patent allowance",
                "award certainty",
            ],
        },
        "reviewer_tracks": tracks,
        "official_live_data_targets": OFFICIAL_DATA_SOURCES,
        "sam_renewal_support": {
            "current_browser_state": (
                "Not inspected by this builder. A historical July 9 artifact records "
                "Entity Registration Submitted and an email confirmation; current "
                "active status is not verified."
            ),
            "human_next_step": (
                "Open SAM.gov and verify current entity status read-only. Keep terms, "
                "reps/certs, banking, role requests, and final submissions human-controlled."
            ),
            "codex_safe_support": [
                "Record SAM submission evidence without exposing OTPs, bank data, or private portal fields.",
                "Monitor status and surface any follow-up notices.",
                "Prepare next opportunity packages from official instructions.",
                "Do not submit future reps/certs, pricing, or portal packages without human confirmation.",
            ],
            "known_email_context": [
                "A July 9 artifact records a SAM confirmation email for a submitted entity registration.",
                "The historical receipt is not proof of current active registration, eligibility, award, or source selection.",
                "Any SAM account key rotation reminder should be handled separately from entity renewal.",
            ],
        },
        "email_signal_triage": {
            "real_signals": [
                "The prior Georgia PATENTS route is closed and retained only as historical routing evidence.",
                "A historical LANL reply identified a VISION licensing contact; current mailbox state must be reconciled before follow-up.",
                "Login.gov confirms DSIP connection, which supports the federal submission route.",
                "The historical SAM submission receipt requires a fresh current-status check before any eligibility claim.",
            ],
            "deprioritized_signals": [
                "Pitch-event or pay-before-pitch routes should not drive the proof stack.",
                "Venture studio help is useful only if they bring technical validation, real customers, or non-extractive terms.",
            ],
        },
        "next_48_hours": [
            "Verify current SAM entity status read-only; do not infer active status from the July 9 receipt.",
            "Keep the closed Georgia PATENTS route closed.",
            "Reconcile the full LANL/VISION email thread before any bounded follow-up.",
            "Build FAA AWC Data API and FAA NASR source adapters as the next live-data expansion path.",
            "Use the current official opportunity queue; do not revive closed FHWA or expired lanes.",
        ],
        "outputs": {
            "json": "out/ops/technical_gov_reviewer_approval_stack_latest.json",
            "dashboard_json": "dashboard/data/technical_gov_reviewer_approval_stack.json",
            "markdown": "grant_submissions/funding_sprint_20260709/TECHNICAL_GOV_REVIEWER_APPROVAL_STACK_2026-07-09.md",
        },
    }
    payload["approval_stack_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    metrics = payload["core_truth"]["metrics"]
    lines = [
        "# Technical / Government Reviewer Approval Stack - 2026-07-09",
        "",
        "Purpose: route LumenCore away from pay-to-pitch pressure and toward technical reviewers, government protocol readiness, IP defense, and official live-data expansion.",
        "",
        "This artifact is a reviewer-readiness and action-control packet. It does not authorize SAM submission, legal filings, external sends, agency certifications, live trading, or capital movement without human approval.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Reviewer tracks: `{summary['reviewer_track_count']}`",
        f"- Official live-data targets: `{summary['official_data_source_count']}`",
        f"- Venture studio deprioritized: `{str(summary['venture_studio_deprioritized']).lower()}`",
        f"- Technical reviewer first: `{str(summary['technical_reviewer_first']).lower()}`",
        f"- Historical SAM submission receipt present: `{str(summary['sam_historical_submission_receipt_present']).lower()}`",
        f"- Historical SAM receipt generated UTC: `{summary['sam_historical_submission_receipt_generated_utc']}`",
        f"- Current SAM active status verified: `{str(summary['sam_current_active_status_verified']).lower()}`",
        f"- Current SAM status: `{summary['sam_current_status']}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Portal submission without human: `{str(summary['portal_submission_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Approval stack SHA-256: `{payload['approval_stack_sha256']}`",
        "",
        "## Core Truth",
        "",
        payload["core_truth"]["plain_english"],
        "",
        f"- Registered geometry families: `{metrics['registered_geometry_family_count']}`",
        f"- Internal performance champion present: `{str(metrics['internal_performance_champion_present']).lower()}`",
        f"- Compatible adapter routes: `{metrics['compatible_adapter_route_count']}`",
        f"- Direct measured routes: `{metrics['direct_measured_route_count']}`",
        f"- Conditioned-synthetic routes: `{metrics['conditioned_synthetic_route_count']}`",
        f"- Baseline comparisons: `{metrics['baseline_comparison_count']}`",
        f"- Direct all-baseline global promotions: `{metrics['direct_all_baseline_global_holm_positive_count']}`",
        f"- Performance rows reviewed: `{metrics['performance_rows_reviewed']}`",
        f"- Legacy ready rows excluded: `{metrics['legacy_ready_rows_excluded']}`",
        f"- Numeric fallbacks: `{metrics['numeric_fallback_count']}`",
        f"- Source inventory: `{metrics['source_inventory_measured_count']}` measured sources / `{metrics['source_inventory_measured_rows']}` rows",
        f"- Source inventory is performance evidence: `{str(metrics['source_inventory_is_performance_evidence']).lower()}`",
        f"- Kuramoto was protocol-selected: `{str(metrics['kuramoto_candidate_was_protocol_selected']).lower()}`",
        f"- Development-selected candidate: `{metrics['kuramoto_development_selected_candidate']}`",
        f"- Kuramoto holdouts: `{metrics['kuramoto_holdout_count']}`",
        f"- Kuramoto wins vs Kalman: `{metrics['kuramoto_wins_vs_kalman']}`",
        f"- Kuramoto losses or ties vs Kalman: `{metrics['kuramoto_losses_or_ties_vs_kalman']}`",
        f"- Kuramoto mean skill delta vs Kalman: `{metrics['kuramoto_mean_delta_vs_kalman']}`",
        f"- Kuramoto registered-baseline mean wins: `{metrics['kuramoto_registered_baseline_mean_win_count']}/{metrics['kuramoto_registered_baseline_count']}`",
        f"- Kuramoto estimated replay rows: `{metrics['kuramoto_estimated_rows_replayed']}`",
        f"- Data-room markdown artifacts: `{metrics['data_room_markdown_artifacts']}`",
        f"- Data-room control artifacts: `{metrics['data_room_control_artifacts']}`",
        f"- Field validation claim allowed: `{str(metrics['field_validation_claim_allowed']).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(metrics['real_dollar_savings_claim_allowed']).lower()}`",
        "",
        f"Safe technical claim: {payload['core_truth']['safe_technical_claim']}",
        "",
        "Blocked claims:",
    ]
    for claim in payload["core_truth"]["blocked_claims"]:
        lines.append(f"- `{claim}`")

    lines.extend(["", "## Reviewer Tracks", ""])
    for track in payload["reviewer_tracks"]:
        lines.extend(
            [
                f"### {track['name']}",
                "",
                f"- Status: `{track['status']}`",
                f"- Why this is real: {track['why_this_is_real']}",
                "- Proof to show:",
            ]
        )
        for proof in track["proof_to_show"]:
            lines.append(f"  - {proof}")
        lines.extend([f"- Next action: {track['next_action']}", f"- Human gate: {track['human_gate']}", ""])

    lines.extend(["## Official Live-Data Targets", ""])
    for source in payload["official_live_data_targets"]:
        lines.extend(
            [
                f"### {source['name']}",
                "",
                f"- Source ID: `{source['source_id']}`",
                f"- URL: {source['official_url']}",
                f"- Reviewer value: {source['reviewer_value']}",
                f"- Luma use: {source['luma_use']}",
                f"- Integration posture: `{source['integration_posture']}`",
                "",
            ]
        )

    sam = payload["sam_renewal_support"]
    lines.extend(
        [
            "## SAM Status Support",
            "",
            f"- Current browser state: {sam['current_browser_state']}",
            f"- Human next step: {sam['human_next_step']}",
            "- Codex safe support:",
        ]
    )
    for item in sam["codex_safe_support"]:
        lines.append(f"  - {item}")
    lines.append("- Known email context:")
    for item in sam["known_email_context"]:
        lines.append(f"  - {item}")

    triage = payload["email_signal_triage"]
    lines.extend(["", "## Email Signal Triage", "", "Real signals:"])
    for item in triage["real_signals"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Deprioritized signals:")
    for item in triage["deprioritized_signals"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Next 48 Hours", ""])
    for item in payload["next_48_hours"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public data-room markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "reviewer_tracks": payload["summary"]["reviewer_track_count"],
                "official_data_targets": payload["summary"]["official_data_source_count"],
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
