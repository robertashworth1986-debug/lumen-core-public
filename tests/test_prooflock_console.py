from __future__ import annotations

import copy
import hashlib
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
    assert report["policy_valid"] is True
    assert report["receipt_hash"]["matches"] is True
    assert report["artifact_count"] == 4
    assert report["artifact_hash_match_count"] == 4
    assert all(row["hash_matches"] for row in report["artifacts"])
    assert report["recorded_decision"] == "HOLD"
    assert report["promotion_allowed"] is False
    assert [gate["authority_source"] for gate in report["gates"][:2]] == [
        "VERIFIER_DERIVED",
        "VERIFIER_DERIVED",
    ]
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

    assert report["integrity_valid"] is True
    assert report["policy_valid"] is False
    assert report["promotion_allowed"] is False
    assert "PROMOTE is prohibited" in " ".join(report["policy_errors"])


@pytest.mark.parametrize(
    "decision",
    ["HOLD", "REJECT", "PROMOTE"],
)
def test_resealed_self_authored_passes_cannot_mint_authority(decision):
    module = load_module()
    receipt = sample_receipt()
    for gate in receipt["gates"]:
        if gate.get("required_for_promotion"):
            gate["status"] = "PASS"
    receipt["decision"] = decision
    receipt["receipt_sha256"] = module.stable_hash(module.receipt_payload(receipt))

    report = module.verify_receipt(receipt)

    assert report["integrity_valid"] is True
    assert report["policy_valid"] is False
    assert set(report["required_open_or_failed_gates"]) == {
        "engineering_cad",
        "prototype_test",
        "qualified_safety_review",
        "human_release",
    }
    assert report["recorded_decision"] == decision
    assert report["promotion_allowed"] is False
    assert all(
        gate["effective_status"] == "OPEN"
        for gate in report["gates"]
        if gate["gate_id"] in report["required_open_or_failed_gates"]
    )


@pytest.mark.parametrize("attack", ["remove", "downgrade"])
def test_canonical_required_gate_contract_cannot_be_removed_or_downgraded(attack):
    module = load_module()
    receipt = sample_receipt()
    if attack == "remove":
        receipt["gates"] = [gate for gate in receipt["gates"] if gate["gate_id"] != "human_release"]
    else:
        next(gate for gate in receipt["gates"] if gate["gate_id"] == "human_release")[
            "required_for_promotion"
        ] = False
    receipt["receipt_sha256"] = module.stable_hash(module.receipt_payload(receipt))

    report = module.verify_receipt(receipt)

    assert report["integrity_valid"] is False
    assert report["promotion_allowed"] is False
    assert "canonical" in " ".join(report["integrity_errors"])


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
    threat_model = (APP_DIR / "THREAT_MODEL.md").read_text(encoding="utf-8")
    narration = (
        ROOT / "docs" / "OPENAI_BUILD_WEEK_PROOFLOCK_DEMO_NARRATION_2026-07-18.md"
    ).read_text(encoding="utf-8")
    checklist = (
        ROOT / "docs" / "OPENAI_BUILD_WEEK_PROOFLOCK_HUMAN_GATE_CHECKLIST_2026-07-18.md"
    ).read_text(encoding="utf-8")
    release_receipt = (
        ROOT / "docs" / "OPENAI_BUILD_WEEK_PROOFLOCK_LIVE_RELEASE_RECEIPT_2026-07-18.md"
    ).read_text(encoding="utf-8")
    readiness = (
        ROOT / "docs" / "OPENAI_BUILD_WEEK_PROOFLOCK_SUBMISSION_READINESS_2026-07-17.md"
    ).read_text(encoding="utf-8")

    assert "ProofLock Console" in html
    assert "Artifact matrix" in html
    assert "Run guided proof" in html
    assert "Effective decision" in html
    assert "crypto.subtle.digest" in core
    assert "PROMOTE is prohibited" in core
    assert 'return report.promotion_allowed ? "PROMOTE" : "HOLD"' in script
    assert "requested decision" in script
    assert "effective decision" in script
    assert "runGuidedProof" in lattice
    assert "Developer Tools" in readme
    assert "/feedback" in readme
    assert "does not infer or invent the model identity" in readme
    assert "external service is required" in readme
    assert "refusing self-authored authority escalation" in readme
    assert "recomputes a valid receipt hash" in readme
    assert "SHA-256 detects byte changes but does not authenticate" in threat_model
    assert "twenty-seven passing tests" not in narration
    assert "exact source commit and current test receipt" in narration
    assert "Do not present the historical public release as current-head evidence" in narration
    assert "`28 passed`" not in checklist
    assert "Verified video publication" in checklist
    assert "https://youtu.be/3qhK9WSJuaY" in checklist
    assert "publicly resolvable" in checklist
    assert "2026-07-20T21:41:43Z" in checklist
    assert "Current focused local test result: `55 passed, 3 skipped`" in checklist
    assert "GitHub account is locked by a billing issue" in checklist
    assert "Current live-file identity: `15/15`" in checklist
    assert "b2ac8cef10ee5b9db765a17cdbf6f13e6b917ce5" in checklist
    assert "4b241a62e4f3fd76582d5e7992cc6ff119e36594b4f77e8713a1a75bac7984bc" in checklist
    assert "9f1d417cb29c132ecc9a31f3a572adbcb3ebd66208517e70ad9adab6e8684b15" in checklist
    assert "Historical release only" in release_receipt
    assert "must not be used as current release evidence" in release_receipt
    assert "`32 passed`" not in readiness


