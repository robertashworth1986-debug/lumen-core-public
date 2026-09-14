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

### Legacy dashboard observations corrected September 14, 2026

`dashboard/update_compliance_progress.py` now reports file metadata only.
Its existing list format is retained, but statuses are
`artifact_present_unverified` or `no_usable_artifact_observed`; every item
explicitly keeps functional completion and compliance unverified. Empty files,
directories, symlinks, paths escaping the selected root, and unreadable metadata
cannot establish completion. The inventory does not read artifact contents.
Status publication uses an atomic replacement so a failed write preserves the
previous record.

`dashboard/orchestrator_watchdog.py` compares timezone-aware UTC timestamps,
observes only a bounded 64 KiB / 100-line error tail, and does not classify a
quiet or absent error log as a stalled process. Stale activity, future mtimes
beyond a two-second observation tolerance, and indicators in a recently
modified error tail call for inspection. Tail indicators are not an event
rate. Every report keeps process health and restart authority unverified;
logs alone do not identify a process or prove successful work. An optional
`--json-output` exports the same bounded observation. The alert reader rejects
stale, future-dated, malformed, and legacy watchdog records and never treats an
old inventory `complete` label as compliance acceptance.

The legacy `dashboard/self_heal_orchestrator.py` full-stack launch loop is
retired. Its former importable restart function fails explicitly, and its CLI
exits without starting a process or writing a successful-recovery record.
The existing runtime manager remains the operating path:

```powershell
code/ops/MANAGE_LOCAL_STACK.ps1 -Action status
```

That manager's status action may maintain its local process registry; it is
not a scientific validation or an authorization to change execution controls.
Any actual recovery must still establish current process identity, intended
stack group, runtime controls, and post-action health separately.

`dashboard/automate_luma_stack.ps1 -Python <intended-python-path>` now runs
only the three existing inventory/log collectors from its own directory.
Exit 0 means those observations were written; exit 2 means the watchdog
reported log issues; exit 1 means a collector failed. These outcomes do not
certify runtime health or compliance. The driver does not invoke example
proofs, alerts, recovery, or trades. PowerShell regression tests use harmless
stub collectors to verify success, diagnostic issues, failure, and path
independence.

`dashboard/generate_validation_proof.py` is now a compatibility entry point
for `run_ensemble_meta_strategy.py`. It requires the same explicit input and
cost arguments, delegates to that single corrected evaluator, and creates no
`proof_live` artifacts. The old one-row/empty-result always-long example is
not validation evidence. See `docs/HARMONIC_VALIDATION_PROTOCOL.md` for the
versioned diagnostic and synthetic replay instructions. The historical
`code/validation_proof_pack.py` helper and retained historical files are not
retroactively reclassified.

### Supervisor process ownership corrected September 14, 2026

The existing `code/luma_supervisor.py` now observes Windows process objects with
zero-timeout waits and creation-time identity. It requests only synchronization
and limited-query rights. Windows PID observation never sends a signal. Unknown
or inaccessible process state is preserved as unknown and cannot trigger a
replacement launch. A changed creation identity prevents a reused PID from
inheriting the earlier observation.

The compatibility adoption reader uses CIM and Windows command-line parsing,
checks the expected arguments, interpreter and stack path, and rejects ambiguous
matches. The current interpreter's Windows venv redirector is recognized only
with its observed parent/child relationship, known base interpreter and matching
remaining arguments. Unsupported interpreter relationships remain review holds.
Unreadable inventory cannot establish absence and authorize a new launch; a
separately identified exact match can still be observed. Adopted processes are
external observations and are never terminated by `Service.stop`.

A held operating-system file lock protects the supervisor's singleton state.
The bounded legacy PID record remains readable and is preserved if its PID is
present or unknown. A malformed record stops recovery for review. The lock file
is retained after release so concurrent processes cannot lock different inodes.
Import and `--help` no longer create runtime directories or acquire the lock.

The supervisor no longer clears shared ports or calls `taskkill` during startup.
Startup, polling and publication failures clean up owned direct child handles;
one cleanup failure does not skip the remaining handles. Failed termination
remains explicit and preserves the process reference. This does not establish
ownership or verified cleanup of a complete descendant process tree, including
children behind a Windows redirector. No automatic foreign-process takeover or
full-tree recovery is claimed.

`supervisor_health.json` now declares `process_presence_only`, `all_running`,
per-service observation and ownership, and `application_health_verified=false`.
The legacy `all_healthy` field is false because process presence is insufficient
to certify application work. Consumers must not interpret that false field as
proof the platform is down; endpoint behavior, source freshness, artifact
progress and execution controls require their own evidence.

Isolated regression checks include real disposable Windows child processes,
concurrent lock acquisition, base and venv command identity, PID reuse,
unreadable inventory, access denial, partial startup and shutdown failures.
No running canonical supervisor was restarted and this source repair is not a
runtime-activation receipt. The earlier signal-zero experiment did not reproduce
termination of its disposable child; the repair follows the documented API
semantics and the now-passing passive-observation checks, not a claimed crash.

API references: [Python process signals](https://docs.python.org/3.11/library/os.html#os.kill),
[Windows process handles](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess),
[zero-timeout waits](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject),
[creation times](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes),
and [Windows command parsing](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-commandlinetoargvw).

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
