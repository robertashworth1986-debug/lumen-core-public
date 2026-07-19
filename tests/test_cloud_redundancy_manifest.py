from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "BUILD_CLOUD_REDUNDANCY_MANIFEST.py"
POLICY_PATH = ROOT / "config" / "cloud_redundancy_policy_v1.json"
FIXED_TIME = "2026-07-18T18:00:00Z"
FIXTURE_SOURCE = "build_week/prooflock_console/public_receipt.json"
FIXTURE_SCHEMA = "lumencore.test_public_receipt.v1"


def load_module():
    spec = importlib.util.spec_from_file_location("cloud_redundancy_manifest", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def public_receipt(**updates) -> dict:
    payload = {
        "schema": FIXTURE_SCHEMA,
        "receipt_id": "bounded-public-test-receipt",
        "status": "PASS",
        "artifact_path": "artifacts/public/result.json",
        "claim_boundary": "Byte identity only; no external completion or approval is asserted.",
    }
    payload.update(updates)
    return payload


def encode_receipt(payload: dict) -> bytes:
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def fixture_lane(tmp_path: Path, payload: dict | None = None) -> tuple[Path, Path, Path, dict]:
    root = tmp_path / "repo"
    source = root / Path(*FIXTURE_SOURCE.split("/"))
    source.parent.mkdir(parents=True)
    raw = encode_receipt(payload or public_receipt())
    source.write_bytes(raw)

    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    policy["allowlist"] = [
        {
            "id": "bounded_public_test_receipt",
            "source_path": FIXTURE_SOURCE,
            "expected_sha256": sha256(raw),
            "receipt_schema": FIXTURE_SCHEMA,
            "classification": "PUBLIC_SAFE_NON_SECRET_RECEIPT",
            "public_safety_basis": "Synthetic public-safe receipt used only for an isolated test fixture.",
        }
    ]
    policy_path = root / "config" / "cloud_redundancy_policy_v1.json"
    policy_path.parent.mkdir(parents=True)
    policy_path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return root, policy_path, source, policy


def write_policy(policy_path: Path, policy: dict) -> None:
    policy_path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build(module, root: Path, policy_path: Path) -> dict:
    return module.build_manifest(policy_path, root=root, as_of_utc=FIXED_TIME)


def test_repository_policy_hashes_every_exact_public_receipt():
    module = load_module()
    manifest = module.build_manifest(POLICY_PATH, root=ROOT, as_of_utc=FIXED_TIME)

    summary = manifest["summary"]
    assert summary["manifest_state"] == "LOCAL_MANIFEST_READY_REMOTE_REDUNDANCY_NOT_PROVEN"
    assert summary["selected_source_count"] == 2
    assert summary["hashed_source_count"] == summary["selected_source_count"]
    assert summary["all_sources_hashed"] is True
    assert summary["all_hashes_match"] is True
    assert summary["independent_redundant_copy_proven"] is False
    assert all(row["sha256"] and len(row["sha256"]) == 64 for row in manifest["source_artifacts"])
    assert all(row["content_scan"] == {"state": "PASS", "findings": []} for row in manifest["source_artifacts"])


def test_fixed_timestamp_produces_byte_deterministic_output(tmp_path: Path):
    module = load_module()
    root, policy_path, _, _ = fixture_lane(tmp_path)

    first = build(module, root, policy_path)
    second = build(module, root, policy_path)
    assert first == second
    assert module.canonical_json_bytes(first) == module.canonical_json_bytes(second)
    assert module.render_markdown(first) == module.render_markdown(second)
    assert first["as_of_utc"] == FIXED_TIME
    assert first["manifest_sha256"] == second["manifest_sha256"]


@pytest.mark.parametrize(
    ("source_path", "term"),
    [
        ("build_week/prooflock_console/private/public_receipt.json", "PRIVATE"),
        ("build_week/prooflock_console/patent_receipt.json", "PATENT"),
        ("build_week/prooflock_console/portal_receipt.json", "PORTAL"),
        ("build_week/prooflock_console/email_receipt.json", "EMAIL"),
        ("build_week/prooflock_console/credential_receipt.json", "CREDENTIAL"),
        ("build_week/prooflock_console/raw/evidence_receipt.json", "RAW"),
        ("build_week/prooflock_console/registry_receipt.json", "REGISTRY"),
        ("build_week/prooflock_console/api_key_receipt.json", "API_KEY"),
    ],
)
def test_denied_source_classes_are_rejected_before_source_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_path: str,
    term: str,
):
    module = load_module()
    root, policy_path, _, policy = fixture_lane(tmp_path)
    policy["allowlist"][0]["source_path"] = source_path
    write_policy(policy_path, policy)

    def forbidden_read(*_args, **_kwargs):
        raise AssertionError("a statically denied source must never be opened")

    monkeypatch.setattr(module, "read_source_bytes", forbidden_read)
    with pytest.raises(module.PolicyError, match=term):
        build(module, root, policy_path)


