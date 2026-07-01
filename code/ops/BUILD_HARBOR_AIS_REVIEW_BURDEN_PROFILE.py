from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OPS_DIR = Path(__file__).resolve().parent
if str(OPS_DIR) not in sys.path:
    sys.path.insert(0, str(OPS_DIR))

from BUILD_HARBOR_AIS_INJECTION_BENCHMARK import (  # noqa: E402
    angle_delta_deg,
    haversine_nm,
    learn_thresholds,
    motion_score,
    parse_time,
    percentile,
    read_json,
    safe_float,
    sha256_file,
    write_json,
    write_text,
)


OUT_OPS = ROOT / "out" / "ops"
GRANT_DIR = ROOT / "grant_submissions" / "NV063_HarborSentinel"
RUN_ROOT = ROOT / "out" / "harbor_ais_review_burden"

SPLIT_JSON = OUT_OPS / "harbor_ais_heldout_splits_latest.json"
OUT_JSON = OUT_OPS / "harbor_ais_review_burden_profile_latest.json"
OUT_MD = GRANT_DIR / "NV063_AIS_REVIEW_BURDEN_PROFILE_2026-06-21.md"

CLAIM_BOUNDARY = (
    "This is an unlabeled public AIS review-burden profile. It estimates natural "
    "candidate queues, density context, and capped analyst-review workload from "
    "held-out validation traffic. It does not measure precision, false positives, "
    "real threat detection, multi-source fusion, ADS-B/radar performance, Navy/SSDS "
    "integration, field validation, or operational suitability."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def read_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            mmsi = str(raw.get("MMSI", "")).strip()
            timestamp = parse_time(raw.get("BaseDateTime"))
            lat = safe_float(raw.get("LAT"))
            lon = safe_float(raw.get("LON"))
            sog = safe_float(raw.get("SOG"))
            cog = safe_float(raw.get("COG"))
            if not (mmsi and timestamp and lat is not None and lon is not None):
                continue
            rows.append(
                {
                    "mmsi": mmsi,
                    "timestamp": timestamp,
                    "lat": lat,
                    "lon": lon,
                    "sog": sog,
                    "cog": cog,
                }
            )
    return rows


def hour_key(value: datetime) -> str:
    return value.replace(minute=0, second=0, microsecond=0).isoformat()


def grid_key(lat: float, lon: float, *, grid_degrees: float) -> str:
    lat_cell = math.floor(lat / grid_degrees) * grid_degrees
    lon_cell = math.floor(lon / grid_degrees) * grid_degrees
    return f"{lat_cell:.3f}:{lon_cell:.3f}"


def build_context_segments(
    rows: list[dict[str, Any]],
    *,
    max_interval_minutes: float,
    grid_degrees: float,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["mmsi"]].append(row)
    segments: list[dict[str, Any]] = []
    for mmsi, group in grouped.items():
        group.sort(key=lambda item: item["timestamp"])
        for left, right in zip(group, group[1:]):
            minutes = (right["timestamp"] - left["timestamp"]).total_seconds() / 60.0
            if minutes <= 0 or minutes > max_interval_minutes:
                continue
            mid_lat = (float(left["lat"]) + float(right["lat"])) / 2.0
            mid_lon = (float(left["lon"]) + float(right["lon"])) / 2.0
            derived_speed = haversine_nm(
                float(left["lat"]),
                float(left["lon"]),
                float(right["lat"]),
                float(right["lon"]),
            ) / (minutes / 60.0)
            sog_values = [value for value in (left.get("sog"), right.get("sog")) if value is not None]
            sog = sum(float(value) for value in sog_values) / len(sog_values) if sog_values else 0.0
            turn = angle_delta_deg(left.get("cog"), right.get("cog"))
            segment = {
                "mmsi": mmsi,
                "timestamp": right["timestamp"],
                "hour": hour_key(right["timestamp"]),
                "grid": grid_key(mid_lat, mid_lon, grid_degrees=grid_degrees),
                "minutes": minutes,
                "lat": mid_lat,
                "lon": mid_lon,
                "sog_knots": max(0.0, sog),
                "derived_speed_knots": max(0.0, derived_speed),
                "speed_gap_knots": abs(max(0.0, derived_speed) - max(0.0, sog)),
                "turn_rate_deg_per_min": turn / minutes,
            }
            segments.append(segment)
    return segments


def motion_features(segment: dict[str, Any]) -> dict[str, float]:
    return {
        "sog_knots": float(segment["sog_knots"]),
        "derived_speed_knots": float(segment["derived_speed_knots"]),
        "speed_gap_knots": float(segment["speed_gap_knots"]),
        "turn_rate_deg_per_min": float(segment["turn_rate_deg_per_min"]),
    }


def density_counts(segments: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for segment in segments:
        counts[(str(segment["hour"]), str(segment["grid"]))] += 1
    return dict(counts)


def density_thresholds(dev_segments: list[dict[str, Any]]) -> dict[str, float]:
    counts = list(density_counts(dev_segments).values())
    return {
        "sparse_max": percentile([float(value) for value in counts], 0.50, floor=1.0),
        "normal_max": percentile([float(value) for value in counts], 0.90, floor=1.0),
    }


def density_tier(count: int, thresholds: dict[str, float]) -> str:
    if count <= thresholds["sparse_max"]:
        return "sparse"
    if count <= thresholds["normal_max"]:
        return "normal"
    return "dense"


def enrich_segments(
    segments: list[dict[str, Any]],
    *,
    thresholds: dict[str, float],
    density_by_cell_hour: dict[tuple[str, str], int],
    density_bands: dict[str, float],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for segment in segments:
        score = motion_score(motion_features(segment), thresholds)
        density = density_by_cell_hour.get((str(segment["hour"]), str(segment["grid"])), 0)
        enriched.append(
            {
                **segment,
                "motion_score": score,
                "candidate": score > 1.0,
                "density_count": density,
                "density_tier": density_tier(density, density_bands),
            }
        )
    return enriched


def ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def by_hour_summary(segments: list[dict[str, Any]], *, caps: tuple[int, ...]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for segment in segments:
        grouped[str(segment["hour"])].append(segment)
    rows: list[dict[str, Any]] = []
    for hour, group in sorted(grouped.items()):
        candidates = [segment for segment in group if segment["candidate"]]
        ordered_candidates = sorted(candidates, key=lambda row: float(row["motion_score"]), reverse=True)
        row: dict[str, Any] = {
            "hour": hour,
            "segments": len(group),
            "candidates": len(candidates),
            "candidate_rate": ratio(len(candidates), len(group)),
            "max_motion_score": max((float(segment["motion_score"]) for segment in group), default=0.0),
        }
        for cap in caps:
            row[f"retained_at_cap_{cap}"] = min(cap, len(ordered_candidates))
            row[f"retained_fraction_at_cap_{cap}"] = ratio(min(cap, len(ordered_candidates)), len(candidates))
        rows.append(row)
    return rows


def tier_summary(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tier in ("sparse", "normal", "dense"):
        group = [segment for segment in segments if segment["density_tier"] == tier]
        candidates = [segment for segment in group if segment["candidate"]]
        rows.append(
            {
                "density_tier": tier,
                "segments": len(group),
                "candidates": len(candidates),
                "candidate_rate": ratio(len(candidates), len(group)),
                "mean_density_count": mean(float(segment["density_count"]) for segment in group) if group else 0.0,
            }
        )
    return rows


def aggregate_queue(hour_rows: list[dict[str, Any]], *, caps: tuple[int, ...]) -> dict[str, Any]:
    candidates_per_hour = [float(row["candidates"]) for row in hour_rows]
    segments_per_hour = [float(row["segments"]) for row in hour_rows]
    total_candidates = sum(candidates_per_hour)
    total_segments = sum(segments_per_hour)
    cap_rows = {}
    for cap in caps:
        retained = sum(float(row[f"retained_at_cap_{cap}"]) for row in hour_rows)
        cap_rows[str(cap)] = {
            "cap_per_hour": cap,
            "retained_candidates": retained,
            "retained_candidate_fraction": ratio(retained, total_candidates),
            "mean_retained_per_hour": mean(float(row[f"retained_at_cap_{cap}"]) for row in hour_rows) if hour_rows else 0.0,
        }
    return {
        "validation_hours": len(hour_rows),
        "validation_segments": int(total_segments),
        "validation_candidates": int(total_candidates),
        "validation_candidate_rate": ratio(total_candidates, total_segments),
        "mean_segments_per_hour": mean(segments_per_hour) if segments_per_hour else 0.0,
        "mean_candidates_per_hour": mean(candidates_per_hour) if candidates_per_hour else 0.0,
        "p95_candidates_per_hour": percentile(candidates_per_hour, 0.95, floor=0.0),
        "max_candidates_per_hour": max(candidates_per_hour) if candidates_per_hour else 0.0,
        "hours_with_candidates": sum(1 for value in candidates_per_hour if value > 0),
        "capped_review_queues": cap_rows,
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def manifest_for(paths: list[Path], generated_utc: str) -> dict[str, Any]:
    return {
        "schema": "harbor_ais_review_burden_manifest_v1",
        "generated_utc": generated_utc,
        "files": {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in paths
        },
    }


def build_profile(
    *,
    split_json: Path = SPLIT_JSON,
    out_dir: Path,
    max_interval_minutes: float = 120.0,
    grid_degrees: float = 0.05,
    caps: tuple[int, ...] = (5, 10, 20),
) -> dict[str, Any]:
    split = read_json(split_json)
    dev_path = Path(str(split.get("splits", {}).get("development", {}).get("path", "")))
    val_path = Path(str(split.get("splits", {}).get("validation", {}).get("path", "")))
    if not dev_path.exists() or not val_path.exists():
        raise FileNotFoundError("Development or validation split CSV is missing.")
    out_dir.mkdir(parents=True, exist_ok=False)

    dev_segments = build_context_segments(
        read_rows(dev_path),
        max_interval_minutes=max_interval_minutes,
        grid_degrees=grid_degrees,
    )
    val_segments = build_context_segments(
        read_rows(val_path),
        max_interval_minutes=max_interval_minutes,
        grid_degrees=grid_degrees,
    )
    thresholds = learn_thresholds([motion_features(segment) for segment in dev_segments])
    density_bands = density_thresholds(dev_segments)
    dev_enriched = enrich_segments(
        dev_segments,
        thresholds=thresholds,
        density_by_cell_hour=density_counts(dev_segments),
        density_bands=density_bands,
    )
    val_enriched = enrich_segments(
        val_segments,
        thresholds=thresholds,
        density_by_cell_hour=density_counts(val_segments),
        density_bands=density_bands,
    )
    hour_rows = by_hour_summary(val_enriched, caps=caps)
    tier_rows = tier_summary(val_enriched)
    generated_utc = now_utc()
    summary = {
        "schema": "harbor_ais_review_burden_profile_v1",
        "generated_utc": generated_utc,
        "posture": "PUBLIC_AIS_REVIEW_BURDEN_PROFILE_READY",
        "source_split_manifest": rel(split_json),
        "selected_region": split.get("selected_region", {}),
        "input_hashes": {
            "development_csv_sha256": sha256_file(dev_path),
            "validation_csv_sha256": sha256_file(val_path),
        },
        "configuration": {
            "max_interval_minutes": max_interval_minutes,
            "grid_degrees": grid_degrees,
            "review_caps_per_hour": list(caps),
            "threshold_source": "development split only",
            "density_band_source": "development split only",
        },
        "development": {
            "rows": split.get("splits", {}).get("development", {}).get("rows"),
            "segments": len(dev_enriched),
            "candidate_rate": ratio(sum(1 for row in dev_enriched if row["candidate"]), len(dev_enriched)),
        },
        "validation": {
            "rows": split.get("splits", {}).get("validation", {}).get("rows"),
            "segments": len(val_enriched),
        },
        "thresholds": thresholds,
        "density_thresholds": density_bands,
        "review_queue": aggregate_queue(hour_rows, caps=caps),
        "density_tiers": tier_rows,
        "claim_gate": {
            "ready_for_portal_upload": False,
            "ready_for_submit": False,
            "measures_false_positive_rate": False,
            "proves_field_performance": False,
            "proves_operational_suitability": False,
        },
        "claim_boundary": CLAIM_BOUNDARY,
    }

    summary_path = out_dir / "summary.json"
    hour_path = out_dir / "queue_by_hour.csv"
    tier_path = out_dir / "density_tiers.csv"
    scorecard_path = out_dir / "SCORECARD.md"
    manifest_path = out_dir / "manifest.sha256.json"

    write_json(summary_path, summary)
    write_csv(
        hour_path,
        hour_rows,
        [
            "hour",
            "segments",
            "candidates",
            "candidate_rate",
            "max_motion_score",
            *[f"retained_at_cap_{cap}" for cap in caps],
            *[f"retained_fraction_at_cap_{cap}" for cap in caps],
        ],
    )
    write_csv(
        tier_path,
        tier_rows,
        ["density_tier", "segments", "candidates", "candidate_rate", "mean_density_count"],
    )
    write_text(scorecard_path, render_markdown(summary))
    write_json(manifest_path, manifest_for([summary_path, hour_path, tier_path, scorecard_path], generated_utc))
    return summary


def render_markdown(payload: dict[str, Any]) -> str:
    queue = payload["review_queue"]
    caps = payload["configuration"]["review_caps_per_hour"]
    region = payload["selected_region"]
    lines = [
        "# HarborSentinel AIS Review-Burden Profile",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        f"Posture: `{payload['posture']}`",
        "",
        "## Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Region And Inputs",
        "",
        f"- Region: {region.get('label')} (`{region.get('region_id')}`)",
        f"- Development segments: {payload['development']['segments']}",
        f"- Validation segments: {payload['validation']['segments']}",
        f"- Development CSV SHA-256: `{payload['input_hashes']['development_csv_sha256']}`",
        f"- Validation CSV SHA-256: `{payload['input_hashes']['validation_csv_sha256']}`",
        "",
        "## Natural Review Queue",
        "",
        f"- Validation hours: {queue['validation_hours']}",
        f"- Validation candidate rate: {queue['validation_candidate_rate']:.4f}",
        f"- Mean candidates/hour: {queue['mean_candidates_per_hour']:.3f}",
        f"- P95 candidates/hour: {queue['p95_candidates_per_hour']:.3f}",
        f"- Max candidates/hour: {queue['max_candidates_per_hour']:.0f}",
        f"- Hours with candidates: {queue['hours_with_candidates']}",
        "",
        "## Capped Review Queues",
        "",
        "| Cap/hour | Retained candidate fraction | Mean retained/hour |",
        "|---:|---:|---:|",
    ]
    for cap in caps:
        row = queue["capped_review_queues"][str(cap)]
        lines.append(
            f"| {cap} | {row['retained_candidate_fraction']:.4f} | {row['mean_retained_per_hour']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Density Context",
            "",
            "| Density tier | Segments | Candidates | Candidate rate | Mean density count |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in payload["density_tiers"]:
        lines.append(
            f"| {row['density_tier']} | {row['segments']} | {row['candidates']} | "
            f"{row['candidate_rate']:.4f} | {row['mean_density_count']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Claim Gate",
            "",
            "- ready_for_portal_upload: false",
            "- ready_for_submit: false",
            "- measures_false_positive_rate: false",
            "- proves_field_performance: false",
            "- proves_operational_suitability: false",
            "",
        ]
    )
    return "\n".join(lines)


def write_latest_outputs(summary: dict[str, Any]) -> None:
    write_json(OUT_JSON, summary)
    write_text(OUT_MD, render_markdown(summary))


def main() -> int:
    out_dir = RUN_ROOT / now_tag()
    summary = build_profile(out_dir=out_dir)
    write_latest_outputs(summary)
    print(
        json.dumps(
            {
                "posture": summary["posture"],
                "validation_candidate_rate": summary["review_queue"]["validation_candidate_rate"],
                "p95_candidates_per_hour": summary["review_queue"]["p95_candidates_per_hour"],
                "out_dir": rel(out_dir),
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
