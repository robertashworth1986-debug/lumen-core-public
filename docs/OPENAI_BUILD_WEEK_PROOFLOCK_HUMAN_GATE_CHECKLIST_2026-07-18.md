# ProofLock Build Week Human Gate Checklist

**Official deadline recorded in the submission packet:** July 21, 2026 at 5:00 PM Pacific / 7:00 PM Central

**Latest official reminder:** Devpost email `Deadline TOMORROW | last minute tips - OpenAI Build Week`, received `2026-07-20T21:41:43Z`, confirms the deadline, permits a YouTube video that is public or unlisted, requires voiceover coverage of both Codex and GPT-5.6, requires the `/feedback` Session ID, and requires the entry to show `Submitted` rather than `Draft`.

**Current checkpoint:** July 21, 2026 at 11:02 AM Central. This is the canonical current-readiness source; older Build Week readiness and predeployment notes are historical records.

## Prepared Assets And Current Holds

- Project title: `ProofLock Console`
- Category: `Developer Tools`
- Public repository: `https://github.com/robertashworth1986-debug/lumen-core-public`
- Draft pull request: `https://github.com/robertashworth1986-debug/lumen-core-public/pull/36`
- Current public demonstration: `https://lumen-core.ai/build_week/prooflock_console/`
- Current deployed source commit: `b2ac8cef10ee5b9db765a17cdbf6f13e6b917ce5` on `build-week/prooflock-judge-ready`.
- Current focused local test result: `55 passed, 3 skipped`. The published video remains truthfully bound to its immediately prior `54 passed, 3 skipped` assembly receipt.
- Current-head GitHub Actions: workflow jobs did not start because the GitHub account is locked by a billing issue. This is an account gate, not a passing or failing test result.
- Current live-file identity: `15/15` against commit `b2ac8cef10ee5b9db765a17cdbf6f13e6b917ce5` at `2026-07-21T13:47:38Z`; release gate `PASS`; live-gate SHA-256 `4b241a62e4f3fd76582d5e7992cc6ff119e36594b4f77e8713a1a75bac7984bc`.
- Exact release archive: 15 files; SHA-256 `e6a1b8adea8fb14432e6d3d27c9021dbd9349473323c347d3276b9906c47ca65`.
- Verified video publication: the selected Luma-voice 125.27-second H.264/AAC candidate with SHA-256 `9f1d417cb29c132ecc9a31f3a572adbcb3ebd66208517e70ad9adab6e8684b15` is public at `https://youtu.be/3qhK9WSJuaY`. YouTube reported no copyright issues; its player exposed the complete `2:06` media; and the public watch page and oEmbed metadata resolved with the expected title. The narration transcript QA preserved every critical phrase. The channel still requires phone verification before accepting the prepared custom thumbnail.
- Devpost state: Robert reported completing the final submission. The public page resolves at `https://devpost.com/software/prooflock-console`, visibly lists the project as submitted to OpenAI Build Week, and embeds the matching public Luma-voice video. Devpost independently sent `Submission confirmed: ProofLock Console` at `2026-07-21T16:00:55Z` and permits edits until `2026-07-21T17:00:00-07:00`. No reply is required. This proves the observable submission state, not that terms were read, contest acceptance beyond submission, judging, endorsement, or an award.
- Model evidence: the private `/feedback` Session ID is saved in Devpost and the judge-facing model reference is consistently `GPT-5.6`; the identifier itself remains excluded from public receipts.
- Private Session ID SHA-256: `CEDEC32157F2516DF88505802805761AE3535F093FB9B1B06CA6DEFF4A344FD9`
- Public repository metadata: both bounded release paths fail closed unless the exact reviewer-facing description, homepage, visibility, default branch, and six-topic set match the canonical public contract; each path preserves that decision in its release receipt.
- Session hash reconciliation: `docs/OPENAI_BUILD_WEEK_PROOFLOCK_SESSION_HASH_RECONCILIATION_2026-07-18.md`
- Historical release receipt: `docs/OPENAI_BUILD_WEEK_PROOFLOCK_LIVE_RELEASE_RECEIPT_2026-07-18.md`
- Final voiceover: `docs/OPENAI_BUILD_WEEK_PROOFLOCK_VOICEOVER_2026-07-20.md`
- YouTube publication receipt: `evidence/openai_build_week/prooflock_youtube_publication_receipt_20260721.json`

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
4. The bounded local operator bridge was used because GitHub Actions remained blocked before runner assignment. It deployed only the approved 15-file snapshot with the exact source commit and action-time token `DEPLOY_PROOFLOCK_EXACT_SNAPSHOT`:

   ```powershell
   pwsh code/deploy/PUSH_PROOFLOCK_RELEASE_ON_VPS.ps1 `
     -SourceCommit <full-40-character-commit> `
     -Approval DEPLOY_PROOFLOCK_EXACT_SNAPSHOT `
     -Execute
   ```

   The bridge packages immutable Git blobs, requires the commit to equal `HEAD` and be reachable from the public release branch, verifies the pinned SSH host key, invokes only the bounded server-side installer, and preserves package, deployment, and live-gate receipts. It remains `HOLD` without both `-Execute` and the exact approval token.
5. Preserve the current `15/15` live-verifier receipt and the fact that GitHub-hosted CI was unavailable because the account was locked before runner assignment.
6. Use the current public release URL and exact commit in the submission.
7. The selected Luma-voice 125.27-second video candidate with intelligible computer-generated narration is published publicly.
8. The public watch page and oEmbed metadata resolve and the YouTube player reports the complete media with audio present. Preserve the dated Devpost reminder as the source for allowing an unlisted link.
9. The repository, live-demo, YouTube URL, verified Session ID, and model identity are saved in Devpost.
10. Confirm that pre-existing work and new Build Week work are separated exactly as stated above.
11. The complete public project page resolves and exposes the expected live-demo, repository, and matching YouTube links.
12. Robert reported performing the final submission; the public page now shows `Submitted to OpenAI Build Week`.
13. Preserve the observable submission state in the self-hashed publication receipt without claiming acceptance, judging, endorsement, or an award.

## Final Review

- [x] Devpost account and challenge registration verified
- [x] Category is `Developer Tools`
- [x] Title and description match this packet
- [x] Repository link opens without authentication
- [x] Live demonstration opens without authentication
- [x] YouTube video is public, under three minutes, publicly resolvable, and contains verified AAC audio
- [x] Private task-metadata Session ID candidate matches the published SHA-256
- [x] `/feedback` Session ID comes from the primary build task and is saved only in the private Devpost field
- [x] The submitted model reference is `GPT-5.6`, consistent across the voiceover, project story, and judge-facing metadata
- [x] No patent-sensitive or private material is exposed in the prepared entry and video
- [x] No safety, field-validation, revenue, certification, or patent claim is implied
- [x] Pre-existing and Build Week contributions are clearly separated
- [x] All public links resolve from the submitted Devpost project page
- [ ] Robert has reviewed the full preview
- [x] Observable submission confirmation is saved in a self-hashed bounded receipt
- [x] Devpost's confirmation email independently corroborates submission and requires no reply

## Stop Conditions

Do not upload or submit if the video cannot play while signed out, the Session ID has not been confirmed through `/feedback`, the country is absent, the live demo fails, the repository is inaccessible, the final terms have not been reviewed by Robert, or the entry implies that receipt integrity proves the underlying engineering claim.
