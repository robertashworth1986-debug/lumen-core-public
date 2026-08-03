from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_NOAHS_PROOF_CHAIN_GATE.py"
CONFIG = ROOT / "config" / "noahs_proof_chain_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("noahs_proof_chain_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_config_declares_exact_chain_and_closes_claim_boundaries():
    module = load_module()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    validation = module.validate_config(config)

    assert validation["passed"] is True
    assert tuple(validation["link_ids"]) == module.REQUIRED_LINK_IDS
    assert all(validation["checks"].values())
    assert config["architecture_name"] == "NOAHS"
    assert config["policies"]["allow_network_access"] is False
    assert config["policies"]["allow_file_mutation"] is False
    assert config["policies"]["allow_external_action"] is False
    assert config["policies"]["infer_performance_from_internal_receipts"] is False
    front_door = next(row for row in config["links"] if row["id"] == "public_front_door")
    artifact_ids = {row["id"] for row in front_door["artifacts"]}
    rule_ids = {row["id"] for row in front_door["rules"]}
    assert "live_domain_service_contract" in artifact_ids
    assert "front_door_service_contract" in rule_ids
    claim_flags = {
        key: value
        for key, value in config["no_claim_boundaries"].items()
        if key.endswith("_claim_allowed")
    }
    assert claim_flags
    assert set(claim_flags.values()) == {False}


def test_current_gate_fails_closed_and_hashes_declared_sources():
    module = load_module()
    gate = module.build_gate(root=ROOT)

    assert gate["schema"] == "noahs_proof_chain_gate.v1"
    assert gate["architecture_name"] == "NOAHS"
    assert gate["overall_state"] == "BLOCKED"
    assert gate["reviewer_release_ready"] is False
    assert gate["summary"]["link_count"] == 10
    assert gate["summary"]["blocked_link_count"] > 0
    assert gate["controls"] == {
        "network_access_performed": False,
        "files_written": False,
        "external_action_performed": False,
        "performance_inference_performed": False,
        "symlinks_followed": False,
    }
    for link in gate["links"]:
        for artifact in link["artifacts"]:
            if artifact["exists"]:
                assert module.is_sha256(artifact["sha256"])

    blocker_codes = {row["code"] for row in gate["blockers"]}
    assert {
        "ZERO_BYTE_ARTIFACT",
        "UNSAFE_EVIDENCE_PATH",
        "BASELINE_REPLAY_BODY_UNAVAILABLE",
    } & blocker_codes
    assert "PUBLICATION_CUSTODY_DRIFT" in blocker_codes
    assert "LIVE_DOMAIN_SERVICE_CONTRACT_BLOCKED" in blocker_codes
    assert "BASELINE_INCOMPLETE" in blocker_codes
    assert "CURRENT_ROW_SUMMARY_INCONSISTENT" in blocker_codes
    assert "SAMPLE_GATE_CLOSED" in blocker_codes
    assert "REPRODUCIBILITY_NOT_CURRENT" in blocker_codes
    assert "IMMUTABLE_MANIFEST_DRIFT" in blocker_codes
    assert "GIT_DIRTY" in blocker_codes
    assert "INDEPENDENT_VALIDATION_MISSING" in blocker_codes

    unhashed = {key: value for key, value in gate.items() if key != "gate_sha256"}
    assert gate["gate_sha256"] == module.canonical_sha256(unhashed)


def test_artifact_inspection_blocks_missing_zero_and_stale(tmp_path):
    module = load_module()
    zero_path = tmp_path / "zero.json"
    zero_path.write_bytes(b"")
    stale_path = tmp_path / "stale.json"
    stale_path.write_text(
        json.dumps({"generated_utc": "2026-07-01T00:00:00+00:00"}),
        encoding="utf-8",
    )
    store = module.ArtifactStore(tmp_path)
    observed = datetime(2026, 7, 25, tzinfo=timezone.utc)

    missing = module.inspect_artifact(
        store,
        {"id": "missing", "path": "missing.json", "min_bytes": 1},
        observed_utc=observed,
    )
    zero = module.inspect_artifact(
        store,
        {"id": "zero", "path": "zero.json", "min_bytes": 1},
        observed_utc=observed,
    )
    stale = module.inspect_artifact(
        store,
        {
            "id": "stale",
            "path": "stale.json",
            "min_bytes": 1,
            "max_age_hours": 24,
            "timestamp_fields": ["generated_utc"],
        },
        observed_utc=observed,
    )

    assert {row["code"] for row in missing["blockers"]} == {"MISSING_ARTIFACT"}
    assert "ZERO_BYTE_ARTIFACT" in {row["code"] for row in zero["blockers"]}
    assert "STALE_ARTIFACT" in {row["code"] for row in stale["blockers"]}


def test_manifest_check_detects_changed_source(tmp_path):
    module = load_module()
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("current", encoding="utf-8")
    manifest = {
        "artifacts": [
            {
                "path": "evidence.txt",
                "bytes": len("original"),
                "sha256": module.canonical_sha256("not-the-file"),
            }
        ]
    }
    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    store = module.ArtifactStore(tmp_path)
    result = module.check_manifest_entries(
        store,
        {
            "id": "manifest",
            "type": "manifest_entries",
            "artifact": "manifest.json",
            "array_fields": ["artifacts"],
            "path_field": "path",
            "sha256_field": "sha256",
            "bytes_field": "bytes",
            "min_entries": 1,
        },
    )

    assert result["passed"] is False
    assert result["matched_count"] == 0
    assert result["mismatches"][0]["reason"] == "sha256_mismatch"
    assert {row["code"] for row in result["blockers"]} == {
        "MANIFEST_HASH_MISMATCH"
    }


def test_append_only_chain_verifier_detects_broken_prior_hash(tmp_path):
    module = load_module()
    first = {
        "schema": "test.v1",
        "prior_record_chain_sha256": module.ZERO_HASH,
        "protocol_sha256": "a" * 64,
        "protocol_commit": "b" * 40,
        "value": 1,
    }
    first["record_sha256"] = module.canonical_sha256(first)
    second = {
        "schema": "test.v1",
        "prior_record_chain_sha256": "f" * 64,
        "protocol_sha256": "a" * 64,
        "protocol_commit": "b" * 40,
        "value": 2,
    }
    second["record_sha256"] = module.canonical_sha256(second)
    chain_path = tmp_path / "chain.jsonl"
    chain_path.write_text(
        "\n".join(
            [
                json.dumps(first, sort_keys=True, separators=(",", ":")),
                json.dumps(second, sort_keys=True, separators=(",", ":")),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = module.verify_jsonl_chain(
        module.ArtifactStore(tmp_path),
        "chain.jsonl",
        expected_protocol_sha256="a" * 64,
        expected_protocol_commit="b" * 40,
    )

    assert result["passed"] is False
    assert result["record_count"] == 1
    assert "CHAIN_PRIOR_HASH_MISMATCH" in {
        row["code"] for row in result["blockers"]
    }


def test_repository_paths_cannot_escape_or_follow_symlinks(tmp_path):
    module = load_module()
    store = module.ArtifactStore(tmp_path)

    invalid = store.snapshot("../outside.json")
    assert invalid["exists"] is False
    assert "repository-relative" in invalid["path_error"]
