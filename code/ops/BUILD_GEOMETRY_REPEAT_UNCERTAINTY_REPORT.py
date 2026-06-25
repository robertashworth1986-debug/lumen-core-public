from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

REPEAT_VALIDATION_JSON = OUT_OPS / "geometry_repeat_proof_validation_latest.json"
REPEAT_VALIDATION_SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_REPEAT_PROOF_VALIDATION.py"
OUT_JSON = OUT_OPS / "geometry_repeat_uncertainty_report_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_repeat_uncertainty_report.json"
OUT_MD = DOCS / "GEOMETRY_REPEAT_UNCERTAINTY_REPORT_2026-06-25.md"

BOUNDARY = (
    "This report summarizes uncertainty over frozen live-source replay windows. It is a repeat-window evidence "
    "report, not a prospective field trial, not realized savings, not a fixed-dollar valuation, and not permission "
    "for live trading or autonomous operational changes."
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


def load_repeat_validation_payload() -> dict[str, Any]:
    payload = read_json(REPEAT_VALIDATION_JSON)
    if payload.get("validations"):
        return payload

    spec = importlib.util.spec_from_file_location("geometry_repeat_proof_validation_for_uncertainty", REPEAT_VALIDATION_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build_payload()


def wilson_lower_bound(successes: int, total: int, z: float = 1.959963984540054) -> float:
    if total <= 0:
        return 0.0
    p_hat = successes / total
    denom = 1 + z**2 / total
    centre = p_hat + z**2 / (2 * total)
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * total)) / total)
    return max(0.0, (centre - margin) / denom)


def one_sided_sign_test_p_value(successes: int, total: int) -> float:
    if total <= 0:
        return 1.0
    return sum(math.comb(total, k) for k in range(successes, total + 1)) / (2**total)


def t_critical_95_two_sided(total: int) -> float:
    df = max(1, total - 1)
    table = {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
        11: 2.201,
        12: 2.179,
        13: 2.16,
        14: 2.145,
        15: 2.131,
        16: 2.12,
        17: 2.11,
        18: 2.101,
        19: 2.093,
        20: 2.086,
        21: 2.08,
        22: 2.074,
        23: 2.069,
        24: 2.064,
        25: 2.06,
        26: 2.056,
        27: 2.052,
        28: 2.048,
        29: 2.045,
        30: 2.042,
    }
    return table.get(df, 1.96)


def margin_stats(deltas: list[float]) -> dict[str, Any]:
    if not deltas:
        return {
            "mean_delta": None,
            "median_delta": None,
            "min_delta": None,
            "max_delta": None,
            "stdev_delta": None,
            "normal_t_lower_95_delta": None,
            "normal_t_upper_95_delta": None,
        }
    if len(deltas) == 1:
        single = round(deltas[0], 6)
        return {
            "mean_delta": single,
            "median_delta": single,
            "min_delta": single,
            "max_delta": single,
            "stdev_delta": 0.0,
            "normal_t_lower_95_delta": single,
            "normal_t_upper_95_delta": single,
        }
    avg = mean(deltas)
    sd = stdev(deltas)
    critical = t_critical_95_two_sided(len(deltas))
    half_width = critical * sd / math.sqrt(len(deltas))
    return {
        "mean_delta": round(avg, 6),
        "median_delta": round(median(deltas), 6),
        "min_delta": round(min(deltas), 6),
        "max_delta": round(max(deltas), 6),
        "stdev_delta": round(sd, 6),
        "normal_t_lower_95_delta": round(avg - half_width, 6),
        "normal_t_upper_95_delta": round(avg + half_width, 6),
    }


