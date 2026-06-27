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

KURAMOTO_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"
CHAMPION_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
TRUTH_SWEEP_JSON = OUT_OPS / "field_money_truth_sweep_latest.json"
VALUE_METER_JSON = OUT_OPS / "live_proof_value_meter_latest.json"
DOLLAR_LADDER_JSON = OUT_OPS / "field_validated_dollar_claim_ladder_latest.json"
LIVE_DOMAIN_DEPLOYMENT_JSON = OUT_OPS / "live_domain_deployment_feed_latest.json"

OUT_JSON = OUT_OPS / "champion_metric_gauntlet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "champion_metric_gauntlet.json"
OUT_MD = DOCS / "CHAMPION_METRIC_GAUNTLET_2026-06-27.md"

BOUNDARY = (
    "Champion metric gauntlet only. This artifact explains the current internal winner, the tests it has "
    "passed, the tests it has not passed, and the safest claim language. It does not create field validation, "
    "realized savings, trading profit, medical efficacy, award certainty, or a fixed dollar price for frozen deltas."
)


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


def metric_gate(
    name: str,
    actual: Any,
    threshold: Any,
    passed: bool,
    why_it_matters: str,
    claim_effect: str,
    blocker: bool = False,
) -> dict[str, Any]:
    return {
        "name": name,
        "actual": actual,
        "threshold": threshold,
        "passed": bool(passed),
        "status": "PASS" if passed else ("BLOCKED" if blocker else "NEEDS_WORK"),
        "blocker": bool(blocker and not passed),
        "why_it_matters": why_it_matters,
        "claim_effect": claim_effect,
    }


def live_domain_verified() -> bool:
    deployment = read_json(LIVE_DOMAIN_DEPLOYMENT_JSON)
    summary = as_dict(deployment.get("summary"))
    return (
        summary.get("domain_deployment_state") == "LIVE_DOMAIN_HASH_VERIFIED"
        and bool(summary.get("live_domain_reviewer_ready"))
        and as_int(summary.get("required_remote_hash_match_count")) >= as_int(summary.get("required_feed_count"), 1)
    )


def strongest_current(champion: dict[str, Any], kuramoto: dict[str, Any]) -> dict[str, Any]:
    board = as_dict(champion.get("champion_of_champions"))
    strongest = as_dict(board.get("strongest_current"))
    summary = as_dict(kuramoto.get("summary"))
    holdout = as_dict(strongest.get("kuramoto_holdout_evidence"))
    evidence = summary or holdout
    family = str(strongest.get("family") or evidence.get("candidate") or "kuramoto_phase_coupling")
    label = str(strongest.get("label") or "Kuramoto phase coupling")
    baseline = str(evidence.get("named_baseline") or "kalman_filter")

    return {
        "family": family,
        "label": label,
        "lane": strongest.get("lane", "wave_resonance_timing"),
        "evidence_status": strongest.get(
            "evidence_status",
            "expanded_source_conditioned_holdout_winner_not_field_validated",
        ),
        "claim_stage": strongest.get(
            "claim_stage",
            "buyer_authorized_field_replay_request_ready_not_field_validated",
        ),
        "named_baseline": baseline,
        "holdout_count": as_int(evidence.get("holdout_count")),
        "wins_vs_named_baseline": as_int(evidence.get("wins_vs_kalman") or evidence.get("wins_vs_best_baseline")),
        "wins_vs_best_baseline": as_int(evidence.get("wins_vs_best_baseline")),
        "losses_or_ties_vs_named_baseline": as_int(evidence.get("losses_or_ties_vs_kalman")),
        "win_rate_vs_named_baseline": round(as_float(evidence.get("win_rate_vs_kalman")), 6),
        "mean_delta_vs_named_baseline": round(as_float(evidence.get("mean_delta_vs_kalman")), 6),
        "min_delta_vs_named_baseline": round(as_float(evidence.get("min_delta_vs_kalman")), 6),
        "max_delta_vs_named_baseline": round(as_float(evidence.get("max_delta_vs_kalman")), 6),
        "effect_stability_ratio_min_over_mean": round(
            as_float(evidence.get("min_delta_vs_kalman")) / max(as_float(evidence.get("mean_delta_vs_kalman")), 1e-12),
            6,
        ),
        "one_sided_sign_test_p_value": as_float(evidence.get("one_sided_sign_test_p_value"), 1.0),
        "wilson_95_win_rate_lower": round(as_float(evidence.get("wilson_95_win_rate_lower")), 6),
        "wilson_95_win_rate_upper": round(as_float(evidence.get("wilson_95_win_rate_upper")), 6),
        "estimated_rows_replayed": as_int(evidence.get("estimated_rows_replayed")),
        "numeric_samples_read": as_int(evidence.get("numeric_samples_read")),
        "source_system_count": as_int(evidence.get("source_system_count")),
        "source_systems": as_list(evidence.get("source_systems")),
        "holdout_chain_sha256": str(evidence.get("holdout_chain_sha256", "")),
        "ready_for_buyer_authorized_field_replay_request": bool(
            evidence.get("ready_for_buyer_authorized_field_replay_request")
            or strongest.get("ready_for_buyer_authorized_field_replay_request")
        ),
        "passes_internal_20_holdout_gate": bool(evidence.get("passes_internal_20_holdout_gate")),
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
    }


