# Luma Operator Context

Generated UTC: `2026-07-01T15:38:38.076910+00:00`
Context SHA-256: `9e69257c0087ca8dd03baa28f7e3df5439eb6edee6d6e1b2a8dd9a1ca3e0b99f`

## Current Truth

- Champion: `kuramoto_phase_coupling` vs `kalman_filter`
- Holdout wins: `24/24`
- Mean delta: `0.140668`
- Weakest delta: `0.044697`
- Estimated rows replayed: `2506267`
- Source systems in champion replay: `4`
- Expanded sweep source systems: `8`
- Expanded sweep comparisons: `975/1224` wins
- Expanded sweep win rate: `79.66%`
- Expanded sweep rows/samples: `7152281` rows / `93596` numeric samples
- Expanded field-grade source hygiene passed: `false`
- Buyer field replay request ready: `true`
- Field validation claim allowed: `false`
- Real dollar savings claim allowed: `false`

Kuramoto phase coupling is the current internal champion because it beat kalman_filter on 24/24 source-conditioned holdouts across 4 champion-replay source systems. The broader live-source universe currently shows 19 measured providers and 186 mapped source files/feeds available for additional benchmark promotion. That is strong enough to request a buyer-authorized field replay, but it is not field validation or realized dollar savings yet.

The strongest current story is not 'everything wins.' It is that one champion family has a clear source-conditioned replay win, with the wave/resonance timing lane standing out as the cleanest high-volume internal lane. Energy price pressure is promising but mixed; branching is honest negative evidence where classic baselines still compete.

## Live Domain

- State: `LOCAL_READY_DOMAIN_NOT_VERIFIED_OR_STALE`
- Reviewer ready: `false`
- Required feeds matched: `11/12`
- Stale/missing required feeds: `1`

## Source Breadth

- Runtime-bound keys: `31`
- Measured enabled sources: `23/23`
- Measured sectors: `17/17`
- Fresh HTTP measured sources: `25/29`
- Fresh HTTP measured rows: `823`
- Live-context replay rows: `150`
- Live-context candidate wins vs named baselines: `4`
- Live-context snapshot chain: `60a692c3c47d37ba3051122bc04f08f173fa47cd6476e0b290a801b70133e537`
- Latest measured providers in safe ping: `22`
- Latest blocked/thin providers in safe ping: `6`

Provider gaps to fix:
- `ALPACA`: `NO_LATEST_STATUS`; next: Add this provider to the latest safe ping/harvest adapter so key-ready becomes measured, not merely configured.
- `BINANCE_PUBLIC`: `PROBE_FAILED_OR_THIN`; next: Do not fight the location restriction; use Kraken/CoinGecko or another allowed market source instead.
- `EPA_AQS`: `PROBE_FAILED_OR_THIN`; next: Refresh the EPA AQS email/key pair; the latest probe reports invalid email/key.
- `KRAKEN`: `NO_LATEST_STATUS`; next: Add this provider to the latest safe ping/harvest adapter so key-ready becomes measured, not merely configured.
- `NREL`: `PROBE_FAILED_OR_THIN`; next: Retry DNS/network and use a known NREL developer endpoint; current failure is name resolution.
- `SAM_GOV`: `UNCONFIGURED`; next: Enable only if this source is needed for the current proof lane, then bind the expected API key.
- `THE_ODDS_API`: `PROBE_FAILED_OR_THIN`; next: Reactivate or replace the key before using sports-market data in current proof claims.
- `WORLD_BANK_PUBLIC`: `PROBE_FAILED_OR_THIN`; next: Review the redacted probe note, repair the adapter or key, then rerun the provider harvest.

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

Operate LumenCore as a measurement-first proof-to-pilot platform. The standard is not hype; the standard is reviewer-safe proof that survives hostile reading. Every improvement claim must name its source data, baseline, metric, replay rules, code commit, hashes, negative results, claim boundary, and next external validation gate. Treat the current internal champion as a strong lead, not a universal law: Kuramoto phase coupling is 24/24 on the locked champion holdouts, and the expanded sweep currently shows source-conditioned strength across eight lanes/systems, while still preserving mixed and negative evidence. Prioritize one narrow paid field replay over broad claims: buyer-approved held-out data, incumbent baseline, acceptance metric, economic conversion, and a signed result. Ship only canonical, secret-free proof feeds to the public domain, keep dashboards beautiful but honest, preserve this context after every pass, and convert the next action toward a lab, agency, or system owner saying yes to a held-out replay.
