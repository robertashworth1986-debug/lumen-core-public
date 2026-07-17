from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT = ROOT / "grant_submissions" / "funding_sprint_20260709"
JSON_OUT = SPRINT / "FHWA_TSMO_PARTNER_OUTREACH_CONTROL_2026-07-17.json"
MD_OUT = SPRINT / "FHWA_TSMO_PARTNER_OUTREACH_CONTROL_2026-07-17.md"

SUBJECT = "FHWA TSMO Data Initiative (693JJ326R000012) - bounded teaming fit"
BODY = """Hello Ms. Flanigan,

I am reaching out because Cambridge Systematics' published work shows deep FHWA and Transportation Systems Management and Operations program experience. LumenCore is evaluating whether to participate in FHWA solicitation 693JJ326R000012, due August 3, 2026 at 9:00 a.m. ET, only through a qualified prime or team member that can truthfully document the Phase I corporate-experience requirement.

Our proposed contribution is narrow: data-quality controls; chronological, baseline-locked model benchmarking; uncertainty and abstention gates; reproducible evidence manifests; and API-based prototype evaluation. We would not represent Cambridge Systematics as a partner, cite its experience, or use customer information without written agreement and verification.

Is Cambridge Systematics pursuing this opportunity, and if so, would you or the appropriate colleague be open to a 20-30 minute fit check by July 23? The initial call would cover only role fit, corporate-experience eligibility, conflicts, data rights, and schedule. No confidential or patent-sensitive information is needed.

Official opportunity: https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view

If this is not in your lane, a referral to the appropriate federal programs or proposal lead would be appreciated.

Best regards,
Robert Ashworth
Founder and Chief Scientist, LumenCore"""

SENT_UTC = "2026-07-17T10:08:29Z"
MESSAGE_ID_SHA256 = "d27b64996ab87149931992cd81dd1562b996504f0c4dd72e8384564ad0a44752"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_payload() -> dict[str, Any]:
    return {
        "schema": "lumencore.fhwa_tsmo_partner_outreach_control.v1",
        "as_of_date": "2026-07-17",
        "status": "OUTBOUND_SENT_PARTNER_CONFIRMATION_PENDING",
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
            "contact_role": "Vice President and FHWA Office of Operations program manager",
            "recipient_domain": "camsys.com",
            "public_professional_route_verified": True,
            "qualification_basis": [
                "Official company biography describes more than 17 years focused on TSMO.",
                "Official company biography describes leadership of FHWA TSMO work and program management for FHWA Office of Operations contracts.",
                "Official company materials describe transportation data integration, analytics, governance, and ground-truthed findings.",
            ],
            "official_company_sources": [
                "https://camsys.com/blog/people/erin-flanigan",
                "https://camsys.com/services-and-products/data-and-analytics",
            ],
        },
        "pre_send_gates": {
            "official_target_evidence_verified": True,
            "prior_recipient_or_organization_mailbox_matches": 0,
            "mailbox_search_method": "Connected Gmail exact-recipient and organization search before send.",
            "attachment_count": 0,
            "patent_sensitive_material_included": False,
            "partner_relationship_claimed": False,
            "customer_information_requested": False,
            "send_gate_passed": True,
        },
        "outbound": {
            "sent_utc": SENT_UTC,
            "gmail_label_observed": "SENT",
            "message_id_sha256": MESSAGE_ID_SHA256,
            "subject": SUBJECT,
            "subject_sha256": sha256_text(SUBJECT),
            "body_sha256": sha256_text(BODY),
            "body": BODY,
        },
        "response_control": {
            "state": "CONTACTED_NOT_CONFIRMED",
            "qualified_partner_evidence_present": False,
            "bid_posture": "NO_GO_AS_SOLO_PRIME_PARTNER_CONFIRMATION_REQUIRED",
            "send_now": False,
            "do_not_duplicate_send": True,
            "no_follow_up_before": "2026-07-23",
            "next_action": (
                "Monitor for a reply. If Cambridge Systematics responds, verify role, "
                "documentable corporate experience, conflicts, references, facilities, "
                "data rights, and schedule before any teaming or proposal claim."
            ),
        },
        "claim_boundary": (
            "The official company pages support target selection, and the Gmail SENT label plus "
            "hashed message identifier support transmission. They do not establish receipt, "
            "interest, a teaming relationship, permission to cite corporate experience, "
            "independent validation, proposal compliance, submission, award, or funding."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    target = payload["target"]
    response = payload["response_control"]
    outbound = payload["outbound"]
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
        f"Public professional role: {target['contact_role']}",
        "",
    ]
    lines.extend(f"- {item}" for item in target["qualification_basis"])
    lines.extend(
        [
            "",
            "## Transmission Receipt",
            "",
            f"- Sent UTC: `{outbound['sent_utc']}`",
            f"- Recipient domain: `{target['recipient_domain']}`",
            f"- Gmail label observed: `{outbound['gmail_label_observed']}`",
            f"- Message ID SHA-256: `{outbound['message_id_sha256']}`",
            "- Attachments: `0`",
            "",
            "## Message",
            "",
            f"Subject: {outbound['subject']}",
            "",
            outbound["body"],
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


def write_outputs(payload: dict[str, Any]) -> None:
    JSON_OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    MD_OUT.write_text(render_markdown(payload), encoding="utf-8")


def main() -> int:
    payload = build_payload()
    write_outputs(payload)
    print(json.dumps({"status": payload["status"], "sent_utc": SENT_UTC}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
