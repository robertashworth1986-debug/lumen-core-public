from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOURS_PER_YEAR = 24.0 * 365.0


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_utc(value: Any) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    fmts = (
        "%Y%m%dT%H%M%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S%z",
    )
    for fmt in fmts:
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def normalize_token(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^A-Z0-9]+", "", str(value).upper())


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
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


def pick_latest_by_site_set(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str, str], dict[str, Any]] = {}
    latest_ts: dict[tuple[str, str, str], datetime] = {}

    for row in rows:
        source = str(row.get("source") or "UNKNOWN")
        sector = str(row.get("sector") or "unknown")
        constraint = str(row.get("constraint") or "default")
        key = (normalize_token(source), normalize_token(sector), normalize_token(constraint))

        ts = parse_utc(row.get("generated_utc"))
        prev_ts = latest_ts.get(key)
        if prev_ts is None or ts >= prev_ts:
            latest[key] = row
            latest_ts[key] = ts

    out = list(latest.values())
    out.sort(key=lambda r: parse_utc(r.get("generated_utc")), reverse=True)
    return out


def classify_action(gain_pct: float) -> str:
    if gain_pct >= 5.0:
        return "scale_now"
    if gain_pct >= 1.0:
        return "scale_guarded"
    if gain_pct >= 0.01:
        return "protect_and_compound"
    return "observe"


def fmt_usd(value: float) -> str:
    return f"${value:,.2f}"


