# ProofLock Current-Head Live Release Gate

- Observed UTC: `2026-07-18T13:45:52.697945+00:00`
- Source commit: `8c235f587fa748745b67903cda17817c7a344c7d`
- Git source bytes verified: `true`
- Worktree raw bytes match commit: `false`
- Status: `STALE_OR_INCOMPLETE_DEPLOYMENT_HOLD`
- Submission gate: `HOLD`
- Byte matches: `10/14`
- Gate SHA-256: `fffb459781b72b49e4dc0fbd1a0b6d086e2f2b5af616b6a5d7d770360ad8ad28`

## File Evidence

| File | HTTP | Redirect | Byte match | State |
|---|---:|---|---|---|
| `app.js` | `200` | `true` | `true` | `MATCH` |
| `bootstrap.js` | `200` | `true` | `true` | `MATCH` |
| `index.html` | `200` | `true` | `true` | `MATCH` |
| `prooflock_core.js` | `200` | `true` | `false` | `CONTENT_MISMATCH` |
| `prooflock_favicon.svg` | `200` | `true` | `false` | `CONTENT_MISMATCH` |
| `prooflock_lattice.css` | `200` | `true` | `true` | `MATCH` |
| `prooflock_lattice.js` | `200` | `true` | `true` | `MATCH` |
| `README.md` | `200` | `true` | `true` | `MATCH` |
| `sample_receipt.json` | `200` | `true` | `true` | `MATCH` |
| `styles.css` | `200` | `true` | `true` | `MATCH` |
| `three.core.min.js` | `200` | `true` | `true` | `MATCH` |
| `three.module.min.js` | `200` | `true` | `true` | `MATCH` |
| `THREE_LICENSE.txt` | `200` | `true` | `false` | `CONTENT_MISMATCH` |
| `verify_receipt.py` | `200` | `true` | `false` | `CONTENT_MISMATCH` |

## Required Actions

1. Do not present the live route as current-head evidence.
2. After explicit release approval, deploy the exact bounded console directory from the named source commit.
3. Rerun this gate and require every listed file to return HTTP 200 with an exact byte match before final Devpost review.

## Claim Boundary

This gate compares public HTTP response bytes with deployable source blobs loaded from the named Git commit at one observation time. A full match establishes only observed byte identity for the listed files. It does not prove uninterrupted availability, correct server configuration, security, engineering performance, external validation, Build Week eligibility, selection, or authority to submit.
