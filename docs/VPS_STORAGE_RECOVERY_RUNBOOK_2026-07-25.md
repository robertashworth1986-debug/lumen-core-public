# VPS Storage Recovery Planning Runbook

Date: 2026-07-25

## Purpose

This lane builds a bounded storage-recovery plan from existing local evidence.
It does not recover storage.

The lane consists of:

- `config/vps_storage_retention_policy_v1.json`, a source-pinned,
  planning-only policy and candidate inventory;
- `code/ops/BUILD_VPS_STORAGE_RECOVERY_PLAN.py`, a read-only planner that
  verifies the policy and optionally consumes a current local snapshot; and
- `tests/test_vps_storage_recovery_plan.py`, focused fail-closed tests.

Every emitted plan is machine-readable JSON and includes `plan_sha256`. The
digest is SHA-256 over canonical JSON after removing `plan_sha256`.

## Exact No-Action Boundary

The planner does not:

- connect to the VPS or any provider;
- inspect authenticated portals;
- create, move, archive, truncate, or delete data;
- create an archive or recovery bundle;
- restart, reload, enable, or disable a service;
- resize a filesystem, logical volume, or block volume;
- buy storage, hosting, or another service;
- deploy or redeploy code;
- change DNS, proxy, firewall, or routing state;
- read, print, store, or transmit a credential value; or
- grant HumanUnlock.

It reads local files and writes JSON to standard output only. Shell redirection
or publication of that output is a separate operator action.

## Local Evidence Boundary

The policy pins existing repository evidence by path and SHA-256:

| Evidence | Role |
| --- | --- |
| `docs/VPS_DOMAIN_DASHBOARD_RECOVERY_2026-06-19.md` | Historical full-disk incident and ledger observation |
| `docs/LUMA_PRODUCTION_CONTEXT.md` | Historical recovery, rotation, and headroom guidance |
| `code/CANONICAL_GOV_DATA_COLLECTOR.py` | Government snapshot producer definition |
| `code/dashboard_unified_refresh.py` | Government snapshot consumer definition |
| `deploy/PUSH_TO_VPS.ps1` | Full-deploy mutation surface |
| `deploy/PUSH_PROOF_FEEDS_TO_VPS.ps1` | Proof-feed deployment mutation surface |
| `code/deploy/deploy_vps.sh` | Runtime directories and Linux deployment mutation surface |

Missing files, hash drift, malformed policy data, a policy self-hash mismatch,
or any policy field that authorizes external action produces
`BLOCKED_POLICY_OR_EVIDENCE_DRIFT`.

The historical documents conflict across time by design: the root filesystem
was reported full on June 19 and recovered to about 70 percent used on July 5.
Neither observation proves current state. The policy preserves both and sets
`current_vps_state_claimed=false`.

## Known Candidate Inventory

The source-pinned policy registers these aliases:

| Alias | Path token | Default posture |
| --- | --- | --- |
| `government_snapshot_batches` | `application_root/out/gov_live_snapshots` | Retain pending evidence |
| `service_outputs` | `application_root/out/ops` | Retain pending evidence |
| `execution_outputs` | `application_root/out/execution` | Retain pending evidence |
| `paper_ticker_ledger` | `application_root/out/execution/paper_ticker_ledger` | Retain pending evidence |
| `archive_outputs` | `application_root/out/archive` | Retain as archive pending review |
| `application_runtime` | `application_root/python_runtime` | Redeploy review, never cleanup by inference |
| `system_logs` | `system_log_root/lumencore` | Retain pending evidence |

An alias is a review target, not permission. The policy deliberately omits a
numeric conversion of the historical "about 9.8 GB" ledger statement because
it was approximate and later superseded by a rotation event.

## Reclaim Estimate Semantics

The planner separates three quantities:

1. `current_observed_bytes`: bytes in a supplied current local snapshot;
2. `potential_reclaimable_upper_bound_bytes`: an unverified upper bound using
   the maximum observed size per non-additive accounting group; and
3. `confirmed_reclaimable_bytes`: always `0` in this planning lane.

The upper bound is not a safe-delete estimate and is not a safe-archive
estimate. Candidate rows always carry:

- `safe_to_archive=false`;
- `safe_to_delete=false`; and
- `execution_authorized=false`.

When no current snapshot is supplied, current sizes and the aggregate upper
bound are `null`, and the estimate status is
`BLOCKED_CURRENT_SIZE_EVIDENCE_MISSING`.

## Snapshot Contract

