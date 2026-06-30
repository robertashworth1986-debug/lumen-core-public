# Locked Source Baseline Replay Sweep

Generated UTC: `2026-06-30T01:30:19.417822+00:00`

Locked source baseline replay sweep. This runs every ready local/uploaded measured source row from the geometry live source manifest through available source-conditioned replay adapters and compares candidates against the locked baselines for their lane. It includes an energy price-pressure proxy adapter so those rows are tested instead of blocked. This is source-conditioned replay evidence, not field validation, not realized savings, not a fixed-dollar frozen-delta sales claim, not live trading, and not a medical or addiction-treatment claim.

## Summary

- Manifest rows: `498`
- Ready rows: `317`
- Adapter-backed routes replayed: `317`
- Geometry routes replayed: `170`
- Energy proxy routes replayed: `147`
- Baseline comparisons: `1229`
- Candidate wins: `982`
- Loss/tie comparisons: `247`
- Estimated rows replayed: `7289287`
- Numeric samples read: `89438`
- Mean score delta: `0.115431`
- Best score delta: `0.421141`
- Replay chain SHA-256: `4f846b97193dc20cbc58fc14ace1179ffe84ad0277ede796f6bc136f13e2842c`
- Field validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`

## Lane Scoreboard

| Lane | Routes | Baseline Comparisons | Wins | Rows | Numeric Samples | Mean Delta | Best Delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `wave_resonance_timing` | `150` | `600` | `600` | `2950964` | `42535` | `0.182131` | `0.388056` |
| `energy_price_pressure_proxy` | `147` | `567` | `339` | `2950964` | `42531` | `0.050111` | `0.421141` |
| `thermal_ventilation` | `8` | `24` | `24` | `441538` | `1451` | `0.122474` | `0.156928` |
| `branching_transport` | `10` | `30` | `11` | `693681` | `2200` | `0.003764` | `0.242542` |
| `optimal_curve_transport` | `2` | `8` | `8` | `252140` | `721` | `0.140153` | `0.258127` |

## Top Positive Comparisons

| Lane | Candidate | Baseline | Delta | Source |
| --- | --- | --- | ---: | --- |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `seasonal_naive` | `0.421141` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_O.000_runs_best_timeseries.csv__t.csv__22b46e9294.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `seasonal_naive` | `0.421141` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_Termius_best_timeseries.csv__t.csv__f51b9fb1ef.csv` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `seasonal_naive` | `0.421141` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_STAGING_GLYPH_INGEST_20260129_082348Z_99_RAW_ORIGINALS_iCloud_O.000_runs_best_timeseries.csv__t.csv__b17a35f516.csv` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.388056` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/Data_sets__MER_T09_04.csv__641def4c59.csv` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.381557` | `data/live_measured/coingecko_public/coingecko_public_20260629T184753Z.csv` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.381124` | `data/live_measured/fred/fred_latest.json` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.377041` | `data/live_measured/nasa/nasa_latest.json` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.376833` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_O.000_runs_best_timeseries.csv__t.csv__22b46e9294.csv` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.367568` | `data/live_measured/coingecko_public/coingecko_public_latest.json` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.365983` | `data/live_measured/finnhub/finnhub_20260629T184753Z.json` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.365081` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_LumenHybrid_VAULT_WhiteHole__SOURCE_OF_TRUTH_Termius_best_timeseries.csv__energy.csv__eb90fb4cc8.csv` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.359977` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/data/Data sets/EBA.txt` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.355723` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/clean_data/LumenLab__crawler_out_timeseries_C_STAGING_GLYPH_INGEST_20260129_082348Z_99_RAW_ORIGINALS_iCloud_O.000_runs_best_timeseries.csv__t.csv__b17a35f516.csv` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.34706` | `data/live_measured/nasa/nasa_20260629T184753Z.json` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | `0.345174` | `C:/LumaTrader/INSTITUTIONAL_STACK_V2/data/live_fetched/fred_2yr_yield.csv` |

## Claim Boundaries

- Allowed: source-conditioned replay claims with hashes, baselines, and metric names.
- Not allowed yet: field validation, realized savings, fixed-dollar frozen-delta value, live trading, or medical/addiction-treatment language.
- Unlock path: buyer/agency/lab supplies held-out operational data, incumbent baseline, acceptance metric, and economic conversion.
