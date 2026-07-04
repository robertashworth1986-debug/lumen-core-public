from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DATA = ROOT / "dashboard" / "data"
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"

HOLDOUT_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"
PHASE_PROXY_JSON = DASHBOARD_DATA / "champion_phase_proxy_diagnostics.json"
BASELINE_GAUNTLET_JSON = DASHBOARD_DATA / "baseline_gauntlet_coverage.json"

OUT_JSON = OUT_OPS / "kuramoto_accepted_metric_audit_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "kuramoto_accepted_metric_audit.json"
OUT_MD = DOCS / "KURAMOTO_ACCEPTED_METRIC_AUDIT_2026-07-03.md"

BOUNDARY = (
    "Accepted Kuramoto/grid metric audit only. Order-parameter and phase-bound items are replay-data "
    "proxies derived from source-conditioned numeric holdouts; critical coupling and IEEE grid benchmark "
    "claims require an explicit topology, coupling matrix, natural-frequency model, and/or buyer-approved "
    "benchmark case. This artifact does not establish field validation, hardware PLL validation, grid safety, "
    "realized savings, certification, or trading performance."
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


def stable_sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def metric_status_rows(
    holdout_summary: dict[str, Any],
    phase_summary: dict[str, Any],
    baseline_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    holdouts = int(holdout_summary.get("holdout_count") or 0)
    wins = int(holdout_summary.get("wins_vs_kalman") or 0)
    non_degenerate = int(phase_summary.get("non_degenerate_numeric_holdout_count") or 0)
    usable = int(phase_summary.get("usable_numeric_holdout_count") or 0)
    executed_baselines = int(baseline_summary.get("executed_in_locked_replay") or 0)

    return [
        {
            "metric_id": "kuramoto_order_parameter_proxy",
            "accepted_metric_name": "Kuramoto order parameter R",
            "status": "REPLAY_PROXY_READY",
            "current_measurement": {
                "mean_phase_coherence_proxy": phase_summary.get("mean_phase_coherence_proxy"),
                "usable_numeric_holdouts": usable,
                "non_degenerate_numeric_holdouts": non_degenerate,
            },
            "why_it_matters": (
                "R is the standard synchronization/coherence readout. The current replay proxy uses a "
                "mean resultant length over derived phases from numeric holdouts."
            ),
            "claim_allowed_now": (
                "Replay-data order-parameter-like coherence proxy across source-conditioned holdouts."
            ),
            "claim_not_allowed_yet": "Physical grid or PLL synchronization without accepted topology/instrument data.",
            "next_unlock": "Run the same metric on IEEE 39/118/300 cases or a buyer-approved topology.",
        },
        {
            "metric_id": "kuramoto_phase_bound_stress_proxy",
            "accepted_metric_name": "Phase-bound / phase-slip stress",
            "status": "REPLAY_PROXY_READY",
            "current_measurement": {
                "mean_circular_phase_error_proxy": phase_summary.get("mean_circular_phase_error_proxy"),
                "mean_phase_slip_proxy_rate": phase_summary.get("mean_phase_slip_proxy_rate"),
                "mean_spectral_concentration_proxy": phase_summary.get("mean_spectral_concentration_proxy"),
                "non_degenerate_numeric_holdouts": non_degenerate,
            },
            "why_it_matters": (
                "Phase-bound stress checks whether the candidate keeps derived phase movement bounded "
                "under replay noise, drift, and shock windows."
            ),
            "claim_allowed_now": "Replay-data phase-slip and circular-error proxy diagnostics.",
            "claim_not_allowed_yet": "Hardware phase-noise, RF, PLL jitter, or grid stability claims.",
            "next_unlock": "Add instrumented phase logs, PMU-like traces, RF IQ captures, or accepted grid cases.",
        },
        {
            "metric_id": "kuramoto_critical_coupling_threshold",
            "accepted_metric_name": "Critical coupling threshold Kc",
            "status": "EXTERNAL_TOPOLOGY_REQUIRED",
            "current_measurement": {
                "holdout_wins_vs_kalman": wins,
                "holdout_count": holdouts,
                "executed_named_baselines": executed_baselines,
            },
            "why_it_matters": (
                "Kc estimates how much coupling strength a network needs before synchronization emerges; "
                "it is a topology-dependent property, not a free-standing time-series score."
            ),
            "claim_allowed_now": "Ready-to-run metric request for externally supplied topology/coupling data.",
            "claim_not_allowed_yet": "A numeric Kc improvement claim for grid, RF, PLL, or facility systems.",
            "next_unlock": "Obtain IEEE bus case adapter or buyer-supplied graph, natural frequencies, and acceptance metric.",
        },
        {
            "metric_id": "ieee_grid_case_replay",
            "accepted_metric_name": "IEEE 39/118/300 bus benchmark cases",
            "status": "IMPLEMENTATION_OR_DATASET_NEEDED",
            "current_measurement": {
                "current_source_conditioned_holdouts": holdouts,
                "current_estimated_rows_replayed": holdout_summary.get("estimated_rows_replayed"),
                "baseline_gauntlet_rows": baseline_summary.get("locked_replay_estimated_rows"),
            },
            "why_it_matters": (
                "IEEE cases are accepted frozen grid topologies that make grid-sync claims easier for external "
                "reviewers to reproduce."
            ),
            "claim_allowed_now": "IEEE case adapter is a clear next validation milestone.",
            "claim_not_allowed_yet": "IEEE 39/118/300 benchmark superiority.",
            "next_unlock": "Add MATPOWER/PYPOWER/pandapower case loader and run locked replay against the same claim gates.",
        },
    ]


def build_payload() -> dict[str, Any]:
    holdout = read_json(HOLDOUT_JSON)
    phase_proxy = read_json(PHASE_PROXY_JSON)
    baseline = read_json(BASELINE_GAUNTLET_JSON)

    holdout_summary = as_dict(holdout.get("summary"))
    phase_summary = as_dict(phase_proxy.get("summary"))
    baseline_summary = as_dict(baseline.get("summary"))
    rows = metric_status_rows(holdout_summary, phase_summary, baseline_summary)

    proxy_ready = [row for row in rows if row["status"] == "REPLAY_PROXY_READY"]
    externally_blocked = [row for row in rows if row["status"] != "REPLAY_PROXY_READY"]
    summary = {
        "champion_family": holdout_summary.get("candidate") or "kuramoto_phase_coupling",
        "named_baseline": holdout_summary.get("named_baseline") or "kalman_filter",
        "holdout_count": holdout_summary.get("holdout_count"),
        "wins_vs_named_baseline": holdout_summary.get("wins_vs_kalman"),
        "mean_delta_vs_named_baseline": holdout_summary.get("mean_delta_vs_kalman"),
        "estimated_rows_replayed": holdout_summary.get("estimated_rows_replayed"),
        "source_system_count": holdout_summary.get("source_system_count"),
        "executed_named_baselines": baseline_summary.get("executed_in_locked_replay"),
        "locked_replay_comparisons": baseline_summary.get("locked_replay_baseline_comparisons"),
        "locked_replay_estimated_rows": baseline_summary.get("locked_replay_estimated_rows"),
        "proxy_metrics_ready": len(proxy_ready),
        "external_or_adapter_blocked_metrics": len(externally_blocked),
        "accepted_metric_proxy_language_allowed": len(proxy_ready) >= 2,
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "business_plan_language": (
            "LumenCore has an internal Kuramoto phase-coupling champion with accepted-metric proxy diagnostics "
            "ready for external replay discussion: order-parameter-like coherence and phase-bound stress proxies. "
            "Critical coupling and IEEE grid-case claims remain explicit next validation gates."
        ),
    }

    payload = {
        "schema": "kuramoto_accepted_metric_audit_v1",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "inputs": {
            "holdout_expansion": str(HOLDOUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "phase_proxy_diagnostics": str(PHASE_PROXY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "baseline_gauntlet": str(BASELINE_GAUNTLET_JSON.relative_to(ROOT)).replace("\\", "/"),
        },
        "summary": summary,
        "accepted_metric_rows": rows,
        "claim_controls": {
            "allowed_now": [
                "source-conditioned replay champion",
                "accepted-metric proxy language for order-parameter-like coherence",
                "accepted-metric proxy language for phase-bound stress",
                "buyer-authorized field replay request",
            ],
            "not_allowed_yet": [
                "field validation",
                "realized or guaranteed dollar savings",
                "hardware PLL/RF/grid stability certification",
                "IEEE 39/118/300 superiority",
                "critical-coupling improvement claim",
            ],
        },
    }
    payload["audit_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "accepted_metric_rows": payload["accepted_metric_rows"],
            "claim_controls": payload["claim_controls"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = as_dict(payload.get("summary"))
    lines = [
        "# Kuramoto Accepted Metric Audit",
        "",
        f"Generated UTC: `{payload.get('generated_utc')}`",
        f"Audit SHA-256: `{payload.get('audit_sha256')}`",
        "",
        "## Truth Line",
        "",
        str(summary.get("business_plan_language") or ""),
        "",
        "This is a bridge from internal replay evidence to reviewer-recognizable synchronization metrics. It is not a field-validation certificate.",
        "",
        "## Current Champion",
        "",
        f"- Champion: `{summary.get('champion_family')}`",
        f"- Named baseline: `{summary.get('named_baseline')}`",
        f"- Holdout wins: `{summary.get('wins_vs_named_baseline')}/{summary.get('holdout_count')}`",
        f"- Mean delta vs named baseline: `{summary.get('mean_delta_vs_named_baseline')}`",
        f"- Estimated rows replayed: `{summary.get('estimated_rows_replayed')}`",
        f"- Source systems: `{summary.get('source_system_count')}`",
        f"- Executed named baselines in gauntlet: `{summary.get('executed_named_baselines')}`",
        f"- Locked replay comparisons: `{summary.get('locked_replay_comparisons')}`",
        f"- Accepted metric proxy language allowed: `{str(summary.get('accepted_metric_proxy_language_allowed')).lower()}`",
        f"- Field validation claim allowed: `{str(summary.get('field_validation_claim_allowed')).lower()}`",
        "",
        "## Accepted Metric Map",
        "",
        "| Metric | Status | What We Can Say Now | What Is Still Blocked | Next Unlock |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in as_list(payload.get("accepted_metric_rows")):
        item = as_dict(row)
        lines.append(
            "| "
            f"{item.get('accepted_metric_name')} | "
            f"`{item.get('status')}` | "
            f"{item.get('claim_allowed_now')} | "
            f"{item.get('claim_not_allowed_yet')} | "
            f"{item.get('next_unlock')} |"
        )
    lines.extend(["", "## Boundary", "", str(payload.get("boundary") or "")])
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(payload).rstrip("\r\n") + "\n", encoding="utf-8")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(payload["summary"]["business_plan_language"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
