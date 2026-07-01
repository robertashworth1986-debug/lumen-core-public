from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "ops"
GRANTS = ROOT / "grant_submissions"

LIVE_SOURCES = ROOT / "config" / "live_sources.json"
APPROVED_OPEN = ROOT / "config" / "approved_open_access_sources.json"
LIVE_BREADTH_PANEL = OUT / "live_breadth_value_panel_latest.json"
MULTI_ASSET_PACK = OUT / "multi_asset_frozen_delta_pack_latest.json"
KRAKEN_ALPHA_MAP = OUT / "kraken_multi_tf_alpha_map_latest.json"
DICE_SYNTHESIS = OUT / "dice_evidence_synthesis_latest.json"

OUT_JSON = OUT / "live_breadth_replay_bridge_latest.json"
OUT_MD = GRANTS / "LIVE_BREADTH_REPLAY_BRIDGE_2026-06-20.md"

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\bUEI\s+[A-Z0-9]{8,16}\b", re.IGNORECASE),
    re.compile(r"\bCAGE/NCAGE\s+[A-Z0-9]{3,10}\b", re.IGNORECASE),
    re.compile(r"\bCAGE\s+[A-Z0-9]{3,10}\b", re.IGNORECASE),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def scrub(text: str) -> str:
    clean = text
    for pattern in SECRET_PATTERNS:
        clean = pattern.sub("[REDACTED]", clean)
    return clean


def provider_rollup(live_sources: dict[str, Any]) -> dict[str, Any]:
    providers = live_sources.get("providers", {}) if isinstance(live_sources, dict) else {}
    if not isinstance(providers, dict):
        providers = {}
    rows: list[dict[str, Any]] = []
    for name, row in providers.items():
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "provider": str(name),
                "sector": str(row.get("sector") or ""),
                "status": str(row.get("status") or ""),
                "probe_ok": bool(row.get("probe_ok")),
                "measured": bool(row.get("measured")),
                "rows": int(row.get("rows") or 0),
                "matched_file_count": len(row.get("matched_files") or []),
                "last_truth_sync_utc": str(row.get("last_truth_sync_utc") or ""),
            }
        )
    rows.sort(key=lambda item: (item["measured"], item["rows"]), reverse=True)
    return {
        "provider_count": len(rows),
        "live_key_present_count": sum(1 for row in rows if row["status"] == "LIVE_KEY_PRESENT"),
        "probe_ok_count": sum(1 for row in rows if row["probe_ok"]),
        "measured_count": sum(1 for row in rows if row["measured"]),
        "total_rows_reported": sum(int(row["rows"]) for row in rows),
        "providers": rows,
    }


