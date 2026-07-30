from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FIELD_PACKET = ROOT / "out" / "ops" / "field_validation_buyer_pilot_packet_latest.json"
CONTROL_ROOM = ROOT / "out" / "ops" / "proof_to_pilot_control_room_latest.json"
OUT_JSON = ROOT / "out" / "ops" / "evidence_protocol_review_fixed_scope_offer_latest.json"
OUT_DASHBOARD_JSON = (
    ROOT / "dashboard" / "data" / "evidence_protocol_review_fixed_scope_offer.json"
)
OUT_MD = ROOT / "docs" / "LUMENCORE_EVIDENCE_PROTOCOL_REVIEW_FIXED_SCOPE_OFFER_2026-07-30.md"

FIXED_FEE_USD = 3500
DEPOSIT_USD = 1750
BALANCE_USD = 1750


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


def stable_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_json_sha256(value: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def source_controls() -> tuple[dict[str, Any], dict[str, Any], int, int]:
    field_packet = read_json(FIELD_PACKET)
    control_room = read_json(CONTROL_ROOM)
    if field_packet.get("schema") != "field_validation_buyer_pilot_packet_v2":
        raise ValueError("Field-validation packet schema is missing or stale")
    if control_room.get("schema") != "proof_to_pilot_control_room_v2":
        raise ValueError("Proof-to-pilot control-room schema is missing or stale")

    field_summary = field_packet.get("summary")
    room_summary = control_room.get("summary")
    packets = field_packet.get("packets")
    if not isinstance(field_summary, dict) or not isinstance(room_summary, dict):
        raise ValueError("Source summaries are missing")
    if not isinstance(packets, list) or not packets:
        raise ValueError("No bounded protocol-review packet is available")
    if field_summary.get("protocol_review_packet_count", 0) < 1:
        raise ValueError("No protocol-review service is supported")
    if field_summary.get("internal_performance_champion_count") != 0:
        raise ValueError("This offer must not price a performance champion")
    if field_summary.get("field_replay_candidate_count") != 0:
        raise ValueError("This offer must not imply field-replay readiness")
    if field_summary.get("manual_outreach_ready_count") != 0:
        raise ValueError("This offer builder does not authorize outreach")
    if room_summary.get("paid_evaluation_offer_allowed") is not True:
        raise ValueError("The control room does not permit a bounded paid evaluation offer")
    if room_summary.get("buyer_authorized_pilot_scoping_ready") is not False:
        raise ValueError("Buyer-authorized pilot scoping must remain open")
    if room_summary.get("pilot_ready_count") != 0:
        raise ValueError("No current candidate may be represented as pilot-ready")

    price_lows: list[int] = []
    price_highs: list[int] = []
    for packet in packets:
        if not isinstance(packet, dict):
            raise ValueError("Protocol-review packet must be an object")
        offer = packet.get("paid_offer")
        if not isinstance(offer, dict):
            raise ValueError("Protocol-review packet has no bounded paid offer")
        price_range = offer.get("price_range_usd")
        if not isinstance(price_range, dict):
            raise ValueError("Protocol-review packet has no price range")
        price_lows.append(int(price_range["low"]))
        price_highs.append(int(price_range["high"]))

    supported_low = max(price_lows)
    supported_high = min(price_highs)
    if not supported_low <= FIXED_FEE_USD <= supported_high:
        raise ValueError("Candidate fixed fee is outside the existing bounded service range")
    return field_packet, control_room, supported_low, supported_high


def build_payload(generated_utc: str | None = None) -> dict[str, Any]:
    field_packet, control_room, supported_low, supported_high = source_controls()
    field_summary = field_packet["summary"]
    room_summary = control_room["summary"]

    payload: dict[str, Any] = {
        "schema": "lumencore.evidence_protocol_review_fixed_scope_offer.v1",
        "generated_utc": generated_utc or now_utc(),
        "status": "DRAFT_FIXED_SCOPE_FOUNDER_PRICE_BUYER_AND_RECIPIENT_APPROVAL_REQUIRED",
        "product_id": "prooflock_evidence_protocol_review_sprint_v1",
        "product_name": "ProofLock Evidence Protocol Review Sprint",
        "commercial_category": "professional_services_fixed_scope",
        "purpose": (
            "Help one buyer define and replay a source-native benchmark or evidence workflow "
            "without selling an unsupported model winner, savings estimate, or field result."
        ),
        "commercial_terms": {
            "candidate_fixed_fee_usd": FIXED_FEE_USD,
            "candidate_deposit_usd": DEPOSIT_USD,
            "candidate_balance_usd": BALANCE_USD,
            "existing_supported_service_range_usd": {
                "low": supported_low,
                "high": supported_high,
            },
            "duration_business_days": 10,
            "kickoff_condition": (
                "Signed scope, cleared payment, named buyer owner, approved source, and complete "
                "buyer inputs"
            ),
            "payment_timing": "Candidate only; founder and buyer must approve exact terms in writing",
            "price_committed": False,
            "founder_price_approval_required": True,
        },
        "scope_limits": {
            "buyer_workflows": 1,
            "authorized_source_systems": 1,
            "registered_incumbent_baselines_max": 3,
            "candidate_methods_max": 2,
            "evaluation_windows_max": 20,
            "review_meetings": 2,
            "revision_rounds": 1,
            "production_access": False,
            "portal_administration": False,
            "autonomous_submission": False,
        },
        "buyer_inputs_required": [
            "One authorized timestamped source or approved public source",
            "One operational question and target variable",
            "The accepted incumbent and up to three source-native baselines",
            "A frozen development and untouched holdout boundary",
            "Acceptance metrics, guardrails, exclusions, and failure-reporting rules",
            "A named buyer workflow owner authorized to approve the protocol",
        ],
        "deliverables": [
            "Source-task compatibility and data-quality memo",
            "Predeclared benchmark and evidence protocol",
            "Registered incumbent-baseline matrix",
            "Reproducible execution bundle with hashes and retained negative results",
            "Offline reviewer packet with explicit claim and non-claim boundaries",
            "One final readout and buyer decision memo",
        ],
        "acceptance_criteria": [
            "All six deliverables are present and readable",
            "The buyer-approved source, task, baselines, windows, metrics, and exclusions are frozen before evaluation",
            "The supplied replay verifies against the delivered hashes on the agreed environment",
            "Failures, abstentions, and negative results are retained rather than omitted",
            "The final memo distinguishes observed results from inference and unsupported claims",
        ],
        "exclusions": [
            "No promise of performance, savings, revenue, funding, award, or acceptance",
            "A claim that any geometry family or model is a current champion",
            "Production deployment, managed operations, or service-level agreement",
            "Credentials, signatures, certifications, payments, uploads, sends, or submissions",
            "Protected health information, controlled unclassified information, classified data, or export-controlled data",
            "Legal, accounting, cybersecurity accreditation, or acquisition advice",
        ],
        "source_evidence": {
            "field_packet": FIELD_PACKET.relative_to(ROOT).as_posix(),
            "field_packet_sha256": hashlib.sha256(FIELD_PACKET.read_bytes()).hexdigest(),
            "control_room": CONTROL_ROOM.relative_to(ROOT).as_posix(),
            "control_room_sha256": hashlib.sha256(CONTROL_ROOM.read_bytes()).hexdigest(),
            "protocol_review_packet_count": field_summary["protocol_review_packet_count"],
            "internal_performance_champion_count": field_summary[
                "internal_performance_champion_count"
            ],
            "pilot_ready_count": room_summary["pilot_ready_count"],
            "paid_evaluation_offer_allowed": room_summary[
                "paid_evaluation_offer_allowed"
            ],
        },
        "controls": {
            "buyer_selected": False,
            "recipient_selected": False,
            "buyer_data_approved": False,
            "founder_price_approved": False,
            "contract_terms_approved": False,
            "external_send_allowed": False,
            "bulk_outreach_allowed": False,
            "portal_action_allowed": False,
            "performance_claim_allowed": False,
            "savings_claim_allowed": False,
            "field_validation_claim_allowed": False,
        },
        "safest_next_action": (
            "Select one real buyer and one authorized source, confirm the buyer's accepted baseline, "
            "then obtain founder approval for the exact fixed fee, recipient, data terms, and outreach."
        ),
        "claim_boundary": (
            "This is a draft fixed-scope professional-services offer supported by local protocol "
            "and receipt behavior. It is not a customer result, field validation, performance "
            "champion, realized savings estimate, contract, invoice, or outreach authorization."
        ),
    }
    payload["payload_sha256"] = stable_json_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    terms = payload["commercial_terms"]
    limits = payload["scope_limits"]
    lines = [
        "# ProofLock Evidence Protocol Review Sprint",
        "",
        f"Status: `{payload['status']}`",
        "",
        payload["purpose"],
        "",
        "## Candidate Commercial Terms",
        "",
        f"- Fixed fee: `${terms['candidate_fixed_fee_usd']:,}`",
        f"- Candidate kickoff deposit: `${terms['candidate_deposit_usd']:,}`",
        f"- Candidate delivery balance: `${terms['candidate_balance_usd']:,}`",
        f"- Duration: `{terms['duration_business_days']}` business days after the kickoff condition is met",
        f"- Existing supported service range: `${terms['existing_supported_service_range_usd']['low']:,}` to `${terms['existing_supported_service_range_usd']['high']:,}`",
        "- Price status: candidate only; founder and buyer written approval required",
        "",
        "## Fixed Scope",
        "",
        f"- One buyer workflow and one authorized source system",
        f"- Up to `{limits['registered_incumbent_baselines_max']}` registered incumbent baselines",
        f"- Up to `{limits['candidate_methods_max']}` candidate methods and `{limits['evaluation_windows_max']}` evaluation windows",
        f"- `{limits['review_meetings']}` review meetings and `{limits['revision_rounds']}` revision round",
        "- No production access, portal administration, managed submission, or autonomous action",
        "",
        "## Buyer Inputs",
        "",
        *[f"- {item}" for item in payload["buyer_inputs_required"]],
        "",
        "## Deliverables",
        "",
        *[f"{index}. {item}" for index, item in enumerate(payload["deliverables"], start=1)],
        "",
        "## Acceptance",
        "",
        *[f"- {item}" for item in payload["acceptance_criteria"]],
        "",
        "## Exclusions",
        "",
        *[f"- {item}" for item in payload["exclusions"]],
        "",
        "## Current Gate",
        "",
        "- Buyer selected: `false`",
        "- Recipient selected: `false`",
        "- Founder price approved: `false`",
        "- External send allowed: `false`",
        "- Performance, savings, and field-validation claims allowed: `false`",
        "",
        f"Safest next action: {payload['safest_next_action']}",
        "",
        "## Boundary",
        "",
        payload["claim_boundary"],
        "",
        f"Payload SHA-256: `{payload['payload_sha256']}`",
        "",
    ]
    return "\n".join(lines)


def serialized_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=True) + "\n"


