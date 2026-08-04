from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "BUILD_RELEASE_SCOPE_HYGIENE_GATE.py"
AS_OF = "2026-08-01T23:30:00Z"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "release_scope_hygiene_gate", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def write(repo: Path, relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_git(repo, "init")
    run_git(repo, "config", "user.email", "test@example.invalid")
    run_git(repo, "config", "user.name", "Test Runner")
    write(repo, "seed.txt", "base\n")
    run_git(repo, "add", "seed.txt")
    run_git(repo, "commit", "-m", "base")
    return repo


def stage_fixture(module, repo: Path, relative: str = "dashboard/public.txt") -> Path:
    stage_root = repo / ".deploy_stage" / "public_reviewer_release_test"
    content = "bounded public evidence\n"
    write(repo, f".deploy_stage/public_reviewer_release_test/{relative}", content)
    staged_file = stage_root / relative
    staged_bytes = staged_file.read_bytes()
    manifest = {
        "schema": module.STAGE_SCHEMA,
        "stage_state": "LOCAL_STAGE_READY",
        "plan_path": "out/ops/release_plan.json",
        "plan_sha256": "a" * 64,
        "stage_root": ".deploy_stage/public_reviewer_release_test",
        "files": [
            {
                "id": "bounded_public_evidence",
                "source_path": "out/reviewer/public.txt",
                "source_sha256": hashlib.sha256(staged_bytes).hexdigest(),
                "bytes": len(staged_bytes),
                "staged_relative_path": relative,
                "intended_public_target_path": relative,
                "public_url": "https://example.invalid/public.txt",
                "mime_type": "text/plain",
            }
        ],
        "summary": {
            "item_count": 1,
            "files_staged_locally": True,
            "public_root_copy_performed": False,
            "network_action_performed": False,
            "publication_performed": False,
            "stage_ready": True,
        },
        "authority": {
            "human_unlock_required_for_vps_or_publication": True,
            "external_action_authorized_by_stage": False,
            "credentials_required_for_local_stage": False,
        },
        "boundary": "Local stage only.",
    }
    manifest["manifest_sha256"] = module.canonical_sha256(manifest)
    manifest_path = stage_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest_path


def test_safe_source_only_index_passes(tmp_path: Path):
    module = load_module()
    repo = fixture_repo(tmp_path)
    write(repo, "code/safe.py", "print('safe')\n")
    run_git(repo, "add", "code/safe.py")

    gate = module.build_gate(repo, as_of_utc=AS_OF)

    assert gate["summary"] == {
        "status": "PASS_RELEASE_SCOPE_HYGIENE",
        "release_scope_claim_allowed": True,
        "staged_path_count": 1,
        "prohibited_staged_path_count": 0,
    }
    assert gate["prohibited_category_counts"] == {}
    assert gate["blockers"] == []


def test_generated_private_and_secret_like_paths_block_without_disclosure(
    tmp_path: Path,
):
    module = load_module()
    repo = fixture_repo(tmp_path)
    sensitive_paths = {
        "tmp/render/node_modules/pkg/index.js": "sentinel_dependency_7f8a\n",
        "output/pdf/job_applications/private_resume.pdf": (
            "sentinel_application_2c41\n"
        ),
        "config/.env.production": "sentinel_credential_8b93\n",
        "code/__pycache__/module.pyc": "sentinel_cache_4d12\n",
    }
    for path, content in sensitive_paths.items():
        write(repo, path, content)
    run_git(repo, "add", "-f", ".")

    gate = module.build_gate(repo, as_of_utc=AS_OF)
    encoded = json.dumps(gate)

    assert gate["summary"]["status"] == (
        "BLOCKED_PROHIBITED_STAGED_PATH_CLASSES"
    )
    assert gate["summary"]["release_scope_claim_allowed"] is False
    assert gate["summary"]["prohibited_staged_path_count"] == 4
    assert gate["prohibited_category_counts"] == {
        "CACHE_ARTIFACT": 1,
        "PRIVATE_APPLICATION_PACKET": 1,
        "SECRET_LIKE_FILENAME": 1,
        "TEMPORARY_WORKSPACE": 1,
        "VENDORED_DEPENDENCY_TREE": 1,
    }
    for path in sensitive_paths:
        assert path not in encoded
    for content in sensitive_paths.values():
        assert content.strip() not in encoded


def test_git_boundary_is_read_only_and_local(monkeypatch, tmp_path: Path):
    module = load_module()
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        args = tuple(command[5:])
        if args == ("rev-parse", "--is-inside-work-tree"):
            return subprocess.CompletedProcess(command, 0, stdout=b"true\n")
        if args == (
            "diff",
            "--cached",
            "--name-only",
            "-z",
            "--diff-filter=ACMR",
        ):
            return subprocess.CompletedProcess(
                command, 0, stdout=b"code/safe.py\0"
            )
        return subprocess.CompletedProcess(command, 1, stdout=b"")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    gate = module.build_gate(tmp_path, as_of_utc=AS_OF)

    assert gate["summary"]["status"] == "PASS_RELEASE_SCOPE_HYGIENE"
    assert calls
    assert {command[5] for command in calls} <= module.READ_ONLY_GIT_COMMANDS
    assert all(command[:2] == ["git", "-c"] for command in calls)
    assert all(kwargs is not None for kwargs in [gate["privacy_controls"]])
    forbidden = {"add", "commit", "fetch", "merge", "push", "reset", "rm"}
    assert not ({command[5] for command in calls} & forbidden)


def test_classification_is_bounded_and_case_insensitive():
    module = load_module()

    assert module.classify_path("TMP/X/Node_Modules/pkg/a.js") == {
        "TEMPORARY_WORKSPACE",
        "VENDORED_DEPENDENCY_TREE",
    }
    assert module.classify_path("docs/public_report.md") == set()
    assert module.classify_path("config/client_credentials.json") == {
        "SECRET_LIKE_FILENAME"
    }


def test_sealed_isolated_release_stage_passes_without_path_disclosure(tmp_path: Path):
    module = load_module()
    repo = fixture_repo(tmp_path)
    manifest_path = stage_fixture(module, repo)
    status_before = run_git(repo, "status", "--short")

    gate = module.build_gate(
        repo,
        as_of_utc=AS_OF,
        stage_manifest=manifest_path,
    )

    assert gate["mode"] == module.STAGE_MODE
    assert gate["summary"] == {
        "status": "PASS_RELEASE_STAGE_HYGIENE",
        "release_scope_claim_allowed": True,
        "staged_path_count": 1,
        "prohibited_staged_path_count": 0,
        "hash_verified_path_count": 1,
    }
    assert gate["scope_binding"]["plan_sha256"] == "a" * 64
    assert gate["scope_binding"]["stage_manifest_sha256"]
    assert gate["scope_binding"]["manifest_path_recorded"] is False
    assert gate["blockers"] == []
    assert run_git(repo, "status", "--short") == status_before
    encoded = json.dumps(gate)
    assert "dashboard/public.txt" not in encoded
    assert "bounded public evidence" not in encoded


def test_prohibited_release_stage_blocks_without_path_disclosure(tmp_path: Path):
    module = load_module()
    repo = fixture_repo(tmp_path)
    relative = "tmp/release/node_modules/pkg/index.js"
    manifest_path = stage_fixture(module, repo, relative=relative)

    gate = module.build_gate(repo, as_of_utc=AS_OF, stage_manifest=manifest_path)

    assert gate["summary"]["status"] == "BLOCKED_RELEASE_STAGE_HYGIENE"
    assert gate["summary"]["release_scope_claim_allowed"] is False
    assert gate["summary"]["prohibited_staged_path_count"] == 1
    assert gate["prohibited_category_counts"] == {
        "TEMPORARY_WORKSPACE": 1,
        "VENDORED_DEPENDENCY_TREE": 1,
    }
    assert "PROHIBITED_STAGED_PATH_CLASSES" in {
        row["code"] for row in gate["blockers"]
    }
    assert relative not in json.dumps(gate)


def test_release_stage_file_drift_blocks(tmp_path: Path):
    module = load_module()
    repo = fixture_repo(tmp_path)
    manifest_path = stage_fixture(module, repo)
    staged_file = manifest_path.parent / "dashboard" / "public.txt"
    staged_file.write_text("drifted bytes\n", encoding="utf-8")

    gate = module.build_gate(repo, as_of_utc=AS_OF, stage_manifest=manifest_path)

    assert gate["summary"]["status"] == "BLOCKED_RELEASE_STAGE_HYGIENE"
    assert gate["summary"]["hash_verified_path_count"] == 0
    assert "STAGED_FILE_VERIFICATION_FAILED" in {
        row["code"] for row in gate["blockers"]
    }


def test_tampered_release_stage_manifest_blocks(tmp_path: Path):
    module = load_module()
    repo = fixture_repo(tmp_path)
    manifest_path = stage_fixture(module, repo)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["summary"]["publication_performed"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    gate = module.build_gate(repo, as_of_utc=AS_OF, stage_manifest=manifest_path)

    assert gate["summary"]["status"] == "BLOCKED_RELEASE_STAGE_HYGIENE"
    assert {row["code"] for row in gate["blockers"]} >= {
        "STAGE_MANIFEST_HASH_INVALID",
        "STAGE_CONTRACT_INVALID",
    }
