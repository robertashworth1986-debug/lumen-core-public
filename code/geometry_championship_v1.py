"""Validate and freeze Geometry Championship V1 readiness.

This is a registry, readiness-ranking, and evidence-gate runner.
Lane-specific benchmarks must exist before any family can be promoted into a
performance champion. Candidate champions here are benchmark priorities, not
claims of real-world performance.
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

MINIMUM_FAMILY_COUNT = 50
MINIMUM_NATURE_OR_FLOW_LOGIC_FAMILY_COUNT = 50

REQUIRED_FAMILY_IDS = {
    "mycelium_network",
    "slime_mold_routing",
    "magnetic_field_geometry",
    "toroidal_fields",
    "halbach_arrays",
    "flower_of_life_hexagonal_packing",
    "non_euclidean_geodesics",
    "frobenius_stability",
    "bee_foraging_paths",
    "bird_v_formation_flocking",
    "wolf_pack_pursuit_paths",
    "ant_trails",
    "river_deltas",
    "leaf_veins",
    "vascular_lung_branching",
    "termite_mound_ventilation",
    "hibernation_bounded_wake_logic",
    "hybrid_flowforms",
}
PERFORMANCE_READY_STATUSES = {"implemented", "validated"}
LEGACY_STATUSES = {"legacy_analogue_only", "legacy_transform_only"}
STATUS_READINESS_SCORE = {
    "validated": 100,
    "implemented": 85,
    "benchmark_design_ready": 58,
    "legacy_transform_only": 46,
    "legacy_analogue_only": 42,
    "diagnostic_specification": 32,
    "specification_only": 24,
    "concept_only": 16,
}


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


def has_native_nature_or_flow_logic(family: dict[str, Any]) -> bool:
    """Count native geometry logic without letting legacy beast imports inflate it."""
    family_id = str(family.get("id", ""))
    return bool(family.get("natural_logic")) and not family_id.startswith("beast_")


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
    if missing:
        errors.append("missing required families: " + ", ".join(missing))
    minimum_count = int(registry.get("minimum_family_count", MINIMUM_FAMILY_COUNT))
    if len(ids) < minimum_count:
        errors.append(f"registry must contain at least {minimum_count} families")
    nature_or_flow_count = sum(
        1
        for family in families
        if isinstance(family, dict) and has_native_nature_or_flow_logic(family)
    )
    if nature_or_flow_count < MINIMUM_NATURE_OR_FLOW_LOGIC_FAMILY_COUNT:
        errors.append(
            "registry must contain at least "
            f"{MINIMUM_NATURE_OR_FLOW_LOGIC_FAMILY_COUNT} native nature/flow logic families"
        )

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


def family_readiness_score(family: dict[str, Any]) -> int:
    score = STATUS_READINESS_SCORE.get(str(family.get("status", "")), 0)
    for field, bonus in (
        ("natural_logic", 4),
        ("benchmark_hypothesis", 6),
        ("first_test", 6),
        ("promotion_metric", 6),
        ("failure_mode", 4),
        ("located_source", 3),
        ("located_result", 3),
    ):
        if family.get(field):
            score += bonus
    if family.get("competitor", True) is False:
        score -= 20
    return max(0, min(score, 100))


def candidate_rankings(registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in registry["families"]:
        if family.get("competitor", True) is False:
            continue
        rows.append(
            {
                "id": family["id"],
                "label": family["label"],
                "lane": family["lane"],
                "status": family["status"],
                "readiness_score": family_readiness_score(family),
                "benchmark_hypothesis": family.get("benchmark_hypothesis", ""),
                "first_test": family.get("first_test", ""),
            }
        )
    rows.sort(key=lambda row: (-row["readiness_score"], row["lane"], row["id"]))
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def lane_candidate_champions(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    champions: dict[str, dict[str, Any]] = {}
    for row in rows:
        champions.setdefault(str(row["lane"]), row)
    return champions


def build_readiness(registry: dict[str, Any]) -> dict[str, Any]:
    families = registry["families"]
    nature_or_flow_logic = [
        family["id"]
        for family in families
        if has_native_nature_or_flow_logic(family)
    ]
    benchmark_specified = [
        family["id"]
        for family in families
        if all(
            family.get(field)
            for field in (
                "natural_logic",
                "benchmark_hypothesis",
                "first_test",
                "promotion_metric",
                "failure_mode",
            )
        )
        and family.get("competitor", True)
    ]
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
    rankings = candidate_rankings(registry)
    lane_champions = lane_candidate_champions(rankings)
    return {
        "family_count": len(families),
        "lane_count": len(registry["lanes"]),
        "lane_family_counts": lane_counts,
        "nature_or_flow_logic_family_count": len(nature_or_flow_logic),
        "native_nature_or_flow_logic_families": nature_or_flow_logic,
        "benchmark_specified_family_count": len(benchmark_specified),
        "benchmark_specified_families": benchmark_specified,
        "performance_ready_families": runnable,
        "legacy_only_families": legacy,
        "pending_families": pending,
        "candidate_rankings": rankings,
        "lane_candidate_champions": lane_champions,
        "champion_of_champions_candidate": rankings[0] if rankings else None,
        "championship_ready": bool(runnable) and not pending,
        "performance_results_generated": False,
        "performance_champion": None,
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
        "geometry performance champion. Candidate champions below are benchmark",
        "priorities only.",
        "",
        "## Readiness",
        "",
        f"- Families registered: {readiness['family_count']}",
        f"- Lanes registered: {readiness['lane_count']}",
        (
            "- Native nature/flow logic families: "
            f"{readiness['nature_or_flow_logic_family_count']}"
        ),
        (
            "- Benchmark-specified families: "
            f"{readiness['benchmark_specified_family_count']}"
        ),
        (
            "- Performance-ready families: "
            f"{len(readiness['performance_ready_families'])}"
        ),
        f"- Legacy analogues only: {len(readiness['legacy_only_families'])}",
        f"- Pending families: {len(readiness['pending_families'])}",
        f"- Verdict: `{readiness['verdict']}`",
        "",
        "## Candidate Champions To Benchmark Next",
        "",
        "| Lane | Candidate | Status | Readiness Score |",
        "|---|---|---|---|",
    ]
    for lane, row in sorted(readiness["lane_candidate_champions"].items()):
        lines.append(
            f"| {lane} | {row['label']} | {row['status']} | "
            f"{row['readiness_score']} |"
        )
    champion = readiness["champion_of_champions_candidate"]
    if champion:
        lines.extend(
            [
                "",
                "Candidate champion-of-champions to benchmark first: "
                f"`{champion['label']}` in `{champion['lane']}` "
                f"(readiness score {champion['readiness_score']}).",
                "",
            ]
        )
    lines.extend(
        [
        "## Family Status",
        "",
        "| Family | Lane | Status | Competitor | Readiness Score |",
        "|---|---|---|---|---|",
        ]
    )
    for family in registry["families"]:
        lines.append(
            f"| {family['label']} | {family['lane']} | {family['status']} | "
            f"{str(family.get('competitor', True)).lower()} | "
            f"{family_readiness_score(family)} |"
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
