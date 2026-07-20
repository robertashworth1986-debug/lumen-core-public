from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SUBMISSION_DIR = ROOT / "grant_submissions" / "NASHVILLE_EC_FALL_2026"
PRIVATE_DIR = SUBMISSION_DIR / "private"
PUBLIC_JSON = SUBMISSION_DIR / "NASHVILLE_EC_FINANCIAL_AID_ACTION_2026-07-20.json"
PUBLIC_MD = SUBMISSION_DIR / "NASHVILLE_EC_FINANCIAL_AID_ACTION_2026-07-20.md"

PUBLIC_SCHEMA = "lumencore.nashville_ec_financial_aid_action.v1"
PRIVATE_SCHEMA = "lumencore.nashville_ec_financial_aid_private_response.v1"
FOUNDER_FACTS_SCHEMA = "lumencore.nashville_ec_private_founder_facts.v1"

REQUEST_RECEIVED_UTC = "2026-07-20T19:52:03Z"
FORM_OBSERVED_UTC = "2026-07-20T23:36:30Z"
DEADLINE_DATE = "2026-07-22"
FEE_COVERAGE_OPTIONS = (
    "None of it",
    "Part of it",
    "I can pay in full - I just need to confirm my spot",
)
OUTSIDE_CAPITAL_OPTIONS = ("Yes", "No")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def private_output_allowed(path: Path) -> bool:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return True
    try:
        resolved.relative_to(PRIVATE_DIR.resolve())
    except ValueError:
        return False
    return True


def build_public_action() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": PUBLIC_SCHEMA,
        "status": "FINANCIAL_AID_FORM_REQUEST_RECEIVED_ACTION_OPEN",
        "organization": "Nashville Entrepreneur Center",
        "program": "Fall 2026 TakeOff accelerator",
        "source": {
            "channel": "CONNECTED_GMAIL_INBOUND",
            "received_utc": REQUEST_RECEIVED_UTC,
            "sender_role": "Program Manager",
            "subject": "Following Up on Your Accelerator Application",
            "private_source_identifier_recorded": False,
            "private_form_url_recorded": False,
        },
        "deadline": {
            "date": DEADLINE_DATE,
            "weekday": "Wednesday",
            "time": None,
            "timezone": None,
            "time_status": "NOT_STATED_IN_MESSAGE",
            "timezone_status": "NOT_STATED_IN_MESSAGE",
            "internal_finish_target": "2026-07-21T17:00:00-05:00",
            "internal_finish_target_status": "INTERNAL_TARGET_NOT_OFFICIAL_DEADLINE",
        },
        "live_form_observation": {
            "observed_utc": FORM_OBSERVED_UTC,
            "method": "NON_SUBMITTING_BROWSER_DOM_INSPECTION",
            "required_identity_field_count": 2,
            "required_financial_question_count": 3,
            "optional_context_field_count": 1,
            "required_fields": [
                {"field": "First Name", "control": "TEXT"},
                {"field": "Last Name", "control": "TEXT"},
                {
                    "field": "How much of the program fee can you cover right now?",
                    "control": "SELECT",
                    "options": list(FEE_COVERAGE_OPTIONS),
                },
                {
                    "field": "What is your current monthly revenue?",
                    "control": "CURRENCY",
                },
                {
                    "field": "Have you raised any outside capital in the last 12 months?",
                    "control": "SELECT",
                    "options": list(OUTSIDE_CAPITAL_OPTIONS),
                },
            ],
            "optional_fields": [
                {
                    "field": "Anything about your situation you'd like us to know?",
                    "control": "RICH_TEXT",
                }
            ],
            "form_submitted_during_observation": False,
        },
        "routing": {
            "email_reply_required": False,
            "initial_application_resubmission_required": False,
            "financial_aid_form_action_required": True,
            "duplicate_application_send_allowed": False,
            "final_form_submit_human_gated": True,
            "builder_can_submit_form": False,
        },
        "claim_boundary": (
            "This receipt records a connected-mailbox request and a non-submitting live "
            "form-schema observation. It does not prove that the financial-aid form was "
            "completed or submitted, that aid will be awarded, that the accelerator "
            "application was accepted, or that any financial statement was independently "
            "verified."
        ),
    }
    payload["action_receipt_sha256"] = stable_hash(payload)
    return payload