def analyze_validation(row: dict[str, Any]) -> dict[str, Any]:
    windows = row.get("window_results", [])
    deltas = [
        float(window["candidate_score_delta_vs_named_baseline"])
        for window in windows
        if window.get("candidate_score_delta_vs_named_baseline") is not None
    ]
    total = len(deltas)
    wins = sum(1 for delta in deltas if delta > 0)
    stats = margin_stats(deltas)
    win_rate = wins / total if total else 0.0
    sign_p = one_sided_sign_test_p_value(wins, total)
    wilson_lower = wilson_lower_bound(wins, total)
    min_source_count = int(row.get("min_source_count", 0) or 0)
    distinct_win_hash_count = int(row.get("distinct_win_hash_count", 0) or 0)
    robust_gate = (
        bool(row.get("repeat_candidate_gate_passed"))
        and total >= 5
        and wins == total
        and stats["min_delta"] is not None
        and stats["min_delta"] > 0
        and stats["normal_t_lower_95_delta"] is not None
        and stats["normal_t_lower_95_delta"] > 0
        and wilson_lower >= 0.5
        and sign_p <= 0.05
        and min_source_count >= 3
        and distinct_win_hash_count >= 5
    )
    blockers: list[str] = []
    if total < 5:
        blockers.append("fewer_than_5_replay_windows")
    if wins < total:
        blockers.append("not_all_windows_positive")
    if stats["min_delta"] is None or stats["min_delta"] <= 0:
        blockers.append("non_positive_min_delta")
    if stats["normal_t_lower_95_delta"] is None or stats["normal_t_lower_95_delta"] <= 0:
        blockers.append("non_positive_margin_lower_95")
    if wilson_lower < 0.5:
        blockers.append("win_rate_lower_bound_below_majority")
    if sign_p > 0.05:
        blockers.append("sign_test_not_below_0_05")
    if min_source_count < 3:
        blockers.append("minimum_source_count_below_3")
    if distinct_win_hash_count < 5:
        blockers.append("fewer_than_5_distinct_winning_source_hashes")
    if not row.get("repeat_candidate_gate_passed"):
        blockers.append("repeat_candidate_gate_not_passed")

    analysis = {
        "family_id": row.get("family_id", ""),
        "lane": row.get("lane", ""),
        "named_baseline": row.get("named_baseline", ""),
        "window_count": total,
        "win_count": wins,
        "win_rate": round(win_rate, 6),
        "wilson_lower_95_win_rate": round(wilson_lower, 6),
        "one_sided_sign_test_p_value": round(sign_p, 8),
        "min_source_count": min_source_count,
        "distinct_win_hash_count": distinct_win_hash_count,
        "candidate_best_geometry_count": row.get("candidate_best_geometry_count", 0),
        "repeat_candidate_gate_passed": bool(row.get("repeat_candidate_gate_passed")),
        "robust_repeat_uncertainty_gate_passed": robust_gate,
        "blockers": blockers,
        "delta_stats": stats,
        "evidence_stage": "robust_repeat_window_candidate_not_field_validated"
        if robust_gate
        else "repeat_uncertainty_not_promoted",
        "claim_gate": {
            "ready_for_field_validation_claim": False,
            "ready_for_real_dollar_claim": False,
            "ready_for_bulk_sales_claim": False,
            "ready_for_live_trading": False,
        },
    }
    analysis["analysis_sha256"] = stable_sha256(analysis)
    return analysis