def build_report(
    stack_root: Path,
    delta_file: Path,
    opportunity_scan_file: Path,
    optimization_file: Path,
    min_gain_pct: float,
    top_n: int,
) -> dict[str, Any]:
    deltas_all = load_jsonl(delta_file)
    if not deltas_all:
        raise RuntimeError(f"No delta records found at {delta_file}")

    deltas_latest = pick_latest_by_site_set(deltas_all)
    scan = load_json(opportunity_scan_file)
    optimization = load_json(optimization_file)

    active_rows = (
        scan.get("registry", {}).get("active_rows", [])
        if isinstance(scan, dict)
        else []
    )
    active_by_source: dict[str, dict[str, Any]] = {}
    for row in active_rows:
        if not isinstance(row, dict):
            continue
        src = normalize_token(row.get("source"))
        if src:
            active_by_source[src] = row

    event_rows: list[dict[str, Any]] = []
    filtered_out = 0
    for row in deltas_latest:
        source = str(row.get("source") or "UNKNOWN")
        sector = str(row.get("sector") or "unknown")
        constraint = str(row.get("constraint") or "default")

        baseline_hourly = to_float(row.get("baseline_loss_rate_usd_per_hour"), 0.0)
        gain_pct = to_float(row.get("optimization_gain_pct"), 0.0)
        reported_hourly = to_float(row.get("estimated_hourly_value_usd"), 0.0)

        if gain_pct <= 0.0 and baseline_hourly > 0.0 and reported_hourly > 0.0:
            gain_pct = (reported_hourly / baseline_hourly) * 100.0

        if gain_pct < min_gain_pct:
            filtered_out += 1
            continue

        computed_hourly = baseline_hourly * (gain_pct / 100.0)
        selected_hourly = reported_hourly if reported_hourly > 0 else computed_hourly
        annualized_value = selected_hourly * HOURS_PER_YEAR

        micro_floor_hourly = baseline_hourly * (min_gain_pct / 100.0)
        micro_floor_annual = micro_floor_hourly * HOURS_PER_YEAR

        active_row = active_by_source.get(normalize_token(source), {})
        active_enabled = bool(active_row.get("enabled")) if isinstance(active_row, dict) else False
        key_present = bool(row.get("key_present", False))
        live_active = bool(key_present or active_enabled)

        generated_utc = str(row.get("generated_utc") or "")
        predicted_failure_utc = str(row.get("predicted_failure_utc") or "")

        why_text = (
            f"{source} in {sector} has baseline exposure {fmt_usd(baseline_hourly)}/hour; "
            f"harmonic flowform gain {gain_pct:.4f}% converts to {fmt_usd(selected_hourly)}/hour."
            if baseline_hourly > 0
            else f"{source} in {sector} shows harmonic flowform gain {gain_pct:.4f}% with modeled value {fmt_usd(selected_hourly)}/hour."
        )
        when_text = (
            f"Observed at {generated_utc}; predicted pressure window {predicted_failure_utc}."
            if predicted_failure_utc
            else f"Observed at {generated_utc}."
        )
        what_text = f"site={source}; set={sector}::{constraint}"
        how_much_text = (
            f"{fmt_usd(selected_hourly)}/hour, {fmt_usd(annualized_value)}/year; "
            f"micro-floor {min_gain_pct:.4f}% alone is {fmt_usd(micro_floor_hourly)}/hour ({fmt_usd(micro_floor_annual)}/year)."
        )

        event_rows.append(
            {
                "generated_utc": generated_utc,
                "source": source,
                "sector": sector,
                "constraint": constraint,
                "set_id": f"{sector}::{constraint}",
                "predicted_failure_utc": predicted_failure_utc,
                "trust_tier": str(row.get("trust_tier") or ""),
                "key_present": key_present,
                "live_active": live_active,
                "active_registry_enabled": active_enabled,
                "active_registry_env": str(active_row.get("env") or "") if isinstance(active_row, dict) else "",
                "active_registry_rows": to_float(active_row.get("rows"), 0.0) if isinstance(active_row, dict) else 0.0,
                "rows_written": to_float(row.get("rows_written"), 0.0),
                "baseline_loss_rate_usd_per_hour": baseline_hourly,
                "optimization_gain_pct": gain_pct,
                "estimated_hourly_value_usd": reported_hourly,
                "computed_hourly_value_usd": computed_hourly,
                "selected_hourly_value_usd": selected_hourly,
                "annualized_value_usd": annualized_value,
                "micro_gain_floor_pct": min_gain_pct,
                "micro_gain_floor_hourly_usd": micro_floor_hourly,
                "micro_gain_floor_annual_usd": micro_floor_annual,
                "predicted_failure_cost_usd": to_float(row.get("predicted_failure_cost_usd"), 0.0),
                "estimated_avoided_loss_usd": to_float(row.get("estimated_avoided_loss_usd"), 0.0),
                "estimated_residual_loss_usd": to_float(row.get("estimated_residual_loss_usd"), 0.0),
                "why": why_text,
                "when": when_text,
                "what": what_text,
                "how_much": how_much_text,
                "action": classify_action(gain_pct),
            }
        )

    if not event_rows:
        raise RuntimeError(
            f"No delta records met min_gain_pct={min_gain_pct}. Check {delta_file}"
        )

    site_rollup: dict[str, dict[str, Any]] = {}
    set_rollup: dict[str, dict[str, Any]] = {}

    for row in event_rows:
        source = row["source"]
        set_id = row["set_id"]
        sector = row["sector"]
        constraint = row["constraint"]

        s = site_rollup.setdefault(
            source,
            {
                "site": source,
                "live_active": False,
                "set_count": 0,
                "sector_count": 0,
                "total_baseline_loss_rate_usd_per_hour": 0.0,
                "total_selected_hourly_value_usd": 0.0,
                "total_annualized_value_usd": 0.0,
                "micro_gain_floor_hourly_usd": 0.0,
                "micro_gain_floor_annual_usd": 0.0,
                "weighted_gain_numerator": 0.0,
                "weighted_gain_denominator": 0.0,
                "max_gain_pct": 0.0,
                "last_event_utc": "",
                "sets": set(),
                "sectors": set(),
            },
        )

        baseline_hourly = row["baseline_loss_rate_usd_per_hour"]
        gain_pct = row["optimization_gain_pct"]
        s["live_active"] = bool(s["live_active"] or row["live_active"])
        s["total_baseline_loss_rate_usd_per_hour"] += baseline_hourly
        s["total_selected_hourly_value_usd"] += row["selected_hourly_value_usd"]
        s["total_annualized_value_usd"] += row["annualized_value_usd"]
        s["micro_gain_floor_hourly_usd"] += row["micro_gain_floor_hourly_usd"]
        s["micro_gain_floor_annual_usd"] += row["micro_gain_floor_annual_usd"]
        s["weighted_gain_numerator"] += gain_pct * max(baseline_hourly, 0.0)
        s["weighted_gain_denominator"] += max(baseline_hourly, 0.0)
        s["max_gain_pct"] = max(s["max_gain_pct"], gain_pct)
        s["last_event_utc"] = max(str(s["last_event_utc"]), str(row["generated_utc"]))
        s["sets"].add(set_id)
        s["sectors"].add(sector)

        g = set_rollup.setdefault(
            set_id,
            {
                "set_id": set_id,
                "sector": sector,
                "constraint": constraint,
                "site_count": 0,
                "total_baseline_loss_rate_usd_per_hour": 0.0,
                "total_selected_hourly_value_usd": 0.0,
                "total_annualized_value_usd": 0.0,
                "micro_gain_floor_hourly_usd": 0.0,
                "micro_gain_floor_annual_usd": 0.0,
                "weighted_gain_numerator": 0.0,
                "weighted_gain_denominator": 0.0,
                "max_gain_pct": 0.0,
                "last_event_utc": "",
                "sites": set(),
            },
        )

        g["total_baseline_loss_rate_usd_per_hour"] += baseline_hourly
        g["total_selected_hourly_value_usd"] += row["selected_hourly_value_usd"]
        g["total_annualized_value_usd"] += row["annualized_value_usd"]
        g["micro_gain_floor_hourly_usd"] += row["micro_gain_floor_hourly_usd"]
        g["micro_gain_floor_annual_usd"] += row["micro_gain_floor_annual_usd"]
        g["weighted_gain_numerator"] += gain_pct * max(baseline_hourly, 0.0)
        g["weighted_gain_denominator"] += max(baseline_hourly, 0.0)
        g["max_gain_pct"] = max(g["max_gain_pct"], gain_pct)
        g["last_event_utc"] = max(str(g["last_event_utc"]), str(row["generated_utc"]))
        g["sites"].add(source)

    site_rows: list[dict[str, Any]] = []
    for src, row in site_rollup.items():
        denom = row["weighted_gain_denominator"]
        weighted_gain_pct = row["weighted_gain_numerator"] / denom if denom > 0 else 0.0
        site_rows.append(
            {
                "site": src,
                "live_active": bool(row["live_active"]),
                "set_count": len(row["sets"]),
                "sector_count": len(row["sectors"]),
                "total_baseline_loss_rate_usd_per_hour": row["total_baseline_loss_rate_usd_per_hour"],
                "total_selected_hourly_value_usd": row["total_selected_hourly_value_usd"],
                "total_annualized_value_usd": row["total_annualized_value_usd"],
                "micro_gain_floor_hourly_usd": row["micro_gain_floor_hourly_usd"],
                "micro_gain_floor_annual_usd": row["micro_gain_floor_annual_usd"],
                "weighted_gain_pct": weighted_gain_pct,
                "max_gain_pct": row["max_gain_pct"],
                "recommended_action": classify_action(weighted_gain_pct),
                "last_event_utc": row["last_event_utc"],
            }
        )

    set_rows: list[dict[str, Any]] = []
    for set_id, row in set_rollup.items():
        denom = row["weighted_gain_denominator"]
        weighted_gain_pct = row["weighted_gain_numerator"] / denom if denom > 0 else 0.0
        top_sites = sorted(row["sites"])[:5]
        set_rows.append(
            {
                "set_id": set_id,
                "sector": row["sector"],
                "constraint": row["constraint"],
                "site_count": len(row["sites"]),
                "total_baseline_loss_rate_usd_per_hour": row["total_baseline_loss_rate_usd_per_hour"],
                "total_selected_hourly_value_usd": row["total_selected_hourly_value_usd"],
                "total_annualized_value_usd": row["total_annualized_value_usd"],
                "micro_gain_floor_hourly_usd": row["micro_gain_floor_hourly_usd"],
                "micro_gain_floor_annual_usd": row["micro_gain_floor_annual_usd"],
                "weighted_gain_pct": weighted_gain_pct,
                "max_gain_pct": row["max_gain_pct"],
                "recommended_action": classify_action(weighted_gain_pct),
                "last_event_utc": row["last_event_utc"],
                "sample_sites": ", ".join(top_sites),
            }
        )

    site_rows.sort(key=lambda r: r["total_annualized_value_usd"], reverse=True)
    set_rows.sort(key=lambda r: r["total_annualized_value_usd"], reverse=True)
    event_rows.sort(key=lambda r: r["annualized_value_usd"], reverse=True)

    total_baseline_hourly = sum(r["total_baseline_loss_rate_usd_per_hour"] for r in site_rows)
    total_hourly_value = sum(r["total_selected_hourly_value_usd"] for r in site_rows)
    total_annualized_value = sum(r["total_annualized_value_usd"] for r in site_rows)
    total_micro_hourly = sum(r["micro_gain_floor_hourly_usd"] for r in site_rows)
    total_micro_annual = sum(r["micro_gain_floor_annual_usd"] for r in site_rows)
    live_active_sites = sum(1 for r in site_rows if r["live_active"])

    recommended = optimization.get("recommended", {}) if isinstance(optimization, dict) else {}

    report = {
        "generated_utc": utc_now_iso(),
        "scope": {
            "stack_root": str(stack_root),
            "min_gain_pct": min_gain_pct,
            "selection_mode": "latest_per_site_set",
            "top_n": top_n,
        },
        "evidence_inputs": {
            "delta_file": str(delta_file),
            "opportunity_scan_file": str(opportunity_scan_file),
            "optimization_file": str(optimization_file),
            "delta_records_raw": len(deltas_all),
            "delta_records_latest_site_set": len(deltas_latest),
            "delta_records_used": len(event_rows),
            "delta_records_filtered_out": filtered_out,
        },
        "cross_sector_context": {
            "recommended": recommended,
            "optimization_generated_utc": optimization.get("generated_utc") if isinstance(optimization, dict) else None,
        },
        "totals": {
            "site_count": len(site_rows),
            "set_count": len(set_rows),
            "live_active_site_count": live_active_sites,
            "total_baseline_loss_rate_usd_per_hour": total_baseline_hourly,
            "total_selected_hourly_value_usd": total_hourly_value,
            "total_annualized_value_usd": total_annualized_value,
            "micro_gain_floor_pct": min_gain_pct,
            "micro_gain_floor_total_hourly_usd": total_micro_hourly,
            "micro_gain_floor_total_annual_usd": total_micro_annual,
        },
        "site_rollup": site_rows,
        "set_rollup": set_rows,
        "top_site_events": event_rows[: max(1, top_n)],
    }

    return report


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


