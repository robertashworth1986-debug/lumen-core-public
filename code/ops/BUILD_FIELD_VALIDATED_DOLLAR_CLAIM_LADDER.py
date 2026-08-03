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

VALUATION_JSON = OUT_OPS / "valuation_proposal_target_packet_latest.json"
REVENUE_JSON = OUT_OPS / "proof_to_revenue_engine_latest.json"
CHAMPION_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
CONTROL_ROOM_JSON = OUT_OPS / "field_validation_control_room_latest.json"

OUT_JSON = OUT_OPS / "field_validated_dollar_claim_ladder_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "field_validated_dollar_claim_ladder.json"
OUT_MD = DOCS / "FIELD_VALIDATED_DOLLAR_CLAIM_LADDER_2026-06-27.md"

BOUNDARY = (
    "Current model-outcome value is zero for claim purposes. LumenCore has no "
    "performance champion, buyer-authorized field replay, realized savings, or "
    "accepted economic conversion factor. Hypothetical arithmetic is educational "
    "only. A separately scoped technical service fee is a price for work, not proof "
    "of model value, ROI, savings, enterprise value, or award certainty."
)

IMPROVEMENT_PCTS = [0.001, 0.005, 0.01, 0.05, 0.1, 1.0]
LOSS_POOLS = [1_000_000_000, 10_000_000_000, 100_000_000_000]


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
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def money(value: Any) -> str:
    return f"${as_float(value):,.2f}"


def gross_value(loss_pool_usd: float, improvement_pct: float) -> float:
    return loss_pool_usd * (improvement_pct / 100.0)


def windowed_value(annual_value_usd: float, months: int) -> float:
    return annual_value_usd * (months / 12.0)


def hypothetical_sector_math() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pool in LOSS_POOLS:
        for pct in IMPROVEMENT_PCTS:
            annual = gross_value(pool, pct)
            rows.append(
                {
                    "loss_pool_usd": pool,
                    "hypothetical_improvement_pct": pct,
                    "arithmetic_annual_usd": round(annual, 2),
                    "arithmetic_first_3_months_usd": round(
                        windowed_value(annual, 3), 2
                    ),
                    "current_claim_allowed": False,
                    "boundary": (
                        "Arithmetic illustration only. LumenCore has not measured or "
                        "field-validated this improvement on this loss pool."
                    ),
                }
            )
    return rows


def service_pricing(valuation: dict[str, Any]) -> dict[str, Any]:
    state = as_dict(valuation.get("valuation_state"))
    current_offer = as_dict(state.get("current_priceable_offer"))
    review = as_dict(current_offer.get("paid_protocol_review_usd"))
    implementation = as_dict(
        current_offer.get("benchmark_implementation_usd")
    )
    return {
        "paid_protocol_review_usd": {
            "low": as_int(review.get("low"), 2500),
            "high": as_int(review.get("high"), 7500),
            "status": (
                "service_scoping_range_not_model_value_roi_savings_or_enterprise_value"
            ),
        },
        "benchmark_implementation_usd": {
            "low": as_int(implementation.get("low"), 7500),
            "high": as_int(implementation.get("high"), 25000),
            "status": (
                "custom_scope_after_data_rights_baselines_and_acceptance_criteria"
            ),
        },
        "service_price_is_model_outcome_value": False,
        "service_price_is_realized_savings": False,
        "service_price_is_enterprise_valuation": False,
    }


