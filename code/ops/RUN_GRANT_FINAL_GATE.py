from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
OUT_GATE = OUT_OPS / "grant_final_gate"
APP_PACKETS = ROOT / "out" / "grants" / "application_packets"
APPROVED_ROOT = ROOT / "out" / "grants" / "_approved"

REQUIRED_DOCS = [
    "application.json",
    "application.md",
    "technical_volume.md",
    "commercialization_plan.md",
    "cover_letter.md",
    "budget.json",
    "eligibility_report.json",
    "evidence_manifest.json",
    "manifest.sha256.json",
    "approval_state.json",
    "submission_packet.json",
    "SUBMIT_HOWTO.md",
]

CRITICAL_PLACEHOLDER_DOCS = {
    "application.md",
    "technical_volume.md",
    "commercialization_plan.md",
    "cover_letter.md",
}

PLACEHOLDER_PATTERNS = [
    "TO_BE_FILLED",
    "GRANT##########",
    "<AOR name>",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except Exception:
        return path.as_posix()


def find_latest_application_packet(opp_num: str) -> Path | None:
    if not APP_PACKETS.exists():
        return None
    candidates = sorted(APP_PACKETS.glob(f"*_${opp_num}.json"))
    if not candidates:
        candidates = sorted(APP_PACKETS.glob(f"*_{opp_num}.json"))
    if not candidates:
        return None

    best_path = None
    best_stamp = ""
    for path in candidates:
        payload = load_json(path)
        stamp = ""
        if isinstance(payload, dict):
            stamp = str(payload.get("generated_utc") or "")
        if not stamp:
            stamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        if stamp > best_stamp:
            best_stamp = stamp
            best_path = path
    return best_path


def normalize_opp_slug(opp_num: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", opp_num.strip().lower()).strip("_")


def find_latest_approved_run(opp_num: str) -> Path | None:
    if not APPROVED_ROOT.exists():
        return None
    slug = normalize_opp_slug(opp_num)
    roots = [p for p in APPROVED_ROOT.iterdir() if p.is_dir() and slug in p.name.lower()]
    if not roots:
        return None

    run_candidates: list[Path] = []
    for root in roots:
        for child in root.iterdir():
            if child.is_dir():
                run_candidates.append(child)

    if not run_candidates:
        return None
    return sorted(run_candidates, key=lambda p: p.name)[-1]


def parse_us_date(value: str) -> datetime | None:
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](20\d{2})", value or "")
    if not m:
        return None
    try:
        return datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)), tzinfo=timezone.utc)
    except Exception:
        return None


def extract_placeholder_hits(text: str) -> list[str]:
    hits: list[str] = []
    upper = text.upper()
    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.upper() in upper:
            hits.append(pattern)
    return hits


