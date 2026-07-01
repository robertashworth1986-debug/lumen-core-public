import argparse
import csv
import heapq
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
GRANT_DIR = ROOT / "grant_submissions" / "NV063_HarborSentinel"

ACQUISITION_JSON = OUT_OPS / "harbor_ais_pilot_acquisition_latest.json"
REPO_JSON = OUT_OPS / "harbor_ais_heldout_splits_latest.json"
REPO_MD = GRANT_DIR / "NV063_AIS_HELDOUT_SPLIT_MANIFEST_2026-06-20.md"


@dataclass(frozen=True)
class Region:
    region_id: str
    label: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float


REGIONS = (
    Region("hampton_roads", "Hampton Roads / Norfolk", 36.55, 37.35, -76.75, -75.65),
    Region("new_york_harbor", "New York Harbor", 40.25, 41.05, -74.45, -73.35),
    Region("houston_galveston", "Houston / Galveston", 28.75, 30.25, -95.65, -94.35),
    Region("new_orleans_delta", "New Orleans / Mississippi River Delta", 28.60, 30.35, -90.95, -88.65),
    Region("los_angeles_long_beach", "Los Angeles / Long Beach", 33.35, 34.20, -118.70, -117.75),
    Region("puget_sound", "Puget Sound", 47.00, 48.35, -123.35, -122.00),
    Region("san_francisco_bay", "San Francisco Bay", 37.15, 38.35, -123.10, -121.70),
    Region("delaware_bay", "Delaware Bay", 38.70, 40.25, -75.75, -74.55),
)


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


def stable_key(row: dict[str, str]) -> int:
    import hashlib

    token = "|".join(
        [
            str(row.get("MMSI", "")),
            str(row.get("BaseDateTime", "")),
            str(row.get("LAT", "")),
            str(row.get("LON", "")),
        ]
    )
    return int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)


def safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    return number if number == number else None


def row_region(row: dict[str, str], regions: tuple[Region, ...] = REGIONS) -> Region | None:
    lat = safe_float(row.get("LAT") or row.get("lat"))
    lon = safe_float(row.get("LON") or row.get("lon"))
    if lat is None or lon is None:
        return None
    for region in regions:
        if region.lat_min <= lat <= region.lat_max and region.lon_min <= lon <= region.lon_max:
            return region
    return None


def split_for_time(value: str) -> str:
    text = str(value or "")
    try:
        hour = int(text[11:13])
    except Exception:
        key = stable_key({"BaseDateTime": text})
        return "development" if key % 2 == 0 else "validation"
    return "development" if hour < 12 else "validation"


def stream_zip_csv(path: Path):
    with zipfile.ZipFile(path) as archive:
        csv_members = [info for info in archive.infolist() if info.filename.lower().endswith(".csv")]
        if not csv_members:
            raise RuntimeError(f"No CSV member found in {path}")
        member = csv_members[0]
        with archive.open(member, "r") as raw:
            wrapped = io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")
            reader = csv.DictReader(wrapped)
            for row in reader:
                yield row


def scan_regions(raw_zip: Path) -> dict[str, Any]:
    stats: dict[str, dict[str, Any]] = {
        region.region_id: {
            "region_id": region.region_id,
            "label": region.label,
            "bounds": {
                "lat_min": region.lat_min,
                "lat_max": region.lat_max,
                "lon_min": region.lon_min,
                "lon_max": region.lon_max,
            },
            "rows": 0,
            "unique_mmsi": set(),
            "time_min": "",
            "time_max": "",
        }
        for region in REGIONS
    }
    total_rows = 0
    for row in stream_zip_csv(raw_zip):
        total_rows += 1
        region = row_region(row)
        if region is None:
            continue
        item = stats[region.region_id]
        item["rows"] += 1
        mmsi = str(row.get("MMSI", "")).strip()
        if mmsi:
            item["unique_mmsi"].add(mmsi)
        timestamp = str(row.get("BaseDateTime", "")).strip()
        if timestamp:
            item["time_min"] = min(item["time_min"], timestamp) if item["time_min"] else timestamp
            item["time_max"] = max(item["time_max"], timestamp) if item["time_max"] else timestamp
    clean = {}
    for key, item in stats.items():
        unique_mmsi = item.pop("unique_mmsi")
        item["unique_mmsi"] = len(unique_mmsi)
        clean[key] = item
    return {"total_raw_rows_scanned": total_rows, "regions": clean}


