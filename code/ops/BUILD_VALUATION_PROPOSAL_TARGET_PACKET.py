from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

GAUNTLET_JSON = DASHBOARD_DATA / "champion_metric_gauntlet.json"
LOCKED_SWEEP_JSON = DASHBOARD_DATA / "locked_source_baseline_replay_sweep.json"
READY_REPLAY_JSON = DASHBOARD_DATA / "geometry_ready_source_replay.json"
KURAMOTO_JSON = DASHBOARD_DATA / "kuramoto_holdout_expansion.json"
DOLLAR_GATE_JSON = DASHBOARD_DATA / "dollar_claim_gate.json"
CLAIM_LADDER_JSON = DASHBOARD_DATA / "field_validated_dollar_claim_ladder.json"
HYPERCORE_PROTOCOL_JSON = ROOT / "config" / "hypercore_v8_validation_protocol_v1.json"

OUT_JSON = OUT_OPS / "valuation_proposal_target_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "valuation_proposal_target_packet.json"
OUT_MD = DOCS / "VALUATION_PROPOSAL_TARGET_PACKET_2026-06-26.md"

BOUNDARY = (
    "This packet prices only a bounded technical service: source-task compatibility "
    "review, evidence audit, source normalization, accepted-baseline registration, "
    "and reproducible benchmark implementation. The current measured geometry "
    "results contain no internal performance champion. This packet does not assert "
    "enterprise value, field validation, realized savings, fixed-dollar algorithm "
    "value, medical efficacy, trading edge, grant certainty, or buyer ROI."
)


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


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def money(value: Any) -> str:
    return f"${safe_float(value):,.0f}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    read_json(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")
    os.replace(temporary, path)


