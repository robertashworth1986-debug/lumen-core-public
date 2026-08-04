from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

LIVE_DOMAIN_JSON = OUT_OPS / "live_domain_deployment_feed_latest.json"
GAUNTLET_JSON = OUT_OPS / "champion_metric_gauntlet_latest.json"
CROSS_SECTOR_JSON = OUT_OPS / "kuramoto_cross_sector_benchmark_latest.json"
PROOF_TO_PILOT_JSON = OUT_OPS / "proof_to_pilot_control_room_latest.json"
VALUATION_JSON = OUT_OPS / "valuation_proposal_target_packet_latest.json"
PRODUCT_PRIORITY_JSON = DASHBOARD_DATA / "product_lane_priority_engine_20260718.json"
FIRST_BUYER_JSON = DASHBOARD_DATA / "first_buyer_target_board.json"
LEGACY_OUTREACH_JSON = OUT_OPS / "paid_pilot_outreach_queue_latest.json"

OUT_JSON = OUT_OPS / "proof_to_revenue_engine_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "proof_to_revenue_engine.json"
OUT_MD = DOCS / "PROOF_TO_REVENUE_ENGINE_2026-06-27.md"


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
    temporary.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")
    os.replace(temporary, path)


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def format_usd_range(price: dict[str, Any]) -> str:
    low = int(price.get("low") or 0)
    high = int(price.get("high") or 0)
    if low <= 0 or high <= 0:
        return "price pending"
    if low == high:
        return f"${low:,}"
    return f"${low:,}-${high:,}"


def require_inputs() -> dict[str, dict[str, Any]]:
    inputs = {
        "live": read_json(LIVE_DOMAIN_JSON),
        "gauntlet": read_json(GAUNTLET_JSON),
        "cross_sector": read_json(CROSS_SECTOR_JSON),
        "proof_to_pilot": read_json(PROOF_TO_PILOT_JSON),
        "valuation": read_json(VALUATION_JSON),
        "product_priority": read_json(PRODUCT_PRIORITY_JSON),
        "first_buyer": read_json(FIRST_BUYER_JSON),
        "legacy_outreach": read_json(LEGACY_OUTREACH_JSON),
    }
    expected = {
        "live": "live_domain_deployment_feed_v1",
        "gauntlet": "champion_metric_gauntlet_v2",
        "cross_sector": "lumencore.kuramoto_cross_sector_benchmark.v1",
        "proof_to_pilot": "proof_to_pilot_control_room_v2",
        "valuation": "valuation_proposal_target_packet_v3",
        "product_priority": "product_lane_priority_engine_v1",
        "first_buyer": "first_buyer_target_board_v3",
    }
    for name, schema in expected.items():
        actual = inputs[name].get("schema")
        if actual != schema:
            raise ValueError(f"{name} must use {schema}; found {actual!r}")
    return inputs


def product_offer(product: dict[str, Any]) -> dict[str, Any]:
    internal_gate = bool(product.get("internal_evidence_gate_passed"))
    buyer_gate = as_dict(product.get("buyer_readiness_gate"))
    return {
        "product_lane_id": product.get("id"),
        "name": product.get("name"),
        "offer": product.get("offer"),
        "recurring_model": product.get("recurring_model"),
        "validated_evidence_coverage": product.get(
            "validated_evidence_coverage"
        ),
        "validated_evidence_count": product.get("validated_evidence_count"),
        "required_evidence_count": product.get("required_evidence_count"),
        "internal_evidence_gate_passed": internal_gate,
        "buyer_readiness_gate": buyer_gate,
        "first_validation": product.get("first_validation"),
        "pricing_status": "scope_before_quote_no_price_asserted",
        "product_process_scoping_allowed": internal_gate,
        "external_outreach_ready": False,
        "model_performance_dependency": False,
        "claim_boundary": (
            "This offer is for a human-controlled opportunity workflow. It does "
            "not inherit performance, savings, award, or field-validation claims "
            "from the geometry research lane."
        ),
    }


