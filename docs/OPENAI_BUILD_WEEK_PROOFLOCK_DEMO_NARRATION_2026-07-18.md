# ProofLock Demo Narration

**Target runtime:** 2 minutes 20 seconds

**Recording surface:** `HOLD`. Do not record the final video from the historical `e9a1aba` release. Replace this line with the newly verified public URL only after the current deployment candidate reaches `14/14` live byte identity.

## 0:00-0:18 - Open

On screen: show the complete console before selecting any control.

> This is ProofLock, a developer tool for checking whether an evidence packet is intact and whether it has the authority to move forward. It separates a valid receipt from permission to promote the claim.

## 0:18-0:42 - The Problem

On screen: point to Integrity, Artifacts, Required Gates, and Decision.

> Technical projects often blur three different questions: did the files stay unchanged, do the files support the statement being made, and has the right person approved release? ProofLock keeps those questions separate and fails closed when any required authority gate is open.

## 0:42-1:03 - Canonical Verification

On screen: show `Verified`, `4 / 4`, `4 held`, and `HOLD`.

> The browser canonicalizes and hashes the receipt, rehashes four same-origin public artifacts, and checks the required gates. Here, integrity is verified and all four artifacts match, but four engineering and human gates are still open. The honest decision is HOLD.

## 1:03-1:38 - Guided Negative Proof

On screen: select **Run guided proof** and let the sequence complete.

> The guided proof first confirms custody. It then applies an in-memory mutation to the claim. That mutation breaks integrity, so the release is rejected. ProofLock restores the exact canonical text, verifies the artifacts again, and returns to HOLD. A truthful receipt can be intact without granting permission to promote the underlying claim.

## 1:38-2:02 - Reproducibility

On screen: show the repository or briefly scroll the verification log.

> The same rules run in the browser and in a Python command-line verifier. The focused suite covers canonical hashes, path boundaries, browser and Python parity, deterministic visuals, reduced motion, exact restoration, accessibility hooks, and local-only dependencies. The exact current result comes from the current-head CI receipt shown with the demo.

## 2:02-2:20 - Codex And Boundary

On screen: return to the final `HOLD` state.

> OpenAI Codex helped isolate, implement, and test this bounded release while preserving provenance and keeping unsupported claims behind explicit gates. ProofLock proves receipt integrity and artifact identity. It does not pretend that a hash proves safety, patentability, field performance, or commercial readiness.

## Model Provenance Line

Do not record a model name or Session ID until the primary Codex task's `/feedback` value is directly confirmed. Keep the private candidate and its digest out of the video and public repository.

## Recording Checks

- Use a quiet room and a microphone level that never clips.
- Record at 1080p or higher with the browser zoom at 100 percent.
- Keep the pointer still except when identifying a control or selecting **Run guided proof**.
- Wait for the exact restored `HOLD` state before the closing sentence.
- Do not show email, credentials, private proposals, patent drafts, browser bookmarks, or notification banners.
