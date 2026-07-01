# Luma Operator Context

Generated UTC: `2026-07-01T11:51:01.521182+00:00`
Context SHA-256: `bc34b259ccfe2805a0d44a95b9e4649eca523cc3b98fbc46d44e50862f249f69`

## Current Truth

- Champion: `kuramoto_phase_coupling` vs `kalman_filter`
- Holdout wins: `24/24`
- Mean delta: `0.140668`
- Weakest delta: `0.044697`
- Estimated rows replayed: `2506267`
- Source systems in champion replay: `4`
- Buyer field replay request ready: `true`
- Field validation claim allowed: `false`
- Real dollar savings claim allowed: `false`

Kuramoto phase coupling is the current internal champion because it beat kalman_filter on 24/24 source-conditioned holdouts across 4 champion-replay source systems. The broader live-source universe currently shows 17 measured providers and 186 mapped source files/feeds available for additional benchmark promotion. That is strong enough to request a buyer-authorized field replay, but it is not field validation or realized dollar savings yet.

## Live Domain

- State: `LIVE_DOMAIN_HASH_VERIFIED`
- Reviewer ready: `true`
- Required feeds matched: `12/12`
- Stale/missing required feeds: `0`

## Source Breadth

- Runtime-bound keys: `31`
- Measured enabled sources: `23/23`
- Measured sectors: `17/17`
- Latest measured providers in safe ping: `15`
- Latest blocked/thin providers in safe ping: `7`

Provider gaps to fix:
- `ALPACA`: `NO_LATEST_STATUS`; next: Add this provider to the latest safe ping/harvest adapter so key-ready becomes measured, not merely configured.
- `BINANCE_PUBLIC`: `PROBE_FAILED_OR_THIN`; next: Do not fight the location restriction; use Kraken/CoinGecko or another allowed market source instead.
- `EIA`: `PROBE_FAILED_OR_THIN`; next: Rerun the EIA probe and promote existing local EIA CSV/API pulls; 502 appears upstream, not proof failure.
- `EPA_AQS`: `PROBE_FAILED_OR_THIN`; next: Refresh the EPA AQS email/key pair; the latest probe reports invalid email/key.
- `KRAKEN`: `NO_LATEST_STATUS`; next: Add this provider to the latest safe ping/harvest adapter so key-ready becomes measured, not merely configured.
- `NASA`: `PROBE_FAILED_OR_THIN`; next: Rerun with a longer timeout and a smaller endpoint before declaring NASA unavailable.
- `NREL`: `PROBE_FAILED_OR_THIN`; next: Retry DNS/network and use a known NREL developer endpoint; current failure is name resolution.
- `SAM_GOV`: `UNCONFIGURED`; next: Enable only if this source is needed for the current proof lane, then bind the expected API key.
- `THE_ODDS_API`: `PROBE_FAILED_OR_THIN`; next: Reactivate or replace the key before using sports-market data in current proof claims.

## Replay Lanes

| Lane | Wins | Comparisons | Win Rate | Rows | Mean Delta |
|---|---:|---:|---:|---:|---:|
| `wave_resonance_timing` | 588 | 588 | 1.0 | 2880414 | 0.18595 |
| `energy_price_pressure_proxy` | 338 | 567 | 0.59612 | 2880414 | 0.052908 |
| `thermal_ventilation` | 24 | 24 | 1.0 | 441538 | 0.118918 |
| `branching_transport` | 13 | 33 | 0.393939 | 695728 | 0.016296 |
| `optimal_curve_transport` | 12 | 12 | 1.0 | 254187 | 0.16296 |

## Dollar Gate

- Bounded estimated hourly signal: `$4520.0`
- Bounded estimated annual signal: `$39595200.0`
- Blocked context-only annual surface: `$52288496940.0`
- Safe line: Use bounded estimated avoided-cost signal language only; realized savings require a buyer-authorized field replay with locked baseline, held-out data, acceptance metric, and economic conversion.

## First Outreach Lane

- Buyer: `EPRI AI for Power / Incubatenergy Labs`
- Action: Send one manually reviewed inquiry through the official challenge/contact path.
- Send gate: Operator must review recipient, footer, opt-out text, and final page before sending.

## Next 10 Actions

- Keep generated render-QA folders uncommitted unless a specific packet requires them.
- Run the focused proof tests before every commit.
- Promote EIA, NASA, NREL, EPA_AQS, Alpaca, and Kraken provider rows only after their latest pings are measured.
- Run direct phase-slip, circular error, and amplitude-error diagnostics for the Kuramoto champion.
- Run residual autocorrelation and calibration checks on the promoted source-system holdouts.
- Run leave-one-source-out replay before claiming broader source generalization.
- Keep live-domain hash verification green after every proof feed update.
- Use EPRI AI for Power / Incubatenergy as the first manual paid-pilot outreach lane.
- Ask for buyer-approved held-out data, incumbent baseline, pass/fail metric, and cost conversion.
- Do not claim field validation, realized savings, live trading edge, or fixed frozen-delta price until external gates close.

## Long-Arc Operator Prompt

Operate LumenCore as a measurement-first proof-to-pilot platform. Every improvement claim must name its source data, baseline, metric, replay rules, hashes, negative results, claim boundary, and next external validation gate. Prioritize one narrow paid field replay over broad hype: buyer-approved held-out data, incumbent baseline, acceptance metric, economic conversion, and a signed result. Ship only canonical, secret-free proof feeds to the public domain, keep dashboards honest, and preserve this context after every pass.
