# Measured Source Evidence Register - 2026-07-09

Purpose: make the live-source proof layer inspectable for reviewers without inflating it into a result, award, or operating claim.

This register is an evidence inventory. It does not authorize source-rights claims, field validation language, realized savings language, final submissions, live trading, or autonomous external actions.

## Status

- Status: `MEASURED_SOURCE_REGISTER_READY_RECONCILIATION_REQUIRED`
- Register SHA-256: `3ca5e02058d33007a34bf98f54f760edc9e9e79ec7d5290839beb3265229541d`
- Registry-backed sources: `17`
- Registry-backed enabled sources: `17`
- Registry-backed measured sources: `11`
- Registry-backed hash-backed measured sources: `0`
- Registry-backed measured rows: `44`
- Registry coverage: `64.71`%
- Current probe sources: `28`
- Current probe enabled sources: `27`
- Current probe measured sources: `23`
- Current probe hash-backed measured sources: `23`
- Current probe measured rows: `2377`
- Current probe coverage: `85.19`%
- Registry-only sources: `ALPACA, KRAKEN`
- Registry-only measured rows awaiting current hash refresh: `1`
- Registry measured without snapshot hash: `ALPACA`
- Reconciliation required: `true`
- Geometry manifest unique sources: `204`
- Geometry manifest materialized rows: `500`
- Geometry manifest discovered rows: `603`
- Geometry manifest omitted rows disclosed: `103`
- Field validation claim allowed: `false`
- Customer outcome value claim allowed: `false`
- Award value claim allowed: `false`
- Source authority claimed: `false`
- Live trading allowed: `false`
- Autonomous external action allowed: `false`

## Reconciliation Note

The registry is a merged continuity layer. The current probe array is the latest measurement run. Sources measured in the registry but absent from the current probe, or lacking snapshot hashes, remain useful context but require refresh before being called current hash-backed evidence.

## Current Kuramoto Head-to-Head

- Integrity pass: `true`
- Status: `NO_CROSS_SECTOR_EFFICIENCY_GAIN_PROVEN`
- Measured retrospective sources: `6`
- Rolling evaluation origins: `786`
- Protocol-matched strategies: `10`
- Positive exploratory sectors: `0`
- Proven sector gains: `0`
- Frozen EIA anchor is negative: `true`
- Cross-sector efficiency claim allowed: `false`
- Realized-savings claim allowed: `false`
- Evidence chain SHA-256: `5538aafe96b331bf3125f85e113bc2efb74a153fe81e507b5602187e4493f0a1`
- Artifact chain SHA-256: `610389ac85972219224bac53d55aa29546e84268475a5121a522136988ff9e88`

The current result is negative evidence: it narrows the next external test and must not be rewritten as a performance or economic win.

## Allowed Language

- 17-source canonical registry with 17 currently enabled sources
- 30 merged source rows across the canonical registry and current probe
- current-probe measured source rows when snapshot hashes are present
- bounded estimated-value context under stated assumptions
- source coverage for reviewer diligence and benchmark routing
- the current governed Kuramoto comparison reports zero proven sector gains

## Blocked Language

- Do not claim field validation.
- Do not claim realized savings.
- Do not claim guaranteed award.
- Do not claim source authority.
- Do not claim trading profit.
- Do not claim autonomous execution approval.
- Do not claim Kuramoto cross-sector efficiency.
- Do not claim Kuramoto-attributable dollar savings.

## Source Rows

