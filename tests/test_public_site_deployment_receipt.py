from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "public_site_deployment_receipt",
    ROOT / "code" / "ops" / "VERIFY_PUBLIC_SITE_DEPLOYMENT_RECEIPT.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def canonical_receipt() -> dict:
    return MODULE.read_json(MODULE.DEFAULT_RECEIPT)


def write_receipt(path: Path, payload: dict) -> None:
    unsigned = copy.deepcopy(payload)
    unsigned.pop("receipt_sha256", None)
    payload = copy.deepcopy(payload)
    payload["receipt_sha256"] = MODULE.sha256_bytes(MODULE.canonical_bytes(unsigned))
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_retained_receipt_reconstructs_exact_release() -> None:
    result = MODULE.verify_receipt()
    assert result["valid"] is True
    assert result["source_commit"] == MODULE.DEFAULT_SOURCE_COMMIT
    assert result["release_file_count"] == 43
    assert result["live_release_verified"] is True
    assert result["incident_state"] == "NO_INCIDENT_OBSERVED"
    assert len(result["verification_sha256"]) == 64


def test_full_retained_history_reconstructs_every_release() -> None:
    result = MODULE.verify_all_receipts()
    assert result["valid"] is True
    assert result["receipt_count"] == 2
    assert set(result["source_commits"]) == {
        "e513f65a219a12e539d9f7dd3ea47a6a081c5262",
        MODULE.DEFAULT_SOURCE_COMMIT,
    }
    assert all(item["live_release_verified"] for item in result["receipts"])
    assert len(result["verification_sha256"]) == 64


def test_repository_receipt_path_must_match_source_commit(tmp_path: Path) -> None:
    fake_root = tmp_path / "repo"
    bad_path = (
        fake_root
        / "evidence"
        / "public-site-deployments"
        / ("0" * 40)
        / "deployment-receipt.json"
    )
    bad_path.parent.mkdir(parents=True)
    with pytest.raises(MODULE.DeploymentReceiptError, match="not bound"):
        MODULE._bind_repository_receipt_path(
            root=fake_root,
            receipt_path=bad_path,
            source_commit=MODULE.DEFAULT_SOURCE_COMMIT,
        )


def test_self_hash_tampering_fails_closed(tmp_path: Path) -> None:
    receipt = canonical_receipt()
    receipt["deployment"]["matched_file_count"] = 42
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(MODULE.DeploymentReceiptError, match="self-hash"):
        MODULE.verify_receipt(receipt_path=path)


def test_promoted_live_count_fails_closed(tmp_path: Path) -> None:
    receipt = canonical_receipt()
    receipt["post_deployment_audit"]["matched_file_count"] = 42
    path = tmp_path / "bad-count.json"
    write_receipt(path, receipt)
    with pytest.raises(MODULE.DeploymentReceiptError, match="audit count"):
        MODULE.verify_receipt(receipt_path=path)


def test_missing_negative_boundary_fails_closed(tmp_path: Path) -> None:
    receipt = canonical_receipt()
    receipt["claim_boundaries"][0] = "All controls are complete."
    path = tmp_path / "promoted.json"
    write_receipt(path, receipt)
    with pytest.raises(MODULE.DeploymentReceiptError, match="claim boundary"):
        MODULE.verify_receipt(receipt_path=path)
