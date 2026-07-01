from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "ops"
HARBOR = ROOT / "grant_submissions" / "NV063_HarborSentinel"

JSON_OUT = OUT / "harbor_ais_pilot_registry_latest.json"
MD_OUT = HARBOR / "NV063_AIS_PILOT_SOURCE_REGISTRY_2026-06-20.md"

NOAA_2024_DAILY_INDEX = "https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/index.html"
NOAA_2024_DAILY_SAMPLE = "https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/AIS_2024_01_01.zip"
NOAA_ACCESSAIS = "https://coast.noaa.gov/digitalcoast/tools/ais.html"
MARINECADASTRE_ACCESSAIS = "https://marinecadastre.gov/accessais/"
NOAA_VESSEL_TRAFFIC = "https://coast.noaa.gov/digitalcoast/data/vesseltraffic.html"
NOAA_AIS_TRACK_GITHUB = "https://github.com/ocm-marinecadastre/ais-vessel-traffic"
NOAA_AIS_TRACK_SAMPLE = "https://ocmgeodatastor1.blob.core.windows.net/marinecadastre/aistrack/ais-track-2025-02.parquet"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def head_probe(url: str, timeout: float = 20.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "LumenCore-Harbor-AIS-Pilot/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            length = response.headers.get("content-length")
            bytes_value = int(length) if length and length.isdigit() else None
            return {
                "url": url,
                "checked": True,
                "ok": 200 <= int(response.status) < 400,
                "status_code": int(response.status),
                "bytes": bytes_value,
                "mib": round(bytes_value / (1024 * 1024), 3) if bytes_value else None,
                "content_type": response.headers.get("content-type"),
            }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"url": url, "checked": True, "ok": False, "error": str(exc)}


def _decision(probe: dict[str, Any], *, max_auto_download_mib: float) -> str:
    if not probe.get("checked"):
        return "UNPROBED"
    if not probe.get("ok"):
        return "SOURCE_PROBE_FAILED"
    size = probe.get("mib")
    if size is None:
        return "SIZE_UNKNOWN_DOWNLOAD_REQUIRES_USER_APPROVAL"
    if float(size) > max_auto_download_mib:
        return "DOWNLOAD_BLOCKED_BY_SIZE_POLICY"
    return "DOWNLOAD_CANDIDATE_REQUIRES_EXPLICIT_FLAG"


def build_registry(*, live_probe: bool = False, max_auto_download_mib: float = 50.0) -> dict[str, Any]:
    candidate_specs = [
        {
            "id": "noaa_2024_daily_csv_zip_2024_01_01",
            "source_family": "NOAA daily AIS CSV ZIP",
            "url": NOAA_2024_DAILY_SAMPLE,
            "index_url": NOAA_2024_DAILY_INDEX,
            "intended_use": "Smallest practical reproducible pilot from the daily CSV bulk lane; still large enough to require explicit opt-in before download.",
            "schema_expectation": "ZIP archive containing AIS CSV rows with MMSI/time/position/navigation fields.",
        },
        {
            "id": "noaa_ais_track_geoparquet_2025_02",
            "source_family": "NOAA/MarineCadastre analysis-ready AIS track GeoParquet",
            "url": NOAA_AIS_TRACK_SAMPLE,
            "index_url": NOAA_AIS_TRACK_GITHUB,
            "intended_use": "Monthly vessel-track pilot candidate when Parquet tooling and enough local storage are available.",
            "schema_expectation": "Monthly GeoParquet file containing processed AIS vessel-track geometry/features.",
        },
    ]
    candidates: list[dict[str, Any]] = []
    for spec in candidate_specs:
        probe = head_probe(spec["url"]) if live_probe else {
            "url": spec["url"],
            "checked": False,
            "ok": None,
            "reason": "live probe disabled",
        }
        candidates.append(
            {
                **spec,
                "probe": probe,
                "acquisition_decision": _decision(
                    probe,
                    max_auto_download_mib=max_auto_download_mib,
                ),
            }
        )

    return {
        "generated_utc": now_utc(),
        "schema": "harbor_ais_pilot_source_registry_v1",
        "posture": "PUBLIC_AIS_SOURCES_PROBED_DOWNLOAD_NOT_EXECUTED",
        "live_probe_enabled": live_probe,
        "max_auto_download_mib": max_auto_download_mib,
        "official_sources": {
            "noaa_accessais": NOAA_ACCESSAIS,
            "marinecadastre_accessais": MARINECADASTRE_ACCESSAIS,
            "noaa_vessel_traffic": NOAA_VESSEL_TRAFFIC,
            "noaa_2024_daily_index": NOAA_2024_DAILY_INDEX,
            "noaa_ais_track_github": NOAA_AIS_TRACK_GITHUB,
        },
        "official_facts_used": [
            "AccessAIS is the official custom-download path for historical U.S. vessel-traffic data by geography and time range.",
            "NOAA's 2024 daily AIS CSV bulk directory is an official public data lane but the full annual set is far larger than a grant-prep smoke test.",
            "NOAA/MarineCadastre AIS vessel-track GeoParquet files are analysis-ready public data, but monthly files are large and require suitable local tooling.",
        ],
        "candidates": candidates,
        "claim_boundary": (
            "This registry proves public AIS acquisition paths and size gates. "
            "It does not download AIS rows, produce representative validation, "
            "or establish Navy/SSDS/field performance."
        ),
        "external_data_workspace": {
            "recommended_env_var": "LUMA_HARBOR_DATA_ROOT",
            "recommended_drive_use": (
                "Use the external Glyph drive for raw NOAA/MarineCadastre files "
                "and extracted working subsets; keep only manifests, hashes, "
                "schema profiles, and small derived summaries in the repo."
            ),
            "suggested_layout": [
                "LumaData/HarborSentinel/raw/noaa_ais/",
                "LumaData/HarborSentinel/working/noaa_ais/",
                "LumaData/HarborSentinel/manifests/",
                "LumaData/HarborSentinel/derived/",
            ],
            "repo_rule": (
                "Do not commit raw ZIP, Parquet, CSV, or extracted AIS bulk data. "
                "Commit source registries, SHA-256 manifests, schema profiles, "
                "and bounded summary metrics only."
            ),
        },
        "next_executable_step": (
            "Run a user-approved NOAA AIS download with a bounded size limit, "
            "hash the raw archive, record license/source metadata, extract a "
            "small withheld validation split, and rerun HarborSentinel without "
            "changing thresholds on that split."
        ),
    }


