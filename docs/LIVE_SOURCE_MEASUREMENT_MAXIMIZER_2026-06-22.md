# Live Source Measurement Maximizer

Generated UTC: `2026-07-11T13:24:37.672963+00:00`

## Summary

- Enabled sources: 29
- Measured sources: 25
- Failed/thin sources: 4
- Total measured rows: 2940
- Coverage: 86.21%
- Estimated annual value surface: $22,926,347,617.20
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
| KRAKEN_PUBLIC | crypto_market | MEASURED | 300 | `data/live_measured/kraken_public/kraken_public_20260711T132415Z.json` | `07166ae8b2a9e246d10c98cf959ddbd19a5410e5e2b913b2f982bd54b9d48963` |
| BINANCE_PUBLIC | crypto_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/binance_public/binance_public_20260711T132415Z.json` | `26460c3e3636ed849ee1122dd996c4f39d4e1aa70d7bbce158762328b5654ef0` |
| COINGECKO_PUBLIC | crypto_market | MEASURED | 6 | `data/live_measured/coingecko_public/coingecko_public_20260711T132415Z.json` | `497851f72bd09299b5a366b3543f3a6fdced5e0ca20a64045dc905638233007d` |
| FINNHUB | market_data | MEASURED | 4 | `data/live_measured/finnhub/finnhub_20260711T132415Z.json` | `07736042be43fcea4150985d7e232ae9acca813dea1564ae811b88548352d43a` |
| ALPHAVANTAGE | market_data | MEASURED | 100 | `data/live_measured/alphavantage/alphavantage_20260711T132415Z.json` | `305403d94ffb9fa17f85a1ca8f6d605d12f59c576b51518c739ad11b351007ab` |
| TWELVE_DATA | market_data | MEASURED | 300 | `data/live_measured/twelve_data/twelve_data_20260711T132415Z.json` | `eb4b2fe416d91cee77c7054488d4db028afbe51c901a0da00b4c0301ff2e5acf` |
| MASSIVE | market_data | MEASURED | 3 | `data/live_measured/massive/massive_20260711T132415Z.json` | `1a4cfef058be4ef3fe089506b62fdef50f0f2daf55d6b22148b3426e90af23c0` |
| FRED | rates | MEASURED | 300 | `data/live_measured/fred/fred_20260711T132415Z.json` | `a25b593fb2fbab47a3a959bd28ca4ecad9720ffbef5cbb8a22607bdbd3bfbf01` |
| EIA | energy | MEASURED | 300 | `data/live_measured/eia/eia_20260711T132415Z.json` | `99df72507f5c9ae461818cbae68a08b9f11c1cba9d51f5cc8146f9ee91ad83dc` |
| BLS | labor | MEASURED | 30 | `data/live_measured/bls/bls_20260711T132415Z.json` | `ec442c24f3c4c74d7104c647a6eefb5b5c96e9a12d1acf5ad3d797eb86e7c289` |
| NASA | space | MEASURED | 1 | `data/live_measured/nasa/nasa_20260711T132415Z.json` | `2854ceb9cae456595dbe86bb2c3d8c5b86f4f173d1d1f1c99bbd1aea7332598c` |
| NOAA_NCEI | weather | MEASURED | 11 | `data/live_measured/noaa_ncei/noaa_ncei_20260711T132415Z.json` | `43bbf28ba06ddc0ad42975509bfe4eff21a235f9a85bf5c013f718ca0e0da8aa` |
| NWS_PUBLIC | weather | MEASURED | 156 | `data/live_measured/nws_public/nws_public_20260711T132415Z.json` | `28574d15a88b8c3a3a3e9bd57abe5572852f2bf65066379e46470d0f7d1caa09` |
| OPEN_METEO_PUBLIC | weather | MEASURED | 48 | `data/live_measured/open_meteo_public/open_meteo_public_20260711T132415Z.json` | `46a11ef8eb13542cde16b36c4125c070f17eece9074745ff6294d83f59ef8a5a` |
| NREL | energy_lab | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/nrel/nrel_20260711T132415Z.json` | `daca0ed3cfa4bf0654d4a48e0e5d4585eb46c1abe6b7e3b7090175e3c61ef350` |
| USGS_WATER | water | MEASURED | 1 | `data/live_measured/usgs_water/usgs_water_20260711T132415Z.json` | `61349bf6484c389f117a14478cf39713def6f6c395094eb6d9b69e180172f25f` |
| CENSUS | demographic | MEASURED | 1 | `data/live_measured/census/census_20260711T132415Z.json` | `515c6076ed7da6c62efe9bdddc7ee37bff2d53cdc5e19f1dd9666476d3f1766e` |
| BEA | macro | MEASURED | 13 | `data/live_measured/bea/bea_20260711T132415Z.json` | `8b5e04c9478c1c83381424b98a965481b9772f5a08cb46398e70202ca6eb6015` |
| EPA_AQS | air_quality | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/epa_aqs/epa_aqs_20260711T132415Z.json` | `39a7056ac0fbb8a486ba1f7eeda4c4150e54ca1a575f9e0387506efacd4fb16f` |
| AIRNOW | air_quality | MEASURED | 3 | `data/live_measured/airnow/airnow_20260711T132415Z.json` | `b92ecec889c6a54beddd4942a08e99192bea0132a673301281e5a2db37216f3a` |
| THE_ODDS_API | sports_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/the_odds_api/the_odds_api_20260711T132415Z.json` | `1acc22e320d192b63b323d569b7e44551e065c8b699dd41ec6ee55a08ae64af1` |
| SAM_GOV | federal_opportunity | UNCONFIGURED | 0 | `data/live_measured/sam_gov/sam_gov_20260711T132415Z.json` | `3f1a64ac44449e502792cdb504ff98d16a17e07d2c4f2fc95164760f342d9c41` |
| GRANTS_GOV | federal_opportunity | MEASURED | 258 | `data/live_measured/grants_gov/grants_gov_20260711T132415Z.json` | `e107562047022294ade015b8ac46935c56dd302920c90c20bebd2ddfab232089` |
| WEBHOOK | internal | MEASURED | 1 | `data/live_measured/webhook/webhook_20260711T132415Z.json` | `34913602ab07267a24998122b44dbb9942b19f4fe6dc7f0e61843b64066bae5d` |
| TREASURY_FISCAL_PUBLIC | rates | MEASURED | 300 | `data/live_measured/treasury_fiscal_public/treasury_fiscal_public_20260711T132415Z.json` | `bd617210eca71310b8863d1916b56f6f8f4ef8530fbd1b73d68b8117c541e959` |
| SEC_PUBLIC | market_data | MEASURED | 300 | `data/live_measured/sec_public/sec_public_20260711T132415Z.json` | `c146593894f77976a28e4aa74eef6b4b458fed9eef6a4072915b5fd1b151b896` |
| COINBASE_PUBLIC | crypto_market | MEASURED | 300 | `data/live_measured/coinbase_public/coinbase_public_20260711T132415Z.json` | `2473621294112fcd5623b03b2fe03d6a8cef19fc49667fcc4e452661ecd3decf` |
| WORLD_BANK_PUBLIC | macro | MEASURED | 1 | `data/live_measured/world_bank_public/world_bank_public_20260711T132415Z.json` | `f11e8ae95cb44ecc77d5a62e83c2d026b8a5255b1ed788d80a5f69a9d0633197` |
