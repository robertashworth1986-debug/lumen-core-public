from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "BUILD_PUBLIC_RELEASE_SYNC_PLAN.py"


def load_module():
    spec = importlib.util.spec_from_file_location("public_release_sync_plan", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def fixture_repo(
    tmp_path: Path,
    *,
    content: str = "Bounded internal evidence only. No external validation is asserted.\n",
    source_rel: str = "docs/public.md",
    target_rel: str = "public/evidence/public.md",
) -> tuple[Path, Path, dict]:
    root = tmp_path / "repo"
    target = tmp_path / "target"
    root.mkdir(parents=True)
    target.mkdir(parents=True)
    source = root / source_rel
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(content, encoding="utf-8")
    receipt = root / "tests" / "receipt.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text('{"passed":true}\n', encoding="utf-8")
    run_git(root, "init")
    run_git(root, "config", "user.email", "test@example.invalid")
    run_git(root, "config", "user.name", "Test Runner")
    run_git(root, "add", source_rel, "tests/receipt.json")
    run_git(root, "commit", "-m", "fixture")
    commit = run_git(root, "rev-parse", "HEAD")

    policy = {
        "schema": "lumencore.public_release_sync_policy.v1",
        "status": "frozen",
        "mode": "DRY_RUN_ONLY",
        "allowed_source_roots": ["docs"],
        "allowed_target_roots": ["public/evidence"],
        "allowed_extension_mime": {".md": "text/markdown"},
        "allowed_claim_states": ["BOUNDED_INTERNAL_EVIDENCE"],
        "denied_path_tokens": sorted(load_module().HARD_DENIED_PATH_TOKENS),
        "allowed_public_hosts": ["example.test"],
        "allowed_public_url_prefixes": ["/evidence/"],
        "max_source_bytes": 100000,
        "max_source_age_hours": 720,
        "network_actions": {action: "HUMAN_UNLOCK_REQUIRED" for action in load_module().NETWORK_ACTIONS},
        "allowlist": [
            {
                "id": "public_fixture",
                "source_path": source_rel,
                "expected_source_sha256": sha256(source),
                "target_path": target_rel,
                "public_url": "https://example.test/evidence/public.md",
                "mime_type": "text/markdown",
                "claim_state": "BOUNDED_INTERNAL_EVIDENCE",
                "claim_boundary": "Bounded internal evidence only; no approval or external validation is asserted.",
                "source_commit": commit,
                "last_validated_utc": "2026-07-17T00:00:00Z",
                "max_age_hours": 72,
                "test_receipt_refs": [
                    {"path": "tests/receipt.json", "expected_sha256": sha256(receipt)}
                ],
            }
        ],
    }
    policy_path = root / "config" / "policy.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    return root, target, policy


def write_policy(root: Path, policy: dict) -> Path:
    path = root / "config" / "policy.json"
    path.write_text(json.dumps(policy), encoding="utf-8")
    return path


def build(module, root: Path, target: Path, policy: dict):
    return module.build_plan(
        write_policy(root, policy),
        root=root,
        target_root=target,
        as_of_utc="2026-07-18T00:00:00Z",
    )


def blockers(plan: dict) -> set[str]:
    return set(plan["items"][0]["blockers"])


def test_private_path_is_rejected_before_release(tmp_path: Path):
    module = load_module()
    root, target, policy = fixture_repo(tmp_path, source_rel="docs/private/report.md")
    plan = build(module, root, target, policy)
    assert "SOURCE_PATH_DENIED_PRIVATE" in blockers(plan)
    assert plan["items"][0]["content_scan"]["state"] == "NOT_SCANNED"


def test_secret_like_content_is_blocked_without_echoing_value(tmp_path: Path):
    module = load_module()
    secret_value = "ABCD1234SUPERSECRET9999"
    root, target, policy = fixture_repo(tmp_path, content=f"api_key = {secret_value}\n")
    plan = build(module, root, target, policy)
    assert "SECRET_CONTENT_SECRET_ASSIGNMENT" in blockers(plan)
    assert secret_value not in json.dumps(plan)


def test_traversal_and_symlink_sources_are_rejected(tmp_path: Path):
    module = load_module()
    root, target, policy = fixture_repo(tmp_path)
    policy["allowlist"][0]["source_path"] = "../escape.md"
    traversal = build(module, root, target, policy)
    assert "source_path:TRAVERSAL_OR_NONCANONICAL" in blockers(traversal)

    root2, target2, policy2 = fixture_repo(tmp_path / "linkcase")
    source = root2 / "docs" / "public.md"
    outside = tmp_path / "outside.md"
    outside.write_text("outside\n", encoding="utf-8")
    source.unlink()
    try:
        os.symlink(outside, source)
    except OSError:
        pytest.skip("symbolic links are not available in this Windows environment")
    linked = build(module, root2, target2, policy2)
    assert "SOURCE_SYMLINK_IN_PATH" in blockers(linked)


def test_unsupported_public_claim_is_blocked(tmp_path: Path):
    module = load_module()
    root, target, policy = fixture_repo(
        tmp_path,
        content="This platform is government approved, guaranteed, and the world's best.\n",
    )
    plan = build(module, root, target, policy)
    assert {
        "UNSUPPORTED_CLAIM_GOVERNMENT_APPROVAL",
        "UNSUPPORTED_CLAIM_GUARANTEE",
        "UNSUPPORTED_CLAIM_SUPERLATIVE",
    }.issubset(blockers(plan))


def test_explicit_negative_claim_boundary_is_not_promoted_to_a_claim(tmp_path: Path):
    module = load_module()
    root, target, policy = fixture_repo(
        tmp_path,
        content="This pass does not prove government approval, guaranteed value, or a world's best result.\n",
    )
    plan = build(module, root, target, policy)
    assert not {code for code in blockers(plan) if code.startswith("UNSUPPORTED_CLAIM_")}


def test_stale_source_hash_and_commit_are_blocked(tmp_path: Path):
    module = load_module()
    root, target, policy = fixture_repo(tmp_path)
    (root / "docs" / "public.md").write_text("changed after validation\n", encoding="utf-8")
    plan = build(module, root, target, policy)
    assert "STALE_SOURCE_HASH" in blockers(plan)
    assert "SOURCE_DIFFERS_FROM_COMMIT" in blockers(plan)


def test_existing_exact_hash_is_idempotent_noop(tmp_path: Path):
    module = load_module()
    root, target, policy = fixture_repo(tmp_path)
    source = root / "docs" / "public.md"
    destination = target / "public" / "evidence" / "public.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
    plan = build(module, root, target, policy)
    row = plan["items"][0]
    assert row["blockers"] == []
    assert row["planned_action"] == "NOOP_EXACT_MATCH"
    assert row["target_probe"]["exact_hash_match"] is True
    assert row["target_probe"]["overwrite_allowed"] is False


def test_existing_different_target_is_never_overwritten(tmp_path: Path):
    module = load_module()
    root, target, policy = fixture_repo(tmp_path)
    destination = target / "public" / "evidence" / "public.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("different public content\n", encoding="utf-8")
    before = destination.read_bytes()
    plan = build(module, root, target, policy)
    assert "TARGET_EXISTS_HASH_MISMATCH" in blockers(plan)
    assert plan["items"][0]["planned_action"] == "BLOCK"
    assert destination.read_bytes() == before


def test_plan_is_deterministic_for_same_inputs(tmp_path: Path):
    module = load_module()
    root, target, policy = fixture_repo(tmp_path)
    first = build(module, root, target, policy)
    second = build(module, root, target, policy)
    assert first == second
    assert first["plan_sha256"] == second["plan_sha256"]


def test_all_network_actions_require_human_unlock(tmp_path: Path):
    module = load_module()
    root, target, policy = fixture_repo(tmp_path)
    plan = build(module, root, target, policy)
    assert set(plan["network_actions"]) == set(module.NETWORK_ACTIONS)
    assert set(plan["network_actions"].values()) == {"HUMAN_UNLOCK_REQUIRED"}
    assert plan["human_gate"] == "HUMAN_UNLOCK_REQUIRED"
    capability = plan["capability_boundary"]
    assert capability["allowlisted_candidate_bytes_scanned_locally"] is True
    assert all(
        value is False
        for key, value in capability.items()
        if key != "allowlisted_candidate_bytes_scanned_locally"
    )
    assert plan["summary"]["network_action_performed"] is False
    assert plan["summary"]["public_release_completed"] is False
