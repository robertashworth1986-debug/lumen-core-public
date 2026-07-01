from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
GRANTS = ROOT / "grant_submissions"
OUT = ROOT / "out" / "ops"

FREEZE_JSON = OUT / "top_submission_package_freeze_latest.json"
ACTION_BOARD_JSON = OUT / "action_time_submission_board_latest.json"
OUT_JSON = OUT / "portal_preview_runbook_latest.json"
OUT_MD = GRANTS / "PORTAL_PREVIEW_RUNBOOK_2026-06-20.md"

NO_CLICK_RULE = (
    "Stop before upload finalization, certification, consent, signature, workspace lock, "
    "or submit. Fresh action-time approval is required for each such action."
)

COMMON_DONT_CAPTURE = [
    "passwords",
    "MFA or one-time codes",
    "API keys or private tokens",
    "TIN/EIN or banking details",
    "private profile screenshots containing sensitive account data",
]

PACKAGE_PORTAL_META = {
    "DICE": {
        "portal": "DARPA BAAT",
        "open_url": "https://baa.darpa.mil/",
        "opportunity_hint": "DICE / HR001126S0010",
        "preview_goal": "Confirm BAAT organization association, submitter authority, DICE opportunity visibility, accepted file type, and upload-preview rendering.",
        "stop_before": "BAAT consent, certification, final upload, submission, or any action that locks the workspace.",
    },
    "HarborSentinel": {
        "portal": "DSIP",
        "open_url": "https://www.dodsbirsttr.mil/submissions/",
        "opportunity_hint": "DON26BZ03-NV063 / HarborSentinel",
        "preview_goal": "Confirm DSIP organization linkage, submitter authority, topic visibility, required Volume 2/form fields, budget/forms, compliance pages, and attachment preview behavior.",
        "stop_before": "DSIP certification pages, final upload, submit, workspace lock, or any representation the user has not reviewed.",
    },
}


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


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def upload_candidates(package: dict[str, Any]) -> list[dict[str, Any]]:
    rows = package.get("upload_candidates", [])
    if not isinstance(rows, list):
        return []
    return [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("exists") is True
        and row.get("sha256")
        and row.get("bytes")
    ]


