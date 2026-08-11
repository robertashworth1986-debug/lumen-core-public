# Public-site exact deployment receipt — 2026-08-09

This receipt records one successful, human-gated static-site release for
`lumen-core.ai`. It binds the 43 allowlisted public files to source commit
`e513f65a219a12e539d9f7dd3ea47a6a081c5262`, a deterministic archive, two
verified GitHub/Sigstore predicates, the VPS deployment run, and a separate
post-deployment live audit.

This is first-party deployment and custody evidence. It is not an independent
audit, certification, penetration test, SLSA-level claim, scientific
validation, field validation, customer acceptance, revenue record, or
whole-product/VPS assurance statement.

## Exact subject

| Field | Bound value |
|---|---|
| Repository | `robertashworth1986-debug/lumen-core-public` |
| Source commit | `e513f65a219a12e539d9f7dd3ea47a6a081c5262` |
| Release files | `43` |
| Archive bytes | `2,908,160` |
| Archive SHA-256 | `01886fb9ecd5d853d914fce905b4a8a89f189dd4b92ec1d9cc2d0865f7cad48f` |
| Manifest SHA-256 | `eba7c363a5c958a3bbffab5b867fea3b1cb47ac5b1dc3c16468a3dcffe55bd7f` |
| CycloneDX | `1.6`, 43 components |
| CycloneDX SHA-256 | `84b41f40f975d05e4fa516df07d3166b1520f6bd85dfb4e818529fe3acc84c43` |

## Supply-chain run

[Run 31291262952](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31291262952)
completed successfully on the named `main` commit. It produced and verified:

1. `https://slsa.dev/provenance/v1`
2. `https://cyclonedx.org/bom`

Both verification records bind the repository, `refs/heads/main`, source
commit, GitHub-hosted runner, workflow identity, and GitHub Actions OIDC issuer.
No SLSA level is claimed.

## Gated deployment

[Run 31291391266](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31291391266)
accepted the literal `DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT` approval for the same
full commit. The workflow:

- checked out the approved commit;
- packaged immutable Git blobs;
- verified bounded remote prerequisites;
- uploaded only the allowlisted archive;
- captured rollback identity;
- applied the exact files; and
- matched all 43 live bytes and allowed MIME types before succeeding.

The deployment live gate completed at `2026-08-09T02:56:46.842494Z` with
`43/43` matches and `release_verified: true`.

## Independent post-deployment workflow

[Run 31291435144](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31291435144)
then rebuilt the same immutable subject and performed a read-only live audit.
It recorded:

- expected files: `43`
- matched files: `43`
- mismatches: `0`
- fetch errors: `0`
- severity: `NONE`
- incident state: `NO_INCIDENT_OBSERVED`
- decision: `MONITOR`
- release verified: `true`

The audit did not mutate production or authorize incident closure, gateway
repair, secret changes, DNS changes, notification, legal attestation, or any
other consequential action.

## Reproduce the retained receipt

The compact machine record is
[`deployment-receipt.json`](../evidence/public-site-deployments/e513f65a219a12e539d9f7dd3ea47a6a081c5262/deployment-receipt.json).
Its verifier reconstructs the exact release archive and CycloneDX document from
the immutable Git commit, checks the subject hashes, validates the run and
attestation fields, and enforces the negative claim boundaries:

```bash
python code/ops/VERIFY_PUBLIC_SITE_DEPLOYMENT_RECEIPT.py
```

The local verifier does not perform a fresh GitHub signature lookup or live
HTTP audit. Reviewers can inspect or download the named GitHub run artifacts
and run constrained `gh attestation verify` commands when current online
verification is required.

## Private custody

The raw downloaded workflow artifacts, signed bundles, deployment receipts,
post-deployment audit, and an additional local 43-of-43 verification are
retained in founder-controlled E-drive custody. Raw private-custody bundle bytes
are not copied into the public repository.

## Claim boundary

This receipt establishes exact static-release identity and one successful
bounded deployment event for the named commit. It does not establish that any
later commit is deployed, that unallowlisted or private runtime components were
inventoried, or that LumenCore is certified, independently validated,
field-validated, revenue-generating, or authorized for production AI, physical
control, government submission, or live trading.
