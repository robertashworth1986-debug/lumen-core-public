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

LIVE_VALUE_JSON = OUT_OPS / "live_proof_value_meter_latest.json"
TRUTH_SWEEP_JSON = OUT_OPS / "field_money_truth_sweep_latest.json"
CHAMPION_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
ASSET_BOARD_JSON = OUT_OPS / "geometry_asset_wiring_board_latest.json"

OUT_JSON = OUT_OPS / "field_validated_dollar_claim_ladder_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "field_validated_dollar_claim_ladder.json"
OUT_MD = DOCS / "FIELD_VALIDATED_DOLLAR_CLAIM_LADDER_2026-06-27.md"

BOUNDARY = (
    "Dollar claim ladder only. This artifact separates today's bounded estimated-value language from "
    "future field-validated avoided-cost claims. It does not create realized savings, trading profit, "
    "award certainty, or a fixed price for frozen deltas."
)

IMPROVEMENT_PCTS = [0.001, 0.005, 0.01, 0.05, 0.1, 1.0]
LOSS_POOLS = [1_000_000_000, 10_000_000_000, 100_000_000_000]
CAPTURE_RATES = [0.5, 1.0, 5.0, 10.0, 20.0]


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


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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


def annual_capture(annual_value_usd: float, capture_rate_pct: float) -> float:
    return annual_value_usd * (capture_rate_pct / 100.0)


def sector_math_table() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pool in LOSS_POOLS:
        for pct in IMPROVEMENT_PCTS:
            annual = gross_value(pool, pct)
            rows.append(
                {
                    "loss_pool_usd": pool,
                    "improvement_pct": pct,
                    "annual_gross_avoided_cost_surface_usd": round(annual, 2),
                    "first_3_months_gross_avoided_cost_surface_usd": round(windowed_value(annual, 3), 2),
                    "first_month_gross_avoided_cost_surface_usd": round(windowed_value(annual, 1), 2),
                    "boundary": "Math surface only; not a claim until field validated on a named system.",
                }
            )
    return rows