def build_payload() -> dict[str, Any]:
    repeat_payload = load_repeat_validation_payload()
    analyses = [analyze_validation(row) for row in repeat_payload.get("validations", []) if isinstance(row, dict)]
    robust = [row for row in analyses if row["robust_repeat_uncertainty_gate_passed"]]
    summary = {
        "family_count": len(analyses),
        "robust_repeat_uncertainty_gate_passed_count": len(robust),
        "total_windows_analyzed": sum(row["window_count"] for row in analyses),
        "total_winning_windows": sum(row["win_count"] for row in analyses),
        "robust_candidates": [
            {
                "family_id": row["family_id"],
                "lane": row["lane"],
                "win_count": row["win_count"],
                "window_count": row["window_count"],
                "min_delta": row["delta_stats"]["min_delta"],
                "mean_delta": row["delta_stats"]["mean_delta"],
                "normal_t_lower_95_delta": row["delta_stats"]["normal_t_lower_95_delta"],
                "wilson_lower_95_win_rate": row["wilson_lower_95_win_rate"],
                "one_sided_sign_test_p_value": row["one_sided_sign_test_p_value"],
            }
            for row in robust
        ],
        "ready_for_field_validation_claim": False,
        "ready_for_real_dollar_claim": False,
        "ready_for_bulk_sales_claim": False,
        "ready_for_live_trading": False,
        "uncertainty_chain_sha256": stable_sha256(analyses),
    }
    return {
        "schema": "geometry_repeat_uncertainty_report_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "geometry_repeat_proof_validation": str(REPEAT_VALIDATION_JSON.relative_to(ROOT)),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
        "repeat_validation_summary": repeat_payload.get("summary", {}),
        "summary": summary,
        "analyses": analyses,
        "claim_controls": {
            "allowed": [
                "robust repeat-window candidate",
                "frozen replay uncertainty evidence",
                "pilot evaluation target",
            ],
            "blocked": [
                "field validation",
                "realized savings",
                "fixed-dollar valuation",
                "bulk sales claim",
                "live trading",
            ],
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Repeat Uncertainty Report",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Families analyzed: `{summary['family_count']}`",
        f"- Robust repeat-window candidates: `{summary['robust_repeat_uncertainty_gate_passed_count']}`",
        f"- Total windows analyzed: `{summary['total_windows_analyzed']}`",
        f"- Total winning windows: `{summary['total_winning_windows']}`",
        f"- Ready for field-validation claim: `{str(summary['ready_for_field_validation_claim']).lower()}`",
        f"- Ready for real-dollar claim: `{str(summary['ready_for_real_dollar_claim']).lower()}`",
        f"- Ready for bulk sales claim: `{str(summary['ready_for_bulk_sales_claim']).lower()}`",
        f"- Uncertainty chain SHA-256: `{summary['uncertainty_chain_sha256']}`",
        "",
        "## Robust Repeat-Window Candidates",
        "",
    ]
    if not summary["robust_candidates"]:
        lines.append("No family passed the robust repeat-window uncertainty gate.")
    for row in summary["robust_candidates"]:
        lines.append(
            f"- `{row['family_id']}` ({row['lane']}): {row['win_count']}/{row['window_count']} positive windows, "
            f"min delta `{row['min_delta']}`, mean delta `{row['mean_delta']}`, "
            f"95% lower margin `{row['normal_t_lower_95_delta']}`, "
            f"Wilson lower win-rate `{row['wilson_lower_95_win_rate']}`, "
            f"sign-test p `{row['one_sided_sign_test_p_value']}`."
        )
    lines.extend(
        [
            "",
            "## Family Table",
            "",
            "| Family | Lane | Wins | Min Delta | Mean Delta | Lower 95 Delta | Wilson Lower Win Rate | Sign-Test p | Gate |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in payload["analyses"]:
        stats = row["delta_stats"]
        lines.append(
            f"| `{row['family_id']}` | `{row['lane']}` | {row['win_count']}/{row['window_count']} | "
            f"{stats['min_delta']} | {stats['mean_delta']} | {stats['normal_t_lower_95_delta']} | "
            f"{row['wilson_lower_95_win_rate']} | {row['one_sided_sign_test_p_value']} | "
            f"`{str(row['robust_repeat_uncertainty_gate_passed']).lower()}` |"
        )
    lines.extend(
        [
            "",
            "## Controls",
            "",
            "- A robust repeat-window candidate is a stronger buyer/pilot target than a single replay win.",
            "- This still is not field validation because the data was not buyer-authorized prospective field data.",
            "- Real-dollar claims require buyer/agency data, holdout rules agreed in advance, and observed operational or economic deltas.",
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
                "family_count": payload["summary"]["family_count"],
                "robust_repeat_uncertainty_gate_passed_count": payload["summary"][
                    "robust_repeat_uncertainty_gate_passed_count"
                ],
                "total_windows_analyzed": payload["summary"]["total_windows_analyzed"],
                "json": payload["outputs"]["json"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
