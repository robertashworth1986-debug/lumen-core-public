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
| Python and JavaScript/TypeScript source | CodeQL `security-extended` queries with action v4.37.8 pinned to immutable commit `db488ddef3bf6cb639b32c2e9a7c0a7ea8271d28` | Pull request, push to `main`, weekly schedule, manual run | The analysis job or SARIF upload did not complete. A successful job does not mean zero vulnerabilities. |
| Declared dependency changes | GitHub dependency review pinned to an immutable commit | Pull request | The proposed change introduces a high or critical advisory in a runtime or development dependency, or the review could not complete. |
| Current dashboard dependency set | Named advisory remediation plus an explicit compatibility and provenance contract | Strict install, full npm tree, audit, verifier, module-load smoke, and pull-request checks | The lock resolves ECharts 6.1.0, ECharts GL 2.1.0, Anime.js 4.5.0, and Three.js 0.185.1. Unused model-viewer and TensorFlow.js are absent; removing TensorFlow.js also removes argparse, sprintf-js and form-data. Alert closure still depends on the default branch ingesting the merged lockfile. |
| Dependency maintenance | Dependabot version-update proposals | Weekly | An update proposal may still require compatibility testing and human review. Nothing is auto-merged. |
| Vulnerability intake | Private GitHub advisory route and direct security contact | Reporter initiated | A report enters the bounded triage process; receipt is not validation of the report. |
| Remediation governance | Severity, containment, target, exception, and closure rules in `SECURITY.md` | Confirmed finding | A finding remains open until a correction or explicitly bounded, expiring exception is recorded. |
| Secret scanning | GitHub secret scanning and push protection, plus the targeted credential-history verifier | Push, remote scan, and bounded manual reconciliation | A detected value or unresolved provider-history gate remains visible; absence from the current tree is not provider rotation or Git-history remediation. |
| Default-branch governance | Exact remote branch-protection observation | Bounded manual reconciliation | `main` was not protected at the recorded observation time; merge discipline in prior PRs is not an enforced repository setting. |

## Unused vulnerable npm chain removal — October 7, 2026

