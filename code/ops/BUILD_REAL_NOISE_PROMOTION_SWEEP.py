from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"
LIVE_MEASURED = ROOT / "data" / "live_measured"
LEGACY_DATA = ROOT.parent / "data"

OUT_JSON = OUT_OPS / "real_noise_promotion_sweep_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "real_noise_promotion_sweep.json"
OUT_MD = DOCS / "REAL_NOISE_PROMOTION_SWEEP_2026-07-03.md"

BOUNDARY = (
    "Real-noise promotion sweep only. It hashes local/provider snapshots, measures noise and baseline-probe "
    "readiness, and identifies datasets ready for locked replay. It does not prove field validation, realized "
    "savings, fixed frozen-delta pricing, safety certification, medical efficacy, or autonomous live trading."
)

LANE_HINTS = {
    "energy_grid_proxy": ["eia", "energy", "nuclear", "eba", "net_generation", "mer_t09"],
    "market_noise": ["kraken", "coinbase", "coingecko", "binance", "alphavantage", "finnhub", "twelve", "massive"],
    "macro_rate_labor": ["fred", "bls", "bea", "treasury", "census", "unrate", "dgs10", "cpiaucsl"],
    "air_weather_water": ["airnow", "epa", "noaa", "nws", "open_meteo", "usgs", "water"],
    "federal_opportunity": ["sam_gov", "grants_gov", "sec_public", "world_bank"],
    "space_science": ["nasa", "nrel"],
}

LEGACY_CSV_ALLOWLIST = [
    "kraken_live.csv",
    "kraken_live_5000.csv",
    "fred_DGS10.csv",
    "fred_UNRATE.csv",
    "fred_CPIAUCSL.csv",
    "MER_T09_04.csv",
    "Net_generation_for_all_sectors (1).csv",
    "Net_generation_United_States_all_sectors_annual (1).csv",
    "Daily_U.S._nuclear_capacity_outage.csv",
    "Daily_U.S._nuclear_capacity_outage (1).csv",
    "Nuclear_Plant_Outages_for_3_6_2026.csv",
    "930-data-export.csv",
    "930-data-export (1).csv",
    "930-data-export (2).csv",
    "table1.csv",
    "table14.csv",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "na", "n/a"}:
        return None
    text = text.replace(",", "").replace("$", "").replace("%", "")
    if text in {"-", "--"}:
        return None
    try:
        out = float(text)
    except ValueError:
        return None
    if not math.isfinite(out):
        return None
    return out


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def provider_from_path(path: Path) -> str:
    try:
        return path.relative_to(LIVE_MEASURED).parts[0].upper()
    except ValueError:
        return path.stem.upper().replace(" ", "_")


def lane_for(path: Path, provider: str) -> str:
    haystack = f"{provider} {path.name} {path.parent.name}".lower()
    for lane, hints in LANE_HINTS.items():
        if any(hint in haystack for hint in hints):
            return lane
    return "general_real_noise"


def read_csv_rows(path: Path, limit: int = 100_000) -> tuple[list[dict[str, str]], list[str], str | None]:
    encodings = ["utf-8-sig", "utf-8", "cp1252"]
    last_error: str | None = None
    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                sample = handle.read(8192)
                handle.seek(0)
                dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
                reader = csv.DictReader(handle, dialect=dialect)
                rows = []
                for idx, row in enumerate(reader):
                    if idx >= limit:
                        break
                    rows.append({str(k): ("" if v is None else str(v)) for k, v in row.items() if k is not None})
                return rows, list(reader.fieldnames or []), None
        except Exception as exc:  # best-effort intake across messy exports
            last_error = f"{type(exc).__name__}: {exc}"
    return [], [], last_error


def robust_outliers(values: list[float]) -> int:
    if len(values) < 5:
        return 0
    center = median(values)
    deviations = [abs(v - center) for v in values]
    mad = median(deviations)
    if mad == 0:
        return 0
    return sum(1 for v in values if abs(0.6745 * (v - center) / mad) > 3.5)


def lag1_autocorr(values: list[float]) -> float | None:
    if len(values) < 3:
        return None
    left = values[:-1]
    right = values[1:]
    mean_l = sum(left) / len(left)
    mean_r = sum(right) / len(right)
    num = sum((a - mean_l) * (b - mean_r) for a, b in zip(left, right))
    den_l = sum((a - mean_l) ** 2 for a in left)
    den_r = sum((b - mean_r) ** 2 for b in right)
    den = math.sqrt(den_l * den_r)
    return None if den == 0 else num / den


