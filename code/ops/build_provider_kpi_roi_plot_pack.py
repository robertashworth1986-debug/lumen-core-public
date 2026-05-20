#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DEFAULT_REGISTRY = ROOT / "config" / "live_source_registry.json"
DEFAULT_HISTORY = OUT_OPS / "provider_kpi_roi_history_1m.jsonl"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def parse_registry_rows(path: Path) -> list[dict[str, Any]]:
    data = load_json(path, {})
    rows: list[Any] = []

    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        for key in ("rows", "live_source_registry", "sources", "providers"):
            maybe_rows = data.get(key)
            if isinstance(maybe_rows, list):
                rows = maybe_rows
                break

    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
    return out


def provider_row(row: dict[str, Any], monthly_provider_cost_usd: float) -> dict[str, Any]:
    translated = row.get("translated_value") if isinstance(row.get("translated_value"), dict) else {}
    source = str(row.get("source", "UNKNOWN") or "UNKNOWN").upper().strip()
    sector = str(row.get("sector", "unknown") or "unknown").strip().lower()
    status = str(row.get("status", "UNKNOWN") or "UNKNOWN")
    rows_count = int(max(0.0, as_float(row.get("rows", 0))))

    enabled = as_bool(row.get("enabled"))
    measured_value = row.get("measured")
    if measured_value is None:
        measured = (
            str(row.get("dollar_basis", "")).upper() == "MEASURED"
            or (as_bool(row.get("probe_ok")) and rows_count > 0)
            or rows_count > 0
        )
    else:
        measured = as_bool(measured_value)

    hour_usd = max(0.0, as_float(translated.get("hour", 0.0)))
    day_usd = max(0.0, as_float(translated.get("day", 0.0)))
    week_usd = max(0.0, as_float(translated.get("week", 0.0)))
    month_usd = max(0.0, as_float(translated.get("month", 0.0)))
    year_usd = max(0.0, as_float(translated.get("year", 0.0)))

    if month_usd <= 0.0:
        month_usd = max(day_usd * 30.0, week_usd * 4.345, hour_usd * 24.0 * 30.0)

    quality_weight = 1.0 if measured else 0.40 if enabled else 0.10
    coverage_weight = min(1.0, math.log1p(float(rows_count)) / math.log(101.0))
    kpi_score = round(100.0 * ((0.70 * quality_weight) + (0.30 * coverage_weight)), 2)

    roi_proxy_pct = round(((month_usd - monthly_provider_cost_usd) / max(monthly_provider_cost_usd, 1.0)) * 100.0, 2)

    return {
        "source": source,
        "sector": sector,
        "status": status,
        "enabled": enabled,
        "measured": measured,
        "rows": rows_count,
        "http_status": int(as_float(row.get("http_status", 0))),
        "last_probe_utc": str(row.get("last_probe_utc", "") or ""),
        "probe_note": str(row.get("probe_note", "") or ""),
        "month_value_usd": round(month_usd, 2),
        "day_value_usd": round(day_usd, 2),
        "hour_value_usd": round(hour_usd, 2),
        "year_value_usd": round(year_usd, 2),
        "kpi_score": kpi_score,
        "roi_proxy_pct": roi_proxy_pct,
        "monthly_cost_usd": round(monthly_provider_cost_usd, 2),
    }


