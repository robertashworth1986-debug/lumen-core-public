# WhiteHole and WhiteHoleLab Audit

As of: `2026-08-02T14:01:36Z`

## Bottom Line

WhiteHole is useful as historical custody, continuity, and reproducibility
infrastructure. WhiteHoleLab is an early read-only market-diagnostic prototype
plus a historical website prototype. Neither currently establishes forecasting
skill, alpha, outage prevention, realized savings, field performance, or buyer
acceptance.

There is no separately observed "White Whole Lab" product or repository. In
this workspace, that phrase refers to `C:/WhiteHoleLab`, which contains the
nested `WhiteHole` archive.

The current governed LumenCore repository should remain the product and reviewer
front door. WhiteHole artifacts may support provenance after source, hash, and
claim-boundary checks; they should not be presented as current performance
evidence.

## Observed State

| Surface | Observation | Implication |
|---|---|---|
| `C:/WhiteHole` | Path is absent | Legacy defaults and scheduled-task actions that use this path cannot reach the observed archive |
| `C:/WhiteHoleLab` | 61,520 files; about 8.96 GiB | Large historical lab/archive tree, not a small deployable product |
| `C:/WhiteHoleLab/WhiteHole` | 24,178 files; about 7.99 GiB | Observed location of the historical WhiteHole archive |
| `C:/WhiteHoleLab/engine/LUMENCORE_REALITY` | Clean local Git worktree at commit `4d9f0f11d920082ed28dffc9d4af1f95ef2718cf`; last commit `2025-12-24` | Reproducible historical snapshot, but stale relative to the governed platform |
| WhiteHoleLab universe output | Latest work folder is `work_20251220_225712` | No current market or prospective evidence |
| WhiteHole freeze | Latest retained freeze ZIP is `WHITEHOLE_FREEZE_20260717T084702Z.zip`; its observed SHA-256 matches its sidecar | Valid custody receipt for that retained bundle only |
| WhiteHole freeze inventory | 70 historical freeze IDs: 66 manifests, 70 SHA-256 sidecars, and 1 retained `WHITEHOLE_FREEZE_*.zip`; 1 bundle is hash-verified and 69 source ZIPs are absent | Sidecars and manifests do not substitute for missing source bundles |
| E-drive premium mirror before repair | 40 ZIPs, about 13.30 GB; newest mirrored ZIP observed `2026-05-11` | Root-path drift had left the premium mirror stale |
| E-drive premium mirror after repair | Run `20260802T110829Z` inspected 675 files and copied 82; the July 17 freeze is present | Manifest and summary SHA-256 values match the run ledger; no source or destination file was deleted |

## Scheduled Tasks

The observed WhiteHole scheduled tasks are disabled. Their actions still target
scripts under the absent `C:/WhiteHole` root. `WhiteHole-Freeze`,
`WhiteHole-Maintain`, and `WhiteHole-WeeklyEvidence` also have nonzero last-task
results.

Do not re-enable or redirect those tasks as a maintenance shortcut. The maintain
lane can invoke operating-system updates, and legacy watchdog behavior has been
superseded by the governed local observer. Any repair requires a bounded change
plan, exact target-path verification, and action-time human approval.

## Research-Code Review

`whitehole_lab.py` and `whitehole_universe.py` are compact read-only Kraken
experiments. They fetch public OHLC data, compute heuristic coherence and
fracture measures, simulate geometric-Brownian-motion paths, and emit hashed
reports or proof packs. This is a useful demonstration of deterministic artifact
packaging and public-data intake.

The code is not a validated forecasting or trading system:

- no frozen train, validation, and test chronology;
- no accepted named baseline comparison;
- thresholds and quantiles are derived from the same observed window being
  summarized;
- the universe ranking score is an ad hoc combination of coherence, fracture,
  and liquidity;
- Monte Carlo paths are scenarios, not calibrated predictive intervals;
- no multiple-testing control, prospective settlement, or independent evaluator;
- no focused test suite or current run receipt was observed.

Three implementation defects also limit proof-pack completeness and state
consistency:

- the ticker-key fallback in `whitehole_universe.py` iterates over candidate
  mappings but performs no comparison or assignment, so every missing exact key
  is silently skipped;
- `manifest.json` is written before `report.pdf` is produced, so the report is
  appended to the in-memory file list but is absent from the saved manifest.
- the result row recomputes `state_now` from coherence thresholds alone and
  ignores the emitted fracture state, so a fractured observation can be
  mislabeled `FLOW`, `STRAIN`, or `OVERLOAD` instead of `FRACTURE`.

Accordingly, WhiteHole coherence scores and watchlist ranks must remain
descriptive diagnostics. They are not alpha, expected return, savings, or
promotion evidence.

## Website Review

`C:/WhiteHoleLab/LumenWeb/site` is a January 2026 prototype, not the current
public-site source. It contains an example canonical URL, a placeholder form
endpoint, embedded personal contact data, and unsupported outage-prevention and
instant-payback language. It must not be deployed or copied into the governed
public site without a full evidence and privacy rewrite.

One private-configuration file is also present in the lab tree. Its contents
were not opened for this audit. Treat the complete archive as private by
default and never bulk-publish it.

## What To Preserve

1. Hash sidecars, manifests, freeze receipts, and the clean historical Git
   snapshot as provenance evidence.
2. Read-only public-data collection and deterministic proof-pack construction as
   implementation history.
3. Whitehole/blackhole language only as the already-bounded source/sink routing
   metaphor, never as exotic physics or energy creation.

## What To Use Now

Use the current LumenCore reviewer front door, source-native whitepaper, V3
prospective custody protocol, ProofLock opportunity-operations lane, and bounded
HyperCore V8 preflight. HyperCore remains a buyer-data validation candidate; it
is not a promoted champion and has no independent performance or economic
receipt.

## Safest Next Action

Keep WhiteHole frozen as an archive. The premium-mirror script now resolves both
the historical and observed roots and has refreshed the E-drive mirror with a
hashed receipt. Next, inventory retained versus missing bundles explicitly and
move only reviewer-relevant, hash-verified artifacts into the governed LumenCore
evidence map. Do not revive legacy tasks, deploy the old site, or promote the
heuristic market ranks.
