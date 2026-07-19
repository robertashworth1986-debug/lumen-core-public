from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tarfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACKAGER_PATH = ROOT / "code" / "deploy" / "package_prooflock_release.py"
APPLY_SCRIPT = ROOT / "code" / "deploy" / "APPLY_PROOFLOCK_RELEASE_ON_VPS.sh"
PROOFLOCK_WORKFLOW = ROOT / ".github" / "workflows" / "deploy-prooflock-release.yml"
DASHBOARD_WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"


def load_packager():
    spec = importlib.util.spec_from_file_location("package_prooflock_release", PACKAGER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def make_release_repo(tmp_path: Path):
    module = load_packager()
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "--quiet")
    git(repo, "config", "user.email", "prooflock-tests@example.invalid")
    git(repo, "config", "user.name", "ProofLock Tests")
    git(repo, "config", "core.autocrlf", "false")

    for index, repo_path in enumerate(module.RELEASE_PATHS, start=1):
        path = repo / repo_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"committed-{index}\n".encode("ascii"))
    git(repo, "add", "--", *module.RELEASE_PATHS)
    git(repo, "commit", "--quiet", "-m", "release fixture")
    commit = git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    committed = {
        repo_path: git(repo, "cat-file", "blob", f"{commit}:{repo_path}")
        for repo_path in module.RELEASE_PATHS
    }
    return module, repo, commit, committed


def build_package(tmp_path: Path):
    module, repo, commit, committed = make_release_repo(tmp_path)
    archive = tmp_path / "prooflock-release.tar"
    manifest = tmp_path / "prooflock-release-manifest.json"
    payload = module.build_release_package(
        repo_root=repo,
        source_commit=commit,
        archive_path=archive,
        manifest_path=manifest,
    )
    return module, repo, commit, committed, archive, manifest, payload


