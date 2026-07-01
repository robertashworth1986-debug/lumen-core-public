from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

HOLDOUT_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"
GAUNTLET_JSON = OUT_OPS / "champion_metric_gauntlet_latest.json"
GEOMETRY_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
REVENUE_JSON = OUT_OPS / "proof_to_revenue_engine_latest.json"
LIVE_DOMAIN_JSON = OUT_OPS / "live_domain_deployment_feed_latest.json"

OUT_JSON = OUT_OPS / "champion_stress_test_matrix_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "champion_stress_test_matrix.json"
OUT_MD = DOCS / "CHAMPION_STRESS_TEST_MATRIX_2026-06-27.md"

BOUNDARY = (
    "Champion stress-test matrix. This artifact compacts the current champion's source-conditioned "
    "holdout replay evidence into a buyer/reviewer-safe test matrix. It does not create field "
    "validation, realized savings, fixed frozen-delta pricing, live trading authorization, medical "
    "efficacy, or universal geometry-superiority claims."
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


def mean(values: list[float]) -> float:
    return round(statistics.mean(values), 6) if values else 0.0


def min_or_zero(values: list[float]) -> float:
    return round(min(values), 6) if values else 0.0


def max_or_zero(values: list[float]) -> float:
    return round(max(values), 6) if values else 0.0


def pass_gate(
    name: str,
    passed: bool,
    actual: Any,
    threshold: str,
    why: str,
    claim_effect: str,
    blocker: bool = False,
    status: str | None = None,
) -> dict[str, Any]:
    gate_status = status or ("PASS" if passed else ("BLOCKED" if blocker else "FAIL"))
    return {
        "name": name,
        "status": gate_status,
        "passed": bool(passed),
        "blocker": bool(blocker),
        "actual": actual,
        "threshold": threshold,
        "why_it_matters": why,
        "claim_effect": claim_effect,
    }


def blocked_gate(name: str, why: str, unlock: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": "NOT_RUN_REQUIRES_NEXT_GATE",
        "passed": False,
        "blocker": True,
        "actual": "not measured in current artifact",
        "threshold": unlock,
        "why_it_matters": why,
        "claim_effect": "Blocks field-validation, realized-savings, and strongest technical superiority language.",
    }


def source_matrix(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("source_system") or "unknown")].append(row)

    matrix: list[dict[str, Any]] = []
    for source, source_rows in sorted(grouped.items()):
        deltas = [as_float(row.get("delta_vs_kalman")) for row in source_rows]
        best_deltas = [as_float(row.get("delta_vs_best_baseline")) for row in source_rows]
        profiles = [as_dict(row.get("profile")) for row in source_rows]
        matrix.append(
            {
                "source_system": source,
                "holdout_count": len(source_rows),
                "wins_vs_named_baseline": sum(bool(row.get("candidate_beats_kalman")) for row in source_rows),
                "wins_vs_best_same_run_baseline": sum(
                    bool(row.get("candidate_beats_best_baseline")) for row in source_rows
                ),
                "estimated_rows": sum(as_int(row.get("estimated_rows")) for row in source_rows),
                "numeric_samples": sum(as_int(row.get("numeric_samples")) for row in source_rows),
                "fallback_count": sum(bool(profile.get("fallback_used")) for profile in profiles),
                "min_delta_vs_named_baseline": min_or_zero(deltas),
                "mean_delta_vs_named_baseline": mean(deltas),
                "max_delta_vs_named_baseline": max_or_zero(deltas),
                "min_delta_vs_best_same_run_baseline": min_or_zero(best_deltas),
                "mean_delta_vs_best_same_run_baseline": mean(best_deltas),
                "max_delta_vs_best_same_run_baseline": max_or_zero(best_deltas),
                "mean_stress_index": mean([as_float(profile.get("stress_index")) for profile in profiles]),
                "max_shock_index": max_or_zero([as_float(profile.get("shock_index")) for profile in profiles]),
                "mean_abs_trend_index": mean([abs(as_float(profile.get("trend_index"))) for profile in profiles]),
                "mean_coefficient_of_variation": mean(
                    [as_float(profile.get("coefficient_of_variation")) for profile in profiles]
                ),
                "representative_sources": sorted(
                    {
                        str(as_dict(row.get("profile")).get("source") or row.get("source_path") or "")
                        for row in source_rows
                        if as_dict(row.get("profile")).get("source") or row.get("source_path")
                    }
                )[:5],
            }
        )
    return matrix


