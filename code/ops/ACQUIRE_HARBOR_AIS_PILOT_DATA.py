from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
GRANT_DIR = ROOT / "grant_submissions" / "NV063_HarborSentinel"

REPO_JSON = OUT_OPS / "harbor_ais_pilot_acquisition_latest.json"
REPO_MD = GRANT_DIR / "NV063_AIS_PILOT_ACQUISITION_2026-06-20.md"

DEFAULT_DATA_ROOT = Path(os.environ.get("LUMA_HARBOR_DATA_ROOT") or "G:/LumaData/HarborSentinel")

CANDIDATES: dict[str, dict[str, str]] = {
    "noaa_2024_01_01_daily_zip": {
        "label": "NOAA daily AIS CSV ZIP 2024-01-01",
        "source_family": "NOAA daily AIS CSV ZIP",
        "url": "https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/AIS_2024_01_01.zip",
        "filename": "AIS_2024_01_01.zip",
        "raw_subdir": "raw/noaa_ais",
        "profile_kind": "zip_csv",
        "official_index_url": "https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/index.html",
    },
    "noaa_ais_track_2025_02_geoparquet": {
        "label": "NOAA/MarineCadastre AIS track GeoParquet 2025-02",
        "source_family": "NOAA/MarineCadastre AIS track GeoParquet",
        "url": "https://ocmgeodatastor1.blob.core.windows.net/marinecadastre/aistrack/ais-track-2025-02.parquet",
        "filename": "ais-track-2025-02.parquet",
        "raw_subdir": "raw/noaa_ais_geoparquet",
        "profile_kind": "parquet",
        "official_index_url": "https://github.com/ocm-marinecadastre/ais-vessel-traffic",
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except Exception:
        return str(path).replace("\\", "/")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_float(value: Any) -> float | None:
    try:
        n = float(value)
    except Exception:
        return None
    return n if n == n else None


def layout(data_root: Path) -> dict[str, Path]:
    return {
        "root": data_root,
        "raw_noaa_ais": data_root / "raw" / "noaa_ais",
        "raw_noaa_ais_geoparquet": data_root / "raw" / "noaa_ais_geoparquet",
        "working_noaa_ais": data_root / "working" / "noaa_ais",
        "manifests": data_root / "manifests",
        "derived": data_root / "derived",
    }


def ensure_layout(data_root: Path) -> dict[str, Path]:
    paths = layout(data_root)
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def download_stream(url: str, dest: Path, max_mib: float) -> dict[str, Any]:
    max_bytes = int(max_mib * 1024 * 1024)
    if dest.exists() and dest.stat().st_size > 0:
        return {
            "status": "already_exists",
            "bytes": dest.stat().st_size,
            "path": str(dest),
            "resumed": False,
        }

    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    resume_from = part.stat().st_size if part.exists() else 0

    headers = {"User-Agent": "LumaHarborSentinelAISAcquisition/1.0"}
    if resume_from:
        headers["Range"] = f"bytes={resume_from}-"

    req = urllib.request.Request(url, headers=headers)
    start = time.time()
    last_print = start
    mode = "ab" if resume_from else "wb"

    with urllib.request.urlopen(req, timeout=60) as resp:
        status_code = int(getattr(resp, "status", 200))
        if resume_from and status_code != 206:
            part.unlink(missing_ok=True)
            resume_from = 0
            mode = "wb"

        content_length = resp.headers.get("Content-Length")
        total_expected = resume_from + int(content_length) if content_length and content_length.isdigit() else None
        if total_expected is not None and total_expected > max_bytes:
            raise RuntimeError(
                f"Refusing download: expected {total_expected / 1024 / 1024:.1f} MiB exceeds --max-mib {max_mib:.1f}"
            )

        downloaded = resume_from
        with part.open(mode + ("" if "b" in mode else "b")) as fh:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
                downloaded += len(chunk)
                if downloaded > max_bytes:
                    raise RuntimeError(
                        f"Refusing download: received {downloaded / 1024 / 1024:.1f} MiB exceeds --max-mib {max_mib:.1f}"
                    )
                now = time.time()
                if now - last_print >= 5:
                    if total_expected:
                        pct = downloaded / total_expected * 100
                        print(f"download {downloaded / 1024 / 1024:.1f}/{total_expected / 1024 / 1024:.1f} MiB ({pct:.1f}%)")
                    else:
                        print(f"download {downloaded / 1024 / 1024:.1f} MiB")
                    last_print = now

    os.replace(part, dest)
    return {
        "status": "downloaded",
        "bytes": dest.stat().st_size,
        "path": str(dest),
        "resumed": resume_from > 0,
        "elapsed_seconds": round(time.time() - start, 3),
    }


def profile_zip_csv(path: Path, sample_rows: int) -> dict[str, Any]:
    with zipfile.ZipFile(path) as zf:
        infos = [info for info in zf.infolist() if not info.is_dir()]
        csv_infos = [info for info in infos if info.filename.lower().endswith(".csv")]
        if not csv_infos:
            return {
                "profile_status": "no_csv_member",
                "zip_members": [info.filename for info in infos[:20]],
                "zip_member_count": len(infos),
            }
        info = csv_infos[0]
        lat_values: list[float] = []
        lon_values: list[float] = []
        sog_values: list[float] = []
        times: list[str] = []
        mmsi_values: set[str] = set()
        rows_seen = 0
        with zf.open(info, "r") as raw:
            wrapped = io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")
            reader = csv.DictReader(wrapped)
            columns = list(reader.fieldnames or [])
            for row in reader:
                rows_seen += 1
                if row.get("MMSI"):
                    mmsi_values.add(str(row.get("MMSI", "")).strip())
                if row.get("BaseDateTime"):
                    times.append(str(row.get("BaseDateTime", "")).strip())
                lat = safe_float(row.get("LAT") or row.get("lat"))
                lon = safe_float(row.get("LON") or row.get("lon"))
                sog = safe_float(row.get("SOG") or row.get("sog"))
                if lat is not None:
                    lat_values.append(lat)
                if lon is not None:
                    lon_values.append(lon)
                if sog is not None:
                    sog_values.append(sog)
                if rows_seen >= sample_rows:
                    break

    return {
        "profile_status": "sampled",
        "zip_member_count": len(infos),
        "csv_member": info.filename,
        "csv_compressed_bytes": int(info.compress_size),
        "csv_uncompressed_bytes": int(info.file_size),
        "sample_rows": rows_seen,
        "columns": columns,
        "unique_mmsi_in_sample": len(mmsi_values),
        "time_min_in_sample": min(times) if times else "",
        "time_max_in_sample": max(times) if times else "",
        "lat_min_in_sample": min(lat_values) if lat_values else None,
        "lat_max_in_sample": max(lat_values) if lat_values else None,
        "lon_min_in_sample": min(lon_values) if lon_values else None,
        "lon_max_in_sample": max(lon_values) if lon_values else None,
        "sog_avg_in_sample": round(sum(sog_values) / len(sog_values), 4) if sog_values else None,
    }


def profile_parquet(path: Path) -> dict[str, Any]:
    return {
        "profile_status": "stored_not_profiled",
        "reason": "Parquet profiling is intentionally deferred until pyarrow/geopandas lane is selected.",
        "bytes": path.stat().st_size if path.exists() else 0,
    }


def build_markdown(payload: dict[str, Any]) -> str:
    source = payload["source"]
    raw = payload["raw_file"]
    profile = payload["profile"]
    return "\n".join(
        [
            "# HarborSentinel AIS Pilot Acquisition",
            "",
            f"Generated UTC: {payload['generated_utc']}",
            "",
            f"Posture: `{payload['posture']}`",
            "",
            "## Source",
            "",
            f"- Candidate: {source['label']}",
            f"- Source family: {source['source_family']}",
            f"- URL: {source['url']}",
            f"- Official index: {source['official_index_url']}",
            "",
            "## Raw External File",
            "",
            f"- Path: `{raw['path']}`",
            f"- Bytes: {raw['bytes']}",
            f"- SHA-256: `{raw['sha256']}`",
            "",
            "## Schema/Profile",
            "",
            f"- Profile status: {profile.get('profile_status')}",
            f"- Sample rows: {profile.get('sample_rows', 0)}",
            f"- Columns: {', '.join(profile.get('columns', []) or [])}",
            f"- Time range in sample: {profile.get('time_min_in_sample', '')} to {profile.get('time_max_in_sample', '')}",
            f"- Latitude sample bounds: {profile.get('lat_min_in_sample')} to {profile.get('lat_max_in_sample')}",
            f"- Longitude sample bounds: {profile.get('lon_min_in_sample')} to {profile.get('lon_max_in_sample')}",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
            "## Next Step",
            "",
            "Extract a bounded development/validation split on the external drive, freeze split hashes, then rerun the HarborSentinel gate without moving thresholds after validation is held out.",
        ]
    )


def acquire(
    data_root: Path,
    candidate_id: str,
    max_mib: float,
    sample_rows: int,
    download: bool,
) -> dict[str, Any]:
    if candidate_id not in CANDIDATES:
        raise KeyError(f"Unknown candidate: {candidate_id}")
    paths = ensure_layout(data_root)
    candidate = CANDIDATES[candidate_id]
    dest = data_root / candidate["raw_subdir"] / candidate["filename"]

    download_result = {"status": "download_skipped", "path": str(dest), "bytes": dest.stat().st_size if dest.exists() else 0}
    if download:
        download_result = download_stream(candidate["url"], dest, max_mib=max_mib)
    if not dest.exists():
        raise FileNotFoundError(f"Raw file not available: {dest}")

    digest = sha256_file(dest)
    if candidate["profile_kind"] == "zip_csv":
        profile = profile_zip_csv(dest, sample_rows=sample_rows)
    elif candidate["profile_kind"] == "parquet":
        profile = profile_parquet(dest)
    else:
        profile = {"profile_status": "unknown_profile_kind"}

    payload = {
        "generated_utc": now_utc(),
        "schema": "harbor_ais_pilot_acquisition_v1",
        "posture": "PUBLIC_AIS_RAW_ACQUIRED_HASHED_PROFILED" if profile.get("profile_status") == "sampled" else "PUBLIC_AIS_RAW_ACQUIRED_HASHED",
        "data_root": str(data_root),
        "layout": {key: str(value) for key, value in paths.items()},
        "source": {
            "candidate_id": candidate_id,
            "label": candidate["label"],
            "source_family": candidate["source_family"],
            "url": candidate["url"],
            "official_index_url": candidate["official_index_url"],
        },
        "download": download_result,
        "raw_file": {
            "path": str(dest),
            "bytes": dest.stat().st_size,
            "sha256": digest,
        },
        "profile": profile,
        "repo_outputs": {
            "json": rel(REPO_JSON),
            "markdown": rel(REPO_MD),
        },
        "claim_boundary": (
            "This acquisition proves that a public AIS raw file was staged on the external data drive, "
            "hashed, and schema-profiled. It does not prove HarborSentinel performance, Navy/SSDS "
            "integration, field validation, ADS-B rights, radar performance, or operational suitability."
        ),
    }

    tag = utc_tag()
    external_manifest = paths["manifests"] / f"harbor_ais_pilot_acquisition_{tag}.json"
    external_latest = paths["manifests"] / "harbor_ais_pilot_acquisition_latest.json"
    payload["external_manifests"] = {
        "tagged": str(external_manifest),
        "latest": str(external_latest),
    }

    write_json(external_manifest, payload)
    write_json(external_latest, payload)
    write_json(REPO_JSON, payload)
    write_text(REPO_MD, build_markdown(payload))
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Acquire a bounded public AIS pilot file to an external data root.")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT), help="External HarborSentinel data root.")
    parser.add_argument("--candidate", default="noaa_2024_01_01_daily_zip", choices=sorted(CANDIDATES))
    parser.add_argument("--max-mib", type=float, default=512.0, help="Maximum allowed single-file download size.")
    parser.add_argument("--sample-rows", type=int, default=10000, help="Rows to scan for schema/profile.")
    parser.add_argument("--no-download", action="store_true", help="Profile/hash an already staged file without downloading.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = acquire(
        data_root=Path(args.data_root),
        candidate_id=args.candidate,
        max_mib=args.max_mib,
        sample_rows=max(1, int(args.sample_rows)),
        download=not args.no_download,
    )
    print(
        json.dumps(
            {
                "posture": payload["posture"],
                "raw_file": payload["raw_file"]["path"],
                "bytes": payload["raw_file"]["bytes"],
                "sha256": payload["raw_file"]["sha256"],
                "json": rel(REPO_JSON),
                "markdown": rel(REPO_MD),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
