from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OPS_OUT = ROOT / "out" / "ops"

LIVE_BREADTH_PANEL = OPS_OUT / "live_breadth_value_panel_latest.json"
INFRA_FROZEN_DELTAS = ROOT / "out" / "infra_frozen_deltas.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            text = line.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\n") + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def lane_tier(hourly_value: float) -> str:
    if hourly_value >= 100_000:
        return "institutional"
    if hourly_value >= 10_000:
        return "growth"
    return "seed"


def pick_latest_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        source = str(row.get("source") or "").strip()
        sector = str(row.get("sector") or "").strip()
        constraint = str(row.get("constraint") or "").strip()
        if not source:
            continue
        key = (source, sector, constraint)
        candidate_ts = str(row.get("generated_utc") or "")
        current = latest_map.get(key)
        if current is None:
            latest_map[key] = row
            continue
        current_ts = str(current.get("generated_utc") or "")
        if candidate_ts >= current_ts:
            latest_map[key] = row
    return list(latest_map.values())


def build_top_lanes(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lanes: list[dict[str, Any]] = []
    for row in source_rows:
        source = str(row.get("source") or "").strip()
        if not source:
            continue
        estimated_hourly = as_float(row.get("estimated_hourly_value_usd"), 0.0)
        lane = {
            "evidence_source": str(row.get("evidence_source") or "live_breadth_panel_source_row").strip(),
            "provenance": str(row.get("provenance") or "").strip(),
            "primary_live_evidence": as_bool(row.get("primary_live_evidence")),
            "source": source,
            "sector": str(row.get("sector") or "").strip(),
            "constraint": str(row.get("constraint") or "").strip() or "default",
            "generated_utc": str(row.get("generated_utc") or "").strip(),
            "optimization_gain_pct": as_float(row.get("optimization_gain_pct"), 0.0),
            "baseline_loss_rate_usd_per_hour": as_float(row.get("baseline_loss_rate_usd_per_hour"), 0.0),
            "estimated_hourly_value_usd": estimated_hourly,
            "estimated_daily_value_usd": as_float(row.get("estimated_daily_value_usd"), 0.0),
            "estimated_annual_value_usd": as_float(row.get("estimated_annual_value_usd"), 0.0),
            "predicted_failure_cost_usd": as_float(row.get("predicted_failure_cost_usd"), 0.0),
            "estimated_avoided_loss_usd": as_float(row.get("estimated_avoided_loss_usd"), 0.0),
            "estimated_residual_loss_usd": as_float(row.get("estimated_residual_loss_usd"), 0.0),
            "translated_source_yearly_value_usd": as_float(row.get("translated_source_yearly_value_usd"), 0.0),
            "trust_tier": str(row.get("trust_tier") or "").strip(),
            "key_present": as_bool(row.get("key_present")),
            "enabled_source": as_bool(row.get("enabled_source")),
            "measured_source": as_bool(row.get("measured_source")),
            "premium_tier": lane_tier(estimated_hourly),
        }
        lanes.append(lane)

    lanes.sort(key=lambda x: x.get("estimated_hourly_value_usd", 0.0), reverse=True)
    return lanes


def split_lanes_by_provenance(lanes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    live_measured = [row for row in lanes if as_bool(row.get("measured_source")) and as_bool(row.get("primary_live_evidence"))]
    context_only = [row for row in lanes if row not in live_measured]
    return live_measured, context_only


def build_markdown(payload: dict[str, Any]) -> str:
    headline = payload.get("headline", {}) if isinstance(payload.get("headline"), dict) else {}
    lanes = payload.get("live_measured_top_lanes", []) if isinstance(payload.get("live_measured_top_lanes"), list) else []
    context_lanes = payload.get("context_only_lanes", []) if isinstance(payload.get("context_only_lanes"), list) else []

    lines: list[str] = []
    lines.append("# Multi Asset Frozen Delta Pack")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append("")
    lines.append("## Headline")
    lines.append(f"- Primary evidence mode: {headline.get('primary_evidence_mode', 'unknown')}")
    lines.append(f"- Live-measured annual value signal: {headline.get('live_measured_annual_value_usd', 0):,.2f} USD")
    lines.append(f"- Live-measured hourly value signal: {headline.get('live_measured_hourly_value_usd', 0):,.2f} USD")
    lines.append(f"- Live-measured lanes in pack: {headline.get('live_measured_lane_count', 0)}")
    lines.append(f"- Context-only lanes: {headline.get('context_only_lane_count', 0)}")
    lines.append(f"- Live-measured lanes with >=10k hourly value: {headline.get('live_measured_ten_k_plus_lane_count', 0)}")
    lines.append(f"- Sources enabled: {headline.get('enabled_source_count', 0)}")
    lines.append(f"- Sources measured: {headline.get('measured_source_count', 0)}")
    lines.append(f"- Boundary: {payload.get('claim_gate', {}).get('boundary', '')}")
    lines.append("")
    lines.append("## Top Live-Measured Lanes")
    lines.append("| # | Source | Sector | Hourly USD | Annual USD | Tier |")
    lines.append("|---:|---|---|---:|---:|---|")
    for idx, row in enumerate(lanes[:15], start=1):
        lines.append(
            f"| {idx} | {row.get('source', '')} | {row.get('sector', '')} | {row.get('estimated_hourly_value_usd', 0):,.2f} | {row.get('estimated_annual_value_usd', 0):,.2f} | {row.get('premium_tier', '')} |"
        )
    if not lanes:
        lines.append("| - | No live-measured lanes resolved | - | 0.00 | 0.00 | gated |")
    lines.append("")
    lines.append("## Context-Only Lanes")
    lines.append("")
    lines.append("These rows are not promoted as live evidence until the live source registry marks them measured.")
    lines.append("")
    lines.append("| # | Source | Sector | Hourly USD | Provenance |")
    lines.append("|---:|---|---|---:|---|")
    for idx, row in enumerate(context_lanes[:15], start=1):
        lines.append(
            f"| {idx} | {row.get('source', '')} | {row.get('sector', '')} | {row.get('estimated_hourly_value_usd', 0):,.2f} | {row.get('provenance', '') or row.get('evidence_source', '')} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    panel = load_json(LIVE_BREADTH_PANEL, {})
    if not isinstance(panel, dict):
        raise SystemExit(f"Invalid panel payload: {LIVE_BREADTH_PANEL}")

    panel_rows = panel.get("source_rows") if isinstance(panel.get("source_rows"), list) else []
    latest_panel_rows = pick_latest_rows([r for r in panel_rows if isinstance(r, dict)])
    top_lanes = build_top_lanes(latest_panel_rows)
    live_measured_lanes, context_only_lanes = split_lanes_by_provenance(top_lanes)

    frozen_rows = load_jsonl(INFRA_FROZEN_DELTAS)
    latest_frozen_rows = pick_latest_rows(frozen_rows)

    total_hourly = sum(as_float(r.get("estimated_hourly_value_usd"), 0.0) for r in live_measured_lanes)
    total_annual = sum(as_float(r.get("estimated_annual_value_usd"), 0.0) for r in live_measured_lanes)
    context_hourly = sum(as_float(r.get("estimated_hourly_value_usd"), 0.0) for r in context_only_lanes)
    context_annual = sum(as_float(r.get("estimated_annual_value_usd"), 0.0) for r in context_only_lanes)
    enabled_count = sum(1 for r in top_lanes if as_bool(r.get("enabled_source")))
    measured_count = sum(1 for r in live_measured_lanes if as_bool(r.get("measured_source")))
    ten_k_plus = sum(1 for r in live_measured_lanes if as_float(r.get("estimated_hourly_value_usd"), 0.0) >= 10_000)
    panel_provenance = panel.get("evidence_provenance", {}) if isinstance(panel.get("evidence_provenance"), dict) else {}
    primary_mode = str(panel_provenance.get("primary_evidence_mode") or ("live_measured_delta_rows" if live_measured_lanes else "no_live_measured_lanes"))

    run_tag = now_tag()
    payload = {
        "generated_utc": now_iso(),
        "run_tag": run_tag,
        "scope": "multi_asset_frozen_delta_pack",
        "inputs": {
            "live_breadth_value_panel_latest_json": str(LIVE_BREADTH_PANEL),
            "infra_frozen_deltas_jsonl": str(INFRA_FROZEN_DELTAS),
            "panel_source_rows": len(panel_rows),
            "panel_latest_rows": len(latest_panel_rows),
            "infra_frozen_rows_raw": len(frozen_rows),
            "infra_frozen_rows_latest": len(latest_frozen_rows),
            "panel_primary_evidence_mode": primary_mode,
        },
        "headline": {
            "lane_count": len(top_lanes),
            "live_measured_lane_count": len(live_measured_lanes),
            "context_only_lane_count": len(context_only_lanes),
            "live_measured_ten_k_plus_lane_count": ten_k_plus,
            "enabled_source_count": enabled_count,
            "measured_source_count": measured_count,
            "primary_evidence_mode": primary_mode,
            "live_measured_hourly_value_usd": round(total_hourly, 2),
            "live_measured_annual_value_usd": round(total_annual, 2),
            "context_only_hourly_value_usd": round(context_hourly, 2),
            "context_only_annual_value_usd": round(context_annual, 2),
            "estimated_hourly_value_usd": round(total_hourly, 2),
            "estimated_annual_value_usd": round(total_annual, 2),
            "top_lane_source": live_measured_lanes[0].get("source") if live_measured_lanes else "",
            "top_lane_sector": live_measured_lanes[0].get("sector") if live_measured_lanes else "",
            "top_lane_hourly_value_usd": round(as_float(live_measured_lanes[0].get("estimated_hourly_value_usd"), 0.0), 2) if live_measured_lanes else 0.0,
        },
        "claim_gate": {
            "live_measured_pack": bool(live_measured_lanes),
            "synthetic_or_reference_primary": not bool(live_measured_lanes),
            "grant_merit_proven": False,
            "trading_profit_proven": False,
            "boundary": (
                "Headline values include only rows marked measured_source and primary_live_evidence. "
                "Unmeasured frozen deltas, synthetic controls, and reference fallbacks are context-only."
            ),
        },
        "top_lanes": top_lanes,
        "live_measured_top_lanes": live_measured_lanes,
        "context_only_lanes": context_only_lanes,
    }

    json_tagged = OPS_OUT / f"multi_asset_frozen_delta_pack_{run_tag}.json"
    json_latest = OPS_OUT / "multi_asset_frozen_delta_pack_latest.json"
    md_tagged = OPS_OUT / f"multi_asset_frozen_delta_pack_{run_tag}.md"
    md_latest = OPS_OUT / "multi_asset_frozen_delta_pack_latest.md"
    csv_tagged = OPS_OUT / f"multi_asset_frozen_delta_pack_{run_tag}.csv"
    csv_latest = OPS_OUT / "multi_asset_frozen_delta_pack_latest.csv"

    write_json(json_tagged, payload)
    write_json(json_latest, payload)

    md_text = build_markdown(payload)
    write_text(md_tagged, md_text)
    write_text(md_latest, md_text)

    csv_rows: list[dict[str, Any]] = []
    for row in top_lanes:
        csv_rows.append(
            {
                "source": row.get("source", ""),
                "sector": row.get("sector", ""),
                "constraint": row.get("constraint", ""),
                "estimated_hourly_value_usd": row.get("estimated_hourly_value_usd", 0.0),
                "estimated_annual_value_usd": row.get("estimated_annual_value_usd", 0.0),
                "optimization_gain_pct": row.get("optimization_gain_pct", 0.0),
                "premium_tier": row.get("premium_tier", ""),
                "evidence_source": row.get("evidence_source", ""),
                "provenance": row.get("provenance", ""),
                "primary_live_evidence": row.get("primary_live_evidence", False),
                "enabled_source": row.get("enabled_source", False),
                "measured_source": row.get("measured_source", False),
            }
        )

    write_csv(
        csv_tagged,
        csv_rows,
        [
            "source",
            "sector",
            "constraint",
            "estimated_hourly_value_usd",
            "estimated_annual_value_usd",
            "optimization_gain_pct",
            "premium_tier",
            "evidence_source",
            "provenance",
            "primary_live_evidence",
            "enabled_source",
            "measured_source",
        ],
    )
    write_csv(
        csv_latest,
        csv_rows,
        [
            "source",
            "sector",
            "constraint",
            "estimated_hourly_value_usd",
            "estimated_annual_value_usd",
            "optimization_gain_pct",
            "premium_tier",
            "evidence_source",
            "provenance",
            "primary_live_evidence",
            "enabled_source",
            "measured_source",
        ],
    )

    print("BUILD_MULTI_ASSET_FROZEN_DELTA_PACK")
    print(f"json_latest={json_latest}")
    print(f"md_latest={md_latest}")
    print(f"csv_latest={csv_latest}")
    print(f"lanes={len(top_lanes)}")
    print(f"hourly_total={total_hourly:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
