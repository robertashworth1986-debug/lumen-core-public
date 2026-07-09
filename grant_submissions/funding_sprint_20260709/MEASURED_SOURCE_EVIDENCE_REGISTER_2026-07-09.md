# Measured Source Evidence Register - 2026-07-09

Purpose: make the live-source proof layer inspectable for reviewers without inflating it into a result, award, or operating claim.

This register is an evidence inventory. It does not authorize source-rights claims, field validation language, realized savings language, final submissions, live trading, or autonomous external actions.

## Status

- Status: `MEASURED_SOURCE_REGISTER_READY_RECONCILIATION_REQUIRED`
- Register SHA-256: `2acd6d5b2b640fd8522fa3796687594496b507a6c311705d27dc1f529e0bdb46`
- Registry-backed sources: `30`
- Registry-backed enabled sources: `29`
- Registry-backed measured sources: `25`
- Registry-backed hash-backed measured sources: `23`
- Registry-backed measured rows: `2580`
- Current probe sources: `28`
- Current probe enabled sources: `27`
- Current probe measured sources: `23`
- Current probe hash-backed measured sources: `23`
- Current probe measured rows: `2377`
- Registry-only sources: `ALPACA, KRAKEN`
- Registry measured without snapshot hash: `ALPACA, KRAKEN`
- Reconciliation required: `true`
- Geometry manifest unique sources: `204`
- Geometry manifest rows: `551`
- Field validation claim allowed: `false`
- Customer outcome value claim allowed: `false`
- Award value claim allowed: `false`
- Source authority claimed: `false`
- Live trading allowed: `false`
- Autonomous external action allowed: `false`

## Reconciliation Note

The registry is a merged continuity layer. The current probe array is the latest measurement run. Sources measured in the registry but absent from the current probe, or lacking snapshot hashes, remain useful context but require refresh before being called current hash-backed evidence.

## Allowed Language

- registry-backed 29-source inventory
- current-probe measured source rows when snapshot hashes are present
- bounded estimated-value context under stated assumptions
- source coverage for reviewer diligence and benchmark routing

## Blocked Language

- Do not claim field validation.
- Do not claim realized savings.
- Do not claim guaranteed award.
- Do not claim source authority.
- Do not claim trading profit.
- Do not claim autonomous execution approval.

## Source Rows

