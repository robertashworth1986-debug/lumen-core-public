from __future__ import annotations

import argparse
import hashlib
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = (
    ROOT
    / "grant_submissions"
    / "OPENAI_BUILD_WEEK_20260721"
    / "OPENAI_BUILD_WEEK_PORTAL_PROGRESS_2026-07-19.json"
)

CHALLENGE_ID = "30223-openai-build-week"
PROJECT_DETAILS_URL = (
    "https://devpost.com/submit-to/30223-openai-build-week/manage/submissions/"
    "1104232-prooflock-console/project_details/edit"
)
DEADLINE_CENTRAL = "2026-07-21T19:00:00-05:00"
DEADLINE_UTC = "2026-07-22T00:00:00Z"

GMAIL_MESSAGE_METADATA = {
    "message_id": "19f795524f98f57a",
    "sender": "Devpost <support@devpost.com>",
    "subject": "OpenAI Build Week: You're in!",
    "timestamp_utc": "2026-07-19T07:44:10Z",
}

EXPECTED_OPEN_GATES = [
    "additional_info_completion",
    "feedback_session_id",
    "final_preview_review",
    "final_submission",
    "project_details_completion",
    "public_youtube_video",
]

CLAIM_BOUNDARY = (
    "Two independent evidence bases confirm challenge registration and the stated deadline, and a direct "
    "browser observation confirms a ProofLock Console project draft at two of five portal steps. They do not "
    "prove completed project details, completed additional information, a /feedback Session ID, a public video, "
    "final preview approval, final submission, judging, "
    "endorsement, award, external validation, funding, patent rights, or value."
)


