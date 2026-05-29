# Changelog

All notable changes to LumenCore™ / lumen-core.ai are recorded here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### In Progress
- Watchdog guard for live executor drift prevention
- Multi-TF alpha map auto-refresh on dashboard

---

## [2026-05-29] — Live Executor Stability + Paper Trader Purge

### Fixed
- **Live executor duplicate-child false positive** — Rewrote `_is_duplicate_child_executor()` in `live_executor.py`. Old PID-recycling edge case caused executor to self-block on launch. New logic uses env-marker + parent-PID + commandline triple-check.
- **Paper trader PnL pollution** — Added `paper_enabled` guard to `alpaca_paper_orchestrator.py`. Orchestrator now reads `runtime_control.json` on startup and exits cleanly if `paper_enabled=False`, preventing stale -$37k paper PnL from bleeding into dashboards.
- **Stale env var on executor relaunch** — `RUN_LIVE_COMPOUNDING_STACK.ps1` now clears `LUMA_LIVE_EXECUTOR_ROOT_PID` before each executor spawn.

### Changed
- `paper_trade_state.json` reset to clean state: `pnl=$0`, `status=DISABLED`, `equity=$100k`
- Old 88,859-entry paper ledger archived to `paper_trade_ledger_archive_20260529.jsonl`
- `seed_validation_readout.json` `paper_trade_reported_pnl_usd` zeroed

### Infra
- Live Kraken executor confirmed running: equity $313–$314, 8 open positions, heartbeat updating every ~2 min
- Risk gate correctly blocking new entries at 84.9% portfolio heat (threshold: 35%)

---

## [2026-05-27] — Kraken Multi-TF Alpha Map + UI Tab Execution

### Added
- **Kraken Multi-TF Alpha Map** (`RUN_KRAKEN_MULTI_TF_ALPHA_MAP.ps1`) — scans 711 pairs across 4 timeframes (1h, 4h, 1d, 1w), scores alpha candidates, renders live on 3D globe
- **UI tab execution confirm modal** — approval hub now shows trade confirmation dialog with TXID capture before firing live orders

### Fixed
- Kraken nonce scale and top-10 API pagination
- VPS Scout API Python 3.9 compatibility fixes
- Dashboard root path recovery after VPS redeploy

---

## [2026-05-26] — Evidence Publish + Master Universe V2

### Added
- **Evidence publish dataset polish gate** — row vs dataset validation before publishing to hash chain
- **Master Universe V2** — extended to 500+ symbols with mega Yahoo Finance integration + extended ML models

### Fixed
- Evidence publish `row_count vs dataset_count` mismatch gate

---

## [2026-05-24] — LinkedIn Visual Parity + Live Mode Alignment

### Added
- LinkedIn visual parity profile pack — automated profile card generation
- Universal orchestrator cadence alignment — live mode heartbeat synchronization across all services

### Fixed
- Live mode flag propagation from `runtime_control.json` to all orchestrators

---

## [2026-05-23] — Full Live Trading Stack Hardening

### Added
- **Approval guard** — buy-only cap and sell-balance pre-check before order submission
- **Cash depletion sell mode** — automatic pivot to liquidation-only when cash drops below threshold
- **Peak rollover** — equity peak tracking for drawdown calculations
- **Alpha gate watch-only runtime toggle** — real-time enable/disable of alpha scanning without restart
- **Sell lock-in cooldown** — prevents rapid re-entry after a forced sell

### Fixed
- `profitability_net_edge_gate` — net edge threshold was using gross instead of net after fees
- `conviction_sizing` — position size was ignoring edge score on high-conviction signals

---

## [2026-05-22] — Healthcare Access Gate + Mission Control Artifacts

### Added
- Healthcare pipeline access gate with institutional role enforcement
- Mission Control support artifacts: domain health checks, service dependency mapping
- Staples "go-time" launchers and Office.com fallback routing

---

## [2026-05-21] — Healthcare Pipeline + Dashboard Commit

### Added
- Healthcare access institutional pipeline (capacity prediction, access scoring)
- Dashboard live commit from pipeline run results

---

## [2026-05-20] — Investor Heartbeat + Grants Pack

### Added
- Investor heartbeat surface and progress tracker
- Grant apply profile bootstrap and package gates
- Master valuation multi-engine licensing and auto-refresh
- Site reach blueprint grant amplification pack
- Explainer voice masterpitch hardening

### Fixed
- Alpaca paper executor sys.path bootstrap
- Data breadth ZIP probe and diagnostics noise filter

---

## [2026-05-18] — Grant Submit Lanes

### Added
- Simpler Grants URL routing and direct submit lane
- LinkedIn OAuth bootstrap + status diagnostics

---

## [2026-05-17] — Grant Hunter + VPS Push Hardening

### Fixed
- Grant hunter submit guidance fix — form field mapping for USASpending.gov
- VPS push: exclude `venv/`, `__pycache__/`, archive staging from upload
- Outreach biometric fallback and LinkedIn key hydration

---

## [2026-05-16] — Public Truth Policy + Application Context

### Added
- Public truth-only policy: dashboards only surface verified, hash-chained data
- Application context resolver and filler hardening for grant auto-fill
- SKIPS grant autofill pack

### Fixed
- Grant submission deadline US date parse (MM/DD vs DD/MM)
- Orchestrator path resolution after VPS redeploy

---

## [2026-05-15] — VPS Dashboard Mirror Sync

### Added
- VPS dashboard mirror sync key and target path registry
- Trader uncapped runtime semantics — removes artificial cap on compounding stack

---

## [2026-05-14] — Symbol Flip Learning

### Added
- Symbol flip learning integration — executor learns which symbols trend-reverse vs trend-continue

---

## [2026-05-12] — Edge Proof Gate + Live Run Continuity

### Added
- Edge proof gate before live executor: requires minimum verified edge before orders fire
- Live run continuity after VPS redeploy: XRP pin and edge gate preserved
- Dashboard package modernization

### Fixed
- Dashboard JSON NaN parse error (Infinity values from Python floats)
- Dashboard filemode parity (chmod alignment between stack and VPS)

---

## [2026-05-11] — Impact Assumptions + Git Sync

### Added
- Impact assumptions config — non-hardcoded savings projections for grant evidence
- One-click VPS elevation arglist
- Git sync and context bootstrap

---

## [2026-05-09] — Kraken Nonce + Top-10 API

### Fixed
- Kraken nonce scale causing signature rejection on high-frequency calls
- Top-10 alpha API pagination

---

## [2026-05-01 through 2026-04-01] — Foundation Build

### Built from scratch (solo, zero funding)
- 7 strategy generations (Gen4 → Gen7 + Hybrid V2) all producing real Kraken TXIDs
- LumenCore™ harmonic intelligence architecture — patent pending
- Full institutional ops stack: mission control, approval hub, evidence chain, alpha globe
- Cross-sector optimization engine: energy, finance, defense, healthcare, smart cities
- 711-pair Kraken scanner with multi-timeframe scoring
- Federal brief + daemon heartbeat proof system
- DOE SBIR Phase I documentation package
- Cumberland Science Museum, FSI, InlineLighting pilot program frameworks
- Hardware IP: curved motherboards, honeycomb EV batteries, nature-flow robotics (drafted)
