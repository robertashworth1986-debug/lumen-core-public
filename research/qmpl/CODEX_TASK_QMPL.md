# Codex Task — Execute and Harden the QMPL Validation Suite

## Objective

Run the public-safe QMPL baseline suite on the local Windows machine, preserve all
results on disk, and improve reliability without adding unsupported claims or
publishing private inventor details.

## Required sequence

1. Work on branch `research/qmpl-swarm-validation-sweep`.
2. Locate the canonical LumenCore lexicon and constants files using:
   `powershell -ExecutionPolicy Bypass -File .\research\qmpl\Run-QMPLSweep.ps1 -FindLumaFiles`
3. Ask Robert to identify the canonical files if more than one candidate is found.
4. Run the suite with explicit paths:
   `powershell -ExecutionPolicy Bypass -File .\research\qmpl\Run-QMPLSweep.ps1 -ConstantsPath "<PATH>" -LexiconPath "<PATH>"`
5. Preserve the generated timestamped folder under `artifacts\qmpl\`.
6. Verify every SHA-256 in `manifest.json`.
7. Run the test file.
8. Do not alter the user's canonical lexicon or constants.
9. Do not add weapons, targeting, pursuit, payload delivery, evasion, or autonomous
   engagement behavior.
10. Do not describe simulation output as aerodynamic validation, flight validation,
    external validation, certification, or field performance.
11. Commit code improvements separately from generated result artifacts.
12. Report failures and negative results instead of suppressing them.

## Reviewer gate

Do not mark PR ready for review until:
- the run is reproducible from a clean checkout;
- the manifest includes code/config/constants/lexicon hashes;
- at least three seeds complete for every configured condition;
- failures are retained;
- a claim-to-artifact map is generated;
- private implementation details remain outside the public repository.
