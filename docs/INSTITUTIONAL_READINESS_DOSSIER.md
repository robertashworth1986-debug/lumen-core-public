# LumenCore Institutional Readiness Dossier

**Register date:** 2026-08-08

**Scope:** public repository and Buyer-Owned Baseline Validation Sprint

**Machine register:** [`config/institutional_readiness_register_v1.json`](../config/institutional_readiness_register_v1.json)

**Current standards map:** [`docs/INSTITUTIONAL_ASSURANCE_CROSSWALK.md`](INSTITUTIONAL_ASSURANCE_CROSSWALK.md)

The standards map is a first-party informative crosswalk to selected current
NIST, OWASP, and SLSA themes. It is not certification, full conformance, an
external audit, or a penetration test.

## Decision

LumenCore is ready for a **non-confidential buyer fit review and buyer-specific
scoping conversation**. It is not represented as production-certified or ready
to receive regulated or confidential buyer data without additional controls.

**Production decision: `HOLD`.**

The first credible transaction remains a bounded Buyer-Owned Baseline
Validation Sprint: one authorized source, one accepted incumbent baseline, one
locked primary metric and threshold, one replayable evidence package, and one
explicit decision. A neutral, incomplete, or negative result remains a valid
deliverable.

## Control register

| Domain | Current state | What exists | Gate before promotion |
|---|---|---|---|
| Source and reproducibility | Implemented first-party | Public capsule verifier, pinned reviewer runtime, dependency lock, replay instructions | Protocol-matched non-author execution receipt |
| Evidence custody and claim governance | Implemented first-party | Proof Capsule v3, claim-boundary register, fail-closed verifier | Buyer-owned source/baseline/metric binding |
| Security reporting | Documented control | Private advisory route, supported-version boundary, best-effort response process | Buyer-specific severity, notice, and remediation terms |
| Repository supply chain | Partial/scoped implementation | Pinned workflow actions, hash-locked reviewer dependencies, scoped reviewer inventory, deterministic CycloneDX 1.6 coverage for the exact 30-file public release, and a main-only signed-attestation lane | Complete VPS/runtime inventory, vulnerability process, retained successful attestation verification, and any separately assessed SLSA level |
| Public deployment | Prepared, not executed for this commit | Exact-snapshot build, deploy, and live-audit protocol | Successful current-commit live audit receipt |
| Data rights and handling | Buyer-specific gate | Intake, SOW, and handling schedule templates | Executed rights, classification, retention, access, and legal terms |
| Identity, access, and runtime | Prepared, not executed | Default-deny operator boundary and separately gated repair path | Authorized live repair and retained negative-access evidence |
| Incident response and continuity | Documented control | Bounded policy, severity model, deterministic CI tabletop, and read-only live release classification | Separately authorized live restoration exercise and buyer-specific incident, continuity, backup, restoration, and notice terms |
| Legal, certification, and insurance | Open gap | IP and claim boundaries; buyer-specific SOW template | Legal, IP, insurance, regulatory, and certification review |
| Commercial delivery | Prepared, not executed | One offer, fit intake, proposed pricing, and SOW template | Qualified buyer, signed scope, authorized source, and cleared initial payment |
| External validation | Prepared, not executed | CODECHECK handoff, receipt template, and replication docket | Completed qualified non-author execution receipt |
| Privacy and regulated data | Buyer-specific gate | Public-data boundary and classification schedule | Applicable privacy, jurisdiction, export, and regulated-data approval |

## What a buyer can do now

1. Review the public evidence without sharing confidential information.
2. Run the dependency-free Proof Capsule verifier from `QUICKSTART.md`.
3. Inspect the pinned CODECHECK execution target and its first-party receipts.
4. Complete the non-confidential fit intake.
5. Negotiate a buyer-specific SOW, data-handling schedule, baseline, metric,
   threshold, failure rules, acceptance criteria, and decision owner.

This is a review and scoping path. It is not permission to ingest buyer data,
connect to production, place trades, operate critical infrastructure, or make a
regulated decision.

## Production blockers

The public evidence does not currently establish:

- independent validation or field validation;
- a customer, signed paid scope, cleared payment, revenue, or market-tested price;
- SOC 2, ISO 27001, FedRAMP, regulatory, or safety certification;
- a penetration test or independently audited security program;
- an enterprise support, response, recovery, or availability SLA;
- an executed data-processing agreement or legal approval of the offer;
- a complete product, VPS, gateway, container, and deployment-runtime SBOM;
- a tested live incident-response or recovery exercise, business-continuity or disaster-recovery certification, or customer-notification performance;
- privacy or regulated-data authorization; or
- an exact live-domain snapshot matching the checked-out commit.

Until a successful exact-snapshot audit receipt exists for the checked-out
commit, treat `lumen-core.ai` as an unverified convenience projection that may
lag the repository. Do not substitute the live site for commit-bound evidence.

## Evidence interpretation

A green verifier or hash establishes only the named property: file identity,
schema conformance, custody, deterministic replay, or claim-gate behavior. It
does not turn a self-authored claim into an independent finding and does not
establish safety, legal sufficiency, production fitness, performance, or value.

The reviewer-suite inventory and exact-public-release CycloneDX inventory cover
their declared scopes. Neither is described as a complete product, VPS,
gateway, container, or organization-wide SBOM.

## Recommended first engagement boundary

The lowest-risk credible first engagement uses non-confidential or explicitly
authorized data in an isolated replay environment. It excludes production
control, live trading, autonomous actuation, regulated decisions, and any claim
that the result is independently or field validated. Promotion requires the
buyer-defined evidence and authority gates recorded in the signed scope.

## Machine verification

From a clean checkout with Python 3.10 or newer:

```bash
python code/ops/VERIFY_INSTITUTIONAL_READINESS.py --json-out institutional-readiness-receipt.json
python -m unittest discover -s tests -p "test_institutional_readiness.py" -v
```

The receipt hashes every cited evidence file and fails closed if the register
promotes readiness, removes a required negative boundary, cites a missing or
unsafe path, drifts its status totals, or describes the live domain as an exact
current snapshot without the required release evidence.

---

**Review-ready is not production-certified. Evidence before claims.**
