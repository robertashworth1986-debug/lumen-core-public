# ProofLock Console - Devpost Description Draft

## Tagline

Hash what exists. Hold what is not proven.

## Project Description

AI-assisted software can move faster than its evidence. ProofLock Console is a small developer tool that keeps those two things synchronized. It accepts a canonical JSON receipt, recomputes its SHA-256 identity, fetches and rehashes declared public repository artifacts, and evaluates required promotion gates separately from receipt integrity.

The bundled demonstration uses a real public artifact lineage created during the challenge window: the FLOWFORM V2 and V3 curved-motherboard and honeycomb-battery concept renders and their manifests. The console verifies all four artifact hashes and the declared lineage, then deliberately holds promotion because engineering CAD, prototype testing, qualified safety review, and human release remain open. A valid receipt is therefore not mistaken for a validated product claim.

The browser implementation uses Web Crypto and blocks arbitrary or escaping artifact paths. A matching Python CLI provides the same fail-closed review path for automation and CI. Deterministic tests cover receipt tampering, path traversal, artifact custody, and attempts to promote while required gates remain open. The interface is responsive and requires no account, API key, build step, or paid service for the bundled test.

## Build Week New Work

The focused console, receipt contract, CLI verifier, responsive interface, and tests were added after the submission period opened. The larger LumenCore repository and source concept assets are pre-existing dependencies. The scoped commit and directory make that boundary inspectable.

## Codex Collaboration

Codex reviewed the official rules, narrowed the product to one judge-testable workflow, implemented the browser and Python verification paths, wrote the tests, ran desktop and mobile QA, and preserved explicit human/final-submission gates. Before submission, add the verified GPT-5.6 model label and the `/feedback` Session ID from the task containing most of the implementation; do not infer either value.

## Testing

Repository: https://github.com/robertashworth1986-debug/lumen-core-public

Scoped source: https://github.com/robertashworth1986-debug/lumen-core-public/tree/1578504204c429d7f05779897dc3d5430038f681/build_week/prooflock_console

Run `python -m http.server 8088` from the repository root and open `/build_week/prooflock_console/`, or run `python build_week/prooflock_console/verify_receipt.py` for the CLI verification report.

## Boundary

This packet records a bounded Build Week readiness audit for the public ProofLock Console. It does not prove Devpost registration, GPT-5.6 model identity, a valid /feedback session ID, a public demo deployment, a YouTube upload, eligibility acceptance, final submission, judging outcome, OpenAI endorsement, prize entitlement, external validation, patent rights, safety, engineering performance, funding, or commercial value.
