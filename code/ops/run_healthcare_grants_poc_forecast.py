from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
ENGINE_DIR = ROOT / "out" / "ops" / "healthcare_grants_engine"
ENGINE_LATEST_JSON = ENGINE_DIR / "healthcare_grants_engine_latest.json"
ENGINE_HEARTBEAT_JSON = ENGINE_DIR / "healthcare_grants_engine_heartbeat_latest.json"

OUT_DIR = ROOT / "out" / "ops" / "healthcare_grants_poc"


DEFAULT_HORIZONS = (30, 60, 90)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip("\r\n") + "\n", encoding="utf-8")


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def funding_proxy_usd(record: dict[str, Any]) -> float:
    funding = record.get("funding", {}) if isinstance(record.get("funding"), dict) else {}
    ceiling = to_float(funding.get("award_ceiling_usd"))
    floor = to_float(funding.get("award_floor_usd"))
    total = to_float(funding.get("total_funding_usd"))
    expected_awards = to_int(funding.get("expected_awards"))

    if isinstance(ceiling, float) and ceiling > 0.0:
        return float(ceiling)
    if isinstance(total, float) and total > 0.0 and isinstance(expected_awards, int) and expected_awards > 0:
        return float(total) / float(expected_awards)
    if isinstance(floor, float) and floor > 0.0:
        return float(floor)
    return 0.0


def default_scenarios() -> list[dict[str, Any]]:
    return [
        {
            "name": "conservative",
            "assumptions": {
                "action_submit_rate": {
                    "IMMEDIATE_SUBMIT": 0.80,
                    "FAST_TRACK": 0.60,
                    "ACTIVE_PIPELINE": 0.38,
                    "WATCHLIST": 0.16,
                },
                "eligibility_pass_rate": 0.62,
                "award_rate": 0.08,
                "cost_per_submission_usd": 3500.0,
            },
        },
        {
            "name": "base",
            "assumptions": {
                "action_submit_rate": {
                    "IMMEDIATE_SUBMIT": 0.92,
                    "FAST_TRACK": 0.74,
                    "ACTIVE_PIPELINE": 0.52,
                    "WATCHLIST": 0.25,
                },
                "eligibility_pass_rate": 0.72,
                "award_rate": 0.12,
                "cost_per_submission_usd": 3200.0,
            },
        },
        {
            "name": "upside",
            "assumptions": {
                "action_submit_rate": {
                    "IMMEDIATE_SUBMIT": 0.98,
                    "FAST_TRACK": 0.84,
                    "ACTIVE_PIPELINE": 0.68,
                    "WATCHLIST": 0.35,
                },
                "eligibility_pass_rate": 0.82,
                "award_rate": 0.18,
                "cost_per_submission_usd": 3000.0,
            },
        },
    ]


