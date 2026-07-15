# EIA Prospective Source-Timing Audit

Generated UTC: `2026-07-15T02:23:15.348705+00:00`

## Decision

The original daily protocol remains frozen as a zero-prediction negative result. The official hourly feed can reconstruct settled daily totals exactly, but its observed forecast horizon does not expose a complete future local day before the daily protocol's target-local-midnight seal. No backfill or relaxed deadline is permitted.

The scientifically valid remediation is a separate hourly prospective protocol with a pre-interval seal and isolated append-only ledgers.

## Reconciliation

- Authorities reconciled: `8/8`
- Exact hourly-to-daily comparisons: `158/158`
- All authority comparisons exact: `true`
- Hourly labels are UTC hour endings. The interval is assigned to a local day after subtracting one hour and converting to the authority IANA timezone.
- Completeness requires exactly every expected hour ending for that 23/24/25-hour local day.

| Authority | Comparisons | Exact | Max abs delta MWh | Future complete day available |
|---|---:|---:|---:|---|
| CISO | 20 | 20 | 0.0 | false |
| ERCO | 20 | 20 | 0.0 | false |
| ISNE | 20 | 20 | 0.0 | false |
| MISO | 20 | 20 | 0.0 | false |
| NYIS | 20 | 20 | 0.0 | false |
| PJM | 20 | 20 | 0.0 | false |
| SWPP | 19 | 19 | 0.0 | false |
| TVA | 19 | 19 | 0.0 | false |

## Frozen Runtime

- Prediction records: `0`
- Settlement records: `0`
- Negative result preserved: `true`

## Finding

The hourly source exactly reconstructs settled daily D/DF values, but at observation time no authority exposed a complete future local-day DF aggregate before that target day's local-midnight gate. The v1 daily target therefore remains a valid zero-prediction negative result and must not be backfilled.

## Publisher Sources

- [EIA Form EIA-930 hourly API dashboard](https://www.eia.gov/opendata/browser/electricity/rto/region-data)
- [EIA Open Data API documentation](https://www.eia.gov/opendata/documentation.php)

## Claim Boundary

This receipt establishes source equivalence and an observed publication-timing limitation. It does not establish prospective model skill, production readiness, savings, patentability, or external validation.

Machine-readable receipt: `evidence/external_validation/eia_prospective_source_timing_audit_20260714.json`
