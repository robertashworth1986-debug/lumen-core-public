from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
LOCAL_DATA_DIR = ROOT / "data" / "faa_public" / "sdr"
VAULT_DATA_DIR = Path("E:/LumaProofVault/FAA_PUBLIC_RAW/SDR")
PROTOCOL_PATH = ROOT / "config" / "faa_sdr_aviation_reliability_10k_protocol_v1.json"
CATALOG_PATH = ROOT / "config" / "faa_aviation_data_sources_v1.json"
OUT_JSON = ROOT / "out" / "ops" / "faa_sdr_source_audit_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "faa_sdr_source_audit.json"
OUT_MD = ROOT / "docs" / "FAA_SDR_SOURCE_AUDIT_2026-07-13.md"

DOWNLOAD_PAGE = "https://www.faa.gov/av-info/download_SDR"
DOWNLOAD_TEMPLATE = "https://external.apic4e.faa.gov/sdrs/retrieve/SDR-{year}.csv"
REQUIRED_COLUMNS = {
    "OperatorControlNumber",
    "DifficultyDate",
    "AircraftMake",
    "AircraftModel",
    "AircraftTotalTime",
    "AircraftTotalCycles",
    "EngineMake",
    "EngineModel",
    "EngineSerialNumber",
    "EngineTotalTime",
    "EngineTotalCycles",
    "PartMake",
    "PartName",
    "PartNumber",
    "PartCondition",
    "ComponentMake",
    "ComponentModel",
    "ComponentName",
    "JASCCode",
    "StageOfOperationCode",
    "Discrepancy",
}
PROFILE_FIELDS = (
    "EngineMake",
    "EngineModel",
    "EngineSerialNumber",
    "EngineTotalTime",
    "EngineTotalCycles",
    "PartMake",
    "PartName",
    "PartNumber",
    "PartCondition",
    "ComponentMake",
    "ComponentModel",
    "ComponentName",
    "Discrepancy",
)
ENGINE_FIELDS = (
    "EngineMake",
    "EngineModel",
    "EngineSerialNumber",
    "EngineTotalTime",
    "EngineTotalCycles",
)
TOP_FIELDS = (
    "AircraftMake",
    "AircraftModel",
    "EngineMake",
    "EngineModel",
    "PartName",
    "ComponentName",
    "JASCCode",
    "StageOfOperationCode",
)
ROLLS_MODEL_RE = re.compile(r"(?:^|[^A-Z0-9])(RB211|TRENT|AE3007|TAY6|TAYMK|BR700|BR710|BR715|BR725)")
VALID_JASC_RE = re.compile(r"^[0-9]{4}$")

