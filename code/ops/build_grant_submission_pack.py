from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def lane_status(lane: dict[str, Any]) -> str:
    ran = int(lane.get("ran_count", 0) or 0)
    passed = int(lane.get("passed_count", 0) or 0)
    failed = int(lane.get("failed_count", 0) or 0)
    timeout = int(lane.get("timeout_count", 0) or 0)

    if ran > 0 and passed == ran:
        return "GREEN"
    if passed > 0:
        return "YELLOW"
    if failed > 0 or timeout > 0:
        return "RED"
    return "UNKNOWN"


def find_lane(report: dict[str, Any], name: str) -> dict[str, Any]:
    for lane in report.get("lanes", []):
        if str(lane.get("lane")) == name:
            return lane
    return {}


def make_benchmark_table(report: dict[str, Any]) -> str:
    lines = []
    lines.append("# Reviewer-Safe Benchmark Evidence Table")
    lines.append("")
    lines.append("Generated UTC: " + now_utc())
    lines.append("")
    lines.append("This table summarizes reproducible benchmark evidence. It uses cautious language and avoids overclaiming.")
    lines.append("")
    lines.append("| Lane | Status | Existing | Ran | Passed | Failed | Timeout | Reviewer-Safe Use |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---|")

    for lane in report.get("lanes", []):
        status = lane_status(lane)
        if status == "GREEN":
            use = "Use as main supporting preliminary evidence."
        elif status == "YELLOW":
            use = "Use as partial evidence with risks disclosed."
        elif status == "RED":
            use = "Use as planned work only until repaired."
        else:
            use = "Needs review."

        lines.append(
            "| "
            + str(lane.get("lane"))
            + " | "
            + status
            + " | "
            + str(lane.get("existing_count"))
            + " | "
            + str(lane.get("ran_count"))
            + " | "
            + str(lane.get("passed_count"))
            + " | "
            + str(lane.get("failed_count"))
            + " | "
            + str(lane.get("timeout_count"))
            + " | "
            + use
            + " |"
        )

    lines.append("")
    lines.append("## Reviewer-Safe Language")
    lines.append("")
    lines.append("Use: preliminary benchmark, reproducible evidence, bounded synthetic validation, safety-gated runtime, existing-stack discovery, prototype validation.")
    lines.append("")
    lines.append("Avoid: undeniable, guaranteed, risk-free, proven superiority, fully autonomous live trading, production-certified.")
    return "\n".join(lines)


def abstract_template(title: str, agency: str, lane: dict[str, Any], objective: str, transition: str) -> str:
    status = lane_status(lane)

    lines = []
    lines.append("# " + title)
    lines.append("")
    lines.append("Generated UTC: " + now_utc())
    lines.append("")
    lines.append("Agency lane: " + agency)
    lines.append("Evidence status: " + status)
    lines.append("")
    lines.append("## Technical Abstract")
    lines.append("")
    lines.append(
        "LumenCore is a safety-gated measurement, orchestration, and decision-support architecture designed to convert heterogeneous signals into reproducible, auditable evidence. "
        "The current prototype emphasizes bounded autonomy, traceable benchmark outputs, SHA-256 evidence artifacts, and runtime safety controls. "
        "The proposed work will mature the system from preliminary prototype evidence into an agency-specific validation package."
    )
    lines.append("")
    lines.append("## Objective")
    lines.append("")
    lines.append(objective)
    lines.append("")
    lines.append("## Current Evidence")
    lines.append("")
    lines.append("- Existing scripts: " + str(lane.get("existing_count")))
    lines.append("- Scripts ran: " + str(lane.get("ran_count")))
    lines.append("- Passed: " + str(lane.get("passed_count")))
    lines.append("- Failed: " + str(lane.get("failed_count")))
    lines.append("- Timed out: " + str(lane.get("timeout_count")))
    lines.append("")
    lines.append("## Work Plan")
    lines.append("")
    lines.append("1. Freeze baseline benchmark artifacts and SHA-256 manifests.")
    lines.append("2. Expand deterministic synthetic and real-data validation cases.")
    lines.append("3. Add reviewer-facing evidence cards and reproducibility appendix.")
    lines.append("4. Demonstrate safety-gated runtime operation without uncontrolled live actions.")
    lines.append("5. Prepare transition package for agency pilot or partner review.")
    lines.append("")
    lines.append("## Transition Path")
    lines.append("")
    lines.append(transition)
    lines.append("")
    lines.append("## Claims Boundary")
    lines.append("")
    lines.append("This is preliminary prototype evidence. The proposal does not claim production certification, guaranteed performance, or risk-free autonomy.")
    return "\n".join(lines)


