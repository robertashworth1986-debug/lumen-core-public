![LumenCore Banner](https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,50:00ffe7,100:7928ca&height=220&section=header&text=LumenCore%E2%84%A2&fontSize=72&fontColor=ffffff&fontAlignY=38&desc=Proof-to-Pilot%20AI%20%C2%B7%20Replay%20Validation%20%C2%B7%20Founder-Owned%20Architecture&descSize=18&descAlignY=62&animation=fadeIn)

# LumenCore™ — Proof-to-Pilot Assurance Architecture

**Robert Ashworth** | Founder / Systems Architect | LumenCore™

LumenCore turns complex-system claims into bounded, inspectable evidence packages: authorized source, accepted baseline, locked metric, controlled replay or evaluation, hash manifest, result, limitations, and next-pilot decision.

The public repository is a review surface. It is not a certification, an audited revenue report, a field-savings claim, or an outside grant of rights to founder-owned intellectual property.

## Commercial entry offer

The sole primary paid entry point is the **Buyer-Owned Baseline Validation
Sprint**: one authorized source, one accepted incumbent baseline, one primary
metric locked before scoring, and one bounded decision—promote, rerun, external
review, hold, or reject.

The founder-approved launch tiers are proposed at **$7,500**, **$15,000**, and
**from $25,000**, with a maximum 30-calendar-day schedule and a commercial
default of 50% at signed scope and 50% at delivery. These prices are an untested
offer hypothesis, not booked revenue, buyer acceptance, or company valuation.
Work begins only after written agreement on data rights, scope, acceptance,
payment, IP, and decision authority. A neutral or failed result remains a valid
deliverable.

## Start here

**[Open the Canonical Evidence Index](EVIDENCE_INDEX.md)**

**[Open the Reviewer Start Here page](docs/REVIEWER_START_HERE.md)**

**[Open the Institutional Readiness Dossier](docs/INSTITUTIONAL_READINESS_DOSSIER.md)**

**[Open the Institutional Assurance Crosswalk](docs/INSTITUTIONAL_ASSURANCE_CROSSWALK.md)**

**[Open the Incident Response and Continuity Plan](docs/INCIDENT_RESPONSE_AND_CONTINUITY_PLAN.md)**

**[Open the Public Site Supply-Chain Assurance guide](docs/PUBLIC_SITE_SUPPLY_CHAIN_ASSURANCE.md)**

**[Open the retained Signed-Attestation Receipt](docs/PUBLIC_SITE_SIGNED_ATTESTATION_RECEIPT_2026-08-08.md)**

**[Open the Repository Security Assurance guide](docs/REPOSITORY_SECURITY_ASSURANCE.md)**

The index is the canonical evidence map. The reviewer page gives the shortest human path. The index identifies:

- what is merged into the default branch;
- what is a deployed demonstration;
- which benchmark is first-party reproducible;
- which package is prepared for independent execution;
- which pull requests are canonical, stacked, or superseded;
- which external, field, and commercial gates remain open.

A reviewer should not infer current truth by reading every historical or draft pull request independently.

The readiness dossier is the procurement and assurance control map. It says
which controls are implemented first-party, which are only documented or
prepared, which require buyer-specific terms, and which remain open production
blockers. Its machine register and verifier keep the current decision bounded
to non-confidential fit review and buyer-specific scoping; production remains
on `HOLD`.

The assurance crosswalk maps named first-party evidence to current NIST AI
RMF, NIST GenAI Profile, NIST CSF, NIST SSDF, OWASP ASVS, OWASP LLMSVS, and
SLSA reference themes. It is an informative reviewer aid—not certification,
full conformance, an external audit, or a penetration test—and it exposes the
remaining buyer-specific and external-assurance gates.

The incident plan converts exact-snapshot drift into a bounded machine receipt
with severity, affected surfaces, containment, recovery, and explicit human
authorization boundaries. It is a documented first-party control with CI
exercises—not proof of a completed live restoration or an enterprise SLA.

The public-release supply-chain lane creates deterministic CycloneDX 1.6
coverage for all 30 allowlisted site files. Pull requests produce unsigned
verification artifacts; successful `main` builds separately create and verify
GitHub OIDC/Sigstore provenance and SBOM attestations for the exact archive.
The first retained successful set is bound to commit
`5fff567c11bee65b5b1de5415d8b8935cd2dfab0` and can be reconstructed and
checked with the repository verifier. This is not a whole-product or VPS SBOM,
a SLSA level, or deployment proof; the live domain remains on `HOLD`.

Repository source and declared dependency changes are separately covered by
pinned CodeQL, pull-request dependency review, and weekly update proposals.
These are first-party controls, not a vulnerability-free claim, penetration
test, security certification, runtime scan, or deployment authorization.

## Five-minute technical path

1. Open [Reviewer Start Here](docs/REVIEWER_START_HERE.md) and the
   [Canonical Evidence Index](EVIDENCE_INDEX.md).