The [PR #245 security job](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37649817353/job/112889903773)
failed at its unchanged moderate audit threshold. The direct dependency
`@tensorflow/tfjs@4.22.0` brought in `argparse@1.0.10` and `sprintf-js@1.0.3`.
[GHSA-hp3w-g68c-fv3c](https://github.com/advisories/GHSA-hp3w-g68c-fv3c)
identifies unbounded precision specifiers as a denial-of-service risk and lists
no patched release. A tracked-source reference audit found no TensorFlow.js
consumer outside the package manifests. The unrelated Python TensorFlow entry
in the historical launcher is not an npm consumer.

This repair removes the unused direct dependency and its transitive closure,
reducing the installed graph from 76 to 10 packages without changing the
remaining package versions. `form-data` leaves with that closure, so its old
override is removed too. The verifier rejects reintroduction of these four
packages in direct, development or optional dependencies, overrides, and root
or nested lock entries. Regression cases exercise all those paths. Existing
Three.js peer, registry, integrity, strict-install and audit controls remain.

On October 7 the candidate passed local strict `npm ci`, `npm ls --all` and
`npm audit --omit=dev --audit-level=moderate`, reporting zero known advisories
under Node 24.19.0/npm 11.9.0. The maintained workflow separately runs pinned
Node 24.18.0 and the existing module-load checks. The six PDF resource and
compatibility cases from PR #210 are incorporated alongside its `pypdf==6.19.0`
lock repair. Review the exact PR/commit CI receipts before merging.

The separate GitHub AI security review failed before analysis on October 7
with an account-quota error. CodeQL completion is a distinct control. No scan
is disabled or relabeled as passing, and no account entitlement is changed.
These are source/dependency repairs, not proof of a remediated VPS, closed
remote alerts, independent assurance or production authorization.

### Python transport dependency check

A fresh `pip-audit==2.10.1` query of every package in the 39-package
institutional lock found three advisories in urllib3 2.7.0, even after applying
the PDF candidate. Upstream identifies 2.8.0 as the fixed release for
[chunk-size buffering](https://github.com/urllib3/urllib3/security/advisories/GHSA-vxq7-64xx-v4gw),
[Deflate streaming](https://github.com/urllib3/urllib3/security/advisories/GHSA-gh4c-6fx4-qh6g)
and [HTTPS proxy TLS isolation](https://github.com/urllib3/urllib3/security/advisories/GHSA-8988-9cw3-xx77).
The institutional lock now uses 2.8.0; the downloaded wheel and source archive
both match their PyPI SHA-256 records. Only pypdf and urllib3 versions change
relative to the prior main lock. The frozen reviewer lock is unchanged.

The [October 7 comparison](../evidence/dependency_security/20261007/comparison.json)
binds both lock identities and retained audit outputs. The candidate query
reports zero known advisories across all 39 explicitly locked packages; it uses
`--disable-pip --no-deps` to audit that complete declared list without resolving
a different environment. This is time-bound advisory coverage, not runtime
verification or a vulnerability-free claim. The normal hash-locked CI install,
`pip check` and full suite remain the compatibility gate.

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

## PDF dependency refresh - September 23, 2026

This refresh advances active outcome 2, a bounded external review or pilot,
by keeping the existing reviewer dependency repair current. The institutional
requirements, complete Ubuntu/Python 3.11.9 hash lock and deadline sentinel
now pin `pypdf==6.19.0`; only pypdf changes among the 39 locked packages.
The separate frozen reviewer dependency files and September 14 receipts are
unchanged. Both distribution hashes were checked against downloaded PyPI bytes.

Upstream published three additional moderate advisories on September 16 and
marks versions below 6.19.0 affected: [appearance-stream generation](https://github.com/py-pdf/pypdf/security/advisories/GHSA-php9-fj8v-98fj),
[alphabetic page labels](https://github.com/py-pdf/pypdf/security/advisories/GHSA-w23x-9jrw-r45c),
and [dictionary-based embedded-file access](https://github.com/py-pdf/pypdf/security/advisories/GHSA-v247-6f48-mgcj).
The September 14 zero-advisory candidate result therefore cannot justify
merging the earlier 6.17.0 pin today.

Fresh `pip-audit==2.10.1` queries nevertheless reported zero known advisories
for both complete 39-package locks, including the affected 6.17.0 baseline.
This scanner/advisory discrepancy is retained, not counted as remediation
evidence. The upgrade decision follows the upstream affected/fixed ranges.

The six generated-fixture PDF tests retain the three prior guards, exercise
both alphabetic-label bounds, and check normal text, outline, metadata and
attachment round trips. Guard configuration uses pypdf's current temporary
configuration API. The two small label counterexamples fail on 6.17.0 because
it does not reject the input; all six pass on 6.19.0. This is a bounded guard
regression, not a resource-exhaustion measurement. Appearance-stream and
embedded-file complexity fixes are covered by the upstream fixed-version
declaration, not independent local attack benchmarks.

The focused local suite passed 76 tests and 3 subtests on Linux/Python 3.12.14.
That supplementary environment does not replay the locked Python 3.11.9
closure; current-head institutional CI remains the integration gate. The
audit outputs, distribution verification and bounded comparison are retained
in `evidence/dependency_security/20260923/`. No production deployment,
default-branch alert closure or external security validation is implied.

## Historical PDF dependency correction - September 14, 2026

The September 14 candidate institutional dependency set and deadline-sentinel workflow pinned
`pypdf==6.17.0`. The institutional Ubuntu/Python 3.11.9 lock changes only
pypdf and its two distribution hashes; its other 38 package versions and the
separate frozen reviewer dependency files remain unchanged.

A current remote observation found three open moderate pypdf advisories:
[cyclic tree insertion](https://github.com/py-pdf/pypdf/security/advisories/GHSA-jp53-mhqp-8xcg),
[outline expansion](https://github.com/py-pdf/pypdf/security/advisories/GHSA-23w6-3w8w-8484),
and [repeated form extraction](https://github.com/py-pdf/pypdf/security/advisories/GHSA-763m-79hh-57f2).
The older August snapshot below is historical, not a current zero-alert claim.

Four small generated-fixture checks in `tests/test_pdf_dependency_security.py`
exercise those three guards and an ordinary PDF text/outline/metadata round
trip. Against pypdf 6.15.0, three checks failed and the compatibility check
passed; against 6.17.0, all four passed. The cyclic-tree check runs in a
separate, five-second-bounded process. Outline and form budgets are reduced
inside the tests, so these checks do not measure default-limit memory use or
establish safety for arbitrary documents. No attached document is executed.

`pip-audit==2.10.1` reported three known advisories in one package for the
baseline 39-package lock, and zero known advisories for the candidate lock at
the recorded query time. The retained package-level outputs and bounded
comparison are in `evidence/dependency_security/20260914/`. A clean dependency
audit is not vulnerability freedom, PDF sandboxing, deployment, or remote
alert closure. Default-branch alerts remain open until an approved merge and
fresh GitHub reconciliation. Existing PR #210 carries this narrow repair;
PR #199 overlaps on pypdf but also proposes broader numerical-library changes.

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

The August dependency audit was a time-bound registry observation. See the
October 7 removal and its dated audit above for the later advisory and repair;
neither observation is a vulnerability-free or runtime-safety claim.

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

September 21 recheck: the read-only GitHub `branches/main` response at commit
`01edc688003e3e22387cd78d7db4715b0f75f675` again reported `protected=false`,
required-status enforcement `off`, and empty required check lists. The
default-branch enforcement gap therefore remains current. This response does
not recheck secret alerts or prove provider-key rotation. The August secret
snapshot above remains explicitly historical.

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
