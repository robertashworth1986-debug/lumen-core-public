# Live Source Measurement Maximizer

Generated UTC: `2026-07-05T20:56:54.923834+00:00`

## Summary

- Enabled sources: 29
- Measured sources: 25
- Failed/thin sources: 4
- Total measured rows: 1506
- Coverage: 86.21%
- Estimated annual value surface: $20,586,213,130.80
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
| KRAKEN_PUBLIC | crypto_market | MEASURED | 120 | `data/live_measured/kraken_public/kraken_public_20260705T205627Z.json` | `d272bc162591e2f19c14010ad574cb407c43890570120f7587fd3714ad4ee6b0` |
| BINANCE_PUBLIC | crypto_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/binance_public/binance_public_20260705T205627Z.json` | `b2a3ae4833b28e3019aa81c1f9d2af75a69655f6517468115626a754c489e1e6` |
| COINGECKO_PUBLIC | crypto_market | MEASURED | 6 | `data/live_measured/coingecko_public/coingecko_public_20260705T205627Z.json` | `93d181c78e03e0359a5014bd403745ab4364be88423377e32aa84aaa53346676` |
| FINNHUB | market_data | MEASURED | 4 | `data/live_measured/finnhub/finnhub_20260705T205627Z.json` | `bff7aefa476d3809dbcdad7f576f900ff2f086c149d6fdc89048ed9a3aaa89ab` |
| ALPHAVANTAGE | market_data | MEASURED | 100 | `data/live_measured/alphavantage/alphavantage_20260705T205627Z.json` | `7fdbe2062edd70d54ec2f1e602c624fb023f7ee730ed2b803fae3e42ee42f9be` |
| TWELVE_DATA | market_data | MEASURED | 120 | `data/live_measured/twelve_data/twelve_data_20260705T205627Z.json` | `72f88b4f3e54d43bbbfd5921866e23186546db9b410f5a3cefe154b4558345f4` |
| MASSIVE | market_data | MEASURED | 3 | `data/live_measured/massive/massive_20260705T205627Z.json` | `d533baa94e09130a60eadddce0c3fdfb78461f3b679609506f75cb0917061277` |
| FRED | rates | MEASURED | 120 | `data/live_measured/fred/fred_20260705T205627Z.json` | `4ce6d7a6099525ce3183ae4ffe653374514da25e9e94be143b9d8f21a59ec4a0` |
| EIA | energy | MEASURED | 120 | `data/live_measured/eia/eia_20260705T205627Z.json` | `a0f54fea1c1b3ea7c4237cb5ae4c154a7be18bc254a0b3daad933fbe5932a704` |
| BLS | labor | MEASURED | 30 | `data/live_measured/bls/bls_20260705T205627Z.json` | `08e3b6524fc30b744f31f59dc3064d1dc2d66459f623d7a235b6194a5594cb7f` |
| NASA | space | MEASURED | 1 | `data/live_measured/nasa/nasa_20260705T205627Z.json` | `13677fa19710aacb7ba581f71c76b31a0708308469b6b5e87067e015f243963a` |
| NOAA_NCEI | weather | MEASURED | 11 | `data/live_measured/noaa_ncei/noaa_ncei_20260705T205627Z.json` | `d97edc605fe5b8fcb6016c678a92b54b3dd453b120b130186f30bdc16c08e836` |
| NWS_PUBLIC | weather | MEASURED | 120 | `data/live_measured/nws_public/nws_public_20260705T205627Z.json` | `7f51cda23cb2bcc60c957d7b4b9a29ce30f87dae2bf00df13462415ba21db432` |
| OPEN_METEO_PUBLIC | weather | MEASURED | 48 | `data/live_measured/open_meteo_public/open_meteo_public_20260705T205627Z.json` | `e69992bb92bf0bb650d06a1ad21334280bac37cd9d40aca3f8c2863be899bd6b` |
| NREL | energy_lab | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/nrel/nrel_20260705T205627Z.json` | `04712a682e014d3005104925cb3e3afa412d7c27b57b63d1781160fed1f673d3` |
| USGS_WATER | water | MEASURED | 1 | `data/live_measured/usgs_water/usgs_water_20260705T205627Z.json` | `ace094d050def9deb43320aaa9277f3206ba62421530f76b50577cefc7c33a7f` |
| CENSUS | demographic | MEASURED | 1 | `data/live_measured/census/census_20260705T205627Z.json` | `6049f00cc4351a00117fdd19926c329373184fb2a77abe646545cc70dbf8b875` |
| BEA | macro | MEASURED | 13 | `data/live_measured/bea/bea_20260705T205627Z.json` | `72ddc2d0cd7af67ec176a549107d2bf8c5321b15ccda2e36b860392462822848` |
| EPA_AQS | air_quality | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/epa_aqs/epa_aqs_20260705T205627Z.json` | `60f875da0b2fbe73cb150ad0724886338510785333452c8623c2451e226ffb92` |
| AIRNOW | air_quality | MEASURED | 3 | `data/live_measured/airnow/airnow_20260705T205627Z.json` | `39d8c636d0240eb01b06ef8d43d0a2677d51bc0182dd931109b13d4202056338` |
| THE_ODDS_API | sports_market | PROBE_FAILED_OR_THIN | 0 | `data/live_measured/the_odds_api/the_odds_api_20260705T205627Z.json` | `26922dd07f6eae473e6694f3f8eb7f0081964a124058ed49eed91ecf50e7282b` |
| SAM_GOV | federal_opportunity | UNCONFIGURED | 0 | `data/live_measured/sam_gov/sam_gov_20260705T205627Z.json` | `ecbeb42b43a9fd486e8724c00505cd91e6ed108745704c4efbf0fccb730dd2af` |
| GRANTS_GOV | federal_opportunity | MEASURED | 120 | `data/live_measured/grants_gov/grants_gov_20260705T205627Z.json` | `4e0bf54842701e27420957ebe1008dfa836fecbf575b2269c91c1e3a9daaa53a` |
| WEBHOOK | internal | MEASURED | 1 | `data/live_measured/webhook/webhook_20260705T205627Z.json` | `4b8d80a6f1510adbb4ae8cc6d7708e83107b944e2ff9f4f54f1e05c23142694f` |
| TREASURY_FISCAL_PUBLIC | rates | MEASURED | 120 | `data/live_measured/treasury_fiscal_public/treasury_fiscal_public_20260705T205627Z.json` | `87b4cb29994995cc38f9346b0bc597941e5a65639ecf10935d80899eb0b238fd` |
| SEC_PUBLIC | market_data | MEASURED | 120 | `data/live_measured/sec_public/sec_public_20260705T205627Z.json` | `9b4b7d1b13f595c407c32dfba9813069c81ac8a18877bf124b05d1f34a43b36f` |
| COINBASE_PUBLIC | crypto_market | MEASURED | 120 | `data/live_measured/coinbase_public/coinbase_public_20260705T205627Z.json` | `e224b3e4f869d318791f378199beb4d3951d9787857f535edc923026aef4dddb` |
| WORLD_BANK_PUBLIC | macro | MEASURED | 1 | `data/live_measured/world_bank_public/world_bank_public_20260705T205627Z.json` | `bacac532a0b4523d36e08c1c30b3a350884944222f337cd05aac69e3126eb21e` |