def board_card_by_package(board: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cards = board.get("cards", [])
    if not isinstance(cards, list):
        return {}
    return {
        str(card.get("package")): card
        for card in cards
        if isinstance(card, dict) and card.get("package")
    }


def preview_steps(package_name: str, meta: dict[str, str], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    upload_docx = next((row for row in candidates if row.get("role") == "upload_candidate_docx"), None)
    render_pdf = next((row for row in candidates if row.get("role") == "render_preview_pdf"), None)
    steps = [
        {
            "step": 1,
            "name": "Open portal",
            "action": f"User logs in to {meta['portal']} at {meta['open_url']}. Codex may observe and navigate after login.",
            "capture": "Record only login success/failure and whether the expected organization/workspace is visible.",
            "stop_if": "Portal asks for consent, certification, sensitive profile data, or payment-like information.",
        },
        {
            "step": 2,
            "name": "Verify authority",
            "action": "Check organization association and submitter/upload authority for the specific opportunity.",
            "capture": "yes/no/unclear for organization linkage, user role, and submitter authority.",
            "stop_if": "Role is unclear or portal asks to certify authority.",
        },
        {
            "step": 3,
            "name": "Verify opportunity",
            "action": f"Find opportunity/topic `{meta['opportunity_hint']}` and record whether it is visible and open for the intended action.",
            "capture": "Opportunity visibility, current portal deadline/window text, accepted file types, required sections, and page/size limits.",
            "stop_if": "Opportunity is not visible, closed, or instructions differ from the local package assumptions.",
        },
    ]
    if upload_docx:
        steps.append(
            {
                "step": 4,
                "name": "Compare upload candidate",
                "action": f"Use the frozen upload candidate `{upload_docx['path']}` only if its local SHA-256 still equals `{upload_docx['sha256']}`.",
                "capture": "Record whether the portal accepts the file type and whether local hash matches the freeze packet.",
                "stop_if": "Hash differs, file type is rejected, page limit differs, or the portal converts the file unexpectedly.",
            }
        )
    if render_pdf:
        steps.append(
            {
                "step": 5,
                "name": "Compare preview against render PDF",
                "action": f"Compare portal/Word preview against frozen render PDF `{render_pdf['path']}`.",
                "capture": "Record preview page count, visible formatting issues, missing figures/tables, and whether the preview remains within page/size limits.",
                "stop_if": "Preview differs materially, page count exceeds limit, or portal strips required content.",
            }
        )
    steps.append(
        {
            "step": len(steps) + 1,
            "name": "Record stop state",
            "action": "Update the worksheet with portal-safe facts and stop.",
            "capture": "Record remaining blockers and next evidence needed. Do not capture secrets.",
            "stop_if": NO_CLICK_RULE,
        }
    )
    return steps


def package_runbook(package: dict[str, Any], board_card: dict[str, Any]) -> dict[str, Any]:
    name = str(package.get("name", ""))
    meta = PACKAGE_PORTAL_META.get(name, {})
    candidates = upload_candidates(package)
    portal_blockers = [str(item) for item in package.get("portal_user_blockers", []) or []]
    return {
        "package": name,
        "portal": meta.get("portal", package.get("portal", "")),
        "open_url": meta.get("open_url", ""),
        "opportunity_hint": meta.get("opportunity_hint", ""),
        "preview_goal": meta.get("preview_goal", ""),
        "ready_for_preview": bool(package.get("local_ready")) and bool(candidates),
        "ready_for_upload_or_submit": False,
        "stop_before": meta.get("stop_before", NO_CLICK_RULE),
        "upload_candidates": candidates,
        "portal_user_blocker_count": len(portal_blockers),
        "portal_user_blockers": portal_blockers,
        "next_capture_tasks": board_card.get("next_capture_tasks", []) if isinstance(board_card, dict) else [],
        "steps": preview_steps(name, meta, candidates),
    }


def build_runbook(freeze: dict[str, Any] | None = None, board: dict[str, Any] | None = None) -> dict[str, Any]:
    freeze = freeze or read_json(FREEZE_JSON)
    board = board or read_json(ACTION_BOARD_JSON)
    cards = board_card_by_package(board)
    packages = freeze.get("packages", [])
    if not isinstance(packages, list):
        packages = []
    runbooks = [
        package_runbook(package, cards.get(str(package.get("name")), {}))
        for package in packages
        if isinstance(package, dict) and str(package.get("name")) in PACKAGE_PORTAL_META
    ]
    return {
        "generated_utc": now_utc(),
        "schema": "portal_preview_runbook_v1",
        "freeze_source": rel(FREEZE_JSON),
        "action_board_source": rel(ACTION_BOARD_JSON),
        "freeze_signature_sha256": str(freeze.get("freeze_signature_sha256", "")),
        "no_click_rule": NO_CLICK_RULE,
        "do_not_capture": COMMON_DONT_CAPTURE,
        "ready_for_upload_or_submit": False,
        "runbooks": runbooks,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Portal Preview Runbook",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        f"Freeze signature SHA-256: `{payload.get('freeze_signature_sha256', '')}`",
        f"Ready for upload or submit: {payload['ready_for_upload_or_submit']}",
        "",
        "## No-Click Rule",
        "",
        payload["no_click_rule"],
        "",
        "## Do Not Capture",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["do_not_capture"])
    lines.extend(["", "## Portal Runbooks", ""])
    for runbook in payload["runbooks"]:
        lines.extend(
            [
                f"### {runbook['package']} ({runbook['portal']})",
                "",
                f"- URL: {runbook['open_url']}",
                f"- Opportunity/topic hint: `{runbook['opportunity_hint']}`",
                f"- Preview goal: {runbook['preview_goal']}",
                f"- Ready for preview: {runbook['ready_for_preview']}",
                f"- Ready for upload or submit: {runbook['ready_for_upload_or_submit']}",
                f"- Stop before: {runbook['stop_before']}",
                f"- Portal/user blockers: {runbook['portal_user_blocker_count']}",
                "",
                "#### Frozen Upload Candidates",
                "",
                "| Role | Path | Bytes | SHA-256 |",
                "|---|---|---:|---|",
            ]
        )
        for candidate in runbook["upload_candidates"]:
            lines.append(
                f"| {candidate['role']} | `{candidate['path']}` | {candidate['bytes']} | `{candidate['sha256']}` |"
            )
        lines.extend(["", "#### Steps", ""])
        for step in runbook["steps"]:
            lines.extend(
                [
                    f"{step['step']}. {step['name']}",
                    f"   - Action: {step['action']}",
                    f"   - Capture: {step['capture']}",
                    f"   - Stop if: {step['stop_if']}",
                ]
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    payload = build_runbook()
    write_json(OUT_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "runbooks": len(payload["runbooks"]),
                "ready_for_upload_or_submit": payload["ready_for_upload_or_submit"],
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
