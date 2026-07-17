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


def test_epri_response_is_routed_and_explicitly_send_gated():
    text = TEMPLATE.read_text(encoding="utf-8")

    assert "DRAFT_NOT_SENT" in text
    assert "READY_AWAITING_EXPLICIT_SEND" in text
    assert "send EPRI" in text
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

    assert text.count("[ENTER IN PRIVATE GMAIL DRAFT ONLY]") == 5
    assert "2613" not in text
    assert "paddle" not in lowered
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


def test_action_control_packet_has_a_bounded_e_drive_integrity_receipt():
    receipt = json.loads(SYNC_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 9
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["destination_root"].startswith("E:/LumaProofVault/")
    assert "does not prove email transmission" in receipt["claim_boundary"]
    destination = Path(receipt["destination_root"])
    for artifact in receipt["artifacts"]:
        source = ROOT / artifact["source"]
        mirror = destination / source.name
        assert source.is_file(), artifact["source"]
        assert mirror.is_file(), str(mirror)
        assert artifact["bytes"] > 0
        assert re.fullmatch(r"[0-9A-F]{64}", artifact["sha256"])
        assert source.stat().st_size == artifact["bytes"]
        assert mirror.stat().st_size == artifact["bytes"]
        assert hashlib.sha256(source.read_bytes()).hexdigest().upper() == artifact["sha256"]
        assert hashlib.sha256(mirror.read_bytes()).hexdigest().upper() == artifact["sha256"]

    mirrored_sources = {artifact["source"] for artifact in receipt["artifacts"]}
    assert {
        "code/ops/BUILD_SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL.py",
        "tests/test_sam_public_credential_rotation_control.py",
        "grant_submissions/funding_sprint_20260709/SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.json",
        "grant_submissions/funding_sprint_20260709/SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.md",
    }.issubset(mirrored_sources)
