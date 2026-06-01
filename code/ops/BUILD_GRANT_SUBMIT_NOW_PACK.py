"""BUILD_GRANT_SUBMIT_NOW_PACK.py

Innovation pass on the grant pipeline:
- Reads out/ops/grant_submit_lanes/grant_submit_lanes_latest.json
- Drops EXPIRED tickets (close_date already passed)
- Sorts remaining APPROVED lanes by urgency (days_left ascending)
- For each, emits a focused single-ticket markdown brief with:
    * one-click submit URL
    * abstract + project narrative + budget justification + key personnel
    * ready-to-copy "mark submitted" command
- Emits a top-level SUBMIT_NOW.md index with the urgent action list and
  a SUBMIT_NOW.json for downstream automation.

Deterministic outputs go under:
  out/ops/grant_submit_now/<UTC-tag>/
  out/ops/grant_submit_now/SUBMIT_NOW.md   (latest pointer)
  out/ops/grant_submit_now/SUBMIT_NOW.json (latest pointer)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
LANES_LATEST = OUT_OPS / "grant_submit_lanes" / "grant_submit_lanes_latest.json"
TICKETS_DIR = OUT_OPS / "grant_submit_lanes" / "tickets"
PACK_ROOT = OUT_OPS / "grant_submit_now"


def _parse_close(value: str):
    if not value:
        return None
    s = str(value).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _load_ticket_snapshot(ticket_id: str) -> dict:
    path = TICKETS_DIR / f"{ticket_id}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _section(title: str, body) -> str:
    if body is None:
        body = ""
    if isinstance(body, (dict, list)):
        body = json.dumps(body, indent=2, ensure_ascii=False)
    body = str(body).strip()
    if not body:
        return ""
    return f"## {title}\n\n{body}\n\n"


def _render_ticket_md(rec: dict, snapshot: dict) -> str:
    opp = snapshot.get("opportunity", {}) or {}
    org = snapshot.get("organization", {}) or {}
    contacts = snapshot.get("contacts", {}) or {}
    days_left = rec.get("days_left")
    days_str = f"{days_left}d" if isinstance(days_left, int) else "?"
    md = []
    md.append(f"# {rec['ticket_id']} — {rec['title']}\n")
    md.append(f"- Channel: `{rec.get('channel','')}`")
    md.append(f"- Opportunity #: `{rec.get('opp_num','')}`")
    md.append(f"- Close date: **{rec.get('close_date','')}**  (T-{days_str})")
    md.append(f"- Submit URL: <{rec.get('submit_url','')}>")
    md.append(f"- Launch (PowerShell): `start \"\" \"{rec.get('submit_url','')}\"`")
    md.append("")
    md.append("**Mark submitted command:**")
    md.append(
        "```pwsh\npython code/grant_hunter_v2.py submitted "
        f"--ticket {rec['ticket_id']} --tracking-id <TRACKING_ID> --by \"Robert Ashworth\"\n```"
    )
    md.append("")
    md.append(_section("Abstract", snapshot.get("abstract")))
    md.append(_section("Project Narrative", snapshot.get("project_narrative")))
    md.append(_section("Statement of Need", snapshot.get("statement_of_need")))
    md.append(_section("Expected Outcomes", snapshot.get("expected_outcomes")))
    md.append(_section("Budget Narrative", snapshot.get("budget_narrative")))
    bt = snapshot.get("budget_totals")
    if bt:
        md.append(_section("Budget Totals", bt))
    kp = snapshot.get("key_personnel")
    if kp:
        md.append(_section("Key Personnel", kp))
    ec = snapshot.get("evaluation_criteria_responses")
    if ec:
        md.append(_section("Evaluation Criteria Responses", ec))
    md.append(_section("Organization", org))
    md.append(_section("Contacts", contacts))
    md.append(_section("Opportunity Metadata", opp))
    return "\n".join(md)


def main(argv: list[str]) -> int:
    if not LANES_LATEST.exists():
        print(f"ERROR: {LANES_LATEST} not found. Run grant_hunter_v2 submit-lanes first.")
        return 2

    lanes_doc = json.loads(LANES_LATEST.read_text(encoding="utf-8"))
    items = []
    if isinstance(lanes_doc, dict):
        for key in ("lanes", "matched_tickets", "tickets"):
            v = lanes_doc.get(key)
            if isinstance(v, list):
                items = v
                break
        if not items:
            for v in lanes_doc.values():
                if isinstance(v, list) and v and isinstance(v[0], dict) and "ticket_id" in v[0]:
                    items = v
                    break
    if not items:
        print("ERROR: no lane items found in lanes file")
        return 3

    today = datetime.now(timezone.utc).date()
    actionable = []
    expired = []
    for it in items:
        cd = (
            it.get("close_date")
            or it.get("deadline")
            or (it.get("opportunity") or {}).get("close_date")
            or ""
        )
        pd = _parse_close(cd)
        rec = {
            "ticket_id": it.get("ticket_id", ""),
            "title": str(
                it.get("title")
                or it.get("opportunity_title")
                or (it.get("opportunity") or {}).get("title", "")
            ),
            "channel": it.get("channel", ""),
            "opp_num": it.get("opp_num") or it.get("opportunity_number", ""),
            "submit_url": it.get("submit_url", ""),
            "close_date": cd,
            "days_left": (pd - today).days if pd else None,
            "score": it.get("score") or it.get("final_score"),
        }
        if pd and pd < today:
            expired.append(rec)
        else:
            actionable.append(rec)

    actionable.sort(
        key=lambda r: (
            r["days_left"] if isinstance(r["days_left"], int) else 999,
            -float(r.get("score") or 0),
        )
    )

    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pack_dir = PACK_ROOT / tag
    pack_dir.mkdir(parents=True, exist_ok=True)
    PACK_ROOT.mkdir(parents=True, exist_ok=True)

    # Per-ticket briefs + auto-attached fresh multi-asset frozen-delta evidence pack
    brief_files = []
    evidence_results: list[dict] = []
    try:
        # Local import to keep this module standalone-runnable
        from BUILD_GRANT_EVIDENCE_DELTA_PACK import (  # type: ignore
            parse_agency_memo, load_ticket_snapshot as _evp_load_snap,
            build_pack as _evp_build, MEMO_PATH as _EVP_MEMO,
            INFRA_DELTAS as _EVP_DELTAS, PACK_ROOT as _EVP_PACK_ROOT,
            FRESHNESS_HOURS_DEFAULT as _EVP_FRESH_DEF,
        )
        _evp_sections = parse_agency_memo(_EVP_MEMO)
        _evp_available = _EVP_DELTAS.exists()
    except Exception as exc:
        print(f"WARN: evidence-pack module unavailable: {exc}")
        _evp_sections = {}
        _evp_available = False

    for rec in actionable:
        snap = _load_ticket_snapshot(rec["ticket_id"])
        md = _render_ticket_md(rec, snap)
        f = pack_dir / f"{rec['ticket_id']}.md"
        f.write_text(md, encoding="utf-8")
        brief_files.append(str(f))
        if _evp_available:
            ticket_for_evp = {
                "ticket_id": rec["ticket_id"],
                "title": rec.get("title", ""),
                "channel": rec.get("channel", ""),
                "opp_num": rec.get("opp_num", ""),
                "agency": (snap.get("opportunity", {}) or {}).get("agency", "") if isinstance(snap, dict) else "",
                "submit_url": rec.get("submit_url", ""),
                "close_date": rec.get("close_date", ""),
                "score": rec.get("score"),
            }
            try:
                res = _evp_build(ticket_for_evp, snap, _evp_sections, _EVP_FRESH_DEF)
                evidence_results.append(res)
            except Exception as exc:
                print(f"WARN: evidence pack failed for {rec['ticket_id']}: {exc}")
                evidence_results.append({"ticket_id": rec["ticket_id"], "error": str(exc)})

    # Top index markdown
    lines = [
        "# GRANT SUBMIT-NOW PACK",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"Source: `{LANES_LATEST.relative_to(ROOT)}`",
        "",
        f"- Actionable: **{len(actionable)}**",
        f"- Expired (filtered out): {len(expired)}",
        "",
        "## Action Queue (urgency ascending)",
        "",
        "| T- | Ticket | Channel | Opp # | Title | Submit URL |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in actionable:
        days = r["days_left"]
        days_s = f"{days}d" if isinstance(days, int) else "?"
        title = (r["title"] or "")[:80].replace("|", "\\|")
        lines.append(
            f"| {days_s} | `{r['ticket_id']}` | {r['channel']} | "
            f"{r['opp_num']} | {title} | <{r['submit_url']}> |"
        )
    lines.append("")
    lines.append("## Per-Ticket Briefs")
    for r in actionable:
        rel = (pack_dir / f"{r['ticket_id']}.md").relative_to(PACK_ROOT)
        lines.append(f"- [{r['ticket_id']} — {r['title'][:60]}]({rel.as_posix()})")
    lines.append("")
    if evidence_results:
        lines.append("## Fresh Multi-Asset Frozen-Delta Evidence Packs")
        lines.append("")
        lines.append("| Ticket | Freshness | Agency Match | Bundle SHA | Latest Evidence |")
        lines.append("| --- | --- | --- | --- | --- |")
        for r in evidence_results:
            tid = r.get("ticket_id", "")
            if "error" in r:
                lines.append(f"| `{tid}` | ERROR | — | — | {r.get('error','')} |")
                continue
            fresh = (r.get("freshness") or {}).get("state", "?")
            label = r.get("memo_label") or "—"
            sha = (r.get("bundle_sha256") or "")[:16]
            latest = Path(r.get("latest_md") or "")
            try:
                latest_rel = latest.relative_to(ROOT).as_posix() if latest.exists() else ""
            except Exception:
                latest_rel = str(latest)
            link = f"[{latest_rel}](../../../{latest_rel})" if latest_rel else "—"
            lines.append(f"| `{tid}` | {fresh} | {label} | `{sha}` | {link} |")
        lines.append("")
    if expired:
        lines.append("## Expired Tickets (no longer actionable)")
        for r in expired:
            lines.append(f"- `{r['ticket_id']}` closed {r['close_date']} — {r['title'][:60]}")
        lines.append("")

    index_md = "\n".join(lines)
    (pack_dir / "SUBMIT_NOW.md").write_text(index_md, encoding="utf-8")
    (PACK_ROOT / "SUBMIT_NOW.md").write_text(index_md, encoding="utf-8")

    out_json = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_lanes": str(LANES_LATEST),
        "totals": {
            "actionable": len(actionable),
            "expired": len(expired),
            "evidence_packs": len(evidence_results),
        },
        "actionable": actionable,
        "expired": expired,
        "evidence_packs": evidence_results,
        "pack_dir": str(pack_dir),
    }
    (pack_dir / "SUBMIT_NOW.json").write_text(
        json.dumps(out_json, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    (PACK_ROOT / "SUBMIT_NOW.json").write_text(
        json.dumps(out_json, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    print(f"OK  actionable={len(actionable)}  expired_filtered={len(expired)}")
    print(f"    index_md={(PACK_ROOT / 'SUBMIT_NOW.md')}")
    print(f"    index_json={(PACK_ROOT / 'SUBMIT_NOW.json')}")
    print(f"    pack_dir={pack_dir}")
    print()
    print("Next-action shortlist:")
    for r in actionable[:5]:
        days = r["days_left"]
        days_s = f"T-{days}d" if isinstance(days, int) else "T-?"
        print(f"  [{days_s:>5}]  {r['ticket_id']}  {r['title'][:60]}")
        print(f"           {r['submit_url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
