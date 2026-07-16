# LumenCore Architecture Discovery and Validation Engine

**Status:** public-safe research and repository-audit tooling  
**Purpose:** discover candidate architectures, map each one to falsifiable validation work, and prevent unsupported claims from being promoted.

## Operating principle

The engine follows a gated path:

> discover -> fingerprint -> classify -> baseline -> lock metrics -> test -> retain failures -> checksum -> review -> promote

It does **not** autonomously rewrite canonical LumenCore architecture, publish private implementation details, make patent claims, or describe simulation output as external validation.

## What it scans

The runner can scan the connected repository and, when executed locally by Robert/Codex, additional authorized roots such as:

- `C:\LumenCore`
- `C:\LumaUniverse`
- `C:\LumaTrader`
- `E:\INSTITUTIONAL_STACK_V2`
- `E:\GLYPH_DRIVE`

Only file metadata, hashes, static source structure, and public-safe evidence signals are promoted by default. Canonical lexicon and constants files are read only for hashing unless Robert explicitly approves a private analysis path.

## Outputs

Each run produces:

- `architecture_inventory.json`
- `architecture_inventory.csv`
- `validation_backlog.md`
- `claim_risk_register.md`
- `run_manifest.json`
- proof-capsule stubs for the highest-priority candidates

## Candidate scoring

The engine scores each candidate on:

1. **Executable structure** — code, classes, functions, CLI, or tests exist.
2. **Evidence readiness** — named baseline, locked metric, seeds, outputs, or manifests exist.
3. **Reproducibility** — configuration, dependencies, hashes, and deterministic inputs exist.
4. **External-validation readiness** — a bounded question can be given to a qualified reviewer.
5. **Disclosure risk** — patent-sensitive language, unsupported claims, private paths, or safety-sensitive behavior.

A high discovery score is **not** proof that the architecture works. It only determines what deserves the next controlled test.

## PowerShell

Run the public repository audit:

```powershell
powershell -ExecutionPolicy Bypass -File .\research\architecture_engine\Run-ArchitectureAudit.ps1
```

Run across additional authorized local roots without modifying source files:

```powershell
powershell -ExecutionPolicy Bypass -File .\research\architecture_engine\Run-ArchitectureAudit.ps1 `
  -AdditionalRoots "C:\LumenCore","C:\LumaUniverse","C:\LumaTrader","E:\INSTITUTIONAL_STACK_V2","E:\GLYPH_DRIVE"
```

Pass canonical files to record their checksums without copying their contents:

```powershell
powershell -ExecutionPolicy Bypass -File .\research\architecture_engine\Run-ArchitectureAudit.ps1 `
  -ConstantsPath "C:\path\to\canonical_constants.json" `
  -LexiconPath "C:\path\to\canonical_lexicon.json"
```

## Innovation gate

The engine may propose experiments, comparator baselines, and optimization sweeps. It may not automatically merge novel controller logic, change canonical constants, expose private embodiments, or contact validators. Those actions require Robert's explicit approval and, where patent-sensitive, counsel review.
