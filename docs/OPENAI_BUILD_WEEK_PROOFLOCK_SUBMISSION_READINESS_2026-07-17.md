# OpenAI Build Week ProofLock Submission Readiness

> **Historical checkpoint.** This July 18 snapshot is preserved for audit history and is not the current submission state. Use `docs/OPENAI_BUILD_WEEK_PROOFLOCK_HUMAN_GATE_CHECKLIST_2026-07-18.md` as the canonical current-readiness source.

**State date:** 2026-07-18 UTC

**Deadline:** July 21, 2026 at 5:00 PM Pacific / 7:00 PM Central

**Category:** Developer Tools

**Release branch:** `build-week/prooflock-judge-ready`

**Decision:** `HOLD` until every external and founder gate below has direct evidence

## Implemented And Verified

- [x] Package category selected as Developer Tools.
- [x] New-vs-pre-existing work boundary is explicit in the console README.
- [x] Exact no-account, no-key local run and test instructions are documented.
- [x] Canonical receipt and four public artifacts verify from both browser and Python paths.
- [x] Browser and Python canonical hashing, gate logic, and path handling have parity tests.
- [x] Required authority gates fail closed; the bundled receipt remains `HOLD`.
- [x] Guided proof demonstrates mutation rejection and exact canonical editor restoration.
- [x] Desktop 1440x1000 and mobile 390x844 layouts were rendered and visually inspected.
- [x] Desktop and mobile canvas captures are nonblank by pixel-distribution checks.
- [x] Reduced-motion mode disables continuous animation; two captures 750 ms apart are byte-identical.
- [x] Browser console is clean: zero errors and zero warnings after the guided flow.
- [x] Fresh browser network log contains 16 repository-local HTTP 200 requests and no external request.
- [x] Repository `LICENSE` is present.
- [x] Vendored Three.js files retain copyright headers and `dashboard/assets/vendor/THREE_LICENSE.txt` contains the MIT license.
- [x] Historical public release `20260718.1` verified against source commit `e9a1aba`; all 14 deployed files returned HTTP 200 and matched that exact commit archive by SHA-256.
- [ ] Corrected deployable source commit `8c235f5` is live and reverified. The canonical Git-blob audit matches 10 of 14 files; both verifier files are stale, so submission remains on HOLD.
- [x] Current-head deployment state is recorded in `docs/OPENAI_BUILD_WEEK_PROOFLOCK_PREDEPLOYMENT_GATE_2026-07-18.md` and its machine-readable JSON companion.
- [x] Live release QA, visual evidence, and hashes are recorded in `docs/OPENAI_BUILD_WEEK_PROOFLOCK_LIVE_RELEASE_RECEIPT_2026-07-18.md`.
- [x] A timed under-three-minute narration and one-pass human submission checklist are recorded in `docs/OPENAI_BUILD_WEEK_PROOFLOCK_DEMO_NARRATION_2026-07-18.md` and `docs/OPENAI_BUILD_WEEK_PROOFLOCK_HUMAN_GATE_CHECKLIST_2026-07-18.md`.

## External And Human Gates

- [ ] Devpost registration directly verified.
- [x] Public repository and draft pull request directly verified.
- [x] Public live demo URL directly verified.
- [ ] Public YouTube demonstration is under three minutes and includes audio.
- [ ] Narration accurately covers the product, Codex contribution, and confirmed GPT-5.6 use.
- [ ] Primary build task `/feedback` Session ID captured.
- [x] Actual model evidence captured from authoritative session metadata as `gpt-5.6-sol`; the private task-metadata Session ID candidate exactly matches public SHA-256 `CEDEC32157F2516DF88505802805761AE3535F093FB9B1B06CA6DEFF4A344FD9`, with `/feedback` confirmation still open.
- [ ] Founder review of judge-facing copy completed.
- [x] Draft pull request CI completed successfully on authority-fix commit `8c235f5`.
- [ ] Corrected source released and reverified at 14 of 14 exact byte matches.
- [ ] Final Devpost form reviewed by Robert.
- [ ] Final Devpost submit clicked by Robert.

## Repository Baseline Test Note

The complete current-main test collection produced `114 passed, 25 subtests passed, 2 failed` in 37.02 seconds on Windows. Neither failing path differs from `origin/main`:

- `test_public_capsule_verifies` hashes a CRLF checkout of `dice_eia_public_summary.txt` while the manifest records the LF Git blob.
- `test_cli_requires_explicit_apply_and_creates_backup` passes a valid Windows temporary absolute path to a helper that accepts only Unix-style `/...` document roots.

These are cross-platform baseline defects outside the focused Build Week lane. They are not hidden or weakened here, and should be repaired in a separate bounded PR. The current ProofLock-focused suite is green at the current PR head; the exact count belongs to the current-head CI receipt rather than this durable narrative. The live-release receipt preserves its historical `27 passed` run. The separate live-release gate adds seven offline regression checks.

## Judge Test Path

```powershell
python -m http.server 8088
```

Open `http://127.0.0.1:8088/build_week/prooflock_console/`, select **Run guided proof**, and confirm the sequence returns to:

- integrity: `Verified`
- artifacts: `4 / 4`
- required gates: `4 held`
- decision: `HOLD`

Then run:

```powershell
python build_week/prooflock_console/verify_receipt.py
python -m pytest -q tests/test_prooflock_console.py tests/test_prooflock_visual.py
```

## Claim Boundary

ProofLock establishes declared receipt integrity, same-origin repository artifact identity, V2-to-V3 concept lineage, and fail-closed release logic for the bundled public fixture. It does not establish the substantive truth of an arbitrary claim or prove engineering performance, safety, certification, patent rights, manufacturability, field validation, commercial readiness, or independent validation.
