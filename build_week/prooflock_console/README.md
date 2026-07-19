# ProofLock Console

ProofLock Console is a bounded developer tool for verifying a canonical JSON receipt, rehashing its public repository artifacts, and enforcing human-gated promotion rules. The bundled demonstration verifies the FLOWFORM V2-to-V3 curved-motherboard and honeycomb-battery concept lineage while refusing to treat the render as CAD, a prototype, test evidence, or certification.

## OpenAI Build Week Track

- Category: Developer Tools
- Submission period: July 13-21, 2026
- New work boundary: every file in this directory was created during the submission period. The existing LumenCore repository and the V2/V3 source artifacts predate this focused console and are dependencies, not claimed as new Build Week work.
- Codex contribution: Codex mapped the official requirements, selected a bounded product scope, implemented the browser and Python verifiers, wrote the receipt contract and tests, and preserved fail-closed claim gates.
- Model provenance gate: the Devpost entry must include the `/feedback` Codex Session ID and the user-confirmed GPT-5.6 session record. This repository does not infer or invent the model identity.

## Run

From the repository root:

```powershell
python -m http.server 8088
```

Open `http://127.0.0.1:8088/build_week/prooflock_console/`.

Public judge-testable deployment:

`https://lumen-core.ai/build_week/prooflock_console/`

The public deployment is verified byte-for-byte against the six console files and four declared
hardware artifacts by `code/ops/BUILD_OPENAI_BUILD_WEEK_PUBLIC_DEMO_RECEIPT.py`. A successful
deployment receipt proves availability and artifact identity at the recorded observation time; it
does not prove continuous uptime, engineering validation, or any Build Week judging outcome.

Supported platforms: current desktop and mobile browsers with Web Crypto and Fetch support. No account, API key, build step, or external service is required for the bundled demonstration.

## Verify From The CLI

```powershell
python build_week/prooflock_console/verify_receipt.py
```

The CLI exits nonzero when the canonical receipt hash, artifact hashes, schema, path boundary, or recorded decision policy fails. `integrity_valid`, `policy_valid`, and `promotion_allowed` are deliberately separate: a receipt can be intact while a requested `PROMOTE` decision is prohibited or required engineering and release gates remain open.

## Test

```powershell
python -m pytest -q tests/test_prooflock_console.py
```

## Demo Flow

1. Load the bundled receipt and verify four public V2/V3 artifacts.
2. Observe that artifact custody and lineage pass while engineering, prototype, safety, and human-release gates remain open.
3. Change one character in the claim boundary and verify again; the canonical receipt hash fails.
4. Restore the sample and change the decision from `HOLD` to `PROMOTE`; promotion remains blocked while required gates are open.

## Claim Boundary

This tool verifies declared receipt integrity, repository artifact identity, and fail-closed gate logic. It does not independently validate the truth of an arbitrary claim, establish patent rights, certify safety or security, authorize external action, or replace qualified engineering, legal, regulatory, or scientific review.
