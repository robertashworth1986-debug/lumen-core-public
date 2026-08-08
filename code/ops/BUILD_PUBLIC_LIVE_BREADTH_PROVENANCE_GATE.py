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
    "top_live_measured_sector": "power_grid",
}

BOUNDARY = (
    "This historical source-classification snapshot does not prove current feed "
    "availability or freshness, customer savings, revenue, trading profit, grant "
    "merit, agency acceptance, valuation, field performance, operational deployment "
    "readiness, or portal readiness. Economic estimates are intentionally omitted."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_payload() -> dict[str, Any]:
    metrics = dict(PUBLIC_SAFE_METRICS)
    return {
        "generated_utc": now_utc(),
        "schema": "public_live_breadth_provenance_gate_v2",
        "snapshot": {
            "observed_utc": "2026-06-21T07:50:23.657357+00:00",
            "status": "historical_not_current_runtime_evidence",
            "source_registry_included": False,
            "manifest_bound": False,
        },
        "purpose": (
            "Document the public-safe evidence-boundary upgrade for LumenCore "
            "live-breadth and frozen-delta reporting."
        ),
        "public_safe_metrics": metrics,
        "metric_definitions": {
            "enabled_live_sources": (
                "Sources configured as enabled in the historical first-party artifact; "
                "not proof that each source was healthy, fresh, or usable."
            ),
            "measured_live_sources": (
                "Sources marked measured by the historical first-party probe logic; "
                "not proof of dataset fitness, material row depth, independent validation, or current availability."
            ),
            "measured_coverage_pct": (
                "Historical measured-source flag count divided by enabled-source flag count."
            ),
            "promoted_live_measured_source_rows": (
                "Rows historically classified for the measured bucket; no longer promoted as economic or performance evidence."
            ),
            "context_only_source_rows": "Rows retained only as historical research context.",
        },
        "evidence_buckets": [
            {
                "bucket": "live_measured_delta_rows",
                "public_use": "Historical first-party source-classification evidence only.",
                "boundary": (
                    "A successful or measured flag does not establish freshness, row depth, relevance, "
                    "data rights, dataset fitness, customer savings, field performance, or trading profit."
                ),
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
            "economic_estimates_included": False,
            "interpretation": (
                "This artifact reports historical source coverage and provenance buckets only. "
                "It does not convert source breadth into economic, performance, or current-runtime claims."
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
            "Use this capsule as historical claim-quality control showing how LumenCore separated "
            "first-party source flags from context-only rows. Do not use it as current live-breadth, "
            "dataset-fitness, performance, or economic evidence."
        ),
        "boundary": BOUNDARY,
        "claim_gate": {
            "ready_for_portal_upload": False,
            "ready_for_submit": False,
            "grant_merit_proven": False,
            "field_performance_proven": False,
            "trading_profit_proven": False,
            "current_runtime_state_proven": False,
            "economic_value_claim_allowed": False,
            "performance_claim_allowed": False,
            "probe_success_is_dataset_fitness": False,
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
        f"Snapshot observed UTC: {payload['snapshot']['observed_utc']}",
        f"Snapshot status: `{payload['snapshot']['status']}`",
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
        f"| Top live-measured sector | {metrics['top_live_measured_sector']} |",
        "",
        "## Metric Definitions",
        "",
        f"- Enabled live sources: {payload['metric_definitions']['enabled_live_sources']}",
        f"- Measured live sources: {payload['metric_definitions']['measured_live_sources']}",
        f"- Measured coverage: {payload['metric_definitions']['measured_coverage_pct']}",
        f"- Promoted rows: {payload['metric_definitions']['promoted_live_measured_source_rows']}",
        f"- Context-only rows: {payload['metric_definitions']['context_only_source_rows']}",
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
            f"- Economic estimates included: `{str(truth['economic_estimates_included']).lower()}`",
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
            f"- current_runtime_state_proven: `{str(gate['current_runtime_state_proven']).lower()}`",
            f"- economic_value_claim_allowed: `{str(gate['economic_value_claim_allowed']).lower()}`",
            f"- performance_claim_allowed: `{str(gate['performance_claim_allowed']).lower()}`",
            f"- probe_success_is_dataset_fitness: `{str(gate['probe_success_is_dataset_fitness']).lower()}`",
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
                "snapshot_status": payload["snapshot"]["status"],
                "economic_estimates_included": payload["truth_chain_interpretation"][
                    "economic_estimates_included"
                ],
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
