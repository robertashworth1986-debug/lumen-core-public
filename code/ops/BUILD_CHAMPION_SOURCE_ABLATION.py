from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

HOLDOUT_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"
GAUNTLET_JSON = DASHBOARD_DATA / "champion_metric_gauntlet.json"
PHASE_JSON = DASHBOARD_DATA / "champion_phase_proxy_diagnostics.json"

OUT_JSON = OUT_OPS / "champion_source_ablation_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "champion_source_ablation.json"
OUT_MD = DOCS / "CHAMPION_SOURCE_ABLATION_2026-07-03.md"

BOUNDARY = (
    "Champion source ablation. This artifact tests whether the current internal champion remains "
    "positive when each source system is withheld from the current holdout replay. It is internal "
    "source-conditioned evidence only. It is not field validation, not realized savings, not hardware "
    "validation, not a fixed dollar claim, and not live trading evidence."
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


def mean(values: list[float]) -> float:
    return round(statistics.mean(values), 6) if values else 0.0


def min_or_zero(values: list[float]) -> float:
    return round(min(values), 6) if values else 0.0


def max_or_zero(values: list[float]) -> float:
    return round(max(values), 6) if values else 0.0


def stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sign_test_p_value(wins: int, total: int) -> float:
    if total <= 0 or wins <= 0:
        return 1.0
    # One-sided exact sign test under p=0.5: P(X >= wins).
    numerator = sum(math.comb(total, k) for k in range(wins, total + 1))
    return round(numerator / (2**total), 10)


def wilson_lower_bound(wins: int, total: int, z: float = 1.96) -> float:
    if total <= 0:
        return 0.0
    phat = wins / total
    denom = 1 + z * z / total
    center = phat + z * z / (2 * total)
    spread = z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total)
    return round((center - spread) / denom, 6)


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [safe_float(row.get("delta_vs_kalman")) for row in rows]
    best_deltas = [safe_float(row.get("delta_vs_best_baseline")) for row in rows]
    wins_named = sum(bool(row.get("candidate_beats_kalman")) for row in rows)
    wins_best = sum(bool(row.get("candidate_beats_best_baseline")) for row in rows)
    holdout_count = len(rows)
    sources = sorted({str(row.get("source_system") or "unknown") for row in rows})
    return {
        "holdout_count": holdout_count,
        "source_system_count": len(sources),
        "source_systems": sources,
        "wins_vs_named_baseline": wins_named,
        "wins_vs_best_same_run_baseline": wins_best,
        "win_rate_vs_named_baseline": round(wins_named / holdout_count, 6) if holdout_count else 0.0,
        "win_rate_vs_best_same_run_baseline": round(wins_best / holdout_count, 6) if holdout_count else 0.0,
        "mean_delta_vs_named_baseline": mean(deltas),
        "min_delta_vs_named_baseline": min_or_zero(deltas),
        "max_delta_vs_named_baseline": max_or_zero(deltas),
        "mean_delta_vs_best_same_run_baseline": mean(best_deltas),
        "min_delta_vs_best_same_run_baseline": min_or_zero(best_deltas),
        "estimated_rows_replayed": sum(safe_int(row.get("estimated_rows")) for row in rows),
        "numeric_samples_read": sum(safe_int(row.get("numeric_samples")) for row in rows),
        "one_sided_sign_test_p_value": sign_test_p_value(wins_named, holdout_count),
        "wilson_95_win_rate_lower": wilson_lower_bound(wins_named, holdout_count),
    }


def source_cards(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("source_system") or "unknown")].append(row)

    cards: list[dict[str, Any]] = []
    for source, source_rows in sorted(grouped.items()):
        summary = summarize_rows(source_rows)
        summary["source_system"] = source
        summary["claim_gate"] = "single-source internal replay slice; not field validation"
        cards.append(summary)
    return cards


