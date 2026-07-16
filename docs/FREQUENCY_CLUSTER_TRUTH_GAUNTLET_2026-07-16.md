# Frequency-Cluster Truth Gauntlet

## Decision

`NULL_OR_ADVERSE_NOT_PROMOTED_DO_NOT_RUN_ECONOMIC_ACTION`

The normalized inputs are source-authentic Kraken public data. The result is internally hash-sealed, not independently validated, not exchange endorsed, and not permission to trade.

## Measured Result

- Fixed major-pair cohort: `20` pairs
- Development-selected periods: `10.0, 120.0, 30.0` days
- Diagnostic cohort improvement versus one globally strongest baseline: `1.446923%`
- Diagnostic pair-bootstrap CI95: `[0.069718%, 1.825902%]`
- Reviewer metric, mean pair improvement versus each pair's strongest baseline: `-0.287158%`
- Mean worst-baseline effect CI95: `[-0.009688027, 0.004328506]`
- Positive pair diagnostics: `11/20` (`55.0%`; required `60.0%`)
- Individually promoted after block CI and Holm correction: `0`
- Minimum leave-one-pair-out effect: `-0.003310801`

## Gate Checks

- `aggregate_pair_effect_positive`: `FAIL`
- `aggregate_bootstrap_ci95_lower_positive`: `FAIL`
- `minimum_positive_pair_fraction`: `FAIL`
- `leave_one_pair_out_minimum_positive`: `FAIL`
- `minimum_individually_promoted_pairs`: `FAIL`

## Duplicate Integrity

- Run identity: `d35d5d40937ea6b1e0f2d8794b729765ec89ec49c973131e734ba134882c8075`
- Scored computations with that identity: `2`
- Duplicate scored runs: `1`
- Matching evidence receipts: `true`
- Duplicate computations count as independent confirmation: `false`
- Identical protocol plus input hashes are now blocked before inference: `true`

## Runner Provenance

- Primary scoring runner hash: `41ac2dd109d7c890849e56c934f5a6fb8098b93e3111308321edf3afa28b78b8`
- Supplied locked runner hash: `dba7bd52f221980a87badec28e9c53e696590596e357dc854453fac58b8eaa67`
- Hashes match: `false`
- Exact primary source snapshot stored in the run: `false`
- Scope: current runner adds duplicate-input blocking and reviewer-report hardening; the external run is an implementation-version reproduction, not a bit-for-bit executable replay.

## Protocol Timestamp Erratum

- The immutable protocol records `2026-07-16T02:15:00Z` in `frozen_utc`.
- The intended value was `2026-07-16T01:15:00Z`; this was a one-hour UTC transcription error.
- Local filesystem chronology places protocol creation at `2026-07-16T01:12:45.5556419Z` and the primary summary at `2026-07-16T01:23:55.9023038Z`.
- The original protocol remains unchanged because its hash is already linked to the run.
- Scoring rules, inputs, numeric outputs, and the rejection decision are unchanged.

## What Would Unlock Promotion

1. One outside reviewer runs the blind kit without seeing the expected leaderboard.
2. The reviewer returns the summary, terminal manifest hash, environment receipt, and signed attestation.
3. A future prospectively sealed source window independently clears the same frozen gate.
4. Economic action remains disabled until those steps pass and operational risk controls are separately reviewed.