| Source | Sector | Evidence tier | Registry measured | Current measured | Rows | Hash-backed | Snapshot SHA-256 |
|---|---|---|---:|---:|---:|---:|---|
| AIRNOW | air_quality | CURRENT_HASHED_MEASURED_SOURCE | false | true | 3 | true | `295c8aa80588599355815ac10cfadc03886b9d07661982818e03c7469af504b1` |
| ALPHAVANTAGE | market_data | CURRENT_HASHED_MEASURED_SOURCE | false | true | 100 | true | `4f98a6b0e7f569fd2d7a46760cf98eb80a0850efd2e2ce7e502fdf01f96ca5b9` |
| BEA | macro | CURRENT_HASHED_MEASURED_SOURCE | true | true | 13 | true | `fc6f2a3d3cf8c145c751376781ddbf6fc0a87be549b236940eaa482d64b091a4` |
| BLS | labor | CURRENT_HASHED_MEASURED_SOURCE | false | true | 30 | true | `7c1756fb4919c157d9b7600da961f050da54c340af97a65e8ced58a0a674c0ad` |
| CENSUS | demographic | CURRENT_HASHED_MEASURED_SOURCE | true | true | 1 | true | `816230ecd8b6a245f59507f2abed47a3efe1b91acc351902dce75a93fc7aee89` |
| COINBASE_PUBLIC | crypto_market | CURRENT_HASHED_MEASURED_SOURCE | false | true | 250 | true | `c63e292c9679e2002bba39c074d49457ee1591ab199ca1332f49a98e7fba306c` |
| COINGECKO_PUBLIC | crypto_market | CURRENT_HASHED_MEASURED_SOURCE | false | true | 6 | true | `cec133ada002b2738a36c722ad77cacbf389d20b007ac26d8773e1a23401e433` |
| EIA | energy | CURRENT_HASHED_MEASURED_SOURCE | true | true | 250 | true | `6bd7a5a1ce9f7b1f309fce9337ccabf87c7d05cd8d26d58df571ec91f04cec86` |
| FINNHUB | market_data | CURRENT_HASHED_MEASURED_SOURCE | true | true | 4 | true | `da84c3c8f69b429edb6299b43637faf67b2e5d0d0e443ed484dba5fe967ece78` |
| FRED | rates | CURRENT_HASHED_MEASURED_SOURCE | true | true | 248 | true | `5c0c4a4809c24f80b700f1da8d14077e1225ba68d3ef38a97a1596af883b91c2` |
| GRANTS_GOV | federal_opportunity | CURRENT_HASHED_MEASURED_SOURCE | false | true | 250 | true | `a4b990723126847ea78fb9b4fa905829d536220546ef2828cc34f7c37baf5cc6` |
| KRAKEN_PUBLIC | crypto_market | CURRENT_HASHED_MEASURED_SOURCE | false | true | 250 | true | `38cee5af65406459ebd0e56ad241ed76f69862623ec7ddbff94b663381a05875` |
| MASSIVE | market_data | CURRENT_HASHED_MEASURED_SOURCE | false | true | 3 | true | `fc1c63d3827049452f126b1bed1b4434f396c61eebdf2a7e0d7705c9e4a8fc9d` |
| NASA | space | CURRENT_HASHED_MEASURED_SOURCE | true | true | 1 | true | `f168ff9471246672ec138599f56875e96ad9074094f0fb4327db2174e014fbcc` |
| NOAA_NCEI | weather | CURRENT_HASHED_MEASURED_SOURCE | true | true | 11 | true | `f65cd57b5757cbf28a22f21d611e5c14a509b85376e8e6bbfa4da317a8b65f47` |
| NWS_PUBLIC | weather | CURRENT_HASHED_MEASURED_SOURCE | false | true | 156 | true | `38cc1a3ca500522b24bcb6a19537e416fc42b46cc550baf32b2894a624282017` |
| OPEN_METEO_PUBLIC | weather | CURRENT_HASHED_MEASURED_SOURCE | false | true | 48 | true | `6cc3428731618df733f369945c600f479c2080aadfc34881c74da1045278dcbd` |
| SEC_PUBLIC | market_data | CURRENT_HASHED_MEASURED_SOURCE | false | true | 250 | true | `53cf06bd1f0d75ceda98091ae8c4f9e278adcdd313ac010b5141d0e5ccc14081` |
| TREASURY_FISCAL_PUBLIC | rates | CURRENT_HASHED_MEASURED_SOURCE | false | true | 250 | true | `b330e3b11aee6cb885391b530787b0e53ec17c91b7e6823674e9ac3721e3852b` |
| TWELVE_DATA | market_data | CURRENT_HASHED_MEASURED_SOURCE | true | true | 250 | true | `356de5123d56f17e55821814e629785c39e17382f1104314976566362aa6cc0e` |
| USGS_WATER | water | CURRENT_HASHED_MEASURED_SOURCE | true | true | 1 | true | `9c55227d8925fb25a8f743aabf4845642e89a148805c86a5ea43a00e80ef5e31` |
| WEBHOOK | internal | CURRENT_HASHED_MEASURED_SOURCE | true | true | 1 | true | `b77f78e31583947dfb1289281730b1170f62592ac20ce30912061ccfc654a91e` |
| WORLD_BANK_PUBLIC | macro | CURRENT_HASHED_MEASURED_SOURCE | false | true | 1 | true | `996c5aa6c78856cc9583b0255a87f7f8268e79967722511c73ee0634771325c2` |
| ALPACA | broker | REGISTRY_MEASURED_NEEDS_HASH_REFRESH | true | false | 1 | false | `` |
| BINANCE_PUBLIC | crypto_market | CURRENT_PROBE_UNMEASURED_OR_THIN | false | false | 0 | true | `3be8454a0e681298185f3856a8fadb7513d2991f9ddbee838ccdcc1ed83c63c3` |
| EPA_AQS | air_quality | CURRENT_PROBE_UNMEASURED_OR_THIN | false | false | 0 | true | `acce89d7b0bf4333d9b161245ffcb232f0ed8b24a89c1bb0f11bfa27b784db96` |
| KRAKEN | crypto_exec | REGISTRY_UNMEASURED_OR_DISABLED | false | false | 0 | false | `` |
| NREL | energy_lab | CURRENT_PROBE_UNMEASURED_OR_THIN | false | false | 0 | true | `49746fcde2ad77d932ec1405f5d3c2864ad8eaeb367945b3ac5a82bf9a338031` |
| SAM_GOV | federal_opportunity | CURRENT_PROBE_UNMEASURED_OR_THIN | false | false | 0 | true | `b09fdcfabfcf01bee493684bb15c767ac44df4b61aa368bf40519a398d736b63` |
| THE_ODDS_API | sports_market | CURRENT_PROBE_UNMEASURED_OR_THIN | false | false | 0 | true | `0adef2b1e3986ab8a5d646a9a2dc8e6549a42369cb0e015dedf434408ee800b0` |

