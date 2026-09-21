# LumenCore | Reviewer Start Here

**A clear route from the company thesis to executable evidence.**
Robert Ashworth · Founder / Systems Architect

[Website](https://lumen-core.ai/) ·
[Repository](https://github.com/robertashworth1986-debug/lumen-core-public) ·
[Investor brief](../INVESTOR_BRIEF.md) ·
[Full evidence index](../EVIDENCE_INDEX.md) ·
[Portfolio and maturity map](PLATFORM_PROOF_AND_COMMERCIALIZATION_MAP.md)

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
