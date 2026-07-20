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
PACKAGER_PATH = ROOT / "code" / "deploy" / "package_public_site_release.py"
APPLY_SCRIPT = ROOT / "code" / "deploy" / "APPLY_PUBLIC_SITE_RELEASE_ON_VPS.sh"
VERIFY_PATH = ROOT / "code" / "ops" / "VERIFY_PUBLIC_SITE_LIVE_RELEASE.py"
PUBLIC_WORKFLOW = ROOT / ".github" / "workflows" / "deploy-public-site-release.yml"
LEGACY_WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
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
    module = load_module(PACKAGER_PATH, "package_public_site_release")
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "--quiet")
    git(repo, "config", "user.email", "public-site-tests@example.invalid")
    git(repo, "config", "user.name", "Public Site Tests")
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
    archive = tmp_path / "public-site-release.tar"
    manifest = tmp_path / "public-site-release-manifest.json"
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
        (repo / repo_path).write_bytes(b"dirty worktree bytes\r\n")

    archive = tmp_path / "release.tar"
    manifest = tmp_path / "manifest.json"
    payload = module.build_release_package(
        repo_root=repo,
        source_commit=commit,
        archive_path=archive,
        manifest_path=manifest,
    )

    expected_names = [module.archive_name(path) for path in module.RELEASE_PATHS]
    with tarfile.open(archive, mode="r:") as release:
        members = release.getmembers()
        assert [member.name for member in members] == expected_names
        assert all(member.isfile() for member in members)
        assert all(member.mode & 0o777 == 0o644 for member in members)
        archived = {
            member.name: release.extractfile(member).read() for member in members
        }

    assert archived == {
        module.archive_name(repo_path): body
        for repo_path, body in committed.items()
    }
    assert payload["source_commit"] == commit
    assert payload["target_directory"] == "/opt/lumencore/dashboard"
    assert payload["file_count"] == len(module.RELEASE_PATHS)
    assert payload == json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["archive_sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()


def test_release_allowlist_is_public_only_and_dependency_complete():
    module = load_module(PACKAGER_PATH, "package_public_site_release_allowlist")
    names = [module.archive_name(path) for path in module.RELEASE_PATHS]
    assert len(names) == len(set(names)) == 19
    assert names[:3] == [
        "operator_home.html",
        "proof_to_pilot.html",
        "review_sprint.html",
    ]
    assert "assets/luma_command_fabric.js" in names
    assert "assets/public_site.js" in names
    assert "assets/fonts/OFL-Inter.txt" in names
    assert "mission_control.html" not in names
    assert "grants.html" not in names
    assert not any(name.startswith("data/") for name in names)


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


def test_workflows_are_manual_commit_pinned_and_non_destructive():
    public = PUBLIC_WORKFLOW.read_text(encoding="utf-8")
    legacy = LEGACY_WORKFLOW.read_text(encoding="utf-8")
    apply_script = APPLY_SCRIPT.read_text(encoding="utf-8")

    public_trigger = public.split("permissions:", maxsplit=1)[0]
    assert "workflow_dispatch:" in public_trigger
    assert "push:" not in public_trigger
    assert "DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT" in public_trigger
    assert '[[ "$RELEASE_COMMIT" == "$WORKFLOW_COMMIT" ]]' in public
    assert "environment:\n      name: production" in public
    assert public.index('[[ "$APPROVAL" == "DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT" ]]') < public.index(
        "Install SSH key"
    )
    assert "--delete" not in public
    assert "rsync" not in public
    assert "VERIFY_PUBLIC_SITE_LIVE_RELEASE.py" in public

    legacy_trigger = legacy.split("permissions:", maxsplit=1)[0]
    assert "workflow_dispatch:" in legacy_trigger
    assert "push:" not in legacy_trigger
    assert "RUN_LEGACY_BOUNDED_SITE_MAINTENANCE" in legacy_trigger
    assert "--delete" not in legacy
    assert "--inplace" not in legacy
    assert "--size-only" not in legacy

    assert "cp -a --" in apply_script
    assert "pre-deploy.tsv" in apply_script
    assert "post-deploy hash mismatch" in apply_script
    assert "--delete" not in apply_script
    assert "rm -rf -- \"$target_root\"" not in apply_script


def test_live_verifier_maps_home_to_root_and_assets_to_exact_paths():
    verifier = load_module(VERIFY_PATH, "verify_public_site_live_release")
    commit = "a" * 40
    assert verifier.live_url("https://lumen-core.ai", "operator_home.html", commit) == (
        f"https://lumen-core.ai/?release={commit}"
    )
    assert verifier.live_url(
        "https://lumen-core.ai", "assets/fonts/OFL-Inter.txt", commit
    ) == f"https://lumen-core.ai/assets/fonts/OFL-Inter.txt?release={commit}"


def require_posix_apply_test() -> str:
    bash = shutil.which("bash")
    if os.name == "nt" or bash is None:
        pytest.skip("root-side Bash integration test runs on POSIX CI")
    if os.geteuid() == 0:
        pytest.skip("root-side test mode intentionally refuses root")
    return bash


def make_remote_sandbox(test_root: Path, module):
    target = test_root / "opt" / "lumencore" / "dashboard"
    (target / "assets" / "fonts").mkdir(parents=True)
    (target / "assets").chmod(0o711)
    (target / "assets" / "fonts").chmod(0o700)
    old_bodies = {}
    for repo_path in module.RELEASE_PATHS:
        name = module.archive_name(repo_path)
        body = f"old-{name}\n".encode("ascii")
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        path.chmod(0o600)
        old_bodies[name] = body
    (target / "mission_control.html").write_bytes(b"preserve operator page\n")
    (target / "data").mkdir()
    (target / "data" / "snapshot.json").write_bytes(b"{}\n")
    return target, old_bodies


def apply_command(
    bash: str,
    archive: Path,
    manifest: Path,
    commit: str,
    approval: str = "DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT",
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


def test_posix_apply_installs_allowlist_and_preserves_operator_data(tmp_path):
    bash = require_posix_apply_test()
    module, _repo, commit, committed, archive, manifest, _payload = build_package(tmp_path)
    test_root = tmp_path / "remote"
    target, old_bodies = make_remote_sandbox(test_root, module)
    env = dict(os.environ)
    env.update(
        PUBLIC_SITE_DEPLOY_TEST_MODE="1",
        PUBLIC_SITE_DEPLOY_TEST_ROOT=str(test_root),
    )
    completed = subprocess.run(
        apply_command(bash, archive, manifest, commit),
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )
    assert "PUBLIC_SITE_DEPLOYMENT_OK" in completed.stdout
    rollback_match = re.search(r"^PUBLIC_SITE_ROLLBACK_DIR=(.+)$", completed.stdout, re.M)
    assert rollback_match is not None
    rollback = Path(rollback_match.group(1))
    assert (target / "mission_control.html").read_bytes() == b"preserve operator page\n"
    assert (target / "data" / "snapshot.json").read_bytes() == b"{}\n"
    assert stat.S_IMODE((target / "assets").stat().st_mode) == 0o755
    assert stat.S_IMODE((target / "assets" / "fonts").stat().st_mode) == 0o755
    for repo_path in module.RELEASE_PATHS:
        name = module.archive_name(repo_path)
        installed = target / name
        assert installed.read_bytes() == committed[repo_path]
        assert stat.S_IMODE(installed.stat().st_mode) == 0o644
        assert (rollback / "files" / name).read_bytes() == old_bodies[name]


def test_apply_rejects_hold_before_touching_target(tmp_path):
    bash = require_posix_apply_test()
    module, _repo, commit, _committed, archive, manifest, _payload = build_package(tmp_path)
    test_root = tmp_path / "remote"
    target, old_bodies = make_remote_sandbox(test_root, module)
    env = dict(os.environ)
    env.update(
        PUBLIC_SITE_DEPLOY_TEST_MODE="1",
        PUBLIC_SITE_DEPLOY_TEST_ROOT=str(test_root),
    )
    completed = subprocess.run(
        apply_command(bash, archive, manifest, commit, approval="HOLD"),
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )
    assert completed.returncode != 0
    assert "explicit public-site deployment approval is required" in completed.stderr
    assert not (test_root / "opt" / "lumencore" / "rollbacks").exists()
    for name, body in old_bodies.items():
        assert (target / name).read_bytes() == body
