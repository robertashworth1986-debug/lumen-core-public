from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_PATH = ROOT / "out" / "ops" / "external_validation_500_sprint_latest.json"
TEST_RECEIPT_PATH = (
    ROOT / "out" / "ops" / "external_validation_500_sprint_pytest.xml"
)
OUTPUT_DIR = ROOT / "out" / "reports" / "external_validation_500_sprint"
REPORT_DATA_PATH = OUTPUT_DIR / "report_data.json"
GATE_DATA_PATH = OUTPUT_DIR / "gate_progress.json"
BUDGET_DATA_PATH = OUTPUT_DIR / "budget_allocation.json"
ARTIFACT_PATH = OUTPUT_DIR / "artifact.json"
TITLE = "Put the $500 into independent validation"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object at {path}")
    return payload


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def parse_test_receipt(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    if not suites:
        raise ValueError(f"no test suites found in {path}")
    summary = {
        "tests": sum(int(suite.attrib.get("tests", 0)) for suite in suites),
        "failures": sum(int(suite.attrib.get("failures", 0)) for suite in suites),
        "errors": sum(int(suite.attrib.get("errors", 0)) for suite in suites),
        "skipped": sum(int(suite.attrib.get("skipped", 0)) for suite in suites),
        "time_seconds": round(
            sum(float(suite.attrib.get("time", 0.0)) for suite in suites), 3
        ),
    }
    summary["passed"] = (
        summary["tests"] - summary["failures"] - summary["errors"] - summary["skipped"]
    )
    summary["clean"] = (
        summary["tests"] > 0
        and summary["failures"] == 0
        and summary["errors"] == 0
    )
    return summary


def build_report_data(*, generated_utc: str | None = None) -> dict[str, Any]:
    sprint = read_json(SPRINT_PATH)
    tests = parse_test_receipt(TEST_RECEIPT_PATH)
    current = sprint["current_state"]
    milestones = sprint["budget"]["milestones"]

    gates = [
        {
            "order": 1,
            "gate": "Focused technical checks",
            "completion": 1.0 if tests["clean"] else 0.0,
            "observed": f"{tests['passed']}/{tests['tests']} passed",
            "meaning": "The bounded evaluator, runtime, reproduction, and sprint checks passed locally.",
        },
        {
            "order": 2,
            "gate": "Authorities with valid seals",
            "completion": current["authorities_with_valid_seals"]
            / current["authorities_total"],
            "observed": (
                f"{current['authorities_with_valid_seals']}/"
                f"{current['authorities_total']} authorities"
            ),
            "meaning": "SWPP and TVA remain at zero valid prospective seals.",
        },
        {
            "order": 3,
            "gate": "Preliminary sample gate",
            "completion": 1.0 if current["preliminary_gate_ready"] else 0.0,
            "observed": (
                "ready"
                if current["preliminary_gate_ready"]
                else f"{current['common_settled_hour_count']} common settled hours"
            ),
            "meaning": "A performance claim remains closed.",
        },
        {
            "order": 4,
            "gate": "Independent reproduction",
            "completion": (
                1.0 if current["independent_reproduction_complete"] else 0.0
            ),
            "observed": (
                "complete"
                if current["independent_reproduction_complete"]
                else "not complete"
            ),
            "meaning": "The handoff is ready, but no external receipt exists.",
        },
        {
            "order": 5,
            "gate": "Independent evaluator named",
            "completion": 1.0 if current["independent_evaluator_named"] else 0.0,
            "observed": (
                "named" if current["independent_evaluator_named"] else "not named"
            ),
            "meaning": "This is the scarce input the $500 can buy.",
        },
    ]
    allocation = [
        {
            "order": index,
            "milestone": row["label"],
            "amount_usd": row["amount_usd"],
            "hours": row["estimated_hours"],
            "release_condition": row["release_condition"],
            "negative_result_paid": row["paid_if_result_is_negative"],
        }
        for index, row in enumerate(milestones, start=1)
    ]
    data: dict[str, Any] = {
        "schema": "external_validation_500_report_data.v1",
        "generated_utc": generated_utc or now_utc(),
        "decision": sprint["decision"],
        "status": sprint["status"],
        "budget_usd": sprint["budget"]["total_usd"],
        "estimated_reviewer_hours": sprint["budget"]["estimated_total_hours"],
        "current_state": current,
        "focused_test_receipt": tests,
        "gate_progress": gates,
        "budget_allocation": allocation,
        "source_artifacts": sprint["source_artifacts"],
        "sprint_packet_sha256": sprint["packet_sha256"],
        "claim_boundary": sprint["claim_boundary"],
    }
    data["report_data_sha256"] = canonical_sha256(data)
    return data


def build_artifact(data: dict[str, Any]) -> dict[str, Any]:
    source_id = "compiled_validation_sprint"
    compiled_source = {
        "id": source_id,
        "label": "$500 validation sprint compiled evidence",
        "path": repo_path(REPORT_DATA_PATH),
    }
    gate_source = {
        "id": "validation_gate_query",
        "label": "Validation gate completion rows",
        "path": repo_path(GATE_DATA_PATH),
        "query": {
            "engine": "duckdb",
            "language": "sql",
            "sql": (
                "SELECT gate, completion, observed, meaning, \"order\" "
                "FROM read_json_auto("
                f"'{repo_path(GATE_DATA_PATH)}'"
                ") ORDER BY \"order\""
            ),
            "description": (
                "Loads the bounded validation-gate completion rows used by the chart."
            ),
            "tables_used": [repo_path(GATE_DATA_PATH)],
            "executed_at": data["generated_utc"],
            "filters": ["Snapshot generated July 16, 2026"],
            "metric_definitions": [
                "completion is the observed fraction of each binary or coverage gate; it is not a forecasting-skill metric"
            ],
        },
    }
    budget_source = {
        "id": "budget_allocation_query",
        "label": "$500 milestone allocation rows",
        "path": repo_path(BUDGET_DATA_PATH),
        "query": {
            "engine": "duckdb",
            "language": "sql",
            "sql": (
                "SELECT \"order\", milestone, amount_usd, hours, "
                "release_condition, negative_result_paid "
                "FROM read_json_auto("
                f"'{repo_path(BUDGET_DATA_PATH)}'"
                ") ORDER BY \"order\""
            ),
            "description": (
                "Loads the three outcome-independent evaluator milestones."
            ),
            "tables_used": [repo_path(BUDGET_DATA_PATH)],
            "executed_at": data["generated_utc"],
            "filters": ["Total allocation must equal exactly 500 USD"],
            "metric_definitions": [
                "amount_usd is the fixed milestone payment and does not depend on a positive result",
                "hours is a planning estimate rather than a time-and-materials authorization",
            ],
        },
    }
    sources = [compiled_source, gate_source, budget_source]
    current = data["current_state"]
    tests = data["focused_test_receipt"]
    budget_rows = data["budget_allocation"]
    budget_total = sum(row["amount_usd"] for row in budget_rows)

    manifest = {
        "version": 1,
        "surface": "report",
        "title": TITLE,
        "description": (
            "A decision-ready allocation of the available innovation budget "
            "toward independent validation."
        ),
        "generatedAt": data["generated_utc"],
        "sources": sources,
        "charts": [
            {
                "id": "validation_gate_chart",
                "title": "Validation gate completion",
                "subtitle": (
                    "Readiness indicators as of July 16, 2026; percentages show "
                    "gate or coverage completion, not forecasting skill."
                ),
                "type": "bar",
                "dataset": "gate_progress",
                "source": gate_source,
                "valueFormat": "percent",
                "encodings": {
                    "x": {
                        "field": "gate",
                        "type": "nominal",
                        "label": "Validation gate",
                    },
                    "y": {
                        "field": "completion",
                        "type": "quantitative",
                        "label": "Completion",
                    },
                    "tooltip": [
                        {
                            "field": "observed",
                            "type": "nominal",
                            "label": "Observed",
                        },
                        {
                            "field": "meaning",
                            "type": "nominal",
                            "label": "Interpretation",
                        },
                    ],
                },
            }
        ],
        "tables": [
            {
                "id": "budget_allocation_table",
                "title": "$500 milestone allocation",
                "subtitle": (
                    "Fixed deliverables; compensation does not depend on a "
                    "positive result."
                ),
                "dataset": "budget_allocation",
                "source": budget_source,
                "defaultSort": {"field": "order", "direction": "asc"},
                "columns": [
                    {"field": "order", "label": "Step", "type": "number"},
                    {"field": "milestone", "label": "Milestone", "type": "text"},
                    {
                        "field": "amount_usd",
                        "label": "Budget",
                        "format": "currency",
                    },
                    {"field": "hours", "label": "Est. hours", "type": "number"},
                    {
                        "field": "release_condition",
                        "label": "Release condition",
                        "type": "text",
                    },
                    {
                        "field": "negative_result_paid",
                        "label": "Paid if negative",
                        "type": "text",
                    },
                ],
            }
        ],
        "blocks": [
            {
                "id": "report_title",
                "type": "markdown",
                "body": f"# {TITLE}",
            },
            {
                "id": "executive_summary",
                "type": "markdown",
                "sourceId": source_id,
                "body": (
                    "## Executive Summary\n\n"
                    "- **Spend the full $500 on one independent evaluator.** "
                    "Release it in three fixed milestones: $100 for protocol "
                    "review and freeze, $300 for a reviewer-controlled clean-room "
                    "reproduction, and $100 for the attributable final memo.\n"
                    "- **Do not use this money as trading capital or for more "
                    "model tuning.** The platform already has a frozen packet, "
                    "standard-library verifier, protocol template, receipt "
                    "template, and public clean-runner path.\n"
                    f"- **The system is technically review-ready, not externally "
                    f"validated.** {tests['passed']}/{tests['tests']} focused "
                    f"checks pass, but maturity remains Level "
                    f"{current['repository_supported_level']}, only "
                    f"{current['authorities_with_valid_seals']}/"
                    f"{current['authorities_total']} authorities have valid "
                    f"seals, common settled hours are "
                    f"{current['common_settled_hour_count']}, and no independent "
                    f"evaluator is named.\n"
                    "- **Economic pressure relief comes after an attributable "
                    "receipt.** Use that proof to pursue a paid evidence review "
                    "or grant-funded buyer pilot; do not imply revenue, savings, "
                    "or trading profitability from the receipt alone."
                ),
            },
            {
                "id": "bottleneck_finding",
                "type": "markdown",
                "sourceId": source_id,
                "body": (
                    "## The missing scarce input is independent human authority\n\n"
                    "**Most of the technical plumbing is already present.** "
                    "The clean checks and frozen handoff establish reviewability, "
                    "while the coverage and external gates remain visibly open. "
                    "The chart separates technical readiness from external "
                    "validation so a green local test suite cannot be mistaken "
                    "for a performance result."
                ),
            },
            {
                "id": "validation_gate_chart_block",
                "type": "chart",
                "chartId": "validation_gate_chart",
            },
            {
                "id": "allocation_finding",
                "type": "markdown",
                "sourceId": source_id,
                "body": (
                    "## Three fixed milestones protect independence\n\n"
                    f"**The allocation totals exactly ${budget_total}.** Each "
                    "payment is tied to a review artifact rather than a favorable "
                    "finding. The first milestone is paid for an honest accept-or-"
                    "decline decision; the remaining milestones remain payable "
                    "when the reproduction or final conclusion is negative."
                ),
            },
            {
                "id": "budget_allocation_table_block",
                "type": "table",
                "tableId": "budget_allocation_table",
            },
            {
                "id": "recommended_next_steps",
                "type": "markdown",
                "sourceId": source_id,
                "body": (
                    "## Recommended Next Steps\n\n"
                    "1. Copy the evaluator brief from the sprint packet and "
                    "shortlist three candidates with Python, time-series, and "
                    "reproducibility experience.\n"
                    "2. Score independence first. Reject anyone who helped tune "
                    "the model, has an undisclosed interest, or requests a "
                    "positive-result bonus.\n"
                    "3. Have the selected evaluator complete the protocol decision "
                    "before inspecting or scoring new outcomes.\n"
                    "4. Use public GitHub Actions, OSF registration, Zenodo, and "
                    "GitHub Pages for clean execution, preregistration, DOI "
                    "archival, and a reviewer surface at zero platform cost.\n"
                    "5. Release each milestone only after its raw logs, hashes, "
                    "receipt, or memo is delivered. Preserve every discrepancy "
                    "and negative result."
                ),
            },
            {
                "id": "further_questions",
                "type": "markdown",
                "body": (
                    "## Further Questions\n\n"
                    "- Which evaluator can credibly disclose independence and "
                    "remain attributable for the full review window?\n"
                    "- Can the next protocol solve the SWPP and TVA coverage gap "
                    "without post-outcome exclusions or route changes?\n"
                    "- Which buyer or grant program will own the first paid pilot "
                    "metric after the external receipt exists?"
                ),
            },
            {
                "id": "caveats",
                "type": "markdown",
                "sourceId": source_id,
                "body": (
                    "## Caveats and Assumptions\n\n"
                    "- The snapshot is dated July 16, 2026 and will change as "
                    "prospective records accumulate.\n"
                    "- A sponsor-paid evaluator can still be independent only "
                    "with disclosed, fixed, outcome-independent compensation and "
                    "no design role.\n"
                    "- Passing local or clean-runner checks proves software "
                    "reproducibility, not forecasting skill, field performance, "
                    "savings, production readiness, or profitable trading.\n"
                    "- The $500 is a bounded first review budget. It may not buy "
                    "a senior domain expert for a full confirmatory study; if no "
                    "qualified evaluator accepts the fixed scope, keep the money "
                    "unspent rather than lowering the independence standard."
                ),
            },
        ],
    }
    snapshot = {
        "version": 1,
        "generatedAt": data["generated_utc"],
        "status": "ready",
        "datasets": {
            "gate_progress": data["gate_progress"],
            "budget_allocation": data["budget_allocation"],
        },
    }
    return {
        "surface": "report",
        "manifest": manifest,
        "snapshot": snapshot,
        "sources": sources,
        "package_info": {
            "origin": "LumaTrader external validation sprint",
            "artifact_sha256": data["report_data_sha256"],
        },
    }


def write_outputs(report_data: dict[str, Any], artifact: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DATA_PATH.write_text(
        json.dumps(report_data, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    ARTIFACT_PATH.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    GATE_DATA_PATH.write_text(
        json.dumps(report_data["gate_progress"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    BUDGET_DATA_PATH.write_text(
        json.dumps(report_data["budget_allocation"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the canonical report artifact for the $500 sprint."
    )
    parser.add_argument(
        "--generated-utc",
        help="Optional stable report timestamp used for reproducibility checks.",
    )
    args = parser.parse_args()
    report_data = build_report_data(generated_utc=args.generated_utc)
    artifact = build_artifact(report_data)
    write_outputs(report_data, artifact)
    print(repo_path(REPORT_DATA_PATH))
    print(repo_path(ARTIFACT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