def choose_region(scan: dict[str, Any], requested: str | None) -> dict[str, Any]:
    regions = scan.get("regions", {})
    if requested:
        if requested not in regions:
            raise KeyError(f"Unknown region: {requested}")
        return regions[requested]
    ranked = sorted(
        regions.values(),
        key=lambda item: (int(item.get("rows", 0)), int(item.get("unique_mmsi", 0))),
        reverse=True,
    )
    if not ranked or int(ranked[0].get("rows", 0)) <= 0:
        raise RuntimeError("No configured pilot region had AIS rows.")
    return ranked[0]


def keep_row(heap: list[tuple[int, int, dict[str, str]]], row: dict[str, str], max_rows: int, sequence: int) -> None:
    key = stable_key(row)
    item = (-key, sequence, dict(row))
    if len(heap) < max_rows:
        heapq.heappush(heap, item)
        return
    if key < -heap[0][0]:
        heapq.heapreplace(heap, item)


def write_split_csv(path: Path, fieldnames: list[str], heap: list[tuple[int, int, dict[str, str]]]) -> dict[str, Any]:
    rows = [item[2] for item in heap]
    rows.sort(key=lambda row: (str(row.get("BaseDateTime", "")), str(row.get("MMSI", ""))))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return {"path": str(path), "rows": len(rows), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def summarize_split(path: Path) -> dict[str, Any]:
    rows = 0
    unique_mmsi: set[str] = set()
    time_min = ""
    time_max = ""
    lat_values: list[float] = []
    lon_values: list[float] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows += 1
            mmsi = str(row.get("MMSI", "")).strip()
            if mmsi:
                unique_mmsi.add(mmsi)
            timestamp = str(row.get("BaseDateTime", "")).strip()
            if timestamp:
                time_min = min(time_min, timestamp) if time_min else timestamp
                time_max = max(time_max, timestamp) if time_max else timestamp
            lat = safe_float(row.get("LAT"))
            lon = safe_float(row.get("LON"))
            if lat is not None:
                lat_values.append(lat)
            if lon is not None:
                lon_values.append(lon)
    return {
        "rows": rows,
        "unique_mmsi": len(unique_mmsi),
        "time_min": time_min,
        "time_max": time_max,
        "lat_min": min(lat_values) if lat_values else None,
        "lat_max": max(lat_values) if lat_values else None,
        "lon_min": min(lon_values) if lon_values else None,
        "lon_max": max(lon_values) if lon_values else None,
    }


def build_splits(
    *,
    acquisition_json: Path,
    data_root: Path | None,
    max_rows_per_split: int,
    requested_region: str | None,
) -> dict[str, Any]:
    acquisition = read_json(acquisition_json)
    raw_path = Path(str(acquisition.get("raw_file", {}).get("path", "")))
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw AIS ZIP missing: {raw_path}")
    if data_root is None:
        data_root = Path(str(acquisition.get("data_root") or raw_path.parents[2]))
    working_root = data_root / "working" / "noaa_ais"
    manifest_root = data_root / "manifests"
    tag = utc_tag()
    run_dir = working_root / f"heldout_{tag}"

    scan = scan_regions(raw_path)
    selected = choose_region(scan, requested_region)
    selected_id = str(selected["region_id"])
    selected_bounds = selected["bounds"]

    dev_heap: list[tuple[int, int, dict[str, str]]] = []
    val_heap: list[tuple[int, int, dict[str, str]]] = []
    fieldnames: list[str] | None = None
    total_region_rows = 0
    split_counts = {"development": 0, "validation": 0}
    sequence = 0

    selected_region = next(region for region in REGIONS if region.region_id == selected_id)
    for row in stream_zip_csv(raw_path):
        if fieldnames is None:
            fieldnames = list(row.keys())
        if row_region(row, (selected_region,)) is None:
            continue
        total_region_rows += 1
        split = split_for_time(str(row.get("BaseDateTime", "")))
        split_counts[split] += 1
        if split == "development":
            keep_row(dev_heap, row, max_rows_per_split, sequence)
        else:
            keep_row(val_heap, row, max_rows_per_split, sequence)
        sequence += 1

    if fieldnames is None:
        raise RuntimeError("No CSV rows found in raw file.")
    dev_csv = run_dir / "development.csv"
    val_csv = run_dir / "validation.csv"
    dev_file = write_split_csv(dev_csv, fieldnames, dev_heap)
    val_file = write_split_csv(val_csv, fieldnames, val_heap)
    dev_file["summary"] = summarize_split(dev_csv)
    val_file["summary"] = summarize_split(val_csv)

    payload = {
        "generated_utc": now_utc(),
        "schema": "harbor_ais_heldout_splits_v1",
        "posture": "PUBLIC_AIS_HELDOUT_SPLITS_FROZEN",
        "data_root": str(data_root),
        "raw_source": {
            "path": str(raw_path),
            "bytes": acquisition.get("raw_file", {}).get("bytes"),
            "sha256": acquisition.get("raw_file", {}).get("sha256"),
            "source_url": acquisition.get("source", {}).get("url"),
            "source_label": acquisition.get("source", {}).get("label"),
        },
        "region_scan": scan,
        "selected_region": {
            "region_id": selected_id,
            "label": selected["label"],
            "bounds": selected_bounds,
            "total_region_rows": total_region_rows,
            "split_counts_before_cap": split_counts,
        },
        "sampling_rule": {
            "split_rule": "development = BaseDateTime hour < 12 UTC; validation = BaseDateTime hour >= 12 UTC",
            "cap_rule": "When a split exceeds max_rows_per_split, keep the rows with the smallest deterministic SHA-256 row keys over the full split.",
            "max_rows_per_split": max_rows_per_split,
        },
        "splits": {
            "development": dev_file,
            "validation": val_file,
        },
        "claim_boundary": (
            "This artifact freezes public AIS held-out development and validation splits. "
            "It does not establish HarborSentinel detection performance, Navy sensor validation, "
            "SSDS integration, ADS-B rights, radar performance, or operational suitability."
        ),
    }

    manifest_root.mkdir(parents=True, exist_ok=True)
    external_tagged = manifest_root / f"harbor_ais_heldout_splits_{tag}.json"
    external_latest = manifest_root / "harbor_ais_heldout_splits_latest.json"
    payload["external_manifests"] = {"tagged": str(external_tagged), "latest": str(external_latest)}
    write_json(external_tagged, payload)
    write_json(external_latest, payload)
    write_json(REPO_JSON, payload)
    write_text(REPO_MD, render_markdown(payload))
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    selected = payload["selected_region"]
    dev = payload["splits"]["development"]
    val = payload["splits"]["validation"]
    return "\n".join(
        [
            "# HarborSentinel Public AIS Held-Out Split Manifest",
            "",
            f"Generated UTC: {payload['generated_utc']}",
            "",
            f"Posture: `{payload['posture']}`",
            "",
            "## Raw Source",
            "",
            f"- Path: `{payload['raw_source']['path']}`",
            f"- SHA-256: `{payload['raw_source']['sha256']}`",
            f"- Source: {payload['raw_source']['source_url']}",
            "",
            "## Selected Pilot Region",
            "",
            f"- Region: {selected['label']} (`{selected['region_id']}`)",
            f"- Total rows in region: {selected['total_region_rows']}",
            f"- Pre-cap split counts: {selected['split_counts_before_cap']}",
            "",
            "## Frozen Splits",
            "",
            f"- Development CSV: `{dev['path']}`",
            f"  - rows: {dev['rows']}",
            f"  - SHA-256: `{dev['sha256']}`",
            f"- Validation CSV: `{val['path']}`",
            f"  - rows: {val['rows']}",
            f"  - SHA-256: `{val['sha256']}`",
            "",
            "## Sampling Rule",
            "",
            f"- {payload['sampling_rule']['split_rule']}",
            f"- {payload['sampling_rule']['cap_rule']}",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build held-out public AIS splits on the external HarborSentinel data drive.")
    parser.add_argument("--acquisition-json", default=str(ACQUISITION_JSON))
    parser.add_argument("--data-root", default="")
    parser.add_argument("--max-rows-per-split", type=int, default=50000)
    parser.add_argument("--region", default="", help="Optional configured region id.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_splits(
        acquisition_json=Path(args.acquisition_json),
        data_root=Path(args.data_root) if args.data_root else None,
        max_rows_per_split=max(100, int(args.max_rows_per_split)),
        requested_region=args.region.strip() or None,
    )
    print(
        json.dumps(
            {
                "posture": payload["posture"],
                "region": payload["selected_region"]["region_id"],
                "development_rows": payload["splits"]["development"]["rows"],
                "validation_rows": payload["splits"]["validation"]["rows"],
                "json": str(REPO_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(REPO_MD.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
