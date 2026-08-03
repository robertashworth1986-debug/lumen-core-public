# Champion Expanded Metric Rollup

Generated UTC: `2026-07-13T23:45:54.089608+00:00`
Rollup SHA-256: `de1b489624442406cf74d76df0cdd5130a6cb5df45db1f018340b19ec74d02c9`

## Plain English

The current story is not 'everything wins.' The wave/resonance timing lane is the cleanest source-conditioned timing result, but no lane currently clears the configured high-volume row gate. Energy price pressure and branching preserve substantial non-win evidence where classic baselines remain competitive.

## Evidence Summary

- Champion: `kuramoto_phase_coupling`
- Named baseline: `kalman_filter`
- Holdout wins: `24/24`
- Lanes: `5`
- Strong lanes: `0`
- Promising small-sample lanes: `3`
- Total baseline comparisons: `2861`
- Total candidate wins: `1458`
- Total candidate non-wins: `1403`
- Overall locked-lane win rate: `50.96%`
- Estimated rows replayed: `96209`
- Numeric samples read: `127053`
- Source systems replayed: `8`
- Source files replayed: `202`
- Manifest source entries: `202`
- Field-grade source hygiene passed: `false`
- Suspicious route results: `1`
- Measured sources: `25/29`
- Latest bounded measured rows: `2580`

## Lane Scoreboard

| Lane | Status | Wins | Comparisons | Win Rate | Rows | Claim Gate |
|---|---|---:|---:|---:|---:|---|
| `wave_resonance_timing` | `PROMISING_SMALL_SAMPLE` | `756` | `756` | `100.0%` | `46303` | internal locked replay only; requires buyer-authorized holdout for field validation |
| `thermal_ventilation` | `PROMISING_SMALL_SAMPLE` | `42` | `42` | `100.0%` | `1631` | internal locked replay only; requires buyer-authorized holdout for field validation |
| `optimal_curve_transport` | `PROMISING_SMALL_SAMPLE` | `4` | `4` | `100.0%` | `0` | internal locked replay only; requires buyer-authorized holdout for field validation |
| `branching_transport` | `MIXED_SMALL_SAMPLE` | `47` | `75` | `62.67%` | `1973` | internal locked replay only; requires buyer-authorized holdout for field validation |
| `energy_price_pressure_proxy` | `MIXED_SMALL_SAMPLE` | `609` | `1984` | `30.7%` | `46302` | internal locked replay only; requires buyer-authorized holdout for field validation |

## Top Dataset Champion Cards

| System | Lane | Candidate | Wins | Comparisons | Win Rate | Rows | Source |
|---|---|---|---:|---:|---:|---:|---|
| `energy_grid` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `16` | `16` | `100.0%` | `369` | `Daily_U.S._nuclear_capacity_outage (1).csv` |
| `energy_grid` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `16` | `16` | `100.0%` | `369` | `Daily_U.S._nuclear_capacity_outage.csv` |
| `energy_grid` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `16` | `16` | `100.0%` | `369` | `Daily_U.S._nuclear_capacity_outage (1).csv` |
| `energy_grid` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `16` | `16` | `100.0%` | `369` | `Daily_U.S._nuclear_capacity_outage.csv` |
| `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `16` | `16` | `100.0%` | `100` | `alphavantage_20260713T192646Z.json` |
| `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `16` | `16` | `100.0%` | `100` | `alphavantage_latest.json` |
| `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `16` | `16` | `100.0%` | `29` | `Net_generation_United_States_all_sectors_annual.csv` |
| `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `16` | `16` | `100.0%` | `1` | `930-data-export (1).json` |
| `weather_climate` | `branching_transport` | `leaf_veins` | `5` | `5` | `100.0%` | `3` | `NOAA_ncdc api.txt` |
| `water_hydrology` | `branching_transport` | `leaf_veins` | `5` | `5` | `100.0%` | `1` | `usgs_water_20260713T192646Z.csv` |
| `maritime_ais` | `branching_transport` | `leaf_veins` | `5` | `5` | `100.0%` | `0` | `support_list.json` |
| `macro_rates_labor` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `4` | `4` | `100.0%` | `16042` | `fred_DGS10.csv` |

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
