from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"
OUT_OPS = ROOT / "out" / "ops" / "opportunity_autopilot"

RANKED_JSON = ROOT / "out" / "opportunities" / "ranked.json"
FILLER_SUMMARY_JSON = ROOT / "out" / "opportunities" / "filler_summary.json"
FUNDING_QUEUE_JSON = ROOT / "out" / "funding" / "funding_approval_queue.json"
SUBMISSIONS_READY_DIR = ROOT / "out" / "funding" / "submissions_ready"
EMAIL_OPP_LATEST = ROOT / "out" / "opportunities" / "email" / "email_opportunities_latest.json"
EMAIL_RESP_LATEST = ROOT / "out" / "opportunities" / "email" / "email_response_watcher_latest.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _now().isoformat()


def _stamp() -> str:
    return _now().strftime("%Y%m%dT%H%M%SZ")


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")
    tmp.replace(path)


def _run_cmd(name: str, args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        args,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "name": name,
        "args": args,
        "return_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _try_parse_json_blob(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("{") and raw.endswith("}"):
        try:
            return json.loads(raw)
        except Exception:
            return None
    lines = [line for line in raw.splitlines() if line.strip()]
    if not lines:
        return None
    last = lines[-1].strip()
    if last.startswith("{") and last.endswith("}"):
        try:
            return json.loads(last)
        except Exception:
            return None
    return None


def _tail(text: str, n: int = 12) -> str:
    lines = (text or "").splitlines()
    if len(lines) <= n:
        return "\n".join(lines)
    return "\n".join(lines[-n:])


def _queue_counts(queue: list[dict[str, Any]]) -> dict[str, Any]:
    by_state = Counter(str(item.get("approval_state") or "UNKNOWN").upper() for item in queue)
    by_channel = Counter(str(item.get("channel") or "unknown").lower() for item in queue)
    return {
        "total": len(queue),
        "by_state": dict(sorted(by_state.items())),
        "by_channel": dict(sorted(by_channel.items())),
    }


def _build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Opportunity Autopilot Tracker")
    lines.append("")
    lines.append(f"- generated_utc: {report.get('generated_utc', '')}")
    lines.append(f"- status: {report.get('status', '')}")
    lines.append(f"- status_reason: {report.get('status_reason', '')}")
    lines.append("")

    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    lines.append("## Summary")
    lines.append(f"- ranked_actionable: {summary.get('ranked_actionable', 0)}")
    lines.append(f"- autofill_drafted: {summary.get('autofill_drafted', 0)}")
    lines.append(f"- funding_queue_total: {summary.get('funding_queue_total', 0)}")
    lines.append(f"- shipped_this_run: {summary.get('shipped_this_run', 0)}")
    lines.append(f"- shipping_failures: {summary.get('shipping_failures', 0)}")
    lines.append("")

    lines.append("## Shipping")
    shipping = report.get("shipping", {}) if isinstance(report.get("shipping"), dict) else {}
    lines.append(f"- channels: {', '.join(shipping.get('ship_channels', []))}")
    lines.append(f"- eligible_before_ship: {shipping.get('eligible_before_ship', 0)}")
    lines.append(f"- shipped_success: {shipping.get('shipped_success', 0)}")
    lines.append(f"- shipped_failed: {shipping.get('shipped_failed', 0)}")
    manifests = shipping.get("submission_manifests", []) if isinstance(shipping.get("submission_manifests"), list) else []
    if manifests:
        lines.append("- manifests:")
        for manifest in manifests:
            lines.append(f"  - {manifest}")
    lines.append("")

    lines.append("## Queue Counts")
    counts = report.get("funding_queue", {}) if isinstance(report.get("funding_queue"), dict) else {}
    lines.append(f"- total: {counts.get('total', 0)}")
    by_state = counts.get("by_state", {}) if isinstance(counts.get("by_state"), dict) else {}
    for key in sorted(by_state.keys()):
        lines.append(f"- state_{key.lower()}: {by_state.get(key)}")
    by_channel = counts.get("by_channel", {}) if isinstance(counts.get("by_channel"), dict) else {}
    for key in sorted(by_channel.keys()):
        lines.append(f"- channel_{key}: {by_channel.get(key)}")
    lines.append("")

    lines.append("## Command Results")
    cmds = report.get("commands", []) if isinstance(report.get("commands"), list) else []
    for cmd in cmds:
        lines.append(f"- {cmd.get('name')}: rc={cmd.get('return_code')}")
    lines.append("")

    lines.append("## Constraint")
    lines.append("- Federal and lender portals require human login, attestations, and signature; this pipeline prepares and tracks submission-ready packets but does not bypass portal legal requirements.")
    lines.append("")

    lines.append("## Artifact Paths")
    artifacts = report.get("artifacts", {}) if isinstance(report.get("artifacts"), dict) else {}
    for key in sorted(artifacts.keys()):
        lines.append(f"- {key}: {artifacts.get(key)}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run opportunity discovery, autofill, shipping, and tracking in one pass.")
    parser.add_argument("--min-score", type=float, default=0.35)
    parser.add_argument("--harvest-limit", type=int, default=5000)
    parser.add_argument("--fill-limit", type=int, default=50)
    parser.add_argument("--key-rows", type=int, default=30)
    parser.add_argument("--build-top", type=int, default=20)
    parser.add_argument("--ship-channels", default="grant,grant_source_direct,contract,loan,crowdfund")
    parser.add_argument("--skip-email", action="store_true")
    parser.add_argument("--skip-opportunity-harvest", action="store_true")
    parser.add_argument("--skip-opportunity-fill", action="store_true")
    parser.add_argument("--ship-channel-label", default="portal_manual_submit")
    args = parser.parse_args()

    py = sys.executable

    commands: list[dict[str, Any]] = []
    if not args.skip_opportunity_harvest:
        commands.append(
            _run_cmd(
                "opportunity_harvest",
                [
                    py,
                    str(CODE / "opportunity_harvester.py"),
                    "--min-score",
                    str(args.min_score),
                    "--limit",
                    str(args.harvest_limit),
                ],
            )
        )
    if not args.skip_opportunity_fill:
        commands.append(
            _run_cmd(
                "opportunity_fill",
                [
                    py,
                    str(CODE / "opportunity_filler.py"),
                    "--min-score",
                    str(args.min_score),
                    "--limit",
                    str(args.fill_limit),
                ],
            )
        )
    commands.append(
        _run_cmd(
            "funding_harvest_from_keys",
            [
                py,
                str(CODE / "funding_autopilot.py"),
                "harvest-from-keys",
                "--rows",
                str(args.key_rows),
            ],
        )
    )
    commands.append(
        _run_cmd(
            "funding_build",
            [
                py,
                str(CODE / "funding_autopilot.py"),
                "build",
                "--top",
                str(args.build_top),
            ],
        )
    )

    if not args.skip_email:
        commands.append(
            _run_cmd(
                "email_opportunity_once",
                [
                    py,
                    str(CODE / "email_opportunity_finder.py"),
                    "--once",
                    "--max-per-cycle",
                    "75",
                ],
            )
        )
        commands.append(
            _run_cmd(
                "email_response_once",
                [
                    py,
                    str(CODE / "email_response_watcher.py"),
                    "--once",
                    "--max-per-cycle",
                    "75",
                ],
            )
        )

    ship_channels = [c.strip().lower() for c in str(args.ship_channels).split(",") if c.strip()]
    queue_before = _read_json(FUNDING_QUEUE_JSON, [])
    queue_before = queue_before if isinstance(queue_before, list) else []
    eligible = [
        item
        for item in queue_before
        if str(item.get("approval_state") or "").upper() == "APPROVED"
        and str(item.get("channel") or "").lower() in ship_channels
    ]

    ship_results: list[dict[str, Any]] = []
    submission_manifests: list[str] = []
    for item in eligible:
        ticket = str(item.get("ticket_id") or "").strip()
        if not ticket:
            continue
        res = _run_cmd(
            "funding_ship",
            [
                py,
                str(CODE / "funding_autopilot.py"),
                "ship",
                "--ticket",
                ticket,
                "--channel",
                args.ship_channel_label,
            ],
        )
        parsed = _try_parse_json_blob(res.get("stdout", ""))
        if isinstance(parsed, dict) and parsed.get("submission_manifest"):
            submission_manifests.append(str(parsed.get("submission_manifest")))
        res["ticket_id"] = ticket
        ship_results.append(res)

    queue_after = _read_json(FUNDING_QUEUE_JSON, [])
    queue_after = queue_after if isinstance(queue_after, list) else []

    ranked = _read_json(RANKED_JSON, {})
    filler = _read_json(FILLER_SUMMARY_JSON, {})
    email_opp = _read_json(EMAIL_OPP_LATEST, {})
    email_resp = _read_json(EMAIL_RESP_LATEST, {})

    shipped_success = sum(1 for row in ship_results if int(row.get("return_code", 1)) == 0)
    shipped_failed = len(ship_results) - shipped_success

    cmd_failures = [row for row in commands if int(row.get("return_code", 1)) != 0]
    status = "ok" if not cmd_failures and shipped_failed == 0 else "partial"
    status_reason = "all_steps_succeeded" if status == "ok" else "some_steps_failed"

    report = {
        "generated_utc": _iso_now(),
        "scope": "opportunity_autofill_and_tracking",
        "status": status,
        "status_reason": status_reason,
        "config": {
            "min_score": args.min_score,
            "harvest_limit": args.harvest_limit,
            "fill_limit": args.fill_limit,
            "key_rows": args.key_rows,
            "build_top": args.build_top,
            "ship_channels": ship_channels,
            "ship_channel_label": args.ship_channel_label,
            "skip_email": bool(args.skip_email),
            "skip_opportunity_harvest": bool(args.skip_opportunity_harvest),
            "skip_opportunity_fill": bool(args.skip_opportunity_fill),
        },
        "summary": {
            "ranked_actionable": int((ranked or {}).get("total_actionable") or 0),
            "autofill_drafted": int((filler or {}).get("drafted_count") or 0),
            "funding_queue_total": len(queue_after),
            "shipped_this_run": shipped_success,
            "shipping_failures": shipped_failed,
            "email_new_opportunities": int((email_opp or {}).get("new_opportunities") or 0),
            "email_new_responses": int((email_resp or {}).get("new_responses") or 0),
        },
        "funding_queue": _queue_counts(queue_after),
        "shipping": {
            "ship_channels": ship_channels,
            "eligible_before_ship": len(eligible),
            "shipped_success": shipped_success,
            "shipped_failed": shipped_failed,
            "submission_manifests": submission_manifests,
        },
        "commands": [
            {
                "name": row.get("name"),
                "return_code": row.get("return_code"),
                "stdout_tail": _tail(str(row.get("stdout", ""))),
                "stderr_tail": _tail(str(row.get("stderr", ""))),
            }
            for row in commands
        ],
        "ship_results": [
            {
                "ticket_id": row.get("ticket_id"),
                "return_code": row.get("return_code"),
                "stdout_tail": _tail(str(row.get("stdout", ""))),
                "stderr_tail": _tail(str(row.get("stderr", ""))),
            }
            for row in ship_results
        ],
        "artifacts": {
            "ranked_json": str(RANKED_JSON),
            "filler_summary_json": str(FILLER_SUMMARY_JSON),
            "funding_queue_json": str(FUNDING_QUEUE_JSON),
            "submissions_ready_dir": str(SUBMISSIONS_READY_DIR),
            "email_opportunity_latest": str(EMAIL_OPP_LATEST),
            "email_response_latest": str(EMAIL_RESP_LATEST),
        },
        "constraints": {
            "federal_submission": "Requires human portal login and AOR signature; this autopilot prepares and tracks submission-ready packets.",
        },
    }

    stamp = _stamp()
    tagged_json = OUT_OPS / f"opportunity_autopilot_{stamp}.json"
    latest_json = OUT_OPS / "opportunity_autopilot_latest.json"
    tagged_md = OUT_OPS / f"opportunity_autopilot_{stamp}.md"
    latest_md = OUT_OPS / "opportunity_autopilot_latest.md"

    _write_json(tagged_json, report)
    _write_json(latest_json, report)

    md = _build_markdown(report)
    _write_text(tagged_md, md)
    _write_text(latest_md, md)

    print(f"OPPORTUNITY_AUTOPILOT_STATUS={status}")
    print(f"OPPORTUNITY_AUTOPILOT_REASON={status_reason}")
    print(f"OPPORTUNITY_AUTOPILOT_SHIPPED={shipped_success}")
    print(f"OPPORTUNITY_AUTOPILOT_ELIGIBLE={len(eligible)}")
    print(f"OPPORTUNITY_AUTOPILOT_LATEST_JSON={latest_json}")
    print(f"OPPORTUNITY_AUTOPILOT_LATEST_MD={latest_md}")

    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