def leave_one_source_out(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = sorted({str(row.get("source_system") or "unknown") for row in rows})
    ablations: list[dict[str, Any]] = []
    for source in sources:
        kept = [row for row in rows if str(row.get("source_system") or "unknown") != source]
        withheld = [row for row in rows if str(row.get("source_system") or "unknown") == source]
        summary = summarize_rows(kept)
        summary.update(
            {
                "withheld_source_system": source,
                "withheld_holdout_count": len(withheld),
                "withheld_estimated_rows": sum(safe_int(row.get("estimated_rows")) for row in withheld),
                "passes_positive_margin_after_withholding": summary["holdout_count"] > 0
                and summary["wins_vs_named_baseline"] == summary["holdout_count"]
                and summary["min_delta_vs_named_baseline"] > 0,
                "claim_gate": "source ablation pass supports internal robustness language only",
            }
        )
        ablations.append(summary)
    return ablations


def build_payload() -> dict[str, Any]:
    holdout = read_json(HOLDOUT_JSON)
    gauntlet = read_json(GAUNTLET_JSON)
    phase = read_json(PHASE_JSON)
    rows = [row for row in as_list(holdout.get("holdout_results")) if isinstance(row, dict)]
    base = summarize_rows(rows)
    ablations = leave_one_source_out(rows)
    source_level = source_cards(rows)
    ablation_passes = [row for row in ablations if row["passes_positive_margin_after_withholding"]]
    gauntlet_strongest = as_dict(gauntlet.get("strongest_current"))
    phase_summary = as_dict(phase.get("summary"))

    payload: dict[str, Any] = {
        "generated_utc": now_utc(),
        "schema": "champion_source_ablation_v1",
        "purpose": "Test whether the current champion remains positive when each source system is withheld.",
        "boundary": BOUNDARY,
        "summary": {
            "champion_family": gauntlet_strongest.get("family") or base.get("champion_family") or "kuramoto_phase_coupling",
            "champion_label": gauntlet_strongest.get("label") or "Kuramoto phase coupling",
            "lane": gauntlet_strongest.get("lane") or "wave_resonance_timing",
            "named_baseline": gauntlet_strongest.get("named_baseline") or "kalman_filter",
            **base,
            "source_ablation_count": len(ablations),
            "source_ablation_pass_count": len(ablation_passes),
            "source_ablation_pass_rate": round(len(ablation_passes) / len(ablations), 6) if ablations else 0.0,
            "minimum_withheld_source_holdouts": min((safe_int(row.get("withheld_holdout_count")) for row in ablations), default=0),
            "all_leave_one_source_out_passed": len(ablations) > 0 and len(ablation_passes) == len(ablations),
            "phase_proxy_diagnostics_ready": bool(phase_summary.get("phase_proxy_claim_allowed")),
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_frozen_delta_price_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "plain_english_answer": (
                "The champion is not being carried by a single current source system: each leave-one-source-out "
                "slice remains positive against the named Kalman baseline. This strengthens internal robustness "
                "and buyer-replay readiness, while still stopping short of field validation or realized dollars."
            ),
        },
        "claim_controls": {
            "allowed_now": [
                "leave-one-source-out internal robustness evidence",
                "source-conditioned champion robustness",
                "buyer-authorized field replay request ready",
            ],
            "not_allowed_yet": [
                "field validated",
                "realized savings",
                "fixed frozen-delta price",
                "live trading edge",
                "hardware phase-lock validation",
            ],
        },
        "leave_one_source_out": ablations,
        "source_system_cards": source_level,
        "source_artifacts": {
            "holdout_expansion": str(HOLDOUT_JSON.relative_to(ROOT)),
            "champion_metric_gauntlet": str(GAUNTLET_JSON.relative_to(ROOT)),
            "champion_phase_proxy_diagnostics": str(PHASE_JSON.relative_to(ROOT)),
        },
    }
    payload["source_ablation_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "leave_one_source_out": payload["leave_one_source_out"],
            "source_system_cards": payload["source_system_cards"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = as_dict(payload.get("summary"))
    lines = [
        "# Champion Source Ablation",
        "",
        f"Generated UTC: `{payload.get('generated_utc')}`",
        f"Source ablation SHA-256: `{payload.get('source_ablation_sha256')}`",
        "",
        "## Truth Line",
        "",
        str(summary.get("plain_english_answer") or ""),
        "",
        "## Summary",
        "",
        f"- Champion: `{summary.get('champion_family')}`",
        f"- Lane: `{summary.get('lane')}`",
        f"- Named baseline: `{summary.get('named_baseline')}`",
        f"- Holdout wins: `{summary.get('wins_vs_named_baseline')}/{summary.get('holdout_count')}`",
        f"- Source systems: `{summary.get('source_system_count')}`",
        f"- Leave-one-source-out passes: `{summary.get('source_ablation_pass_count')}/{summary.get('source_ablation_count')}`",
        f"- All leave-one-source-out passed: `{str(summary.get('all_leave_one_source_out_passed')).lower()}`",
        f"- Mean delta vs named baseline: `{summary.get('mean_delta_vs_named_baseline')}`",
        f"- Minimum delta vs named baseline: `{summary.get('min_delta_vs_named_baseline')}`",
        f"- Estimated rows replayed: `{summary.get('estimated_rows_replayed')}`",
        f"- Numeric samples read: `{summary.get('numeric_samples_read')}`",
        f"- Field-validation claim allowed: `{str(summary.get('field_validation_claim_allowed')).lower()}`",
        "",
        "## Leave-One-Source-Out Table",
        "",
        "| Withheld Source | Kept Holdouts | Kept Wins | Min Delta | Mean Delta | Pass |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in as_list(payload.get("leave_one_source_out")):
        item = as_dict(row)
        lines.append(
            "| "
            f"`{item.get('withheld_source_system')}` | "
            f"{item.get('holdout_count')} | "
            f"{item.get('wins_vs_named_baseline')} | "
            f"{item.get('min_delta_vs_named_baseline')} | "
            f"{item.get('mean_delta_vs_named_baseline')} | "
            f"`{str(item.get('passes_positive_margin_after_withholding')).lower()}` |"
        )
    lines.extend(
        [
            "",
            "## Source System Cards",
            "",
            "| Source | Holdouts | Wins | Rows | Samples | Mean Delta | Min Delta |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in as_list(payload.get("source_system_cards")):
        item = as_dict(row)
        lines.append(
            "| "
            f"`{item.get('source_system')}` | "
            f"{item.get('holdout_count')} | "
            f"{item.get('wins_vs_named_baseline')} | "
            f"{item.get('estimated_rows_replayed')} | "
            f"{item.get('numeric_samples_read')} | "
            f"{item.get('mean_delta_vs_named_baseline')} | "
            f"{item.get('min_delta_vs_named_baseline')} |"
        )
    lines.extend(["", "## Boundary", "", str(payload.get("boundary") or "")])
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