def mae(values: list[float], mode: str) -> float | None:
    if len(values) < 3:
        return None
    errors: list[float] = []
    prev_ema = values[0]
    alpha = 0.3
    for idx in range(1, len(values)):
        if mode == "persistence":
            pred = values[idx - 1]
        elif mode == "rolling_mean_5":
            window = values[max(0, idx - 5) : idx]
            pred = sum(window) / len(window)
        elif mode == "exp_smoothing_0_3":
            pred = prev_ema
            prev_ema = alpha * values[idx] + (1 - alpha) * prev_ema
        else:
            raise ValueError(mode)
        errors.append(abs(values[idx] - pred))
    return sum(errors) / len(errors) if errors else None


def column_metrics(values: list[float]) -> dict[str, Any]:
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
    delta_abs = [abs(d) for d in deltas]
    mean = sum(values) / len(values) if values else None
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1) if mean is not None and len(values) > 1 else 0.0
    baseline_mae = {
        name: mae(values, name)
        for name in ["persistence", "rolling_mean_5", "exp_smoothing_0_3"]
    }
    ranked = sorted((v, k) for k, v in baseline_mae.items() if v is not None)
    return {
        "n": len(values),
        "mean": round(mean, 8) if mean is not None else None,
        "stdev": round(math.sqrt(variance), 8),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "delta_abs_median": round(median(delta_abs), 8) if delta_abs else None,
        "delta_abs_max": max(delta_abs) if delta_abs else None,
        "robust_outlier_count": robust_outliers(values),
        "shock_count_delta_mad_6": robust_outliers(deltas),
        "lag1_autocorr": round(lag1_autocorr(values), 8) if lag1_autocorr(values) is not None else None,
        "baseline_probe": {
            "best_named_baseline": ranked[0][1] if ranked else None,
            "best_mae": round(ranked[0][0], 8) if ranked else None,
            "all_mae": {k: (round(v, 8) if v is not None else None) for k, v in baseline_mae.items()},
        },
    }


