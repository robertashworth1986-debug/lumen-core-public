# Field Money Truth Sweep

Generated UTC: `2026-06-25T17:19:16.872205+00:00`

This sweep is a hard truth gate. It runs or reads the current live-evidence, geometry, proof, vault, and claim artifacts, then states which commercial claims are allowed. It does not turn field validation or real-dollar savings true unless buyer/agency-authorized field data, preregistered holdouts, named baselines, accepted economic conversion factors, and auditable result artifacts exist.

## Current Truth

- Registered families: `140`
- Live adapter replay count: `4`
- Measured sources / rows: `18` / `418`
- Candidate beats named baseline count: `4`
- Triple-source candidates: `1`
- Rolling champions: `4`
- Safe estimated value signal: `$4,520.00/hour`, `$39,595,200.00/year`
- Blocked context-only value surface: `$52,288,496,940.00/year`

## Gates

- registry_has_all_candidate_families: `true`
- all_families_have_benchmark_specs: `false`
- all_registered_families_live_benchmarked: `false`
- live_data_available_for_benchmarking: `true`
- double_dataset_frozen_assets_present: `true`
- triple_dataset_frozen_assets_present: `true`
- rolling_champion_present: `true`
- glyph_or_external_vault_routed: `true`
- vps_domain_live_dashboard_routed: `false`
- bounded_estimated_value_claim_allowed: `true`
- paid_pilot_scoping_allowed: `true`
- field_validation_claim_allowed: `false`
- real_dollar_savings_claim_allowed: `false`
- fixed_dollar_delta_sale_claim_allowed: `false`
- live_trading_or_autonomous_execution_allowed: `false`

## Allowed Claim Now

bounded estimated value signal plus paid pilot scoping: $4,520.00 / $39,595,200.00 under stated assumptions.

## Blockers

- Only 4 live adapter replay lanes are currently represented for 140 registered families. This blocks all-family validation language.
- Field validation requires buyer or agency authorized operational data, preregistered holdouts, named incumbent baselines, accepted economic conversion factors, and auditable signed or traceable results.
- Real dollar savings require field validation plus accepted economics. Estimated value is allowed; realized savings is blocked.
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

Truth-sweep hash: `405ce796c1af5af7e25ca17167a8430a9c5b65c36ecdbc6aa10958e5865c5c76`
