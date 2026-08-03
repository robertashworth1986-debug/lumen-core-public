from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "code" / "ops" / "BUILD_OPENAI_BUILD_WEEK_PORTAL_PROGRESS_RECEIPT.py"
RECEIPT_PATH = (
    ROOT
    / "grant_submissions"
    / "OPENAI_BUILD_WEEK_20260721"
    / "OPENAI_BUILD_WEEK_PORTAL_PROGRESS_2026-07-19.json"
)
FIXED_OBSERVED_UTC = "2026-07-19T08:58:00Z"


def load_builder():
    spec = importlib.util.spec_from_file_location("openai_build_week_portal_progress_receipt", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def rehash(builder, payload: dict) -> None:
    payload["facts_sha256"] = builder.stable_hash(payload["normalized_facts"])
    unhashed = copy.deepcopy(payload)
    unhashed.pop("receipt_sha256", None)
    payload["receipt_sha256"] = builder.stable_hash(unhashed)


def collect_mapping_keys(value) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key).lower() for key in value}
        for child in value.values():
            keys.update(collect_mapping_keys(child))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for child in value:
            keys.update(collect_mapping_keys(child))
        return keys
    return set()


def test_receipt_has_two_bounded_evidence_bases_and_hashes_normalized_facts() -> None:
    builder = load_builder()
    receipt = builder.build_receipt(FIXED_OBSERVED_UTC)
    verification = builder.verify_receipt(receipt)

    assert verification["valid"] is True
    assert receipt["evidence_basis_count"] == 2
    assert receipt["facts_sha256"] == builder.stable_hash(receipt["normalized_facts"])

    browser = receipt["normalized_facts"]["browser_confirmation"]
    assert browser["evidence_class"] == "DIRECT_BROWSER_OBSERVATION"
    assert browser["recorded_utc"] == FIXED_OBSERVED_UTC
    assert browser["event_timestamp_utc"] is None
    assert browser["event_time_state"] == "NOT_RECORDED_SEPARATELY"
    assert browser["visible_confirmation_text"] == "ProofLock Console | Draft | 2/5 steps done"
    assert browser["challenge_registration_confirmed"] is True
    assert browser["project_name"] == "ProofLock Console"
    assert browser["project_state"] == "DRAFT"
    assert browser["steps_completed"] == 2
    assert browser["steps_total"] == 5
    assert browser["project_shell_creation_proven"] is True

    gmail = receipt["normalized_facts"]["gmail_confirmation"]
    assert gmail["evidence_class"] == "INDEPENDENT_GMAIL_METADATA"
    assert gmail["message_id"] == "19f795524f98f57a"
    assert gmail["sender"] == "Devpost <support@devpost.com>"
    assert gmail["subject"] == "OpenAI Build Week: You're in!"
    assert gmail["timestamp_utc"] == "2026-07-19T07:44:10Z"
    assert gmail["bounded_confirmation"] == {
        "challenge_registration_confirmed": True,
        "deadline_central": "2026-07-21T19:00:00-05:00",
        "deadline_utc": "2026-07-22T00:00:00Z",
    }
    assert gmail["message_body_retained"] is False
    assert gmail["tracking_links_retained"] is False
    assert gmail["private_account_identifiers_retained"] is False


def test_receipt_rejects_fact_tampering_even_when_attacker_recomputes_hashes() -> None:
    builder = load_builder()
    receipt = builder.build_receipt(FIXED_OBSERVED_UTC)
    tampered = copy.deepcopy(receipt)
    tampered["normalized_facts"]["browser_confirmation"]["visible_confirmation_text"] = "Project created"
    rehash(builder, tampered)

    with pytest.raises(builder.ReceiptValidationError, match="bounded evidence contract"):
        builder.verify_receipt(tampered)


def test_receipt_rejects_closed_or_removed_open_gates_and_never_promotes() -> None:
    builder = load_builder()
    receipt = builder.build_receipt(FIXED_OBSERVED_UTC)

    assert receipt["registration_confirmed"] is True
    assert receipt["project_shell_creation_confirmed"] is True
    assert receipt["final_submission_confirmed"] is False
    assert receipt["ready_for_final_submission"] is False
    assert receipt["open_gate_ids"] == [
        "additional_info_completion",
        "feedback_session_id",
        "final_preview_review",
        "final_submission",
        "project_details_completion",
        "public_youtube_video",
    ]

    tampered = copy.deepcopy(receipt)
    tampered["open_gate_ids"].remove("project_details_completion")
    rehash(builder, tampered)
    with pytest.raises(builder.ReceiptValidationError, match="open-gate contract changed"):
        builder.verify_receipt(tampered)

    promoted = copy.deepcopy(receipt)
    promoted["ready_for_final_submission"] = True
    rehash(builder, promoted)
    with pytest.raises(builder.ReceiptValidationError, match="fail closed"):
        builder.verify_receipt(promoted)


def test_writer_is_deterministic_for_explicit_timestamp_and_checked_in_receipt_verifies(tmp_path: Path) -> None:
    builder = load_builder()
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    builder.write_receipt(FIXED_OBSERVED_UTC, first)
    builder.write_receipt(FIXED_OBSERVED_UTC, second)
    assert first.read_bytes() == second.read_bytes()

    checked_in = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    assert builder.verify_receipt(checked_in)["valid"] is True
    serialized = json.dumps(checked_in, sort_keys=True)
    assert "utm_" not in serialized.lower()
    assert "tracking_url" not in serialized.lower()
    assert "account_id" not in collect_mapping_keys(checked_in)
    assert "account_identifier" not in collect_mapping_keys(checked_in)