def build_metric_gauntlet(
    strongest: dict[str, Any],
    champion_summary: dict[str, Any],
    truth_summary: dict[str, Any],
    truth_gates: dict[str, Any],
    live_domain_ready: bool,
) -> list[dict[str, Any]]:
    holdout_count = as_int(strongest.get("holdout_count"))
    wins = as_int(strongest.get("wins_vs_named_baseline"))
    win_rate = as_float(strongest.get("win_rate_vs_named_baseline"))
    min_delta = as_float(strongest.get("min_delta_vs_named_baseline"))
    p_value = as_float(strongest.get("one_sided_sign_test_p_value"), 1.0)
    wilson_lower = as_float(strongest.get("wilson_95_win_rate_lower"))
    source_systems = as_int(strongest.get("source_system_count"))
    rows = as_int(strongest.get("estimated_rows_replayed"))
    chain = str(strongest.get("holdout_chain_sha256", ""))

    return [
        metric_gate(
            "holdout_depth",
            holdout_count,
            ">= 20 source-conditioned holdouts",
            holdout_count >= 20,
            "Prevents one-good-run storytelling.",
            "Supports internal champion language.",
        ),
        metric_gate(
            "baseline_win_count",
            f"{wins}/{holdout_count}",
            ">= 16/20 and preferably all positive",
            wins >= 16 and holdout_count >= 20,
            "Shows the candidate beats a named incumbent across repeated holdouts.",
            "Supports buyer-authorized field replay request language.",
        ),
        metric_gate(
            "baseline_win_rate",
            round(win_rate, 6),
            ">= 0.80",
            win_rate >= 0.80,
            "Reviewers need a simple repeatability measure.",
            "Supports strongest current candidate language.",
        ),
        metric_gate(
            "minimum_delta_positive",
            round(min_delta, 6),
            "> 0",
            min_delta > 0,
            "The weakest holdout still needs to beat the baseline.",
            "Supports robust internal evidence language.",
        ),
        metric_gate(
            "sign_test_strength",
            p_value,
            "<= 0.001",
            p_value <= 0.001,
            "Separates repeated directional wins from noise.",
            "Supports strong internal statistical evidence language.",
        ),
        metric_gate(
            "wilson_lower_bound",
            round(wilson_lower, 6),
            ">= 0.75",
            wilson_lower >= 0.75,
            "Keeps the win-rate claim conservative under uncertainty.",
            "Supports reviewer-safe confidence wording.",
        ),
        metric_gate(
            "source_system_diversity",
            source_systems,
            ">= 3 source systems",
            source_systems >= 3,
            "Reduces the chance that one dataset family is carrying the result.",
            "Supports multi-source internal replay language.",
        ),
        metric_gate(
            "row_replay_depth",
            rows,
            ">= 1,000,000 estimated rows replayed",
            rows >= 1_000_000,
            "Shows the proof was not built on a toy-sized scrape.",
            "Supports scale-of-evidence language.",
        ),
        metric_gate(
            "hash_chain_present",
            chain[:12] + "..." if len(chain) == 64 else chain,
            "64 hex characters",
            len(chain) == 64,
            "Makes the proof packet traceable.",
            "Supports frozen evidence language.",
        ),
        metric_gate(
            "vault_hashes_verified",
            bool(champion_summary.get("vault_hashes_verified") or truth_summary.get("vault_hashes_verified")),
            "true",
            bool(champion_summary.get("vault_hashes_verified") or truth_summary.get("vault_hashes_verified")),
            "Protects provenance when copying to external storage.",
            "Supports reproducibility infrastructure language.",
        ),
        metric_gate(
            "all_families_live_benchmarked",
            bool(truth_gates.get("all_registered_families_live_benchmarked")),
            "true before broad all-family claims",
            bool(truth_gates.get("all_registered_families_live_benchmarked")),
            "Blocks universal geometry-superiority claims.",
            "Broad all-family language remains blocked.",
            blocker=True,
        ),
        metric_gate(
            "live_domain_feed_routed",
            bool(truth_gates.get("vps_domain_live_dashboard_routed") or live_domain_ready),
            "true before hosted reviewer proof claim",
            bool(truth_gates.get("vps_domain_live_dashboard_routed") or live_domain_ready),
            "A reviewer-facing domain needs fresh hosted hashes, not just local files.",
            "Hosted reviewer proof language is allowed once all required feed hashes match.",
            blocker=True,
        ),
        metric_gate(
            "field_validation",
            bool(truth_gates.get("field_validation_claim_allowed")),
            "true before field validated language",
            bool(truth_gates.get("field_validation_claim_allowed")),
            "Requires buyer-authorized operational data and a locked acceptance test.",
            "Field-validation and realized-savings language remains blocked.",
            blocker=True,
        ),
    ]


