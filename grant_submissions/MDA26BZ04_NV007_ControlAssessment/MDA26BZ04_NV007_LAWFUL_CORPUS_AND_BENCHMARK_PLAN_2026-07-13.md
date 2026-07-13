# MDA26BZ04-NV007 Lawful Corpus and Benchmark Plan

Prepared: 2026-07-13

Status: `PLAN_READY_SOURCE_RIGHTS_AND_SME_GATES_OPEN`

## Objective

Build a lawful, reviewable Phase I corpus that can test parsing, normalization, control correlation, confidence, abstention, and assessor correction without claiming access to MDA systems or sensitive operational findings.

## Source Tiers

### Tier 1 - Public Authoritative References

Candidate reference families include the topic-cited NIST SP 800-53 Rev. 5 and NIST SP 800-171 Rev. 2, public CVE/CPE records, and publicly distributable STIG or SCAP reference content. Each source must be recorded with publisher, version, retrieval time, URL or identifier, terms, content hash, and update policy.

Public availability does not automatically grant every redistribution or derivative-use right. The source manifest must record the applicable terms before any content is packaged into a proposal or replay bundle.

### Tier 2 - Synthetic Conformance Fixtures

Create non-sensitive scanner-like fixtures that exercise:

- valid and malformed records
- missing identifiers and conflicting identifiers
- one-to-one, one-to-many, many-to-one, and no-supported mapping cases
- reference-version changes
- duplicate and stale findings
- disconnected synchronization conflicts
- unsupported or low-confidence findings that require abstention

Synthetic fixtures support parser and workflow conformance only. They cannot establish operational accuracy on real ACAS or SCAP outputs.

### Tier 3 - Authorized Representative Artifacts

Obtain representative de-identified ACAS/Nessus and SCAP artifacts only through a written data-rights and handling agreement with a qualified provider. Record permitted use, retention, redistribution, security boundary, de-identification method, and destruction or return obligations.

No representative-data claim is allowed until this gate is satisfied.

## Split and Labeling Plan

- Development: visible to developers for parser and candidate design.
- Validation: used for frozen model/rule selection and threshold selection.
- Blind holdout: withheld from developers until protocol, candidates, baselines, and failure rules are committed.
- Independent replay: held or rerun by a cyber/RMF reviewer who did not tune the candidate.

Stratify where feasible by source tool, finding class, control family, common versus rare mapping, and supported versus abstention-eligible case. Preserve corpus IDs and hashes without publishing sensitive raw content.

## Reference Labels

The reference mapping is not assumed to be perfectly objective. Build it through:

1. versioned authoritative references;
2. a documented mapping rule;
3. primary expert review;
4. second review on a predeclared subset;
5. disagreement and ambiguity codes; and
6. adjudication records that preserve both original judgments.

Report inter-rater agreement and label ambiguity. Do not score ambiguous cases as clean model failures without a declared rule.

## Baselines and Candidate

Required baselines:

- versioned static crosswalk or rule baseline
- lexical retrieval baseline
- human expert mapping on the blind subset

Candidate:

- correlation route with evidence citations, confidence, and explicit abstention

Primary metrics:

- exact control-ID precision, recall, and F1
- control-family precision, recall, and F1
- coverage and abstention rate
- unsupported-mapping rate
- calibration error
- provenance completeness

Workflow metrics:

- analyst minutes per finding
- correction rate and correction type
- inter-rater agreement
- percentage of outputs with complete source, reference, rule/model, and reviewer lineage

## Promotion Gates

No numeric improvement is preclaimed. A Phase I feasibility conclusion requires:

- parsers pass frozen schema and malformed-input tests;
- every scored result is traceable to its source and reference versions;
- the blind holdout is untouched before protocol lock;
- all failures and abstentions are reported;
- the candidate is compared with every predeclared baseline;
- a qualified cyber/RMF reviewer signs the labeling and replay limitations; and
- deployment-profile conformance uses identical frozen vectors and output hashes.

## Open Gates

- source terms and redistribution review
- representative artifact provider
- cyber/RMF reviewer
- independent replay owner
- data-handling architecture
- final corpus size and class balance
- source-update and reference-drift policy

Until these gates close, the corpus plan is a proposed Phase I method, not a completed cyber validation asset.
