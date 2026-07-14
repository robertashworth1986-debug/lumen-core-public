# Security Policy

## Reporting A Vulnerability

Do not open a public issue for a suspected vulnerability, leaked credential, private record, or unsafe consequential-action path.

Use a [private GitHub security advisory](https://github.com/robertashworth1986-debug/lumen-core-public/security/advisories/new). Include the affected component, reproduction steps, likely impact, and whether any credential or personal record may have been exposed. Do not include active secrets in the report body.

Reports are handled on a best-effort basis. No response or remediation service-level guarantee is represented by this public research repository.

## Scope

In scope:

- code and tracked configuration in this repository;
- public pages and public API behavior served by `lumen-core.ai`;
- evidence-integrity controls, manifests, and claim-boundary checks;
- authentication and authorization for consequential-action routes.

Out of scope without separate written authorization:

- denial-of-service testing;
- social engineering;
- destructive testing of third-party accounts or infrastructure;
- attempts to place orders, spend money, submit forms, or modify external records.

## Security Boundaries

This repository is a public technical record, not an assurance that every represented component is production-ready. Private keys, API credentials, tax records, patent records, counsel communications, and privileged source material must remain outside Git.

The `/api/agents/approve` and `/api/agents/log` routes require a server-configured `LUMA_HUMAN_UNLOCK_TOKEN`. The gateway applies the same requirement to grant and opportunity mutations, including outreach dispatch, and to operator mutations under the master, sell, buy, smart-scanner, Kraken sampler, and spike-hunter routes, plus ML-trigger and Node-RED ingest actions. If the token is absent, those mutations and private-log access are disabled. The token must be supplied only by a trusted operator client as a bearer token; it must never be embedded in public browser assets.

Read-only queue responses remove raw source metadata because queued emails, applications, and tickets can contain private fields. Approval receipts are SHA-256 chained for tamper evidence, but a hash chain is not a substitute for access control, backup, or independent audit.

## Repository Hygiene

- Never commit `.env` files, credentials, tokens, private keys, or account exports.
- Treat generated dashboards and logs as untrusted until scanned for secrets and personal information.
- Pin or review third-party actions and dependencies before production use.
- Keep scheduled monitoring workflows read-only; do not grant write access to jobs that only collect status.
- Use strict SSH host verification for deployment.
- Rotate any credential that may have entered Git history, logs, screenshots, or workflow artifacts.

## Evidence Integrity

Historical evidence artifacts should not be silently rewritten. Corrections must produce a new dated artifact or an explicit supersession record. Preserve failures and non-wins, and keep public claims no stronger than the underlying evidence maturity.