def metric_matrix(
    rows: list[dict[str, Any]],
    gauntlet_summary: dict[str, Any],
    geometry_summary: dict[str, Any],
    live_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    holdout_count = len(rows)
    wins_named = sum(bool(row.get("candidate_beats_kalman")) for row in rows)
    wins_best = sum(bool(row.get("candidate_beats_best_baseline")) for row in rows)
    deltas = [as_float(row.get("delta_vs_kalman")) for row in rows]
    best_deltas = [as_float(row.get("delta_vs_best_baseline")) for row in rows]
    ranks = [as_int(row.get("candidate_rank"), 999) for row in rows]
    rank_1_share = (sum(1 for rank in ranks if rank == 1) / holdout_count) if holdout_count else 0.0
    source_systems = {str(row.get("source_system") or "unknown") for row in rows}
    estimated_rows = sum(as_int(row.get("estimated_rows")) for row in rows)
    numeric_samples = sum(as_int(row.get("numeric_samples")) for row in rows)
    profiles = [as_dict(row.get("profile")) for row in rows]
    fallback_count = sum(bool(profile.get("fallback_used")) for profile in profiles)
    fallback_rate = fallback_count / holdout_count if holdout_count else 1.0
    stress_count = sum(as_float(profile.get("stress_index")) >= 0.5 for profile in profiles)
    trend_count = sum(abs(as_float(profile.get("trend_index"))) >= 0.01 for profile in profiles)
    shock_count = sum(as_float(profile.get("shock_index")) > 0.0 for profile in profiles)
    all_family_gap = as_int(geometry_summary.get("benchmark_specified_family_gap_count"), default=999)

    gates = [
        pass_gate(
            "source_conditioned_holdout_depth",
            holdout_count >= 20,
            holdout_count,
            ">= 20 holdouts",
            "Prevents one-good-run storytelling.",
            "Supports current internal champion language.",
        ),
        pass_gate(
            "named_baseline_win_rate",
            holdout_count > 0 and wins_named == holdout_count,
            f"{wins_named}/{holdout_count}",
            "all current holdouts beat the named baseline",
            "Checks the champion against the explicit incumbent comparator.",
            "Supports buyer-authorized field replay request language.",
        ),
        pass_gate(
            "best_same_run_baseline_win_rate",
            holdout_count > 0 and wins_best == holdout_count,
            f"{wins_best}/{holdout_count}",
            "all current holdouts beat the best same-run baseline",
            "Prevents only beating a weak selected baseline.",
            "Supports stronger internal repeatability language.",
        ),
        pass_gate(
            "weakest_margin_positive",
            bool(deltas) and min(deltas) > 0,
            min_or_zero(deltas),
            "> 0.0",
            "Looks for any holdout where the claimed edge disappears.",
            "Supports no-loss internal holdout language.",
        ),
        pass_gate(
            "best_baseline_weakest_margin_positive",
            bool(best_deltas) and min(best_deltas) > 0,
            min_or_zero(best_deltas),
            "> 0.0",
            "Looks for any holdout where another same-run family beats the champion.",
            "Supports current champion rather than merely good-family language.",
        ),
        pass_gate(
            "source_system_diversity",
            len(source_systems) >= 4,
            len(source_systems),
            ">= 4 source systems",
            "Checks whether the evidence is only one data family.",
            "Supports multi-domain internal replay language.",
        ),
        pass_gate(
            "estimated_row_depth",
            estimated_rows >= 1_000_000,
            estimated_rows,
            ">= 1,000,000 estimated rows",
            "Separates toy data from broad replay surface.",
            "Supports broad measured-source replay language.",
        ),
        pass_gate(
            "numeric_sample_depth",
            numeric_samples >= 50_000,
            numeric_samples,
            ">= 50,000 numeric samples read",
            "Checks that the scoring used actual numeric evidence.",
            "Supports data-backed internal benchmark language.",
        ),
        pass_gate(
            "fallback_rate_low",
            fallback_rate <= 0.10,
            round(fallback_rate, 6),
            "<= 10% fallback-profile holdouts",
            "Keeps nonnumeric or missing-source fallbacks from dominating the result.",
            "Supports current artifact quality language.",
        ),
        pass_gate(
            "rank_1_share",
            rank_1_share >= 0.40,
            round(rank_1_share, 6),
            ">= 40% rank-1 holdouts",
            "Checks whether the family is repeatedly first, not barely positive.",
            "Supports champion but still acknowledges rank-2/rank-3 runs.",
        ),
        pass_gate(
            "stress_profile_coverage",
            stress_count >= 3,
            stress_count,
            ">= 3 stressed-profile holdouts",
            "Checks whether the champion was evaluated under noisy or high-variation profiles.",
            "Supports stress-tested internal replay language.",
        ),
        pass_gate(
            "trend_profile_coverage",
            trend_count >= 3,
            trend_count,
            ">= 3 nonflat-trend holdouts",
            "Checks whether the replay includes moving signals, not only static snapshots.",
            "Supports live-breadth style replay language.",
        ),
        pass_gate(
            "shock_profile_coverage",
            shock_count >= 3,
            shock_count,
            ">= 3 shock-bearing holdouts",
            "Checks whether sudden changes exist in the stress surface.",
            "Supports anomaly/drift evaluation language.",
        ),
        pass_gate(
            "hosted_hash_verification",
            bool(live_summary.get("live_domain_reviewer_ready")),
            live_summary.get("domain_deployment_state") or False,
            "LIVE_DOMAIN_HASH_VERIFIED",
            "Confirms reviewer-facing public feeds match local hashes.",
            "Supports public deployment verification language.",
        ),
        pass_gate(
            "all_registry_families_have_benchmark_specs",
            all_family_gap == 0,
            all_family_gap,
            "0 missing benchmark specs",
            "Checks the family registry is no longer an unscored idea list.",
            "Supports all-family registry coverage language, but not all-family superiority.",
        ),
        pass_gate(
            "statistical_repeat_gate",
            as_float(gauntlet_summary.get("one_sided_sign_test_p_value"), 1.0) <= 0.001,
            gauntlet_summary.get("one_sided_sign_test_p_value"),
            "<= 0.001",
            "Checks repeat significance across current holdouts.",
            "Supports strong internal repeatability language.",
        ),
        blocked_gate(
            "phase_slip_and_amplitude_error",
            "Needed to claim a phase-locking mechanism, not just benchmark outperformance.",
            "instrument or replay logs with phase-slip count and amplitude error",
        ),
        blocked_gate(
            "residual_autocorrelation_and_calibration",
            "Needed to know whether remaining errors are structured and exploitable.",
            "residual autocorrelation, calibration, and post-hoc leakage checks",
        ),
        blocked_gate(
            "latency_runtime_budget",
            "Needed for real-time operational claims.",
            "measured latency under the target deployment workload",
        ),
        blocked_gate(
            "buyer_authorized_field_replay",
            "Needed before any field-validation or realized-dollar language.",
            "external owner-approved holdout windows, baseline, metric, and cost conversion",
        ),
        blocked_gate(
            "all_family_live_benchmark_execution",
            "Needed before universal geometry-superiority claims.",
            "execute the full 140-family registry on live measured rows under one locked protocol",
        ),
    ]
    return gates


def rank_histogram(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(as_int(row.get("candidate_rank"), 999)) for row in rows)
    return dict(sorted(counts.items(), key=lambda item: int(item[0])))


def compact_holdouts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in rows:
        profile = as_dict(row.get("profile"))
        compact.append(
            {
                "source_system": row.get("source_system"),
                "source_path": row.get("source_path"),
                "source_sha256_prefix": str(row.get("source_sha256") or "")[:16],
                "candidate_rank": as_int(row.get("candidate_rank")),
                "candidate_score": as_float(row.get("candidate_score")),
                "kalman_score": as_float(row.get("kalman_score")),
                "delta_vs_named_baseline": as_float(row.get("delta_vs_kalman")),
                "delta_vs_best_same_run_baseline": as_float(row.get("delta_vs_best_baseline")),
                "estimated_rows": as_int(row.get("estimated_rows")),
                "numeric_samples": as_int(row.get("numeric_samples")),
                "stress_index": as_float(profile.get("stress_index")),
                "shock_index": as_float(profile.get("shock_index")),
                "trend_index": as_float(profile.get("trend_index")),
                "fallback_used": bool(profile.get("fallback_used")),
                "holdout_sha256": row.get("holdout_sha256"),
            }
        )
    return compact


def build_payload() -> dict[str, Any]:
    holdout_payload = read_json(HOLDOUT_JSON)
    gauntlet = read_json(GAUNTLET_JSON)
    geometry = read_json(GEOMETRY_JSON)
    revenue = read_json(REVENUE_JSON)
    live_domain = read_json(LIVE_DOMAIN_JSON)

    rows = [row for row in as_list(holdout_payload.get("holdout_results")) if isinstance(row, dict)]
    gauntlet_summary = as_dict(gauntlet.get("summary"))
    geometry_summary = as_dict(geometry.get("summary"))
    revenue_summary = as_dict(revenue.get("summary"))
    live_summary = as_dict(live_domain.get("summary"))
    live_domain_hash_verified = bool(live_summary.get("live_domain_reviewer_ready"))
    hosted_feed_phrase = (
        "public hash-verified feeds"
        if live_domain_hash_verified
        else "locally hashable feeds staged for public hash verification"
    )
    evidence_stage = (
        "internal_source_conditioned_replay_public_hash_verified_not_field_validated"
        if live_domain_hash_verified
        else "internal_source_conditioned_replay_public_hash_pending_not_field_validated"
    )

    deltas = [as_float(row.get("delta_vs_kalman")) for row in rows]
    best_deltas = [as_float(row.get("delta_vs_best_baseline")) for row in rows]
    holdout_count = len(rows)
    wins_named = sum(bool(row.get("candidate_beats_kalman")) for row in rows)
    wins_best = sum(bool(row.get("candidate_beats_best_baseline")) for row in rows)
    estimated_rows = sum(as_int(row.get("estimated_rows")) for row in rows)
    numeric_samples = sum(as_int(row.get("numeric_samples")) for row in rows)
    source_systems = sorted({str(row.get("source_system") or "unknown") for row in rows})
    profiles = [as_dict(row.get("profile")) for row in rows]
    fallback_count = sum(bool(profile.get("fallback_used")) for profile in profiles)
    gates = metric_matrix(rows, gauntlet_summary, geometry_summary, live_summary)
    passed_gates = [gate for gate in gates if gate["passed"]]
    blocked_gates = [gate for gate in gates if gate["blocker"] and not gate["passed"]]

    payload: dict[str, Any] = {
        "generated_utc": now_utc(),
        "schema": "champion_stress_test_matrix_v1",
        "purpose": "Create a compact, hosted, reviewer-safe stress matrix for the current champion.",
        "boundary": BOUNDARY,
        "summary": {
            "champion_family": gauntlet_summary.get("champion_family") or "kuramoto_phase_coupling",
            "champion_label": gauntlet_summary.get("champion_label") or "Kuramoto phase coupling",
            "named_baseline": gauntlet_summary.get("named_baseline") or "kalman_filter",
            "evidence_stage": evidence_stage,
            "revenue_stage": revenue_summary.get("revenue_stage") or "manual_paid_pilot_scoping_ready",
            "holdout_count": holdout_count,
            "wins_vs_named_baseline": wins_named,
            "wins_vs_best_same_run_baseline": wins_best,
            "win_rate_vs_named_baseline": round(wins_named / holdout_count, 6) if holdout_count else 0.0,
            "source_system_count": len(source_systems),
            "source_systems": source_systems,
            "estimated_rows_replayed": estimated_rows,
            "numeric_samples_read": numeric_samples,
            "fallback_count": fallback_count,
            "fallback_rate": round(fallback_count / holdout_count, 6) if holdout_count else 1.0,
            "min_delta_vs_named_baseline": min_or_zero(deltas),
            "mean_delta_vs_named_baseline": mean(deltas),
            "max_delta_vs_named_baseline": max_or_zero(deltas),
            "min_delta_vs_best_same_run_baseline": min_or_zero(best_deltas),
            "mean_delta_vs_best_same_run_baseline": mean(best_deltas),
            "max_delta_vs_best_same_run_baseline": max_or_zero(best_deltas),
            "rank_histogram": rank_histogram(rows),
            "live_domain_hash_verified": live_domain_hash_verified,
            "domain_deployment_state": live_summary.get("domain_deployment_state"),
            "metric_gate_pass_count": len(passed_gates),
            "metric_gate_total_count": len(gates),
            "blocked_gate_count": len(blocked_gates),
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_frozen_delta_price_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "manual_paid_pilot_outreach_allowed": bool(revenue_summary.get("manual_reviewed_outreach_allowed")),
            "plain_english_answer": (
                "This is the current money-printer truth line: Kuramoto phase coupling is a strong internal "
                f"champion, with {wins_named}/{holdout_count} source-conditioned holdout wins against "
                f"{gauntlet_summary.get('named_baseline') or 'kalman_filter'} across {len(source_systems)} "
                f"source systems and {hosted_feed_phrase}. The next monetizable step is a paid, "
                "buyer-authorized field replay, not an unverified realized-savings claim."
            ),
        },
        "claim_controls": {
            "allowed_now": [
                "current internal champion",
                "source-conditioned holdout winner",
                (
                    "public hash-verified reviewer feed"
                    if live_domain_hash_verified
                    else "local hashable reviewer feed staged for domain verification"
                ),
                "manual paid-pilot scoping candidate",
                "buyer-authorized field replay request ready",
            ],
            "not_allowed_yet": [
                "field validated",
                "realized dollar savings",
                "fixed dollar value per frozen delta",
                "guaranteed grant award",
                "live trading edge or autonomous execution",
                "universal geometry superiority",
            ],
        },
        "source_system_matrix": source_matrix(rows),
        "metric_stress_tests": gates,
        "holdout_compact": compact_holdouts(rows),
        "source_artifacts": {
            "holdout_expansion": str(HOLDOUT_JSON.relative_to(ROOT)),
            "champion_metric_gauntlet": str(GAUNTLET_JSON.relative_to(ROOT)),
            "geometry_champion_of_champions": str(GEOMETRY_JSON.relative_to(ROOT)),
            "proof_to_revenue_engine": str(REVENUE_JSON.relative_to(ROOT)),
            "live_domain_deployment_feed": str(LIVE_DOMAIN_JSON.relative_to(ROOT)),
        },
        "reviewer_urls": as_dict(live_domain.get("reviewer_urls")),
        "what_to_ask_next": [
            "Which buyer-controlled dataset can we replay under a locked incumbent baseline?",
            "What operational cost factor converts metric improvement into dollars?",
            "What pass/fail threshold would make a paid pilot worth expanding?",
            "Which latency and residual tests must pass for production use?",
            "Which narrow sector should receive the first manual paid-pilot outreach?",
        ],
    }
    payload["stress_matrix_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "source_system_matrix": payload["source_system_matrix"],
            "metric_stress_tests": payload["metric_stress_tests"],
            "holdout_compact": payload["holdout_compact"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = as_dict(payload.get("summary"))
    lines = [
        "# Champion Stress Test Matrix",
        "",
        f"Generated UTC: `{payload.get('generated_utc')}`",
        f"Matrix SHA-256: `{payload.get('stress_matrix_sha256')}`",
        "",
        "## Truth Line",
        "",
        str(summary.get("plain_english_answer") or ""),
        "",
        "## Current Champion",
        "",
        f"- Champion: `{summary.get('champion_family')}`",
        f"- Named baseline: `{summary.get('named_baseline')}`",
        f"- Holdout wins: `{summary.get('wins_vs_named_baseline')}/{summary.get('holdout_count')}`",
        f"- Wins vs best same-run baseline: `{summary.get('wins_vs_best_same_run_baseline')}/{summary.get('holdout_count')}`",
        f"- Source systems: `{summary.get('source_system_count')}`",
        f"- Estimated rows replayed: `{summary.get('estimated_rows_replayed')}`",
        f"- Numeric samples read: `{summary.get('numeric_samples_read')}`",
        f"- Mean delta vs named baseline: `{summary.get('mean_delta_vs_named_baseline')}`",
        f"- Weakest delta vs named baseline: `{summary.get('min_delta_vs_named_baseline')}`",
        f"- Live-domain hash verified: `{str(summary.get('live_domain_hash_verified')).lower()}`",
        "",
        "## Claim Boundary",
        "",
        "Allowed now:",
    ]
    for item in as_list(as_dict(payload.get("claim_controls")).get("allowed_now")):
        lines.append(f"- {item}")
    lines.extend(["", "Not allowed yet:"])
    for item in as_list(as_dict(payload.get("claim_controls")).get("not_allowed_yet")):
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Source System Matrix",
            "",
            "| Source | Holdouts | Rows | Numeric Samples | Wins | Mean Delta | Fallbacks |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in as_list(payload.get("source_system_matrix")):
        source = as_dict(row)
        lines.append(
            "| "
            f"`{source.get('source_system')}` | "
            f"{source.get('holdout_count')} | "
            f"{source.get('estimated_rows')} | "
            f"{source.get('numeric_samples')} | "
            f"{source.get('wins_vs_named_baseline')} | "
            f"{source.get('mean_delta_vs_named_baseline')} | "
            f"{source.get('fallback_count')} |"
        )

    lines.extend(
        [
            "",
            "## Metric Battery",
            "",
            "| Test | Status | Actual | Threshold |",
            "|---|---|---:|---|",
        ]
    )
    for gate in as_list(payload.get("metric_stress_tests")):
        row = as_dict(gate)
        lines.append(
            "| "
            f"`{row.get('name')}` | "
            f"`{row.get('status')}` | "
            f"`{row.get('actual')}` | "
            f"{row.get('threshold')} |"
        )

    lines.extend(
        [
            "",
            "## What This Unlocks",
            "",
            "- A clean paid-pilot conversation: we can show the hosted hash table, the champion matrix, and the blocked field-validation gates in one pass.",
            "- A disciplined dollar path: dollars come only after a buyer locks the dataset, baseline, acceptance metric, and cost conversion.",
            "- A stronger grant/supporting-data story: the proposal can say the proof stack is public, reproducible, and explicitly bounded.",
            "",
            "## What To Ask Next",
            "",
        ]
    )
    for item in as_list(payload.get("what_to_ask_next")):
        lines.append(f"- {item}")
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"Champion stress matrix gates: {payload['summary']['metric_gate_pass_count']}/{payload['summary']['metric_gate_total_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