def blocker_closeout(report: dict[str, Any]) -> str:
    lines = []
    lines.append("# Grant Blocker Closeout Map")
    lines.append("")
    lines.append("Generated UTC: " + now_utc())
    lines.append("")
    lines.append("## Cleared / Not Blocking")
    lines.append("")
    for item in report.get("wins_not_blocking", []):
        lines.append("- " + str(item))

    lines.append("")
    lines.append("## Benchmark Blockers")
    lines.append("")
    blockers = report.get("detected_blockers", [])
    if blockers:
        for item in blockers:
            lines.append("- " + str(item))
    else:
        lines.append("- No benchmark blockers detected in the latest report.")

    lines.append("")
    lines.append("## Package Blockers Still To Close")
    lines.append("")
    lines.append("- Agency-specific one-page abstract: generated by this patch.")
    lines.append("- Reviewer-safe benchmark table: generated by this patch.")
    lines.append("- Budget justification mapped to milestones: template generated by this patch.")
    lines.append("- Commercialization / transition pathway: generated by this patch.")
    lines.append("- Letters of support / pilot validation: still needs human partner documents.")
    lines.append("- Final portal field mapping: template generated by this patch.")
    return "\n".join(lines)


def budget_map() -> str:
    lines = []
    lines.append("# Budget and Milestone Map Template")
    lines.append("")
    lines.append("Generated UTC: " + now_utc())
    lines.append("")
    lines.append("| Milestone | Duration | Technical Output | Evidence Output | Budget Category | Notes |")
    lines.append("|---|---|---|---|---|---|")
    lines.append("| M1 Baseline freeze | Month 1 | Repo, benchmark, safety stack freeze | SHA-256 manifests and baseline report | Labor / cloud / tools | Establish reproducibility.")
    lines.append("| M2 Benchmark expansion | Months 1-2 | More synthetic and real-data cases | Updated evidence cards | Labor / data / compute | Expand validation depth.")
    lines.append("| M3 Agency lane prototype | Months 2-4 | DICE / Harbor / MissionWeave / TrackCast module refinement | Demo report and test logs | Labor / prototyping | Map to agency problem.")
    lines.append("| M4 Pilot package | Months 4-5 | Deployable demo package | Reviewer appendix and transition memo | Labor / travel / admin | Prepare partner/pilot review.")
    lines.append("| M5 Final report | Month 6 | Final prototype + roadmap | Final technical report | Labor / publication / admin | Close Phase I / prep Phase II.")
    lines.append("")
    lines.append("Budget must be adapted to the specific solicitation limits.")
    return "\n".join(lines)


def portal_map() -> str:
    lines = []
    lines.append("# Portal Field Mapping Template")
    lines.append("")
    lines.append("Generated UTC: " + now_utc())
    lines.append("")
    lines.append("| Portal Field | Draft Source | Status | Notes |")
    lines.append("|---|---|---|---|")
    lines.append("| UEI | Operator record | Cleared | User states UEI exists.")
    lines.append("| CAGE | Operator record | Cleared | User states CAGE exists.")
    lines.append("| SAM.gov status | Operator record | Cleared | User states SAM.gov exists.")
    lines.append("| Project title | Agency abstract | Drafted | Customize per solicitation.")
    lines.append("| Technical abstract | Agency abstract files | Drafted | Paste into portal field after review.")
    lines.append("| Keywords | Evidence cards | Drafted | AI, decision support, monitoring, safety-gated autonomy.")
    lines.append("| Budget narrative | Budget map | Template | Needs exact dollar amounts.")
    lines.append("| Commercialization | Transition path | Drafted | Needs partner/pilot details.")
    lines.append("| Attachments | Evidence cards / benchmark table | Drafted | Convert to PDF if portal requires.")
    lines.append("| Letters of support | External partners | Open | Needs human documents.")
    return "\n".join(lines)