def test_hashed_json_artifacts_are_checkout_byte_stable():
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "flowform_curved_motherboard_honeycomb_battery_v2_concept.json -text" in attributes
    assert "flowform_curved_motherboard_honeycomb_battery_v3_concept.json -text" in attributes


def test_youtube_publication_receipt_is_bounded_and_self_hashing():
    receipt_path = (
        ROOT
        / "evidence"
        / "openai_build_week"
        / "prooflock_youtube_publication_receipt_20260721.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    claimed_sha256 = receipt.pop("receipt_sha256")
    canonical = json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")

    assert claimed_sha256 == hashlib.sha256(canonical).hexdigest()
    assert receipt["source_video"]["sha256"] == (
        "9f1d417cb29c132ecc9a31f3a572adbcb3ebd66208517e70ad9adab6e8684b15"
    )
    assert receipt["source_video"]["filename"].endswith("luma_candidate.mp4")
    assert receipt["synthetic_narration"]["critical_phrases_present"] is True
    assert receipt["youtube"]["url"] == "https://youtu.be/3qhK9WSJuaY"
    assert receipt["youtube"]["visibility"] == "PUBLIC"
    assert receipt["youtube"]["copyright_check"] == "COMPLETE_NO_ISSUES_FOUND"
    assert receipt["youtube"]["public_watch_url_resolved"] is True
    assert receipt["devpost"]["final_submission_performed"] is False
    assert receipt["controls"]["private_session_identifier_exposed"] is False
    assert receipt["devpost"]["feedback_session_id_saved"] is True
    assert receipt["devpost"]["final_legal_review_completed"] is False
    assert "does not independently prove contest submission" in receipt["claim_boundary"]


def test_build_week_voiceover_is_bounded_and_describes_the_current_attack():
    voiceover = (
        ROOT / "docs" / "OPENAI_BUILD_WEEK_PROOFLOCK_VOICEOVER_2026-07-20.md"
    ).read_text(encoding="utf-8")

    assert len(re.findall(r"\b[\w'-]+\b", voiceover)) < 350
    assert "recomputes a valid receipt hash" in voiceover
    assert "Receipt integrity still passes" in voiceover
    assert "ProofLock derives four held gates" in voiceover
    assert "keeps the effective decision at HOLD" in voiceover
    assert "external validation" in voiceover
    assert "agent" not in voiceover.lower()
    assert "GPT-5.6" in voiceover
    assert "gpt-5.6-sol" not in voiceover.lower()


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
