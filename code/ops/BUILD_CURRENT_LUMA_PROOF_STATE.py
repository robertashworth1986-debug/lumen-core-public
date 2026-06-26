from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

REGISTRY_JSON = CONFIG / "geometry_championship_v1_registry.json"
READY_REPLAY_JSON = OUT_OPS / "geometry_ready_source_replay_latest.json"
SOURCE_MANIFEST_JSON = OUT_OPS / "geometry_live_source_manifest_latest.json"
REPEAT_VALIDATION_JSON = OUT_OPS / "geometry_repeat_proof_validation_latest.json"
UNCERTAINTY_JSON = OUT_OPS / "geometry_repeat_uncertainty_report_latest.json"
VALUATION_JSON = OUT_OPS / "valuation_proposal_target_packet_latest.json"
CLAIM_MAP_JSON = OUT_OPS / "claim_strength_value_unlock_map_latest.json"
FIELD_MONEY_JSON = OUT_OPS / "field_money_truth_sweep_latest.json"

OUT_JSON = OUT_OPS / "current_luma_proof_state_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "current_luma_proof_state.json"
OUT_MD = DOCS / "CURRENT_LUMA_PROOF_STATE_2026-06-26.md"

BOUNDARY = (
    "Current proof-state checkpoint generated from authoritative local artifacts. It ranks the strongest geometry "
    "candidates and proposal targets, but it does not grant field-validation, realized-savings, fixed-dollar "
    "frozen-delta, clinical, live-trading, or award-certainty claims."
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


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def pct(value: Any) -> str:
    return f"{safe_float(value) * 100:.1f}%"


def money(value: Any) -> str:
    return f"${safe_float(value):,.0f}"


def registry_summary(registry: dict[str, Any]) -> dict[str, Any]:
    families = [row for row in as_list(registry.get("families")) if isinstance(row, dict)]
    lanes = registry.get("lanes", {}) if isinstance(registry.get("lanes"), dict) else {}
    benchmark_specified = [
        row
        for row in families
        if row.get("benchmark_hypothesis") and row.get("promotion_metric") and row.get("failure_mode")
    ]
    natural_paths = [row for row in families if str(row.get("natural_logic", "")).strip()]
    return {
        "family_count": len(families),
        "lane_count": len(lanes),
        "benchmark_specified_family_count": len(benchmark_specified),
        "natural_path_family_count": len(natural_paths),
        "natural_path_target_met": len(natural_paths) >= 50,
        "core_rule": registry.get("core_rule", ""),
        "evidence_boundary": registry.get("evidence_boundary", ""),
    }


def family_index(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("id", "")): row
        for row in as_list(registry.get("families"))
        if isinstance(row, dict) and row.get("id")
    }


def uncertainty_index(uncertainty: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("family_id", "")): row
        for row in as_list(uncertainty.get("analyses"))
        if isinstance(row, dict) and row.get("family_id")
    }


