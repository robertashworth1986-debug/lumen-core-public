# Luma Production Context

Updated: June 11, 2026 (America/Chicago)

## Mission

Build Luma as an evidence-calibrated, multi-horizon decision platform that
continuously measures market state, per-symbol temporal edge, rare-event
precursors, operational readiness, and opportunity deadlines, and only
delegates actions through auditable risk gates.

The platform must optimize for reproducibility, capital preservation,
traceability, and measured edge. A heuristic score, simulation result, or
paper profit is not authorization to place a live order.

## Source Of Truth

- Repository: `C:\LumaTrader\INSTITUTIONAL_STACK_V2`
- Public domain: `https://lumen-core.ai`
- VPS application root: `/opt/lumencore`
- Global runtime control: `config/runtime_control.json`
- Account runtime controls: `config/account_runtime_*.json`
- Automatic-buy control: `config/autobuy.json`
- Public gateway: `code/luma_experience_gateway.py`
- Dashboard refresh: `code/dashboard_unified_refresh.py`
- Paper execution loop: `code/multi_exchange_paper_ticker.py`
- Symbol awareness: `code/execution/luma_symbol_awareness_daemon.py`
- Kraken spike scanner: `code/kraken_spike_hunter_live.py`
- Kraken history collector: `code/ops/collect_kraken_hourly_history.py`
- Timing-edge model: `code/ops/build_symbol_timing_edge_model.py`
- Runtime safety assertion: `code/ops/assert_runtime_safety.py`
- Canonical VPS installer: `code/deploy/deploy_vps.sh`
- Windows deployment entrypoint: `deploy/PUSH_TO_VPS.ps1`

## Current Execution State

The system is intentionally in paper/shadow mode:

- Global mode: `paper`
- Live orders: disabled
- Paper execution: enabled
- Automatic buying: disabled
- Moonshot execution: disabled
- Timing-edge execution authorization: false

Legacy launchers, account rollout, and the live executor fail closed unless the
global live arm and all downstream checks agree. Do not bypass these checks.

## Live-Order Release Gates

Real-money execution remains blocked until all of the following are documented
and passing:

1. At least 26 weeks of clean history for the intended symbol and interval.
2. A materially sized untouched holdout period.
3. Positive out-of-sample expectancy after fees and realistic slippage.
4. Stable results across multiple market regimes and walk-forward windows.
5. Maximum drawdown, concentration, liquidity, and stale-data limits pass.
6. Exchange credentials have least privilege, withdrawal disabled, and tested
   kill-switch behavior.
7. Order sizing, duplicate-order prevention, reconciliation, and restart
   recovery pass controlled canary tests.
8. Runtime safety assertion passes immediately before process start.
9. A human records the approved account, capital cap, symbols, and expiry time
   for the live authorization.

Current timing coverage is approximately 30 days. Candidate timing patterns are
research observations only and do not satisfy the release gates.

## Market Intelligence

The Kraken collector continuously builds public hourly history for the ranked
pair universe. The timing model uses walk-forward train/test evaluation,
Bayesian shrinkage, confidence intervals, daily-low/high labels, forward
maximum favorable excursion, drawdown, and rare-event rates.

The awareness daemon exposes timing context but does not let it modify execution
scores while the model is shadow-only. Moonshot output is explicitly labeled
`heuristic_unvalidated` and `execution_authorized=false`.

The intended progression is:

1. Observe and collect.
2. Build hypotheses.
3. Validate out of sample.
4. Shadow decisions against live market data.
5. Paper trade with full execution costs.
6. Run capped live canaries only after every release gate passes.

## VPS Services

The canonical deployment manages these systemd units:

- `luma-gateway`
- `luma-dashboard-refresh`
- `luma-paper-ticker`
- `luma-symbol-awareness`
- `luma-kraken-history`

The VPS was recovered from a full disk. A legacy ledger created under a literal
Windows-style Linux path was compressed and archived under:

`/opt/lumencore/out/archive/legacy_windows_path_20260608`

Operational logs and high-volume scene simulation output now rotate. Keep at
least 20% disk space free and investigate any recurrence of Windows drive
letters beneath `/opt/lumencore`.

## Deployment And Verification

Run deployment from the repository root:

```powershell
.\deploy\PUSH_TO_VPS.ps1
```

Local safety and regression checks:

```powershell
.\.venv\Scripts\python.exe code\ops\assert_runtime_safety.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_production_repairs.py
git diff --check
```

Public checks:

```powershell
Invoke-RestMethod https://lumen-core.ai/health
Invoke-RestMethod https://lumen-core.ai/api/snapshot
```

Healthy public output must be based on fresh artifact heartbeats. A stale
supervisor heartbeat is nonauthoritative and must not make the domain appear
healthy.

## Grant Factory

The frozen benchmark remains 673 series. Measured artifact breadth is currently
2,586 datasets, 2,479 parseable datasets, and 14,390,128 rows. Applications
must use measured context instead of repeating the frozen benchmark as if it
were the current total.

