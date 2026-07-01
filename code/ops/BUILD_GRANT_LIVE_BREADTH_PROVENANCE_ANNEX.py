from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "ops"
GRANTS = ROOT / "grant_submissions"

LIVE_PANEL = OUT / "live_breadth_value_panel_latest.json"
MULTI_ASSET_PACK = OUT / "multi_asset_frozen_delta_pack_latest.json"
TRUTH_CHAIN = OUT / "frozen_delta_truth_chain" / "frozen_delta_truth_chain_latest.json"
DICE_EVIDENCE = OUT / "grant_evidence_packs" / "DICE_HR001126S0010" / "EVIDENCE_latest.json"
HARBOR_EVIDENCE = OUT / "grant_evidence_packs" / "NV063_HarborSentinel" / "EVIDENCE_latest.json"

OUT_JSON = OUT / "grant_live_breadth_provenance_annex_latest.json"
OUT_MD = GRANTS / "LIVE_BREADTH_PROVENANCE_ANNEX_2026-06-21.md"

SENSITIVE_PATTERNS = [
    re.compile(r"\bUEI\s+[A-Z0-9]{8,16}\b", re.IGNORECASE),
    re.compile(r"\bCAGE/NCAGE\s+[A-Z0-9]{3,10}\b", re.IGNORECASE),
    re.compile(r"\bCAGE\s+[A-Z0-9]{3,10}\b", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
]


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


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except Exception:
        return path.as_posix()


def money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def sanitize(text: str) -> str:
    clean = text
    for pattern in SENSITIVE_PATTERNS:
        clean = pattern.sub("[REDACTED]", clean)
    return clean


def evidence_pack_summary(path: Path) -> dict[str, Any]:
    doc = read_json(path)
    freshness = doc.get("freshness", {}) if isinstance(doc.get("freshness"), dict) else {}
    delta_summary = doc.get("delta_summary", {}) if isinstance(doc.get("delta_summary"), dict) else {}
    return {
        "path": rel(path),
        "exists": path.exists(),
        "freshness_state": freshness.get("state", "missing" if not path.exists() else "unknown"),
        "headline_source_mode": freshness.get("headline_source_mode", ""),
        "primary_evidence_mode": delta_summary.get("primary_evidence_mode", ""),
        "live_measured_hourly_value_usd": float(delta_summary.get("total_hourly_value_usd") or 0.0),
        "context_only_lane_count": int(delta_summary.get("context_only_lane_count") or 0),
        "rows_total": int(delta_summary.get("rows_total") or 0),
        "claim_boundary": str(delta_summary.get("claim_boundary") or ""),
        "freshness_notes": list(freshness.get("notes", []) or []),
    }


def build_annex() -> dict[str, Any]:
    panel = read_json(LIVE_PANEL)
    panel_headline = panel.get("headline", {}) if isinstance(panel.get("headline"), dict) else {}
    pack = read_json(MULTI_ASSET_PACK)
    pack_headline = pack.get("headline", {}) if isinstance(pack.get("headline"), dict) else {}
    truth = read_json(TRUTH_CHAIN)
    truth_metrics = truth.get("metrics", {}) if isinstance(truth.get("metrics"), dict) else {}

    live_measured_hourly = float(panel_headline.get("live_measured_estimated_hourly_value_usd") or 0.0)
    live_measured_annual = float(panel_headline.get("live_measured_estimated_annual_value_usd") or 0.0)
    context_only_hourly = float(panel_headline.get("context_only_estimated_hourly_value_usd") or 0.0)
    context_only_annual = float(panel_headline.get("context_only_estimated_annual_value_usd") or 0.0)

    return {
        "schema": "grant_live_breadth_provenance_annex_v1",
        "generated_utc": now_utc(),
        "sources": {
            "live_breadth_value_panel": rel(LIVE_PANEL),
            "multi_asset_frozen_delta_pack": rel(MULTI_ASSET_PACK),
            "frozen_delta_truth_chain": rel(TRUTH_CHAIN),
            "dice_evidence_pack": rel(DICE_EVIDENCE),
            "harbor_evidence_pack": rel(HARBOR_EVIDENCE),
        },
        "live_breadth_state": {
            "panel_generated_utc": panel.get("generated_utc", ""),
            "primary_evidence_mode": str(panel_headline.get("primary_evidence_mode") or ""),
            "enabled_sources": int(panel_headline.get("enabled_sources") or 0),
            "measured_sources": int(panel_headline.get("measured_sources") or 0),
            "measured_coverage_pct": float(panel_headline.get("measured_coverage_pct") or 0.0),
            "live_measured_source_row_count": int(panel_headline.get("live_measured_source_row_count") or 0),
            "unmeasured_source_row_count": int(panel_headline.get("unmeasured_source_row_count") or 0),
            "reference_fallback_used": bool(panel_headline.get("reference_fallback_used", False)),
            "live_measured_hourly_value_usd": live_measured_hourly,
            "live_measured_annual_value_usd": live_measured_annual,
            "context_only_hourly_value_usd": context_only_hourly,
            "context_only_annual_value_usd": context_only_annual,
            "top_live_measured_sector": str(panel_headline.get("top_live_measured_sector") or ""),
            "top_live_measured_sector_hourly_value_usd": float(
                panel_headline.get("top_live_measured_sector_hourly_value_usd") or 0.0
            ),
            "claim_boundary": str(panel_headline.get("claim_boundary") or ""),
        },
        "multi_asset_pack_state": {
            "primary_evidence_mode": str(pack_headline.get("primary_evidence_mode") or ""),
            "live_measured_lane_count": int(pack_headline.get("live_measured_lane_count") or 0),
            "context_only_lane_count": int(pack_headline.get("context_only_lane_count") or 0),
            "live_measured_ten_k_plus_lane_count": int(pack_headline.get("live_measured_ten_k_plus_lane_count") or 0),
            "live_measured_hourly_value_usd": float(pack_headline.get("live_measured_hourly_value_usd") or 0.0),
            "live_measured_annual_value_usd": float(pack_headline.get("live_measured_annual_value_usd") or 0.0),
        },
        "truth_chain_state": {
            "run_tag": truth.get("run_tag", ""),
            "entry_sha256": truth.get("entry_sha256", ""),
            "annual_value_signal_usd": float(truth_metrics.get("annual_value_signal_usd") or 0.0),
            "promoted_live_measured_annual_value_usd": float(
                truth_metrics.get("promoted_live_measured_annual_value_usd") or 0.0
            ),
            "context_total_annual_value_usd": float(truth_metrics.get("context_total_annual_value_usd") or 0.0),
            "context_only_annual_value_usd": float(truth_metrics.get("context_only_annual_value_usd") or 0.0),
            "primary_evidence_mode": str(truth_metrics.get("primary_evidence_mode") or ""),
        },
        "package_evidence_packs": {
            "DICE_HR001126S0010": evidence_pack_summary(DICE_EVIDENCE),
            "NV063_HarborSentinel": evidence_pack_summary(HARBOR_EVIDENCE),
        },
        "reviewer_use": {
            "synthetic_control_role": (
                "Synthetic and controlled-injection lanes provide labels, adversary knobs, and repeatable ablations."
            ),
            "live_breadth_role": (
                "Live breadth provides measured source coverage, frozen time-series replay realism, and chain-of-custody "
                "evidence after controlled tests. It is not native ground truth for DICE or HarborSentinel."
            ),
            "money_printer_boundary": (
                "The economic signal is a prioritization and preserved-value hypothesis. It is not customer savings, "
                "trading profit, revenue, grant merit, field performance, or valuation proof."
            ),
            "grant_language": (
                "Use the promoted live-measured values only as evidence that the measurement system can ingest, separate, "
                "hash, and report live evidence with context-only estimates fenced off."
            ),
        },
        "claim_gate": {
            "ready_for_portal_upload": False,
            "ready_for_submit": False,
            "grant_merit_proven": False,
            "field_performance_proven": False,
            "trading_profit_proven": False,
            "context_only_promoted_as_live_proof": False,
            "boundary": (
                "Only live-measured rows are promoted as live-breadth evidence. Synthetic controls, reference rows, "
                "context-only estimates, and valuation proxies remain support material and must not be stated as proof."
            ),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    live = payload["live_breadth_state"]
    pack = payload["multi_asset_pack_state"]
    truth = payload["truth_chain_state"]
    gates = payload["claim_gate"]
    reviewer = payload["reviewer_use"]
    packages = payload["package_evidence_packs"]

    lines = [
        "# Live-Breadth Provenance Annex",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Reviewer-Safe Summary",
        "",
        (
            "This annex separates promoted live-measured evidence from context-only "
            "estimates so DICE and HarborSentinel packets can use live breadth without "
            "overclaiming field performance, grant merit, revenue, or trading profit."
        ),
        "",
        "## Promoted Live-Measured Surface",
        "",
        f"- Primary evidence mode: `{live['primary_evidence_mode']}`",
        f"- Measured sources: {live['measured_sources']}/{live['enabled_sources']} ({live['measured_coverage_pct']:.2f}%)",
        f"- Live-measured source rows: {live['live_measured_source_row_count']}",
        f"- Unmeasured/context source rows: {live['unmeasured_source_row_count']}",
        f"- Reference fallback used: `{str(live['reference_fallback_used']).lower()}`",
        f"- Promoted live-measured hourly value signal: {money(live['live_measured_hourly_value_usd'])}",
        f"- Promoted live-measured annual value signal: {money(live['live_measured_annual_value_usd'])}",
        f"- Context-only hourly surface: {money(live['context_only_hourly_value_usd'])}",
        f"- Context-only annual surface: {money(live['context_only_annual_value_usd'])}",
        f"- Top live-measured sector: `{live['top_live_measured_sector']}` at {money(live['top_live_measured_sector_hourly_value_usd'])}/h",
        f"- Claim boundary: {live['claim_boundary']}",
        "",
        "## Multi-Asset Frozen Delta Pack",
        "",
        f"- Primary evidence mode: `{pack['primary_evidence_mode']}`",
        f"- Live-measured lanes: {pack['live_measured_lane_count']}",
        f"- Context-only lanes: {pack['context_only_lane_count']}",
        f"- Live-measured lanes >= $10k/h: {pack['live_measured_ten_k_plus_lane_count']}",
        f"- Live-measured hourly value signal: {money(pack['live_measured_hourly_value_usd'])}",
        f"- Live-measured annual value signal: {money(pack['live_measured_annual_value_usd'])}",
        "",
        "## Truth Chain Anchor",
        "",
        f"- Run tag: `{truth['run_tag']}`",
        f"- Entry SHA-256: `{truth['entry_sha256']}`",
        f"- Annual value signal promoted in truth chain: {money(truth['annual_value_signal_usd'])}",
        f"- Context-total annual value retained as context: {money(truth['context_total_annual_value_usd'])}",
        f"- Context-only annual value retained as context: {money(truth['context_only_annual_value_usd'])}",
        f"- Primary evidence mode: `{truth['primary_evidence_mode']}`",
        "",
        "## Grant Packet Use",
        "",
    ]
    for name, summary in packages.items():
        lines.extend(
            [
                f"### {name}",
                "",
                f"- Evidence pack: `{summary['path']}`",
                f"- Freshness: `{summary['freshness_state']}`",
                f"- Headline source mode: `{summary['headline_source_mode']}`",
                f"- Primary evidence mode: `{summary['primary_evidence_mode']}`",
                f"- Live-measured hourly value signal cited by pack: {money(summary['live_measured_hourly_value_usd'])}",
                f"- Context-only lane count: {summary['context_only_lane_count']}",
                f"- Rows promoted: {summary['rows_total']}",
                f"- Claim boundary: {summary['claim_boundary']}",
                "",
            ]
        )
        if summary["freshness_notes"]:
            lines.append("Freshness notes:")
            lines.extend(f"- {note}" for note in summary["freshness_notes"])
            lines.append("")

    lines.extend(
        [
            "## Reviewer Use",
            "",
            f"- Synthetic control role: {reviewer['synthetic_control_role']}",
            f"- Live breadth role: {reviewer['live_breadth_role']}",
            f"- Economic boundary: {reviewer['money_printer_boundary']}",
            f"- Grant language: {reviewer['grant_language']}",
            "",
            "## Claim Gate",
            "",
            f"- ready_for_portal_upload: `{str(gates['ready_for_portal_upload']).lower()}`",
            f"- ready_for_submit: `{str(gates['ready_for_submit']).lower()}`",
            f"- grant_merit_proven: `{str(gates['grant_merit_proven']).lower()}`",
            f"- field_performance_proven: `{str(gates['field_performance_proven']).lower()}`",
            f"- trading_profit_proven: `{str(gates['trading_profit_proven']).lower()}`",
            f"- context_only_promoted_as_live_proof: `{str(gates['context_only_promoted_as_live_proof']).lower()}`",
            f"- boundary: {gates['boundary']}",
            "",
        ]
    )
    return sanitize("\n".join(lines))


def write_annex(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or build_annex()
    OUT.mkdir(parents=True, exist_ok=True)
    GRANTS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    return payload


def main() -> int:
    payload = write_annex()
    live = payload["live_breadth_state"]
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "primary_evidence_mode": live["primary_evidence_mode"],
                "measured_sources": live["measured_sources"],
                "enabled_sources": live["enabled_sources"],
                "live_measured_hourly_value_usd": live["live_measured_hourly_value_usd"],
                "live_measured_annual_value_usd": live["live_measured_annual_value_usd"],
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