def dashboard_feed_status() -> dict[str, Any]:
    feeds = [
        DASHBOARD_DATA / "champion_metric_gauntlet.json",
        DASHBOARD_DATA / "kuramoto_holdout_expansion.json",
        DASHBOARD_DATA / "geometry_champion_of_champions.json",
        DASHBOARD_DATA / "field_money_truth_sweep.json",
        DASHBOARD_DATA / "live_proof_value_meter.json",
        DASHBOARD_DATA / "field_validated_dollar_claim_ladder.json",
        DASHBOARD_DATA / "dollar_claim_gate.json",
    ]
    rows = []
    for path in feeds:
        rows.append(
            {
                "relative_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else 0,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "",
            }
        )
    ready = [row for row in rows if row["exists"]]
    domain_ready = live_domain_verified()
    return {
        "local_feed_count": len(rows),
        "local_feed_ready_count": len(ready),
        "local_feeds_ready": len(ready) == len(rows),
        "live_domain_routed": domain_ready,
        "status": (
            "LIVE_DOMAIN_HASH_VERIFIED"
            if len(ready) == len(rows) and domain_ready
            else ("LOCAL_READY_DOMAIN_NOT_VERIFIED" if len(ready) == len(rows) else "LOCAL_FEEDS_INCOMPLETE")
        ),
        "feeds": rows,
    }


