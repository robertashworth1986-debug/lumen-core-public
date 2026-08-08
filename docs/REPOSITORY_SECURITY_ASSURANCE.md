# Repository Security Assurance

## Decision

The public repository now has configured first-party source and dependency
security controls. Production remains on `HOLD`.

This lane is intentionally bounded to repository source and dependencies that
GitHub can identify from the checked-out public project. It does not scan the
VPS operating system, reverse proxy, DNS, cloud accounts, private stack,
production secrets, network controls, or a deployed container image.

## Implemented control surfaces

| Surface | Control | Trigger | Failure meaning |
|---|---|---|---|
| Python and JavaScript/TypeScript source | CodeQL `security-extended` queries with the action pinned to an immutable commit | Pull request, push to `main`, weekly schedule, manual run | The analysis job or SARIF upload did not complete. A successful job does not mean zero vulnerabilities. |
| Declared dependency changes | GitHub dependency review pinned to an immutable commit | Pull request | The proposed change introduces a high or critical advisory in a runtime or development dependency, or the review could not complete. |
| Current dashboard dependency set | Lockfile remediation for GHSA-fgmj-fm8m-jvvx and GHSA-hmw2-7cc7-3qxx | Install, audit, verifier, and pull-request checks | The lock resolves ECharts 6.1.0, ECharts GL 2.1.0, form-data 4.0.6, and a peer-compatible Three.js set. Alert closure still depends on the default branch ingesting the merged lockfile. |
| Dependency maintenance | Dependabot version-update proposals | Weekly | An update proposal may still require compatibility testing and human review. Nothing is auto-merged. |
| Vulnerability intake | Private GitHub advisory route and direct security contact | Reporter initiated | A report enters the bounded triage process; receipt is not validation of the report. |
| Remediation governance | Severity, containment, target, exception, and closure rules in `SECURITY.md` | Confirmed finding | A finding remains open until a correction or explicitly bounded, expiring exception is recorded. |

## Evidence protocol

For a named commit, retain the workflow URL, run ID, conclusion, analyzed
languages, action commit, event, source commit, and any resulting alert or
remediation reference. A green run establishes only that the named scan or gate
completed under its recorded configuration.

The machine register is
[`config/repository_security_assurance_v1.json`](../config/repository_security_assurance_v1.json).
The dependency-free verifier is
[`code/ops/VERIFY_REPOSITORY_SECURITY_ASSURANCE.py`](../code/ops/VERIFY_REPOSITORY_SECURITY_ASSURANCE.py).

For the current branch, `npm audit --omit=dev --audit-level=moderate` reports
zero known vulnerabilities in the declared dashboard dependency tree. This is
a time-bound registry result, not a vulnerability-free or runtime-safety claim.

## Claim boundary

These controls do **not** establish a vulnerability-free codebase, a
penetration test, external security audit, SOC 2, ISO 27001, FedRAMP,
production hardening, secure secret handling, live-domain parity, or permission
to deploy. Findings, incomplete scans, and unavailable dependency metadata must
remain visible; they are not converted into passing evidence.

## Next gates

1. Retain successful current-`main` CodeQL results for both configured languages.
2. Retain a successful dependency-review result on an actual dependency-changing pull request.
3. Inventory and scan the deployable container and VPS/runtime layers.
4. Run an authorized independent penetration test against an agreed non-production target.
5. Bind remediation and notification terms to a buyer-specific contract before confidential or regulated data is handled.
