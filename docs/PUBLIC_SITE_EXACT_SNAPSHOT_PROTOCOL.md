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
  current named release commit `1ce7c35975a4011fa844e8b39ccbc950c8c0f398`).
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

## Candidate-origin staging lane

The manual `Stage exact public-site snapshot on candidate origin` workflow is a
separate, pre-DNS lane for a newly purchased Ubuntu host. It cannot create or
purchase a server, call a provider API, mutate DNS, deploy to an address that is
currently serving `lumen-core.ai`, or promote the candidate. It uses the same
immutable 43-file packager and bounded rollback-capable apply script as the
production lane.

The candidate must be created separately with:

- Ubuntu 22.04 or 24.04 LTS;
- one globally routable IPv4 address that is not currently returned for
  `lumen-core.ai`;
- a non-root SSH account with non-interactive sudo;
- its own reviewed SSH private key and `known_hosts` material in the protected
  `production-candidate` GitHub Environment; and
- no gateway, trading, grant, operator-data, or private runtime service.

`code/deploy/BOOTSTRAP_PUBLIC_SITE_ORIGIN.sh` is noninteractive and can run as a
cloud-init shell user-data script when cloud-init first writes the reviewed
`code/deploy/nginx/lumencore-public-origin.conf` payload to the host. It installs
only the bounded Ubuntu edge prerequisites, creates the static release and
rollback roots, validates the reviewed Nginx configuration hash, and captures a
rollback and bootstrap receipt. It does not clone Git, request a certificate,
handle a provider token, or change DNS.

For the fastest reviewed first boot, render
`code/deploy/cloud-init/lumencore-public-origin-cloud-config.yml` only in the
provider's user-data field by replacing its sentinel with the intended SSH
public key. The template creates the locked `lumencore-deploy` account, disables
root/password SSH, validates the SSH daemon configuration, and applies current
Ubuntu package updates. Do not commit a rendered template, private key, provider
token, or account credential. The candidate workflow subsequently uploads and
runs the separately hash-bound origin bootstrap and Nginx configuration.

Until the named canonical certificate and standard Certbot support files exist,
the bootstrap installs an HTTP-only hold that exposes only `/nginx-health` and
the ACME challenge path; every other request returns `503`. Certificate issuance
or transfer is a separate credential/TLS action requiring fresh authorization.
The expected certificate name is `lumen-core.ai`, with valid SAN coverage for
the root, `www`, `app`, and `research` names. Re-running the bootstrap after that
certificate is installed activates the reviewed static-only HTTPS config.

Candidate staging requires all four visible workflow inputs:

1. the full 40-character release commit, equal to the selected workflow ref;
2. the exact candidate IPv4 address;
3. the exact non-root SSH account; and
4. the literal `STAGE_PUBLIC_SITE_CANDIDATE` approval.

The candidate verifier's `--resolve-address` option connects directly to that
literal IP while retaining `lumen-core.ai` in the URL, HTTP Host header, and TLS
SNI. Normal certificate-chain and hostname validation remains enabled. The
candidate must pass all 43 byte/MIME checks, canonical certificate checks,
redirect and health contracts, Nginx validation, and private-listener negative
checks before it can be considered for a separate DNS decision.

A successful candidate run is not production promotion. Changing TTL or any A,
AAAA, CNAME, TXT, or nameserver record still requires a fresh action-time DNS
approval identifying every old and new value. The existing production origin
must remain available as the blue rollback target until the separately approved
cutover passes the canonical public audit and its stabilization window.

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
