from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

PROOF_REVENUE_JSON = OUT_OPS / "proof_to_revenue_engine_latest.json"
STRESS_MATRIX_JSON = OUT_OPS / "champion_stress_test_matrix_latest.json"
LIVE_DOMAIN_JSON = OUT_OPS / "live_domain_deployment_feed_latest.json"
CHAMPION_JSON = DASHBOARD_DATA / "champion_metric_gauntlet.json"
LOCKED_SWEEP_JSON = DASHBOARD_DATA / "locked_source_baseline_replay_sweep.json"
VALUATION_JSON = DASHBOARD_DATA / "valuation_proposal_target_packet.json"
HYPERCORE_PROTOCOL_JSON = ROOT / "config" / "hypercore_v8_validation_protocol_v1.json"

OUT_JSON = OUT_OPS / "first_buyer_target_board_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "first_buyer_target_board.json"
OUT_MD = DOCS / "FIRST_BUYER_TARGET_BOARD_2026-06-27.md"
UPDATED_BUSINESS_PLAN_PDF = Path(
    r"C:\Users\Novac\iCloudDrive\Business plan\LumenCore_Business_Plan_Investor_Ready_UPDATED_2026-07-03.pdf"
)

BOUNDARY = (
    "First-buyer target board. This artifact ranks current official buyer or capital channels and prepares one "
    "bounded protocol-review inquiry. It does not authorize auto-send, bulk outreach, contact scraping, field-"
    "validation claims, realized-savings claims, live trading, or autonomous operational execution."
)

SOURCE_VERIFIED_UTC = "2026-08-04T11:52:54Z"

