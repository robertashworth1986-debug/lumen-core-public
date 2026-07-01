from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GEOMETRY_REGISTRY = ROOT / "config" / "geometry_championship_v1_registry.json"
DEFAULT_BEAST_REGISTRY = ROOT / "full_beast_registry.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def title(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def algo_lane(name: str) -> str:
    lowered = name.lower()
    if any(token in lowered for token in ("consensus", "router", "vote")):
        return "mission_network_routing"
    if any(token in lowered for token in ("phase", "frequency", "harmonic", "resonance", "nodal")):
        return "wave_resonance_timing"
    if any(token in lowered for token in ("curvature", "vortex")):
        return "optimal_curve_transport"
    if "cross_asset" in lowered:
        return "market_signal_geometry"
    return "time_series_model_routing"


def candidate_for(kind: str, name: str) -> dict[str, Any]:
    safe_name = slug(name)
    family_id = f"beast_{kind}_{safe_name}"
    if kind == "flowform":
        lane = "time_series_model_routing"
        status = "legacy_transform_only"
        first_test = "full_beast_flowform_walk_forward_v1"
        promotion_metric = "walk_forward_error_or_return_delta_after_costs"
        natural_logic = f"legacy full-beast signal transform: {name}"
    elif kind == "algo":
        lane = algo_lane(name)
        status = "benchmark_design_ready"
        first_test = "full_beast_algorithm_lane_replay_v1"
        promotion_metric = "baseline_delta_with_false_discovery_control"
        natural_logic = f"legacy full-beast algorithm candidate: {name}"
    elif kind == "strategy":
        lane = "market_signal_geometry"
        status = "benchmark_design_ready"
        first_test = "full_beast_strategy_walk_forward_v1"
        promotion_metric = "net_return_over_drawdown_after_fees"
        natural_logic = f"legacy full-beast strategy candidate: {name}"
    elif kind == "metric":
        lane = "stability_diagnostic"
        status = "diagnostic_specification"
        first_test = "full_beast_metric_profile_selection_stability_v1"
        promotion_metric = "selection_stability_and_false_discovery_control"
        natural_logic = f"legacy full-beast metric profile: {name}"
    else:
        raise ValueError(f"unknown kind {kind!r}")

    return {
        "id": family_id,
        "label": f"Beast {title(kind)}: {title(name)}",
        "lane": lane,
        "status": status,
        "natural_logic": natural_logic,
        "benchmark_hypothesis": (
            f"Test whether {name} improves its assigned lane versus frozen baselines "
            "under live/public replay. Registry inclusion is not evidence of alpha."
        ),
        "first_test": first_test,
        "promotion_metric": promotion_metric,
        "failure_mode": (
            "May overfit legacy backtests, leak regime information, or fail after fees, "
            "latency, slippage, and multiple-comparison control."
        ),
        "source_registry": "full_beast_registry.json",
        "source_kind": kind,
        "source_name": name,
        "provenance": "legacy_beast_registry",
        "claim_boundary": "candidate_only_until_frozen_live_replay_beats_lane_baseline",
    }


def beast_candidates(beast: dict[str, Any]) -> list[dict[str, Any]]:
    groups = [
        ("flowform", "flowforms"),
        ("algo", "algos"),
        ("strategy", "strategies"),
        ("metric", "metric_profiles"),
    ]
    rows: list[dict[str, Any]] = []
    for kind, key in groups:
        values = beast.get(key, [])
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str) and value.strip():
                rows.append(candidate_for(kind, value.strip()))
    return rows


def merge(geometry: dict[str, Any], beast: dict[str, Any]) -> dict[str, Any]:
    families = geometry.get("families")
    if not isinstance(families, list):
        raise ValueError("geometry registry must contain a families array")
    lanes = geometry.get("lanes")
    if not isinstance(lanes, dict):
        raise ValueError("geometry registry must contain a lanes object")

    existing = {str(row.get("id")) for row in families if isinstance(row, dict)}
    candidates = beast_candidates(beast)
    added = []
    skipped = []
    for candidate in candidates:
        if candidate["id"] in existing:
            skipped.append(candidate["id"])
            continue
        if candidate["lane"] not in lanes:
            raise ValueError(f"{candidate['id']} references missing lane {candidate['lane']}")
        families.append(candidate)
        existing.add(candidate["id"])
        added.append(candidate["id"])

    previous_version = int(geometry.get("version", 0) or 0)
    geometry["version"] = max(previous_version + 1, 3)
    geometry["minimum_family_count"] = len(families)
    geometry["legacy_beast_registry_merge"] = {
        "merged_utc": utc_now(),
        "source": str(DEFAULT_BEAST_REGISTRY.relative_to(ROOT)),
        "source_counts": {
            "flowforms": len(beast.get("flowforms", []) or []),
            "algos": len(beast.get("algos", []) or []),
            "strategies": len(beast.get("strategies", []) or []),
            "metric_profiles": len(beast.get("metric_profiles", []) or []),
        },
        "candidates_seen": len(candidates),
        "candidates_added": len(added),
        "candidates_skipped_existing": len(skipped),
        "added_ids": added,
    }
    return geometry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geometry-registry", type=Path, default=DEFAULT_GEOMETRY_REGISTRY)
    parser.add_argument("--beast-registry", type=Path, default=DEFAULT_BEAST_REGISTRY)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    geometry = read_json(args.geometry_registry)
    beast = read_json(args.beast_registry)
    before = len(geometry.get("families", []) or [])
    merged = merge(geometry, beast)
    after = len(merged.get("families", []) or [])
    if not args.dry_run:
        write_json(args.geometry_registry, merged)
    print(
        json.dumps(
            {
                "schema": "full_beast_geometry_registry_merge_v1",
                "geometry_registry": str(args.geometry_registry),
                "beast_registry": str(args.beast_registry),
                "dry_run": args.dry_run,
                "families_before": before,
                "families_after": after,
                "added": after - before,
                "merge": merged.get("legacy_beast_registry_merge", {}),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
