# LumenCore Architecture Discovery and Validation Engine

This engine inventories existing LumenCore architecture lanes and asks one question:

> What evidence is actually present, and what is the next falsifiable gate?

It is deliberately **read-only**. It does not mutate source architectures, canonical lexicons, constants, configurations, or private inventor disclosures.

## Outputs

- `architecture_registry.json` — complete machine-readable inventory
- `architecture_registry.md` — reviewer-readable ranking
- `experiment_queue.json` — missing evidence gates by architecture
- `hybrid_candidate_queue.json` — tests combining existing modules
- `scan_manifest.json` — SHA-256 evidence manifest

## Readiness classes

The score is an internal workflow score, not a technology-readiness level and not external validation:

1. `conceptual`
2. `model_ready`
3. `simulation_candidate`
4. `reproducibility_candidate`
5. `external_review_candidate`

The engine never assigns `externally_validated`. Only an independent qualified reviewer or buyer operating under agreed conditions can support that label.

## PowerShell

Repository only:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\research\architecture_validation\Run-ArchitectureValidation.ps1 `
  -RepoOnly -HashMatches
```

Repository plus known Luma roots:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\research\architecture_validation\Run-ArchitectureValidation.ps1 `
  -HashMatches
```

Known roots are included only when they exist:

- `C:\LumaTrader`
- `C:\LumenCore`
- `C:\LumaUniverse`
- `E:\INSTITUTIONAL_STACK_V2`
- `E:\GLYPH_DRIVE`

## Innovation boundary

The engine may propose a hybrid **experiment**, but it does not declare a new invention, rename founder concepts, publish private implementation details, alter canonical constants, or optimize against an unlocked objective.

A hybrid is promoted only if it:

- has both component baselines;
- has an uncoupled or naive control;
- locks metrics before tuning;
- uses disjoint validation conditions;
- retains failures and negative results;
- produces a manifest and claim boundary;
- passes patent-review gates when implementation details may be novel.