def capture_table(annual_value_usd: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rate in CAPTURE_RATES:
        annual = annual_capture(annual_value_usd, rate)
        rows.append(
            {
                "capture_rate_pct": rate,
                "annual_contract_surface_usd": round(annual, 2),
                "first_3_months_contract_surface_usd": round(windowed_value(annual, 3), 2),
                "boundary": "Illustrative capture only; revenue requires a grant, contract, pilot, or license.",
            }
        )
    return rows


def current_truth(live_value: dict[str, Any], truth: dict[str, Any], champion: dict[str, Any]) -> dict[str, Any]:
    value_gate = as_dict(live_value.get("value_gate"))
    safe_claim = as_dict(value_gate.get("safe_claim"))
    truth_summary = as_dict(truth.get("summary"))
    truth_gates = as_dict(truth.get("gates"))
    champ_summary = as_dict(champion.get("summary"))

    allowed_annual = as_float(
        value_gate.get("allowed_estimated_annual_value_usd"),
        as_float(truth_summary.get("safe_estimated_annual_value_usd")),
    )
    allowed_hourly = as_float(
        value_gate.get("allowed_estimated_hourly_value_usd"),
        as_float(truth_summary.get("safe_estimated_hourly_value_usd")),
    )
    blocked_annual = max(
        as_float(value_gate.get("blocked_context_only_annual_value_usd")),
        as_float(truth_summary.get("blocked_context_annual_value_usd")),
    )

    return {
        "bounded_estimated_value_claim_allowed_now": bool(
            safe_claim.get("estimated_value_signal_allowed")
            or truth_gates.get("bounded_estimated_value_claim_allowed")
        ),
        "paid_pilot_scoping_allowed_now": bool(truth_gates.get("paid_pilot_scoping_allowed")),
        "field_validated_savings_claim_allowed_now": False,
        "realized_customer_or_government_savings_allowed_now": False,
        "trading_profit_or_autonomous_execution_allowed_now": False,
        "allowed_estimated_hourly_value_usd": round(allowed_hourly, 2),
        "allowed_estimated_annual_value_usd": round(allowed_annual, 2),
        "allowed_estimated_first_3_months_value_usd": round(windowed_value(allowed_annual, 3), 2),
        "blocked_context_annual_value_surface_usd": round(blocked_annual, 2),
        "live_measured_source_rows": as_int(value_gate.get("live_measured_source_rows")),
        "live_measured_sources": as_int(truth_summary.get("measured_sources"), as_int(champ_summary.get("live_measured_sources"))),
        "live_measured_rows": as_int(truth_summary.get("total_measured_rows"), as_int(champ_summary.get("live_total_measured_rows"))),
        "strict_rolling_champion_count": as_int(
            champ_summary.get("strict_rolling_champion_count"),
            as_int(truth_summary.get("rolling_champion_count")),
        ),
        "triple_source_candidate_count": as_int(
            champ_summary.get("triple_source_candidate_count"),
            as_int(truth_summary.get("triple_source_candidate_count")),
        ),
        "vault_hashes_verified": bool(champ_summary.get("vault_hashes_verified") or truth_summary.get("vault_hashes_verified")),
        "vps_domain_live_dashboard_routed": bool(truth_gates.get("vps_domain_live_dashboard_routed")),
        "claim_boundary": (
            "Current values are bounded estimated opportunity surfaces under assumptions. "
            "They are not realized savings or a promise that any buyer will pay."
        ),
    }


def strongest_family(champion: dict[str, Any]) -> dict[str, Any]:
    coc = as_dict(champion.get("champion_of_champions"))
    strongest = as_dict(coc.get("strongest_current"))
    if not strongest:
        rankings = [row for row in as_list(champion.get("family_asset_rankings")) if isinstance(row, dict)]
        strongest = rankings[0] if rankings else {}
    holdout = as_dict(strongest.get("kuramoto_holdout_evidence"))
    return {
        "family_id": strongest.get("family", ""),
        "label": strongest.get("label", strongest.get("family", "")),
        "lane": strongest.get("lane", ""),
        "evidence_status": strongest.get("evidence_status", ""),
        "claim_stage": strongest.get("claim_stage", ""),
        "named_baseline": holdout.get("named_baseline", "locked incumbent baseline required"),
        "holdout_count": as_int(holdout.get("holdout_count")),
        "wins_vs_named_baseline": as_int(holdout.get("wins_vs_kalman") or holdout.get("wins_vs_best_baseline")),
        "win_rate_vs_named_baseline": as_float(holdout.get("win_rate_vs_kalman")),
        "mean_delta_vs_named_baseline": as_float(
            holdout.get("mean_delta_vs_kalman"),
            as_float(strongest.get("rolling_latest_score_delta_vs_named_baseline")),
        ),
        "wilson_95_win_rate_lower": as_float(holdout.get("wilson_95_win_rate_lower")),
        "estimated_rows_replayed": as_int(holdout.get("estimated_rows_replayed")),
        "source_system_count": as_int(holdout.get("source_system_count")),
        "source_systems": holdout.get("source_systems", []),
        "chain_sha256": holdout.get("holdout_chain_sha256", champion.get("board_sha256", "")),
        "ready_for_buyer_authorized_field_replay_request": bool(
            holdout.get("ready_for_buyer_authorized_field_replay_request")
            or strongest.get("ready_for_buyer_authorized_field_replay_request")
        ),
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "plain_english": (
            "This is the current internal alpha-flow leader for asking a buyer to run a locked field replay. "
            "It is not yet a customer savings claim."
        ),
    }


def claim_ladder(truth: dict[str, Any], champ: dict[str, Any]) -> list[dict[str, Any]]:
    current = truth
    field_unlock = [
        "buyer or agency authorizes the field data and use case",
        "incumbent baseline is locked before candidate scoring",
        "holdout windows are pre-registered and hashable",
        "candidate and baseline run on identical inputs and constraints",
        "uncertainty interval and failure cases are reported",
        "buyer accepts the economic conversion factor before dollar language",
        "result is signed, attested, or otherwise traceable",
    ]
    return [
        {
            "tier": 0,
            "name": "Current bounded evidence",
            "allowed_now": bool(current["bounded_estimated_value_claim_allowed_now"]),
            "allowed_language": (
                f"Current live/public evidence supports a bounded estimated value opportunity up to "
                f"{money(current['allowed_estimated_hourly_value_usd'])}/hour or "
                f"{money(current['allowed_estimated_annual_value_usd'])}/year under stated assumptions."
            ),
            "forbidden_language": [
                "we saved the government money",
                "field validated",
                "guaranteed ROI",
                "trading profit",
                "this frozen delta is worth a fixed amount",
            ],
        },
        {
            "tier": 1,
            "name": "Buyer-authorized replay request",
            "allowed_now": bool(champ["ready_for_buyer_authorized_field_replay_request"]),
            "allowed_language": (
                f"The current leading family `{champ['family_id']}` is ready to request buyer-authorized "
                f"holdout replay against `{champ['named_baseline']}` with the existing chain hash preserved."
            ),
            "must_include": [
                "not field validation yet",
                "exact requested dataset/window",
                "locked baseline",
                "acceptance metric",
                "failure reporting",
            ],
        },
        {
            "tier": 2,
            "name": "Field-validated avoided-cost claim",
            "allowed_now": False,
            "allowed_language_after_unlock": (
                "On [named system], during [locked window], against [locked baseline], LumenCore reduced "
                "[accepted metric] by [X% with confidence interval], corresponding to an estimated "
                "avoided-cost opportunity of [$Y in 3 months] and [$Z annualized] under the buyer-approved "
                "economic model."
            ),
            "unlock_conditions": field_unlock,
        },
        {
            "tier": 3,
            "name": "Paid pilot or license pricing",
            "allowed_now": bool(current["paid_pilot_scoping_allowed_now"]),
            "allowed_language": (
                "We can price a paid evidence review, replay pilot, or limited license around the bounded "
                "opportunity surface, but actual payment is a negotiated contract/grant/license outcome."
            ),
            "pricing_models": [
                "fixed paid pilot",
                "platform license",
                "success fee tied to validated avoided cost",
                "grant or SBIR/STTR-funded validation",
                "hybrid fixed fee plus upside after independent validation",
            ],
        },
        {
            "tier": 4,
            "name": "Name-your-price strategic platform",
            "allowed_now": False,
            "allowed_language_after_unlock": (
                "Only after repeated external validations across multiple owners and sectors can the platform "
                "support premium strategic licensing language."
            ),
            "unlock_conditions": [
                "multiple independent field validations",
                "repeatable deployment playbook",
                "procurement-safe cybersecurity and data-handling posture",
                "customer references or signed pilots",
                "clear IP and licensing position",
            ],
        },
    ]


def field_validation_accounting_model() -> dict[str, Any]:
    return {
        "recommended_tracking_windows": [
            {
                "window": "first_30_days",
                "purpose": "fast signal, catches immediate regression or operational friction",
                "formula": "observed_30d_value = baseline_cost_rate * measured_delta_pct * 30_day_hours",
            },
            {
                "window": "first_90_days",
                "purpose": "primary pilot economics window",
                "formula": "observed_90d_value = baseline_cost_rate * measured_delta_pct * 90_day_hours",
            },
            {
                "window": "12_month_annualized",
                "purpose": "budget/license planning after the 90-day window is stable",
                "formula": "annualized_value = observed_90d_value * 4, then discount for seasonality and confidence",
            },
        ],
        "minimum_fields_to_lock_before_replay": [
            "system_owner",
            "system_name",
            "baseline_name_and_version",
            "candidate_name_and_version",
            "input_window",
            "outcome_metric",
            "cost_conversion_factor",
            "confidence_rule",
            "exclusions_and_failure_cases",
        ],
        "confidence_discount_rule": (
            "Use the lower confidence bound, not the headline mean, when converting improvement into "
            "buyer-facing dollars."
        ),
    }


def build_payload() -> dict[str, Any]:
    live_value = read_json(LIVE_VALUE_JSON)
    truth_sweep = read_json(TRUTH_SWEEP_JSON)
    champion = read_json(CHAMPION_JSON)
    asset_board = read_json(ASSET_BOARD_JSON)

    current = current_truth(live_value, truth_sweep, champion)
    champ = strongest_family(champion)
    safe_annual = as_float(current["allowed_estimated_annual_value_usd"])
    sector_rows = sector_math_table()
    capture_rows = capture_table(safe_annual)

    one_billion = [row for row in sector_rows if row["loss_pool_usd"] == 1_000_000_000]
    payload = {
        "schema": "field_validated_dollar_claim_ladder_v1",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "direct_answer": {
            "can_claim_real_savings_right_now": False,
            "can_claim_bounded_estimated_value_right_now": current["bounded_estimated_value_claim_allowed_now"],
            "best_current_wording": (
                f"Bounded estimated value opportunity up to {money(current['allowed_estimated_hourly_value_usd'])}/hour "
                f"or {money(current['allowed_estimated_annual_value_usd'])}/year under stated assumptions; "
                "not realized savings and not field validation."
            ),
            "post_field_validation_wording": (
                "After a buyer-authorized locked replay, state the exact system, baseline, metric, "
                "3-month observed value, annualized value, and confidence boundary."
            ),
            "billion_dollar_sector_note": (
                "For a $1B relevant loss pool, 0.001% is $10,000/year and 0.01% is $100,000/year. "
                "That is useful proof, but large revenue needs a larger loss pool, larger validated improvement, "
                "or license/platform pricing beyond a pure savings share."
            ),
        },
        "current_truth": current,
        "strongest_alpha_flow_family": champ,
        "claim_ladder": claim_ladder(current, champ),
        "field_validation_accounting_model": field_validation_accounting_model(),
        "sector_math": {
            "interpretation": "gross avoided-cost surface = relevant annual loss pool * measured improvement percentage",
            "one_billion_examples": one_billion,
            "all_examples": sector_rows,
        },
        "capture_from_current_safe_estimate": capture_rows,
        "buyer_pricing_guidance": {
            "what_to_track": [
                "3-month observed avoided-cost surface",
                "12-month annualized avoided-cost surface",
                "capture rate or license fee",
                "confidence-adjusted lower-bound value",
                "operator burden and false-alarm reduction",
            ],
            "what_to_ask_for_first": (
                "A paid field replay or validation pilot, not a huge savings-share claim before their baseline and economics are locked."
            ),
            "why_this_matters": (
                "Agencies and buyers do not buy a mystical delta. They buy reduced risk, reduced cost, faster review, "
                "better detection, lower downtime, or a validated decision advantage."
            ),
        },
        "name_your_price_gate": {
            "allowed_now": False,
            "plain_truth": (
                "Name-your-price power starts after external field validation plus procurement-safe repeatability. "
                "Right now the correct move is to price validation and evidence review."
            ),
            "next_10_actions": [
                "Run the latest truth sweep with fresh live pull and vault staging.",
                "Rebuild champion and asset boards from the fresh sweep.",
                "Generate this dollar claim ladder after the fresh inputs.",
                "Pick one buyer-authorized replay target: Kuramoto/phase timing, Brachistochrone routing, or energy price pressure.",
                "Lock the incumbent baseline and acceptance metric before sending any proposal.",
                "Map the result to a 90-day and annualized avoided-cost model.",
                "Prepare one paid pilot ask with exact data needed and claim boundaries.",
                "Deploy the same fresh JSON proof feeds to the live domain and verify reachable hashes.",
                "Attach the claim ladder and field-validation protocol to grants/contracts.",
                "Do not make realized-savings, trading-profit, or guaranteed-award claims until the gate flips.",
            ],
        },
        "dashboard_context": {
            "asset_board_summary": asset_board.get("summary", {}),
            "feeds_to_surface": [
                "dashboard/data/field_validated_dollar_claim_ladder.json",
                "dashboard/data/live_proof_value_meter.json",
                "dashboard/data/geometry_champion_of_champions.json",
                "dashboard/data/geometry_asset_wiring_board.json",
                "dashboard/data/field_money_truth_sweep.json",
            ],
        },
        "inputs": {
            "live_proof_value_meter": str(LIVE_VALUE_JSON.relative_to(ROOT)).replace("\\", "/"),
            "field_money_truth_sweep": str(TRUTH_SWEEP_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_champion_of_champions": str(CHAMPION_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_asset_wiring_board": str(ASSET_BOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    payload["claim_ladder_sha256"] = stable_sha256(
        {
            "current_truth": payload["current_truth"],
            "strongest_alpha_flow_family": payload["strongest_alpha_flow_family"],
            "sector_math": payload["sector_math"]["one_billion_examples"],
            "capture_from_current_safe_estimate": payload["capture_from_current_safe_estimate"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    current = payload["current_truth"]
    champ = payload["strongest_alpha_flow_family"]
    lines = [
        "# Field-Validated Dollar Claim Ladder",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Claim ladder SHA-256: `{payload['claim_ladder_sha256']}`",
        "",
        "## Boundary",
        "",
        payload["boundary"],
        "",
        "## Direct Answer",
        "",
        f"- Real savings claim right now: `{str(payload['direct_answer']['can_claim_real_savings_right_now']).lower()}`",
        f"- Bounded estimated value claim right now: `{str(payload['direct_answer']['can_claim_bounded_estimated_value_right_now']).lower()}`",
        f"- Best current wording: {payload['direct_answer']['best_current_wording']}",
        f"- Post-field-validation wording: {payload['direct_answer']['post_field_validation_wording']}",
        f"- Billion-dollar note: {payload['direct_answer']['billion_dollar_sector_note']}",
        "",
        "## Current Numbers",
        "",
        f"- Safe estimated value: `{money(current['allowed_estimated_hourly_value_usd'])}/hour`",
        f"- Safe estimated annual surface: `{money(current['allowed_estimated_annual_value_usd'])}`",
        f"- Safe estimated first 3 months: `{money(current['allowed_estimated_first_3_months_value_usd'])}`",
        f"- Blocked context-only annual surface: `{money(current['blocked_context_annual_value_surface_usd'])}`",
        f"- Field validated savings allowed now: `{str(current['field_validated_savings_claim_allowed_now']).lower()}`",
        f"- VPS/domain live dashboard routed: `{str(current['vps_domain_live_dashboard_routed']).lower()}`",
        "",
        "## Current Alpha-Flow Leader",
        "",
        f"- Family: `{champ['family_id']}`",
        f"- Lane: `{champ['lane']}`",
        f"- Baseline: `{champ['named_baseline']}`",
        f"- Holdout wins: `{champ['wins_vs_named_baseline']} / {champ['holdout_count']}`",
        f"- Mean delta vs baseline: `{champ['mean_delta_vs_named_baseline']}`",
        f"- Estimated rows replayed: `{champ['estimated_rows_replayed']}`",
        f"- Ready for buyer-authorized replay request: `{str(champ['ready_for_buyer_authorized_field_replay_request']).lower()}`",
        f"- Boundary: {champ['plain_english']}",
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
            lines.append(f"- Current language: {row['allowed_language']}")
        if row.get("allowed_language_after_unlock"):
            lines.append(f"- After unlock: {row['allowed_language_after_unlock']}")
        if row.get("unlock_conditions"):
            lines.append("- Unlock conditions:")
            lines.extend(f"  - {item}" for item in row["unlock_conditions"])
        if row.get("forbidden_language"):
            lines.append("- Forbidden now:")
            lines.extend(f"  - {item}" for item in row["forbidden_language"])
        lines.append("")

    lines.extend(
        [
            "## $1B Loss-Pool Examples",
            "",
            "| Improvement | 1 Month | 3 Months | 12 Months |",
            "| ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["sector_math"]["one_billion_examples"]:
        lines.append(
            f"| {row['improvement_pct']}% | {money(row['first_month_gross_avoided_cost_surface_usd'])} | "
            f"{money(row['first_3_months_gross_avoided_cost_surface_usd'])} | "
            f"{money(row['annual_gross_avoided_cost_surface_usd'])} |"
        )

    lines.extend(
        [
            "",
            "## Capture From Current Safe Estimate",
            "",
            "| Capture Rate | 3-Month Contract Surface | Annual Contract Surface |",
            "| ---: | ---: | ---: |",
        ]
    )
    for row in payload["capture_from_current_safe_estimate"]:
        lines.append(
            f"| {row['capture_rate_pct']}% | {money(row['first_3_months_contract_surface_usd'])} | "
            f"{money(row['annual_contract_surface_usd'])} |"
        )

    lines.extend(["", "## Next 10 Actions", ""])
    lines.extend(f"- {item}" for item in payload["name_your_price_gate"]["next_10_actions"])
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
                "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "real_savings_claim_now": payload["direct_answer"]["can_claim_real_savings_right_now"],
                "bounded_estimated_value_now": payload["direct_answer"]["can_claim_bounded_estimated_value_right_now"],
                "safe_estimated_annual_value_usd": payload["current_truth"]["allowed_estimated_annual_value_usd"],
                "top_family": payload["strongest_alpha_flow_family"]["family_id"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