def sector_rows(provider_rows: list[dict[str, Any]], monthly_provider_cost_usd: float) -> list[dict[str, Any]]:
    by_sector: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "sector": "unknown",
            "provider_count": 0,
            "enabled_count": 0,
            "measured_count": 0,
            "rows": 0,
            "month_value_usd": 0.0,
            "day_value_usd": 0.0,
            "hour_value_usd": 0.0,
            "year_value_usd": 0.0,
            "avg_kpi_score": 0.0,
        }
    )

    for item in provider_rows:
        sector = str(item.get("sector", "unknown") or "unknown")
        slot = by_sector[sector]
        slot["sector"] = sector
        slot["provider_count"] += 1
        slot["enabled_count"] += 1 if item.get("enabled") else 0
        slot["measured_count"] += 1 if item.get("measured") else 0
        slot["rows"] += int(item.get("rows", 0) or 0)
        slot["month_value_usd"] += as_float(item.get("month_value_usd", 0.0))
        slot["day_value_usd"] += as_float(item.get("day_value_usd", 0.0))
        slot["hour_value_usd"] += as_float(item.get("hour_value_usd", 0.0))
        slot["year_value_usd"] += as_float(item.get("year_value_usd", 0.0))
        slot["avg_kpi_score"] += as_float(item.get("kpi_score", 0.0))

    out: list[dict[str, Any]] = []
    for sector, slot in by_sector.items():
        provider_count = max(1, int(slot["provider_count"]))
        cost = monthly_provider_cost_usd * provider_count
        month_value = float(slot["month_value_usd"])
        roi_proxy_pct = round(((month_value - cost) / max(cost, 1.0)) * 100.0, 2)
        measured_share_pct = round((float(slot["measured_count"]) / provider_count) * 100.0, 2)
        out.append(
            {
                "sector": sector,
                "provider_count": int(slot["provider_count"]),
                "enabled_count": int(slot["enabled_count"]),
                "measured_count": int(slot["measured_count"]),
                "measured_share_pct": measured_share_pct,
                "rows": int(slot["rows"]),
                "month_value_usd": round(month_value, 2),
                "day_value_usd": round(float(slot["day_value_usd"]), 2),
                "hour_value_usd": round(float(slot["hour_value_usd"]), 2),
                "year_value_usd": round(float(slot["year_value_usd"]), 2),
                "avg_kpi_score": round(float(slot["avg_kpi_score"]) / provider_count, 2),
                "roi_proxy_pct": roi_proxy_pct,
                "monthly_cost_usd": round(cost, 2),
            }
        )

    out.sort(key=lambda row: (row.get("month_value_usd", 0.0), row.get("measured_count", 0)), reverse=True)
    return out


