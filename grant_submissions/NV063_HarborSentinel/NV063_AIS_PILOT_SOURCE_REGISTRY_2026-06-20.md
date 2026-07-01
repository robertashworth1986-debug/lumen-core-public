# NV063 HarborSentinel AIS Pilot Source Registry

Generated UTC: 2026-06-20T01:53:37.420166+00:00

Posture: `PUBLIC_AIS_SOURCES_PROBED_DOWNLOAD_NOT_EXECUTED`

Status: public-AIS source registry and size gate only; no AIS rows were downloaded or scored by this artifact.

## Claim Boundary

This registry proves public AIS acquisition paths and size gates. It does not download AIS rows, produce representative validation, or establish Navy/SSDS/field performance.

## Official Sources

- noaa_accessais: https://coast.noaa.gov/digitalcoast/tools/ais.html
- marinecadastre_accessais: https://marinecadastre.gov/accessais/
- noaa_vessel_traffic: https://coast.noaa.gov/digitalcoast/data/vesseltraffic.html
- noaa_2024_daily_index: https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/index.html
- noaa_ais_track_github: https://github.com/ocm-marinecadastre/ais-vessel-traffic

## Official Facts Used

- AccessAIS is the official custom-download path for historical U.S. vessel-traffic data by geography and time range.
- NOAA's 2024 daily AIS CSV bulk directory is an official public data lane but the full annual set is far larger than a grant-prep smoke test.
- NOAA/MarineCadastre AIS vessel-track GeoParquet files are analysis-ready public data, but monthly files are large and require suitable local tooling.

## Candidate Public AIS Inputs

### noaa_2024_daily_csv_zip_2024_01_01

- family: NOAA daily AIS CSV ZIP
- URL: https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/AIS_2024_01_01.zip
- index/source: https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/index.html
- intended use: Smallest practical reproducible pilot from the daily CSV bulk lane; still large enough to require explicit opt-in before download.
- schema expectation: ZIP archive containing AIS CSV rows with MMSI/time/position/navigation fields.
- acquisition decision: `DOWNLOAD_BLOCKED_BY_SIZE_POLICY`
- probe checked: True
- probe ok: True
- status code: 200
- content length: 276.891 MiB
- content type: application/zip

### noaa_ais_track_geoparquet_2025_02

- family: NOAA/MarineCadastre analysis-ready AIS track GeoParquet
- URL: https://ocmgeodatastor1.blob.core.windows.net/marinecadastre/aistrack/ais-track-2025-02.parquet
- index/source: https://github.com/ocm-marinecadastre/ais-vessel-traffic
- intended use: Monthly vessel-track pilot candidate when Parquet tooling and enough local storage are available.
- schema expectation: Monthly GeoParquet file containing processed AIS vessel-track geometry/features.
- acquisition decision: `DOWNLOAD_BLOCKED_BY_SIZE_POLICY`
- probe checked: True
- probe ok: True
- status code: 200
- content length: 1031.01 MiB
- content type: application/octet-stream

## External Data Workspace

- recommended env var: `LUMA_HARBOR_DATA_ROOT`
- drive use: Use the external Glyph drive for raw NOAA/MarineCadastre files and extracted working subsets; keep only manifests, hashes, schema profiles, and small derived summaries in the repo.
- suggested layout:
  - `LumaData/HarborSentinel/raw/noaa_ais/`
  - `LumaData/HarborSentinel/working/noaa_ais/`
  - `LumaData/HarborSentinel/manifests/`
  - `LumaData/HarborSentinel/derived/`
- repo rule: Do not commit raw ZIP, Parquet, CSV, or extracted AIS bulk data. Commit source registries, SHA-256 manifests, schema profiles, and bounded summary metrics only.

## Representative-Data Gate

- Do not call HarborSentinel representative-data validated until at least one NOAA/MarineCadastre AIS subset is downloaded or exported through AccessAIS, hashed, schema-profiled, partitioned, and scored.
- Do not tune thresholds on the withheld AIS validation split.
- Do not combine OpenSky or equivalent ADS-B data until commercial/government-contractor rights are documented.
- Do not describe generated radar-like tracks as Navy radar, SSDS, or operational sensor data.

## Next Executable Step

Run a user-approved NOAA AIS download with a bounded size limit, hash the raw archive, record license/source metadata, extract a small withheld validation split, and rerun HarborSentinel without changing thresholds on that split.
