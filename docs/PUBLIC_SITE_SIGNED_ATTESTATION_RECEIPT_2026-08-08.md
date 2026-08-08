# Public-site signed-attestation receipt — 2026-08-08

Production decision: **`HOLD`**.

This page records the first retained, successfully verified GitHub OIDC/Sigstore attestation set for the bounded LumenCore public-site release. It is a first-party custody record, not a signature, certification, independent technical validation, security audit, SLSA-level claim, or proof of deployment.

## Exact subject

| Field | Bound value |
|---|---|
| Repository | `robertashworth1986-debug/lumen-core-public` |
| Source commit | `5fff567c11bee65b5b1de5415d8b8935cd2dfab0` |
| Archive | `public-site-release.tar` |
| Archive bytes | `1,802,240` |
| Archive SHA-256 | `b771bf57367cec2f17db56a512b25eca1313539e4a2f8300adf045887449db7f` |
| Exact release files | `30` |
| CycloneDX version | `1.6` |
| CycloneDX components | `30` |

## Signing identity and run

- Workflow: [Public site supply-chain assurance run 31259179162](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31259179162)
- Workflow file: `.github/workflows/public-site-supply-chain.yml`
- Trigger and ref: `push` on `refs/heads/main`
- OIDC issuer: `https://token.actions.githubusercontent.com`
- Runner: GitHub-hosted; self-hosted runners were denied during verification.
- Certificate subject alternative name: `https://github.com/robertashworth1986-debug/lumen-core-public/.github/workflows/public-site-supply-chain.yml@refs/heads/main`

The run completed successfully and produced two verified predicates:

1. `https://slsa.dev/provenance/v1`
2. `https://cyclonedx.org/bom`

Each verification located one transparency-log timestamp. The machine-readable receipt is [`attestation-receipt.json`](../evidence/public-site-supply-chain/5fff567c11bee65b5b1de5415d8b8935cd2dfab0/attestation-receipt.json); its canonical self-hash is `06fbff15295cc4ea3094b91a7babf5b05a6c4bd1898346a765b51733b8831220`.

## Public verification

After downloading the archive artifact from the named workflow run, a reviewer can query GitHub's attestation service with both the repository and signing identity constrained:

```bash
gh attestation verify public-site-release.tar \
  --repo robertashworth1986-debug/lumen-core-public \
  --signer-workflow robertashworth1986-debug/lumen-core-public/.github/workflows/public-site-supply-chain.yml \
  --source-digest 5fff567c11bee65b5b1de5415d8b8935cd2dfab0 \
  --source-ref refs/heads/main \
  --cert-oidc-issuer https://token.actions.githubusercontent.com \
  --deny-self-hosted-runners \
  --predicate-type https://slsa.dev/provenance/v1

gh attestation verify public-site-release.tar \
  --repo robertashworth1986-debug/lumen-core-public \
  --signer-workflow robertashworth1986-debug/lumen-core-public/.github/workflows/public-site-supply-chain.yml \
  --source-digest 5fff567c11bee65b5b1de5415d8b8935cd2dfab0 \
  --source-ref refs/heads/main \
  --cert-oidc-issuer https://token.actions.githubusercontent.com \
  --deny-self-hosted-runners \
  --predicate-type https://cyclonedx.org/bom
```

Repository-local verification rebuilds the exact deterministic archive from immutable Git blobs and checks this receipt:

```bash
python code/ops/VERIFY_PUBLIC_SITE_SIGNED_ATTESTATION_RECEIPT.py
```

That local verifier checks receipt structure, self-hash, exact Git source availability, deterministic archive identity, signer/run fields, predicate identities, custody hashes, and the live-domain HOLD. It does **not** reverify the remote signature; the constrained `gh attestation verify` commands above do that.

## Private custody

The downloaded attestation bundles and signed build artifact remain in founder-controlled E-drive custody. Private bundle bytes are intentionally not copied into the public repository. The retained private manifest has SHA-256 `8cdc29f577c233d47f0b6e2a797f972dc4a48b5ca3a60c167961a23c67751f44`.

## Live-domain boundary

The signed archive is **not proven deployed**. The post-merge live audit checked all 30 expected paths and observed:

- `16` byte matches
- `12` byte mismatches
- `2` fetch errors
- severity `SEV-2`
- incident state `ACTIVE_PUBLIC_RELEASE_INTEGRITY_INCIDENT`
- decision `HOLD_PUBLIC_RELEASE_PROMOTION`

No production deployment is authorized by this receipt. The separate literal approval phrase `DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT` and a subsequent 30-of-30 byte-match audit remain required.

## Claim boundary

This evidence establishes that the named archive was built by the named GitHub-hosted workflow from the named source commit and that the provenance and SBOM attestations were cryptographically verified. It does not establish a SLSA level, whole-product or VPS provenance, vulnerability status, security assurance, regulatory conformance, external validation, production deployment, or live-domain parity.
