# Worktree and Validation Audit - 2026-07-01

## Purpose

This note preserves the current operator state after auditing the repo, proof feeds, tests, and live source gaps. It is meant to stop drift: future work should extend the canonical proof stack, not create another parallel dashboard or make unverified claims.

## Git State

- Repo audited: `C:\LumaTrader\INSTITUTIONAL_STACK_V2`
- Branch: `codex/live-domain-proof-feed-bundle`
- Remote: `origin/codex/live-domain-proof-feed-bundle`
- Latest pushed commit: `3770aca Expose live source readiness proof feeds`
- Worktree state at audit time: clean
- Nested repo scan under `C:\LumaTrader`: only `INSTITUTIONAL_STACK_V2` found, clean

If an editor reports hundreds of pending changes, treat that as stale UI state or another workspace until `git status --short` proves otherwise.

## Health Check

Focused proof/feed tests passed:

```text
42 passed
```

Test scope:

- live domain deployment feed
- live domain proof feed deploy bundle
- champion metric gauntlet
- dollar claim gate
- live source measurement maximizer
- field validated dollar claim ladder
- geometry live wiring matrix
- geometry champion of champions

## Current Public Proof State

- Live domain state: `LIVE_DOMAIN_HASH_VERIFIED`
- Reviewer-ready public proof feed: true
- Required reviewer feeds matched remotely: `12/12`
- Required stale or missing remote feeds: `0`

This is public deployment verification. It is not field validation.

## Current Internal Champion

- Family: `kuramoto_phase_coupling`
- Label: Kuramoto phase coupling
- Named baseline: `kalman_filter`
- Source-conditioned holdout wins: `24/24`
- Holdout win rate: `1.0`
- Mean delta vs named baseline: `0.140668`
- Weakest delta vs named baseline: `0.044697`
- Estimated rows replayed: `2506267`
- Champion replay source-system count: `4`
- Broader measured provider count: `17`
- Manifest unique source/file count: `186`
- Manifest benchmark-ready rows: `313`

Reviewer-safe claim: this is a strong internal, hash-backed, source-conditioned replay result that justifies a buyer-authorized field replay request.

Blocked claims:

- field validation
- realized dollar savings
- fixed value per frozen delta
- live/autonomous trading edge
- grant-award certainty

## Current Live Source Status

Configured providers: `24`

Measured providers:

- AIRNOW
- ALPACA
- ALPHAVANTAGE
- BEA
- BLS
- CENSUS
- COINGECKO_PUBLIC
- FINNHUB
- FRED
- GRANTS_GOV
- KRAKEN
- KRAKEN_PUBLIC
- MASSIVE
- NASA
- TWELVE_DATA
- USGS_WATER
- WEBHOOK

Failed, thin, or missing:

- BINANCE_PUBLIC: region restriction; replace with Kraken/CoinGecko or another allowed market source
- EIA: read timeout; retry smaller endpoint and promote local EIA CSV evidence
- EPA_AQS: invalid email/key response; refresh account/key pair
- NOAA_NCEI: SSL handshake timeout; retry and add NOAA/NWS fallback
- NREL: DNS/name-resolution failure; retry known developer endpoint
- SAM_GOV: missing/disabled; bind key only if needed for federal opportunity evidence
- THE_ODDS_API: deactivated key; renew only if sports-market calibration matters

## Highest-Value Missing Source Families

Priority source families that would strengthen live breadth and buyer credibility:

- ISO/RTO grid feeds: PJM, MISO, ERCOT, CAISO, SPP, NYISO, ISO-NE, BPA, TVA
- Energy reliability/outage feeds: DOE OE-417, FERC/EQR, EIA EBA, EIA nuclear outage, EIA 860/923
- Weather and space weather: NOAA NCEI, NOAA SWPC, NWS API, Open-Meteo fallback
- Environment: EPA AQS, AirNow, OpenAQ
- Maritime/harbor: MarineCadastre AIS, NOAA PORTS, USCG notices, paid AIS if license allows
- Infrastructure/cyber: CISA KEV, NVD, Censys/Shodan only within terms

## First Buyer Lane

Top lane: EPRI AI for Power / Incubatenergy Labs.

Reason: it is aligned with grid AI validation, buyer-authorized replay, and external technical review. The safe ask is not "buy the platform"; the safe ask is "approve a held-out dataset, baseline, metric, and cost conversion so we can run a no-control replay."

Send rule: do not bulk-send. Send one reviewed message at a time.

## Next 10 Concrete Actions

1. Keep the active work on `mission_control.html`, `grants.html`, `quant_lab.html`, and canonical `dashboard/data/*.json` feeds.
2. Re-run focused proof tests before each commit.
3. Fix EIA first using local EIA CSVs plus smaller API endpoints.
4. Refresh EPA AQS credentials and re-probe.
5. Add NOAA/NWS fallback so weather does not block on NCEI timeout.
6. Add TVA/PJM/MISO/CAISO/ERCOT/SPP/NYISO/ISO-NE public feeds as grid credibility boosters.
7. Run leave-one-source-out replay before claiming broader source generalization.
8. Ask EPRI/TVA/EPB/ORNL/TAEBC for buyer-approved held-out data, incumbent baseline, acceptance metric, and economic conversion.
9. Keep dollar claims in bounded estimated language until external validation closes.
10. Preserve this continuity note after each material pass.

## Operator Rule

The platform should become boringly trusted: source, baseline, metric, replay rule, hash, negative result, claim boundary, and next validation gate. That is the route from impressive internal evidence to paid pilots.
