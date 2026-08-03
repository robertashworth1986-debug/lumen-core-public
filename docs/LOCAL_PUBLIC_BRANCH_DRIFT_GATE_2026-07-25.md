# Local Public Branch Drift Gate

Date: 2026-07-25

## Purpose

This gate provides a bounded local observation of the relationship between the
current worktree and the locally available `refs/remotes/origin/main` ref. It
reports commit graph facts and dirty-path counts without recording changed path
names, file contents, remote URLs, credentials, private identifiers, or
patent-sensitive material.

The generated receipt is:

`out/ops/local_public_branch_drift_gate_latest.json`

## Read-Only Boundary

The builder uses only these local Git subcommands:

- `rev-parse`
- `symbolic-ref`
- `merge-base`
- `rev-list`
- `status`

It sets `GIT_OPTIONAL_LOCKS=0`, disables the filesystem monitor for each
observation, and does not perform network access, fetch, pull, checkout, switch,
merge, rebase, stash, commit, push, ref mutation, or worktree mutation.

The builder writes only the requested local JSON receipt. Tests may construct
and mutate disposable repositories under pytest temporary directories; those
fixture operations are not part of the builder.

## Gate Semantics

`PASS_CLEAN_AT_PUBLIC_MAIN_COMMIT` requires all of the following:

- attached HEAD and resolved current branch;
- resolved current HEAD, branch upstream ref and hash, public-main ref and
  hash, and merge base;
- exactly zero commits ahead of and zero commits behind public main;
- exact HEAD/public-main hash equality;
- zero dirty tracked paths and zero dirty untracked paths.

Missing refs, missing Git state, detached HEAD, divergence, and either category
of dirty path fail closed. The gate reports counts only. It never reports the
names or contents of dirty paths.

## Claim Boundary

This local receipt reports bounded Git graph and worktree observations only. It
does not prove that local changes are committed, reviewed, pushed, merged,
published, deployed, or present on public main. Any unresolved ref, detached
HEAD, divergence, or dirty tracked or untracked state blocks a claim that the
local work is on public main.

## Safest Next Action

After human review, selective-port approved changes from a clean worktree
created at the current public-main commit; rerun focused and broad checks there,
then review the resulting diff. Never merge this branch wholesale.

## Commands

Build the local receipt:

```powershell
python code\ops\BUILD_LOCAL_PUBLIC_BRANCH_DRIFT_GATE.py
```

Require a clean public-main result in automation:

```powershell
python code\ops\BUILD_LOCAL_PUBLIC_BRANCH_DRIFT_GATE.py --strict
```

Run focused tests:

```powershell
python -m pytest -q tests\test_local_public_branch_drift_gate.py
```
