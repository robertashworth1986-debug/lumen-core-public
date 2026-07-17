from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


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


def test_artifact_path_cannot_escape_repository_root():
    module = load_module()
    receipt = sample_receipt()
    receipt["artifacts"][0]["repo_relative_path"] = "../private.txt"
    receipt["receipt_sha256"] = module.stable_hash(module.receipt_payload(receipt))

    report = module.verify_receipt(receipt)

    assert report["integrity_valid"] is False
    assert "escapes repository root" in " ".join(report["errors"])


def test_console_is_self_contained_and_documents_build_week_gates():
    html = (APP_DIR / "index.html").read_text(encoding="utf-8")
    script = (APP_DIR / "app.js").read_text(encoding="utf-8")
    readme = (APP_DIR / "README.md").read_text(encoding="utf-8")

    assert "ProofLock Console" in html
    assert "Artifact matrix" in html
    assert "crypto.subtle.digest" in script
    assert "PROMOTE is blocked" in script
    assert "Developer Tools" in readme
    assert "/feedback" in readme
    assert "does not infer or invent the model identity" in readme
    assert "external service is required" in readme
