from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = ROOT / "grant_submissions" / "NASHVILLE_EC_FALL_2026"
APPLICATION_MANIFEST = PACKAGE_DIR / "NASHVILLE_EC_FALL_2026_APPLICATION_MANIFEST_2026-07-16.json"
OUT_JSON = PACKAGE_DIR / "NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json"
OUT_MD = PACKAGE_DIR / "NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.md"

REQUIRED_HUMAN_QUESTION_IDS = {28, 29, 31, 36, 38, 62, 63, 64, 65, 66, 84}
PRIVATE_MARKERS = (
    "full legal name:",
    "signatory email:",
    "signatory telephone:",
    "street address",
    "meeting id",
    "passcode",
    "zoom.us",
    "client_secret",
    "refresh_token",
    "api_key",
    "private key",
)

CLAIM_BOUNDARY = (
    "This artifact reduces a portal fact-check into evidence-supported candidates and explicit founder "
    "attestations. A dated file proves that a named project artifact existed, not continuous full-time work. "
    "Email-thread counts prove bounded communication activity, not customers, sales, validation, or revenue. "
    "No candidate becomes a submitted fact until Robert confirms it in the live portal preview."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_payload(generated_utc: str | None = None) -> dict[str, Any]:
    manifest = read_json(APPLICATION_MANIFEST)
    human_fields = {
        int(row["question_id"]): row
        for row in manifest.get("fields", [])
        if row.get("status") == "HUMAN_CONFIRM_REQUIRED"
    }
    if set(human_fields) != REQUIRED_HUMAN_QUESTION_IDS:
        raise ValueError(
            "Nashville EC human-field schema drift: "
            f"expected {sorted(REQUIRED_HUMAN_QUESTION_IDS)}, found {sorted(human_fields)}"
        )

    evidence_observations = {
        "business_age_floor": {
            "observation": "The earliest LumenCore-named local file found in the bounded metadata scan is dated 2025-07-16.",
            "as_of_date": "2026-07-16",
            "bounded_file_name": "LumenCore_Patent_Cover_Abstract.pdf",
            "bounded_file_bytes": 1972,
            "candidate": "1 to 3 years",
            "strength": "EVIDENCE_SUPPORTED_FOUNDER_CONFIRMATION",
            "limit": "File metadata does not prove the exact business start date or uninterrupted work.",
        },
        "institutional_conversation_floor": {
            "window": "six months ending 2026-07-16",
            "inbound_messages_reviewed": 41,
            "outbound_messages_reviewed": 53,
            "distinct_two_sided_human_threads": 14,
            "distinct_institutional_domains": 8,
            "domains": [
                "cdc.gov",
                "epri.com",
                "evtit.com",
                "lanl.gov",
                "lvlup.vc",
                "uspto.gov",
                "vanderbilt.edu",
                "vynetic.com",
            ],
            "exclusions": [
                "automatic replies",
                "password and account mail",
                "newsletters and one-way marketing",
                "threads without both inbound and outbound human messages",
            ],
            "candidate": "11 to 25",
            "conservative_fallback": "6 to 10",
            "strength": "EVIDENCE_SUPPORTED_CONDITIONAL",
            "decision_rule": (
                "Choose 11 to 25 only if the founder treats the 14 two-sided institutional threads as "
                "distinct qualifying discovery or sales conversations. Otherwise choose 6 to 10."
            ),
            "limit": "Institutional correspondence is not proof of a customer, sale, pilot, or validation.",
        },
        "financial_claim_ledger": {
            "observation": (
                "Current public-safe application, funding, and reviewer artifacts consistently describe "
                "LumenCore as pre-revenue and claim no received grant award or investor capital."
            ),
            "candidate_previous_year_revenue": "$0",
            "candidate_trailing_twelve_month_revenue": "$0",
            "candidate_grant_funds_received": "$0",
            "candidate_investor_capital_received": "$0",
            "strength": "CONSISTENT_WITH_CLAIM_LEDGER_FOUNDER_CONFIRMATION",
            "limit": "The claim ledger is not an accounting system; Robert must confirm the amounts.",
        },
    }

    candidate_answers = [
        {
            "question_ids": [31],
            "labels": [human_fields[31]["label"]],
            "candidate": "1 to 3 years",
            "status": "EVIDENCE_SUPPORTED_FOUNDER_CONFIRMATION",
            "evidence_key": "business_age_floor",
        },
        {
            "question_ids": [84],
            "labels": [human_fields[84]["label"]],
            "candidate": "11 to 25 if each bounded thread is a qualifying conversation; otherwise 6 to 10",
            "status": "EVIDENCE_SUPPORTED_CONDITIONAL",
            "evidence_key": "institutional_conversation_floor",
        },
        {
            "question_ids": [66, 36, 63, 64],
            "labels": [human_fields[qid]["label"] for qid in [66, 36, 63, 64]],
            "candidate": "$0 for each field",
            "status": "CONSISTENT_WITH_CLAIM_LEDGER_FOUNDER_CONFIRMATION",
            "evidence_key": "financial_claim_ledger",
        },
        {
            "question_ids": [38],
            "labels": [human_fields[38]["label"]],
            "candidate": None,
            "status": "FOUNDER_ATTESTATION_ONLY",
            "evidence_key": None,
        },
        {
            "question_ids": [28, 29],
            "labels": [human_fields[qid]["label"] for qid in [28, 29]],
            "candidate": None,
            "status": "FOUNDER_ATTESTATION_ONLY",
            "evidence_key": None,
        },
        {
            "question_ids": [62],
            "labels": [human_fields[62]["label"]],
            "candidate": None,
            "status": "PRIVATE_ACCOUNTING_TOTAL_REQUIRED",
            "evidence_key": None,
        },
        {
            "question_ids": [65],
            "labels": [human_fields[65]["label"]],
            "candidate": None,
            "status": "PRIVATE_ACCOUNTING_TOTAL_REQUIRED",
            "evidence_key": None,
        },
    ]

    confirmation_prompts = [
        {
            "prompt_id": "first_time_founder",
            "reply_line": "First-time founder: YES or NO",
            "covers_question_ids": [38],
        },
        {
            "prompt_id": "full_time_and_hours",
            "reply_line": "Full-time on LumenCore: YES or NO; weekly-hours bracket: [ENTER BRACKET]",
            "covers_question_ids": [28, 29],
        },
        {
            "prompt_id": "conversation_bracket",
            "reply_line": "Discovery/sales conversation bracket: 11-25 or 6-10",
            "covers_question_ids": [84],
        },
        {
            "prompt_id": "zero_financials",
            "reply_line": "Confirm previous-year revenue, trailing-12-month revenue, grants received, and investor capital are all $0: YES or NO",
            "covers_question_ids": [66, 36, 63, 64],
        },
        {
            "prompt_id": "founder_cash",
            "reply_line": "Total founder cash invested in the business: $[ENTER VERIFIED TOTAL]",
            "covers_question_ids": [62],
        },
        {
            "prompt_id": "business_debt",
            "reply_line": "Business debt leveraged to date: $[ENTER BUSINESS DEBT ONLY]",
            "covers_question_ids": [65],
        },
    ]

    payload: dict[str, Any] = {
        "schema": "lumencore.nashville_ec_human_fact_resolution.v1",
        "generated_utc": generated_utc or now_utc(),
        "as_of_date": "2026-07-16",
        "status": "SIX_FOUNDER_CONFIRMATIONS_REQUIRED",
        "source_manifest": rel(APPLICATION_MANIFEST),
        "summary": {
            "required_human_portal_fields": len(human_fields),
            "evidence_supported_candidate_fields": 6,
            "founder_attestation_only_fields": 3,
            "private_accounting_fields": 2,
            "concise_confirmation_prompts": len(confirmation_prompts),
            "optional_demographics_may_be_skipped": True,
            "final_submit_allowed_without_live_preview": False,
        },
        "evidence_observations": evidence_observations,
        "candidate_answers": candidate_answers,
        "confirmation_prompts": confirmation_prompts,
        "optional_demographics": {
            "status": "OPTIONAL_FOUNDER_CHOICE",
            "safe_default": "Leave blank or choose a prefer-not-to-answer option if the portal offers one.",
            "do_not_infer": True,
        },
        "final_action_gate": {
            "all_six_confirmation_prompts_answered": False,
            "portal_preview_reviewed": False,
            "fee_and_terms_reviewed": False,
            "final_submission_authorized_at_action_time": False,
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "outputs": {"json": rel(OUT_JSON), "markdown": rel(OUT_MD)},
    }
    payload["resolution_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Nashville EC Human-Fact Resolution - 2026-07-16",
        "",
        "Direct answer: eleven required portal fields now reduce to six concise founder confirmations. Evidence supports the business-age, conversation-count, and zero-financial candidates, but Robert still owns every final answer.",
        "",
        "## Resolution Summary",
        "",
        f"- Status: `{payload['status']}`",
        f"- Required human portal fields: `{summary['required_human_portal_fields']}`",
        f"- Evidence-supported candidate fields: `{summary['evidence_supported_candidate_fields']}`",
        f"- Founder-attestation-only fields: `{summary['founder_attestation_only_fields']}`",
        f"- Private accounting fields: `{summary['private_accounting_fields']}`",
        f"- Concise confirmation prompts: `{summary['concise_confirmation_prompts']}`",
        f"- Optional demographics may be skipped: `{str(summary['optional_demographics_may_be_skipped']).lower()}`",
        f"- Final submit without live preview: `{str(summary['final_submit_allowed_without_live_preview']).lower()}`",
        f"- Resolution SHA-256: `{payload['resolution_sha256']}`",
        "",
        "## Six-Line Founder Reply",
        "",
        "Reply using these six lines only:",
        "",
        "```text",
    ]
    lines.extend(row["reply_line"] for row in payload["confirmation_prompts"])
    lines.extend(["```", "", "## Evidence-Supported Candidates", ""])

    age = payload["evidence_observations"]["business_age_floor"]
    lines.extend(
        [
            "### Business Age",
            "",
            f"- Candidate: `{age['candidate']}`",
            f"- Basis: {age['observation']}",
            f"- Limit: {age['limit']}",
            "",
        ]
    )
    conversations = payload["evidence_observations"]["institutional_conversation_floor"]
    lines.extend(
        [
            "### Customer Discovery Or Sales Conversations",
            "",
            f"- Two-sided human threads: `{conversations['distinct_two_sided_human_threads']}`",
            f"- Institutional domains: `{conversations['distinct_institutional_domains']}`",
            f"- Candidate bracket: `{conversations['candidate']}`",
            f"- Conservative fallback: `{conversations['conservative_fallback']}`",
            f"- Decision rule: {conversations['decision_rule']}",
            f"- Limit: {conversations['limit']}",
            "",
        ]
    )
    financial = payload["evidence_observations"]["financial_claim_ledger"]
    lines.extend(
        [
            "### Revenue And Received Capital",
            "",
            "- Candidate: previous-year revenue `$0`; trailing-12-month revenue `$0`; grants received `$0`; investor capital received `$0`.",
            f"- Basis: {financial['observation']}",
            f"- Limit: {financial['limit']}",
            "",
            "## Still Founder-Only",
            "",
            "- First-time founder status.",
            "- Full-time status and truthful weekly-hours bracket.",
            "- Cumulative founder cash invested in the business.",
            "- Business debt leveraged, excluding personal debt unless the live form explicitly requires it.",
            "- Whether the 14 bounded threads qualify as 11-25 conversations or should use the conservative 6-10 bracket.",
            "- Final confirmation that all four proposed zero-dollar fields are accurate.",
            "",
            "## Final Gate",
            "",
            "Do not click final submit until all six lines are answered, the complete portal preview is reviewed, and any fee or terms are accepted by Robert at action time.",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def ensure_public_safe(text: str) -> None:
    lowered = text.lower()
    hits = sorted(marker for marker in PRIVATE_MARKERS if marker in lowered)
    if hits:
        raise ValueError(f"Human-fact resolution contains prohibited private markers: {hits}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    ensure_public_safe(json.dumps(payload, sort_keys=True))
    ensure_public_safe(markdown)
    write_json(OUT_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "required_fields": payload["summary"]["required_human_portal_fields"],
                "confirmation_prompts": payload["summary"]["concise_confirmation_prompts"],
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