def validate_public_action(payload: dict[str, Any]) -> None:
    if payload.get("schema") != PUBLIC_SCHEMA:
        raise ValueError("Financial-aid action schema is invalid")
    if payload.get("status") != "FINANCIAL_AID_FORM_REQUEST_RECEIVED_ACTION_OPEN":
        raise ValueError("Financial-aid action status is invalid")
    deadline = payload.get("deadline", {})
    if (
        deadline.get("date") != DEADLINE_DATE
        or deadline.get("time") is not None
        or deadline.get("timezone") is not None
        or deadline.get("time_status") != "NOT_STATED_IN_MESSAGE"
        or deadline.get("timezone_status") != "NOT_STATED_IN_MESSAGE"
    ):
        raise ValueError("Financial-aid deadline uncertainty is not preserved")
    observation = payload.get("live_form_observation", {})
    if (
        observation.get("required_identity_field_count") != 2
        or observation.get("required_financial_question_count") != 3
        or observation.get("optional_context_field_count") != 1
        or observation.get("form_submitted_during_observation") is not False
    ):
        raise ValueError("Financial-aid form schema is incomplete")
    routing = payload.get("routing", {})
    if (
        routing.get("email_reply_required") is not False
        or routing.get("initial_application_resubmission_required") is not False
        or routing.get("financial_aid_form_action_required") is not True
        or routing.get("duplicate_application_send_allowed") is not False
        or routing.get("final_form_submit_human_gated") is not True
        or routing.get("builder_can_submit_form") is not False
    ):
        raise ValueError("Financial-aid routing does not fail closed")
    expected = stable_hash(
        {key: value for key, value in payload.items() if key != "action_receipt_sha256"}
    )
    if payload.get("action_receipt_sha256") != expected:
        raise ValueError("Financial-aid action receipt hash is invalid")