def render_markdown(registry: dict[str, Any]) -> str:
    lines = [
        "# NV063 HarborSentinel AIS Pilot Source Registry",
        "",
        f"Generated UTC: {registry['generated_utc']}",
        "",
        f"Posture: `{registry['posture']}`",
        "",
        "Status: public-AIS source registry and size gate only; no AIS rows were downloaded or scored by this artifact.",
        "",
        "## Claim Boundary",
        "",
        registry["claim_boundary"],
        "",
        "## Official Sources",
        "",
    ]
    for name, url in registry["official_sources"].items():
        lines.append(f"- {name}: {url}")
    lines.extend(["", "## Official Facts Used", ""])
    lines.extend(f"- {fact}" for fact in registry["official_facts_used"])
    lines.extend(["", "## Candidate Public AIS Inputs", ""])
    for candidate in registry["candidates"]:
        probe = candidate["probe"]
        lines.extend(
            [
                f"### {candidate['id']}",
                "",
                f"- family: {candidate['source_family']}",
                f"- URL: {candidate['url']}",
                f"- index/source: {candidate['index_url']}",
                f"- intended use: {candidate['intended_use']}",
                f"- schema expectation: {candidate['schema_expectation']}",
                f"- acquisition decision: `{candidate['acquisition_decision']}`",
                f"- probe checked: {probe.get('checked')}",
            ]
        )
        if probe.get("checked"):
            lines.append(f"- probe ok: {probe.get('ok')}")
            if probe.get("status_code") is not None:
                lines.append(f"- status code: {probe.get('status_code')}")
            if probe.get("mib") is not None:
                lines.append(f"- content length: {probe.get('mib')} MiB")
            if probe.get("content_type"):
                lines.append(f"- content type: {probe.get('content_type')}")
            if probe.get("error"):
                lines.append(f"- probe error: {probe.get('error')}")
        else:
            lines.append(f"- probe note: {probe.get('reason')}")
        lines.append("")
    lines.extend(
        [
            "## External Data Workspace",
            "",
            f"- recommended env var: `{registry['external_data_workspace']['recommended_env_var']}`",
            f"- drive use: {registry['external_data_workspace']['recommended_drive_use']}",
            "- suggested layout:",
        ]
    )
    lines.extend(f"  - `{item}`" for item in registry["external_data_workspace"]["suggested_layout"])
    lines.extend(
        [
            f"- repo rule: {registry['external_data_workspace']['repo_rule']}",
            "",
            "## Representative-Data Gate",
            "",
            "- Do not call HarborSentinel representative-data validated until at least one NOAA/MarineCadastre AIS subset is downloaded or exported through AccessAIS, hashed, schema-profiled, partitioned, and scored.",
            "- Do not tune thresholds on the withheld AIS validation split.",
            "- Do not combine OpenSky or equivalent ADS-B data until commercial/government-contractor rights are documented.",
            "- Do not describe generated radar-like tracks as Navy radar, SSDS, or operational sensor data.",
            "",
            "## Next Executable Step",
            "",
            registry["next_executable_step"],
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-probe", action="store_true", help="HEAD-probe candidate NOAA AIS files")
    parser.add_argument("--max-auto-download-mib", type=float, default=50.0)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    HARBOR.mkdir(parents=True, exist_ok=True)
    registry = build_registry(
        live_probe=args.live_probe,
        max_auto_download_mib=max(0.0, args.max_auto_download_mib),
    )
    JSON_OUT.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    MD_OUT.write_text(render_markdown(registry), encoding="utf-8")
    print(
        json.dumps(
            {
                "posture": registry["posture"],
                "candidates": len(registry["candidates"]),
                "json": rel(JSON_OUT),
                "md": rel(MD_OUT),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