@pytest.mark.parametrize(
    "source_path",
    [
        "../public_receipt.json",
        "build_week/prooflock_console/*.json",
        "C:/private/public_receipt.json",
        "build_week\\prooflock_console\\public_receipt.json",
    ],
)
def test_traversal_globs_and_platform_paths_are_rejected(tmp_path: Path, source_path: str):
    module = load_module()
    root, policy_path, _, policy = fixture_lane(tmp_path)
    policy["allowlist"][0]["source_path"] = source_path
    write_policy(policy_path, policy)

    with pytest.raises(module.PolicyError):
        build(module, root, policy_path)


def test_unlisted_neighbor_is_never_discovered_or_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = load_module()
    root, policy_path, source, _ = fixture_lane(tmp_path)
    neighbor = source.with_name("unlisted_secret_receipt.json")
    neighbor.write_text('{"schema":"x","api_key":"sk-proj-unlisted-secret-value"}\n', encoding="utf-8")
    original = module.read_source_bytes
    reads: list[Path] = []

    def recording_read(path: Path, max_bytes: int):
        reads.append(path)
        return original(path, max_bytes)

    monkeypatch.setattr(module, "read_source_bytes", recording_read)
    manifest = build(module, root, policy_path)
    assert reads == [source]
    assert neighbor.name not in json.dumps(manifest)
    assert manifest["capability_boundary"]["directory_discovery_performed"] is False


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("e_drive", "physical_disk_id", "DIFFERENT_DISK"),
        ("e_drive", "counts_as_independent_redundancy", True),
        ("icloud", "remote_completion", "PROVEN"),
        ("google_drive", "upload", "COMPLETE"),
        ("google_drive", "readback_verification", "PASS"),
    ],
)
def test_topology_cannot_be_tampered_into_false_redundancy(
    tmp_path: Path,
    section: str,
    key: str,
    value: object,
):
    module = load_module()
    root, policy_path, _, policy = fixture_lane(tmp_path)
    policy["storage_topology"][section][key] = value
    write_policy(policy_path, policy)

    with pytest.raises(module.PolicyError, match="storage_topology"):
        build(module, root, policy_path)


def test_deny_boundary_and_no_io_controls_cannot_be_weakened(tmp_path: Path):
    module = load_module()
    root, policy_path, _, policy = fixture_lane(tmp_path)

    weakened = copy.deepcopy(policy)
    weakened["denied_path_terms"].remove("private")
    write_policy(policy_path, weakened)
    with pytest.raises(module.PolicyError, match="denied_path_terms"):
        build(module, root, policy_path)

    weakened = copy.deepcopy(policy)
    weakened["action_boundary"]["uploads"] = "ALLOWED"
    write_policy(policy_path, weakened)
    with pytest.raises(module.PolicyError, match="action_boundary"):
        build(module, root, policy_path)


def test_hash_mismatch_blocks_but_still_records_observed_hash(tmp_path: Path):
    module = load_module()
    root, policy_path, source, _ = fixture_lane(tmp_path)
    source.write_bytes(encode_receipt(public_receipt(status="CHANGED")))

    manifest = build(module, root, policy_path)
    row = manifest["source_artifacts"][0]
    assert row["sha256"] == sha256(source.read_bytes())
    assert row["hash_matches"] is False
    assert "SOURCE_SHA256_MISMATCH" in row["blockers"]
    assert manifest["summary"]["hashed_source_count"] == 1
    assert manifest["summary"]["manifest_state"] == "BLOCKED_FAIL_CLOSED"
    assert manifest["capability_boundary"]["upload_performed"] is False


def test_secret_content_is_blocked_without_echoing_the_value(tmp_path: Path):
    module = load_module()
    secret = "sk-proj-THIS_VALUE_MUST_NEVER_APPEAR_123456789"
    root, policy_path, _, policy = fixture_lane(tmp_path, public_receipt(api_key=secret))
    source = root / Path(*FIXTURE_SOURCE.split("/"))
    policy["allowlist"][0]["expected_sha256"] = sha256(source.read_bytes())
    write_policy(policy_path, policy)

    manifest = build(module, root, policy_path)
    row = manifest["source_artifacts"][0]
    assert row["content_scan"]["state"] == "BLOCKED"
    assert "SENSITIVE_FIELD_HAS_VALUE" in row["blockers"]
    assert any(code.startswith("SECRET_CONTENT_") for code in row["blockers"])
    assert secret not in json.dumps(manifest)
    assert manifest["summary"]["manifest_state"] == "BLOCKED_FAIL_CLOSED"