| Source | Sector | Evidence tier | Registry measured | Current measured | Rows | Hash-backed | Snapshot SHA-256 |
|---|---|---|---:|---:|---:|---:|---|
| AIRNOW | air_quality | CURRENT_HASHED_MEASURED_SOURCE | true | true | 3 | true | `b73d64d3d4166fb56239ab85ae8645a511d2c3db2edcdf1e6da50be0d700a5fa` |
| ALPHAVANTAGE | market_data | CURRENT_HASHED_MEASURED_SOURCE | true | true | 100 | true | `8e0cb6763783a5585be34f978713b9cab028865505b3169eb75444e729305520` |
| BEA | macro | CURRENT_HASHED_MEASURED_SOURCE | true | true | 13 | true | `dc33a3efdacc8f2d49e6a20201b586c98e82eab2edca0d4fef60f123f70dc7a6` |
| BLS | labor | CURRENT_HASHED_MEASURED_SOURCE | true | true | 30 | true | `df3ff0dc9b2bb42a5d70c4de09ccce9d9b9c3654125ef2118bc2574897bbd144` |
| CENSUS | demographic | CURRENT_HASHED_MEASURED_SOURCE | true | true | 1 | true | `6a6b1e623277eaf31ee2f33244c319f829a428002c60c4975e0efec7aa0d3274` |
| COINBASE_PUBLIC | crypto_market | CURRENT_HASHED_MEASURED_SOURCE | true | true | 250 | true | `2f19143980016e3e2d82225a670d5cb8389ad9248441b12a8322f15bec22ca5d` |
| COINGECKO_PUBLIC | crypto_market | CURRENT_HASHED_MEASURED_SOURCE | true | true | 6 | true | `8b975c39a3842802c96bbbc759d77f473758c7aa72490636d0d2830575c1c9ab` |
| EIA | energy | CURRENT_HASHED_MEASURED_SOURCE | true | true | 250 | true | `2ce7824a4c55692a840088910d0880671ce9c1e689705242419ccaa5c4671003` |
| FINNHUB | market_data | CURRENT_HASHED_MEASURED_SOURCE | true | true | 4 | true | `9f86539c927b7c00951919dc7867c730e8982cb8200077e5daaeece159992209` |
| FRED | rates | CURRENT_HASHED_MEASURED_SOURCE | true | true | 248 | true | `aee05642909c4f0dffc9f21113964db0ed0c2b89053589748a50a50e75710f6d` |
| GRANTS_GOV | federal_opportunity | CURRENT_HASHED_MEASURED_SOURCE | true | true | 250 | true | `e29c5f9834f04cc4e53c4264eb93adfff336aa2deab6f6b2ab7fd8e8bccf5c7e` |
| KRAKEN_PUBLIC | crypto_market | CURRENT_HASHED_MEASURED_SOURCE | true | true | 250 | true | `b4e6d9d6928ca82a95ebe7d3ea136cfbb040892c7b63d4ca35f8c7ac503f307a` |
| MASSIVE | market_data | CURRENT_HASHED_MEASURED_SOURCE | true | true | 3 | true | `d5d052e4a563b4deae8b3b1932844b6c33d9f8b6ea72cf26d686637388f29ecf` |
| NASA | space | CURRENT_HASHED_MEASURED_SOURCE | true | true | 1 | true | `131379a8ff6abb7a1223b03c166d3e5f8980de37ba7427073d0ca40691f8f0e0` |
| NOAA_NCEI | weather | CURRENT_HASHED_MEASURED_SOURCE | true | true | 11 | true | `68e8aad64e9b9fd0d642a15661f1e24c953e1b461466e565fe8e2350fd041db5` |
| NWS_PUBLIC | weather | CURRENT_HASHED_MEASURED_SOURCE | true | true | 156 | true | `ec0988170021b5e089a2a2c521f0813c21841d1840f7a9e66041df4b52cdfc2f` |
| OPEN_METEO_PUBLIC | weather | CURRENT_HASHED_MEASURED_SOURCE | true | true | 48 | true | `56e0bafb4065ba3807ad388b7d0b8c46fa730f129c52c7b1ed2c634313f633ce` |
| SEC_PUBLIC | market_data | CURRENT_HASHED_MEASURED_SOURCE | true | true | 250 | true | `99971d8a5ed3d8f65667517c0b4faa4f75e0db2e021602127fc770a0e35ed9c3` |
| TREASURY_FISCAL_PUBLIC | rates | CURRENT_HASHED_MEASURED_SOURCE | true | true | 250 | true | `f4eeeccda65ebcb486cb4f713685cf3658e9024d4c7debd1c4a0f402b470c386` |
| TWELVE_DATA | market_data | CURRENT_HASHED_MEASURED_SOURCE | true | true | 250 | true | `81e99282d5e94e60713b60bba4d74e5e8837ad2405af25a9eb1ddfbf2e6986bf` |
| USGS_WATER | water | CURRENT_HASHED_MEASURED_SOURCE | true | true | 1 | true | `160f0e53fd98ea34445bbd1258c6043a807a1d545ef69cf9ff0ace7ecc7dcda9` |
| WEBHOOK | internal | CURRENT_HASHED_MEASURED_SOURCE | true | true | 1 | true | `22fdceef38a876332d07f68468e9ef4ab89004de0f5bf15af30ae9bd93c9780a` |
| WORLD_BANK_PUBLIC | macro | CURRENT_HASHED_MEASURED_SOURCE | true | true | 1 | true | `2e297a5ab0afbced7a840789e02c7dc395b49c8eb5bd07846f8e3f1557939839` |
| ALPACA | broker | REGISTRY_MEASURED_NEEDS_HASH_REFRESH | true | false | 1 | false | `` |
| KRAKEN | crypto_exec | REGISTRY_MEASURED_NEEDS_HASH_REFRESH | true | false | 202 | false | `` |
| BINANCE_PUBLIC | crypto_market | CURRENT_PROBE_UNMEASURED_OR_THIN | false | false | 0 | true | `e59c8b79f5b264ba573365430161c90fe59b211ef720ed3e3b36a01fd29074ae` |
| EPA_AQS | air_quality | CURRENT_PROBE_UNMEASURED_OR_THIN | false | false | 0 | true | `724e6a208ada7eed97567ea31723dc86ab6f780e019e383ec86df33f2ae0d95f` |
| NREL | energy_lab | CURRENT_PROBE_UNMEASURED_OR_THIN | false | false | 0 | true | `90acadbeece36b3b691301ded2625b16e2e053b8f48f8415d430dd0fd60d7af2` |
| SAM_GOV | federal_opportunity | CURRENT_PROBE_UNMEASURED_OR_THIN | false | false | 0 | true | `97a31a0ac6172d7dfbf317bb16a70db2af43969e0bb2d23fb15863172487a1ba` |
| THE_ODDS_API | sports_market | CURRENT_PROBE_UNMEASURED_OR_THIN | false | false | 0 | true | `ef73603a11f6eb8bff9652f3d68ef7da29a7efaa80955495ab0e0ab9ae588837` |

## Evidence Sources

- `config/live_source_registry.json` | present=`true` | bytes=`38633` | sha256=`335fdb50dd703edc64f76c617543acb32a855c013af93403787b466e537a8827`
- `out/ops/live_source_measurement_maximizer_latest.json` | present=`true` | bytes=`39808` | sha256=`1f9a036f47df94f49e27f2ee39273791b503f9c1dd85d06e3bd3d17f230ec4f9`
- `out/ops/geometry_live_source_manifest_latest.json` | present=`true` | bytes=`479434` | sha256=`c0a1bcadf4409e982898997c789fb109f7117f5d5ab5fc41c289cf534073a69e`
- `out/ops/claim_strength_value_unlock_map_latest.json` | present=`true` | bytes=`17394` | sha256=`b8649042dba25db2061b7a2bdaa95b4387d6db7622159eb822c5a18ccbe1a3b4`
- `grant_submissions/funding_sprint_20260709/PROOF_STACK_EDGE_INDEX_2026-07-09.md` | present=`true` | bytes=`6754` | sha256=`3a814a6751a89939d540381a20acd7eaa0ccec1b970d045191dc64d7a5b49596`
