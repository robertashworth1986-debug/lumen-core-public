from __future__ import annotations

import hashlib
import json
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
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def metric_snapshot(current: dict[str, Any], champion: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    current_manifest = as_dict(current.get("manifest"))
    current_kuramoto = as_dict(current.get("kuramoto_holdout_expansion"))
    current_gates = as_dict(current.get("gates"))
    champ_summary = as_dict(champion.get("summary"))
    strongest = as_dict(as_dict(champion.get("champion_of_champions")).get("strongest_current"))
    strongest_holdout = as_dict(strongest.get("kuramoto_holdout_evidence"))
    data_room_summary = as_dict(manifest.get("summary"))

    return {
        "registered_geometry_family_count": current.get("registry", {}).get("family_count", 0),
        "ready_benchmark_routes": current_manifest.get("ready_for_benchmark_routes", 0),
        "unique_source_count": current_manifest.get("unique_source_count", 0),
        "unique_source_estimated_rows": current_manifest.get("unique_source_estimated_rows", 0),
        "kuramoto_holdout_count": current_kuramoto.get("holdout_count", strongest_holdout.get("holdout_count", 0)),
        "kuramoto_wins_vs_kalman": current_kuramoto.get("wins_vs_kalman", strongest_holdout.get("wins_vs_kalman", 0)),
        "kuramoto_estimated_rows_replayed": current_kuramoto.get(
            "estimated_rows_replayed",
            strongest_holdout.get("estimated_rows_replayed", 0),
        ),
        "kuramoto_one_sided_sign_test_p": current_kuramoto.get(
            "one_sided_sign_test_p_value",
            strongest_holdout.get("one_sided_sign_test_p_value"),
        ),
        "live_measured_sources": champ_summary.get("live_measured_sources", 0),
        "live_total_measured_rows": champ_summary.get("live_total_measured_rows", 0),
        "safe_estimated_annual_value_usd": champ_summary.get("safe_estimated_annual_value_usd", 0),
        "blocked_context_annual_value_usd": champ_summary.get("blocked_context_annual_value_usd", 0),
        "data_room_markdown_artifacts": data_room_summary.get("manifested_markdown_count", 0),
        "data_room_control_artifacts": data_room_summary.get("control_artifact_count", 0),
        "field_validation_claim_allowed": bool(current_gates.get("field_validation_claim_allowed")),
        "real_dollar_savings_claim_allowed": bool(current_gates.get("real_dollar_savings_claim_allowed")),
        "live_trading_allowed": bool(current_gates.get("live_trading_or_autonomous_execution_allowed")),
    }


def reviewer_tracks(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "track_id": "national_lab_or_technical_reviewer",
            "name": "National lab or independent technical reviewer",
            "why_this_is_real": "LANL routed the VISION licensing inquiry to a named main contact returning next week.",
            "proof_to_show": [
                "Kuramoto 24/24 internal source-conditioned holdout wins versus Kalman.",
                "2,506,267 estimated replay rows for the harmonic holdout expansion.",
                "Current proof-state hash and data-room manifest hash.",
                "Failure boundaries showing field validation and real-dollar claims are still locked.",
            ],
            "next_action": "Prepare a no-hype technical review packet and ask for fit, validation route, or licensing pathway.",
            "human_gate": "Human approves any LANL reply, licensing request, NDA, or disclosure.",
            "status": "REAL_TECHNICAL_REVIEW_ROUTE",
        },
        {
            "track_id": "patent_counsel_and_pro_bono",
            "name": "Patent counsel / USPTO pro bono route",
            "why_this_is_real": "USPTO Patent Pro Bono replied and identified Georgia PATENTS as the Tennessee-serving program, with Pro Se assistance as a deadline fallback.",
            "proof_to_show": [
                "Claim-boundary register.",
                "IP counsel diligence packet.",
                "Technical invention map and proof-state boundaries.",
                "No public expansion of claims until counsel review.",
            ],
            "next_action": "Prepare Georgia PATENTS intake package and a Pro Se fallback checklist before the July 2026 deadline window.",
            "human_gate": "Human and licensed counsel decide all filings, claims, deadlines, continuations, PCT, and disclosures.",
            "status": "URGENT_REAL_IP_ROUTE",
        },
        {
            "track_id": "agency_reviewer",
            "name": "Agency reviewer / contracting technical evaluator",
            "why_this_is_real": "SAM, DSIP, FHWA, DARPA DICE, and federal protocol packets already exist; SAM renewal is now the active account blocker.",
            "proof_to_show": [
                "Federal submission protocol packet.",
                "Submission authority matrix.",
                "Immediate federal AI opportunity radar.",
                "Reviewer diligence QA matrix.",
            ],
            "next_action": "Finish SAM renewal with human certifications, then use the agency radar to prioritize official reviewer-facing packages.",
            "human_gate": "Human signs SAM terms, reps/certs, entity renewal, and portal submissions.",
            "status": "ACCOUNT_RENEWAL_AND_REVIEWER_ROUTE",
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
    metrics = metric_snapshot(current, champion, manifest)
    tracks = reviewer_tracks(metrics)

    payload = {
        "schema": "technical_gov_reviewer_approval_stack_v1",
        "generated_utc": now_utc(),
        "status": "TECHNICAL_GOV_REVIEWER_APPROVAL_STACK_READY_HUMAN_ACTION_REQUIRED",
        "summary": {
            "reviewer_track_count": len(tracks),
            "official_data_source_count": len(OFFICIAL_DATA_SOURCES),
            "sam_renewal_blocker": "SAM.gov Terms of Use and login.gov/MFA require the human user in browser.",
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
                "LumenCore's strongest current story is not a sales pitch. It is a measured proof stack with "
                "internal holdout evidence, live-source breadth, and clear locks against unsupported field-validation, "
                "revenue, award, or trading claims."
            ),
            "metrics": metrics,
            "safe_technical_claim": (
                "Kuramoto phase coupling is ready for a buyer-authorized field replay request after internal "
                "source-conditioned holdout evidence; it is not yet field validation or realized savings."
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
            "current_browser_state": "SAM.gov redirected to the public home page and displayed a Terms of Use modal.",
            "human_next_step": "Click Agree if you accept the SAM.gov terms, then complete login.gov/MFA.",
            "codex_safe_support": [
                "Navigate to Workspace > Entity Management > Entities.",
                "Open Robert Ashworth / SQY2XW71ZM51 / 14TM8 if shown.",
                "Prepare renewal checklist and flag changed fields.",
                "Do not submit reps/certs or final renewal without human confirmation.",
            ],
            "known_email_context": [
                "SAM.gov sent a 60-day expiration notice for August 30, 2026.",
                "A prior SAM.gov one-time code email exists but is expired and must not be reused.",
                "SAM account key rotation reminder exists and should be handled separately from entity renewal.",
            ],
        },
        "email_signal_triage": {
            "real_signals": [
                "USPTO Patent Pro Bono routed Tennessee inventors to Georgia PATENTS and noted the Pro Se Assistance Program as a deadline fallback.",
                "LANL replied that Mike Erickson is the main contact for the VISION licensing opportunity when he returns.",
                "Login.gov confirms DSIP connection, which supports the federal submission route.",
                "SAM.gov expiration notice confirms entity renewal is a real blocker before federal award eligibility.",
            ],
            "deprioritized_signals": [
                "Pitch-event or pay-before-pitch routes should not drive the proof stack.",
                "Venture studio help is useful only if they bring technical validation, real customers, or non-extractive terms.",
            ],
        },
        "next_48_hours": [
            "Finish SAM renewal in the browser with human certification.",
            "Prepare Georgia PATENTS intake packet and Pro Se fallback checklist.",
            "Prepare LANL/VISION technical review packet with claim boundaries and current proof hashes.",
            "Build FAA AWC Data API and FAA NASR source adapters as the next live-data expansion path.",
            "Promote FHWA TSMO and Air Force AAC only as official reviewer packages, not broad sales pitches.",
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
        f"- Ready benchmark routes: `{metrics['ready_benchmark_routes']}`",
        f"- Unique source count: `{metrics['unique_source_count']}`",
        f"- Unique source estimated rows: `{metrics['unique_source_estimated_rows']}`",
        f"- Kuramoto holdouts: `{metrics['kuramoto_holdout_count']}`",
        f"- Kuramoto wins vs Kalman: `{metrics['kuramoto_wins_vs_kalman']}`",
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
            "## SAM Renewal Support",
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
