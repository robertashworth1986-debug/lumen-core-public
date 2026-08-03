from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT / "code" / "ops" / "BUILD_LOCAL_PUBLIC_BRANCH_DRIFT_GATE.py"
)
AS_OF = "2026-07-25T22:00:00Z"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "local_public_branch_drift_gate", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_git(repo: Path, *args: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )
    return completed.stdout.strip()


def write(repo: Path, relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit_all(repo: Path, message: str) -> str:
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", message)
    return run_git(repo, "rev-parse", "HEAD")


def fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_git(repo, "init")
    run_git(repo, "config", "user.email", "test@example.invalid")
    run_git(repo, "config", "user.name", "Test Runner")
    write(repo, "seed.txt", "base\n")
    commit_all(repo, "base")
    run_git(repo, "branch", "-M", "main")
    run_git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    run_git(
        repo,
        "config",
        "remote.origin.fetch",
        "+refs/heads/*:refs/remotes/origin/*",
    )
    run_git(repo, "config", "branch.main.remote", "origin")
    run_git(repo, "config", "branch.main.merge", "refs/heads/main")
    return repo


def build(module, repo: Path) -> dict:
    return module.build_gate(repo, as_of_utc=AS_OF)


def blocker_codes(gate: dict) -> set[str]:
    return {row["code"] for row in gate["blockers"]}


def test_clean_exact_public_main_commit_passes(tmp_path: Path):
    module = load_module()
    repo = fixture_repo(tmp_path)

    gate = build(module, repo)

    state = gate["git_state"]
    assert gate["summary"]["status"] == "PASS_CLEAN_AT_PUBLIC_MAIN_COMMIT"
    assert gate["summary"]["public_main_claim_allowed"] is True
    assert state["current_branch"] == "main"
    assert state["current_head"] == state["upstream_hash"]
    assert state["current_head"] == state["public_main_hash"]
    assert state["merge_base"] == state["current_head"]
    assert state["ahead_of_public_main"] == 0
    assert state["behind_public_main"] == 0
    assert state["dirty_tracked_count"] == 0
    assert state["dirty_untracked_count"] == 0


def test_missing_public_and_upstream_refs_fail_closed(tmp_path: Path):
    module = load_module()
    repo = fixture_repo(tmp_path)
    run_git(repo, "update-ref", "-d", "refs/remotes/origin/main")

    gate = build(module, repo)

    assert gate["summary"]["status"] == "BLOCKED_GIT_STATE_UNRESOLVED"
    assert gate["summary"]["public_main_claim_allowed"] is False
    assert {
        "UPSTREAM_REF_UNRESOLVED",
        "UPSTREAM_HASH_UNRESOLVED",
        "PUBLIC_MAIN_REF_UNRESOLVED",
    }.issubset(blocker_codes(gate))
    assert gate["git_state"]["public_main_hash"] is None
    assert gate["git_state"]["merge_base"] is None


def test_detached_head_fails_closed(tmp_path: Path):
    module = load_module()
    repo = fixture_repo(tmp_path)
    run_git(repo, "checkout", "--detach", "HEAD")

    gate = build(module, repo)

    assert gate["summary"]["status"] == "BLOCKED_DETACHED_HEAD"
    assert gate["summary"]["public_main_claim_allowed"] is False
    assert "DETACHED_HEAD" in blocker_codes(gate)
    assert gate["git_state"]["head_attached"] is False
    assert gate["git_state"]["current_branch"] is None
    assert gate["git_state"]["current_head"] == gate["git_state"][
        "public_main_hash"
    ]


def test_divergent_history_reports_exact_ahead_behind_and_blocks(
    tmp_path: Path,
):
    module = load_module()
    repo = fixture_repo(tmp_path)
    run_git(repo, "checkout", "-b", "work")
    run_git(repo, "update-ref", "refs/remotes/origin/work", "HEAD")
    run_git(repo, "config", "branch.work.remote", "origin")
    run_git(repo, "config", "branch.work.merge", "refs/heads/work")
    write(repo, "local.txt", "local commit\n")
    commit_all(repo, "local")

    run_git(repo, "checkout", "main")
    write(repo, "public.txt", "public commit\n")
    public_head = commit_all(repo, "public")
    run_git(repo, "update-ref", "refs/remotes/origin/main", public_head)
    run_git(repo, "checkout", "work")

    gate = build(module, repo)

    state = gate["git_state"]
    assert gate["summary"]["status"] == "BLOCKED_DIVERGED_FROM_PUBLIC_MAIN"
    assert gate["summary"]["public_main_claim_allowed"] is False
    assert state["ahead_of_public_main"] == 1
    assert state["behind_public_main"] == 1
    assert {
        "HEAD_AHEAD_OF_PUBLIC_MAIN",
        "HEAD_BEHIND_PUBLIC_MAIN",
    }.issubset(blocker_codes(gate))


def test_dirty_tracked_and_untracked_counts_block_without_path_disclosure(
    tmp_path: Path,
):
    module = load_module()
    repo = fixture_repo(tmp_path)
    write(repo, "seed.txt", "dirty tracked content\n")
    sensitive_name = "private-patent-note.txt"
    write(repo, sensitive_name, "do not disclose\n")

    gate = build(module, repo)
    encoded = json.dumps(gate)

    state = gate["git_state"]
    assert gate["summary"]["status"] == "BLOCKED_DIRTY_WORKTREE"
    assert gate["summary"]["public_main_claim_allowed"] is False
    assert state["dirty_tracked_count"] == 1
    assert state["dirty_untracked_count"] == 1
    assert {
        "DIRTY_TRACKED_CHANGES",
        "DIRTY_UNTRACKED_CHANGES",
    }.issubset(blocker_codes(gate))
    assert sensitive_name not in encoded
    assert "dirty tracked content" not in encoded
    assert "do not disclose" not in encoded


def test_git_subprocess_boundary_is_read_only_and_local(monkeypatch):
    module = load_module()
    calls: list[list[str]] = []
    head = "1" * 40
    responses = {
        ("rev-parse", "--is-inside-work-tree"): b"true\n",
        ("rev-parse", "--verify", "HEAD"): f"{head}\n".encode(),
        ("symbolic-ref", "--quiet", "--short", "HEAD"): b"main\n",
        (
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{upstream}",
        ): b"origin/main\n",
        (
            "rev-parse",
            "--verify",
            "@{upstream}^{commit}",
        ): f"{head}\n".encode(),
        (
            "rev-parse",
            "--verify",
            "refs/remotes/origin/main^{commit}",
        ): f"{head}\n".encode(),
        (
            "merge-base",
            "HEAD",
            "refs/remotes/origin/main",
        ): f"{head}\n".encode(),
        (
            "rev-list",
            "--left-right",
            "--count",
            "HEAD...refs/remotes/origin/main",
        ): b"0\t0\n",
        (
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ): b"",
    }

    def fake_run(command, **kwargs):
        calls.append(command)
        args = tuple(command[5:])
        return subprocess.CompletedProcess(
            command,
            0 if args in responses else 1,
            stdout=responses.get(args, b""),
            stderr=b"",
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    gate = module.build_gate(Path.cwd(), as_of_utc=AS_OF)

    assert gate["summary"]["status"] == "PASS_CLEAN_AT_PUBLIC_MAIN_COMMIT"
    assert calls
    observed_subcommands = {command[5] for command in calls}
    assert observed_subcommands <= module.READ_ONLY_GIT_COMMANDS
    forbidden = {
        "fetch",
        "checkout",
        "switch",
        "merge",
        "rebase",
        "stash",
        "commit",
        "push",
        "pull",
        "worktree",
        "update-ref",
    }
    assert not any(token in forbidden for command in calls for token in command)
    assert all(command[:3] == ["git", "-c", "core.fsmonitor=false"] for command in calls)
    assert gate["capability_boundary"]["network_access_performed"] is False


def test_gate_hash_is_stable_for_identical_observation(tmp_path: Path):
    module = load_module()
    repo = fixture_repo(tmp_path)

    first = build(module, repo)
    second = build(module, repo)
    expected = dict(first)
    observed_hash = expected.pop("gate_sha256")

    assert first == second
    assert observed_hash == module.canonical_sha256(expected)
    assert first["safest_next_action"].endswith(
        "Never merge this branch wholesale."
    )
