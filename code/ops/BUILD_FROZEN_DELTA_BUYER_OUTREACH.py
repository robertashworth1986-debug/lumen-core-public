from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

HARVEST_JSON = OUT_OPS / "live_evidence_max_harvest_latest.json"
EXTERNAL_INTAKE_JSON = OUT_OPS / "external_proof_drive_intake_latest.json"
OUT_JSON = OUT_OPS / "frozen_delta_buyer_outreach_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "frozen_delta_buyer_outreach.json"
OUT_MD = DOCS / "FROZEN_DELTA_BUYER_OUTREACH_2026-06-25.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
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


def build_payload() -> dict[str, Any]:
    harvest = read_json(HARVEST_JSON)
    intake = read_json(EXTERNAL_INTAKE_JSON)
    summary = harvest.get("summary", {})
    intake_summary = intake.get("summary", {})
    top_candidates = intake.get("top_candidates", [])[:8]

    return {
        "schema": "frozen_delta_buyer_outreach.v1",
        "generated_utc": now_utc(),
        "current_truth": {
            "measured_sources": summary.get("measured_sources"),
            "total_measured_rows": summary.get("total_measured_rows"),
            "live_context_rows_evaluated": summary.get("total_live_context_rows_evaluated"),
            "candidate_beats_named_baseline_count": summary.get("candidate_beats_named_baseline_count"),
            "rolling_champion_count": summary.get("rolling_champion_count"),
            "triple_source_candidate_count": summary.get("triple_source_candidate_count"),
            "external_drive_files_scanned": intake_summary.get("files_seen"),
            "external_drive_candidates": intake_summary.get("candidate_count"),
            "external_live_frozen_triple_threat_candidates": intake_summary.get("live_frozen_triple_threat_candidate_count"),
            "external_content_hash_count": intake_summary.get("content_hash_count"),
            "ready_for_real_dollar_claim": bool(summary.get("ready_for_real_dollar_claim")),
            "field_validation": False,
            "kraken_live_execution_allowed": False,
        },
        "buyer_safe_positioning": (
            "LumenCore offers a paid pilot to review hash-backed frozen live-context evidence packets. "
            "Each packet is meant to show source provenance, measured rows, reproducible hashes, named baselines, "
            "and candidate benchmark deltas. It is not sold as guaranteed savings, field validation, or trading advice."
        ),
        "paid_pilot_offer": {
            "name": "Frozen Delta Evidence Review Pilot",
            "suggested_ask_usd": "5,000-15,000 scoped pilot, adjusted after buyer requirements and rights review",
            "deliverables": [
                "5-10 curated frozen-delta evidence packets matched to the buyer's sector",
                "source/provenance table with content hashes and snapshot hashes",
                "baseline-vs-candidate replay summary with claim boundary",
                "review call and red-team notes",
                "optional follow-on pilot plan for field validation",
            ],
            "not_included": [
                "guaranteed savings",
                "exclusive sale of all raw data",
                "live trading execution",
                "government award guarantee",
                "field validation claim without buyer-side deployment data",
            ],
        },
        "best_initial_buyer_segments": [
            "Defense primes or SBIR/STTR teaming partners needing reproducible technical evidence annexes",
            "Grid/data-center resilience teams that care about drift, outage, cooling, and control evidence",
            "Maritime/AIS analytics teams for HarborSentinel-style anomaly proof packets",
            "Energy analytics, insurance, and operational-risk groups seeking early-warning benchmark packets",
            "University labs or validation partners that can independently test geometry/control claims",
        ],
        "allowed_claims": [
            "We have a reproducible workflow for freezing live-context source evidence with hashes.",
            "The latest local harvest reports 17 measured sources, 417 measured rows, and 141 live-context replay rows.",
            "The external Glyph Drive intake scanned 50,000 files and identified 193 live/frozen triple-threat candidates with 150 top candidate content hashes.",
            "The current rolling gate reports zero repeat rolling champions, so outreach should frame results as candidate evidence ready for paid review/pilot validation.",
        ],
        "blocked_claims": [
            "Do not say the packets are field validated.",
            "Do not say a packet is worth $10,000 to the government as a fact.",
            "Do not claim guaranteed savings, guaranteed awards, or guaranteed alpha.",
            "Do not attach secrets, API keys, account exports, or patent-sensitive claim details in a cold email.",
        ],
        "email_templates": {
            "technical_buyer_short": {
                "subject": "Hash-backed frozen evidence packets for live-context infrastructure review",
                "body": (
                    "Hi {name},\n\n"
                    "I am building LumenCore, a proof-first evidence workflow for freezing live-context infrastructure/market/mission signals, "
                    "hashing the artifacts, and replaying candidate control/geometry strategies against named baselines.\n\n"
                    "The current packet is not a field-validation claim; it is a reproducible review pack. The latest harvest includes 17 measured sources, "
                    "417 measured rows, 141 live-context replay rows, and a Glyph Drive intake with 193 live/frozen candidate packets and 150 content-hashed top files.\n\n"
                    "I am looking for one paid pilot buyer or validation partner to review 5-10 curated frozen-delta packets in your sector and decide whether a field pilot is justified.\n\n"
                    "Would you be open to a 20-minute technical review call this week?\n\n"
                    "Robert Ashworth\n"
                    "LumenCore / NovaCore / LumaTrader\n"
                ),
            },
            "government_teaming_partner": {
                "subject": "Potential evidence annex / validation support for SBIR-STTR or defense resilience work",
                "body": (
                    "Hi {name},\n\n"
                    "I am preparing reviewer-safe LumenCore evidence packets for defense/energy/cyber-physical resilience proposals. "
                    "The system freezes measured source evidence, hashes artifacts, and compares candidate strategies against named baselines with explicit claim boundaries.\n\n"
                    "Current status: strong candidate evidence, not field validation. The live harvest shows 17 measured sources, 417 measured rows, 141 live-context replay rows, "
                    "and 3 candidate wins against named baselines. The repeat-champion gate is intentionally strict and currently reports 0 rolling champions.\n\n"
                    "I am looking for a teaming partner that can help review, validate, or field-test the evidence trail for an upcoming proposal/pilot.\n\n"
                    "Would a short technical screen be useful?\n\n"
                    "Robert Ashworth\n"
                ),
            },
            "validation_lab": {
                "subject": "Independent validation request: frozen live-context benchmark packets",
                "body": (
                    "Hi {name},\n\n"
                    "I am seeking independent review of LumenCore frozen-delta evidence packets. The goal is simple: determine which candidate geometry/control strategies "
                    "continue to beat named baselines when replayed against measured live-context source snapshots.\n\n"
                    "I can provide a bounded, non-sensitive sample packet with hashes, source rows, assumptions, and replay outputs. I am not asking you to accept savings claims; "
                    "I am asking for a rigorous review path that could become a paid validation pilot.\n\n"
                    "Is there a technical contact who reviews reproducible benchmark/provenance packets?\n\n"
                    "Robert Ashworth\n"
                ),
            },
        },
        "send_gate": {
            "mass_email_allowed": False,
            "send_without_user_review": False,
            "recommended_daily_limit": "5-10 highly targeted messages, not a blast",
            "requires_per_recipient_review": True,
        },
        "top_external_candidates": [
            {
                "score": row.get("score"),
                "evidence_class": row.get("evidence_class"),
                "path": row.get("path"),
                "content_sha256": row.get("content_sha256", ""),
                "matched_groups": row.get("matched_groups", []),
            }
            for row in top_candidates
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    truth = payload["current_truth"]
    pilot = payload["paid_pilot_offer"]
    lines = [
        "# Frozen Delta Buyer Outreach Pack",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Buyer-Safe Positioning",
        "",
        payload["buyer_safe_positioning"],
        "",
        "## Current Truth",
        "",
        f"- Measured sources: `{truth['measured_sources']}`",
        f"- Measured rows: `{truth['total_measured_rows']}`",
        f"- Live-context replay rows: `{truth['live_context_rows_evaluated']}`",
        f"- Candidate wins against named baselines: `{truth['candidate_beats_named_baseline_count']}`",
        f"- Rolling champions: `{truth['rolling_champion_count']}`",
        f"- Triple-source candidates: `{truth['triple_source_candidate_count']}`",
        f"- Glyph Drive files scanned: `{truth['external_drive_files_scanned']}`",
        f"- Glyph Drive candidates: `{truth['external_drive_candidates']}`",
        f"- Glyph Drive live/frozen triple-threat candidates: `{truth['external_live_frozen_triple_threat_candidates']}`",
        f"- Content-hashed top candidates: `{truth['external_content_hash_count']}`",
        f"- Ready for real-dollar claim: `{str(truth['ready_for_real_dollar_claim']).lower()}`",
        f"- Field validation: `{str(truth['field_validation']).lower()}`",
        "",
        "## Paid Pilot Offer",
        "",
        f"- Name: {pilot['name']}",
        f"- Suggested ask: {pilot['suggested_ask_usd']}",
        "",
        "Deliverables:",
    ]
    lines.extend(f"- {item}" for item in pilot["deliverables"])
    lines.extend(["", "Not included:"])
    lines.extend(f"- {item}" for item in pilot["not_included"])
    lines.extend(["", "## Best Buyer Segments", ""])
    lines.extend(f"- {item}" for item in payload["best_initial_buyer_segments"])
    lines.extend(["", "## Allowed Claims", ""])
    lines.extend(f"- {item}" for item in payload["allowed_claims"])
    lines.extend(["", "## Blocked Claims", ""])
    lines.extend(f"- {item}" for item in payload["blocked_claims"])
    lines.extend(["", "## Email Templates", ""])
    for key, template in payload["email_templates"].items():
        lines.extend(
            [
                f"### {key}",
                "",
                f"Subject: {template['subject']}",
                "",
                "```text",
                template["body"].rstrip(),
                "```",
                "",
            ]
        )
    lines.extend(["## Top Glyph Drive Candidates", ""])
    for row in payload["top_external_candidates"]:
        lines.append(f"- score `{row['score']}` | `{row['evidence_class']}` | `{row['path']}` | sha `{row['content_sha256']}`")
    lines.extend(
        [
            "",
            "## Send Gate",
            "",
            "- Do not mass email.",
            "- Do not send without reviewing the exact recipient and message.",
            "- Do not attach secrets, raw private account exports, or patent-sensitive details.",
            "- Use the outreach to get a paid pilot/review call, not to claim guaranteed value.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"wrote {OUT_JSON}")
    print(f"wrote {DASHBOARD_JSON}")
    print(f"wrote {OUT_MD}")
    print(json.dumps(payload["current_truth"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
