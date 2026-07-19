# ProofLock Console

ProofLock Console is a bounded developer tool for verifying a canonical JSON receipt, rehashing its public repository artifacts, deriving machine-checkable gates, and refusing self-authored authority escalation. The bundled demonstration verifies the internally consistent FLOWFORM V2-to-V3 curved-motherboard and honeycomb-battery concept lineage while refusing to treat the render as CAD, a prototype, test evidence, or certification.

## OpenAI Build Week Track

- Category: Developer Tools
- Submission period: July 13-21, 2026
- Pre-existing work: the LumenCore repository and four FLOWFORM V2/V3 concept artifacts existed before the July 13, 2026 submission window. They are demonstration inputs, not claimed as new Build Week work.
- Initial Build Week implementation: donor commit `1578504204c429d7f05779897dc3d5430038f681` added the bounded static console, Python verifier, receipt fixture, and focused tests after July 13.
- Current-main elevation: branch `build-week/prooflock-judge-ready`, based on `1faa6e642748637b2b2a5ce0a8db9012defda848`, ports only the focused lane and adds the deterministic evidence lattice, shared browser verification core, path hardening, browser/Python parity checks, guided tamper-and-restore proof, accessibility behavior, and mobile/reduced-motion QA.
- Codex contribution: Codex separated the release from a divergent dirty worktree, preserved source provenance, implemented and tested the verifier and visual states, found a Windows line-ending defect through real-browser testing, and kept every engineering and release gate fail closed.
- Model provenance gate: the Devpost entry must include the `/feedback` Codex Session ID and the user-confirmed GPT-5.6 session record. This repository does not infer or invent the model identity.

## Run

From the repository root:

```powershell
python -m http.server 8088
```

Open `http://127.0.0.1:8088/build_week/prooflock_console/`.

Supported platforms: current desktop and mobile browsers with Web Crypto and Fetch support. No account, API key, build step, or external service is required for the bundled demonstration.

The console loads only files shipped inside `build_week/prooflock_console/`. Its vendored Three.js modules and `THREE_LICENSE.txt` travel with the deployable directory, so copying that directory cannot create a hidden repository-layout dependency. A deterministic Canvas 2D renderer remains available when WebGL is unavailable.

## Verify From The CLI

```powershell
python build_week/prooflock_console/verify_receipt.py
```

The CLI exits nonzero when either integrity or policy validation fails. `integrity_valid`, `policy_valid`, and `promotion_allowed` are deliberately separate: a receipt can be byte-consistent while an attempted authority escalation is still rejected.

## Test

```powershell
python -m pytest -q tests/test_prooflock_console.py tests/test_prooflock_visual.py
```

The second command is the complete focused suite. It checks canonical hashing, artifact and gate logic, safe path resolution, browser/Python parity, deterministic visual state, reduced-motion behavior, exact guided restoration, accessibility hooks, and local-only runtime dependencies.

## Demo Flow

1. Open the local URL; the bundled receipt verifies four public V2/V3 artifacts without an account or rebuild.
2. Observe that artifact custody and lineage pass while engineering, prototype, safety, and human-release gates remain open.
3. Select **Run guided proof**. The console changes every required gate to `PASS`, records `PROMOTE`, recomputes a valid receipt hash, and still blocks promotion because the self-authored engineering, prototype, safety, and human approvals have no trusted verifier.
4. The console then restores the exact canonical editor text and returns to the original `HOLD` state.

The lattice is derived only from the verifier report: red means integrity failure, amber means valid evidence with open authority gates, and green is available only when integrity is valid and every required gate passes. The visualization is not a performance score.

## Claim Boundary

This tool verifies declared receipt integrity, repository artifact identity, internal manifest consistency, and fail-closed gate logic. SHA-256 does not authenticate the receipt author. ProofLock does not independently validate the truth of an arbitrary claim, establish patent rights, certify safety or security, authorize external action, or replace qualified engineering, legal, regulatory, or scientific review.

See [THREAT_MODEL.md](THREAT_MODEL.md) for the trust boundary, covered attacks, and explicit non-guarantees.
