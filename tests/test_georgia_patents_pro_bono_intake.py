from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
TEMPLATE = SPRINT_DIR / "GEORGIA_PATENTS_PRO_BONO_INTAKE_RESPONSE_2026-07-16.md"
RECEIPT = SPRINT_DIR / "GEORGIA_PATENTS_PRO_BONO_INTAKE_ENGAGEMENT_RECEIPT_2026-07-16.json"


def test_intake_response_is_sent_nonconfidential_and_duplicate_gated():
    text = TEMPLATE.read_text(encoding="utf-8")

    assert "SENT_VERIFIED_RESPONSE_PENDING" in text
    assert "patents@gapatents.org" in text
    assert "Attachment: `none`" in text
    assert "CLOSED_THROUGH_2026-07-23" in text
    assert "already-filed applications" in text
    assert "Solo Inventor application" in text
    assert "urgent-routing process" in text


def test_public_intake_artifacts_exclude_unpublished_application_details():
    text = TEMPLATE.read_text(encoding="utf-8")
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    rendered = text + json.dumps(receipt, sort_keys=True)
    lowered = rendered.lower()

    assert re.search(r"\b\d{2}/\d{3},?\d{3}\b", rendered) is None
    assert re.search(r"\b(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]\d{3}[-.\s]\d{4}\b", rendered) is None
    assert "@gmail.com" not in lowered
    assert "meeting id" not in lowered
    assert "passcode" not in lowered
    assert "api_key" not in lowered
    assert "private key" not in lowered


def test_engagement_receipt_preserves_procedural_and_claim_boundaries():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema"] == "lumencore.external_engagement_receipt.v1"
    assert receipt["submission"]["status"] == "SENT_NO_ATTACHMENT"
    assert receipt["submission"]["attachment"] is None
    assert receipt["submission"]["gmail_message_identifier_published"] is False
    assert receipt["submission"]["unpublished_application_material_sent"] is False
    assert receipt["acknowledgment"]["status"] == "OUTBOUND_SENT_INTAKE_RESPONSE_PENDING"
    assert receipt["acknowledgment"]["earliest_follow_up_date"] == "2026-07-24"
    assert receipt["disclosure_boundary"]["program_confidentiality_assumed"] is False
    assert "does not establish" in receipt["claim_boundary"].lower()
