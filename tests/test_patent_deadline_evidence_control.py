from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


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
    module, _, public_payload = build_fixture(tmp_path)
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
    assert evidence["captured_required_docket_role_count"] == 0
    assert evidence["required_docket_role_count"] == 6
    assert evidence["docket_capture_complete"] is False
    assert set(evidence["missing_required_docket_roles"]) == set(
        module.REQUIRED_DOCKET_ROLES
    )
    assert posture["us_prosecution_deadline"] == (
        "UNVERIFIED_REQUIRES_NEWEST_OFFICIAL_NOTICE"
    )
    assert posture["filing_anniversary"] == (
        "NOT_A_US_PROSECUTION_RESPONSE_DEADLINE_BY_ITSELF"
    )
    assert "TIME_SENSITIVE" in posture["foreign_pct_priority"]
    assert public_payload["human_action_gate"]["legal_filing_allowed_without_human"] is False
    assert public_payload["human_action_gate"]["fee_payment_allowed_without_human"] is False


def test_partial_official_capture_cannot_pass_the_complete_docket_gate(tmp_path: Path):
    module = load_module()
    filing_receipt = tmp_path / "filing-receipt.pdf"
    filing_receipt.write_bytes(b"official filing receipt fixture")
    records = module.collect_evidence({"filing_receipt": [filing_receipt]})
    private_payload = module.build_private_payload(
        records=records,
        application_number=None,
        application_type=None,
        payment_received_date=None,
        basic_filing_fee_only_observed=False,
        generated_utc="2026-07-17T12:00:00+00:00",
    )
    public_payload = module.build_public_payload(private_payload)
    evidence = public_payload["public_evidence_summary"]

    assert public_payload["status"] == (
        "PARTIAL_OFFICIAL_DOCKET_CAPTURE_REMAINING_DOWNLOADS_REQUIRED"
    )
    assert evidence["captured_required_docket_role_count"] == 1
    assert evidence["docket_capture_complete"] is False
    assert "filing_receipt" not in evidence["missing_required_docket_roles"]
    assert len(evidence["missing_required_docket_roles"]) == 5
    assert "1 of six required" in public_payload["direct_answer"]
    assert public_payload["human_action_gate"]["patent_center_download_required"] is True


def test_complete_gate_requires_all_six_official_docket_categories(tmp_path: Path):
    module = load_module()
    role_paths = {}
    for role in module.REQUIRED_DOCKET_ROLES:
        path = tmp_path / f"{role}.pdf"
        path.write_bytes(f"official {role} fixture".encode("ascii"))
        role_paths[role] = [path]
    records = module.collect_evidence(role_paths)
    private_payload = module.build_private_payload(
        records=records,
        application_number="99/999,999",
        application_type="Utility nonprovisional fixture",
        payment_received_date=None,
        basic_filing_fee_only_observed=False,
        generated_utc="2026-07-17T12:00:00+00:00",
    )
    public_payload = module.build_public_payload(private_payload)
    evidence = public_payload["public_evidence_summary"]

    assert public_payload["status"] == (
        "OFFICIAL_DOCKET_CAPTURED_PRACTITIONER_REVIEW_REQUIRED"
    )
    assert evidence["captured_required_docket_role_count"] == 6
    assert evidence["missing_required_docket_roles"] == []
    assert evidence["docket_capture_complete"] is True
    assert evidence["submitted_document_list_found"] is True
    assert evidence["fee_history_found"] is True
    assert evidence["transaction_history_found"] is True
    assert public_payload["human_action_gate"]["patent_center_download_required"] is False
    assert public_payload["human_action_gate"]["registered_practitioner_review_required"] is True
    assert "all six required" in public_payload["direct_answer"]


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


