from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "code" / "ops" / "VERIFY_PUBLIC_SITE_SIGNED_ATTESTATION_RECEIPT.py"
RECEIPT_PATH = (
    ROOT
    / "evidence"
    / "public-site-supply-chain"
    / "5fff567c11bee65b5b1de5415d8b8935cd2dfab0"
    / "attestation-receipt.json"
)
GUIDE_PATH = ROOT / "docs" / "PUBLIC_SITE_SIGNED_ATTESTATION_RECEIPT_2026-08-08.md"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VERIFIER = load_module(VERIFIER_PATH, "public_site_signed_attestation_receipt_verifier_tests")


def has_source_commit() -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{VERIFIER.SOURCE_COMMIT}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    ).returncode == 0


def write_receipt(path: Path, value: dict, *, rehash: bool = True) -> None:
    payload = copy.deepcopy(value)
    if rehash:
        unhashed = {key: item for key, item in payload.items() if key != "receipt_sha256"}
        payload["receipt_sha256"] = hashlib.sha256(
            json.dumps(
                unhashed,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


@pytest.mark.skipif(not has_source_commit(), reason="pinned source commit unavailable in shallow checkout")
def test_retained_receipt_reconstructs_exact_archive_and_holds_production():
    verification = VERIFIER.verify_receipt(root=ROOT, receipt_path=RECEIPT_PATH)
    assert verification["valid"] is True
    assert verification["source_commit"] == VERIFIER.SOURCE_COMMIT
    assert verification["subject_sha256"] == (
        "b771bf57367cec2f17db56a512b25eca1313539e4a2f8300adf045887449db7f"
    )
    assert verification["release_file_count"] == 30
    assert verification["attestation_count"] == 2
    assert verification["production_decision"].startswith("HOLD_")
    assert verification["live_release_verified"] is False


def test_receipt_rejects_duplicate_and_nonfinite_json(tmp_path):
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema":"one","schema":"two"}\n', encoding="utf-8")
    with pytest.raises(VERIFIER.SignedAttestationReceiptError, match="duplicate JSON key"):
        VERIFIER.read_json(duplicate)

    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text('{"value":NaN}\n', encoding="utf-8")
    with pytest.raises(VERIFIER.SignedAttestationReceiptError, match="non-finite"):
        VERIFIER.read_json(nonfinite)


def test_receipt_self_hash_fails_closed(tmp_path):
    payload = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    payload["receipt_sha256"] = "0" * 64
    candidate = tmp_path / "receipt.json"
    write_receipt(candidate, payload, rehash=False)
    with pytest.raises(VERIFIER.SignedAttestationReceiptError, match="self-hash"):
        VERIFIER.verify_receipt(root=ROOT, receipt_path=candidate)


def test_verified_predicate_cannot_be_weakened_even_with_rehashed_receipt(tmp_path):
    payload = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    payload["attestations"][0]["verification_state"] = "UNVERIFIED"
    candidate = tmp_path / "receipt.json"
    write_receipt(candidate, payload)
    with pytest.raises(VERIFIER.SignedAttestationReceiptError, match="not verified"):
        VERIFIER.verify_receipt(root=ROOT, receipt_path=candidate)


@pytest.mark.skipif(not has_source_commit(), reason="pinned source commit unavailable in shallow checkout")
def test_subject_hash_must_match_rebuilt_git_archive(tmp_path):
    payload = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    payload["subject"]["sha256"] = "0" * 64
    candidate = tmp_path / "receipt.json"
    write_receipt(candidate, payload)
    with pytest.raises(VERIFIER.SignedAttestationReceiptError, match="archive subject hash"):
        VERIFIER.verify_receipt(root=ROOT, receipt_path=candidate)


def test_signer_identity_cannot_be_redirected(tmp_path):
    payload = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    payload["signer_identity"]["runner_environment"] = "self-hosted"
    candidate = tmp_path / "receipt.json"
    write_receipt(candidate, payload)
    with pytest.raises(VERIFIER.SignedAttestationReceiptError, match="signer identity"):
        VERIFIER.verify_receipt(root=ROOT, receipt_path=candidate)


def test_live_domain_cannot_be_promoted(tmp_path):
    payload = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    payload["live_domain_audit"]["release_verified"] = True
    payload["live_domain_audit"]["production_decision"] = "PROMOTE"
    candidate = tmp_path / "receipt.json"
    write_receipt(candidate, payload)
    with pytest.raises(VERIFIER.SignedAttestationReceiptError, match="falsely promoted"):
        VERIFIER.verify_receipt(root=ROOT, receipt_path=candidate)


def test_public_guide_keeps_remote_and_local_verification_boundaries():
    guide = GUIDE_PATH.read_text(encoding="utf-8")
    for required in (
        "Production decision: **`HOLD`**",
        "gh attestation verify",
        "--source-digest 5fff567c11bee65b5b1de5415d8b8935cd2dfab0",
        "--source-ref refs/heads/main",
        "--deny-self-hosted-runners",
        "does **not** reverify the remote signature",
        "signed archive is **not proven deployed**",
        "DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT",
        "No production deployment is authorized",
    ):
        assert required in guide
