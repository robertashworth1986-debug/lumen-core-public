from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "data" / "public_truth_policy.json"

OUT_OPS = ROOT / "out" / "ops"
OUT_PUBLIC = OUT_OPS / "public_truth"
OUT_IP = ROOT / "out" / "ip_layer"

PUBLIC_LEDGER = OUT_IP / "public_truth_chain_ledger.jsonl"
EMAIL_LATEST = ROOT / "out" / "opportunities" / "email" / "email_opportunities_latest.json"
EMAIL_QUEUE = ROOT / "out" / "opportunities" / "email" / "email_opportunity_queue_latest.json"
EMAIL_DISPATCH_LATEST = ROOT / "out" / "opportunities" / "email" / "outbound_resume_dispatch_latest.json"
EMAIL_RESPONSE_LATEST = ROOT / "out" / "opportunities" / "email" / "email_response_watcher_latest.json"
EMAIL_DISPATCH_MANIFEST = ROOT / "out" / "ops" / "email_resume_dispatcher" / "email_resume_dispatch_manifest_latest.json"
EMAIL_RESPONSE_MANIFEST = ROOT / "out" / "ops" / "email_response_watcher" / "email_response_manifest_latest.json"
APP_CONTEXT_LATEST = ROOT / "out" / "ops" / "application_context" / "application_context_latest.json"
APP_CONTEXT_MANIFEST = ROOT / "out" / "ops" / "application_context" / "application_context_manifest_latest.json"
LINKEDIN_BUILD_LATEST = ROOT / "out" / "ops" / "lumalinkedin_v1_build_latest.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_jsonl_tail(path: Path, n: int = 1) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows[-n:]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")
    tmp.replace(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def prev_entry_sha(path: Path) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for raw in reversed(lines):
        txt = raw.strip()
        if not txt:
            continue
        try:
            row = json.loads(txt)
        except Exception:
            continue
        if isinstance(row, dict):
            return str(row.get("entry_sha256") or "")
    return ""


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def find_first_existing(candidates: list[Path]) -> Path | None:
    for p in candidates:
        if p.exists():
            return p
    return None


def render_markdown(payload: dict[str, Any]) -> str:
    claims = payload.get("claims", {}) if isinstance(payload, dict) else {}
    lines: list[str] = []
    lines.append("# Public Truth Snapshot")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Policy: {payload.get('policy', '')}")
    lines.append(f"Status: {payload.get('status', '')}")
    lines.append("")
    lines.append("## Factual Claims")
    lines.append("")
    lines.append(f"- master_valuation_proxy_usd: {claims.get('master_valuation_proxy_usd', 0)}")
    lines.append(f"- valuation_increment_usd: {claims.get('valuation_increment_usd', 0)}")
    lines.append(f"- autonomous_grant_event_id: {claims.get('autonomous_grant_event_id', '')}")
    lines.append(f"- autonomous_grant_entry_sha256: {claims.get('autonomous_grant_entry_sha256', '')}")
    lines.append(f"- grants_queue_total: {claims.get('grants_queue_total', 0)}")
    lines.append(f"- jobs_queue_total: {claims.get('jobs_queue_total', 0)}")
    lines.append(f"- email_opportunities_new: {claims.get('email_opportunities_new', 0)}")
    lines.append(f"- email_queue_total: {claims.get('email_queue_total', 0)}")
    lines.append(f"- email_resume_dispatch_status: {claims.get('email_resume_dispatch_status', '')}")
    lines.append(f"- email_resume_dispatch_sent_count: {claims.get('email_resume_dispatch_sent_count', 0)}")
    lines.append(f"- email_resume_dispatch_sent_total: {claims.get('email_resume_dispatch_sent_total', 0)}")
    lines.append(f"- email_response_status: {claims.get('email_response_status', '')}")
    lines.append(f"- email_response_new: {claims.get('email_response_new', 0)}")
    lines.append(f"- email_response_matched_outbound_count: {claims.get('email_response_matched_outbound_count', 0)}")
    lines.append(f"- linkedin_refresh_generated_utc: {claims.get('linkedin_refresh_generated_utc', '')}")
    lines.append(f"- application_context_score_pct: {claims.get('application_context_score_pct', 0)}")
    lines.append(f"- application_context_missing_required: {claims.get('application_context_missing_required', 0)}")
    lines.append(f"- opportunities_total: {claims.get('opportunities_total', 0)}")
    lines.append(f"- live_mode: {claims.get('live_mode', '')}")
    lines.append(f"- latest_execution_event_type: {claims.get('latest_execution_event_type', '')}")
    lines.append("")
    lines.append("## Evidence")
    lines.append("")
    for ev in payload.get("evidence", []):
        lines.append(
            f"- {ev.get('path','')} | sha256={ev.get('sha256','')} | bytes={ev.get('bytes',0)} | mtime_utc={ev.get('mtime_utc','')}"
        )
    violations = payload.get("policy_violations", [])
    if violations:
        lines.append("")
        lines.append("## Policy Violations")
        lines.append("")
        for v in violations:
            lines.append(f"- {v}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce current-production truth only for public-facing outputs.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero if policy violations exist.")
    args = parser.parse_args()

    policy_obj = read_json(POLICY_PATH)
    policy = policy_obj if isinstance(policy_obj, dict) else {}
    blocked = [str(x).lower() for x in policy.get("blocked_path_keywords", []) if isinstance(x, str)]
    rules = policy.get("rules") if isinstance(policy.get("rules"), dict) else {}

    rolling_perf = find_first_existing(
        [
            ROOT / "out" / "rolling_performance.json",
            ROOT.parent / "rolling_performance.json",
            ROOT / "rolling_capital" / "rolling_performance.json",
        ]
    )
    exec_events = find_first_existing(
        [
            ROOT / "execution_events.jsonl",
            ROOT / "out" / "execution" / "execution_events.jsonl",
            ROOT.parent / "execution_events.jsonl",
        ]
    )

    sources: dict[str, Path] = {
        "master_valuation": ROOT / "out" / "ops" / "master_valuation" / "master_valuation_latest.json",
        "autonomous_grant_manifest": ROOT / "out" / "ip_layer" / "autonomous_grant_win_manifest_latest.json",
        "luma_explainer_quantified": ROOT / "out" / "ops" / "luma_explainer" / "luma_explainer_quantified_latest.json",
        "investor_metric_readiness": ROOT / "out" / "ops" / "investor_metric_readiness_latest.json",
        "opportunities_tracker": ROOT / "out" / "opportunities" / "tracker.json",
        "grants_queue": ROOT / "out" / "grant_approval_queue.json",
        "jobs_queue": ROOT / "out" / "jobs" / "_queue" / "index.json",
        "email_opportunities_latest": EMAIL_LATEST,
        "email_opportunity_queue": EMAIL_QUEUE,
        "email_resume_dispatch_latest": EMAIL_DISPATCH_LATEST,
        "email_response_latest": EMAIL_RESPONSE_LATEST,
        "email_resume_dispatch_manifest": EMAIL_DISPATCH_MANIFEST,
        "email_response_manifest": EMAIL_RESPONSE_MANIFEST,
        "application_context_latest": APP_CONTEXT_LATEST,
        "application_context_manifest": APP_CONTEXT_MANIFEST,
        "linkedin_build_latest": LINKEDIN_BUILD_LATEST,
    }
    if rolling_perf:
        sources["rolling_performance"] = rolling_perf
    if exec_events:
        sources["execution_events"] = exec_events

    required = [str(x) for x in policy.get("required_artifacts", []) if isinstance(x, str)]

    violations: list[str] = []
    evidence: list[dict[str, Any]] = []
    source_payloads: dict[str, Any] = {}

    if not policy:
        violations.append("missing_or_invalid_policy")
    if policy and not bool(policy.get("enabled", False)):
        violations.append("policy_disabled")
    scope = str(rules.get("public_payload_scope") or "").strip().lower()
    if scope and scope != "current_production":
        violations.append(f"policy_scope_not_current_production:{scope}")

    for name, path in sources.items():
        rel = str(path.relative_to(ROOT)).replace("\\", "/") if path.is_relative_to(ROOT) else str(path).replace("\\", "/")
        lower_rel = rel.lower()
        if any(k in lower_rel for k in blocked):
            violations.append(f"blocked_keyword_path:{rel}")
            continue
        if not path.exists():
            continue
        if path.suffix.lower() == ".jsonl":
            source_payloads[name] = read_jsonl_tail(path, n=3)
        else:
            source_payloads[name] = read_json(path)
        stat = path.stat()
        evidence.append(
            {
                "name": name,
                "path": rel,
                "sha256": sha256_file(path),
                "bytes": stat.st_size,
                "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            }
        )

    for rel in required:
        req_path = ROOT / rel
        rel_norm = rel.replace("\\", "/")
        if not req_path.exists():
            violations.append(f"missing_required_artifact:{rel_norm}")
        if any(k in rel_norm.lower() for k in blocked):
            violations.append(f"blocked_keyword_in_required_artifact:{rel_norm}")

    master_val = source_payloads.get("master_valuation", {})
    if not isinstance(master_val, dict):
        master_val = {}
    grant_manifest = source_payloads.get("autonomous_grant_manifest", {})
    if not isinstance(grant_manifest, dict):
        grant_manifest = {}
    tracker = source_payloads.get("opportunities_tracker", {})
    if not isinstance(tracker, dict):
        tracker = {}
    grants_q = source_payloads.get("grants_queue", {})
    jobs_q = source_payloads.get("jobs_queue", {})
    if not isinstance(jobs_q, dict):
        jobs_q = {}
    email_latest = source_payloads.get("email_opportunities_latest", {})
    if not isinstance(email_latest, dict):
        email_latest = {}
    email_q = source_payloads.get("email_opportunity_queue", {})
    email_dispatch_latest = source_payloads.get("email_resume_dispatch_latest", {})
    if not isinstance(email_dispatch_latest, dict):
        email_dispatch_latest = {}
    email_response_latest = source_payloads.get("email_response_latest", {})
    if not isinstance(email_response_latest, dict):
        email_response_latest = {}
    linkedin_build_latest = source_payloads.get("linkedin_build_latest", {})
    if not isinstance(linkedin_build_latest, dict):
        linkedin_build_latest = {}
    app_context_latest = source_payloads.get("application_context_latest", {})
    if not isinstance(app_context_latest, dict):
        app_context_latest = {}
    rolling = source_payloads.get("rolling_performance", {})
    if not isinstance(rolling, dict):
        rolling = {}
    events_tail = source_payloads.get("execution_events", [])

    latest_event = events_tail[-1] if isinstance(events_tail, list) and events_tail else {}

    claims = {
        "master_valuation_proxy_usd": safe_float(
            (master_val.get("valuation", {}) or {}).get("master_valuation_proxy_usd"),
            0.0,
        ),
        "valuation_increment_usd": safe_float(
            (master_val.get("valuation", {}) or {}).get("valuation_increment_usd"),
            0.0,
        ),
        "grant_and_opportunity_pipeline_value_usd": safe_float(
            (master_val.get("valuation", {}) or {}).get("grant_and_opportunity_pipeline_value_usd"),
            0.0,
        ),
        "grant_finding_and_ranking_system_license_value_usd": safe_float(
            (master_val.get("valuation", {}) or {}).get("grant_finding_and_ranking_system_license_value_usd"),
            0.0,
        ),
        "digital_scout_value_usd": safe_float(
            (master_val.get("valuation", {}) or {}).get("digital_scout_value_usd"),
            0.0,
        ),
        "institutional_trading_system_value_usd": safe_float(
            (master_val.get("valuation", {}) or {}).get("institutional_trading_system_value_usd"),
            0.0,
        ),
        "validated_engine_autonomy_value_usd": safe_float(
            (master_val.get("valuation", {}) or {}).get("validated_engine_autonomy_value_usd"),
            0.0,
        ),
        "autonomous_grant_event_id": str(grant_manifest.get("event_id") or ""),
        "autonomous_grant_entry_sha256": str(grant_manifest.get("entry_sha256") or ""),
        "grants_queue_total": (
            len(grants_q)
            if isinstance(grants_q, list)
            else safe_int(grants_q.get("n_total"), 0)
            if isinstance(grants_q, dict)
            else 0
        ),
        "jobs_queue_total": safe_int(jobs_q.get("n_total"), 0) if isinstance(jobs_q, dict) else 0,
        "email_opportunities_new": safe_int(email_latest.get("new_opportunities"), 0),
        "email_queue_total": len(email_q) if isinstance(email_q, list) else 0,
        "email_resume_dispatch_status": str(email_dispatch_latest.get("status") or ""),
        "email_resume_dispatch_sent_count": safe_int(email_dispatch_latest.get("sent_count"), 0),
        "email_resume_dispatch_sent_total": safe_int(email_dispatch_latest.get("sent_total"), 0),
        "email_response_status": str(email_response_latest.get("status") or ""),
        "email_response_new": safe_int(email_response_latest.get("new_responses"), 0),
        "email_response_matched_outbound_count": safe_int(email_response_latest.get("matched_outbound_count"), 0),
        "linkedin_refresh_generated_utc": str(linkedin_build_latest.get("generated_utc") or ""),
        "application_context_score_pct": safe_float(
            (app_context_latest.get("completeness", {}) or {}).get("score_pct"),
            0.0,
        ),
        "application_context_missing_required": safe_int(
            len((app_context_latest.get("completeness", {}) or {}).get("missing_required_fields") or []),
            0,
        ),
        "opportunities_total": safe_int((tracker.get("opportunities", {}) or {}).get("n_total"), 0) if isinstance(tracker, dict) else 0,
        "live_mode": str(rolling.get("live_now") if isinstance(rolling, dict) else ""),
        "latest_execution_event_type": str(latest_event.get("event") or latest_event.get("event_type") or ""),
        "latest_execution_event_utc": str(latest_event.get("generated_utc") or latest_event.get("timestamp") or ""),
    }

    if bool(rules.get("require_chain_hash_verification", False)):
        if not claims["autonomous_grant_entry_sha256"]:
            violations.append("missing_chain_hash:autonomous_grant_entry_sha256")
    if bool(rules.get("require_frozen_artifacts", False)) and not evidence:
        violations.append("no_evidence_artifacts_collected")
    if bool(rules.get("require_deterministic_latest_alias", False)):
        latest_aliases = [
            EMAIL_LATEST,
            EMAIL_QUEUE,
            EMAIL_DISPATCH_LATEST,
            EMAIL_RESPONSE_LATEST,
            APP_CONTEXT_LATEST,
        ]
        for alias in latest_aliases:
            if not alias.exists():
                violations.append(f"missing_latest_alias:{alias}")

    status = "PASS" if not violations else "FAIL"
    generated_utc = now_iso()
    tag = utc_tag()

    base_payload = {
        "generated_utc": generated_utc,
        "schema": "public_truth_snapshot_v1",
        "policy": str(policy.get("name") or "current_production_truth_only"),
        "status": status,
        "claims": claims,
        "evidence": evidence,
        "policy_violations": violations,
    }

    prev_sha = prev_entry_sha(PUBLIC_LEDGER)
    entry_no_hash = {
        "generated_utc": generated_utc,
        "event_id": f"PUBLIC_TRUTH_{tag}",
        "previous_entry_sha256": prev_sha,
        "status": status,
        "claims": claims,
        "evidence_sha256": {ev["path"]: ev["sha256"] for ev in evidence},
        "policy": base_payload["policy"],
    }
    canonical = json.dumps(entry_no_hash, sort_keys=True, separators=(",", ":")).encode("utf-8")
    entry_sha256 = hashlib.sha256(canonical).hexdigest()
    ledger_row = dict(entry_no_hash)
    ledger_row["entry_sha256"] = entry_sha256
    append_jsonl(PUBLIC_LEDGER, ledger_row)

    base_payload["chain"] = {
        "ledger_path": str(PUBLIC_LEDGER),
        "event_id": ledger_row["event_id"],
        "entry_sha256": entry_sha256,
        "previous_entry_sha256": prev_sha,
    }

    OUT_PUBLIC.mkdir(parents=True, exist_ok=True)
    OUT_IP.mkdir(parents=True, exist_ok=True)

    snap_json = OUT_PUBLIC / f"public_truth_snapshot_{tag}.json"
    snap_md = OUT_PUBLIC / f"public_truth_snapshot_{tag}.md"
    snap_json_latest = OUT_PUBLIC / "public_truth_latest.json"
    snap_md_latest = OUT_PUBLIC / "public_truth_latest.md"

    write_json(snap_json, base_payload)
    write_text(snap_md, render_markdown(base_payload))
    write_json(snap_json_latest, base_payload)
    write_text(snap_md_latest, render_markdown(base_payload))

    manifest = {
        "generated_utc": now_iso(),
        "schema": "public_truth_manifest_v1",
        "policy": base_payload["policy"],
        "status": status,
        "snapshot": str(snap_json),
        "snapshot_sha256": sha256_file(snap_json),
        "markdown": str(snap_md),
        "markdown_sha256": sha256_file(snap_md),
        "chain": base_payload["chain"],
        "violations": violations,
    }
    manifest_tag = OUT_PUBLIC / f"public_truth_manifest_{tag}.json"
    manifest_latest = OUT_PUBLIC / "public_truth_manifest_latest.json"
    write_json(manifest_tag, manifest)
    write_json(manifest_latest, manifest)

    print(f"PUBLIC_TRUTH_STATUS={status}")
    print(f"PUBLIC_TRUTH_LATEST={snap_json_latest}")
    print(f"PUBLIC_TRUTH_MANIFEST={manifest_latest}")
    print(f"PUBLIC_TRUTH_CHAIN_ENTRY={entry_sha256}")

    if args.strict and violations:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
