# Live Source Measurement Maximizer

Generated UTC: `2026-07-01T11:22:33.917556+00:00`

## Summary

- Enabled sources: 23
- Measured sources: 17
- Failed/thin sources: 6
- Total measured rows: 465
- Coverage: 73.91%
- Estimated annual value surface: $7,236,217,096.80
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
- `NASA`
- `TWELVE_DATA`
- `USGS_WATER`
- `WEBHOOK`

## Failed Or Thin Sources

- `BINANCE_PUBLIC`
- `EIA`
- `EPA_AQS`
- `NOAA_NCEI`
- `NREL`
- `THE_ODDS_API`

## Provider Rows

| Source | Sector | Status | Rows | Snapshot | SHA-256 |
|---|---|---|---:|---|---|
| KRAKEN_PUBLIC | crypto_market | MEASURED | 40 | `data/live_measured/kraken_public/kraken_public_20260701T112145Z.json` | `af6d626fc68de74234152e09b41ad60c650a42702ef05b4203ddb6e639c81c0e` |
| BINANCE_PUBLIC | crypto_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/binance_public/binance_public_20260701T112145Z.json` | `33b233c88af5ee8eb6ddf82e1d47202ad12ad99342fe5e959cea781ee2b5145a` |
| COINGECKO_PUBLIC | crypto_market | MEASURED | 6 | `data/live_measured/coingecko_public/coingecko_public_20260701T112145Z.json` | `90a6ce36aa30634eb4462a364fb7bcd9e2439a665bcefc048cd893e1a54ca20e` |
| FINNHUB | market_data | MEASURED | 4 | `data/live_measured/finnhub/finnhub_20260701T112145Z.json` | `f8a5ff0d211a7df3a36ba5871967b4599f7cbe48e840ae59ee15e825cb468bd8` |
| ALPHAVANTAGE | market_data | MEASURED | 40 | `data/live_measured/alphavantage/alphavantage_20260701T112145Z.json` | `25a65714abc77dd267d2df5f7dd653b7168f61e984129f9dad7f48e9b7cfa476` |
| TWELVE_DATA | market_data | MEASURED | 40 | `data/live_measured/twelve_data/twelve_data_20260701T112145Z.json` | `727f0cafeb4088a7f70ba0ccc5d5625d5be38e339a766a2c652a4cdf5b196bc9` |
| MASSIVE | market_data | MEASURED | 3 | `data/live_measured/massive/massive_20260701T112145Z.json` | `73d0cf98d05bc859263ae0b6f05b4c2ad7108b5d1e1effdc31c27ba8d693cfc9` |
| FRED | rates | MEASURED | 40 | `data/live_measured/fred/fred_20260701T112145Z.json` | `af580a08135d1720a24802246395e9fd499860e572b19686059ea117e763ba85` |
| EIA | energy | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/eia/eia_20260701T112145Z.json` | `20601771b3ebf311467de3075798ba2d3111a3fd1670620927a4a4544b3e486c` |
| BLS | labor | MEASURED | 29 | `data/live_measured/bls/bls_20260701T112145Z.json` | `7042f3179a96181bd3702286195eb50b547131bc3cf540b95bd15bba26a7edb5` |
| NASA | space | MEASURED | 1 | `data/live_measured/nasa/nasa_20260701T112145Z.json` | `7638b84e3ff3ce1c97b6acdb0791cf1c23da1aaf0e3a368298f815a6b6dc9916` |
| NOAA_NCEI | weather | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/noaa_ncei/noaa_ncei_20260701T112145Z.json` | `8be8e9ff8b134680795f643b752fcf84df3f7d1bf1b5ca47a1f7a774fa2722b3` |
| NREL | energy_lab | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/nrel/nrel_20260701T112145Z.json` | `805f4d0cf8e914fbaebdf0b26761f43a4d272beaa6fd37fc6be50bada6249839` |
| USGS_WATER | water | MEASURED | 1 | `data/live_measured/usgs_water/usgs_water_20260701T112145Z.json` | `f690424bcf4aa518bc2c1546d9e09a7a95bf50cb094ef02891496c8288467c67` |
| CENSUS | demographic | MEASURED | 1 | `data/live_measured/census/census_20260701T112145Z.json` | `c3670f0330cfea756c7347b897720869eb48f81911ef7b25af8a042e229b573e` |
| BEA | macro | MEASURED | 13 | `data/live_measured/bea/bea_20260701T112145Z.json` | `9a489dd101e168290f82390e8663bfbd3af6a9907661fe94bc85107e9cd3dd9b` |
| EPA_AQS | air_quality | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/epa_aqs/epa_aqs_20260701T112145Z.json` | `0d6da6e5e0bb2c4e7d64dfacdaa405f1459da7bcfc696891e72718a7e0bec1b1` |
| AIRNOW | air_quality | MEASURED | 3 | `data/live_measured/airnow/airnow_20260701T112145Z.json` | `e75479891eb0893221f1d37e031554b3f891be5ed65eef81f2efd9665229c8c0` |
| THE_ODDS_API | sports_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/the_odds_api/the_odds_api_20260701T112145Z.json` | `e539556068e439f3f5dc479b14e21be1652bca743459b575565f4b3dc6d7ee93` |
| SAM_GOV | federal_opportunity | UNCONFIGURED | 0 | `data/live_measured/sam_gov/sam_gov_20260701T112145Z.json` | `09f62f74b3ea10d790df5bb6b07669f9a15fc36248819889df6d92786f73391d` |
| GRANTS_GOV | federal_opportunity | MEASURED | 40 | `data/live_measured/grants_gov/grants_gov_20260701T112145Z.json` | `365c4e0ea2ddc0370f9962c97d2641ae024f59331a430b04a326757de259a934` |
| WEBHOOK | internal | MEASURED | 1 | `data/live_measured/webhook/webhook_20260701T112145Z.json` | `e663f22d14b426752842de0a4372a1c20d19470a9a891697210168dae31a4c94` |
