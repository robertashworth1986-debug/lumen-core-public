# Public Site Supply-Chain Assurance

## Decision

LumenCore now has a deterministic CycloneDX 1.6 inventory for the exact
43-file public release at commit
`e513f65a219a12e539d9f7dd3ea47a6a081c5262` and a separate GitHub-hosted `main` workflow that signs
the release archive's build provenance and SBOM association with GitHub's
OIDC/Sigstore artifact-attestation service.

This is a bounded release control. It is not a complete VPS, operating-system,
gateway, container, private-stack, or organization-wide SBOM. No SLSA level is claimed.
It is not certification, a penetration test, independent validation,
production authorization, or evidence that any later source commit matches the
live domain.

## What is inventoried

The builder consumes the immutable public release archive and strict release
manifest. It emits one CycloneDX file component for every allowlisted release
file, preserving:

- public archive path;
- canonical repository path;
- Git blob identity;
- SHA-256 content identity;
- byte count; and
- install mode.

The allowlist also carries `legacy-route HOLD stubs` for retired public dashboard URLs.
Those files are intentionally shipped as noindex redirect guards so stale VPS files or old links cannot be mistaken for the current public validation surface.

The root application component binds the archive SHA-256, source commit,
repository URL, bounded target directory, inventory scope, and explicit
absence of a SLSA-level or broad live-deployment claim. The verifier requires
one component for every file in the release manifest—43 of 43 for commit
`e513f65a`—and rejects missing, reordered, duplicated, unknown, or altered
release identities.

## Two evidence layers

1. **Every pull request and `main` build:** deterministic release package,
   CycloneDX inventory, first-party local receipt, verification receipt, and
   SHA-256 manifest. These are unsigned build outputs.
2. **GitHub-hosted `main` build only:** Sigstore-signed SLSA provenance and a
   Sigstore-signed CycloneDX SBOM attestation. The signing job has OIDC and
   attestation permissions; the pull-request build job has read-only contents
   permission and cannot sign.

The signed bundles are verified in the workflow against the repository,
signer workflow, `refs/heads/main`, source digest, GitHub OIDC issuer, and a
GitHub-hosted runner requirement before they are retained as artifacts.

The first retained successful set is documented in
[`PUBLIC_SITE_SIGNED_ATTESTATION_RECEIPT_2026-08-08.md`](PUBLIC_SITE_SIGNED_ATTESTATION_RECEIPT_2026-08-08.md).
It binds the exact archive to source commit
`5fff567c11bee65b5b1de5415d8b8935cd2dfab0`, workflow run `31259179162`, the
two predicate types, constrained verification results, and founder-controlled
private bundle custody. The public receipt is a first-party custody record; it
is not itself a signature or external validation.

The named deployed release is documented in
[`PUBLIC_SITE_EXACT_DEPLOYMENT_RECEIPT_2026-08-09.md`](PUBLIC_SITE_EXACT_DEPLOYMENT_RECEIPT_2026-08-09.md).
It binds the 43-file archive for commit `e513f65a` to the successful supply-chain
run, human-gated deployment run, 43-of-43 live-byte verification, security-header
receipt, and a separate read-only post-deployment audit. That receipt is
first-party deployment evidence for the named static release; it is not external
validation or broader production authorization.

## Consumer verification

After downloading `public-site-release.tar`, verify signed build provenance:

```bash
gh attestation verify public-site-release.tar \
  --repo robertashworth1986-debug/lumen-core-public \
  --signer-workflow robertashworth1986-debug/lumen-core-public/.github/workflows/public-site-supply-chain.yml \
  --source-digest FULL_MAIN_COMMIT_SHA \
  --source-ref refs/heads/main \
  --cert-oidc-issuer https://token.actions.githubusercontent.com \
  --deny-self-hosted-runners
```

Verify the signed CycloneDX predicate by adding:

```bash
--predicate-type https://cyclonedx.org/bom
```

The repository, workflow path, commit, and expected predicate type are policy
inputs, not facts to infer from the artifact itself.

For the historical retained set, also run the repository-local attestation
receipt verifier:

```bash
python code/ops/VERIFY_PUBLIC_SITE_SIGNED_ATTESTATION_RECEIPT.py
```

It reconstructs the exact deterministic archive from immutable Git blobs and
checks the public receipt's identities and `HOLD`. It does not replace the
constrained online `gh attestation verify` signature check.

For the named deployed release, run:

```bash
python code/ops/VERIFY_PUBLIC_SITE_DEPLOYMENT_RECEIPT.py
```

It reconstructs the exact 43-file archive from immutable Git blobs and checks
the retained first-party deployment receipt. It does not contact GitHub or the
live domain, so it does not replace fresh signature or HTTP verification.

## Production boundary

The exact static release at commit `e513f65a` passed the separately gated
`DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT` workflow, rollback capture, 43-of-43 live
byte verification, and independent read-only audit. A signed build by itself
still does not prove deployment, and any later release must pass the same gate.
The broader platform production decision remains `HOLD`.

## Remaining gates

- repeat the human-gated deploy and exact live audit for every later release;
- inventory and govern the VPS OS, gateway, runtime services, and external
  dependencies in their own deployment scope;
- add vulnerability triage and time-bounded exception handling;
- periodically re-verify retained attestation bundles and trusted roots; and
- obtain buyer-specific security, legal, data, insurance, and acceptance
  review.
