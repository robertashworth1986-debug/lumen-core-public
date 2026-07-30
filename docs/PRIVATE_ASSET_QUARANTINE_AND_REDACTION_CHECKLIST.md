# Private Asset Quarantine and Redaction Checklist

## Purpose

Screenshots and uploaded files can contain strong operating evidence, but they can also expose personal, legal, financial, account, infrastructure, credential, or third-party information. This checklist defines what must remain private and what must be redacted before any asset is copied into the public repository, website, investor material, grant attachment, or reviewer packet.

## Never publish directly

Keep the unredacted original outside the public repository when an asset contains any of the following:

- passwords, API keys, access tokens, recovery codes, QR codes, session cookies, or authentication secrets;
- tax identifiers, banking details, payment-card data, transaction identifiers, account balances, or private billing history;
- Social Security numbers, dates of birth, personal addresses, private telephone numbers, signatures, identity documents, or family records;
- private email addresses, mailbox message IDs, thread IDs, draft IDs, or full private conversation history;
- UEI, CAGE, NCAGE, SAM, JCP, SPRS, DIBBS, Grants.gov, agency-portal, or contractor-account screens containing non-public profile or status details;
- unpublished patent-enabling details, counsel communications, privileged material, invention assignments, or confidential filing strategy;
- server addresses, usernames, filesystem paths, private logs, topology, host keys, environment variables, or operational credentials;
- customer, reviewer, evaluator, Government, university, laboratory, consortium, investor, or partner information that was not authorized for publication;
- vehicle, court, medical, insurance, power-of-attorney, housing, family, or other personal records.

## Redaction standard

A public derivative must:

1. be created from a copy, never by overwriting the only original;
2. permanently remove sensitive pixels or text rather than covering them with a movable shape;
3. crop unrelated browser chrome, notifications, tabs, account avatars, and background windows;
4. remove EXIF or other embedded metadata where practical;
5. replace private identifiers with bounded labels such as `[REDACTED ACCOUNT]` or `[PRIVATE IDENTIFIER]`;
6. preserve the minimum context needed to support the named fact;
7. include a caption stating what the image proves and what it does not prove;
8. record the source date and whether the underlying state may have changed;
9. retain the unredacted original only in founder-controlled private custody;
10. receive a final visual review at 100% zoom before publication.

## Evidence treatment

A screenshot proves only the visible state at the captured time. It does not automatically establish:

- delivery, receipt, review, acceptance, award, funding, payment, customer adoption, or partnership;
- current portal or account status after the capture time;
- legal compliance, certification, eligibility, or authorization;
- independent validation, field performance, production readiness, or realized savings;
- ownership or transfer of intellectual-property rights.

## Publication decision

Use this decision sequence:

- **Public-safe and necessary:** publish the minimum redacted derivative with a bounded caption.
- **Useful but sensitive:** summarize the fact in text and retain the screenshot privately.
- **Personal or privileged:** quarantine; do not publish or summarize beyond what is necessary.
- **Stale or conflicting:** retain as historical evidence and label it non-current.
- **Conceptual rather than evidentiary:** route to `CONCEPTUAL_RND_AND_VISUAL_ASSET_BOUNDARY.md`.

## Public derivative record

For every redacted public derivative, record:

- source asset identifier;
- capture date;
- redaction date;
- person who reviewed the redaction;
- public claim supported;
- limitations and staleness risk;
- public file hash;
- private-original custody location, recorded without exposing that location publicly.

## Operating rule

**Publish the fact, not the account. Preserve the original privately. Expose only the minimum artifact required for review.**
