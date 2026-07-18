from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "build_week" / "prooflock_console"
SCRIPT = APP_DIR / "verify_receipt.py"
SAMPLE = APP_DIR / "sample_receipt.json"


def load_module():
    spec = importlib.util.spec_from_file_location("prooflock_console_verifier", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sample_receipt() -> dict:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def test_bundled_receipt_hashes_every_artifact_and_holds_promotion():
    module = load_module()
    receipt = sample_receipt()
    report = module.verify_receipt(receipt)

    assert report["schema"] == "lumencore.prooflock_verification_report.v1"
    assert report["integrity_valid"] is True
    assert report["receipt_hash"]["matches"] is True
    assert report["artifact_count"] == 4
    assert report["artifact_hash_match_count"] == 4
    assert all(row["hash_matches"] for row in report["artifacts"])
    assert report["recorded_decision"] == "HOLD"
    assert report["promotion_allowed"] is False
    assert set(report["required_open_or_failed_gates"]) == {
        "engineering_cad",
        "prototype_test",
        "qualified_safety_review",
        "human_release",
    }


def test_receipt_mutation_is_detected():
    module = load_module()
    receipt = sample_receipt()
    receipt["claim_boundary"] += " changed"

    report = module.verify_receipt(receipt)

    assert report["integrity_valid"] is False
    assert report["receipt_hash"]["matches"] is False
    assert "receipt_sha256 does not match" in " ".join(report["errors"])


def test_promotion_cannot_clear_required_open_gates():
    module = load_module()
    receipt = sample_receipt()
    receipt["decision"] = "PROMOTE"
    receipt["receipt_sha256"] = module.stable_hash(module.receipt_payload(receipt))

    report = module.verify_receipt(receipt)

    assert report["integrity_valid"] is False
    assert report["promotion_allowed"] is False
    assert "PROMOTE is prohibited" in " ".join(report["errors"])


@pytest.mark.parametrize(
    ("decision", "expected_promotion_allowed"),
    [("HOLD", False), ("REJECT", False), ("PROMOTE", True)],
)
def test_all_required_gates_pass_still_requires_explicit_promote_decision(
    decision, expected_promotion_allowed
):
    module = load_module()
    receipt = sample_receipt()
    for gate in receipt["gates"]:
        if gate.get("required_for_promotion"):
            gate["status"] = "PASS"
    receipt["decision"] = decision
    receipt["receipt_sha256"] = module.stable_hash(module.receipt_payload(receipt))

    report = module.verify_receipt(receipt)

    assert report["integrity_valid"] is True
    assert report["required_open_or_failed_gates"] == []
    assert report["recorded_decision"] == decision
    assert report["promotion_allowed"] is expected_promotion_allowed


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../private.txt",
        "/etc/passwd",
        "C:/private.txt",
        "https://example.invalid/file.json",
        "assets/%2e%2e/private.txt",
        "assets\\..\\private.txt",
        "assets//private.txt",
    ],
)
def test_artifact_path_cannot_escape_repository_allowlist(unsafe_path):
    module = load_module()
    receipt = sample_receipt()
    receipt["artifacts"][0]["repo_relative_path"] = unsafe_path
    receipt["receipt_sha256"] = module.stable_hash(module.receipt_payload(receipt))

    report = module.verify_receipt(receipt)

    assert report["integrity_valid"] is False
    assert "artifact path" in " ".join(report["errors"])


def test_duplicate_artifact_id_and_invalid_expected_hash_fail_closed():
    module = load_module()
    receipt = sample_receipt()
    receipt["artifacts"][1]["artifact_id"] = receipt["artifacts"][0]["artifact_id"]
    receipt["artifacts"][1]["expected_sha256"] = "not-a-hash"
    receipt["receipt_sha256"] = module.stable_hash(module.receipt_payload(receipt))

    report = module.verify_receipt(receipt)

    assert report["integrity_valid"] is False
    assert "duplicate artifact_id" in " ".join(report["errors"])
    assert "invalid expected_sha256" in " ".join(report["errors"])


def test_console_is_self_contained_and_documents_build_week_gates():
    html = (APP_DIR / "index.html").read_text(encoding="utf-8")
    script = (APP_DIR / "app.js").read_text(encoding="utf-8")
    core = (APP_DIR / "prooflock_core.js").read_text(encoding="utf-8")
    lattice = (APP_DIR / "prooflock_lattice.js").read_text(encoding="utf-8")
    readme = (APP_DIR / "README.md").read_text(encoding="utf-8")

    assert "ProofLock Console" in html
    assert "Artifact matrix" in html
    assert "Run guided proof" in html
    assert "crypto.subtle.digest" in core
    assert "PROMOTE is prohibited" in core
    assert "runGuidedProof" in lattice
    assert "Developer Tools" in readme
    assert "/feedback" in readme
    assert "does not infer or invent the model identity" in readme
    assert "external service is required" in readme


def test_hashed_json_artifacts_are_checkout_byte_stable():
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "flowform_curved_motherboard_honeycomb_battery_v2_concept.json -text" in attributes
    assert "flowform_curved_motherboard_honeycomb_battery_v3_concept.json -text" in attributes


def test_public_session_reconciliation_is_bounded_and_identifier_free():
    receipt = (
        ROOT
        / "docs"
        / "OPENAI_BUILD_WEEK_PROOFLOCK_SESSION_HASH_RECONCILIATION_2026-07-18.md"
    ).read_text(encoding="utf-8")

    assert "CANDIDATE_HASH_MATCH_CONFIRMED" in receipt
    assert "CEDEC32157F2516DF88505802805761AE3535F093FB9B1B06CA6DEFF4A344FD9" in receipt
    assert "does **not** establish that `/feedback` returns that candidate" in receipt
    assert not re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        receipt,
    )
