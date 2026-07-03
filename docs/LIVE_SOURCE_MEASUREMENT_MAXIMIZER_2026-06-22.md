# Live Source Measurement Maximizer

Generated UTC: `2026-07-03T01:18:39.405817+00:00`

## Summary

- Enabled sources: 29
- Measured sources: 25
- Failed/thin sources: 4
- Total measured rows: 1326
- Coverage: 86.21%
- Estimated annual value surface: $20,071,845,553.20
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
| KRAKEN_PUBLIC | crypto_market | MEASURED | 100 | `data/live_measured/kraken_public/kraken_public_20260703T011824Z.json` | `026cea8a0832f0c350ac62ce95b3724b5add80d269c65134abdf3c5bca5f50dd` |
| BINANCE_PUBLIC | crypto_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/binance_public/binance_public_20260703T011824Z.json` | `3b7bff7cf5033602b19b89088a63fcd143b251cfb6c181b730c79e95bcc644bf` |
| COINGECKO_PUBLIC | crypto_market | MEASURED | 6 | `data/live_measured/coingecko_public/coingecko_public_20260703T011824Z.json` | `c26b51e826d3c7bb6258dd7a5dd7d3fa4a8f3ca923a0ab70450d5afb249f9405` |
| FINNHUB | market_data | MEASURED | 4 | `data/live_measured/finnhub/finnhub_20260703T011824Z.json` | `cf5a1e84e311fa940aff515761f65de9d2693b8f4b8a1194599324e6d2548f40` |
| ALPHAVANTAGE | market_data | MEASURED | 100 | `data/live_measured/alphavantage/alphavantage_20260703T011824Z.json` | `7838391985c5f25165aab8e3722707420417ed7dc800e6f9dce911cc0e8b3ce3` |
| TWELVE_DATA | market_data | MEASURED | 100 | `data/live_measured/twelve_data/twelve_data_20260703T011824Z.json` | `33c462a9f7de67c745b84585fe57d840cdf419106a445de615b5b2293766d622` |
| MASSIVE | market_data | MEASURED | 3 | `data/live_measured/massive/massive_20260703T011824Z.json` | `4a8fd7f0c8fe03caa9f1db78d9d41c9e489e3e66ed758cf28fe81fd660e401ba` |
| FRED | rates | MEASURED | 100 | `data/live_measured/fred/fred_20260703T011824Z.json` | `bd463f51ca3047ac8797a7e5c7c2ba4fe2d869494d24b202aae84527af2c6e18` |
| EIA | energy | MEASURED | 100 | `data/live_measured/eia/eia_20260703T011824Z.json` | `32b5096200855ad774aae69e9d6d251b2a8b39c42d665beedbb3fa9f3565e521` |
| BLS | labor | MEASURED | 30 | `data/live_measured/bls/bls_20260703T011824Z.json` | `a80a01946f7931eefcb5e75be3a8440e40d79293c436d41cb4cfb0adaa59c3e9` |
| NASA | space | MEASURED | 1 | `data/live_measured/nasa/nasa_20260703T011824Z.json` | `fdac7043f2f8bfb76d3dd1d868453de55733a22e8415586fb424e17d314b74b0` |
| NOAA_NCEI | weather | MEASURED | 11 | `data/live_measured/noaa_ncei/noaa_ncei_20260703T011824Z.json` | `31c24568577a13594b9334f46f0674ee2ed194b6581a22d217098c81ebcdda66` |
| NWS_PUBLIC | weather | MEASURED | 100 | `data/live_measured/nws_public/nws_public_20260703T011824Z.json` | `d135972db722bd60424cb537c86c1aa59962aab8c1adf4e47ed1d2a060c88084` |
| OPEN_METEO_PUBLIC | weather | MEASURED | 48 | `data/live_measured/open_meteo_public/open_meteo_public_20260703T011824Z.json` | `289031ab32cd1c4d299c0df25f7c99f3d01d2f6282f3ef20e469688c0cfff4e5` |
| NREL | energy_lab | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/nrel/nrel_20260703T011824Z.json` | `9a9cd35e05df85dc48c5dcdd1112a86b588ae6469cf995d86776735fffc751fe` |
| USGS_WATER | water | MEASURED | 1 | `data/live_measured/usgs_water/usgs_water_20260703T011824Z.json` | `83621296c64ecb65268d1fb3b32e6082aa0fc37bea7d943bb3c88bd09a49b8b6` |
| CENSUS | demographic | MEASURED | 1 | `data/live_measured/census/census_20260703T011824Z.json` | `06fbe8ffaa26ef582d0c78e2c7ab5ab8d8f923d5be04bff1cc2949521f5ed7b5` |
| BEA | macro | MEASURED | 13 | `data/live_measured/bea/bea_20260703T011824Z.json` | `a5705e71611fc97ec9f696ab459dd89cd5a5676d7df09370cd71ad2a678f445f` |
| EPA_AQS | air_quality | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/epa_aqs/epa_aqs_20260703T011824Z.json` | `323ca3db21a3009d5af6a043e631d4c89a3cdcca2fad0ddd7d1ffd947a71a11d` |
| AIRNOW | air_quality | MEASURED | 3 | `data/live_measured/airnow/airnow_20260703T011824Z.json` | `ccb3e6e7b64aa55e30918411137850fbfa92cbae7affb6e0de1969816d389270` |
| THE_ODDS_API | sports_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/the_odds_api/the_odds_api_20260703T011824Z.json` | `cec6d21ec4730cce7febfa19a2e05116d5946b77e233784ffa12b0c23e8e9806` |
| SAM_GOV | federal_opportunity | UNCONFIGURED | 0 | `data/live_measured/sam_gov/sam_gov_20260703T011824Z.json` | `ccfe02e5f6d08881eac9cb4c2321b439c23d613fc40a0175f1c53e11e2014e30` |
| GRANTS_GOV | federal_opportunity | MEASURED | 100 | `data/live_measured/grants_gov/grants_gov_20260703T011824Z.json` | `8e6f0a17d72780a6678ddde723a680339d5a52d063449905a2f59e73d0d0181e` |
| WEBHOOK | internal | MEASURED | 1 | `data/live_measured/webhook/webhook_20260703T011824Z.json` | `8f29eaee8cc1e19ff5b32aa8db3062d760f6738d2b77daade4b9c561c01ab1e9` |
| TREASURY_FISCAL_PUBLIC | rates | MEASURED | 100 | `data/live_measured/treasury_fiscal_public/treasury_fiscal_public_20260703T011824Z.json` | `966df318d07251cd34097e225b58fa1a63c405a42a4ccf6ae2f71c16c30e49ac` |
| SEC_PUBLIC | market_data | MEASURED | 100 | `data/live_measured/sec_public/sec_public_20260703T011824Z.json` | `d953ec9d06c81a8b869c9916d6554cb0a2e99a8b8f09ff8c437c9533b765514d` |
| COINBASE_PUBLIC | crypto_market | MEASURED | 100 | `data/live_measured/coinbase_public/coinbase_public_20260703T011824Z.json` | `ae8c20b6cd3eaaba8a9feac02a05a8f5febea1035e9c3a50ca661a4c741c24ac` |
| WORLD_BANK_PUBLIC | macro | MEASURED | 1 | `data/live_measured/world_bank_public/world_bank_public_20260703T011824Z.json` | `8e809df6609aa389aaf48e4cec1f67172a6b2babbc6c7f8a07c4e5791e95c40d` |