def document_review(path: Path) -> dict[str, Any]:
    exists = path.exists()
    row: dict[str, Any] = {
        "path": rel(path),
        "exists": exists,
        "bytes": 0,
        "sha256": "",
        "line_count": 0,
        "placeholder_hits": [],
    }
    if not exists:
        return row

    st = path.stat()
    row["bytes"] = int(st.st_size)
    row["sha256"] = sha256_file(path)

    if path.suffix.lower() in {".md", ".json", ".txt"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
        row["line_count"] = len(text.splitlines())
        row["placeholder_hits"] = extract_placeholder_hits(text)

    return row


def verify_manifest(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.sha256.json"
    payload = load_json(manifest_path)

    failures: list[str] = []
    checked = 0
    listed = 0
    if not isinstance(payload, dict):
        return {
            "status": "FAIL",
            "checked": 0,
            "listed": 0,
            "failures": ["manifest.sha256.json missing or invalid"],
        }

    files = payload.get("files")
    if not isinstance(files, dict):
        return {
            "status": "FAIL",
            "checked": 0,
            "listed": 0,
            "failures": ["manifest.sha256.json missing files map"],
        }

    for name, row in files.items():
        listed += 1
        if not isinstance(row, dict):
            failures.append(f"manifest row malformed: {name}")
            continue
        target = run_dir / name
        expected = str(row.get("sha256") or "")
        if not target.exists():
            failures.append(f"manifest file missing: {name}")
            continue
        checked += 1
        actual = sha256_file(target)
        if actual != expected:
            failures.append(f"manifest hash mismatch: {name}")

    return {
        "status": "PASS" if not failures else "FAIL",
        "checked": checked,
        "listed": listed,
        "failures": failures,
    }


def build_gate(opp_num: str) -> dict[str, Any]:
    packet_path = find_latest_application_packet(opp_num)
    run_dir = find_latest_approved_run(opp_num)

    blockers: list[str] = []
    warnings: list[str] = []

    if packet_path is None:
        blockers.append(f"No application packet found for {opp_num}")
    if run_dir is None:
        blockers.append(f"No approved run directory found for {opp_num}")

    packet = load_json(packet_path) if packet_path else None

    docs_review: list[dict[str, Any]] = []
    if run_dir is not None:
        for name in REQUIRED_DOCS:
            docs_review.append(document_review(run_dir / name))

    missing_docs = [r["path"] for r in docs_review if not r.get("exists")]
    if missing_docs:
        blockers.append(f"Missing required packet docs: {missing_docs}")

    for row in docs_review:
        path_rel = str(row.get("path") or "")
        name = Path(path_rel).name if path_rel else ""
        hits = row.get("placeholder_hits", [])
        if name in CRITICAL_PLACEHOLDER_DOCS and isinstance(hits, list) and hits:
            blockers.append(f"Placeholder tokens remain in {name}: {hits}")
        elif isinstance(hits, list) and hits:
            warnings.append(f"Placeholder tokens remain in {name}: {hits}")

    approval_state = {}
    if run_dir is not None:
        raw_state = load_json(run_dir / "approval_state.json")
        if isinstance(raw_state, dict):
            approval_state = raw_state

    state = str(approval_state.get("state") or "").strip().lower()
    if state != "approved":
        blockers.append(f"approval_state must be approved, found: {state or 'missing'}")

    manifest_check = verify_manifest(run_dir) if run_dir is not None else {
        "status": "FAIL",
        "checked": 0,
        "listed": 0,
        "failures": ["run_dir missing"],
    }
    if manifest_check.get("status") != "PASS":
        blockers.append(f"manifest verification failed: {manifest_check.get('failures', [])}")

    submission_packet = load_json(run_dir / "submission_packet.json") if run_dir is not None else None
    if isinstance(submission_packet, dict):
        pkt_state = str(submission_packet.get("approval_state") or "")
        if pkt_state and pkt_state.lower() != state:
            warnings.append(
                "submission_packet approval_state differs from approval_state.json; regenerate submission kit before portal submit"
            )

    close_date = ""
    if isinstance(packet, dict):
        opp = packet.get("opportunity", {}) if isinstance(packet.get("opportunity"), dict) else {}
        close_date = str(opp.get("close_date") or "")

    parsed_deadline = parse_us_date(close_date)
    if parsed_deadline is None:
        warnings.append(f"Unable to parse close_date: {close_date or 'missing'}")
    else:
        days_remaining = (parsed_deadline.date() - datetime.now(timezone.utc).date()).days
        if days_remaining < 0:
            blockers.append(f"Opportunity appears expired based on close_date {close_date}")
        elif days_remaining == 0:
            warnings.append("Deadline appears to be today; submit immediately with AOR")
        elif days_remaining <= 2:
            warnings.append(f"Deadline is near ({days_remaining} days remaining)")

    applicant_checks = {
        "uei_present": False,
        "ein_present": False,
        "sam_active": False,
    }
    if isinstance(packet, dict):
        org = packet.get("organization", {}) if isinstance(packet.get("organization"), dict) else {}
        applicant_checks["uei_present"] = bool(str(org.get("uei") or "").strip())
        applicant_checks["ein_present"] = bool(str(org.get("ein") or "").strip())
        applicant_checks["sam_active"] = bool(org.get("sam_registered") is True)

    if not applicant_checks["uei_present"]:
        blockers.append("UEI missing in organization block")
    if not applicant_checks["ein_present"]:
        blockers.append("EIN missing in organization block")
    if not applicant_checks["sam_active"]:
        blockers.append("SAM registration is not active in packet")

    decision = "APPROVED" if not blockers else "BLOCKED"
    gate = {
        "generated_utc": now_iso(),
        "scope": "grant_final_gate",
        "schema": "grant_final_gate_v1",
        "opp_num": opp_num,
        "decision": decision,
        "blockers": blockers,
        "warnings": warnings,
        "application_packet_path": rel(packet_path) if packet_path else "",
        "approved_run_dir": rel(run_dir) if run_dir else "",
        "documents_reviewed": docs_review,
        "manifest_verification": manifest_check,
        "approval_state": approval_state,
        "applicant_checks": applicant_checks,
    }
    gate_material = dict(gate)
    gate["final_gate_signature_sha256"] = canonical_sha256(gate_material)
    return gate


def render_gate_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Grant Final Gate")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Opportunity: {payload.get('opp_num', '')}")
    lines.append(f"Decision: {payload.get('decision', '')}")
    lines.append(f"Gate Signature SHA256: {payload.get('final_gate_signature_sha256', '')}")
    lines.append("")

    blockers = payload.get("blockers", [])
    lines.append("## Blockers")
    lines.append("")
    if blockers:
        for b in blockers:
            lines.append(f"- {b}")
    else:
        lines.append("- none")
    lines.append("")

    warnings = payload.get("warnings", [])
    lines.append("## Warnings")
    lines.append("")
    if warnings:
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Documents Reviewed")
    lines.append("")
    for row in payload.get("documents_reviewed", []):
        lines.append(
            f"- {row.get('path','')} | exists={row.get('exists', False)} | bytes={row.get('bytes', 0)} | sha256={row.get('sha256', '')}"
        )
    lines.append("")

    manifest = payload.get("manifest_verification", {}) if isinstance(payload, dict) else {}
    lines.append("## Manifest Verification")
    lines.append("")
    lines.append(f"- status: {manifest.get('status', '')}")
    lines.append(f"- listed: {manifest.get('listed', 0)}")
    lines.append(f"- checked: {manifest.get('checked', 0)}")
    for f in manifest.get("failures", []):
        lines.append(f"- failure: {f}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any]) -> dict[str, Path]:
    OUT_GATE.mkdir(parents=True, exist_ok=True)
    tag = now_tag()
    opp_slug = normalize_opp_slug(str(payload.get("opp_num") or "unknown"))

    json_ts = OUT_GATE / f"grant_final_gate_{opp_slug}_{tag}.json"
    md_ts = OUT_GATE / f"grant_final_gate_{opp_slug}_{tag}.md"
    json_latest = OUT_GATE / f"grant_final_gate_{opp_slug}_latest.json"
    md_latest = OUT_GATE / f"grant_final_gate_{opp_slug}_latest.md"

    json_latest_global = OUT_GATE / "grant_final_gate_latest.json"
    md_latest_global = OUT_GATE / "grant_final_gate_latest.md"

    json_text = json.dumps(payload, indent=2)
    md_text = render_gate_markdown(payload)

    json_ts.write_text(json_text, encoding="utf-8")
    md_ts.write_text(md_text, encoding="utf-8")
    json_latest.write_text(json_text, encoding="utf-8")
    md_latest.write_text(md_text, encoding="utf-8")
    json_latest_global.write_text(json_text, encoding="utf-8")
    md_latest_global.write_text(md_text, encoding="utf-8")

    return {
        "json_ts": json_ts,
        "md_ts": md_ts,
        "json_latest": json_latest,
        "md_latest": md_latest,
        "json_latest_global": json_latest_global,
        "md_latest_global": md_latest_global,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run final gate review for a selected grant package.")
    parser.add_argument("--opp-num", default="DE-FOA-0003539")
    parser.add_argument("--strict", action="store_true", help="Return non-zero if decision is BLOCKED.")
    args = parser.parse_args()

    gate = build_gate(args.opp_num)
    paths = write_outputs(gate)

    print(f"GRANT_FINAL_GATE_DECISION={gate.get('decision', '')}")
    print(f"GRANT_FINAL_GATE_SIGNATURE={gate.get('final_gate_signature_sha256', '')}")
    print(f"GRANT_FINAL_GATE_JSON={paths['json_latest']}")
    print(f"GRANT_FINAL_GATE_MD={paths['md_latest']}")

    if args.strict and str(gate.get("decision") or "") != "APPROVED":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