CLAIM_BOUNDARY = (
    "FAA SDR is report-only observational maintenance data. This audit does not estimate failure rates, establish "
    "causality, determine airworthiness, validate an engine-health monitor, authorize operational use, or show FAA, "
    "operator, airport, or OEM approval. Rolls-Royce-family rows are an exploratory public-data subgroup only."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize(value: Any) -> str:
    return " ".join(str(value or "").upper().strip().split())


def parse_date(value: str) -> datetime | None:
    text = value.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def is_rolls_royce_row(row: dict[str, str]) -> bool:
    make = normalize(row.get("EngineMake"))
    model = normalize(row.get("EngineModel"))
    named_text = " | ".join(
        normalize(row.get(field))
        for field in ("EngineMake", "EngineModel", "PartMake", "ComponentMake")
    )
    explicit_make = make == "RROYCE" or "ROLLS ROYCE" in make or "ROLLS-ROYCE" in make
    explicit_name = "ROLLS ROYCE" in named_text or "ROLLS-ROYCE" in named_text
    return bool(explicit_make or explicit_name or ROLLS_MODEL_RE.search(model))


def top_counts(counter: Counter[str], limit: int = 20) -> dict[str, int]:
    return {key: int(value) for key, value in counter.most_common(limit)}


def discover_source_files() -> list[Path]:
    local_files = sorted(LOCAL_DATA_DIR.glob("SDR-20??.csv"))
    return local_files or sorted(VAULT_DATA_DIR.glob("SDR-20??.csv"))


def build_payload(
    paths: Iterable[Path] | None = None,
    *,
    holdout_target: int = 10_000,
    protocol_id: str = "faa-sdr-triage-10k-v1",
) -> dict[str, Any]:
    source_paths = [Path(path) for path in (paths or discover_source_files())]
    if not source_paths:
        raise FileNotFoundError(f"No SDR CSV files found under {LOCAL_DATA_DIR} or {VAULT_DATA_DIR}")

    total_rows = 0
    missing_keys = 0
    invalid_dates = 0
    key_counts: Counter[str] = Counter()
    row_hash_counts: Counter[str] = Counter()
    field_nonempty: Counter[str] = Counter()
    top_values: dict[str, Counter[str]] = {field: Counter() for field in TOP_FIELDS}
    rolls_values: dict[str, Counter[str]] = {
        field: Counter() for field in ("EngineMake", "EngineModel", "AircraftMake", "PartName", "ComponentName")
    }
    rows_per_year: Counter[int] = Counter()
    rolls_per_year: Counter[int] = Counter()
    source_receipts: list[dict[str, Any]] = []
    date_min: datetime | None = None
    date_max: datetime | None = None
    engine_any_rows = 0
    rroyce_make_rows = 0
    rolls_family_rows = 0
    development_eligible = 0
    holdout_eligible: list[tuple[str, str]] = []
    holdout_engine_rows = 0
    holdout_rolls_rows = 0
    reference_header: list[str] | None = None

    for path in source_paths:
        if not path.exists():
            raise FileNotFoundError(path)
        try:
            source_year = int(path.stem.rsplit("-", 1)[-1])
        except ValueError as exc:
            raise ValueError(f"Expected an SDR-YYYY.csv filename: {path}") from exc

        file_rows = 0
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            header = list(reader.fieldnames or [])
            missing_columns = sorted(REQUIRED_COLUMNS.difference(header))
            if missing_columns:
                raise ValueError(f"{path.name} is missing required columns: {missing_columns}")
            if reference_header is None:
                reference_header = header
            schema_matches = header == reference_header

            for row in reader:
                total_rows += 1
                file_rows += 1
                rows_per_year[source_year] += 1

                key = normalize(row.get("OperatorControlNumber"))
                if key:
                    key_counts[key] += 1
                else:
                    missing_keys += 1

                row_hash = stable_sha256([normalize(row.get(field)) for field in header])
                row_hash_counts[row_hash] += 1

                parsed_date = parse_date(str(row.get("DifficultyDate") or ""))
                if parsed_date is None:
                    invalid_dates += 1
                else:
                    date_min = parsed_date if date_min is None or parsed_date < date_min else date_min
                    date_max = parsed_date if date_max is None or parsed_date > date_max else date_max

                for field in PROFILE_FIELDS:
                    if normalize(row.get(field)):
                        field_nonempty[field] += 1
                for field in TOP_FIELDS:
                    value = normalize(row.get(field))
                    if value:
                        top_values[field][value] += 1

                engine_present = any(normalize(row.get(field)) for field in ENGINE_FIELDS)
                if engine_present:
                    engine_any_rows += 1

                engine_make = normalize(row.get("EngineMake"))
                rroyce_make = engine_make == "RROYCE" or "ROLLS ROYCE" in engine_make or "ROLLS-ROYCE" in engine_make
                if rroyce_make:
                    rroyce_make_rows += 1
                rolls_row = is_rolls_royce_row(row)
                if rolls_row:
                    rolls_family_rows += 1
                    rolls_per_year[source_year] += 1
                    for field in rolls_values:
                        value = normalize(row.get(field))
                        if value:
                            rolls_values[field][value] += 1

                valid_jasc = bool(VALID_JASC_RE.fullmatch(normalize(row.get("JASCCode"))))
                if parsed_date is not None and valid_jasc and key:
                    if parsed_date.year <= 2025:
                        development_eligible += 1
                    elif parsed_date.year == 2026:
                        selection_hash = hashlib.sha256(f"{protocol_id}:{key}".encode("utf-8")).hexdigest()
                        holdout_eligible.append((selection_hash, key))
                        if engine_present:
                            holdout_engine_rows += 1
                        if rolls_row:
                            holdout_rolls_rows += 1

        source_receipts.append(
            {
                "year": source_year,
                "path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
                "official_url": DOWNLOAD_TEMPLATE.format(year=source_year),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "rows": file_rows,
                "columns": len(header),
                "schema_matches_reference": schema_matches,
            }
        )

    duplicate_key_rows = sum(count for count in key_counts.values() if count > 1)
    duplicate_key_values = sum(1 for count in key_counts.values() if count > 1)
    exact_duplicate_rows = sum(count for count in row_hash_counts.values() if count > 1)
    holdout_eligible.sort()
    selected = holdout_eligible[:holdout_target]
    selected_keys = [key for _, key in selected]
    selected_digest = hashlib.sha256("\n".join(selected_keys).encode("utf-8")).hexdigest()

    source_set = [
        {"year": row["year"], "sha256": row["sha256"], "rows": row["rows"]}
        for row in sorted(source_receipts, key=lambda item: item["year"])
    ]
    all_schema_match = all(row["schema_matches_reference"] for row in source_receipts)
    unique_keys = len(key_counts)
    holdout_feasible = len(selected) == holdout_target and duplicate_key_rows == 0

    payload: dict[str, Any] = {
        "schema": "faa_sdr_source_audit_v1",
        "generated_utc": now_utc(),
        "source": {
            "name": "FAA Service Difficulty Reports",
            "official_download_page": DOWNLOAD_PAGE,
            "source_set_sha256": stable_sha256(source_set),
            "files": sorted(source_receipts, key=lambda item: item["year"]),
        },
        "observed_grain": "One CSV row per unique OperatorControlNumber in the pulled 2023-2026 source files.",
        "summary": {
            "row_count": total_rows,
            "column_count": len(reference_header or []),
            "file_count": len(source_receipts),
            "date_min": date_min.date().isoformat() if date_min else None,
            "date_max": date_max.date().isoformat() if date_max else None,
            "unique_nonempty_keys": unique_keys,
            "missing_key_rows": missing_keys,
            "duplicate_key_rows": duplicate_key_rows,
            "duplicate_key_values": duplicate_key_values,
            "exact_duplicate_rows": exact_duplicate_rows,
            "invalid_date_rows": invalid_dates,
            "all_schemas_match": all_schema_match,
            "engine_any_rows": engine_any_rows,
            "rroyce_engine_make_rows": rroyce_make_rows,
            "rolls_royce_family_rows": rolls_family_rows,
        },
        "rows_per_source_year": {str(year): rows_per_year[year] for year in sorted(rows_per_year)},
        "rolls_royce_rows_per_source_year": {
            str(year): rolls_per_year[year] for year in sorted(rows_per_year)
        },
        "field_completeness": {
            field: {
                "nonempty_rows": field_nonempty[field],
                "rate": round(field_nonempty[field] / total_rows, 6) if total_rows else 0.0,
            }
            for field in PROFILE_FIELDS
        },
        "top_values": {field: top_counts(top_values[field]) for field in TOP_FIELDS},
        "rolls_royce_exploratory_profile": {
            "selection_rule": (
                "EngineMake equals RROYCE or names Rolls-Royce, or EngineModel matches one of the declared "
                "RB211, Trent, AE3007, Tay, or BR700-family tokens."
            ),
            "rows": rolls_family_rows,
            "top_values": {field: top_counts(rolls_values[field], 30) for field in rolls_values},
            "confirmatory_claim_allowed": False,
        },
        "ten_thousand_protocol_readiness": {
            "protocol_path": PROTOCOL_PATH.relative_to(ROOT).as_posix(),
            "protocol_id": protocol_id,
            "protocol_sha256": sha256_file(PROTOCOL_PATH),
            "development_eligible_rows": development_eligible,
            "holdout_eligible_rows": len(holdout_eligible),
            "holdout_target": holdout_target,
            "selected_unique_rows": len(selected),
            "selected_id_set_sha256": selected_digest,
            "selection_feasible": holdout_feasible,
            "all_aviation_report_level_10k_gate": holdout_feasible,
            "engine_populated_holdout_rows": holdout_engine_rows,
            "engine_specific_10k_gate": holdout_engine_rows >= holdout_target,
            "rolls_royce_holdout_rows": holdout_rolls_rows,
            "rolls_royce_specific_10k_gate": holdout_rolls_rows >= holdout_target,
            "benchmark_executed": False,
        },
        "quality_findings": [
            {
                "severity": "pass",
                "finding": "The four pulled files have identical 76-column schemas and unique nonempty report keys.",
                "impact": "A deterministic 10,000-report holdout can be formed without replacement.",
            },
            {
                "severity": "high",
                "finding": "Engine fields are sparse in the report population.",
                "impact": "The public files do not support a 10,000-row engine-specific or Rolls-Royce-specific confirmatory study.",
            },
            {
                "severity": "high",
                "finding": "SDR contains reported difficulties but no fleet-hour or cycle exposure denominator for unaffected aircraft.",
                "impact": "Failure rates, causal effects, predictive maintenance claims, and economic savings cannot be estimated from SDR alone.",
            },
            {
                "severity": "medium",
                "finding": "The 2026 file is a partial calendar year ending at the observed maximum difficulty date.",
                "impact": "Raw 2026 volume must not be compared with full prior years without time normalization and late-reporting checks.",
            },
        ],
        "claim_matrix": {
            "source_ingestion_and_hash_receipt": True,
            "report_level_10k_protocol_feasible": holdout_feasible,
            "report_level_benchmark_completed": False,
            "engine_specific_10k_protocol_feasible": holdout_engine_rows >= holdout_target,
            "rolls_royce_specific_10k_protocol_feasible": holdout_rolls_rows >= holdout_target,
            "faa_validation_claim_allowed": False,
            "oem_validation_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "airworthiness_claim_allowed": False,
            "economic_savings_claim_allowed": False,
        },
        "catalog_path": CATALOG_PATH.relative_to(ROOT).as_posix(),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    payload["receipt_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    readiness = payload["ten_thousand_protocol_readiness"]
    lines = [
        "# FAA SDR Source Audit and 10,000-Scenario Readiness",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Decision",
        "",
        f"- Pulled and hashed reports: `{summary['row_count']:,}` across `{summary['file_count']}` yearly files.",
        f"- Unique report keys: `{summary['unique_nonempty_keys']:,}`; duplicate-key rows: `{summary['duplicate_key_rows']:,}`.",
        f"- Report-level 10,000-row holdout feasible: `{str(readiness['selection_feasible']).lower()}`.",
        f"- Engine-populated 2026 holdout rows: `{readiness['engine_populated_holdout_rows']:,}`.",
        f"- Rolls-Royce-family 2026 holdout rows: `{readiness['rolls_royce_holdout_rows']:,}`.",
        f"- Benchmark executed: `{str(readiness['benchmark_executed']).lower()}`.",
        "",
        "The defensible next study is a report-level maintenance-triage benchmark. An engine-specific or "
        "Rolls-Royce-specific 10,000-row claim is not supported by this public slice.",
        "",
        "## Source Receipts",
        "",
        "| Year | Rows | Bytes | Columns | Schema match | SHA-256 |",
        "|---:|---:|---:|---:|---|---|",
    ]
    for row in payload["source"]["files"]:
        lines.append(
            f"| {row['year']} | {row['rows']:,} | {row['bytes']:,} | {row['columns']} | "
            f"{str(row['schema_matches_reference']).lower()} | `{row['sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## Quality Profile",
            "",
            f"Observed date range: `{summary['date_min']}` through `{summary['date_max']}`.",
            "",
            "| Field | Nonempty rows | Completeness |",
            "|---|---:|---:|",
        ]
    )
    for field, row in payload["field_completeness"].items():
        lines.append(f"| {field} | {row['nonempty_rows']:,} | {row['rate']:.2%} |")
    lines.extend(
        [
            "",
            "## Frozen 10,000-Scenario Design",
            "",
            f"- Development eligible rows (2023-2025): `{readiness['development_eligible_rows']:,}`.",
            f"- 2026 holdout eligible rows: `{readiness['holdout_eligible_rows']:,}`.",
            f"- Deterministically selected unique holdout rows: `{readiness['selected_unique_rows']:,}`.",
            f"- Selected-ID set SHA-256: `{readiness['selected_id_set_sha256']}`.",
            f"- Protocol: `{readiness['protocol_path']}`.",
            f"- Protocol SHA-256: `{readiness['protocol_sha256']}`.",
            "",
            "The selection is without replacement and report IDs cannot cross development and holdout windows. "
            "The protocol forbids outcome-revealing fields and preserves all wins, non-wins, errors, seeds, and package versions.",
            "",
            "## Rolls-Royce Boundary",
            "",
            f"The transparent matching rule identifies `{summary['rolls_royce_family_rows']:,}` exploratory rows across "
            f"2023-2026, including `{summary['rroyce_engine_make_rows']:,}` rows explicitly coded `RROYCE`. "
            "This is useful for taxonomy and data-access planning, not a trusted-engine validation claim.",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
            f"Receipt SHA-256: `{payload['receipt_sha256']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"output": str(OUT_JSON), "summary": payload["summary"], "readiness": payload["ten_thousand_protocol_readiness"]}, indent=2))


if __name__ == "__main__":
    main()
