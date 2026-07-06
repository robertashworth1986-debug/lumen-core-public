# Live Source Measurement Maximizer

Generated UTC: `2026-07-05T21:20:44.262856+00:00`

## Summary

- Enabled sources: 29
- Measured sources: 25
- Failed/thin sources: 4
- Total measured rows: 2580
- Coverage: 86.21%
- Estimated annual value surface: $22,495,647,588.00
- Boundary: This pass proves fresh measured rows and hashes. It does not prove realized savings, field validation, trading profit, or guaranteed award value.

## Measured Sources

- `AIRNOW`
- `ALPACA`
- `ALPHAVANTAGE`
- `BEA`
- `BLS`
- `CENSUS`
- `COINBASE_PUBLIC`
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
- `NWS_PUBLIC`
- `OPEN_METEO_PUBLIC`
- `SEC_PUBLIC`
- `TREASURY_FISCAL_PUBLIC`
- `TWELVE_DATA`
- `USGS_WATER`
- `WEBHOOK`
- `WORLD_BANK_PUBLIC`

## Failed Or Thin Sources

- `BINANCE_PUBLIC`
- `EPA_AQS`
- `NREL`
- `THE_ODDS_API`

## Provider Rows

| Source | Sector | Status | Rows | Snapshot | SHA-256 |
|---|---|---|---:|---|---|
| KRAKEN_PUBLIC | crypto_market | MEASURED | 250 | `data/live_measured/kraken_public/kraken_public_20260705T212018Z.json` | `b4e6d9d6928ca82a95ebe7d3ea136cfbb040892c7b63d4ca35f8c7ac503f307a` |
| BINANCE_PUBLIC | crypto_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/binance_public/binance_public_20260705T212018Z.json` | `e59c8b79f5b264ba573365430161c90fe59b211ef720ed3e3b36a01fd29074ae` |
| COINGECKO_PUBLIC | crypto_market | MEASURED | 6 | `data/live_measured/coingecko_public/coingecko_public_20260705T212018Z.json` | `8b975c39a3842802c96bbbc759d77f473758c7aa72490636d0d2830575c1c9ab` |
| FINNHUB | market_data | MEASURED | 4 | `data/live_measured/finnhub/finnhub_20260705T212018Z.json` | `9f86539c927b7c00951919dc7867c730e8982cb8200077e5daaeece159992209` |
| ALPHAVANTAGE | market_data | MEASURED | 100 | `data/live_measured/alphavantage/alphavantage_20260705T212018Z.json` | `8e0cb6763783a5585be34f978713b9cab028865505b3169eb75444e729305520` |
| TWELVE_DATA | market_data | MEASURED | 250 | `data/live_measured/twelve_data/twelve_data_20260705T212018Z.json` | `81e99282d5e94e60713b60bba4d74e5e8837ad2405af25a9eb1ddfbf2e6986bf` |
| MASSIVE | market_data | MEASURED | 3 | `data/live_measured/massive/massive_20260705T212018Z.json` | `d5d052e4a563b4deae8b3b1932844b6c33d9f8b6ea72cf26d686637388f29ecf` |
| FRED | rates | MEASURED | 248 | `data/live_measured/fred/fred_20260705T212018Z.json` | `aee05642909c4f0dffc9f21113964db0ed0c2b89053589748a50a50e75710f6d` |
| EIA | energy | MEASURED | 250 | `data/live_measured/eia/eia_20260705T212018Z.json` | `2ce7824a4c55692a840088910d0880671ce9c1e689705242419ccaa5c4671003` |
| BLS | labor | MEASURED | 30 | `data/live_measured/bls/bls_20260705T212018Z.json` | `df3ff0dc9b2bb42a5d70c4de09ccce9d9b9c3654125ef2118bc2574897bbd144` |
| NASA | space | MEASURED | 1 | `data/live_measured/nasa/nasa_20260705T212018Z.json` | `131379a8ff6abb7a1223b03c166d3e5f8980de37ba7427073d0ca40691f8f0e0` |
| NOAA_NCEI | weather | MEASURED | 11 | `data/live_measured/noaa_ncei/noaa_ncei_20260705T212018Z.json` | `68e8aad64e9b9fd0d642a15661f1e24c953e1b461466e565fe8e2350fd041db5` |
| NWS_PUBLIC | weather | MEASURED | 156 | `data/live_measured/nws_public/nws_public_20260705T212018Z.json` | `ec0988170021b5e089a2a2c521f0813c21841d1840f7a9e66041df4b52cdfc2f` |
| OPEN_METEO_PUBLIC | weather | MEASURED | 48 | `data/live_measured/open_meteo_public/open_meteo_public_20260705T212018Z.json` | `56e0bafb4065ba3807ad388b7d0b8c46fa730f129c52c7b1ed2c634313f633ce` |
| NREL | energy_lab | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/nrel/nrel_20260705T212018Z.json` | `90acadbeece36b3b691301ded2625b16e2e053b8f48f8415d430dd0fd60d7af2` |
| USGS_WATER | water | MEASURED | 1 | `data/live_measured/usgs_water/usgs_water_20260705T212018Z.json` | `160f0e53fd98ea34445bbd1258c6043a807a1d545ef69cf9ff0ace7ecc7dcda9` |
| CENSUS | demographic | MEASURED | 1 | `data/live_measured/census/census_20260705T212018Z.json` | `6a6b1e623277eaf31ee2f33244c319f829a428002c60c4975e0efec7aa0d3274` |
| BEA | macro | MEASURED | 13 | `data/live_measured/bea/bea_20260705T212018Z.json` | `dc33a3efdacc8f2d49e6a20201b586c98e82eab2edca0d4fef60f123f70dc7a6` |
| EPA_AQS | air_quality | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/epa_aqs/epa_aqs_20260705T212018Z.json` | `724e6a208ada7eed97567ea31723dc86ab6f780e019e383ec86df33f2ae0d95f` |
| AIRNOW | air_quality | MEASURED | 3 | `data/live_measured/airnow/airnow_20260705T212018Z.json` | `b73d64d3d4166fb56239ab85ae8645a511d2c3db2edcdf1e6da50be0d700a5fa` |
| THE_ODDS_API | sports_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/the_odds_api/the_odds_api_20260705T212018Z.json` | `ef73603a11f6eb8bff9652f3d68ef7da29a7efaa80955495ab0e0ab9ae588837` |
| SAM_GOV | federal_opportunity | UNCONFIGURED | 0 | `data/live_measured/sam_gov/sam_gov_20260705T212018Z.json` | `97a31a0ac6172d7dfbf317bb16a70db2af43969e0bb2d23fb15863172487a1ba` |
| GRANTS_GOV | federal_opportunity | MEASURED | 250 | `data/live_measured/grants_gov/grants_gov_20260705T212018Z.json` | `e29c5f9834f04cc4e53c4264eb93adfff336aa2deab6f6b2ab7fd8e8bccf5c7e` |
| WEBHOOK | internal | MEASURED | 1 | `data/live_measured/webhook/webhook_20260705T212018Z.json` | `22fdceef38a876332d07f68468e9ef4ab89004de0f5bf15af30ae9bd93c9780a` |
| TREASURY_FISCAL_PUBLIC | rates | MEASURED | 250 | `data/live_measured/treasury_fiscal_public/treasury_fiscal_public_20260705T212018Z.json` | `f4eeeccda65ebcb486cb4f713685cf3658e9024d4c7debd1c4a0f402b470c386` |
| SEC_PUBLIC | market_data | MEASURED | 250 | `data/live_measured/sec_public/sec_public_20260705T212018Z.json` | `99971d8a5ed3d8f65667517c0b4faa4f75e0db2e021602127fc770a0e35ed9c3` |
| COINBASE_PUBLIC | crypto_market | MEASURED | 250 | `data/live_measured/coinbase_public/coinbase_public_20260705T212018Z.json` | `2f19143980016e3e2d82225a670d5cb8389ad9248441b12a8322f15bec22ca5d` |
| WORLD_BANK_PUBLIC | macro | MEASURED | 1 | `data/live_measured/world_bank_public/world_bank_public_20260705T212018Z.json` | `2e297a5ab0afbced7a840789e02c7dc395b49c8eb5bd07846f8e3f1557939839` |
