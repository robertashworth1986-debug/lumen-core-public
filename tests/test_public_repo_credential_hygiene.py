from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "code" / "ops" / "VERIFY_PUBLIC_REPO_CREDENTIAL_HYGIENE.py"
RECEIPT = (
    ROOT
    / "grant_submissions"
    / "ONC_ARGOS_20260730"
    / "ARGOS_PUBLIC_REPOSITORY_SECURITY_GATE_2026-07-28.json"
)


def load_verifier():
    spec = importlib.util.spec_from_file_location(
        "verify_public_repo_credential_hygiene",
        VERIFIER,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_security_receipt_matches_placeholder_only_current_file():
    module = load_verifier()
    payload = module.build_payload()
    committed = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert module.canonical_json_bytes(payload) == module.canonical_json_bytes(
        committed
    )
    assert payload["current_file"]["placeholder_only"] is True
    assert payload["current_file"]["non_placeholder_value_count"] == 0
    assert payload["current_file"]["non_placeholder_field_names"] == []
    assert payload["current_file"]["required_environment_references_present"] is True
    assert payload["history"]["historical_exposure_detected"] is True
    assert payload["history"]["scan_complete"] is True
    assert payload["history"]["scan_failure_count"] == 0
    assert payload["history"]["scan_scope"] == (
        "HEAD_REACHABLE_UNIQUE_BLOBS_FOR_TARGET_PATH"
    )
    assert (
        payload["history"]["remote_public_history_verification_confirmed"]
        is False
    )
    assert payload["history"]["historical_exposed_blob_count"] == 1
    assert payload["history"]["target_history_blob_count"] == 2
    assert module.SHA256_RE.fullmatch(
        payload["history"]["target_history_blob_set_sha256"]
    )
    assert set(payload["history"]["historical_sensitive_field_names"]) == {
        "api_key",
        "client_id",
        "client_secret",
    }
    assert payload["public_repository_link_allowed"] is False
    assert payload["sanitized_external_response_allowed"] is True
    assert payload["final_argos_send_allowed_by_security_gate"] is True
    assert payload["external_action_performed"] is False


def test_status_evidence_receipts_are_structured_and_fail_closed():
    module = load_verifier()
    status = module.read_json(module.STATUS_PATH)
    module.validate_status(status)

    tampered = json.loads(json.dumps(status))
    tampered["providers"]["spotify"]["rotation_confirmed"] = True
    tampered["providers"]["spotify"]["evidence_receipt"] = "looks good"
    with pytest.raises(
        module.CredentialHygieneError,
        match="STATUS_ROTATION_SPOTIFY_EVIDENCE_SHAPE_INVALID",
    ):
        module.validate_status(tampered)


def test_historical_object_read_failure_blocks_the_scan(monkeypatch):
    module = load_verifier()

    def fake_git_output(*args, **_kwargs):
        if args[:2] == ("rev-parse", "--is-shallow-repository"):
            return "false\n"
        if args[:3] == ("rev-parse", "--verify", "HEAD"):
            return ("f" * 40) + "\n"
        if args[0] == "rev-list":
            return ("a" * 40) + "\n"
        if args[0] == "rev-parse":
            return ("b" * 40) + "\n"
        raise AssertionError(args)

    monkeypatch.setattr(module, "git_output", fake_git_output)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1,
            stdout=b"",
            stderr=b"synthetic read failure",
        ),
    )
    with pytest.raises(
        module.CredentialHygieneError,
        match="HISTORY_OBJECT_READ_FAILED",
    ):
        module.historical_exposure_summary()


def test_historical_scan_rejects_a_shallow_repository(monkeypatch):
    module = load_verifier()
    monkeypatch.setattr(
        module,
        "git_output",
        lambda *args, **_kwargs: "true\n"
        if args[:2] == ("rev-parse", "--is-shallow-repository")
        else "",
    )

    with pytest.raises(
        module.CredentialHygieneError,
        match="HISTORY_SCAN_REQUIRES_COMPLETE_CLONE",
    ):
        module.historical_exposure_summary()


def test_scanner_reports_field_metadata_without_returning_values():
    module = load_verifier()
    synthetic_value = "SYNTHETIC_VALUE_123456789"
    scan = module.scan_text(
        "api_key: "
        + synthetic_value
        + "\nclient_id: ${SPOTIFY_CLIENT_ID}\n"
    )

    assert scan["non_placeholder_fields"] == [
        {
            "line": 1,
            "key": "api_key",
            "placeholder_like": False,
        }
    ]
    assert synthetic_value not in json.dumps(scan)
    assert scan["env_references"] == ["SPOTIFY_CLIENT_ID"]


def test_target_hash_is_stable_across_line_endings(tmp_path):
    module = load_verifier()
    lf = tmp_path / "registry-lf.yaml"
    crlf = tmp_path / "registry-crlf.yaml"
    lf.write_bytes(b"api_key: ${YOUTUBE_API_KEY}\n")
    crlf.write_bytes(b"api_key: ${YOUTUBE_API_KEY}\r\n")

    assert module.file_sha256(lf) == module.file_sha256(crlf)


def test_security_verifier_cli_is_current_and_redacted():
    result = subprocess.run(
        [sys.executable, str(VERIFIER), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output == {
        "status": "CURRENT",
        "decision": "ALLOW_SANITIZED_EXTERNAL_RESPONSE_BLOCK_PUBLIC_REPO_LINK",
        "current_file_placeholder_only": True,
        "historical_exposure_detected": True,
        "historical_scan_complete": True,
        "provider_rotations_confirmed": False,
        "remote_public_history_verification_confirmed": False,
        "public_repository_link_allowed": False,
        "final_argos_send_allowed_by_security_gate": True,
        "external_action_performed": False,
    }
