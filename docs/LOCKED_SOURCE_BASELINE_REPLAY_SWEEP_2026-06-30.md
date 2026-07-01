# Locked Source Baseline Replay Sweep

Generated UTC: `2026-07-01T08:20:34.969692+00:00`

Locked source baseline replay sweep. This runs every ready local/uploaded measured source row from the geometry live source manifest through available source-conditioned replay adapters and compares candidates against the locked baselines for their lane. It includes an energy price-pressure proxy adapter so those rows are tested instead of blocked. This is source-conditioned replay evidence, not field validation, not realized savings, not a fixed-dollar frozen-delta sales claim, not live trading, and not a medical or addiction-treatment claim.

## Summary

- Manifest rows: `497`
- Ready rows: `313`
- Adapter-backed routes replayed: `313`
- Geometry routes replayed: `169`
- Energy proxy routes replayed: `144`
- Baseline comparisons: `1224`
- Candidate wins: `975`
- Loss/tie comparisons: `249`
- Estimated rows replayed: `7152281`
- Numeric samples read: `93596`
- Mean score delta: `0.118206`
- Best score delta: `0.421141`
- Replay chain SHA-256: `825b5b4090a944a6306caeac16a3fc583def8444d9dc232da864dbd627a30587`
- Field validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`

## Lane Scoreboard

| Lane | Routes | Baseline Comparisons | Wins | Rows | Numeric Samples | Mean Delta | Best Delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `wave_resonance_timing` | `147` | `588` | `588` | `2880414` | `44614` | `0.18595` | `0.388056` |
| `energy_price_pressure_proxy` | `144` | `567` | `338` | `2880414` | `44610` | `0.052908` | `0.421141` |
| `thermal_ventilation` | `8` | `24` | `24` | `441538` | `1451` | `0.118918` | `0.152459` |
| `branching_transport` | `11` | `33` | `13` | `695728` | `2200` | `0.016296` | `0.32329` |
| `optimal_curve_transport` | `3` | `12` | `12` | `254187` | `721` | `0.16296` | `0.258127` |

## Top Positive Comparisons

| Lane | Candidate | Baseline | Delta | Source |
| --- | --- | --- | ---: | --- |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `seasonal_naive` | `0.421141` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_O.000_runs_best_timeseries.csv__t.csv__22b46e9294.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `seasonal_naive` | `0.421141` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_Termius_best_timeseries.csv__t.csv__f51b9fb1ef.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `seasonal_naive` | `0.421141` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_STAGING_GLYPH_INGEST_20260129_082348Z_99_RAW_ORIGINALS_iCloud_O.000_runs_best_timeseries.csv__t.csv__b17a35f516.csv` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.388056` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/Data_sets__MER_T09_04.csv__641def4c59.csv` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.376833` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_O.000_runs_best_timeseries.csv__t.csv__22b46e9294.csv` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.374685` | `data/live_measured/eia/eia_latest.json` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.374153` | `data/live_measured/kraken_public/kraken_public_20260701T060342Z.json` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.367652` | `data/live_measured/fred/fred_20260701T060342Z.json` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.366614` | `data/live_measured/grants_gov/grants_gov_latest.json` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.365081` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_Termius_best_timeseries.csv__energy.csv__eb90fb4cc8.csv` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.364694` | `data/live_measured/bls/bls_20260701T060342Z.csv` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.363679` | `data/live_measured/kraken_public/kraken_public_latest.json` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.363174` | `data/live_measured/the_odds_api/the_odds_api_20260701T060342Z.json` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.359977` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/data/Data sets/EBA.txt` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.358283` | `data/live_measured/eia/eia_20260701T060342Z.json` |

## Claim Boundaries

- Allowed: source-conditioned replay claims with hashes, baselines, and metric names.
- Not allowed yet: field validation, realized savings, fixed-dollar frozen-delta value, live trading, or medical/addiction-treatment language.
- Unlock path: buyer/agency/lab supplies held-out operational data, incumbent baseline, acceptance metric, and economic conversion.
