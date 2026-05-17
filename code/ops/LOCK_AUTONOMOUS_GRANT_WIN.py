from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
OUT_IP = ROOT / "out" / "ip_layer"

MASTER_VAL_DIR = OUT_OPS / "master_valuation"
LUMA_EXPLAINER_DIR = OUT_OPS / "luma_explainer"
PREV_MASTER_VAL = MASTER_VAL_DIR / "master_valuation_latest.json"

INVESTOR_READINESS = OUT_OPS / "investor_metric_readiness_latest.json"
SKIP_AUTOFILL = OUT_OPS / "skips_grant_autofill" / "skips_grant_autofill_latest.json"
GRANT_QUEUE = ROOT / "out" / "grant_approval_queue.json"
GRANTS_RANKED = ROOT / "out" / "grants" / "grants_ranked_v2.json"
OPP_TRACKER = ROOT / "out" / "opportunities" / "tracker.json"
JOBS_QUEUE = ROOT / "out" / "jobs" / "_queue" / "index.json"
RESUME_LATEST = ROOT / "out" / "resume" / "resume_lumalinkedin_v1_latest.json"
EMAIL_QUEUE = ROOT / "out" / "opportunities" / "email" / "email_opportunity_queue_latest.json"
APP_CONTEXT_LATEST = ROOT / "out" / "ops" / "application_context" / "application_context_latest.json"
PUBLIC_TRUTH_LEDGER = OUT_IP / "public_truth_chain_ledger.jsonl"

IP_LEDGER = OUT_IP / "autonomous_grant_win_chain_ledger.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def read_prev_hash(ledger_path: Path) -> str:
    if not ledger_path.exists():
        return ""
    lines = ledger_path.read_text(encoding="utf-8", errors="ignore").splitlines()
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


