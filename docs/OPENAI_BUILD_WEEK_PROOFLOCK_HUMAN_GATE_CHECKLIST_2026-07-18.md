# ProofLock Build Week Human Gate Checklist

**Official deadline recorded in the submission packet:** July 21, 2026 at 5:00 PM Pacific / 7:00 PM Central

**Internal target:** complete the human gates by July 20 at 6:00 PM Central so the final day is recovery time.

## Ready Assets

- Project title: `ProofLock Console`
- Category: `Developer Tools`
- Public repository: `https://github.com/robertashworth1986-debug/lumen-core-public`
- Draft pull request: `https://github.com/robertashworth1986-debug/lumen-core-public/pull/36`
- Live demonstration: `https://lumen-core.ai/build_week/prooflock_console/?release=20260718.1&commit=e9a1aba`
- Deployed source commit: `e9a1aba6fdfb368c64887af7e9caeee8aac21abb`
- Latest verified live-QA commit: `a7731fa`
- Focused test result: `27 passed`
- Live-file identity: `14/14` HTTP 200 responses and exact SHA-256 matches
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
3. Capture the actual model name from authoritative Codex UI or session metadata. Do not infer it from conversation text or memory.
4. Record the live demonstration using the timed narration. Keep the final cut under three minutes with intelligible audio.
5. Upload the video to YouTube as public or unlisted, according to the live rules, and verify playback while signed out.
6. Enter the repository, live-demo, and YouTube URLs into Devpost. Paste only the verified Session ID and model identity.
7. Confirm that pre-existing work and new Build Week work are separated exactly as stated above.
8. Preview the complete entry and test every link in a signed-out window.
9. Robert performs the final review and clicks Submit.
10. Save the Devpost confirmation page or email as a private submission receipt and hash it locally.

## Final Review

- [ ] Devpost account and challenge registration verified
- [ ] Category is `Developer Tools`
- [ ] Title and description match this packet
- [ ] Repository link opens without authentication
- [ ] Live demonstration opens without authentication
- [ ] YouTube video is under three minutes and plays with audio while signed out
- [ ] `/feedback` Session ID comes from the primary build task
- [ ] Model name comes from authoritative session evidence
- [ ] No patent-sensitive or private material is exposed
- [ ] No safety, field-validation, revenue, certification, or patent claim is implied
- [ ] Pre-existing and Build Week contributions are clearly separated
- [ ] All links pass a final signed-out check
- [ ] Robert has reviewed the full preview
- [ ] Submission confirmation is saved and hashed

## Stop Conditions

Do not submit if the video link is private, the Session ID or model identity is inferred, the live demo fails, the repository is inaccessible, or the entry implies that receipt integrity proves the underlying engineering claim.