def safe_draft_template(product: dict[str, Any], proof_offer: dict[str, Any]) -> dict[str, Any]:
    name = str(product.get("name") or "ProofLock Opportunity Operations")
    return {
        "recipient_selected": False,
        "subject": f"Technical fit review: {name}",
        "body": "\n".join(
            [
                "Hello [Name],",
                "",
                (
                    f"I am seeking a technical fit review for {name}, a "
                    "human-controlled workflow for opportunity discovery, evidence "
                    "assembly, preflight, and receipts."
                ),
                "",
                (
                    "The request is a bounded workflow or evidence-protocol review. "
                    "I am not claiming guaranteed awards, model superiority, field "
                    "validation, realized savings, or autonomous final submission."
                ),
                "",
                (
                    "Would a 20-minute fit call be appropriate after we verify the "
                    "official route, current recipient, workflow baseline, acceptance "
                    "criteria, and human approval gates?"
                ),
                "",
                (
                    "The separate source-native protocol-review service has a "
                    f"candidate fee of {format_usd_range(proof_offer)}, subject to "
                    "founder approval and written scope confirmation; product "
                    "workflow pricing is quoted only after scope."
                ),
                "",
                "Respectfully,",
                "Robert Ashworth",
            ]
        ),
        "status": "draft_only_no_recipient_not_ready_to_send",
        "send_allowed": False,
        "why_not_ready": (
            "Current official route, duplicate-send history, recipient fit, live "
            "reviewer URL, and exact action-time approval are unresolved."
        ),
    }


