# Energy Price-Pressure Forecast Evidence

Generated UTC: 2026-07-29T08:11:23.945412+00:00

## Boundary

This is a historical measured energy-system stress proxy, not a wholesale power-price forecast, price-pressure validation, or real-dollar savings claim. It combines EIA grid demand/generation, EIA day-ahead demand rows, nuclear-outage stress, FRED macro series, and current geometry context. The demand-residual comparison is exploratory and has not passed a registered all-baseline or multiplicity-controlled promotion gate. ISO/RTO LMP or settlement data with auditable timestamps is required for any price claim.

## Summary

- Hourly grid rows: 190
- Forecast rows generated: 24
- Price-pressure max band: high
- Promoted model beats best named baseline: False
- Exploratory demand-proxy MAE improvement: 36.387422%
- Multiplicity-controlled promotion passed: False
- Actual electricity price series connected: False
- Ready for price-pressure claim: False
- Energy-stress proxy description allowed: True
- Ready for real dollar claim: False

## Walk-Forward Demand Proxy Backtest

| Model | MAE MWh | RMSE MWh | MAE % avg demand |
|---|---:|---:|---:|
| persistence | 7840.754613 | 10157.045376 | 1.714039 |
| eia_day_ahead_forecast | 7592.183814 | 9270.964546 | 1.659699 |
| phase_locked_residual_corrector | 4829.583823 | 6041.353712 | 1.055778 |

## Next Forecast Windows

| Hour | Pressure | Band | Predicted Demand MWh |
|---:|---:|---|---:|
| 1 | 71.208675 | high | 475812.319497 |
| 2 | 68.528922 | high | 465648.83591 |
| 3 | 65.573782 | high | 454440.893081 |
| 4 | 62.739047 | elevated | 443689.614043 |
| 5 | 60.466988 | elevated | 435072.390933 |
| 6 | 58.826304 | elevated | 428849.776131 |
| 7 | 58.115198 | elevated | 426152.769714 |
| 8 | 58.092949 | elevated | 426068.387226 |

## Claim Gate

- Use now: historical measured energy-system stress proxy and exploratory demand-residual diagnostic, with the limits stated beside it.
- Do not claim yet: a price forecast, price-pressure validation, promoted-model superiority, realized savings, field validation, live trading alpha, or guaranteed award outcome.
- Unlock next: connect ISO/RTO LMP settlement data and run the same walk-forward harness against actual prices.
