# ProofLock Demo Narration

**Target runtime:** 2 minutes 35 seconds or less

**Recording surface:** `HOLD`. Record locally from the current branch for rehearsal only. Do not present the historical public release as current-head evidence. Record the final public demo only after the exact 15-file release reaches `15/15` live byte identity and the live verifier passes against the same commit.

## 0:00-0:14 - Open

On screen: show the complete console before selecting any control.

> This is ProofLock, a developer tool that checks whether an evidence packet is intact and whether it has authority to move forward. A valid receipt is necessary, but it is not permission to promote a claim.

## 0:14-0:36 - The Problem

On screen: point to Integrity, Artifacts, Required Gates, and Decision.

> Technical reviews often blur three questions: did the files stay unchanged, do they support the statement being made, and has a trusted reviewer authorized release? ProofLock keeps integrity, evidence, and authority separate, then fails closed when a required authority gate is unsupported.

## 0:36-0:58 - Canonical Verification

On screen: show `Verified`, `4 / 4`, `4 held`, and `HOLD`.

> The browser canonicalizes and hashes the receipt, rehashes four same-origin public artifacts, and derives the effective gates. Integrity is verified and all four artifacts match. Four engineering and human authority gates remain held, so the effective decision is HOLD.

## 0:58-1:34 - Guided Authority Attack

On screen: select **Run guided proof** and let the sequence complete.

> Now the guided proof performs the harder attack. It changes every required gate to PASS, requests PROMOTE, and recomputes a valid receipt hash. Receipt integrity still passes. But self-authored engineering, prototype, safety, and human approvals are not trusted authority. ProofLock derives four held gates, blocks the requested promotion, and keeps the effective decision at HOLD.

## 1:34-1:50 - Exact Restoration

On screen: let the guided proof restore the canonical sample.

> The console restores the exact canonical receipt text, rehashes the artifacts, and returns to the original HOLD state. The attack never changes the source files or grants itself authority.

## 1:50-2:16 - Reproducibility

On screen: show the repository or briefly scroll the verification log.

> The same rules run in the browser and in a Python command-line verifier. Focused tests cover canonical hashes, path boundaries, browser and Python parity, deterministic visuals, reduced motion, exact restoration, accessibility hooks, deployment isolation, and local-only dependencies. The video must name the exact source commit and current test receipt used for the recording.

## 2:16-2:35 - Codex And Boundary

On screen: return to the final `HOLD` state.

> OpenAI Codex helped isolate, implement, challenge, and test this bounded release while preserving provenance. ProofLock demonstrates receipt integrity, artifact identity, policy enforcement, and authority separation. It does not claim that a hash proves safety, patentability, field performance, external validation, or commercial readiness.

## Model Provenance Line

Do not record a model name or Session ID until the primary Codex task's `/feedback` value is directly confirmed. Keep the private candidate and its digest out of the video and public repository.

## Recording Checks

- Use a quiet room and a microphone level that never clips.
- Record at 1080p or higher with the browser zoom at 100 percent.
- Keep the pointer still except when identifying a control or selecting **Run guided proof**.
- During the attack, confirm `receipt PASS`, `policy BLOCKED`, requested decision `PROMOTE`, four effective gates held, and effective decision `HOLD`.
- Wait for exact canonical restoration and the restored `HOLD` state before the closing sentence.
- Do not show email, credentials, private proposals, patent drafts, browser bookmarks, or notification banners.
