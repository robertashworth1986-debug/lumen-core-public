from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in name)


def status_for_lane(lane: dict[str, Any]) -> str:
    if lane.get("passed_count", 0) == lane.get("ran_count", 0) and lane.get("ran_count", 0) > 0:
        return "GREEN"
    if lane.get("passed_count", 0) > 0:
        return "YELLOW"
    return "RED"


def claim_language(lane_name: str, status: str) -> str:
    if status == "GREEN":
        return (
            "Reviewer-safe claim: this lane has passing preliminary benchmark evidence "
            "inside the current repository, with reproducible scripts and SHA-256-tracked artifacts."
        )
    if status == "YELLOW":
        return (
            "Reviewer-safe claim: this lane has partial passing preliminary benchmark evidence, "
            "but one or more scripts require cleanup before it should be presented as complete."
        )
    return (
        "Reviewer-safe claim: this lane is not yet evidence-ready. Scripts exist, but no passing "
        "benchmark was recorded in the latest run."
    )


def build_card(report: dict[str, Any], lane: dict[str, Any]) -> str:
    status = status_for_lane(lane)
    lines = []
    lines.append("# Grant Evidence Card — " + str(lane.get("lane")))
    lines.append("")
    lines.append("Generated UTC: " + now_utc())
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append("- Evidence status: " + status)
    lines.append("- Existing scripts: " + str(lane.get("existing_count")))
    lines.append("- Scripts ran: " + str(lane.get("ran_count")))
    lines.append("- Passed: " + str(lane.get("passed_count")))
    lines.append("- Failed: " + str(lane.get("failed_count")))
    lines.append("- Timed out: " + str(lane.get("timeout_count")))
    lines.append("")
    lines.append("## Claim Type")
    lines.append("")
    lines.append(str(lane.get("claim_type")))
    lines.append("")
    lines.append("## Reviewer-Safe Claim")
    lines.append("")
    lines.append(claim_language(str(lane.get("lane")), status))
    lines.append("")
    lines.append("## Evidence Table")
    lines.append("")
    lines.append("| Script | Exists | Ran | Return Code | Timeout | SHA-256 |")
    lines.append("|---|---:|---:|---:|---:|---|")

    for result in lane.get("results", []):
        lines.append(
            "| "
            + str(result.get("path"))
            + " | "
            + str(result.get("exists"))
            + " | "
            + str(result.get("ran"))
            + " | "
            + str(result.get("returncode"))
            + " | "
            + str(result.get("timeout"))
            + " | "
            + str(result.get("sha256"))
            + " |"
        )

    lines.append("")
    lines.append("## Use In Grant Narrative")
    lines.append("")
    if status == "GREEN":
        lines.append("- Use this lane in the main technical narrative.")
        lines.append("- Include the evidence table in an appendix.")
        lines.append("- Describe results as preliminary and reproducible, not final proof.")
    elif status == "YELLOW":
        lines.append("- Use this lane carefully as partial evidence.")
        lines.append("- Put failures/timeouts in risk mitigation or next-work section.")
        lines.append("- Fix the failing script before submission when possible.")
    else:
        lines.append("- Do not use this lane as a positive result yet.")
        lines.append("- Use it only as planned work or a development roadmap until fixed.")
        lines.append("- Prioritize debugging before submission.")

    lines.append("")
    lines.append("## Next Action")
    lines.append("")
    if str(lane.get("lane")) == "Navy_TrackCast":
        lines.append("- Fix TrackCast failing scripts first; this is the only detected benchmark lane blocker.")
    elif status == "YELLOW":
        lines.append("- Review the failing or timeout script and rerun the benchmark lab.")
    else:
        lines.append("- Convert this evidence card into agency-specific proposal language.")

    return "\n".join(lines)


