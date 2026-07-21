from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "EPRI_OPEN_POWER_AI_MOU_RESPONSE_TEMPLATE_2026-07-16.md"
)
SYNC_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "CURRENT_ACTION_CONTROL_E_DRIVE_SYNC_RECEIPT_2026-07-16.json"
)
ENGAGEMENT_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "EPRI_OPEN_POWER_AI_MOU_ENGAGEMENT_RECEIPT_2026-07-16.json"
)
PRIVATE_STREET_PATTERN = re.compile(
    r"\b\d{1,6}\s+[A-Za-z0-9 .'-]+\s(?:st|street|rd|road|dr|drive|ave|avenue|ln|lane|blvd|way|ct|court)\b",
    re.IGNORECASE,
)


def test_epri_response_is_routed_and_duplicate_send_gated():
    text = TEMPLATE.read_text(encoding="utf-8")

    assert "SENT_VERIFIED_RESPONSE_PENDING" in text
    assert "SENT_VERIFIED" in text
    assert "Duplicate-send gate: `CLOSED`" in text
    for address in (
        "MDahl@epri.com",
        "SToews@epri.com",
        "OpenPowerAI@epri.com",
        "lmidmore@epri.com",
        "jrenshaw@epri.com",
    ):
        assert address in text


def test_epri_response_keeps_private_identity_values_out_of_repo():
    text = TEMPLATE.read_text(encoding="utf-8")
    lowered = text.lower()

    assert "private Gmail thread only" in text
    assert PRIVATE_STREET_PATTERN.search(text) is None
    assert re.search(r"\b\d{5}(?:-\d{4})?\b", text) is None
    assert "full legal party name:" not in lowered
    assert "api key" not in lowered
    assert "password" not in lowered
    assert "private key" not in lowered


def test_epri_response_preserves_claim_boundaries():
    text = TEMPLATE.read_text(encoding="utf-8")

    for phrase in (
        "does not claim executed membership",
        "EPRI endorsement",
        "independent validation",
        "contract award",
        "patent-sensitive material",
    ):
        assert phrase in text


def test_epri_engagement_receipt_is_redacted_and_monitor_only():
    receipt = json.loads(ENGAGEMENT_RECEIPT.read_text(encoding="utf-8"))
    rendered = json.dumps(receipt).lower()

    assert receipt["schema"] == "lumencore.external_engagement_receipt.v1"
    assert receipt["submission"]["status"] == "SENT_NO_ATTACHMENT"
    assert receipt["submission"]["attachment"] is None
    assert receipt["submission"]["private_identity_values_stored_in_public_receipt"] is False
    assert receipt["acknowledgment"]["status"] == "OUTBOUND_SENT_MOU_PENDING"
    assert receipt["acknowledgment"]["earliest_follow_up_date"] == "2026-07-23"
    assert PRIVATE_STREET_PATTERN.search(rendered) is None
    assert re.search(r"\b\d{5}(?:-\d{4})?\b", rendered) is None
    assert "full legal party name:" not in rendered
    assert "does not establish an executed mou" in receipt["claim_boundary"].lower()


def test_action_control_packet_historical_e_drive_receipt_is_consistent():
    receipt = json.loads(SYNC_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 25
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["destination_root"].startswith("E:/LumaProofVault/")
    assert "does not prove email transmission" in receipt["claim_boundary"]
    destination = Path(receipt["destination_root"])
    for artifact in receipt["artifacts"]:
        mirror = destination / Path(artifact["source"]).name
        assert mirror.is_file(), str(mirror)
        assert artifact["bytes"] > 0
        assert re.fullmatch(r"[0-9A-F]{64}", artifact["sha256"])
        assert artifact["copy_sha256_matched"] is True
        assert mirror.stat().st_size == artifact["bytes"]
        assert hashlib.sha256(mirror.read_bytes()).hexdigest().upper() == artifact["sha256"]

    mirrored_sources = {artifact["source"] for artifact in receipt["artifacts"]}
    assert {
        "code/ops/BUILD_SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL.py",
        "code/ops/INSTALL_SAM_PUBLIC_CREDENTIAL.py",
        "tests/test_sam_public_credential_rotation_control.py",
        "tests/test_install_sam_public_credential.py",
        "grant_submissions/funding_sprint_20260709/SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.json",
        "grant_submissions/funding_sprint_20260709/SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.md",
        "grant_submissions/funding_sprint_20260709/NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD_2026-07-17.md",
        "code/ops/BUILD_PATENT_DEADLINE_EVIDENCE_CONTROL.py",
        "tests/test_patent_deadline_evidence_control.py",
        "grant_submissions/funding_sprint_20260709/PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.json",
        "grant_submissions/funding_sprint_20260709/PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.md",
        "code/ops/BUILD_IP_COUNSEL_DILIGENCE_PACKET.py",
        "tests/test_ip_counsel_diligence_packet.py",
        "grant_submissions/funding_sprint_20260709/IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md",
        "dashboard/data/ip_counsel_diligence_packet.json",
        "docs/DEADLINE_RECOVERY_CHECKLIST.md",
        "code/ops/PREPARE_PATENT_CENTER_PRIVATE_CAPTURE.py",
        "tests/test_prepare_patent_center_private_capture.py",
        "grant_submissions/funding_sprint_20260709/PATENT_CENTER_PRIVATE_DOCKET_CAPTURE_WORKFLOW_2026-07-17.md",
        "grant_submissions/funding_sprint_20260709/PATENT_PRACTITIONER_DOCKET_REVIEW_REQUEST_TEMPLATE_2026-07-17.md",
    }.issubset(mirrored_sources)
