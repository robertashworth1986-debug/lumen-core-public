from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

READINESS_JSON = OUT_OPS / "grant_submission_readiness_audit_latest.json"
DICE_LOCK_JSON = OUT_OPS / "dice_submission_lock_packet_latest.json"
HARBOR_AIS_JSON = OUT_OPS / "harbor_ais_pilot_registry_latest.json"
HARBOR_DATA_JSON = OUT_OPS / "harbor_data_source_readiness_audit_latest.json"
HARBOR_AIS_ACQUISITION_JSON = OUT_OPS / "harbor_ais_pilot_acquisition_latest.json"
HARBOR_AIS_SPLITS_JSON = OUT_OPS / "harbor_ais_heldout_splits_latest.json"
HARBOR_PUBLIC_AIS_GATE_JSON = OUT_OPS / "harbor_public_ais_gate_latest.json"
HARBOR_AIS_IO_PREFLIGHT_JSON = OUT_OPS / "harbor_ais_io_preflight_latest.json"
HARBOR_AIS_INJECTION_JSON = OUT_OPS / "harbor_ais_injection_benchmark_latest.json"

OPS_FEED_JSON = OUT_OPS / "grant_dashboard_status_feed_latest.json"
DASHBOARD_FEED_JSON = DASHBOARD_DATA / "grant_readiness_status.json"


