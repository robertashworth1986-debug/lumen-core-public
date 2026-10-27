# Private legacy feed repair boundary

This source change supports active outcome 2: trustworthy reviewer/operator
observations. It does **not** restore four public feeds or authorize runtime
promotion. The existing public metrics contract and its fail-closed verdict stay
unchanged. Issue #234 remains open.

## Operator-only, read-only contracts

The four filename routes are installed only in the operator serving profile,
behind the unchanged operator middleware. The minimal profile continues to HOLD
all four, imports no artifact reader, and starts no producer. GET never invokes
the old builders, evidence auto-repair, broker adapters, or workers.

| Private route | Existing artifact and disposition |
|---|---|
| `/api/live_status.json` | Always `producer_unmapped` (503). The similarly named infrastructure builder contains scenario constants and is not an authoritative live observation source. |
| `/api/federal_brief.json` | Reads only `out/federal_brief.json`; missing/malformed/stale output fails. Even a recently generated output remains `source_provenance_unverified` (503): the current builder supplies no binding to its upstream observations and silently defaults missing inputs. |
| `/api/evidence_summary.json` | Reads the newest canonical UTC-named directory under `dashboard/evidence/runs`, its `summary.json`, and `manifest.sha256.json`. Requires matching run identities, the exact summary hash, and valid dataset counts. Returns only run identity and counts, labeled retained research. It does not call `/api/evidence/latest` or claim fresh input observations or measured performance. |
| `/api/executor_heartbeat.json` | Reads `out/execution/live_executor_heartbeat.json`, requires schema `1.0.0`, aware `timestamp_utc`, and an enumerated status. Returns only those three fields. A fresh blocked/error heartbeat remains blocked/error, not healthy execution. No trading worker is started. |

Successful responses use `lumencore_private_feed_observation.v1`, with separate
observation and source timestamps, source SHA-256, explicit freshness basis,
finite configured age budget, `data_available`, disposition, and a small field
allowlist. Failures return 503 with `data_available=false` and no data payload.
All responses are no-store. SHA-256 establishes byte identity, not independent
validation or trusted provenance of the original research itself.

The reader refuses duplicate JSON members, non-finite numbers, invalid schemas,
missing/naive/future/stale timestamps, files over one MiB, more than 1,000 run
entries, symlinks in any path component, nonregular files, and detected changes
during reads. Linux descriptor-relative NOFOLLOW reads fail closed on unsupported
platforms. It never logs or returns absolute paths, exception strings, source
payloads outside the allowlist, account balances, order details, or credentials.

## Configuration is a separate production decision

The source supplies **no freshness defaults**. The three non-live-status routes
require their respective positive finite environment values:

- `LUMA_PRIVATE_FEED_MAX_AGE_SECONDS_FEDERAL_BRIEF`
- `LUMA_PRIVATE_FEED_MAX_AGE_SECONDS_EVIDENCE_SUMMARY`
- `LUMA_PRIVATE_FEED_MAX_AGE_SECONDS_EXECUTOR_HEARTBEAT`

Absent/invalid budgets return `freshness_unconfigured`, before artifact reads.
Research run age is not dataset observation age. The heartbeat budget must be
chosen against the actual producer cadence. Budget configuration alone cannot
repair a missing producer or federal provenance.

Production target: the existing Linux `luma-gateway` service and its existing
`/opt/lumencore` root. No new artifact permission, public alias, or copied private
source is authorized by this code. Its exact runtime closure now contains 21
files, including `operator_feed_reads.py`; all corresponding workflow count
checks are updated. Static-site releases cannot install this runtime change.

Before any live change, separately approve the exact commit, service restart and
configuration values through the guarded runtime process. Existing operator
access uses `LUMA_OPERATOR_API_TOKEN` / `LUMA_OPERATOR_API_TOKENS`; provisioning
or changing such credentials requires specific approval and secure handoff.
They protect broad operator APIs, not merely these reads. Do not put them in the
public metrics workflow. The runtime repair lane separately requires its private
HumanUnlock gate. This patch neither sets those values nor changes service users,
permissions, authentication, visibility, or worker state.

## Acceptance

Local tests use synthetic files only and do not prove production restoration.
Required CI installs the existing hash-locked institutional dependencies and
requires HTTP dependencies before running authentication and minimal-profile
integration tests. A live acceptance receipt must separately establish the
approved commit/service identity, denied anonymous access, real artifact
availability, exact schema, source age and configured budget. Until that receipt,
the scheduled public monitor remains an honest report of unavailable private
feeds. Live status mapping and federal producer provenance remain unresolved.
