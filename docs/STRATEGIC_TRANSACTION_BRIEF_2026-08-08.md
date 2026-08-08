# LumenCore Buyer-Owned Baseline Validation Sprint

**Status:** exploratory founder-authorized inquiry. No buyer commitment, paid
scope, executed pilot, revenue, external validation, valuation, license, sale,
or partnership is established by this document.

## The customer problem

Technical buyers often cannot tell whether an AI, analytics, or engineering
claim deserves pilot capital. Results may lack an accepted baseline, fixed
success criteria, replayable inputs, negative-result reporting, or an
independently inspectable custody trail.

## The primary offer

LumenCore offers a bounded, buyer-owned baseline validation sprint. The buyer
provides an authorized dataset or replay window, accepts the incumbent
baseline, and locks the primary metric and threshold before execution.

LumenCore returns:

- a frozen run contract;
- candidate and baseline execution receipts;
- a negative-result and failure register;
- a SHA-256 input/output manifest;
- an offline verifier; and
- a buyer-readable Proof Capsule.

The output supports one of five buyer decisions: **promote, rerun, external
review, hold, or reject**. The sprint does not guarantee an improvement or
authorize production use. Scope, schedule, data rights, acceptance criteria,
and price require a signed paid-pilot statement of work.

## Public diligence path

Reviewers should begin with:

1. [`EVIDENCE_INDEX.md`](../EVIDENCE_INDEX.md)
2. [`config/evidence_graph_v1.json`](../config/evidence_graph_v1.json)
3. [`code/ops/VERIFY_EVIDENCE_GRAPH.py`](../code/ops/VERIFY_EVIDENCE_GRAPH.py)
4. [ProofLock Console](https://lumen-core.ai/build_week/prooflock_console/)
5. [`QUICKSTART.md`](../QUICKSTART.md)

The sealed machine-readable offer is
[`config/strategic_transaction_packet_v2.json`](../config/strategic_transaction_packet_v2.json).
Its fail-closed verifier is
[`code/ops/VERIFY_STRATEGIC_TRANSACTION_PACKET.py`](../code/ops/VERIFY_STRATEGIC_TRANSACTION_PACKET.py).

## Scope-to-signature path

A qualified buyer can begin without transferring confidential data:

1. complete the
   [non-confidential fit intake](LUMENCORE_BUYER_OWNED_VALIDATION_INTAKE.md);
2. inspect the
   [canonical bounded offer](LUMENCORE_BOUNDED_VALIDATION_SPRINT_OFFER.md);
3. convert only a `scope_candidate` into the
   [buyer-specific SOW template](LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md);
4. complete appropriate legal, security, data-rights, procurement, and pricing
   review; and
5. begin work only under an accepted written scope or controlling purchase
   instrument and after any required initial payment is confirmed.

The fit intake is not a contract, invoice, commitment, or authorization to
transfer data. Unknown facts remain `UNKNOWN`; they are not filled by inference.

The canonical evidence graph currently classifies PR 34 as a merged
capability, PR 36 and the ProofLock Console as deployed demonstrations, and PR
55 as a first-party reproduced record. PR 49 and PR 64 are retained only as
historical, superseded ancestors. These states must not be promoted into claims
of customer adoption, independent validation, revenue, or field performance.

## Secondary strategic options

Only after qualified diligence, a counterparty may discuss a defined license,
acquihire-plus-license, or acquisition. These are secondary options, not the
primary market entry. No ownership, source code, confidential material, patent
right, credential, or data transfers before signed definitive agreements and
verified consideration.

## Diligence boundary

A serious engagement requires founder authority and chain-of-title review,
third-party license and data-rights review, security and credential separation,
independent execution of the agreed package, buyer-specific integration
planning, and signed definitive documents where applicable.

Private financial records, personal information, unpublished enabling detail,
patent-sensitive material, credentials, private infrastructure, private
datasets, regulated information, and buyer-specific pricing stay private until
the appropriate qualified process exists.

Public review and contact entrypoint:
<https://lumen-core.ai/proof_to_pilot.html>