def current_truth(
    valuation: dict[str, Any],
    revenue: dict[str, Any],
    champion: dict[str, Any],
    control_room: dict[str, Any],
) -> dict[str, Any]:
    valuation_gates = as_dict(valuation.get("claim_gates"))
    revenue_summary = as_dict(revenue.get("summary"))
    champion_summary = as_dict(champion.get("summary"))
    control_summary = as_dict(control_room.get("summary"))
    return {
        "current_performance_champion_present": False,
        "modeled_dollar_projection_allowed_now": False,
        "bounded_estimated_value_claim_allowed_now": False,
        "field_validated_savings_claim_allowed_now": False,
        "realized_customer_or_government_savings_allowed_now": False,
        "fixed_dollar_delta_sale_claim_allowed_now": False,
        "enterprise_valuation_asserted_now": False,
        "buyer_authorized_field_replay_request_ready_now": False,
        "live_trading_or_autonomous_execution_allowed_now": False,
        "allowed_estimated_hourly_value_usd": 0.0,
        "allowed_estimated_annual_value_usd": 0.0,
        "allowed_estimated_first_3_months_value_usd": 0.0,
        "allowed_realized_savings_usd": 0.0,
        "direct_all_baseline_global_holm_positive_count": as_int(
            champion_summary.get(
                "direct_all_baseline_global_holm_positive_count"
            )
        ),
        "cross_sector_gain_proven_count": as_int(
            revenue_summary.get("cross_sector_gain_proven_count")
        ),
        "cross_sector_sector_count": as_int(
            revenue_summary.get("cross_sector_sector_count")
        ),
        "field_validated_family_count": as_int(
            champion_summary.get("field_validated_family_count")
        ),
        "robust_repeat_candidate_count": as_int(
            champion_summary.get("robust_repeat_candidate_count")
        ),
        "paid_protocol_review_scoping_allowed_now": bool(
            valuation_gates.get("paid_protocol_review_scoping_allowed")
            and control_summary.get("paid_protocol_review_scoping_ready")
        ),
        "live_domain_hash_verified": bool(
            revenue_summary.get("live_domain_hash_verified")
        ),
        "required_remote_hash_matches": as_int(
            revenue_summary.get("required_remote_hash_matches")
        ),
        "required_feed_count": as_int(
            revenue_summary.get("required_feed_count")
        ),
        "claim_boundary": BOUNDARY,
    }


def reference_candidate(
    revenue: dict[str, Any], champion: dict[str, Any]
) -> dict[str, Any]:
    revenue_summary = as_dict(revenue.get("summary"))
    coc = as_dict(champion.get("champion_of_champions"))
    harmonic = as_dict(coc.get("best_harmonic_candidate"))
    holdout = as_dict(harmonic.get("kuramoto_holdout_evidence"))
    return {
        "role": "measured_reference_candidate_not_performance_champion",
        "family_id": revenue_summary.get(
            "measured_reference_candidate", "kuramoto_phase_coupling"
        ),
        "development_selected_candidate": revenue_summary.get(
            "development_selected_candidate", "lissajous_phase_paths"
        ),
        "candidate_was_protocol_selected": bool(
            holdout.get("candidate_was_protocol_selected")
        ),
        "named_baseline": revenue_summary.get(
            "internal_replay_named_baseline",
            holdout.get("named_baseline", "kalman_local_linear_trend"),
        ),
        "holdout_count": as_int(
            revenue_summary.get(
                "internal_replay_holdout_count", holdout.get("holdout_count")
            )
        ),
        "wins_vs_named_baseline": as_int(
            revenue_summary.get(
                "internal_replay_holdout_wins",
                holdout.get("wins_vs_kalman"),
            )
        ),
        "mean_delta_vs_named_baseline": as_float(
            revenue_summary.get(
                "internal_replay_mean_delta",
                holdout.get("mean_delta_vs_kalman"),
            )
        ),
        "registered_baseline_count": as_int(
            holdout.get("registered_baseline_count")
        ),
        "registered_baseline_mean_win_count": as_int(
            holdout.get("registered_baseline_mean_win_count")
        ),
        "ready_for_buyer_authorized_field_replay_request": False,
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "plain_english": (
            "Kuramoto is retained as a measured negative reference. It was not "
            "development-selected, did not beat the registered source-native "
            "baselines, and is not a performance champion or buyer replay request."
        ),
    }


def claim_ladder(
    truth: dict[str, Any], reference: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "tier": 0,
            "name": "Current measured nonpromotion result",
            "allowed_now": True,
            "allowed_language": (
                f"`{reference['family_id']}` won "
                f"{reference['wins_vs_named_baseline']} of "
                f"{reference['holdout_count']} paired holdouts against "
                f"`{reference['named_baseline']}` with mean delta "
                f"{reference['mean_delta_vs_named_baseline']:.6f}; no current "
                "performance champion or dollar outcome is claimed."
            ),
        },
        {
            "tier": 1,
            "name": "Separately scoped technical service",
            "allowed_now": bool(
                truth["paid_protocol_review_scoping_allowed_now"]
            ),
            "allowed_language": (
                "Price source-task mapping, baseline registration, chronology "
                "freezing, reproducible execution, and claim-boundary review as "
                "professional work. Do not describe the fee as model value or ROI."
            ),
        },
        {
            "tier": 2,
            "name": "Buyer-authorized source-native replay",
            "allowed_now": False,
            "unlock_conditions": [
                "buyer authorizes the exact source, use case, and data rights",
                "development candidate and every source-native baseline are frozen",
                "chronology, acceptance metric, and multiplicity correction are locked",
                "candidate passes the full direct-measured promotion gate",
                "action-time human approval is received before external contact",
            ],
        },
        {
            "tier": 3,
            "name": "Field-validated avoided-cost conversion",
            "allowed_now": False,
            "unlock_conditions": [
                "external owner accepts the measured operational result",
                "buyer accepts the economic conversion factor and denominator",
                "lower confidence bound remains positive after exclusions",
                "result is independently traceable and repeatable",
            ],
        },
        {
            "tier": 4,
            "name": "Enterprise valuation or broad savings claim",
            "allowed_now": False,
            "unlock_conditions": [
                "independent diligence",
                "multiple external validations",
                "customer revenue or signed procurement evidence",
                "clear IP, licensing, security, and deployment posture",
            ],
        },
    ]


