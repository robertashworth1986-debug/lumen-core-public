# Public-site exact deployment receipt — 2026-08-12 UTC

This receipt records the second retained, human-gated static-site release for
`lumen-core.ai`. It binds the 43 allowlisted public files to source commit
`1ce7c35975a4011fa844e8b39ccbc950c8c0f398`, a deterministic archive, two
verified GitHub/Sigstore predicates, the VPS deployment run, and a separate
read-only post-deployment live audit.

This is first-party deployment and custody evidence. It is not an independent
audit, certification, penetration test, SLSA-level claim, scientific or field
validation, customer acceptance, revenue record, or whole-product/VPS
assurance statement.

## Exact subject

| Field | Bound value |
|---|---|
| Repository | `robertashworth1986-debug/lumen-core-public` |
| Source commit | `1ce7c35975a4011fa844e8b39ccbc950c8c0f398` |
| Release files | `43` |
| Archive bytes | `2,488,320` |
| Archive SHA-256 | `681c89bb446a83393b52d02d02ea05bb6ccabf63a60d65bdb9efb074c56b3fa9` |
| Manifest SHA-256 | `36d114d34f01ec139d1e1df08e407af1c7e49ee370d5f7ca36a07a1b68063efa` |
| CycloneDX | `1.6`, 43 components |
| CycloneDX SHA-256 | `258fbb0b985e2eefba22e13c1848854151ec90c56612415123b1461dac0b108e` |

## Supply-chain run

[Run 31548604617](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31548604617)
completed successfully on the named `main` commit. It produced and verified:

1. `https://slsa.dev/provenance/v1`
2. `https://cyclonedx.org/bom`

Both verification records bind the repository, `refs/heads/main`, source
commit, GitHub-hosted runner, workflow identity, and GitHub Actions OIDC issuer.
Each record contains one verified transparency-log timestamp. No SLSA level is
claimed.

## Gated deployment

[Run 31548829514](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31548829514)
accepted the literal `DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT` approval for the same
full commit. The workflow:

- checked out the approved commit;
- packaged immutable Git blobs;
- verified bounded remote prerequisites;
- uploaded only the allowlisted archive;
- captured the pre-deploy identity in a timestamped rollback directory;
- applied only the exact allowlisted files; and
- matched all 43 live bytes and allowed MIME types before succeeding.

The deployment live gate completed at `2026-08-12T00:04:05.483835Z` with
`43/43` matches and `release_verified: true`.

## Independent post-deployment workflow

[Run 31548906293](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31548906293)
then rebuilt the same immutable subject and performed a separate read-only live
audit. It recorded:

- expected files: `43`
- matched files: `43`
- mismatches: `0`
- fetch errors: `0`
- severity: `NONE`
- incident state: `NO_INCIDENT_OBSERVED`
- decision: `MONITOR`
- release verified: `true`

The audit performed no production mutation and did not authorize incident
closure, gateway repair, secret or DNS changes, notification, legal
attestation, government submission, live trading, or any other consequential
action.

## Append-only deployment history

The earlier receipt for commit
`e513f65a219a12e539d9f7dd3ea47a6a081c5262` remains retained. The current
verifier discovers every receipt under `evidence/public-site-deployments/`,
reconstructs each named Git subject, and rejects a directory/source mismatch,
duplicate source commit, altered subject, promoted claim, or invalid self-hash.

The compact record for this release is
[`deployment-receipt.json`](../evidence/public-site-deployments/1ce7c35975a4011fa844e8b39ccbc950c8c0f398/deployment-receipt.json).
Verify the complete retained history with:

```bash
python code/ops/VERIFY_PUBLIC_SITE_DEPLOYMENT_RECEIPT.py
```

The local verifier reconstructs Git subjects and checks retained first-party
records. It does not perform a fresh GitHub signature lookup or live HTTP audit.
Reviewers can inspect the named GitHub runs and independently rerun constrained
`gh attestation verify` and exact-live-audit commands when current online
verification is required.

## Private custody

The raw downloaded supply-chain artifacts, signed bundles, deployment and
rollback receipts, exact archive, manifest, and post-deployment audit are
retained in founder-controlled E-drive custody. Those raw private-custody bytes
are not copied into the public repository.

## Claim boundary

This receipt establishes exact static-release identity and one successful
bounded deployment event for the named commit. It does not establish that a
later commit is deployed, that unallowlisted or private runtime components were
inventoried, or that LumenCore is certified, independently validated,
field-validated, revenue-generating, or authorized for production AI, physical
control, government submission, or live trading.
