# Public Site Exact-Snapshot Protocol

## Purpose

This protocol provides a manual, fail-closed release lane for the bounded public
review surfaces at `lumen-core.ai`. It complements the existing automatic site
maintenance workflow; it does not authorize a deployment by itself.

## Security and custody properties

- The requested release must be a full 40-character commit SHA.
- The requested commit must be the same commit that contains the workflow being
  executed.
- An explicit `DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT` workflow input is required
  before SSH credentials are installed.
- Only the 26 files in `RELEASE_PATHS` are packaged.
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

## Public release surfaces

The allowlist covers the proof-first homepage, bounded engagement page,
external-review docket, public status page, bounded evidence page, shared
styles/command fabric, crawl metadata and public mark, and the ProofLock browser
verifier with its protocol fixtures.

It deliberately excludes credentials, runtime logs, live order controls,
private evidence, grant packets, identity documents, and mutable data feeds.

## Human release command

Run the `Deploy exact public-site snapshot to VPS` workflow against the exact
commit to be released. Enter that full commit SHA and select
`DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT` only after reviewing the commit and the
production-environment approval gate.

## Claim boundary

A successful release receipt establishes byte identity between the selected Git
snapshot and the checked public URLs. It does not establish external validation,
field performance, savings, endorsement, certification, customer acceptance, or
deployment of any trading or infrastructure-control system.
