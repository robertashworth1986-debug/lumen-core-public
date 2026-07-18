# Contributing to LumenCore™

Thank you for reviewing LumenCore and considering a contribution.

LumenCore is a founder-built proof-to-pilot architecture. This public repository is a bounded review surface containing reviewer-safe code, documentation, dashboards, manifests, tests, and evidence artifacts. It is not a representation that every module is production-deployed, independently validated, certified, revenue-generating, or available for unrestricted external modification.

## Before contributing

Please read:

- `README.md`
- `SECURITY.md`
- `docs/CLAIM_BOUNDARY_REGISTER.md`
- `docs/FOUNDER_IP_AND_EXTERNAL_REVIEW_BOUNDARY.md`
- any path-specific README or evidence receipt relevant to the proposed change.

Security vulnerabilities must be reported privately through the process in `SECURITY.md`, not through a public issue.

## Useful contribution types

Contributions are most useful when they improve one bounded concern:

- reproducibility and deterministic verification;
- tests and negative-result coverage;
- accessibility, responsive behavior, or browser compatibility;
- documentation and reviewer quickstarts;
- evidence manifests, schemas, and source mapping;
- fail-closed release controls;
- dependency, workflow, or supply-chain hardening;
- public-safe service and product clarity;
- correction of stale or unsupported claims.

Do not combine unrelated platform expansion, outreach, deployment, compliance certification, and evidence changes in one pull request.

## Claim discipline

Every contribution must preserve the distinction between:

- measured;
- replayed;
- synthetic;
- modeled;
- estimated;
- externally validated.

Do not introduce claims of customer status, partnership, agency endorsement, independent validation, field performance, savings, revenue, safety, certification, patentability, award status, or superiority without directly cited documentary evidence and an explicit authorization boundary.

A hash proves identity or custody within its declared scope. It does not prove substantive truth, safety, legal rights, or release authority.

## Intellectual-property boundary

Reviewing or contributing to this repository does not transfer ownership of pre-existing LumenCore architecture, module names, lexicon, designs, private artifacts, or patent-sensitive material.

Do not submit confidential employer information, third-party proprietary material, controlled technical data, personal records, credentials, or content you do not have authority to contribute.

Contributions accepted into the repository are licensed under the repository license. Pre-existing founder-owned material remains subject to the boundaries documented in the repository.

## Development workflow

1. Start from the current default branch.
2. Create a narrowly named branch.
3. Change one concern.
4. Add or update tests.
5. Run the focused tests and any affected baseline tests.
6. Record exact results, including failures and known limitations.
7. Open a draft pull request.
8. Keep deployment, submission, certification, outreach, and legal actions outside the code change unless explicitly authorized.

## Pull-request requirements

A pull request should state:

- purpose and scope;
- exact paths changed;
- evidence or issue being addressed;
- test commands and exact results;
- claim-boundary impact;
- security impact;
- backward-compatibility or deployment impact;
- open blockers;
- what was not deployed, submitted, certified, or externally claimed.

Historical evidence packets and receipts should not be rewritten to look current. Create a new dated artifact when the underlying state changes.

## Style and safety

- Never commit credentials or private keys.
- Prefer deterministic local behavior and repository-pinned dependencies.
- Keep workflow permissions least-privileged.
- Preserve immutable evidence and historical receipts.
- Keep browser and Python/CLI verification rules in parity where both exist.
- Add regression tests for any corrected security or authority invariant.
- Prefer accessible semantic HTML and reduced-motion support.
- Avoid unnecessary build systems or external runtime dependencies for static reviewer surfaces.

## Review standard

The review standard is not “does it sound impressive?” It is:

- Can another person reproduce it?
- Is the source identified?
- Is the comparator fair and frozen?
- Was the metric chosen before scoring?
- Are negative results retained?
- Are limitations explicit?
- Does the system fail closed when authority or evidence is missing?

Evidence before claims.
