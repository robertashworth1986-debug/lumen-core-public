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
import sys
import tarfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACKAGER_PATH = ROOT / "code" / "deploy" / "package_public_site_release.py"
APPLY_SCRIPT = ROOT / "code" / "deploy" / "APPLY_PUBLIC_SITE_RELEASE_ON_VPS.sh"
DISCOVERY_SCRIPT = ROOT / "code" / "deploy" / "DISCOVER_PUBLIC_SITE_ROLLBACK_AUTHORITY_ON_VPS.py"
RESTORE_SCRIPT = ROOT / "code" / "deploy" / "RESTORE_PUBLIC_SITE_RELEASE_ON_VPS.sh"
VERIFY_PATH = ROOT / "code" / "ops" / "VERIFY_PUBLIC_SITE_LIVE_RELEASE.py"
PUBLIC_WORKFLOW = ROOT / ".github" / "workflows" / "deploy-public-site-release.yml"
LIVE_AUDIT_WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"
ROLLBACK_CAPABILITY = "ab" * 32


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
    assert module.validate_release_manifest(payload, source_commit=commit) == payload
    assert payload == json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["archive_sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()


def test_release_allowlist_is_public_only_and_dependency_complete():
    module = load_module(PACKAGER_PATH, "package_public_site_release_allowlist")
    names = [module.archive_name(path) for path in module.RELEASE_PATHS]
    assert len(names) == len(set(names)) == 43
    assert names[:5] == [
        "operator_home.html",
        "opportunity_sprint.html",
        "proof_to_pilot.html",
        "external_review.html",
        "reviewer_docket.json",
    ]
    assert "evidence/index_bounded.html" in names
    assert "mission_control.html" in names
    assert "quant_lab.html" in names
    assert "grants.html" in names
    assert "kraken_execution_dashboard.html" in names
    assert "forecast.html" in names
    assert "anomalies.html" in names
    assert "explain.html" in names
    assert "lab.html" in names
    assert "assets/lumencore.js" in names
    assert "assets/vendor/three.min.js" in names
    assert "js/alpha_globe_3d.js" in names
    assert "js/cinematic_telemetry_layer.js" in names
    assert "js/luma_design_system.js" in names
    assert "js/luma_path_resolver.js" in names
    assert "robots.txt" in names
    assert "sitemap.xml" in names
    assert "site.webmanifest" in names
    assert "manifest.json" in names
    assert "assets/lumaarc_arc_seal_v1.png" in names
    assert "assets/lumencore.css" in names
    assert "assets/luma_command_fabric.js" in names
    assert "assets/luma_institutional_surface.css" in names
    assert "assets/luma_institutional_surface.js" in names
    assert "assets/prooflock/bounded_validation_protocol_v2.json" in names
    assert "build_week/prooflock_console/index.html" in names
    assert "build_week/prooflock_console/three.module.min.js" in names
    assert not any(name.startswith("data/") for name in names)

    apply_script = APPLY_SCRIPT.read_text(encoding="utf-8")
    restore_script = RESTORE_SCRIPT.read_text(encoding="utf-8")
    for script in (apply_script, restore_script):
        match = re.search(
            r"readonly -a RELEASE_FILES=\(\n(?P<body>.*?)\n\)",
            script,
            flags=re.DOTALL,
        )
        assert match is not None
        root_allowlist = re.findall(r'^\s+"([^"]+)"$', match.group("body"), re.MULTILINE)
        assert root_allowlist == names


def test_release_count_is_bound_to_current_control_records():
    module = load_module(PACKAGER_PATH, "package_public_site_release_control_count")
    release_count = len(module.RELEASE_PATHS)
    assert release_count == 43

    protocol = (ROOT / "docs" / "PUBLIC_SITE_EXACT_SNAPSHOT_PROTOCOL.md").read_text(
        encoding="utf-8"
    )
    incident_plan = (
        ROOT / "docs" / "INCIDENT_RESPONSE_AND_CONTINUITY_PLAN.md"
    ).read_text(encoding="utf-8")
    incident_policy = json.loads(
        (ROOT / "config" / "incident_response_and_continuity_v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert f"({release_count} for" in protocol
    assert "full allowlisted manifest" in incident_plan
    assert "every live byte and MIME check declared by the release manifest" in incident_plan
    assert (
        "rerun the full-manifest exact-byte and MIME audit against the deployed commit"
        in incident_policy["recovery_sequence"]
    )


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


def test_exact_snapshot_workflow_is_manual_commit_pinned_and_non_destructive():
    public = PUBLIC_WORKFLOW.read_text(encoding="utf-8")
    apply_script = APPLY_SCRIPT.read_text(encoding="utf-8")
    restore_script = RESTORE_SCRIPT.read_text(encoding="utf-8")

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
    assert "BUILD_PUBLIC_SITE_DEPLOYMENT_TRANSACTION_RECEIPT.py" in public
    assert "RESTORE_PUBLIC_SITE_RELEASE_ON_VPS.sh" in public
    assert "steps.live_gate.outcome == 'failure'" in public
    assert "steps.live_gate.outcome == 'success'" not in public.split(
        "Compensate a rejected candidate", maxsplit=1
    )[1].split("Build status-only", maxsplit=1)[0]
    assert "python - /tmp/public-site-deployment-transaction.json" not in public
    assert "python-version: '3.11.9'" in public
    assert "sys.version_info >= (3, 9)" in public
    assert "validate-rejected-live" in public
    assert "public-site-live-gate.untrusted.json" in public
    assert "--authority-receipt /tmp/public-site-rollback-authority.json" in public
    assert "BUILD_PUBLIC_SITE_DEPLOYMENT_TRANSACTION_RECEIPT.py" in public
    assert "\n            verify \\" in public

    assert "cp -a --" in apply_script
    assert "pre-deploy.tsv" in apply_script
    assert "post-deploy hash mismatch" in apply_script
    assert "--delete" not in apply_script
    assert "rm -rf -- \"$target_root\"" not in apply_script
    assert "rm -rf -- \"$target_root\"" not in restore_script
    assert "rollback-capability-stdin" in apply_script
    assert "rollback-capability-stdin" in restore_script
    assert "rollback_capability_sha256" in apply_script
    assert "rollback_capability_sha256" in restore_script
    assert '.deployment.lock' in apply_script
    assert '.deployment.lock' in restore_script
    assert 'flock -n 9' in apply_script
    assert 'flock -n 9' in restore_script
    assert "revalidate_file_target" in restore_script
    assert "revalidate_directory_target" in restore_script
    assert "PUBLIC_SITE_DEPLOY_TEST_BEFORE_TARGET_HOOK" in restore_script


def test_legacy_auto_deploy_is_replaced_by_read_only_exact_live_audit():
    module = load_module(PACKAGER_PATH, "package_public_site_release_audit_trigger")
    audit = LIVE_AUDIT_WORKFLOW.read_text(encoding="utf-8")
    trigger = audit.split("permissions:", maxsplit=1)[0]
    assert "push:" in trigger
    assert "schedule:" in trigger
    assert "permissions:\n  contents: read" in audit
    assert "package_public_site_release.py" in audit
    assert "VERIFY_PUBLIC_SITE_LIVE_RELEASE.py" in audit
    assert "reviewer_docket.json" in audit
    for forbidden in (
        "VPS_SSH_PRIVATE_KEY",
        "VPS_HOST",
        "ssh ",
        "scp ",
        "rsync",
        "--delete",
        "sudo ",
    ):
        assert forbidden not in audit
    assert "deploy-public-site-release.yml" in audit
    trigger_paths = re.findall(r'^\s+- ["\']([^"\']+)["\']$', trigger, re.MULTILINE)
    uncovered = []
    for path in module.RELEASE_PATHS:
        covered = any(
            path.startswith(pattern[:-2]) if pattern.endswith("/**") else path == pattern
            for pattern in trigger_paths
        )
        if not covered:
            uncovered.append(path)
    assert uncovered == []


def test_ambiguous_local_apply_evidence_still_routes_through_remote_discovery():
    workflow = PUBLIC_WORKFLOW.read_text(encoding="utf-8")
    apply_block = workflow.split("- name: Apply exact files", maxsplit=1)[1].split(
        "- name: Discover exact remote authority", maxsplit=1
    )[0]
    live_block = workflow.split(
        "- name: Discover exact remote authority", maxsplit=1
    )[1].split("- name: Compensate a rejected candidate", maxsplit=1)[0]
    compensation_block = workflow.split(
        "- name: Compensate a rejected candidate", maxsplit=1
    )[1].split("- name: Build status-only", maxsplit=1)[0]
    assert "/tmp/public-site-apply-command.txt" in apply_block
    assert "$GITHUB_OUTPUT" not in apply_block
    assert "if: always()" in live_block
    assert "DISCOVER_PUBLIC_SITE_ROLLBACK_AUTHORITY_ON_VPS.py" in live_block
    assert "steps.apply.outcome" not in live_block
    assert "steps.live_gate.outcome == 'failure'" in compensation_block
    assert "DISCOVER_PUBLIC_SITE_ROLLBACK_AUTHORITY_ON_VPS.py" in compensation_block
    assert "steps.apply.outcome" not in compensation_block
    assert workflow.count("DISCOVER_PUBLIC_SITE_ROLLBACK_AUTHORITY_ON_VPS.py") >= 3


def test_live_verifier_maps_canonical_routes_and_assets_to_exact_paths():
    verifier = load_module(VERIFY_PATH, "verify_public_site_live_release")
    commit = "a" * 40
    assert verifier.live_url("https://lumen-core.ai", "operator_home.html", commit) == (
        f"https://lumen-core.ai/?release={commit}"
    )
    assert verifier.live_url(
        "https://lumen-core.ai", "evidence/index_bounded.html", commit
    ) == f"https://lumen-core.ai/evidence/?release={commit}"
    assert verifier.live_url(
        "https://lumen-core.ai", "build_week/prooflock_console/index.html", commit
    ) == f"https://lumen-core.ai/build_week/prooflock_console/?release={commit}"
    assert verifier.live_url(
        "https://lumen-core.ai", "assets/lumencore.css", commit
    ) == f"https://lumen-core.ai/assets/lumencore.css?release={commit}"
    assert verifier.content_type_allowed("manifest.json", "application/json")
    assert verifier.content_type_allowed(
        "manifest.json", "application/manifest+json"
    )
    assert not verifier.content_type_allowed(
        "manifest.json", "application/octet-stream"
    )
    assert verifier.content_type_allowed("reviewer_docket.json", "application/json")
    assert not verifier.content_type_allowed(
        "reviewer_docket.json", "application/octet-stream"
    )
    assert verifier.content_type_allowed(
        "site.webmanifest", "application/octet-stream"
    )


def test_live_verifier_rejects_duplicate_json_keys(tmp_path):
    verifier = load_module(VERIFY_PATH, "verify_public_site_duplicate_keys")
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema":"first","schema":"second"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        verifier.load_manifest(manifest)


def test_live_verifier_rejects_unknown_manifest_row_fields(tmp_path):
    verifier = load_module(VERIFY_PATH, "verify_public_site_unknown_row")
    commit = "a" * 40
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "archive_sha256": "b" * 64,
                "file_count": 1,
                "files": [
                    {
                        "archive_name": "operator_home.html",
                        "bytes": 1,
                        "git_blob_oid": "c" * 40,
                        "install_mode": "0644",
                        "repo_path": "dashboard/operator_home.html",
                        "sha256": "d" * 64,
                        "unexpected": True,
                    }
                ],
                "schema": "lumencore.public_site_release_manifest.v1",
                "source_commit": commit,
                "target_directory": "/opt/lumencore/dashboard",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="manifest file row"):
        verifier.verify(
            manifest_path=manifest,
            source_commit=commit,
            base_url="https://example.invalid",
            timeout=0.1,
        )


def require_posix_apply_test() -> str:
    bash = shutil.which("bash")
    if os.name == "nt" or bash is None:
        pytest.skip("root-side Bash integration test runs on POSIX CI")
    if os.geteuid() == 0:
        pytest.skip("root-side test mode intentionally refuses root")
    return bash


def make_remote_sandbox(test_root: Path, module):
    target = test_root / "opt" / "lumencore" / "dashboard"
    target.mkdir(parents=True)
    old_bodies = {}
    for repo_path in module.RELEASE_PATHS:
        name = module.archive_name(repo_path)
        body = f"old-{name}\n".encode("ascii")
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        path.chmod(0o600)
        old_bodies[name] = body
    (target / "local_operator_notes.html").write_bytes(b"preserve non-release page\n")
    (target / "data").mkdir()
    (target / "data" / "snapshot.json").write_bytes(b"{}\n")
    return target, old_bodies


def test_posix_authority_discovery_recovers_completed_apply_without_stdout(tmp_path):
    require_posix_apply_test()
    commit = "a" * 40
    capability_sha = hashlib.sha256(ROLLBACK_CAPABILITY.encode("ascii")).hexdigest()
    rollback_base = tmp_path / "rollbacks" / "public-site"
    rollback_base.mkdir(parents=True)
    rollback_base.chmod(0o750)
    capture = rollback_base / f"20260831T120000Z-{commit[:12]}"
    capture.mkdir()
    capture.chmod(0o700)
    state_bodies = {
        "release-manifest.json": b"manifest\n",
        "pre-deploy.tsv": b"pre\n",
        "directory-state.tsv": b"directories\n",
        "post-deploy.tsv": b"post\n",
    }
    for name, body in state_bodies.items():
        path = capture / name
        path.write_bytes(body)
        path.chmod(0o600)
    authority = {
        "authority_scope": "FAILED_EXTERNAL_LIVE_GATE_COMPENSATION_IN_SAME_WORKFLOW_RUN_ONLY",
        "created_at_utc": "2026-08-31T12:00:00Z",
        "deployment_approval": "DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT",
        "directory_state_sha256": hashlib.sha256(state_bodies["directory-state.tsv"]).hexdigest(),
        "post_deploy_sha256": hashlib.sha256(state_bodies["post-deploy.tsv"]).hexdigest(),
        "pre_deploy_sha256": hashlib.sha256(state_bodies["pre-deploy.tsv"]).hexdigest(),
        "python_version": "3.11.9",
        "release_manifest_sha256": hashlib.sha256(state_bodies["release-manifest.json"]).hexdigest(),
        "repository": "robertashworth1986-debug/lumen-core-public",
        "rollback_capability_sha256": capability_sha,
        "rollback_capture_id": capture.name,
        "run_attempt": 1,
        "run_id": 123456789,
        "schema": "lumencore.public_site_same_run_rollback_authority.v1",
        "source_commit": commit,
        "target_directory": "/opt/lumencore/dashboard",
        "workflow": ".github/workflows/deploy-public-site-release.yml",
    }
    canonical = json.dumps(
        authority, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    authority["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    authority_path = capture / "rollback-authority.json"
    authority_path.write_text(
        json.dumps(authority, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
        newline="\n",
    )
    authority_path.chmod(0o600)
    command = [
        sys.executable,
        str(DISCOVERY_SCRIPT),
        "--rollback-base",
        str(rollback_base),
        "--source-commit",
        commit,
        "--run-id",
        "123456789",
        "--run-attempt",
        "1",
        "--capability-sha256",
        capability_sha,
    ]
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    assert f"PUBLIC_SITE_ROLLBACK_DIR={capture}" in completed.stdout
    assert "PUBLIC_SITE_DEPLOYMENT_OK" in completed.stdout

    (capture / "post-deploy.tsv").write_bytes(b"tampered\n")
    rejected = subprocess.run(command, check=False, text=True, capture_output=True)
    assert rejected.returncode != 0
    assert "found 0" in rejected.stderr


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
        "--run-id",
        "123456789",
        "--run-attempt",
        "1",
        "--rollback-capability-stdin",
        "--approval",
        approval,
    ]


def restore_command(
    bash: str,
    rollback: Path,
    commit: str,
    *,
    run_id: str = "123456789",
    run_attempt: str = "1",
    live_gate_receipt: Path | None = None,
):
    command = [
        bash,
        str(RESTORE_SCRIPT),
        "--rollback-dir",
        str(rollback),
        "--source-commit",
        commit,
        "--run-id",
        run_id,
        "--run-attempt",
        run_attempt,
        "--rollback-capability-stdin",
        "--trigger",
        "LIVE_GATE_REJECTED" if live_gate_receipt else "LIVE_GATE_ERROR_OR_MISSING",
    ]
    if live_gate_receipt:
        command.extend(["--live-gate-receipt", str(live_gate_receipt)])
    command.extend(
        [
        "--approval",
        "DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT",
        ]
    )
    return command


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
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    assert "PUBLIC_SITE_DEPLOYMENT_OK" in completed.stdout
    rollback_match = re.search(r"^PUBLIC_SITE_ROLLBACK_DIR=(.+)$", completed.stdout, re.M)
    assert rollback_match is not None
    rollback = Path(rollback_match.group(1))
    authority = json.loads((rollback / "rollback-authority.json").read_text(encoding="ascii"))
    assert authority["run_id"] == 123456789
    assert authority["run_attempt"] == 1
    assert tuple(int(part) for part in authority["python_version"].split(".")) >= (3, 9, 0)
    assert authority["rollback_capability_sha256"] == hashlib.sha256(
        ROLLBACK_CAPABILITY.encode("ascii")
    ).hexdigest()
    assert (target / "local_operator_notes.html").read_bytes() == b"preserve non-release page\n"
    assert (target / "data" / "snapshot.json").read_bytes() == b"{}\n"
    assert stat.S_IMODE((target / "assets").stat().st_mode) == 0o755
    assert stat.S_IMODE((target / "assets" / "prooflock").stat().st_mode) == 0o755
    assert stat.S_IMODE((target / "evidence").stat().st_mode) == 0o755
    assert stat.S_IMODE((target / "build_week" / "prooflock_console").stat().st_mode) == 0o755
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
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    assert completed.returncode != 0
    assert "explicit public-site deployment approval is required" in completed.stderr
    assert not (test_root / "opt" / "lumencore" / "rollbacks").exists()
    for name, body in old_bodies.items():
        assert (target / name).read_bytes() == body


def test_apply_rejects_duplicate_manifest_key_before_touching_target(tmp_path):
    bash = require_posix_apply_test()
    module, _repo, commit, _committed, archive, manifest, _payload = build_package(tmp_path)
    original = manifest.read_text(encoding="utf-8")
    manifest.write_text(
        original.replace("{\n", '{\n  "schema": "duplicate",\n', 1),
        encoding="utf-8",
    )
    test_root = tmp_path / "remote"
    target, old_bodies = make_remote_sandbox(test_root, module)
    env = dict(os.environ)
    env.update(
        PUBLIC_SITE_DEPLOY_TEST_MODE="1",
        PUBLIC_SITE_DEPLOY_TEST_ROOT=str(test_root),
    )
    completed = subprocess.run(
        apply_command(bash, archive, manifest, commit),
        check=False,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    assert completed.returncode != 0
    assert "duplicate JSON key: schema" in completed.stderr
    assert not (test_root / "opt" / "lumencore" / "rollbacks").exists()
    for name, body in old_bodies.items():
        assert (target / name).read_bytes() == body


def test_posix_remote_python_floor_fails_before_lock_or_target_touch(tmp_path):
    bash = require_posix_apply_test()
    module, _repo, commit, _committed, archive, manifest, _payload = build_package(tmp_path)
    test_root = tmp_path / "remote"
    target, old_bodies = make_remote_sandbox(test_root, module)
    shim_root = tmp_path / "shim"
    shim_root.mkdir()
    shim = shim_root / "python3"
    shim.write_text("#!/usr/bin/env sh\nexit 1\n", encoding="ascii", newline="\n")
    shim.chmod(0o700)
    env = dict(os.environ)
    env.update(
        PATH=str(shim_root) + os.pathsep + env["PATH"],
        PUBLIC_SITE_DEPLOY_TEST_MODE="1",
        PUBLIC_SITE_DEPLOY_TEST_ROOT=str(test_root),
    )
    completed = subprocess.run(
        apply_command(bash, archive, manifest, commit),
        check=False,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    assert completed.returncode != 0
    assert "python3 3.9 or newer is required" in completed.stderr
    assert not (test_root / "opt" / "lumencore" / "rollbacks").exists()
    for name, body in old_bodies.items():
        assert (target / name).read_bytes() == body


def test_posix_same_attempt_compensation_restores_exact_prior_state(tmp_path):
    bash = require_posix_apply_test()
    module, _repo, commit, committed, archive, manifest, _payload = build_package(tmp_path)
    test_root = tmp_path / "remote"
    target, old_bodies = make_remote_sandbox(test_root, module)
    missing_name = module.archive_name(module.RELEASE_PATHS[-1])
    (target / missing_name).unlink()
    old_bodies.pop(missing_name)
    env = dict(os.environ)
    env.update(
        PUBLIC_SITE_DEPLOY_TEST_MODE="1",
        PUBLIC_SITE_DEPLOY_TEST_ROOT=str(test_root),
    )
    applied = subprocess.run(
        apply_command(bash, archive, manifest, commit),
        check=True,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    rollback = Path(
        re.search(r"^PUBLIC_SITE_ROLLBACK_DIR=(.+)$", applied.stdout, re.M).group(1)
    )
    restored = subprocess.run(
        restore_command(bash, rollback, commit),
        check=True,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    assert "PUBLIC_SITE_ROLLBACK_OK" in restored.stdout
    for name, body in old_bodies.items():
        assert (target / name).read_bytes() == body
        assert stat.S_IMODE((target / name).stat().st_mode) == 0o600
    assert not (target / missing_name).exists()
    assert (target / "local_operator_notes.html").read_bytes() == b"preserve non-release page\n"
    assert (target / "data" / "snapshot.json").read_bytes() == b"{}\n"
    receipt = json.loads((rollback / "rollback-receipt.json").read_text(encoding="ascii"))
    assert receipt["schema"] == "lumencore.public_site_same_run_compensation.v1"
    assert receipt["rollback_verified"] is True
    assert receipt["restored_file_count"] == len(module.RELEASE_PATHS)
    assert receipt["live_gate_receipt_sha256"] is None
    assert receipt["trigger"] == "LIVE_GATE_ERROR_OR_MISSING"
    assert all(
        (target / module.archive_name(path)).read_bytes() != committed[path]
        for path in module.RELEASE_PATHS[:-1]
    )
    replay = subprocess.run(
        restore_command(bash, rollback, commit),
        check=False,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    assert replay.returncode != 0
    assert "rollback receipt already exists; replay is forbidden" in replay.stderr


def test_posix_rejected_live_receipt_is_bound_to_compensation(tmp_path):
    bash = require_posix_apply_test()
    verifier = load_module(VERIFY_PATH, "verify_public_site_compensation_fixture")
    module, _repo, commit, _committed, archive, manifest, payload = build_package(tmp_path)
    test_root = tmp_path / "remote"
    target, old_bodies = make_remote_sandbox(test_root, module)
    env = dict(os.environ)
    env.update(
        PUBLIC_SITE_DEPLOY_TEST_MODE="1",
        PUBLIC_SITE_DEPLOY_TEST_ROOT=str(test_root),
    )
    applied = subprocess.run(
        apply_command(bash, archive, manifest, commit),
        check=True,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    rollback = Path(
        re.search(r"^PUBLIC_SITE_ROLLBACK_DIR=(.+)$", applied.stdout, re.M).group(1)
    )
    results = []
    for index, row in enumerate(payload["files"]):
        match = index > 0
        actual = row["sha256"] if match else "f" * 64
        results.append(
            {
                "actual_sha256": actual,
                "archive_name": row["archive_name"],
                "bytes": row["bytes"],
                "content_type": "text/html" if index == 0 else "text/plain",
                "content_type_allowed": True,
                "expected_sha256": row["sha256"],
                "http_status": 200,
                "status": "MATCH" if match else "MISMATCH",
                "url": verifier.live_url(
                    "https://lumen-core.ai", row["archive_name"], commit
                ),
            }
        )
    live = {
        "base_url": "https://lumen-core.ai",
        "checked_at_utc": "2026-08-31T12:01:00Z",
        "expected_file_count": len(results),
        "matched_file_count": len(results) - 1,
        "release_verified": False,
        "results": results,
        "schema": "lumencore.public_site_live_verification.v1",
        "source_commit": commit,
    }
    live_path = tmp_path / "live-gate.json"
    live_path.write_text(json.dumps(live, indent=2) + "\n", encoding="utf-8")
    restored = subprocess.run(
        restore_command(bash, rollback, commit, live_gate_receipt=live_path),
        check=True,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    assert "PUBLIC_SITE_ROLLBACK_OK" in restored.stdout
    receipt = json.loads((rollback / "rollback-receipt.json").read_text(encoding="ascii"))
    assert receipt["trigger"] == "LIVE_GATE_REJECTED"
    assert receipt["live_gate_receipt_sha256"] == hashlib.sha256(
        live_path.read_bytes()
    ).hexdigest()
    for name, body in old_bodies.items():
        assert (target / name).read_bytes() == body


@pytest.mark.parametrize(
    "tamper",
    [
        "capability",
        "run_attempt",
        "backup",
        "backup_symlink",
        "backup_hardlink",
        "backup_extra",
        "backup_missing",
        "concurrent_target",
        "target_symlink",
    ],
)
def test_posix_compensation_rejects_replay_tamper_or_concurrent_drift_before_touch(
    tmp_path, tamper
):
    bash = require_posix_apply_test()
    module, _repo, commit, committed, archive, manifest, _payload = build_package(tmp_path)
    test_root = tmp_path / "remote"
    target, _old_bodies = make_remote_sandbox(test_root, module)
    env = dict(os.environ)
    env.update(
        PUBLIC_SITE_DEPLOY_TEST_MODE="1",
        PUBLIC_SITE_DEPLOY_TEST_ROOT=str(test_root),
    )
    applied = subprocess.run(
        apply_command(bash, archive, manifest, commit),
        check=True,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    rollback = Path(
        re.search(r"^PUBLIC_SITE_ROLLBACK_DIR=(.+)$", applied.stdout, re.M).group(1)
    )
    first_name = module.archive_name(module.RELEASE_PATHS[0])
    last_name = module.archive_name(module.RELEASE_PATHS[-1])
    capability = ROLLBACK_CAPABILITY
    if tamper == "capability":
        capability = "cd" * 32
    elif tamper == "backup":
        (rollback / "files" / first_name).write_bytes(b"tampered backup\n")
    elif tamper == "backup_symlink":
        backup = rollback / "files" / first_name
        backup.unlink()
        backup.symlink_to(target / first_name)
    elif tamper == "backup_hardlink":
        backup = rollback / "files" / first_name
        linked = tmp_path / "linked-backup"
        os.link(backup, linked)
    elif tamper == "backup_extra":
        (rollback / "files" / "unexpected.txt").write_bytes(b"unexpected\n")
    elif tamper == "backup_missing":
        (rollback / "files" / first_name).unlink()
    elif tamper == "target_symlink":
        (target / first_name).unlink()
        (target / first_name).symlink_to(target / "local_operator_notes.html")
    elif tamper == "concurrent_target":
        (target / first_name).write_bytes(b"concurrent third-party bytes\n")
    untouched_candidate = (target / last_name).read_bytes()
    failed = subprocess.run(
        restore_command(
            bash,
            rollback,
            commit,
            run_attempt="2" if tamper == "run_attempt" else "1",
        ),
        check=False,
        text=True,
        input=capability + "\n",
        capture_output=True,
        env=env,
    )
    assert failed.returncode != 0
    assert not (rollback / "rollback-receipt.json").exists()
    assert (target / last_name).read_bytes() == untouched_candidate == committed[module.RELEASE_PATHS[-1]]
    if tamper not in {"concurrent_target", "target_symlink"}:
        assert (target / first_name).read_bytes() == committed[module.RELEASE_PATHS[0]]


def test_posix_late_drift_hook_preserves_third_state_and_retry_is_idempotent(tmp_path):
    bash = require_posix_apply_test()
    module, _repo, commit, committed, archive, manifest, _payload = build_package(tmp_path)
    test_root = tmp_path / "remote"
    target, old_bodies = make_remote_sandbox(test_root, module)
    env = dict(os.environ)
    env.update(
        PUBLIC_SITE_DEPLOY_TEST_MODE="1",
        PUBLIC_SITE_DEPLOY_TEST_ROOT=str(test_root),
    )
    applied = subprocess.run(
        apply_command(bash, archive, manifest, commit),
        check=True,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    rollback = Path(
        re.search(r"^PUBLIC_SITE_ROLLBACK_DIR=(.+)$", applied.stdout, re.M).group(1)
    )
    last_name = module.archive_name(module.RELEASE_PATHS[-1])
    hook = tmp_path / "inject-late-drift.sh"
    marker = tmp_path / "hook-fired"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        f"if [[ \"$1\" == {json.dumps(last_name)} && ! -e {json.dumps(str(marker))} ]]; then\n"
        f"  printf '%s\\n' 'late third-party state' > {json.dumps(str(target / last_name))}\n"
        f"  : > {json.dumps(str(marker))}\n"
        "fi\n",
        encoding="utf-8",
        newline="\n",
    )
    hook.chmod(0o700)
    env_with_hook = dict(env)
    env_with_hook["PUBLIC_SITE_DEPLOY_TEST_BEFORE_TARGET_HOOK"] = str(hook)
    failed = subprocess.run(
        restore_command(bash, rollback, commit),
        check=False,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env_with_hook,
    )
    assert failed.returncode != 0
    assert "outside candidate or prior state before mutation" in failed.stderr
    assert (target / last_name).read_bytes() == b"late third-party state\n"
    assert not (rollback / "rollback-receipt.json").exists()

    (target / last_name).write_bytes(committed[module.RELEASE_PATHS[-1]])
    (target / last_name).chmod(0o644)
    restored = subprocess.run(
        restore_command(bash, rollback, commit),
        check=True,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    assert "PUBLIC_SITE_ROLLBACK_OK" in restored.stdout
    assert json.loads((rollback / "rollback-receipt.json").read_text(encoding="ascii"))[
        "rollback_verified"
    ] is True
    for name, body in old_bodies.items():
        assert (target / name).read_bytes() == body


def test_posix_unrelated_data_blocks_missing_directory_removal_and_is_preserved(tmp_path):
    bash = require_posix_apply_test()
    module, _repo, commit, _committed, archive, manifest, _payload = build_package(tmp_path)
    test_root = tmp_path / "remote"
    target, old_bodies = make_remote_sandbox(test_root, module)
    missing_prefix = "build_week/prooflock_console/"
    for name in list(old_bodies):
        if name.startswith(missing_prefix):
            old_bodies.pop(name)
    shutil.rmtree(target / "build_week")
    env = dict(os.environ)
    env.update(
        PUBLIC_SITE_DEPLOY_TEST_MODE="1",
        PUBLIC_SITE_DEPLOY_TEST_ROOT=str(test_root),
    )
    applied = subprocess.run(
        apply_command(bash, archive, manifest, commit),
        check=True,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    rollback = Path(
        re.search(r"^PUBLIC_SITE_ROLLBACK_DIR=(.+)$", applied.stdout, re.M).group(1)
    )
    unrelated = target / "build_week" / "prooflock_console" / "operator-note.txt"
    unrelated.write_bytes(b"preserve operator data\n")
    failed = subprocess.run(
        restore_command(bash, rollback, commit),
        check=False,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    assert failed.returncode != 0
    assert unrelated.read_bytes() == b"preserve operator data\n"
    assert not (rollback / "rollback-receipt.json").exists()

    unrelated.unlink()
    restored = subprocess.run(
        restore_command(bash, rollback, commit),
        check=True,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    assert "PUBLIC_SITE_ROLLBACK_OK" in restored.stdout
    assert not (target / "build_week").exists()
    for name, body in old_bodies.items():
        assert (target / name).read_bytes() == body


def test_posix_shared_mutation_lock_blocks_restore_before_touch(tmp_path):
    bash = require_posix_apply_test()
    import fcntl

    module, _repo, commit, committed, archive, manifest, _payload = build_package(tmp_path)
    test_root = tmp_path / "remote"
    target, _old_bodies = make_remote_sandbox(test_root, module)
    env = dict(os.environ)
    env.update(
        PUBLIC_SITE_DEPLOY_TEST_MODE="1",
        PUBLIC_SITE_DEPLOY_TEST_ROOT=str(test_root),
    )
    applied = subprocess.run(
        apply_command(bash, archive, manifest, commit),
        check=True,
        text=True,
        input=ROLLBACK_CAPABILITY + "\n",
        capture_output=True,
        env=env,
    )
    rollback = Path(
        re.search(r"^PUBLIC_SITE_ROLLBACK_DIR=(.+)$", applied.stdout, re.M).group(1)
    )
    lock_path = test_root / "opt" / "lumencore" / "rollbacks" / "public-site" / ".deployment.lock"
    with lock_path.open("a+b") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        failed = subprocess.run(
            restore_command(bash, rollback, commit),
            check=False,
            text=True,
            input=ROLLBACK_CAPABILITY + "\n",
            capture_output=True,
            env=env,
        )
    assert failed.returncode != 0
    assert "holds the deployment lock" in failed.stderr
    assert not (rollback / "rollback-receipt.json").exists()
    for repo_path in module.RELEASE_PATHS:
        assert (target / module.archive_name(repo_path)).read_bytes() == committed[repo_path]