def write_outputs(payload: dict[str, Any]) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_DASHBOARD_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    rendered_json = serialized_payload(payload)
    OUT_JSON.write_text(rendered_json, encoding="utf-8")
    OUT_DASHBOARD_JSON.write_text(rendered_json, encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")


def check_outputs() -> None:
    published = read_json(OUT_JSON)
    expected = build_payload(str(published["generated_utc"]))
    if OUT_JSON.read_text(encoding="utf-8") != serialized_payload(expected):
        raise ValueError("Fixed-scope offer JSON is stale")
    if OUT_DASHBOARD_JSON.read_text(encoding="utf-8") != serialized_payload(expected):
        raise ValueError("Fixed-scope offer dashboard JSON is stale")
    if OUT_MD.read_text(encoding="utf-8") != render_markdown(expected):
        raise ValueError("Fixed-scope offer Markdown is stale")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the fail-closed ProofLock fixed-scope paid protocol-review offer."
    )
    parser.add_argument("--generated-utc")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        check_outputs()
        print("evidence protocol-review fixed-scope offer outputs are current")
        return 0

    payload = build_payload(args.generated_utc)
    write_outputs(payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "candidate_fixed_fee_usd": payload["commercial_terms"][
                    "candidate_fixed_fee_usd"
                ],
                "duration_business_days": payload["commercial_terms"][
                    "duration_business_days"
                ],
                "external_send_allowed": payload["controls"][
                    "external_send_allowed"
                ],
                "payload_sha256": payload["payload_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
