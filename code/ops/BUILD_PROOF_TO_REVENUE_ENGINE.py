from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

LIVE_DOMAIN_JSON = OUT_OPS / "live_domain_deployment_feed_latest.json"
GAUNTLET_JSON = OUT_OPS / "champion_metric_gauntlet_latest.json"
OUTREACH_JSON = OUT_OPS / "paid_pilot_outreach_queue_latest.json"
VALUE_JSON = OUT_OPS / "live_proof_value_meter_latest.json"

OUT_JSON = OUT_OPS / "proof_to_revenue_engine_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "proof_to_revenue_engine.json"
OUT_MD = DOCS / "PROOF_TO_REVENUE_ENGINE_2026-06-27.md"

BOUNDARY = (
    "Proof-to-revenue engine. This artifact turns verified public proof feeds and internal benchmark evidence into "
    "manual paid-pilot actions. It does not authorize bulk email, fixed dollar claims, field-validation claims, "
    "realized savings claims, live trading, or autonomous execution."
)


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def money(value: Any) -> str:
    return f"${as_float(value):,.2f}"


def compact_target(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": as_int(row.get("rank")),
        "target_segment": str(row.get("target_segment") or ""),
        "buyer_role": str(row.get("buyer_role") or ""),
        "family_id": str(row.get("family_id") or ""),
        "lane": str(row.get("lane") or ""),
        "fit_score": as_int(row.get("fit_score")),
        "measured_outcome": str(row.get("measured_outcome") or ""),
        "subject": str(row.get("subject") or ""),
        "proof_line": str(row.get("proof_line") or ""),
        "send_now_allowed": False,
        "manual_review_required": True,
    }


def safe_email_template(top_target: dict[str, Any], champion: dict[str, Any], reviewer_urls: dict[str, Any]) -> dict[str, Any]:
    family = champion.get("champion_label") or champion.get("champion_family") or top_target.get("family_id")
    segment = top_target.get("target_segment", "technical evaluation").replace("_", " ")
    return {
        "subject": f"Paid pilot scoping: verified proof feed for {segment}",
        "body": "\n".join(
            [
                "Hello,",
                "",
                (
                    "I am looking for the right technical reviewer for a bounded paid evaluation of a "
                    "hash-verified benchmark packet."
                ),
                "",
                (
                    f"The current internal champion is {family}. It has public proof-feed hashes available for review, "
                    "but I am not claiming field validation or realized savings yet."
                ),
                "",
                (
                    "The ask is narrow: a 20-minute fit call to decide whether a buyer-authorized field replay is "
                    "worth scoping, using your approved baseline, holdout windows, and economic conversion factors."
                ),
                "",
                f"Reviewer URL: {reviewer_urls.get('champion_feed_primary', '')}",
                f"Mission console: {reviewer_urls.get('mission_control', '')}",
                "",
                "If you are not the right person, who owns analytics validation or pilot scoping for this area?",
                "",
                "Respectfully,",
                "Robert Ashworth",
            ]
        ),
        "send_mode": "manual_review_only",
        "why_not_autosend": "Recipient, organization fit, physical mailing footer, and opt-out language must be reviewed by a human.",
    }


