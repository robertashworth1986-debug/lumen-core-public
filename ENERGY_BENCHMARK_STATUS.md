# LumenCore energy benchmark — research continuity checkpoint

**RESEARCH ONLY. Performance promotion: HOLD. Production deployment: NOT AUTHORIZED.**

This is the entry point for continuing the energy benchmark without losing the branch, evidence or negative findings. A successful preservation workflow publishes a research prerelease, not a production version and not a valuation claim.

## Verified published checkpoint — 2026-09-05

Research archive: https://github.com/robertashworth1986-debug/lumen-core-public/releases/tag/research-energy-20260905-584e88a0f376

The archive is published (not draft), marked prerelease and not promoted as the latest production version. Its 16 assets include nine original source/result archives, all 600 Stage 5 diagnostic records, source code, hashes and a recoverable Git-history bundle containing 2,444 reachable commits. An isolated offline restore and `git fsck --full` passed. This is not an audit of laptop/VPS-only history.

The original publication attempt failed after upload because draft lookup by tag failed. The same existing draft was subsequently verified and published by numeric release ID; nothing was overwritten and no scientific data were rescored to obtain success. The general publisher is repaired in the working branch. The original checkpoint snapshot is retained unchanged for traceability.

Published scientific checkpoint: `584e88a0f376ca016a085077047052d406081f98`. Publisher repair: `920e5146bb4294ffefb9b4c717c9efd74915b6ec`. Publication verification run: `33975030133`. Later closeout files document publication rather than changing the frozen scientific result.

Read `evidence/energy_continuity/CLOSEOUT_20260905.json`, `PUBLICATION_RECEIPT_20260905.json`, and `OFFLINE_RECOVERY_20260905.json` for exact receipts. Review remains in draft PR #215; continuity tracker #214 stays open for the next bounded batch. Main, DNS and production were not modified.

## Where to continue

- Cumulative review: https://github.com/robertashworth1986-debug/lumen-core-public/pull/215
- Open owner-assigned continuity tracker: https://github.com/robertashworth1986-debug/lumen-core-public/issues/214
- Working branch: `exp/energy-stage4-delayed-router-20260905`
- Publication workflow: `.github/workflows/energy-research-checkpoint.yml`
- Original source/result archive index: `evidence/energy_continuity/ARCHIVE_PLAN.json`
- Exact published tag, SHA, asset digests and execution lineage: the release's `CHECKPOINT_MANIFEST.json` and workflow `PUBLICATION_RECEIPT.json`.
- Findings and final read-back receipts added after execution live in `evidence/energy_continuity/`.

## Claim authority, newest first

Stage 5 is a same-origin missing-data engineering diagnostic on already examined 2025 observations. It cannot authorize a superiority claim. Its 600 records reuse historical outcomes across seeds; they are not 600 independent field experiments.

Stage 4 (`evidence/energy_stage4/FINDINGS_20260905.json`) scored 90/108 planned comparisons. No candidate/station/horizon cell passed all three comparators. The missing 46042 2025 source remains a hold, not a substituted station.

Stage 3 (`experiments/energy_multisource/stage3/FINDINGS_20260905.json`) documents exact-time and delayed-outcome corrections. Earlier geothermal percentages and zero-selected-loss claims must not be used without those corrections. Earlier artifacts are retained for audit, not reinstated as current claim authority.

No independent validation, generated-electricity gain, safe operating limits, causal reservoir benefit, revenue or valuation has been established by these releases.

## What the archive preserves

Nine original artifact ZIPs (222,287,455 bytes total) are checked against their exact SHA-256 digests. The publication adds Stage 5 results and tests, a research-code snapshot, an offline Git bundle of the checkpoint's full reachable ancestry, the archive plan, and a checksum manifest. The Git bundle does not establish that laptop/VPS-only history has been audited or recovered.

Nothing is promoted based on a green workflow alone. Archive verification, experiment completion, research performance and production authority are separate states. Published release assets are outside the Actions artifact retention lifecycle; they still depend on maintaining the repository/account and must not be treated as undeletable storage.

## Reproduce the next diagnostic

Using the research code snapshot and the preserved `energy-stage4-ci.zip`, extract that archive into `prior/`, then run from the code root:

```sh
python -m pip install numpy==2.3.5
python -m unittest discover -s experiments/energy_multisource/stage5 -p 'test_*.py' -v
python experiments/energy_multisource/stage5/run_stage5.py --prior prior --out replay-stage5
```

Verify `SHA256SUMS.txt` before using downloaded archives. Never fill missing future targets, select replacement data after scoring, or label reused 2025 data as untouched confirmation.

## Recover the checkpoint's Git history without overwriting another checkout

Create a new empty directory, initialize Git there, fetch `HEAD` from the downloaded `research-history.bundle`, then create a recovery branch at `FETCH_HEAD`. The bundle is a backup of remotely reachable checkpoint ancestry only; do not force-push it over another branch.

## Next acceptance gates

Review same-origin diagnostics, quantify clean-accuracy versus dropout tradeoffs, improve uncertainty calibration, and register an actually fresh evaluation period before scoring revised methods. Review registry/provenance compatibility and historical-script status before considering PR #215 for merge. A separate read-only laptop/VPS inventory is needed to resolve local-only history.

Every continuation must record its source commit, protocol, execution ID, result files, claim decision, publication/read-back status and next action in issue #214. Do not replace this with a promise of unattended background work.
