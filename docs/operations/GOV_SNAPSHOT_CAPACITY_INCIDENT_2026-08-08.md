# Government Snapshot Capacity Incident — 2026-08-08

## Status

Recovery in progress. This document records observed operational facts and the
bounded software correction. It is not a claim of external validation or field
performance.

## Observed state

- The Oracle VPS root filesystem reached 100% allocation and inode exhaustion.
- `/opt/lumencore/out/gov_live_snapshots` contained at least 620,390 files and
  occupied approximately 117 GB during diagnosis.
- `luma-dashboard-refresh.service` repeatedly exited successfully with
  `loop already running` and was restarted every five seconds by
  `Restart=always`.
- When the filesystem was full, the singleton lock could be created as a
  zero-byte file before its JSON payload write failed.
- Collector throttling existed only in process memory, so a restarted process
  did not inherit the prior attempt time.

## Root cause

Three controls interacted badly under disk exhaustion:

1. a partial singleton-lock write was not removed on failure;
2. a successful duplicate-worker exit was treated as restartable forever; and
3. the government collector had no persistent lease or storage-capacity gate.

## Bounded correction

- Persist the collector attempt lease before collection begins.
- Block collection when minimum free space is unavailable or the configured
  snapshot-file ceiling is reached.
- Remove a partially created singleton lock when its payload write fails.
- Restart the dashboard worker only on failure and rate-limit repeated starts.
- Never prune evidence automatically. Custody transfer, integrity checks, and
  an explicit human-authorized retention action remain separate gates.

## Defaults

- Minimum free space: 2 GiB (`LUMA_GOV_SNAPSHOT_MIN_FREE_BYTES`).
- Maximum snapshot files: 100,000 (`LUMA_GOV_SNAPSHOT_MAX_FILES`).
- Persistent collection interval: 900 seconds in the dashboard worker.

## Recovery boundary

The code correction prevents additional uncontrolled growth after deployment.
It does not itself recover disk space. The existing snapshot corpus must first
be transferred to the E-drive custody vault, counted, archive-tested, and
SHA-256 sealed. VPS pruning remains locked behind the production HumanUnlock
control.
