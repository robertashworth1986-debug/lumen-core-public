from __future__ import annotations

import hashlib
import json
import math
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


def _unique_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError("nonfinite JSON number")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("nonfinite JSON number")
    return parsed


def read_source(path: Path, source_id: str, observed_utc: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind the parsed summary to the exact bytes read, without copying private bodies."""
    receipt: dict[str, Any] = {
        "source_id": source_id, "read_utc": observed_utc, "status": "MISSING",
        "sha256": None, "bytes": None, "source_generated_utc": None,
        "source_age_seconds": None, "source_freshness": "UNKNOWN",
        "freshness_limit_seconds": 86400, "underlying_artifacts_verified": False,
    }
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return {}, receipt
    except OSError:
        receipt["status"] = "UNREADABLE"
        return {}, receipt
    receipt.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    try:
        payload = json.loads(raw, object_pairs_hook=_unique_members, parse_constant=_reject_nonfinite, parse_float=_finite_float)
        if not isinstance(payload, dict):
            raise ValueError("source must be an object")
    except (ValueError, UnicodeError):
        receipt["status"] = "INVALID_JSON"
        return {}, receipt
    receipt["status"] = "READ"
    stamp = payload.get("generated_utc")
    if stamp is not None:
        try:
            if not isinstance(stamp, str):
                raise ValueError("timestamp must be text")
            generated = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if generated.utcoffset() is None:
                raise ValueError("timestamp must include timezone")
            observed = datetime.fromisoformat(observed_utc.replace("Z", "+00:00"))
            age = (observed - generated).total_seconds()
            receipt.update(source_generated_utc=generated.astimezone(timezone.utc).isoformat(), source_age_seconds=age)
            receipt["source_freshness"] = "FUTURE_TIMESTAMP" if age < 0 else ("STALE" if age > 86400 else "CURRENT")
        except (ValueError, TypeError, OverflowError):
            receipt["source_freshness"] = "INVALID_TIMESTAMP"
    return payload, receipt


def reported_count(summary: dict[str, Any], key: str) -> int | None:
    value = summary.get(key)
    return value if type(value) is int and value >= 0 else None


def display_count(value: int | None) -> str:
    return "UNKNOWN" if value is None else f"{value:,}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def build_payload() -> dict[str, Any]:
    generated_utc = now_utc()
    harvest, harvest_receipt = read_source(HARVEST_JSON, "live_evidence_max_harvest", generated_utc)
    intake, intake_receipt = read_source(EXTERNAL_INTAKE_JSON, "external_proof_drive_intake", generated_utc)
    summary = harvest.get("summary") if isinstance(harvest.get("summary"), dict) else {}
    intake_summary = intake.get("summary") if isinstance(intake.get("summary"), dict) else {}
    count_fields = {
        "measured_sources": (summary, "measured_sources"),
        "total_measured_rows": (summary, "total_measured_rows"),
        "live_context_rows_evaluated": (summary, "total_live_context_rows_evaluated"),
        "candidate_beats_named_baseline_count": (summary, "candidate_beats_named_baseline_count"),
        "registered_baseline_comparison_count": (summary, "registered_baseline_comparison_count"),
        "registered_baseline_mean_win_count": (summary, "registered_baseline_mean_win_count"),
        "registered_baseline_global_holm_positive_count": (summary, "registered_baseline_global_holm_positive_count"),
        "rolling_champion_count": (summary, "rolling_champion_count"),
        "triple_source_candidate_count": (summary, "triple_source_candidate_count"),
        "external_drive_files_scanned": (intake_summary, "files_seen"),
        "external_drive_candidates": (intake_summary, "candidate_count"),
        "external_live_frozen_triple_threat_candidates": (intake_summary, "live_frozen_triple_threat_candidate_count"),
        "external_content_hash_count": (intake_summary, "content_hash_count"),
    }
    truth = {field: reported_count(source, key) for field, (source, key) in count_fields.items()}
    unknown_counts = [key for key, value in truth.items() if value is None]
    count_consistency_issues = []
    comparisons = truth["registered_baseline_comparison_count"]
    for key in ("registered_baseline_mean_win_count", "registered_baseline_global_holm_positive_count"):
        if comparisons is not None and truth[key] is not None and truth[key] > comparisons:
            count_consistency_issues.append(f"{key}_exceeds_registered_comparisons")
    truth.update(
        ready_for_real_dollar_claim=False, field_validation=False, kraken_live_execution_allowed=False,
        financial_effect_verified=False, verified_annual_savings_usd=None,
        reported_ready_for_real_dollar_claim=(summary.get("ready_for_real_dollar_claim") if type(summary.get("ready_for_real_dollar_claim")) is bool else None),
        evidence_basis="SOURCE_REPORTED_COUNTS_NOT_INDEPENDENTLY_VERIFIED_EFFECTS",
    )
    harvest_date = harvest_receipt["source_generated_utc"] or "UNKNOWN"
    intake_date = intake_receipt["source_generated_utc"] or "UNKNOWN"
    reported_harvest = (
        f"The harvest snapshot dated {harvest_date} reports "
        f"{display_count(truth['measured_sources'])} sources marked measured, "
        f"{display_count(truth['total_measured_rows'])} source rows and "
        f"{display_count(truth['live_context_rows_evaluated'])} live-context replay rows. "
        "These are reported intake and replay counts, not verified intervention effects."
    )
    reported_comparisons = (
        f"The same snapshot reports {display_count(truth['candidate_beats_named_baseline_count'])} candidate wins against named baselines, "
        f"{display_count(truth['registered_baseline_mean_win_count'])} mean wins among "
        f"{display_count(truth['registered_baseline_comparison_count'])} registered comparisons, "
        f"{display_count(truth['registered_baseline_global_holm_positive_count'])} globally Holm-positive comparisons and "
        f"{display_count(truth['rolling_champion_count'])} rolling champions. "
        "These differently scoped counts must not be added or used as an authorization."
    )
    reported_intake = (
        f"The private intake summary dated {intake_date} reports "
        f"{display_count(truth['external_drive_files_scanned'])} files scanned, "
        f"{display_count(truth['external_drive_candidates'])} inventory candidates and "
        f"{display_count(truth['external_content_hash_count'])} content hashes. "
        "Inventory and hashes do not establish replay suitability, publication rights or performance."
    )
    source_receipts = {"harvest": harvest_receipt, "external_intake": intake_receipt}
    source_review_required = bool(unknown_counts or count_consistency_issues) or any(
        receipt["status"] != "READ" or receipt["source_freshness"] != "CURRENT"
        for receipt in source_receipts.values()
    )

    return {
        "schema": "frozen_delta_buyer_outreach.v1",
        "generated_utc": generated_utc,
        "source_receipts": source_receipts,
        "unknown_or_invalid_count_fields": unknown_counts,
        "count_consistency_issues": count_consistency_issues,
        "decision_state": "HOLD_SOURCE_REVIEW" if source_review_required else "HOLD_EXTERNAL_VALIDATION",
        "current_truth": truth,
        "buyer_safe_positioning": (
            "LumenCore offers a paid pilot to review hash-backed frozen live-context evidence packets. "
            "Each packet is meant to show source provenance, measured rows, reproducible hashes, named baselines, "
            "and candidate benchmark deltas. It is not sold as guaranteed savings, field validation, or trading advice."
        ),
        "paid_pilot_offer": {
            "name": "Frozen Delta Evidence Review Pilot",
            "suggested_ask_usd": "Illustrative scoping range 5,000-15,000; no buyer acceptance or agreed price is established",
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
            reported_harvest,
            reported_comparisons,
            reported_intake,
            "A dated source summary is not current external-state verification. Any buyer packet still needs source rights, exact replay artifacts and recipient-specific review.",
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
                    f"{reported_harvest}\n\n"
                    f"{reported_comparisons}\n\n"
                    "I am looking for one paid pilot buyer or validation partner to review 5-10 curated frozen-delta packets in your sector and decide whether a field pilot is justified.\n\n"
                    "Would you be open to a 20-minute technical review call this week?\n\n"
                    "Robert Ashworth\n"
                    "LumenCore\n"
                ),
            },
            "government_teaming_partner": {
                "subject": "Potential evidence annex / validation support for SBIR-STTR or defense resilience work",
                "body": (
                    "Hi {name},\n\n"
                    "I am preparing reviewer-safe LumenCore evidence packets for defense/energy/cyber-physical resilience proposals. "
                    "The system freezes measured source evidence, hashes artifacts, and compares candidate strategies against named baselines with explicit claim boundaries.\n\n"
                    f"{reported_harvest}\n\n"
                    f"{reported_comparisons}\n\n"
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
                    "beat, tie or lose to named baselines when replayed against frozen source snapshots.\n\n"
                    f"{reported_harvest}\n\n"
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
        "top_external_candidates": [],
        "external_candidate_details_status": "PRIVATE_DETAILS_EXCLUDED_FROM_PUBLIC_OUTPUT",
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
        "## Source-Reported Counts",
        "",
        f"- Sources reported as measured: `{display_count(truth['measured_sources'])}`",
        f"- Reported source rows: `{display_count(truth['total_measured_rows'])}`",
        f"- Live-context replay rows: `{display_count(truth['live_context_rows_evaluated'])}`",
        f"- Candidate wins against named baselines: `{display_count(truth['candidate_beats_named_baseline_count'])}`",
        f"- Rolling champions: `{display_count(truth['rolling_champion_count'])}`",
        f"- Triple-source candidates: `{display_count(truth['triple_source_candidate_count'])}`",
        f"- Private inventory files scanned: `{display_count(truth['external_drive_files_scanned'])}`",
        f"- Private inventory candidates: `{display_count(truth['external_drive_candidates'])}`",
        f"- Inventory live/frozen candidates: `{display_count(truth['external_live_frozen_triple_threat_candidates'])}`",
        f"- Reported content hashes: `{display_count(truth['external_content_hash_count'])}`",
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
    lines.extend(["", "## Source Identities And Observation Times", ""])
    for source_id, receipt in payload["source_receipts"].items():
        lines.append(
            f"- {source_id}: status `{receipt['status']}`, source time `{receipt['source_generated_utc'] or 'UNKNOWN'}`, "
            f"read time `{receipt['read_utc']}`, freshness `{receipt['source_freshness']}`, "
            f"bytes `{receipt['bytes']}`, SHA-256 `{receipt['sha256'] or 'UNKNOWN'}`."
        )
    lines.extend(["", "Underlying source artifacts and effects are not verified by this builder. Private candidate paths and bodies are excluded."])
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
