# Current Proof Posture And Next Tests

Generated UTC: `2026-07-03`

This note is the short operating brief for the current LumenCore proof stack. It is meant to stop drift: use it before creating another dashboard, another grant claim, or another outreach email.

## What Is Strong Right Now

The strongest current technical story is narrow and real:

- Current internal champion: `kuramoto_phase_coupling`
- Label: `Kuramoto phase coupling`
- Lane: `wave_resonance_timing`
- Named baseline: `kalman_filter`
- Source-conditioned holdouts: `24`
- Wins vs named baseline: `24/24`
- Losses/ties vs named baseline: `0`
- Win rate: `100%`
- Mean delta vs baseline: `0.140668`
- Minimum delta vs baseline: `0.044697`
- One-sided sign-test p-value: `6e-08`
- Wilson 95% lower win-rate bound: `0.862024`
- Numeric samples read: `66,690`
- Estimated rows replayed in champion core: `2,506,267`
- Champion source systems: `energy_grid`, `macro_rates_labor`, `market_data`, `sports_market`
- Holdout chain SHA-256: `2227dd06869d292c82918d3f9cfab2b87cbe441cd44e398ec4a1024c6f5a655c`

Plain English: this is enough to say LumenCore has a strong internal replay champion and is ready to ask a buyer, lab, utility, or agency for a locked external field replay. It is not enough to say field validated or realized savings.

## Broader Live Breadth

The latest live-source maximizer shows:

- Enabled providers: `29`
- Measured providers: `25`
- Failed or thin providers: `4`
- Latest bounded measured rows: `1,326`
- Coverage: `86.21%`
- Bounded estimated annual opportunity surface: `$20,071,845,553.20`

Measured providers:

`AIRNOW`, `ALPACA`, `ALPHAVANTAGE`, `BEA`, `BLS`, `CENSUS`, `COINBASE_PUBLIC`, `COINGECKO_PUBLIC`, `EIA`, `FINNHUB`, `FRED`, `GRANTS_GOV`, `KRAKEN`, `KRAKEN_PUBLIC`, `MASSIVE`, `NASA`, `NOAA_NCEI`, `NWS_PUBLIC`, `OPEN_METEO_PUBLIC`, `SEC_PUBLIC`, `TREASURY_FISCAL_PUBLIC`, `TWELVE_DATA`, `USGS_WATER`, `WEBHOOK`, `WORLD_BANK_PUBLIC`.

Failed or thin providers:

`BINANCE_PUBLIC`, `EPA_AQS`, `NREL`, `THE_ODDS_API`.

Important distinction: the 25 measured providers are the broader live-breadth inventory. They do not automatically count as proof for the Kuramoto champion until each provider is promoted through a named baseline, normalized schema, locked metric, and replay manifest.

## Locked Replay Breadth

The locked source baseline replay sweep shows:

- Adapter-backed routes: `313`
- Baseline comparisons: `1,224`
- Candidate wins: `975`
- Candidate losses/ties: `249`
- Source count: `159`
- Numeric samples read: `93,596`
- Estimated rows replayed: `7,152,281`
- Mean score delta: `0.118206`
- Best score delta: `0.421141`
- Replay chain SHA-256: `825b5b4090a944a6306caeac16a3fc583def8444d9dc232da864dbd627a30587`

Safe claim: source-conditioned internal replay evidence exists across a broad locked benchmark sweep.

Unsafe claim: this proves realized savings, field validation, fixed frozen-delta pricing, live trading alpha, medical efficacy, or universal geometry superiority.

## Live Domain Proof Feed

The live domain proof feed is ready as a reviewer evidence layer:

- Feed-only deploy ready: `true`
- Required feeds ready: `12/12`
- Publishes config or secrets: `false`
- Service restart required: `false`
- Boundary: feed-only evidence publish, not field validation.

Use this as a credibility rail: it proves the public domain can show hash-verified evidence feeds, not that a buyer has accepted a savings claim.

## What This Is Worth Today

Today, the platform is worth pursuing as:

- a paid evidence review;
- a buyer-authorized field replay pilot;
- a grant-funded validation project;
- a narrow platform license around replay, provenance, and benchmark dashboards.

It is not ready for a fixed claim like "this frozen delta is worth $10,000" or "we saved $21B." Those become possible only after a buyer or external lab agrees on:

- the held-out operational dataset;
- the incumbent baseline;
- the acceptance metric;
- the replay window;
- the economic conversion factor;
- the pass/fail protocol;
- the report format they will accept.

## Next Highest-Impact Tests

Run these in order:

1. Leave-one-source-out replay on the Kuramoto champion.
2. Per-source residual metrics: MAE, RMSE, WAPE, residual bias, residual autocorrelation.
3. Direct phase diagnostics: circular phase error, phase-slip count, lock duration, recovery time, coherence.
4. Robustness perturbation: missingness, delayed samples, spikes, drift, regime split, bootstrap confidence intervals.
5. Promote one new measured provider at a time into the locked replay suite.
6. Clean manifest hygiene so package/runtime files stay in stress tests, not field-grade proof.
7. Fix or demote `BINANCE_PUBLIC`, `EPA_AQS`, `NREL`, and `THE_ODDS_API`.
8. Add SAM.gov after the safe key helper is run.
9. Add ISO/RTO and utility event windows for grid/energy buyer relevance.
10. Convert one top lane into a buyer-ready field replay ask with an external acceptance metric.

## Exact Claim Language To Use

Use:

> LumenCore currently has a hashable internal replay champion in the wave/resonance timing lane. Kuramoto phase coupling beat a named Kalman baseline on 24 of 24 source-conditioned holdouts, with 2.5M estimated rows replayed in the champion core and a broader 25-provider live-breadth inventory ready for staged promotion. The system is ready for buyer-authorized field replay, not yet field validated.

Avoid:

> field validated, guaranteed savings, realized savings, institutional trading alpha, medical treatment, universal geometry superiority, or fixed dollar value per frozen delta.

## Immediate Operator Command For SAM.gov

SAM.gov is structurally wired, but it still needs a local key entry before it can become measured breadth:

```powershell
cd C:\LumaTrader\INSTITUTIONAL_STACK_V2
pwsh -ExecutionPolicy Bypass -File .\tools\Set-SamApiKey.ps1 -Validate -SetUserEnv
```

After that succeeds, rerun the live-source maximizer and dollar ladder.
