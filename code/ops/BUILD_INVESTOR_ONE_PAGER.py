"""Build a claim-bounded investor and partner evidence brief.

The builder intentionally excludes modeled valuations, projected savings,
performance promotion, and stale opportunity calls. It reports current local
evidence states and preserves external sharing as a human decision.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "out" / "ops" / "investor_one_pager"

PRODUCT_PRIORITY = (
    ROOT / "dashboard" / "data" / "product_lane_priority_engine_20260718.json"
)
PROOF_TO_REVENUE = ROOT / "out" / "ops" / "proof_to_revenue_engine_latest.json"
SCIENCE_LEDGER = (
    ROOT / "out" / "ops" / "source_native_family_baseline_ledger_latest.json"
)
PROSPECTIVE_STATUS = (
    ROOT / "out" / "ops" / "time_series_source_native_prospective_protocol_status.json"
)
CAPABILITY_MATRIX = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "CROSS_AGENCY_CAPABILITY_MATRIX_2026-07-26.json"
)
PILOT_CONFIG = ROOT / "config" / "prooflock_opportunity_ops_pilot_v1.json"

OUTPUT_MD = DEST / "INVESTOR_ONE_PAGER.md"
OUTPUT_JSON = DEST / "INVESTOR_ONE_PAGER.json"
OUTPUT_HTML = DEST / "INVESTOR_ONE_PAGER.html"

BOUNDARY = (
    "Internal draft for recipient-specific review. Local artifacts and tests can "
    "establish software, protocol, custody, and gate behavior only. They do not "
    "establish valuation, customer acceptance, awards, agency endorsement, field "
    "performance, realized savings, trading alpha, or production authorization."
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def artifact_receipt(path: Path) -> dict[str, Any]:
    try:
        relative = str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        relative = str(path)
    if not path.is_file():
        return {
            "path": relative,
            "exists": False,
            "bytes": 0,
            "sha256": None,
        }
    content = path.read_bytes()
    return {
        "path": relative,
        "exists": True,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def build_payload(at: datetime | None = None) -> dict[str, Any]:
    at = at or now_utc()
    product = read_json(PRODUCT_PRIORITY)
    revenue = read_json(PROOF_TO_REVENUE)
    science = read_json(SCIENCE_LEDGER)
    prospective = read_json(PROSPECTIVE_STATUS)
    capability = read_json(CAPABILITY_MATRIX)
    pilot = read_json(PILOT_CONFIG)

    source_paths = (
        PRODUCT_PRIORITY,
        PROOF_TO_REVENUE,
        SCIENCE_LEDGER,
        PROSPECTIVE_STATUS,
        CAPABILITY_MATRIX,
        PILOT_CONFIG,
    )
    receipts = [artifact_receipt(path) for path in source_paths]
    sources_complete = all(receipt["exists"] for receipt in receipts)

    ranking = product.get("ranking")
    top_lane = ranking[0] if isinstance(ranking, list) and ranking else {}
    science_summary = science.get("summary")
    if not isinstance(science_summary, dict):
        science_summary = {}
    capability_summary = capability.get("summary")
    if not isinstance(capability_summary, dict):
        capability_summary = {}

    payload: dict[str, Any] = {
        "schema": "lumen.investor_one_pager/v2",
        "generated_utc": at.astimezone(timezone.utc).isoformat(),
        "status": (
            "INTERNAL_DRAFT_RECIPIENT_AND_CLAIM_REVIEW_REQUIRED"
            if sources_complete
            else "BLOCKED_MISSING_CANONICAL_EVIDENCE"
        ),
        "external_share_ready": False,
        "recipient_selected": False,
        "boundary": BOUNDARY,
        "headline": (
            "LumenCore is a governed evidence-engineering stack for reproducible "
            "technical decisions, source-native evaluation, and human-authorized "
            "opportunity operations."
        ),
        "product": {
            "priority_lane": top_lane.get("id"),
            "offer": top_lane.get("offer"),
            "strategy_score_is_valuation": False,
            "internal_evidence_gate_passed": top_lane.get(
                "internal_evidence_gate_passed"
            ),
            "validated_evidence_count": top_lane.get("validated_evidence_count"),
            "required_evidence_count": top_lane.get("required_evidence_count"),
            "buyer_readiness_gate_passed": (
                top_lane.get("buyer_readiness_gate") or {}
            ).get("passed"),
            "first_required_validation": top_lane.get("first_validation"),
            "revenue_stage": revenue.get("revenue_stage"),
            "external_outreach_ready": revenue.get("external_outreach_ready"),
        },
        "scientific_evidence": {
            "registered_family_count": science_summary.get(
                "registered_family_count"
            ),
            "implementation_present_count": science_summary.get(
                "implementation_present_count"
            ),
            "implementation_required_count": science_summary.get(
                "implementation_required_count"
            ),
            "executed_direct_source_baseline_comparison_count": science_summary.get(
                "executed_direct_source_baseline_comparison_count"
            ),
            "internal_source_native_promotion_gate_pass_count": science_summary.get(
                "internal_source_native_promotion_gate_pass_count"
            ),
            "global_holm_positive_count": science_summary.get(
                "individual_comparison_global_holm_positive_count"
            ),
            "prospective_protocol_status": prospective.get("protocol_status"),
            "prospective_promotion_decision": prospective.get(
                "promotion_decision"
            ),
            "prospective_protocol_id": prospective.get("protocol_id"),
            "prospective_protocol_sha256": prospective.get(
                "protocol_payload_sha256"
            ),
            "eligible_future_observation_count": prospective.get(
                "eligible_future_observation_count"
            ),
            "performance_claim_allowed": False,
            "claim_boundary": science_summary.get(
                "claim_boundary", prospective.get("claim_boundary")
            ),
        },
        "government_readiness": {
            "capability_matrix_status": capability.get("status"),
            "proven_local_module_count": (
                capability_summary.get("effective_class_counts") or {}
            ).get("PROVEN"),
            "bounded_module_count": (
                capability_summary.get("effective_class_counts") or {}
            ).get("BOUNDED"),
            "restricted_claim_allowed_count": capability_summary.get(
                "restricted_claim_allowed_count"
            ),
            "external_action_count": capability_summary.get(
                "external_action_count"
            ),
            "posture": (
                "Bounded evidence-readiness sprint or specialized workstream "
                "under a qualified prime; notice-specific conformance remains "
                "an action-time review."
            ),
        },
        "pilot": {
            "protocol_id": pilot.get("protocol_id"),
            "status": pilot.get("status"),
            "duration_days": pilot.get("duration_days"),
            "buyer_selected": False,
            "pricing_approved": bool((pilot.get("pricing") or {}).get(
                "founder_approved"
            )),
            "minimum_sample": pilot.get("minimum_sample"),
            "acceptance_metric_count": len(pilot.get("acceptance_metrics") or []),
            "final_submission_automated": False,
        },
        "commercial_asks": [
            {
                "ask": "Independent protocol review",
                "purpose": (
                    "Review the frozen source-native prospective protocol before "
                    "future observations become eligible."
                ),
                "price_or_value_claim": None,
            },
            {
                "ask": "Buyer-scoped 30-day ProofLock pilot",
                "purpose": (
                    "Freeze one workflow baseline, denominators, thresholds, and "
                    "human gates, then measure the bounded outcome."
                ),
                "price_or_value_claim": None,
            },
            {
                "ask": "Qualified-prime teaming conversation",
                "purpose": (
                    "Evaluate a specialized evidence-engineering workstream against "
                    "a current notice and the prime's delivery boundary."
                ),
                "price_or_value_claim": None,
            },
        ],
        "claim_controls": {
            "allowed_now": [
                "The repository contains source hashing, replay, receipt, abstention, and human-gate software patterns.",
                "A source-native benchmark ledger records positive, neutral, negative, and inconclusive results.",
                "A prospective protocol is frozen and waiting for future eligible observations.",
                "A buyer-neutral pilot protocol defines exact metrics, denominators, exclusions, RACI, and human authority.",
            ],
            "blocked_now": [
                "valuation or enterprise-value statements",
                "modeled or realized savings statements",
                "customer, agency, or independent acceptance",
                "field performance or universal superiority",
                "trading alpha or live-capital readiness",
                "autonomous grants, certification, signing, sending, uploading, or submission",
                "guaranteed awards, revenue, or procurement outcomes",
            ],
        },
        "economics": {
            "valuation_stated": False,
            "savings_stated": False,
            "revenue_stated": False,
            "rule": (
                "Quantify value only after a named buyer approves the baseline, "
                "counterfactual, denominator, period, exclusions, and validation owner."
            ),
        },
        "source_receipts": receipts,
        "all_canonical_sources_present": sources_complete,
    }
    payload["brief_payload_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    product = payload["product"]
    science = payload["scientific_evidence"]
    government = payload["government_readiness"]
    pilot = payload["pilot"]
    lines = [
        "# LumenCore Investor and Partner Evidence Brief",
        "",
        "**DRAFT ONLY - RECIPIENT NOT SELECTED - EXTERNAL CLAIM REVIEW REQUIRED**",
        "",
        f"- Generated UTC: `{payload['generated_utc']}`",
        f"- Status: `{payload['status']}`",
        f"- External share ready: `{str(payload['external_share_ready']).lower()}`",
        "",
        f"> {payload['boundary']}",
        "",
        "## What Exists Now",
        "",
        payload["headline"],
        "",
        f"- Priority product lane: `{product['priority_lane']}`",
        f"- Offer: {product['offer']}",
        (
            f"- Typed internal evidence: `{product['validated_evidence_count']}` / "
            f"`{product['required_evidence_count']}` required artifacts"
        ),
        f"- Buyer-readiness gate passed: `{str(product['buyer_readiness_gate_passed']).lower()}`",
        f"- Required external validation: {product['first_required_validation']}",
        "",
        "## Scientific Status",
        "",
        (
            f"- Registered families: `{science['registered_family_count']}`; "
            f"implemented: `{science['implementation_present_count']}`; "
            f"implementation gaps: `{science['implementation_required_count']}`"
        ),
        (
            "- Direct source-native comparisons executed: "
            f"`{science['executed_direct_source_baseline_comparison_count']}`"
        ),
        (
            "- Promotion gates passed: "
            f"`{science['internal_source_native_promotion_gate_pass_count']}`; "
            f"global Holm-positive comparisons: `{science['global_holm_positive_count']}`"
        ),
        (
            f"- Prospective protocol: `{science['prospective_protocol_status']}` / "
            f"`{science['prospective_promotion_decision']}`"
        ),
        f"- Eligible future observations: `{science['eligible_future_observation_count']}`",
        f"- Protocol SHA-256: `{science['prospective_protocol_sha256']}`",
        "",
        "The present scientific contribution is the governed comparison and evidence protocol, not a promoted performance champion.",
        "",
        "## Commercial Path",
        "",
        f"- Pilot protocol: `{pilot['protocol_id']}`",
        f"- Buyer selected: `{str(pilot['buyer_selected']).lower()}`",
        f"- Pricing approved: `{str(pilot['pricing_approved']).lower()}`",
        f"- Acceptance metrics: `{pilot['acceptance_metric_count']}`",
        "- Final submission automated: `false`",
        "",
    ]
    for item in payload["commercial_asks"]:
        lines.append(f"- **{item['ask']}**: {item['purpose']}")
    lines.extend(
        [
            "",
            "## Government and Prime Posture",
            "",
            f"- Capability matrix: `{government['capability_matrix_status']}`",
            f"- Proven local modules: `{government['proven_local_module_count']}`",
            f"- Bounded modules: `{government['bounded_module_count']}`",
            f"- Restricted external claims allowed: `{government['restricted_claim_allowed_count']}`",
            f"- External actions authorized: `{government['external_action_count']}`",
            f"- Posture: {government['posture']}",
            "",
            "## Not Claimed",
            "",
        ]
    )
    lines.extend(
        f"- {item}" for item in payload["claim_controls"]["blocked_now"]
    )
    lines.extend(
        [
            "",
            "## Receipt",
            "",
            f"- Payload SHA-256: `{payload['brief_payload_sha256']}`",
            f"- Canonical sources present: `{str(payload['all_canonical_sources_present']).lower()}`",
        ]
    )
    return "\n".join(lines)


def render_html(payload: dict[str, Any]) -> str:
    markdown = render_markdown(payload)
    sections: list[str] = []
    in_list = False
    for raw_line in markdown.splitlines():
        line = escape(raw_line)
        if line.startswith("# "):
            if in_list:
                sections.append("</ul>")
                in_list = False
            sections.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            if in_list:
                sections.append("</ul>")
                in_list = False
            sections.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("- "):
            if not in_list:
                sections.append("<ul>")
                in_list = True
            sections.append(f"<li>{line[2:]}</li>")
        elif line.startswith("&gt; "):
            if in_list:
                sections.append("</ul>")
                in_list = False
            sections.append(f"<blockquote>{line[5:]}</blockquote>")
        elif line:
            if in_list:
                sections.append("</ul>")
                in_list = False
            sections.append(f"<p>{line}</p>")
    if in_list:
        sections.append("</ul>")
    body = "\n".join(sections)
    return "\n".join(
        [
            "<!doctype html>",
            "<html lang=\"en\">",
            "<head>",
            "<meta charset=\"utf-8\">",
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
            "<title>LumenCore Investor and Partner Evidence Brief</title>",
            "<style>",
            "body{font-family:Segoe UI,Arial,sans-serif;max-width:820px;margin:0 auto;padding:28px;color:#17202a;line-height:1.5}",
            "h1{font-size:28px}h2{font-size:19px;margin-top:28px;border-bottom:1px solid #cbd5e1;padding-bottom:6px}",
            "blockquote{border-left:4px solid #0f766e;margin:18px 0;padding:10px 16px;background:#f0fdfa}",
            "li{margin:6px 0}code{font-family:Consolas,monospace}",
            "</style>",
            "</head>",
            f"<body>{body}</body>",
            "</html>",
        ]
    )


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    OUTPUT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    OUTPUT_MD.write_text(render_markdown(payload) + "\n", encoding="utf-8")
    OUTPUT_HTML.write_text(render_html(payload) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "status": payload["status"],
                "external_share_ready": payload["external_share_ready"],
                "recipient_selected": payload["recipient_selected"],
                "payload_sha256": payload["brief_payload_sha256"],
                "outputs": [
                    str(OUTPUT_JSON),
                    str(OUTPUT_MD),
                    str(OUTPUT_HTML),
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