Schema: `luma.vps_storage_snapshot.v1`

Required top-level fields:

| Field | Required evidence |
| --- | --- |
| `schema` | Exact schema identifier |
| `observed_at_utc` | Offset-aware ISO 8601 observation time |
| `scope` | `source_kind=local_json_snapshot` and `observation_only=true` |
| `filesystems` | Capacity, use, availability, percentage, and type per mount |
| `mounts` | Device alias, volume role, and separate-volume fact per mount |
| `directory_usage` | Registered alias, mount, bytes, and policy-matching content class |
| `service_health` | Service alias, status, health, and mount dependencies |
| `backup_state` | Verification, authority, evidence references, and alias coverage |
| `retention_state` | Policy presence, authority, and policy reference |
| `hosting_state` | Static, dynamic, and shared-root facts |

Use lowercase aliases rather than hostnames, people, account IDs, or private
paths. The planner hashes backup and retention evidence references before
including them in output. Snapshot keys that indicate passwords, tokens,
private keys, one-time codes, or other credentials are rejected without
echoing their values.

## Run

Inventory-only local review:

```powershell
python code\ops\BUILD_VPS_STORAGE_RECOVERY_PLAN.py
```

This returns `BLOCKED_CURRENT_SNAPSHOT_MISSING` and exit code `2`. It is the
correct current result when no current machine-readable observation exists.

Review a supplied current local snapshot:

```powershell
python code\ops\BUILD_VPS_STORAGE_RECOVERY_PLAN.py --snapshot C:\path\to\local_snapshot.json
```

Use a different local policy only for deliberate review:

```powershell
python code\ops\BUILD_VPS_STORAGE_RECOVERY_PLAN.py --policy C:\path\to\policy.json --snapshot C:\path\to\local_snapshot.json
```

Exit status:

| Status | Meaning |
| --- | --- |
| `0` | Evidence is complete enough for read-only human review |
| `2` | Policy, current snapshot, backup, or retention authority is blocked |

Exit code `0` does not authorize a mutation.

## Decision Lanes

The plan distinguishes four future decisions:

| Lane | Required posture |
| --- | --- |
| Archive | Blocked until backup, retention, holds, destination integrity, rollback, and HumanUnlock are complete |
| Delete | Always `BLOCKED_NO_DELETE_AUTHORITY`; requires an exact object manifest and separate action-time decision |
| Resize | Blocked until provider/filesystem compatibility, capacity, cost, backup, rollback, maintenance window, and HumanUnlock are complete |
| Redeploy | Blocked until headroom, locked package hash, dependencies, rollback, smoke tests, and HumanUnlock are complete |

Even when prerequisites are represented as complete, archive, resize, and
redeploy become `HUMAN_REVIEW_ELIGIBLE_NO_EXECUTION_AUTHORITY`, not approved.
Delete remains blocked.

## HumanUnlock Boundary

Every future mutation requires a private action-time
`LUMA_HUMAN_UNLOCK_TOKEN` of at least 32 characters. The planner:

- never reads or validates a token value;
- never prints or persists a token value;
- never infers approval from a snapshot or policy; and
- always reports `human_unlock_present=false` and
  `execution_authorized=false`.

Deletion, archive/move, service restart, DNS change, storage purchase, storage
resize, deploy, and credential actions remain locked.

## Current Blockers

Based only on the source-pinned repository evidence:

1. No current local machine-readable VPS snapshot is present.
2. Current filesystem capacity, use, and free bytes are therefore unknown.
3. Current candidate-directory byte counts are unknown.
4. Historical storage observations are stale and cannot be promoted to current.
5. Verified backup coverage and restore evidence are not established here.
6. An authorized retention decision and hold review are not established here.
7. No archive destination, resize design, purchase decision, redeploy package,
   rollback plan, or action-time HumanUnlock is present.

Those blockers permit planning and evidence collection only.

## Verification

Run the focused suite:

```powershell
python -m pytest -q tests\test_vps_storage_recovery_plan.py
```

The tests verify:

- policy and evidence-file hashes;
- policy tamper detection;
- inventory-only fail-closed output;
- snapshot schema and authority gates;
- zero confirmed reclaimable bytes;
- non-additive upper-bound accounting;
- separate archive/delete/resize/redeploy decisions;
- HumanUnlock locking;
- sensitive-reference hashing;
- absence of network and mutation APIs;
- no destructive command payloads;
- stdout-only CLI behavior; and
- independently recomputed plan self-hashes.
