# Security Policy

## Scope

This repository is a public, reviewer-safe surface for LumenCore code, documentation, dashboards, evidence manifests, and bounded demonstrations. It must not contain production credentials, private keys, API secrets, classified or controlled information, personal records, raw submission credentials, or private patent-sensitive material.

## Reporting a vulnerability

Do not open a public GitHub issue for a suspected vulnerability that could expose credentials, private data, deployment access, evidence integrity, release authority, or a reproducible exploit.

Use GitHub's private security-advisory channel:

`https://github.com/robertashworth1986-debug/lumen-core-public/security/advisories/new`

Or contact:

**Robert Ashworth**<br>
Founder / Systems Architect, LumenCore<br>
`robertashworth4444@gmail.com`

Suggested subject:

`[SECURITY] LumenCore responsible disclosure`

Include, where safe:

- the affected path, commit, release, or URL;
- a concise description of the issue;
- reproduction steps;
- observed and expected behavior;
- the security impact;
- any suggested mitigation;
- whether the report contains sensitive information that should not be redistributed.

Do not include live credentials, personal data, or destructive proof-of-concept payloads unless specifically requested through a secure channel.

## Response process

LumenCore will use a best-effort process to:

1. acknowledge a credible report;
2. reproduce and classify the issue;
3. place affected promotion or deployment paths on `HOLD` when appropriate;
4. correct the issue in a bounded branch;
5. add regression coverage when practical;
6. document the exact affected and corrected commits;
7. publish a limited advisory after remediation when disclosure is safe and useful.

No response-time guarantee or bug-bounty payment is currently offered.

## Supported versions

The actively supported security surface is the current default branch and any explicitly identified current release. Historical commits, archived evidence packets, and old live-release receipts remain immutable records of their exact state and should not be interpreted as supported current deployments.

## Evidence and release integrity

A valid hash or signed artifact establishes identity or custody only within its declared scope. It does not by itself establish safety, authorization, substantive truth, operational readiness, or permission to promote a claim.

Security-sensitive changes should preserve fail-closed behavior, least-privilege workflow permissions, deterministic verification, explicit claim boundaries, and separation between integrity and human release authority.