def test_raw_email_content_and_personal_address_are_blocked(tmp_path: Path):
    module = load_module()
    message = "From: sender@example.test\nTo: recipient@example.test\nSubject: private export"
    root, policy_path, _, _ = fixture_lane(tmp_path, public_receipt(message=message))

    manifest = build(module, root, policy_path)
    blockers = set(manifest["source_artifacts"][0]["blockers"])
    assert "RAW_EMAIL_CONTENT" in blockers
    assert "PERSONAL_DATA_EMAIL_ADDRESS" in blockers
    assert "sender@example.test" not in json.dumps(manifest)


@pytest.mark.parametrize(
    "embedded_path",
    [
        "private/export.json",
        "patent/claims.json",
        "portal/submission.json",
        "email/message.json",
        "credential/store.json",
        "evidence/raw/capture.json",
    ],
)
def test_denied_embedded_paths_block_an_otherwise_allowlisted_receipt(tmp_path: Path, embedded_path: str):
    module = load_module()
    root, policy_path, _, _ = fixture_lane(tmp_path, public_receipt(artifact_path=embedded_path))

    manifest = build(module, root, policy_path)
    row = manifest["source_artifacts"][0]
    assert row["state"] == "BLOCKED_FAIL_CLOSED"
    assert any(code.startswith("EMBEDDED_DENIED_PATH_") for code in row["blockers"])
    assert embedded_path not in json.dumps(manifest)


def test_schema_mismatch_and_symlink_escape_fail_closed(tmp_path: Path):
    module = load_module()
    root, policy_path, source, _ = fixture_lane(tmp_path, public_receipt(schema="wrong.schema.v1"))
    mismatch = build(module, root, policy_path)
    assert "RECEIPT_SCHEMA_MISMATCH" in mismatch["source_artifacts"][0]["blockers"]

    outside = tmp_path / "outside_receipt.json"
    outside.write_bytes(encode_receipt(public_receipt()))
    source.unlink()
    try:
        os.symlink(outside, source)
    except OSError:
        pytest.skip("symbolic links are unavailable in this Windows environment")
    linked = build(module, root, policy_path)
    assert "SYMLINK_IN_PATH" in linked["source_artifacts"][0]["blockers"]
    assert linked["source_artifacts"][0]["sha256"] is None


def test_manifest_states_storage_and_connector_truth_without_external_io(tmp_path: Path):
    module = load_module()
    root, policy_path, _, _ = fixture_lane(tmp_path)
    manifest = build(module, root, policy_path)

    topology = manifest["storage_topology"]
    assert topology["c_drive"]["physical_disk_id"] == topology["e_drive"]["physical_disk_id"]
    assert topology["e_drive"]["relationship_to_c"] == "C_AND_E_ARE_VOLUMES_ON_THE_SAME_PHYSICAL_DISK"
    assert topology["e_drive"]["counts_as_independent_redundancy"] is False
    assert topology["icloud"]["role"] == "LOCAL_SYNC_CANDIDATE_ONLY"
    assert topology["icloud"]["remote_completion"] == "NOT_PROVEN"
    assert topology["google_drive"]["role"] == "OFF_DEVICE_TARGET"
    assert topology["google_drive"]["connector_action"] == "SEPARATE_UPLOAD_AND_READBACK_REQUIRED"

    capability = manifest["capability_boundary"]
    allowed_true = {"policy_file_read", "allowlisted_source_bytes_read_locally"}
    assert {key for key, value in capability.items() if value is True} == allowed_true
    assert manifest["connector_actions"]["google_drive_upload_and_readback"]["state"] == "NOT_PERFORMED"
    assert manifest["connector_actions"]["icloud_remote_completion_verification"]["remote_completion"] == "NOT_PROVEN"


def test_markdown_says_remote_completion_is_not_proven(tmp_path: Path):
    module = load_module()
    root, policy_path, _, _ = fixture_lane(tmp_path)
    markdown = module.render_markdown(build(module, root, policy_path))

    assert "same physical disk as `C:`" in markdown
    assert "remote completion `NOT_PROVEN`" in markdown
    assert "separate connector upload/readback `NOT_PERFORMED`" in markdown
    assert "performed no copy, sync, upload, readback, network, registry, credential" in markdown