def lane_summary_rows(locked: dict[str, Any]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for row in locked.get("lane_scoreboard", []):
        if not isinstance(row, dict):
            continue
        cleaned.append(
            {
                "lane": row.get("lane", ""),
                "evidence_mode": row.get("evidence_mode", ""),
                "routes_replayed": safe_int(row.get("routes_replayed")),
                "baseline_comparison_count": safe_int(
                    row.get("baseline_comparison_count")
                ),
                "raw_mean_win_count": safe_int(
                    row.get("candidate_win_count")
                ),
                "global_holm_positive_count": safe_int(
                    row.get("global_holm_positive_count")
                ),
                "performance_rows": safe_int(row.get("numeric_samples")),
                "mean_score_delta": row.get("mean_score_delta"),
                "best_score_delta": row.get("best_score_delta"),
                "locked_baselines": row.get("locked_baselines", []),
                "source_names": row.get("source_names", []),
                "performance_superiority_claim_allowed": False,
            }
        )
    return sorted(cleaned, key=lambda row: row["lane"])


def hypercore_commercial_boundary() -> dict[str, Any]:
    payload = read_json(HYPERCORE_PROTOCOL_JSON)
    if payload.get("schema") != "hypercore_v8_validation_protocol_v1":
        raise ValueError("Hypercore V8 validation protocol is required")
    commercial = payload.get("commercial_boundary")
    if not isinstance(commercial, dict):
        raise ValueError("Hypercore V8 commercial boundary is invalid")
    if commercial.get("fee_status") != "candidate_not_committed":
        raise ValueError("Hypercore review fee must remain candidate and uncommitted")
    if commercial.get("external_send_allowed") is not False:
        raise ValueError("Hypercore commercial boundary must remain fail-closed")
    if commercial.get("contract_or_price_acceptance_proven") is not False:
        raise ValueError("Hypercore price acceptance cannot be inferred")
    return commercial


def proposal_target(commercial: dict[str, Any] | None = None) -> dict[str, Any]:
    commercial = commercial or hypercore_commercial_boundary()
    review_fee = safe_int(commercial.get("candidate_fee_usd"))
    review_days = safe_int(commercial.get("candidate_duration_business_days"))
    extension = commercial.get("implementation_extension_range_usd", {})
    if not isinstance(extension, dict):
        raise ValueError("Hypercore implementation extension range is invalid")
    return {
        "target_name": "Source-Native Benchmark and Evidence Protocol Review",
        "target_segment": (
            "government_lab_utility_or_industrial_analytics_validation_team"
        ),
        "buyer_role": (
            "Technical program manager, validation lead, data-science lead, "
            "research software lead, or engineering assurance lead"
        ),
        "why_this_first": (
            "LumenCore can sell the governed method it has now: map a measured "
            "source to the correct task, normalize its schema, register accepted "
            "incumbent baselines, freeze chronology and metrics, execute a "
            "reproducible comparison, and preserve both positive and negative "
            "results. The current EIA result demonstrates the method's ability "
            "to reject an unsupported candidate rather than manufacture a win."
        ),
        "proposal_ask": (
            "20-minute technical fit call followed by a fixed-scope paid protocol "
            "review or benchmark implementation."
        ),
        "paid_review_scope_usd": {
            "low": review_fee,
            "high": review_fee,
            "duration_business_days": review_days,
            "offer_name": commercial.get("first_offer"),
            "status": commercial.get("fee_status"),
            "founder_approved": False,
            "buyer_accepted": False,
        },
        "optional_benchmark_build_usd": {
            "low": safe_int(extension.get("low")),
            "high": safe_int(extension.get("high")),
            "status": "custom_scope_after_data_rights_and_acceptance_criteria",
            "founder_approved": False,
            "buyer_accepted": False,
        },
        "validation_bridge_budget": {
            "planning_range_usd": {"low": 250000, "high": 500000},
            "enterprise_valuation": None,
            "valuation_status": (
                "not_asserted_pending_independent_diligence_external_validation_and_revenue"
            ),
            "use": (
                "independent evaluation, legal and IP support, source adapters, "
                "reproducibility infrastructure, and first customer delivery"
            ),
        },
        "acceptance_outputs": [
            "signed source-task compatibility matrix",
            "normalized source schema and data-quality report",
            "registered incumbent baseline set",
            "frozen development/holdout protocol",
            "reproducible benchmark report with hashes and negative results",
            "explicit claim and non-claim boundary",
        ],
        "required_buyer_inputs": [
            "authorized data or a public source approved for the engagement",
            "the operational question and target outcome",
            "incumbent or accepted baseline candidates",
            "failure costs and decision cadence",
            "reviewer or system-owner acceptance criteria",
        ],
    }


def proposal_blurb(truth: dict[str, Any], overall: dict[str, Any]) -> str:
    return (
        "LumenCore offers a fixed-scope source-native benchmark and evidence "
        "protocol review. The current stack has exercised four compatibility-gated "
        f"adapters across {overall['baseline_comparison_count']} registered baseline "
        f"comparisons and {overall['performance_rows_reviewed']:,} performance rows. "
        "No direct measured candidate cleared every baseline after global correction, "
        "and the system preserved that negative result. The engagement would map one "
        "authorized source to the correct task, freeze chronology and accepted "
        "baselines, run the comparison reproducibly, and deliver a reviewer-ready "
        "evidence packet. This is a technical service offer, not a performance, "
        "savings, enterprise-value, or award claim."
    )


def build_payload() -> dict[str, Any]:
    gauntlet = read_json(GAUNTLET_JSON)
    locked = read_json(LOCKED_SWEEP_JSON)
    ready = read_json(READY_REPLAY_JSON)
    kuramoto = read_json(KURAMOTO_JSON)
    dollar_gate = read_json(DOLLAR_GATE_JSON)
    claim_ladder = read_json(CLAIM_LADDER_JSON)
    commercial = hypercore_commercial_boundary()

    if gauntlet.get("schema") != "champion_metric_gauntlet_v2":
        raise ValueError("champion metric gauntlet v2 is required")
    if locked.get("schema") != "locked_source_baseline_replay_sweep_v2":
        raise ValueError("locked source baseline replay sweep v2 is required")
    if ready.get("schema") != "geometry_ready_source_replay_v2":
        raise ValueError("geometry ready source replay v2 is required")
    if kuramoto.get("schema") != "kuramoto_holdout_expansion_v2":
        raise ValueError("Kuramoto measured audit v2 is required")

    gauntlet_summary = gauntlet.get("summary", {})
    locked_summary = locked.get("summary", {})
    ready_summary = ready.get("summary", {})
    kuramoto_summary = kuramoto.get("summary", {})
    lanes = lane_summary_rows(locked)
    target = proposal_target(commercial)

    overall = {
        "adapter_backed_route_count": safe_int(
            locked_summary.get("adapter_backed_routes")
        ),
        "source_conditioned_route_count": safe_int(
            locked_summary.get("source_conditioned_routes_replayed")
        ),
        "direct_measured_route_count": safe_int(
            locked_summary.get("direct_measured_routes_replayed")
        ),
        "baseline_comparison_count": safe_int(
            locked_summary.get("baseline_comparison_count")
        ),
        "raw_mean_win_count": safe_int(
            locked_summary.get("candidate_win_count")
        ),
        "global_holm_positive_count": safe_int(
            locked_summary.get("global_holm_positive_count")
        ),
        "promoted_candidate_count": safe_int(
            ready_summary.get(
                "direct_all_baseline_global_holm_positive_count"
            )
        ),
        "performance_rows_reviewed": safe_int(
            locked_summary.get("numeric_samples_read")
        ),
        "source_count": safe_int(locked_summary.get("source_count")),
        "legacy_ready_rows_excluded": safe_int(
            locked_summary.get("unclassified_manifest_rows_excluded")
        ),
        "numeric_fallback_profiles_used": safe_int(
            locked_summary.get("fallback_profiles_used")
        ),
        "replay_chain_sha256": locked_summary.get(
            "replay_chain_sha256", ""
        ),
        "performance_superiority_claim_allowed": False,
    }

    current_truth = {
        "internal_performance_champion_present": False,
        "reference_candidate": kuramoto_summary.get("candidate", ""),
        "reference_candidate_label": "Kuramoto phase coupling",
        "reference_lane": "wave_resonance_timing",
        "reference_named_baseline": kuramoto_summary.get(
            "named_baseline", ""
        ),
        "reference_holdout_wins": safe_int(
            kuramoto_summary.get("wins_vs_kalman")
        ),
        "reference_holdout_count": safe_int(
            kuramoto_summary.get("holdout_count")
        ),
        "reference_mean_delta_vs_named_baseline": safe_float(
            kuramoto_summary.get("mean_delta_vs_kalman")
        ),
        "development_selected_candidate": kuramoto_summary.get(
            "development_selected_candidate", ""
        ),
        "reference_candidate_was_protocol_selected": bool(
            kuramoto_summary.get("candidate_was_protocol_selected")
        ),
        "reference_candidate_cleared_all_baselines": bool(
            kuramoto_summary.get(
                "candidate_beats_all_registered_baselines_after_holm"
            )
        ),
        "buyer_authorized_field_replay_request_ready": False,
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "bounded_estimated_value_claim_allowed": False,
        "safe_estimated_hourly_value_usd": 0.0,
        "safe_estimated_annual_value_usd": 0.0,
    }

    payload = {
        "schema": "valuation_proposal_target_packet_v3",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "champion_metric_gauntlet": rel(GAUNTLET_JSON),
            "locked_source_baseline_replay_sweep": rel(
                LOCKED_SWEEP_JSON
            ),
            "geometry_ready_source_replay": rel(READY_REPLAY_JSON),
            "kuramoto_measured_audit": rel(KURAMOTO_JSON),
            "dollar_claim_gate_context_only": rel(DOLLAR_GATE_JSON),
            "field_validated_dollar_claim_ladder_context_only": rel(
                CLAIM_LADDER_JSON
            ),
            "hypercore_v8_commercial_boundary": rel(HYPERCORE_PROTOCOL_JSON),
        },
        "input_sha256": {
            rel(path): file_sha256(path)
            for path in (
                GAUNTLET_JSON,
                LOCKED_SWEEP_JSON,
                READY_REPLAY_JSON,
                KURAMOTO_JSON,
                HYPERCORE_PROTOCOL_JSON,
            )
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
        "current_truth": current_truth,
        "overall_locked_sweep_stats": overall,
        "lane_stats": lanes,
        "recommended_first_proposal_target": target,
        "valuation_state": {
            "current_evidence_stage": (
                "direct_measured_nonpromotion_plus_conditioned_synthetic_research_leads"
            ),
            "enterprise_valuation_asserted": False,
            "enterprise_valuation_status": target["validation_bridge_budget"][
                "valuation_status"
            ],
            "defensible_money_status": (
                "Price paid technical evaluation, protocol review, source "
                "normalization, or reproducible benchmark implementation. Do not "
                "price algorithmic performance, realized savings, or enterprise "
                "value from the current negative result."
            ),
            "current_priceable_offer": {
                "paid_protocol_review_usd": target[
                    "paid_review_scope_usd"
                ],
                "benchmark_implementation_usd": target[
                    "optional_benchmark_build_usd"
                ],
                "platform_license": (
                    "defer until external validation or a paid customer accepts "
                    "a productized evidence workflow"
                ),
            },
        },
        "proposal_blurb": proposal_blurb(current_truth, overall),
        "claim_gates": {
            "source_conditioned_research_lead_language_allowed": True,
            "measured_nonpromotion_language_allowed": True,
            "paid_protocol_review_scoping_allowed": True,
            "buyer_authorized_field_replay_request_ready": False,
            "bounded_estimated_value_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "grant_award_certainty_allowed": False,
            "medical_or_treatment_claim_allowed": False,
        },
        "context_artifacts_loaded": {
            "dollar_gate": bool(dollar_gate),
            "claim_ladder": bool(claim_ladder),
            "gauntlet_internal_champion": bool(
                gauntlet_summary.get("internal_champion")
            ),
        },
    }
    payload["packet_sha256"] = stable_sha256(
        {
            "current_truth": payload["current_truth"],
            "overall_locked_sweep_stats": payload[
                "overall_locked_sweep_stats"
            ],
            "lane_stats": payload["lane_stats"],
            "recommended_first_proposal_target": payload[
                "recommended_first_proposal_target"
            ],
            "valuation_state": payload["valuation_state"],
            "claim_gates": payload["claim_gates"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    truth = payload["current_truth"]
    overall = payload["overall_locked_sweep_stats"]
    target = payload["recommended_first_proposal_target"]
    valuation = payload["valuation_state"]
    lines = [
        "# Valuation Proposal Target Packet",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Current Evidence State",
        "",
        f"- Internal performance champion present: `{str(truth['internal_performance_champion_present']).lower()}`",
        f"- Measured reference candidate: `{truth['reference_candidate']}`",
        f"- Frozen development-selected candidate: `{truth['development_selected_candidate']}`",
        f"- Reference candidate selected by protocol: `{str(truth['reference_candidate_was_protocol_selected']).lower()}`",
        f"- Paired-day result vs `{truth['reference_named_baseline']}`: `{truth['reference_holdout_wins']}/{truth['reference_holdout_count']}`",
        f"- Mean source-native skill delta: `{truth['reference_mean_delta_vs_named_baseline']}`",
        f"- Cleared every source-specific baseline: `{str(truth['reference_candidate_cleared_all_baselines']).lower()}`",
        "",
        "## Compatibility-Gated Sweep",
        "",
        f"- Adapter-backed routes: `{overall['adapter_backed_route_count']}`",
        f"- Direct measured routes: `{overall['direct_measured_route_count']}`",
        f"- Conditioned-synthetic routes: `{overall['source_conditioned_route_count']}`",
        f"- Registered baseline comparisons: `{overall['baseline_comparison_count']}`",
        f"- Raw positive mean comparisons: `{overall['raw_mean_win_count']}`",
        f"- Globally corrected positive comparisons: `{overall['global_holm_positive_count']}`",
        f"- Promoted direct candidates: `{overall['promoted_candidate_count']}`",
        f"- Performance rows reviewed: `{overall['performance_rows_reviewed']}`",
        f"- Legacy generic ready rows excluded: `{overall['legacy_ready_rows_excluded']}`",
        f"- Numeric fallback profiles: `{overall['numeric_fallback_profiles_used']}`",
        "",
        "## Defensible Money State",
        "",
        f"- Evidence stage: `{valuation['current_evidence_stage']}`",
        f"- Enterprise valuation asserted: `{str(valuation['enterprise_valuation_asserted']).lower()}`",
        f"- Defensible money status: {valuation['defensible_money_status']}",
        "",
        "## First Proposal Target",
        "",
        f"- Target: {target['target_name']}",
        f"- Buyer role: {target['buyer_role']}",
        f"- Why this first: {target['why_this_first']}",
        f"- Ask: {target['proposal_ask']}",
        f"- Protocol review candidate: `{money(target['paid_review_scope_usd']['low'])}` fixed for `{target['paid_review_scope_usd']['duration_business_days']}` business days; status `{target['paid_review_scope_usd']['status']}`",
        f"- Benchmark build range: `{money(target['optional_benchmark_build_usd']['low'])}` to `{money(target['optional_benchmark_build_usd']['high'])}`",
        "",
        "## Reviewer-Safe Proposal Blurb",
        "",
        payload["proposal_blurb"],
        "",
        "## Boundaries",
        "",
        "- Do not state a current performance champion, field validation, realized savings, enterprise value, live trading edge, medical efficacy, or award certainty.",
        "- Sell the bounded technical work that exists now: protocol, source compatibility, baseline registration, reproducibility, and reviewer-ready evidence.",
    ]
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))


if __name__ == "__main__":
    main()
