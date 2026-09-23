# Cloudflare static recovery preview

This directory packages the exact governed LumenCore public-site release
`1ce7c35975a4011fa844e8b39ccbc950c8c0f398` as a Cloudflare Worker with Static
Assets. It is a recovery preview, not a production-domain cutover.

This advances canonical active outcome 2—reviewer-surface continuity. It does
not create a new product, platform, dashboard, or evidence claim.

## Boundaries

- Only the 43 files selected by
  `code/deploy/package_public_site_release.py` are materialized. Mutable
  dashboard data, credentials, logs, operator controls, and private evidence
  are not uploaded.
- `/`, `/evidence/`, and the ProofLock console root are mapped to their exact
  release assets.
- `/api/*`, `/auth/*`, `/ws*`, and `/health` fail closed with a `503` HOLD
  response because the origin backend has not been migrated.
- The Worker adds the six security headers required by the retained public-site
  policy plus a preview-only `X-Robots-Tag` that prevents indexing.
- `wrangler.jsonc` disables live `workers.dev` traffic and enables only
  version-scoped preview URLs. It declares no custom domain, DNS route, zone
  mutation, KV/D1/R2 binding, secret, or private origin.

## Verify locally

From this directory:

```bash
npm ci
npm run check
npm run dev -- --ip 127.0.0.1 --inspector-ip 127.0.0.1
```

`npm run prepare:site` reconstructs the release from immutable Git blobs,
verifies the 43-file manifest and archive hash, and writes only the ignored
`site/` and `.release/` directories.

## Deploy a preview

After authenticating Wrangler to the intended Cloudflare account:

```bash
npm run status
npm run deploy:preview
```

The command reruns every local gate, uploads a version without deploying it to
live traffic, and creates the `recovery` preview alias. Review that version URL
before any separate custom-domain or nameserver decision. A preview upload does
not authorize a production DNS cutover and does not establish dynamic-service
recovery.

Cloudflare cannot upload a version until the named Worker exists. If
`npm run status` confirms that `lumencore-recovery-preview` has never been
created, the account owner must separately authorize this one-time bootstrap:

```bash
CLOUDFLARE_RECOVERY_BOOTSTRAP_APPROVAL=BOOTSTRAP_CLOUDFLARE_RECOVERY_PREVIEW \
  npm run bootstrap:preview
```

The approval-gated bootstrap reruns every check and creates the Worker and its
initial deployment record. Because `workers_dev` is false and the configuration
contains no route or custom domain, it does not attach production traffic. Do
not use the bootstrap command when the Worker already exists; subsequent
preview updates use `npm run deploy:preview`.
