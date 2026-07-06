# Locked Source Baseline Replay Sweep

Generated UTC: `2026-07-06T01:04:35.793990+00:00`

Locked source baseline replay sweep. This runs every ready local/uploaded measured source row from the geometry live source manifest through available source-conditioned replay adapters and compares candidates against the locked baselines for their lane. It includes an energy price-pressure proxy adapter so those rows are tested instead of blocked. This is source-conditioned replay evidence, not field validation, not realized savings, not a fixed-dollar frozen-delta sales claim, not live trading, and not a medical or addiction-treatment claim.

## Summary

- Manifest rows: `500`
- Ready rows: `349`
- Adapter-backed routes replayed: `349`
- Geometry routes replayed: `187`
- Energy proxy routes replayed: `162`
- Baseline comparisons: `2303`
- Candidate wins: `1540`
- Loss/tie comparisons: `763`
- Estimated rows replayed: `7154095`
- Numeric samples read: `98056`
- Mean score delta: `0.099291`
- Best score delta: `0.680913`
- Replay chain SHA-256: `a0bb9ff93c7b046bad7c6484ffa93f8b2ae5f96f9d070fd5d6ff3afbbb6b3024`
- Field validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`

## Lane Scoreboard

| Lane | Routes | Baseline Comparisons | Wins | Rows | Numeric Samples | Mean Delta | Best Delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `energy_price_pressure_proxy` | `162` | `1552` | `801` | `2881321` | `48971` | `0.057444` | `0.680913` |
| `wave_resonance_timing` | `165` | `660` | `660` | `2881321` | `48975` | `0.19377` | `0.388056` |
| `branching_transport` | `11` | `55` | `43` | `695728` | `69` | `0.120934` | `0.331672` |
| `thermal_ventilation` | `8` | `24` | `24` | `441538` | `41` | `0.103805` | `0.150738` |
| `optimal_curve_transport` | `3` | `12` | `12` | `254187` | `0` | `0.206883` | `0.259176` |

## Top Positive Comparisons

| Lane | Candidate | Baseline | Delta | Source |
| --- | --- | --- | ---: | --- |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `particle_filter` | `0.680913` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/data/live_fetched/fred_fx_gbpusd.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `particle_filter` | `0.655278` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/data/live_fetched/fred_fx_eurusd.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `lightgbm` | `0.635821` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_O.000_runs_best_timeseries.csv__t.csv__22b46e9294.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `lightgbm` | `0.635821` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_Termius_best_timeseries.csv__t.csv__f51b9fb1ef.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `lightgbm` | `0.635821` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_STAGING_GLYPH_INGEST_20260129_082348Z_99_RAW_ORIGINALS_iCloud_O.000_runs_best_timeseries.csv__t.csv__b17a35f516.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `xgboost` | `0.626577` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_The_master_master_dossier_LumenCore_KPI_Run_2000.csv__score.csv__1a55521dbd.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `xgboost` | `0.619218` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_O.000_runs_best_timeseries.csv__t.csv__22b46e9294.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `xgboost` | `0.619218` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_Termius_best_timeseries.csv__t.csv__f51b9fb1ef.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `xgboost` | `0.619218` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_STAGING_GLYPH_INGEST_20260129_082348Z_99_RAW_ORIGINALS_iCloud_O.000_runs_best_timeseries.csv__t.csv__b17a35f516.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `particle_filter` | `0.611074` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/data/live_fetched/fred_vix.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `random_forest_regression` | `0.584755` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_O.000_runs_best_timeseries.csv__t.csv__22b46e9294.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `random_forest_regression` | `0.584755` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_Termius_best_timeseries.csv__t.csv__f51b9fb1ef.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `random_forest_regression` | `0.584755` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_STAGING_GLYPH_INGEST_20260129_082348Z_99_RAW_ORIGINALS_iCloud_O.000_runs_best_timeseries.csv__t.csv__b17a35f516.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `particle_filter` | `0.575591` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/data/live_fetched/av_fx_chfusd.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `particle_filter` | `0.573832` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/data/live_fetched/av_fx_jpyusd.csv` |

## Claim Boundaries

- Allowed: source-conditioned replay claims with hashes, baselines, and metric names.
- Not allowed yet: field validation, realized savings, fixed-dollar frozen-delta value, live trading, or medical/addiction-treatment language.
- Unlock path: buyer/agency/lab supplies held-out operational data, incumbent baseline, acceptance metric, and economic conversion.
