from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT = ROOT / "grant_submissions" / "funding_sprint_20260709"
JSON_OUT = SPRINT / "FHWA_TSMO_PARTNER_OUTREACH_CONTROL_2026-07-17.json"
MD_OUT = SPRINT / "FHWA_TSMO_PARTNER_OUTREACH_CONTROL_2026-07-17.md"
RESPONSE_OUT = SPRINT / "FHWA_TSMO_PARTNER_RESPONSE_CONTROL_2026-07-17.md"

ORIGINAL_SUBJECT = "FHWA TSMO Data Initiative (693JJ326R000012) - bounded teaming fit"
ORIGINAL_BODY = """Hello Ms. Flanigan,

I am reaching out because Cambridge Systematics' published work shows deep FHWA and Transportation Systems Management and Operations program experience. LumenCore is evaluating whether to participate in FHWA solicitation 693JJ326R000012, due August 3, 2026 at 9:00 a.m. ET, only through a qualified prime or team member that can truthfully document the Phase I corporate-experience requirement.

Our proposed contribution is narrow: data-quality controls; chronological, baseline-locked model benchmarking; uncertainty and abstention gates; reproducible evidence manifests; and API-based prototype evaluation. We would not represent Cambridge Systematics as a partner, cite its experience, or use customer information without written agreement and verification.

Is Cambridge Systematics pursuing this opportunity, and if so, would you or the appropriate colleague be open to a 20-30 minute fit check by July 23? The initial call would cover only role fit, corporate-experience eligibility, conflicts, data rights, and schedule. No confidential or patent-sensitive information is needed.

Official opportunity: https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view

If this is not in your lane, a referral to the appropriate federal programs or proposal lead would be appreciated.

Best regards,
Robert Ashworth
Founder and Chief Scientist, LumenCore"""

REPLACEMENT_SUBJECT = (
    "FHWA TSMO Data Initiative (693JJ326R000012) - teaming fit / routing request"
)
REPLACEMENT_BODY = """Hello Ms. Binder,

I am contacting you because Cambridge Systematics' current 2026 materials identify you as Principal, VP Federal Market and Transportation Policy, and the firm's published work reflects substantial FHWA and Transportation Systems Management and Operations experience. A message sent earlier today to a TSMO contact address listed on the company site was returned as an invalid recipient, so I am using this current official route and will not resend to that address.

LumenCore is evaluating whether to participate in FHWA solicitation 693JJ326R000012, due August 3, 2026 at 9:00 a.m. ET, only through a qualified prime or team member that can truthfully document the Phase I corporate-experience requirement.

Our proposed contribution is narrow: data-quality controls; chronological, baseline-locked model benchmarking; uncertainty and abstention gates; reproducible evidence manifests; and API-based prototype evaluation. We would not represent Cambridge Systematics as a partner, cite its experience, or use customer information without written agreement and verification.

Is Cambridge Systematics pursuing this opportunity, and if so, would you or the appropriate colleague be open to a 20-30 minute fit check by July 23? The initial call would cover only role fit, corporate-experience eligibility, conflicts, data rights, and schedule. No confidential or patent-sensitive information is needed.

Official opportunity: https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view

If another colleague owns this lane, a referral would be appreciated.

Best regards,
Robert Ashworth
Founder and Chief Scientist, LumenCore"""

REFERRAL_ACK_SUBJECT = (
    "Re: FHWA TSMO Data Initiative (693JJ326R000012) - teaming fit / routing request"
)
REFERRAL_ACK_BODY_PUBLIC = """Susan,

Thank you for the quick routing. The original message was sent to the rejected official-profile route, which Gmail returned as: "the address couldn't be found, or is unable to receive mail." I can provide the delivery-status notice if it would help investigate.

Sogand,

Thank you for considering a brief fit check. LumenCore is interested only in a bounded supporting role if Cambridge Systematics is pursuing FHWA solicitation 693JJ326R000012 and our capabilities fit your response plan.

A 20-30 minute discussion on or before July 23 would be enough to cover role scope, the Phase I corporate-experience boundary, conflicts, data rights, and schedule. Our candidate contribution is limited to data-quality controls, chronological and baseline-locked model benchmarking, uncertainty and abstention gates, reproducible evidence manifests, and API-based prototype evaluation. No confidential or patent-sensitive information is needed for the initial discussion.

Please suggest a time that works for your team and I will do my best to accommodate it. I will not represent Cambridge Systematics as a partner or cite its experience without written agreement and verification.

Best regards,
Robert Ashworth
Founder and Chief Scientist, LumenCore"""

