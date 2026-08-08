# Public Site Supply-Chain Assurance

## Decision

LumenCore now has a deterministic CycloneDX 1.6 inventory for the exact
30-file public release and a separate GitHub-hosted `main` workflow that signs
the release archive's build provenance and SBOM association with GitHub's
OIDC/Sigstore artifact-attestation service.

This is a bounded release control. It is not a complete VPS, operating-system,
gateway, container, private-stack, or organization-wide SBOM. No SLSA level is claimed.
It is not certification, a penetration test, independent validation,
production authorization, or evidence that the live domain matches the source
commit.

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

The root application component binds the archive SHA-256, source commit,
repository URL, bounded target directory, inventory scope, and explicit
absence of a SLSA-level or live-deployment claim. The verifier requires 30 of
30 components and rejects missing, reordered, duplicated, unknown, or altered
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

## Production boundary

The live site remains `HOLD` until the separately gated exact-snapshot workflow
receives the literal `DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT`, applies the selected
commit with rollback capture, and proves every public URL byte against that
commit's release manifest. A signed build proves provenance and integrity of
the archive; it does not prove that the archive was deployed.

## Remaining gates

- deploy and verify an explicitly approved exact snapshot;
- inventory and govern the VPS OS, gateway, runtime services, and external
  dependencies in their own deployment scope;
- add vulnerability triage and time-bounded exception handling;
- retain and periodically re-verify attestation bundles and trusted roots; and
- obtain buyer-specific security, legal, data, insurance, and acceptance
  review.