def source_count_by_sector(approved_open: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    sources = approved_open.get("sources", []) if isinstance(approved_open, dict) else []
    for row in sources:
        if not isinstance(row, dict):
            continue
        sector = str(row.get("sector") or "unknown")
        counts[sector] = counts.get(sector, 0) + 1
    return dict(sorted(counts.items()))


def artifact_state(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "path": rel(path),
        "exists": exists,
        "bytes": path.stat().st_size if exists else 0,
        "last_write_utc": (
            datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
            if exists
            else ""
        ),
    }


def build_bridge() -> dict[str, Any]:
    live_sources = read_json(LIVE_SOURCES, {})
    approved_open = read_json(APPROVED_OPEN, {})
    panel = read_json(LIVE_BREADTH_PANEL, {})
    multi_asset = read_json(MULTI_ASSET_PACK, {})
    kraken_alpha = read_json(KRAKEN_ALPHA_MAP, {})
    dice = read_json(DICE_SYNTHESIS, {})

    rollup = provider_rollup(live_sources if isinstance(live_sources, dict) else {})
    approved_sector_counts = source_count_by_sector(approved_open if isinstance(approved_open, dict) else {})
    panel_headline = panel.get("headline", {}) if isinstance(panel, dict) else {}
    multi_headline = multi_asset.get("headline", {}) if isinstance(multi_asset, dict) else {}

    grant_lanes = [
        {
            "grant_lane": "DICE",
            "best_use_of_live_breadth": "primary_frozen_live_replay_with_synthetic_controls",
            "candidate_live_sources": ["KRAKEN", "EIA", "NREL", "FRED", "BEA", "USGS_WATER", "NOAA_NCEI"],
            "why_synthetic_still_matters": (
                "Synthetic is a secondary control lane only. DICE still needs known task intent, role labels, "
                "adversary knobs, and controlled ablations, while live breadth supplies the primary realism signal."
            ),
            "next_replay_adapter": (
                "Convert live time-series windows into timestamped task graphs, role constraints, "
                "stale-data injections, and recovery events; run centralized, peer, contract, and hybrid baselines."
            ),
            "claim_status": "live_data_not_direct_DICE_proof",
        },
        {
            "grant_lane": "HarborSentinel",
            "best_use_of_live_breadth": "representative_public_signal_replay",
            "candidate_live_sources": ["public AIS artifacts", "NOAA_NCEI", "NOAA_TIDES", "USGS_WATER"],
            "why_synthetic_still_matters": (
                "Controlled injections create labels. Public live feeds add realism but cannot substitute for Navy field data."
            ),
            "next_replay_adapter": "Freeze AIS/weather windows, inject labeled anomalies, hold out time blocks, and report false-positive boundaries.",
            "claim_status": "public_replay_evidence_not_field_validation",
        },
        {
            "grant_lane": "NSF / MissionWeave / cross-sector autonomy",
            "best_use_of_live_breadth": "multi-sector_replay_and_ablation",
            "candidate_live_sources": ["EIA", "NREL", "FRED", "BEA", "BLS", "USGS_WATER", "NASA"],
            "why_synthetic_still_matters": (
                "Synthetic control is retained for causal isolation and negative controls; live replay is the promoted evidence lane."
            ),
            "next_replay_adapter": "Run identical model families across frozen windows with leakage checks, walk-forward splits, and abstention metrics.",
            "claim_status": "replay_ready_after_manifest_and_baseline_gate",
        },
        {
            "grant_lane": "Trader / Kraken execution",
            "best_use_of_live_breadth": "shadow_forward_and_walk_forward_only",
            "candidate_live_sources": ["KRAKEN", "ALPACA", "POLYGON", "TWELVE_DATA", "FINNHUB"],
            "why_synthetic_still_matters": (
                "Synthetic market stress tests stay as guardrail/kill-switch controls; live and forward-shadow data decide credibility."
            ),
            "next_replay_adapter": "Keep live orders off; freeze signals before outcomes; score walk-forward net of fees, spread, slippage, and guard failures.",
            "claim_status": "not_grant_merit_and_not_live_profit_proof",
        },
    ]

    payload = {
        "schema": "live_breadth_replay_bridge_v1",
        "generated_utc": now_utc(),
        "core_answer": (
            "Use live breadth as the promoted evidence lane. Synthetic deltas stay only as "
            "bounded controls for labels, ablations, and failure injection."
        ),
        "live_breadth_rollup": rollup,
        "approved_open_source_sector_counts": approved_sector_counts,
        "existing_artifacts": {
            "live_sources": artifact_state(LIVE_SOURCES),
            "approved_open_access_sources": artifact_state(APPROVED_OPEN),
            "live_breadth_value_panel": artifact_state(LIVE_BREADTH_PANEL),
            "multi_asset_frozen_delta_pack": artifact_state(MULTI_ASSET_PACK),
            "kraken_multi_tf_alpha_map": artifact_state(KRAKEN_ALPHA_MAP),
            "dice_evidence_synthesis": artifact_state(DICE_SYNTHESIS),
        },
        "current_measured_context": {
            "panel_measured_sources": panel_headline.get("measured_sources"),
            "panel_enabled_sources": panel_headline.get("enabled_sources"),
            "panel_live_sector_count": panel_headline.get("live_sector_count"),
            "multi_asset_lane_count": multi_headline.get("lane_count"),
            "multi_asset_live_measured_lane_count": multi_headline.get("live_measured_lane_count"),
            "multi_asset_context_only_lane_count": multi_headline.get("context_only_lane_count"),
            "multi_asset_ten_k_plus_lane_count": multi_headline.get(
                "live_measured_ten_k_plus_lane_count",
                multi_headline.get("ten_k_plus_lane_count"),
            ),
            "multi_asset_live_measured_hourly_value_usd": multi_headline.get("live_measured_hourly_value_usd"),
            "multi_asset_live_measured_annual_value_usd": multi_headline.get("live_measured_annual_value_usd"),
            "multi_asset_context_only_hourly_value_usd": multi_headline.get("context_only_hourly_value_usd"),
            "kraken_pairs_analyzed": kraken_alpha.get("pairs_analyzed") if isinstance(kraken_alpha, dict) else None,
            "kraken_pairs_after_liquidity_filter": kraken_alpha.get("pairs_after_liquidity_filter") if isinstance(kraken_alpha, dict) else None,
        },
        "evidence_ladder": [
            "live_source_manifest_and_hash",
            "frozen_live_replay_claim_specific_adapter",
            "synthetic_control_known_labels",
            "frozen_live_replay_hash_manifested",
            "walk_forward_or_holdout_baselines",
            "forward_shadow_decision_before_outcome",
            "partner_or_field_validation",
        ],
        "grant_lanes": grant_lanes,
        "claim_gate": {
            "ready_for_portal_upload": False,
            "ready_for_submit": False,
            "live_data_proves_grant_merit": False,
            "live_data_proves_trading_profit": False,
            "synthetic_primary_evidence": False,
            "promoted_evidence_policy": (
                "Do not promote synthetic/control deltas above live-measured source rows, "
                "frozen live replay, or forward-shadow decisions."
            ),
            "boundary": (
                "Live breadth can support realism and replay coverage only after manifests, "
                "baselines, leakage controls, and claim-specific labels are present."
            ),
        },
    }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    rollup = payload["live_breadth_rollup"]
    context = payload["current_measured_context"]
    lines = [
        "# Live Breadth Replay Bridge",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Core Answer",
        "",
        payload["core_answer"],
        "",
        "## Why Synthetic Controls Still Exist",
        "",
        "- Live breadth is the promoted evidence lane for source realism, sector transfer, drift, missing data, and operational mess.",
        "- Synthetic runs stay as controls for labels, controlled adversary knobs, and repeatable ablations.",
        "- Reviewer-grade proof should move in this order: live source manifest, frozen live replay, synthetic controls, forward shadow, partner/field validation.",
        "",
        "## Live Breadth State",
        "",
        f"- Providers indexed: {rollup['provider_count']}",
        f"- Live-key-present providers: {rollup['live_key_present_count']}",
        f"- Probe-ok providers: {rollup['probe_ok_count']}",
        f"- Measured providers: {rollup['measured_count']}",
        f"- Total rows reported by registry: {rollup['total_rows_reported']}",
        f"- Panel measured sources: {context.get('panel_measured_sources')}",
        f"- Panel enabled sources: {context.get('panel_enabled_sources')}",
        f"- Multi-asset live-measured lanes: {context.get('multi_asset_live_measured_lane_count')}",
        f"- Multi-asset context-only lanes: {context.get('multi_asset_context_only_lane_count')}",
        f"- Multi-asset live-measured annual signal: {context.get('multi_asset_live_measured_annual_value_usd')}",
        f"- Kraken pairs analyzed: {context.get('kraken_pairs_analyzed')}",
        "",
        "## Evidence Ladder",
        "",
    ]
    lines.extend(f"{idx}. {item}" for idx, item in enumerate(payload["evidence_ladder"], start=1))
    lines.extend(
        [
            "",
            "## Grant Lane Mapping",
            "",
            "| Lane | Best use | Claim status | Next replay adapter |",
            "|---|---|---|---|",
        ]
    )
    for lane in payload["grant_lanes"]:
        lines.append(
            f"| {lane['grant_lane']} | {lane['best_use_of_live_breadth']} | "
            f"{lane['claim_status']} | {lane['next_replay_adapter']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Gate",
            "",
            "- ready_for_portal_upload: false",
            "- ready_for_submit: false",
            "- live_data_proves_grant_merit: false",
            "- live_data_proves_trading_profit: false",
            "- synthetic_primary_evidence: false",
            f"- promoted_evidence_policy: {payload['claim_gate']['promoted_evidence_policy']}",
            f"- boundary: {payload['claim_gate']['boundary']}",
            "",
        ]
    )
    return scrub("\n".join(lines))


def write_bridge(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or build_bridge()
    OUT.mkdir(parents=True, exist_ok=True)
    GRANTS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    return payload


def main() -> int:
    payload = write_bridge()
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "providers": payload["live_breadth_rollup"]["provider_count"],
                "measured": payload["live_breadth_rollup"]["measured_count"],
                "wrote_json": rel(OUT_JSON),
                "wrote_md": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