def load_history_points(path: Path, max_points: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    out: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if isinstance(row, dict):
                    out.append(row)
    except Exception:
        return []

    if len(out) > max_points:
        out = out[-max_points:]
    return out


def copy_latest(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def try_import_pyplot():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        return plt
    except Exception:
        return None


def render_plots(
    plt,
    providers: list[dict[str, Any]],
    sectors: list[dict[str, Any]],
    history_points: list[dict[str, Any]],
    pack_dir: Path,
) -> list[Path]:
    out_files: list[Path] = []

    providers_sorted = sorted(providers, key=lambda item: float(item.get("month_value_usd", 0.0)), reverse=True)
    provider_names = [str(item["source"]) for item in providers_sorted]
    provider_kpi = [as_float(item.get("kpi_score", 0.0)) for item in providers_sorted]
    provider_month_k = [as_float(item.get("month_value_usd", 0.0)) / 1000.0 for item in providers_sorted]
    provider_colors = ["#0b8f3a" if item.get("measured") else "#d17c00" if item.get("enabled") else "#6b7280" for item in providers_sorted]

    if provider_names:
        fig, ax = plt.subplots(figsize=(max(12.0, len(provider_names) * 0.55), 6.0))
        ax.bar(provider_names, provider_kpi, color=provider_colors)
        ax.set_title("Provider KPI Score (1m Snapshot)")
        ax.set_ylabel("KPI Score")
        ax.set_ylim(0, 100)
        ax.tick_params(axis="x", rotation=60)
        fig.tight_layout()
        p1 = pack_dir / "provider_kpi_score_1m.png"
        fig.savefig(p1, dpi=150)
        plt.close(fig)
        out_files.append(p1)

        fig, ax = plt.subplots(figsize=(max(12.0, len(provider_names) * 0.55), 6.0))
        ax.bar(provider_names, provider_month_k, color=provider_colors)
        ax.set_title("Provider Monthly Value Proxy (1m Snapshot)")
        ax.set_ylabel("Month Value (kUSD)")
        ax.tick_params(axis="x", rotation=60)
        fig.tight_layout()
        p2 = pack_dir / "provider_month_value_1m.png"
        fig.savefig(p2, dpi=150)
        plt.close(fig)
        out_files.append(p2)

    sectors_sorted = sorted(sectors, key=lambda item: float(item.get("month_value_usd", 0.0)), reverse=True)
    sector_names = [str(item["sector"]) for item in sectors_sorted]
    sector_month_m = [as_float(item.get("month_value_usd", 0.0)) / 1_000_000.0 for item in sectors_sorted]
    sector_share = [as_float(item.get("measured_share_pct", 0.0)) for item in sectors_sorted]

    if sector_names:
        fig, ax = plt.subplots(figsize=(max(10.0, len(sector_names) * 0.8), 6.0))
        ax.bar(sector_names, sector_month_m, color="#14532d")
        ax.set_title("Sector Monthly Value Proxy (1m Snapshot)")
        ax.set_ylabel("Month Value (MUSD)")
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()
        p3 = pack_dir / "sector_month_value_1m.png"
        fig.savefig(p3, dpi=150)
        plt.close(fig)
        out_files.append(p3)

        fig, ax = plt.subplots(figsize=(max(10.0, len(sector_names) * 0.8), 6.0))
        ax.bar(sector_names, sector_share, color="#0f766e")
        ax.set_title("Sector Measured Share (1m Snapshot)")
        ax.set_ylabel("Measured Share (%)")
        ax.set_ylim(0, 100)
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()
        p4 = pack_dir / "sector_measured_share_1m.png"
        fig.savefig(p4, dpi=150)
        plt.close(fig)
        out_files.append(p4)

    timeline_points = []
    for row in history_points:
        ts_raw = str(row.get("generated_utc", "") or "")
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except Exception:
            continue
        timeline_points.append(
            {
                "ts": ts,
                "measured": as_float(row.get("measured_count", 0.0)),
                "enabled": as_float(row.get("enabled_count", 0.0)),
                "month_value_musd": as_float(row.get("total_month_value_usd", 0.0)) / 1_000_000.0,
            }
        )

    timeline_points.sort(key=lambda item: item["ts"])
    if timeline_points:
        xs = [item["ts"] for item in timeline_points]
        measured = [item["measured"] for item in timeline_points]
        enabled = [item["enabled"] for item in timeline_points]
        month_value_musd = [item["month_value_musd"] for item in timeline_points]

        fig, ax1 = plt.subplots(figsize=(12.0, 6.0))
        ax1.plot(xs, measured, color="#0b8f3a", linewidth=2.0, label="Measured")
        ax1.plot(xs, enabled, color="#2563eb", linewidth=1.5, linestyle="--", label="Enabled")
        ax1.set_title("Provider Health Timeline (1m)")
        ax1.set_ylabel("Provider Count")
        ax1.tick_params(axis="x", rotation=35)

        ax2 = ax1.twinx()
        ax2.plot(xs, month_value_musd, color="#7c3aed", linewidth=1.5, label="Total Month Value (MUSD)")
        ax2.set_ylabel("Month Value (MUSD)")

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

        fig.tight_layout()
        p5 = pack_dir / "provider_health_timeline_1m.png"
        fig.savefig(p5, dpi=150)
        plt.close(fig)
        out_files.append(p5)

    return out_files


def main() -> int:
    parser = argparse.ArgumentParser(description="Build provider KPI/ROI report and 1m plots from live source registry.")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="Path to live_source_registry.json")
    parser.add_argument("--out-dir", default=str(OUT_OPS), help="Output directory for generated artifacts")
    parser.add_argument(
        "--history-file",
        default=str(DEFAULT_HISTORY),
        help="JSONL history file for 1m timeline points",
    )
    parser.add_argument(
        "--monthly-provider-cost-usd",
        type=float,
        default=500.0,
        help="Assumed monthly ops cost per provider for ROI proxy calculations",
    )
    parser.add_argument(
        "--timeline-points",
        type=int,
        default=1440,
        help="Max history points loaded for timeline plotting",
    )
    args = parser.parse_args()

    registry_path = Path(args.registry)
    out_dir = Path(args.out_dir)
    history_file = Path(args.history_file)

    rows = parse_registry_rows(registry_path)
    if not rows:
        raise SystemExit(f"No provider rows found in registry: {registry_path}")

    providers = [provider_row(row, monthly_provider_cost_usd=max(1.0, float(args.monthly_provider_cost_usd))) for row in rows]
    providers.sort(key=lambda item: (as_float(item.get("month_value_usd", 0.0)), as_float(item.get("kpi_score", 0.0))), reverse=True)

    sectors = sector_rows(providers, monthly_provider_cost_usd=max(1.0, float(args.monthly_provider_cost_usd)))

    measured_count = sum(1 for item in providers if item.get("measured"))
    enabled_count = sum(1 for item in providers if item.get("enabled"))
    provider_count = len(providers)
    total_month_value_usd = round(sum(as_float(item.get("month_value_usd", 0.0)) for item in providers), 2)

    failing_enabled = [
        {
            "source": item.get("source"),
            "sector": item.get("sector"),
            "status": item.get("status"),
            "http_status": item.get("http_status"),
            "probe_note": item.get("probe_note"),
        }
        for item in providers
        if item.get("enabled") and not item.get("measured")
    ]

    snapshot = {
        "generated_utc": now_utc(),
        "provider_count": provider_count,
        "enabled_count": enabled_count,
        "measured_count": measured_count,
        "measured_share_pct": round((measured_count / max(provider_count, 1)) * 100.0, 2),
        "total_month_value_usd": total_month_value_usd,
    }
    append_jsonl(history_file, snapshot)

    history_points = load_history_points(history_file, max_points=max(1, int(args.timeline_points)))

    stamp = utc_stamp()
    pack_dir = out_dir / f"provider_kpi_roi_pack_{stamp}"
    pack_dir.mkdir(parents=True, exist_ok=True)

    provider_csv = pack_dir / "provider_kpi_roi_1m.csv"
    sector_csv = pack_dir / "sector_kpi_roi_1m.csv"

    write_csv(
        provider_csv,
        providers,
        fieldnames=[
            "source",
            "sector",
            "status",
            "enabled",
            "measured",
            "rows",
            "http_status",
            "last_probe_utc",
            "month_value_usd",
            "day_value_usd",
            "hour_value_usd",
            "year_value_usd",
            "kpi_score",
            "roi_proxy_pct",
            "monthly_cost_usd",
            "probe_note",
        ],
    )
    write_csv(
        sector_csv,
        sectors,
        fieldnames=[
            "sector",
            "provider_count",
            "enabled_count",
            "measured_count",
            "measured_share_pct",
            "rows",
            "month_value_usd",
            "day_value_usd",
            "hour_value_usd",
            "year_value_usd",
            "avg_kpi_score",
            "roi_proxy_pct",
            "monthly_cost_usd",
        ],
    )

    summary = {
        "generated_utc": now_utc(),
        "scope": "provider_kpi_roi_plot_pack",
        "registry_path": str(registry_path),
        "history_path": str(history_file),
        "counts": snapshot,
        "top_measured": providers[:10],
        "failing_enabled_sources": failing_enabled,
        "sector_summary": sectors,
        "methodology": {
            "kpi_score": "0-100 weighted score from measured status and observed row coverage",
            "roi_proxy_pct": "((month_value_usd - monthly_provider_cost_usd) / monthly_provider_cost_usd) * 100",
            "monthly_provider_cost_usd": round(max(1.0, float(args.monthly_provider_cost_usd)), 2),
            "note": "ROI is a proxy from live translated value, not realized trade PnL.",
        },
        "evidence_paths": {
            "provider_csv": str(provider_csv),
            "sector_csv": str(sector_csv),
        },
    }

    summary_path = pack_dir / "provider_kpi_roi_pack_summary.json"
    save_json(summary_path, summary)

    latest_provider_csv = out_dir / "provider_kpi_roi_1m_latest.csv"
    latest_sector_csv = out_dir / "sector_kpi_roi_1m_latest.csv"
    latest_summary_json = out_dir / "provider_kpi_roi_pack_latest.json"

    copy_latest(provider_csv, latest_provider_csv)
    copy_latest(sector_csv, latest_sector_csv)
    copy_latest(summary_path, latest_summary_json)

    generated_plot_paths: list[Path] = []
    plt = try_import_pyplot()
    if plt is not None:
        generated_plot_paths = render_plots(plt, providers, sectors, history_points, pack_dir)
        for plot_path in generated_plot_paths:
            latest_plot = out_dir / f"{plot_path.stem}_latest.png"
            copy_latest(plot_path, latest_plot)

    summary["evidence_paths"]["pack_dir"] = str(pack_dir)
    summary["evidence_paths"]["plots"] = [str(path) for path in generated_plot_paths]
    save_json(summary_path, summary)
    copy_latest(summary_path, latest_summary_json)

    print(f"[provider_count] {provider_count}")
    print(f"[enabled_count] {enabled_count}")
    print(f"[measured_count] {measured_count}")
    print(f"[total_month_value_usd] {total_month_value_usd}")
    print(f"[summary] {summary_path}")
    if failing_enabled:
        failed = ", ".join(str(item.get("source")) for item in failing_enabled)
        print(f"[failing_enabled_sources] {failed}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
