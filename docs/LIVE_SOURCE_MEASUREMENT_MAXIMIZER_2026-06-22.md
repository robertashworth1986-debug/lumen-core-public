# Live Source Measurement Maximizer

Generated UTC: `2026-07-01T12:36:36.167442+00:00`

## Summary

- Enabled sources: 23
- Measured sources: 19
- Failed/thin sources: 4
- Total measured rows: 516
- Coverage: 82.61%
- Estimated annual value surface: $12,173,289,849.60
- Boundary: This pass proves fresh measured rows and hashes. It does not prove realized savings, field validation, trading profit, or guaranteed award value.

## Measured Sources

- `AIRNOW`
- `ALPACA`
- `ALPHAVANTAGE`
- `BEA`
- `BLS`
- `CENSUS`
- `COINGECKO_PUBLIC`
- `EIA`
- `FINNHUB`
- `FRED`
- `GRANTS_GOV`
- `KRAKEN`
- `KRAKEN_PUBLIC`
- `MASSIVE`
- `NASA`
- `NOAA_NCEI`
- `TWELVE_DATA`
- `USGS_WATER`
- `WEBHOOK`

## Failed Or Thin Sources

- `BINANCE_PUBLIC`
- `EPA_AQS`
- `NREL`
- `THE_ODDS_API`

## Provider Rows

| Source | Sector | Status | Rows | Snapshot | SHA-256 |
|---|---|---|---:|---|---|
| KRAKEN_PUBLIC | crypto_market | MEASURED | 40 | `data/live_measured/kraken_public/kraken_public_20260701T123604Z.json` | `cc9ac2266a7a18ca40200f6844338450582c31a5986abb78a45a163c19408424` |
| BINANCE_PUBLIC | crypto_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/binance_public/binance_public_20260701T123604Z.json` | `0045f6fbb544640c0eeb66887be52afcdad06d03aa96e6ca4ea1945501dc86b5` |
| COINGECKO_PUBLIC | crypto_market | MEASURED | 6 | `data/live_measured/coingecko_public/coingecko_public_20260701T123604Z.json` | `368272756b2c3d6c1a9f4ad61d8b313a086db65a344ac75b4214a6bb159cc565` |
| FINNHUB | market_data | MEASURED | 4 | `data/live_measured/finnhub/finnhub_20260701T123604Z.json` | `4bbd7112900e08e4cc847ee6155adbb2750fba7ebabd6ee80a78f9361ee8a0d1` |
| ALPHAVANTAGE | market_data | MEASURED | 40 | `data/live_measured/alphavantage/alphavantage_20260701T123604Z.json` | `9496f7251daeb48c034ef3322c4e9901d585253dd9c44253c37f5d50ba2cfd86` |
| TWELVE_DATA | market_data | MEASURED | 40 | `data/live_measured/twelve_data/twelve_data_20260701T123604Z.json` | `17664d1bbd6b908162c3dfce9021bde4d83799e811c4f902242e6f46ba074c13` |
| MASSIVE | market_data | MEASURED | 3 | `data/live_measured/massive/massive_20260701T123604Z.json` | `bf00435d1f695d932b93656c84d881ce25f6f0934419d83a2f523177bf2d0c6c` |
| FRED | rates | MEASURED | 40 | `data/live_measured/fred/fred_20260701T123604Z.json` | `7f989168b7e5b48a19934c522588cbe57bd30f543b1e866e506e595f4a28dd51` |
| EIA | energy | MEASURED | 40 | `data/live_measured/eia/eia_20260701T123604Z.json` | `276c1cf59cb02dbb286cd3a6c08d7059a4f416b039c3149f7dcf16cb5bc4aa38` |
| BLS | labor | MEASURED | 29 | `data/live_measured/bls/bls_20260701T123604Z.json` | `104e22c51dd4de124a5a7d7929c66ec78dff87a671458e9fc48ef6e5cca16c7d` |
| NASA | space | MEASURED | 1 | `data/live_measured/nasa/nasa_20260701T123604Z.json` | `3016e2968ac17096cd13d36bae5c711b60aa0d0895748adaef6091ac728780f0` |
| NOAA_NCEI | weather | MEASURED | 11 | `data/live_measured/noaa_ncei/noaa_ncei_20260701T123604Z.json` | `455767b9a7eba0d6df50f6c3c705e1bc7c8e04bee281ccbc43b748fc68fe08d6` |
| NREL | energy_lab | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/nrel/nrel_20260701T123604Z.json` | `5e415fb67c02ddf25adc0ce406dbb896dd210e780131718d31e78cac2095f65c` |
| USGS_WATER | water | MEASURED | 1 | `data/live_measured/usgs_water/usgs_water_20260701T123604Z.json` | `d07cf7f159b7f31643ae44699f5355b0feb9aecd99e79a43eda60522ac65ab65` |
| CENSUS | demographic | MEASURED | 1 | `data/live_measured/census/census_20260701T123604Z.json` | `341152b9df75b41bd1b945d85c8b9e562a0019b6d4b1e464589bec6eb6a1050b` |
| BEA | macro | MEASURED | 13 | `data/live_measured/bea/bea_20260701T123604Z.json` | `9cf6382689ba3b7bec01d74077cd166eb5ffac9cec489f6dc80ef9e91838b260` |
| EPA_AQS | air_quality | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/epa_aqs/epa_aqs_20260701T123604Z.json` | `2f5ead14cade6408f2d027b540d4a415793d694fb577eff4b26438a89dd4140a` |
| AIRNOW | air_quality | MEASURED | 3 | `data/live_measured/airnow/airnow_20260701T123604Z.json` | `779712ebf77f10f1592f6d3f055723f80e0768dda1a28538b2ee6a7c55de4b69` |
| THE_ODDS_API | sports_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/the_odds_api/the_odds_api_20260701T123604Z.json` | `a1893be4858e23419898656a50b7049622b77fb714530080d777fb7c09d65948` |
| SAM_GOV | federal_opportunity | UNCONFIGURED | 0 | `data/live_measured/sam_gov/sam_gov_20260701T123604Z.json` | `f3f78c36c7f4abdb1dcedb687f8c205dc1875d2a0ae6a5393da828ccdf0da7c1` |
| GRANTS_GOV | federal_opportunity | MEASURED | 40 | `data/live_measured/grants_gov/grants_gov_20260701T123604Z.json` | `b9dff935730b035c0df90b1b9d909d11e9b6c77927d93262ebc195cdd98a537b` |
| WEBHOOK | internal | MEASURED | 1 | `data/live_measured/webhook/webhook_20260701T123604Z.json` | `871c437c2082b2df2c47d04b3f9a84fdd3ce4c51c1f1e02f5e4cc731896855fe` |
