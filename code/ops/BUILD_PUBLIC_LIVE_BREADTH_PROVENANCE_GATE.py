from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
OUT_OPS = ROOT / "out" / "ops"

OUT_MD = DOCS / "LIVE_BREADTH_PROVENANCE_GATE_CAPSULE_2026-06-21.md"
DASHBOARD_JSON = DASHBOARD_DATA / "live_breadth_provenance_gate.json"
OUT_JSON = OUT_OPS / "public_live_breadth_provenance_gate_latest.json"


PUBLIC_SAFE_METRICS = {
    "enabled_live_sources": 17,
    "measured_live_sources": 12,
    "measured_coverage_pct": 70.59,
    "promoted_live_measured_source_rows": 11,
    "context_only_source_rows": 8,
    "reference_fallback_used": False,
    "promoted_live_measured_hourly_value_signal_usd": 8435.0,
    "promoted_live_measured_annual_value_signal_usd": 73890600.0,
    "context_only_annual_surface_usd": 52257442740.0,
    "top_live_measured_sector": "power_grid",
    "top_live_measured_sector_hourly_value_usd": 5562.5,
    "truth_chain_promoted_annual_value_signal_usd": 73890600.0,
}

BOUNDARY = (
    "This public-safe capsule does not prove actual customer savings, revenue, "
    "trading profit, grant merit, agency acceptance, valuation, field performance, "
    "operational deployment readiness, or portal readiness. Dollar figures are "
    "value-signal estimates from a provenance-gated measurement layer, not "
    "realized savings, not revenue, not an investment claim, and not a guarantee."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def money(value: Any, digits: int = 0) -> str:
    try:
        return f"${float(value):,.{digits}f}"
    except Exception:
        return "$0"


def build_payload() -> dict[str, Any]:
    metrics = dict(PUBLIC_SAFE_METRICS)
    return {
        "generated_utc": now_utc(),
        "schema": "public_live_breadth_provenance_gate_v1",
        "purpose": (
            "Document the public-safe evidence-boundary upgrade for LumenCore "
            "live-breadth and frozen-delta reporting."
        ),
        "public_safe_metrics": metrics,
        "evidence_buckets": [
            {
                "bucket": "live_measured_delta_rows",
                "public_use": "Promoted live-breadth evidence.",
                "boundary": "Still not proof of customer savings, grant merit, field performance, or trading profit.",
            },
            {
                "bucket": "unmeasured_frozen_delta_rows",
                "public_use": "Context-only until source measurement is proven.",
                "boundary": "May remain visible for research prioritization but cannot inflate headline evidence.",
            },
            {
                "bucket": "reference_fallback_only",
                "public_use": "Calibration/context only.",
                "boundary": "Not live evidence and not a substitute for measured source rows.",
            },
        ],
        "truth_chain_interpretation": {
            "promoted_annual_value_signal_usd": metrics["truth_chain_promoted_annual_value_signal_usd"],
            "context_only_annual_surface_usd": metrics["context_only_annual_surface_usd"],
            "interpretation": (
                "The public annual value signal should be read as the promoted live-measured "
                "measurement surface only. The larger context-only surface is retained for "
                "research prioritization and must not be described as live proof."
            ),
        },
        "grant_packet_use": {
            "dice": (
                "Useful as proof of measurement discipline and replay realism after synthetic controls; "
                "not native DICE ground truth or DICE metric attainment."
            ),
            "harbor_sentinel": (
                "Useful as cross-stack provenance discipline; HarborSentinel merit still rests on "
                "bounded public AIS evidence, controlled injections, review-burden profile, and future authorized lanes."
            ),
        },
        "reviewer_use": (
            "Use this capsule as public evidence-quality control showing that LumenCore separates "
            "live-measured evidence from context-only evidence before using frozen deltas in public "
            "or grant-facing materials."
        ),
        "boundary": BOUNDARY,
        "claim_gate": {
            "ready_for_portal_upload": False,
            "ready_for_submit": False,
            "grant_merit_proven": False,
            "field_performance_proven": False,
            "trading_profit_proven": False,
            "context_only_promoted_as_live_proof": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    metrics = payload["public_safe_metrics"]
    truth = payload["truth_chain_interpretation"]
    gate = payload["claim_gate"]

    lines = [
        "# Live-Breadth Provenance Gate Capsule",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        "## Purpose",
        "",
        payload["purpose"],
        "",
        (
            "The useful change is simple: only rows tied to measured live sources are "
            "promoted as live-breadth evidence. Unmeasured frozen deltas, reference "
            "fallback rows, synthetic controls, and exploratory context stay visible, "
            "but they are not allowed to inflate the headline evidence layer."
        ),
        "",
        "## Public-Safe Snapshot",
        "",
        "| Field | Value |",
        "|---|---:|",
        f"| Enabled live sources | {metrics['enabled_live_sources']} |",
        f"| Measured live sources | {metrics['measured_live_sources']} |",
        f"| Measured coverage | {metrics['measured_coverage_pct']:.2f}% |",
        f"| Promoted live-measured source rows | {metrics['promoted_live_measured_source_rows']} |",
        f"| Context-only source rows | {metrics['context_only_source_rows']} |",
        f"| Reference fallback used | {str(metrics['reference_fallback_used']).lower()} |",
        f"| Promoted live-measured hourly value signal | {money(metrics['promoted_live_measured_hourly_value_signal_usd'])} |",
        f"| Promoted live-measured annual value signal | {money(metrics['promoted_live_measured_annual_value_signal_usd'])} |",
        f"| Context-only annual surface | {money(metrics['context_only_annual_surface_usd'])} |",
        f"| Top live-measured sector | {metrics['top_live_measured_sector']} |",
        f"| Top live-measured sector hourly value signal | {money(metrics['top_live_measured_sector_hourly_value_usd'])} |",
        "",
        "## Evidence Buckets",
        "",
    ]
    for row in payload["evidence_buckets"]:
        lines.extend(
            [
                f"### `{row['bucket']}`",
                "",
                f"- Public use: {row['public_use']}",
                f"- Boundary: {row['boundary']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Truth-Chain Interpretation",
            "",
            f"- Promoted annual value signal: {money(truth['promoted_annual_value_signal_usd'])}",
            f"- Context-only annual surface retained as context: {money(truth['context_only_annual_surface_usd'])}",
            f"- Interpretation: {truth['interpretation']}",
            "",
            "## Grant Packet Use",
            "",
            f"- DICE: {payload['grant_packet_use']['dice']}",
            f"- HarborSentinel: {payload['grant_packet_use']['harbor_sentinel']}",
            "",
            "## Boundary",
            "",
            payload["boundary"],
            "",
            "## Reviewer Use",
            "",
            payload["reviewer_use"],
            "",
            "## Claim Gate",
            "",
            f"- ready_for_portal_upload: `{str(gate['ready_for_portal_upload']).lower()}`",
            f"- ready_for_submit: `{str(gate['ready_for_submit']).lower()}`",
            f"- grant_merit_proven: `{str(gate['grant_merit_proven']).lower()}`",
            f"- field_performance_proven: `{str(gate['field_performance_proven']).lower()}`",
            f"- trading_profit_proven: `{str(gate['trading_profit_proven']).lower()}`",
            f"- context_only_promoted_as_live_proof: `{str(gate['context_only_promoted_as_live_proof']).lower()}`",
        ]
    )
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def write_payload(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    return payload


def main() -> int:
    payload = write_payload()
    metrics = payload["public_safe_metrics"]
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "measured_sources": metrics["measured_live_sources"],
                "enabled_sources": metrics["enabled_live_sources"],
                "promoted_annual_value_signal_usd": metrics[
                    "promoted_live_measured_annual_value_signal_usd"
                ],
                "context_only_annual_surface_usd": metrics["context_only_annual_surface_usd"],
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
