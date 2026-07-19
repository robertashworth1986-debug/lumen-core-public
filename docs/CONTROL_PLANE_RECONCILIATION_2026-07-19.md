# LumenCore Control-Plane Reconciliation — 2026-07-19 UTC

**Owner:** Robert Ashworth  
**State ID:** `control-plane-20260719T025600Z`  
**Machine-readable state:** `dashboard/data/control_plane_state.json`  
**State SHA-256:** `6dcd309c0da75b14a1024b590f4160b8e7169f7ad0cd9583bccc4faae0e45304`  
**Authority:** Public-safe reconciliation only; not action authority.  
**Failure mode:** `FAIL_CLOSED`

## Purpose

This snapshot reconciles the latest bounded Gmail handoffs, current GitHub pull-request heads and workflows, official deadline checks, and known historical repository snapshots into one ordered control surface.

It exists to prevent five recurring control failures:

1. a historical dashboard being treated as live portal authority;
2. an older pull-request description being treated as the current head;
3. one proposal lane borrowing certifications, files, or assumptions from another;
4. green CI being treated as deployment or submission evidence;
5. duplicate outreach being triggered by stale coordination text.

The state does not send email, access a portal, sign, certify, merge, deploy, pay, accept legal terms, or submit anything.

## Current execution order

| Priority | Lane | Current bounded state | Deadline lock | Immediate control |
|---:|---|---|---|---|
| 1 | MissionWeave | `BLOCKED` — latest handoff records 36/50 gates cleared and 14 open | 2026-07-22 12:00 PM Eastern | Preserve JCP/DD Form 2345 and final certification as fail-closed; retrieve only official evidence and component clarification. |
| 2 | HarborSentinel | `RECONCILIATION_REQUIRED` | 2026-07-22 12:00 PM Eastern | Re-establish current topic-specific portal and attachment state; do not rely on the June dashboard or closed PR #3 as submission authority. |
| 3 | ProofLock | `HOLD` — PR #36 head `4584a41dbedd2f856bba5fa8202e7dcc8e4a448f`; current workflows green; live release 10/14 | 2026-07-21 7:00 PM Central | Deploy only the four stale files through the ProofLock lane, require 14/14, refresh the release receipt, then complete the human video and Devpost gates. |
| 4 | Public site | `READY_FOR_REVIEW` — PR #38 head `e67e5074d908e0b57d2d8e4f59e8ef5745299ba8`; current workflows green | No external deadline | Reconcile the PR description with current QA; do not deploy until the deadline lanes are safe. |
| 5 | DICE | `PREPARATION` — PR #37 head `69d48c09b7dbed80a8043952becbf76642c7eb98` | 2026-08-25 2:00 PM Eastern | Complete the official Amendment 01 redline and P1-template conformity before broader drafting. Absence of a separate encouraging reply is not treated as a fabricated invitation gate. |
| 6 | Outreach governance | `NO_ACTION_DUE` — latest handoff head `85a1c5c178af38c841a25e423b057790a4177c8e`; zero send-now lanes | Event-driven | Recheck Gmail immediately before any future decision; preserve the append-only sent-receipt ledger and follow-up limit. |
| 7 | EPRI / OPAI | `WAITING` | Event-driven | The requested onboarding information was already sent once. Wait for DocuSign or an exact entity-format correction; do not duplicate. |
| 8 | Patent Center | `READ_ONLY` | Official-record driven | Retrieve and hash official notices while signed in; do not infer deadlines, file, pay, or make legal conclusions from repository dates. |
| 9 | EIA prospective lane | `PRELIMINARY` | Evidence driven | Continue collection without accuracy, outage, savings, or validation promotion. |

## Exact stale-state findings

### `docs/CANONICAL_OPERATING_STATE.md`

The July 17 snapshot contains superseded operational statements, including an unsent-EPRI-draft state and an older pull-request curation list. This PR adds a prominent historical-snapshot notice rather than rewriting unrelated active implementation scope.

### `dashboard/data/grant_readiness_status.json`

The checked-in feed was generated on June 20. It contains useful historical package and public AIS evidence, but it must not be interpreted as current DSIP, BAAT, NSF, JCP, certification, or submit readiness.

A separate high-severity control finding remains queued: a fallback generator must never replace the source generation timestamp with the present observation time in a way that launders stale readiness into a fresh-looking feed. The bounded correction is to preserve `source_generated_utc`, add a separate `observed_utc`, and force `HISTORICAL_SNAPSHOT_HOLD` when current source receipts are unavailable.

### ProofLock PR #36

The actual current head and green workflows are newer than portions of the PR description. The live byte-identity gate is still 10/14, with these stale files:

- `prooflock_core.js`
- `prooflock_favicon.svg`
- `THREE_LICENSE.txt`
- `verify_receipt.py`

The earlier `e9a1aba` 14/14 receipt remains useful only for that historical build. It cannot prove that the corrected current authority predicate is deployed.

An independent implementation review also found a bounded browser/Python parity gap: the browser verifier normalizes malformed JSON row types into structured failures, while the Python verifier can raise when a receipt, artifact row, or gate row is not an object. That correction belongs on PR #36, not in this control-plane branch.

### Public-site PR #38

The branch is current-head green and has a later browser-QA receipt than the initial PR description. The description should be reconciled before final review or merge; the control-plane branch does not alter public-site runtime files.

## What this control-plane PR changes

- adds the machine-readable, hash-locked control-plane state;
- adds a standard-library verifier for schema, state hash, deadline locks, unique priorities, evidence rows, required open gates, stale-source registration, public/private boundary, and explicit non-action controls;
- adds focused tests for valid custody, deadline locks, duplicated lanes, missing gates, unauthorized actions, payload mutation, and private-identifier exclusion;
- adds path-scoped GitHub Actions CI;
- marks the older canonical operating-state file as a historical snapshot pending full reconciliation.

## Separation rules

- MissionWeave and HarborSentinel are separate July 22 proposals. Do not share Volume V assumptions, certifications, rights assertions, portal receipts, or founder answers between them without topic-specific evidence.
- ProofLock and the public site remain separate branches and release decisions.
- DICE remains later preparation and must not consume July 21–22 execution capacity except for bounded document preservation.
- Research lanes remain non-promotional unless their own predeclared evidence gates pass.
- Luma1 and Luma2 may work in parallel, but repository heads, exact paths, test receipts, exclusions, and action boundaries must be returned in one auditable handoff.

## Actions explicitly not taken by this state

No external email, portal upload, certification, signature, final confirmation, payment, legal acceptance, pull-request merge, production deployment, public video publication, Devpost submission, or claim expansion is represented by this artifact.

**Operating principle:** evidence before claims; bounded light speed.