def repeat_candidates(
    repeat: dict[str, Any],
    uncertainty: dict[str, dict[str, Any]],
    families: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in as_list(repeat.get("validations")):
        if not isinstance(row, dict):
            continue
        family_id = str(row.get("family_id", ""))
        if not family_id:
            continue
        u = uncertainty.get(family_id, {})
        deltas = [
            safe_float(item.get("candidate_score_delta_vs_named_baseline"))
            for item in as_list(row.get("window_results"))
            if isinstance(item, dict) and item.get("candidate_score_delta_vs_named_baseline") is not None
        ]
        mean_delta = safe_float(u.get("delta_stats", {}).get("mean_delta")) if isinstance(u.get("delta_stats"), dict) else 0.0
        if mean_delta == 0.0 and deltas:
            mean_delta = mean(deltas)
        robust = bool(u.get("robust_repeat_uncertainty_gate_passed"))
        repeat_passed = bool(row.get("repeat_candidate_gate_passed"))
        evidence_stage = (
            "robust_repeat_champion_not_field_validated"
            if robust
            else "repeat_candidate_needs_more_holdouts"
            if repeat_passed
            else "repeat_replay_observed_not_promoted"
        )
        score = 82.0
        score += 18.0 if robust else 0.0
        score += min(safe_int(row.get("repeat_live_win_count")) * 2.2, 18.0)
        score += min(safe_int(row.get("distinct_win_hash_count")) * 1.4, 12.0)
        score += min(abs(mean_delta) * 90.0, 18.0)
        score -= 12.0 if not repeat_passed else 0.0
        rows[family_id] = {
            "family_id": family_id,
            "label": families.get(family_id, {}).get("label", family_id),
            "lane": row.get("lane", ""),
            "named_baseline": row.get("named_baseline", ""),
            "evidence_stage": evidence_stage,
            "proof_score": round(score, 3),
            "repeat_live_win_count": safe_int(row.get("repeat_live_win_count")),
            "window_count": safe_int(row.get("available_window_count")),
            "distinct_win_hash_count": safe_int(row.get("distinct_win_hash_count")),
            "min_source_count": safe_int(row.get("min_source_count")),
            "mean_delta_vs_named_baseline": round(mean_delta, 6),
            "lower_95_delta": (
                round(safe_float(u.get("delta_stats", {}).get("normal_t_lower_95_delta")), 6)
                if isinstance(u.get("delta_stats"), dict)
                else None
            ),
            "sign_test_p_value": u.get("one_sided_sign_test_p_value"),
            "wilson_lower_95_win_rate": u.get("wilson_lower_95_win_rate"),
            "source_names": row.get("source_names", []),
            "claim_boundary": row.get("claim_boundary", ""),
        }
    return rows


def ready_source_candidates(
    ready: dict[str, Any],
    families: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in as_list(ready.get("lane_scoreboard")):
        if not isinstance(row, dict):
            continue
        family_id = str(row.get("candidate_family", ""))
        if not family_id:
            continue
        replay_count = safe_int(row.get("replay_count"))
        wins = safe_int(row.get("candidate_win_count"))
        mean_delta = safe_float(row.get("mean_delta_vs_named_baseline"))
        win_rate = wins / replay_count if replay_count else 0.0
        if replay_count >= 3 and win_rate >= 1.0:
            stage = "source_conditioned_multi_replay_winner_not_field_validated"
            base = 76.0
        elif wins > 0:
            stage = "source_conditioned_candidate_needs_repeat"
            base = 62.0
        else:
            stage = "negative_source_conditioned_replay_demote"
            base = 22.0
        score = base + min(win_rate * 12.0, 12.0) + min(max(mean_delta, 0.0) * 120.0, 24.0)
        score += min(math.log10(max(safe_int(row.get("estimated_rows")), 1)) * 2.0, 14.0)
        rows[family_id] = {
            "family_id": family_id,
            "label": families.get(family_id, {}).get("label", family_id),
            "lane": row.get("lane", ""),
            "named_baseline": row.get("baseline_family", ""),
            "evidence_stage": stage,
            "proof_score": round(score, 3),
            "source_conditioned_replays": replay_count,
            "source_conditioned_wins": wins,
            "source_conditioned_win_rate": round(win_rate, 6),
            "estimated_rows": safe_int(row.get("estimated_rows")),
            "numeric_samples": safe_int(row.get("numeric_samples")),
            "mean_delta_vs_named_baseline": round(mean_delta, 6),
            "best_delta_vs_named_baseline": row.get("best_delta_vs_named_baseline"),
        }
    return rows


def merge_candidates(
    repeat_rows: dict[str, dict[str, Any]],
    ready_rows: dict[str, dict[str, Any]],
    families: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    merged_ids = set(repeat_rows) | set(ready_rows)
    merged: list[dict[str, Any]] = []
    for family_id in merged_ids:
        repeat = repeat_rows.get(family_id, {})
        ready = ready_rows.get(family_id, {})
        family = families.get(family_id, {})
        proof_score = max(safe_float(repeat.get("proof_score")), safe_float(ready.get("proof_score")))
        if repeat and ready:
            proof_score += 8.0
        stages = [str(item.get("evidence_stage", "")) for item in (repeat, ready) if item]
        if any(stage.startswith("robust_repeat") for stage in stages):
            stage = "robust_repeat_plus_current_replay" if ready else "robust_repeat_champion_not_field_validated"
        elif any("negative" in stage for stage in stages):
            stage = "negative_current_replay_demote"
        elif any(stage.startswith("source_conditioned_multi") for stage in stages):
            stage = "source_conditioned_multi_replay_winner_not_field_validated"
        elif any(stage.startswith("source_conditioned_candidate") for stage in stages):
            stage = "source_conditioned_candidate_needs_repeat"
        else:
            stage = stages[0] if stages else "registry_only"
        merged.append(
            {
                "family_id": family_id,
                "label": family.get("label", family_id),
                "lane": repeat.get("lane") or ready.get("lane") or family.get("lane", ""),
                "evidence_stage": stage,
                "proof_score": round(proof_score, 3),
                "repeat_evidence": repeat,
                "source_conditioned_evidence": ready,
                "safe_claim": safe_claim(stage, repeat or ready),
                "next_move": next_move(stage, repeat or ready),
            }
        )
    merged.sort(key=lambda row: (-safe_float(row.get("proof_score")), row.get("family_id", "")))
    for rank, row in enumerate(merged, start=1):
        row["rank"] = rank
    return merged


def safe_claim(stage: str, evidence: dict[str, Any]) -> str:
    family = evidence.get("family_id", "candidate")
    lane = evidence.get("lane", "lane")
    if stage.startswith("robust_repeat"):
        return (
            f"{family} is a robust repeat-window benchmark candidate on {lane}; this supports paid technical "
            "evaluation scoping, not field validation or realized savings."
        )
    if stage.startswith("source_conditioned_multi"):
        return (
            f"{family} is the strongest current source-conditioned replay candidate on {lane}; it needs more "
            "holdout windows, buyer-authorized baselines, and field validation before dollar claims."
        )
    if "negative" in stage:
        return f"{family} lost or tied in the current source-conditioned replay and should be rerouted or demoted."
    return f"{family} remains a research candidate until it wins frozen replays against named baselines."


def next_move(stage: str, evidence: dict[str, Any]) -> str:
    if stage.startswith("robust_repeat"):
        return "Package as a bounded appendix and ask for buyer-authorized holdout replay."
    if stage.startswith("source_conditioned_multi"):
        return "Run at least 20 pre-registered holdout windows and add accepted incumbent baselines."
    if "negative" in stage:
        return "Do not pitch this as a winner; use it as negative evidence and test alternate branching families."
    return "Wire to an adapter or leave as registry-only."


def top_next_actions(payload: dict[str, Any]) -> list[str]:
    best = payload["champion_rankings"][0] if payload["champion_rankings"] else {}
    return [
        f"Lead with {best.get('family_id', 'the top candidate')} only in bounded benchmark language.",
        "Run Kuramoto phase-coupling on at least 20 more EIA/FRED/NOAA/NASA holdout windows.",
        "Pull ISO/RTO LMP or accepted electricity-price settlement data before any real-dollar energy claim.",
        "Move leaf-vein branching out of winner language until it beats minimum-spanning-tree on fresh source-conditioned routes.",
        "Attach the current proof-state JSON hash to grant and buyer packets so reviewers can reproduce the evidence boundary.",
    ]


def build_payload() -> dict[str, Any]:
    registry = read_json(REGISTRY_JSON)
    ready = read_json(READY_REPLAY_JSON)
    manifest = read_json(SOURCE_MANIFEST_JSON)
    repeat = read_json(REPEAT_VALIDATION_JSON)
    uncertainty = read_json(UNCERTAINTY_JSON)
    valuation = read_json(VALUATION_JSON)
    claim_map = read_json(CLAIM_MAP_JSON)
    field_money = read_json(FIELD_MONEY_JSON)

    families = family_index(registry)
    repeat_rows = repeat_candidates(repeat, uncertainty_index(uncertainty), families)
    ready_rows = ready_source_candidates(ready, families)
    champion_rankings = merge_candidates(repeat_rows, ready_rows, families)

    ready_summary = ready.get("summary", {}) if isinstance(ready.get("summary"), dict) else {}
    manifest_summary = manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {}
    valuation_state = valuation.get("valuation_state", {}) if isinstance(valuation.get("valuation_state"), dict) else {}
    claim_summary = claim_map.get("summary", {}) if isinstance(claim_map.get("summary"), dict) else {}
    field_summary = field_money.get("summary", {}) if isinstance(field_money.get("summary"), dict) else {}

    gates = {
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "paid_technical_evaluation_scoping_allowed": True,
        "all_registered_families_live_benchmarked": False,
        "natural_path_registry_target_met": registry_summary(registry)["natural_path_target_met"],
    }

    payload = {
        "schema": "current_luma_proof_state.v1",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "registry": registry_summary(registry),
        "ready_source_replay": {
            "routes": ready_summary.get("routes_replayed", 0),
            "candidate_wins": ready_summary.get("candidate_win_count", 0),
            "candidate_losses_or_ties": ready_summary.get("candidate_loss_or_tie_count", 0),
            "estimated_rows_replayed": ready_summary.get("estimated_rows_replayed", 0),
            "numeric_samples_read": ready_summary.get("numeric_samples_read", 0),
            "mean_delta_vs_named_baseline": ready_summary.get("mean_delta_vs_named_baseline", 0.0),
            "strongest_positive_family": ready_summary.get("strongest_positive_family", ""),
            "strongest_positive_lane": ready_summary.get("strongest_positive_lane", ""),
            "strongest_positive_delta": ready_summary.get("strongest_positive_delta", 0.0),
            "replay_chain_sha256": ready_summary.get("replay_chain_sha256", ""),
        },
        "manifest": {
            "ready_for_benchmark_routes": manifest_summary.get("ready_for_benchmark_row_count", 0),
            "unique_source_count": manifest_summary.get("unique_source_count", 0),
            "unique_source_estimated_rows": manifest_summary.get("unique_source_estimated_rows", 0),
            "manifest_sha256": manifest_summary.get("manifest_sha256", ""),
        },
        "repeat_validation": repeat.get("summary", {}),
        "uncertainty": uncertainty.get("summary", {}),
        "valuation": {
            "strongest_current_claim": claim_summary.get("strongest_current_claim", ""),
            "safe_estimated_hourly_value_usd": claim_summary.get(
                "safe_estimated_hourly_value_usd", field_summary.get("safe_estimated_hourly_value_usd", 0)
            ),
            "safe_estimated_annual_value_usd": claim_summary.get(
                "safe_estimated_annual_value_usd", field_summary.get("safe_estimated_annual_value_usd", 0)
            ),
            "blocked_context_annual_value_usd": claim_summary.get(
                "blocked_context_annual_value_usd", field_summary.get("blocked_context_annual_value_usd", 0)
            ),
            "current_priceable_offer": valuation_state.get("current_priceable_offer", {}),
        },
        "proposal_target": valuation.get("recommended_first_proposal_target", {}),
        "champion_rankings": champion_rankings,
        "gates": gates,
        "next_actions": [],
        "inputs": {
            "registry": str(REGISTRY_JSON.relative_to(ROOT)),
            "ready_source_replay": str(READY_REPLAY_JSON.relative_to(ROOT)),
            "source_manifest": str(SOURCE_MANIFEST_JSON.relative_to(ROOT)),
            "repeat_validation": str(REPEAT_VALIDATION_JSON.relative_to(ROOT)),
            "uncertainty": str(UNCERTAINTY_JSON.relative_to(ROOT)),
            "valuation": str(VALUATION_JSON.relative_to(ROOT)),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
    }
    payload["next_actions"] = top_next_actions(payload)
    payload["proof_state_sha256"] = stable_sha256(
        {
            "registry": payload["registry"],
            "ready_source_replay": payload["ready_source_replay"],
            "manifest": payload["manifest"],
            "repeat_validation": payload["repeat_validation"],
            "uncertainty": payload["uncertainty"],
            "valuation": payload["valuation"],
            "proposal_target": payload["proposal_target"],
            "champion_rankings": payload["champion_rankings"],
            "gates": payload["gates"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    registry = payload["registry"]
    ready = payload["ready_source_replay"]
    manifest = payload["manifest"]
    valuation = payload["valuation"]
    gates = payload["gates"]
    lines = [
        "# Current Luma Proof State",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["boundary"],
        "",
        "## Hard Numbers",
        "",
        f"- Registered geometry families: `{registry['family_count']}`",
        f"- Natural-path families: `{registry['natural_path_family_count']}`",
        f"- Benchmark-specified families: `{registry['benchmark_specified_family_count']}`",
        f"- Ready-for-benchmark manifest routes: `{manifest['ready_for_benchmark_routes']}`",
        f"- Unique source files in manifest: `{manifest['unique_source_count']}`",
        f"- Manifest estimated rows: `{manifest['unique_source_estimated_rows']}`",
        f"- Current source-conditioned replay routes: `{ready['routes']}`",
        f"- Current source-conditioned wins/losses: `{ready['candidate_wins']}` / `{ready['candidate_losses_or_ties']}`",
        f"- Current replay estimated rows: `{ready['estimated_rows_replayed']}`",
        f"- Numeric samples read: `{ready['numeric_samples_read']}`",
        f"- Mean replay delta vs named baselines: `{ready['mean_delta_vs_named_baseline']}`",
        f"- Strongest current delta: `{ready['strongest_positive_delta']}` from `{ready['strongest_positive_family']}`",
        "",
        "## Champion Ranking",
        "",
        "| Rank | Family | Lane | Stage | Score | Main Claim |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for row in payload["champion_rankings"][:8]:
        lines.append(
            f"| {row['rank']} | `{row['family_id']}` | `{row['lane']}` | `{row['evidence_stage']}` | "
            f"{row['proof_score']} | {row['safe_claim']} |"
        )
    lines.extend(
        [
            "",
            "## Money State",
            "",
            f"- Strongest current commercial claim: `{valuation['strongest_current_claim']}`",
            f"- Safe estimated hourly value signal: `{money(valuation['safe_estimated_hourly_value_usd'])}`",
            f"- Safe estimated annual value signal: `{money(valuation['safe_estimated_annual_value_usd'])}`",
            f"- Blocked context annual surface: `{money(valuation['blocked_context_annual_value_usd'])}`",
            "- The blocked context surface is not a realized savings claim.",
            "",
            "## First Proposal Target",
            "",
        ]
    )
    target = payload["proposal_target"]
    if target:
        lines.extend(
            [
                f"- Target: {target.get('target_name', '')}",
                f"- Buyer role: {target.get('buyer_role', '')}",
                f"- Ask: {target.get('proposal_ask', '')}",
                f"- Acceptance metric: {target.get('acceptance_metric', '')}",
            ]
        )
    else:
        lines.append("- No proposal target generated yet.")
    lines.extend(["", "## Claim Gates", ""])
    for key, value in gates.items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend(["", "## Next Actions", ""])
    for item in payload["next_actions"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Inputs",
            "",
        ]
    )
    for label, path in payload["inputs"].items():
        lines.append(f"- {label}: `{path}`")
    lines.append(f"- Proof-state SHA-256: `{payload['proof_state_sha256']}`")
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"Proof state SHA256: {payload['proof_state_sha256']}")


if __name__ == "__main__":
    main()
