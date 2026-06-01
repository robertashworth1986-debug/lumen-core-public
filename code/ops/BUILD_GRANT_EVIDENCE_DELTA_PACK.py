"""BUILD_GRANT_EVIDENCE_DELTA_PACK.py

Per-ticket "extra polished multi-asset frozen deltas" evidence packet.

For each grant ticket we are about to fill out / submit, this builds a
fresh, hash-chained packet that combines:

  1. Multi-asset frozen deltas (latest record per sector) from
     out/infra_frozen_deltas.jsonl
  2. The latest frozen-delta truth-chain entry (chain-of-custody hash)
     from out/ops/frozen_delta_truth_chain/frozen_delta_truth_chain_latest.json
  3. Live breadth signals when available (institutional leaderboard /
     kraken multi-tf alpha map / live source status)
  4. Agency-aligned narrative section pulled from
     evidence/agency_alignment_memo.md (the DoD/DARPA/DOE/DHS/NSF/NIST/NASA memo)
  5. SHA-256 manifest covering every file in the bundle

Outputs (per ticket):
  out/ops/grant_evidence_packs/<TICKET>/<TAG>/EVIDENCE.md
  out/ops/grant_evidence_packs/<TICKET>/<TAG>/EVIDENCE.json
  out/ops/grant_evidence_packs/<TICKET>/<TAG>/manifest.sha256.json
  out/ops/grant_evidence_packs/<TICKET>/EVIDENCE_latest.md  (pointer)
  out/ops/grant_evidence_packs/<TICKET>/EVIDENCE_latest.json (pointer)

CLI:
  python code/ops/BUILD_GRANT_EVIDENCE_DELTA_PACK.py --ticket <TICKET_ID> [--ticket ...]
  python code/ops/BUILD_GRANT_EVIDENCE_DELTA_PACK.py --all-actionable

Returns exit code 0 on success, 2 on missing inputs, 3 on no tickets resolved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
OUT_OPS = OUT / "ops"

INFRA_DELTAS = OUT / "infra_frozen_deltas.jsonl"
FROZEN_LEDGER = OUT / "frozen_delta_ledger.jsonl"
TRUTH_CHAIN_LATEST = OUT_OPS / "frozen_delta_truth_chain" / "frozen_delta_truth_chain_latest.json"
SNAPSHOT_LATEST = OUT_OPS / "frozen_delta_truth_chain" / "frozen_delta_snapshot_latest.json"

LANES_LATEST = OUT_OPS / "grant_submit_lanes" / "grant_submit_lanes_latest.json"
TICKETS_DIR = OUT_OPS / "grant_submit_lanes" / "tickets"
APPROVAL_QUEUE = OUT / "grant_approval_queue.json"

MEMO_PATH = ROOT / "evidence" / "agency_alignment_memo.md"

PACK_ROOT = OUT_OPS / "grant_evidence_packs"

LIVE_BREADTH_CANDIDATES = [
    OUT_OPS / "live_breadth_value_panel" / "live_breadth_value_panel_latest.json",
    OUT_OPS / "investor_mission_control" / "investor_mission_control_latest.json",
    OUT / "institutional_leaderboard.csv",
    OUT / "live_source_status.json",
    OUT_OPS / "kraken_multi_tf_alpha_map" / "kraken_multi_tf_alpha_map_latest.json",
]

FRESHNESS_HOURS_DEFAULT = 24

AGENCY_KEYWORD_MAP = [
    # (matcher_regex, agency_section_header, short_label)
    # DARPA must come before DoD: DSO (Defense Sciences Office), I2O, MTO, BTO, STO, TTO are DARPA offices.
    (r"\bdarpa\b|\bhr001\d|defense sciences office|\bdso\b|\bi2o\b|\bmto\b|\bbto\b|\bsto\b|\btto\b", "Defense Advanced Research Projects Agency (DARPA)", "DARPA"),
    (r"\bdod\b|department of defense|defense\b|\bonr\b|\bafrl\b|\barmy\b|\bnavy\b|air force|space force", "Department of Defense (DoD)", "DoD"),
    (r"\bdoe\b|department of energy|arpa-?e|grid modernization|electric grid", "Department of Energy (DOE)", "DOE"),
    (r"\bdhs\b|\bcisa\b|homeland security|critical infrastructure", "Department of Homeland Security (DHS / CISA)", "DHS"),
    (r"\bnsf\b|national science foundation", "National Science Foundation (NSF)", "NSF"),
    (r"\bnist\b|standards and technology", "National Institute of Standards and Technology (NIST)", "NIST"),
    (r"\bnasa\b|aeronautics and space", "NASA (Autonomy and Robotics)", "NASA"),
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_jsonl(path: Path, limit: int | None = None) -> list[dict]:
    out: list[dict] = []
    if not path.exists():
        return out
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        if limit is not None:
            out = out[-limit:]
        return out
    except Exception:
        return out


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _file_age_hours(path: Path) -> float | None:
    if not path.exists():
        return None
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return (datetime.now(timezone.utc) - mtime).total_seconds() / 3600.0
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Memo parsing
# ---------------------------------------------------------------------------

def parse_agency_memo(memo_path: Path) -> dict[str, str]:
    """Split the memo into sections keyed by the H3 header text."""
    if not memo_path.exists():
        return {}
    try:
        text = memo_path.read_text(encoding="utf-8")
    except Exception:
        return {}
    sections: dict[str, str] = {}
    # Split on H3 headers (### ...)
    parts = re.split(r"\n###\s+", text)
    if len(parts) < 2:
        return {}
    for part in parts[1:]:
        head, _, body = part.partition("\n")
        head = head.strip()
        # Trim at next H2/H1 boundary
        body = re.split(r"\n##\s+", body, maxsplit=1)[0].strip()
        sections[head] = body
    return sections


def match_agency_section(
    sections: dict[str, str],
    text_blob: str,
) -> tuple[str | None, str | None, str | None]:
    """Return (matched_header, label, body) for the first agency keyword hit."""
    blob = text_blob.lower()
    for pattern, header, label in AGENCY_KEYWORD_MAP:
        if re.search(pattern, blob):
            body = sections.get(header)
            if body:
                return header, label, body
    return None, None, None


# ---------------------------------------------------------------------------
# Frozen delta gathering
# ---------------------------------------------------------------------------

def gather_multi_asset_deltas(jsonl_path: Path) -> tuple[list[dict], dict]:
    """Read the deltas jsonl and pick the most-recent record per (sector|source)."""
    rows = _load_jsonl(jsonl_path)
    by_key: dict[str, dict] = {}
    for row in rows:
        sector = row.get("sector") or row.get("source") or "unknown"
        src = row.get("source") or "unknown"
        key = f"{sector}|{src}"
        prior = by_key.get(key)
        if prior is None:
            by_key[key] = row
            continue
        if str(row.get("generated_utc", "")) >= str(prior.get("generated_utc", "")):
            by_key[key] = row
    latest = sorted(
        by_key.values(),
        key=lambda r: float(r.get("estimated_hourly_value_usd") or 0.0),
        reverse=True,
    )
    summary = {
        "rows_total": len(rows),
        "asset_keys": len(by_key),
        "sectors": sorted({r.get("sector", "") for r in latest if r.get("sector")}),
        "total_hourly_value_usd": round(
            sum(float(r.get("estimated_hourly_value_usd") or 0.0) for r in latest), 2
        ),
        "total_avoided_loss_usd": round(
            sum(float(r.get("estimated_avoided_loss_usd") or 0.0) for r in latest), 2
        ),
        "trust_tiers": sorted({r.get("trust_tier", "") for r in latest if r.get("trust_tier")}),
    }
    return latest, summary


def gather_live_breadth() -> dict:
    panel: dict[str, Any] = {"sources": []}
    for cand in LIVE_BREADTH_CANDIDATES:
        if cand.exists():
            entry = {
                "path": str(cand.relative_to(ROOT)).replace("\\", "/"),
                "exists": True,
                "bytes": cand.stat().st_size,
                "mtime_utc": datetime.fromtimestamp(cand.stat().st_mtime, tz=timezone.utc).isoformat(),
                "age_hours": round(_file_age_hours(cand) or -1, 2),
            }
            if cand.suffix.lower() == ".json":
                doc = _load_json(cand)
                # Pull a few headline numerics if obvious
                summary = {}
                for key in ("generated_utc", "live_now", "annual_value_signal_usd",
                            "router_edge_pct", "harmonic_win_rate_pct",
                            "measured_sources", "enabled_sources",
                            "valuation_proxy_usd", "top_sector"):
                    if isinstance(doc, dict) and key in doc:
                        summary[key] = doc[key]
                if not summary and isinstance(doc, dict):
                    metrics = doc.get("metrics") or {}
                    for key in ("annual_value_signal_usd", "router_edge_pct",
                                "harmonic_win_rate_pct", "top_sector",
                                "measured_sources", "enabled_sources"):
                        if key in metrics:
                            summary[key] = metrics[key]
                entry["summary"] = summary
            panel["sources"].append(entry)
    panel["resolved_count"] = len(panel["sources"])
    return panel


# ---------------------------------------------------------------------------
# Ticket resolution
# ---------------------------------------------------------------------------

def _normalize_ticket_record(it: dict) -> dict:
    return {
        "ticket_id": it.get("ticket_id", ""),
        "title": str(
            it.get("title")
            or it.get("opportunity_title")
            or (it.get("opportunity") or {}).get("title", "")
        ),
        "channel": it.get("channel", ""),
        "opp_num": it.get("opp_num") or it.get("opportunity_number", ""),
        "agency": it.get("agency")
            or (it.get("opportunity") or {}).get("agency", "")
            or it.get("agency_name", ""),
        "submit_url": it.get("submit_url", ""),
        "close_date": it.get("close_date") or (it.get("opportunity") or {}).get("close_date", ""),
        "score": it.get("score") or it.get("final_score"),
    }


def load_lane_tickets() -> list[dict]:
    if not LANES_LATEST.exists():
        return []
    doc = _load_json(LANES_LATEST)
    items = []
    if isinstance(doc, dict):
        for key in ("lanes", "matched_tickets", "tickets"):
            v = doc.get(key)
            if isinstance(v, list):
                items = v
                break
        if not items:
            for v in doc.values():
                if isinstance(v, list) and v and isinstance(v[0], dict) and "ticket_id" in v[0]:
                    items = v
                    break
    return [_normalize_ticket_record(it) for it in items if it.get("ticket_id")]


def load_ticket_snapshot(ticket_id: str) -> dict:
    p = TICKETS_DIR / f"{ticket_id}.json"
    return _load_json(p)


def filter_actionable(items: list[dict]) -> list[dict]:
    today = datetime.now(timezone.utc).date()
    out = []
    for it in items:
        cd = it.get("close_date", "")
        if not cd:
            out.append(it)
            continue
        parsed = None
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
            try:
                parsed = datetime.strptime(str(cd).strip(), fmt).date()
                break
            except ValueError:
                continue
        if parsed is None or parsed >= today:
            out.append(it)
    return out


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def _fmt_usd(x: Any) -> str:
    try:
        return f"${float(x):,.0f}"
    except Exception:
        return str(x)


def render_evidence_md(
    ticket: dict,
    snapshot: dict,
    deltas: list[dict],
    delta_summary: dict,
    truth_chain: dict,
    breadth: dict,
    memo_section: tuple[str | None, str | None, str | None],
    freshness: dict,
    bundle_sha: str,
) -> str:
    head, label, body = memo_section
    lines: list[str] = []
    lines.append(f"# Evidence Packet — {ticket['ticket_id']}")
    lines.append("")
    lines.append(f"**Title:** {ticket.get('title','')}")
    lines.append(f"**Agency (resolved):** {ticket.get('agency') or label or 'unspecified'}")
    lines.append(f"**Opportunity #:** `{ticket.get('opp_num','')}`  |  **Channel:** `{ticket.get('channel','')}`")
    lines.append(f"**Close date:** {ticket.get('close_date','')}")
    lines.append(f"**Submit URL:** <{ticket.get('submit_url','')}>")
    lines.append("")
    lines.append(f"**Bundle SHA-256:** `{bundle_sha}`")
    lines.append(f"**Generated UTC:** {_utc_now_iso()}")
    lines.append("")

    # Freshness banner
    fresh_state = freshness.get("state", "unknown")
    lines.append(f"**Freshness:** {fresh_state.upper()}  "
                 f"(deltas age: {freshness.get('infra_deltas_age_hours','?')}h, "
                 f"truth-chain age: {freshness.get('truth_chain_age_hours','?')}h)")
    lines.append("")

    # 1. Agency Alignment
    lines.append("## 1. Agency Alignment")
    lines.append("")
    if body:
        lines.append(f"_Excerpt from `evidence/agency_alignment_memo.md` — section: **{head}**_")
        lines.append("")
        lines.append(body)
    else:
        lines.append(
            "_No agency keyword matched. Defaulting to LumenCore™ core position from memo:_"
        )
        lines.append("")
        lines.append(
            "LumenCore™ is a measurement-first architecture that detects instability "
            "earlier than conventional monitoring, quantifies drift and coherence loss, "
            "translates system behavior into operational and economic impact, and enables "
            "simulation-driven optimization before failure occurs."
        )
    lines.append("")

    # 2. Multi-Asset Frozen Deltas
    lines.append("## 2. Multi-Asset Frozen Deltas (live, hash-chained)")
    lines.append("")
    lines.append(
        f"- Source: `{INFRA_DELTAS.relative_to(ROOT).as_posix()}`  "
        f"({delta_summary.get('rows_total',0)} rows, "
        f"{delta_summary.get('asset_keys',0)} unique sector|source keys)"
    )
    lines.append(f"- Sectors covered: {', '.join(delta_summary.get('sectors', []) or ['—'])}")
    lines.append(
        f"- Aggregate hourly value signal: "
        f"{_fmt_usd(delta_summary.get('total_hourly_value_usd', 0))}"
    )
    lines.append(
        f"- Aggregate avoided-loss signal: "
        f"{_fmt_usd(delta_summary.get('total_avoided_loss_usd', 0))}"
    )
    lines.append(f"- Trust tiers present: {', '.join(delta_summary.get('trust_tiers', []) or ['—'])}")
    lines.append("")
    lines.append("| Sector | Source | Constraint | Hourly Value | Avoided Loss | Trust |")
    lines.append("| --- | --- | --- | ---: | ---: | --- |")
    for r in deltas[:25]:
        lines.append(
            f"| {r.get('sector','')} | {r.get('source','')} | {r.get('constraint','')} "
            f"| {_fmt_usd(r.get('estimated_hourly_value_usd',0))} "
            f"| {_fmt_usd(r.get('estimated_avoided_loss_usd',0))} "
            f"| {r.get('trust_tier','')} |"
        )
    lines.append("")

    # 3. Truth-chain anchor
    lines.append("## 3. Frozen Delta Truth-Chain Anchor")
    lines.append("")
    if truth_chain:
        lines.append(f"- Run tag: `{truth_chain.get('run_tag','')}`")
        lines.append(f"- Generated UTC: {truth_chain.get('generated_utc','')}")
        lines.append(f"- Previous entry SHA-256: `{truth_chain.get('previous_entry_sha256','')}`")
        lines.append(f"- Entry SHA-256: `{truth_chain.get('entry_sha256','')}`")
        lines.append(f"- Ledger: `{truth_chain.get('ledger_path','')}`")
        metrics = truth_chain.get("metrics") or {}
        if metrics:
            lines.append("")
            lines.append("**Anchored metrics:**")
            for key in (
                "annual_value_signal_usd", "router_edge_pct", "harmonic_win_rate_pct",
                "top_sector", "top_sector_hourly_value_usd",
                "measured_sources", "enabled_sources", "measured_coverage_pct",
                "benchmark_prevented_pct", "valuation_proxy_usd",
                "grants_queue_total", "public_truth_status",
            ):
                if key in metrics:
                    val = metrics[key]
                    if "usd" in key.lower():
                        val = _fmt_usd(val)
                    lines.append(f"  - `{key}` = {val}")
    else:
        lines.append("_Truth-chain latest pointer not found._")
    lines.append("")

    # 4. Live breadth
    lines.append("## 4. Live Breadth Surface")
    lines.append("")
    if breadth.get("resolved_count", 0) == 0:
        lines.append("_No live-breadth artifacts resolved on disk; running on truth-chain anchor only._")
    else:
        lines.append(f"Resolved {breadth['resolved_count']} live-breadth source(s):")
        for s in breadth.get("sources", []):
            lines.append(
                f"- `{s['path']}` — {s['bytes']} bytes, age {s['age_hours']}h"
            )
            summary = s.get("summary") or {}
            if summary:
                for k, v in summary.items():
                    if "usd" in k.lower():
                        v = _fmt_usd(v)
                    lines.append(f"    - `{k}` = {v}")
    lines.append("")

    # 5. Snapshot abstract from ticket if present
    if snapshot:
        lines.append("## 5. Ticket Narrative Snapshot")
        lines.append("")
        for sec_key, sec_title in (
            ("abstract", "Abstract"),
            ("statement_of_need", "Statement of Need"),
            ("expected_outcomes", "Expected Outcomes"),
        ):
            v = snapshot.get(sec_key)
            if v:
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, indent=2, ensure_ascii=False)
                lines.append(f"### {sec_title}")
                lines.append("")
                lines.append(str(v).strip())
                lines.append("")

    # 6. Manifest pointer
    lines.append("## 6. Manifest")
    lines.append("")
    lines.append("See `manifest.sha256.json` for per-file SHA-256 hashes covering this packet.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "_Generated by `code/ops/BUILD_GRANT_EVIDENCE_DELTA_PACK.py`. "
        "Re-run any time before submission to refresh deltas, breadth, and chain anchor._"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_pack(
    ticket: dict,
    snapshot: dict,
    sections: dict[str, str],
    freshness_hours: int,
) -> dict:
    deltas, delta_summary = gather_multi_asset_deltas(INFRA_DELTAS)
    truth_chain = _load_json(TRUTH_CHAIN_LATEST)
    breadth = gather_live_breadth()

    blob = " ".join(str(x) for x in [
        ticket.get("agency", ""),
        ticket.get("title", ""),
        ticket.get("opp_num", ""),
        ticket.get("channel", ""),
        snapshot.get("opportunity", {}) if isinstance(snapshot, dict) else "",
    ])
    memo_match = match_agency_section(sections, blob)

    age_deltas = _file_age_hours(INFRA_DELTAS)
    age_chain = _file_age_hours(TRUTH_CHAIN_LATEST)
    fresh_state = "fresh"
    notes = []
    if age_deltas is None:
        fresh_state = "missing"
        notes.append("infra_frozen_deltas.jsonl missing")
    elif age_deltas > freshness_hours:
        fresh_state = "stale"
        notes.append(f"infra_frozen_deltas.jsonl age {age_deltas:.1f}h > {freshness_hours}h")
    if age_chain is not None and age_chain > freshness_hours:
        if fresh_state == "fresh":
            fresh_state = "partial"
        notes.append(f"truth_chain_latest age {age_chain:.1f}h > {freshness_hours}h")
    freshness = {
        "state": fresh_state,
        "infra_deltas_age_hours": round(age_deltas, 2) if age_deltas is not None else None,
        "truth_chain_age_hours": round(age_chain, 2) if age_chain is not None else None,
        "threshold_hours": freshness_hours,
        "notes": notes,
    }

    tag = _utc_tag()
    pack_dir = PACK_ROOT / ticket["ticket_id"] / tag
    pack_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema": "lumen.grant_evidence_pack/v1",
        "generated_utc": _utc_now_iso(),
        "run_tag": tag,
        "ticket": ticket,
        "memo_match": {
            "header": memo_match[0],
            "label": memo_match[1],
            "matched": memo_match[2] is not None,
        },
        "memo_excerpt": memo_match[2],
        "freshness": freshness,
        "delta_summary": delta_summary,
        "deltas_top": deltas[:50],
        "truth_chain": {
            "run_tag": truth_chain.get("run_tag"),
            "entry_sha256": truth_chain.get("entry_sha256"),
            "previous_entry_sha256": truth_chain.get("previous_entry_sha256"),
            "generated_utc": truth_chain.get("generated_utc"),
            "metrics": truth_chain.get("metrics", {}),
            "ledger_path": truth_chain.get("ledger_path"),
        },
        "live_breadth": breadth,
    }

    # Emit JSON first so we can hash it
    payload_bytes = json.dumps(payload, indent=2, ensure_ascii=False, default=str).encode("utf-8")
    bundle_sha = _sha256_bytes(payload_bytes)
    payload["bundle_sha256"] = bundle_sha

    json_path = pack_dir / "EVIDENCE.json"
    json_path.write_bytes(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str).encode("utf-8")
    )

    md_text = render_evidence_md(
        ticket, snapshot, deltas, delta_summary, truth_chain, breadth,
        memo_match, freshness, bundle_sha,
    )
    md_path = pack_dir / "EVIDENCE.md"
    md_path.write_text(md_text, encoding="utf-8")

    # Manifest
    manifest = {
        "schema": "lumen.grant_evidence_manifest/v1",
        "generated_utc": _utc_now_iso(),
        "ticket_id": ticket["ticket_id"],
        "run_tag": tag,
        "bundle_sha256": bundle_sha,
        "files": [],
    }
    for p in (json_path, md_path):
        manifest["files"].append({
            "path_rel": str(p.relative_to(ROOT)).replace("\\", "/"),
            "sha256": _sha256_file(p),
            "bytes": p.stat().st_size,
        })
    # Also hash the source inputs we depended on
    for src in (INFRA_DELTAS, TRUTH_CHAIN_LATEST, SNAPSHOT_LATEST, MEMO_PATH, FROZEN_LEDGER):
        if src.exists():
            manifest["files"].append({
                "path_rel": str(src.relative_to(ROOT)).replace("\\", "/"),
                "sha256": _sha256_file(src),
                "bytes": src.stat().st_size,
                "role": "source",
            })

    manifest_path = pack_dir / "manifest.sha256.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Latest pointers
    latest_dir = PACK_ROOT / ticket["ticket_id"]
    (latest_dir / "EVIDENCE_latest.md").write_text(md_text, encoding="utf-8")
    (latest_dir / "EVIDENCE_latest.json").write_bytes(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str).encode("utf-8")
    )
    (latest_dir / "manifest_latest.sha256.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return {
        "ticket_id": ticket["ticket_id"],
        "pack_dir": str(pack_dir),
        "evidence_md": str(md_path),
        "evidence_json": str(json_path),
        "manifest": str(manifest_path),
        "latest_md": str(latest_dir / "EVIDENCE_latest.md"),
        "bundle_sha256": bundle_sha,
        "freshness": freshness,
        "memo_label": memo_match[1],
        "delta_sectors": delta_summary.get("sectors", []),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build grant evidence delta pack(s)")
    parser.add_argument("--ticket", action="append", default=[],
                        help="Ticket ID (repeatable)")
    parser.add_argument("--all-actionable", action="store_true",
                        help="Build for every non-expired ticket in submit-lanes")
    parser.add_argument("--freshness-hours", type=int, default=FRESHNESS_HOURS_DEFAULT)
    args = parser.parse_args(argv)

    sections = parse_agency_memo(MEMO_PATH)
    if not sections:
        print(f"WARN: agency memo not parsed at {MEMO_PATH}", file=sys.stderr)

    lane_items = load_lane_tickets()
    by_id = {it["ticket_id"]: it for it in lane_items}

    target_ids: list[str] = []
    if args.all_actionable:
        target_ids = [it["ticket_id"] for it in filter_actionable(lane_items)]
    target_ids.extend(t for t in args.ticket if t not in target_ids)

    if not target_ids:
        print("ERROR: no tickets resolved (use --ticket or --all-actionable)", file=sys.stderr)
        return 3

    if not INFRA_DELTAS.exists():
        print(f"ERROR: {INFRA_DELTAS} missing — cannot build multi-asset deltas", file=sys.stderr)
        return 2

    PACK_ROOT.mkdir(parents=True, exist_ok=True)

    results = []
    for tid in target_ids:
        ticket = by_id.get(tid)
        if ticket is None:
            ticket = {
                "ticket_id": tid,
                "title": "",
                "channel": "",
                "opp_num": "",
                "agency": "",
                "submit_url": "",
                "close_date": "",
                "score": None,
            }
        snap = load_ticket_snapshot(tid)
        # Use snapshot agency if ticket missing
        if not ticket.get("agency"):
            opp = snap.get("opportunity", {}) if isinstance(snap, dict) else {}
            ticket["agency"] = opp.get("agency") or opp.get("agency_name") or ticket.get("agency", "")
        try:
            res = build_pack(ticket, snap, sections, args.freshness_hours)
            results.append(res)
            fr = res["freshness"]["state"]
            print(f"OK  {tid}  freshness={fr}  agency={res.get('memo_label') or '-'}  "
                  f"sectors={len(res.get('delta_sectors') or [])}  "
                  f"sha={res['bundle_sha256'][:12]}")
        except Exception as exc:
            print(f"FAIL {tid}  {exc}", file=sys.stderr)
            results.append({"ticket_id": tid, "error": str(exc)})

    # Top-level index
    index = {
        "schema": "lumen.grant_evidence_pack_index/v1",
        "generated_utc": _utc_now_iso(),
        "freshness_hours": args.freshness_hours,
        "results": results,
    }
    (PACK_ROOT / "EVIDENCE_INDEX_latest.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    md = ["# Grant Evidence Pack Index", "",
          f"Generated UTC: {_utc_now_iso()}",
          f"Freshness threshold: {args.freshness_hours}h",
          "",
          "| Ticket | Freshness | Agency Match | Sectors | Bundle SHA |",
          "| --- | --- | --- | ---: | --- |"]
    for r in results:
        if "error" in r:
            md.append(f"| `{r['ticket_id']}` | ERROR | — | — | — |")
            continue
        md.append(
            f"| `{r['ticket_id']}` | {r['freshness']['state']} | "
            f"{r.get('memo_label') or '—'} | {len(r.get('delta_sectors') or [])} | "
            f"`{r['bundle_sha256'][:16]}` |"
        )
    (PACK_ROOT / "EVIDENCE_INDEX_latest.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    return 0 if all("error" not in r for r in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
