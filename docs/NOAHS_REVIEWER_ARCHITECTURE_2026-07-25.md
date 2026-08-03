# NOAHS Reviewer Architecture

Prepared: 2026-07-25

## Purpose

NOAHS is the working architecture name for LumenCore's reviewer proof chain. This document does not assign or imply an acronym expansion.

NOAHS answers one bounded question:

> Is every required custody link current, internally consistent, hash-verifiable, preregistered where applicable, reproducible for the exact release, and independently validated before a reviewer-facing release is called ready?

The answer is conjunctive. Every required link must pass. One missing, zero-byte, stale, inconsistent, hash-drifted, sample-gated, or independently unverified link blocks the release.

NOAHS is not a performance evaluator. It does not calculate or promote model deltas, savings, field outcomes, production readiness, patent scope, trading results, awards, or endorsements.

## Control Files

- Configuration: `config/noahs_proof_chain_v1.json`
- Read-only builder: `code/ops/BUILD_NOAHS_PROOF_CHAIN_GATE.py`
- Focused tests: `tests/test_noahs_proof_chain_gate.py`
- Architecture: `docs/NOAHS_REVIEWER_ARCHITECTURE_2026-07-25.md`

The builder writes no repository artifacts. It reads configured evidence, computes current hashes in memory, validates the chain, prints a gate result, and exits nonzero when blocked.

## Required Chain

| Order | Link | What must be true | Fail-closed examples |
| ---: | --- | --- | --- |
| 1 | Public front door | A recent proof-feed receipt, a sealed seven-endpoint service-contract receipt, and a nonempty local reviewer page exist. | Stale receipt, gateway failure, redirect drift, wrong content type, missing page. |
| 2 | Publication custody | Every required local feed still matches the hash and byte count sealed by the publication receipt. | Feed drift, zero-byte feed, missing feed. |
| 3 | Current source breadth | The current registry is fresh, unique by source, semantically consistent, and above the configured bounded intake floor. | Stale registry, duplicate source, measured flag/status disagreement, zero measured rows. |
| 4 | Baseline custody and completeness | The locked replay body exists and every declared named baseline is actually executed. | Zero-byte replay, implementation-needed baseline, proxy-only baseline, embedded hash failure. |
| 5 | Champion metric custody | The internal holdout chain and accepted-metric audit hashes verify and all high-risk claim gates remain closed. | Broken embedded seal, missing named baseline, source hash missing, field-claim gate open. |
| 6 | Current-row seal | Summary totals equal the current provider rows and each measured snapshot verifies against its embedded canonical hash. | Continuity-only row inflation, stale probe, missing snapshot, row-count mismatch. |
| 7 | Preregistered sample gates | Protocol hashes are pinned, append-only chains verify, status counts match the chains, and the declared sample gate is open. | Protocol drift, broken prior hash, backfilled-chain inconsistency, preliminary sample gate closed. |
| 8 | Reproducibility | The capsule self-hash and source hashes verify for the current branch and commit, including the configured clean-runner and cross-platform locks. | Old branch, old commit, source drift, missing cross-platform lock. |
| 9 | Immutable release manifest | Data-room and vault source manifests match the current files and the Git worktree is clean. | Manifest drift, stale seal, missing source, dirty worktree. |
| 10 | Independent validation | A named, outcome-independent evaluator has completed the reproduction and the resulting receipt supports the declared maturity gate. | Budget packet only, evaluator unnamed, reproduction incomplete, self-assigned maturity. |

## Gate Semantics

The machine-readable result uses:

- `PASS`: every direct artifact and every rule for the link passed.
- `BLOCKED`: at least one direct artifact or rule failed.
- `reviewer_release_ready: true`: all ten required links passed.
- `reviewer_release_ready: false`: one or more required links are blocked.

Every direct source artifact includes its current SHA-256 in the gate output. Manifested child artifacts are independently rehashed and compared with their declared hash and byte count. Append-only EIA chains are replayed record by record using their prior-record and record hashes.

Freshness is an operational custody rule, not a scientific threshold. The configured windows intentionally expire live receipts, row registries, status projections, and release manifests so historical evidence cannot silently present itself as current.

## Read-Only Operation

Concise blocker view:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python code/ops/BUILD_NOAHS_PROOF_CHAIN_GATE.py --format summary --allow-blocked
```

Machine-readable gate:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python code/ops/BUILD_NOAHS_PROOF_CHAIN_GATE.py --format json --allow-blocked
```

Omit `--allow-blocked` in CI or a release preflight. A blocked gate then exits with status `1`.

The builder performs no network request, file write, external action, portal interaction, or performance inference. Repository-relative paths are mandatory, and symlink evidence paths are rejected.

## Current Audit Posture

The 2026-07-25 source audit identified several expected blockers that NOAHS now expresses directly:

1. The live-domain proof-feed receipt is historical, required publication feeds have drifted, and the current service contract is blocked by gateway and edge-route failures.
2. The locked baseline replay body is zero bytes and the declared baseline set is incomplete.
3. Fresh source probes and older hash-backed snapshots do not form one current, reconciled row seal.
4. Preregistered hourly lanes remain below their preliminary common-hour gates.
5. The reproducibility capsule identifies an older branch and commit.
6. The data-room and proof-vault source manifests no longer match every current source artifact.
7. The worktree is not an immutable release.
8. No named independent evaluator has completed an independent reproduction.

These are custody blockers, not negative performance findings.

## No-Claim Boundary

NOAHS verifies evidence custody, freshness, consistency, preregistration, and independent-validation gates. It does not establish model skill, field performance, realized savings, deployment readiness, patent scope, trading results, an award, or endorsement.

Internal receipts remain internal receipts. A passing local hash check cannot be promoted into external validation, and a passing sample-size threshold cannot be promoted into a scientific result without the frozen evaluation rules and independent boundary also passing.
