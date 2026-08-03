# Field Money Truth Sweep

Generated UTC: `2026-07-29T03:39:49.206159+00:00`

This sweep is a hard truth gate. It runs or reads the current live-evidence, geometry, proof, vault, and claim artifacts, then states which commercial claims are allowed. It does not turn field validation or real-dollar savings true unless buyer/agency-authorized field data, preregistered holdouts, named baselines, accepted economic conversion factors, and auditable result artifacts exist.

## Current Truth

- Registered families: `140`
- Live adapter replay count: `5`
- Measured sources / rows: `25` / `2580`
- Candidate beats named baseline count: `4`
- Triple-source rolling champions: `4`
- Triple-source candidates: `0`
- Rolling champions: `5`
- Claimable estimated value signal: `$0.00/hour`, `$0.00/year`

## Gates

- registry_has_all_candidate_families: `true`
- all_families_have_benchmark_specs: `true`
- all_registered_families_live_benchmarked: `false`
- live_data_available_for_benchmarking: `true`
- double_dataset_frozen_assets_present: `true`
- triple_dataset_frozen_assets_present: `true`
- rolling_champion_present: `true`
- glyph_or_external_vault_routed: `true`
- vps_domain_live_dashboard_routed: `false`
- bounded_estimated_value_claim_allowed: `false`
- paid_pilot_scoping_allowed: `true`
- field_validation_claim_allowed: `false`
- real_dollar_savings_claim_allowed: `false`
- fixed_dollar_delta_sale_claim_allowed: `false`
- live_trading_or_autonomous_execution_allowed: `false`

## Allowed Claim Now

bounded workflow pilot scoping with no dollar projection: $0.00 / $0.00. Quote only a scoped pilot fee; do not infer savings or model-performance value.

## Blockers

- Only 5 live adapter replay lanes are currently represented for 140 registered families. This blocks all-family validation language.
- Field validation requires buyer or agency authorized operational data, preregistered holdouts, named incumbent baselines, accepted economic conversion factors, and auditable signed or traceable results.
- No current lane clears the buyer-approved dollar-projection gate. Input projections remain suppressed.
- VPS/domain proof routing requires a verified deployed dashboard URL and fresh hosted artifact hashes; local dashboard JSON alone is not enough.

## Commands

Fresh live pull and vault stage:

```powershell
pwsh -ExecutionPolicy Bypass -File .\tools\Run-FieldMoneyTruthSweep.ps1 -FreshLivePull -StageGlyphVault
```
Fast run using existing snapshots:

```powershell
pwsh -ExecutionPolicy Bypass -File .\tools\Run-FieldMoneyTruthSweep.ps1 -StageGlyphVault
```

Truth-sweep hash: `e3b2f2bc1a629d36c44b7a74acf847ea6cc203508ec4e8eef9337f36daea0176`
