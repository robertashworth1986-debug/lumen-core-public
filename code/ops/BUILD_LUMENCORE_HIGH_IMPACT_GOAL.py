from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

READINESS_JSON = OUT_OPS / "grant_submission_readiness_audit_latest.json"
DASHBOARD_FEED_JSON = OUT_OPS / "grant_dashboard_status_feed_latest.json"
PUBLIC_DASHBOARD_FEED_JSON = DASHBOARD_DATA / "grant_readiness_status.json"
HARBOR_AIS_ACQUISITION_JSON = OUT_OPS / "harbor_ais_pilot_acquisition_latest.json"
HARBOR_AIS_SPLITS_JSON = OUT_OPS / "harbor_ais_heldout_splits_latest.json"
HARBOR_PUBLIC_AIS_GATE_JSON = OUT_OPS / "harbor_public_ais_gate_latest.json"
HARBOR_AIS_IO_PREFLIGHT_JSON = OUT_OPS / "harbor_ais_io_preflight_latest.json"
HARBOR_AIS_INJECTION_JSON = OUT_OPS / "harbor_ais_injection_benchmark_latest.json"

OUT_JSON = OUT_OPS / "lumencore_high_impact_goal_latest.json"
OUT_MD = DOCS / "LUMENCORE_HIGH_IMPACT_GOAL_2026-06-20.md"
DASHBOARD_JSON = DASHBOARD_DATA / "lumencore_high_impact_goal.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def has_best_single_axis_baseline(payload: dict[str, Any]) -> bool:
    result = payload.get("controlled_injection_benchmark", {})
    if not isinstance(result, dict) or not result:
        result = payload
    suite = result.get("baseline_suite", {})
    if not isinstance(suite, dict):
        return False
    best = suite.get("best_single_axis_baseline", {})
    return isinstance(best, dict) and bool(best.get("name"))


def score_lumenstock(
    readiness: dict[str, Any],
    dashboard: dict[str, Any],
    acquisition: dict[str, Any],
    splits: dict[str, Any],
    public_gate: dict[str, Any],
    io_preflight: dict[str, Any],
    injection_benchmark: dict[str, Any],
) -> dict[str, Any]:
    summary = readiness.get("summary", {}) if isinstance(readiness.get("summary"), dict) else {}
    local_blockers = int(summary.get("local_blockers", 0) or 0)
    portal_blockers = int(summary.get("portal_user_blockers", 0) or 0)
    packages = int(summary.get("packages", 0) or 0)
    geometry_matched = int(summary.get("geometry_registry_matched", 0) or 0)
    geometry_expected = int(summary.get("geometry_registry_expected", 0) or 0)
    acquisition_ready = acquisition.get("posture") == "PUBLIC_AIS_RAW_ACQUIRED_HASHED_PROFILED"
    splits_ready = splits.get("posture") == "PUBLIC_AIS_HELDOUT_SPLITS_FROZEN"
    gate_ready = public_gate.get("posture") == "PUBLIC_AIS_SINGLE_LANE_GATE_READY"
    io_posture = str(io_preflight.get("posture", "NOT_RUN"))
    io_ready = io_posture == "PUBLIC_AIS_SPLIT_IO_READY"
    io_blocked = io_posture == "PUBLIC_AIS_SPLIT_IO_BLOCKED"
    injection_ready = str(injection_benchmark.get("posture", "")) == "PUBLIC_AIS_INJECTION_BENCHMARK_READY"
    artifact_count = int(dashboard.get("builder_velocity", {}).get("artifact_count", 0) or 0)

    components = {
        "proof_integrity": 100 if local_blockers == 0 else 45,
        "data_representativeness": min(95, 55 + (15 if acquisition_ready else 0) + (10 if splits_ready else 0) + (15 if gate_ready else 0)),
        "data_operability": 90 if io_ready else (45 if io_blocked else 60),
        "benchmark_governance": min(
            95,
            70
            + (10 if geometry_expected and geometry_matched == geometry_expected else 0)
            + (15 if injection_ready else 0),
        ),
        "compliance_readiness": max(20, 80 - portal_blockers * 2),
        "grant_factory_maturity": min(85, 35 + packages * 8 + artifact_count * 4),
        "market_traction": 20,
        "revenue_evidence": 10,
    }
    composite = round(sum(components.values()) / len(components), 2)
    return {
        "name": "LumenStock Proof-Weighted Opportunity Index",
        "ticker_style_symbol": "LUMEN-PWI",
        "composite": composite,
        "components": components,
        "interpretation": (
            "Internal proof/value readiness index. It is not equity, not a token, "
            "not a securities offering, not investment advice, and not a valuation."
        ),
    }