def build_payload() -> dict[str, Any]:
    live = read_json(LIVE_DOMAIN_JSON)
    gauntlet = read_json(GAUNTLET_JSON)
    outreach = read_json(OUTREACH_JSON)
    value_meter = read_json(VALUE_JSON)

    live_summary = as_dict(live.get("summary"))
    gauntlet_summary = as_dict(gauntlet.get("summary"))
    outreach_summary = as_dict(outreach.get("summary"))
    value_answer = as_dict(value_meter.get("answer"))
    reviewer_urls = as_dict(live.get("reviewer_urls"))

    queue = [row for row in as_list(outreach.get("queue")) if isinstance(row, dict)]
    top_targets = [compact_target(row) for row in queue[:5]]
    top_target = top_targets[0] if top_targets else {}

    live_hash_verified = live_summary.get("domain_deployment_state") == "LIVE_DOMAIN_HASH_VERIFIED" and bool(
        live_summary.get("live_domain_reviewer_ready")
    )
    champion_ready = bool(gauntlet_summary.get("buyer_authorized_field_replay_request_ready"))
    manual_outreach_ready = bool(outreach_summary.get("manual_reviewed_outreach_allowed"))
    field_validation_allowed = False
    realized_savings_allowed = False

    revenue_stage = (
        "manual_paid_pilot_scoping_ready"
        if live_hash_verified and champion_ready and manual_outreach_ready
        else "proof_stack_not_ready_for_outreach"
    )
    safest_first_offer = {
        "name": "Paid evidence review / field replay scoping",
        "pricing_posture": "quote after scope; no fixed delta price yet",
        "deliverable": (
            "Review the public proof feed, lock the buyer baseline, select holdout windows, and decide whether a "
            "buyer-authorized field replay should be purchased."
        ),
        "allowed_today": revenue_stage == "manual_paid_pilot_scoping_ready",
    }

    payload = {
        "schema": "proof_to_revenue_engine_v1",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "summary": {
            "revenue_stage": revenue_stage,
            "live_domain_hash_verified": live_hash_verified,
            "required_remote_hash_matches": as_int(live_summary.get("required_remote_hash_match_count")),
            "required_feed_count": as_int(live_summary.get("required_feed_count")),
            "champion_family": gauntlet_summary.get("champion_family"),
            "champion_label": gauntlet_summary.get("champion_label"),
            "named_baseline": gauntlet_summary.get("named_baseline"),
            "holdout_wins": gauntlet_summary.get("holdout_wins"),
            "holdout_count": gauntlet_summary.get("holdout_count"),
            "source_system_count": gauntlet_summary.get("source_system_count"),
            "estimated_rows_replayed": gauntlet_summary.get("estimated_rows_replayed"),
            "safe_estimated_hourly_value_usd": round(as_float(gauntlet_summary.get("safe_estimated_hourly_value_usd")), 2),
            "safe_estimated_annual_value_usd": round(as_float(gauntlet_summary.get("safe_estimated_annual_value_usd")), 2),
            "manual_reviewed_outreach_allowed": manual_outreach_ready,
            "send_without_user_review_allowed": False,
            "bulk_email_allowed": False,
            "field_validation_claim_allowed": field_validation_allowed,
            "realized_savings_claim_allowed": realized_savings_allowed,
            "fixed_frozen_delta_price_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "plain_english_answer": (
                "The proof stack is now strong enough for manually reviewed paid-pilot outreach: public hashes match, "
                f"{gauntlet_summary.get('champion_label')} beat {gauntlet_summary.get('named_baseline')} on "
                f"{gauntlet_summary.get('holdout_wins')}/{gauntlet_summary.get('holdout_count')} holdouts, and the "
                "next money gate is buyer-authorized field replay. It is not yet a realized savings claim."
            ),
        },
        "reviewer_urls": reviewer_urls,
        "safest_first_offer": safest_first_offer,
        "top_manual_targets": top_targets,
        "safe_email_template": safe_email_template(top_target, gauntlet_summary, reviewer_urls) if top_target else {},
        "field_validation_unlock": [
            "buyer-approved operational or representative field dataset",
            "named incumbent baseline and locked evaluation metric",
            "pre-registered holdout windows",
            "same data, same time windows, same compute constraints for baseline and candidate",
            "buyer-approved economic conversion factor",
            "signed or otherwise traceable replay result artifact",
        ],
        "what_to_ask_next": [
            "Which reviewer URL should be used first?",
            "Which current champion and named baseline are we claiming?",
            "Which top target segment gets the first manual email?",
            "What buyer-owned data would unlock field validation?",
            "What exact metric converts this into a dollar claim?",
            "Which statements are still blocked?",
            "What price can be quoted only after scope?",
            "What test would most increase valuation this week?",
            "Which grant packet should cite this proof feed?",
            "What proof should never be sent without human review?",
        ],
        "claim_controls": {
            "allowed": [
                "public hash-verified proof feed",
                "internal champion against named baseline",
                "bounded estimated value surface",
                "manual paid-pilot scoping",
                "buyer-authorized field replay request",
            ],
            "blocked": [
                "field validated",
                "realized savings",
                "fixed value per frozen delta",
                "guaranteed funding",
                "guaranteed trading profit",
                "bulk email or scraped outreach",
            ],
        },
        "source_status": {
            "live_domain_loaded": bool(live),
            "gauntlet_loaded": bool(gauntlet),
            "outreach_queue_loaded": bool(outreach),
            "value_meter_loaded": bool(value_meter),
            "value_meter_answer": value_answer,
        },
    }
    payload["proof_to_revenue_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "reviewer_urls": payload["reviewer_urls"],
            "safest_first_offer": payload["safest_first_offer"],
            "top_manual_targets": payload["top_manual_targets"],
            "field_validation_unlock": payload["field_validation_unlock"],
            "claim_controls": payload["claim_controls"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = as_dict(payload.get("summary"))
    lines = [
        "# Proof To Revenue Engine",
        "",
        f"Generated UTC: `{payload.get('generated_utc')}`",
        "",
        "## Current State",
        "",
        summary.get("plain_english_answer", ""),
        "",
        "## Deployment Verification",
        "",
        f"- Live domain hash verified: `{str(summary.get('live_domain_hash_verified')).lower()}`",
        f"- Required remote hash matches: `{summary.get('required_remote_hash_matches')}/{summary.get('required_feed_count')}`",
        f"- Reviewer champion feed: `{payload.get('reviewer_urls', {}).get('champion_feed_primary', '')}`",
        f"- Mission control: `{payload.get('reviewer_urls', {}).get('mission_control', '')}`",
        "",
        "## Champion Evidence",
        "",
        f"- Champion: `{summary.get('champion_label')}`",
        f"- Named baseline: `{summary.get('named_baseline')}`",
        f"- Holdout wins: `{summary.get('holdout_wins')}/{summary.get('holdout_count')}`",
        f"- Source systems: `{summary.get('source_system_count')}`",
        f"- Estimated rows replayed: `{summary.get('estimated_rows_replayed')}`",
        f"- Safe estimated hourly value surface: `{money(summary.get('safe_estimated_hourly_value_usd'))}`",
        f"- Safe estimated annual value surface: `{money(summary.get('safe_estimated_annual_value_usd'))}`",
        "",
        "## What We Can Sell Today",
        "",
        f"- Revenue stage: `{summary.get('revenue_stage')}`",
        f"- Safest first offer: `{payload.get('safest_first_offer', {}).get('name', '')}`",
        f"- Pricing posture: `{payload.get('safest_first_offer', {}).get('pricing_posture', '')}`",
        f"- Manual reviewed outreach allowed: `{str(summary.get('manual_reviewed_outreach_allowed')).lower()}`",
        f"- Send without user review allowed: `{str(summary.get('send_without_user_review_allowed')).lower()}`",
        "",
        "## Top Manual Targets",
        "",
    ]
    for row in as_list(payload.get("top_manual_targets")):
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- `{row.get('rank')}` {row.get('target_segment')} -> {row.get('buyer_role')} "
            f"({row.get('family_id')}, fit {row.get('fit_score')})"
        )
    lines.extend(
        [
            "",
            "## Field Validation Unlock",
            "",
        ]
    )
    for item in as_list(payload.get("field_validation_unlock")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Blocked Claims",
            "",
        ]
    )
    for item in as_dict(payload.get("claim_controls")).get("blocked", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## What To Ask Next",
            "",
        ]
    )
    for i, item in enumerate(as_list(payload.get("what_to_ask_next")), 1):
        lines.append(f"{i}. {item}")
    lines.extend(
        [
            "",
            f"Proof-to-revenue SHA-256: `{payload.get('proof_to_revenue_sha256')}`",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(payload["summary"]["plain_english_answer"])


if __name__ == "__main__":
    main()
