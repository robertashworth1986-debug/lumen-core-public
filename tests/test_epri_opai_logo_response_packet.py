from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_EPRI_OPAI_LOGO_RESPONSE_PACKET.py"
JSON_PACKET = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "EPRI_OPAI_LOGO_RESPONSE_PACKET_2026-07-25.json"
)
MD_PACKET = JSON_PACKET.with_suffix(".md")

EXPECTED_ASSETS = {
    "dashboard/brand/lumencore_logo_on_dark_1024.png": {
        "file_bytes": 105408,
        "sha256": (
            "2829e259a38f1d3914f80a6a688f13ce0d80513278fccf869d47ff77d270a62c"
        ),
    },
    "dashboard/brand/lumencore_logo_on_light_1024.png": {
        "file_bytes": 105988,
        "sha256": (
            "7b14dcf7bb72c78eac7f73f6c0da76e229cb8329040160fcc9fcff4d3d2fe5e5"
        ),
    },
}


def load_module():
    spec = importlib.util.spec_from_file_location("epri_logo_response_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def canonical_sha256_without_seal(packet: dict) -> str:
    unhashed = {key: value for key, value in packet.items() if key != "packet_sha256"}
    canonical = json.dumps(
        unhashed,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def test_builder_verifies_exact_canonical_png_metadata():
    module = load_module()
    packet = module.build_packet(generated_utc="2026-07-25T23:59:00Z")

    assert packet["status"] == (
        "LOGO_PAIR_SENT_ONCE_POST_SEND_VERIFIED_DO_NOT_RESEND"
    )
    assert packet["summary"]["ready_asset_count"] == 2
    assert len(packet["assets"]) == 2
    for asset in packet["assets"]:
        expected = EXPECTED_ASSETS[asset["path"]]
        assert asset["exists"] is True
        assert asset["png_signature_hex"] == "89504e470d0a1a0a"
        assert asset["png_signature_valid"] is True
        assert asset["ihdr_present"] is True
        assert (asset["width"], asset["height"]) == (1024, 1024)
        assert asset["exact_dimensions_valid"] is True
        assert asset["file_bytes"] == expected["file_bytes"]
        assert asset["sha256"] == expected["sha256"]
        assert asset["ready"] is True
        assert asset["blockers"] == []


def test_packet_uses_matching_registry_template_and_binds_bounded_reply():
    module = load_module()
    packet = module.build_packet(generated_utc="2026-07-25T23:59:00Z")
    match = packet["template_match"]
    reply = packet["bounded_reply"]

    assert match["requested_template_id"] == "REQUESTED_ASSET_DELIVERY_REPLY"
    assert match["matching_template_exists"] is True
    assert match["match_status"] == "MATCHED"
    assert match["template_gap"] is None
    assert match["attachment_policy"] == "EXPLICIT_REQUEST_ONLY"
    assert match["send_policy"] == "REPLY_AFTER_FACT_REVIEW"
    assert match["private_render_only"] is True
    assert reply["subject"] == (
        "Re: [EXTERNAL] LumenCore Open Power AI onboarding follow-up"
    )
    assert "Attached are only the materials explicitly requested" in reply["body"]
    assert "lumencore_logo_on_dark_1024.png" in reply["body"]
    assert "lumencore_logo_on_light_1024.png" in reply["body"]
    assert module.PERMITTED_USE_MARKER in reply["body"]
    assert reply["body"].endswith("Robert Ashworth\nFounder\nLumenCore")
    assert reply["recipient_addresses_embedded"] is False
    assert reply["routing_values_embedded"] is False
    assert reply["send_or_draft_performed"] is True
    assert reply["render_status"] == (
        "HISTORICAL_PRE_SEND_COPY_SUPERSEDED_BY_SEND_RECEIPT"
    )


def test_packet_preserves_prior_response_and_duplicate_send_state():
    module = load_module()
    packet = module.build_packet(generated_utc="2026-07-25T23:59:00Z")

    assert packet["summary"][
        "prior_contact_work_group_and_permission_response_sent"
    ] is True
    prior = packet["prior_response_state"]
    assert prior["primary_contact_sent"] is True
    assert prior["work_group_representatives_sent"] is True
    assert prior["logo_permission_sent"] is True
    assert prior["logo_files_sent_in_recorded_state"] is True
    assert prior["repeat_prior_answers_in_reply"] is False

    duplicate = packet["duplicate_send_decision"]
    assert duplicate["decision"] == "BLOCK_SEND_ALREADY_SENT_ONCE"
    assert duplicate["recorded_logo_files_sent"] is True
    assert duplicate["fresh_full_thread_check_required"] is False
    assert set(duplicate["do_not_repeat"]) == {
        "primary contact facts",
        "work-group representative facts",
        "logo permission answer",
    }
    identity_source = packet["source_evidence"]["public_identity_authority"]
    assert identity_source["path"] == (
        "docs/PUBLIC_VISIBILITY_AND_SOURCE_AUTHORITY_2026-06-20.md"
    )
    assert identity_source["file_bytes"] > 0
    assert re.fullmatch(r"[0-9a-f]{64}", identity_source["sha256"])


def test_packet_allows_only_two_logos_and_requires_human_action_time_gate():
    module = load_module()
    packet = module.build_packet(generated_utc="2026-07-25T23:59:00Z")
    attachment = packet["attachment_control"]
    gates = packet["action_gates"]

    assert attachment["explicit_request_recorded"] is True
    assert attachment["attachment_count"] == 2
    assert set(attachment["attachment_allowlist"]) == set(EXPECTED_ASSETS)
    assert attachment["additional_attachments_allowed"] is False

    assert gates["fresh_full_thread_check_required"] is False
    assert gates["exact_action_time_approval_required"] is False
    assert gates["external_send_allowed_without_action_time_approval"] is False
    assert gates["email_access_performed"] is True
    assert gates["email_draft_created"] is False
    assert gates["email_sent"] is True
    assert gates["invitation_accepted"] is False
    assert gates["meeting_credentials_used"] is False
    assert gates["external_action_performed"] is True

    missing = {fact["fact_id"]: fact["status"] for fact in packet["missing_facts"]}
    assert missing == {}
    assert packet["summary"]["logo_pair_sent_verified"] is True
    assert packet["send_status_checks"]
    assert all(packet["send_status_checks"].values())


def test_packet_contains_no_recipient_address_message_id_or_meeting_secret():
    module = load_module()
    packet = module.build_packet(generated_utc="2026-07-25T23:59:00Z")
    serialized = json.dumps(packet, sort_keys=True)
    lowered = serialized.lower()

    assert re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", serialized, re.I) is None
    assert "recipient_email" not in lowered
    assert "source_message_id" not in lowered
    assert "meeting id" not in lowered
    assert "passcode" not in lowered
    assert "password" not in lowered
    assert "otp" not in lowered


def test_packet_is_self_hashed_and_generated_artifacts_match():
    packet = json.loads(JSON_PACKET.read_text(encoding="utf-8"))
    markdown = MD_PACKET.read_text(encoding="utf-8")

    assert packet["packet_sha256"] == canonical_sha256_without_seal(packet)
    assert packet["packet_sha256"] in markdown
    assert packet["status"] in markdown
    for path, expected in EXPECTED_ASSETS.items():
        assert path in markdown
        assert expected["sha256"] in markdown
        assert str(expected["file_bytes"]) in markdown


def test_writer_creates_only_requested_json_and_markdown(tmp_path):
    module = load_module()
    packet = module.build_packet(generated_utc="2026-07-25T23:59:00Z")
    json_out = tmp_path / "packet.json"
    md_out = tmp_path / "packet.md"

    module.write_packet(packet, json_out=json_out, md_out=md_out)

    assert {path.name for path in tmp_path.iterdir()} == {"packet.json", "packet.md"}
    assert json.loads(json_out.read_text(encoding="utf-8")) == packet
    assert packet["packet_sha256"] in md_out.read_text(encoding="utf-8")


def test_builder_has_no_external_action_implementation():
    source = SCRIPT.read_text(encoding="utf-8").lower()

    for forbidden_import in (
        "import requests",
        "import smtplib",
        "import imaplib",
        "import socket",
        "import subprocess",
        "from gmail",
    ):
        assert forbidden_import not in source
    for forbidden_call in (
        ".send_message(",
        ".create_draft(",
        "accept_invitation(",
    ):
        assert forbidden_call not in source
