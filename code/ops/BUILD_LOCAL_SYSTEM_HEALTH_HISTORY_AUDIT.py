#!/usr/bin/env python3
"""Build a read-only, public-safe audit of legacy LumenHybrid health snapshots.

The source tree is treated as immutable evidence. The builder reads snapshots,
sidecars, proof archives, the custody ledger, and the legacy collector script;
it writes only fixed repository artifacts. Published output uses aliases and
hashes, never source paths, usernames, host identity, or drive letters.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "out" / "ops" / "local_system_health_history_audit_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "local_system_health_history_audit.json"
OUT_MD = ROOT / "docs" / "LOCAL_SYSTEM_HEALTH_HISTORY_AUDIT_2026-07-14.md"

HORIZONS_DAYS = (30, 90, 180)
SNAPSHOT_GLOB = "meso_sys_*.json"
PROOF_GLOB = "MESO_SYS_*.zip"
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
UTC_TOKEN = re.compile(r"(\d{8}T\d{6}Z)", re.IGNORECASE)
LEDGER_MESO = re.compile(
    r"^(?P<event>\d{8}T\d{6}Z)\|MESO_SYS\|"
    r"PATH=(?P<snapshot>.*?) SHA=(?P<snapshot_sha>[0-9a-fA-F]{64}) "
    r"ZIP=(?P<proof>.*?) ZIP_SHA=(?P<proof_sha>[0-9a-fA-F]{64})$"
)
LEGACY_CPU_POINT_SAMPLE_SECONDS = 1

CLAIM_BOUNDARY = (
    "This audit summarizes local, unevenly spaced point observations. Each legacy CPU value is a single "
    "one-second sample, not continuous utilization. Sparse point samples and free-space deltas can identify "
    "observed pressure and capacity change, but they cannot establish hardware degradation, root cause, "
    "prevented failure, field validation, independent validation, or a medical or safety diagnosis. The legacy "
    "collector does not measure temperature, SMART or NVMe wear, battery health or cycles, fan speed, GPU state, "
    "power state, network health, or per-process attribution."
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def stable_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_basename(value: str) -> str:
    """Return a basename for either Windows or POSIX ledger syntax."""

    return value.replace("\\", "/").rsplit("/", 1)[-1]


def artifact_alias(kind: str, filename: str) -> str:
    match = UTC_TOKEN.search(filename)
    token = match.group(1).upper() if match else sha256_bytes(filename.encode("utf-8"))[:16]
    return f"legacy_{kind}_{token}"


def file_receipt(kind: str, path: Path) -> dict[str, Any]:
    return {
        "alias": artifact_alias(kind, path.name),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def set_receipt(alias: str, rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    manifest_rows = sorted(
        (
            {
                "alias": str(row["alias"]),
                "bytes": int(row["bytes"]),
                "sha256": str(row["sha256"]),
            }
            for row in rows
        ),
        key=lambda row: row["alias"],
    )
    return {
        "alias": alias,
        "record_count": len(manifest_rows),
        "logical_bytes": sum(row["bytes"] for row in manifest_rows),
        "manifest_sha256": stable_sha256(manifest_rows),
    }


def optional_file_receipt(alias: str, path: Path, *, record_count: int | None = None) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {
            "alias": alias,
            "available": False,
            "bytes": 0,
            "sha256": None,
            "record_count": 0 if record_count is None else record_count,
        }
    row: dict[str, Any] = {
        "alias": alias,
        "available": True,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if record_count is not None:
        row["record_count"] = record_count
    return row


def defect(code: str, alias: str, severity: str, detail: str) -> dict[str, str]:
    return {
        "code": code,
        "artifact_alias": alias,
        "severity": severity,
        "detail": detail,
    }


def parse_observed_utc(value: Any) -> datetime:
    text = str(value or "").strip()
    try:
        return datetime.strptime(text, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("snapshot UTC has no offset")
        return parsed.astimezone(timezone.utc)


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def load_snapshot_sources(snapshot_dir: Path) -> dict[str, Any]:
    if not snapshot_dir.exists() or not snapshot_dir.is_dir():
        raise FileNotFoundError("legacy snapshot source is unavailable")

    receipts: list[dict[str, Any]] = []
    sidecar_receipts: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    findings: list[dict[str, str]] = []
    source_rows: dict[str, dict[str, Any]] = {}

    for path in sorted(snapshot_dir.glob(SNAPSHOT_GLOB), key=lambda item: item.name):
        receipt = file_receipt("snapshot", path)
        receipts.append(receipt)
        alias = receipt["alias"]
        source_rows[path.name] = {
            "alias": alias,
            "sha256": receipt["sha256"],
            "bytes": receipt["bytes"],
        }

        if receipt["bytes"] == 0:
            findings.append(defect("snapshot_zero_bytes", alias, "high", "Snapshot file is empty."))

        sidecar = path.with_name(path.name + ".sha256.txt")
        if not sidecar.exists():
            findings.append(
                defect("snapshot_sidecar_missing", alias, "high", "Snapshot has no SHA-256 sidecar.")
            )
        else:
            sidecar_receipt = file_receipt("snapshot_sidecar", sidecar)
            sidecar_receipts.append(sidecar_receipt)
            claimed = sidecar.read_text(encoding="utf-8-sig", errors="replace").strip().split()
            claimed_hash = claimed[0].lower() if claimed else ""
            if not HEX_64.fullmatch(claimed_hash):
                findings.append(
                    defect(
                        "snapshot_sidecar_invalid",
                        alias,
                        "high",
                        "Snapshot sidecar does not contain one valid SHA-256 value.",
                    )
                )
            elif claimed_hash != receipt["sha256"]:
                findings.append(
                    defect(
                        "snapshot_sidecar_hash_mismatch",
                        alias,
                        "critical",
                        "Snapshot bytes do not match the sidecar claim.",
                    )
                )

        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            findings.append(
                defect("snapshot_json_invalid", alias, "high", "Snapshot is not valid UTF-8 JSON.")
            )
            continue
        if not isinstance(payload, dict):
            findings.append(
                defect("snapshot_shape_invalid", alias, "high", "Snapshot JSON is not an object.")
            )
            continue

        try:
            observed_at = parse_observed_utc(payload.get("utc"))
        except (TypeError, ValueError):
            findings.append(
                defect("snapshot_utc_invalid", alias, "high", "Snapshot UTC field is invalid.")
            )
            continue

        cpu = finite_number(payload.get("cpu_pct"))
        if cpu is None or not 0 <= cpu <= 100:
            findings.append(
                defect("snapshot_cpu_invalid", alias, "medium", "CPU point sample is absent or out of range.")
            )
            cpu = None

        mem_free = finite_number(payload.get("mem_free_mb"))
        mem_total = finite_number(payload.get("mem_total_mb"))
        if (
            mem_free is None
            or mem_total is None
            or mem_total <= 0
            or mem_free < 0
            or mem_free > mem_total
        ):
            findings.append(
                defect("snapshot_memory_invalid", alias, "medium", "Memory values are absent or inconsistent.")
            )
            mem_free = None
            mem_total = None

        uptime = finite_number(payload.get("uptime_s"))
        if uptime is None or uptime < 0:
            findings.append(
                defect("snapshot_uptime_invalid", alias, "low", "Uptime is absent or negative.")
            )
            uptime = None

        disks: list[dict[str, Any]] = []
        raw_disks = payload.get("disks")
        if not isinstance(raw_disks, list):
            findings.append(
                defect("snapshot_volume_list_invalid", alias, "medium", "Volume observations are not a list.")
            )
            raw_disks = []
        for index, row in enumerate(raw_disks):
            if not isinstance(row, dict):
                findings.append(
                    defect(
                        "snapshot_volume_invalid",
                        alias,
                        "medium",
                        f"Volume observation {index + 1} is not an object.",
                    )
                )
                continue
            source_id = str(row.get("drive") or "").strip().upper()
            free_gb = finite_number(row.get("freeGB"))
            size_gb = finite_number(row.get("sizeGB"))
            if (
                not source_id
                or free_gb is None
                or size_gb is None
                or size_gb <= 0
                or free_gb < 0
                or free_gb > size_gb
            ):
                findings.append(
                    defect(
                        "snapshot_volume_invalid",
                        alias,
                        "medium",
                        f"Volume observation {index + 1} is absent or inconsistent.",
                    )
                )
                continue
            disks.append({"source_id": source_id, "free_gb": free_gb, "size_gb": size_gb})

        observations.append(
            {
                "source_name": path.name,
                "alias": alias,
                "observed_at": observed_at,
                "cpu_pct": cpu,
                "mem_free_mb": mem_free,
                "mem_total_mb": mem_total,
                "uptime_s": uptime,
                "disks": disks,
            }
        )

    observations.sort(key=lambda row: (row["observed_at"], row["source_name"]))
    by_timestamp = Counter(row["observed_at"] for row in observations)
    for observed_at, count in sorted(by_timestamp.items()):
        if count > 1:
            findings.append(
                defect(
                    "snapshot_timestamp_duplicate",
                    f"legacy_snapshot_time_{observed_at.strftime('%Y%m%dT%H%M%SZ')}",
                    "high",
                    f"{count} valid snapshots claim the same UTC timestamp.",
                )
            )

    return {
        "receipts": receipts,
        "sidecar_receipts": sidecar_receipts,
        "observations": observations,
        "findings": findings,
        "source_rows": source_rows,
    }


def load_proof_sources(proof_dir: Path) -> dict[str, Any]:
    receipts: list[dict[str, Any]] = []
    findings: list[dict[str, str]] = []
    source_rows: dict[str, dict[str, Any]] = {}
    if not proof_dir.exists() or not proof_dir.is_dir():
        return {"receipts": receipts, "findings": findings, "source_rows": source_rows}
    for path in sorted(proof_dir.glob(PROOF_GLOB), key=lambda item: item.name):
        receipt = file_receipt("proof", path)
        receipts.append(receipt)
        source_rows[path.name] = {
            "alias": receipt["alias"],
            "sha256": receipt["sha256"],
            "bytes": receipt["bytes"],
        }
        if receipt["bytes"] == 0:
            findings.append(defect("proof_zero_bytes", receipt["alias"], "high", "Proof archive is empty."))
    return {"receipts": receipts, "findings": findings, "source_rows": source_rows}


def load_ledger(ledger_path: Path) -> dict[str, Any]:
    if not ledger_path.exists() or not ledger_path.is_file():
        return {
            "available": False,
            "line_count": 0,
            "records": [],
            "findings": [
                defect("ledger_missing", "legacy_health_custody_ledger", "critical", "Custody ledger is unavailable.")
            ],
            "receipt": optional_file_receipt("legacy_health_custody_ledger", ledger_path, record_count=0),
        }
    text = ledger_path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    records: list[dict[str, str]] = []
    findings: list[dict[str, str]] = []
    for line_number, line in enumerate(lines, start=1):
        if "|MESO_SYS|" not in line:
            continue
        match = LEDGER_MESO.fullmatch(line.strip())
        if not match:
            findings.append(
                defect(
                    "ledger_meso_record_malformed",
                    f"legacy_ledger_line_{line_number}",
                    "high",
                    "MESO ledger row does not match the frozen record grammar.",
                )
            )
            continue
        row = match.groupdict()
        records.append(
            {
                "event": row["event"].upper(),
                "snapshot_name": source_basename(row["snapshot"]),
                "snapshot_sha256": row["snapshot_sha"].lower(),
                "proof_name": source_basename(row["proof"]),
                "proof_sha256": row["proof_sha"].lower(),
            }
        )
    receipt = optional_file_receipt("legacy_health_custody_ledger", ledger_path, record_count=len(lines))
    receipt["meso_record_count"] = len(records)
    return {
        "available": True,
        "line_count": len(lines),
        "records": records,
        "findings": findings,
        "receipt": receipt,
    }


def reconcile_integrity(
    snapshots: dict[str, Any],
    proofs: dict[str, Any],
    ledger: dict[str, Any],
) -> dict[str, Any]:
    findings = list(snapshots["findings"]) + list(proofs["findings"]) + list(ledger["findings"])
    snapshot_rows = snapshots["source_rows"]
    proof_rows = proofs["source_rows"]
    ledgered_snapshots: set[str] = set()
    ledgered_proofs: set[str] = set()
    complete_snapshots: set[str] = set()
    snapshot_reference_counts: Counter[str] = Counter()
    proof_reference_counts: Counter[str] = Counter()

    for row in ledger["records"]:
        snapshot_name = row["snapshot_name"]
        proof_name = row["proof_name"]
        ledgered_snapshots.add(snapshot_name)
        ledgered_proofs.add(proof_name)
        snapshot_reference_counts[snapshot_name] += 1
        proof_reference_counts[proof_name] += 1
        complete = True

        snapshot = snapshot_rows.get(snapshot_name)
        if snapshot is None:
            findings.append(
                defect(
                    "ledger_snapshot_missing",
                    artifact_alias("snapshot", snapshot_name),
                    "critical",
                    "Ledger references a snapshot absent from the audited snapshot set.",
                )
            )
            complete = False
        elif snapshot["sha256"] != row["snapshot_sha256"]:
            findings.append(
                defect(
                    "ledger_snapshot_hash_mismatch",
                    snapshot["alias"],
                    "critical",
                    "Snapshot bytes do not match the ledger hash.",
                )
            )
            complete = False

        proof = proof_rows.get(proof_name)
        if proof is None:
            findings.append(
                defect(
                    "ledger_proof_missing",
                    artifact_alias("proof", proof_name),
                    "critical",
                    "Ledger references a proof archive absent from the audited proof set.",
                )
            )
            complete = False
        elif proof["sha256"] != row["proof_sha256"]:
            findings.append(
                defect(
                    "ledger_proof_hash_mismatch",
                    proof["alias"],
                    "critical",
                    "Proof bytes do not match the ledger hash.",
                )
            )
            complete = False

        if complete:
            complete_snapshots.add(snapshot_name)

    for name, count in sorted(snapshot_reference_counts.items()):
        if count > 1:
            findings.append(
                defect(
                    "ledger_snapshot_duplicate_reference",
                    snapshot_rows.get(name, {"alias": artifact_alias("snapshot", name)})["alias"],
                    "high",
                    f"Snapshot is referenced by {count} MESO ledger rows.",
                )
            )
    for name, count in sorted(proof_reference_counts.items()):
        if count > 1:
            findings.append(
                defect(
                    "ledger_proof_duplicate_reference",
                    proof_rows.get(name, {"alias": artifact_alias("proof", name)})["alias"],
                    "high",
                    f"Proof archive is referenced by {count} MESO ledger rows.",
                )
            )

    for name, row in sorted(snapshot_rows.items()):
        if name not in ledgered_snapshots:
            findings.append(
                defect("snapshot_unledgered", row["alias"], "high", "Snapshot has no MESO custody-ledger row.")
            )
    for name, row in sorted(proof_rows.items()):
        if name not in ledgered_proofs:
            findings.append(
                defect("proof_unledgered", row["alias"], "high", "Proof archive has no MESO custody-ledger row.")
            )

    findings.sort(key=lambda row: (row["code"], row["artifact_alias"], row["detail"]))
    counts = Counter(row["code"] for row in findings)
    return {
        "status": "verified" if not findings else "defects_present",
        "counts": {
            "snapshot_files": len(snapshots["receipts"]),
            "valid_snapshots": len(snapshots["observations"]),
            "snapshot_sidecars": len(snapshots["sidecar_receipts"]),
            "proof_archives": len(proofs["receipts"]),
            "ledger_meso_records": len(ledger["records"]),
            "complete_ledger_receipts": len(complete_snapshots),
            "defect_count": len(findings),
        },
        "defect_counts": dict(sorted(counts.items())),
        "defects": findings,
        "complete_snapshot_names": complete_snapshots,
    }


def percentile(values: Iterable[float], percent: float) -> float | None:
    rows = sorted(float(value) for value in values)
    if not rows:
        return None
    position = (len(rows) - 1) * percent / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return rows[lower]
    weight = position - lower
    return rows[lower] * (1.0 - weight) + rows[upper] * weight


def rounded(value: float | None, digits: int = 6) -> float | None:
    return None if value is None else round(float(value), digits)


def volume_alias_map(observations: list[dict[str, Any]]) -> dict[str, str]:
    ordered: list[str] = []
    for row in observations:
        for volume in row["disks"]:
            source_id = volume["source_id"]
            if source_id not in ordered:
                ordered.append(source_id)
    aliases: dict[str, str] = {}
    for index, source_id in enumerate(ordered):
        aliases[source_id] = "system_volume" if index == 0 else f"auxiliary_volume_{index}"
    return aliases


def cadence_summary(times: list[datetime]) -> dict[str, Any]:
    gaps = [
        (current - prior).total_seconds() / 60.0
        for prior, current in zip(times, times[1:])
        if current >= prior
    ]
    return {
        "gap_count": len(gaps),
        "median_gap_minutes": rounded(statistics.median(gaps) if gaps else None),
        "p95_gap_minutes": rounded(percentile(gaps, 95)),
        "max_gap_minutes": rounded(max(gaps) if gaps else None),
    }


def summarize_window(
    observations: list[dict[str, Any]],
    start: datetime,
    end: datetime,
    *,
    expected_hour_buckets: int,
    volume_aliases: dict[str, str],
) -> dict[str, Any]:
    rows = [row for row in observations if start <= row["observed_at"] <= end]
    times = [row["observed_at"] for row in rows]
    hour_buckets = {
        value.replace(minute=0, second=0, microsecond=0)
        for value in times
    }
    cpu = [row["cpu_pct"] for row in rows if row["cpu_pct"] is not None]
    memory = [
        100.0 * row["mem_free_mb"] / row["mem_total_mb"]
        for row in rows
        if row["mem_free_mb"] is not None and row["mem_total_mb"]
    ]
    volume_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for volume in row["disks"]:
            alias = volume_aliases[volume["source_id"]]
            volume_rows[alias].append(
                {
                    "observed_at": row["observed_at"],
                    "free_gb": volume["free_gb"],
                    "size_gb": volume["size_gb"],
                }
            )

    volumes: dict[str, Any] = {}
    alias_order = sorted(
        volume_rows,
        key=lambda alias: (alias != "system_volume", alias),
    )
    for alias in alias_order:
        samples = volume_rows[alias]
        first = samples[0]
        last = samples[-1]
        minimum = min(samples, key=lambda row: (row["free_gb"], row["observed_at"]))
        volumes[alias] = {
            "sample_count": len(samples),
            "first_observed_utc": iso_utc(first["observed_at"]),
            "first_free_gb": rounded(first["free_gb"]),
            "last_observed_utc": iso_utc(last["observed_at"]),
            "last_free_gb": rounded(last["free_gb"]),
            "delta_free_gb": rounded(last["free_gb"] - first["free_gb"]),
            "minimum_free_gb": rounded(minimum["free_gb"]),
            "minimum_free_observed_utc": iso_utc(minimum["observed_at"]),
        }

    return {
        "window_start_utc": iso_utc(start),
        "window_end_utc": iso_utc(end),
        "snapshot_count": len(rows),
        "unique_snapshot_time_count": len(set(times)),
        "active_utc_date_count": len({value.date() for value in times}),
        "expected_hour_bucket_count": expected_hour_buckets,
        "observed_hour_bucket_count": len(hour_buckets),
        "hour_bucket_coverage_pct": rounded(
            100.0 * len(hour_buckets) / expected_hour_buckets if expected_hour_buckets else None
        ),
        "coverage_definition": (
            "UTC hour buckets containing at least one point sample divided by expected buckets; not duration coverage."
        ),
        "cadence": cadence_summary(times),
        "cpu_point_samples": {
            "sample_seconds_each": LEGACY_CPU_POINT_SAMPLE_SECONDS,
            "valid_sample_count": len(cpu),
            "median_percent": rounded(statistics.median(cpu) if cpu else None),
            "p95_percent": rounded(percentile(cpu, 95)),
            "maximum_percent": rounded(max(cpu) if cpu else None),
            "sustained_utilization_claim_allowed": False,
        },
        "memory_free": {
            "valid_sample_count": len(memory),
            "median_percent": rounded(statistics.median(memory) if memory else None),
            "p10_percent": rounded(percentile(memory, 10)),
            "minimum_percent": rounded(min(memory) if memory else None),
            "samples_below_20_percent": sum(value < 20 for value in memory),
            "samples_below_10_percent": sum(value < 10 for value in memory),
            "samples_below_5_percent": sum(value < 5 for value in memory),
        },
        "volume_free_space": volumes,
        "hardware_degradation_claim_allowed": False,
    }


def build_history_summary(observations: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not observations:
        empty = {
            "valid_snapshot_count": 0,
            "first_observed_utc": None,
            "last_observed_utc": None,
            "elapsed_days": 0.0,
            "active_utc_date_count": 0,
            "expected_hour_bucket_count": 0,
            "observed_hour_bucket_count": 0,
            "hour_bucket_coverage_pct": 0.0,
            "cadence": cadence_summary([]),
        }
        return empty, {str(days): None for days in HORIZONS_DAYS}

    rows = sorted(observations, key=lambda row: (row["observed_at"], row["source_name"]))
    times = [row["observed_at"] for row in rows]
    first = times[0]
    last = times[-1]
    first_hour = first.replace(minute=0, second=0, microsecond=0)
    last_hour = last.replace(minute=0, second=0, microsecond=0)
    expected_hours = int((last_hour - first_hour).total_seconds() // 3600) + 1
    observed_hours = len(
        {value.replace(minute=0, second=0, microsecond=0) for value in times}
    )
    summary = {
        "valid_snapshot_count": len(rows),
        "unique_snapshot_time_count": len(set(times)),
        "first_observed_utc": iso_utc(first),
        "last_observed_utc": iso_utc(last),
        "elapsed_days": rounded((last - first).total_seconds() / 86400.0),
        "active_utc_date_count": len({value.date() for value in times}),
        "expected_hour_bucket_count": expected_hours,
        "observed_hour_bucket_count": observed_hours,
        "hour_bucket_coverage_pct": rounded(100.0 * observed_hours / expected_hours),
        "cadence": cadence_summary(times),
    }
    aliases = volume_alias_map(rows)
    windows = {
        str(days): summarize_window(
            rows,
            last - timedelta(days=days),
            last,
            expected_hour_buckets=days * 24 + 1,
            volume_aliases=aliases,
        )
        for days in HORIZONS_DAYS
    }
    return summary, windows


def build_payload(
    snapshot_dir: Path,
    proof_dir: Path,
    ledger_path: Path,
    collector_path: Path,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    snapshots = load_snapshot_sources(Path(snapshot_dir))
    proofs = load_proof_sources(Path(proof_dir))
    ledger = load_ledger(Path(ledger_path))
    integrity = reconcile_integrity(snapshots, proofs, ledger)
    history, windows = build_history_summary(snapshots["observations"])

    manifest = {
        "schema": "luma.local_system_health_history_source_manifest.v1",
        "snapshot_set": set_receipt("legacy_health_snapshot_set", snapshots["receipts"]),
        "snapshot_sidecar_set": set_receipt(
            "legacy_health_snapshot_sidecar_set", snapshots["sidecar_receipts"]
        ),
        "proof_set": set_receipt("legacy_health_proof_set", proofs["receipts"]),
        "custody_ledger": ledger["receipt"],
        "legacy_collector": optional_file_receipt("legacy_health_collector", Path(collector_path), record_count=1),
    }
    manifest_sha256 = stable_sha256(manifest)
    generated = (generated_at or utc_now()).astimezone(timezone.utc)

    payload: dict[str, Any] = {
        "schema": "luma.local_system_health_history_audit.v1",
        "generated_utc": iso_utc(generated),
        "mode": "read_only_legacy_evidence_audit",
        "evidence_class": "local_unevenly_spaced_point_observation",
        "source_manifest": manifest,
        "source_manifest_sha256": manifest_sha256,
        "summary": history,
        "trailing_windows": windows,
        "integrity": {
            "status": integrity["status"],
            "counts": integrity["counts"],
            "defect_counts": integrity["defect_counts"],
            "defects": integrity["defects"],
        },
        "measurement_boundary": {
            "legacy_cpu_point_sample_seconds": LEGACY_CPU_POINT_SAMPLE_SECONDS,
            "continuous_cpu_observation": False,
            "duration_coverage_calculable": False,
            "uneven_cadence_preserved": True,
            "source_files_repaired_or_rewritten": False,
            "unmeasured_hardware_domains": [
                "battery_health_and_cycles",
                "fan_speed",
                "gpu_state",
                "network_health",
                "power_state",
                "process_attribution",
                "smart_or_nvme_wear",
                "temperature",
            ],
        },
        "claim_controls": {
            "local_pressure_observations_allowed": True,
            "free_space_change_observations_allowed": True,
            "hardware_degradation_claim_allowed": False,
            "root_cause_claim_allowed": False,
            "prevented_failure_claim_allowed": False,
            "independent_validation_claim_allowed": False,
            "field_validation_claim_allowed": False,
        },
        "claim_boundary": CLAIM_BOUNDARY,
    }
    payload["audit_receipt_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    integrity = payload["integrity"]
    manifest = payload["source_manifest"]
    lines = [
        "# Local System Health History Audit",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Decision",
        "",
        f"- Valid point snapshots: `{summary['valid_snapshot_count']:,}`.",
        f"- Observed UTC range: `{summary['first_observed_utc']}` through `{summary['last_observed_utc']}`.",
        f"- Active UTC dates: `{summary['active_utc_date_count']:,}`.",
        f"- UTC-hour bucket coverage: `{summary['hour_bucket_coverage_pct']:.2f}%`.",
        f"- Integrity status: `{integrity['status']}` with `{integrity['counts']['defect_count']:,}` recorded defects.",
        "- Hardware degradation claim allowed: `false`.",
        "",
        "The history contains useful local pressure and free-space observations, but its CPU values are sparse "
        "one-second point samples. It is not a continuous hardware-health or degradation study.",
        "",
        "## Source Manifest Receipts",
        "",
        "| Source alias | Records | Logical bytes | SHA-256 |",
        "|---|---:|---:|---|",
        f"| {manifest['snapshot_set']['alias']} | {manifest['snapshot_set']['record_count']:,} | "
        f"{manifest['snapshot_set']['logical_bytes']:,} | `{manifest['snapshot_set']['manifest_sha256']}` |",
        f"| {manifest['snapshot_sidecar_set']['alias']} | {manifest['snapshot_sidecar_set']['record_count']:,} | "
        f"{manifest['snapshot_sidecar_set']['logical_bytes']:,} | `{manifest['snapshot_sidecar_set']['manifest_sha256']}` |",
        f"| {manifest['proof_set']['alias']} | {manifest['proof_set']['record_count']:,} | "
        f"{manifest['proof_set']['logical_bytes']:,} | `{manifest['proof_set']['manifest_sha256']}` |",
        f"| {manifest['custody_ledger']['alias']} | {manifest['custody_ledger']['record_count']:,} | "
        f"{manifest['custody_ledger']['bytes']:,} | `{manifest['custody_ledger']['sha256']}` |",
        f"| {manifest['legacy_collector']['alias']} | {manifest['legacy_collector']['record_count']:,} | "
        f"{manifest['legacy_collector']['bytes']:,} | `{manifest['legacy_collector']['sha256']}` |",
        "",
        f"Source-manifest SHA-256: `{payload['source_manifest_sha256']}`",
        "",
        "## Exact Trailing Windows",
        "",
        "| Window | Snapshots | Active dates | Observed / expected UTC-hour buckets | CPU median / p95 | "
        "Memory-free median / p10 |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for days in HORIZONS_DAYS:
        row = payload["trailing_windows"][str(days)]
        cpu = row["cpu_point_samples"]
        memory = row["memory_free"]
        lines.append(
            f"| {days} days | {row['snapshot_count']:,} | {row['active_utc_date_count']:,} | "
            f"{row['observed_hour_bucket_count']:,} / {row['expected_hour_bucket_count']:,} | "
            f"{cpu['median_percent']:.2f}% / {cpu['p95_percent']:.2f}% | "
            f"{memory['median_percent']:.2f}% / {memory['p10_percent']:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Integrity Defects",
            "",
            "| Code | Count |",
            "|---|---:|",
        ]
    )
    if integrity["defect_counts"]:
        for code, count in integrity["defect_counts"].items():
            lines.append(f"| {code} | {count:,} |")
    else:
        lines.append("| none | 0 |")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
            f"Audit receipt SHA-256: `{payload['audit_receipt_sha256']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def require_repo_path(path: Path) -> Path:
    resolved_root = ROOT.resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError("audit output must remain inside the repository")
    return resolved


def write_json(path: Path, payload: dict[str, Any]) -> None:
    destination = require_repo_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    destination = require_repo_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_markdown(payload), encoding="utf-8")


def default_source_root() -> Path:
    configured = os.environ.get("LUMA_LEGACY_HEALTH_ROOT")
    if configured:
        return Path(configured)
    system_drive = os.environ.get("SystemDrive", "C:")
    return Path(system_drive + os.sep) / "LumenHybrid"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=default_source_root())
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source_root = args.source_root
    try:
        payload = build_payload(
            source_root / "runs",
            source_root / "proof",
            source_root / "CHAIN_OF_CUSTODY_256.txt",
            source_root / "tools" / "RUN_HYBRID.ps1",
        )
        if not args.check_only:
            write_json(OUT_JSON, payload)
            write_json(DASHBOARD_JSON, payload)
            write_markdown(OUT_MD, payload)
        print(
            json.dumps(
                {
                    "status": "checked" if args.check_only else "written",
                    "output_written": not args.check_only,
                    "schema": payload["schema"],
                    "source_manifest_sha256": payload["source_manifest_sha256"],
                    "valid_snapshot_count": payload["summary"]["valid_snapshot_count"],
                    "defect_count": payload["integrity"]["counts"]["defect_count"],
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {"status": "error", "error_type": type(exc).__name__},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