## Evidence Sources

- `config/live_source_registry.json` | present=`true` | bytes=`16215` | sha256=`d291c441158c77358ce4eb974e266aa83580f0db067f1e45ab097654c9e9cb4f`
- `out/ops/live_source_measurement_maximizer_latest.json` | present=`true` | bytes=`39808` | sha256=`a208ea39d59574cc501d9920d402e2a277a7804afd9c3dfd88f8ca7db063646b`
- `out/ops/geometry_live_source_manifest_latest.json` | present=`true` | bytes=`469686` | sha256=`d2ffa4c4b9c6c431ec79fd56bd057378ddcf36002069ac8c4702d5bbd82af519`
- `out/ops/claim_strength_value_unlock_map_latest.json` | present=`true` | bytes=`17394` | sha256=`b8649042dba25db2061b7a2bdaa95b4387d6db7622159eb822c5a18ccbe1a3b4`
- `out/ops/kuramoto_cross_sector_benchmark_latest.json` | present=`true` | bytes=`75338` | sha256=`a86a522ad72dbbd94142c729bdd65f41b14657b4d684d2270245c4df231686ad`
- `out/ops/kuramoto_cross_sector_benchmark_manifest_latest.json` | present=`true` | bytes=`5180` | sha256=`950598e800ab192c735748b988c6133bbe97af4cf7f6966b8ed927d6408b3f1b`
- `grant_submissions/funding_sprint_20260709/PROOF_STACK_EDGE_INDEX_2026-07-09.md` | present=`true` | bytes=`6754` | sha256=`3a814a6751a89939d540381a20acd7eaa0ccec1b970d045191dc64d7a5b49596`
