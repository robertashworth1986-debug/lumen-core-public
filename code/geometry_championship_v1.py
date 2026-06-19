"""Validate and freeze Geometry Championship V1 readiness.

This is a registry and evidence-gate runner, not a performance tournament.
Lane-specific benchmarks must exist before any family can be promoted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "config" / "geometry_championship_v1_registry.json"
DEFAULT_OUT_ROOT = ROOT / "out" / "geometry_championship_v1"
RUN_TAG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}")

REQUIRED_FAMILY_IDS = {
    "mycelium_network",
    "slime_mold_routing",
    "magnetic_field_geometry",
    "toroidal_fields",
    "halbach_arrays",
    "flower_of_life_hexagonal_packing",
    "non_euclidean_geodesics",
    "frobenius_stability",
    "bird_v_formation_flocking",
    "ant_trails",
    "river_deltas",
    "leaf_veins",
    "vascular_lung_branching",
    "termite_mound_ventilation",
}
PERFORMANCE_READY_STATUSES = {"implemented", "validated"}
LEGACY_STATUSES = {"legacy_analogue_only", "legacy_transform_only"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_commit(root: Path = ROOT) -> str | None:
    try:
        value = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return value or None


def load_registry(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("registry root must be an object")
    return data


def validate_registry(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if registry.get("schema") != "geometry_championship_v1_registry":
        errors.append("unexpected schema")
    if registry.get("cross_lane_ranking_allowed") is not False:
        errors.append("cross-lane ranking must be disabled")

    lanes = registry.get("lanes")
    families = registry.get("families")
    gate = registry.get("promotion_gate")
    if not isinstance(lanes, dict) or not lanes:
        errors.append("lanes must be a non-empty object")
        lanes = {}
    if not isinstance(families, list):
        errors.append("families must be an array")
        families = []
    if not isinstance(gate, dict) or not gate:
        errors.append("promotion_gate must be a non-empty object")

    ids: list[str] = []
    for index, family in enumerate(families):
        if not isinstance(family, dict):
            errors.append(f"family {index} must be an object")
            continue
        family_id = family.get("id")
        lane = family.get("lane")
        status = family.get("status")
        if not isinstance(family_id, str) or not family_id:
            errors.append(f"family {index} has no id")
        else:
            ids.append(family_id)
        if lane not in lanes:
            errors.append(f"{family_id or index} references unknown lane {lane!r}")
        if not isinstance(status, str) or not status:
            errors.append(f"{family_id or index} has no status")

    if len(ids) != len(set(ids)):
        errors.append("family ids must be unique")
    missing = sorted(REQUIRED_FAMILY_IDS - set(ids))
    extra = sorted(set(ids) - REQUIRED_FAMILY_IDS)
    if missing:
        errors.append("missing required families: " + ", ".join(missing))
    if extra:
        errors.append("unexpected families: " + ", ".join(extra))

    frobenius = next(
        (family for family in families if family.get("id") == "frobenius_stability"),
        None,
    )
    if frobenius and frobenius.get("competitor", True) is not False:
        errors.append("Frobenius stability must be a diagnostic, not a competitor")

    for lane_name, lane in lanes.items():
        if not isinstance(lane, dict):
            errors.append(f"lane {lane_name} must be an object")
            continue
        if not lane.get("baselines"):
            errors.append(f"lane {lane_name} has no baselines")
        if not lane.get("metrics"):
            errors.append(f"lane {lane_name} has no metrics")
    return errors


def build_readiness(registry: dict[str, Any]) -> dict[str, Any]:
    families = registry["families"]
    runnable = [
        family["id"]
        for family in families
        if family["status"] in PERFORMANCE_READY_STATUSES
        and family.get("competitor", True)
    ]
    legacy = [
        family["id"]
        for family in families
        if family["status"] in LEGACY_STATUSES
    ]
    pending = [
        family["id"]
        for family in families
        if family["id"] not in runnable and family["id"] not in legacy
    ]
    lane_counts: dict[str, int] = {}
    for family in families:
        lane = str(family["lane"])
        lane_counts[lane] = lane_counts.get(lane, 0) + 1
    return {
        "family_count": len(families),
        "lane_count": len(registry["lanes"]),
        "lane_family_counts": lane_counts,
        "performance_ready_families": runnable,
        "legacy_only_families": legacy,
        "pending_families": pending,
        "championship_ready": bool(runnable) and not pending,
        "performance_results_generated": False,
        "claim_gate_passed": False,
        "verdict": (
            "ready_for_lane_benchmarks"
            if runnable
            else "not_ready_no_performance_implementations"
        ),
    }


def render_scorecard(
    registry: dict[str, Any],
    readiness: dict[str, Any],
    generated_utc: str,
) -> str:
    lines = [
        "# Geometry Championship V1 Readiness",
        "",
        f"Generated UTC: `{generated_utc}`",
        "",
        "## Evidence Boundary",
        "",
        str(registry["evidence_boundary"]),
        "",
        "This run validates and freezes the family registry. It does not report a",
        "geometry performance champion.",
        "",
        "## Readiness",
        "",
        f"- Families registered: {readiness['family_count']}",
        f"- Lanes registered: {readiness['lane_count']}",
        (
            "- Performance-ready families: "
            f"{len(readiness['performance_ready_families'])}"
        ),
        f"- Legacy analogues only: {len(readiness['legacy_only_families'])}",
        f"- Pending families: {len(readiness['pending_families'])}",
        f"- Verdict: `{readiness['verdict']}`",
        "",
        "## Family Status",
        "",
        "| Family | Lane | Status | Competitor |",
        "|---|---|---|---|",
    ]
    for family in registry["families"]:
        lines.append(
            f"| {family['label']} | {family['lane']} | {family['status']} | "
            f"{str(family.get('competitor', True)).lower()} |"
        )
    lines.extend(
        [
            "",
            "## Rule",
            "",
            str(registry["core_rule"]),
            "",
        ]
    )
    return "\n".join(lines)


def write_run(
    registry_path: Path,
    out_dir: Path,
    *,
    generated: datetime | None = None,
) -> dict[str, Any]:
    registry = load_registry(registry_path)
    errors = validate_registry(registry)
    if errors:
        raise ValueError("invalid geometry registry: " + "; ".join(errors))

    generated = generated or utc_now()
    generated_utc = generated.isoformat()
    readiness = build_readiness(registry)
    out_dir.mkdir(parents=True, exist_ok=False)

    snapshot_path = out_dir / "registry.snapshot.json"
    summary_path = out_dir / "summary.json"
    scorecard_path = out_dir / "SCORECARD.md"
    snapshot_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema": "geometry_championship_v1_readiness",
        "generated_utc": generated_utc,
        "source_commit": source_commit(),
        "registry_source": str(registry_path.resolve()),
        "evidence_boundary": registry["evidence_boundary"],
        "readiness": readiness,
        "validation": {
            "registry_valid": True,
            "required_family_ids_present": True,
            "cross_lane_ranking_disabled": True,
            "performance_benchmark_run": False,
        },
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    scorecard_path.write_text(
        render_scorecard(registry, readiness, generated_utc),
        encoding="utf-8",
    )
    files = {}
    for path in (snapshot_path, summary_path, scorecard_path):
        files[path.name] = {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
    manifest = {
        "schema": "geometry_championship_v1_manifest",
        "generated_utc": generated_utc,
        "files": files,
    }
    (out_dir / "manifest.sha256.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--run-tag")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_tag = args.run_tag or utc_now().strftime("%Y%m%dT%H%M%SZ")
    if not RUN_TAG_RE.fullmatch(run_tag):
        raise SystemExit("run tag must contain only letters, numbers, dot, dash, or underscore")
    out_dir = args.out_root / run_tag
    summary = write_run(args.registry, out_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
