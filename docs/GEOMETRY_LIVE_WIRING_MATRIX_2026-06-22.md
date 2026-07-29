# Geometry Live Wiring Matrix

Generated UTC: `2026-07-29T13:48:58.512822+00:00`

## Summary

- Lanes: 12
- Families: 140
- Implementations present: 35
- Frozen generated executions: 30
- Source-conditioned replay receipts: 4
- Field-validated families: 0
- Fresh measured sources: 24
- Fresh failed/thin sources: 4
- Total measured rows: 17081
- EIA status: `MEASURED` with 250 rows
- Claimable annual value: $0.00
- Context-only modeled source surface: $22,495,647,588.00
- Lanes ready for direct measured replay build: 3
- Lanes ready for source-conditioned synthetic stress build: 4
- Qualified direct-source links: 10
- Qualified conditioning-source links: 12
- Context-only measured-source links: 46
- Top live replay source-map cards: 5
- Top replay cards ready for direct measured build: 2
- Top replay cards ready for conditioned simulation: 2
- Top replay measured source links: 33
- Ready for live geometry claim: `false`
- Ready for real-dollar claim: `false`
- Kraken live execution allowed: `false`
- Boundary: Measured source availability alone is context, not task compatibility or family execution. Direct measured replay, source-conditioned synthetic stress, frozen generated execution, and field validation are separate gates. This matrix is not field validation, realized savings, award certainty, or trading profit.

## Top Live Replay Source Map

| Rank | Lane | Candidate | Best Baseline | Direct | Conditioned | Context | Direct Ready |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | `optimal_curve_transport` | `brachistochrone_descent` | `minimum_jerk_curve` | none | none | KRAKEN_PUBLIC, COINGECKO_PUBLIC, FRED, GRANTS_GOV, EIA | `false` |
| 2 | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | EIA_GRID_VALIDATION | none | EIA, FRED, KRAKEN_PUBLIC, NOAA_NCEI, NASA | `true` |
| 3 | `branching_transport` | `leaf_veins` | `minimum_spanning_tree` | none | EIA, NWS_PUBLIC, OPEN_METEO_PUBLIC | NOAA_NCEI, USGS_WATER, WEBHOOK | `false` |
| 4 | `thermal_ventilation` | `thermal_plume_convection` | `straight_duct` | none | EIA, NWS_PUBLIC, OPEN_METEO_PUBLIC | NOAA_NCEI | `false` |
| 5 | `time_series_model_routing` | `fractal_brownian_surface` | `` | EIA_GRID_VALIDATION, FRED, BLS, KRAKEN_PUBLIC, TWELVE_DATA, ALPHAVANTAGE | none | EIA, BEA, CENSUS, NOAA_NCEI, FINNHUB, MASSIVE | `true` |

Each row separates direct measured replay from source-conditioned synthetic stress. Neither is a live performance claim; promotion still requires a frozen lane replay, uncertainty bounds, and claim-gate approval.

## Proof Build Priority Queue

### 1. time_series_model_routing

- Score: 131.24
- Measured sources: EIA_GRID_VALIDATION, EIA, FRED, BEA, BLS, CENSUS, NOAA_NCEI, KRAKEN_PUBLIC, FINNHUB, TWELVE_DATA, ALPHAVANTAGE, MASSIVE
- Direct measured replay sources: EIA_GRID_VALIDATION, FRED, BLS, KRAKEN_PUBLIC, TWELVE_DATA, ALPHAVANTAGE
- Source-conditioned synthetic stress sources: none
- Blocked sources: none
- Generated champion: `none`
- Proof-value champion: `beast_algo_echo_stack`
- First live replay: walk-forward forecasting and regime-drift replay across macro, weather, and market proxies
- Safe claim: Direct-source readiness requires a task-compatible observed outcome and an executable family implementation. Source-conditioned simulations remain synthetic. Neither is field validation, realized savings, award certainty, or a profit claim.

### 2. market_signal_geometry

- Score: 55.38
- Measured sources: KRAKEN_PUBLIC, FINNHUB, TWELVE_DATA, ALPHAVANTAGE, MASSIVE, COINGECKO_PUBLIC
- Direct measured replay sources: KRAKEN_PUBLIC, TWELVE_DATA, ALPHAVANTAGE
- Source-conditioned synthetic stress sources: none
- Blocked sources: KRAKEN, BINANCE_PUBLIC
- Generated champion: `none`
- Proof-value champion: `beast_strategy_breakout`
- First live replay: paper-only walk-forward replay with fees, slippage, drawdown, and abstention controls
- Safe claim: Direct-source readiness requires a task-compatible observed outcome and an executable family implementation. Source-conditioned simulations remain synthetic. Neither is field validation, realized savings, award certainty, or a profit claim.

