from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from application_context_resolver import load_application_profile


ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = ROOT / "out" / "grants" / "_queue" / "index.json"
BATCH_PATH = ROOT / "out" / "ops" / "federal_grant_batch_fill_latest.json"
SCAN_PATH = ROOT / "out" / "grants" / "_queue" / "opportunity_scan.json"
PROFILE_PATH = ROOT / "data" / "company_profile.json"
OPS_DIR = ROOT / "out" / "ops"


CONTRACT_RX = re.compile(r"\b(contract|procurement|acquisition|solicitation|rfp|rfi|idiq|baa)\b", re.I)
LOAN_RX = re.compile(r"\b(loan|lending|microloan|credit\s+facility|debt)\b", re.I)
FINANCE_SIGNAL_RX = re.compile(r"\b(financial|financing|capital)\b", re.I)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_days_remaining(value: str | None) -> int | None:
    if not value:
        return None
    txt = str(value).strip()
    if not txt or re.search(r"rolling|open", txt, flags=re.I):
        return None

    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            dt = datetime.strptime(txt, fmt).replace(tzinfo=timezone.utc)
            return max(0, int((dt - datetime.now(timezone.utc)).days))
        except ValueError:
            continue
    return None


def _sort_key(row: dict) -> tuple[int, float]:
    days = row.get("days_remaining")
    if days is None:
        days = 99999
    score = float(row.get("score") or 0.0)
    return int(days), -score


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _build_markdown_contract_loan(payload: dict) -> str:
    q = payload["queue_snapshot"]
    s = payload["summary"]

    lines: list[str] = []
    lines.append(f"# Contract and Loan Opportunity Pack ({payload['generated_utc']})")
    lines.append("")
    lines.append("## Scope")
    lines.append("- extraction: contract + loan opportunities from approved queue")
    lines.append("- evidence: out/grants/_queue/index.json ; out/ops/federal_grant_batch_fill_latest.json ; out/grants/_queue/opportunity_scan.json")
    lines.append("")
    lines.append("## Queue Snapshot")
    lines.append(f"- total: {q['total']}")
    lines.append(f"- approved: {q['approved']}")
    lines.append(f"- draft: {q['draft']}")
    lines.append(f"- submitted: {q['submitted']}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- contract candidates: {s['contract_candidates']} (ready now: {s['contract_ready_now']})")
    lines.append(f"- loan candidates: {s['loan_candidates']} (ready now: {s['loan_ready_now']})")
    lines.append(f"- financing signal candidates: {s['financing_signal_candidates']}")
    lines.append(f"- scan contract watchlist: {s['scan_contract_watchlist']}")
    lines.append("")

    lines.append("## Contract Candidates")
    contract_candidates = payload["contract_candidates"]
    if contract_candidates:
        for c in contract_candidates:
            blockers = "; ".join(c.get("blockers") or []) or "none"
            lines.append(
                "- "
                f"{c.get('program_id')} | {c.get('program')} | state={c.get('state')} | "
                f"ready={c.get('ready')} | deadline={c.get('deadline')} | "
                f"days_remaining={c.get('days_remaining')} | portal={c.get('portal_url')} | "
                f"blockers={blockers}"
            )
    else:
        lines.append("- none in current queue snapshot")
    lines.append("")

    lines.append("## Loan Candidates")
    loan_candidates = payload["loan_candidates"]
    if loan_candidates:
        for c in loan_candidates:
            blockers = "; ".join(c.get("blockers") or []) or "none"
            lines.append(
                "- "
                f"{c.get('program_id')} | {c.get('program')} | state={c.get('state')} | "
                f"ready={c.get('ready')} | deadline={c.get('deadline')} | "
                f"days_remaining={c.get('days_remaining')} | portal={c.get('portal_url')} | "
                f"blockers={blockers}"
            )
    else:
        lines.append("- none found in current federal queue (no explicit loan opportunity_type and no loan keyword matches)")
    lines.append("")

    lines.append("## Financing Signal Candidates (Not Loans)")
    signal_candidates = payload["financing_signal_candidates"]
    if signal_candidates:
        for c in signal_candidates:
            lines.append(
                "- "
                f"{c.get('program_id')} | {c.get('program')} | type={c.get('opportunity_type')} | "
                f"deadline={c.get('deadline')} | portal={c.get('portal_url')}"
            )
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Fill Workflow")
    lines.append("- 1) Open submit_howto from the selected row.")
    lines.append("- 2) Use submission_packet fields directly in the external portal.")
    lines.append("- 3) Capture confirmation evidence (timestamp + confirmation id) before state changes.")
    lines.append("- 4) Mark submitted only after confirmation artifact exists.")
    return "\n".join(lines)


