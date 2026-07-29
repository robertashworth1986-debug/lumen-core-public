# ERDC SDC Phase II ROM Approval Workflow - 2026-07-29

This workflow converts the remaining ERDC estimated-price blocker into a private, auditable control. Labor rates, costs, profit, risk reserve, the candidate price, private-input fingerprints, and private row counts remain outside public artifacts.

## Scope Lock

- Opportunity: `W912HZ26SC005`
- Pricing scope: Phase II prototype development only
- Internal planning assumption: 16 weeks; this is not an ERDC-mandated period
- Phase III demonstration costs: excluded
- Phase IV implementation and scaling costs: excluded
- Resultant-award posture: firm-fixed price if an award is later pursued
- Current lane: RFI/CSO market research; funding is not currently available
- Original CSO PDF deadline text: `1700 EST, 07 AUG 2026`
- Current live-page deadline text: `4:00 PM CT on August 7, 2026`
- Operational stop rule: complete before `4:00 PM CT on August 7, 2026`

## Private Inputs

1. Direct labor role, hours, rate, and supportable rate basis.
2. Fringe rate and direct-labor base.
3. Indirect rate and direct-labor-plus-fringe base.
4. Itemized cloud, data, storage, software, equipment, and authorized-travel costs.
5. Firm-fixed-price risk reserve rate.
6. Profit rate.
7. Rounding increment and one candidate estimated price.
8. Cost-basis, scope-exclusion, subcontractor, and founder-approval attestations.

## Public Safety Boundary

The builder reads private values only when explicitly invoked with a bounded git-ignored input path. Public JSON and Markdown expose only Boolean readiness states, current-source custody, unresolved gate names, and the public gate hash. They do not expose private amounts, rates, row counts, or a private-input fingerprint.

## Commands

```powershell
python code\ops\BUILD_ERDC_SDC_PHASE2_ROM_GATE.py --check-target
python code\ops\BUILD_ERDC_SDC_PHASE2_ROM_GATE.py
python code\ops\BUILD_ERDC_SDC_PHASE2_ROM_GATE.py --private-input grant_submissions\funding_sprint_20260709\private\W912HZ26SC005\ERDC_SDC_PHASE2_ROM.private.json
```

## Final Gates

- Support every labor and indirect-rate input.
- Itemize every other direct cost.
- Exclude uncommitted subcontractor costs.
- Verify the candidate exactly matches the declared formula and rounding increment.
- Obtain founder approval and timestamp.
- Insert the approved amount only into the private final PDF.
- Insert and verify the current proposal contact email.
- Verify active SAM `all awards` contract registration and exact legal entity and address match.
- Sign in to the required Submittable account and inspect the complete current form.
- Validate the exact private final PDF against the current CSO and July 20 FAQ.
- Review portal questions, terms, complete preview, and final confirmation.

## Claim Boundary

This is a pricing-control workflow, not a quote, certified accounting record, proposal submission, contract, award, Government price determination, SAM verification, or authorization to accept portal terms.
