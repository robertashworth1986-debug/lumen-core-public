from __future__ import annotations

import argparse
import ast
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "config" / "geometry_championship_v1_registry.json"
DEFAULT_REPLAY = ROOT / "out" / "ops" / "locked_source_baseline_replay_sweep_latest.json"
DEFAULT_CONFIRMATORY_AUDIT = (
    ROOT / "out" / "ops" / "geometry_confirmatory_promotion_audit_latest.json"
)
DEFAULT_JSON = ROOT / "out" / "ops" / "full_geometry_protocol_field_latest.json"

BENCHMARK_MODULES = {
    "branching_transport": ROOT / "code" / "geometry_branching_transport_benchmark.py",
    "optimal_curve_transport": ROOT / "code" / "geometry_optimal_curve_transport_benchmark.py",
    "thermal_ventilation": ROOT / "code" / "geometry_thermal_ventilation_benchmark.py",
    "time_series_model_routing": ROOT / "code" / "geometry_time_series_model_routing_benchmark.py",
    "wave_resonance_timing": ROOT / "code" / "geometry_wave_resonance_timing_benchmark.py",
}

LATEST_EVIDENCE = {
    "branching_transport": ROOT / "out" / "geometry_branching_transport" / "latest.json",
    "optimal_curve_transport": ROOT / "out" / "geometry_optimal_curve_transport" / "latest.json",
    "thermal_ventilation": ROOT / "out" / "geometry_thermal_ventilation" / "latest.json",
    "wave_resonance_timing": ROOT / "out" / "geometry_wave_resonance_timing" / "latest.json",
}

