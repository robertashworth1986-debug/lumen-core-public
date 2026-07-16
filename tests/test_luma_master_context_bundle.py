from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "code" / "ops" / "BUILD_LUMA_MASTER_CONTEXT_BUNDLE.py"
SPEC = importlib.util.spec_from_file_location("luma_master_context_bundle", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def fixture_registry() -> dict:
    return {
        "schema": "test_registry",
        "private_output": {
            "vault_relative_dir": "PRIVATE_CONTEXT",
            "latest_json": "LUMA_MASTER_CONTEXT_LATEST.json",
            "latest_markdown": "LUMA_MASTER_CONTEXT_LATEST.md",
            "latest_manifest": "LUMA_MASTER_CONTEXT_MANIFEST_LATEST.json",
            "run_dir": "RUNS",
        },
        "startup_order": ["reviewer_evidence", "private_note_context"],
        "sources": [
            {
                "id": "reviewer_context",
                "role": "reviewer_evidence",
                "location": "repo",
                "path": "reviewer.json",
                "builder": "builder.py",
                "status": "current",
                "canonical": True,
                "privacy": "public_safe",
                "max_age_hours": 100000,
            },
            {
                "id": "private_note_capsule",
                "role": "private_note_context",
                "location": "vault",
                "path": "notes.json",
                "builder": "notes.py",
                "status": "current",
                "canonical": True,
                "privacy": "private_metadata",
                "max_age_hours": 100000,
            },
        ],
    }


def test_bundle_keeps_source_bodies_out_and_extracts_only_safe_summary(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    repo.mkdir()
    write_json(
        repo / "reviewer.json",
        {
            "current_evidence_posture": {
                "highest_repository_wide_supported_level": 3,
                "level_5_attained": False,
            },
            "proof_cards": [{"private_body": "DO_NOT_COPY_THIS_SENTINEL"}],
            "source_input_chain_sha256": "a" * 64,
        },
    )
    write_json(
        vault / "notes.json",
        {
            "source_summary": {
                "record_count": 12,
                "unique_content_hashes": 8,
                "duplicate_file_count": 4,
            },
            "note_bodies": ["DO_NOT_COPY_THIS_SENTINEL"],
        },
    )
    registry_path = repo / "registry.json"
    write_json(registry_path, fixture_registry())

    payload = MODULE.build_payload(
        repo_root=repo,
        vault_root=vault,
        registry_path=registry_path,
        generated_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
    )

    serialized = json.dumps(payload)
    assert "DO_NOT_COPY_THIS_SENTINEL" not in serialized
    assert payload["integrity"]["canonical_gate_passed"] is True
    assert payload["canonical_source_by_role"]["reviewer_evidence"] == "reviewer_context"
    assert set(payload["startup_order"]) == set(payload["canonical_source_by_role"])


def test_bundle_detects_parallel_canonical_roles(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    repo.mkdir()
    write_json(repo / "reviewer.json", {})
    write_json(vault / "notes.json", {})
    registry = fixture_registry()
    registry["sources"][1]["role"] = "reviewer_evidence"
    registry_path = repo / "registry.json"
    write_json(registry_path, registry)

    payload = MODULE.build_payload(
        repo_root=repo,
        vault_root=vault,
        registry_path=registry_path,
        generated_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
    )

    assert payload["integrity"]["canonical_gate_passed"] is False
    assert payload["integrity"]["canonical_role_collision_count"] == 1


def test_bundle_detects_stale_current_canonical_sources(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    repo.mkdir()
    write_json(repo / "reviewer.json", {})
    write_json(vault / "notes.json", {})
    registry = fixture_registry()
    for source in registry["sources"]:
        source["max_age_hours"] = 1
    registry_path = repo / "registry.json"
    write_json(registry_path, registry)

    payload = MODULE.build_payload(
        repo_root=repo,
        vault_root=vault,
        registry_path=registry_path,
        generated_at=datetime.now(timezone.utc) + timedelta(hours=2),
    )

    assert payload["integrity"]["canonical_gate_passed"] is True
    assert payload["integrity"]["freshness_gate_passed"] is False
    assert set(payload["integrity"]["stale_current_canonical_sources"]) == {
        "reviewer_context",
        "private_note_capsule",
    }


def test_write_bundle_creates_hash_verified_latest_and_run_receipts(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    repo.mkdir()
    write_json(repo / "reviewer.json", {})
    write_json(vault / "notes.json", {})
    registry_path = repo / "registry.json"
    write_json(registry_path, fixture_registry())
    payload = MODULE.build_payload(
        repo_root=repo,
        vault_root=vault,
        registry_path=registry_path,
        generated_at=datetime(2026, 7, 14, 5, 30, tzinfo=timezone.utc),
    )

    verification = MODULE.write_bundle(payload, vault_root=vault, registry_path=registry_path)

    latest = vault / "PRIVATE_CONTEXT" / "LUMA_MASTER_CONTEXT_LATEST.json"
    manifest = json.loads(
        (vault / "PRIVATE_CONTEXT" / "LUMA_MASTER_CONTEXT_MANIFEST_LATEST.json").read_text(encoding="utf-8")
    )
    assert latest.is_file()
    assert verification["json_sha256"] == manifest["artifacts"][latest.name]
    assert Path(verification["run_dir"]).is_dir()


def test_published_bundle_gate_detects_git_and_artifact_drift(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    repo.mkdir()
    write_json(repo / "reviewer.json", {})
    write_json(vault / "notes.json", {})
    registry_path = repo / "registry.json"
    write_json(registry_path, fixture_registry())
    payload = MODULE.build_payload(
        repo_root=repo,
        vault_root=vault,
        registry_path=registry_path,
        generated_at=datetime(2026, 7, 14, 5, 30, tzinfo=timezone.utc),
    )
    payload["git"] = {
        "available": True,
        "head": "a" * 40,
        "branch": "reviewer-branch",
        "dirty_path_count": 0,
    }
    MODULE.write_bundle(payload, vault_root=vault, registry_path=registry_path)

    clean = MODULE.verify_published_bundle(payload, vault_root=vault, registry_path=registry_path)
    assert clean["gate_passed"] is True
    assert clean["reasons"] == []

    moved_head = deepcopy(payload)
    moved_head["git"]["head"] = "b" * 40
    stale = MODULE.verify_published_bundle(moved_head, vault_root=vault, registry_path=registry_path)
    assert stale["gate_passed"] is False
    assert stale["reasons"] == ["git_head_mismatch"]

    latest_markdown = vault / "PRIVATE_CONTEXT" / "LUMA_MASTER_CONTEXT_LATEST.md"
    latest_markdown.write_text("tampered\n", encoding="utf-8")
    tampered = MODULE.verify_published_bundle(payload, vault_root=vault, registry_path=registry_path)
    assert tampered["gate_passed"] is False
    assert tampered["reasons"] == ["latest_markdown_hash_mismatch"]
