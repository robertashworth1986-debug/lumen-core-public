from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

TOP_REPLAY_JSON = OUT_OPS / "top_geometry_live_replay_results_latest.json"
MATRIX_JSON = OUT_OPS / "geometry_live_wiring_matrix_latest.json"
LEGACY_MANIFEST_JSON = OUT_OPS / "geometry_live_source_manifest_latest.json"

OUT_JSON = OUT_OPS / "geometry_ready_source_replay_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_ready_source_replay.json"
OUT_MD = DOCS / "GEOMETRY_READY_SOURCE_REPLAY_2026-06-26.md"

EVIDENCE_BOUNDARY = (
    "This artifact is the compatibility-gated replay register for top geometry "
    "cards. Direct measured replay is allowed only when the source schema, task, "
    "chronology, outcome, and source-specific baseline set satisfy geometry "
    "source-task compatibility v3. Source-conditioned synthetic stress is listed "
    "separately and cannot establish source performance. Context-only sources and "
    "the legacy generic ready-for-benchmark manifest are excluded from performance "
    "counts. This is not field validation, realized savings, a fixed-dollar claim, "
    "medical evidence, award certainty, or live execution permission."
)

FORBIDDEN_CLAIM_TERMS = (
    "guaranteed award",
    "guaranteed profit",
    "live_order_placement",
    "heroin-like",
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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


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


def compact_result(card: dict[str, Any], rank: int) -> dict[str, Any]:
    gauntlet = (
        card.get("baseline_gauntlet", {})
        if isinstance(card.get("baseline_gauntlet"), dict)
        else {}
    )
    inference = (
        card.get("paired_inference", {})
        if isinstance(card.get("paired_inference"), dict)
        else {}
    )
    evidence_mode = str(card.get("evidence_mode", ""))
    direct_sources = sorted(
        {str(value) for value in card.get("direct_replay_source_names", [])}
    )
    conditioned_sources = sorted(
        {
            str(value)
            for value in card.get("conditioned_stress_source_names", [])
        }
    )
    excluded_context = sorted(
        {
            str(value)
            for value in card.get("excluded_context_source_names", [])
        }
    )
    comparisons = [
        {
            "baseline_family_id": row.get("baseline_family_id", ""),
            "candidate_score_delta": row.get("candidate_score_delta"),
            "candidate_beats_baseline_mean": bool(
                row.get("candidate_beats_baseline_mean")
            ),
            "statistically_positive_after_global_holm": bool(
                row.get("statistically_positive_after_global_holm")
            ),
            "paired_unit_count": safe_int(
                (
                    row.get("paired_inference", {})
                    if isinstance(row.get("paired_inference"), dict)
                    else {}
                ).get("paired_unit_count")
            ),
        }
        for row in card.get("baseline_comparisons", [])
        if isinstance(row, dict)
    ]
    result = {
        "rank": rank,
        "lane": card.get("lane", ""),
        "registered_candidate_family": card.get("candidate_family_id", ""),
        "candidate_family": card.get(
            "evaluated_candidate_family_id",
            card.get("candidate_family_id", ""),
        ),
        "candidate_resolution": card.get("candidate_resolution", ""),
        "baseline_family": card.get("named_baseline", ""),
        "best_baseline_family": card.get("best_baseline_family_id", ""),
        "adapter_status": card.get("adapter_status", ""),
        "evidence_mode": evidence_mode,
        "compatibility_contract_version": (
            "geometry_source_task_compatibility_v3"
        ),
        "direct_replay_sources": direct_sources,
        "conditioned_stress_sources": conditioned_sources,
        "excluded_context_sources": excluded_context,
        "snapshot_sha256s": sorted(
            set(card.get("direct_replay_snapshot_sha256s", []))
            | set(card.get("conditioned_stress_snapshot_sha256s", []))
        ),
        "performance_rows_evaluated": safe_int(
            card.get("performance_rows_evaluated")
        ),
        "paired_unit_count": safe_int(inference.get("paired_unit_count")),
        "candidate_delta_vs_named_baseline": card.get(
            "candidate_score_delta_vs_named_baseline"
        ),
        "candidate_beats_named_baseline": bool(
            card.get("candidate_beats_named_baseline")
        ),
        "registered_baseline_count": safe_int(
            gauntlet.get("registered_baseline_count")
        ),
        "registered_baseline_mean_win_count": safe_int(
            gauntlet.get("mean_score_win_count")
        ),
        "registered_baseline_global_holm_positive_count": safe_int(
            gauntlet.get("global_holm_positive_count")
        ),
        "candidate_beats_all_registered_baselines_mean": bool(
            gauntlet.get("candidate_beats_all_registered_baselines_mean")
        ),
        "candidate_beats_all_registered_baselines_after_global_holm": bool(
            gauntlet.get(
                "candidate_beats_all_registered_baselines_after_global_holm"
            )
        ),
        "baseline_comparisons": comparisons,
        "broad_source_performance_claim_allowed": False,
        "claim_gates": {
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "medical_or_addiction_treatment_claim_allowed": False,
        },
    }
    result["route_sha256"] = stable_sha256(
        {key: value for key, value in result.items() if key != "route_sha256"}
    )
    return result


def lane_scoreboard(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scoreboard: list[dict[str, Any]] = []
    for result in results:
        deltas = [
            safe_float(row.get("candidate_score_delta"))
            for row in result.get("baseline_comparisons", [])
        ]
        deltas = [value for value in deltas if value is not None]
        scoreboard.append(
            {
                "lane": result["lane"],
                "candidate_family": result["candidate_family"],
                "registered_candidate_family": result[
                    "registered_candidate_family"
                ],
                "baseline_family": result["baseline_family"],
                "evidence_mode": result["evidence_mode"],
                "replay_count": int(
                    str(result["adapter_status"]).endswith("_ran")
                ),
                "candidate_win_count": result[
                    "registered_baseline_mean_win_count"
                ],
                "global_holm_positive_count": result[
                    "registered_baseline_global_holm_positive_count"
                ],
                "baseline_comparison_count": result[
                    "registered_baseline_count"
                ],
                "performance_rows": result["performance_rows_evaluated"],
                "source_names": sorted(
                    set(result["direct_replay_sources"])
                    | set(result["conditioned_stress_sources"])
                ),
                "mean_delta_vs_named_baseline": (
                    round(mean(deltas), 6) if deltas else None
                ),
                "best_delta_vs_named_baseline": (
                    round(max(deltas), 6) if deltas else None
                ),
            }
        )
    return sorted(scoreboard, key=lambda row: row["lane"])


def build_payload(
    *,
    max_routes: int | None = None,
    sample_limit: int | None = None,
) -> dict[str, Any]:
    # Legacy truncation knobs are intentionally ignored. The v3 compatibility
    # matrix decides eligibility; row-count sampling cannot create eligibility.
    _ = max_routes, sample_limit

    top_replay = read_json(TOP_REPLAY_JSON)
    matrix = read_json(MATRIX_JSON)
    legacy_manifest = read_json(LEGACY_MANIFEST_JSON)
    if top_replay.get("schema") != "top_geometry_live_replay_results_v2":
        raise ValueError("top geometry live replay v2 is required")
    if matrix.get("schema") != "geometry_live_wiring_matrix_v3":
        raise ValueError("geometry live wiring matrix v3 is required")

    cards = [
        dict(card)
        for card in top_replay.get("replay_cards", [])
        if isinstance(card, dict)
    ]
    results = [
        compact_result(card, rank)
        for rank, card in enumerate(cards, start=1)
    ]
    scoreboard = lane_scoreboard(results)
    direct = [
        row for row in results if row["evidence_mode"] == "direct_measured_replay"
    ]
    conditioned = [
        row
        for row in results
        if row["evidence_mode"] == "source_conditioned_synthetic_stress"
    ]
    unavailable = [
        row
        for row in results
        if row["evidence_mode"] == "no_compatible_replay_input"
    ]
    direct_all_baseline = [
        row
        for row in direct
        if row[
            "candidate_beats_all_registered_baselines_after_global_holm"
        ]
    ]
    conditioned_named_wins = [
        row for row in conditioned if row["candidate_beats_named_baseline"]
    ]
    source_hashes = {
        value
        for row in results
        for value in row.get("snapshot_sha256s", [])
        if value
    }
    legacy_ready_rows = [
        row
        for row in legacy_manifest.get("manifest_rows", [])
        if isinstance(row, dict) and row.get("ready_for_benchmark")
    ]

    summary = {
        "cards_reviewed": len(results),
        "routes_replayed": sum(
            str(row["adapter_status"]).endswith("_ran") for row in results
        ),
        "lanes_replayed": len(
            {
                row["lane"]
                for row in results
                if str(row["adapter_status"]).endswith("_ran")
            }
        ),
        "source_files_replayed": len(source_hashes),
        "estimated_rows_replayed": sum(
            row["performance_rows_evaluated"] for row in results
        ),
        "numeric_samples_read": sum(
            row["performance_rows_evaluated"] for row in results
        ),
        "performance_rows_reviewed": sum(
            row["performance_rows_evaluated"] for row in results
        ),
        "direct_measured_replay_count": len(direct),
        "source_conditioned_synthetic_stress_count": len(conditioned),
        "no_compatible_replay_input_count": len(unavailable),
        "candidate_win_count": len(direct_all_baseline),
        "candidate_loss_or_tie_count": len(direct) - len(direct_all_baseline),
        "source_conditioned_named_baseline_mean_win_count": len(
            conditioned_named_wins
        ),
        "direct_all_baseline_global_holm_positive_count": len(
            direct_all_baseline
        ),
        "legacy_ready_for_benchmark_rows_excluded": len(legacy_ready_rows),
        "numeric_fallback_profile_count": 0,
        "broad_source_performance_claim_allowed": False,
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "medical_or_addiction_treatment_claim_allowed": False,
    }
    payload = {
        "schema": "geometry_ready_source_replay_v2",
        "generated_utc": now_utc(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "inputs": {
            "top_geometry_live_replay_results": rel(TOP_REPLAY_JSON),
            "top_geometry_live_replay_results_sha256": file_sha256(
                TOP_REPLAY_JSON
            ),
            "geometry_live_wiring_matrix": rel(MATRIX_JSON),
            "geometry_live_wiring_matrix_sha256": file_sha256(MATRIX_JSON),
            "legacy_source_manifest_audit_only": rel(LEGACY_MANIFEST_JSON),
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
        "summary": summary,
        "lane_scoreboard": scoreboard,
        "ready_source_replay_results": results,
        "next_actions": [
            "Preserve the measured EIA wave and generic time-series losses as nonpromotion evidence.",
            "Do not treat the thermal conditioned-synthetic mean win as direct source performance.",
            "Build a direct measured thermal adapter with source-native accepted baselines before promotion.",
            "Build a compatible measured optimal-curve dataset and incumbent baseline before replaying Brachistochrone.",
            "Run development-only family search, freeze one candidate per lane, then evaluate the untouched holdout once.",
            "Require all registered source-specific baselines and global multiplicity correction for every promotion.",
            "Acquire independent repeat runs only after a direct measured candidate clears the first-run gate.",
        ],
        "claim_gates": {
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "medical_or_addiction_treatment_claim_allowed": False,
            "mass_email_allowed": False,
            "buyer_authorized_field_pilot_required": True,
        },
    }
    payload["summary"]["replay_chain_sha256"] = stable_sha256(
        {
            "summary_without_chain": payload["summary"],
            "route_hashes": [row["route_sha256"] for row in results],
        }
    )
    serialized = json.dumps(payload, sort_keys=True, default=str).lower()
    for term in FORBIDDEN_CLAIM_TERMS:
        if term in serialized:
            raise ValueError(
                f"Forbidden claim term leaked into ready-source replay: {term}"
            )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Ready Source Replay",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Top cards reviewed: `{summary['cards_reviewed']}`",
        f"- Compatible adapters run: `{summary['routes_replayed']}`",
        f"- Direct measured replays: `{summary['direct_measured_replay_count']}`",
        f"- Source-conditioned synthetic stress cards: `{summary['source_conditioned_synthetic_stress_count']}`",
        f"- No-compatible-input cards: `{summary['no_compatible_replay_input_count']}`",
        f"- Direct all-baseline globally corrected promotions: `{summary['direct_all_baseline_global_holm_positive_count']}`",
        f"- Conditioned-synthetic named-baseline mean wins: `{summary['source_conditioned_named_baseline_mean_win_count']}`",
        f"- Legacy generic ready rows excluded: `{summary['legacy_ready_for_benchmark_rows_excluded']}`",
        f"- Numeric fallback profiles: `{summary['numeric_fallback_profile_count']}`",
        f"- Replay chain SHA-256: `{summary['replay_chain_sha256']}`",
        "",
        "## Compatibility-Gated Results",
        "",
        "| Lane | Evaluated candidate | Registered candidate | Mode | Baselines | Mean wins | Global positives | Rows |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["ready_source_replay_results"]:
        lines.append(
            f"| `{row['lane']}` | `{row['candidate_family']}` | "
            f"`{row['registered_candidate_family']}` | `{row['evidence_mode']}` | "
            f"{row['registered_baseline_count']} | "
            f"{row['registered_baseline_mean_win_count']} | "
            f"{row['registered_baseline_global_holm_positive_count']} | "
            f"{row['performance_rows_evaluated']} |"
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- Direct measured replay and source-conditioned synthetic stress are separate evidence modes.",
            "- The current direct measured cards do not clear their complete source-specific baseline gauntlets.",
            "- The thermal conditioned-synthetic mean win is a research lead, not field validation or source performance.",
            "- No realized savings, fixed-dollar, medical, live-trading, or award-certainty claim is allowed.",
            "",
            "## Next Actions",
            "",
        ]
    )
    for index, action in enumerate(payload["next_actions"], start=1):
        lines.append(f"{index}. {action}")
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))


if __name__ == "__main__":
    main()
