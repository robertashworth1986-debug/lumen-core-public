# Codex Task — Run and Harden the Architecture Validation Engine

## Mission

Use the architecture engine to inventory all accessible LumenCore roots, identify the best-supported architecture lanes, and generate a validation queue. Work read-only against canonical source roots.

## Required sequence

1. Work on branch `research/architecture-validation-engine`.
2. Execute:

   ```powershell
   powershell -ExecutionPolicy Bypass `
     -File .\research\architecture_validation\Run-ArchitectureValidation.ps1 `
     -HashMatches
   ```

3. Inspect `architecture_registry.md`, `experiment_queue.json`, and `hybrid_candidate_queue.json`.
4. Verify that the scanner did not modify any canonical lexicon, constants, or architecture files.
5. Verify every output checksum in `scan_manifest.json`.
6. For the top five detected lanes, create one issue-sized experiment plan each: source, baseline, locked metrics, development/validation split, failure tests, manifest, claim boundary, and next gate.
7. Do not merge or publish result claims automatically.
8. Do not infer external validation, certification, customer deployment, agency endorsement, or patentability.
9. Keep patent-sensitive implementation details in a private disclosure queue.
10. Reject optimization if the objective, baseline, failure conditions, or safety constraints are not locked.

## Safety and scope

Keep all work in non-operational, simulation, replay, evidence, and human-reviewed research lanes. Do not add prohibited operational-use behavior or unsafe physical-control functionality.

## Innovation rule

Generate hybrid experiments only from existing founder-owned modules. Every hybrid must compete against both component baselines plus a naive control. A novel hybrid remains a research candidate until patent review and reproducible evidence exist.