ORIGINAL_SENT_UTC = "2026-07-17T10:08:29Z"
ORIGINAL_FAILURE_UTC = "2026-07-17T10:08:31Z"
ORIGINAL_MESSAGE_ID_SHA256 = (
    "d27b64996ab87149931992cd81dd1562b996504f0c4dd72e8384564ad0a44752"
)
ORIGINAL_DSN_MESSAGE_ID_SHA256 = (
    "dc22b523b0e618dd7e461b631b877473bb4f323ace2797a6fe0a3bce34ac40e5"
)
REPLACEMENT_SENT_UTC = "2026-07-17T12:35:16Z"
REPLACEMENT_MESSAGE_ID_SHA256 = (
    "e39959cf09ccba85deccd2ce2c36a0bf8526e337f5ff6ea2abe1c8c989fe406f"
)
REFERRAL_RECEIVED_UTC = "2026-07-17T14:15:28Z"
REFERRAL_MESSAGE_ID_SHA256 = (
    "747d1ddbd4c0d64994462b2d7183384eb17c8237c9ddaeca338fef9a6812eb09"
)
REFERRAL_ACK_SENT_UTC = "2026-07-17T14:41:54Z"
REFERRAL_ACK_MESSAGE_ID_SHA256 = (
    "4dc96cdefa25b4554bf730d002fd4e63f1420feb6fa50f3b9470f89adf1dbe25"
)
REFERRAL_ACK_BODY_SHA256 = (
    "9e704e831cb33f2013cad0b880a1c48539184bc6e1344ef48533b9c6b799ec84"
)
TEAM_SET_RESPONSE_RECEIVED_UTC = "2026-07-17T16:28:25Z"
TEAM_SET_RESPONSE_MESSAGE_ID_SHA256 = (
    "70cb86e922dd6af11bd790b9e4c22b1630f1634993ff3e5a4e11eccea5003d98"
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_payload() -> dict[str, Any]:
    return {
        "schema": "lumencore.fhwa_tsmo_partner_outreach_control.v3",
        "as_of_date": "2026-07-17",
        "status": "RESPONSE_LEAD_DECLINED_ADDITIONAL_PARTNER_TEAM_SET",
        "opportunity": {
            "notice_id": "693JJ326R000012",
            "title": "Transportation Systems Management and Operations Data Initiative",
            "agency": "Federal Highway Administration",
            "phase_i_deadline": "2026-08-03T09:00:00-04:00",
            "internal_response_target": "2026-07-23",
            "official_notice": "https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view",
        },
        "target": {
            "organization": "Cambridge Systematics",
            "active_contact_role": (
                "Principal, VP Federal Market and Transportation Policy"
            ),
            "response_lead_role": (
                "Subject matter expert leading Cambridge Systematics' response"
            ),
            "rejected_contact_role": (
                "Vice President and FHWA Office of Operations program manager"
            ),
            "recipient_domain": "camsys.com",
            "active_public_professional_route_verified": True,
            "inbound_referral_verified": True,
            "private_contact_values_stored_in_public_receipt": False,
            "qualification_basis": [
                "The current official TRB 2026 company page identifies the active contact as Principal, VP Federal Market and Transportation Policy.",
                "The official company biography for the rejected route documents deep FHWA TSMO and Office of Operations experience but its listed mailbox returned SMTP 550 Invalid Recipient.",
                "The replacement message asks only for pursuit status, role fit, or routing and does not claim a partnership.",
                "The active contact replied and referred the request to the subject matter expert leading this response; the referral does not itself confirm pursuit, teaming, or permission to cite experience.",
                "The referred response lead later stated that the team was already set and would not add partners for this pursuit.",
            ],
            "official_company_sources": [
                "https://camsys.com/trb",
                "https://camsys.com/blog/people/erin-flanigan",
            ],
        },
        "replacement_pre_send_gates": {
            "active_official_target_evidence_verified": True,
            "original_delivery_failure_verified": True,
            "prior_active_recipient_mailbox_matches": 0,
            "mailbox_search_method": "Connected Gmail exact-recipient and organization search before send.",
            "attachment_count": 0,
            "patent_sensitive_material_included": False,
            "partner_relationship_claimed": False,
            "customer_information_requested": False,
            "send_gate_passed": True,
        },
        "outbound_history": [
            {
                "attempt_index": 1,
                "route_role": "official TSMO profile contact",
                "status": "DELIVERY_REJECTED_550_INVALID_RECIPIENT",
                "sent_utc": ORIGINAL_SENT_UTC,
                "failure_utc": ORIGINAL_FAILURE_UTC,
                "smtp_status_code": 550,
                "gmail_label_observed": "SENT",
                "message_id_sha256": ORIGINAL_MESSAGE_ID_SHA256,
                "dsn_message_id_sha256": ORIGINAL_DSN_MESSAGE_ID_SHA256,
                "subject": ORIGINAL_SUBJECT,
                "subject_sha256": sha256_text(ORIGINAL_SUBJECT),
                "body_sha256": sha256_text(ORIGINAL_BODY),
                "body": ORIGINAL_BODY,
                "attachment_count": 0,
                "delivery_confirmed": False,
            },
            {
                "attempt_index": 2,
                "route_role": "current official federal-market contact",
                "status": "DELIVERED_BY_SUBSTANTIVE_REPLY_REFERRAL_RECEIVED",
                "sent_utc": REPLACEMENT_SENT_UTC,
                "failure_utc": None,
                "smtp_status_code": None,
                "gmail_label_observed": "SENT",
                "message_id_sha256": REPLACEMENT_MESSAGE_ID_SHA256,
                "subject": REPLACEMENT_SUBJECT,
                "subject_sha256": sha256_text(REPLACEMENT_SUBJECT),
                "body_sha256": sha256_text(REPLACEMENT_BODY),
                "body": REPLACEMENT_BODY,
                "attachment_count": 0,
                "immediate_delivery_rejection_observed": False,
                "delivery_confirmed": True,
            },
            {
                "attempt_index": 3,
                "route_role": "referred response lead and routing contacts",
                "status": "THREADED_REFERRAL_ACKNOWLEDGMENT_SENT_FIT_CHECK_PENDING",
                "sent_utc": REFERRAL_ACK_SENT_UTC,
                "failure_utc": None,
                "smtp_status_code": None,
                "gmail_label_observed": "SENT",
                "message_id_sha256": REFERRAL_ACK_MESSAGE_ID_SHA256,
                "subject": REFERRAL_ACK_SUBJECT,
                "subject_sha256": sha256_text(REFERRAL_ACK_SUBJECT),
                "body_sha256": REFERRAL_ACK_BODY_SHA256,
                "body_sha256_scope": "EXACT_SENT_BODY_PRIVATE_SOURCE",
                "body": REFERRAL_ACK_BODY_PUBLIC,
                "body_public_redaction_applied": True,
                "attachment_count": 0,
                "immediate_delivery_rejection_observed": False,
                "delivery_confirmed": False,
            },
        ],
        "inbound_history": [
            {
                "event_index": 1,
                "status": "QUALIFIED_RESPONSE_LEAD_REFERRAL_RECEIVED",
                "received_utc": REFERRAL_RECEIVED_UTC,
                "message_id_sha256": REFERRAL_MESSAGE_ID_SHA256,
                "sender_role": "Vice President, Federal Transportation Market and Policy",
                "referred_lead_role": (
                    "Subject matter expert leading Cambridge Systematics' response"
                ),
                "attachment_count": 0,
                "original_route_failure_question_received": True,
                "pursuit_confirmed": False,
                "partnership_confirmed": False,
                "permission_to_cite_experience_confirmed": False,
                "fit_check_confirmed": False,
            },
            {
                "event_index": 2,
                "status": "TEAM_SET_NO_ADDITIONAL_PARTNERS",
                "received_utc": TEAM_SET_RESPONSE_RECEIVED_UTC,
                "message_id_sha256": TEAM_SET_RESPONSE_MESSAGE_ID_SHA256,
                "sender_role": "Subject matter expert leading the response",
                "attachment_count": 0,
                "pursuit_confirmed": True,
                "partnership_confirmed": False,
                "permission_to_cite_experience_confirmed": False,
                "fit_check_confirmed": False,
                "additional_partner_slot_available": False,
                "future_opportunity_recontact_invited": True,
            },
        ],
        "delivery_reconciliation": {
            "attempt_count": 3,
            "delivery_failure_count": 1,
            "replacement_send_count": 1,
            "threaded_acknowledgment_send_count": 1,
            "confirmed_delivery_count": 1,
            "response_count": 2,
            "qualified_response_lead_referral_count": 1,
            "fit_check_confirmed_count": 0,
            "team_set_decline_count": 1,
            "active_attempt_index": 3,
            "stale_route_reuse_allowed": False,
        },
        "response_control": {
            "state": "NO_GO_TEAM_SET_NO_ADDITIONAL_PARTNERS",
            "qualified_partner_evidence_present": False,
            "qualified_response_lead_referral_present": True,
            "response_lead_final_response_received": True,
            "fit_check_confirmed": False,
            "bid_posture": "NO_GO_NO_QUALIFIED_TEAMING_PARTNER",
            "send_now": False,
            "do_not_duplicate_send": True,
            "no_follow_up_before": None,
            "next_action": (
                "Close this Cambridge Systematics pursuit route without another reply or "
                "follow-up. Do not cite the firm, its experience, or a relationship. Reopen only "
                "if Cambridge Systematics initiates a future-opportunity conversation."
            ),
        },
        "response_templates": {
            "artifact": RESPONSE_OUT.resolve().relative_to(ROOT.resolve()).as_posix(),
            "branch_count": 5,
            "autonomous_send_allowed": False,
        },
        "claim_boundary": (
            "The Gmail records prove that the first route was rejected, the replacement message "
            "received a substantive reply, the request was referred to the subject matter expert "
            "leading this response, one bounded acknowledgment was sent, and the response lead "
            "then stated that its team was already set and would not add partners. This is a no-go "
            "for this teaming route; it does not establish a relationship, permission to cite "
            "corporate experience, independent validation, proposal compliance, submission, award, "
            "or funding."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    target = payload["target"]
    response = payload["response_control"]
    delivery = payload["delivery_reconciliation"]
    active = next(
        row
        for row in payload["outbound_history"]
        if row["attempt_index"] == delivery["active_attempt_index"]
    )
    lines = [
        "# FHWA TSMO Partner Outreach Control",
        "",
        f"Status: `{payload['status']}`",
        f"Opportunity: `{payload['opportunity']['notice_id']}`",
        f"Phase I deadline: `{payload['opportunity']['phase_i_deadline']}`",
        "",
        "## Verified Target Basis",
        "",
        f"Organization: {target['organization']}",
        f"Active public professional role: {target['active_contact_role']}",
        "",
    ]
    lines.extend(f"- {item}" for item in target["qualification_basis"])
    lines.extend(
        [
            "",
            "## Delivery Reconciliation",
            "",
            f"- Attempts: `{delivery['attempt_count']}`",
            f"- Delivery failures: `{delivery['delivery_failure_count']}`",
            f"- Replacement sends: `{delivery['replacement_send_count']}`",
            f"- Confirmed deliveries: `{delivery['confirmed_delivery_count']}`",
            f"- Responses: `{delivery['response_count']}`",
            f"- Qualified response-lead referrals: `{delivery['qualified_response_lead_referral_count']}`",
            f"- Fit checks confirmed: `{delivery['fit_check_confirmed_count']}`",
            f"- Team-set declines: `{delivery['team_set_decline_count']}`",
            f"- Recipient domain: `{target['recipient_domain']}`",
            "",
        ]
    )
    for attempt in payload["outbound_history"]:
        lines.extend(
            [
                f"### Attempt {attempt['attempt_index']}",
                "",
                f"- Route role: {attempt['route_role']}",
                f"- Status: `{attempt['status']}`",
                f"- Sent UTC: `{attempt['sent_utc']}`",
                f"- Message ID SHA-256: `{attempt['message_id_sha256']}`",
                f"- Attachments: `{attempt['attachment_count']}`",
                "",
            ]
        )
    lines.extend(["## Inbound Outcomes", ""])
    for inbound in payload["inbound_history"]:
        lines.extend(
            [
                f"### Inbound {inbound['event_index']}",
                "",
                f"- Status: `{inbound['status']}`",
                f"- Received UTC: `{inbound['received_utc']}`",
                f"- Sender role: {inbound['sender_role']}",
                f"- Message ID SHA-256: `{inbound['message_id_sha256']}`",
                f"- Partnership confirmed: `{str(inbound['partnership_confirmed']).lower()}`",
                f"- Fit check confirmed: `{str(inbound['fit_check_confirmed']).lower()}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Active Threaded Message",
            "",
            f"Subject: {active['subject']}",
            "",
            active["body"],
            "",
            "## Response Gate",
            "",
            f"- State: `{response['state']}`",
            f"- Bid posture: `{response['bid_posture']}`",
            f"- No duplicate follow-up before: `{response['no_follow_up_before']}`",
            f"- Next action: {response['next_action']}",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def render_response_templates(payload: dict[str, Any]) -> str:
    deadline = payload["opportunity"]["phase_i_deadline"]
    return f"""# FHWA TSMO Partner Response Control - 2026-07-17

Opportunity: `693JJ326R000012`

Phase I deadline: `{deadline}`

Status: `{payload['status']}`

These branches are bounded drafts. Use only the branch supported by a new inbound message. Do not state that delivery, interest, a partnership, permission to cite experience, proposal compliance, or selection exists unless the written record establishes it.

## Interested Or Correct Owner

Thank you for confirming the right lane. A 20-30 minute fit check would be helpful. The initial discussion can stay limited to pursuit status, LumenCore's possible role, the mandatory corporate-experience requirement, conflicts, schedule, data rights, and what evidence could be cited only with written permission. Please send two suitable windows and the preferred meeting method. No confidential or patent-sensitive information is needed for this first check.

## Referral Provided

Thank you for the referral. Reply once in the existing thread, identify the referral accurately, and keep the request limited to pursuit, role fit, corporate-experience boundaries, conflicts, data rights, and schedule. Do not describe Cambridge Systematics as a partner without written agreement.

## More Information Requested

Thank you. I can provide a short, nonconfidential capability note limited to data-quality controls, chronological baseline-locked benchmarking, uncertainty and abstention, reproducible evidence manifests, and API-based prototype evaluation. Before sending an attachment, I will verify its current hash, public-safe status, and relevance to the specific question. It will not claim FHWA deployment, agency validation, customer savings, or a teaming relationship.

## Not Pursuing Or Decline

Thank you for the clear response. I will close this outreach route and will not represent any relationship or use Cambridge Systematics' experience in the proposal.

## NDA Or Confidential Information Requested

Thank you. I can first provide a public, nonconfidential overview. Any NDA, teaming agreement, proprietary exchange, data-rights term, or patent-sensitive disclosure must be reviewed and approved before signature or transmission. I will not send controlled or confidential material in this email thread.

## Stop Conditions

- Do not reuse the rejected address.
- The current team-set response closes this route; do not send another acknowledgment or scheduling follow-up.
- Do not attach confidential, controlled, patent-sensitive, customer, or unverified performance material.
- Do not accept or sign an NDA, teaming agreement, data-rights term, pricing term, or exclusivity term through this template.
- Do not claim delivery, receipt, pursuit, partnership, permission to cite experience, submission, award, or validation without written evidence.

## Claim Boundary

{payload['claim_boundary']}
"""


def write_outputs(payload: dict[str, Any]) -> None:
    JSON_OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    MD_OUT.write_text(render_markdown(payload), encoding="utf-8")
    RESPONSE_OUT.write_text(render_response_templates(payload), encoding="utf-8")


def main() -> int:
    payload = build_payload()
    write_outputs(payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "active_sent_utc": REFERRAL_ACK_SENT_UTC,
                "delivery_failure_count": payload["delivery_reconciliation"][
                    "delivery_failure_count"
                ],
                "response_templates": payload["response_templates"]["artifact"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
