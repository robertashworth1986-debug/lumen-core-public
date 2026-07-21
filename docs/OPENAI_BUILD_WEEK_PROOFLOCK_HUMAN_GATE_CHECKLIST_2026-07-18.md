# ProofLock Build Week Human Gate Checklist

**Official deadline recorded in the submission packet:** July 21, 2026 at 5:00 PM Pacific / 7:00 PM Central

**Latest official reminder:** Devpost email `Deadline TOMORROW | last minute tips - OpenAI Build Week`, received `2026-07-20T21:41:43Z`, confirms the deadline, permits a YouTube video that is public or unlisted, requires voiceover coverage of both Codex and GPT-5.6, requires the `/feedback` Session ID, and requires the entry to show `Submitted` rather than `Draft`.

**Internal target:** complete the human gates by July 20 at 6:00 PM Central so the final day is recovery time.

## Prepared Assets And Current Holds

- Project title: `ProofLock Console`
- Category: `Developer Tools`
- Public repository: `https://github.com/robertashworth1986-debug/lumen-core-public`
- Draft pull request: `https://github.com/robertashworth1986-debug/lumen-core-public/pull/36`
- Historical live demonstration only: `https://lumen-core.ai/build_week/prooflock_console/?release=20260718.1&commit=e9a1aba`
- Historical deployed source commit: `e9a1aba6fdfb368c64887af7e9caeee8aac21abb`; this release predates the corrected `decision == "PROMOTE"` invariant and must not be used for the final recording.
- Deployment candidate: the exact 40-character commit selected at action time. This checklist is not a commit pin.
- Current focused local test result: `52 passed, 3 skipped`; rerun immediately before recording and preserve the exact current-head receipt.
- Current-head GitHub Actions: workflow jobs did not start because the GitHub account is locked by a billing issue. This is an account gate, not a passing or failing test result.
- Latest observed live-file identity: `4/15` against commit `305401d213cde9609e324d6559cd6fd00dfbe502` at `2026-07-21T04:40:55Z`; the live route is not current-head evidence. The live-release and submission gates remain `HOLD`.
- Model evidence: retain the private task-metadata candidate, but do not state a final model identity until the primary task's `/feedback` value is directly confirmed.
- Private Session ID SHA-256: `CEDEC32157F2516DF88505802805761AE3535F093FB9B1B06CA6DEFF4A344FD9`
- Session hash reconciliation: `docs/OPENAI_BUILD_WEEK_PROOFLOCK_SESSION_HASH_RECONCILIATION_2026-07-18.md`
- Release receipt: `docs/OPENAI_BUILD_WEEK_PROOFLOCK_LIVE_RELEASE_RECEIPT_2026-07-18.md`
- Timed narration: `docs/OPENAI_BUILD_WEEK_PROOFLOCK_DEMO_NARRATION_2026-07-18.md`

## Judge-Facing Copy

### One-Line Description

ProofLock is a fail-closed developer tool that verifies a canonical evidence receipt, rehashes its public artifacts, and refuses promotion while required engineering or human-authority gates remain open.

### What It Demonstrates

The bundled FLOWFORM concept artifacts are pre-existing demonstration inputs. The Build Week work is the verifier and review surface around them: deterministic receipt hashing, artifact custody checks, browser/Python parity, safe path handling, a guided mutation-and-restoration proof, accessibility behavior, mobile QA, and fail-closed promotion logic.

### Codex Contribution

Codex isolated the focused release from a divergent working tree, preserved source provenance, implemented and tested the browser and Python verification paths, found and bounded a Windows line-ending defect through real-browser testing, prepared the live release, and kept every unsupported engineering or release claim behind an explicit gate.

### Claim Boundary

ProofLock proves declared receipt integrity, repository artifact identity, and release-gate behavior. It does not independently prove the substantive truth, safety, patentability, manufacturability, field performance, or commercial readiness of an artifact.

## Human-Only Sequence

1. Sign in to Devpost and verify the correct challenge, category, rules, deadline, and required fields.
2. Run `/feedback` in the primary Codex build task and retain the exact Session ID requested by the form.
3. Compare the private `/feedback` Session ID with the saved task-metadata candidate. Do not expose the private identifier in the repository or video, and do not infer a model name from local task metadata when the form requires direct `/feedback` evidence.
4. Restore GitHub Actions billing eligibility and use the dedicated ProofLock release workflow. If the account lock cannot be cleared before the deadline, the bounded local operator bridge may be used only with the exact source commit and action-time token `DEPLOY_PROOFLOCK_EXACT_SNAPSHOT`:

   ```powershell
   pwsh code/deploy/PUSH_PROOFLOCK_RELEASE_ON_VPS.ps1 `
     -SourceCommit <full-40-character-commit> `
     -Approval DEPLOY_PROOFLOCK_EXACT_SNAPSHOT `
     -Execute
   ```

   The bridge packages immutable Git blobs, requires the commit to equal `HEAD` and be reachable from the public release branch, verifies the pinned SSH host key, invokes only the bounded server-side installer, and preserves package, deployment, and live-gate receipts. It remains `HOLD` without both `-Execute` and the exact approval token.
5. Require the current-commit live verifier to report `15/15`, preserve the immutable custody pin, and record that GitHub-hosted CI was unavailable if the bounded fallback was used.
6. Replace the historical recording URL in the narration with the newly verified release URL.
7. Record the live demonstration using the timed narration. Keep the final cut under three minutes with intelligible audio.
8. Upload the video to YouTube as **public or unlisted** and verify playback while signed out. Preserve the dated Devpost reminder as the source for allowing an unlisted link.
9. Enter the repository, live-demo, and YouTube URLs into Devpost. Paste only the verified Session ID and model identity.
10. Confirm that pre-existing work and new Build Week work are separated exactly as stated above.
11. Preview the complete entry and test every link in a signed-out window.
12. Robert performs the final review and clicks Submit.
13. Save the Devpost confirmation page or email as a private submission receipt and hash it locally.

## Final Review

- [ ] Devpost account and challenge registration verified
- [ ] Category is `Developer Tools`
- [ ] Title and description match this packet
- [ ] Repository link opens without authentication
- [ ] Live demonstration opens without authentication
- [ ] YouTube video is public or unlisted, under three minutes, and plays with audio while signed out
- [x] Private task-metadata Session ID candidate matches the published SHA-256
- [ ] `/feedback` Session ID comes from the primary build task
- [ ] Model name is directly confirmed from the primary task rather than inferred
- [ ] No patent-sensitive or private material is exposed
- [ ] No safety, field-validation, revenue, certification, or patent claim is implied
- [ ] Pre-existing and Build Week contributions are clearly separated
- [ ] All links pass a final signed-out check
- [ ] Robert has reviewed the full preview
- [ ] Submission confirmation is saved and hashed

## Stop Conditions

Do not record the final shareable video or submit while the current live release is below `15/15`. Do not submit if the video cannot play while signed out, the Session ID has not been confirmed through `/feedback`, the model identity is inferred, the live demo fails, the repository is inaccessible, neither GitHub CI nor the bounded manual fallback has produced equivalent preserved receipts, or the entry implies that receipt integrity proves the underlying engineering claim.
