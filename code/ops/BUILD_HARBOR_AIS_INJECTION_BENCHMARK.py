from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
GRANT_DIR = ROOT / "grant_submissions" / "NV063_HarborSentinel"

SPLIT_JSON = OUT_OPS / "harbor_ais_heldout_splits_latest.json"
OUT_JSON = OUT_OPS / "harbor_ais_injection_benchmark_latest.json"
OUT_MD = GRANT_DIR / "NV063_AIS_INJECTION_BENCHMARK_2026-06-20.md"


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
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


def parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def percentile(values: list[float], q: float, *, floor: float = 0.0) -> float:
    clean = sorted(value for value in values if value == value)
    if not clean:
        return floor
    if len(clean) == 1:
        return max(clean[0], floor)
    pos = (len(clean) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return max(clean[lo], floor)
    value = clean[lo] * (hi - pos) + clean[hi] * (pos - lo)
    return max(value, floor)


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_nm = 3440.065
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return radius_nm * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def angle_delta_deg(left: float | None, right: float | None) -> float:
    if left is None or right is None:
        return 0.0
    return abs((right - left + 180.0) % 360.0 - 180.0)


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


def build_segments(rows: list[dict[str, Any]], *, max_interval_minutes: float) -> list[dict[str, Any]]:
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
            derived_speed = haversine_nm(
                float(left["lat"]),
                float(left["lon"]),
                float(right["lat"]),
                float(right["lon"]),
            ) / (minutes / 60.0)
            sog_values = [value for value in (left.get("sog"), right.get("sog")) if value is not None]
            sog = sum(float(value) for value in sog_values) / len(sog_values) if sog_values else 0.0
            turn = angle_delta_deg(left.get("cog"), right.get("cog"))
            segments.append(
                {
                    "mmsi": mmsi,
                    "minutes": minutes,
                    "sog_knots": max(0.0, sog),
                    "derived_speed_knots": max(0.0, derived_speed),
                    "speed_gap_knots": abs(max(0.0, derived_speed) - max(0.0, sog)),
                    "turn_rate_deg_per_min": turn / minutes,
                }
            )
    return segments


def learn_thresholds(segments: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "sog_knots_p99": percentile([row["sog_knots"] for row in segments], 0.99, floor=0.1),
        "derived_speed_knots_p99": percentile([row["derived_speed_knots"] for row in segments], 0.99, floor=0.1),
        "speed_gap_knots_p99": percentile([row["speed_gap_knots"] for row in segments], 0.99, floor=0.1),
        "turn_rate_deg_per_min_p99": percentile([row["turn_rate_deg_per_min"] for row in segments], 0.99, floor=0.1),
    }


def motion_score(segment: dict[str, float], thresholds: dict[str, float]) -> float:
    ratios = [
        segment["sog_knots"] / thresholds["sog_knots_p99"],
        segment["derived_speed_knots"] / thresholds["derived_speed_knots_p99"],
        segment["speed_gap_knots"] / thresholds["speed_gap_knots_p99"],
        segment["turn_rate_deg_per_min"] / thresholds["turn_rate_deg_per_min_p99"],
    ]
    return max(ratios)


def sog_baseline_score(segment: dict[str, float], thresholds: dict[str, float]) -> float:
    return segment["sog_knots"] / thresholds["sog_knots_p99"]


def candidate_rate(segments: list[dict[str, float]], thresholds: dict[str, float], scorer) -> float:
    if not segments:
        return 0.0
    return sum(1 for row in segments if scorer(row, thresholds) > 1.0) / len(segments)


def deterministic_sample(segments: list[dict[str, Any]], *, limit: int, salt: str) -> list[dict[str, Any]]:
    ranked = sorted(
        segments,
        key=lambda row: hashlib.sha256(
            f"{salt}|{row['mmsi']}|{row['minutes']:.6f}|{row['sog_knots']:.6f}|{row['derived_speed_knots']:.6f}".encode(
                "utf-8"
            )
        ).hexdigest(),
    )
    return ranked[: min(limit, len(ranked))]


def inject(segment: dict[str, float], family: str, thresholds: dict[str, float]) -> dict[str, float]:
    mutated = dict(segment)
    if family == "speed_burst":
        mutated["sog_knots"] = max(mutated["sog_knots"] * 2.5, thresholds["sog_knots_p99"] * 1.35)
        mutated["derived_speed_knots"] = max(
            mutated["derived_speed_knots"] * 2.5,
            thresholds["derived_speed_knots_p99"] * 1.35,
        )
        mutated["speed_gap_knots"] = abs(mutated["derived_speed_knots"] - mutated["sog_knots"])
    elif family == "position_jump":
        mutated["derived_speed_knots"] = max(
            mutated["derived_speed_knots"] + thresholds["derived_speed_knots_p99"] * 1.5,
            thresholds["derived_speed_knots_p99"] * 1.6,
        )
        mutated["speed_gap_knots"] = abs(mutated["derived_speed_knots"] - mutated["sog_knots"])
    elif family == "heading_snap":
        mutated["turn_rate_deg_per_min"] = max(
            mutated["turn_rate_deg_per_min"] + thresholds["turn_rate_deg_per_min_p99"] * 1.8,
            thresholds["turn_rate_deg_per_min_p99"] * 1.8,
        )
    elif family == "consistency_gap":
        mutated["speed_gap_knots"] = max(
            mutated["speed_gap_knots"] + thresholds["speed_gap_knots_p99"] * 1.8,
            thresholds["speed_gap_knots_p99"] * 1.8,
        )
    else:
        raise ValueError(f"Unknown injection family: {family}")
    return mutated


def evaluate_injections(
    validation_segments: list[dict[str, float]],
    thresholds: dict[str, float],
    *,
    max_injections_per_family: int,
) -> dict[str, Any]:
    families = ("speed_burst", "position_jump", "heading_snap", "consistency_gap")
    by_family: dict[str, Any] = {}
    total = 0
    detector_hits = 0
    baseline_hits = 0
    for family in families:
        sample = deterministic_sample(validation_segments, limit=max_injections_per_family, salt=family)
        detector = 0
        baseline = 0
        for segment in sample:
            mutated = inject(segment, family, thresholds)
            detector += int(motion_score(mutated, thresholds) > 1.0)
            baseline += int(sog_baseline_score(mutated, thresholds) > 1.0)
        count = len(sample)
        total += count
        detector_hits += detector
        baseline_hits += baseline
        by_family[family] = {
            "injected_segments": count,
            "motion_consistency_recall": detector / count if count else 0.0,
            "speed_only_baseline_recall": baseline / count if count else 0.0,
            "boundary": "Controlled kinematic injection on public AIS validation segments; not a real threat label.",
        }
    return {
        "families": by_family,
        "total_injected_segments": total,
        "motion_consistency_recall": detector_hits / total if total else 0.0,
        "speed_only_baseline_recall": baseline_hits / total if total else 0.0,
        "recall_lift_vs_speed_only": (
            (detector_hits / total) - (baseline_hits / total) if total else 0.0
        ),
    }


def build_benchmark(
    split_json: Path,
    *,
    max_interval_minutes: float = 120.0,
    max_injections_per_family: int = 5000,
    min_segments: int = 1000,
    write_outputs: bool = True,
) -> dict[str, Any]:
    split = read_json(split_json)
    dev_path = Path(str(split.get("splits", {}).get("development", {}).get("path", "")))
    val_path = Path(str(split.get("splits", {}).get("validation", {}).get("path", "")))
    if not dev_path.exists() or not val_path.exists():
        raise FileNotFoundError("Development or validation split CSV is missing.")

    dev_segments = build_segments(read_rows(dev_path), max_interval_minutes=max_interval_minutes)
    val_segments = build_segments(read_rows(val_path), max_interval_minutes=max_interval_minutes)
    thresholds = learn_thresholds(dev_segments)
    injections = evaluate_injections(
        val_segments,
        thresholds,
        max_injections_per_family=max_injections_per_family,
    )
    natural = {
        "development_motion_candidate_rate": candidate_rate(dev_segments, thresholds, motion_score),
        "validation_motion_candidate_rate": candidate_rate(val_segments, thresholds, motion_score),
        "development_speed_only_candidate_rate": candidate_rate(dev_segments, thresholds, sog_baseline_score),
        "validation_speed_only_candidate_rate": candidate_rate(val_segments, thresholds, sog_baseline_score),
        "boundary": "Natural candidate rates are unlabeled review queues, not false-positive rates.",
    }
    enough_data = len(dev_segments) >= min_segments and len(val_segments) >= min_segments
    posture = (
        "PUBLIC_AIS_INJECTION_BENCHMARK_READY"
        if enough_data and injections["motion_consistency_recall"] > injections["speed_only_baseline_recall"]
        else "PUBLIC_AIS_INJECTION_BENCHMARK_REVIEW"
    )
    payload = {
        "generated_utc": now_utc(),
        "schema": "harbor_ais_injection_benchmark_v1",
        "posture": posture,
        "source_split_manifest": str(split_json),
        "selected_region": split.get("selected_region", {}),
        "raw_source": {
            "source_url": split.get("raw_source", {}).get("source_url", ""),
            "source_label": split.get("raw_source", {}).get("source_label", ""),
            "sha256": split.get("raw_source", {}).get("sha256", ""),
            "bytes": split.get("raw_source", {}).get("bytes"),
        },
        "input_hashes": {
            "development_csv_sha256": sha256_file(dev_path),
            "validation_csv_sha256": sha256_file(val_path),
        },
        "development": {
            "rows": split.get("splits", {}).get("development", {}).get("rows"),
            "segments": len(dev_segments),
        },
        "validation": {
            "rows": split.get("splits", {}).get("validation", {}).get("rows"),
            "segments": len(val_segments),
        },
        "thresholds": {
            "source": "development split only",
            "quantile": "p99",
            "max_interval_minutes": max_interval_minutes,
            "values": thresholds,
        },
        "natural_candidate_rates": natural,
        "controlled_injection_benchmark": injections,
        "baseline": {
            "name": "speed_only_sog_p99",
            "description": "Flags only segments whose AIS SOG exceeds the development p99 SOG threshold.",
        },
        "detector": {
            "name": "motion_consistency_v1",
            "description": (
                "Flags segments exceeding frozen development p99 thresholds for SOG, derived speed, "
                "SOG-vs-derived speed gap, or turn-rate."
            ),
        },
        "claim_boundary": (
            "This is a held-out public AIS controlled-injection benchmark. It demonstrates that a "
            "frozen development-threshold motion-consistency detector catches injected kinematic "
            "perturbations on validation AIS segments better than a speed-only baseline. It does not "
            "establish HarborSentinel operational detection performance, real adversary detection, "
            "multi-source fusion, ADS-B/radar validation, Navy/SSDS integration, field performance, "
            "or operational suitability."
        ),
    }
    if write_outputs:
        write_json(OUT_JSON, payload)
        write_text(OUT_MD, render_markdown(payload))
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    injection = payload["controlled_injection_benchmark"]
    natural = payload["natural_candidate_rates"]
    region = payload["selected_region"]
    return "\n".join(
        [
            "# HarborSentinel Public AIS Controlled-Injection Benchmark",
            "",
            f"Generated UTC: {payload['generated_utc']}",
            "",
            f"Posture: `{payload['posture']}`",
            "",
            "## Region And Split",
            "",
            f"- Region: {region.get('label')} (`{region.get('region_id')}`)",
            f"- Development segments: {payload['development']['segments']}",
            f"- Validation segments: {payload['validation']['segments']}",
            f"- Development CSV SHA-256: `{payload['input_hashes']['development_csv_sha256']}`",
            f"- Validation CSV SHA-256: `{payload['input_hashes']['validation_csv_sha256']}`",
            "",
            "## Frozen Thresholds",
            "",
            "- Threshold source: development split only",
            "- Threshold quantile: p99",
            f"- Max segment interval: {payload['thresholds']['max_interval_minutes']} minutes",
            "",
            "## Natural Candidate Rates",
            "",
            f"- Motion-consistency validation candidate rate: {natural['validation_motion_candidate_rate']:.4f}",
            f"- Speed-only validation candidate rate: {natural['validation_speed_only_candidate_rate']:.4f}",
            "- Boundary: natural candidate rates are unlabeled review queues, not false-positive rates.",
            "",
            "## Controlled Injection Result",
            "",
            f"- Total injected validation segments: {injection['total_injected_segments']}",
            f"- Motion-consistency recall: {injection['motion_consistency_recall']:.4f}",
            f"- Speed-only baseline recall: {injection['speed_only_baseline_recall']:.4f}",
            f"- Recall lift versus speed-only: {injection['recall_lift_vs_speed_only']:.4f}",
            "",
            "## Family Recall",
            "",
            *[
                (
                    f"- {family}: motion {metrics['motion_consistency_recall']:.4f}; "
                    f"speed-only {metrics['speed_only_baseline_recall']:.4f}; "
                    f"n={metrics['injected_segments']}"
                )
                for family, metrics in injection["families"].items()
            ],
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a held-out public AIS controlled-injection benchmark.")
    parser.add_argument("--split-json", default=str(SPLIT_JSON))
    parser.add_argument("--max-interval-minutes", type=float, default=120.0)
    parser.add_argument("--max-injections-per-family", type=int, default=5000)
    parser.add_argument("--min-segments", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_benchmark(
        Path(args.split_json),
        max_interval_minutes=float(args.max_interval_minutes),
        max_injections_per_family=max(1, int(args.max_injections_per_family)),
        min_segments=max(1, int(args.min_segments)),
    )
    print(
        json.dumps(
            {
                "posture": payload["posture"],
                "region": payload["selected_region"].get("region_id"),
                "development_segments": payload["development"]["segments"],
                "validation_segments": payload["validation"]["segments"],
                "motion_recall": payload["controlled_injection_benchmark"]["motion_consistency_recall"],
                "baseline_recall": payload["controlled_injection_benchmark"]["speed_only_baseline_recall"],
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
