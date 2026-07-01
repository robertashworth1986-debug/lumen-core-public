# Reviewer Evidence Gate

Generated UTC: `2026-06-24T19:17:23.726159+00:00`

## Verdict

- Ready for reviewer packet: `True`
- Claim boundary: Reviewer-facing claims may cite live measured rows, hashes, and conservative readiness status. Do not present paper trades, synthetic-only benchmarks, generated visuals, estimated value surfaces, or legacy benchmark numbers as field validation, realized savings, trading profit, or award certainty.

## Live Evidence Promoted

- Enabled sources: 22
- Measured sources: 17
- Failed/thin sources: 5
- Total measured rows: 417
- Source truth rows: 23
- Source truth repaired from registry: `True`
- Estimated annual value surface: $10,650,192,942.00

### Reviewer-Safe Claims

- The stack currently maintains a hashable live-source measurement chain.
- The latest pass measured multiple public/private data-source surfaces and recorded snapshot hashes.
- Geometry families are wired to live-source replay queues but are not yet field-validation claims.

### Live Measured Sources

| Source | Sector | Rows | Snapshot | SHA-256 |
|---|---|---:|---|---|
| KRAKEN_PUBLIC | crypto_market | 25 | `data/live_measured/kraken_public/kraken_public_20260624T182429Z.json` | `80d0a0fa0bbfe4459e625f1e2136127eea0bd737367fa3ad72c607f0901e4c93` |
| COINGECKO_PUBLIC | crypto_market | 6 | `data/live_measured/coingecko_public/coingecko_public_20260624T182429Z.json` | `d847bd68c0edbd06826d0fb50b53b768b0c705fc1f60186321fde5a5cfb74f0c` |
| FINNHUB | market_data | 4 | `data/live_measured/finnhub/finnhub_20260624T182429Z.json` | `c9c317ff3ea3c124466769eaed8fa128cd25da5e8b6ec727052389cb4e7cdf8a` |
| ALPHAVANTAGE | market_data | 25 | `data/live_measured/alphavantage/alphavantage_20260624T182429Z.json` | `780dd74ca2a7eb5be90fb9cd821294e649d1e71aaedbdefeeedbac3f7f513707` |
| TWELVE_DATA | market_data | 25 | `data/live_measured/twelve_data/twelve_data_20260624T182429Z.json` | `a0224add0f9c32f6cf7d1295ca43ebb67d17d73855a934a3309bfb41ca3d7a4d` |
| MASSIVE | market_data | 3 | `data/live_measured/massive/massive_20260624T182429Z.json` | `27accc303bc2b1fb27b1184bfc28eb93e76191c956b61875c68d41d5a2be55f5` |
| FRED | rates | 24 | `data/live_measured/fred/fred_20260624T182429Z.json` | `aa9fdd9d8e1083ed6e1f884072ac39402e14668e59738bd79e05a892370dd3b3` |
| EIA | energy | 25 | `data/live_measured/eia/eia_20260624T182429Z.json` | `83423346bb467c11d87e03d75b78124792a0d62e58f93c13138609a5c18164c5` |
| BLS | labor | 25 | `data/live_measured/bls/bls_20260624T182429Z.json` | `7de82f4d7f48341820013e0c9ae826ac00b1047b1eaef1671fc9393ebf018b59` |
| NOAA_NCEI | weather | 11 | `data/live_measured/noaa_ncei/noaa_ncei_20260624T182429Z.json` | `bb625ab7852dc074a9ad208f5597d7cc80e5e66aa4ccf3ef6314c0a4b807e299` |
| USGS_WATER | water | 1 | `data/live_measured/usgs_water/usgs_water_20260624T182429Z.json` | `97490ed0b8e95b647bd077217415161395b650a5e08cd7b9095ae63356982859` |
| CENSUS | demographic | 1 | `data/live_measured/census/census_20260624T182429Z.json` | `509d698e7953737c1567deeb5e238810a8acd85d07ba14c1e36b9d683a94dad9` |
| BEA | macro | 13 | `data/live_measured/bea/bea_20260624T182429Z.json` | `4f70185867fd2df89fc21c5b717577714810d955b6ab20d148f7cbe131a0047e` |
| GRANTS_GOV | federal_opportunity | 25 | `data/live_measured/grants_gov/grants_gov_20260624T182429Z.json` | `6b171c8ee07f41a6da9ef3741af3a24f406cc46cc593e9ddbf3172781d0d0b3d` |
| WEBHOOK | internal | 1 | `data/live_measured/webhook/webhook_20260624T182429Z.json` | `c5677cef98ad5513056dd42fd186cd2ee3ed570a1fc35f3512da476922144b2b` |