def build_private_response(
    founder_facts: dict[str, Any],
    *,
    fee_coverage: str | None = None,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    if founder_facts.get("schema") != FOUNDER_FACTS_SCHEMA:
        raise ValueError(f"Founder facts schema must be {FOUNDER_FACTS_SCHEMA}")
    if founder_facts.get("zero_financials_confirmed") is not True:
        raise ValueError("Zero revenue and outside-capital facts require founder confirmation")
    if fee_coverage is not None and fee_coverage not in FEE_COVERAGE_OPTIONS:
        raise ValueError("Program-fee coverage must match a live form option")

    fee_status = (
        "FOUNDER_CONFIRMED" if fee_coverage is not None else "FOUNDER_CONFIRMATION_REQUIRED"
    )
    fee_context = {
        None: (
            "Financial aid would materially affect my ability to participate. I will "
            "confirm the amount I can cover before submitting this form."
        ),
        "None of it": (
            "I cannot cover the program fee right now, so financial aid would determine "
            "whether I can participate."
        ),
        "Part of it": (
            "I can cover part of the program fee, and financial aid for the remaining "
            "amount would determine whether I can participate."
        ),
        "I can pay in full - I just need to confirm my spot": (
            "I can pay the program fee in full and am using this form to confirm my spot."
        ),
    }[fee_coverage]
    payload: dict[str, Any] = {
        "schema": PRIVATE_SCHEMA,
        "generated_utc": generated_utc or now_utc(),
        "status": (
            "READY_FOR_FOUNDER_REVIEW_AND_SUBMIT"
            if fee_coverage is not None
            else "PROGRAM_FEE_COVERAGE_CONFIRMATION_REQUIRED"
        ),
        "private_portal_only": True,
        "public_repo_publish_allowed": False,
        "answers": [
            {
                "field": "First Name",
                "value": "Robert",
                "status": "EXISTING_APPLICATION_IDENTITY",
            },
            {
                "field": "Last Name",
                "value": "Ashworth",
                "status": "EXISTING_APPLICATION_IDENTITY",
            },
            {
                "field": "How much of the program fee can you cover right now?",
                "value": fee_coverage or "None of it",
                "status": fee_status,
                "note": (
                    "None of it is the conservative candidate because the submitted "
                    "application recorded no current fee commitment. Confirm the live "
                    "answer before selecting it."
                ),
            },
            {
                "field": "What is your current monthly revenue?",
                "value_usd": 0,
                "status": "FOUNDER_FACTS_CONFIRMED",
            },
            {
                "field": "Have you raised any outside capital in the last 12 months?",
                "value": "No",
                "status": "FOUNDER_FACTS_CONFIRMED",
            },
            {
                "field": "Anything about your situation you'd like us to know?",
                "value": (
                    "I am a pre-revenue, self-funded solo founder with no outside capital. "
                    "I have personally covered the hardware, software, internet, and AI "
                    f"expenses required to build the working prototype. {fee_context}"
                ),
                "status": (
                    "OPTIONAL_FOUNDER_REVIEW_REQUIRED"
                    if fee_coverage is not None
                    else "PROGRAM_FEE_COVERAGE_CONFIRMATION_REQUIRED"
                ),
            },
        ],
        "source_fact_summary": {
            "first_time_founder": founder_facts.get("first_time_founder"),
            "monthly_revenue_usd": 0,
            "outside_capital_last_12_months": False,
            "founder_cash_invested_usd": founder_facts.get(
                "founder_cash_invested_usd"
            ),
            "business_debt_usd": founder_facts.get("business_debt_usd"),
            "founder_cash_is_not_revenue_or_outside_capital": True,
        },
        "final_action_gate": {
            "program_fee_coverage_confirmed": fee_coverage is not None,
            "all_required_answers_assembled": fee_coverage is not None,
            "live_form_preview_reviewed": False,
            "final_submission_authorized_at_action_time": False,
            "submission_performed": False,
        },
        "claim_boundary": (
            "This private worksheet translates founder-confirmed facts into the observed "
            "financial-aid form fields. It does not independently verify those facts, "
            "submit the form, accept program terms, or establish an aid or accelerator "
            "decision."
        ),
    }
    payload["private_response_sha256"] = stable_hash(payload)
    return payload


def render_public_markdown(payload: dict[str, Any]) -> str:
    deadline = payload["deadline"]
    observation = payload["live_form_observation"]
    return "\n".join(
        [
            "# Nashville EC Financial Aid Action",
            "",
            f"- Status: `{payload['status']}`",
            f"- Request received UTC: `{payload['source']['received_utc']}`",
            f"- Deadline date: `{deadline['date']}`",
            "- Official deadline time: `not stated`",
            "- Official deadline timezone: `not stated`",
            f"- Internal finish target: `{deadline['internal_finish_target']}`",
            f"- Required identity fields: `{observation['required_identity_field_count']}`",
            f"- Required financial questions: `{observation['required_financial_question_count']}`",
            f"- Optional context fields: `{observation['optional_context_field_count']}`",
            "- Email reply required: `false`",
            "- Initial application resubmission required: `false`",
            "- Final form submission remains founder-gated: `true`",
            f"- Action receipt SHA-256: `{payload['action_receipt_sha256']}`",
            "",
            "## Required Form Questions",
            "",
            "1. Program-fee amount the founder can cover now.",
            "2. Current monthly revenue.",
            "3. Outside capital raised during the last 12 months.",
            "",
            "## Routing",
            "",
            "Complete the separate financial-aid form from the existing inbound email. "
            "Do not resubmit the accelerator application and do not send an email reply "
            "unless the program manager asks a separate question.",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )


def render_private_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Nashville EC Financial Aid Private Response",
        "",
        f"- Status: `{payload['status']}`",
        f"- Generated UTC: `{payload['generated_utc']}`",
        f"- SHA-256: `{payload['private_response_sha256']}`",
        "",
    ]
    for row in payload["answers"]:
        value = row.get("value", row.get("value_usd"))
        lines.extend(
            [
                f"## {row['field']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Candidate answer: {value}",
                *((f"- Note: {row['note']}",) if row.get("note") else ()),
                "",
            ]
        )
    lines.extend(
        [
            "## Final Action Gate",
            "",
            "- Confirm the program-fee coverage selection.",
            "- Review the optional context sentence for accuracy.",
            "- Review the live form preview.",
            "- The founder personally controls final Submit.",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def mirror_private_response(
    private_json: Path,
    private_markdown: Path,
    destination_root: Path,
    *,
    generated_utc: str | None = None,
) -> tuple[dict[str, Any], Path, Path]:
    destination_root = destination_root.resolve()
    if destination_root == ROOT.resolve() or destination_root.is_relative_to(
        ROOT.resolve()
    ):
        raise ValueError("Private mirror destination must remain outside the public repository")
    if not destination_root.parent.exists():
        raise ValueError(
            f"Private mirror parent is unavailable: {destination_root.parent}"
        )

    destination_root.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []
    for source in (private_json.resolve(), private_markdown.resolve()):
        if not source.is_file():
            raise ValueError(f"Private response artifact is missing: {source.name}")
        destination = (destination_root / source.name).resolve()
        if not destination.is_relative_to(destination_root):
            raise ValueError(f"Unsafe private mirror destination: {destination}")
        shutil.copy2(source, destination)
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        destination_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
        if (
            source_hash != destination_hash
            or source.stat().st_size != destination.stat().st_size
        ):
            raise ValueError(f"Private mirror verification failed: {source.name}")
        artifacts.append(
            {
                "source_name": source.name,
                "destination_name": destination.name,
                "bytes": source.stat().st_size,
                "sha256": source_hash,
                "copy_sha256_matched": True,
            }
        )

    payload: dict[str, Any] = {
        "schema": "lumencore.private_bounded_mirror_receipt.v1",
        "generated_utc": generated_utc or now_utc(),
        "destination_root": destination_root.as_posix(),
        "artifact_count": len(artifacts),
        "all_sha256_matched_after_copy": True,
        "private_values_present": True,
        "public_repo_publish_allowed": False,
        "artifacts": artifacts,
        "claim_boundary": (
            "This private receipt proves only copy integrity for the two private response "
            "artifacts. It does not prove form submission, financial-aid approval, "
            "accelerator selection, funding, or independent verification of the answers."
        ),
    }
    local_receipt = (
        private_json.parent
        / "nashville_ec_financial_aid_private_e_drive_sync_receipt.json"
    )
    mirror_receipt = destination_root / local_receipt.name
    write_json(local_receipt, payload)
    shutil.copy2(local_receipt, mirror_receipt)
    if hashlib.sha256(local_receipt.read_bytes()).hexdigest() != hashlib.sha256(
        mirror_receipt.read_bytes()
    ).hexdigest():
        raise ValueError("Private mirror receipt self-copy hash mismatch")
    return payload, local_receipt, mirror_receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the public-safe Nashville EC financial-aid action receipt."
    )
    parser.add_argument("--public-json", type=Path, default=PUBLIC_JSON)
    parser.add_argument("--private-facts", type=Path)
    parser.add_argument("--private-output", type=Path)
    parser.add_argument("--private-mirror-root", type=Path)
    parser.add_argument("--fee-coverage", choices=FEE_COVERAGE_OPTIONS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    public_payload = build_public_action()
    validate_public_action(public_payload)
    public_json = args.public_json.resolve()
    public_md = public_json.with_suffix(".md")
    write_json(public_json, public_payload)
    public_md.write_text(render_public_markdown(public_payload), encoding="utf-8")

    result: dict[str, Any] = {
        "status": public_payload["status"],
        "public_json": str(public_json),
        "public_markdown": str(public_md),
        "action_receipt_sha256": public_payload["action_receipt_sha256"],
        "private_response_written": False,
    }
    if (
        args.private_facts
        or args.private_output
        or args.private_mirror_root
        or args.fee_coverage
    ):
        if not args.private_facts or not args.private_output:
            raise SystemExit(
                "--private-facts and --private-output are both required for a private response"
            )
        private_output = args.private_output.resolve()
        private_md = private_output.with_suffix(".md")
        if not private_output_allowed(private_output) or not private_output_allowed(
            private_md
        ):
            raise SystemExit(
                "Refusing to write private financial answers into a tracked repository path"
            )
        private_payload = build_private_response(
            read_json(args.private_facts), fee_coverage=args.fee_coverage
        )
        write_json(private_output, private_payload)
        private_md.write_text(render_private_markdown(private_payload), encoding="utf-8")
        result.update(
            {
                "private_response_written": True,
                "private_status": private_payload["status"],
                "private_output": str(private_output),
                "private_markdown": str(private_md),
                "private_response_sha256": private_payload[
                    "private_response_sha256"
                ],
            }
        )
        if args.private_mirror_root:
            mirror_payload, local_receipt, mirror_receipt = mirror_private_response(
                private_output,
                private_md,
                args.private_mirror_root,
            )
            result.update(
                {
                    "private_mirror_status": "PRIVATE_E_DRIVE_MIRROR_VERIFIED",
                    "private_mirror_artifact_count": mirror_payload["artifact_count"],
                    "private_mirror_receipt": str(local_receipt),
                    "private_mirror_receipt_copy": str(mirror_receipt),
                }
            )

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
