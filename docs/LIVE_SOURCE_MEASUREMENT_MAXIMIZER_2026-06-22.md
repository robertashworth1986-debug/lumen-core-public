# Live Source Measurement Maximizer

Generated UTC: `2026-07-13T19:27:13.908831+00:00`

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
| KRAKEN_PUBLIC | crypto_market | MEASURED | 250 | `data/live_measured/kraken_public/kraken_public_20260713T192646Z.json` | `38cee5af65406459ebd0e56ad241ed76f69862623ec7ddbff94b663381a05875` |
| BINANCE_PUBLIC | crypto_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/binance_public/binance_public_20260713T192646Z.json` | `3be8454a0e681298185f3856a8fadb7513d2991f9ddbee838ccdcc1ed83c63c3` |
| COINGECKO_PUBLIC | crypto_market | MEASURED | 6 | `data/live_measured/coingecko_public/coingecko_public_20260713T192646Z.json` | `cec133ada002b2738a36c722ad77cacbf389d20b007ac26d8773e1a23401e433` |
| FINNHUB | market_data | MEASURED | 4 | `data/live_measured/finnhub/finnhub_20260713T192646Z.json` | `da84c3c8f69b429edb6299b43637faf67b2e5d0d0e443ed484dba5fe967ece78` |
| ALPHAVANTAGE | market_data | MEASURED | 100 | `data/live_measured/alphavantage/alphavantage_20260713T192646Z.json` | `4f98a6b0e7f569fd2d7a46760cf98eb80a0850efd2e2ce7e502fdf01f96ca5b9` |
| TWELVE_DATA | market_data | MEASURED | 250 | `data/live_measured/twelve_data/twelve_data_20260713T192646Z.json` | `356de5123d56f17e55821814e629785c39e17382f1104314976566362aa6cc0e` |
| MASSIVE | market_data | MEASURED | 3 | `data/live_measured/massive/massive_20260713T192646Z.json` | `fc1c63d3827049452f126b1bed1b4434f396c61eebdf2a7e0d7705c9e4a8fc9d` |
| FRED | rates | MEASURED | 248 | `data/live_measured/fred/fred_20260713T192646Z.json` | `5c0c4a4809c24f80b700f1da8d14077e1225ba68d3ef38a97a1596af883b91c2` |
| EIA | energy | MEASURED | 250 | `data/live_measured/eia/eia_20260713T192646Z.json` | `6bd7a5a1ce9f7b1f309fce9337ccabf87c7d05cd8d26d58df571ec91f04cec86` |
| BLS | labor | MEASURED | 30 | `data/live_measured/bls/bls_20260713T192646Z.json` | `7c1756fb4919c157d9b7600da961f050da54c340af97a65e8ced58a0a674c0ad` |
| NASA | space | MEASURED | 1 | `data/live_measured/nasa/nasa_20260713T192646Z.json` | `f168ff9471246672ec138599f56875e96ad9074094f0fb4327db2174e014fbcc` |
| NOAA_NCEI | weather | MEASURED | 11 | `data/live_measured/noaa_ncei/noaa_ncei_20260713T192646Z.json` | `f65cd57b5757cbf28a22f21d611e5c14a509b85376e8e6bbfa4da317a8b65f47` |
| NWS_PUBLIC | weather | MEASURED | 156 | `data/live_measured/nws_public/nws_public_20260713T192646Z.json` | `38cc1a3ca500522b24bcb6a19537e416fc42b46cc550baf32b2894a624282017` |
| OPEN_METEO_PUBLIC | weather | MEASURED | 48 | `data/live_measured/open_meteo_public/open_meteo_public_20260713T192646Z.json` | `6cc3428731618df733f369945c600f479c2080aadfc34881c74da1045278dcbd` |
| NREL | energy_lab | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/nrel/nrel_20260713T192646Z.json` | `49746fcde2ad77d932ec1405f5d3c2864ad8eaeb367945b3ac5a82bf9a338031` |
| USGS_WATER | water | MEASURED | 1 | `data/live_measured/usgs_water/usgs_water_20260713T192646Z.json` | `9c55227d8925fb25a8f743aabf4845642e89a148805c86a5ea43a00e80ef5e31` |
| CENSUS | demographic | MEASURED | 1 | `data/live_measured/census/census_20260713T192646Z.json` | `816230ecd8b6a245f59507f2abed47a3efe1b91acc351902dce75a93fc7aee89` |
| BEA | macro | MEASURED | 13 | `data/live_measured/bea/bea_20260713T192646Z.json` | `fc6f2a3d3cf8c145c751376781ddbf6fc0a87be549b236940eaa482d64b091a4` |
| EPA_AQS | air_quality | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/epa_aqs/epa_aqs_20260713T192646Z.json` | `acce89d7b0bf4333d9b161245ffcb232f0ed8b24a89c1bb0f11bfa27b784db96` |
| AIRNOW | air_quality | MEASURED | 3 | `data/live_measured/airnow/airnow_20260713T192646Z.json` | `295c8aa80588599355815ac10cfadc03886b9d07661982818e03c7469af504b1` |
| THE_ODDS_API | sports_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/the_odds_api/the_odds_api_20260713T192646Z.json` | `0adef2b1e3986ab8a5d646a9a2dc8e6549a42369cb0e015dedf434408ee800b0` |
| SAM_GOV | federal_opportunity | UNCONFIGURED | 0 | `data/live_measured/sam_gov/sam_gov_20260713T192646Z.json` | `b09fdcfabfcf01bee493684bb15c767ac44df4b61aa368bf40519a398d736b63` |
| GRANTS_GOV | federal_opportunity | MEASURED | 250 | `data/live_measured/grants_gov/grants_gov_20260713T192646Z.json` | `a4b990723126847ea78fb9b4fa905829d536220546ef2828cc34f7c37baf5cc6` |
| WEBHOOK | internal | MEASURED | 1 | `data/live_measured/webhook/webhook_20260713T192646Z.json` | `b77f78e31583947dfb1289281730b1170f62592ac20ce30912061ccfc654a91e` |
| TREASURY_FISCAL_PUBLIC | rates | MEASURED | 250 | `data/live_measured/treasury_fiscal_public/treasury_fiscal_public_20260713T192646Z.json` | `b330e3b11aee6cb885391b530787b0e53ec17c91b7e6823674e9ac3721e3852b` |
| SEC_PUBLIC | market_data | MEASURED | 250 | `data/live_measured/sec_public/sec_public_20260713T192646Z.json` | `53cf06bd1f0d75ceda98091ae8c4f9e278adcdd313ac010b5141d0e5ccc14081` |
| COINBASE_PUBLIC | crypto_market | MEASURED | 250 | `data/live_measured/coinbase_public/coinbase_public_20260713T192646Z.json` | `c63e292c9679e2002bba39c074d49457ee1591ab199ca1332f49a98e7fba306c` |
| WORLD_BANK_PUBLIC | macro | MEASURED | 1 | `data/live_measured/world_bank_public/world_bank_public_20260713T192646Z.json` | `996c5aa6c78856cc9583b0255a87f7f8268e79967722511c73ee0634771325c2` |