### 3. wave_resonance_timing

- Score: 51.756
- Measured sources: EIA_GRID_VALIDATION, EIA, FRED, KRAKEN_PUBLIC, NOAA_NCEI, NASA
- Direct measured replay sources: EIA_GRID_VALIDATION
- Source-conditioned synthetic stress sources: none
- Blocked sources: none
- Generated champion: `kuramoto_phase_coupling`
- Proof-value champion: `beast_algo_cross_asset_resonance`
- First live replay: oscillatory-window replay comparing Kuramoto, PLL, Kalman, FFT, and ARIMA under identical frozen windows
- Safe claim: Direct-source readiness requires a task-compatible observed outcome and an executable family implementation. Source-conditioned simulations remain synthetic. Neither is field validation, realized savings, award certainty, or a profit claim.

### 4. thermal_ventilation

- Score: 47.764
- Measured sources: EIA, NWS_PUBLIC, OPEN_METEO_PUBLIC, NOAA_NCEI
- Direct measured replay sources: none
- Source-conditioned synthetic stress sources: EIA, NWS_PUBLIC, OPEN_METEO_PUBLIC
- Blocked sources: NREL
- Generated champion: `thermal_plume_convection`
- Proof-value champion: `rayleigh_benard_cells`
- First live replay: load-plus-ambient thermal replay comparing plume/cellular ventilation against straight-duct baselines
- Safe claim: Direct-source readiness requires a task-compatible observed outcome and an executable family implementation. Source-conditioned simulations remain synthetic. Neither is field validation, realized savings, award certainty, or a profit claim.

### 5. branching_transport

- Score: 40.442
- Measured sources: EIA, NWS_PUBLIC, OPEN_METEO_PUBLIC, NOAA_NCEI, USGS_WATER, WEBHOOK
- Direct measured replay sources: none
- Source-conditioned synthetic stress sources: EIA, NWS_PUBLIC, OPEN_METEO_PUBLIC
- Blocked sources: NREL
- Generated champion: `leaf_veins`
- Proof-value champion: `crack_propagation_paths`
- First live replay: critical-flow and failure-propagation replay using EIA load, weather, hydrology, and event signals
- Safe claim: Direct-source readiness requires a task-compatible observed outcome and an executable family implementation. Source-conditioned simulations remain synthetic. Neither is field validation, realized savings, award certainty, or a profit claim.

### 6. field_guided_control

- Score: 39.9
- Measured sources: NWS_PUBLIC, OPEN_METEO_PUBLIC, NOAA_NCEI, NASA, USGS_WATER, KRAKEN_PUBLIC
- Direct measured replay sources: none
- Source-conditioned synthetic stress sources: NWS_PUBLIC, OPEN_METEO_PUBLIC
- Blocked sources: none
- Generated champion: `none`
- Proof-value champion: `atmospheric_jet_stream_paths`
- First live replay: field drift and corridor-control replay using weather, hydrology, and public time-series stress controls
- Safe claim: Direct-source readiness requires a task-compatible observed outcome and an executable family implementation. Source-conditioned simulations remain synthetic. Neither is field validation, realized savings, award certainty, or a profit claim.

### 7. optimal_curve_transport

- Score: 39.645
- Measured sources: KRAKEN_PUBLIC, COINGECKO_PUBLIC, FRED, GRANTS_GOV, EIA
- Direct measured replay sources: none
- Source-conditioned synthetic stress sources: none
- Blocked sources: none
- Generated champion: `brachistochrone_descent`
- Proof-value champion: `beast_algo_curvature_pressure`
- First live replay: frozen path-window replay using public time series as constraints, not as trading signals
- Safe claim: Direct-source readiness requires a task-compatible observed outcome and an executable family implementation. Source-conditioned simulations remain synthetic. Neither is field validation, realized savings, award certainty, or a profit claim.

### 8. multi_agent_coordination

