# Codex Task — LumenCore Architecture Discovery and Validation Engine

## Mission

Use the architecture engine to identify every credible LumenCore architecture in the authorized repository and local roots, then convert discovery into a ranked, falsifiable validation backlog.

## Non-negotiable boundaries

1. Do not change canonical lexicon or constants.
2. Do not expose private implementation details, patent-sensitive embodiments, credentials, personal data, or unpublished application content.
3. Do not execute arbitrary discovered scripts during the discovery pass.
4. Do not describe static discovery, simulation, or internal replay as external validation.
5. Do not add weapons, targeting, pursuit, evasion, payload-delivery, or lethal behavior.
6. Do not contact validators, merge the branch, or submit a patent/grant filing without Robert's explicit approval.
7. Retain negative results, failures, and unsupported candidates.

## Sequence

### Stage 1 — Public repository audit

```powershell
powershell -ExecutionPolicy Bypass -File .\research\architecture_engine\Run-ArchitectureAudit.ps1
```

Verify:

- `architecture_inventory.json` exists;
- `validation_backlog.md` exists;
- `claim_risk_register.md` exists;
- `run_manifest.json` verifies;
- all tests pass.

### Stage 2 — Authorized local metadata audit

```powershell
powershell -ExecutionPolicy Bypass -File .\research\architecture_engine\Run-ArchitectureAudit.ps1 `
  -AdditionalRoots "C:\LumenCore","C:\LumaUniverse","C:\LumaTrader","E:\INSTITUTIONAL_STACK_V2","E:\GLYPH_DRIVE"
```

This stage must remain metadata-only. Show Robert the inventory and candidate paths before reading private contents.

### Stage 3 — Canonical context selection

Ask Robert to identify the canonical lexicon and constants files from the metadata inventory. Rerun with explicit paths so their hashes are recorded without copying their contents.

### Stage 4 — Private content scan only after approval

If Robert explicitly approves selected private roots, rerun with `-ExternalContentScan`, but:

- keep outputs outside the public repository;
- redact absolute paths, personal data, credentials, and proprietary source excerpts;
- commit only public-safe validation plans, never private implementation content.

### Stage 5 — Candidate validation packets

For each high-priority architecture:

1. write one bounded hypothesis;
2. name at least three comparators;
3. lock metrics before execution;
4. define datasets/simulators and seeds;
5. map failure conditions;
6. create a checksum-backed Proof Capsule;
7. classify the result as measured, replay, synthetic, modeled, estimated, or externally validated;
8. route patent-sensitive mechanisms to a private inventor disclosure.

### Stage 6 — Optimization and innovation

Optimization is permitted only inside a registered experiment:

- preserve the incumbent and unoptimized baseline;
- define the search space before scoring;
- isolate each architectural change;
- use held-out seeds or windows;
- quantify compute and communication cost;
- record failed variants;
- promote no variant until it reproduces across parameter neighborhoods.

Innovation proposals must be labeled `hypothesis`, `candidate mechanism`, or `unvalidated embodiment` until tested and reviewed.

## Completion gate

Do not mark the pull request ready until:

- the public repo audit runs from a clean checkout;
- hashes verify;
- all tests pass;
- the top architectures have comparator-and-metric maps;
- private candidates remain private;
- every promoted sentence points to an artifact;
- Robert has reviewed the validation priority order.