def expected_pipeline_metrics(records: list[dict[str, Any]], scenario: dict[str, Any], horizons: list[int]) -> dict[str, Any]:
    assumptions = scenario.get("assumptions", {}) if isinstance(scenario.get("assumptions"), dict) else {}
    submit_rates = assumptions.get("action_submit_rate", {}) if isinstance(assumptions.get("action_submit_rate"), dict) else {}

    eligibility_pass_rate = float(assumptions.get("eligibility_pass_rate", 0.70) or 0.0)
    award_rate = float(assumptions.get("award_rate", 0.10) or 0.0)
    cost_per_submission_usd = float(assumptions.get("cost_per_submission_usd", 3500.0) or 0.0)

    def _record_projection(row: dict[str, Any]) -> dict[str, float]:
        action = str(row.get("action") or "WATCHLIST")
        submit_rate = float(submit_rates.get(action, submit_rates.get("WATCHLIST", 0.0)) or 0.0)
        submit_prob = max(min(submit_rate * eligibility_pass_rate, 1.0), 0.0)
        award_prob = max(min(submit_prob * award_rate, 1.0), 0.0)
        funding_proxy = funding_proxy_usd(row)
        expected_award_value = award_prob * funding_proxy
        expected_submission_cost = submit_prob * cost_per_submission_usd
        return {
            "submit_prob": submit_prob,
            "award_prob": award_prob,
            "funding_proxy_usd": funding_proxy,
            "expected_award_value_usd": expected_award_value,
            "expected_submission_cost_usd": expected_submission_cost,
        }

    projections = [_record_projection(row) for row in records]

    expected_submissions = sum(row["submit_prob"] for row in projections)
    expected_awards = sum(row["award_prob"] for row in projections)
    expected_award_value_usd = sum(row["expected_award_value_usd"] for row in projections)
    expected_submission_cost_usd = sum(row["expected_submission_cost_usd"] for row in projections)
    expected_net_value_usd = expected_award_value_usd - expected_submission_cost_usd

    by_horizon: list[dict[str, Any]] = []
    for horizon in horizons:
        scoped_records = [
            row for row in records
            if isinstance(row.get("days_to_close"), int) and int(row.get("days_to_close")) <= int(horizon)
        ]
        scoped_proj = [_record_projection(row) for row in scoped_records]
        by_horizon.append(
            {
                "horizon_days": int(horizon),
                "n_records": int(len(scoped_records)),
                "expected_submissions": round(sum(item["submit_prob"] for item in scoped_proj), 4),
                "expected_awards": round(sum(item["award_prob"] for item in scoped_proj), 4),
                "expected_award_value_usd": round(sum(item["expected_award_value_usd"] for item in scoped_proj), 2),
                "expected_submission_cost_usd": round(sum(item["expected_submission_cost_usd"] for item in scoped_proj), 2),
                "expected_net_value_usd": round(
                    sum(item["expected_award_value_usd"] for item in scoped_proj)
                    - sum(item["expected_submission_cost_usd"] for item in scoped_proj),
                    2,
                ),
            }
        )

    known_funding_rows = sum(1 for row in projections if float(row.get("funding_proxy_usd", 0.0)) > 0.0)

    return {
        "totals": {
            "n_records": int(len(records)),
            "known_funding_rows": int(known_funding_rows),
            "funding_coverage_pct": round((float(known_funding_rows) / max(float(len(records)), 1.0)) * 100.0, 4),
            "expected_submissions": round(expected_submissions, 4),
            "expected_awards": round(expected_awards, 4),
            "expected_award_value_usd": round(expected_award_value_usd, 2),
            "expected_submission_cost_usd": round(expected_submission_cost_usd, 2),
            "expected_net_value_usd": round(expected_net_value_usd, 2),
        },
        "by_horizon": by_horizon,
    }


