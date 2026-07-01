# Live Source Measurement Maximizer

Generated UTC: `2026-07-01T06:04:01.744598+00:00`

## Summary

- Enabled sources: 23
- Measured sources: 17
- Failed/thin sources: 6
- Total measured rows: 523
- Coverage: 73.91%
- Estimated annual value surface: $8,189,516,738.40
- Boundary: This pass proves fresh measured rows and hashes. It does not prove realized savings, field validation, trading profit, or guaranteed award value.

## Measured Sources

- `AIRNOW`
- `ALPACA`
- `ALPHAVANTAGE`
- `BEA`
- `BLS`
- `CENSUS`
- `COINGECKO_PUBLIC`
- `FINNHUB`
- `FRED`
- `GRANTS_GOV`
- `KRAKEN`
- `KRAKEN_PUBLIC`
- `MASSIVE`
- `NOAA_NCEI`
- `TWELVE_DATA`
- `USGS_WATER`
- `WEBHOOK`

## Failed Or Thin Sources

- `BINANCE_PUBLIC`
- `EIA`
- `EPA_AQS`
- `NASA`
- `NREL`
- `THE_ODDS_API`

## Provider Rows

| Source | Sector | Status | Rows | Snapshot | SHA-256 |
|---|---|---|---:|---|---|
| KRAKEN_PUBLIC | crypto_market | MEASURED | 50 | `data/live_measured/kraken_public/kraken_public_20260701T060342Z.json` | `d4610a775738d4151815eb0e18f4479db2d7462a79e1c2046d64f2d3c3c68133` |
| BINANCE_PUBLIC | crypto_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/binance_public/binance_public_20260701T060342Z.json` | `ed49d9475fbed0c7d98cb720205371bca52667ef32af9cd1017fb58d0f567778` |
| COINGECKO_PUBLIC | crypto_market | MEASURED | 6 | `data/live_measured/coingecko_public/coingecko_public_20260701T060342Z.json` | `9c81bd8555a15d5f5de3ed24c09b0e95c2e065c7feb0f3492c1fa5bee67e29d9` |
| FINNHUB | market_data | MEASURED | 4 | `data/live_measured/finnhub/finnhub_20260701T060342Z.json` | `9580bf7009d081dc9543e2e7ff73819fb4fb9fe479b367dfc09d3bf5172c0ed8` |
| ALPHAVANTAGE | market_data | MEASURED | 50 | `data/live_measured/alphavantage/alphavantage_20260701T060342Z.json` | `5c1a0bcb0e72034e6e44352c34a433cffc3701de7b361c7263b55f82fcdef1c5` |
| TWELVE_DATA | market_data | MEASURED | 50 | `data/live_measured/twelve_data/twelve_data_20260701T060342Z.json` | `f52259c662ad2d0b249d52b1c9e96675d8a041bc30d48dba2425da359e778396` |
| MASSIVE | market_data | MEASURED | 3 | `data/live_measured/massive/massive_20260701T060342Z.json` | `c76cafac338363d58d2ae6c2378da31221a394acb13ae4c390e278387fb0d516` |
| FRED | rates | MEASURED | 48 | `data/live_measured/fred/fred_20260701T060342Z.json` | `ac1091c05b2c1bcf378345979daedc464cec271b997c57a04ebebf837db2168b` |
| EIA | energy | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/eia/eia_20260701T060342Z.json` | `00025cade8b23c71d148ff6c7545d24c4e731f583003bcb83c3e77576651d589` |
| BLS | labor | MEASURED | 29 | `data/live_measured/bls/bls_20260701T060342Z.json` | `edc7f908dfd5deabe639e2716effb679eb24b6c075e4ee09a53ebf154317de40` |
| NASA | space | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/nasa/nasa_20260701T060342Z.json` | `474034979bce4070e837958fd595bc98f2b9881553b58b575aa05bb1e75bc21f` |
| NOAA_NCEI | weather | MEASURED | 11 | `data/live_measured/noaa_ncei/noaa_ncei_20260701T060342Z.json` | `8476b8a2ebac01b13f097cd7e00bcffcd32835aca5c54ccd1dca4dbe7e5865f6` |
| NREL | energy_lab | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/nrel/nrel_20260701T060342Z.json` | `ae32306e8518bac91791cf745dc35fc1c954680862649b46d0c31ac8bb57dd3e` |
| USGS_WATER | water | MEASURED | 1 | `data/live_measured/usgs_water/usgs_water_20260701T060342Z.json` | `4dcedca0bb34e85b7ead86827d6608a75e896ba9cbbc8d18c22c1464e0439786` |
| CENSUS | demographic | MEASURED | 1 | `data/live_measured/census/census_20260701T060342Z.json` | `a110469bd32acc1a98a6b443f47205aa61f511d38921f82725dc576728c6738e` |
| BEA | macro | MEASURED | 13 | `data/live_measured/bea/bea_20260701T060342Z.json` | `cd5a109f6bcc05a1439a70a386329f927ea03291bbecc57720e74329aca8e886` |
| EPA_AQS | air_quality | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/epa_aqs/epa_aqs_20260701T060342Z.json` | `71bf3ad04abbaf006369aeae761be6c973d0ee8a9f1b15a198af6f290a5095db` |
| AIRNOW | air_quality | MEASURED | 3 | `data/live_measured/airnow/airnow_20260701T060342Z.json` | `e20bb93c3208ad0ce8ea1d32c3fe880500fc6c2633c885b21aaeb139b5f8a57e` |
| THE_ODDS_API | sports_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/the_odds_api/the_odds_api_20260701T060342Z.json` | `5e62e27b10bf8c2e732d139719acabf110b7854fe01de5573c22490ea82638d0` |
| SAM_GOV | federal_opportunity | UNCONFIGURED | 0 | `data/live_measured/sam_gov/sam_gov_20260701T060342Z.json` | `558b0c09a92b88fde2b1403a190609a3b0226c0e84c76ea7eccdbe16cbacab85` |
| GRANTS_GOV | federal_opportunity | MEASURED | 50 | `data/live_measured/grants_gov/grants_gov_20260701T060342Z.json` | `0647f6db63033f9d02d464efbde0b004b27dd0bd68a717b32eed11aa95ba1ef1` |
| WEBHOOK | internal | MEASURED | 1 | `data/live_measured/webhook/webhook_20260701T060342Z.json` | `6980aacedf43467c1ea90008b0d75844f2d6a627fa936fe96799dda5fc05cd11` |
