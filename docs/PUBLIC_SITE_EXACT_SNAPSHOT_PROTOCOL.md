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
- Only the files in the reviewed `RELEASE_PATHS` allowlist are packaged (43 for
  the current release allowlist).
- Package bytes are read from immutable Git blobs, not from mutable worktree
  files.
- The manifest binds the source commit, Git blob IDs, byte counts, file hashes,
  archive hash, target directory, and install mode.
- Duplicate JSON keys, non-finite JSON values, unknown fields, unsafe paths,
  symlinks, executable blobs, and unexpected archive members fail closed.
- The remote apply captures pre-deploy file identity and copies the replaced
  allowlisted files into a timestamped rollback directory.
- Before the apply can disarm its internal error rollback, it validates every
  captured backup and emits an immutable authority capsule bound to the exact
  repository, workflow, run ID, run attempt, source commit, manifest and state
  hashes, rollback directory, approval literal, and a one-attempt capability
  digest.
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

## Same-run compensation after a rejected live gate

The literal `DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT` approval authorizes one exact
candidate transaction. Within that same still-running workflow attempt only,
the transaction may compensate automatically when the external byte/MIME gate
rejects the installed candidate or cannot produce a valid receipt. This is part
of the reviewed exact-snapshot transaction; it is not a reusable restoration
workflow or general incident-repair authority.

The runner generates a fresh 256-bit capability for the attempt, masks it, and
passes it to the apply and compensation scripts through standard input. Only
its SHA-256 digest is retained in the immutable remote authority capsule. The
raw capability is never printed, uploaded as an artifact, written into the
rollback directory, accepted as a dispatch input, or retained after the job.
Run ID and run attempt alone are public metadata and do not authorize a restore.

The runner uses pinned Python 3.11.9. Before either remote mutation script can
inspect or change the target, the VPS must expose Python 3.9 or newer and the
fixed root-owned deployment lock under the bounded rollback base. Apply and
restore hold that same lock throughout their capture, preflight, mutation,
verification, and receipt phases. GitHub concurrency serializes canonical
workflow attempts; the VPS lock serializes cooperating direct script writers.
The resolved remote Python version is retained in the immutable authority
capsule. Uncooperative root mutation remains outside this guarantee.

Remote command transport and remote apply evidence are separate states. After
any invoked or ambiguous apply, both the live-gate and compensation phases can
independently rediscover exactly one authority by repository, workflow, run,
attempt, commit, capability digest, capture directory, self-hash, and all bound
state-file hashes. A local stdout parser, `tee`, or step-output failure therefore
cannot by itself suppress live verification or compensation.

Before the first compensation mutation, the restore contract validates the
authority self-hash, capability digest, run and commit bindings, exact manifest
and TSV hashes, exact allowlist order, backup inventory, independent regular
backup inodes, and every current target. Each target must equal either the
installed candidate state or the captured prior state. The script revalidates
that identity immediately before and after each file or directory mutation;
any third state stops before that target is touched and forbids a verified
receipt. A failed partial attempt can contain an admissible candidate/prior mix,
so the same authorized attempt may retry idempotently after the third state is
separately reconciled. It may not overwrite that third state.
Previously present files are restored through verified temporary files and
atomic rename. Previously missing allowlisted files are removed only when their
current state is the candidate state. Non-release files are never selected.

The only successful deployment state is `CANDIDATE_VERIFIED`. If compensation
verifies the prior allowlisted local bytes, numeric ownership, and modes, the
transaction records `PRIOR_STATE_RESTORED` and the workflow intentionally
remains red because the candidate was rejected. Missing, malformed, failed, or
interrupted compensation records `INDETERMINATE_FAIL_CLOSED`. A valid live gate
forbids compensation.

A present live-gate file is not automatically trusted. The runner first applies
the same strict manifest, schema, commit, URL, row-order, and aggregate checks
used by transaction adjudication. Only a valid `release_verified=false` receipt
is sent to the rejected-gate restore route. Malformed or contradictory bytes are
renamed as an untrusted artifact, never sent as restore authority, and use the
error-or-missing compensation route.

Runner cancellation, runner loss, network loss, or host loss can prevent the
same-run compensation from completing. No workflow can guarantee execution
after those failures. Any later or arbitrary rollback, retry, incident repair,
or incident closure requires a new human-reviewed authority decision.

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

A verified compensation receipt establishes only restoration of the captured
allowlisted local bytes, numeric ownership, and modes. It does not establish
public recovery through a proxy, cache, CDN, DNS, or TLS boundary; it is not a
successful candidate deployment, incident closure, disaster-recovery exercise,
certification, independent audit, or SLA result.
