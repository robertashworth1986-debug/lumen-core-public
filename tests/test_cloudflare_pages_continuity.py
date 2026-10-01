from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_CODE = ROOT / "code" / "deploy"
BUILDER_PATH = DEPLOY_CODE / "build_cloudflare_pages_preview.py"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "cloudflare-pages-continuity.yml"
GUIDE_PATH = ROOT / "docs" / "API_AND_DEMO_CONTINUITY_CHECKLIST.md"


def load_builder():
    sys.path.insert(0, str(DEPLOY_CODE))
    try:
        spec = importlib.util.spec_from_file_location("cloudflare_pages_builder", BUILDER_PATH)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


BUILDER = load_builder()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def make_release_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "--quiet")
    git(repo, "config", "user.email", "pages-tests@example.invalid")
    git(repo, "config", "user.name", "Pages Tests")
    for index, repo_path in enumerate(BUILDER.release.RELEASE_PATHS, start=1):
        path = repo / repo_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"committed-{index}\n".encode("ascii"))
    git(repo, "add", "--", *BUILDER.release.RELEASE_PATHS)
    git(repo, "commit", "--quiet", "-m", "pages fixture")
    commit = git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    return repo, commit


def test_preview_uses_pinned_blobs_and_byte_identical_route_aliases(tmp_path):
    repo, commit = make_release_repo(tmp_path)
    for repo_path in BUILDER.release.RELEASE_PATHS:
        (repo / repo_path).write_bytes(b"dirty worktree bytes\n")

    output = tmp_path / "pages"
    manifest = tmp_path / "pages-manifest.json"
    payload = BUILDER.build_pages_preview(
        repo_root=repo,
        source_commit=commit,
        output_dir=output,
        manifest_path=manifest,
    )

    expected_paths = {
        BUILDER.release.archive_name(path) for path in BUILDER.release.RELEASE_PATHS
    } | set(BUILDER.ALIASES)
    actual_paths = {
        path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()
    }
    assert actual_paths == expected_paths
    assert (output / "index.html").read_bytes() == (output / "operator_home.html").read_bytes()
    assert (output / "evidence" / "index.html").read_bytes() == (
        output / "evidence" / "index_bounded.html"
    ).read_bytes()
    assert (output / "operator_home.html").read_bytes() != b"dirty worktree bytes\n"
    assert payload["schema"] == "lumencore.cloudflare_pages_preview_manifest.v1"
    assert payload["deployment_state"] == "NOT_DEPLOYED"
    assert payload["source_commit"] == commit
    assert payload["source_file_count"] == 43
    assert payload["alias_count"] == 2
    assert payload["file_count"] == 45
    assert payload == json.loads(manifest.read_text(encoding="utf-8"))
    for alias in payload["aliases"]:
        assert alias["sha256"] == hashlib.sha256(
            (output / alias["path"]).read_bytes()
        ).hexdigest()


def test_preview_fails_closed_for_unpinned_source_or_existing_output(tmp_path):
    repo, commit = make_release_repo(tmp_path)
    with pytest.raises(BUILDER.PagesPreviewError, match="full 40-character"):
        BUILDER.build_pages_preview(
            repo_root=repo,
            source_commit=commit[:12],
            output_dir=tmp_path / "short",
            manifest_path=tmp_path / "short.json",
        )

    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(BUILDER.PagesPreviewError, match="already exists"):
        BUILDER.build_pages_preview(
            repo_root=repo,
            source_commit=commit,
            output_dir=output,
            manifest_path=tmp_path / "existing.json",
        )


def test_workflow_packages_only_and_has_no_cloudflare_or_dns_write_path():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    trigger = workflow.split("permissions:", maxsplit=1)[0]
    assert "pull_request:" in trigger
    assert "workflow_dispatch:" in trigger
    assert "PACKAGE_CLOUDFLARE_PAGES_PREVIEW" in trigger
    assert "permissions:\n  contents: read" in workflow
    assert "persist-credentials: false" in workflow
    assert "build_cloudflare_pages_preview.py" in workflow
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in workflow
    for forbidden in (
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
        "wrangler ",
        "pages deploy",
        "dns_records",
        "nameserver",
    ):
        assert forbidden not in workflow


def test_continuity_guide_keeps_dns_and_deployment_as_separate_approval_steps():
    guide = GUIDE_PATH.read_text(encoding="utf-8")
    assert "Cloudflare Pages continuity package" in guide
    assert "does not deploy" in guide
    assert "preserve the existing Zoho mail records" in guide