## Quarantine

### Blocked Or Thin Sources

| Source | Status | Reason |
|---|---|---|
| BINANCE_PUBLIC | PROBE_FAILED_OR_THIN | http_error:{   "code": 0,   "msg": "Service unavailable from a restricted location according to 'b. Eligibility' in https://www.binance.com/en/terms. Please contact customer servic |
| NASA | PROBE_FAILED_OR_THIN | http_error:upstream connect error or disconnect/reset before headers. reset reason: connection timeout |
| NREL | PROBE_FAILED_OR_THIN | exception:URLError:<urlopen error [Errno 11001] getaddrinfo failed> |
| EPA_AQS | PROBE_FAILED_OR_THIN | http_error:{   "Header": [     {       "status": "Failed",       "request_time": "2026-06-24T14:24:54.987-04:00",       "url": "https://aqs.epa.gov/data/api/list/states?email=[REDA |
| THE_ODDS_API | PROBE_FAILED_OR_THIN | http_error:{"message":"API key is deactivated. This could be due to cancelation or a failed payment","error_code":"DEACTIVATED_KEY","details_url":"https://the-odds-api.com/liveapi/ |
| SAM_GOV | UNCONFIGURED | missing_env |

### Paper/Synthetic Rules

- Paper trades are internal calibration evidence only.
- Synthetic benchmarks are lab evidence only until paired with fresh live replay windows.
- Generated visuals are communication assets only, not engineering proof.
- Dollar surfaces are sizing/context estimates only until a buyer, baseline, and measured lift are validated.

### Legacy Sources

| Source | Classification | Exists | Reason |
|---|---|---:|---|
| DOE SBIR Phase I master draft | LEGACY_BENCHMARK_REVIEW_REQUIRED | True | Contains useful DOE positioning and historic benchmark language, but must be reconciled with the current live-source proof chain before reviewer use. |
| EchoLock early signal proof note | CONCEPT_POSITIONING_SAFE | True | Useful read-only resilience framing; proof snapshot language needs an artifact link before numeric or operational claims. |
| DoD agency alignment memo | AGENCY_POSITIONING_SAFE | True | Useful agency alignment language; not a performance proof by itself. |
| Master master dossier | ARCHIVE_REVIEW_REQUIRED | True | Contains historic PDFs, KPI CSVs, reports, and visuals that should be cited only after each claim is mapped to a current hashable artifact. |

## Geometry Gate

- Classification: `LIVE_WIRED_NOT_CLAIM_READY`
- Lanes: 12
- Families: 140
- Live-source measured count: 17
- Ready for live geometry claim: `False`
- Ready for real-dollar claim: `False`

| Rank | Lane | Live Wiring Score | Claim Ready | Champion Candidate |
|---:|---|---:|---:|---|
| 1 | time_series_model_routing | 159.24 | False | Fractal Brownian surface |
| 2 | stability_diagnostic | 114.48 | False | Markov blanket boundaries |
| 3 | optimal_curve_transport | 101.645 | False | Brachistochrone fastest-descent curve |
| 4 | market_signal_geometry | 78.38 | False | Order-book liquidity contours |
| 5 | wave_resonance_timing | 76.756 | False | Chladni nodal patterns |
| 6 | resource_aware_scheduling | 74.14 | False | Cicada prime-cycle scheduling |
| 7 | multi_agent_coordination | 70.58 | False | Bird V-formation or flocking |
| 8 | branching_transport | 66.442 | False | Crack propagation paths |

## Submission Rule

Use this gate as the first page of any grant, contract, LinkedIn, or investor evidence review. If a claim is not in `promote.live_measured_sources` or explicitly marked as concept/legacy, it should not be presented as proof.