def _build_markdown_investor(email_pack: dict) -> str:
    km = email_pack["key_metrics"]
    lines: list[str] = []
    lines.append(f"# Investor Response Email Pack ({email_pack['generated_utc']})")
    lines.append("")
    lines.append("## Metrics Context")
    lines.append(f"- queue_total: {km['queue_total']}")
    lines.append(f"- queue_approved: {km['queue_approved']}")
    lines.append(f"- ready_total: {km['ready_total']}")
    lines.append(f"- blocked_approved: {km['blocked_approved']}")
    lines.append("")

    for template in email_pack["templates"]:
        lines.append(f"## Template: {template['id']}")
        lines.append(f"Subject: {template['subject']}")
        lines.append("")
        lines.append(template["body"].strip())
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    queue = _load_json(QUEUE_PATH)
    batch = _load_json(BATCH_PATH)
    scan = _load_json(SCAN_PATH)
    profile = load_application_profile()

    pre_map = {
        str(item.get("grant_id")): item
        for item in batch.get("items", [])
        if item and item.get("grant_id")
    }

    contract_candidates: list[dict] = []
    loan_candidates: list[dict] = []
    financing_signal_candidates: list[dict] = []

    for item in queue.get("items", []):
        text = " ".join(
            str(item.get(k) or "")
            for k in ("program_id", "program", "agency", "opportunity_type", "url")
        )
        opp_type = str(item.get("opportunity_type") or "").lower()

        is_contract = opp_type == "contract" or bool(CONTRACT_RX.search(text))
        is_loan = opp_type == "loan" or bool(LOAN_RX.search(text))
        is_finance_signal = (not is_loan) and bool(FINANCE_SIGNAL_RX.search(text))

        if not (is_contract or is_loan or is_finance_signal):
            continue

        pre = pre_map.get(str(item.get("program_id")))
        if pre:
            deadline_obj = pre.get("deadline") or {}
            deadline = deadline_obj.get("deadline") or item.get("deadline_typical")
            days_remaining = deadline_obj.get("days_remaining")
            ready = bool(pre.get("ready"))
            blockers = list(pre.get("blockers") or [])
            portal_url = pre.get("portal_url") or item.get("url")
            submission_packet = pre.get("submission_packet")
            submit_howto = pre.get("submit_howto")
        else:
            deadline = item.get("deadline_typical")
            days_remaining = None
            ready = None
            blockers = []
            portal_url = item.get("url")
            submission_packet = None
            submit_howto = None

        if days_remaining is None:
            days_remaining = _parse_days_remaining(item.get("deadline_typical"))

        row = {
            "program_id": item.get("program_id"),
            "state": item.get("state"),
            "score": item.get("score"),
            "agency": item.get("agency"),
            "program": item.get("program"),
            "opportunity_type": item.get("opportunity_type"),
            "source": item.get("source"),
            "ceiling_usd": item.get("ceiling_usd"),
            "deadline": deadline,
            "days_remaining": days_remaining,
            "ready": ready,
            "blockers": blockers,
            "portal_url": portal_url,
            "source_url": item.get("url"),
            "opportunity_id": item.get("opportunity_id"),
            "opportunity_number": item.get("opp_num"),
            "submission_packet": submission_packet,
            "submit_howto": submit_howto,
        }

        if is_loan:
            loan_candidates.append(row)
        elif is_contract:
            contract_candidates.append(row)
        else:
            financing_signal_candidates.append(row)

    contract_candidates.sort(key=_sort_key)
    loan_candidates.sort(key=_sort_key)
    financing_signal_candidates.sort(key=_sort_key)

    scan_contract_watchlist: list[dict] = []
    for top in scan.get("top") or []:
        src = (top or {}).get("source_metadata") or {}
        if str(src.get("opportunity_type") or "").lower() != "contract":
            continue
        opp_num = src.get("opp_num")
        scan_contract_watchlist.append(
            {
                "id": top.get("id"),
                "program": top.get("program"),
                "agency": top.get("agency"),
                "deadline_typical": top.get("deadline_typical"),
                "source": src.get("source"),
                "opportunity_number": opp_num,
                "opportunity_id": src.get("opportunity_id"),
                "award_ceiling_usd": src.get("award_ceiling_usd"),
                "url": f"https://www.grants.gov/search-results-detail/{opp_num}" if opp_num else None,
            }
        )

    generated_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    contract_loan_pack = {
        "generated_utc": generated_utc,
        "scope": "contract + loan opportunity extraction from approved federal queue and latest preflight packets",
        "evidence_paths": {
            "queue_index": "out/grants/_queue/index.json",
            "preflight_batch": "out/ops/federal_grant_batch_fill_latest.json",
            "opportunity_scan": "out/grants/_queue/opportunity_scan.json",
        },
        "queue_snapshot": {
            "total": queue.get("n_total"),
            "approved": queue.get("n_approved"),
            "draft": queue.get("n_draft"),
            "submitted": queue.get("n_submitted"),
        },
        "summary": {
            "contract_candidates": len(contract_candidates),
            "contract_ready_now": sum(1 for row in contract_candidates if row.get("ready") is True),
            "loan_candidates": len(loan_candidates),
            "loan_ready_now": sum(1 for row in loan_candidates if row.get("ready") is True),
            "financing_signal_candidates": len(financing_signal_candidates),
            "scan_contract_watchlist": len(scan_contract_watchlist),
        },
        "contract_candidates": contract_candidates,
        "loan_candidates": loan_candidates,
        "financing_signal_candidates": financing_signal_candidates,
        "scan_contract_watchlist": scan_contract_watchlist,
        "filler_notes": [
            "For each candidate, use submit_howto and submission_packet to complete portal filing.",
            "Do not mark as submitted until external portal confirmation is captured.",
            "Loan lane is empty in current federal queue; expand discovery scope if loan products are required.",
        ],
    }

    contract_json_ts = OPS_DIR / f"contract_loan_opportunity_pack_{generated_utc}.json"
    contract_md_ts = OPS_DIR / f"contract_loan_opportunity_pack_{generated_utc}.md"
    contract_json_latest = OPS_DIR / "contract_loan_opportunity_pack_latest.json"
    contract_md_latest = OPS_DIR / "contract_loan_opportunity_pack_latest.md"

    _write_json(contract_json_ts, contract_loan_pack)
    _write_json(contract_json_latest, contract_loan_pack)

    contract_md_text = _build_markdown_contract_loan(contract_loan_pack)
    contract_md_ts.write_text(contract_md_text, encoding="utf-8")
    contract_md_latest.write_text(contract_md_text, encoding="utf-8")

    company_name = profile.get("company", {}).get("dba", "LumenCore / LumaTrader")
    founder_name = profile.get("pi", {}).get("name", "Robert BabyRay Ashworth")
    batch_results = batch.get("results", {})

    email_pack = {
        "generated_utc": generated_utc,
        "scope": "investor outbound and reply templates tied to current grant execution state",
        "evidence_paths": {
            "readiness_report": "out/ops/federal_grant_batch_fill_latest.json",
            "queue_index": "out/grants/_queue/index.json",
            "contract_loan_pack": "out/ops/contract_loan_opportunity_pack_latest.json",
        },
        "key_metrics": {
            "queue_total": queue.get("n_total"),
            "queue_approved": queue.get("n_approved"),
            "ready_total": batch_results.get("n_ready_total"),
            "blocked_approved": batch_results.get("n_blocked_approved"),
        },
        "templates": [
            {
                "id": "investor_short_update",
                "subject": "Quick update: federal pipeline + submission velocity",
                "body": (
                    f"Hi [Investor Name],\n\n"
                    f"Quick update from {company_name}:\n"
                    f"- Federal queue is now fully approved at {queue.get('n_approved')} opportunities.\n"
                    f"- Current preflight run shows {batch_results.get('n_ready_total')} ready-to-submit opportunities.\n"
                    "- We completed another full batch truth pass and now have deterministic submission packets for each approved item.\n\n"
                    "Execution status this session:\n"
                    "- AI Builder submission is complete.\n"
                    "- Dream Makers is fully drafted in Skip (2/2 answers complete); final external portal submit is pending partner-site confirmation.\n"
                    "- Verizon lanes are queued, but both require Verizon Digital Ready account-gated external submission.\n\n"
                    "If useful, I can send a 1-page investor brief with: (1) current live readiness counts, (2) top near-deadline opportunities, and (3) next 7-day execution plan.\n\n"
                    f"Best,\n{founder_name}\n"
                ),
            },
            {
                "id": "reply_to_interested_investor",
                "subject": "Re: interest in LumenCore / LumaTrader - next diligence packet",
                "body": (
                    "Hi [Investor Name],\n\n"
                    "Thank you for the interest. Here is the current operating snapshot:\n"
                    f"- {queue.get('n_approved')} approved federal opportunities in queue\n"
                    f"- {batch_results.get('n_ready_total')} currently ready for submission in latest preflight\n"
                    "- End-to-end submission packet artifacts generated for approved items\n\n"
                    "What we can provide immediately:\n"
                    "1. Evidence-backed readiness report (JSON + MD)\n"
                    "2. Priority submission queue by deadline\n"
                    "3. External-portal execution log as submissions are confirmed\n\n"
                    "If you share your preferred diligence format, I can return a tailored packet today (technical, commercial, and execution-risk sections).\n\n"
                    f"Best,\n{founder_name}\n"
                ),
            },
            {
                "id": "follow_up_no_reply",
                "subject": "Following up: execution evidence + near-term milestones",
                "body": (
                    "Hi [Investor Name],\n\n"
                    "Following up in case this got buried.\n\n"
                    "We have advanced the stack to a clean execution posture:\n"
                    f"- {queue.get('n_approved')} opportunities approved\n"
                    f"- {batch_results.get('n_ready_total')} submission-ready in latest federal preflight\n"
                    "- Submission artifacts and evidence paths updated for immediate filing\n\n"
                    "Near-term milestone window:\n"
                    "- Complete external partner-site submissions for the highest-fit due-soon opportunities\n"
                    "- Convert ready federal queue items to submitted with confirmation evidence\n"
                    "- Deliver a concise operating memo with before/after execution counts\n\n"
                    "If timing is right, I can send the condensed memo and open items list.\n\n"
                    f"Best,\n{founder_name}\n"
                ),
            },
        ],
    }

    investor_json_ts = OPS_DIR / f"investor_response_email_pack_{generated_utc}.json"
    investor_md_ts = OPS_DIR / f"investor_response_email_pack_{generated_utc}.md"
    investor_json_latest = OPS_DIR / "investor_response_email_pack_latest.json"
    investor_md_latest = OPS_DIR / "investor_response_email_pack_latest.md"

    _write_json(investor_json_ts, email_pack)
    _write_json(investor_json_latest, email_pack)

    investor_md_text = _build_markdown_investor(email_pack)
    investor_md_ts.write_text(investor_md_text, encoding="utf-8")
    investor_md_latest.write_text(investor_md_text, encoding="utf-8")

    print(f"[ok] {contract_json_ts.as_posix()}")
    print(f"[ok] {contract_md_ts.as_posix()}")
    print(f"[ok] {investor_json_ts.as_posix()}")
    print(f"[ok] {investor_md_ts.as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
