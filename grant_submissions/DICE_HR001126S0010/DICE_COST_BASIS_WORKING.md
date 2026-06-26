# DICE Cost Basis - Working Draft

Updated: June 13, 2026

Status: planning basis only; not a certified cost proposal, accounting
determination, vendor quote, or commitment by any proposed teammate.

## Solicitation Basis

DARPA HR001126S0010 describes DICE as a 36-month, three-phase effort:

- Phase 1: 9 months, decentralization and early comparison against
  state-of-the-art centrally orchestrated multi-agent systems;
- Phase 2: 15 months, adversarial robustness; and
- Phase 3: 12 months, scalability.

Section 7 states that cost realism depends on realistic and substantiated
labor hours, materials, equipment, travel, subaward, and other cost bases.
The BAA also states that resource sharing may be required for an Other
Transaction for Research or Prototype award. The Government retains
discretion over the final award instrument.

## Reconciled Planning Total

| Cost element | Working assumption | Total |
|---|---|---:|
| Direct labor | 21,060 hours at provisional $100/hour blended direct rate | $2,106,000 |
| Fringe | 25% of direct labor | $527,000 |
| Overhead and G&A | 28% of direct labor plus fringe, rounded | $737,000 |
| Specialized subawards and consultants | Distributed systems, inference control, HPC, and independent evaluation scopes | $350,000 |
| Cloud and HPC | Development, model inference, adversarial evaluation, scaling, storage, and logging | $1,040,000 |
| Travel | Program reviews, integration events, and demonstrations | $80,000 |
| Software, data, and equipment | Developer systems, storage, licenses, and test data | $80,000 |
| **Total** | **36-month planning estimate** | **$4,920,000** |

The labor plan represents about 3.9 full-time-equivalent years per program
year using 1,800 productive hours per FTE-year. That is a lean average staffing
level for combined TA1/TA2 work and assumes the specialized subaward effort is
available when needed.

## Phase Reconciliation

| Cost element | Phase 1, months 1-9 | Phase 2, months 10-24 | Phase 3, months 25-36 | Total |
|---|---:|---:|---:|---:|
| Direct labor | $430,000 | $900,000 | $776,000 | $2,106,000 |
| Fringe | $108,000 | $225,000 | $194,000 | $527,000 |
| Overhead and G&A | $151,000 | $315,000 | $271,000 | $737,000 |
| Subawards and consultants | $120,000 | $150,000 | $80,000 | $350,000 |
| Cloud and HPC | $180,000 | $420,000 | $440,000 | $1,040,000 |
| Travel | $20,000 | $20,000 | $40,000 | $80,000 |
| Software, data, and equipment | $41,000 | $20,000 | $19,000 | $80,000 |
| **Phase total** | **$1,050,000** | **$2,050,000** | **$1,820,000** | **$4,920,000** |

## Labor-Hour Planning Envelope

The 21,060 direct labor hours should be converted into named labor categories
only after the performer structure is known. A defensible full proposal should
identify, at minimum:

- principal investigator and technical integration lead;
- TA1 distributed planning/consensus research;
- TA2 inference-control and evaluation research;
- research software and simulation engineering;
- cloud/HPC and reproducibility engineering; and
- independent adversarial evaluation.

No unnamed person should be represented as committed. Employee, consultant,
and subaward treatment must match the actual relationship and applicable
cost principles.

## Sensitivity and Cost Controls

- A 15% change in labor, fringe, and indirect assumptions moves the total by
  about $506,000.
- A 30% change in cloud/HPC usage moves the total by about $312,000.
- A 25% change in specialized subaward/consultant scope moves the total by
  about $88,000.
- The current practical planning range is therefore approximately $4.0
  million to $5.8 million until rates, teaming, quotations, and resource
  sharing are resolved.
- Phase 1 should gate larger model and scaling spend behind measured adaptor
  integration, baseline, and small-scale inference results.
- Cloud estimates must distinguish stochastic simulation from actual
  foundation-model inference; the existing 100,000-agent result is not an LLM
  inference cost measurement.
- Use TA3-provided simulation capabilities where allowed and technically
  appropriate rather than duplicating Government-provided infrastructure.

## Required Before Full Proposal

1. Select the intended award instrument for proposal planning and document
   any required resource sharing.
2. Validate the accounting treatment and indirect-rate bases with qualified
   federal-contract cost support.
3. Convert labor hours into named categories, task assignments, and phase
   hours.
4. Obtain written scopes and quotations for each subaward or consultant.
5. Obtain cloud/HPC quotations and document utilization assumptions by
   workload type.
6. Reconcile every task, deliverable, milestone, and cost element to the
   official DARPA cost templates.
7. Preserve this document as a planning record; do not submit it as a
   certified representation without review.
