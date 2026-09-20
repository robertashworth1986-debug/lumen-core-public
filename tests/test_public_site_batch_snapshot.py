"""Immutable Git snapshot batching preserves release bytes and strict boundaries."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_packager():
    spec = importlib.util.spec_from_file_location("batch_snapshot_subject", ROOT / "code/deploy/package_public_site_release.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo, *args, input_data=None):
    return subprocess.run(["git", "-C", str(repo), *args], input=input_data, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True, timeout=15).stdout


@pytest.fixture
def small_repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "--quiet")
    git(root, "config", "user.email", "snapshot-tests@example.invalid")
    git(root, "config", "user.name", "Snapshot Tests")
    git(root, "config", "core.autocrlf", "false")
    bodies = {"dashboard/a.html": b"original\n", "dashboard/binary.bin": b"a\x00\nb\xff\n",
              "dashboard/empty.dat": b"", "dashboard/copy.html": b"original\n"}
    for name, body in bodies.items():
        path = root / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(body)
    git(root, "add", "--", "dashboard")
    git(root, "commit", "--quiet", "-m", "immutable test data")
    commit = git(root, "rev-parse", "HEAD").decode().strip()
    return root, commit, bodies


def build(module, repo, commit, bodies, folder):
    return module.build_release_package(repo_root=repo, source_commit=commit,
        archive_path=folder / "release.tar", manifest_path=folder / "manifest.json", release_paths=tuple(bodies))


def test_one_package_does_not_spawn_git_per_file(small_repo, tmp_path, monkeypatch):
    module = load_packager()
    repo, commit, bodies = small_repo
    commands = []
    original = module._git

    def observed(root, *args, **kwargs):
        commands.append(args[0])
        return original(root, *args, **kwargs)

    monkeypatch.setattr(module, "_git", observed)
    payload = build(module, repo, commit, bodies, tmp_path)
    with tarfile.open(tmp_path / "release.tar", "r:") as archive:
        assert {item.name: archive.extractfile(item).read() for item in archive} == {
            name.removeprefix("dashboard/"): data for name, data in bodies.items()}
    assert payload["file_count"] == 4
    assert len(commands) <= 4, commands


def test_git_replace_cannot_change_bytes_under_a_pinned_commit(small_repo, tmp_path):
    module = load_packager()
    repo, commit, bodies = small_repo
    oid = git(repo, "rev-parse", f"{commit}:dashboard/a.html").decode().strip()
    replacement = git(repo, "hash-object", "-w", "--stdin", input_data=b"replacement must not become release bytes\n").decode().strip()
    git(repo, "replace", oid, replacement)
    build(module, repo, commit, bodies, tmp_path)
    with tarfile.open(tmp_path / "release.tar", "r:") as archive:
        assert archive.extractfile("a.html").read() == bodies["dashboard/a.html"]


def test_dirty_worktree_and_later_head_do_not_change_the_pinned_batch(small_repo, tmp_path):
    module = load_packager()
    repo, commit, bodies = small_repo
    (repo / "dashboard/a.html").write_bytes(b"later commit\n")
    git(repo, "add", "--", "dashboard/a.html")
    git(repo, "commit", "--quiet", "-m", "new head")
    (repo / "dashboard/binary.bin").write_bytes(b"uncommitted")
    payload = build(module, repo, commit, bodies, tmp_path)
    assert payload["source_commit"] == commit
    with tarfile.open(tmp_path / "release.tar", "r:") as archive:
        assert archive.extractfile("a.html").read() == bodies["dashboard/a.html"]
        assert archive.extractfile("binary.bin").read() == bodies["dashboard/binary.bin"]


@pytest.mark.parametrize("paths", [(), ("dashboard/a.html", "dashboard/a.html"), ("dashboard/missing.html",), ("dashboard/../outside",)])
def test_invalid_batch_membership_produces_no_release(small_repo, tmp_path, paths):
    module = load_packager()
    repo, commit, _ = small_repo
    with pytest.raises(module.ReleasePackageError):
        module.build_release_package(repo_root=repo, source_commit=commit, archive_path=tmp_path / "bad.tar",
                                     manifest_path=tmp_path / "bad.json", release_paths=paths)
    assert not (tmp_path / "bad.tar").exists()
    assert not (tmp_path / "bad.json").exists()


def git_oid(body):
    return hashlib.sha1(f"blob {len(body)}\0".encode() + body, usedforsecurity=False).hexdigest()


def batch_record(body):
    return f"{git_oid(body)} blob {len(body)}\n".encode() + body + b"\n"


def test_batch_parser_preserves_empty_binary_and_newline_containing_objects():
    module = load_packager()
    bodies = [b"", b"line\nnext\x00\xff\n", b"header-like blob 100\n"]
    expected = [(git_oid(body), len(body)) for body in bodies]
    assert module._parse_batch_objects(b"".join(batch_record(body) for body in bodies), expected) == {
        git_oid(body): body for body in bodies}


@pytest.mark.parametrize("mutation", ["wrong_oid", "wrong_type", "wrong_size", "changed_body", "missing_terminator", "truncated_body", "trailing_data", "missing_object"])
def test_batch_parser_rejects_inconsistent_or_incomplete_git_output(mutation):
    module = load_packager()
    body = b"frozen\n\x00data"
    payload = batch_record(body)
    if mutation == "wrong_oid":
        payload = b"0" * 40 + payload[40:]
    elif mutation == "wrong_type":
        payload = payload.replace(b" blob ", b" tree ", 1)
    elif mutation == "wrong_size":
        payload = payload.replace(f"blob {len(body)}".encode(), b"blob 9999", 1)
    elif mutation == "changed_body":
        payload = payload.replace(b"frozen", b"forged", 1)
    elif mutation == "missing_terminator":
        payload = payload[:-1]
    elif mutation == "truncated_body":
        payload = payload[:-4]
    elif mutation == "trailing_data":
        payload += b"unexpected\n"
    elif mutation == "missing_object":
        payload = f"{git_oid(body)} missing\n".encode()
    with pytest.raises(module.ReleasePackageError):
        module._parse_batch_objects(payload, [(git_oid(body), len(body))])


@pytest.mark.parametrize("mutation", ["duplicate", "oversized", "symlink", "gitlink", "unterminated"])
def test_invalid_tree_metadata_is_rejected_before_any_blob_fetch(monkeypatch, mutation):
    module = load_packager()
    commit = "1" * 40
    oid = git_oid(b"data")
    mode, kind, size = "100644", "blob", "4"
    if mutation == "oversized":
        size = str(module.MAX_RELEASE_BYTES + 1)
    elif mutation == "symlink":
        mode = "120000"
    elif mutation == "gitlink":
        mode, kind, size = "160000", "commit", "-"
    tree = f"{mode} {kind} {oid} {size}\tdashboard/a.html\0".encode()
    if mutation == "duplicate":
        tree *= 2
    elif mutation == "unterminated":
        tree = tree[:-1]
    calls = []

    def fake_git(root, *args, **kwargs):
        calls.append(args[0])
        if args[0] == "rev-parse":
            return (commit + "\n").encode()
        if args[0] == "ls-tree":
            return tree
        raise AssertionError("Invalid metadata reached blob fetch")

    monkeypatch.setattr(module, "_git", fake_git)
    with pytest.raises(module.ReleasePackageError):
        module._read_commit_blobs(Path("unused"), commit, ("dashboard/a.html",))
    assert calls == ["rev-parse", "ls-tree"]


def test_shared_blob_is_fetched_once_and_nonselected_paths_are_not_read(small_repo, monkeypatch):
    module = load_packager()
    repo, commit, bodies = small_repo
    original = module._git
    batch_requests = []

    def observed(root, *args, **kwargs):
        if args[0] == "cat-file":
            batch_requests.append(kwargs["input_data"])
        return original(root, *args, **kwargs)

    monkeypatch.setattr(module, "_git", observed)
    selected = ("dashboard/a.html", "dashboard/copy.html")
    snapshot = module._read_commit_blobs(repo, commit, selected)
    assert list(snapshot) == list(selected)
    assert len(batch_requests) == 1
    assert batch_requests[0].splitlines() == [git_oid(bodies["dashboard/a.html"]).encode()]


def test_git_timeout_is_a_release_error(monkeypatch):
    module = load_packager()

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(module.subprocess, "run", timeout)
    with pytest.raises(module.ReleasePackageError, match="failed"):
        module._git(Path("unused"), "rev-parse", "HEAD")
