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
| Current dashboard dependency set | Lockfile remediation for GHSA-fgmj-fm8m-jvvx and GHSA-hmw2-7cc7-3qxx, plus an explicit compatibility and provenance contract | Strict install, full npm tree, audit, verifier, module-load smoke, and pull-request checks | The lock resolves ECharts 6.1.0, ECharts GL 2.1.0, form-data 4.0.6, Anime.js 4.5.0, and Three.js 0.185.1. The unused model-viewer package that required Three.js `^0.183.0` is absent. Alert closure still depends on the default branch ingesting the merged lockfile. |
| Dependency maintenance | Dependabot version-update proposals | Weekly | An update proposal may still require compatibility testing and human review. Nothing is auto-merged. |
| Vulnerability intake | Private GitHub advisory route and direct security contact | Reporter initiated | A report enters the bounded triage process; receipt is not validation of the report. |
| Remediation governance | Severity, containment, target, exception, and closure rules in `SECURITY.md` | Confirmed finding | A finding remains open until a correction or explicitly bounded, expiring exception is recorded. |
| Secret scanning | GitHub secret scanning and push protection, plus the targeted credential-history verifier | Push, remote scan, and bounded manual reconciliation | A detected value or unresolved provider-history gate remains visible; absence from the current tree is not provider rotation or Git-history remediation. |
| Default-branch governance | Exact remote branch-protection observation | Bounded manual reconciliation | `main` was not protected at the recorded observation time; merge discipline in prior PRs is not an enforced repository setting. |

## Visual dependency compatibility decision — August 31, 2026

Dependabot PR #189 proposed Anime.js 4.5.0 and Three.js 0.185.1. A strict
`npm ci` reproduction rejected that graph because `@google/model-viewer` 4.3.1
requires Three.js `^0.183.0`. A repository reference audit found no dashboard
source that imports or renders model-viewer; outside the package files, it was
only an optional recommendation in the modernization sweep. Removing that
unused package is therefore narrower and more truthful than forcing npm or
downgrading the requested Three.js update.

The bounded repair therefore makes the deployable compatibility decision
explicit:

- upgrade Anime.js from resolved version 4.4.1 to 4.5.0 and require its Three.js
  adapter exports to load;
- upgrade Three.js to 0.185.1, which satisfies Anime.js 4.5.0 and
  postprocessing 6.39.4;
- remove model-viewer from both the package graph and the modernization
  recommender so an unattended sweep cannot recreate the incompatible graph;
- require `--strict-peer-deps`, explicitly disable force and legacy-peer mode,
  watch root and dashboard `.npmrc` files, and reject workflow/environment
  bypass configuration, manifest/lock divergence, non-registry source or
  malformed SHA-512 integrity for the named remediation packages,
  model-viewer reintroduction, unexpected Three.js peer packages, dependency
  downgrades, and peer-contract drift;
- run `npm ci`, `npm ls --all`, `npm audit --omit=dev
  --audit-level=moderate`, and direct module-load smoke checks on the pinned
  Node 24.18.0 runtime.

This is a declared npm-graph repair, not a claim that the public visual runtime
was upgraded. The primary dashboard field still uses its separately vendored
Three.js 0.160.1 asset and pinned 0.160.1 CDN fallbacks; the ProofLock console
still carries its separate revision-184 module. Neither asset is changed here.
These checks establish a coherent declared dependency graph and bounded
first-party module loading only. They do not establish browser/GPU
compatibility across devices, visual quality, sustained runtime behavior,
vulnerability freedom, production deployment, or external validation.

## Evidence protocol

For a named commit, retain the workflow URL, run ID, conclusion, analyzed
languages, action commit, event, source commit, and any resulting alert or
remediation reference. A green run establishes only that the named scan or gate
completed under its recorded configuration.

The machine register is
[`config/repository_security_assurance_v1.json`](../config/repository_security_assurance_v1.json).
The dependency-free verifier is
[`code/ops/VERIFY_REPOSITORY_SECURITY_ASSURANCE.py`](../code/ops/VERIFY_REPOSITORY_SECURITY_ASSURANCE.py).

## Exact remote security snapshot — August 12, 2026

At `2026-08-12T06:44:30Z`, the GitHub repository was reconciled against exact
`main` commit `54c81c8526a1193830f9881a51987c506234d896` without printing any
detected value. Secret scanning, secret-scanning push protection, and
Dependabot security updates were enabled. Open Dependabot and CodeQL alert
counts were zero.

Secret scanning initially showed 29 open alerts. Alerts 2 through 29 were all
classified by GitHub as GoCardless live access tokens, but a value-redacted
history audit established that every value exactly matched the removed
generator expression `live_domain_proof_feeds_<UTC_STAMP>`. The 28 alert values
appeared only as deterministic deployment-stage directory identifiers across
51 allowlisted historical deployment-feed locations, and none occurred in the
current tracked tree. Those 28 remote alerts were resolved as false positives
with that bounded basis.

Alert 1 remains open. It is a historical Google API key finding whose detected
value is absent from the current tracked tree, but no non-secret provider
rotation or revocation receipt and no public-history-remediation receipt are
recorded. Its validity remains `unknown`. The existing credential-hygiene gate
therefore remains fail-closed for provider rotation and remote-history closure.
No credential was printed, recovered, tested, used, rotated, or revoked during
this pass.

The default `main` branch was not protected at the same remote observation.
Required status checks and pull-request reviews are operating practices but are
not currently enforced by a GitHub branch-protection setting. Enabling or
changing that account-level setting remains a founder decision because an
incorrect rule could lock out the sole maintainer or block bounded emergency
recovery.

For the current branch, `npm audit --omit=dev --audit-level=moderate` reports
zero known vulnerabilities in the declared dashboard dependency tree. This is
a time-bound registry result, not a vulnerability-free or runtime-safety claim.

## Claim boundary

These controls do **not** establish a vulnerability-free codebase, a
penetration test, external security audit, SOC 2, ISO 27001, FedRAMP,
production hardening, secure secret handling, live-domain parity, or permission
to deploy. They also do not establish provider rotation or revocation, public
Git-history remediation, removal from forks or caches, zero open secret alerts,
or enforced default-branch protection. Findings, incomplete scans, and
unavailable dependency metadata must remain visible; they are not converted
into passing evidence.

## Next gates

1. Rotate or revoke the historical Google/YouTube provider key, retain only a
   non-secret provider receipt, and then reconcile alert 1 without exposing the
   detected value.
2. Decide and apply a founder-safe `main` branch rule only after confirming the
   exact required check names and a recovery path for the sole maintainer.
3. Retain successful current-`main` CodeQL results for both configured languages.
4. Retain a successful dependency-review result on an actual dependency-changing pull request.
5. Inventory and scan the deployable container and VPS/runtime layers.
6. Run an authorized independent penetration test against an agreed non-production target.
7. Bind remediation and notification terms to a buyer-specific contract before confidential or regulated data is handled.