def build_payload() -> dict[str, Any]:
    inputs = require_inputs()
    live_summary = as_dict(inputs["live"].get("summary"))
    gauntlet_summary = as_dict(inputs["gauntlet"].get("summary"))
    strongest = as_dict(inputs["gauntlet"].get("strongest_current"))
    cross_gates = as_dict(inputs["cross_sector"].get("gates"))
    pilot_summary = as_dict(inputs["proof_to_pilot"].get("summary"))
    valuation_state = as_dict(inputs["valuation"].get("valuation_state"))
    current_priceable = as_dict(
        valuation_state.get("current_priceable_offer")
    )
    first_summary = as_dict(inputs["first_buyer"].get("summary"))
    first_packet = as_dict(inputs["first_buyer"].get("primary_manual_email"))
    first_candidates = [
        as_dict(row)
        for row in as_list(inputs["first_buyer"].get("candidates"))
        if as_dict(row)
    ]
    first_candidate = first_candidates[0] if first_candidates else {}
    recipient_selected = bool(first_packet.get("recipient_email"))
    ranking = [
        as_dict(row)
        for row in as_list(inputs["product_priority"].get("ranking"))
        if as_dict(row)
    ]
    product = ranking[0] if ranking else {}
    if not product:
        raise ValueError("A ranked product-process lane is required")

    live_hash_verified = (
        live_summary.get("domain_deployment_state") == "LIVE_DOMAIN_HASH_VERIFIED"
        and bool(live_summary.get("live_domain_reviewer_ready"))
    )
    external_outreach_ready = False
    revenue_stage = (
        "bounded_product_and_protocol_discovery_recipient_selected_send_blocked"
        if live_hash_verified
        else "bounded_offers_ready_local_only_domain_stale_recipient_selected_send_blocked"
    )
    protocol_price = as_dict(
        current_priceable.get("paid_protocol_review_usd")
    )
    benchmark_price = as_dict(
        current_priceable.get("benchmark_implementation_usd")
    )
    product_process_offer = product_offer(product)

    payload: dict[str, Any] = {
        "schema": "proof_to_revenue_engine_v3",
        "generated_utc": now_utc(),
        "boundary": (
            "This engine separates a product-process offer from geometry-model "
            "performance evidence. It can scope a bounded protocol review or "
            "human-controlled workflow product locally. It does not authorize "
            "external outreach, pricing based on model gains, field or savings "
            "claims, guaranteed awards, live trading, or autonomous submissions."
        ),
        "summary": {
            "revenue_stage": revenue_stage,
            "live_domain_hash_verified": live_hash_verified,
            "required_remote_hash_matches": int(
                live_summary.get("required_remote_hash_match_count") or 0
            ),
            "required_feed_count": int(
                live_summary.get("required_feed_count") or 0
            ),
            "sellable_product_lane": product.get("id"),
            "sellable_product_name": product.get("name"),
            "product_internal_evidence_gate_passed": bool(
                product_process_offer["internal_evidence_gate_passed"]
            ),
            "product_buyer_readiness_gate_passed": bool(
                as_dict(
                    product_process_offer.get("buyer_readiness_gate")
                ).get("passed")
            ),
            "product_process_scoping_allowed": bool(
                product_process_offer["product_process_scoping_allowed"]
            ),
            "internal_performance_champion_present": False,
            "measured_reference_candidate": strongest.get("family"),
            "development_selected_candidate": strongest.get(
                "development_selected_candidate"
            ),
            "reference_candidate_was_protocol_selected": bool(
                strongest.get("candidate_was_protocol_selected")
            ),
            "internal_replay_named_baseline": gauntlet_summary.get(
                "named_baseline"
            ),
            "internal_replay_holdout_wins": gauntlet_summary.get(
                "holdout_wins"
            ),
            "internal_replay_holdout_count": gauntlet_summary.get(
                "holdout_count"
            ),
            "internal_replay_mean_delta": gauntlet_summary.get(
                "mean_delta_vs_named_baseline"
            ),
            "cross_sector_benchmark_status": inputs["cross_sector"].get(
                "status"
            ),
            "cross_sector_sector_count": int(
                cross_gates.get("sector_count") or 0
            ),
            "cross_sector_gain_proven_count": int(
                cross_gates.get("sector_gain_proven_count") or 0
            ),
            "cross_sector_efficiency_claim_allowed": False,
            "model_performance_marketing_allowed": False,
            "safe_estimated_hourly_value_usd": 0.0,
            "safe_estimated_annual_value_usd": 0.0,
            "modeled_dollar_projection_allowed": False,
            "paid_protocol_review_scoping_allowed": bool(
                pilot_summary.get("paid_protocol_review_scoping_allowed")
            ),
            "pilot_ready_count": int(
                pilot_summary.get("pilot_ready_count") or 0
            ),
            "manual_reviewed_outreach_allowed": False,
            "external_outreach_ready": external_outreach_ready,
            "send_without_user_review_allowed": False,
            "bulk_email_allowed": False,
            "field_validation_claim_allowed": False,
            "realized_savings_claim_allowed": False,
            "fixed_frozen_delta_price_claim_allowed": False,
            "enterprise_valuation_asserted": bool(
                valuation_state.get("enterprise_valuation_asserted")
            ),
            "live_trading_or_autonomous_execution_allowed": False,
            "recommended_first_buyer": first_summary.get(
                "recommended_first_buyer"
            ),
            "plain_english_answer": (
                "LumenCore has two bounded commercial paths that do not depend on "
                "a winning geometry model: a source-native benchmark and evidence "
                "protocol review, and a human-controlled ProofLock opportunity "
                "workflow discovery engagement. The top product lane passes its "
                "typed internal artifact checks but remains blocked at buyer "
                "validation and external outreach. No current geometry family is a "
                "performance champion, the cross-sector benchmark found zero proven "
                "sector gains, the live reviewer domain has stale hashes, and no "
                "buyer acceptance is proven. One current public route and bounded "
                "protocol-review draft are selected, but the footer, action-time "
                "route refresh, and exact packet approval remain unresolved."
            ),
        },
        "commercial_offers": {
            "source_native_protocol_review": {
                "price_usd": protocol_price,
                "status": "scope_ready_not_performance_pricing",
                "offer": "source-task mapping, baseline registration, frozen chronology, reproducible execution, and claim-boundary review",
            },
            "benchmark_implementation": {
                "price_usd": benchmark_price,
                "status": "custom_scope_after_data_rights_and_acceptance_criteria",
            },
            "product_process_discovery": product_process_offer,
        },
        "safe_draft_template": safe_draft_template(product, protocol_price),
        "top_manual_targets": [
            {
                "organization": first_candidate.get("organization"),
                "buyer_channel_type": first_candidate.get("buyer_channel_type"),
                "routing_status": first_candidate.get("routing_status"),
                "send_now_allowed": False,
            }
        ]
        if first_candidate
        else [],
        "selected_protocol_review_packet": {
            "recipient_name": first_packet.get("recipient_name"),
            "recipient_email": first_packet.get("recipient_email"),
            "subject": first_packet.get("subject"),
            "subject_sha256": first_packet.get("subject_sha256"),
            "body_sha256": first_packet.get("body_sha256"),
            "packet_sha256": first_packet.get("packet_sha256"),
            "attachment_count": int(first_packet.get("attachment_count") or 0),
            "send_ready": bool(first_packet.get("send_ready")),
            "send_gate": first_packet.get("send_gate"),
            "hashes_cover_placeholder_draft_only": bool(
                first_packet.get("hashes_cover_placeholder_draft_only")
            ),
        },
        "target_status": {
            "recipient_selected": recipient_selected,
            "recommended_first_buyer": first_summary.get(
                "recommended_first_buyer"
            ),
            "packet_send_ready": bool(first_packet.get("send_ready")),
            "packet_send_gate": first_packet.get("send_gate"),
            "legacy_paid_pilot_queue_excluded": bool(
                inputs["legacy_outreach"]
            ),
            "legacy_paid_pilot_queue_schema": inputs["legacy_outreach"].get(
                "schema"
            ),
            "legacy_paid_pilot_queue_generated_utc": inputs[
                "legacy_outreach"
            ].get("generated_utc"),
            "exclusion_reason": (
                "The June 27 queue predates the current nonpromotion and no-send "
                "contracts and is not an action source."
            ),
        },
        "current_model_evidence": {
            "candidate_family": strongest.get("family"),
            "development_selected_candidate": strongest.get(
                "development_selected_candidate"
            ),
            "candidate_was_protocol_selected": strongest.get(
                "candidate_was_protocol_selected"
            ),
            "direct_measured_result": (
                f"{gauntlet_summary.get('holdout_wins')}/"
                f"{gauntlet_summary.get('holdout_count')} paired EIA days "
                f"against {gauntlet_summary.get('named_baseline')}; mean skill "
                f"{gauntlet_summary.get('mean_delta_vs_named_baseline')}"
            ),
            "cross_sector_status": inputs["cross_sector"].get("status"),
            "sector_gain_proven_count": int(
                cross_gates.get("sector_gain_proven_count") or 0
            ),
            "sector_count": int(cross_gates.get("sector_count") or 0),
            "external_cross_sector_replication_complete": bool(
                cross_gates.get("external_cross_sector_replication_complete")
            ),
            "prospective_cross_sector_holdout_complete": bool(
                cross_gates.get("prospective_cross_sector_holdout_complete")
            ),
            "safest_next_action": inputs["cross_sector"].get(
                "safest_next_action"
            ),
            "claim_boundary": inputs["cross_sector"].get("claim_boundary"),
        },
        "external_unlock": [
            "refresh and verify every required live-domain proof-feed hash",
            "refresh the selected current official route at action time",
            "reconcile duplicate-send history again at action time",
            "replace the business-mailing-address placeholder with founder-approved footer text",
            "freeze the buyer's current workflow baseline and acceptance criteria",
            "obtain exact action-time approval before external outreach",
        ],
        "what_to_ask_next": [
            "Which product-process workflow has urgent pain independent of model performance?",
            "What is the buyer's current time-to-pursue and package-quality baseline?",
            "Which source portals and eligibility rules may the workflow use?",
            "Which acceptance metrics and cutoff times will be frozen before work begins?",
            "Who owns unresolved facts, attachments, certifications, and final submission?",
            "Does the buyer need a protocol review, benchmark implementation, or workflow discovery engagement?",
            "What current official route and recipient are verified?",
            "What prior sends or packets must be reconciled before contact?",
            "Which negative scientific results must remain visible?",
            "Who gives exact action-time approval for any external send?",
        ],
        "claim_controls": {
            "allowed": [
                "bounded source-native protocol-review pricing",
                "bounded benchmark-implementation pricing",
                "human-controlled product-process discovery scoping",
                "measured nonpromotion and negative cross-sector evidence",
            ],
            "blocked": [
                "current geometry performance champion",
                "cross-sector efficiency gain",
                "modeled dollar projection from forecast error",
                "field validation",
                "realized savings",
                "fixed value per frozen delta",
                "enterprise valuation from current evidence",
                "guaranteed funding or award",
                "guaranteed trading profit",
                "bulk or unapproved outreach",
            ],
        },
        "source_status": {
            "live_domain_loaded": bool(inputs["live"]),
            "gauntlet_loaded": bool(inputs["gauntlet"]),
            "cross_sector_benchmark_loaded": bool(inputs["cross_sector"]),
            "proof_to_pilot_loaded": bool(inputs["proof_to_pilot"]),
            "valuation_loaded": bool(inputs["valuation"]),
            "product_priority_loaded": bool(inputs["product_priority"]),
            "first_buyer_loaded": bool(inputs["first_buyer"]),
            "legacy_outreach_queue_excluded": True,
        },
    }
    payload["proof_to_revenue_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "commercial_offers": payload["commercial_offers"],
            "target_status": payload["target_status"],
            "current_model_evidence": payload["current_model_evidence"],
            "external_unlock": payload["external_unlock"],
            "claim_controls": payload["claim_controls"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    offers = payload["commercial_offers"]
    protocol = offers["source_native_protocol_review"]["price_usd"]
    benchmark = offers["benchmark_implementation"]["price_usd"]
    product = offers["product_process_discovery"]
    evidence = payload["current_model_evidence"]
    lines = [
        "# Proof To Revenue Engine",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["boundary"],
        "",
        "## Current State",
        "",
        summary["plain_english_answer"],
        "",
        f"- Revenue stage: `{summary['revenue_stage']}`",
        f"- Live domain hash verified: `{str(summary['live_domain_hash_verified']).lower()}`",
        f"- Required remote hash matches: `{summary['required_remote_hash_matches']}/{summary['required_feed_count']}`",
        f"- Internal performance champion present: `{str(summary['internal_performance_champion_present']).lower()}`",
        f"- Pilot-ready candidates: `{summary['pilot_ready_count']}`",
        f"- Manual reviewed outreach allowed: `{str(summary['manual_reviewed_outreach_allowed']).lower()}`",
        f"- External outreach ready: `{str(summary['external_outreach_ready']).lower()}`",
        f"- Modeled dollar projection allowed: `{str(summary['modeled_dollar_projection_allowed']).lower()}`",
        "",
        "## Current Model Evidence",
        "",
        f"- Measured reference candidate: `{evidence['candidate_family']}`",
        f"- Development-selected candidate: `{evidence['development_selected_candidate']}`",
        f"- Candidate was protocol-selected: `{str(evidence['candidate_was_protocol_selected']).lower()}`",
        f"- Direct measured result: {evidence['direct_measured_result']}",
        f"- Cross-sector status: `{evidence['cross_sector_status']}`",
        f"- Proven sector gains: `{evidence['sector_gain_proven_count']}/{evidence['sector_count']}`",
        "",
        "## Bounded Commercial Offers",
        "",
        f"- Source-native protocol review candidate: `${protocol.get('low'):,}` fixed for `{protocol.get('duration_business_days')}` business days; status `{protocol.get('status')}`",
        f"- Benchmark implementation: `${benchmark.get('low'):,}`-`${benchmark.get('high'):,}`",
        f"- Product-process lane: `{product['name']}`",
        f"- Product-process pricing: `{product['pricing_status']}`",
        f"- Product internal evidence gate passed: `{str(product['internal_evidence_gate_passed']).lower()}`",
        f"- Product buyer-readiness gate passed: `{str(product['buyer_readiness_gate'].get('passed', False)).lower()}`",
        f"- Product-process scoping allowed: `{str(product['product_process_scoping_allowed']).lower()}`",
        f"- Product-process external outreach ready: `{str(product['external_outreach_ready']).lower()}`",
        "",
        "## Target Gate",
        "",
        f"- Recipient selected: `{str(payload['target_status']['recipient_selected']).lower()}`",
        f"- Recommended first buyer: `{payload['target_status']['recommended_first_buyer'] or 'none'}`",
        f"- Selected packet send ready: `{str(payload['target_status']['packet_send_ready']).lower()}`",
        f"- Selected packet gate: `{payload['target_status']['packet_send_gate']}`",
        f"- Legacy paid-pilot queue excluded: `{str(payload['target_status']['legacy_paid_pilot_queue_excluded']).lower()}`",
        f"- Exclusion reason: {payload['target_status']['exclusion_reason']}",
        "",
        "## External Unlock",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["external_unlock"])
    lines.extend(["", "## Blocked Claims", ""])
    lines.extend(f"- {item}" for item in payload["claim_controls"]["blocked"])
    lines.extend(["", "## What To Ask Next", ""])
    lines.extend(
        f"{index}. {item}"
        for index, item in enumerate(payload["what_to_ask_next"], start=1)
    )
    lines.extend(
        [
            "",
            f"Proof-to-revenue SHA-256: `{payload['proof_to_revenue_sha256']}`",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "revenue_stage": payload["summary"]["revenue_stage"],
                "product_lane": payload["summary"]["sellable_product_lane"],
                "external_outreach_ready": payload["summary"][
                    "external_outreach_ready"
                ],
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