def next_tests() -> list[dict[str, str]]:
    return [
        {
            "test": "amplitude_error_check",
            "reason": "Phase-locking can win timing while hiding amplitude mistakes.",
            "output": "MAE/RMSE/MAPE by holdout and by source system.",
        },
        {
            "test": "phase_error_distribution",
            "reason": "The strongest claim is phase behavior; measure it directly.",
            "output": "Circular error, phase slip count, and phase-lock duration.",
        },
        {
            "test": "directional_accuracy",
            "reason": "Buyers care whether the system moves action in the right direction.",
            "output": "Up/down or risk/no-risk confusion matrix.",
        },
        {
            "test": "residual_autocorrelation",
            "reason": "A model that leaves structured residuals has not captured the system.",
            "output": "Ljung-Box style residual health by holdout.",
        },
        {
            "test": "ablation_against_neighbor_geometries",
            "reason": "Proves Kuramoto is not just inheriting a general wave-family boost.",
            "output": "Kuramoto vs PLL, Lissajous, harmonic potential, and Kalman variants.",
        },
        {
            "test": "drift_and_outlier_stress",
            "reason": "Field systems break under drift, missingness, and spikes.",
            "output": "Performance under dropouts, jumps, and delayed samples.",
        },
        {
            "test": "latency_and_cost_budget",
            "reason": "Operational buyers need to know if it runs fast enough.",
            "output": "Runtime, memory, and update cadence per source.",
        },
        {
            "test": "buyer_economic_conversion_dry_run",
            "reason": "Dollar claims need accepted conversion factors.",
            "output": "Scenario table only, with field-validation gates still closed.",
        },
        {
            "test": "hosted_hash_verification",
            "reason": "The live domain should serve the same proof hashes as the local packet.",
            "output": "VPS/domain feed manifest with matching SHA-256 values.",
        },
        {
            "test": "authorized_field_replay_protocol",
            "reason": "This is the bridge from internal proof to a field validation claim.",
            "output": "Signed or logged buyer replay packet with locked baseline and acceptance criteria.",
        },
    ]