def build_trackcast_triage(report: dict[str, Any]) -> str:
    track = None
    for lane in report.get("lanes", []):
        if str(lane.get("lane")) == "Navy_TrackCast":
            track = lane
            break

    lines = []
    lines.append("# Navy TrackCast Failure Triage")
    lines.append("")
    lines.append("Generated UTC: " + now_utc())
    lines.append("")

    if not track:
        lines.append("No Navy_TrackCast lane found.")
        return "\n".join(lines)

    lines.append("## Summary")
    lines.append("")
    lines.append("- Existing scripts: " + str(track.get("existing_count")))
    lines.append("- Ran: " + str(track.get("ran_count")))
    lines.append("- Passed: " + str(track.get("passed_count")))
    lines.append("- Failed: " + str(track.get("failed_count")))
    lines.append("- Timed out: " + str(track.get("timeout_count")))
    lines.append("")
    lines.append("## Failed Scripts")
    lines.append("")

    for result in track.get("results", []):
        if result.get("ran") and result.get("returncode") not in [0, None]:
            lines.append("### " + str(result.get("path")))
            lines.append("")
            lines.append("- Return code: " + str(result.get("returncode")))
            lines.append("- Timeout: " + str(result.get("timeout")))
            lines.append("- SHA-256: " + str(result.get("sha256")))
            if result.get("stderr_tail"):
                lines.append("")
                lines.append("Error tail:")
                lines.append("```text")
                lines.append(str(result.get("stderr_tail"))[-3000:])
                lines.append("```")
            if result.get("stdout_tail"):
                lines.append("")
                lines.append("Output tail:")
                lines.append("```text")
                lines.append(str(result.get("stdout_tail"))[-3000:])
                lines.append("```")
            lines.append("")

    lines.append("## Repair Plan")
    lines.append("")
    lines.append("1. Identify whether failures are missing dependency, missing data file, import path issue, or actual assertion failure.")
    lines.append("2. Add a deterministic synthetic fixture so TrackCast can pass without external APIs.")
    lines.append("3. Rerun the grant evidence benchmark lab.")
    lines.append("4. Promote TrackCast from RED to GREEN or YELLOW before Navy submission.")

    return "\n".join(lines)


def build_blocker_map(report: dict[str, Any]) -> str:
    lines = []
    lines.append("# Grant Submission Blocker Map")
    lines.append("")
    lines.append("Generated UTC: " + now_utc())
    lines.append("")
    lines.append("## Not Blocking")
    lines.append("")
    for item in report.get("wins_not_blocking", []):
        lines.append("- " + str(item))

    lines.append("")
    lines.append("## Detected Benchmark Blockers")
    lines.append("")
    if report.get("detected_blockers"):
        for item in report.get("detected_blockers", []):
            lines.append("- " + str(item))
    else:
        lines.append("- None detected.")

    lines.append("")
    lines.append("## Package Blockers To Close")
    lines.append("")
    for item in report.get("likely_remaining_blockers", []):
        lines.append("- " + str(item))

    lines.append("")
    lines.append("## Priority Order")
    lines.append("")
    lines.append("1. Fix Navy_TrackCast benchmark failures.")
    lines.append("2. Build one-page agency technical abstracts.")
    lines.append("3. Build reviewer-safe benchmark table.")
    lines.append("4. Map budget to milestones.")
    lines.append("5. Add transition/commercialization path.")
    lines.append("6. Add letters of support or pilot validation.")
    lines.append("7. Finish final portal field mapping.")

    return "\n".join(lines)


def main() -> int:
    root = repo_root()
    report_path = root / "out" / "grant_evidence" / "LATEST_grant_evidence_benchmark_lab.json"
    report = load_json(report_path)

    cards_dir = root / "docs" / "grant_evidence_cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    generated = []

    for lane in report.get("lanes", []):
        name = safe_name(str(lane.get("lane")))
        path = cards_dir / (name + "_EVIDENCE_CARD.md")
        path.write_text(build_card(report, lane), encoding="utf-8")
        generated.append(str(path.relative_to(root)))

    trackcast_path = root / "out" / "grant_evidence" / "TRACKCAST_FAILURE_TRIAGE.md"
    trackcast_path.write_text(build_trackcast_triage(report), encoding="utf-8")
    generated.append(str(trackcast_path.relative_to(root)))

    blocker_path = cards_dir / "GRANT_SUBMISSION_BLOCKER_MAP.md"
    blocker_path.write_text(build_blocker_map(report), encoding="utf-8")
    generated.append(str(blocker_path.relative_to(root)))

    index_lines = []
    index_lines.append("# Grant Evidence Cards Index")
    index_lines.append("")
    index_lines.append("Generated UTC: " + now_utc())
    index_lines.append("")
    for item in generated:
        index_lines.append("- " + item)

    index_path = cards_dir / "INDEX.md"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")
    generated.append(str(index_path.relative_to(root)))

    print(json.dumps({"generated": generated}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
