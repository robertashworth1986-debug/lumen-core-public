from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PATENT_DEADLINE_EVIDENCE_CONTROL.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "patent_deadline_evidence_control", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def build_fixture(tmp_path: Path):
    module = load_module()
    payment = tmp_path / "payment.pdf"
    crop = tmp_path / "receipt-crop.png"
    duplicate_crop = tmp_path / "receipt-crop-copy.png"
    payment.write_bytes(b"official payment acknowledgement fixture")
    crop.write_bytes(b"official receipt crop fixture")
    duplicate_crop.write_bytes(crop.read_bytes())

    records = module.collect_evidence(
        {
            "payment_acknowledgement": [payment],
            "payment_receipt_screenshot": [crop, duplicate_crop],
            "filing_receipt": [],
            "official_correspondence": [],
            "official_status_record": [],
            "claims_record": [],
        }
    )
    private_payload = module.build_private_payload(
        records=records,
        application_number="99/999,999",
        application_type="Utility nonprovisional fixture",
        payment_received_date="2030-01-02",
        basic_filing_fee_only_observed=True,
        generated_utc="2026-07-16T12:00:00+00:00",
    )
    public_payload = module.build_public_payload(private_payload)
    return module, private_payload, public_payload


def test_private_docket_hashes_and_deduplicates_exact_sources(tmp_path: Path):
    _, private_payload, _ = build_fixture(tmp_path)
    summary = private_payload["summary"]

    assert private_payload["schema"] == "lumencore.patent_deadline_private_docket.v1"
    assert private_payload["private_only"] is True
    assert summary["source_count"] == 3
    assert summary["unique_source_count"] == 2
    assert summary["duplicate_source_count"] == 1
    assert summary["payment_acknowledgement_found"] is True
    assert summary["filing_receipt_found"] is False
    assert summary["official_correspondence_found"] is False
    assert len(private_payload["private_docket_sha256"]) == 64
    for row in private_payload["evidence"]:
        assert len(row["source_sha256"]) == 64


def test_public_control_does_not_turn_payment_into_deadline_proof(tmp_path: Path):
    _, _, public_payload = build_fixture(tmp_path)
    evidence = public_payload["public_evidence_summary"]
    posture = public_payload["deadline_posture"]

    assert public_payload["schema"] == "lumencore.patent_deadline_evidence_control.v1"
    assert public_payload["status"] == (
        "PAYMENT_ACKNOWLEDGEMENT_ONLY_OFFICIAL_DOCKET_REQUIRED"
    )
    assert evidence["payment_acknowledgement_found"] is True
    assert evidence["filing_receipt_found"] is False
    assert evidence["official_correspondence_found"] is False
    assert evidence["claims_record_found"] is False
    assert posture["us_prosecution_deadline"] == (
        "UNVERIFIED_REQUIRES_NEWEST_OFFICIAL_NOTICE"
    )
    assert posture["filing_anniversary"] == (
        "NOT_A_US_PROSECUTION_RESPONSE_DEADLINE_BY_ITSELF"
    )
    assert "TIME_SENSITIVE" in posture["foreign_pct_priority"]
    assert public_payload["human_action_gate"]["legal_filing_allowed_without_human"] is False
    assert public_payload["human_action_gate"]["fee_payment_allowed_without_human"] is False


def test_public_control_redacts_private_identity_paths_and_hashes(tmp_path: Path):
    module, private_payload, public_payload = build_fixture(tmp_path)
    public_text = json.dumps(public_payload, sort_keys=True)
    rendered = module.render_markdown(public_payload)
    combined = public_text + rendered

    assert "99/999,999" not in combined
    assert "2030-01-02" not in combined
    for row in private_payload["evidence"]:
        assert row["private_source_path"] not in combined
        assert row["source_name"] not in combined
        assert row["source_sha256"] not in combined
    assert "private paths published: `false`" in rendered.lower()
    assert "application identifier published: `false`" in rendered.lower()


def test_control_requires_complete_patent_center_capture_and_official_sources(
    tmp_path: Path,
):
    module, private_payload, public_payload = build_fixture(tmp_path)
    items = {row["item"] for row in public_payload["required_patent_center_capture"]}
    urls = {row["url"] for row in public_payload["official_sources"]}

    assert {
        "Application data and current status",
        "Filing Receipt",
        "All outgoing correspondence",
        "Submitted document list",
        "Fee payment history",
        "Transaction history",
    }.issubset(items)
    assert any(url.startswith("https://www.uspto.gov/") for url in urls)
    assert any(url.startswith("https://www.wipo.int/") for url in urls)
    assert len(public_payload["official_sources"]) >= 6
    module.validate_public_redaction(public_payload, private_payload)
