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

TOP_REPLAY_JSON = OUT_OPS / "top_geometry_live_replay_results_latest.json"
ASSET_MAP_JSON = OUT_OPS / "geometry_champion_asset_map_latest.json"
MATRIX_JSON = OUT_OPS / "geometry_live_wiring_matrix_latest.json"

OUT_JSON = OUT_OPS / "geometry_repeat_proof_validation_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_repeat_proof_validation.json"
OUT_MD = DOCS / "GEOMETRY_REPEAT_PROOF_VALIDATION_2026-06-25.md"

BOUNDARY = (
    "This is a compatibility-gated repeat-evidence audit. A family is eligible "
    "for repeat confirmation only after direct measured replay beats every "
    "registered source-specific baseline under the frozen source protocol and "
    "global multiplicity correction. Repeat promotion then requires at least two "
    "distinct frozen run hashes. Source-conditioned synthetic stress, context-only "
    "sources, historical proxy rows, and single frozen runs cannot satisfy this "
    "gate. This is not field validation, realized savings, a dollar claim, award "
    "certainty, or live execution permission."
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


def validation_from_card(card: dict[str, Any]) -> dict[str, Any]:
    evidence_mode = str(card.get("evidence_mode", ""))
    gauntlet = (
        card.get("baseline_gauntlet", {})
        if isinstance(card.get("baseline_gauntlet"), dict)
        else {}
    )
    evaluated = str(
        card.get("evaluated_candidate_family_id")
        or card.get("candidate_family_id")
        or ""
    )
    registered = str(card.get("candidate_family_id", ""))
    direct = evidence_mode == "direct_measured_replay"
    cleared_source_gate = bool(
        direct
        and gauntlet.get(
            "candidate_beats_all_registered_baselines_after_global_holm"
        )
    )

    direct_hashes = sorted(
        {
            str(value)
            for value in card.get("direct_replay_snapshot_sha256s", [])
            if str(value)
        }
    )
    independent_run_hashes: list[str] = []
    repeat_eligible = cleared_source_gate
    repeat_passed = bool(
        repeat_eligible and len(independent_run_hashes) >= 2
    )

    blockers: list[str] = []
    if not direct:
        blockers.append("evidence_mode_not_direct_measured_replay")
    if direct and not cleared_source_gate:
        blockers.append(
            "source_specific_all_baseline_global_holm_gate_not_passed"
        )
    if evaluated != registered:
        blockers.append(
            "registered_card_candidate_not_the_protocol_evaluated_candidate"
        )
    if len(independent_run_hashes) < 2:
        blockers.append("fewer_than_2_independent_frozen_repeat_run_hashes")

    if repeat_passed:
        stage = "direct_measured_repeat_candidate_not_field_validated"
    elif direct:
        stage = "direct_measured_nonpromotion_not_repeat_eligible"
    elif evidence_mode == "source_conditioned_synthetic_stress":
        stage = "source_conditioned_synthetic_stress_not_repeat_evidence"
    else:
        stage = "no_compatible_direct_measured_replay"

    validation = {
        "family_id": evaluated,
        "registered_card_candidate_family_id": registered,
        "candidate_resolution": card.get("candidate_resolution", ""),
        "lane": card.get("lane", ""),
        "named_baseline": card.get("named_baseline", ""),
        "best_baseline_family_id": card.get("best_baseline_family_id", ""),
        "evidence_mode": evidence_mode,
        "adapter_status": card.get("adapter_status", ""),
        "compatibility_contract_version": (
            "geometry_source_task_compatibility_v3"
        ),
        "direct_replay_source_names": card.get(
            "direct_replay_source_names", []
        ),
        "direct_replay_snapshot_sha256s": direct_hashes,
        "conditioned_stress_source_names": card.get(
            "conditioned_stress_source_names", []
        ),
        "excluded_context_source_names": card.get(
            "excluded_context_source_names", []
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
        "paired_unit_count": safe_int(
            (
                card.get("paired_inference", {})
                if isinstance(card.get("paired_inference"), dict)
                else {}
            ).get("paired_unit_count")
        ),
        "performance_rows_evaluated": safe_int(
            card.get("performance_rows_evaluated")
        ),
        "eligible_for_repeat_confirmation": repeat_eligible,
        "independent_repeat_run_hashes": independent_run_hashes,
        "independent_repeat_run_count": len(independent_run_hashes),
        "available_window_count": 0,
        "min_source_count": safe_int(card.get("direct_replay_source_count")),
        "repeat_live_win_count": 0,
        "distinct_window_hash_count": 0,
        "distinct_win_hash_count": 0,
        "candidate_best_geometry_count": 0,
        "repeat_candidate_gate_passed": repeat_passed,
        "blockers": blockers,
        "evidence_stage": stage,
        "window_results": [],
        "claim_gate": {
            "ready_for_live_geometry_claim": False,
            "ready_for_real_dollar_claim": False,
            "field_validation": False,
            "kraken_live_execution_allowed": False,
        },
        "claim_boundary": BOUNDARY,
    }
    validation["validation_sha256"] = stable_sha256(validation)
    return validation


def build_payload() -> dict[str, Any]:
    top_replay = read_json(TOP_REPLAY_JSON)
    if top_replay.get("schema") != "top_geometry_live_replay_results_v2":
        raise ValueError("top geometry replay v2 is required")
    matrix = read_json(MATRIX_JSON)
    if matrix.get("schema") != "geometry_live_wiring_matrix_v3":
        raise ValueError("geometry live wiring matrix v3 is required")
    asset_map = read_json(ASSET_MAP_JSON)

    cards = [
        dict(card)
        for card in top_replay.get("replay_cards", [])
        if isinstance(card, dict)
    ]
    validations = [validation_from_card(card) for card in cards]
    eligible = [
        row for row in validations if row["eligible_for_repeat_confirmation"]
    ]
    repeat_passed = [
        row for row in validations if row["repeat_candidate_gate_passed"]
    ]
    direct = [
        row
        for row in validations
        if row["evidence_mode"] == "direct_measured_replay"
    ]
    conditioned = [
        row
        for row in validations
        if row["evidence_mode"] == "source_conditioned_synthetic_stress"
    ]

    summary = {
        "validated_family_count": len(validations),
        "direct_measured_family_count": len(direct),
        "source_conditioned_synthetic_family_count": len(conditioned),
        "repeat_confirmation_eligible_count": len(eligible),
        "repeat_candidate_gate_passed_count": len(repeat_passed),
        "total_windows_replayed": 0,
        "total_live_context_rows_evaluated": 0,
        "total_performance_rows_reviewed": sum(
            row["performance_rows_evaluated"] for row in validations
        ),
        "historical_proxy_repeat_rows_accepted": 0,
        "top_repeat_candidates": [
            {
                "family_id": row["family_id"],
                "lane": row["lane"],
                "repeat_live_win_count": row["repeat_live_win_count"],
                "distinct_win_hash_count": row["distinct_win_hash_count"],
                "min_source_count": row["min_source_count"],
            }
            for row in repeat_passed
        ],
        "validation_chain_sha256": stable_sha256(validations),
        "ready_for_live_geometry_claim": False,
        "ready_for_real_dollar_claim": False,
        "field_validation": False,
        "kraken_live_execution_allowed": False,
    }
    return {
        "schema": "geometry_repeat_proof_validation_v2",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "top_geometry_live_replay_results": rel(TOP_REPLAY_JSON),
            "top_geometry_live_replay_results_sha256": file_sha256(
                TOP_REPLAY_JSON
            ),
            "geometry_live_wiring_matrix": rel(MATRIX_JSON),
            "geometry_live_wiring_matrix_sha256": file_sha256(MATRIX_JSON),
            "geometry_champion_asset_map": rel(ASSET_MAP_JSON),
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
        "asset_map_summary": asset_map.get("summary", {}),
        "summary": summary,
        "validations": validations,
        "claim_controls": {
            "allowed": [
                "direct measured nonpromotion result",
                "source-conditioned synthetic stress result",
                "repeat-evidence gap statement",
                "development-only research target",
            ],
            "blocked": [
                "repeat live champion",
                "field validation",
                "realized savings",
                "real-dollar claim",
                "award certainty",
                "live trading permission",
            ],
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Repeat Proof Validation",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Families audited: `{summary['validated_family_count']}`",
        f"- Direct measured families: `{summary['direct_measured_family_count']}`",
        f"- Repeat-confirmation eligible: `{summary['repeat_confirmation_eligible_count']}`",
        f"- Repeat candidate gates passed: `{summary['repeat_candidate_gate_passed_count']}`",
        f"- Independent repeat windows accepted: `{summary['total_windows_replayed']}`",
        f"- Historical proxy repeat rows accepted: `{summary['historical_proxy_repeat_rows_accepted']}`",
        f"- Ready for live geometry claim: `{str(summary['ready_for_live_geometry_claim']).lower()}`",
        f"- Ready for real-dollar claim: `{str(summary['ready_for_real_dollar_claim']).lower()}`",
        f"- Field validation: `{str(summary['field_validation']).lower()}`",
        f"- Validation chain SHA-256: `{summary['validation_chain_sha256']}`",
        "",
        "## Family Results",
        "",
        "| Evaluated family | Registered card family | Lane | Mode | Baselines | Global pass | Repeat runs | Gate |",
        "| --- | --- | --- | --- | ---: | --- | ---: | --- |",
    ]
    for row in payload["validations"]:
        lines.append(
            f"| `{row['family_id']}` | `{row['registered_card_candidate_family_id']}` | "
            f"`{row['lane']}` | `{row['evidence_mode']}` | "
            f"{row['registered_baseline_count']} | "
            f"`{str(row['candidate_beats_all_registered_baselines_after_global_holm']).lower()}` | "
            f"{row['independent_repeat_run_count']} | "
            f"`{str(row['repeat_candidate_gate_passed']).lower()}` |"
        )
    lines.extend(
        [
            "",
            "## Current Interpretation",
            "",
            "No family currently qualifies for repeat confirmation. The direct measured "
            "wave and time-series cards failed their source-specific baseline gauntlets; "
            "the branching and thermal cards are source-conditioned synthetic stress; "
            "and the optimal-curve card has no compatible direct replay input.",
            "",
            "This is not field validation and does not prove a real-dollar outcome. The "
            "next valid repeat run starts only after a direct measured candidate clears "
            "all registered source-specific baselines under global correction.",
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
                "validated_family_count": payload["summary"][
                    "validated_family_count"
                ],
                "repeat_candidate_gate_passed_count": payload["summary"][
                    "repeat_candidate_gate_passed_count"
                ],
                "json": payload["outputs"]["json"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