def field_validation_accounting_model() -> dict[str, Any]:
    return {
        "status": "future_only_not_current_value",
        "minimum_fields_to_lock": [
            "system_owner",
            "system_name",
            "source_and_version",
            "baseline_name_and_version",
            "candidate_name_and_version",
            "chronological_input_window",
            "outcome_metric_and_denominator",
            "economic_conversion_factor",
            "confidence_rule",
            "exclusions_and_failure_cases",
        ],
        "conversion_rule": (
            "Only after the technical gate passes may the buyer-approved economic "
            "conversion use the positive lower confidence bound. Until then the "
            "claimable outcome value is zero."
        ),
    }


def build_payload() -> dict[str, Any]:
    valuation = read_json(VALUATION_JSON)
    revenue = read_json(REVENUE_JSON)
    champion = read_json(CHAMPION_JSON)
    control_room = read_json(CONTROL_ROOM_JSON)

    truth = current_truth(valuation, revenue, champion, control_room)
    reference = reference_candidate(revenue, champion)
    math_rows = hypothetical_sector_math()
    one_billion = [
        row for row in math_rows if row["loss_pool_usd"] == 1_000_000_000
    ]
    pricing = service_pricing(valuation)
    payload = {
        "schema": "field_validated_dollar_claim_ladder_v2",
        "generated_utc": now_utc(),
        "purpose": (
            "Fail-closed public claim contract for model-outcome dollars, "
            "technical service pricing, and future field-validation unlocks."
        ),
        "boundary": BOUNDARY,
        "direct_answer": {
            "can_claim_real_savings_right_now": False,
            "can_claim_bounded_estimated_value_right_now": False,
            "can_publish_modeled_dollar_projection_right_now": False,
            "can_scope_paid_protocol_review_right_now": bool(
                truth["paid_protocol_review_scoping_allowed_now"]
            ),
            "best_current_wording": (
                "No current model-outcome dollar projection is allowed. LumenCore "
                "may separately scope a source-native protocol review or benchmark "
                "implementation as paid technical work."
            ),
            "one_percent_of_one_billion_note": (
                "One percent of $1 billion is $10 million as arithmetic. It is not "
                "a LumenCore savings, efficiency, valuation, or revenue claim."
            ),
        },
        "current_truth": truth,
        "reference_candidate": reference,
        "strongest_alpha_flow_family": reference,
        "service_pricing": pricing,
        "claim_ladder": claim_ladder(truth, reference),
        "field_validation_accounting_model": (
            field_validation_accounting_model()
        ),
        "hypothetical_sector_math": {
            "current_claim_allowed": False,
            "interpretation": (
                "loss pool multiplied by hypothetical improvement; arithmetic "
                "education only, not measured LumenCore performance"
            ),
            "one_billion_examples": one_billion,
            "all_examples": math_rows,
        },
        "capture_from_current_safe_estimate": [],
        "supersedes": {
            "schema": "field_validated_dollar_claim_ladder_v1",
            "reason": (
                "The v1 ladder treated an assumption-based opportunity surface as "
                "a present bounded value signal. V2 zeros all model-outcome dollars "
                "until external source-native and economic gates pass."
            ),
        },
        "inputs": {
            "valuation_proposal_target_packet": str(
                VALUATION_JSON.relative_to(ROOT)
            ).replace("\\", "/"),
            "proof_to_revenue_engine": str(
                REVENUE_JSON.relative_to(ROOT)
            ).replace("\\", "/"),
            "geometry_champion_of_champions": str(
                CHAMPION_JSON.relative_to(ROOT)
            ).replace("\\", "/"),
            "field_validation_control_room": str(
                CONTROL_ROOM_JSON.relative_to(ROOT)
            ).replace("\\", "/"),
        },
    }
    payload["claim_ladder_sha256"] = stable_sha256(
        {
            "current_truth": truth,
            "reference_candidate": reference,
            "service_pricing": pricing,
            "claim_ladder": payload["claim_ladder"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    truth = payload["current_truth"]
    reference = payload["reference_candidate"]
    review = payload["service_pricing"]["paid_protocol_review_usd"]
    implementation = payload["service_pricing"][
        "benchmark_implementation_usd"
    ]
    lines = [
        "# Field-Validated Dollar Claim Ladder",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Claim ladder SHA-256: `{payload['claim_ladder_sha256']}`",
        "",
        "## Current Answer",
        "",
        payload["boundary"],
        "",
        "- Current performance champion: `false`",
        "- Modeled dollar projection allowed now: `false`",
        "- Real savings claim right now: `false`",
        "- Field validated savings allowed now: `false`",
        "- Enterprise valuation asserted now: `false`",
        "- Claimable hourly model-outcome value: `$0.00`",
        "- Claimable annual model-outcome value: `$0.00`",
        "",
        "## Measured Reference",
        "",
        f"- Candidate: `{reference['family_id']}`",
        (
            f"- Development-selected candidate: "
            f"`{reference['development_selected_candidate']}`"
        ),
        (
            f"- Holdout wins: `{reference['wins_vs_named_baseline']} / "
            f"{reference['holdout_count']}`"
        ),
        (
            f"- Mean delta vs `{reference['named_baseline']}`: "
            f"`{reference['mean_delta_vs_named_baseline']:.6f}`"
        ),
        "- Buyer-authorized replay request ready: `false`",
        f"- Boundary: {reference['plain_english']}",
        "",
        "## Separately Scoped Services",
        "",
        (
            f"- Protocol review: `{money(review['low'])}` to "
            f"`{money(review['high'])}`"
        ),
        (
            f"- Benchmark implementation: `{money(implementation['low'])}` "
            f"to `{money(implementation['high'])}`"
        ),
        (
            "- These are service-scoping ranges. They are not model value, "
            "realized savings, ROI, enterprise value, or an award forecast."
        ),
        "",
        "## Claim Ladder",
        "",
    ]
    for row in payload["claim_ladder"]:
        lines.extend(
            [
                f"### Tier {row['tier']}: {row['name']}",
                "",
                f"- Allowed now: `{str(row['allowed_now']).lower()}`",
            ]
        )
        if row.get("allowed_language"):
            lines.append(f"- Language: {row['allowed_language']}")
        if row.get("unlock_conditions"):
            lines.append("- Unlock conditions:")
            lines.extend(
                f"  - {item}" for item in row["unlock_conditions"]
            )
        lines.append("")

    lines.extend(
        [
            "## Hypothetical Arithmetic",
            "",
            (
                "One percent of $1 billion is $10 million. The table below is "
                "math only; every row has `current_claim_allowed=false`."
            ),
            "",
            "| Hypothetical Improvement | Annual Arithmetic | Current Claim |",
            "| ---: | ---: | :---: |",
        ]
    )
    for row in payload["hypothetical_sector_math"][
        "one_billion_examples"
    ]:
        lines.append(
            f"| {row['hypothetical_improvement_pct']}% | "
            f"{money(row['arithmetic_annual_usd'])} | false |"
        )

    lines.extend(
        [
            "",
            "## Future Conversion Contract",
            "",
            payload["field_validation_accounting_model"]["conversion_rule"],
            "",
            (
                f"Current hash state: "
                f"`{truth['required_remote_hash_matches']} / "
                f"{truth['required_feed_count']}` required feeds match. Hash "
                "identity is custody evidence, not performance evidence."
            ),
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(payload: dict[str, Any]) -> None:
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))


def main() -> int:
    payload = build_payload()
    write_outputs(payload)
    print(
        json.dumps(
            {
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace(
                    "\\", "/"
                ),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "schema": payload["schema"],
                "modeled_dollar_projection_allowed_now": (
                    payload["current_truth"][
                        "modeled_dollar_projection_allowed_now"
                    ]
                ),
                "claimable_annual_model_outcome_value_usd": (
                    payload["current_truth"][
                        "allowed_estimated_annual_value_usd"
                    ]
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