BOUNDARIES = [
    "No grant is marked submitted by this feed.",
    "Portal authority, certifications, and action-time submit approval remain user gates.",
    "Synthetic benchmarks support bounded software feasibility only, not field validation.",
    "HarborSentinel public AIS has raw acquisition, held-out splits, and a single-lane readiness gate; this is data-readiness evidence, not detection-performance or field validation.",
    "HarborSentinel controlled-injection benchmarking is detector-vs-baseline evidence on public AIS perturbations, not real adversary detection, multi-source fusion, or field validation.",
    "Trading, Kraken, live-breadth, or frozen-delta artifacts must not be cited as profit proof.",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def compact_package(package: dict[str, Any]) -> dict[str, Any]:
    required = package.get("required_artifacts", [])
    if not isinstance(required, list):
        required = []
    manifests = package.get("evidence_manifests", [])
    if not isinstance(manifests, list):
        manifests = []
    render = package.get("render") if isinstance(package.get("render"), dict) else None

    return {
        "name": str(package.get("name", "")),
        "portal": str(package.get("portal", "")),
        "readiness": str(package.get("readiness", "")),
        "required_artifacts_present": sum(1 for row in required if isinstance(row, dict) and row.get("exists")),
        "required_artifacts_total": len(required),
        "manifest_matched": sum(int(row.get("matched", 0)) for row in manifests if isinstance(row, dict)),
        "manifest_expected": sum(int(row.get("expected", 0)) for row in manifests if isinstance(row, dict)),
        "render_ok": bool(render.get("ok")) if render else None,
        "local_blockers": len(package.get("local_blockers", []) or []),
        "portal_user_blockers": len(package.get("portal_user_blockers", []) or []),
    }


def source_probe_summary(harbor_ais: dict[str, Any]) -> dict[str, Any]:
    candidates = []
    rows = (
        harbor_ais.get("candidate_sources", [])
        or harbor_ais.get("candidates", [])
        or harbor_ais.get("sources", [])
        or []
    )
    for row in rows:
        if not isinstance(row, dict):
            continue
        probe = row.get("probe") if isinstance(row.get("probe"), dict) else {}
        candidates.append(
            {
                "label": str(row.get("label") or row.get("name") or row.get("id") or "source"),
                "url": str(row.get("url") or row.get("href") or ""),
                "status_code": probe.get("status_code") or row.get("status_code"),
                "content_length_bytes": probe.get("content_length_bytes") or probe.get("bytes") or row.get("content_length_bytes"),
                "download_allowed": bool(row.get("download_allowed", False)),
            }
        )
    return {
        "posture": str(harbor_ais.get("posture", "UNKNOWN")),
        "candidate_count": len(candidates),
        "candidates": candidates[:5],
    }


def io_preflight_summary(preflight: dict[str, Any]) -> dict[str, Any]:
    if not preflight:
        return {
            "posture": "NOT_RUN",
            "required_ok": 0,
            "required_files": 0,
            "any_timeout": False,
            "probes": [],
            "claim_boundary": (
                "No AIS split I/O preflight artifact is available in this feed. "
                "Do not run or cite controlled-injection results until the frozen split is readable."
            ),
        }
    probes = []
    for row in preflight.get("probes", []) or []:
        if not isinstance(row, dict):
            continue
        probes.append(
            {
                "label": str(row.get("label", "")),
                "status": str(row.get("status", "")),
                "ok": bool(row.get("ok", False)),
                "expected_bytes": row.get("expected_bytes"),
                "actual_bytes": row.get("actual_bytes"),
                "size_matches": row.get("size_matches"),
                "sample_bytes_read": row.get("sample_bytes_read"),
                "timeout_seconds": row.get("timeout_seconds"),
                "elapsed_seconds": row.get("elapsed_seconds"),
                "full_hash_requested": bool(row.get("full_hash_requested", False)),
                "sha256_matches": row.get("sha256_matches"),
            }
        )
    summary = preflight.get("summary", {}) if isinstance(preflight.get("summary"), dict) else {}
    return {
        "posture": str(preflight.get("posture", "UNKNOWN")),
        "required_ok": int(summary.get("required_ok", 0) or 0),
        "required_files": int(summary.get("required_files", 0) or 0),
        "all_required_ok": bool(summary.get("all_required_ok", False)),
        "any_timeout": bool(summary.get("any_timeout", False)),
        "full_hash_match_count": summary.get("full_hash_match_count"),
        "timeout_seconds": preflight.get("timeout_seconds"),
        "sample_bytes": preflight.get("sample_bytes"),
        "full_hash": bool(preflight.get("full_hash", False)),
        "probes": probes,
        "next_gate": str(preflight.get("next_gate", "")),
        "claim_boundary": str(preflight.get("claim_boundary", "")),
    }


def injection_benchmark_summary(benchmark: dict[str, Any]) -> dict[str, Any]:
    if not benchmark:
        return {
            "posture": "NOT_RUN",
            "total_injected_segments": 0,
            "motion_consistency_recall": 0.0,
            "speed_only_baseline_recall": 0.0,
            "recall_lift_vs_speed_only": 0.0,
            "families": {},
            "claim_boundary": (
                "No controlled-injection benchmark artifact is available in this feed. "
                "Do not cite HarborSentinel detector performance from this lane."
            ),
        }
    result = benchmark.get("controlled_injection_benchmark", {})
    families = result.get("families", {}) if isinstance(result.get("families"), dict) else {}
    safe_families: dict[str, Any] = {}
    for name, row in families.items():
        if not isinstance(row, dict):
            continue
        safe_families[str(name)] = {
            "injected_segments": row.get("injected_segments"),
            "motion_consistency_recall": row.get("motion_consistency_recall"),
            "speed_only_baseline_recall": row.get("speed_only_baseline_recall"),
            "boundary": row.get("boundary", ""),
        }
    return {
        "posture": str(benchmark.get("posture", "UNKNOWN")),
        "development_segments": benchmark.get("development", {}).get("segments"),
        "validation_segments": benchmark.get("validation", {}).get("segments"),
        "total_injected_segments": result.get("total_injected_segments", 0),
        "motion_consistency_recall": result.get("motion_consistency_recall", 0.0),
        "speed_only_baseline_recall": result.get("speed_only_baseline_recall", 0.0),
        "recall_lift_vs_speed_only": result.get("recall_lift_vs_speed_only", 0.0),
        "families": safe_families,
        "natural_candidate_rates": benchmark.get("natural_candidate_rates", {}),
        "claim_boundary": str(benchmark.get("claim_boundary", "")),
    }


def artifact_velocity(generated: list[tuple[str, datetime]]) -> dict[str, Any]:
    unique = []
    seen = set()
    for name, ts in generated:
        if not name or name in seen:
            continue
        seen.add(name)
        unique.append((name, ts))
    if not unique:
        return {
            "artifact_count": 0,
            "window_seconds": 0,
            "per_second": 0.0,
            "per_minute": 0.0,
            "per_hour": 0.0,
            "measurement_boundary": "No timestamped artifacts were available.",
        }

    times = [ts for _, ts in unique]
    start = min(times)
    end = max(times)
    window_seconds = max((end - start).total_seconds(), 1.0)
    rate = len(unique) / window_seconds
    return {
        "artifact_count": len(unique),
        "window_start_utc": start.isoformat(),
        "window_end_utc": end.isoformat(),
        "window_seconds": round(window_seconds, 3),
        "per_second": round(rate, 6),
        "per_minute": round(rate * 60, 3),
        "per_hour": round(rate * 3600, 3),
        "measurement_boundary": (
            "Rate is computed only from timestamped local artifacts in this feed. "
            "It is not a model benchmark, labor-cost estimate, revenue claim, or funding probability."
        ),
    }


def build_feed() -> dict[str, Any]:
    readiness = read_json(READINESS_JSON)
    dice = read_json(DICE_LOCK_JSON)
    harbor_ais = read_json(HARBOR_AIS_JSON)
    harbor_data = read_json(HARBOR_DATA_JSON)
    harbor_acquisition = read_json(HARBOR_AIS_ACQUISITION_JSON)
    harbor_splits = read_json(HARBOR_AIS_SPLITS_JSON)
    harbor_gate = read_json(HARBOR_PUBLIC_AIS_GATE_JSON)
    harbor_io_preflight = read_json(HARBOR_AIS_IO_PREFLIGHT_JSON)
    harbor_injection_benchmark = read_json(HARBOR_AIS_INJECTION_JSON)

    if not any(
        [
            readiness,
            dice,
            harbor_ais,
            harbor_data,
            harbor_acquisition,
            harbor_splits,
            harbor_gate,
            harbor_io_preflight,
            harbor_injection_benchmark,
        ]
    ):
        public_snapshot = read_json(DASHBOARD_FEED_JSON)
        if public_snapshot.get("schema") == "grant_dashboard_status_feed_v1":
            public_snapshot["generated_utc"] = now_utc()
            public_snapshot["scope"] = "dashboard_safe_grant_readiness_public_snapshot"
            harbor = public_snapshot.get("harbor")
            if isinstance(harbor, dict) and "ais_io_preflight" not in harbor:
                harbor["ais_io_preflight"] = io_preflight_summary({})
            if isinstance(harbor, dict) and "ais_injection_benchmark" not in harbor:
                harbor["ais_injection_benchmark"] = injection_benchmark_summary({})
            return public_snapshot

    packages = [
        compact_package(row)
        for row in readiness.get("packages", [])
        if isinstance(row, dict)
    ]
    generated: list[tuple[str, datetime]] = []
    for name, payload in [
        ("top_five_readiness_audit", readiness),
        ("dice_submission_lock_packet", dice),
        ("harbor_ais_pilot_registry", harbor_ais),
        ("harbor_data_source_readiness_audit", harbor_data),
        ("harbor_ais_pilot_acquisition", harbor_acquisition),
        ("harbor_ais_heldout_splits", harbor_splits),
        ("harbor_public_ais_gate", harbor_gate),
        ("harbor_ais_io_preflight", harbor_io_preflight),
        ("harbor_ais_injection_benchmark", harbor_injection_benchmark),
    ]:
        ts = parse_dt(payload.get("generated_utc"))
        if ts is not None:
            generated.append((name, ts))

    summary = readiness.get("summary", {}) if isinstance(readiness.get("summary"), dict) else {}
    local_blockers = int(summary.get("local_blockers", 0) or 0)
    portal_user_blockers = int(summary.get("portal_user_blockers", 0) or 0)
    posture = str(readiness.get("posture", "UNKNOWN"))
    dice_local_blockers = len(dice.get("local_blockers", []) or [])
    dice_portal_blockers = len(dice.get("portal_user_blockers", []) or [])
    harbor_io = io_preflight_summary(harbor_io_preflight)
    harbor_injection = injection_benchmark_summary(harbor_injection_benchmark)

    return {
        "generated_utc": now_utc(),
        "schema": "grant_dashboard_status_feed_v1",
        "scope": "dashboard_safe_grant_readiness",
        "posture": posture,
        "summary": {
            "packages": int(summary.get("packages", len(packages)) or len(packages)),
            "local_blockers": local_blockers,
            "portal_user_blockers": portal_user_blockers,
            "submitted_by_feed": 0,
            "ready_local_not_portal": local_blockers == 0 and portal_user_blockers > 0,
            "dashboard_signal": "LOCAL_READY_PORTAL_BLOCKED" if local_blockers == 0 else "LOCAL_BLOCKED",
        },
        "priority_cards": [
            {
                "key": "DICE Lock",
                "value": str(dice.get("posture", "UNKNOWN")),
                "sub": f"{dice_local_blockers} local blockers · {dice_portal_blockers} portal/user gates",
                "tone": "warn" if dice_portal_blockers else "good",
            },
            {
                "key": "Top-Five Grants",
                "value": f"{local_blockers} local / {portal_user_blockers} portal",
                "sub": "Local packages are file-ready; submissions remain portal/user gated.",
                "tone": "warn" if portal_user_blockers else "good",
            },
            {
                "key": "Harbor AIS",
                "value": str(harbor_injection.get("posture") or harbor_io.get("posture") or harbor_gate.get("posture") or harbor_acquisition.get("posture") or harbor_ais.get("posture", "SOURCE_PROBED")),
                "sub": (
                    "Controlled public AIS injection benchmark ready; not real-world or field validation."
                    if harbor_injection.get("posture") == "PUBLIC_AIS_INJECTION_BENCHMARK_READY"
                    else
                    "Frozen AIS split I/O must be ready before controlled-injection benchmarking."
                    if harbor_io.get("posture") == "PUBLIC_AIS_SPLIT_IO_BLOCKED"
                    else "Public AIS splits/gate ready; still not multi-source or field validation."
                ),
                "tone": "warn",
            },
            {
                "key": "Builder Velocity",
                "value": "measured",
                "sub": "Artifact throughput only; no revenue claim or award-probability claim.",
                "tone": "good",
            },
        ],
        "packages": packages,
        "dice_lock": {
            "posture": str(dice.get("posture", "UNKNOWN")),
            "local_blockers": dice_local_blockers,
            "portal_user_blockers": dice_portal_blockers,
            "visible_url_count": dice.get("docx_checks", {}).get("visible_text", {}).get("visible_url_count"),
            "placeholder_hits": dice.get("docx_checks", {}).get("visible_text", {}).get("placeholder_hits", []),
            "render_page_png_count": dice.get("render_check", {}).get("page_png_count"),
            "rom_cost_boundary_present": dice.get("docx_checks", {}).get("visible_text", {}).get("rom_cost_boundary_present"),
        },
        "harbor": {
            "data_source_posture": str(harbor_data.get("posture", "UNKNOWN")),
            "ais_pilot": source_probe_summary(harbor_ais),
            "ais_acquisition": {
                "posture": str(harbor_acquisition.get("posture", "NOT_ACQUIRED")),
                "source_url": str(harbor_acquisition.get("source", {}).get("url", "")),
                "raw_file_bytes": harbor_acquisition.get("raw_file", {}).get("bytes"),
                "raw_file_sha256": str(harbor_acquisition.get("raw_file", {}).get("sha256", "")),
                "sample_rows": harbor_acquisition.get("profile", {}).get("sample_rows"),
                "columns": harbor_acquisition.get("profile", {}).get("columns", []),
                "claim_boundary": str(harbor_acquisition.get("claim_boundary", "")),
            },
            "ais_heldout_splits": {
                "posture": str(harbor_splits.get("posture", "NOT_SPLIT")),
                "region": harbor_splits.get("selected_region", {}),
                "development_rows": harbor_splits.get("splits", {}).get("development", {}).get("rows"),
                "validation_rows": harbor_splits.get("splits", {}).get("validation", {}).get("rows"),
                "development_sha256": str(harbor_splits.get("splits", {}).get("development", {}).get("sha256", "")),
                "validation_sha256": str(harbor_splits.get("splits", {}).get("validation", {}).get("sha256", "")),
                "claim_boundary": str(harbor_splits.get("claim_boundary", "")),
            },
            "public_ais_gate": {
                "posture": str(harbor_gate.get("posture", "NOT_RUN")),
                "region": harbor_gate.get("selected_region", {}),
                "development_rows": harbor_gate.get("development", {}).get("row_metrics", {}).get("rows"),
                "validation_rows": harbor_gate.get("validation", {}).get("row_metrics", {}).get("rows"),
                "overlap_mmsi": harbor_gate.get("holdout_overlap", {}).get("overlap_mmsi"),
                "gate_checks": harbor_gate.get("gate_checks", {}),
                "claim_boundary": str(harbor_gate.get("claim_boundary", "")),
            },
            "ais_io_preflight": harbor_io,
            "ais_injection_benchmark": harbor_injection,
            "external_raw_data_rule": (
                "Stage large NOAA/MarineCadastre/public AIS files on an external raw-data volume "
                "via LUMA_HARBOR_DATA_ROOT; commit only hashes, manifests, schema profiles, and bounded summaries."
            ),
        },
        "builder_velocity": artifact_velocity(generated),
        "claim_boundaries": BOUNDARIES,
        "source_files": {
            "readiness_audit": "out/ops/grant_submission_readiness_audit_latest.json",
            "dice_lock": "out/ops/dice_submission_lock_packet_latest.json",
            "harbor_ais": "out/ops/harbor_ais_pilot_registry_latest.json",
            "harbor_data": "out/ops/harbor_data_source_readiness_audit_latest.json",
            "harbor_ais_acquisition": "out/ops/harbor_ais_pilot_acquisition_latest.json",
            "harbor_ais_splits": "out/ops/harbor_ais_heldout_splits_latest.json",
            "harbor_public_ais_gate": "out/ops/harbor_public_ais_gate_latest.json",
            "harbor_ais_io_preflight": "out/ops/harbor_ais_io_preflight_latest.json",
            "harbor_ais_injection_benchmark": "out/ops/harbor_ais_injection_benchmark_latest.json",
        },
    }


def main() -> int:
    feed = build_feed()
    write_json(OPS_FEED_JSON, feed)
    write_json(DASHBOARD_FEED_JSON, feed)
    print(
        json.dumps(
            {
                "posture": feed["posture"],
                "local_blockers": feed["summary"]["local_blockers"],
                "portal_user_blockers": feed["summary"]["portal_user_blockers"],
                "ops_json": str(OPS_FEED_JSON.relative_to(ROOT)).replace("\\", "/"),
                "dashboard_json": str(DASHBOARD_FEED_JSON.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