def transition_path() -> str:
    lines = []
    lines.append("# Commercialization and Transition Path")
    lines.append("")
    lines.append("Generated UTC: " + now_utc())
    lines.append("")
    lines.append("LumenCore can transition through three paths:")
    lines.append("")
    lines.append("1. Agency pilot: deploy a bounded, safety-gated demonstration focused on monitoring, decision support, and evidence traceability.")
    lines.append("2. Infrastructure partner validation: use data-center, energy, port, logistics, or emergency-management style workflows to validate practical value.")
    lines.append("3. Commercial licensing: package the runtime evidence engine, benchmark harnesses, and dashboard outputs as a licensed decision-support layer.")
    lines.append("")
    lines.append("Near-term transition evidence should include pilot letters, non-sensitive screenshots, benchmark appendices, and SHA-256 manifests.")
    return "\n".join(lines)


def main() -> int:
    repo = root()
    report_path = repo / "out" / "grant_evidence" / "LATEST_grant_evidence_benchmark_lab.json"
    report = load_json(report_path)

    out = repo / "docs" / "grant_submission_pack"
    out.mkdir(parents=True, exist_ok=True)

    files = {}

    files["BENCHMARK_EVIDENCE_TABLE.md"] = make_benchmark_table(report)
    files["GRANT_BLOCKER_CLOSEOUT_MAP.md"] = blocker_closeout(report)
    files["BUDGET_MILESTONE_MAP_TEMPLATE.md"] = budget_map()
    files["PORTAL_FIELD_MAPPING_TEMPLATE.md"] = portal_map()
    files["COMMERCIALIZATION_TRANSITION_PATH.md"] = transition_path()

    files["DARPA_DICE_ONE_PAGE_ABSTRACT.md"] = abstract_template(
        "DARPA DICE One-Page Technical Abstract",
        "DARPA_DICE",
        find_lane(report, "DARPA_DICE"),
        "Develop a reproducible decision-intelligence benchmark layer for complex, adversarial, and multi-signal environments.",
        "Transition through a bounded prototype that demonstrates auditability, safety gates, and reproducible decision-support evidence."
    )

    files["NAVY_HARBORSENTINEL_ONE_PAGE_ABSTRACT.md"] = abstract_template(
        "Navy HarborSentinel One-Page Technical Abstract",
        "Navy_HarborSentinel",
        find_lane(report, "Navy_HarborSentinel"),
        "Advance a harbor and infrastructure monitoring prototype using synthetic validation, anomaly monitoring, and reviewer-safe benchmark evidence.",
        "Transition through port, facility, or infrastructure monitoring pilots with bounded synthetic and real-data scenarios."
    )

    files["DLA_MISSIONWEAVE_ONE_PAGE_ABSTRACT.md"] = abstract_template(
        "DLA MissionWeave One-Page Technical Abstract",
        "DLA_MissionWeave",
        find_lane(report, "DLA_MissionWeave"),
        "Demonstrate workflow orchestration and mission-support automation with reproducible benchmark evidence and traceable runtime outputs.",
        "Transition through logistics workflow mapping, routing simulations, and operational decision-support dashboards."
    )

    files["NSF_PROJECT_PITCH_ONE_PAGE_ABSTRACT.md"] = abstract_template(
        "NSF Project Pitch One-Page Technical Abstract",
        "NSF_Project_Pitch",
        find_lane(report, "NSF_Project_Pitch"),
        "Frame LumenCore as a research platform for reproducible evaluation of safety-gated autonomy, signal fusion, and evidence-driven optimization.",
        "Transition through peer-reviewable benchmark studies, prototype demos, and commercialization partner validation."
    )

    files["NAVY_TRACKCAST_ONE_PAGE_ABSTRACT.md"] = abstract_template(
        "Navy TrackCast One-Page Technical Abstract",
        "Navy_TrackCast",
        find_lane(report, "Navy_TrackCast"),
        "Validate existing TrackCast stack discovery and mature it into direct performance benchmarks for signal tracking, regime shift detection, and early warning.",
        "Transition after direct benchmark repair converts the existing-stack proof into operational performance evidence."
    )

    index = []
    index.append("# Grant Submission Pack Index")
    index.append("")
    index.append("Generated UTC: " + now_utc())
    index.append("")
    for name in sorted(files):
        index.append("- " + name)
    files["INDEX.md"] = "\n".join(index)

    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")

    print(json.dumps({"generated": sorted(files.keys())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