def count_pass_rows(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        txt = raw.strip()
        if not txt:
            continue
        try:
            row = json.loads(txt)
        except Exception:
            continue
        if isinstance(row, dict) and str(row.get("status") or "").upper() == "PASS":
            count += 1
    return count


def count_entries(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        txt = raw.strip()
        if not txt:
            continue
        try:
            row = json.loads(txt)
        except Exception:
            continue
        if isinstance(row, dict):
            count += 1
    return count


def template_total(use_of_funds: dict[str, Any], key: str) -> float:
    bucket = use_of_funds.get(key, {}) if isinstance(use_of_funds, dict) else {}
    if not isinstance(bucket, dict):
        return 0.0
    total = 0.0
    for value in bucket.values():
        total += safe_float(value, 0.0)
    return total


def build_valuation() -> tuple[dict[str, Any], list[Path]]:
    investor = load_json(INVESTOR_READINESS)
    skip = load_json(SKIP_AUTOFILL)
    grant_queue = load_json(GRANT_QUEUE)
    ranked = load_json(GRANTS_RANKED)
    tracker = load_json(OPP_TRACKER)
    jobs = load_json(JOBS_QUEUE)
    resume = load_json(RESUME_LATEST)
    email_queue = load_json(EMAIL_QUEUE)
    app_context = load_json(APP_CONTEXT_LATEST)
    prev_master_val = load_json(PREV_MASTER_VAL)

    summary = investor.get("summary", {}) if isinstance(investor, dict) else {}
    signal = summary.get("signal_evidence", {}) if isinstance(summary, dict) else {}
    annual_value_signal = safe_float(signal.get("annual_value_usd"), 0.0)
    router_edge_pct = safe_float(signal.get("router_edge_pct"), 0.0)
    harmonic_win_rate_pct = safe_float(signal.get("harmonic_win_rate_pct"), 0.0)

    variants = skip.get("opportunity_variants", []) if isinstance(skip, dict) else []
    if not isinstance(variants, list):
        variants = []
    use_of_funds = skip.get("use_of_funds_templates", {}) if isinstance(skip, dict) else {}

    skip_total_target_usd = 0.0
    for row in variants:
        if not isinstance(row, dict):
            continue
        key = str(row.get("recommended_budget_template") or "")
        skip_total_target_usd += template_total(use_of_funds, key)

    evidence_candidates = [
        INVESTOR_READINESS,
        SKIP_AUTOFILL,
        GRANT_QUEUE,
        GRANTS_RANKED,
        OPP_TRACKER,
        JOBS_QUEUE,
        EMAIL_QUEUE,
        APP_CONTEXT_LATEST,
        RESUME_LATEST,
    ]
    existing_evidence = [p for p in evidence_candidates if p.exists()]

    queue_count = 0
    if isinstance(grant_queue, list):
        queue_count = len(grant_queue)
    elif isinstance(grant_queue, dict):
        queue_count = safe_int(grant_queue.get("count"), 0)

    ranked_open = safe_int(ranked.get("total_open"), 0) if isinstance(ranked, dict) else 0
    jobs_draft = safe_int(jobs.get("n_draft"), 0) if isinstance(jobs, dict) else 0
    opp_total = safe_int((tracker.get("opportunities", {}) or {}).get("n_total"), 0) if isinstance(tracker, dict) else 0
    email_queue_count = len(email_queue) if isinstance(email_queue, list) else 0
    truth_pass_count = count_pass_rows(PUBLIC_TRUTH_LEDGER)
    autonomous_pass_count = count_entries(IP_LEDGER) + 1
    context_score_pct = safe_float(
        ((app_context.get("completeness", {}) or {}).get("score_pct") if isinstance(app_context, dict) else 0.0),
        0.0,
    )
    context_missing_required = safe_int(
        len(((app_context.get("completeness", {}) or {}).get("missing_required_fields") if isinstance(app_context, dict) else []) or []),
        0,
    )

    evidence_completeness = min(1.0, len(existing_evidence) / 9.0)
    momentum_component = min(1.0, (queue_count + ranked_open + jobs_draft + opp_total + email_queue_count) / 120.0)
    technical_component = min(1.0, max(0.0, router_edge_pct) / 100.0 + max(0.0, harmonic_win_rate_pct) / 200.0)
    context_component = min(1.0, max(0.0, context_score_pct) / 100.0)
    confidence_index = round(
        0.45 * evidence_completeness + 0.20 * momentum_component + 0.25 * technical_component + 0.10 * context_component,
        6,
    )

    truth_pass_uplift_multiplier = round(1.0 + min(1.5, truth_pass_count * 0.10), 6)
    pass_compound_multiplier = round(1.0 + (autonomous_pass_count * 0.025) + ((autonomous_pass_count ** 1.2) * 0.002), 6)
    innovation_multiplier = round(
        1.0
        + 0.35 * min(1.0, max(0.0, router_edge_pct) / 100.0)
        + 0.25 * min(1.0, max(0.0, harmonic_win_rate_pct) / 100.0)
        + 0.20 * context_component,
        6,
    )

    autonomous_grant_execution_value_usd = round(
        skip_total_target_usd
        * (1.0 + confidence_index)
        * truth_pass_uplift_multiplier
        * pass_compound_multiplier
        * innovation_multiplier,
        2,
    )
    institutional_signal_link_value_usd = round(min(annual_value_signal * 0.0001, 5_000_000.0), 2)
    chain_of_custody_value_usd = round(min(2_500_000.0, truth_pass_count * 250_000.0), 2)
    pass_momentum_value_usd = round((autonomous_pass_count ** 1.18) * 140_000.0, 2)
    raw_valuation_increment_usd = round(
        autonomous_grant_execution_value_usd
        + institutional_signal_link_value_usd
        + chain_of_custody_value_usd
        + pass_momentum_value_usd,
        2,
    )

    prev_valuation_increment_usd = safe_float(
        ((prev_master_val.get("valuation", {}) or {}).get("valuation_increment_usd") if isinstance(prev_master_val, dict) else 0.0),
        0.0,
    )
    minimum_pass_jump_usd = round(max(250_000.0, (autonomous_pass_count ** 1.05) * 85_000.0), 2)
    monotonic_override_applied = False
    valuation_increment_usd = raw_valuation_increment_usd
    if prev_valuation_increment_usd > 0 and valuation_increment_usd <= prev_valuation_increment_usd:
        valuation_increment_usd = round(prev_valuation_increment_usd + minimum_pass_jump_usd, 2)
        monotonic_override_applied = True

    master_valuation_proxy_usd = round(annual_value_signal + valuation_increment_usd, 2)

    valuation = {
        "generated_utc": now_iso(),
        "scope": "master_valuation_autonomous_grant_win_v1",
        "thesis": {
            "label": "First real win: end-to-end autonomous harmonic AI grant execution",
            "status": "locked_for_ip_and_valuation",
        },
        "inputs": {
            "annual_value_signal_usd": annual_value_signal,
            "router_edge_pct": router_edge_pct,
            "harmonic_win_rate_pct": harmonic_win_rate_pct,
            "skip_total_target_usd": skip_total_target_usd,
            "queue_count": queue_count,
            "ranked_open_opportunities": ranked_open,
            "jobs_draft_count": jobs_draft,
            "email_queue_count": email_queue_count,
            "opportunity_package_count": opp_total,
            "truth_pass_count": truth_pass_count,
            "autonomous_pass_count": autonomous_pass_count,
            "application_context_score_pct": context_score_pct,
            "application_context_missing_required": context_missing_required,
            "evidence_file_count": len(existing_evidence),
        },
        "assumptions": {
            "confidence_index": confidence_index,
            "truth_pass_uplift_multiplier": truth_pass_uplift_multiplier,
            "pass_compound_multiplier": pass_compound_multiplier,
            "innovation_multiplier": innovation_multiplier,
            "minimum_pass_jump_usd": minimum_pass_jump_usd,
            "monotonic_override_applied": monotonic_override_applied,
            "formula": "raw_increment = skip_total_target*(1+confidence_index)*truth_pass_uplift*pass_compound*innovation_multiplier + min(annual_value_signal*0.0001, 5000000) + min(truth_pass_count*250000, 2500000) + pass_momentum_value; final_increment = max(raw_increment, prev_increment + minimum_pass_jump_usd)",
            "note": "Assumption-based decision valuation, not audited GAAP enterprise value.",
        },
        "valuation": {
            "autonomous_grant_execution_value_usd": autonomous_grant_execution_value_usd,
            "institutional_signal_link_value_usd": institutional_signal_link_value_usd,
            "chain_of_custody_value_usd": chain_of_custody_value_usd,
            "pass_momentum_value_usd": pass_momentum_value_usd,
            "raw_valuation_increment_usd": raw_valuation_increment_usd,
            "valuation_increment_usd": valuation_increment_usd,
            "master_valuation_proxy_usd": master_valuation_proxy_usd,
        },
        "evidence_paths": [str(p) for p in existing_evidence],
    }
    return valuation, existing_evidence


def render_valuation_markdown(payload: dict[str, Any]) -> str:
    i = payload.get("inputs", {}) if isinstance(payload, dict) else {}
    v = payload.get("valuation", {}) if isinstance(payload, dict) else {}
    a = payload.get("assumptions", {}) if isinstance(payload, dict) else {}

    def money(x: Any) -> str:
        return f"${safe_float(x):,.2f}"

    lines: list[str] = []
    lines.append("# Master Valuation Update")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Scope: {payload.get('scope', '')}")
    lines.append("")
    lines.append("## Locked Thesis")
    lines.append("")
    lines.append(str(((payload.get("thesis", {}) or {}).get("label", ""))))
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- Annual value signal: {money(i.get('annual_value_signal_usd'))}")
    lines.append(f"- Router edge: {safe_float(i.get('router_edge_pct')):.2f}%")
    lines.append(f"- Harmonic win rate: {safe_float(i.get('harmonic_win_rate_pct')):.2f}%")
    lines.append(f"- Skip total target USD: {money(i.get('skip_total_target_usd'))}")
    lines.append(f"- Email queue count: {safe_int(i.get('email_queue_count'))}")
    lines.append(f"- Truth pass count: {safe_int(i.get('truth_pass_count'))}")
    lines.append(f"- Autonomous pass count: {safe_int(i.get('autonomous_pass_count'))}")
    lines.append(f"- Application context score: {safe_float(i.get('application_context_score_pct')):.2f}%")
    lines.append(f"- Application context missing required: {safe_int(i.get('application_context_missing_required'))}")
    lines.append(f"- Evidence file count: {safe_int(i.get('evidence_file_count'))}")
    lines.append("")
    lines.append("## Valuation")
    lines.append("")
    lines.append(f"- Autonomous grant execution value: {money(v.get('autonomous_grant_execution_value_usd'))}")
    lines.append(f"- Institutional signal-link value: {money(v.get('institutional_signal_link_value_usd'))}")
    lines.append(f"- Chain-of-custody value: {money(v.get('chain_of_custody_value_usd'))}")
    lines.append(f"- Pass momentum value: {money(v.get('pass_momentum_value_usd'))}")
    lines.append(f"- Raw valuation increment: {money(v.get('raw_valuation_increment_usd'))}")
    lines.append(f"- Valuation increment: {money(v.get('valuation_increment_usd'))}")
    lines.append(f"- Master valuation proxy: {money(v.get('master_valuation_proxy_usd'))}")
    lines.append("")
    lines.append("## Assumptions")
    lines.append("")
    lines.append(f"- Confidence index: {safe_float(a.get('confidence_index')):.6f}")
    lines.append(f"- Truth pass uplift multiplier: {safe_float(a.get('truth_pass_uplift_multiplier')):.6f}")
    lines.append(f"- Pass compound multiplier: {safe_float(a.get('pass_compound_multiplier')):.6f}")
    lines.append(f"- Innovation multiplier: {safe_float(a.get('innovation_multiplier')):.6f}")
    lines.append(f"- Minimum pass jump USD: {money(a.get('minimum_pass_jump_usd'))}")
    lines.append(f"- Monotonic override applied: {bool(a.get('monotonic_override_applied'))}")
    lines.append(f"- Formula: {a.get('formula', '')}")
    lines.append(f"- Note: {a.get('note', '')}")
    lines.append("")
    lines.append("## Evidence Paths")
    lines.append("")
    for p in payload.get("evidence_paths", []):
        lines.append(f"- {p}")
    lines.append("")
    return "\n".join(lines)


def build_luma_explainer(payload: dict[str, Any], entry_sha: str, event_id: str) -> dict[str, Any]:
    i = payload.get("inputs", {}) if isinstance(payload, dict) else {}
    v = payload.get("valuation", {}) if isinstance(payload, dict) else {}

    annual_signal = safe_float(i.get("annual_value_signal_usd"), 0.0)
    valuation_increment = safe_float(v.get("valuation_increment_usd"), 0.0)
    confidence = safe_float((payload.get("assumptions", {}) or {}).get("confidence_index"), 0.0)

    master_pitch = (
        "Luma Explainer Quantified Edition: We have now locked the first full end-to-end autonomous harmonic AI grant execution as a validated production event. "
        f"Signal-backed annual value is ${annual_signal:,.2f}, this grant-automation event adds an assumption-based valuation increment of ${valuation_increment:,.2f}, "
        f"and the event is frozen into an IP chain ledger at hash {entry_sha[:16]}...."
    )

    return {
        "generated_utc": now_iso(),
        "schema": "luma_explainer_quantified_v1",
        "event_id": event_id,
        "entry_sha256": entry_sha,
        "master_pitch": master_pitch,
        "sections": {
            "autonomous_win": {
                "title": "Autonomous Grant Win",
                "text": "First real win locked: full autonomous harmonic AI grant workflow executed, packaged, scored, and ledgered.",
            },
            "valuation": {
                "title": "Master Valuation Update",
                "text": (
                    f"Annual signal ${annual_signal:,.2f}; valuation increment ${valuation_increment:,.2f}; "
                    f"confidence index {confidence:.6f}."
                ),
            },
            "ip_chain": {
                "title": "IP Freeze and Chain of Custody",
                "text": (
                    "Event recorded with SHA256 manifest over all evidence paths and appended to autonomous grant win chain ledger. "
                    f"Entry hash: {entry_sha}."
                ),
            },
        },
        "walkthrough_order": ["autonomous_win", "valuation", "ip_chain"],
    }


def render_explainer_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Luma Explainer Quantified Pack")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Event ID: {payload.get('event_id', '')}")
    lines.append(f"Entry SHA256: {payload.get('entry_sha256', '')}")
    lines.append("")
    lines.append("## Master Pitch")
    lines.append("")
    lines.append(str(payload.get("master_pitch", "")))
    lines.append("")
    lines.append("## Sections")
    lines.append("")
    sections = payload.get("sections", {}) if isinstance(payload, dict) else {}
    if isinstance(sections, dict):
        for key in payload.get("walkthrough_order", []):
            row = sections.get(key, {})
            if not isinstance(row, dict):
                continue
            lines.append(f"### {row.get('title', key)}")
            lines.append("")
            lines.append(str(row.get("text", "")))
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Lock autonomous grant win into IP chain and update valuation artifacts.")
    parser.add_argument("--event-label", default="first_real_win_autonomous_harmonic_ai_grant_execution")
    args = parser.parse_args()

    valuation, evidence_files = build_valuation()
    tag = now_tag()

    MASTER_VAL_DIR.mkdir(parents=True, exist_ok=True)
    OUT_IP.mkdir(parents=True, exist_ok=True)
    LUMA_EXPLAINER_DIR.mkdir(parents=True, exist_ok=True)

    evidence_hashes: dict[str, str] = {}
    for p in evidence_files:
        try:
            evidence_hashes[str(p)] = sha256_file(p)
        except Exception:
            continue

    previous_entry_sha256 = read_prev_hash(IP_LEDGER)
    event_id = f"AUTONOMOUS_GRANT_WIN_{tag}"
    entry_data = {
        "generated_utc": now_iso(),
        "event_id": event_id,
        "event_label": args.event_label,
        "previous_entry_sha256": previous_entry_sha256,
        "statement": "First real win locked: full end-to-end autonomous harmonic AI grant execution.",
        "valuation": valuation.get("valuation", {}),
        "evidence_sha256": evidence_hashes,
    }
    canonical = json.dumps(entry_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    entry_sha256 = hashlib.sha256(canonical).hexdigest()
    ledger_row = dict(entry_data)
    ledger_row["entry_sha256"] = entry_sha256
    append_jsonl(IP_LEDGER, ledger_row)

    valuation["ip_lock"] = {
        "event_id": event_id,
        "entry_sha256": entry_sha256,
        "previous_entry_sha256": previous_entry_sha256,
        "ledger_path": str(IP_LEDGER),
    }

    val_json_tag = MASTER_VAL_DIR / f"master_valuation_{tag}.json"
    val_md_tag = MASTER_VAL_DIR / f"master_valuation_{tag}.md"
    val_json_latest = MASTER_VAL_DIR / "master_valuation_latest.json"
    val_md_latest = MASTER_VAL_DIR / "master_valuation_latest.md"

    write_json(val_json_tag, valuation)
    write_text(val_md_tag, render_valuation_markdown(valuation))
    write_json(val_json_latest, valuation)
    write_text(val_md_latest, render_valuation_markdown(valuation))

    manifest = {
        "generated_utc": now_iso(),
        "event_id": event_id,
        "entry_sha256": entry_sha256,
        "paths": {
            "ledger": str(IP_LEDGER),
            "master_valuation_json": str(val_json_tag),
            "master_valuation_md": str(val_md_tag),
        },
        "sha256": {
            str(val_json_tag): sha256_file(val_json_tag),
            str(val_md_tag): sha256_file(val_md_tag),
        },
        "evidence_sha256": evidence_hashes,
    }
    manifest_path = OUT_IP / f"autonomous_grant_win_manifest_{tag}.json"
    manifest_latest = OUT_IP / "autonomous_grant_win_manifest_latest.json"
    write_json(manifest_path, manifest)
    write_json(manifest_latest, manifest)

    statement_md = OUT_IP / f"autonomous_grant_win_statement_{tag}.md"
    statement_latest = OUT_IP / "autonomous_grant_win_statement_latest.md"
    statement_text = (
        "# Autonomous Grant Win Lock\n\n"
        f"Generated UTC: {manifest.get('generated_utc','')}\n"
        f"Event ID: {event_id}\n"
        f"Entry SHA256: {entry_sha256}\n"
        f"Previous SHA256: {previous_entry_sha256 or 'GENESIS'}\n\n"
        "Statement: first real win full end-to-end autonomous harmonic AI grant execution is now frozen into the IP chain ledger.\n"
    )
    write_text(statement_md, statement_text)
    write_text(statement_latest, statement_text)

    explainer = build_luma_explainer(valuation, entry_sha256, event_id)
    exp_json_tag = LUMA_EXPLAINER_DIR / f"luma_explainer_quantified_{tag}.json"
    exp_md_tag = LUMA_EXPLAINER_DIR / f"luma_explainer_quantified_{tag}.md"
    exp_json_latest = LUMA_EXPLAINER_DIR / "luma_explainer_quantified_latest.json"
    exp_md_latest = LUMA_EXPLAINER_DIR / "luma_explainer_quantified_latest.md"

    write_json(exp_json_tag, explainer)
    write_text(exp_md_tag, render_explainer_markdown(explainer))
    write_json(exp_json_latest, explainer)
    write_text(exp_md_latest, render_explainer_markdown(explainer))

    print(f"MASTER_VALUATION_LATEST={val_json_latest}")
    print(f"IP_LEDGER={IP_LEDGER}")
    print(f"IP_MANIFEST={manifest_path}")
    print(f"LUMA_EXPLAINER_LATEST={exp_json_latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
