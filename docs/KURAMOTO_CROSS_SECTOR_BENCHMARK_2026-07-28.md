# Kuramoto Cross-Sector Benchmark

Generated UTC: `2026-07-29T03:32:25.752573Z`
Status: `NO_CROSS_SECTOR_EFFICIENCY_GAIN_PROVEN`
Evidence chain SHA-256: `5538aafe96b331bf3125f85e113bc2efb74a153fe81e507b5602187e4493f0a1`

## Decision

No sector-level Kuramoto efficiency gain is proven.
No positive exploratory sector survived comparison with its best protocol baseline.

The old coefficient-driven 24/24 result is not used as real-data performance evidence. The separately frozen EIA benchmark is retained, including its negative result.

## Coverage

- Explicit retrospective sources admitted: `6` / `6`
- Anchored protocol-frozen benchmarks: `1`
- Rolling evaluation origins: `786`
- Protocol-matched strategies per retrospective source: `10`
- Sector gains proven: `0`
- External cross-sector replication complete: `false`

## Sector Ranking

| Rank | Sector | Sources | Positive vs best | Strong retrospective | Mean improvement vs best | Status |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `electric_generation` | 1 | 0 | 0 | -21.9613% | `NO_SECTOR_GAIN_PROVEN` |
| 2 | `electric_grid_demand` | 1 | 0 | 0 | -184.0912% | `NO_SECTOR_GAIN_PROVEN` |
| 3 | `market_telemetry_research_only` | 1 | 0 | 0 | -449.6233% | `NO_SECTOR_GAIN_PROVEN` |
| 4 | `macro_rates` | 1 | 0 | 0 | -552.6600% | `NO_SECTOR_GAIN_PROVEN` |
| 5 | `nuclear_outage` | 1 | 0 | 0 | -897.2966% | `NO_SECTOR_GAIN_PROVEN` |
| 6 | `macro_prices_labor` | 2 | 0 | 0 | -1017.1381% | `NO_SECTOR_GAIN_PROVEN` |

## Source Results

| Source | Sector | Candidate rank | Best baseline | MAE improvement vs best | Status |
| --- | --- | ---: | --- | ---: | --- |
| `fred_dgs10_business_daily` | `macro_rates` | 10 / 10 | `naive_last` | -552.6600% | `NO_KURAMOTO_GAIN_PROVEN_ON_THIS_SOURCE` |
| `fred_cpiaucsl_monthly` | `macro_prices_labor` | 9 / 10 | `naive_last` | -1478.0933% | `NO_KURAMOTO_GAIN_PROVEN_ON_THIS_SOURCE` |
| `fred_unrate_monthly` | `macro_prices_labor` | 9 / 10 | `naive_last` | -556.1829% | `NO_KURAMOTO_GAIN_PROVEN_ON_THIS_SOURCE` |
| `eia_us_generation_monthly` | `electric_generation` | 5 / 10 | `autoregressive_ridge` | -21.9613% | `NO_KURAMOTO_GAIN_PROVEN_ON_THIS_SOURCE` |
| `eia_nuclear_outage_daily_2025` | `nuclear_outage` | 10 / 10 | `naive_last` | -897.2966% | `NO_KURAMOTO_GAIN_PROVEN_ON_THIS_SOURCE` |
| `kraken_btc_minute_public` | `market_telemetry_research_only` | 8 / 10 | `naive_last` | -449.6233% | `NO_KURAMOTO_GAIN_PROVEN_ON_THIS_SOURCE` |
| `eia_grid_wave_champion_20260713` | `electric_grid_demand` | 9 / 10 | `autoregressive_ridge_p14` | -184.0912% | `NEGATIVE_KURAMOTO_EVIDENCE` |

## Dollar Sensitivity

These values are arithmetic sensitivity only, not LumenCore-attributable savings.

| Improvement | Sensitivity on a $1B annual value stream |
| ---: | ---: |
| 0.001% | $10,000/year |
| 0.01% | $100,000/year |
| 0.1% | $1,000,000/year |
| 1% | $10,000,000/year |

Required conversion: `annual_value = validated_native_unit_error_reduction_per_period * validated_periods_per_year * buyer_approved_cost_per_native_unit`

## Live-Breadth Admission

- Manifest present: `true`
- Manifest count internally consistent: `true`
- Discovered routes: `603`
- Materialized routes: `500`
- Omitted routes disclosed: `103`
- Discovery-manifest membership is not benchmark admission.
- Thin, unrelated, duplicated, and contract-free source systems remain excluded.

## Next Proof Step

Do not market a Kuramoto efficiency gain. Preserve the negative results and test a future never-before-scored window only after the sector, incumbent baseline, native metric, and economic conversion are approved by an external owner.

## Boundary

> This protocol can produce retrospective local-snapshot software evidence and reproduce the separately frozen EIA public-data benchmark. It cannot by itself establish cross-sector efficiency, field performance, realized savings, safety, procurement acceptance, external validation, trading edge, or an unbeatable claim.