def test_package_uses_only_exact_pinned_git_blobs(tmp_path):
    module, repo, commit, committed = make_release_repo(tmp_path)
    for repo_path in module.RELEASE_PATHS:
        (repo / repo_path).write_bytes(b"dirty Windows worktree bytes\r\n")

    archive = tmp_path / "prooflock-release.tar"
    manifest = tmp_path / "prooflock-release-manifest.json"
    payload = module.build_release_package(
        repo_root=repo,
        source_commit=commit,
        archive_path=archive,
        manifest_path=manifest,
    )

    expected_names = [Path(path).name for path in module.RELEASE_PATHS]
    with tarfile.open(archive, mode="r:") as release:
        members = release.getmembers()
        assert [member.name for member in members] == expected_names
        assert all(member.isfile() for member in members)
        assert all(member.mode & 0o777 == 0o644 for member in members)
        archived = {
            member.name: release.extractfile(member).read() for member in members
        }

    assert archived == {
        Path(repo_path).name: body for repo_path, body in committed.items()
    }
    assert payload["source_commit"] == commit
    assert payload["file_count"] == 4
    assert [row["repo_path"] for row in payload["files"]] == list(
        module.RELEASE_PATHS
    )
    assert payload == json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["archive_sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()


def test_package_rejects_unpinned_or_executable_sources(tmp_path):
    module, repo, commit, _committed = make_release_repo(tmp_path)
    archive = tmp_path / "release.tar"
    manifest = tmp_path / "manifest.json"

    with pytest.raises(module.ReleasePackageError, match="full 40-character"):
        module.build_release_package(
            repo_root=repo,
            source_commit=commit[:12],
            archive_path=archive,
            manifest_path=manifest,
        )

    executable_path = module.RELEASE_PATHS[0]
    git(repo, "update-index", "--chmod=+x", "--", executable_path)
    git(repo, "commit", "--quiet", "-m", "unsafe executable mode")
    executable_commit = git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    with pytest.raises(module.ReleasePackageError, match="non-executable regular Git blob"):
        module.build_release_package(
            repo_root=repo,
            source_commit=executable_commit,
            archive_path=archive,
            manifest_path=manifest,
        )


def test_workflows_encode_the_bounded_fail_closed_contract():
    module = load_packager()
    dashboard = DASHBOARD_WORKFLOW.read_text(encoding="utf-8")
    prooflock = PROOFLOCK_WORKFLOW.read_text(encoding="utf-8")
    apply_script = APPLY_SCRIPT.read_text(encoding="utf-8")

    dashboard_sync = dashboard.split("- name: Sync dashboard assets", maxsplit=1)[1].split(
        "- name: Sync data snapshots", maxsplit=1
    )[0]
    assert "--delete" in dashboard_sync
    assert "--filter='protect /build_week/***'" in dashboard_sync
    assert "--exclude='/build_week/'" in dashboard_sync
    assert "https://lumen-core.ai/build_week/prooflock_console/" in dashboard
    assert "<title>ProofLock Console</title>" in dashboard

    trigger = prooflock.split("permissions:", maxsplit=1)[0]
    assert "workflow_dispatch:" in trigger
    assert "push:" not in trigger
    assert "DEPLOY_PROOFLOCK_EXACT_FOUR" in trigger
    assert '[[ "$RELEASE_COMMIT" == "$WORKFLOW_COMMIT" ]]' in prooflock
    assert "environment:\n      name: production" in prooflock
    assert prooflock.index('[[ "$APPROVAL" == "DEPLOY_PROOFLOCK_EXACT_FOUR" ]]') < prooflock.index(
        "Install SSH key"
    )
    assert "--delete" not in prooflock
    assert "rsync" not in prooflock

    assert "/opt/lumencore/dashboard/build_week/prooflock_console" in apply_script
    assert "cp -a --" in apply_script
    assert "pre-deploy.tsv" in apply_script
    assert "post-deploy hash mismatch" in apply_script
    assert "install -o root -g root -m 0644" in apply_script
    assert "chmod 0644" in apply_script
    assert "--delete" not in apply_script
    for repo_path in module.RELEASE_PATHS:
        assert f'"{Path(repo_path).name}"' in apply_script


def require_posix_apply_test() -> str:
    bash = shutil.which("bash")
    if os.name == "nt" or bash is None:
        pytest.skip("root-side Bash integration test runs on POSIX CI")
    if os.geteuid() == 0:
        pytest.skip("root-side test mode intentionally refuses root")
    return bash


def make_remote_sandbox(test_root: Path, module, old_mode: int = 0o600):
    build_week = test_root / "opt" / "lumencore" / "dashboard" / "build_week"
    target = build_week / "prooflock_console"
    target.mkdir(parents=True)
    build_week.chmod(0o711)
    target.chmod(0o700)
    old_bodies = {}
    for repo_path in module.RELEASE_PATHS:
        name = Path(repo_path).name
        body = f"old-{name}\n".encode("ascii")
        path = target / name
        path.write_bytes(body)
        path.chmod(old_mode)
        old_bodies[name] = body
    (target / "untouched.txt").write_bytes(b"preserve me\n")
    return build_week, target, old_bodies


def apply_command(
    bash: str,
    archive: Path,
    manifest: Path,
    commit: str,
    approval: str = "DEPLOY_PROOFLOCK_EXACT_FOUR",
):
    return [
        bash,
        str(APPLY_SCRIPT),
        "--archive",
        str(archive),
        "--manifest",
        str(manifest),
        "--source-commit",
        commit,
        "--approval",
        approval,
    ]


def test_posix_apply_captures_identity_and_installs_non_executable_files(tmp_path):
    bash = require_posix_apply_test()
    module, _repo, commit, committed, archive, manifest, _payload = build_package(
        tmp_path
    )
    test_root = tmp_path / "remote"
    build_week, target, old_bodies = make_remote_sandbox(test_root, module)
    env = dict(os.environ)
    env.update(
        PROOFLOCK_DEPLOY_TEST_MODE="1",
        PROOFLOCK_DEPLOY_TEST_ROOT=str(test_root),
    )

    completed = subprocess.run(
        apply_command(bash, archive, manifest, commit),
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )

    assert "PROOFLOCK_DEPLOYMENT_OK" in completed.stdout
    rollback_match = re.search(r"^PROOFLOCK_ROLLBACK_DIR=(.+)$", completed.stdout, re.M)
    assert rollback_match is not None
    rollback = Path(rollback_match.group(1))
    assert rollback.parent == test_root / "opt" / "lumencore" / "rollbacks" / "prooflock"
    assert (target / "untouched.txt").read_bytes() == b"preserve me\n"
    assert stat.S_IMODE(build_week.stat().st_mode) == 0o755
    assert stat.S_IMODE(target.stat().st_mode) == 0o755

    for repo_path in module.RELEASE_PATHS:
        name = Path(repo_path).name
        installed = target / name
        assert installed.read_bytes() == committed[repo_path]
        assert stat.S_IMODE(installed.stat().st_mode) == 0o644
        backup = rollback / "files" / name
        assert backup.read_bytes() == old_bodies[name]
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600

    pre_receipt = (rollback / "pre-deploy.tsv").read_text(encoding="utf-8")
    post_receipt = (rollback / "post-deploy.tsv").read_text(encoding="utf-8")
    assert pre_receipt.count("\tPRESENT\t") == 4
    assert post_receipt.count("\t644\n") == 4


def test_posix_apply_rolls_back_a_partial_install(tmp_path):
    bash = require_posix_apply_test()
    module, _repo, commit, _committed, archive, manifest, _payload = build_package(
        tmp_path
    )
    test_root = tmp_path / "remote"
    build_week, target, old_bodies = make_remote_sandbox(test_root, module)

    real_mv = shutil.which("mv")
    assert real_mv is not None
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    counter = tmp_path / "mv-counter"
    fake_mv = fake_bin / "mv"
    fake_mv.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'count="$(cat "$PROOFLOCK_MV_COUNTER" 2>/dev/null || printf 0)"\n'
        'count=$((count + 1))\n'
        'printf "%s\\n" "$count" > "$PROOFLOCK_MV_COUNTER"\n'
        'if [[ "$count" -eq 2 ]]; then exit 71; fi\n'
        f'exec "{real_mv}" "$@"\n',
        encoding="utf-8",
        newline="\n",
    )
    fake_mv.chmod(0o755)

    env = dict(os.environ)
    env.update(
        PATH=f"{fake_bin}{os.pathsep}{env['PATH']}",
        PROOFLOCK_DEPLOY_TEST_MODE="1",
        PROOFLOCK_DEPLOY_TEST_ROOT=str(test_root),
        PROOFLOCK_MV_COUNTER=str(counter),
    )
    completed = subprocess.run(
        apply_command(bash, archive, manifest, commit),
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )

    assert completed.returncode != 0
    assert "ROLLBACK_APPLIED=" in completed.stderr
    assert stat.S_IMODE(build_week.stat().st_mode) == 0o711
    assert stat.S_IMODE(target.stat().st_mode) == 0o700
    assert not list(target.glob(".*.prooflock-*"))
    for name, body in old_bodies.items():
        restored = target / name
        assert restored.read_bytes() == body
        assert stat.S_IMODE(restored.stat().st_mode) == 0o600


def test_apply_rejects_missing_approval_before_touching_target(tmp_path):
    bash = require_posix_apply_test()
    module, _repo, commit, _committed, archive, manifest, _payload = build_package(
        tmp_path
    )
    test_root = tmp_path / "remote"
    _build_week, target, old_bodies = make_remote_sandbox(test_root, module)
    env = dict(os.environ)
    env.update(
        PROOFLOCK_DEPLOY_TEST_MODE="1",
        PROOFLOCK_DEPLOY_TEST_ROOT=str(test_root),
    )

    completed = subprocess.run(
        apply_command(bash, archive, manifest, commit, approval="HOLD"),
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )

    assert completed.returncode != 0
    assert "explicit ProofLock deployment approval is required" in completed.stderr
    assert not (test_root / "opt" / "lumencore" / "rollbacks").exists()
    for name, body in old_bodies.items():
        assert (target / name).read_bytes() == body
