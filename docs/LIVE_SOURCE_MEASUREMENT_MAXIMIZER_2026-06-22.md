# Live Source Measurement Maximizer

Generated UTC: `2026-07-01T14:59:55.102255+00:00`

## Summary

- Enabled sources: 29
- Measured sources: 25
- Failed/thin sources: 4
- Total measured rows: 823
- Coverage: 86.21%
- Estimated annual value surface: $18,041,944,890.00
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
| KRAKEN_PUBLIC | crypto_market | MEASURED | 50 | `data/live_measured/kraken_public/kraken_public_20260701T145937Z.json` | `b270fbade7dcfb09558f1b1cc9244b9a5488f8c5aa774ceba8f5b402746eb04a` |
| BINANCE_PUBLIC | crypto_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/binance_public/binance_public_20260701T145937Z.json` | `ee5879be498e88e83291b6b5b1c353496824aeaf88146b32ef0392ba693e0732` |
| COINGECKO_PUBLIC | crypto_market | MEASURED | 6 | `data/live_measured/coingecko_public/coingecko_public_20260701T145937Z.json` | `e5f53d30c3feaa3d4a4bb7b457f90e5635c457897fec5b4824bffd3128d0390d` |
| FINNHUB | market_data | MEASURED | 4 | `data/live_measured/finnhub/finnhub_20260701T145937Z.json` | `bf1b305cc21a526feaf1239ccd2f61929c455bee201f05bc99b7d06444d0a6a3` |
| ALPHAVANTAGE | market_data | MEASURED | 50 | `data/live_measured/alphavantage/alphavantage_20260701T145937Z.json` | `0039e338e11ec374b605cccde3a7e399a6aa42f26a391a96c4b90064014da279` |
| TWELVE_DATA | market_data | MEASURED | 50 | `data/live_measured/twelve_data/twelve_data_20260701T145937Z.json` | `e4afe5299deddd3a8b82f9630e63ffbcd577f12e8404bd671353f7967085edc9` |
| MASSIVE | market_data | MEASURED | 3 | `data/live_measured/massive/massive_20260701T145937Z.json` | `935d650a7ccee15da5d36565bf00cbd17e51c600f0be184180caad1081630126` |
| FRED | rates | MEASURED | 48 | `data/live_measured/fred/fred_20260701T145937Z.json` | `23a1fbd6675371ddbafdec460df5d62ef6843a6625e7fd0ac36e38de86709fa4` |
| EIA | energy | MEASURED | 50 | `data/live_measured/eia/eia_20260701T145937Z.json` | `1cf813349fd3d60693e09dee82cfb843ec4e790878d88679e858ae943036ace6` |
| BLS | labor | MEASURED | 29 | `data/live_measured/bls/bls_20260701T145937Z.json` | `fa20696375e388b550d92447dfcb30a376c906bc16410aaad6f68479423b9c77` |
| NASA | space | MEASURED | 1 | `data/live_measured/nasa/nasa_20260701T145937Z.json` | `5fbb51f41cfb3ff2326e7a30fe3c3c9a5c713c0c4eb59208be50f0afb1f4f3d3` |
| NOAA_NCEI | weather | MEASURED | 11 | `data/live_measured/noaa_ncei/noaa_ncei_20260701T145937Z.json` | `1c7aee2f8a47119a16ec06784412ddac6a16a30777d4921313c43023a60bbe75` |
| NWS_PUBLIC | weather | MEASURED | 50 | `data/live_measured/nws_public/nws_public_20260701T145937Z.json` | `b15b2528cb3012d5c7ebc9c2782b9ddc65869bd4471aa40748ace5e0defd960f` |
| OPEN_METEO_PUBLIC | weather | MEASURED | 48 | `data/live_measured/open_meteo_public/open_meteo_public_20260701T145937Z.json` | `d1461657c1896b005420acc451ce5a39d1e39800f9f213dca879b9255099ba97` |
| NREL | energy_lab | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/nrel/nrel_20260701T145937Z.json` | `f22b97af0ab2cc0b387ee08553095039419606ce39ff639979f240e733e3c559` |
| USGS_WATER | water | MEASURED | 1 | `data/live_measured/usgs_water/usgs_water_20260701T145937Z.json` | `0c8dc34db4dd897b5e1017935eda3cd2d3c06eaab081502223f6578b9bd1c769` |
| CENSUS | demographic | MEASURED | 1 | `data/live_measured/census/census_20260701T145937Z.json` | `6d0f50c3808dd9b3d43604576c96dc9bfd911ae0f8e92983f6f124c0f04ba549` |
| BEA | macro | MEASURED | 13 | `data/live_measured/bea/bea_20260701T145937Z.json` | `54b03e2109873bd71d1a8bfac8e1d8c928c1ff30c8ee6d3c1dcb9c7042a26cbf` |
| EPA_AQS | air_quality | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/epa_aqs/epa_aqs_20260701T145937Z.json` | `00739f070929059e016fe9389e880cbbf086386c65f2637a906bfa24b88bb0a6` |
| AIRNOW | air_quality | MEASURED | 3 | `data/live_measured/airnow/airnow_20260701T145937Z.json` | `a5f43a1e2467072c09559422b9d45ce2d4a2a5691dd40fab111817daa8bb6767` |
| THE_ODDS_API | sports_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/the_odds_api/the_odds_api_20260701T145937Z.json` | `1ce885e090d6869fdc1710c5f8f6500ba3a7beefd37ca8adea1af57f9dd491b8` |
| SAM_GOV | federal_opportunity | UNCONFIGURED | 0 | `data/live_measured/sam_gov/sam_gov_20260701T145937Z.json` | `c4144529f544b83d4f75e37169a4604f60187eb6325a1f2ade6076d970c056dc` |
| GRANTS_GOV | federal_opportunity | MEASURED | 50 | `data/live_measured/grants_gov/grants_gov_20260701T145937Z.json` | `7613ef135f9e18ed3bc000c9fef5cc6c3816ad555acab02f53806a9f00c8a521` |
| WEBHOOK | internal | MEASURED | 1 | `data/live_measured/webhook/webhook_20260701T145937Z.json` | `5be16308511ecce8a5d4a4823ba50c13f657de6f8fc70aad4b70286222658755` |
| TREASURY_FISCAL_PUBLIC | rates | MEASURED | 50 | `data/live_measured/treasury_fiscal_public/treasury_fiscal_public_20260701T145937Z.json` | `2110ac10c5c0e91c913e0e8738e2e79872e81deba50fbad36116eb0ebc5904a9` |
| SEC_PUBLIC | market_data | MEASURED | 50 | `data/live_measured/sec_public/sec_public_20260701T145937Z.json` | `d11ae465f04ed44302e996f3269528c6d64e42c95780dd21f486d314b20d0c61` |
| COINBASE_PUBLIC | crypto_market | MEASURED | 50 | `data/live_measured/coinbase_public/coinbase_public_20260701T145937Z.json` | `856dd722db164a6b807ac48ed024542c18204a79c027ea4f4cd173428a58928a` |
| WORLD_BANK_PUBLIC | macro | MEASURED | 1 | `data/live_measured/world_bank_public/world_bank_public_20260701T145937Z.json` | `9712f9cc6b583c3384d68b08c2289c8bb5a616992cfaec6663a921bc79a152a6` |