def analyze_csv(path: Path) -> dict[str, Any]:
    rows, fieldnames, error = read_csv_rows(path)
    provider = provider_from_path(path)
    lane = lane_for(path, provider)
    payload: dict[str, Any] = {
        "provider": provider,
        "lane": lane,
        "path": rel(path),
        "absolute_path": str(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "rows_read": len(rows),
        "columns": len(fieldnames),
        "parse_error": error,
    }
    if error or not rows:
        payload.update(
            {
                "promotion_state": "blocked_parse_or_empty",
                "numeric_samples": 0,
                "ready_for_locked_replay": False,
                "claim_use": "inventory_only",
            }
        )
        return payload

    numeric_columns: dict[str, list[float]] = {}
    missing_cells = 0
    for name in fieldnames:
        vals = []
        for row in rows:
            raw = row.get(name, "")
            if raw == "":
                missing_cells += 1
            parsed = parse_float(raw)
            if parsed is not None:
                vals.append(parsed)
        if len(vals) >= 3:
            numeric_columns[name] = vals

    numeric_samples = sum(len(vals) for vals in numeric_columns.values())
    timestamp_like = [
        name
        for name in fieldnames
        if re.search(r"(date|time|period|timestamp|datetime|created|updated)", name, flags=re.I)
    ]
    structural_column_re = re.compile(
        r"(^|_|\b)(id|index|rank|row|unnamed|time|date|period|year|month|yyyy|yyyymm|epoch|column_order|order|number)(_|$|\b)",
        flags=re.I,
    )
    signal_candidates = [
        name
        for name in numeric_columns
        if name not in timestamp_like and not structural_column_re.search(name)
    ]
    signal_name = None
    if numeric_columns:
        candidate_pool = signal_candidates or list(numeric_columns)
        signal_name = max(candidate_pool, key=lambda k: (len(numeric_columns[k]), len(set(numeric_columns[k]))))
        signal = numeric_columns[signal_name]
        metrics = column_metrics(signal)
    else:
        metrics = {}

    ready = bool(len(rows) >= 20 and numeric_samples >= 20 and signal_name and metrics.get("baseline_probe", {}).get("best_mae") is not None)
    strong = bool(ready and len(rows) >= 100 and numeric_samples >= 100)
    payload.update(
        {
            "numeric_columns": len(numeric_columns),
            "numeric_samples": numeric_samples,
            "missing_cells": missing_cells,
            "timestamp_like_columns": timestamp_like[:8],
            "primary_signal_column": signal_name,
            "primary_signal_selection": "value_column" if signal_name in signal_candidates else "fallback_structural_column",
            "primary_signal_metrics": metrics,
            "ready_for_locked_replay": ready,
            "promotion_state": "strong_real_noise_replay_candidate" if strong else ("real_noise_replay_candidate" if ready else "thin_real_noise_inventory"),
            "claim_use": "locked_replay_ready_not_field_validated" if ready else "inventory_only",
        }
    )
    return payload


def discover_csvs() -> list[Path]:
    paths: list[Path] = []
    if LIVE_MEASURED.exists():
        paths.extend(sorted(LIVE_MEASURED.rglob("*.csv")))
    if LEGACY_DATA.exists():
        for name in LEGACY_CSV_ALLOWLIST:
            candidate = LEGACY_DATA / name
            if candidate.exists():
                paths.append(candidate)
    seen = set()
    unique = []
    for path in paths:
        key = str(path).lower()
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def build_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Real Noise Promotion Sweep",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        "## Boundary",
        "",
        BOUNDARY,
        "",
        "## Summary",
        "",
        f"- CSV snapshots scanned: {summary['csv_snapshots_scanned']}",
        f"- Ready for locked replay: {summary['ready_for_locked_replay']}",
        f"- Strong real-noise candidates: {summary['strong_real_noise_candidates']}",
        f"- Rows read: {summary['rows_read']:,}",
        f"- Numeric samples: {summary['numeric_samples']:,}",
        f"- Lanes with ready data: {summary['lanes_with_ready_data']}",
        "",
        "## Strongest Ready Sources",
        "",
        "| Provider | Lane | Rows | Numeric Samples | Signal | Best Baseline MAE | State |",
        "|---|---:|---:|---:|---|---:|---|",
    ]
    ready = [s for s in payload["sources"] if s.get("ready_for_locked_replay")]
    ready.sort(key=lambda s: (s.get("numeric_samples", 0), s.get("rows_read", 0)), reverse=True)
    for source in ready[:20]:
        metrics = source.get("primary_signal_metrics", {})
        probe = metrics.get("baseline_probe", {}) if isinstance(metrics, dict) else {}
        lines.append(
            "| {provider} | {lane} | {rows} | {samples} | {signal} | {mae} | {state} |".format(
                provider=source.get("provider"),
                lane=source.get("lane"),
                rows=source.get("rows_read"),
                samples=source.get("numeric_samples"),
                signal=source.get("primary_signal_column"),
                mae=probe.get("best_mae"),
                state=source.get("promotion_state"),
            )
        )
    lines.extend(
        [
            "",
            "## Next Actions",
            "",
            "1. Run the locked champion-vs-baseline replay on each ready source lane.",
            "2. Freeze per-source replay outputs with hashes and negative-evidence notes.",
            "3. Ask an external buyer/lab to approve held-out data, acceptance metric, and avoided-cost conversion.",
            "4. Promote dollar claims only after the outside owner accepts the replay protocol and result interpretation.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    sources = [analyze_csv(path) for path in discover_csvs()]
    lane_rollup: dict[str, dict[str, Any]] = {}
    for source in sources:
        lane = str(source.get("lane", "general_real_noise"))
        row = lane_rollup.setdefault(
            lane,
            {
                "sources": 0,
                "ready_sources": 0,
                "rows_read": 0,
                "numeric_samples": 0,
                "strongest_providers": [],
            },
        )
        row["sources"] += 1
        row["rows_read"] += int(source.get("rows_read") or 0)
        row["numeric_samples"] += int(source.get("numeric_samples") or 0)
        if source.get("ready_for_locked_replay"):
            row["ready_sources"] += 1
            row["strongest_providers"].append(source.get("provider"))

    ready = [s for s in sources if s.get("ready_for_locked_replay")]
    strong = [s for s in sources if s.get("promotion_state") == "strong_real_noise_replay_candidate"]
    payload: dict[str, Any] = {
        "schema": "real_noise_promotion_sweep_v1",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "summary": {
            "csv_snapshots_scanned": len(sources),
            "ready_for_locked_replay": len(ready),
            "strong_real_noise_candidates": len(strong),
            "rows_read": sum(int(s.get("rows_read") or 0) for s in sources),
            "numeric_samples": sum(int(s.get("numeric_samples") or 0) for s in sources),
            "lanes_with_ready_data": sum(1 for lane in lane_rollup.values() if lane["ready_sources"] > 0),
            "field_validation_claim_allowed": False,
            "fixed_dollar_claim_allowed": False,
            "next_claim_stage": "internal_real_noise_locked_replay",
        },
        "lane_rollup": lane_rollup,
        "sources": sources,
        "claim_ladder": [
            {
                "stage": "real_noise_inventory",
                "allowed": True,
                "language": "We have hashed real-world noisy snapshots across multiple sectors.",
            },
            {
                "stage": "locked_replay_ready",
                "allowed": bool(ready),
                "language": "These sources are ready for locked replay against named baselines.",
            },
            {
                "stage": "field_validated_savings",
                "allowed": False,
                "language": "Blocked until an outside owner supplies or approves held-out data, metric, and economic conversion.",
            },
        ],
        "outputs": {
            "ops_json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["artifact_sha256"] = stable_sha256({k: v for k, v in payload.items() if k != "artifact_sha256"})
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, build_markdown(payload))
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