def build_markdown(
    generated_utc: str,
    scope: dict[str, Any],
    baseline: dict[str, Any],
    scenarios: list[dict[str, Any]],
    evidence_paths: list[str],
) -> str:
    lines: list[str] = []
    lines.append("# Healthcare Grants Engine Proof of Concept")
    lines.append("")
    lines.append(f"- Generated UTC: {generated_utc}")
    lines.append(f"- Scope: top_n={scope.get('top_n')}, horizons_days={scope.get('horizons_days')}")
    lines.append(f"- Baseline scanned: {baseline.get('n_scanned', 0)}")
    lines.append(f"- Baseline scored: {baseline.get('n_scored', 0)}")
    lines.append(f"- Baseline selected: {baseline.get('n_selected', 0)}")
    lines.append("")

    lines.append("## Baseline Action Mix")
    action_counts = baseline.get("action_counts", {}) if isinstance(baseline.get("action_counts"), dict) else {}
    if action_counts:
        for action, count in action_counts.items():
            lines.append(f"- {action}: {count}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Future-State Scenario Projections")
    for scenario in scenarios:
        name = str(scenario.get("name") or "scenario")
        assumptions = scenario.get("assumptions", {}) if isinstance(scenario.get("assumptions"), dict) else {}
        totals = scenario.get("projections", {}).get("totals", {}) if isinstance(scenario.get("projections"), dict) else {}
        lines.append(f"### {name.title()} Scenario")
        lines.append(f"- eligibility_pass_rate: {assumptions.get('eligibility_pass_rate')}")
        lines.append(f"- award_rate: {assumptions.get('award_rate')}")
        lines.append(f"- cost_per_submission_usd: {assumptions.get('cost_per_submission_usd')}")
        lines.append(f"- expected_submissions: {totals.get('expected_submissions')}")
        lines.append(f"- expected_awards: {totals.get('expected_awards')}")
        lines.append(f"- expected_award_value_usd: {totals.get('expected_award_value_usd')}")
        lines.append(f"- expected_submission_cost_usd: {totals.get('expected_submission_cost_usd')}")
        lines.append(f"- expected_net_value_usd: {totals.get('expected_net_value_usd')}")

        horizon_rows = scenario.get("projections", {}).get("by_horizon", []) if isinstance(scenario.get("projections"), dict) else []
        if isinstance(horizon_rows, list) and horizon_rows:
            lines.append("")
            lines.append("| Horizon (days) | Records | Exp Submissions | Exp Awards | Exp Award Value USD | Exp Net Value USD |")
            lines.append("|---:|---:|---:|---:|---:|---:|")
            for row in horizon_rows:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    "| "
                    f"{row.get('horizon_days')} | {row.get('n_records')} | {row.get('expected_submissions')} | "
                    f"{row.get('expected_awards')} | {row.get('expected_award_value_usd')} | {row.get('expected_net_value_usd')} |"
                )
        lines.append("")

    lines.append("## Notes")
    lines.append("- This PoC is scenario-based forecasting, not a guarantee of awards.")
    lines.append("- Funding projections only use available award fields from source records.")
    lines.append("- Tune scenario assumptions as your team improves submission quality and eligibility filtering.")
    lines.append("")

    lines.append("## Evidence Paths")
    for path in evidence_paths:
        lines.append(f"- {path}")

    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run(top_n: int, horizons: list[int]) -> dict[str, Any]:
    engine_payload = read_json(ENGINE_LATEST_JSON, {})
    if not isinstance(engine_payload, dict):
        raise RuntimeError("Engine payload missing or invalid")

    records = engine_payload.get("records", [])
    if not isinstance(records, list):
        records = []

    records = records[: max(int(top_n), 1)]

    action_counts = Counter(str(row.get("action") or "") for row in records if str(row.get("action") or "").strip())
    avg_composite = 0.0
    if records:
        avg_composite = sum(float((row.get("scores") or {}).get("composite", 0.0)) for row in records) / float(len(records))

    baseline = {
        "n_scanned": int((engine_payload.get("metrics") or {}).get("n_scanned", 0)),
        "n_scored": int((engine_payload.get("metrics") or {}).get("n_scored", 0)),
        "n_selected": int((engine_payload.get("metrics") or {}).get("n_selected", 0)),
        "n_records_used_for_poc": int(len(records)),
        "avg_composite_score": round(float(avg_composite), 4),
        "action_counts": dict(action_counts),
        "engine_generated_utc": str(engine_payload.get("generated_utc") or ""),
        "engine_scope": engine_payload.get("scope", {}),
    }

    scenarios = default_scenarios()
    for scenario in scenarios:
        scenario["projections"] = expected_pipeline_metrics(records, scenario, horizons)

    generated_utc = now_utc_iso()
    tag = now_tag()

    scope = {
        "top_n": int(len(records)),
        "horizons_days": [int(h) for h in horizons],
    }

    evidence_paths = [
        str(ENGINE_LATEST_JSON),
        str(ENGINE_HEARTBEAT_JSON),
        str(ROOT / "code" / "ops" / "run_healthcare_grants_engine.py"),
        str(ROOT / "code" / "ops" / "run_healthcare_grants_poc_forecast.py"),
    ]

    payload = {
        "schema": "healthcare_grants_poc_forecast_v1",
        "generated_utc": generated_utc,
        "scope": scope,
        "baseline": baseline,
        "scenarios": scenarios,
        "evidence_paths": evidence_paths,
        "notes": {
            "warning": "Forecasts are scenario-based estimates and not guaranteed outcomes.",
            "method": "expected values from action-stage submission rates, eligibility pass rate, and award probability.",
        },
    }

    csv_rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        name = str(scenario.get("name") or "scenario")
        assumptions = scenario.get("assumptions", {}) if isinstance(scenario.get("assumptions"), dict) else {}
        projections = scenario.get("projections", {}) if isinstance(scenario.get("projections"), dict) else {}
        totals = projections.get("totals", {}) if isinstance(projections.get("totals"), dict) else {}

        csv_rows.append(
            {
                "scenario": name,
                "horizon_days": "ALL",
                "n_records": totals.get("n_records"),
                "expected_submissions": totals.get("expected_submissions"),
                "expected_awards": totals.get("expected_awards"),
                "expected_award_value_usd": totals.get("expected_award_value_usd"),
                "expected_submission_cost_usd": totals.get("expected_submission_cost_usd"),
                "expected_net_value_usd": totals.get("expected_net_value_usd"),
                "eligibility_pass_rate": assumptions.get("eligibility_pass_rate"),
                "award_rate": assumptions.get("award_rate"),
                "cost_per_submission_usd": assumptions.get("cost_per_submission_usd"),
            }
        )

        by_horizon = projections.get("by_horizon", []) if isinstance(projections.get("by_horizon"), list) else []
        for row in by_horizon:
            if not isinstance(row, dict):
                continue
            csv_rows.append(
                {
                    "scenario": name,
                    "horizon_days": row.get("horizon_days"),
                    "n_records": row.get("n_records"),
                    "expected_submissions": row.get("expected_submissions"),
                    "expected_awards": row.get("expected_awards"),
                    "expected_award_value_usd": row.get("expected_award_value_usd"),
                    "expected_submission_cost_usd": row.get("expected_submission_cost_usd"),
                    "expected_net_value_usd": row.get("expected_net_value_usd"),
                    "eligibility_pass_rate": assumptions.get("eligibility_pass_rate"),
                    "award_rate": assumptions.get("award_rate"),
                    "cost_per_submission_usd": assumptions.get("cost_per_submission_usd"),
                }
            )

    report_md = build_markdown(
        generated_utc=generated_utc,
        scope=scope,
        baseline=baseline,
        scenarios=scenarios,
        evidence_paths=evidence_paths,
    )

    version_json = OUT_DIR / f"healthcare_grants_poc_forecast_{tag}.json"
    latest_json = OUT_DIR / "healthcare_grants_poc_forecast_latest.json"
    version_csv = OUT_DIR / f"healthcare_grants_poc_forecast_{tag}.csv"
    latest_csv = OUT_DIR / "healthcare_grants_poc_forecast_latest.csv"
    version_md = OUT_DIR / f"healthcare_grants_poc_forecast_{tag}.md"
    latest_md = OUT_DIR / "healthcare_grants_poc_forecast_latest.md"

    write_json(version_json, payload)
    write_json(latest_json, payload)
    write_csv(version_csv, csv_rows)
    write_csv(latest_csv, csv_rows)
    write_text(version_md, report_md)
    write_text(latest_md, report_md)

    heartbeat = {
        "generated_utc": generated_utc,
        "status": "ok",
        "reason": "poc_forecast_complete",
        "scope": scope,
        "baseline": {
            "n_scanned": baseline.get("n_scanned", 0),
            "n_scored": baseline.get("n_scored", 0),
            "n_selected": baseline.get("n_selected", 0),
            "n_records_used_for_poc": baseline.get("n_records_used_for_poc", 0),
        },
        "artifacts": {
            "json": str(version_json),
            "json_latest": str(latest_json),
            "csv": str(version_csv),
            "csv_latest": str(latest_csv),
            "markdown": str(version_md),
            "markdown_latest": str(latest_md),
        },
        "evidence_paths": evidence_paths,
    }

    heartbeat_path = OUT_DIR / "healthcare_grants_poc_forecast_heartbeat_latest.json"
    write_json(heartbeat_path, heartbeat)

    return {
        "generated_utc": generated_utc,
        "scope": scope,
        "baseline": baseline,
        "artifacts": heartbeat["artifacts"],
        "heartbeat": str(heartbeat_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build proof-of-concept and future-state scenario forecasts from healthcare grants engine outputs."
    )
    parser.add_argument("--top-n", type=int, default=40, help="Maximum number of records from engine latest output used in PoC.")
    parser.add_argument(
        "--horizons-days",
        type=str,
        default=",".join(str(x) for x in DEFAULT_HORIZONS),
        help="Comma-separated forecast horizons in days, e.g., 30,60,90",
    )
    return parser.parse_args()


def parse_horizons(raw: str) -> list[int]:
    parts = [item.strip() for item in str(raw or "").split(",") if item.strip()]
    out: list[int] = []
    for part in parts:
        try:
            days = int(float(part))
        except Exception:
            continue
        if days > 0:
            out.append(days)
    if not out:
        return list(DEFAULT_HORIZONS)
    return sorted(list(dict.fromkeys(out)))


def main() -> int:
    args = parse_args()
    result = run(
        top_n=max(int(args.top_n), 1),
        horizons=parse_horizons(args.horizons_days),
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
