# ERDC SDC Phase II ROM Approval Workflow - 2026-07-17

This workflow converts the remaining ERDC estimated-price blocker into a private, auditable control. It intentionally keeps labor rates, costs, profit, risk reserve, and the candidate price out of public artifacts.

## Scope Lock

- Opportunity: `W912HZ26SC005`
- Pricing scope: Phase II prototype development only
- Proposal assumption: 16 weeks
- Phase III demonstration costs: excluded
- Phase IV implementation and scaling costs: excluded
- Resultant award posture: firm-fixed price if an award is later pursued
- Current funding posture: funding is not currently available

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

The builder reads private values only when explicitly invoked with a bounded git-ignored input path. Its public JSON and Markdown contain status, booleans, counts, source hashes, unresolved gate names, and a hash of the private candidate. They never contain a private amount or rate.

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
- Verify the computed candidate exactly matches the declared formula and rounding increment.
- Obtain founder approval and timestamp.
- Insert the approved amount only into the private final PDF.
- Separately verify active SAM contract registration, exact legal entity and address match, current portal questions, terms, and final confirmation.

## Claim Boundary

This is a pricing-control workflow, not a quote, certified accounting record, proposal submission, contract, award, Government price determination, SAM verification, or authorization to accept portal terms.