EVIDENCE_BOUNDARY = (
    "Coverage and execution audit only. Registry inclusion, an implementation, or a generated "
    "benchmark result is not field validation, certification, airworthiness evidence, operational "
    "approval, universal superiority, realized savings, or trading alpha. Cross-lane ranking is "
    "forbidden."
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected object in {path}")
    return data


def literal_string(node: ast.AST) -> str | None:
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return None
    return value if isinstance(value, str) else None


def module_geometry_families(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    families: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or len(node.args) < 3:
            continue
        function_name = ""
        if isinstance(node.func, ast.Name):
            function_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            function_name = node.func.attr
        if function_name != "StrategySpec":
            continue
        kind = literal_string(node.args[1])
        family_id = literal_string(node.args[2])
        if kind == "geometry_family" and family_id:
            families.add(family_id)
    return families


def evidence_geometry_families(path: Path) -> tuple[set[str], dict[str, Any]]:
    if not path.exists():
        return set(), {"path": str(path), "exists": False}
    payload = load_json(path)
    families = {
        str(row.get("family_id"))
        for row in payload.get("strategies", [])
        if isinstance(row, dict)
        and row.get("kind") == "geometry_family"
        and row.get("family_id")
    }
    return families, {
        "path": str(path),
        "exists": True,
        "sha256": sha256_file(path),
        "generated_utc": payload.get("generated_utc"),
        "schema": payload.get("schema"),
        "validation_scenario_count": (payload.get("validation") or {}).get("scenario_count"),
        "promotion_gate": (payload.get("promotion_gate") or {}).get("gate"),
    }


def replay_evidence(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if not path.exists():
        return {}, {"path": str(path), "exists": False}
    payload = load_json(path)
    grouped: dict[str, dict[str, Any]] = {}
    for row in payload.get("route_results", []):
        if not isinstance(row, dict) or not row.get("candidate_family"):
            continue
        family_id = str(row["candidate_family"])
        item = grouped.setdefault(
            family_id,
            {
                "route_count": 0,
                "comparison_count": 0,
                "candidate_win_count": 0,
                "estimated_row_exposure": 0,
                "lanes": set(),
                "systems": set(),
            },
        )
        item["route_count"] += 1
        item["comparison_count"] += int(row.get("comparison_count") or 0)
        item["candidate_win_count"] += int(row.get("candidate_win_count") or 0)
        item["estimated_row_exposure"] += int(row.get("estimated_rows") or 0)
        if row.get("lane"):
            item["lanes"].add(str(row["lane"]))
        if row.get("system"):
            item["systems"].add(str(row["system"]))
    normalized: dict[str, dict[str, Any]] = {}
    for family_id, row in grouped.items():
        normalized[family_id] = {
            **row,
            "lanes": sorted(row["lanes"]),
            "systems": sorted(row["systems"]),
        }
    return normalized, {
        "path": str(path),
        "exists": True,
        "sha256": sha256_file(path),
        "generated_utc": payload.get("generated_utc"),
        "schema": payload.get("schema"),
        "route_result_count": len(payload.get("route_results", [])),
    }


def confirmatory_evidence(
    path: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    if not path.exists():
        return {}, {}, {"path": str(path), "exists": False}
    payload = load_json(path)
    declared_audit_sha256 = str(payload.get("audit_sha256") or "")
    unhashed = {key: value for key, value in payload.items() if key != "audit_sha256"}
    computed_audit_sha256 = sha256_payload(unhashed)
    if not declared_audit_sha256 or declared_audit_sha256 != computed_audit_sha256:
        raise ValueError(f"confirmatory audit self-hash is invalid: {path}")

    by_family: dict[str, dict[str, Any]] = {}
    for comparison in payload.get("family_comparisons", []):
        if not isinstance(comparison, dict) or not comparison.get("family_id"):
            continue
        family_id = str(comparison["family_id"])
        if family_id in by_family:
            raise ValueError(f"duplicate confirmatory family: {family_id}")
        by_family[family_id] = comparison

    by_lane: dict[str, dict[str, Any]] = {}
    for lane in payload.get("lanes", []):
        if not isinstance(lane, dict) or not lane.get("lane"):
            continue
        lane_id = str(lane["lane"])
        by_lane[lane_id] = lane

    return by_family, by_lane, {
        "path": str(path),
        "exists": True,
        "file_sha256": sha256_file(path),
        "schema": payload.get("schema"),
        "generated_utc": payload.get("generated_utc"),
        "declared_audit_sha256": declared_audit_sha256,
        "computed_audit_sha256": computed_audit_sha256,
        "declared_audit_sha256_valid": True,
        "summary": payload.get("summary"),
    }


def disposition_for(
    family: dict[str, Any],
    *,
    implemented: bool,
    frozen_executed: bool,
    replay: dict[str, Any] | None,
) -> str:
    if replay:
        return "EXECUTED_SOURCE_CONDITIONED_REPLAY"
    if frozen_executed:
        return "EXECUTED_FROZEN_GENERATED_BENCHMARK"
    if implemented:
        return "IMPLEMENTED_AWAITING_CURRENT_FROZEN_RUN"
    if family.get("competitor", True) is False or family.get("status") == "diagnostic_specification":
        return "DIAGNOSTIC_IMPLEMENTATION_REQUIRED"
    return "PERFORMANCE_IMPLEMENTATION_REQUIRED"


def build_matrix(
    registry_path: Path = DEFAULT_REGISTRY,
    replay_path: Path = DEFAULT_REPLAY,
    confirmatory_audit_path: Path = DEFAULT_CONFIRMATORY_AUDIT,
    benchmark_modules: dict[str, Path] | None = None,
    latest_evidence: dict[str, Path] | None = None,
) -> dict[str, Any]:
    benchmark_modules = benchmark_modules or BENCHMARK_MODULES
    latest_evidence = latest_evidence or LATEST_EVIDENCE
    registry = load_json(registry_path)
    families = registry.get("families")
    lanes = registry.get("lanes")
    if not isinstance(families, list) or not isinstance(lanes, dict):
        raise ValueError("registry must contain family and lane collections")
    if registry.get("cross_lane_ranking_allowed") is not False:
        raise ValueError("cross-lane ranking must remain disabled")

    implemented_by_lane: dict[str, set[str]] = {}
    module_receipts: list[dict[str, Any]] = []
    for lane, path in sorted(benchmark_modules.items()):
        family_ids = module_geometry_families(path) if path.exists() else set()
        implemented_by_lane[lane] = family_ids
        module_receipts.append(
            {
                "lane": lane,
                "path": str(path),
                "exists": path.exists(),
                "sha256": sha256_file(path) if path.exists() else None,
                "implemented_family_count": len(family_ids),
                "implemented_families": sorted(family_ids),
            }
        )

    executed_by_lane: dict[str, set[str]] = {}
    evidence_receipts: list[dict[str, Any]] = []
    for lane, path in sorted(latest_evidence.items()):
        family_ids, receipt = evidence_geometry_families(path)
        executed_by_lane[lane] = family_ids
        evidence_receipts.append({"lane": lane, **receipt, "executed_families": sorted(family_ids)})

    replay_by_family, replay_receipt = replay_evidence(replay_path)
    confirmatory_by_family, confirmatory_by_lane, confirmatory_receipt = confirmatory_evidence(
        confirmatory_audit_path
    )
    rows: list[dict[str, Any]] = []
    lane_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[str] = set()
    for family in families:
        if not isinstance(family, dict) or not family.get("id") or not family.get("lane"):
            raise ValueError("every registry family must have an id and lane")
        family_id = str(family["id"])
        lane = str(family["lane"])
        if family_id in seen:
            raise ValueError(f"duplicate family id: {family_id}")
        seen.add(family_id)
        implemented = family_id in implemented_by_lane.get(lane, set())
        frozen_executed = family_id in executed_by_lane.get(lane, set())
        replay = replay_by_family.get(family_id)
        confirmatory = confirmatory_by_family.get(family_id)
        confirmatory_lane = confirmatory_by_lane.get(lane)
        if confirmatory and str(confirmatory.get("lane")) != lane:
            raise ValueError(f"confirmatory lane mismatch for {family_id}")
        if confirmatory and not frozen_executed:
            raise ValueError(f"confirmatory result lacks current frozen execution: {family_id}")
        lane_spec = lanes.get(lane) or {}
        internal_lumengrade = (
            str((confirmatory_lane or {}).get("lumengrade") or "LG2")
            if confirmatory
            else "LG1"
            if implemented
            else "LG0"
        )
        row = {
            "family_id": family_id,
            "label": family.get("label"),
            "lane": lane,
            "registry_status": family.get("status"),
            "competitor": family.get("competitor", True),
            "protocol_baselines": str(lane_spec.get("baselines") or "").split(),
            "protocol_metrics": str(lane_spec.get("metrics") or "").split(),
            "benchmark_hypothesis": family.get("benchmark_hypothesis"),
            "promotion_metric": family.get("promotion_metric"),
            "failure_mode": family.get("failure_mode"),
            "implementation_present": implemented,
            "frozen_generated_benchmark_executed": frozen_executed,
            "source_conditioned_replay": replay or None,
            "confirmatory_audit": (
                {
                    "audit_sha256": confirmatory_receipt.get("declared_audit_sha256"),
                    "baseline_id": confirmatory.get("baseline_id"),
                    "development_preselected": bool(confirmatory.get("development_preselected")),
                    "confirmatory_pass": bool(confirmatory.get("confirmatory_pass")),
                    "decision": confirmatory.get("decision"),
                    "failed_checks": list(confirmatory.get("failed_checks") or []),
                    "paired_score_interval": confirmatory.get("paired_score_interval"),
                }
                if confirmatory
                else None
            ),
            "internal_lumengrade": internal_lumengrade,
            "external_validation": False,
            "disposition": disposition_for(
                family,
                implemented=implemented,
                frozen_executed=frozen_executed,
                replay=replay,
            ),
            "field_validated": False,
            "certified_or_operationally_approved": False,
        }
        rows.append(row)
        lane_buckets[lane].append(row)

    rows.sort(key=lambda row: (str(row["lane"]), str(row["family_id"])))
    lane_summary: list[dict[str, Any]] = []
    for lane in sorted(lanes):
        items = lane_buckets.get(lane, [])
        lane_summary.append(
            {
                "lane": lane,
                "registered_family_count": len(items),
                "implementation_present_count": sum(bool(row["implementation_present"]) for row in items),
                "frozen_generated_executed_count": sum(
                    bool(row["frozen_generated_benchmark_executed"]) for row in items
                ),
                "source_conditioned_replay_count": sum(bool(row["source_conditioned_replay"]) for row in items),
                "confirmatory_audited_count": sum(bool(row["confirmatory_audit"]) for row in items),
                "development_preselected_count": sum(
                    bool((row["confirmatory_audit"] or {}).get("development_preselected"))
                    for row in items
                ),
                "internal_confirmatory_pass_count": sum(
                    bool((row["confirmatory_audit"] or {}).get("confirmatory_pass"))
                    for row in items
                ),
                "confirmatory_nonpromotion_count": sum(
                    (row["confirmatory_audit"] or {}).get("decision")
                    == "NOT_PROMOTED_CONFIRMATORY_GATE_FAILED"
                    for row in items
                ),
                "implementation_required_count": sum(
                    row["disposition"].endswith("IMPLEMENTATION_REQUIRED") for row in items
                ),
                "protocol_baselines": str((lanes.get(lane) or {}).get("baselines") or "").split(),
                "protocol_metrics": str((lanes.get(lane) or {}).get("metrics") or "").split(),
            }
        )

    generated = utc_now()
    summary = {
        "registered_family_count": len(rows),
        "registered_lane_count": len(lanes),
        "implementation_present_count": sum(bool(row["implementation_present"]) for row in rows),
        "frozen_generated_executed_count": sum(
            bool(row["frozen_generated_benchmark_executed"]) for row in rows
        ),
        "source_conditioned_replay_count": sum(bool(row["source_conditioned_replay"]) for row in rows),
        "confirmatory_audited_count": sum(bool(row["confirmatory_audit"]) for row in rows),
        "development_preselected_count": sum(
            bool((row["confirmatory_audit"] or {}).get("development_preselected")) for row in rows
        ),
        "internal_confirmatory_pass_count": sum(
            bool((row["confirmatory_audit"] or {}).get("confirmatory_pass")) for row in rows
        ),
        "confirmatory_nonpromotion_count": sum(
            (row["confirmatory_audit"] or {}).get("decision")
            == "NOT_PROMOTED_CONFIRMATORY_GATE_FAILED"
            for row in rows
        ),
        "descriptive_only_confirmatory_count": sum(
            (row["confirmatory_audit"] or {}).get("decision")
            == "DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED"
            for row in rows
        ),
        "implementation_required_count": sum(
            row["disposition"].endswith("IMPLEMENTATION_REQUIRED") for row in rows
        ),
        "all_registered_families_accounted_for": len(rows) == len(families) == len(seen),
        "all_registered_families_performance_executed": all(
            bool(row["frozen_generated_benchmark_executed"] or row["source_conditioned_replay"])
            for row in rows
            if row["competitor"]
        ),
        "cross_lane_ranking_performed": False,
        "field_validation_claim_allowed": False,
        "certification_claim_allowed": False,
    }
    payload: dict[str, Any] = {
        "schema": "full_geometry_protocol_field_v2",
        "generated_utc": generated.isoformat(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "purpose": (
            "Account for every registered geometry, distinguish specification coverage from "
            "execution coverage, and route each family only to its declared lane protocol."
        ),
        "summary": summary,
        "lane_summary": lane_summary,
        "families": rows,
        "inputs": {
            "registry": {
                "path": str(registry_path),
                "sha256": sha256_file(registry_path),
                "schema": registry.get("schema"),
                "version": registry.get("version"),
            },
            "benchmark_modules": module_receipts,
            "latest_evidence": evidence_receipts,
            "source_conditioned_replay": replay_receipt,
            "confirmatory_audit": confirmatory_receipt,
        },
        "claim_gate": {
            "registry_coverage_is_performance_evidence": False,
            "generated_benchmark_is_field_validation": False,
            "source_conditioned_replay_is_field_validation": False,
            "internal_lumengrade_is_external_certification": False,
            "only_development_preselected_family_is_confirmatory_eligible": True,
            "cross_lane_champion_allowed": False,
            "negative_and_missing_results_retained": True,
        },
    }
    payload["board_sha256"] = sha256_payload(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Full Geometry Protocol Field",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Board SHA-256: `{payload['board_sha256']}`",
        "",
        "## Evidence Boundary",
        "",
        payload["evidence_boundary"],
        "",
        "## Execution Truth",
        "",
        f"- Registered families accounted for: `{summary['registered_family_count']}`.",
        f"- Registered lanes accounted for: `{summary['registered_lane_count']}`.",
        f"- Concrete benchmark implementations found: `{summary['implementation_present_count']}`.",
        f"- Families in current frozen generated runs: `{summary['frozen_generated_executed_count']}`.",
        f"- Families with source-conditioned replay: `{summary['source_conditioned_replay_count']}`.",
        f"- Families covered by the confirmatory audit: `{summary['confirmatory_audited_count']}`.",
        f"- Development-preselected candidates: `{summary['development_preselected_count']}`.",
        f"- Internal confirmatory passes: `{summary['internal_confirmatory_pass_count']}`.",
        f"- Confirmatory non-promotions: `{summary['confirmatory_nonpromotion_count']}`.",
        f"- Descriptive-only comparisons: `{summary['descriptive_only_confirmatory_count']}`.",
        f"- Families still requiring implementation: `{summary['implementation_required_count']}`.",
        f"- All families performance-executed: `{str(summary['all_registered_families_performance_executed']).lower()}`.",
        "- No family is silently counted as tested because it merely has a benchmark specification.",
        "",
        "## Lane Coverage",
        "",
        "| Lane | Registered | Implemented | Frozen Run | Audited | Selected | Pass | Non-promoted | Implementation Needed |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["lane_summary"]:
        lines.append(
            f"| `{row['lane']}` | {row['registered_family_count']} | "
            f"{row['implementation_present_count']} | {row['frozen_generated_executed_count']} | "
            f"{row['confirmatory_audited_count']} | {row['development_preselected_count']} | "
            f"{row['internal_confirmatory_pass_count']} | {row['confirmatory_nonpromotion_count']} | "
            f"{row['implementation_required_count']} |"
        )
    lines.extend(
        [
            "",
            "## Family Ledger",
            "",
            "| Lane | Family | Disposition | LumenGrade | Confirmatory Decision | Frozen Run | Source Replay |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in payload["families"]:
        lines.append(
            f"| `{row['lane']}` | `{row['family_id']}` | `{row['disposition']}` | "
            f"`{row['internal_lumengrade']}` | "
            f"`{(row['confirmatory_audit'] or {}).get('decision') or 'NOT_AUDITED'}` | "
            f"{str(row['frozen_generated_benchmark_executed']).lower()} | "
            f"{str(bool(row['source_conditioned_replay'])).lower()} |"
        )
    lines.extend(
        [
            "",
            "## Promotion Rule",
            "",
            "A family can advance only within its own lane after identical frozen inputs, named "
            "baselines, paired uncertainty, multiple-comparison control, runtime measurement, "
            "retention of null results, and independent or representative validation for any "
            "operational claim.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], json_path: Path = DEFAULT_JSON) -> tuple[Path, Path]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    date_tag = str(payload["generated_utc"])[:10]
    markdown_path = ROOT / "docs" / f"FULL_GEOMETRY_PROTOCOL_FIELD_{date_tag}.md"
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    return json_path, markdown_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--confirmatory-audit", type=Path, default=DEFAULT_CONFIRMATORY_AUDIT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_matrix(args.registry, args.replay, args.confirmatory_audit)
    json_path, markdown_path = write_outputs(payload, args.json_out)
    print(
        json.dumps(
            {
                "json": str(json_path),
                "markdown": str(markdown_path),
                "summary": payload["summary"],
                "board_sha256": payload["board_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
