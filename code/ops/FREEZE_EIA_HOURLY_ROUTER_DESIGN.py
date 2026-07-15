"""Freeze and verify the historical EIA hourly-router design receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = ROOT / "config" / "eia_grid_prospective_hourly_router_protocol_v1.json"
SOURCE_RESULT_PATH = ROOT / "out" / "eia_grid_prospective_hourly_router" / "design_benchmark.json"
FROZEN_RESULT_PATH = (
    ROOT
    / "evidence"
    / "external_validation"
    / "eia_grid_hourly_router_design_benchmark_20260714.json"
)
RECEIPT_PATH = (
    ROOT
    / "evidence"
    / "external_validation"
    / "eia_grid_hourly_router_design_freeze_20260714.json"
)
DOC_PATH = ROOT / "docs" / "EIA_GRID_PROSPECTIVE_HOURLY_ROUTER_2026-07-14.md"


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build_receipt() -> tuple[dict[str, Any], bytes]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    expected_result_hash = protocol["historical_design"]["result_sha256"]
    if FROZEN_RESULT_PATH.exists():
        result_path = FROZEN_RESULT_PATH
    elif SOURCE_RESULT_PATH.exists():
        result_path = SOURCE_RESULT_PATH
    else:
        raise FileNotFoundError("historical design benchmark is unavailable")
    result_bytes = result_path.read_bytes().replace(b"\r\n", b"\n")
    observed_result_hash = hashlib.sha256(result_bytes).hexdigest()
    if observed_result_hash != expected_result_hash:
        raise ValueError("historical design benchmark hash differs from the protocol")
    result = json.loads(result_bytes.decode("utf-8"))
    if result.get("selected_route_map") != protocol["router"]["route_map"]:
        raise ValueError("protocol route map differs from the frozen historical winners")
    expected_authorities = sorted(protocol["balancing_authorities"])
    observed_authorities = sorted(
        row["respondent"] for row in result.get("authority_metrics", [])
    )
    if observed_authorities != expected_authorities:
        raise ValueError("historical result does not cover every protocol authority")
    if int(result.get("training_row_count", 0)) <= 0 or int(
        result.get("validation_row_count", 0)
    ) <= 0:
        raise ValueError("historical result has an empty design split")

    receipt = {
        "schema": "eia_grid_hourly_router_design_freeze.v1",
        "protocol_id": protocol["protocol_id"],
        "protocol_path": PROTOCOL_PATH.relative_to(ROOT).as_posix(),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "design_result_path": FROZEN_RESULT_PATH.relative_to(ROOT).as_posix(),
        "design_result_sha256": observed_result_hash,
        "source_panel_row_count": result["source_panel_row_count"],
        "source_panel_row_chain_sha256": result["source_panel_row_chain_sha256"],
        "training_row_count": result["training_row_count"],
        "validation_row_count": result["validation_row_count"],
        "selected_route_map": result["selected_route_map"],
        "route_map_matches_protocol": True,
        "first_allowed_period_end_utc": protocol["prospective_window"][
            "first_allowed_period_end_utc"
        ],
        "backfills_allowed": False,
        "dynamic_override_allowed": False,
        "predecessor_disposition": protocol["predecessor"]["disposition"],
        "predecessor_source_timing_receipt": protocol["predecessor"][
            "source_timing_receipt"
        ],
        "claim_boundary": protocol["claim_boundary"],
    }
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    return receipt, result_bytes


def render_markdown(receipt: dict[str, Any]) -> str:
    lines = [
        "# EIA Grid Prospective Hourly Router",
        "",
        "## Frozen Design",
        "",
        f"- Protocol: `{receipt['protocol_path']}`",
        f"- Protocol SHA256: `{receipt['protocol_sha256']}`",
        f"- Historical design receipt: `{receipt['design_result_path']}`",
        f"- Historical design SHA256: `{receipt['design_result_sha256']}`",
        f"- Source rows: `{receipt['source_panel_row_count']}`",
        f"- Training rows: `{receipt['training_row_count']}`",
        f"- Validation rows: `{receipt['validation_row_count']}`",
        f"- First allowed UTC hour ending: `{receipt['first_allowed_period_end_utc']}`",
        "- Backfills: `false`",
        "- Dynamic route overrides: `false`",
        "",
        "## Frozen Authority Routes",
        "",
        "| Authority | Candidate |",
        "|---|---|",
    ]
    lines.extend(
        f"| {authority} | {candidate} |"
        for authority, candidate in sorted(receipt["selected_route_map"].items())
    )
    lines.extend(
        [
            "",
            "## Scientific Boundary",
            "",
            "The historical window selected the routes and is exploratory. Only targets sealed after the protocol freeze, before each interval starts, and before target actual demand appears can contribute prospective evidence.",
            "",
            receipt["claim_boundary"],
            "",
            "## Operations",
            "",
            "- Core: `code/eia_grid_prospective_hourly_router.py`",
            "- One-cycle wrapper: `tools/Run-EiaProspectiveHourlyRouterCycle.ps1`",
            "- Scheduler registration: `tools/Register-EiaProspectiveHourlyRouterTask.ps1`",
            "- Prediction ledger: `out/eia_grid_prospective_hourly_router/sealed_predictions.jsonl`",
            "- Settlement ledger: `out/eia_grid_prospective_hourly_router/settlements.jsonl`",
            "- Operational receipt chain: `out/eia_grid_prospective_hourly_router/operational_runs.jsonl`",
            "- Status: `out/eia_grid_prospective_hourly_router/prospective_status_latest.json`",
            "",
            "The runtime source cache and ledgers are operational artifacts, not repository fixtures. Each chain fails closed on a broken prior hash or record hash, and no credential is serialized.",
            "",
            "## Publisher Sources",
            "",
            "- [EIA Form EIA-930 hourly API dashboard](https://www.eia.gov/opendata/browser/electricity/rto/region-data)",
            "- [EIA Open Data API documentation](https://www.eia.gov/opendata/documentation.php)",
            "",
            "## Verification",
            "",
            "```powershell",
            "python code/ops/FREEZE_EIA_HOURLY_ROUTER_DESIGN.py --check",
            "python -m pytest -q tests/test_eia_grid_prospective_hourly_router.py tests/test_eia_prospective_source_timing_audit.py",
            "powershell -NoProfile -ExecutionPolicy Bypass -File tools/Run-EiaProspectiveHourlyRouterCycle.ps1 -DryRun",
            "```",
            "",
            f"Machine-readable freeze receipt: `{RECEIPT_PATH.relative_to(ROOT).as_posix()}`",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    receipt, result_bytes = build_receipt()
    if args.check:
        if not FROZEN_RESULT_PATH.exists() or file_sha256(FROZEN_RESULT_PATH) != receipt[
            "design_result_sha256"
        ]:
            raise ValueError("frozen design artifact is missing or changed")
        stored = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        if stored != receipt:
            raise ValueError("stored design-freeze receipt is stale")
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0
    FROZEN_RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    FROZEN_RESULT_PATH.write_bytes(result_bytes)
    RECEIPT_PATH.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    DOC_PATH.write_text(render_markdown(receipt), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "design_result_sha256": receipt["design_result_sha256"],
                "protocol_sha256": receipt["protocol_sha256"],
                "receipt_sha256": receipt["receipt_sha256"],
                "route_map_matches_protocol": receipt["route_map_matches_protocol"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
