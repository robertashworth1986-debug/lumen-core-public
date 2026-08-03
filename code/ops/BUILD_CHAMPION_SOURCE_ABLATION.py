from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

HOLDOUT_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"
SWEEP_JSON = OUT_OPS / "locked_source_baseline_replay_sweep_latest.json"
WIRING_JSON = DASHBOARD_DATA / "geometry_live_wiring_matrix.json"

OUT_JSON = OUT_OPS / "champion_source_ablation_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "champion_source_ablation.json"
OUT_MD = DOCS / "CHAMPION_SOURCE_ABLATION_2026-07-03.md"

EXPECTED_CONTRACT = {
    "direct_measured_routes": 2,
    "conditioned_synthetic_routes": 2,
    "baseline_comparisons": 22,
    "performance_rows": 32608,
    "direct_all_baseline_global_holm_positive_promotions": 0,
    "inventory_measured_sources": 24,
    "inventory_measured_rows": 17081,
    "kuramoto_wins_vs_kalman": 482,
    "kuramoto_holdouts": 1525,
    "kuramoto_mean_delta_vs_kalman": -0.508191,
}

BOUNDARY = (
    "This is a nonpromotion source-ablation diagnostic. It audits source dependence and evidence "
    "coverage; it does not identify a performance champion. Direct measured replay, conditioned-"
    "synthetic replay, and source inventory are separate evidence classes. Inventory counts are "
    "inventory only. No field-validation, realized-savings, fixed-dollar, live-trading, or hardware "
    "performance claim is allowed."
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
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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
        return int(float(value))
    except (TypeError, ValueError):
        return default


def stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def source_cards(comparisons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in comparisons:
        source = str(row.get("source_system") or "unknown")
        grouped.setdefault(source, []).append(row)

    cards: list[dict[str, Any]] = []
    for source, rows in sorted(grouped.items()):
        baselines = sorted({str(row.get("baseline") or "unknown") for row in rows})
        cards.append(
            {
                "source_system": source,
                "baseline_comparison_count": len(rows),
                "registered_baselines": baselines,
                "paired_daily_holdouts": max(
                    (safe_int(row.get("daily_pair_count")) for row in rows),
                    default=0,
                ),
                "comparison_gate_pass_count": sum(
                    bool(row.get("passes_comparison_gate")) for row in rows
                ),
                "supports_performance_champion_claim": False,
                "claim_gate": (
                    "Measured reference slice only; source coverage does not establish a champion."
                ),
            }
        )
    return cards


def leave_one_source_out(
    comparisons: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sources = sorted(
        {str(row.get("source_system") or "unknown") for row in comparisons}
    )
    diagnostics: list[dict[str, Any]] = []
    for source in sources:
        kept = [
            row
            for row in comparisons
            if str(row.get("source_system") or "unknown") != source
        ]
        remaining_sources = sorted(
            {str(row.get("source_system") or "unknown") for row in kept}
        )
        diagnostics.append(
            {
                "withheld_source_system": source,
                "remaining_source_system_count": len(remaining_sources),
                "remaining_source_systems": remaining_sources,
                "remaining_baseline_comparison_count": len(kept),
                "diagnostic_evaluable": bool(kept),
                "supports_performance_champion_claim": False,
                "supports_promotion": False,
                "claim_gate": (
                    "Withholding this source leaves no independent measured source replay; "
                    "the diagnostic is not evaluable."
                    if not kept
                    else "Source-ablation result is diagnostic only and cannot promote a candidate."
                ),
            }
        )
    return diagnostics


def build_payload() -> dict[str, Any]:
    holdout = read_json(HOLDOUT_JSON)
    sweep = read_json(SWEEP_JSON)
    wiring = read_json(WIRING_JSON)

    holdout_summary = as_dict(holdout.get("summary"))
    sweep_summary = as_dict(sweep.get("summary"))
    wiring_summary = as_dict(wiring.get("summary"))
    comparisons = [
        row
        for row in as_list(holdout.get("holdout_results"))
        if isinstance(row, dict)
    ]

    contract = {
        "performance_champion_present": False,
        "direct_measured_routes": safe_int(
            sweep_summary.get("direct_measured_routes_replayed")
        ),
        "conditioned_synthetic_routes": safe_int(
            sweep_summary.get("source_conditioned_routes_replayed")
        ),
        "baseline_comparisons": safe_int(
            sweep_summary.get("baseline_comparison_count")
        ),
        "performance_rows": safe_int(sweep_summary.get("numeric_samples_read")),
        "direct_all_baseline_global_holm_positive_promotions": safe_int(
            sweep_summary.get("global_holm_positive_count")
        ),
        "inventory_measured_sources": safe_int(
            wiring_summary.get("live_source_measured_count")
        ),
        "inventory_measured_rows": safe_int(
            wiring_summary.get("total_measured_rows")
        ),
        "inventory_is_performance_evidence": False,
    }
    contract_matches_expected = all(
        contract.get(key) == value
        for key, value in EXPECTED_CONTRACT.items()
        if key in contract
    )

    reference = {
        "family": str(
            holdout_summary.get("candidate") or "kuramoto_phase_coupling"
        ),
        "status": "negative_measured_reference_not_development_selected",
        "evidence_mode": str(
            holdout_summary.get("evidence_mode") or "direct_measured_replay"
        ),
        "development_selected_candidate": str(
            holdout_summary.get("development_selected_candidate")
            or "lissajous_phase_paths"
        ),
        "was_development_selected": bool(
            holdout_summary.get("candidate_was_protocol_selected")
        ),
        "wins_vs_kalman": safe_int(holdout_summary.get("wins_vs_kalman")),
        "holdout_count": safe_int(holdout_summary.get("holdout_count")),
        "mean_delta_vs_kalman": round(
            safe_float(holdout_summary.get("mean_delta_vs_kalman")), 6
        ),
        "registered_baseline_count": safe_int(
            holdout_summary.get("registered_baseline_count")
        ),
        "registered_baseline_gate_pass_count": safe_int(
            holdout_summary.get("registered_baseline_gate_pass_count")
        ),
        "candidate_beats_all_registered_baselines_after_holm": bool(
            holdout_summary.get(
                "candidate_beats_all_registered_baselines_after_holm"
            )
        ),
        "supports_performance_champion_claim": False,
        "supports_promotion": False,
    }
    reference_matches_expected = (
        reference["wins_vs_kalman"]
        == EXPECTED_CONTRACT["kuramoto_wins_vs_kalman"]
        and reference["holdout_count"] == EXPECTED_CONTRACT["kuramoto_holdouts"]
        and reference["mean_delta_vs_kalman"]
        == EXPECTED_CONTRACT["kuramoto_mean_delta_vs_kalman"]
        and reference["was_development_selected"] is False
    )

    source_level = source_cards(comparisons)
    ablations = leave_one_source_out(comparisons)
    evaluable_ablations = sum(
        bool(row.get("diagnostic_evaluable")) for row in ablations
    )

    payload: dict[str, Any] = {
        "generated_utc": now_utc(),
        "schema": "champion_source_ablation_v2",
        "artifact_role": "nonpromotion_source_ablation_diagnostic",
        "purpose": (
            "Audit measured-source dependence for the Kuramoto negative reference "
            "without selecting, ranking, or promoting a performance candidate."
        ),
        "boundary": BOUNDARY,
        "canonical_evidence_contract": contract,
        "reference_audit": reference,
        "summary": {
            "performance_champion_present": False,
            "promotion_candidate_present": False,
            "contract_matches_expected": contract_matches_expected,
            "reference_matches_expected": reference_matches_expected,
            "source_system_count": len(source_level),
            "source_ablation_count": len(ablations),
            "evaluable_source_ablation_count": evaluable_ablations,
            "source_ablation_supports_promotion_count": 0,
            "field_validation_claim_allowed": False,
            "performance_superiority_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "plain_english_answer": (
                "No performance champion is present. Kuramoto is a negative measured "
                "reference: it won 482 of 1,525 paired holdouts against the named Kalman "
                "baseline with mean delta -0.508191, and it was not development-selected. "
                "Its measured audit uses one source system, so withholding that source "
                "leaves no evaluable replay and supports no promotion claim."
            ),
        },
        "claim_controls": {
            "allowed_now": [
                "negative measured reference audit",
                "single-source dependence limitation",
                "separation of direct measured and conditioned-synthetic routes",
                "source inventory as inventory only",
            ],
            "not_allowed": [
                "performance champion",
                "candidate promotion",
                "cross-source robustness",
                "field validated",
                "performance superiority",
                "realized savings",
                "fixed dollar value",
                "live trading edge",
                "hardware phase-lock validation",
            ],
        },
        "leave_one_source_out": ablations,
        "source_system_cards": source_level,
        "source_artifacts": {
            "kuramoto_negative_reference": str(HOLDOUT_JSON.relative_to(ROOT)),
            "compatibility_gated_replay_sweep": str(SWEEP_JSON.relative_to(ROOT)),
            "source_inventory": str(WIRING_JSON.relative_to(ROOT)),
        },
    }
    payload["source_ablation_sha256"] = stable_sha256(
        {
            "canonical_evidence_contract": payload["canonical_evidence_contract"],
            "reference_audit": payload["reference_audit"],
            "summary": payload["summary"],
            "leave_one_source_out": payload["leave_one_source_out"],
            "source_system_cards": payload["source_system_cards"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = as_dict(payload.get("summary"))
    contract = as_dict(payload.get("canonical_evidence_contract"))
    reference = as_dict(payload.get("reference_audit"))
    lines = [
        "# Source Ablation Nonpromotion Diagnostic",
        "",
        f"Generated UTC: `{payload.get('generated_utc')}`",
        f"Diagnostic SHA-256: `{payload.get('source_ablation_sha256')}`",
        "",
        "## Truth Line",
        "",
        str(summary.get("plain_english_answer") or ""),
        "",
        "## Canonical Evidence Contract",
        "",
        f"- Performance champion present: `{str(contract.get('performance_champion_present')).lower()}`",
        f"- Direct measured routes: `{contract.get('direct_measured_routes')}`",
        f"- Conditioned-synthetic routes: `{contract.get('conditioned_synthetic_routes')}`",
        f"- Baseline comparisons: `{contract.get('baseline_comparisons')}`",
        f"- Performance rows: `{contract.get('performance_rows')}`",
        (
            "- Direct all-baseline globally Holm-positive promotions: "
            f"`{contract.get('direct_all_baseline_global_holm_positive_promotions')}`"
        ),
        f"- Inventory measured sources: `{contract.get('inventory_measured_sources')}`",
        f"- Inventory measured rows: `{contract.get('inventory_measured_rows')}`",
        f"- Inventory is performance evidence: `{str(contract.get('inventory_is_performance_evidence')).lower()}`",
        "",
        "## Negative Measured Reference",
        "",
        f"- Family: `{reference.get('family')}`",
        f"- Status: `{reference.get('status')}`",
        f"- Development-selected: `{str(reference.get('was_development_selected')).lower()}`",
        f"- Development-selected candidate: `{reference.get('development_selected_candidate')}`",
        f"- Wins vs named Kalman baseline: `{reference.get('wins_vs_kalman')}/{reference.get('holdout_count')}`",
        f"- Mean delta vs named Kalman baseline: `{reference.get('mean_delta_vs_kalman')}`",
        f"- Supports promotion: `{str(reference.get('supports_promotion')).lower()}`",
        "",
        "## Leave-One-Source-Out Diagnostic",
        "",
        "| Withheld Source | Remaining Sources | Remaining Comparisons | Evaluable | Supports Promotion |",
        "|---|---:|---:|---|---|",
    ]
    for row in as_list(payload.get("leave_one_source_out")):
        item = as_dict(row)
        lines.append(
            "| "
            f"`{item.get('withheld_source_system')}` | "
            f"{item.get('remaining_source_system_count')} | "
            f"{item.get('remaining_baseline_comparison_count')} | "
            f"`{str(item.get('diagnostic_evaluable')).lower()}` | "
            f"`{str(item.get('supports_promotion')).lower()}` |"
        )
    lines.extend(["", "## Boundary", "", str(payload.get("boundary") or "")])
    return "\n".join(lines)


def write_outputs(
    payload: dict[str, Any],
    *,
    out_json: Path = OUT_JSON,
    dashboard_json: Path = DASHBOARD_JSON,
    out_md: Path = OUT_MD,
) -> None:
    write_json(out_json, payload)
    write_json(dashboard_json, payload)
    write_text(out_md, render_markdown(payload))


def main() -> int:
    payload = build_payload()
    write_outputs(payload)
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(payload["summary"]["plain_english_answer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
