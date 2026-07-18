# OpenAI Build Week ProofLock Submission Readiness

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
- [x] Public live release verified at `https://lumen-core.ai/build_week/prooflock_console/?release=20260718.1&commit=e9a1aba`.
- [x] All 14 deployed files returned HTTP 200 and matched the exact commit archive by SHA-256.
- [x] Live release QA, visual evidence, and hashes are recorded in `docs/OPENAI_BUILD_WEEK_PROOFLOCK_LIVE_RELEASE_RECEIPT_2026-07-18.md`.

## External And Human Gates

- [ ] Devpost registration directly verified.
- [x] Public repository and draft pull request directly verified.
- [x] Public live demo URL directly verified.
- [ ] Public YouTube demonstration is under three minutes and includes audio.
- [ ] Narration accurately covers the product, Codex contribution, and confirmed GPT-5.6 use.
- [ ] Primary build task `/feedback` Session ID captured.
- [ ] Actual GPT-5.6 model/session evidence captured from authoritative UI or session metadata.
- [ ] Founder review of judge-facing copy completed.
- [x] Draft pull request CI completed successfully on head commit `e9a1aba6fdfb368c64887af7e9caeee8aac21abb`.
- [ ] Final Devpost form reviewed by Robert.
- [ ] Final Devpost submit clicked by Robert.

## Repository Baseline Test Note

The complete current-main test collection produced `114 passed, 25 subtests passed, 2 failed` in 37.02 seconds on Windows. Neither failing path differs from `origin/main`:

- `test_public_capsule_verifies` hashes a CRLF checkout of `dice_eia_public_summary.txt` while the manifest records the LF Git blob.
- `test_cli_requires_explicit_apply_and_creates_backup` passes a valid Windows temporary absolute path to a helper that accepts only Unix-style `/...` document roots.

These are cross-platform baseline defects outside the focused Build Week lane. They are not hidden or weakened here, and should be repaired in a separate bounded PR. The complete ProofLock-focused suite remains `27 passed`.

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
