# Public Site Exact-Snapshot Protocol

## Purpose

This protocol provides a manual, fail-closed release lane for the bounded public
review surfaces at `lumen-core.ai`. It is the only repository workflow allowed
to mutate production site files; it does not authorize a deployment by itself.
The legacy `deploy.yml` path is now a read-only exact-byte audit.

## Security and custody properties

- The requested release must be a full 40-character commit SHA.
- The requested commit must be the same commit that contains the workflow being
  executed.
- The workflow must be dispatched from `refs/heads/main`; a matching SHA on
  an unmerged branch or tag cannot authorize production access.
- An explicit `DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT` workflow input is required
  before SSH credentials are installed.
- Only the files in the reviewed `RELEASE_PATHS` allowlist are packaged (190 for
  the cohort and frozen EIA review release). Earlier 43-file, 119-file and 189-file releases retain their original
  membership, reconstructed from their pinned literal allowlists as data.
- Package bytes are read from immutable Git blobs, not from mutable worktree
  files.
- The manifest binds the source commit, Git blob IDs, byte counts, file hashes,
  archive hash, target directory, and install mode.
- Duplicate JSON keys, non-finite JSON values, unknown fields, unsafe paths,
  symlinks, executable blobs, and unexpected archive members fail closed.
- The remote apply captures pre-deploy file identity and copies the replaced
  allowlisted files into a timestamped rollback directory.
- Files outside the allowlist, including runtime data and non-release operator
  pages, are preserved.
- Every installed file is re-hashed before the deployment can succeed.
- Every canonical public URL is downloaded and compared byte-for-byte with the
  release manifest after installation.
- The live audit validates every manifest row before requesting any URL and
  refuses an empty release. Its bounded static scope allows at most 1,000 files,
  a 1 MiB manifest, 64 MiB per file and 512 MiB of declared files in total.
  Canonical paths and positive finite timeouts are required. Each response is
  read only up to its declared byte count plus one; an oversized or interrupted
  response remains an error. A match requires both the declared length and
  SHA-256, as well as the existing HTTP and MIME checks. The incident classifier
  independently checks the recorded length against the same manifest.
- The separate public-site supply-chain workflow inventories every allowlisted
  release file and, on `main`, signs and verifies build-provenance and SBOM
  attestations for the release archive before any human deployment decision.
- The deployment independently verifies both signed predicates against the
  locally rebuilt archive, canonical repository, signing workflow, exact source
  commit, main ref, GitHub OIDC issuer, and hosted-runner requirement before
  installing an SSH key. Missing or invalid attestations stop the deployment;
  an unsigned package cannot reach the VPS through this workflow. Verification
  receipts are retained with the deployment artifacts.
- Successful named deployments are added to an append-only receipt history;
  the repository verifier reconstructs every retained Git subject rather than
  allowing a newer receipt to replace an earlier one.

## Public release surfaces

The allowlist covers the proof-first homepage, bounded engagement page,
external-review page and machine-readable reviewer docket, public status page,
bounded evidence page, shared styles/command fabric, crawl metadata and public
mark, the ProofLock browser verifier with its protocol fixtures, and noindex
HOLD stubs for previous operator and research dashboard URLs. The reviewed
`downloads/eia-two-window-review-20260922.zip` is part of the same immutable
release and must pass exact-byte and ZIP MIME verification before promotion.

It deliberately excludes credentials, runtime logs, live order controls,
private evidence, grant packets, identity documents, and mutable data feeds. The
legacy route stubs do not expose runtime telemetry or operational controls; they
only redirect stale public links back to the bounded validation path.

## Human release command

Wait for the `Public site supply-chain assurance` workflow to finish both build
and signing jobs for the exact main commit to be released. Run the
`Deploy exact public-site snapshot to VPS` workflow on `main`. Enter that full
commit SHA and select
`DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT` only after reviewing the commit and the
production-environment approval gate.

## Claim boundary

A successful release receipt establishes byte identity between the selected Git
snapshot and the checked public URLs. It does not establish external validation,
field performance, savings, endorsement, certification, customer acceptance, or
deployment of any trading or infrastructure-control system.

Signed build provenance establishes workflow and artifact identity for the
archive. It does not establish a SLSA level, whole-product security, or that the
archive was deployed.
