# ProofLock Live Release Receipt

> **Historical release only.** This receipt applies only to release `20260718.1` at source commit `e9a1aba...`. It predates the corrected requirement that promotion also needs recorded decision `PROMOTE`. It must not be used as current release evidence or as the final recording surface. The current deployment candidate is `08659335e6ed7f838a276b6203526deff5dddd3b`, whose live gate remains `HOLD` at `10/14` byte matches until the four stale files are deployed and independently rechecked.

- Release: `20260718.1`
- Source commit: `e9a1aba6fdfb368c64887af7e9caeee8aac21abb`
- Live route: `https://lumen-core.ai/build_week/prooflock_console/?release=20260718.1&commit=e9a1aba`
- Deployment archive: `prooflock_console_e9a1aba.tar.gz`
- Archive bytes: `210189`
- Archive SHA-256: `88CC98ECBB7177043930E76F5C8505DFD15DBBB807C7B4CF7B8CA288C2DD88C1`

## Source And Deployment Identity

The deployment archive was built from the source commit above. All 14 live release files returned HTTP 200 and matched the archive's file bytes by SHA-256. The deployed console uses only its versioned, local runtime graph; it does not require a CDN, account, API key, or external service for the bundled verification demonstration.

## Historical Verification State

| Check | Result |
|---|---|
| Focused Python suite | `27 passed` |
| JavaScript syntax | Passed |
| CLI receipt integrity | Valid |
| Artifact hashes | `4/4` matched |
| Recorded decision | `HOLD` |
| Required authority gates | `4` held open |
| Promotion allowed | `false` |
| GitHub `verify` check | Success |
| GitHub `outreach-lock` check | Success |

For this historical release, the guided live-browser proof verified custody, applied an in-memory claim mutation, rejected the mutation, restored the exact canonical editor text, and returned to `HOLD` without browser-console errors. This result does not establish the later corrected decision invariant.

## Browser QA

### Desktop

- Viewport: `1440 x 1000`
- Horizontal page overflow: `0 px`
- Controls outside viewport: `0`
- WebGL lattice: rendered
- Canvas crop non-background ratio: `0.163707`
- Canvas crop channel standard deviation: approximately `[24.794, 24.811, 20.815]`
- Blank-canvas check: `false`

### Mobile

- Viewport: `390 x 844`
- Horizontal page overflow: `0 px`
- Controls outside viewport: `0`
- Control layout: stable `2 x 2` grid
- Visible canvas: `390 x 448`
- Canvas crop non-background ratio: `0.313358`
- Canvas crop channel standard deviation: approximately `[39.470, 41.110, 38.478]`
- Blank-canvas check: `false`

## Visual Evidence

| Path | Bytes | SHA-256 |
|---|---:|---|
| `docs/evidence/prooflock/prooflock_live_desktop_e9a1aba.png` | `90789` | `1794CD6990DDBCCF71EA471CD7F332796717B059B9C5DA2456D65D5DE40E05AA` |
| `docs/evidence/prooflock/prooflock_live_mobile_e9a1aba.png` | `60787` | `68D8439C9562195D07081ED2D77A77507A42ED2D1462EDE14AA6DC8C84483519` |

## Claim Boundary

For release `20260718.1` only, this receipt establishes source/deployment byte identity, deterministic receipt verification as it existed at that commit, bounded artifact custody, and successful browser rendering at the tested viewports. It does not establish the later corrected decision invariant, current deployment status, engineering performance, safety, patentability, external scientific validation, commercial readiness, legal acceptance, or authority to promote the underlying hardware concept.