def test_existing_private_docket_can_rebuild_public_control_without_rewriting_private(
    tmp_path: Path,
):
    module, private_payload, _ = build_fixture(tmp_path)
    private_path = tmp_path / "docket.private.json"
    private_path.write_text(json.dumps(private_payload), encoding="utf-8")

    loaded = module.read_private_docket(private_path)
    public_payload = module.build_public_payload(loaded)

    assert loaded == private_payload
    assert public_payload["status"] == (
        "PAYMENT_ACKNOWLEDGEMENT_ONLY_OFFICIAL_DOCKET_REQUIRED"
    )
    assert public_payload["public_evidence_summary"]["required_docket_role_count"] == 6
    assert "99/999,999" not in json.dumps(public_payload, sort_keys=True)


def test_public_gate_recomputes_roles_from_evidence_not_summary(tmp_path: Path):
    module, private_payload, _ = build_fixture(tmp_path)
    private_payload["summary"].update(
        {
            "document_roles": list(module.REQUIRED_DOCKET_ROLES),
            "filing_receipt_found": True,
            "official_correspondence_found": True,
            "official_status_record_found": True,
            "submitted_document_list_found": True,
            "fee_history_found": True,
            "transaction_history_found": True,
            "missing_required_docket_roles": [],
            "docket_capture_complete": True,
        }
    )

    public_payload = module.build_public_payload(private_payload)
    evidence = public_payload["public_evidence_summary"]

    assert public_payload["status"] == (
        "PAYMENT_ACKNOWLEDGEMENT_ONLY_OFFICIAL_DOCKET_REQUIRED"
    )
    assert evidence["captured_required_docket_role_count"] == 0
    assert evidence["docket_capture_complete"] is False
    assert set(evidence["missing_required_docket_roles"]) == set(
        module.REQUIRED_DOCKET_ROLES
    )


def test_private_docket_reader_accepts_legacy_summary_and_derives_new_gate(
    tmp_path: Path,
):
    module, private_payload, _ = build_fixture(tmp_path)
    for key in (
        "submitted_document_list_found",
        "fee_history_found",
        "transaction_history_found",
        "required_docket_roles",
        "missing_required_docket_roles",
        "docket_capture_complete",
    ):
        private_payload["summary"].pop(key, None)
    private_payload.pop("private_docket_sha256")
    private_payload["private_docket_sha256"] = module.stable_sha256(private_payload)
    private_path = tmp_path / "legacy.private.json"
    private_path.write_text(json.dumps(private_payload), encoding="utf-8")

    loaded = module.read_private_docket(private_path)
    public_payload = module.build_public_payload(loaded)

    assert public_payload["public_evidence_summary"][
        "captured_required_docket_role_count"
    ] == 0
    assert public_payload["public_evidence_summary"]["docket_capture_complete"] is False


def test_private_docket_reader_rejects_tamper_or_contradictory_summary(
    tmp_path: Path,
):
    module, private_payload, _ = build_fixture(tmp_path)
    tampered = json.loads(json.dumps(private_payload))
    tampered["application_type"] = "Changed after sealing"
    tampered_path = tmp_path / "tampered.private.json"
    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")

    with pytest.raises(ValueError, match="hash does not match"):
        module.read_private_docket(tampered_path)

    contradictory = json.loads(json.dumps(private_payload))
    contradictory["summary"]["docket_capture_complete"] = True
    contradictory.pop("private_docket_sha256")
    contradictory["private_docket_sha256"] = module.stable_sha256(contradictory)
    contradictory_path = tmp_path / "contradictory.private.json"
    contradictory_path.write_text(json.dumps(contradictory), encoding="utf-8")

    with pytest.raises(ValueError, match="summary contradicts evidence"):
        module.read_private_docket(contradictory_path)


def test_private_docket_reader_rejects_public_or_wrong_schema_payload(tmp_path: Path):
    module = load_module()
    path = tmp_path / "wrong.json"
    path.write_text(
        json.dumps(
            {
                "schema": "wrong",
                "private_only": False,
                "summary": {},
                "evidence": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="schema"):
        module.read_private_docket(path)
