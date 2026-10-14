# LumenCore | Reviewer Start Here

**A clear route from the company thesis to executable evidence.**
Robert Ashworth · Founder / Systems Architect

[Website](https://lumen-core.ai/) ·
[Repository](https://github.com/robertashworth1986-debug/lumen-core-public) ·
[Investor brief](../INVESTOR_BRIEF.md) ·
[Full evidence index](../EVIDENCE_INDEX.md) ·
[Portfolio and maturity map](PLATFORM_PROOF_AND_COMMERCIALIZATION_MAP.md)

## Technical review route

1. Record the exact Git commit under review and run the five-minute checks below.
2. Inspect the verifier and its adversarial tests, then the existing assurance
   crosswalk and production HOLD gates.
3. Use the full-suite setup below for current source behavior. Use the separately
   pinned executor handoff for the frozen scientific computation.
4. Follow the [portfolio map](PLATFORM_PROOF_AND_COMMERCIALIZATION_MAP.md) to
   each asset's implementation, evidence and next gate. Record reproducible
   findings with the command, environment, expected result and observed result.

**Source and live delivery are separate checks.** The October 7, 2026
[live audit](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37614701203)
of source `e5487b6d` matched 192 of 246 expected files, with 3 mismatches and
51 missing files. Start from this GitHub checkout; a reachable website does not
establish current source parity. This dated observation is not a deployment fix.

## The 90-second overview

LumenCore is a **proof-to-pilot AI infrastructure validation architecture**.
It helps a buyer compare an AI, forecasting, routing, or infrastructure
candidate against an accepted baseline, then packages the result, constraints,
provenance, and decision authority into an inspectable Proof Capsule.

LumenCore is the platform. ProofLock is its evidence and claim-governance layer.
The primary paid entry point is the **Buyer-Owned Baseline Validation Sprint**:
one authorized source, one accepted incumbent baseline, one locked primary
metric and threshold, one replayable proof package, and one bounded decision.
Lumen Infrastructure Sentinel is the first sector validation lane; the broader
portfolio remains governed research, delivery, or concept work.

| Question | Evidence to open | What it establishes |
|---|---|---|
| Is there an implementation I can run? | [Proof Capsule quickstart](../QUICKSTART.md) | Current-checkout schema, file custody, manifest, and claim-gate checks. |
| Is there a replayable computation? | [Pinned executor handoff](CODECHECK_INDEPENDENT_EXECUTOR_HANDOFF_2026-07-21.md) | A frozen computation with three first-party replay suites and 31/31 assertions in the dated July 21 receipt. |
| Are governance controls inspectable? | [14-control assurance crosswalk](INSTITUTIONAL_ASSURANCE_CROSSWALK.md) | Evidence-linked implemented, documented, scoped, prepared, buyer-specific, and open states. |
| Is there a controlled delivery path? | [Buyer-owned sprint offer](LUMENCORE_BOUNDED_VALIDATION_SPRINT_OFFER.md) | Defined scope, acceptance, rights, payment, and decision gates; prices remain untested with buyers. |

**Current decision:** non-confidential fit review and buyer-specific scoping.
**Production decision: `HOLD`.** Independent execution, buyer acceptance,
customer revenue, field savings, and certification remain open milestones.
The [readiness dossier](INSTITUTIONAL_READINESS_DOSSIER.md) makes those gates
specific. The machine-readable portfolio receipt records zero subscription-ready
lanes; research breadth does not establish customers or deployed products.

## A focused team review

### October 14 follow-up: code review and launch decision

This continuation advances active outcome 2 using the existing reviewer path.
An outside code review should return a written assessment of code quality,
security, scalability, reusable components and the work required for a bounded
launch. Record the agreed scope, effort and cost ceiling separately before paid
work begins. A proposed review, an AI-assisted scan or a passing first-party
test run does not establish completed independent evaluation. A human reviewer
should identify the commands they executed and own their written conclusions.

Start with one reproduction, then inspect the controls below. Return each
blocker with severity, file/line, expected and observed behavior, remediation
and a bounded effort estimate. Separate repairable components from any component
that needs replacement; state the assumptions behind a rebuild estimate.

| Review question | Current-source focus | Remaining acceptance gate |
|---|---|---|
| Can an order bypass the intended boundary? | Kraken permits enumerated read-only private calls and explicitly validated `AddOrder`; batch, amend, edit and unknown private calls reject before transport. Alpaca does not automatically retry a mutation after an ambiguous transport failure. | Broker reconciliation, idempotent intent/recovery design and prospective after-cost paper evaluation. No live order authority follows from these repairs. |
| Do malformed inputs fail predictably? | Forecast CSV parser failures use the structured rejection path. Non-ASCII operator tokens reject through HTTP/WebSocket authorization. | An outside reviewer must test the actual deployed boundary separately. Local tests are not a penetration test. |
| Can the serving path support a buyer workload? | Inspect the bounded gateway executor and lifetime lock, then forecast calendar/history scans, input budgets and ledger ownership. | Define input size, arrival rate, latency, queue limits, cancellation and resource budgets before a controlled load test. No institutional throughput claim is established. |
| What is the smallest deliverable a buyer can accept? | One authorized data package, accepted baseline, locked metric, explicit limitations and a reviewer-readable decision record. | Named technical and budget owners, handling agreement, accepted scope and required payment; tests and referrals do not establish revenue. |

After installing the full-suite environment below, reproduce the changed boundaries:

```bash
python -m pytest -q tests/test_order_safety_gate.py tests/test_order_safety_facades.py tests/test_order_safety_alpaca_paper_boundary.py
python -m pytest -q tests/test_forecast_evaluation_v2.py tests/test_operator_api_access.py
```

### Read the early rolling dashboards as historical research

The [estate scope review](LUMENCORE_ESTATE_SCOPE_REVIEW_2026-10-04.md) locates the
earlier Mission Control, Quant Lab, trading sweeps and simulation outputs. Their
existence is useful implementation history; a rolling display, Monte Carlo run
or frozen hash does not by itself demonstrate a profitable decision.

In particular, [the infrastructure loop builder](../code/infra_live_loop_builder.py)
contains fixed row counts, improvement percentages and assumed hourly loss
rates; it does not fetch those rows or measure an achieved improvement. The
[constraint detector](../code/execution/institutional_constraint_detector.py)
simulates provider failures and labels one minus modeled impact an optimization
gain. Neither output is a measured saving or cash receipt. Do not execute the
historical builder as a review shortcut: it has top-level filesystem writes.
The [historical harmonic tournament](../code/institutional_harmonic_suite.py)
also retains same-period signal accounting, clipped returns and test-dependent
selection. October 13 accounting repairs in other engines do not repair or
retroactively validate this historical tournament.

Continuous source capture can support new hypotheses. To test one, use a
timestamped authorized source, an accepted baseline, a frozen candidate and
evaluation rule, then prospective shadow measurement and human review. Trading
must retain fees, spread, slippage, fill/exit failures, drawdowns and account
reconciliation. Infrastructure value needs a buyer-owned action and measured
cost/benefit after operating overhead. Neither path guarantees a positive result.
The [public metrics contract](PUBLIC_METRICS_CONTRACT.md) still records four
unresolved legacy feed contracts; gateway liveness is not live-data freshness.

### October 13 repair review, including trading

The current-source repair pass adds a versioned forecast reviewer, receipt
reconciliation, cross-runtime ProofLock serialization, private-output access
controls, bounded gateway work and paper-trading accounting checks. Record the
exact checkout before running them. Frozen v1 scientific code and results remain
historical evidence; these repairs do not silently restate their results.

After installing the full-suite environment below, start with:

```bash
python -m pytest -q tests/test_execution_accounting_regressions.py tests/test_order_safety_gate.py tests/test_order_safety_alpaca_paper_boundary.py
python -m pytest -q tests/test_forecast_evaluation_v2.py tests/test_codecheck_independent_execution_receipt.py tests/test_eia_constraint_strict_verifier.py
python -m pytest -q tests/test_prooflock_canonicalization_parity.py tests/test_operator_api_access.py tests/test_gateway_runtime_concurrency.py tests/test_gateway_lifetime_lock.py
```

The trading fixtures check future-data isolation, delayed signals, after-cost
accounting, first-loss drawdown, finite risk inputs, capped sizing and append-only
ledger recovery. They contact no broker and place no orders. They do not establish
profitability, prospective paper performance or reconciled historical balances.
The ledger retains historical bytes; a corrected projection is not a broker
reconciliation or a corrected historical profit claim.

Run the separately pinned synthetic forecast command in
[Forecast evaluation v2](FORECAST_EVALUATION_V2_REVIEW.md). Its deliberately
adverse comparison remains visible and the report always returns
`HUMAN_REVIEW_HOLD`. Complete input identities and calendar/as-of timing are
software checks; supplied feature causality, publication history, data rights,
accepted baseline and independence still require human review.

ProofLock's new v2 serialization is explicitly versioned and uses tagged binary64
numbers and scalar Unicode key ordering; it is not JCS. Historical portable v1
sample bytes remain unchanged. Ambiguous v1 numbers or strings reject rather
than receiving a new silent identity. See the
[compatibility contract](../dashboard/build_week/prooflock_console/CANONICALIZATION.md).

For a separate clean serving smoke, use CPython 3.11.9 and a fresh environment:

```bash
python3.11 -m venv .venv-gateway-minimal
. .venv-gateway-minimal/bin/activate
python -m pip install --require-hashes --only-binary=:all: -r requirements-gateway-minimal-ubuntu-py311.lock
python code/ops/VERIFY_GATEWAY_MINIMAL_RUNTIME.py --smoke
```

This smoke uses ephemeral loopback HTTP and the explicit minimal reviewer
profile. It starts no legacy providers, market workers or control loops; its
forecast/operator components remain HOLD. It does not establish the full legacy
gateway dependency closure, shared producer coordination or live server parity.
Use the separate [runtime CI](../.github/workflows/gateway-runtime-ci.yml) for
native Linux/Windows lifetime-lock checks. Current-source tests and a static
release build do not enact nginx or gateway changes on a server.

Start together with the five-minute check, then divide the inspection by question.
The first pass can stay within these existing surfaces; the portfolio is context,
not a requirement to inspect every historical experiment.

| Track | Inspect first | Decision to return |
|---|---|---|
| Code and security | [Verifier](../code/proof_capsule_verifier.py), [adversarial tests](../tests/test_proof_capsule_verifier.py), [ProofLock threat model](../dashboard/build_week/prooflock_console/THREAT_MODEL.md), [dependency controls](REPOSITORY_SECURITY_ASSURANCE.md) | Can malformed, oversized or tampered evidence pass? Which trust assumptions need stronger controls? |
| Reproducibility and forecasting | [Frozen executor handoff](CODECHECK_INDEPENDENT_EXECUTOR_HANDOFF_2026-07-21.md), [constraint comparisons](CODECHECK_EIA_EXECUTABLE_COMPUTATION_NOTE_2026-07-20.md), [strict identity verifier](../code/ops/VERIFY_EIA_CONSTRAINT_REVIEW.py) | Can the named computation be repeated, and do its failed gates support the stated HOLD decision? |
| Systems and delivery | [Readiness dossier](INSTITUTIONAL_READINESS_DOSSIER.md), [release workflow](../.github/workflows/public-site-supply-chain.yml), [incident plan](INCIDENT_RESPONSE_AND_CONTINUITY_PLAN.md), [buyer-owned scope](LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md) | What is the smallest externally testable offer, and which controls must close before deployment? |

Return findings with the **commit, environment, command, expected behavior,
observed behavior, severity and proposed next gate**. Separate a reproduced
defect from a question or design recommendation. Report security findings through
the private route in [SECURITY.md](../SECURITY.md), without posting credentials
or sensitive reproduction data in a public issue.

## Reviewing the full portfolio

The [portfolio map](PLATFORM_PROOF_AND_COMMERCIALIZATION_MAP.md) covers trading,
Grant Factory, Mission Control, Quant Lab, ProofLock, energy and thermal research,
HyperCore, EchoLock, LumaJet, LumaSkin, digital-twin concepts and Node-RED/immersive
integrations. Start with the asset-specific maturity, source and next gate.
Historical implementation, a current source file, a simulated result and a
publicly operating service are different evidence states. Private-held receipts
are identified separately from public artifacts.

## The five-minute verification path

From a clean checkout, use Python 3.10 or newer. These checks require no API
key, private data, live service, or third-party Python package:

```bash
python code/proof_capsule_verifier.py examples/proof_capsule/dice_eia_public_capsule.json --root .
python -m unittest discover -s tests -p "test_proof_capsule_verifier.py" -v
```

The first command must return `"valid": true`. Inspect the receipt's
`verification_scope`, `capsule_file_sha256`, `declared_external_validation_status`,
and `human_unlock_required` fields. The second command checks valid and
adversarial paths. Passing establishes only the declared schema, custody, and
claim-gate behavior; it does not reproduce the underlying experiment.

To inspect governance consistency, run:

```bash
python code/ops/VERIFY_INSTITUTIONAL_ASSURANCE_CROSSWALK.py
python code/ops/VERIFY_INSTITUTIONAL_READINESS.py
```

These verify the declared registers, evidence paths, statuses, limitations,
and workflow bindings. They do not establish independently assessed control
operating effectiveness. The [ProofLock demonstration](https://lumen-core.ai/build_week/prooflock_console/)
provides a visual companion to the evidence and decision gates.

## Full current-source test suite

Use Ubuntu 24.04 x86-64 and CPython 3.11.9, matching the existing
[institutional workflow](../.github/workflows/institutional-readiness.yml).
Use a normal user account: POSIX permission tests intentionally skip under root.
Record `git rev-parse HEAD` with every result; a branch test is not a main-branch
or live-release attestation.

```bash
git clone https://github.com/robertashworth1986-debug/lumen-core-public.git
cd lumen-core-public
git rev-parse HEAD
git fetch origin 1c0eb51754beffac6f4df484914e35efc21c253f
git cat-file -e '1c0eb51754beffac6f4df484914e35efc21c253f^{commit}'
python3.11 -c 'import sys; assert sys.version_info[:3] == (3, 11, 9)'
python3.11 -m venv .venv
. .venv/bin/activate
python code/ops/VERIFY_INSTITUTIONAL_DEPENDENCY_LOCK.py
python -m pip install --require-hashes --only-binary=:all: -r requirements-institutional-ubuntu-py311.lock
python -m pip check
PYTHONHASHSEED=0 TZ=UTC OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  python -m pytest -q -rs --durations=20 --junitxml=out/institutional-readiness/reviewer-suite.xml
```

The explicit fetch supplies the historical author-package objects used by
`test_codecheck_eia_mainline_integration.py`. A shallow or single-branch checkout
can lack them even after deepening main. Do not weaken those checks or replace
the pinned identity to make a run pass. Inspect all reported skips: generated
publication fixtures, Windows process checks and the optional Zig compiler have
separate prerequisites; Linux success does not imply those paths executed.

The October 10 [main-source run](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/38011625758)
at `c8bfc2f9` recorded 1,466 passed tests, 8 skips and 201 subtests in the
full-repository job. Those are dated first-party checks, not independent review.
The [review-preparation PR #245](https://github.com/robertashworth1986-debug/lumen-core-public/pull/245)
incorporates the existing PDF security repair from
[PR #210](https://github.com/robertashworth1986-debug/lumen-core-public/pull/210):
`pypdf==6.19.0`, the hash-locked distributions and six generated-fixture checks.
It also removes the unused TensorFlow.js dependency chain responsible for the
October 7 npm audit failure and updates urllib3 to 2.8.0 after a fresh Python
audit found three transport advisories. Review the exact commit's checks and the
[dated security record](REPOSITORY_SECURITY_ASSURANCE.md) before relying on
these changes; a passing source suite is not a deployment receipt.

## Open gates at the October 7 review

| Gate | Recorded state | Evidence needed to close it |
|---|---|---|
| Independent evaluation | First-party checks exist; independent execution is pending. | A qualified evaluator's complete execution receipt and deviations. |
| Live static release | October 7 audit: 192/246 files match, 3 differ, 51 are missing. | Authorized exact-main release, signed provenance and complete live-byte verification. |
| Operational data | [Issue #234](https://github.com/robertashworth1986-debug/lumen-core-public/issues/234) retains four unavailable legacy feeds. | Owner-approved producer, route, schema and freshness contracts with end-to-end verification. |
| Server recovery | The October 4 diagnosis identified paper-ledger ownership and gateway source/identity gaps; source preparation does not repair them. | Existing guarded [ledger repair](../.github/workflows/repair-paper-ticker-ledger.yml) and [gateway repair](../.github/workflows/repair-gateway-dependency-closure.yml), with runtime readback and rollback evidence. |
| Repository assurance | Main-branch protection remains unenforced; the historical provider-key closure lacks a non-secret receipt. | Founder-approved branch enforcement with a recovery path, and provider rotation/revocation plus history reconciliation. |
| Supplemental AI scan | The October 7 [AI review job](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37649823151) failed before analysis because account quota was exhausted. | A completed scan after account availability is restored; this is not a passing scan or a code finding. |

These gates distinguish **ready for technical review** from approval to deploy,
handle buyer data or make externally validated performance claims. CodeQL and
the maintained test jobs have their own receipts and do not replace an incomplete scan.

## September 21 constraint evidence

The [current computation note](CODECHECK_EIA_EXECUTABLE_COMPUTATION_NOTE_2026-07-20.md)
includes two retained historical windows, all baseline comparisons and the
remaining HOLD gates. Verify both reviewed packet identities with:

```bash
python code/ops/VERIFY_EIA_CONSTRAINT_REVIEW.py
```

This standard-library check requires the reviewed manifest pins and complete
input/output membership. It checks artifact integrity, not the scientific
merit of the comparison or independent validation. The original frozen runners
remain unchanged for historical reproducibility; their membership-only checks
are superseded by this strict verifier.

## The stronger pinned computation

The externally executable computation is frozen at commit
`1c0eb51754beffac6f4df484914e35efc21c253f`. It requires **Ubuntu 24.04 x86-64**,
**CPython 3.11.9**, and `requirements-reviewer-ubuntu-py311.lock`;
a Windows or different-Python run is not protocol-matched evidence.

Follow the [executable-computation note](CODECHECK_EIA_EXECUTABLE_COMPUTATION_NOTE_2026-07-20.md)
and [independent-executor handoff](CODECHECK_INDEPENDENT_EXECUTOR_HANDOFF_2026-07-21.md).
Compare the six declared outputs with the
[July 21 first-party receipt](../evidence/reproducibility/codecheck_reviewer_container_1c0eb517_20260721/reviewer_reproducibility_receipt.json).
Preserve failures and deviations, including the declared post-observation
numeric-portability amendment. A passing replay does not erase a failed
promotion or coverage gate in the underlying result.

No non-author execution receipt or CODECHECK certificate is currently claimed.
This is the next technical validation milestone, not a completed external result.

## Deeper diligence, by decision

| Review area | Canonical source | Machine evidence or related control |
|---|---|---|
| Company and commercial focus | [Investor brief](../INVESTOR_BRIEF.md); [current validation offer](STRATEGIC_TRANSACTION_BRIEF_2026-08-08.md) | [Offer contract](../config/bounded_validation_sprint_v1.json) |
| Evidence and research hierarchy | [Canonical Evidence Index](../EVIDENCE_INDEX.md); [governed portfolio audit](LUMENCORE_ENGINE_PORTFOLIO_AUDIT_2026-08-08.md) | [Portfolio receipt](../dashboard/data/lumencore_engine_portfolio_audit.json) |
| Procurement readiness | [Institutional readiness dossier](INSTITUTIONAL_READINESS_DOSSIER.md) | [Readiness register](../config/institutional_readiness_register_v1.json) |
| Standards orientation | [Institutional assurance crosswalk](INSTITUTIONAL_ASSURANCE_CROSSWALK.md) | [Assurance register](../config/institutional_assurance_crosswalk_v1.json) |
| Claim and custody discipline | [Proof Capsule schema](PROOF_CAPSULE_SCHEMA.md); [Claim Boundary Register](CLAIM_BOUNDARY_REGISTER.md) | [Verifier](../code/proof_capsule_verifier.py) |
| Security and recovery | [Repository security assurance](REPOSITORY_SECURITY_ASSURANCE.md); [incident response plan](INCIDENT_RESPONSE_AND_CONTINUITY_PLAN.md) | [Security register](../config/repository_security_assurance_v1.json) |
| Build and release identity | [Exact-snapshot protocol](PUBLIC_SITE_EXACT_SNAPSHOT_PROTOCOL.md); [supply-chain assurance](PUBLIC_SITE_SUPPLY_CHAIN_ASSURANCE.md) | [Signed-attestation receipt](PUBLIC_SITE_SIGNED_ATTESTATION_RECEIPT_2026-08-08.md); [August 12 release receipt](PUBLIC_SITE_EXACT_DEPLOYMENT_RECEIPT_2026-08-12.md) |
| Public security headers | [Separate header deployment receipt](PUBLIC_SECURITY_HEADER_DEPLOYMENT_RECEIPT_2026-08-09.md) | [Header receipt verifier](../code/ops/VERIFY_PUBLIC_SECURITY_HEADER_RECEIPT.py) |
| Buyer rights and delivery | [Non-confidential fit intake](LUMENCORE_BUYER_OWNED_VALIDATION_INTAKE.md); [buyer-specific SOW](LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md) | [Pilot report template](PILOT_REPORT_TEMPLATE.md); [founder IP boundary](FOUNDER_IP_AND_EXTERNAL_REVIEW_BOUNDARY.md) |

The assurance crosswalk maps selected NIST AI RMF, NIST GenAI Profile, NIST CSF,
NIST SSDF, OWASP ASVS, OWASP LLMSVS, and SLSA themes. It is a first-party
informative map, not certification, full conformance, an external audit, or a
penetration test. The repository security register also preserves dated open
credential-history, runtime, and branch-protection gaps. Read the dated source
record before making a present-day security or availability claim.

## Repository evidence and the live domain

Use the [commit-bound repository docket](../dashboard/reviewer_docket.json) for
the checked-out state. The [live docket](https://lumen-core.ai/reviewer_docket.json)
is a convenience projection and may lag the default branch or be unavailable.
Record any mismatch as live-release drift; do not silently substitute one
source for the other.

The named static release `1ce7c35975a4011fa844e8b39ccbc950c8c0f398` has dated
first-party receipts for a 43-file CycloneDX 1.6 inventory, constrained GitHub
OIDC/Sigstore provenance and SBOM verification, human-gated deployment, rollback
capture, 43-of-43 live-byte verification, and a separate read-only audit.
The earlier `e513f65a` release remains in the append-only history; the historical
`5fff567c` receipt retains the first successful signed set. Local verification
can reconstruct the named immutable Git objects when full history is available.
Fresh remote signature and live HTTP checks are separate operations.

These static-release results do not establish today's live parity, a complete
product or VPS SBOM, a SLSA level, sustained availability, gateway provenance,
or broader production authorization. The documented incident tabletop is not
a completed live restoration exercise or an enterprise SLA.

## What would move the decision forward?

A qualified evaluator can execute the frozen package and return a complete
receipt. A prospective buyer can select one workflow, authorize one source,
accept the incumbent baseline and locked success criteria, and name a decision
owner through the [fit intake](LUMENCORE_BUYER_OWNED_VALIDATION_INTAKE.md).
The deliverable retains positive, neutral, incomplete, and negative results,
then supports a human-authorized promote, revise, rerun, hold, or stop decision.

The repository does not by itself establish scientific or field validation,
certified safety, regulatory approval, patent scope, guaranteed performance,
commercial deployment, or customer value. EPRI/OPAI participation is a bounded
contribution path through committee and work-group meetings; it does not
establish endorsement, validation, procurement selection, adoption, award,
or funding.

**Evidence before claims. One source, one baseline, one decision.**
