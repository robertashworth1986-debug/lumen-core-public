from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "code" / "ops" / "VERIFY_PUBLIC_SECURITY_HEADER_RECEIPT.py"
RECEIPT_PATH = (
    ROOT
    / "evidence"
    / "public-security-headers"
    / "04f5397422cc8e651ddde5cc7e7c57a334866c01"
    / "deployment-receipt.json"
)
GUIDE_PATH = ROOT / "docs" / "PUBLIC_SECURITY_HEADER_DEPLOYMENT_RECEIPT_2026-08-09.md"
RECEIPT_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "public-security-header-receipt.yml"
REQUIREMENTS_PATH = ROOT / ".github" / "requirements" / "public-security-header-receipt.txt"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VERIFIER = load_module(VERIFIER_PATH, "public_security_header_receipt_tests")


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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_retained_receipt_binds_exact_main_run_and_three_origins():
    result = VERIFIER.verify_receipt(root=ROOT, receipt_path=RECEIPT_PATH)
    assert result["valid"] is True
    assert result["source_commit"] == VERIFIER.SOURCE_COMMIT
    assert result["workflow_run_id"] == 31289595192
    assert result["route_count"] == 7
    assert result["observation_origin_count"] == 3
    assert result["production_decision"].endswith("NO_BROADER_PRODUCTION_PROMOTION")


def test_duplicate_and_nonfinite_json_fail_closed(tmp_path):
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema":"one","schema":"two"}\n', encoding="utf-8")
    with pytest.raises(VERIFIER.PublicSecurityHeaderReceiptError, match="duplicate JSON key"):
        VERIFIER.read_json(duplicate)

    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text('{"value":NaN}\n', encoding="utf-8")
    with pytest.raises(VERIFIER.PublicSecurityHeaderReceiptError, match="non-finite"):
        VERIFIER.read_json(nonfinite)


def test_self_hash_rejects_tampering(tmp_path):
    payload = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    payload["receipt_sha256"] = "0" * 64
    candidate = tmp_path / "receipt.json"
    write_receipt(candidate, payload, rehash=False)
    with pytest.raises(VERIFIER.PublicSecurityHeaderReceiptError, match="self-hash"):
        VERIFIER.verify_receipt(root=ROOT, receipt_path=candidate)


def test_route_coverage_cannot_be_reduced_even_after_rehash(tmp_path):
    payload = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    payload["routes"].pop()
    candidate = tmp_path / "receipt.json"
    write_receipt(candidate, payload)
    with pytest.raises(VERIFIER.PublicSecurityHeaderReceiptError, match="route coverage"):
        VERIFIER.verify_receipt(root=ROOT, receipt_path=candidate)


def test_policy_cannot_be_weakened_even_after_rehash(tmp_path):
    payload = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    payload["header_policy"]["X-Frame-Options"] = "SAMEORIGIN"
    candidate = tmp_path / "receipt.json"
    write_receipt(candidate, payload)
    with pytest.raises(VERIFIER.PublicSecurityHeaderReceiptError, match="header policy"):
        VERIFIER.verify_receipt(root=ROOT, receipt_path=candidate)


def test_origin_pass_cannot_be_promoted_from_failure(tmp_path):
    payload = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    payload["observation_origins"][2]["passed_route_count"] = 6
    candidate = tmp_path / "receipt.json"
    write_receipt(candidate, payload)
    with pytest.raises(VERIFIER.PublicSecurityHeaderReceiptError, match="observation origin failed"):
        VERIFIER.verify_receipt(root=ROOT, receipt_path=candidate)


def test_rollback_state_cannot_be_hidden(tmp_path):
    payload = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    payload["execution"]["rollback_triggered"] = True
    candidate = tmp_path / "receipt.json"
    write_receipt(candidate, payload)
    with pytest.raises(VERIFIER.PublicSecurityHeaderReceiptError, match="execution state"):
        VERIFIER.verify_receipt(root=ROOT, receipt_path=candidate)


def test_guide_preserves_bounded_security_claims():
    guide = GUIDE_PATH.read_text(encoding="utf-8")
    for required in (
        "not a penetration test",
        "not establish vulnerability-free status",
        "does not contact the live domain or GitHub",
        "NO_BROADER_PRODUCTION_PROMOTION",
        "31289595192",
        "8ac130ba2a313c795750105141cbfec4b4656c40cfe04cb3b5c58a377681f12d",
    ):
        assert required in guide


def test_receipt_workflow_pins_actions_and_python_wheels():
    workflow = RECEIPT_WORKFLOW_PATH.read_text(encoding="utf-8")
    requirements = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in workflow
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97" in workflow
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in workflow
    assert "--only-binary=:all:" in workflow
    assert "--require-hashes" in workflow
    assert "public-security-header-receipt.txt" in workflow
    assert "pytest==9.1.0" in requirements
    assert requirements.count("--hash=sha256:") >= 6
