from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

REPEAT_VALIDATION_JSON = (
    OUT_OPS / "geometry_repeat_proof_validation_latest.json"
)
REPEAT_VALIDATION_SCRIPT = (
    ROOT / "code" / "ops" / "BUILD_GEOMETRY_REPEAT_PROOF_VALIDATION.py"
)
OUT_JSON = OUT_OPS / "geometry_repeat_uncertainty_report_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_repeat_uncertainty_report.json"
OUT_MD = DOCS / "GEOMETRY_REPEAT_UNCERTAINTY_REPORT_2026-06-25.md"

BOUNDARY = (
    "This report is a fail-closed uncertainty audit over qualified repeat runs. "
    "The current compatibility-gated repeat validation contains no eligible "
    "independent repeat runs, so no uncertainty or robust-repeat promotion is "
    "computed. Paired units from a single frozen benchmark, source-conditioned "
    "synthetic stress, historical proxy rows, and context-only sources are not "
    "independent repeats. This is not a prospective field trial, field validation, "
    "realized savings, a fixed-dollar valuation, or live execution permission."
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


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


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


def load_repeat_validation_payload() -> dict[str, Any]:
    payload = read_json(REPEAT_VALIDATION_JSON)
    if payload.get("schema") == "geometry_repeat_proof_validation_v2":
        return payload

    spec = importlib.util.spec_from_file_location(
        "geometry_repeat_proof_validation_for_uncertainty",
        REPEAT_VALIDATION_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise ImportError(
            f"Could not load repeat validation: {REPEAT_VALIDATION_SCRIPT}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_payload()


def analyze_validation(row: dict[str, Any]) -> dict[str, Any]:
    eligible = bool(row.get("eligible_for_repeat_confirmation"))
    independent_count = int(row.get("independent_repeat_run_count", 0) or 0)
    repeat_passed = bool(row.get("repeat_candidate_gate_passed"))
    blockers = list(row.get("blockers", []))
    if not eligible and "repeat_confirmation_not_eligible" not in blockers:
        blockers.append("repeat_confirmation_not_eligible")
    if independent_count < 2 and "independent_repeat_runs_missing" not in blockers:
        blockers.append("independent_repeat_runs_missing")
    if not repeat_passed and "repeat_candidate_gate_not_passed" not in blockers:
        blockers.append("repeat_candidate_gate_not_passed")

    analysis = {
        "family_id": row.get("family_id", ""),
        "registered_card_candidate_family_id": row.get(
            "registered_card_candidate_family_id", ""
        ),
        "lane": row.get("lane", ""),
        "named_baseline": row.get("named_baseline", ""),
        "evidence_mode": row.get("evidence_mode", ""),
        "window_count": independent_count,
        "win_count": 0,
        "win_rate": 0.0,
        "wilson_lower_95_win_rate": 0.0,
        "one_sided_sign_test_p_value": 1.0,
        "min_source_count": row.get("min_source_count", 0),
        "distinct_win_hash_count": 0,
        "candidate_best_geometry_count": 0,
        "repeat_candidate_gate_passed": repeat_passed,
        "robust_repeat_uncertainty_gate_passed": False,
        "blockers": blockers,
        "delta_stats": {
            "mean_delta": None,
            "median_delta": None,
            "min_delta": None,
            "max_delta": None,
            "stdev_delta": None,
            "normal_t_lower_95_delta": None,
            "normal_t_upper_95_delta": None,
        },
        "evidence_stage": (
            "repeat_uncertainty_not_computable_no_qualified_independent_runs"
        ),
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
    if repeat_payload.get("schema") != "geometry_repeat_proof_validation_v2":
        raise ValueError("geometry repeat proof validation v2 is required")
    analyses = [
        analyze_validation(row)
        for row in repeat_payload.get("validations", [])
        if isinstance(row, dict)
    ]
    robust = [
        row
        for row in analyses
        if row["robust_repeat_uncertainty_gate_passed"]
    ]
    summary = {
        "family_count": len(analyses),
        "repeat_confirmation_eligible_count": sum(
            bool(row.get("repeat_candidate_gate_passed")) for row in analyses
        ),
        "robust_repeat_uncertainty_gate_passed_count": len(robust),
        "total_windows_analyzed": sum(row["window_count"] for row in analyses),
        "total_winning_windows": 0,
        "robust_candidates": [],
        "uncertainty_computable": False,
        "ready_for_field_validation_claim": False,
        "ready_for_real_dollar_claim": False,
        "ready_for_bulk_sales_claim": False,
        "ready_for_live_trading": False,
        "uncertainty_chain_sha256": stable_sha256(analyses),
    }
    return {
        "schema": "geometry_repeat_uncertainty_report_v2",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "geometry_repeat_proof_validation": rel(
                REPEAT_VALIDATION_JSON
            ),
            "geometry_repeat_proof_validation_sha256": (
                file_sha256(REPEAT_VALIDATION_JSON)
                if REPEAT_VALIDATION_JSON.exists()
                else ""
            ),
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
        "repeat_validation_summary": repeat_payload.get("summary", {}),
        "summary": summary,
        "analyses": analyses,
        "claim_controls": {
            "allowed": [
                "uncertainty not computable statement",
                "qualified repeat-evidence gap",
                "development-only research target",
            ],
            "blocked": [
                "robust repeat-window candidate",
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
        f"- Families audited: `{summary['family_count']}`",
        f"- Robust repeat-window candidates: `{summary['robust_repeat_uncertainty_gate_passed_count']}`",
        f"- Qualified independent windows analyzed: `{summary['total_windows_analyzed']}`",
        f"- Uncertainty computable: `{str(summary['uncertainty_computable']).lower()}`",
        f"- Ready for field-validation claim: `{str(summary['ready_for_field_validation_claim']).lower()}`",
        f"- Ready for real-dollar claim: `{str(summary['ready_for_real_dollar_claim']).lower()}`",
        f"- Ready for bulk sales claim: `{str(summary['ready_for_bulk_sales_claim']).lower()}`",
        f"- Uncertainty chain SHA-256: `{summary['uncertainty_chain_sha256']}`",
        "",
        "## Family Table",
        "",
        "| Evaluated family | Registered card family | Lane | Mode | Qualified repeats | Gate |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for row in payload["analyses"]:
        lines.append(
            f"| `{row['family_id']}` | `{row['registered_card_candidate_family_id']}` | "
            f"`{row['lane']}` | `{row['evidence_mode']}` | "
            f"{row['window_count']} | "
            f"`{str(row['robust_repeat_uncertainty_gate_passed']).lower()}` |"
        )
    lines.extend(
        [
            "",
            "## Current Interpretation",
            "",
            "No family has qualified independent repeat runs, so uncertainty is not "
            "computable and no robust-repeat candidate exists. Real-dollar claims "
            "require a direct measured candidate that first clears its complete "
            "source-specific baseline gauntlet, followed by distinct frozen repeat "
            "runs and an independently authorized field protocol.",
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
                "robust_repeat_uncertainty_gate_passed_count": payload[
                    "summary"
                ]["robust_repeat_uncertainty_gate_passed_count"],
                "total_windows_analyzed": payload["summary"][
                    "total_windows_analyzed"
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
