# LumenCore Institutional Readiness Dossier

**Register date:** 2026-08-28

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

The current canonical map contains **19 named evidence-ranked systems** or
explicit unverified states while retaining 15 registered implementation lanes
as artifact-coverage counts. This is one LumenCore platform: ProofLock is the
evidence and claim-governance layer, Frozen Delta is the method inside the sole
primary offer, and the remaining systems are ranked research or implementation
lanes rather than separately validated products.

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
| Evidence-ranked ecosystem and claim map | Implemented first-party | One platform/one offer hierarchy, 19 named systems or unverified states, 15 implementation lanes, adverse findings, next gates, and reviewer/resume alignment | Advance only the buyer-relevant lane after its named source, baseline, metric, result, and outside-review gates |
| Security reporting | Documented control | Private advisory route, supported-version boundary, best-effort response process | Buyer-specific severity, notice, and remediation terms |
| Repository supply chain | Partial/scoped implementation | Pinned workflow actions, hash-locked reviewer dependencies, deterministic CycloneDX 1.6 coverage for the exact 43-file named public release, constrained GitHub OIDC/Sigstore provenance, and a current-tracked-text URL-query credential-literal gate | Provider credential rotation and public-history review, complete VPS/runtime inventory, vulnerability process, periodic trusted-root re-verification, and any separately assessed SLSA level |
| Public deployment | Implemented first-party for named release `1ce7c359`; prior `e513f65a` receipt retained | Human-gated exact deployment, rollback capture, 43-of-43 live-byte verification, separate read-only post-deployment audit, and an append-only commit-bound receipt history; security-header evidence is a separate bounded control | Repeat the exact gate for every later release; separately assess gateway and runtime layers |
| Candidate public origin and migration | Prepared, not executed | Provider-neutral static-only Ubuntu bootstrap, manual commit-pinned staging workflow, rollback capture, exact-byte/SNI/certificate verifier, and private-listener negative checks | Exact provider plan, spend ceiling, SSH key, firewall, protected environment, TLS method, candidate staging approval, then a separate record-by-record DNS cutover |
| Data rights and handling | Buyer-specific gate | Intake, SOW, and handling schedule templates | Executed rights, classification, retention, access, and legal terms |
| Identity, access, and runtime | Prepared, not executed | Default-deny operator boundary and separately gated repair path | Authorized live repair and retained negative-access evidence |
| Trading execution and custody safety | Prepared, not executed | Fail-closed private-endpoint allowlist, validate-only order path, receipt-limited manual liquidation, blocked automatic cancellation/payout/withdrawal facades, exact Alpaca paper origin, and a HumanUnlock-gated paper-ledger repair | Execute the approved repair, verify deployed ownership and venue permissions, begin a fresh observation-only SLO epoch, and obtain independent review before promotion |
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

No new live-capital order authority is granted by the trading controls or this
dossier. The Monday-safe trading demonstration remains observation-only and
paper-only until the deployed service, venue permissions, long-run SLO, and
independent-review gates are satisfied.

The candidate-origin lane does not purchase a VPS, issue a certificate, or change DNS.
Those actions remain separate exact approvals, and the current origin remains
the rollback target until an approved candidate passes the complete pre-DNS
audit and a later cutover stabilization window.

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
- live-capital production readiness, profitable trading edge, restricted venue-side permissions, deployed-code parity, or a healthy fresh paper-runtime SLO epoch;
- a purchased and fully verified candidate origin, canonical certificate on that candidate, approved DNS cutover, completed stabilization window, or current-origin decommissioning;
- rotation of the historically exposed provider credential or verified remediation of public Git history; or
- an exact live-domain snapshot for any later checked-out commit without its own
  successful release receipt.

Named release `1ce7c35975a4011fa844e8b39ccbc950c8c0f398` has a successful
exact-snapshot receipt, and the earlier `e513f65a` receipt remains retained. For
any later checked-out commit without its own receipt, treat `lumen-core.ai` as
an unverified convenience projection that may lag the repository. Do not
substitute the live site for commit-bound evidence.

## Evidence interpretation

A green verifier or hash establishes only the named property: file identity,
schema conformance, custody, deterministic replay, or claim-gate behavior. It
does not turn a self-authored claim into an independent finding and does not
establish safety, legal sufficiency, production fitness, performance, or value.

The reviewer-suite inventory and exact-public-release CycloneDX inventory cover
their declared scopes. Neither is described as a complete product, VPS,
gateway, container, or organization-wide SBOM.

The current tracked-text credential gate establishes only that its bounded scan
found no detected non-placeholder credential literal in a URL query parameter.
It does not establish provider rotation, clean public history, absence from
binary or untracked files, or whole-repository secret absence.

The trading audit establishes repository-source controls only. Historical
legacy files, deployed copies, exchange account permissions, runtime ownership,
availability history, strategy quality, slippage, and profitability require
separate verification. A green paper heartbeat is not a production certificate,
and a failed predecessor SLO epoch must remain retained when a new epoch begins.

The current deployment receipt proves only that the 43-file archive for named
commit `1ce7c359` was bound to the recorded supply-chain, deployment,
rollback-capture, exact-byte, and read-only audit results. The append-only
verifier also reconstructs the earlier `e513f65a` subject. Its local checks are
first-party and do not themselves re-run remote signatures or live HTTP checks.
The receipt history does not establish a SLSA level, vulnerability status,
complete-product provenance, external validation, or broader platform
production authorization.

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
snapshot beyond the named release evidence.

---

**Review-ready is not production-certified. Evidence before claims.**