2. Run the dependency-free current-checkout verifier in [QUICKSTART.md](QUICKSTART.md).
3. Inspect the current [Proof Capsule v3 standard](https://github.com/robertashworth1986-debug/lumen-core-public/pull/101)
   and [ProofLock bounded release and buyer path](https://github.com/robertashworth1986-debug/lumen-core-public/pull/98).
4. For the stronger pinned computation, follow the
   [CODECHECK executable-computation note](docs/CODECHECK_EIA_EXECUTABLE_COMPUTATION_NOTE_2026-07-20.md)
   and [independent-executor handoff](docs/CODECHECK_INDEPENDENT_EXECUTOR_HANDOFF_2026-07-21.md).
5. If the evidence is relevant to a buyer decision, review the current
   [bounded validation offer](docs/LUMENCORE_BOUNDED_VALIDATION_SPRINT_OFFER.md),
   [buyer-owned intake](docs/LUMENCORE_BUYER_OWNED_VALIDATION_INTAKE.md), and
   [statement-of-work template](docs/LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md).

These are two different verification levels. The quick verifier checks the
current public capsule's schema, file custody, and claim gates on Python 3.10+
without third-party packages. The CODECHECK target recreates a frozen
computation at immutable commit `1c0eb51754beffac6f4df484914e35efc21c253f`
under Ubuntu 24.04 x86-64, CPython 3.11.9, and the hash-locked dependency set.
Neither path by itself establishes scientific validity, field performance, or
independent validation.

### Independent execution target

The root `codecheck.yml` defines one bounded external execution target: three
reproducibility suites, 31 assertions, and six declared outputs. The reviewed
source and five-page preprint are frozen at commit
`1c0eb51754beffac6f4df484914e35efc21c253f`.

Author-operated CI and container receipts are first-party executability
evidence only. Independent execution, a CODECHECK certificate, scientific or
field validation, agency approval, savings, trading performance, patent
conclusions, and company valuation remain unverified.

### Frozen CODECHECK package

The external execution target is the immutable source commit above, not the
moving branch head. Its root `README.md`, `codecheck.yml`, and `LICENSE` form
the author package required by the CODECHECK community workflow. The frozen
README contains the exact dependency-lock and capsule commands; the six files
declared in `codecheck.yml` are the outputs a reviewer must recreate.

This branch separately verifies that the 30-file computational core remains
byte-identical to that target. Reviewer assignment, execution, reporting, and
certificate metadata are intentionally absent until supplied by CODECHECK.

## Core method

```text
Authorize source
      ↓
Lock baseline, metric, threshold, and failure rules
      ↓
Run replay, simulation, benchmark, or bounded evaluation
      ↓
Preserve positive, neutral, incomplete, and negative results
      ↓
Generate hashes, manifests, receipts, and limitations
      ↓
Recommend promote, rerun, external review, hold, or reject
```

LumenCore emphasizes fail-closed decisions: missing rights, ambiguous provenance, invalid manifests, incomplete gates, or absent human authority must not silently become a promoted claim.

## Current strongest public capabilities

| Capability | Current bounded state |
|---|---|
| Proof Capsule verifier | Version 3 current standard merged; validates strict evidence structure, custody, manifests, resource limits, external-report binding, and claim boundaries. |
| ProofLock Console | Deployed bounded demonstration; verifies receipt integrity and refuses unauthorized promotion. |
| EIA benchmark package | First-party reproducible for the named pinned package; prepared for non-author execution. |
| External replication docket | Draft protocol for preregistration, evaluator independence, frozen inputs, deviations, and negative results. |
| Exact public-release supply chain | Deterministic 30-file CycloneDX 1.6 inventory plus a main-only GitHub OIDC/Sigstore provenance and SBOM-attestation lane; no whole-product SBOM, SLSA level, or deployment-parity claim. |
| Buyer-Owned Baseline Validation Sprint | Sole primary paid offer; proposed tiers are $7,500, $15,000, and from $25,000. Pricing is not buyer-tested, and no signed scope, cleared payment, or delivery is claimed. ProofLock supplies the evidence and custody layer. |

## Evidence-state definitions

- **Measured:** rows, files, commits, outputs, or runs exist.
- **Replay:** a controlled replay output exists; this is not field validation.
- **Synthetic:** generated or simulated benchmark evidence.
- **Modeled:** simulation or internal modeling output.
- **Estimated:** economic translation or opportunity framing.
- **First-party reproduced:** the author/operator reproduced the named package from pinned source and environment.
- **Externally executable:** a bounded package exists for a non-author evaluator.
- **Externally validated:** a qualified outside party verified the agreed result under controlled conditions.
- **Field validated:** a data owner or operational partner validated the result under agreed field conditions.

## What LumenCore does not currently claim

LumenCore does not claim, without separately linked evidence:

- audited or GAAP-recognized revenue;
- signed enterprise deployment;
- field-validated savings or guaranteed ROI;
- certified aircraft, suit, medical, weapons, or autonomous physical-control capability;
- agency endorsement or award likelihood;
- independent validation merely because internal CI is green;
- universal superiority of a model, algorithm, geometry, or routing method;
- experimental, field, safety, certification, patent-scope, performance, or deployment proof merely because a concept illustration or design render exists.

## Proof Capsule model

```json
{
  "schema_version": "3.0",
  "source": "named source, rights status, and bounded window",
  "baseline": "named comparator selected before scoring",
  "locked_metric": "metric definition locked before the run",
  "run": "compatible run type, UTC timestamp, commit, dependencies, and window",
  "manifest": "role-separated artifact hashes using proof-capsule-manifest-v3",
  "external_validation": "explicit status plus manifest-bound report provenance",
  "result": "bounded summary with negative results and failure notes",
  "claim_boundary": "what this proves and does not prove",
  "pilot_decision": "review, rerun, external validation, or pilot scope"
}
```

The verifier binds the exact capsule bytes and canonical JSON to its receipt, rejects
unknown fields and artifact aliases, and distinguishes manifest-bound external-report
custody from validator identity, independence, and conclusions that still require human
review. Action-time HumanUnlock remains outside machine verification.

## Public review surfaces

- Website: <https://lumen-core.ai/>
- Primary offer — Buyer-Owned Baseline Validation Sprint: <https://lumen-core.ai/proof_to_pilot.html>
- Secondary funding-workflow variant (not the primary offer): <https://lumen-core.ai/opportunity_sprint.html>
- Evidence surface: <https://lumen-core.ai/evidence/>
- ProofLock Console: <https://lumen-core.ai/build_week/prooflock_console/>
- Proof Capsule schema: [docs/PROOF_CAPSULE_SCHEMA.md](docs/PROOF_CAPSULE_SCHEMA.md)
- Claim boundaries: [docs/CLAIM_BOUNDARY_REGISTER.md](docs/CLAIM_BOUNDARY_REGISTER.md)
- Conceptual R&D and visual asset boundary: [docs/CONCEPTUAL_RND_AND_VISUAL_ASSET_BOUNDARY.md](docs/CONCEPTUAL_RND_AND_VISUAL_ASSET_BOUNDARY.md)
- Private asset quarantine and redaction checklist: [docs/PRIVATE_ASSET_QUARANTINE_AND_REDACTION_CHECKLIST.md](docs/PRIVATE_ASSET_QUARANTINE_AND_REDACTION_CHECKLIST.md)
- Founder/IP boundary: [docs/FOUNDER_IP_AND_EXTERNAL_REVIEW_BOUNDARY.md](docs/FOUNDER_IP_AND_EXTERNAL_REVIEW_BOUNDARY.md)
- Pilot report template: [docs/PILOT_REPORT_TEMPLATE.md](docs/PILOT_REPORT_TEMPLATE.md)
- Primary bounded validation offer: [docs/LUMENCORE_BOUNDED_VALIDATION_SPRINT_OFFER.md](docs/LUMENCORE_BOUNDED_VALIDATION_SPRINT_OFFER.md)
- Buyer-owned validation intake: [docs/LUMENCORE_BUYER_OWNED_VALIDATION_INTAKE.md](docs/LUMENCORE_BUYER_OWNED_VALIDATION_INTAKE.md)
- Statement-of-work template: [docs/LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md](docs/LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md)
- Secondary funding-workflow data boundary: [docs/PROOFLOCK_OPPORTUNITY_SPRINT_DATA_HANDLING_SCHEDULE.md](docs/PROOFLOCK_OPPORTUNITY_SPRINT_DATA_HANDLING_SCHEDULE.md)
- Exact public-release SBOM and signed-attestation boundary: [docs/PUBLIC_SITE_SUPPLY_CHAIN_ASSURANCE.md](docs/PUBLIC_SITE_SUPPLY_CHAIN_ASSURANCE.md)
- Retained exact-release attestation receipt: [docs/PUBLIC_SITE_SIGNED_ATTESTATION_RECEIPT_2026-08-08.md](docs/PUBLIC_SITE_SIGNED_ATTESTATION_RECEIPT_2026-08-08.md)

## Intellectual-property boundary

LumenCore, ProofLock, FlowForm, EchoLock, EtherFrame, AetherReach, LumenShell, LumaTrader, LumaScout, LumaJet, LumaSuit, LumaSkin, EchoForm, and related founder-originated architecture and lexicon remain founder-controlled unless a signed written agreement states otherwise.

Review, discussion, repository access, comments, introductions, or proposed services do not transfer rights to pre-existing code, architecture, names, constants, proof materials, or patentable structure.

## Contact

**Robert Ashworth** — Founder / Systems Architect, LumenCore

- Site: <https://lumen-core.ai>
- GitHub: <https://github.com/robertashworth1986-debug/lumen-core-public>

---

*Founder-owned. Evidence before claims. Bounded light speed.*

![Footer](https://capsule-render.vercel.app/api?type=waving&color=0:7928ca,100:00ffe7&height=120&section=footer&text=lumen-core.ai%20%C2%B7%20Evidence%20before%20claims&fontSize=16&fontColor=ffffff&fontAlignY=65)