class ReceiptValidationError(ValueError):
    pass


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def normalize_utc(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReceiptValidationError("observed timestamp must be a non-empty ISO-8601 string")
    candidate = value.strip()
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReceiptValidationError(f"invalid observed timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ReceiptValidationError("observed timestamp must include a UTC offset")
    parsed = parsed.astimezone(timezone.utc)
    if parsed.microsecond:
        rendered = parsed.isoformat(timespec="microseconds")
    else:
        rendered = parsed.isoformat(timespec="seconds")
    return rendered.replace("+00:00", "Z")


def build_normalized_facts(observed_utc: str) -> dict[str, Any]:
    observed_utc = normalize_utc(observed_utc)
    return {
        "browser_confirmation": {
            "evidence_id": "devpost_browser_project_draft_confirmation",
            "evidence_class": "DIRECT_BROWSER_OBSERVATION",
            "recorded_utc": observed_utc,
            "event_timestamp_utc": None,
            "event_time_state": "NOT_RECORDED_SEPARATELY",
            "challenge_id": CHALLENGE_ID,
            "page_url": PROJECT_DETAILS_URL,
            "visible_confirmation_text": "ProofLock Console | Draft | 2/5 steps done",
            "challenge_registration_confirmed": True,
            "signed_in_portal_observed": True,
            "project_name": "ProofLock Console",
            "project_state": "DRAFT",
            "steps_completed": 2,
            "steps_total": 5,
            "current_section": "Project details",
            "project_shell_creation_proven": True,
            "final_submission_proven": False,
        },
        "gmail_confirmation": {
            "evidence_id": "devpost_gmail_registration_confirmation",
            "evidence_class": "INDEPENDENT_GMAIL_METADATA",
            **GMAIL_MESSAGE_METADATA,
            "bounded_confirmation": {
                "challenge_registration_confirmed": True,
                "deadline_central": DEADLINE_CENTRAL,
                "deadline_utc": DEADLINE_UTC,
            },
            "message_body_retained": False,
            "tracking_links_retained": False,
            "private_account_identifiers_retained": False,
        },
    }


def build_receipt(observed_utc: str) -> dict[str, Any]:
    normalized_facts = build_normalized_facts(observed_utc)
    receipt: dict[str, Any] = {
        "schema": "lumencore.openai_build_week_portal_progress_receipt.v1",
        "recorded_observation_utc": normalize_utc(observed_utc),
        "status": "PROJECT_DRAFT_2_OF_5_VIDEO_FEEDBACK_OPEN",
        "challenge": {
            "challenge_id": CHALLENGE_ID,
            "deadline_central": DEADLINE_CENTRAL,
            "deadline_utc": DEADLINE_UTC,
        },
        "normalized_facts": normalized_facts,
        "facts_sha256": stable_hash(normalized_facts),
        "derived_states": {
            "challenge_registration": {
                "state": "CONFIRMED",
                "classification": "EVIDENCE_SUPPORTED_DERIVATION",
                "basis_ids": [
                    "devpost_browser_project_draft_confirmation",
                    "devpost_gmail_registration_confirmation",
                ],
            },
            "project_shell_creation": {
                "state": "CONFIRMED",
                "classification": "DIRECT_BROWSER_OBSERVATION",
                "basis_ids": ["devpost_browser_project_draft_confirmation"],
            },
            "final_submission": {
                "state": "NOT_PROVEN",
                "classification": "FAIL_CLOSED_STATUS",
                "basis_ids": [],
            },
        },
        "evidence_basis_count": 2,
        "registration_confirmed": True,
        "project_shell_creation_confirmed": True,
        "final_submission_confirmed": False,
        "ready_for_final_submission": False,
        "open_gate_ids": EXPECTED_OPEN_GATES,
        "privacy_controls": {
            "gmail_metadata_only": True,
            "tracking_links_excluded": True,
            "private_account_identifiers_excluded": True,
        },
        "claim_boundary": CLAIM_BOUNDARY,
    }
    receipt["receipt_sha256"] = stable_hash(receipt)
    return receipt


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReceiptValidationError(message)


def verify_receipt(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ReceiptValidationError("portal progress receipt must be a JSON object")

    observed_utc = normalize_utc(str(payload.get("recorded_observation_utc") or ""))
    expected_facts = build_normalized_facts(observed_utc)
    observed_facts = payload.get("normalized_facts")
    _require(observed_facts == expected_facts, "normalized portal facts differ from the bounded evidence contract")
    _require(payload.get("facts_sha256") == stable_hash(observed_facts), "normalized facts hash is invalid")

    unhashed = deepcopy(payload)
    recorded_receipt_hash = unhashed.pop("receipt_sha256", None)
    _require(
        isinstance(recorded_receipt_hash, str) and recorded_receipt_hash == stable_hash(unhashed),
        "portal progress receipt hash is invalid",
    )

    _require(
        payload.get("schema") == "lumencore.openai_build_week_portal_progress_receipt.v1",
        "unexpected portal progress receipt schema",
    )
    _require(payload.get("status") == "PROJECT_DRAFT_2_OF_5_VIDEO_FEEDBACK_OPEN", "unsafe receipt status")
    _require(payload.get("evidence_basis_count") == 2, "two independent evidence bases are required")
    _require(payload.get("registration_confirmed") is True, "challenge registration is not confirmed")
    _require(payload.get("project_shell_creation_confirmed") is True, "project creation is not confirmed")
    _require(payload.get("final_submission_confirmed") is False, "final submission must remain unproven")
    _require(payload.get("ready_for_final_submission") is False, "receipt must fail closed")
    _require(payload.get("open_gate_ids") == EXPECTED_OPEN_GATES, "open-gate contract changed")
    _require(payload.get("claim_boundary") == CLAIM_BOUNDARY, "claim boundary changed")
    _require(
        payload.get("derived_states", {}).get("project_shell_creation", {}).get("state") == "CONFIRMED",
        "project-shell state must remain CONFIRMED",
    )
    _require(
        payload.get("derived_states", {}).get("final_submission", {}).get("state") == "NOT_PROVEN",
        "final-submission state must remain NOT_PROVEN",
    )

    return {
        "valid": True,
        "receipt_sha256": recorded_receipt_hash,
        "facts_sha256": payload["facts_sha256"],
        "evidence_basis_count": 2,
        "registration_confirmed": True,
        "project_shell_creation_confirmed": True,
        "final_submission_confirmed": False,
        "open_gate_ids": list(EXPECTED_OPEN_GATES),
    }


def load_and_verify(path: Path = OUTPUT_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptValidationError(f"unable to read portal progress receipt: {path}") from exc
    verify_receipt(payload)
    return payload


def write_receipt(observed_utc: str, output_path: Path = OUTPUT_PATH) -> Path:
    payload = build_receipt(observed_utc)
    verify_receipt(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(f".{output_path.name}.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the bounded OpenAI Build Week portal-progress receipt."
    )
    parser.add_argument(
        "--observed-utc",
        required=True,
        help="Explicit ISO-8601 timestamp recording the direct browser observation.",
    )
    args = parser.parse_args()
    path = write_receipt(args.observed_utc)
    payload = load_and_verify(path)
    print(
        json.dumps(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "receipt_sha256": payload["receipt_sha256"],
                "facts_sha256": payload["facts_sha256"],
                "status": payload["status"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
