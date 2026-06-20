from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
GRANT_DIR = ROOT / "grant_submissions" / "NV063_HarborSentinel"

SPLIT_JSON = OUT_OPS / "harbor_ais_heldout_splits_latest.json"
REPO_JSON = OUT_OPS / "harbor_public_ais_gate_latest.json"
REPO_MD = GRANT_DIR / "NV063_PUBLIC_AIS_GATE_2026-06-20.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    return number if number == number else None


def parse_time(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def percentile(values: list[float], q: float) -> float | None:
    clean = sorted(value for value in values if value == value)
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    pos = (len(clean) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return clean[lo]
    return clean[lo] * (hi - pos) + clean[hi] * (pos - lo)


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_nm = 3440.065
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return radius_nm * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def read_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            timestamp = parse_time(str(raw.get("BaseDateTime", "")))
            lat = safe_float(raw.get("LAT"))
            lon = safe_float(raw.get("LON"))
            sog = safe_float(raw.get("SOG"))
            cog = safe_float(raw.get("COG"))
            mmsi = str(raw.get("MMSI", "")).strip()
            rows.append(
                {
                    "mmsi": mmsi,
                    "timestamp": timestamp,
                    "lat": lat,
                    "lon": lon,
                    "sog": sog,
                    "cog": cog,
                    "vessel_type": str(raw.get("VesselType", "")).strip(),
                    "complete_core": bool(mmsi and timestamp and lat is not None and lon is not None),
                    "complete_motion": bool(sog is not None and cog is not None),
                }
            )
    return rows


def row_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    core = [row for row in rows if row["complete_core"]]
    motion = [row for row in rows if row["complete_motion"]]
    mmsi = {row["mmsi"] for row in core if row["mmsi"]}
    times = [row["timestamp"] for row in core if row["timestamp"]]
    lats = [row["lat"] for row in core if row["lat"] is not None]
    lons = [row["lon"] for row in core if row["lon"] is not None]
    vessel_types = Counter(row["vessel_type"] or "unknown" for row in rows)
    return {
        "rows": total,
        "core_completeness": len(core) / total if total else 0.0,
        "motion_completeness": len(motion) / total if total else 0.0,
        "unique_mmsi": len(mmsi),
        "time_min": min(times).isoformat() if times else "",
        "time_max": max(times).isoformat() if times else "",
        "lat_min": min(lats) if lats else None,
        "lat_max": max(lats) if lats else None,
        "lon_min": min(lons) if lons else None,
        "lon_max": max(lons) if lons else None,
        "top_vessel_types": vessel_types.most_common(8),
    }


def track_features(rows: list[dict[str, Any]], *, min_points: int) -> dict[str, Any]:
    by_mmsi: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["complete_core"]:
            by_mmsi[row["mmsi"]].append(row)
    track_counts: list[int] = []
    intervals_minutes: list[float] = []
    derived_speed_knots: list[float] = []
    sog_values: list[float] = []
    eligible_tracks = 0
    for group in by_mmsi.values():
        group.sort(key=lambda item: item["timestamp"])
        if len(group) < min_points:
            continue
        eligible_tracks += 1
        track_counts.append(len(group))
        for row in group:
            if row["sog"] is not None:
                sog_values.append(float(row["sog"]))
        for left, right in zip(group, group[1:]):
            minutes = (right["timestamp"] - left["timestamp"]).total_seconds() / 60.0
            if minutes <= 0:
                continue
            intervals_minutes.append(minutes)
            distance_nm = haversine_nm(float(left["lat"]), float(left["lon"]), float(right["lat"]), float(right["lon"]))
            derived_speed_knots.append(distance_nm / (minutes / 60.0))
    return {
        "eligible_tracks": eligible_tracks,
        "median_points_per_eligible_track": median(track_counts) if track_counts else 0,
        "median_interval_minutes": median(intervals_minutes) if intervals_minutes else None,
        "p95_interval_minutes": percentile(intervals_minutes, 0.95),
        "sog_p95_knots": percentile(sog_values, 0.95),
        "sog_p99_knots": percentile(sog_values, 0.99),
        "derived_speed_p95_knots": percentile(derived_speed_knots, 0.95),
        "derived_speed_p99_knots": percentile(derived_speed_knots, 0.99),
        "segment_count": len(derived_speed_knots),
    }


def validation_diagnostics(rows: list[dict[str, Any]], dev_features: dict[str, Any], *, min_points: int) -> dict[str, Any]:
    features = track_features(rows, min_points=min_points)
    sog_threshold = dev_features.get("sog_p99_knots")
    derived_threshold = dev_features.get("derived_speed_p99_knots")
    sog_values = [float(row["sog"]) for row in rows if row.get("sog") is not None]
    sog_outliers = [value for value in sog_values if sog_threshold is not None and value > float(sog_threshold)]

    by_mmsi: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["complete_core"]:
            by_mmsi[row["mmsi"]].append(row)
    derived_values: list[float] = []
    for group in by_mmsi.values():
        group.sort(key=lambda item: item["timestamp"])
        if len(group) < min_points:
            continue
        for left, right in zip(group, group[1:]):
            minutes = (right["timestamp"] - left["timestamp"]).total_seconds() / 60.0
            if minutes <= 0:
                continue
            distance_nm = haversine_nm(float(left["lat"]), float(left["lon"]), float(right["lat"]), float(right["lon"]))
            derived_values.append(distance_nm / (minutes / 60.0))
    derived_outliers = [
        value
        for value in derived_values
        if derived_threshold is not None and value > float(derived_threshold)
    ]
    return {
        **features,
        "frozen_dev_thresholds": {
            "sog_p99_knots": sog_threshold,
            "derived_speed_p99_knots": derived_threshold,
            "note": "Thresholds are derived from the development split only and applied unchanged to validation.",
        },
        "validation_sog_over_dev_p99_rate": len(sog_outliers) / len(sog_values) if sog_values else 0.0,
        "validation_derived_speed_over_dev_p99_rate": len(derived_outliers) / len(derived_values) if derived_values else 0.0,
        "diagnostic_boundary": "Outlier rates are data-quality diagnostics, not threat detection performance.",
    }


def build_gate(split_json: Path, min_track_points: int, *, write_outputs: bool = True) -> dict[str, Any]:
    split = read_json(split_json)
    dev_path = Path(str(split.get("splits", {}).get("development", {}).get("path", "")))
    val_path = Path(str(split.get("splits", {}).get("validation", {}).get("path", "")))
    if not dev_path.exists() or not val_path.exists():
        raise FileNotFoundError("Development or validation split CSV is missing.")
    dev_rows = read_rows(dev_path)
    val_rows = read_rows(val_path)
    dev_metrics = row_metrics(dev_rows)
    val_metrics = row_metrics(val_rows)
    dev_features = track_features(dev_rows, min_points=min_track_points)
    val_diag = validation_diagnostics(val_rows, dev_features, min_points=min_track_points)
    dev_mmsi = {row["mmsi"] for row in dev_rows if row["complete_core"]}
    val_mmsi = {row["mmsi"] for row in val_rows if row["complete_core"]}
    overlap = dev_mmsi & val_mmsi

    gate_checks = {
        "development_rows_at_least_10000": dev_metrics["rows"] >= 10000,
        "validation_rows_at_least_10000": val_metrics["rows"] >= 10000,
        "core_completeness_at_least_99pct": min(dev_metrics["core_completeness"], val_metrics["core_completeness"]) >= 0.99,
        "overlap_mmsi_at_least_100": len(overlap) >= 100,
        "validation_eligible_tracks_at_least_50": int(val_diag["eligible_tracks"]) >= 50,
    }
    posture = "PUBLIC_AIS_SINGLE_LANE_GATE_READY" if all(gate_checks.values()) else "PUBLIC_AIS_SINGLE_LANE_GATE_BLOCKED"

    payload = {
        "generated_utc": now_utc(),
        "schema": "harbor_public_ais_gate_v1",
        "posture": posture,
        "source_split_manifest": str(split_json),
        "selected_region": split.get("selected_region", {}),
        "raw_source": split.get("raw_source", {}),
        "input_hashes": {
            "development_csv_sha256": sha256_file(dev_path),
            "validation_csv_sha256": sha256_file(val_path),
        },
        "development": {
            "file": str(dev_path),
            "row_metrics": dev_metrics,
            "track_features": dev_features,
        },
        "validation": {
            "file": str(val_path),
            "row_metrics": val_metrics,
            "track_features_and_diagnostics": val_diag,
        },
        "holdout_overlap": {
            "development_unique_mmsi": len(dev_mmsi),
            "validation_unique_mmsi": len(val_mmsi),
            "overlap_mmsi": len(overlap),
        },
        "gate_checks": gate_checks,
        "claim_boundary": (
            "This gate establishes public AIS single-lane data readiness, schema coverage, "
            "track overlap, and frozen development-to-validation diagnostics. It does not "
            "establish HarborSentinel detection performance, multi-source fusion performance, "
            "ADS-B licensing, radar validation, Navy/SSDS integration, field performance, "
            "or operational suitability."
        ),
    }

    if write_outputs:
        split_data_root = Path(str(split.get("data_root", "")))
        manifest_root = split_data_root / "manifests" if split_data_root else None
        if manifest_root:
            tag = utc_tag()
            tagged = manifest_root / f"harbor_public_ais_gate_{tag}.json"
            latest = manifest_root / "harbor_public_ais_gate_latest.json"
            payload["external_manifests"] = {"tagged": str(tagged), "latest": str(latest)}
            write_json(tagged, payload)
            write_json(latest, payload)
        write_json(REPO_JSON, payload)
        write_text(REPO_MD, render_markdown(payload))
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    dev = payload["development"]["row_metrics"]
    val = payload["validation"]["row_metrics"]
    diag = payload["validation"]["track_features_and_diagnostics"]
    return "\n".join(
        [
            "# HarborSentinel Public AIS Single-Lane Gate",
            "",
            f"Generated UTC: {payload['generated_utc']}",
            "",
            f"Posture: `{payload['posture']}`",
            "",
            "## Selected Region",
            "",
            f"- Region: {payload['selected_region'].get('label')} (`{payload['selected_region'].get('region_id')}`)",
            "",
            "## Split Coverage",
            "",
            f"- Development rows: {dev['rows']}; unique MMSI: {dev['unique_mmsi']}; core completeness: {dev['core_completeness']:.4f}",
            f"- Validation rows: {val['rows']}; unique MMSI: {val['unique_mmsi']}; core completeness: {val['core_completeness']:.4f}",
            f"- MMSI overlap: {payload['holdout_overlap']['overlap_mmsi']}",
            "",
            "## Frozen Validation Diagnostics",
            "",
            f"- Validation eligible tracks: {diag['eligible_tracks']}",
            f"- Validation SOG over dev p99 rate: {diag['validation_sog_over_dev_p99_rate']:.4f}",
            f"- Validation derived-speed over dev p99 rate: {diag['validation_derived_speed_over_dev_p99_rate']:.4f}",
            "- Boundary: outlier rates are data-quality diagnostics, not threat detection performance.",
            "",
            "## Gate Checks",
            "",
            *[f"- {name}: {value}" for name, value in payload["gate_checks"].items()],
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a public AIS single-lane readiness gate on held-out HarborSentinel splits.")
    parser.add_argument("--split-json", default=str(SPLIT_JSON))
    parser.add_argument("--min-track-points", type=int, default=4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_gate(Path(args.split_json), min_track_points=max(2, int(args.min_track_points)))
    print(
        json.dumps(
            {
                "posture": payload["posture"],
                "region": payload["selected_region"].get("region_id"),
                "development_rows": payload["development"]["row_metrics"]["rows"],
                "validation_rows": payload["validation"]["row_metrics"]["rows"],
                "overlap_mmsi": payload["holdout_overlap"]["overlap_mmsi"],
                "json": str(REPO_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(REPO_MD.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