- Score: 38.58
- Measured sources: NWS_PUBLIC, OPEN_METEO_PUBLIC, NOAA_NCEI, GRANTS_GOV, KRAKEN_PUBLIC, WEBHOOK
- Direct measured replay sources: none
- Source-conditioned synthetic stress sources: NWS_PUBLIC, OPEN_METEO_PUBLIC
- Blocked sources: none
- Generated champion: `none`
- Proof-value champion: `bird_v_formation_flocking`
- First live replay: multi-agent coordination replay under weather/event disruption and public time-series stress
- Safe claim: Direct-source readiness requires a task-compatible observed outcome and an executable family implementation. Source-conditioned simulations remain synthetic. Neither is field validation, realized savings, award certainty, or a profit claim.

### 9. resource_aware_scheduling

- Score: 29.14
- Measured sources: GRANTS_GOV, BLS, FRED, BEA, WEBHOOK
- Direct measured replay sources: none
- Source-conditioned synthetic stress sources: GRANTS_GOV
- Blocked sources: none
- Generated champion: `none`
- Proof-value champion: `cicada_prime_cycles`
- First live replay: bounded wake/scheduling replay using macro pressure and internal event cadence
- Safe claim: Direct-source readiness requires a task-compatible observed outcome and an executable family implementation. Source-conditioned simulations remain synthetic. Neither is field validation, realized savings, award certainty, or a profit claim.

### 10. stability_diagnostic

- Score: 22.48
- Measured sources: FRED, BEA, BLS, NOAA_NCEI, EIA, KRAKEN_PUBLIC, WEBHOOK
- Direct measured replay sources: none
- Source-conditioned synthetic stress sources: none
- Blocked sources: none
- Generated champion: `none`
- Proof-value champion: `markov_blanket_boundaries`
- First live replay: Frobenius, perturbation, and drift diagnostics over measured source snapshots
- Safe claim: Direct-source readiness requires a task-compatible observed outcome and an executable family implementation. Source-conditioned simulations remain synthetic. Neither is field validation, realized savings, award certainty, or a profit claim.

### 11. mission_network_routing

- Score: 21.68
- Measured sources: GRANTS_GOV, NOAA_NCEI, USGS_WATER, WEBHOOK
- Direct measured replay sources: none
- Source-conditioned synthetic stress sources: GRANTS_GOV
- Blocked sources: SAM_GOV
- Generated champion: `none`
- Proof-value champion: `ant_trails`
- First live replay: degraded-network routing windows from grant/opportunity, weather, water, and event-ingress signals
- Safe claim: Direct-source readiness requires a task-compatible observed outcome and an executable family implementation. Source-conditioned simulations remain synthetic. Neither is field validation, realized savings, award certainty, or a profit claim.

### 12. packing_topology

- Score: 9.36
- Measured sources: CENSUS, GRANTS_GOV, BEA
- Direct measured replay sources: none
- Source-conditioned synthetic stress sources: none
- Blocked sources: NREL
- Generated champion: `none`
- Proof-value champion: `coral_growth_fronts`
- First live replay: regional demand and layout-density replay for sensor, hardware, and infrastructure placement
- Safe claim: Direct-source readiness requires a task-compatible observed outcome and an executable family implementation. Source-conditioned simulations remain synthetic. Neither is field validation, realized savings, award certainty, or a profit claim.

## Blockers To Clear

- `BINANCE_PUBLIC` remains failed/thin in the fresh maximizer run.
- `EPA_AQS` remains failed/thin in the fresh maximizer run.
- `NREL` remains failed/thin in the fresh maximizer run.
- `THE_ODDS_API` remains failed/thin in the fresh maximizer run.

## Next Actions

- Run direct measured comparisons first for time_series_model_routing and wave_resonance_timing using their source-specific baseline rosters.
- Treat branching_transport, thermal_ventilation, mission_network_routing, and multi_agent_coordination source links as synthetic stress conditioning until direct outcome telemetry exists.
- Do not use optimal_curve_transport source snapshots as performance inputs until observed paths, constraints, and outcomes are available.
- Build an EIA residual-matrix adapter before calling stability_diagnostic direct-replay ready.
- Fix NREL DNS/API reachability because it remains a key energy-lab blocker.
- Add SAM_GOV_API_KEY if contract-bid/opportunity wiring should become measured.
- Keep market_signal_geometry in paper/replay mode until a separate trading safety audit and explicit action-time approval exist.

## Boundary

This matrix is a live-source wiring and replay-priority artifact. It is not field validation, not a realized-dollar proof, not an award-selection promise, and not permission for live trading.
