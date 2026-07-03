# Champion Expanded Metric Rollup

Generated UTC: `2026-07-03T00:12:57.281477+00:00`
Rollup SHA-256: `afddb05e3dbe5f04eb8513427866bcb026bea8fff8825d84bff4627ae062881e`

## Plain English

The strongest current story is not 'everything wins.' It is that one champion family has a clear source-conditioned replay win, with the wave/resonance timing lane standing out as the cleanest high-volume internal lane. Energy price pressure is promising but mixed; branching is honest negative evidence where classic baselines still compete.

## Evidence Summary

- Champion: `kuramoto_phase_coupling`
- Named baseline: `kalman_filter`
- Holdout wins: `24/24`
- Lanes: `5`
- Strong lanes: `3`
- Total baseline comparisons: `1224`
- Total candidate wins: `975`
- Overall locked-lane win rate: `79.66%`
- Estimated rows replayed: `7152281`
- Numeric samples read: `93596`
- Source systems replayed: `8`
- Source files replayed: `159`
- Manifest source entries: `159`
- Field-grade source hygiene passed: `false`
- Suspicious route results: `2`
- Measured sources: `25/29`
- Latest bounded measured rows: `823`

## Lane Scoreboard

| Lane | Status | Wins | Comparisons | Win Rate | Rows | Claim Gate |
|---|---|---:|---:|---:|---:|---|
| `wave_resonance_timing` | `STRONG_INTERNAL_REPLAY_WIN` | `588` | `588` | `100.0%` | `2880414` | internal locked replay only; requires buyer-authorized holdout for field validation |
| `thermal_ventilation` | `STRONG_INTERNAL_REPLAY_WIN` | `24` | `24` | `100.0%` | `441538` | internal locked replay only; requires buyer-authorized holdout for field validation |
| `optimal_curve_transport` | `PROMISING_SMALL_SAMPLE` | `12` | `12` | `100.0%` | `254187` | internal locked replay only; requires buyer-authorized holdout for field validation |
| `energy_price_pressure_proxy` | `MIXED_OR_BASELINE_STILL_COMPETITIVE` | `338` | `567` | `59.61%` | `2880414` | internal locked replay only; requires buyer-authorized holdout for field validation |
| `branching_transport` | `MIXED_OR_BASELINE_STILL_COMPETITIVE` | `13` | `33` | `39.39%` | `695728` | internal locked replay only; requires buyer-authorized holdout for field validation |

## Top Dataset Champion Cards

| System | Lane | Candidate | Wins | Comparisons | Win Rate | Rows | Source |
|---|---|---|---:|---:|---:|---:|---|
| `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `7` | `7` | `100.0%` | `50` | `alphavantage_20260701T060342Z.json` |
| `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `7` | `7` | `100.0%` | `50` | `alphavantage_latest.json` |
| `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `7` | `7` | `100.0%` | `48` | `fred_20260701T060342Z.json` |
| `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `7` | `7` | `100.0%` | `48` | `fred_latest.json` |
| `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `7` | `7` | `100.0%` | `4` | `finnhub_20260701T060342Z.csv` |
| `maritime_ais` | `optimal_curve_transport` | `brachistochrone_descent` | `4` | `4` | `100.0%` | `249999` | `930-data-export.csv` |
| `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `4` | `4` | `100.0%` | `249999` | `LumenLab__crawler_out_master_index.csv__4839a4e25d.csv` |
| `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `4` | `4` | `100.0%` | `249999` | `full_beast_leaderboard.csv` |
| `energy_grid` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `4` | `4` | `100.0%` | `249999` | `Net_generation_United_States_all_sectors_annual (1).csv` |
| `energy_grid` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `4` | `4` | `100.0%` | `191506` | `Net_generation_for_all_sectors (1).csv` |
| `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `4` | `4` | `100.0%` | `160080` | `LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_The_master_master_dossier_LumenCore_KPI_Run_2000.csv__R.csv__06d36a49d5.csv` |
| `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `4` | `4` | `100.0%` | `160080` | `LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_The_master_master_dossier_LumenCore_KPI_Run_2000.csv__a.csv__11dbf13ef1.csv` |

## Claim State

- Live-domain reviewer ready: `true`
- Field-validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`
- Fixed frozen-delta price claim allowed: `false`

## Source Hygiene

Some replay rows appear to come from package/runtime paths. Keep them as stress/noise tests, but exclude them from field-grade live-system proof until the source manifest is cleaned.

## Missing / Next Source Families

- SAM.gov contract opportunity API
- EPA AQS with valid email/key pairing
- NREL or OpenEI energy lab endpoints
- ISO/RTO operations feeds: PJM, MISO, ERCOT, CAISO, SPP, NYISO, ISO-NE, TVA/BPA
- utility outage or reliability event windows
- NOAA SWPC space weather and NWS alerts
- MarineCadastre AIS / NOAA PORTS for HarborSentinel lanes

## Next 10 Actions

- Promote wave_resonance_timing as the first paid field-replay candidate.
- Run leave-one-source-out on the current champion.
- Run residual autocorrelation on each lane, not only aggregate scores.
- Clean the replay manifest so package/runtime files stay in stress tests and cannot inflate live-system proof.
- Expand thermal_ventilation with real HVAC/cooling or facility traces.
- Expand energy_price_pressure_proxy with ISO/RTO load, price, outage, and forecast windows.
- Keep branching_transport visible as negative evidence until it beats min-cost/Steiner/MST baselines.
- Add SAM.gov opportunity feed after a valid key is configured.
- Fix EPA AQS and NREL credentials/endpoints or demote them from enabled sources.
- Ask EPRI/TVA/utility lab for a held-out dataset, baseline, acceptance metric, and cost conversion.

## Boundary

Champion expanded metric rollup. This summarizes internal replay lanes, live-source breadth, baseline comparisons, and claim gates. It does not prove external field validation, realized savings, fixed frozen-delta pricing, medical efficacy, grant award certainty, or live trading performance.
