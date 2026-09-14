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
- An explicit `DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT` workflow input is required
  before SSH credentials are installed.
- Only the files in the reviewed `RELEASE_PATHS` allowlist are packaged (189 for
  the cohort-enabled release). Earlier 43-file and 119-file releases retain their original
  membership, reconstructed from their pinned literal allowlists as data.
- Package bytes are read from immutable Git blobs, not from mutable worktree
  files.
- The local packager reads the selected tree once and fetches unique blob
  objects in one size-delimited Git batch. Git replacement objects are disabled;
  returned object identities, types, sizes, body hashes and framing are checked.
  Missing or repeated paths, noncanonical membership, more than 1,000 files or
  more than 128 MiB of selected payload fail before an archive is published.
  Each Git invocation has a 30-second timeout. No snapshot cache survives a call.
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
- The separate public-site supply-chain workflow inventories every allowlisted
  release file and, on `main`, signs and verifies build-provenance and SBOM
  attestations for the release archive before any human deployment decision.
- Successful named deployments are added to an append-only receipt history;
  the repository verifier reconstructs every retained Git subject rather than
  allowing a newer receipt to replace an earlier one.

## Public release surfaces

The allowlist covers the proof-first homepage, bounded engagement page,
external-review page and machine-readable reviewer docket, public status page,
bounded evidence page, shared styles/command fabric, crawl metadata and public
mark, the ProofLock browser verifier with its protocol fixtures, and noindex
HOLD stubs for previous operator and research dashboard URLs.

It deliberately excludes credentials, runtime logs, live order controls,
private evidence, grant packets, identity documents, and mutable data feeds. The
legacy route stubs do not expose runtime telemetry or operational controls; they
only redirect stale public links back to the bounded validation path.

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

Signed build provenance establishes workflow and artifact identity for the
archive. It does not establish a SLSA level, whole-product security, or that the
archive was deployed.

## Live observation bounds - 2026-09-14

The read-only live verifier rejects empty releases and validates every manifest
row before requesting any URL. It bounds manifest input to 1 MiB, declared
release content to 128 MiB and 1,000 files, and accepts only finite positive
per-request timeouts up to 60 seconds. Each response read is limited to the
declared file size plus one detection byte. An oversized or interrupted body
produces an explicit error; a partial prefix is never presented as a complete
body hash. A match requires the expected byte count as well as the SHA-256,
HTTP status and applicable MIME check. The incident classifier independently
checks the byte count before accepting a matching observation. These controls
retain the v1 receipt format and do not authorize any production mutation.

## Local batching observation - 2026-09-14

A paired first-party Windows build of the same 189 files at source commit
`7dc72f0cbda864156f848ed6870e9f44b3e4320b` took 38.4701 seconds with the previous
reader and 2.0684 seconds with the batch reader. Git calls fell from 379 to 4.
The 20,825,185 selected payload bytes produced byte-identical tar archives and
manifests. The observed ratio was 18.60 times in this one pair under concurrent
test load; it is not a general performance guarantee, an energy measurement or
a financial valuation. The exact timings and hashes are retained in the
[local observation receipt](../evidence/public-site-supply-chain/batch-reader-20260914.json).

The same reader is used by the supply-chain input verifier. Its existing row,
archive, inventory, provenance and authority checks remain required. Neither
this optimization nor its local checks authorize or demonstrate deployment.
