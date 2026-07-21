from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "DEADLINE_INTEGRITY_REPAIR_CHECKPOINT_2026-07-21.json"
)
SIDECAR = RECEIPT.with_suffix(RECEIPT.suffix + ".sha256")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def git_blob_oid(commit: str, relative_path: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"{commit}:{relative_path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_checkpoint_is_commit_bound_public_safe_and_human_gated():
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert payload["schema"] == "lumencore.deadline_integrity_repair_checkpoint.v1"
    assert len(payload["source_commit"]) == 40
    assert payload["source_worktree_tracked_clean"] is True
    assert payload["artifact_count"] == len(payload["artifacts"]) == 39
    assert payload["all_source_git_blobs_match_commit"] is True
    assert payload["all_sha256_matched_after_copy"] is True
    assert payload["relative_paths_preserved"] is True
    assert payload["private_files_mirrored"] is False
    assert payload["browser_navigation_performed"] is False
    assert payload["external_send_performed"] is False
    assert payload["portal_submission_performed"] is False
    assert payload["certification_or_terms_accepted"] is False
    assert "does not prove email transmission" in payload["claim_boundary"]
    assert "human-controlled" in payload["claim_boundary"]

    unhashed = dict(payload)
    recorded_payload_hash = unhashed.pop("receipt_payload_sha256")
    encoded = json.dumps(
        unhashed,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    assert sha256_bytes(encoded) == recorded_payload_hash

    for artifact in payload["artifacts"]:
        normalized = artifact["source"].replace("\\", "/").lower()
        assert "/private/" not in f"/{normalized}/"
        assert ".private." not in normalized
        commit_oid = git_blob_oid(payload["source_commit"], artifact["source"])
        assert commit_oid == artifact["commit_git_blob_oid"]
        assert artifact["source_git_blob_oid"] == artifact["commit_git_blob_oid"]
        assert artifact["bytes"] == artifact["copy_bytes"]
        assert artifact["sha256"] == artifact["copy_sha256"]
        assert artifact["source_git_blob_match"] is True
        assert artifact["copy_sha256_matched"] is True

        destination = Path(artifact["destination"])
        if destination.is_file():
            assert destination.stat().st_size == artifact["copy_bytes"]
            assert sha256_bytes(destination.read_bytes()) == artifact["copy_sha256"]


def test_checkpoint_receipt_and_sidecar_are_hash_consistent():
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    receipt_hash = sha256_bytes(RECEIPT.read_bytes())
    sidecar_hash, sidecar_name = SIDECAR.read_text(encoding="ascii").strip().split()

    assert sidecar_hash == receipt_hash
    assert sidecar_name == RECEIPT.name

    receipt_copy = Path(payload["receipt_copy_destination"])
    sidecar_copy = Path(payload["sidecar_copy_destination"])
    if receipt_copy.is_file():
        assert sha256_bytes(receipt_copy.read_bytes()) == receipt_hash
    if sidecar_copy.is_file():
        assert sha256_bytes(sidecar_copy.read_bytes()) == sha256_bytes(SIDECAR.read_bytes())