def build_payload() -> dict[str, Any]:
    generated = now_utc()
    kuramoto = read_json(KURAMOTO_JSON)
    champion = read_json(CHAMPION_JSON)
    truth = read_json(TRUTH_SWEEP_JSON)
    value_meter = read_json(VALUE_METER_JSON)
    dollar_ladder = read_json(DOLLAR_LADDER_JSON)

    champion_summary = as_dict(champion.get("summary"))
    truth_summary = as_dict(truth.get("summary"))
    truth_gates = as_dict(truth.get("gates"))
    strongest = strongest_current(champion, kuramoto)
    domain_ready = live_domain_verified()
    gauntlet = build_metric_gauntlet(strongest, champion_summary, truth_summary, truth_gates, domain_ready)
    blockers = [row for row in gauntlet if row.get("blocker")]
    passed = [row for row in gauntlet if row.get("passed")]
    safe_annual = as_float(
        champion_summary.get("safe_estimated_annual_value_usd"),
        as_float(truth_summary.get("safe_estimated_annual_value_usd")),
    )
    safe_hourly = as_float(
        champion_summary.get("safe_estimated_hourly_value_usd"),
        as_float(truth_summary.get("safe_estimated_hourly_value_usd")),
    )
    feed_status = dashboard_feed_status()

    payload: dict[str, Any] = {
        "generated_utc": generated,
        "schema": "champion_metric_gauntlet_v1",
        "purpose": "Reviewer-safe metric gauntlet for the current strongest geometry family.",
        "boundary": BOUNDARY,
        "strongest_current": strongest,
        "summary": {
            "internal_champion": True,
            "champion_family": strongest["family"],
            "champion_label": strongest["label"],
            "named_baseline": strongest["named_baseline"],
            "holdout_wins": strongest["wins_vs_named_baseline"],
            "holdout_count": strongest["holdout_count"],
            "holdout_win_rate": strongest["win_rate_vs_named_baseline"],
            "mean_delta_vs_named_baseline": strongest["mean_delta_vs_named_baseline"],
            "min_delta_vs_named_baseline": strongest["min_delta_vs_named_baseline"],
            "source_system_count": strongest["source_system_count"],
            "estimated_rows_replayed": strongest["estimated_rows_replayed"],
            "numeric_samples_read": strongest["numeric_samples_read"],
            "one_sided_sign_test_p_value": strongest["one_sided_sign_test_p_value"],
            "wilson_95_win_rate_lower": strongest["wilson_95_win_rate_lower"],
            "gauntlet_pass_count": len(passed),
            "gauntlet_total_count": len(gauntlet),
            "blocking_gate_count": len(blockers),
            "reviewer_safe_internal_claim_allowed": True,
            "buyer_authorized_field_replay_request_ready": bool(
                strongest["ready_for_buyer_authorized_field_replay_request"]
            ),
            "bounded_estimated_value_claim_allowed": bool(
                truth_gates.get("bounded_estimated_value_claim_allowed")
                or champion_summary.get("bounded_estimated_value_claim_allowed")
            ),
            "paid_pilot_scoping_allowed": bool(
                truth_gates.get("paid_pilot_scoping_allowed") or champion_summary.get("paid_pilot_scoping_allowed")
            ),
            "safe_estimated_hourly_value_usd": round(safe_hourly, 2),
            "safe_estimated_annual_value_usd": round(safe_annual, 2),
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "live_domain_reviewer_ready": bool(feed_status["live_domain_routed"]),
            "plain_english_answer": (
                f"{strongest['label']} is the current internal champion because it beat "
                f"{strongest['named_baseline']} on {strongest['wins_vs_named_baseline']}/"
                f"{strongest['holdout_count']} source-conditioned holdouts across "
                f"{strongest['source_system_count']} source systems. That is strong enough to request "
                "a buyer-authorized field replay, but it is not field validation or realized dollar savings yet."
            ),
        },
        "metric_gauntlet": gauntlet,
        "blockers": blockers,
        "next_10_tests": next_tests(),
        "dashboard_feed_status": feed_status,
        "source_artifacts": {
            "kuramoto_holdout_expansion": str(KURAMOTO_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_champion_of_champions": str(CHAMPION_JSON.relative_to(ROOT)).replace("\\", "/"),
            "field_money_truth_sweep": str(TRUTH_SWEEP_JSON.relative_to(ROOT)).replace("\\", "/"),
            "live_proof_value_meter": str(VALUE_METER_JSON.relative_to(ROOT)).replace("\\", "/"),
            "field_validated_dollar_claim_ladder": str(DOLLAR_LADDER_JSON.relative_to(ROOT)).replace("\\", "/"),
        },
        "source_status": {
            "kuramoto_loaded": bool(kuramoto),
            "champion_loaded": bool(champion),
            "truth_sweep_loaded": bool(truth),
            "value_meter_loaded": bool(value_meter),
            "dollar_ladder_loaded": bool(dollar_ladder),
        },
        "claim_language": {
            "allowed": [
                "current internal champion",
                "source-conditioned holdout winner against a named baseline",
                "buyer-authorized field replay request ready",
                "bounded estimated opportunity surface",
                "paid pilot scoping candidate",
            ],
            "not_allowed": [
                "field validated",
                "realized dollar savings",
                "grant award certainty",
                "fixed dollar value per frozen delta",
                "live trading edge or autonomous execution",
                "universal geometry superiority",
            ],
        },
    }
    payload["gauntlet_sha256"] = stable_sha256(
        {
            "strongest_current": payload["strongest_current"],
            "summary": payload["summary"],
            "metric_gauntlet": payload["metric_gauntlet"],
            "blockers": payload["blockers"],
            "next_10_tests": payload["next_10_tests"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = as_dict(payload.get("summary"))
    strongest = as_dict(payload.get("strongest_current"))
    lines = [
        "# Champion Metric Gauntlet",
        "",
        f"Generated UTC: `{payload.get('generated_utc')}`",
        "",
        "## What To Ask Me",
        "",
        "Ask questions that force evidence, gates, and next actions:",
        "",
        "1. What is proven right now, and what is only promising?",
        "2. Which geometry family is the current champion, and what named baseline did it beat?",
        "3. How many holdouts, rows, source systems, and hashes back the claim?",
        "4. Which claim is safe for a grant reviewer today?",
        "5. What exactly blocks field validation and real dollar savings?",
        "6. What is the next test that would increase valuation the most?",
        "7. What should be shown on the live domain before a reviewer sees it?",
        "8. What should never be said because it overclaims the evidence?",
        "",
        "## Current Answer",
        "",
        summary.get("plain_english_answer", ""),
        "",
        "## Strongest Current Candidate",
        "",
        f"- Family: `{strongest.get('family')}`",
        f"- Label: `{strongest.get('label')}`",
        f"- Lane: `{strongest.get('lane')}`",
        f"- Named baseline: `{strongest.get('named_baseline')}`",
        f"- Holdout wins: `{summary.get('holdout_wins')}/{summary.get('holdout_count')}`",
        f"- Mean delta vs baseline: `{summary.get('mean_delta_vs_named_baseline')}`",
        f"- Min delta vs baseline: `{summary.get('min_delta_vs_named_baseline')}`",
        f"- Source systems: `{summary.get('source_system_count')}`",
        f"- Estimated rows replayed: `{summary.get('estimated_rows_replayed')}`",
        f"- Sign-test p-value: `{summary.get('one_sided_sign_test_p_value')}`",
        f"- Wilson lower 95% win-rate bound: `{summary.get('wilson_95_win_rate_lower')}`",
        f"- Holdout chain SHA-256: `{strongest.get('holdout_chain_sha256')}`",
        "",
        "## Safe Claim State",
        "",
        f"- Reviewer-safe internal claim allowed: `{str(summary.get('reviewer_safe_internal_claim_allowed')).lower()}`",
        f"- Buyer-authorized field replay request ready: `{str(summary.get('buyer_authorized_field_replay_request_ready')).lower()}`",
        f"- Bounded estimated value claim allowed: `{str(summary.get('bounded_estimated_value_claim_allowed')).lower()}`",
        f"- Paid pilot scoping allowed: `{str(summary.get('paid_pilot_scoping_allowed')).lower()}`",
        f"- Field-validation claim allowed: `{str(summary.get('field_validation_claim_allowed')).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(summary.get('real_dollar_savings_claim_allowed')).lower()}`",
        f"- Live trading or autonomous execution allowed: `{str(summary.get('live_trading_or_autonomous_execution_allowed')).lower()}`",
        f"- Safe estimated hourly value surface: `{money(summary.get('safe_estimated_hourly_value_usd'))}`",
        f"- Safe estimated annual value surface: `{money(summary.get('safe_estimated_annual_value_usd'))}`",
        "",
        "## Metric Gates",
        "",
    ]
    for gate in as_list(payload.get("metric_gauntlet")):
        if not isinstance(gate, dict):
            continue
        lines.append(
            f"- `{gate['name']}`: `{gate['status']}` | actual `{gate['actual']}` | threshold `{gate['threshold']}`"
        )
    lines.extend(
        [
            "",
            "## Blockers",
            "",
        ]
    )
    blockers = [row for row in as_list(payload.get("blockers")) if isinstance(row, dict)]
    if blockers:
        for row in blockers:
            lines.append(f"- `{row['name']}`: {row['claim_effect']}")
    else:
        lines.append("- No blocking gates detected.")
    lines.extend(
        [
            "",
            "## Next 10 Tests",
            "",
        ]
    )
    for row in as_list(payload.get("next_10_tests")):
        if isinstance(row, dict):
            lines.append(f"- `{row['test']}`: {row['reason']} Output: {row['output']}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            payload.get("boundary", BOUNDARY),
            "",
            f"Gauntlet SHA-256: `{payload.get('gauntlet_sha256')}`",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(payload["summary"]["plain_english_answer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
