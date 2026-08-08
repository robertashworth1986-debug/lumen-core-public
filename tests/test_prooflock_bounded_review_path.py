from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "dashboard" / "build_week" / "prooflock_console"
SCRIPT = APP_DIR / "verify_receipt.py"
SAMPLE = APP_DIR / "sample_receipt.json"


def load_module():
    spec = importlib.util.spec_from_file_location("prooflock_bounded_verifier", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def sample_receipt() -> dict:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def committed_artifact_root(tmp_path: Path, receipt: dict) -> Path:
    for artifact in receipt["artifacts"]:
        relative = artifact["repo_relative_path"]
        committed = subprocess.run(
            ["git", "cat-file", "blob", f"HEAD:dashboard/{relative}"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(committed)
    return tmp_path


def test_public_demo_binds_exact_committed_blobs_and_holds_promotion(tmp_path):
    module = load_module()
    receipt = sample_receipt()
    root = committed_artifact_root(tmp_path, receipt)
    for artifact in receipt["artifacts"]:
        observed = hashlib.sha256(
            (root / artifact["repo_relative_path"]).read_bytes()
        ).hexdigest()
        assert artifact["expected_sha256"] == observed
    report = module.verify_receipt(receipt, root=root)
    assert report["integrity_valid"] is True
    assert report["policy_valid"] is True
    assert report["artifact_count"] == 2
    assert report["artifact_hash_match_count"] == 2
    assert report["recorded_decision"] == "HOLD"
    assert report["promotion_allowed"] is False
    assert set(report["required_open_or_failed_gates"]) == {
        "baseline_contract",
        "held_out_evaluation",
        "independent_review",
        "human_release",
    }


@pytest.mark.parametrize("decision", ["HOLD", "REJECT", "PROMOTE"])
def test_resealed_self_authored_passes_cannot_mint_authority(decision, tmp_path):
    module = load_module()
    receipt = sample_receipt()
    for gate in receipt["gates"]:
        if gate.get("required_for_promotion"):
            gate["status"] = "PASS"
    receipt["decision"] = decision
    receipt["receipt_sha256"] = module.stable_hash(
        module.receipt_payload(receipt)
    )
    report = module.verify_receipt(
        receipt,
        root=committed_artifact_root(tmp_path, receipt),
    )
    assert report["integrity_valid"] is True
    assert report["policy_valid"] is False
    assert report["promotion_allowed"] is False
    assert set(report["required_open_or_failed_gates"]) == {
        "baseline_contract",
        "held_out_evaluation",
        "independent_review",
        "human_release",
    }


def test_receipt_mutation_and_missing_authority_gate_fail_closed():
    module = load_module()
    mutated = sample_receipt()
    mutated["claim_boundary"] += " changed"
    report = module.verify_receipt(mutated)
    assert report["integrity_valid"] is False
    assert report["receipt_hash"]["matches"] is False

    removed = sample_receipt()
    removed["gates"] = [
        gate for gate in removed["gates"] if gate["gate_id"] != "human_release"
    ]
    removed["receipt_sha256"] = module.stable_hash(
        module.receipt_payload(removed)
    )
    report = module.verify_receipt(removed)
    assert report["integrity_valid"] is False
    assert report["promotion_allowed"] is False


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../private.txt",
        "/etc/passwd",
        "C:/private.txt",
        "https://example.invalid/file.json",
        "assets/%2e%2e/private.txt",
        "assets\\..\\private.txt",
    ],
)
def test_artifact_path_cannot_escape_public_assets(unsafe_path):
    module = load_module()
    receipt = sample_receipt()
    receipt["artifacts"][0]["repo_relative_path"] = unsafe_path
    receipt["receipt_sha256"] = module.stable_hash(
        module.receipt_payload(receipt)
    )
    report = module.verify_receipt(receipt)
    assert report["integrity_valid"] is False
    assert "artifact path" in " ".join(report["errors"])


def test_public_pages_present_one_problem_and_explicit_boundaries():
    offer = (ROOT / "dashboard" / "proof_to_pilot.html").read_text(
        encoding="utf-8"
    )
    console = (APP_DIR / "index.html").read_text(encoding="utf-8")
    readme = (APP_DIR / "README.md").read_text(encoding="utf-8")
    assert 'content="bounded-validation-offer-v1"' in offer
    assert "One candidate. One accepted baseline." in offer
    assert "No favorable result is promised." in offer
    assert "$7,500" in offer
    assert "/build_week/prooflock_console/" in offer
    assert "What ProofLock solves" in console
    assert "cannot mint" in readme
    forbidden = [
        "guaranteed ROI",
        "guaranteed savings",
        "field validated",
        "institutional grade",
        "Nobel",
    ]
    normalized = offer.lower()
    for phrase in forbidden:
        if phrase.lower() == "guaranteed roi":
            # It appears only inside the explicit non-guarantee boundary.
            assert normalized.count(phrase.lower()) == 1
        else:
            assert phrase.lower() not in normalized


def test_exact_live_audit_requires_offer_and_prooflock_bytes():
    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(
        encoding="utf-8"
    )
    assert "dashboard/build_week/prooflock_console/**" in workflow
    assert '"dashboard/opportunity_sprint.html"' in workflow
    assert '"dashboard/proof_to_pilot.html"' in workflow
    assert "package_public_site_release.py" in workflow
    assert "VERIFY_PUBLIC_SITE_LIVE_RELEASE.py" in workflow
    assert "VPS_SSH_PRIVATE_KEY" not in workflow
    assert "rsync" not in workflow