SOURCE_REFS: dict[str, dict[str, str]] = {
    "southern_new_ventures": {
        "url": "https://www.southerncompany.com/future-of-energy/new-ventures.html",
        "fact": (
            "Southern Company New Ventures says it introduces novel technology pilots and solutions, and lists "
            "AI, data-driven tools, grid optimization, AI models, and grid operations among its current focus areas."
        ),
        "public_contact": "https://www.southerncompany.com/contact-us.html",
        "verified_utc": SOURCE_VERIFIED_UTC,
    },
    "pge_research_and_development": {
        "url": "https://www.pge.com/en/about/pge-systems/research-and-development.html",
        "fact": (
            "PG&E says it needs ideas from broad external sources, publishes AI-centered R&D priorities, invites "
            "collaborative problem solving, and publishes innovation@pge.com for questions and requests."
        ),
        "public_contact": "innovation@pge.com",
        "verified_utc": SOURCE_VERIFIED_UTC,
    },
    "exelon_2c2i": {
        "url": "https://www.exeloncorp.com/community/foundation",
        "fact": (
            "Exelon's 2c2i program is accepting applications through September 27, 2026 for climate-focused "
            "startups; it describes $100,000-$300,000 investments and requires measurable climate, territory, "
            "community, product, market, team, and traction fit."
        ),
        "public_contact": "exelonfoundation@exeloncorp.com",
        "verified_utc": SOURCE_VERIFIED_UTC,
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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def proof_snapshot() -> dict[str, Any]:
    live = read_json(LIVE_DOMAIN_JSON)
    champion = read_json(CHAMPION_JSON)
    locked = read_json(LOCKED_SWEEP_JSON)
    valuation = read_json(VALUATION_JSON)

    if champion.get("schema") != "champion_metric_gauntlet_v2":
        raise ValueError("champion metric gauntlet v2 is required")
    if locked.get("schema") != "locked_source_baseline_replay_sweep_v2":
        raise ValueError("locked source baseline replay sweep v2 is required")
    if valuation.get("schema") != "valuation_proposal_target_packet_v3":
        raise ValueError("valuation proposal target packet v3 is required")

    live_summary = as_dict(live.get("summary"))
    reviewer_urls = as_dict(live.get("reviewer_urls"))
    champion_summary = as_dict(champion.get("summary"))
    strongest = as_dict(champion.get("strongest_current"))
    locked_summary = as_dict(locked.get("summary"))
    valuation_truth = as_dict(valuation.get("current_truth"))
    valuation_overall = as_dict(
        valuation.get("overall_locked_sweep_stats")
    )

    holdout_wins = as_int(champion_summary.get("holdout_wins"))
    holdout_count = as_int(champion_summary.get("holdout_count"))
    champion_rows = as_int(champion_summary.get("estimated_rows_replayed"))
    champion_samples = as_int(champion_summary.get("numeric_samples_read"))
    locked_comparisons = as_int(
        locked_summary.get("baseline_comparison_count")
    )
    locked_wins = as_int(locked_summary.get("candidate_win_count"))
    live_ready = bool(
        live_summary.get("domain_deployment_state")
        == "LIVE_DOMAIN_HASH_VERIFIED"
        and champion_summary.get("live_domain_reviewer_ready")
    )

    return {
        "revenue_stage": "paid_protocol_review_scoping_ready_draft_only",
        "internal_performance_champion_present": False,
        "reference_candidate": strongest.get(
            "family", "kuramoto_phase_coupling"
        ),
        "reference_candidate_label": strongest.get(
            "label", "Kuramoto phase coupling"
        ),
        "development_selected_candidate": strongest.get(
            "development_selected_candidate", "lissajous_phase_paths"
        ),
        "reference_candidate_was_protocol_selected": bool(
            strongest.get("candidate_was_protocol_selected")
        ),
        "named_baseline": strongest.get(
            "named_baseline", "kalman_local_linear_trend"
        ),
        "holdout_wins": holdout_wins,
        "holdout_count": holdout_count,
        "holdout_win_rate": as_float(
            champion_summary.get("holdout_win_rate")
        ),
        "mean_delta_vs_named_baseline": as_float(
            champion_summary.get("mean_delta_vs_named_baseline")
        ),
        "candidate_beats_all_registered_baselines_after_holm": bool(
            strongest.get(
                "candidate_beats_all_registered_baselines_after_holm"
            )
        ),
        "source_system_count": as_int(
            champion_summary.get("source_system_count")
        ),
        "estimated_rows_replayed": champion_rows,
        "numeric_samples_read": champion_samples,
        "broader_enabled_provider_count": as_int(champion_summary.get("broader_enabled_provider_count")),
        "broader_measured_provider_count": as_int(champion_summary.get("broader_measured_provider_count")),
        "manifest_unique_source_count": as_int(champion_summary.get("manifest_unique_source_count")),
        "manifest_ready_for_benchmark_row_count": as_int(
            champion_summary.get("manifest_ready_for_benchmark_row_count")
        ),
        "locked_adapter_backed_routes": as_int(
            locked_summary.get("adapter_backed_routes")
        ),
        "locked_direct_measured_routes": as_int(
            locked_summary.get("direct_measured_routes_replayed")
        ),
        "locked_conditioned_synthetic_routes": as_int(
            locked_summary.get("source_conditioned_routes_replayed")
        ),
        "locked_baseline_comparison_count": locked_comparisons,
        "locked_raw_mean_win_count": locked_wins,
        "locked_global_holm_positive_count": as_int(
            locked_summary.get("global_holm_positive_count")
        ),
        "locked_candidate_loss_or_tie_count": as_int(
            locked_summary.get("candidate_loss_or_tie_count")
            or max(0, locked_comparisons - locked_wins)
        ),
        "locked_performance_rows_reviewed": as_int(
            locked_summary.get("numeric_samples_read")
        ),
        "legacy_ready_rows_excluded": as_int(
            locked_summary.get("unclassified_manifest_rows_excluded")
        ),
        "numeric_fallback_profile_count": as_int(
            locked_summary.get("fallback_profiles_used")
        ),
        "locked_replay_chain_sha256": locked_summary.get("replay_chain_sha256")
        or valuation_overall.get("replay_chain_sha256", ""),
        "safe_estimated_hourly_value_usd": 0.0,
        "safe_estimated_annual_value_usd": 0.0,
        "paid_protocol_review_scoping_allowed": True,
        "field_replay_request_ready": False,
        "live_domain_hash_verified": live_ready,
        "live_domain_reviewer_ready": bool(
            live_summary.get("live_domain_reviewer_ready") or champion_summary.get("live_domain_reviewer_ready")
        ),
        "champion_feed_primary": reviewer_urls.get("champion_feed_primary", ""),
        "mission_control": reviewer_urls.get("mission_control", "https://lumen-core.ai/mission_control.html"),
        "proof_to_revenue_feed": "https://lumen-core.ai/data/proof_to_revenue_engine.json",
        "stress_matrix_feed": "https://lumen-core.ai/data/champion_stress_test_matrix.json",
        "business_plan_pdf": str(UPDATED_BUSINESS_PLAN_PDF),
        "business_plan_pdf_exists": UPDATED_BUSINESS_PLAN_PDF.exists(),
    }


def commercial_offer_snapshot() -> dict[str, Any]:
    payload = read_json(HYPERCORE_PROTOCOL_JSON)
    if payload.get("schema") != "hypercore_v8_validation_protocol_v1":
        raise ValueError("Hypercore V8 validation protocol is required")
    commercial = as_dict(payload.get("commercial_boundary"))
    if commercial.get("fee_status") != "candidate_not_committed":
        raise ValueError("Hypercore fee must remain candidate and uncommitted")
    if commercial.get("external_send_allowed") is not False:
        raise ValueError("Hypercore commercial boundary must remain fail-closed")
    if commercial.get("contract_or_price_acceptance_proven") is not False:
        raise ValueError("Buyer price acceptance cannot be inferred")
    return {
        "service": "source-native benchmark and evidence protocol review",
        "candidate_fee_usd": as_int(commercial.get("candidate_fee_usd")),
        "candidate_duration_business_days": as_int(
            commercial.get("candidate_duration_business_days")
        ),
        "fee_status": commercial.get("fee_status"),
        "founder_approved": False,
        "buyer_accepted": False,
        "external_send_allowed": False,
        "contract_or_price_acceptance_proven": False,
        "source": str(HYPERCORE_PROTOCOL_JSON.relative_to(ROOT)).replace("\\", "/"),
    }


def make_candidates(
    snapshot: dict[str, Any], commercial: dict[str, Any]
) -> list[dict[str, Any]]:
    reference = snapshot["reference_candidate_label"]
    baseline = snapshot["named_baseline"]
    proof_line = (
        f"{reference} was audited on {snapshot['holdout_count']} paired measured "
        f"EIA holdout days and won {snapshot['holdout_wins']} pairs versus {baseline}, "
        f"but its mean skill delta was {snapshot['mean_delta_vs_named_baseline']:.6f} "
        "and it did not clear the source-specific all-baseline gate. The "
        "compatibility-gated sweep covers "
        f"{snapshot['locked_adapter_backed_routes']} adapter-backed routes, "
        f"{snapshot['locked_baseline_comparison_count']} baseline comparisons, "
        f"{snapshot['locked_global_holm_positive_count']} globally corrected "
        f"positive direct comparisons, and {snapshot['locked_performance_rows_reviewed']:,} "
        "performance rows. This supports a paid source-native benchmark or evidence "
        "protocol review, not a candidate-performance, field, or savings claim."
    )

    offer_line = (
        f"${commercial['candidate_fee_usd']:,} candidate fixed fee for "
        f"{commercial['candidate_duration_business_days']} business days, subject to written "
        "scope confirmation; no fee acceptance is inferred."
    )
    candidates = [
        {
            "rank": 2,
            "organization": "Southern Company New Ventures",
            "buyer_channel_type": "utility_new_ventures_pilot_channel",
            "best_buyer_role": "New Ventures innovation intake team",
            "why_this_buyer_first": (
                "The current official page explicitly invites external technology collaboration, pilots, AI and "
                "data-driven tools, grid optimization, AI models, and grid operations. Its visible Contact Us control "
                "now resolves to a general contact page rather than a named New Ventures inbox, so the recipient "
                "must be verified before any draft can be addressed."
            ),
            "fit_score": 95,
            "proof_fit": [
                "AI model evidence review",
                "grid analytics benchmark governance",
                "pilot acceptance criteria",
                "positive and negative result custody",
            ],
            "first_ask": (
                "Request a 20-minute fit call for one fixed-scope source-native benchmark and evidence protocol "
                f"review. Candidate commercial scope: {offer_line}"
            ),
            "buyer_data_needed": [
                "one authorized analytics use case and source",
                "accepted incumbent baselines",
                "pre-registered chronology and metrics",
                "data-use and no-production-write boundaries",
            ],
            "source_keys": ["southern_new_ventures"],
            "public_contact_route": {
                "type": "official_web_contact_route_recipient_unresolved",
                "address": SOURCE_REFS["southern_new_ventures"]["public_contact"],
                "authority": "The official New Ventures page links its Contact Us control to the official Southern Company contact page; no named New Ventures email was visible in the current source review.",
            },
            "duplicate_check": {
                "checked_utc": SOURCE_VERIFIED_UTC,
                "scope": "Gmail all mail and Sent for Southern Company and official Southern domains",
                "relevant_prior_outbound_count": 0,
                "relevant_prior_inbound_count": 0,
                "duplicate_send_decision": "recipient_unresolved_no_email_send",
            },
            "risk_notes": [
                "The visible official route does not establish a named recipient, budget, procurement authority, or buyer acceptance.",
                "Do not use the historical direct address without a fresh official-source confirmation.",
            ],
            "recommended_action_today": (
                "Use the official contact route only to obtain the correct intake owner; do not address or send the "
                "protocol-review draft through this lane until a named official recipient is verified."
            ),
            "proof_line": proof_line,
        },
        {
            "rank": 1,
            "organization": "PG&E Research and Development",
            "buyer_channel_type": "regulated_utility_research_and_innovation_channel",
            "best_buyer_role": "Utility Partnerships and Innovation / R&D intake team",
            "why_this_buyer_first": (
                "PG&E's current official R&D page invites external ideas, publishes AI-centered challenge areas, "
                "and currently publishes a direct innovation inbox. That makes it the best prepared one-message "
                "draft lane for the governed-review service, subject to the action-time route and duplicate checks."
            ),
            "fit_score": 93,
            "proof_fit": [
                "AI investment evidence",
                "model and data collaboration",
                "grid planning benchmark governance",
                "wildfire and asset-risk analytics review",
            ],
            "first_ask": (
                "Request routing to the owner of AI/model validation for one bounded source-native protocol review. "
                f"Candidate commercial scope: {offer_line}"
            ),
            "buyer_data_needed": [
                "one PG&E-priority analytics question",
                "authorized historical source",
                "accepted incumbent baselines and decision metric",
                "procurement or R&D sponsorship route",
            ],
            "source_keys": ["pge_research_and_development"],
            "public_contact_route": {
                "type": "official_public_innovation_inbox",
                "address": SOURCE_REFS["pge_research_and_development"]["public_contact"],
                "authority": "Published in the Contact us section of PG&E's official R&D page",
            },
            "duplicate_check": {
                "checked_utc": SOURCE_VERIFIED_UTC,
                "scope": "Gmail all mail and Sent for PG&E and official PG&E domains",
                "relevant_prior_outbound_count": 0,
                "relevant_prior_inbound_count": 0,
                "duplicate_send_decision": "clean_new_route_one_message_max_after_action_time_approval",
            },
            "risk_notes": [
                "PG&E may route external work through a formal bid, pitch-fest, or regulated R&D process.",
                "No current budget, data access, or procurement authority is proven by the public contact page.",
            ],
            "recommended_action_today": (
                "Prepare one no-attachment technical fit inquiry; do not send until the compliance placeholder, "
                "fresh duplicate check, and exact action-time approval gates are cleared."
            ),
            "proof_line": proof_line,
        },
        {
            "rank": 3,
            "organization": "Exelon Foundation 2c2i",
            "buyer_channel_type": "equity_bearing_climate_startup_capital_channel",
            "best_buyer_role": "2c2i application and program review team",
            "why_this_buyer_first": (
                "This is a current capital route rather than a buyer. It offers a meaningful investment range and "
                "an Impact Project, but LumenCore must first prove a measurable climate tie, an Exelon-territory "
                "deployment plan, community benefit, and traction without inventing those facts."
            ),
            "fit_score": 68,
            "proof_fit": [
                "grid resilience evidence",
                "climate adaptation decision support",
                "Impact Project measurement governance",
            ],
            "first_ask": (
                "Do not send the paid-review sales email. Audit the official application against climate, territory, "
                "community, traction, and equity-structure gates before deciding whether to apply by September 27, 2026."
            ),
            "buyer_data_needed": [
                "measurable climate mitigation or adaptation pathway",
                "specific Exelon-market operating plan",
                "community and environmental-justice benefit",
                "truthful traction and financing facts",
                "founder acceptance of equity, debt, or SAFE terms",
            ],
            "source_keys": ["exelon_2c2i"],
            "public_contact_route": {
                "type": "official_application_and_program_inbox",
                "address": SOURCE_REFS["exelon_2c2i"]["public_contact"],
                "authority": "Published on Exelon's official 2c2i application page",
            },
            "duplicate_check": {
                "checked_utc": SOURCE_VERIFIED_UTC,
                "scope": "Gmail all mail and Sent for Exelon and official Exelon domains",
                "relevant_prior_outbound_count": 0,
                "relevant_prior_inbound_count": 0,
                "duplicate_send_decision": "no_sales_email_application_fit_audit_required",
            },
            "risk_notes": [
                "The program is equity-bearing and may use common equity, preferred shares, debt, or a SAFE.",
                "Current LumenCore evidence does not by itself prove climate impact, local deployment, or traction fit.",
            ],
            "recommended_action_today": (
                "Preserve as a separate capital application lane; do not conflate it with the paid buyer outreach."
            ),
            "proof_line": proof_line,
        },
    ]

    for candidate in candidates:
        candidate["source_refs"] = [SOURCE_REFS[key] for key in candidate["source_keys"]]
        candidate["manual_review_required"] = True
        candidate["send_now_allowed"] = False
        if candidate["organization"].startswith("Exelon"):
            candidate["routing_status"] = "application_only_fit_gates_unresolved"
        elif candidate["organization"].startswith("Southern"):
            candidate["routing_status"] = "official_contact_route_recipient_unresolved_no_email_send"
        else:
            candidate["routing_status"] = "verified_clean_route_action_time_approval_required"
        candidate["source_freshness_status"] = (
            "official_route_reviewed_2026_08_04_action_time_refresh_required"
        )
        candidate["candidate_sha256"] = stable_sha256(
            {key: value for key, value in candidate.items() if key != "candidate_sha256"}
        )
    return sorted(candidates, key=lambda candidate: int(candidate["rank"]))


def make_primary_email(
    snapshot: dict[str, Any],
    candidate: dict[str, Any],
    commercial: dict[str, Any],
) -> dict[str, Any]:
    subject = "Fixed-scope evidence review for utility AI and grid analytics"
    route = as_dict(candidate.get("public_contact_route"))
    body = f"""Hello {candidate['organization']} team,

I am Robert Ashworth, founder of LumenCore. I am reaching out because your official innovation page describes a route for external ideas and collaboration. I am asking only whether this fixed-scope evidence-review service belongs with your team or should be routed to the appropriate owner.

LumenCore offers a fixed-scope, {commercial['candidate_duration_business_days']}-business-day source-native benchmark and evidence protocol review. For one authorized analytics use case, the review registers accepted incumbent baselines and metrics before comparison, preserves chronology, runs reproducible holdouts under identical constraints, and delivers a reviewer-ready packet that retains both positive and negative results.

The candidate fee is ${commercial['candidate_fee_usd']:,}, subject to written scope confirmation. This is a service-fee proposal, not a claim of field performance, savings, return on investment, or production control. No operational write access is required.

Would your team be open to a 20-minute fit call, or route me to the person responsible for AI, model validation, or grid-analytics pilot evaluation?

Reviewer surface: {snapshot['mission_control']}

Respectfully,
Robert Ashworth
LumenCore
[FOUNDER-APPROVED BUSINESS MAILING ADDRESS REQUIRED]

This is a one-time technical fit inquiry. Reply "remove" and no further outreach will be sent.
"""
    missing_facts = [
        "founder-approved business mailing address for the commercial-email footer",
        "founder approval of the exact recipient, candidate fee, subject, and final body hash",
        "confirmation that the official public route remains current at action time",
    ]
    packet = {
        "recipient_name": f"{candidate['organization']} team",
        "recipient_email": route.get("address", ""),
        "recipient_authority": route.get("authority", ""),
        "recipient_route_verified_utc": SOURCE_VERIFIED_UTC,
        "subject": subject,
        "body": body,
        "subject_sha256": text_sha256(subject),
        "body_sha256": text_sha256(body),
        "hashes_cover_placeholder_draft_only": True,
        "attachments": [],
        "attachment_count": 0,
        "cc": [],
        "bcc": [],
        "candidate_fee_usd": commercial["candidate_fee_usd"],
        "candidate_duration_business_days": commercial[
            "candidate_duration_business_days"
        ],
        "fee_status": commercial["fee_status"],
        "founder_approved": False,
        "buyer_accepted": False,
        "duplicate_check": candidate["duplicate_check"],
        "duplicate_send_decision": candidate["duplicate_check"][
            "duplicate_send_decision"
        ],
        "missing_facts": missing_facts,
        "send_ready": False,
        "send_mode": "draft_only_missing_compliance_fact_and_action_time_approval",
        "send_gate": "BLOCKED_BUSINESS_ADDRESS_AND_EXACT_ACTION_TIME_APPROVAL_REQUIRED",
        "why_not_autosend": (
            "The official public route is documented, but the final commercial footer, action-time duplicate check, "
            "and exact approval are missing. The current hashes cover a placeholder draft and cannot authorize a send."
        ),
    }
    packet["packet_sha256"] = stable_sha256(
        {key: value for key, value in packet.items() if key != "packet_sha256"}
    )
    return packet


def build_payload() -> dict[str, Any]:
    snapshot = proof_snapshot()
    commercial = commercial_offer_snapshot()
    candidates = make_candidates(snapshot, commercial)
    primary = candidates[0]
    excluded_historical_routes = [
        {
            "organization": "EPRI Open Power AI",
            "decision": "inbound_only_no_new_outreach",
            "basis": "Current local outreach policy records the completed onboarding and logo response; no resend is allowed.",
        },
        {
            "organization": "EPB Chattanooga",
            "decision": "exclude_duplicate_risk_no_new_outreach",
            "basis": "Full-thread mailbox check found four separate outbound messages and no inbound reply.",
            "relevant_prior_outbound_count": 4,
            "relevant_prior_inbound_count": 0,
        },
        {
            "organization": "TVA / Spark Cleantech",
            "decision": "exclude_duplicate_risk_no_new_outreach",
            "basis": "Full-thread mailbox check found three separate outbound messages across the TVA/Spark route and no inbound reply.",
            "relevant_prior_outbound_count": 3,
            "relevant_prior_inbound_count": 0,
        },
    ]
    payload = {
        "schema": "first_buyer_target_board_v3",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "summary": {
            "recommended_first_buyer": primary["organization"],
            "recommended_first_buyer_type": primary["buyer_channel_type"],
            "recommended_first_action": (
                "Insert and approve a business mailing address, refresh the official route and duplicate check at "
                "action time, then request exact approval for one no-attachment message."
            ),
            "candidate_count": len(candidates),
            "current_official_source_verified_count": len(candidates),
            "recipient_selected_count": 1,
            "exact_packet_prepared_count": 1,
            "send_ready_target_count": 0,
            "historical_duplicate_risk_route_count": 2,
            "manual_reviewed_outreach_allowed": False,
            "paid_protocol_review_scoping_allowed": True,
            "send_without_user_review_allowed": False,
            "bulk_email_allowed": False,
            "contact_scraping_allowed": False,
            "fixed_frozen_delta_price_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "realized_savings_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "proof_revenue_stage": snapshot["revenue_stage"],
            "proof_internal_performance_champion_present": snapshot[
                "internal_performance_champion_present"
            ],
            "proof_live_domain_hash_verified": snapshot["live_domain_hash_verified"],
            "proof_holdout_wins": snapshot["holdout_wins"],
            "proof_holdout_count": snapshot["holdout_count"],
            "proof_champion_source_system_count": snapshot["source_system_count"],
            "proof_broader_measured_provider_count": snapshot["broader_measured_provider_count"],
            "proof_locked_adapter_backed_routes": snapshot["locked_adapter_backed_routes"],
            "proof_locked_baseline_comparison_count": snapshot["locked_baseline_comparison_count"],
            "proof_locked_global_holm_positive_count": snapshot[
                "locked_global_holm_positive_count"
            ],
            "proof_locked_performance_rows_reviewed": snapshot[
                "locked_performance_rows_reviewed"
            ],
            "proof_legacy_ready_rows_excluded": snapshot[
                "legacy_ready_rows_excluded"
            ],
            "proof_numeric_fallback_profile_count": snapshot[
                "numeric_fallback_profile_count"
            ],
        },
        "proof_snapshot": snapshot,
        "commercial_offer": commercial,
        "source_refs": SOURCE_REFS,
        "current_route_verification": {
            "verified_utc": SOURCE_VERIFIED_UTC,
            "official_source_count": len(SOURCE_REFS),
            "gmail_scope": (
                "All Mail and Sent checks for Southern Company, PG&E, and Exelon names and official domains; "
                "full-thread checks for excluded EPB and TVA/Spark histories."
            ),
            "official_route_refresh_required_at_action_time": True,
            "mailbox_duplicate_refresh_required_at_action_time": True,
        },
        "excluded_historical_routes": excluded_historical_routes,
        "candidates": candidates,
        "primary_manual_email": make_primary_email(snapshot, primary, commercial),
        "claim_controls": {
            "allowed_today": [
                "draft a paid source-native protocol review offer",
                "verify one current official buyer channel",
                "reconcile sent history and routing controls",
                "prepare a bounded benchmark implementation scope",
            ],
            "blocked_until_action_time_clearance": [
                "send any outreach",
                "treat a selected public route as proof of buyer or procurement authority",
                "describe any family as a performance champion",
                "request a field replay for the current Kuramoto result",
                "field validated",
                "realized savings",
                "fixed price per frozen delta",
                "award certainty",
                "alpha certainty",
                "live operational control",
            ],
        },
        "next_30_minutes": [
            "Keep EPRI inbound-only and exclude the over-contacted EPB and TVA/Spark routes.",
            "Obtain or approve a non-residential LumenCore business mailing address for the one-time inquiry footer.",
            "Refresh the Southern Company official route and Gmail duplicate check immediately before any send.",
            "Recompute the final body hash after the footer is complete.",
            "Request exact action-time approval for the recipient, subject hash, body hash, zero attachments, and no CC/BCC.",
        ],
    }
    payload["first_buyer_board_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "proof_snapshot": payload["proof_snapshot"],
            "commercial_offer": payload["commercial_offer"],
            "candidates": payload["candidates"],
            "excluded_historical_routes": payload[
                "excluded_historical_routes"
            ],
            "primary_manual_email": payload["primary_manual_email"],
            "claim_controls": payload["claim_controls"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    snapshot = payload["proof_snapshot"]
    commercial = payload["commercial_offer"]
    route_verification = payload["current_route_verification"]
    email = payload["primary_manual_email"]
    lines = [
        "# First Buyer Target Board",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["boundary"],
        "",
        "## Decision",
        "",
        f"- First buyer channel: `{summary['recommended_first_buyer']}`",
        f"- Channel type: `{summary['recommended_first_buyer_type']}`",
        f"- First action: {summary['recommended_first_action']}",
        f"- Current official sources verified: `{summary['current_official_source_verified_count']}`",
        f"- Exact packets prepared: `{summary['exact_packet_prepared_count']}`",
        f"- Send-ready packets: `{summary['send_ready_target_count']}`",
        f"- Send without user review: `{str(summary['send_without_user_review_allowed']).lower()}`",
        f"- Bulk email allowed: `{str(summary['bulk_email_allowed']).lower()}`",
        f"- Field-validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Realized-savings claim allowed: `{str(summary['realized_savings_claim_allowed']).lower()}`",
        "",
        "## Proof Snapshot",
        "",
        f"- Internal performance champion present: `{str(snapshot['internal_performance_champion_present']).lower()}`",
        f"- Measured reference candidate: `{snapshot['reference_candidate_label']}`",
        f"- Development-selected candidate: `{snapshot['development_selected_candidate']}`",
        f"- Reference candidate was protocol-selected: `{str(snapshot['reference_candidate_was_protocol_selected']).lower()}`",
        f"- Named baseline: `{snapshot['named_baseline']}`",
        f"- Holdout wins: `{snapshot['holdout_wins']}/{snapshot['holdout_count']}`",
        f"- Mean skill delta: `{snapshot['mean_delta_vs_named_baseline']}`",
        f"- Reference measured rows replayed: `{snapshot['estimated_rows_replayed']:,}`",
        f"- Reference source systems: `{snapshot['source_system_count']}`",
        f"- Broader measured providers: `{snapshot['broader_measured_provider_count']}/{snapshot['broader_enabled_provider_count']}`",
        f"- Compatibility-gated sweep: `{snapshot['locked_adapter_backed_routes']}` routes, `{snapshot['locked_baseline_comparison_count']}` comparisons, `{snapshot['locked_global_holm_positive_count']}` global positives, `{snapshot['locked_performance_rows_reviewed']:,}` performance rows",
        f"- Live-domain hash verified: `{str(snapshot['live_domain_hash_verified']).lower()}`",
        f"- Business plan PDF: `{snapshot['business_plan_pdf']}`",
        f"- Stress matrix feed: {snapshot['stress_matrix_feed']}",
        "",
        "## Commercial Boundary",
        "",
        f"- Service: {commercial['service']}",
        f"- Candidate fee: `${commercial['candidate_fee_usd']:,}`",
        f"- Candidate duration: `{commercial['candidate_duration_business_days']}` business days",
        f"- Fee status: `{commercial['fee_status']}`",
        f"- Buyer accepted: `{str(commercial['buyer_accepted']).lower()}`",
        f"- External send allowed by source protocol: `{str(commercial['external_send_allowed']).lower()}`",
        "",
        "## Route Verification",
        "",
        f"- Verified UTC: `{route_verification['verified_utc']}`",
        f"- Official sources checked: `{route_verification['official_source_count']}`",
        f"- Mailbox scope: {route_verification['gmail_scope']}",
        f"- Refresh official route at action time: `{str(route_verification['official_route_refresh_required_at_action_time']).lower()}`",
        f"- Refresh duplicate check at action time: `{str(route_verification['mailbox_duplicate_refresh_required_at_action_time']).lower()}`",
        "",
        "## Ranked Buyer Targets",
        "",
    ]
    for candidate in payload["candidates"]:
        lines.extend(
            [
                f"### {candidate['rank']}. {candidate['organization']}",
                "",
                f"- Buyer role: {candidate['best_buyer_role']}",
                f"- Fit score: `{candidate['fit_score']}`",
                f"- Why first: {candidate['why_this_buyer_first']}",
                f"- First ask: {candidate['first_ask']}",
                f"- Data needed: {', '.join(candidate['buyer_data_needed'])}",
                f"- Routing status: `{candidate['routing_status']}`",
                f"- Public route type: `{candidate['public_contact_route']['type']}`",
                f"- Public route: `{candidate['public_contact_route']['address']}`",
                f"- Duplicate decision: `{candidate['duplicate_check']['duplicate_send_decision']}`",
                f"- Prior relevant outbound/inbound: `{candidate['duplicate_check']['relevant_prior_outbound_count']}/{candidate['duplicate_check']['relevant_prior_inbound_count']}`",
                f"- Send now allowed: `{str(candidate['send_now_allowed']).lower()}`",
                "- Sources:",
            ]
        )
        for source in candidate["source_refs"]:
            lines.append(f"  - {source['url']} - {source['fact']}")
        lines.append("")
    lines.extend(
        [
            "## Excluded Historical Routes",
            "",
        ]
    )
    for excluded in payload["excluded_historical_routes"]:
        counts = ""
        if "relevant_prior_outbound_count" in excluded:
            counts = (
                " Prior relevant outbound/inbound: "
                f"`{excluded['relevant_prior_outbound_count']}/{excluded['relevant_prior_inbound_count']}`."
            )
        lines.append(
            f"- **{excluded['organization']}**: `{excluded['decision']}`. {excluded['basis']}{counts}"
        )
    lines.extend(
        [
            "",
            "## Selected Draft Packet",
            "",
            f"- Recipient: {email['recipient_name']} `<{email['recipient_email']}>`",
            f"- Recipient authority: {email['recipient_authority']}",
            f"- Route verified UTC: `{email['recipient_route_verified_utc']}`",
            f"- Candidate fee/duration: `${email['candidate_fee_usd']:,}` / `{email['candidate_duration_business_days']}` business days",
            f"- Attachments: `{email['attachment_count']}`",
            f"- CC/BCC: `{len(email['cc'])}/{len(email['bcc'])}`",
            f"- Subject SHA-256: `{email['subject_sha256']}`",
            f"- Body SHA-256: `{email['body_sha256']}`",
            f"- Packet SHA-256: `{email['packet_sha256']}`",
            f"- Placeholder-draft hashes only: `{str(email['hashes_cover_placeholder_draft_only']).lower()}`",
            f"- Send ready: `{str(email['send_ready']).lower()}`",
            f"- Send gate: `{email['send_gate']}`",
            f"- Missing facts: {', '.join(email['missing_facts'])}",
            "",
            f"Subject: {email['subject']}",
            "",
            "```text",
            email["body"].rstrip(),
            "```",
            "",
            "## Claim Controls",
            "",
            "- Allowed today: " + ", ".join(payload["claim_controls"]["allowed_today"]),
            "- Blocked until action-time clearance: "
            + ", ".join(
                payload["claim_controls"][
                    "blocked_until_action_time_clearance"
                ]
            ),
            "",
            f"First-buyer board SHA-256: `{payload['first_buyer_board_sha256']}`",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"wrote {OUT_JSON}")
    print(f"wrote {DASHBOARD_JSON}")
    print(f"wrote {OUT_MD}")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
