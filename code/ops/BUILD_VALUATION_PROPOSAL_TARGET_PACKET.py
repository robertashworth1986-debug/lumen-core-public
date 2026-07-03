from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

CHAMPION_JSON = DASHBOARD_DATA / "champion_metric_gauntlet.json"
LOCKED_SWEEP_JSON = DASHBOARD_DATA / "locked_source_baseline_replay_sweep.json"
DOLLAR_GATE_JSON = DASHBOARD_DATA / "dollar_claim_gate.json"
CLAIM_LADDER_JSON = DASHBOARD_DATA / "field_validated_dollar_claim_ladder.json"

OUT_JSON = OUT_OPS / "valuation_proposal_target_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "valuation_proposal_target_packet.json"
OUT_MD = DOCS / "VALUATION_PROPOSAL_TARGET_PACKET_2026-06-26.md"

UPDATED_BUSINESS_PLAN_PDF = Path(
    r"C:\Users\Novac\iCloudDrive\Business plan\LumenCore_Business_Plan_Investor_Ready_UPDATED_2026-07-03.pdf"
)
UPDATED_BUSINESS_PLAN_MD = DOCS / "LUMENCORE_BUSINESS_PLAN_INVESTOR_READY_UPDATED_2026-07-03.md"

BOUNDARY = (
    "Valuation and proposal target packet. This translates the current July 2026 frozen/source-conditioned replay "
    "evidence into bounded business language, a first paid-pilot target, and reviewer-safe proposal numbers. It does "
    "not authorize field-validation, realized-savings, fixed-dollar frozen-delta, medical, live-trading, grant-award, "
    "or guaranteed ROI claims."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
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


def percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "n/a"


def money(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except Exception:
        return "n/a"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def lane_summary_rows(locked: dict[str, Any]) -> list[dict[str, Any]]:
    rows = locked.get("lane_scoreboard", [])
    if not isinstance(rows, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        comparisons = int(row.get("baseline_comparison_count") or 0)
        wins = int(row.get("candidate_win_count") or 0)
        cleaned.append(
            {
                "lane": row.get("lane", ""),
                "routes_replayed": int(row.get("routes_replayed") or 0),
                "baseline_comparison_count": comparisons,
                "candidate_win_count": wins,
                "candidate_loss_or_tie_count": max(0, comparisons - wins),
                "comparison_win_rate": round(wins / comparisons, 6) if comparisons else 0.0,
                "estimated_rows": int(row.get("estimated_rows") or 0),
                "numeric_samples": int(row.get("numeric_samples") or 0),
                "mean_score_delta": row.get("mean_score_delta"),
                "best_score_delta": row.get("best_score_delta"),
                "locked_baselines": row.get("locked_baselines", []),
                "evidence_status": "source_conditioned_replay_not_field_validation",
            }
        )
    cleaned.sort(
        key=lambda item: (
            -float(item["comparison_win_rate"]),
            -float(item.get("mean_score_delta") or -999),
            -int(item["estimated_rows"]),
        )
    )
    return cleaned


def proposal_target(champion: dict[str, Any], locked_summary: dict[str, Any], lanes: list[dict[str, Any]]) -> dict[str, Any]:
    wave_lane = next((row for row in lanes if row.get("lane") == "wave_resonance_timing"), lanes[0] if lanes else {})
    return {
        "target_name": "Energy/Grid AI Field Replay and Paid Evidence Review",
        "target_segment": "utility_grid_analytics_energy_forecasting_or_cyber_physical_validation",
        "buyer_role": "Utility innovation lead, grid reliability analytics lead, national lab validation lead, or accelerator technical reviewer",
        "why_this_first": (
            "The strongest current proof is a narrow phase/timing result: "
            f"{champion.get('champion_label', 'Kuramoto phase coupling')} beat "
            f"{champion.get('named_baseline', 'kalman_filter')} on "
            f"{champion.get('holdout_wins', 24)}/{champion.get('holdout_count', 24)} source-conditioned holdout checks. "
            f"The broader locked sweep adds {locked_summary.get('baseline_comparison_count', 0)} baseline comparisons across "
            f"{locked_summary.get('adapter_backed_routes', 0)} adapter-backed routes."
        ),
        "strongest_lane": wave_lane.get("lane", "wave_resonance_timing"),
        "proposal_ask": "20-minute technical fit call, then a paid evidence review or buyer-authorized replay.",
        "paid_review_scope_usd": {"low": 5000, "high": 15000, "status": "scoping_range_not_value_claim"},
        "validation_bridge_round": {
            "raise_target_usd": {"low": 250000, "high": 500000},
            "valuation_target": "$10M post-money SAFE cap, negotiable in an $8M-$12M band",
            "use": "external validation, patent/legal support, proof-feed hardening, source expansion, and pilot delivery",
        },
        "acceptance_metric": (
            "pre-registered forecast residual, phase/timing error, drift-detection lead time, false positives, "
            "missed events, runtime budget, and buyer-approved avoided-cost conversion"
        ),
        "required_buyer_inputs": [
            "authorized held-out historical windows",
            "incumbent baseline chosen by the system owner",
            "accepted replay metric and failure reporting rule",
            "forbidden tuning rules",
            "economic conversion factor approved before dollar language",
        ],
    }


def build_payload() -> dict[str, Any]:
    champion_doc = read_json(CHAMPION_JSON)
    locked_doc = read_json(LOCKED_SWEEP_JSON)
    dollar_doc = read_json(DOLLAR_GATE_JSON)
    ladder_doc = read_json(CLAIM_LADDER_JSON)

    champion = champion_doc.get("summary", {}) if isinstance(champion_doc.get("summary"), dict) else {}
    strongest = champion_doc.get("strongest_current", {}) if isinstance(champion_doc.get("strongest_current"), dict) else {}
    locked_summary = locked_doc.get("summary", {}) if isinstance(locked_doc.get("summary"), dict) else {}
    dollar_summary = dollar_doc.get("summary", {}) if isinstance(dollar_doc.get("summary"), dict) else {}
    ladder_truth = ladder_doc.get("current_truth", {}) if isinstance(ladder_doc.get("current_truth"), dict) else {}
    lanes = lane_summary_rows(locked_doc)

    comparisons = int(locked_summary.get("baseline_comparison_count") or 0)
    wins = int(locked_summary.get("candidate_win_count") or 0)
    overall = {
        "source_conditioned_route_count": int(locked_summary.get("adapter_backed_routes") or 0),
        "baseline_comparison_count": comparisons,
        "candidate_win_count": wins,
        "candidate_loss_or_tie_count": int(locked_summary.get("candidate_loss_or_tie_count") or max(0, comparisons - wins)),
        "comparison_win_rate": round(wins / comparisons, 6) if comparisons else 0.0,
        "mean_score_delta": locked_summary.get("mean_score_delta"),
        "best_score_delta": locked_summary.get("best_score_delta"),
        "estimated_rows_replayed": int(locked_summary.get("estimated_rows_replayed") or 0),
        "numeric_samples_read": int(locked_summary.get("numeric_samples_read") or 0),
        "source_count": int(locked_summary.get("source_count") or 0),
        "ready_rows": int(locked_summary.get("ready_rows") or 0),
        "lane_count": int(locked_summary.get("lane_count") or len(lanes)),
        "replay_chain_sha256": locked_summary.get("replay_chain_sha256", ""),
        "evidence_status": "source_conditioned_replay_not_field_validation",
    }

    current_truth = {
        "champion_family": champion.get("champion_family") or strongest.get("family"),
        "champion_label": champion.get("champion_label") or strongest.get("label"),
        "champion_baseline": champion.get("named_baseline") or strongest.get("named_baseline"),
        "champion_lane": strongest.get("lane", "wave_resonance_timing"),
        "champion_holdout_wins": int(champion.get("holdout_wins") or strongest.get("wins_vs_named_baseline") or 0),
        "champion_holdout_count": int(champion.get("holdout_count") or strongest.get("holdout_count") or 0),
        "champion_holdout_win_rate": champion.get("holdout_win_rate") or strongest.get("win_rate_vs_named_baseline"),
        "champion_mean_delta_vs_named_baseline": champion.get("mean_delta_vs_named_baseline") or strongest.get("mean_delta_vs_named_baseline"),
        "champion_min_delta_vs_named_baseline": champion.get("min_delta_vs_named_baseline") or strongest.get("min_delta_vs_named_baseline"),
        "champion_sign_test_p_value": champion.get("one_sided_sign_test_p_value") or strongest.get("one_sided_sign_test_p_value"),
        "champion_wilson_95_lower": champion.get("wilson_95_win_rate_lower") or strongest.get("wilson_95_win_rate_lower"),
        "champion_estimated_rows_replayed": int(champion.get("estimated_rows_replayed") or strongest.get("estimated_rows_replayed") or 0),
        "champion_numeric_samples_read": int(champion.get("numeric_samples_read") or strongest.get("numeric_samples_read") or 0),
        "champion_source_system_count": int(champion.get("source_system_count") or strongest.get("source_system_count") or 0),
        "broader_measured_provider_count": champion.get("broader_measured_provider_count"),
        "broader_enabled_provider_count": champion.get("broader_enabled_provider_count"),
        "manifest_unique_source_count": champion.get("manifest_unique_source_count"),
        "manifest_ready_for_benchmark_row_count": champion.get("manifest_ready_for_benchmark_row_count"),
        "live_domain_reviewer_ready": bool(champion.get("live_domain_reviewer_ready")),
        "buyer_authorized_field_replay_request_ready": bool(champion.get("buyer_authorized_field_replay_request_ready")),
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "bounded_estimated_value_claim_allowed": bool(
            champion.get("bounded_estimated_value_claim_allowed")
            or ladder_truth.get("bounded_estimated_value_claim_allowed_now")
        ),
        "safe_estimated_hourly_value_usd": dollar_summary.get("allowed_estimated_hourly_value_usd")
        or ladder_truth.get("allowed_estimated_hourly_value_usd"),
        "safe_estimated_annual_value_usd": dollar_summary.get("allowed_estimated_annual_value_usd")
        or ladder_truth.get("allowed_estimated_annual_value_usd"),
    }

    target = proposal_target(current_truth, locked_summary, lanes)
    payload = {
        "schema": "valuation_proposal_target_packet_v2",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "champion_metric_gauntlet": rel(CHAMPION_JSON),
            "locked_source_baseline_replay_sweep": rel(LOCKED_SWEEP_JSON),
            "dollar_claim_gate": rel(DOLLAR_GATE_JSON),
            "field_validated_dollar_claim_ladder": rel(CLAIM_LADDER_JSON),
            "updated_business_plan_pdf": str(UPDATED_BUSINESS_PLAN_PDF),
            "updated_business_plan_markdown": rel(UPDATED_BUSINESS_PLAN_MD),
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
            "current_evidence_stage": "source_conditioned_replay_with_live_domain_hash_verification",
            "recommended_investor_target": target["validation_bridge_round"],
            "defensible_money_status": (
                "Price paid technical evaluation, field replay, or validation pilot. Do not price fixed-value frozen deltas "
                "or realized savings until an external owner locks data, baseline, metric, and economics."
            ),
            "current_priceable_offer": {
                "paid_evidence_review_usd": target["paid_review_scope_usd"],
                "buyer_authorized_replay": "custom quote after data rights, baseline, metric, and replay window are locked",
                "platform_license": "defer until external validation or first paid pilot",
            },
        },
        "proposal_blurb": proposal_blurb(current_truth, overall),
        "claim_gates": {
            "source_conditioned_replay_claim_allowed": True,
            "buyer_authorized_field_replay_request_ready": current_truth["buyer_authorized_field_replay_request_ready"],
            "bounded_estimated_value_claim_allowed": current_truth["bounded_estimated_value_claim_allowed"],
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "grant_award_certainty_allowed": False,
            "medical_or_treatment_claim_allowed": False,
        },
    }
    payload["packet_sha256"] = stable_sha256(
        {
            "current_truth": payload["current_truth"],
            "overall_locked_sweep_stats": payload["overall_locked_sweep_stats"],
            "lane_stats": payload["lane_stats"],
            "recommended_first_proposal_target": payload["recommended_first_proposal_target"],
            "claim_gates": payload["claim_gates"],
        }
    )
    return payload


def proposal_blurb(truth: dict[str, Any], overall: dict[str, Any]) -> str:
    return (
        "LumenCore requests a technical fit call for a paid evidence review or buyer-authorized field replay. "
        f"The current strongest internal result is narrow and reproducible: {truth.get('champion_label')} beat "
        f"{truth.get('champion_baseline')} on {truth.get('champion_holdout_wins')}/"
        f"{truth.get('champion_holdout_count')} source-conditioned holdout checks, with about "
        f"{truth.get('champion_estimated_rows_replayed'):,} estimated rows replayed in the champion core. "
        f"The broader locked-source sweep covers {overall.get('source_conditioned_route_count')} adapter-backed routes, "
        f"{overall.get('baseline_comparison_count')} baseline comparisons, {overall.get('candidate_win_count')} wins, "
        f"{overall.get('estimated_rows_replayed'):,} estimated rows, and {overall.get('source_count')} mapped sources. "
        "These are internal replay results, not field validation or realized savings. The requested next step is external "
        "held-out data, the buyer's incumbent baseline, pre-registered metrics, and an accepted economic conversion."
    )


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
        "## Canonical July 2026 Proof Line",
        "",
        f"- Champion: `{truth['champion_label']}` (`{truth['champion_family']}`)",
        f"- Lane: `{truth['champion_lane']}`",
        f"- Named baseline: `{truth['champion_baseline']}`",
        f"- Internal holdout result: `{truth['champion_holdout_wins']}/{truth['champion_holdout_count']}`",
        f"- Internal holdout win rate: `{percent(truth['champion_holdout_win_rate'])}`",
        f"- Wilson 95% lower bound: `{percent(truth['champion_wilson_95_lower'])}`",
        f"- Mean delta vs named baseline: `{truth['champion_mean_delta_vs_named_baseline']}`",
        f"- Minimum positive delta: `{truth['champion_min_delta_vs_named_baseline']}`",
        f"- Sign-test p-value: `{truth['champion_sign_test_p_value']}`",
        f"- Champion estimated rows replayed: `{truth['champion_estimated_rows_replayed']:,}`",
        f"- Champion numeric samples read: `{truth['champion_numeric_samples_read']:,}`",
        f"- Champion source systems: `{truth['champion_source_system_count']}`",
        f"- Live-domain reviewer feed ready: `{str(truth['live_domain_reviewer_ready']).lower()}`",
        "",
        "## Broader Locked Sweep",
        "",
        f"- Adapter-backed routes: `{overall['source_conditioned_route_count']}`",
        f"- Baseline comparisons: `{overall['baseline_comparison_count']}`",
        f"- Candidate wins: `{overall['candidate_win_count']}`",
        f"- Candidate losses/ties: `{overall['candidate_loss_or_tie_count']}`",
        f"- Comparison win rate: `{percent(overall['comparison_win_rate'])}`",
        f"- Mean score delta: `{overall['mean_score_delta']}`",
        f"- Best score delta: `{overall['best_score_delta']}`",
        f"- Estimated rows replayed: `{overall['estimated_rows_replayed']:,}`",
        f"- Numeric samples read: `{overall['numeric_samples_read']:,}`",
        f"- Mapped source count: `{overall['source_count']}`",
        f"- Replay chain SHA-256: `{overall['replay_chain_sha256']}`",
        "",
        "## Lane Results",
        "",
        "| Lane | Routes | Comparisons | Wins | Win Rate | Mean Delta | Best Delta | Rows | Baselines |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in payload["lane_stats"]:
        baselines = ", ".join(str(item) for item in row.get("locked_baselines", []))
        lines.append(
            f"| `{row['lane']}` | `{row['routes_replayed']}` | `{row['baseline_comparison_count']}` | "
            f"`{row['candidate_win_count']}` | `{percent(row['comparison_win_rate'])}` | "
            f"`{row['mean_score_delta']}` | `{row['best_score_delta']}` | `{row['estimated_rows']:,}` | {baselines} |"
        )

    lines.extend(
        [
            "",
            "## Honest Valuation State",
            "",
            f"- Evidence stage: `{valuation['current_evidence_stage']}`",
            f"- Defensible money status: {valuation['defensible_money_status']}",
            f"- Bounded estimated-value language allowed: `{str(truth['bounded_estimated_value_claim_allowed']).lower()}`",
            f"- Safe estimated opportunity surface: `{money(truth['safe_estimated_hourly_value_usd'])}/hour` or `{money(truth['safe_estimated_annual_value_usd'])}/year` under stated assumptions.",
            "- This is not realized savings, not a promise that a buyer will pay, and not a fixed price for a frozen delta.",
            f"- Investor target: `{target['validation_bridge_round']['valuation_target']}`",
            f"- Raise target: `{money(target['validation_bridge_round']['raise_target_usd']['low'])}` to `{money(target['validation_bridge_round']['raise_target_usd']['high'])}`",
            "",
            "## First Proposal Target",
            "",
            f"- Target: {target['target_name']}",
            f"- Buyer role: {target['buyer_role']}",
            f"- Why this first: {target['why_this_first']}",
            f"- Ask: {target['proposal_ask']}",
            f"- Paid review scope: `{money(target['paid_review_scope_usd']['low'])}` to `{money(target['paid_review_scope_usd']['high'])}`, scoping only.",
            f"- Acceptance metric: {target['acceptance_metric']}",
            "",
            "## Reviewer-Safe Proposal Blurb",
            "",
            payload["proposal_blurb"],
            "",
            "## Best Current Investor Artifact",
            "",
            f"- Updated PDF: `{payload['inputs']['updated_business_plan_pdf']}`",
            f"- Source markdown: `{payload['inputs']['updated_business_plan_markdown']}`",
            "- Use the updated July 3 business plan for LvlUp/Black Dog and investor applications. Treat older April/May decks as background only unless manually claim-reviewed.",
            "",
            "## Boundaries",
            "",
            "- Do not state field validation, realized savings, fixed frozen-delta dollar value, live trading edge, medical efficacy, or award certainty.",
            "- The strongest current claim is: internal source-conditioned replay winner plus live-domain hash-verified reviewer feed.",
            "- The highest-value next proof is buyer-authorized holdout replay with accepted baseline, accepted metric, and accepted economics.",
            f"- Packet SHA-256: `{payload['packet_sha256']}`",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))


if __name__ == "__main__":
    main()
