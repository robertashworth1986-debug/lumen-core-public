# External Validation Authority Docket

Generated UTC: `2026-07-16T02:48:38.320276+00:00`

This docket proves only the identity and readiness of a bounded external-validation process. It does not prove Level 4 or Level 5 maturity, independent validation, agency approval, NIST certification, field performance, grid reliability improvement, realized savings, patent validity or scope, production readiness, trading performance, or universal model superiority.

## Decision

- Status: `PROSPECTIVE_COLLECTION_ACTIVE_AWAITING_FIRST_ELIGIBLE_SEAL`
- Requested decision: Accept or decline the independent technical evaluator role for the frozen prospective experiment.
- Fundable scope: A bounded independent evaluation and replication engagement may be funded without asserting that Level 4, Level 5, field performance, or economic savings already exist.
- Docket SHA-256: `825f49fe249534a3f58c2b8f663953c834c944bdbf81e65580569f8e74936929`

## Current Evidence

- Current supported level: `3`
- Level 4 gate passed: `false`
- Level 5 gate passed: `false`
- External validation complete: `false`
- Independent evaluator named: `false`
- Evaluator acceptance template ready: `true`
- Clean-runner bundle verified: `true`
- Predictions sealed: `0`
- Settlements recorded: `0`
- Common settled days: `0`
- Runtime state: `WAITING_FOR_FIRST_ELIGIBLE_FORECAST`

## Evaluator Handoff

1. Rehash every portable input and every archived clean-runner artifact.
2. Review the frozen EIA protocol before inspecting prospective outcomes.
3. Copy the blank evaluator-owned acceptance receipt outside the public repository.
4. Complete identity, authority, conflict, attestation, and signature-artifact fields without operator substitution.
5. Run the fail-closed acceptance validator and preserve only a private or redacted hash receipt by default.
6. Observe prediction seals and settlements through the agreed evaluation window.
7. Inspect all routes, fallbacks, exclusions, negative results, and chain-verification events.
8. Independently reproduce the final metric and statistical decision.
9. Sign only the maturity level supported by the complete evidence record.

## Acceptance Package

- Blank template: `config/external_evaluator_acceptance_template_v1.json`
- Template SHA-256: `abc3b961c7e0d17c2f8da95515a0cc51f0d0466acceb2e412340619f440ddf13`
- Validator: `code/ops/VERIFY_EXTERNAL_EVALUATOR_ACCEPTANCE.py`
- Handoff guide: `docs/EXTERNAL_EVALUATOR_ACCEPTANCE_HANDOFF_2026-07-14.md`
- Template ready: `true`
- External identity verified: `false`
- Level 5 promotion allowed: `false`
- Template check: `python code/ops/VERIFY_EXTERNAL_EVALUATOR_ACCEPTANCE.py --expect-template`

The acceptance package verifies blank-template custody and can validate completed-record structure and supplied artifact hashes. It does not authenticate an evaluator, establish independence or legal authority, interpret a signature, complete result signoff, or authorize Level 5 promotion.

## Maturity Gates

- Level 4: at least `90` common settled days per authority plus the complete confirmatory gate.
- Level 5: at least `180` common settled days per authority, Level 4, independent replication, hash verification, conflict disclosure, and evaluator signoff.

## NIST AI RMF Informative Crosswalk

This is a voluntary, informative mapping. It is not a NIST certification or conformity assessment.

| Function | Implemented control | Remaining gap |
| --- | --- | --- |
| `GOVERN` | Named operator and evaluator roles, HumanUnlock boundaries, immutable protocol identity, claim prohibitions, and explicit decision authority. | No independent evaluator has accepted responsibility or signed the protocol. |
| `MAP` | The intended forecast context, EIA source, eight balancing authorities, incumbent comparators, affected operational boundaries, and prohibited uses are documented. | An external domain owner has not yet reviewed context suitability or downstream impacts. |
| `MEASURE` | Predeclared metrics, baselines, timing controls, holdout gates, uncertainty tests, append-only receipts, clean-runner replay, and negative-result reporting are defined. | Prospective samples and settlements have not reached the confirmatory or durability gates. |
| `MANAGE` | Fail-closed eligibility rules, no-backfill controls, chain-tamper rejection, fallback tracking, stop conditions, and blocked deployment claims are documented. | No external organization has adopted an incident, escalation, or production-use decision process for this experiment. |

## Official References

- [NIST AI Risk Management Framework 1.0](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10): Informative mapping to the voluntary Govern, Map, Measure, and Manage functions. This docket is not a NIST certification or conformity assessment.
- [NIST AI RMF Playbook](https://www.nist.gov/itl/ai-risk-management-framework/nist-ai-rmf-playbook): Informative source for voluntary risk-management actions; the Playbook is not a checklist and this docket does not claim complete implementation.
- [EIA API Technical Documentation](https://www.eia.gov/opendata/documentation.php): Primary documentation for the public API that supplies the measured EIA-930 source observations.
- [EIA Form EIA-930 API Dashboard](https://www.eia.gov/opendata/browser/electricity/rto/region-data): Primary publisher description of hourly demand and demand-forecast data by balancing authority.