def write_markdown(path: Path, report: dict[str, Any], top_n: int) -> None:
    totals = report.get("totals", {})
    sites = report.get("site_rollup", [])
    sets = report.get("set_rollup", [])
    events = report.get("top_site_events", [])
    inputs = report.get("evidence_inputs", {})

    lines: list[str] = []
    lines.append("# Harmonic Flowform Live Impact Explainer")
    lines.append("")
    lines.append(f"Generated UTC: {report.get('generated_utc', '')}")
    lines.append(f"Scope: latest per site/set with gain >= {report.get('scope', {}).get('min_gain_pct', 0.01):.4f}%")
    lines.append("")
    lines.append("## Why Tiny Gains Matter")
    lines.append(
        f"At current live baseline exposure of {fmt_usd(to_float(totals.get('total_baseline_loss_rate_usd_per_hour')))} per hour, "
        f"a micro gain floor of {to_float(totals.get('micro_gain_floor_pct')):.4f}% is worth "
        f"{fmt_usd(to_float(totals.get('micro_gain_floor_total_hourly_usd')))} per hour "
        f"or {fmt_usd(to_float(totals.get('micro_gain_floor_total_annual_usd')))} per year."
    )
    lines.append("")
    lines.append("## Portfolio Totals")
    lines.append(f"- Live active sites: {int(to_float(totals.get('live_active_site_count')))}")
    lines.append(f"- Site count: {int(to_float(totals.get('site_count')))}")
    lines.append(f"- Set count: {int(to_float(totals.get('set_count')))}")
    lines.append(f"- Current selected value: {fmt_usd(to_float(totals.get('total_selected_hourly_value_usd')))} per hour")
    lines.append(f"- Current selected annualized value: {fmt_usd(to_float(totals.get('total_annualized_value_usd')))} per year")
    lines.append("")
    lines.append("## Per-Site Impact (Top)")
    lines.append("| Site | Why | When | What | How Much |")
    lines.append("|---|---|---|---|---|")
    for event in events[:top_n]:
        lines.append(
            "| "
            + f"{event.get('source','')}"
            + " | "
            + f"{str(event.get('why','')).replace('|', '/')}"
            + " | "
            + f"{str(event.get('when','')).replace('|', '/')}"
            + " | "
            + f"{str(event.get('what','')).replace('|', '/')}"
            + " | "
            + f"{str(event.get('how_much','')).replace('|', '/')}"
            + " |"
        )

    lines.append("")
    lines.append("## Per-Set Rollup (Top)")
    lines.append("| Set | Sites | Weighted Gain % | Annual Value | Micro-Floor Annual | Action |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for row in sets[:top_n]:
        lines.append(
            "| "
            + f"{row.get('set_id','')}"
            + " | "
            + f"{int(to_float(row.get('site_count')))}"
            + " | "
            + f"{to_float(row.get('weighted_gain_pct')):.4f}%"
            + " | "
            + f"{fmt_usd(to_float(row.get('total_annualized_value_usd')))}"
            + " | "
            + f"{fmt_usd(to_float(row.get('micro_gain_floor_annual_usd')))}"
            + " | "
            + f"{row.get('recommended_action','')}"
            + " |"
        )

    lines.append("")
    lines.append("## Evidence Paths")
    lines.append(f"- Delta ledger: {inputs.get('delta_file','')}")
    lines.append(f"- Active source registry scan: {inputs.get('opportunity_scan_file','')}")
    lines.append(f"- Cross-sector optimization: {inputs.get('optimization_file','')}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a live harmonic flowform impact explainer for sites and sets."
    )
    parser.add_argument(
        "--stack-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Stack root (default: INSTITUTIONAL_STACK_V2)",
    )
    parser.add_argument(
        "--delta-file",
        default="",
        help="Path to frozen delta jsonl (default: <stack>/out/infra_frozen_deltas.jsonl)",
    )
    parser.add_argument(
        "--opportunity-scan-file",
        default="",
        help="Path to opportunity scan json (default: <stack>/out/grants/_queue/opportunity_scan.json)",
    )
    parser.add_argument(
        "--optimization-file",
        default="",
        help="Path to optimization report json (default: <stack>/out/cross_sector_optimization_report.json)",
    )
    parser.add_argument(
        "--min-gain-pct",
        type=float,
        default=0.01,
        help="Minimum optimization gain percentage to include (default: 0.01)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=25,
        help="Top rows to keep in markdown and top event payload (default: 25)",
    )
    args = parser.parse_args()

    stack_root = Path(args.stack_root).resolve()
    delta_file = Path(args.delta_file).resolve() if args.delta_file else (stack_root / "out" / "infra_frozen_deltas.jsonl")
    opportunity_scan_file = Path(args.opportunity_scan_file).resolve() if args.opportunity_scan_file else (stack_root / "out" / "grants" / "_queue" / "opportunity_scan.json")
    optimization_file = Path(args.optimization_file).resolve() if args.optimization_file else (stack_root / "out" / "cross_sector_optimization_report.json")

    report = build_report(
        stack_root=stack_root,
        delta_file=delta_file,
        opportunity_scan_file=opportunity_scan_file,
        optimization_file=optimization_file,
        min_gain_pct=args.min_gain_pct,
        top_n=max(1, int(args.top_n)),
    )

    out_dir = stack_root / "out" / "ops"
    tag = utc_now_tag()

    json_path = out_dir / f"harmonic_flowform_impact_{tag}.json"
    site_csv_path = out_dir / f"harmonic_flowform_site_rollup_{tag}.csv"
    set_csv_path = out_dir / f"harmonic_flowform_set_rollup_{tag}.csv"
    event_csv_path = out_dir / f"harmonic_flowform_event_rollup_{tag}.csv"
    md_path = out_dir / f"harmonic_flowform_impact_{tag}.md"

    write_json(json_path, report)
    write_csv(site_csv_path, report.get("site_rollup", []))
    write_csv(set_csv_path, report.get("set_rollup", []))
    write_csv(event_csv_path, report.get("top_site_events", []))
    write_markdown(md_path, report, top_n=max(1, int(args.top_n)))

    latest_json = out_dir / "harmonic_flowform_impact_latest.json"
    latest_site_csv = out_dir / "harmonic_flowform_site_rollup_latest.csv"
    latest_set_csv = out_dir / "harmonic_flowform_set_rollup_latest.csv"
    latest_event_csv = out_dir / "harmonic_flowform_event_rollup_latest.csv"
    latest_md = out_dir / "harmonic_flowform_impact_latest.md"

    write_json(latest_json, report)
    latest_site_csv.write_text(site_csv_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_set_csv.write_text(set_csv_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_event_csv.write_text(event_csv_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")

    manifest = {
        "generated_utc": report.get("generated_utc"),
        "scope": report.get("scope"),
        "artifacts": {
            "json": str(json_path),
            "site_csv": str(site_csv_path),
            "set_csv": str(set_csv_path),
            "event_csv": str(event_csv_path),
            "markdown": str(md_path),
            "latest_json": str(latest_json),
            "latest_site_csv": str(latest_site_csv),
            "latest_set_csv": str(latest_set_csv),
            "latest_event_csv": str(latest_event_csv),
            "latest_markdown": str(latest_md),
        },
    }
    manifest_path = out_dir / f"harmonic_flowform_impact_manifest_{tag}.json"
    write_json(manifest_path, manifest)

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