def build_payload() -> dict[str, Any]:
    readiness = read_json(READINESS_JSON)
    dashboard = read_json(DASHBOARD_FEED_JSON)
    if not dashboard:
        dashboard = read_json(PUBLIC_DASHBOARD_FEED_JSON)
    if not readiness and dashboard:
        readiness = {
            "posture": dashboard.get("posture", "UNKNOWN"),
            "summary": dashboard.get("summary", {}),
        }
    acquisition = read_json(HARBOR_AIS_ACQUISITION_JSON)
    splits = read_json(HARBOR_AIS_SPLITS_JSON)
    public_gate = read_json(HARBOR_PUBLIC_AIS_GATE_JSON)
    io_preflight = read_json(HARBOR_AIS_IO_PREFLIGHT_JSON)
    injection_benchmark = read_json(HARBOR_AIS_INJECTION_JSON)
    harbor = dashboard.get("harbor", {}) if isinstance(dashboard.get("harbor"), dict) else {}
    if not acquisition:
        acquisition = harbor.get("ais_acquisition", {}) if isinstance(harbor.get("ais_acquisition"), dict) else {}
    if not splits:
        splits = harbor.get("ais_heldout_splits", {}) if isinstance(harbor.get("ais_heldout_splits"), dict) else {}
    if not public_gate:
        gate = harbor.get("public_ais_gate", {}) if isinstance(harbor.get("public_ais_gate"), dict) else {}
        if gate:
            public_gate = {
                "posture": gate.get("posture", "NOT_RUN"),
                "selected_region": gate.get("region", {}),
                "validation": {"row_metrics": {"rows": gate.get("validation_rows", 0)}},
            }
    if not io_preflight:
        io_preflight = harbor.get("ais_io_preflight", {}) if isinstance(harbor.get("ais_io_preflight"), dict) else {}
    if not injection_benchmark:
        injection_benchmark = (
            harbor.get("ais_injection_benchmark", {})
            if isinstance(harbor.get("ais_injection_benchmark"), dict)
            else {}
        )
    elif isinstance(harbor.get("ais_injection_benchmark"), dict) and not has_best_single_axis_baseline(injection_benchmark):
        injection_benchmark = harbor["ais_injection_benchmark"]
    lumenstock = score_lumenstock(readiness, dashboard, acquisition, splits, public_gate, io_preflight, injection_benchmark)
    summary = readiness.get("summary", {}) if isinstance(readiness.get("summary"), dict) else {}
    io_posture = str(io_preflight.get("posture", "NOT_RUN"))
    injection_result = injection_benchmark.get("controlled_injection_benchmark", {})
    if not isinstance(injection_result, dict) or not injection_result:
        injection_result = injection_benchmark
    best_baseline = (
        injection_result.get("baseline_suite", {})
        .get("best_single_axis_baseline", {})
        if isinstance(injection_result.get("baseline_suite", {}), dict)
        else {}
    )

    return {
        "generated_utc": now_utc(),
        "schema": "lumencore_high_impact_goal_v1",
        "north_star_goal": (
            "Make LumenCore the trusted proof-driven adaptive orchestration stack for complex systems: "
            "every claim is backed by reproducible data, every dashboard separates evidence from ambition, "
            "and every grant, contract, customer, or investor conversation can audit the work without needing a pitch."
        ),
        "operating_doctrine": [
            "Proof before claim.",
            "Representative data before field-performance language.",
            "Fail-closed execution before live capital or customer reliance.",
            "Public-safe evidence for traction; private packets for submissions.",
            "Dashboards show truth state, blockers, and next action instead of pretending gates are solved.",
            "No geometry, algorithm, or route family is sacred until it wins under frozen evaluation.",
        ],
        "current_truth": {
            "grant_posture": readiness.get("posture", "UNKNOWN"),
            "packages_checked": summary.get("packages", 0),
            "local_blockers": summary.get("local_blockers", 0),
            "portal_user_blockers": summary.get("portal_user_blockers", 0),
            "harbor_ais_posture": public_gate.get("posture") or splits.get("posture") or acquisition.get("posture", "NOT_ACQUIRED"),
            "harbor_ais_io_preflight_posture": io_posture,
            "harbor_ais_io_preflight_required_ok": io_preflight.get("summary", {}).get("required_ok") if isinstance(io_preflight.get("summary"), dict) else io_preflight.get("required_ok"),
            "harbor_ais_io_preflight_required_files": io_preflight.get("summary", {}).get("required_files") if isinstance(io_preflight.get("summary"), dict) else io_preflight.get("required_files"),
            "harbor_ais_io_preflight_full_hash_match_count": io_preflight.get("summary", {}).get("full_hash_match_count") if isinstance(io_preflight.get("summary"), dict) else io_preflight.get("full_hash_match_count"),
            "harbor_ais_injection_benchmark_posture": injection_benchmark.get("posture", "NOT_RUN"),
            "harbor_ais_injection_motion_recall": injection_result.get("motion_consistency_recall", 0.0),
            "harbor_ais_injection_baseline_recall": injection_result.get("speed_only_baseline_recall", 0.0),
            "harbor_ais_injection_recall_lift": injection_result.get("recall_lift_vs_speed_only", 0.0),
            "harbor_ais_injection_best_single_axis_baseline": best_baseline.get("name", ""),
            "harbor_ais_injection_best_single_axis_recall": best_baseline.get("recall", 0.0),
            "harbor_public_ais_region": public_gate.get("selected_region", {}).get("label", ""),
            "harbor_public_ais_validation_rows": public_gate.get("validation", {}).get("row_metrics", {}).get("rows", 0),
            "builder_velocity": dashboard.get("builder_velocity", {}),
        },
        "highest_leverage_milestones": [
            {
                "lane": "HarborSentinel representative data",
                "target": "Use the frozen NOAA AIS New Orleans / Mississippi River Delta dev/validation split, single-lane gate, and current controlled-injection benchmark as the public representative-data bridge while preserving the boundary that controlled injections are not field validation.",
                "traction_reason": "This moves HarborSentinel beyond synthetic-only source readiness and gives reviewers a reproducible detector-vs-baseline result without claiming Navy operational performance.",
            },
            {
                "lane": "DICE submission quality",
                "target": "Keep DICE locally locked, clear BAAT/SAM/user gates, and preserve the 7-page render/URL/cost-boundary lock packet.",
                "traction_reason": "DARPA reviewers respect crisp boundaries, reproducible evidence, and no portal mistakes.",
            },
            {
                "lane": "Geometry Championship V2",
                "target": "Run nature/field/bio-network/LumenCore hybrids against frozen baselines on at least one representative dataset.",
                "traction_reason": "Winning families become defensible research claims; losing families become credible negative evidence.",
            },
            {
                "lane": "Public trust surface",
                "target": "Publish only sanitized dashboard feeds that show proof state, blockers, hashes, and next actions.",
                "traction_reason": "Serious reviewers can audit the machine without seeing private applications or secrets.",
            },
            {
                "lane": "Revenue path",
                "target": "Convert proof packets into grant submissions, SBIR/BAA conversations, contract bids, paid pilots, and compliance-safe demos.",
                "traction_reason": "Traction comes from buyers and agencies trusting the evidence chain, not from unsupported valuation language.",
            },
        ],
        "lumenstock": lumenstock,
        "next_72_hours": [
            "Package the NOAA AIS held-out split, public AIS gate, local split-cache recovery, and controlled-injection benchmark into the HarborSentinel reviewer proof packet.",
            "Update HarborSentinel proposal language to cite the controlled-injection result only as a bounded public AIS benchmark, not as real-world threat, multi-source fusion, or field validation.",
            "Hydrate grants dashboard with readiness, DICE lock, Harbor AIS, and builder velocity feeds.",
            "Prepare public-safe proof cards for DICE/Harbor without private proposal text.",
            "Use the LumenStock Proof-Weighted Opportunity Index as an internal prioritization meter only.",
        ],
        "hard_boundaries": [
            "Do not represent LumenStock as stock, equity, a token, a public offering, or an investment product.",
            "Do not claim guaranteed funding, guaranteed profit, field validation, CMMC certification, or institutional trading readiness.",
            "Do not describe HarborSentinel controlled-injection detector evidence as real adversary detection, multi-source fusion, Navy/SSDS integration, or field validation.",
            "Do not submit, certify, consent, upload, or move money without fresh action-time approval.",
            "Do not commit raw AIS bulk data, secrets, credentials, private portal screenshots, or private application packets to public repos.",
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# LumenCore High-Impact Goal",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        "## North Star",
        "",
        payload["north_star_goal"],
        "",
        "## Operating Doctrine",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["operating_doctrine"])
    lines.extend(["", "## Current Truth", ""])
    truth = payload["current_truth"]
    lines.extend(
        [
            f"- Grant posture: `{truth['grant_posture']}`",
            f"- Packages checked: {truth['packages_checked']}",
            f"- Local blockers: {truth['local_blockers']}",
            f"- Portal/user blockers: {truth['portal_user_blockers']}",
            f"- Harbor AIS posture: `{truth['harbor_ais_posture']}`",
            f"- Harbor AIS I/O preflight: `{truth.get('harbor_ais_io_preflight_posture', 'NOT_RUN')}` "
            f"({truth.get('harbor_ais_io_preflight_required_ok', 0)}/{truth.get('harbor_ais_io_preflight_required_files', 0)} required files OK; "
            f"{truth.get('harbor_ais_io_preflight_full_hash_match_count', 0)}/{truth.get('harbor_ais_io_preflight_required_files', 0)} full-file SHA-256 matches)",
            f"- Harbor AIS injection benchmark: `{truth.get('harbor_ais_injection_benchmark_posture', 'NOT_RUN')}`, "
            f"motion recall {truth.get('harbor_ais_injection_motion_recall', 0)}, "
            f"speed-only baseline {truth.get('harbor_ais_injection_baseline_recall', 0)}, "
            f"best single-axis baseline `{truth.get('harbor_ais_injection_best_single_axis_baseline') or 'n/a'}` "
            f"recall {truth.get('harbor_ais_injection_best_single_axis_recall', 0)}, "
            f"lift {truth.get('harbor_ais_injection_recall_lift', 0)}",
            f"- Harbor public AIS region: {truth.get('harbor_public_ais_region') or 'n/a'}",
            f"- Harbor public AIS validation rows: {truth.get('harbor_public_ais_validation_rows') or 0}",
        ]
    )
    velocity = truth.get("builder_velocity", {})
    if velocity:
        lines.append(
            f"- Builder artifact velocity: {velocity.get('artifact_count', 0)} timestamped artifacts, "
            f"{velocity.get('per_hour', 0)} artifacts/hour over the measured artifact window"
        )
    lines.extend(["", "## Highest-Leverage Milestones", ""])
    for row in payload["highest_leverage_milestones"]:
        lines.extend(
            [
                f"### {row['lane']}",
                "",
                f"Target: {row['target']}",
                "",
                f"Why it matters: {row['traction_reason']}",
                "",
            ]
        )
    lumenstock = payload["lumenstock"]
    lines.extend(
        [
            "## LumenStock",
            "",
            f"Working name: {lumenstock['name']} (`{lumenstock['ticker_style_symbol']}`)",
            "",
            f"Composite readiness score: {lumenstock['composite']}/100",
            "",
            lumenstock["interpretation"],
            "",
            "Components:",
            "",
        ]
    )
    lines.extend(f"- {key}: {value}/100" for key, value in lumenstock["components"].items())
    lines.extend(["", "## Next 72 Hours", ""])
    lines.extend(f"- {item}" for item in payload["next_72_hours"])
    lines.extend(["", "## Hard Boundaries", ""])
    lines.extend(f"- {item}" for item in payload["hard_boundaries"])
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "north_star": payload["north_star_goal"],
                "lumenstock_score": payload["lumenstock"]["composite"],
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