The queue contains 128 records, but 98 previously approved records are stale
and quarantined. Only one current path is actionable: the NSF Project Pitch.

The NSF workflow is stage-aware:

- Submit a Project Pitch first.
- A full proposal requires an invitation.
- An active SAM registration is required for the full proposal.
- Known full-proposal deadlines: July 27, 2026; November 4, 2026; March 4, 2027.
- The current Phase I budget ceiling is enforced at $305,000.
- Placeholder content blocks readiness.

Official sources:

- NSF Project Pitch: https://seedfund.nsf.gov/apply/project-pitch/
- NSF full proposal: https://seedfund.nsf.gov/apply/full-proposal/
- NSF solicitation: https://seedfund.nsf.gov/solicitation-proposal/
- DOE SBIR: https://science.osti.gov/sbir/Funding-Opportunities/FY-2026
- NIST SBIR: https://www.nist.gov/tpo/small-business-innovation-research-program-sbir

## Identity, Patent, And Compliance

SAM registration status and expiration have not been verified from an
authenticated SAM.gov record. A local application pack created November 4,
2025 contains identifiers but no registration expiration date.

The available patent screenshots verify that a utility nonprovisional
application was filed and paid on July 25, 2025. They do not contain an Office
Action, missing-parts notice, or response deadline. The exact patent deadline
and any available extension must be determined from the latest USPTO
correspondence, not inferred from the filing anniversary.

Official sources:

- SAM entity registration: https://sam.gov/entity-registration
- SAM checklist: https://sam.gov/sites/default/files/2024-11/entity-checklist.pdf
- USPTO application status: https://www.uspto.gov/patents/apply/checking-application-status/check-filing-status-your-patent-application
- USPTO extension guidance: https://www.uspto.gov/web/offices/pac/mpep/s710.html

## Credentials

Do not read credentials from source files, iCloud documents, command history, or
registry exports at runtime. Use environment variables or a dedicated secret
manager. Rotate any credential that has ever been stored in plaintext,
especially exchange and OpenAI keys. Exchange keys must not have withdrawal
permission.

## Operator Constraints

- No performance or profit guarantee is valid.
- Do not present paper equity as realized profit.
- Do not arm live trading to compensate for missing evidence.
- Do not submit grants or legal filings with placeholders.
- Do not infer legal deadlines from draft files or payment receipts.
- Browser-assisted submission requires an authenticated user session and final
  human review before any irreversible submission.

## 2026-07-05 Public Domain Reset

Use this as the current public-surface baseline before sending reviewers,
buyers, investors, or grant contacts to `lumen-core.ai`.

- The live domain reviewer proof feeds were rebuilt and deployed from
  `.deploy_stage/live_domain_proof_feeds_20260705T060243Z`.
- `dashboard/data/live_domain_deployment_feed.json` now reports
  `LIVE_DOMAIN_HASH_VERIFIED`, with 14 of 14 required reviewer proof feeds
  matching on the live domain and 0 required stale/missing feeds.
- `https://lumen-core.ai/proof_to_pilot.html` is live and should be the
  validation/buyer-replay destination.
- Public `/proof/` directory browsing was disabled on the VPS nginx config.
  `/proof/` now redirects to `/proof_to_pilot.html`; direct `/proof/*` output
  browsing returns 404. The deployment template in `deploy/VPS_DEPLOY.sh` was
  patched so a future broad deploy does not re-enable autoindex.
- The VPS root disk was recovered from 100% usage to about 70% usage by clearing
  rebuildable caches and rotating/compressing the oversized paper ticker ledger:
  `/opt/lumencore/out/execution/multi_exchange_paper_ticker_ledger_20260705T062152Z.jsonl.gz`.
- The active paper ticker ledger was recreated empty at
  `/opt/lumencore/out/execution/multi_exchange_paper_ticker_ledger.jsonl`.

Current public pages that passed smoke check:

- `https://lumen-core.ai/`
- `https://lumen-core.ai/operator_home.html`
- `https://lumen-core.ai/mission_control.html`
- `https://lumen-core.ai/quant_lab.html`
- `https://lumen-core.ai/grants.html`
- `https://lumen-core.ai/proof_to_pilot.html`

Current public claim posture:

- Allowed: internal replay evidence, locked baseline replay counts, source
  breadth, accepted-metric proxy diagnostics, and paid pilot scoping language.
- Allowed: bounded estimated value opportunity under stated assumptions.
- Not allowed: field-validated savings, guaranteed ROI, live trading profit,
  fixed dollar price per frozen delta, medical/safety claims, or universal
  geometric superiority.
- Strongest current public wording:
  "LumenCore is ready for buyer-authorized historical replay: held-out data,
  incumbent baseline, pre-registered metric, and economic conversion only if
  the replay passes."
