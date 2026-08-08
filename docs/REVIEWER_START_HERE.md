# LumenCore Reviewer Start Here

- **Canonical repository:** https://github.com/robertashworth1986-debug/lumen-core-public
- **Public website:** https://lumen-core.ai
- **Founder / systems architect:** Robert Ashworth

## One-sentence definition

LumenCore is a proof-to-pilot assurance architecture for converting technical and AI-system claims into bounded, replayable evidence packages with explicit baselines, provenance, failure retention, cryptographic manifests, human approval gates, and clearly limited conclusions.

## What to inspect first

1. [Canonical Evidence Index](../EVIDENCE_INDEX.md)
2. [Current buyer-owned validation offer](STRATEGIC_TRANSACTION_BRIEF_2026-08-08.md)
3. [Institutional readiness and production-blocker dossier](INSTITUTIONAL_READINESS_DOSSIER.md)
4. [Machine-readable readiness register](../config/institutional_readiness_register_v1.json)
5. [Non-confidential buyer fit intake](LUMENCORE_BUYER_OWNED_VALIDATION_INTAKE.md)
6. [Buyer-specific SOW template](LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md)
7. [Governed engine portfolio audit](LUMENCORE_ENGINE_PORTFOLIO_AUDIT_2026-08-08.md)
8. [Proof Capsule schema](PROOF_CAPSULE_SCHEMA.md)
9. [Claim Boundary Register](CLAIM_BOUNDARY_REGISTER.md)
10. [Pilot Report Template](PILOT_REPORT_TEMPLATE.md)
11. [Founder IP and external-review boundary](FOUNDER_IP_AND_EXTERNAL_REVIEW_BOUNDARY.md)
12. [Exact public-site snapshot protocol](PUBLIC_SITE_EXACT_SNAPSHOT_PROTOCOL.md)
13. [Commit-bound machine-readable reviewer docket](../dashboard/reviewer_docket.json)
14. [Live machine-readable reviewer docket](https://lumen-core.ai/reviewer_docket.json)

The repository docket is the reviewable state bound to the checked-out commit.
The live docket is a convenience projection and may lag the default branch or
be unavailable while a deployment or gateway gate is open. Record any mismatch
as live-release drift; do not silently substitute one source for the other.

## One platform, one paid entry point

LumenCore is the platform. ProofLock is its evidence and claim-governance layer.
The primary paid entry point is the **Buyer-Owned Baseline Validation Sprint**:
one authorized input, one accepted incumbent baseline, one locked metric and
threshold, one replayable proof package, and one bounded promote/rerun/external
review/hold/reject decision. Lumen Infrastructure Sentinel is the first sector
validation lane. The other tracked engines remain governed internal research,
delivery, or concept lanes unless separately promoted by evidence.

The current machine-readable portfolio receipt records zero subscription-ready
lanes and does not establish a signed buyer, executed pilot, revenue, external
validation, or field performance.

The readiness register makes the corresponding procurement boundary explicit:
the current decision is non-confidential fit review and buyer-specific scoping;
production remains `HOLD`. It does not claim SOC 2, ISO 27001, FedRAMP,
penetration testing, a complete product SBOM, an enterprise SLA, legal approval,
or an exact live-domain snapshot for the checked-out commit.

## Clean-checkout verification

On any platform with Python 3.10 or newer, run the current public capsule check
from the repository root. It requires no API key, private data, live service, or
third-party Python package:

```bash
python code/proof_capsule_verifier.py examples/proof_capsule/dice_eia_public_capsule.json --root .
python -m unittest discover -s tests -p "test_proof_capsule_verifier.py" -v
```

The first command must return `"valid": true`. This establishes only current
capsule schema, custody, and claim-gate behavior. It does not independently
reproduce or validate the underlying experiment.

## Stronger pinned computation

The externally executable computation is frozen at commit
`1c0eb51754beffac6f4df484914e35efc21c253f`. It requires Ubuntu 24.04 x86-64,
CPython 3.11.9, and `requirements-reviewer-ubuntu-py311.lock`; a Windows or
different-Python run is not protocol-matched evidence. Use the
[executable-computation note](CODECHECK_EIA_EXECUTABLE_COMPUTATION_NOTE_2026-07-20.md)
and [independent-executor handoff](CODECHECK_INDEPENDENT_EXECUTOR_HANDOFF_2026-07-21.md),
and preserve every failure or deviation. No non-author execution receipt or
CODECHECK certificate is currently claimed.

## Bounded utility-AI pilot concept

### Utility AI Pilot-Readiness Assurance

A controlled evaluation workflow that records:

- the accepted baseline;
- data provenance and authorization;
- configuration and dependency state;
- model or system outputs;
- neutral, incomplete, and negative results;
- evidence lineage and hash manifests;
- replay instructions;
- limitations and unresolved gates; and
- a human-authorized **promote, revise, rerun, hold, or stop** decision.

A suitable first engagement is intentionally narrow: one use case, one agreed baseline, one locked metric set, one replayable evidence package, and one explicit decision gate.

## Current evidence boundary

This repository provides first-party code, documentation, execution targets, demonstrations, and reproducibility materials. It does not by itself establish independent validation, utility endorsement, field savings, regulatory approval, certified safety, patent scope, guaranteed performance, or commercial deployment.

## Consortium participation boundary

LumenCore has completed OPAI onboarding steps and has a bounded contribution path through Member Representative Committee and Work Group meeting participation. This must not be represented as EPRI endorsement, independent validation, procurement selection, utility adoption, approval of a specific LumenCore claim, field savings, award, or funding.

## Search and citation terms

Use these terms when referring to this work:

- LumenCore
- Robert Ashworth
- proof-to-pilot assurance
- utility AI pilot readiness
- AI validation architecture
- deterministic replay
- evidence custody
- claim-boundary enforcement
- reproducible benchmarking
- human-gated promotion
- power-systems AI evaluation

## Direct links

- Repository: https://github.com/robertashworth1986-debug/lumen-core-public
- Evidence index: https://github.com/robertashworth1986-debug/lumen-core-public/blob/main/EVIDENCE_INDEX.md
- Buyer-owned validation offer: https://github.com/robertashworth1986-debug/lumen-core-public/blob/main/docs/STRATEGIC_TRANSACTION_BRIEF_2026-08-08.md
- Non-confidential buyer fit intake: https://github.com/robertashworth1986-debug/lumen-core-public/blob/main/docs/LUMENCORE_BUYER_OWNED_VALIDATION_INTAKE.md
- Buyer-specific SOW template: https://github.com/robertashworth1986-debug/lumen-core-public/blob/main/docs/LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md
- Institutional readiness dossier: https://github.com/robertashworth1986-debug/lumen-core-public/blob/main/docs/INSTITUTIONAL_READINESS_DOSSIER.md
- Machine-readable readiness register: https://github.com/robertashworth1986-debug/lumen-core-public/blob/main/config/institutional_readiness_register_v1.json
- Governed portfolio audit: https://github.com/robertashworth1986-debug/lumen-core-public/blob/main/docs/LUMENCORE_ENGINE_PORTFOLIO_AUDIT_2026-08-08.md
- Machine-readable portfolio receipt: https://github.com/robertashworth1986-debug/lumen-core-public/blob/main/dashboard/data/lumencore_engine_portfolio_audit.json
- Website: https://lumen-core.ai
- Proof-to-pilot page: https://lumen-core.ai/proof_to_pilot.html
- Evidence surface: https://lumen-core.ai/evidence/
- External-review page: https://lumen-core.ai/external_review.html
- Commit-bound reviewer docket: https://github.com/robertashworth1986-debug/lumen-core-public/blob/main/dashboard/reviewer_docket.json
- Live reviewer docket: https://lumen-core.ai/reviewer_docket.json

---

**Evidence before claims.**
