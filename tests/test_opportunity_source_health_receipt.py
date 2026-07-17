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
    / "OPPORTUNITY_SOURCE_HEALTH_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)
SIDECAR = RECEIPT.with_suffix(".sha256")
MIRROR_ROOT = Path(
    r"E:\LumaProofVault\SUBMISSIONS\OPPORTUNITY_SOURCE_HEALTH_CONTROL_20260717"
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_sha256(payload: object) -> str:
    rendered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return _sha256(rendered.encode("utf-8"))


def _normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def test_source_health_receipt_binds_git_mirror_and_measured_statuses() -> None:
    receipt_bytes = RECEIPT.read_bytes()
    receipt = json.loads(receipt_bytes)
    rows = receipt["files"]

    assert receipt["schema"] == "lumencore.opportunity_source_health_mirror_receipt.v2"
    assert rows == sorted(rows, key=lambda row: row["relative_path"])
    assert receipt["manifest_sha256"] == _canonical_sha256(rows)
    assert receipt["boundaries"]["in_app_dsip_browser_touched"] is False
    assert receipt["boundaries"]["credentials_mirrored"] is False
    assert receipt["boundaries"]["upstream_response_bodies_mirrored"] is False

    receipt_relative_path = RECEIPT.relative_to(ROOT).as_posix()
    receipt_git_bytes = subprocess.check_output(
        ["git", "show", f":{receipt_relative_path}"],
        cwd=ROOT,
    )
    expected_sidecar = f"{_sha256(receipt_git_bytes)}  {RECEIPT.name}\n"
    assert SIDECAR.read_text(encoding="ascii") == expected_sidecar
    if MIRROR_ROOT.exists():
        mirror_receipt = (MIRROR_ROOT / RECEIPT.relative_to(ROOT)).read_bytes()
        assert _sha256(mirror_receipt) == _sha256(receipt_git_bytes)

    git_rows = []
    mirror_rows = []
    for row in rows:
        assert row["mirror_match"] is True
        mirror_rows.append(
            {
                key: row[key]
                for key in (
                    "relative_path",
                    "worktree_bytes",
                    "worktree_sha256",
                    "mirror_bytes",
                    "mirror_sha256",
                )
            }
        )
        if MIRROR_ROOT.exists():
            mirror_bytes = (MIRROR_ROOT / Path(row["relative_path"])).read_bytes()
            assert len(mirror_bytes) == row["mirror_bytes"]
            assert _sha256(mirror_bytes) == row["mirror_sha256"]

        if row["storage"] != "C_WORKTREE_GIT_INDEX_AND_E_MIRROR":
            assert "git_blob_sha256" not in row
            continue

        relative_path = row["relative_path"]
        git_bytes = subprocess.check_output(
            ["git", "show", f":{relative_path}"],
            cwd=ROOT,
        )
        index_fields = subprocess.check_output(
            ["git", "ls-files", "-s", "--", relative_path],
            cwd=ROOT,
            text=True,
        ).strip().split()
        assert index_fields[1] == row["git_index_object_id_sha1"]
        assert len(git_bytes) == row["git_blob_bytes"]
        assert _sha256(git_bytes) == row["git_blob_sha256"]
        assert _sha256(_normalized(git_bytes)) == row["normalized_content_sha256"]
        if row["git_worktree_equivalence"] == "EXACT_BYTES":
            assert row["git_blob_sha256"] == row["worktree_sha256"]
        else:
            assert row["git_worktree_equivalence"] == "UTF8_TEXT_NEWLINE_NORMALIZED"
        git_rows.append(
            {
                key: row[key]
                for key in (
                    "relative_path",
                    "git_index_object_id_sha1",
                    "git_blob_bytes",
                    "git_blob_sha256",
                )
            }
        )

    assert receipt["git_index_manifest_sha256"] == _canonical_sha256(git_rows)
    assert receipt["worktree_mirror_manifest_sha256"] == _canonical_sha256(mirror_rows)

    statuses = receipt["controls"]["source_status"]
    assert statuses["grants_gov"]["status"] == "LIVE_RESPONSES_RECORDS_PRESENT"
    assert statuses["grants_gov"]["records"] == 474
    assert statuses["sbir_gov"]["status"] == "RATE_LIMITED_INCONCLUSIVE"
    assert statuses["sbir_gov"]["http_status"] == 429
    assert statuses["sam_gov"]["status"] == "HTTP_404_EMPTY_RESPONSE_INCONCLUSIVE"
    assert statuses["sam_gov"]["http_status"] == 404
    assert receipt["controls"]["sam_credential_rotation"]["rotation_verified"] is False

    rendered = json.dumps(receipt)
    assert "api_key=" not in rendered.lower()
    assert "C:\\" not in rendered
    assert "E:\\" not in rendered
