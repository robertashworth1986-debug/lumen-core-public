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

OUT_JSON = OUT_OPS / "first_buyer_target_board_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "first_buyer_target_board.json"
OUT_MD = DOCS / "FIRST_BUYER_TARGET_BOARD_2026-06-27.md"
UPDATED_BUSINESS_PLAN_PDF = Path(
    r"C:\Users\Novac\iCloudDrive\Business plan\LumenCore_Business_Plan_Investor_Ready_UPDATED_2026-07-03.pdf"
)

BOUNDARY = (
    "First-buyer target board. This artifact selects named, source-verified buyer channels for a manual paid "
    "evidence review or buyer-authorized field replay. It does not authorize auto-send, bulk outreach, contact "
    "scraping, fixed frozen-delta pricing, field-validation claims, realized-savings claims, live trading, or "
    "autonomous operational execution."
)


SOURCE_REFS: dict[str, dict[str, str]] = {
    "epri_iel": {
        "url": "https://epri.brightidea.com/community/iel",
        "fact": "Incubatenergy Labs, powered by EPRI, runs quick paid demonstrations with leading utilities, typically within 16 weeks.",
    },
    "epri_ai_power": {
        "url": "https://epri.brightidea.com/AIforPower2026",
        "fact": "AI for Power 2026 connects energy companies, technology providers, and utilities through real-world demonstration projects; pitch day is listed for August 5, 2026.",
    },
    "opai": {
        "url": "https://openpowerai.org/",
        "fact": "Open Power AI describes the AI for Power Challenge as a pathway for utilities, EPRI, and technology providers to collaborate, test, validate, and de-risk AI solutions.",
    },
    "epb_grid": {
        "url": "https://epb.com/energy/automated-grid/",
        "fact": "EPB reports an Automated Grid with outage-minute reduction, real-time usage data, microgrid research, and seconds-scale rerouting.",
    },
    "epb_ornl": {
        "url": "https://epb.com/newsroom/press-releases/microgrid-research-partnership/",
        "fact": "EPB and ORNL describe a long-running partnership to test and deploy innovative controls, sensor systems, building energy models, security, and quantum/supercomputing grid platforms.",
    },
    "tva_future_grid": {
        "url": "https://www.tva.com/energy/technology-innovation/future-grid-performance",
        "fact": "TVA identifies future grid performance challenges tied to renewables, storage, weather-dependent resources, and inverter-based resources.",
    },
    "tva_spark": {
        "url": "https://www.tnresearchpark.org/tva-%F0%9F%A4%9D-spark-cleantech-accelerator/",
        "fact": "TVA sponsors Spark Cleantech Accelerator activity aligned with future grid performance, regional grid transformation, storage integration, and pilot commercialization.",
    },
    "spark_accelerator": {
        "url": "https://www.tnresearchpark.org/spark/accelerator/",
        "fact": "Spark Accelerator offers mentorship, prototyping, customer and partner connections, and partnership opportunities including TVA and ORNL.",
    },
    "doe_grip": {
        "url": "https://www.energy.gov/oe/grid-resilience-and-innovation-partnerships-grip",
        "fact": "DOE's GRIP program targets grid flexibility, reliability, resilience, disruptive events, load growth, cybersecurity, and transformational grid projects.",
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


def make_candidates(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
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

    candidates = [
        {
            "rank": 1,
            "organization": "EPRI AI for Power / Incubatenergy Labs",
            "buyer_channel_type": "national_utility_demonstration_channel",
            "best_buyer_role": "AI for Power / Incubatenergy Labs program reviewer",
            "why_this_buyer_first": (
                "Highest leverage: one accepted demo path can expose the proof stack to multiple utilities and AI/power "
                "decision makers without pretending LumenCore is field validated already."
            ),
            "fit_score": 98,
            "proof_fit": [
                "energy forecasting",
                "grid reliability analytics",
                "power-sector AI validation",
                "field replay and demo scoping",
            ],
            "first_ask": (
                "Request a late technical fit review or next-cycle demo intake: a paid evidence review that uses "
                "EPRI/utility-approved baseline, holdout windows, and pass/fail metrics."
            ),
            "buyer_data_needed": [
                "utility-owned time-series operating data",
                "incumbent forecast/filter baseline",
                "pre-registered holdout windows",
                "accepted reliability or forecast-error metric",
                "economic conversion factors only after technical replay passes",
            ],
            "source_keys": ["epri_iel", "epri_ai_power", "opai"],
            "risk_notes": [
                "May 2026 application window may be closed; use as immediate warm-review target and next-cycle channel.",
                "Do not claim EPRI acceptance until they explicitly respond.",
            ],
            "recommended_action_today": "Monitor the existing inbound-only EPRI channel; do not send a new inquiry.",
            "proof_line": proof_line,
        },
        {
            "rank": 2,
            "organization": "EPB Chattanooga / ORNL grid resilience research path",
            "buyer_channel_type": "direct_grid_owner_and_research_partner",
            "best_buyer_role": "Grid reliability analytics or microgrid research lead",
            "why_this_buyer_first": (
                "Most concrete field-validation fit: EPB has an automated grid, microgrid research, real-time usage data, "
                "and a stated history of testing controls and sensor systems with ORNL."
            ),
            "fit_score": 96,
            "proof_fit": [
                "seconds-scale grid rerouting",
                "outage lead-time and restoration analytics",
                "microgrid reliability",
                "sensor/control data replay",
            ],
            "first_ask": (
                "Ask for a 20-minute local technical fit call to scope a sealed replay on historical outage, reroute, "
                "or microgrid time-series windows."
            ),
            "buyer_data_needed": [
                "historical feeder/microgrid event windows",
                "current automated-grid decision or forecast baseline",
                "outage-minute, reroute-time, or false-alarm metric",
                "guardrails for no operational control",
                "approved anonymization and data-use terms",
            ],
            "source_keys": ["epb_grid", "epb_ornl"],
            "risk_notes": [
                "Likely needs a partner/intro route; do not approach as if EPB has purchased anything.",
                "Keep ask to replay and report, not live control.",
            ],
            "recommended_action_today": "Prepare a one-page EPB/ORNL-specific field replay ask and request the right reviewer.",
            "proof_line": proof_line,
        },
        {
            "rank": 3,
            "organization": "TVA / Spark Cleantech Accelerator bridge",
            "buyer_channel_type": "regional_commercialization_and_utility_partner_bridge",
            "best_buyer_role": "TVA ecosystem partnerships, future grid performance, or Spark accelerator reviewer",
            "why_this_buyer_first": (
                "Strong regional fit: TVA's technology priorities include future grid performance and regional grid "
                "transformation, while Spark offers customer, partner, TVA, and ORNL connections."
            ),
            "fit_score": 94,
            "proof_fit": [
                "future grid performance",
                "regional grid transformation",
                "storage and variable-resource planning",
                "cleantech commercialization",
            ],
            "first_ask": (
                "Ask Spark/TVA for a technical mentor review and a route to one buyer-approved replay dataset or "
                "pilot sponsor."
            ),
            "buyer_data_needed": [
                "regional grid planning or forecasting dataset",
                "current planning/forecast baseline",
                "accepted operational KPI",
                "pilot sponsor and data-rights path",
            ],
            "source_keys": ["tva_future_grid", "tva_spark", "spark_accelerator"],
            "risk_notes": [
                "Accelerator timing may not match today's cash deadline.",
                "Use it as the warmest regional bridge, not the only revenue path.",
            ],
            "recommended_action_today": "Draft a Spark/TVA proof-to-pilot message and ask for the right technical reviewer.",
            "proof_line": proof_line,
        },
        {
            "rank": 4,
            "organization": "DOE GRIP ecosystem partner",
            "buyer_channel_type": "federal_grid_resilience_partner_channel",
            "best_buyer_role": "Utility, local government, or grid-resilience project lead seeking software evidence",
            "why_this_buyer_first": (
                "GRIP is not a direct buyer, but it points to the exact class of utilities and public-sector partners "
                "funded for grid flexibility, resilience, reliability, and early measurable impacts."
            ),
            "fit_score": 88,
            "proof_fit": [
                "grid resilience",
                "reliability evidence",
                "forecasting and early warning",
                "grant-backed field validation",
            ],
            "first_ask": (
                "Use the proof stack as a subcontractor/pilot module in a utility or local-government GRIP-style "
                "resilience project."
            ),
            "buyer_data_needed": [
                "project-owned grid reliability dataset",
                "grant-recognized resilience metric",
                "field replay authorization",
                "awardee or applicant partner signoff",
            ],
            "source_keys": ["doe_grip"],
            "risk_notes": [
                "This is a funding and partner channel, not an immediate cash customer.",
                "Requires partner eligibility and procurement compliance.",
            ],
            "recommended_action_today": "Search current GRIP awardees or applicants for one local grid-resilience partner.",
            "proof_line": proof_line,
        },
        {
            "rank": 5,
            "organization": "Data center power/cooling operations partner",
            "buyer_channel_type": "secondary_private_infrastructure_buyer",
            "best_buyer_role": "Data center energy, cooling, or reliability optimization lead",
            "why_this_buyer_first": (
                "High potential value, but weaker immediate access. Use after the grid buyer lane because private "
                "data-center validation usually requires trust, procurement, and data-rights maturity."
            ),
            "fit_score": 81,
            "proof_fit": [
                "thermal/cooling optimization",
                "energy forecasting",
                "anomaly lead time",
                "load and uptime risk",
            ],
            "first_ask": (
                "Ask for an offline replay against historical load/cooling event windows; no live operations access."
            ),
            "buyer_data_needed": [
                "historical load, cooling, and temperature telemetry",
                "current cooling-control baseline",
                "energy and uptime metrics",
                "security review and NDA",
            ],
            "source_keys": ["epri_ai_power", "tva_future_grid"],
            "risk_notes": [
                "Large buyers are slow without a warm intro.",
                "Keep as second wave unless a direct contact already exists.",
            ],
            "recommended_action_today": "Hold until after one utility/research-channel inquiry is sent.",
            "proof_line": proof_line,
        },
    ]

    for candidate in candidates:
        candidate["source_refs"] = [SOURCE_REFS[key] for key in candidate["source_keys"]]
        candidate["manual_review_required"] = True
        candidate["send_now_allowed"] = False
        candidate["routing_status"] = (
            "inbound_only_no_new_outreach"
            if candidate["organization"].startswith("EPRI")
            else "official_source_duplicate_and_recipient_check_required"
        )
        candidate["source_freshness_status"] = (
            "historical_reference_requires_action_time_official_verification"
        )
        candidate["candidate_sha256"] = stable_sha256(
            {key: value for key, value in candidate.items() if key != "candidate_sha256"}
        )
    return candidates


def make_primary_email(snapshot: dict[str, Any], candidate: dict[str, Any]) -> dict[str, str]:
    reference = snapshot["reference_candidate_label"]
    baseline = snapshot["named_baseline"]
    body = f"""Hello [Name],

I am Robert Ashworth, building LumenCore, a source-native evidence and benchmark framework for infrastructure analytics.

I am looking for the right technical reviewer for one bounded paid protocol review or benchmark implementation. The current measured result is deliberately a negative one: {reference} won {snapshot['holdout_wins']}/{snapshot['holdout_count']} paired EIA holdout days versus {baseline}, had a mean skill delta of {snapshot['mean_delta_vs_named_baseline']:.6f}, and did not clear the complete source-specific baseline gate.

The offer is the governed method, not a claim that this candidate wins: map one authorized source to the correct task, register accepted incumbent baselines, freeze chronology and metrics, run the comparison reproducibly, and deliver a reviewer-ready packet that preserves positive and negative results.

Would you be open to a 20-minute technical fit call about a fixed-scope source-native benchmark and evidence protocol review?

Respectfully,
Robert Ashworth
[physical mailing address]

To stop further outreach, reply "remove."
"""
    return {
        "subject": "Source-native benchmark and evidence protocol review",
        "body": body,
        "send_mode": "draft_only_not_ready_to_send",
        "why_not_autosend": "No recipient is selected. Official-source freshness, routing policy, duplicate-send history, recipient fit, and exact action-time approval are required first.",
    }


def build_payload() -> dict[str, Any]:
    snapshot = proof_snapshot()
    candidates = make_candidates(snapshot)
    primary = candidates[0]
    payload = {
        "schema": "first_buyer_target_board_v2",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "summary": {
            "recommended_first_buyer": None,
            "recommended_first_buyer_type": None,
            "recommended_first_action": (
                "Verify one current official channel, reconcile duplicate-send "
                "history, select a real recipient, and obtain exact action-time "
                "approval before outreach."
            ),
            "candidate_count": len(candidates),
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
        "source_refs": SOURCE_REFS,
        "candidates": candidates,
        "primary_manual_email": make_primary_email(snapshot, primary),
        "claim_controls": {
            "allowed_today": [
                "draft a paid source-native protocol review offer",
                "verify one current official buyer channel",
                "reconcile sent history and routing controls",
                "prepare a bounded benchmark implementation scope",
            ],
            "blocked_until_action_time_clearance": [
                "send any outreach",
                "select or imply a current recipient",
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
            "Keep EPRI inbound-only unless a genuinely new inbound message changes routing.",
            "Refresh one non-EPRI candidate from its current official source.",
            "Check Gmail Sent and the outreach reconciliation ledger for duplicates.",
            "Select a recipient only after channel, fit, and routing checks pass.",
            "Request exact action-time approval for the final recipient, subject, body, and attachments.",
        ],
    }
    payload["first_buyer_board_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "proof_snapshot": payload["proof_snapshot"],
            "candidates": payload["candidates"],
            "claim_controls": payload["claim_controls"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    snapshot = payload["proof_snapshot"]
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
                f"- Send now allowed: `{str(candidate['send_now_allowed']).lower()}`",
                "- Sources:",
            ]
        )
        for source in candidate["source_refs"]:
            lines.append(f"  - {source['url']} - {source['fact']}")
        lines.append("")
    lines.extend(
        [
            "## Draft Email",
            "",
            f"Subject: {payload['primary_manual_email']['subject']}",
            "",
            "```text",
            payload["primary_manual_email"]["body"].rstrip(),
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
