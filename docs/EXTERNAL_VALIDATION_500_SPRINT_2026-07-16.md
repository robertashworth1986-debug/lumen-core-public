# $500 External Validation Sprint

Generated UTC: `2026-07-29T11:40:31.713636+00:00`

## Decision

**Put the full $500 into one outcome-independent external evaluator engagement.** Do not put it into live trading, model tuning, GPUs, ads, or generic subscriptions. The repository already has the frozen packet, verifier, protocol template, receipt template, and public clean-runner infrastructure; the missing scarce input is a qualified independent human.

Status: `BUDGET_HELD_PENDING_HUMAN_SELECTION_OF_AN_INDEPENDENT_EVALUATOR`

No spending, hiring, account creation, or external contact is authorized by this packet. A human must select the evaluator and approve each milestone.

## Why This Is The Bottleneck

- Current supported maturity remains Level `3`; Level 5 attained: `false`.
- The active hourly lane has `951` sealed predictions and `896` settlements.
- Only `6` of `8` authorities have any valid prospective seal; `SWPP, TVA` remain at zero.
- Common settled hours across the full panel: `23`.
- Independent reproduction complete: `false`.
- Performance promotion allowed: `false`.

The current incomplete sample is useful feasibility evidence, not performance validation. The evaluator must preserve that unfavorable state and freeze the next valid protocol before scoring.

## Exact Milestone Allocation

1. **$100 - Independent protocol review and freeze**
   - Estimated scope: 2 hours.
   - Release only when: Evaluator returns an attributable accept-or-decline memo, completed conflict disclosure, and an evaluator-controlled protocol decision before scoring.
   - Payment is fixed and remains due for a negative result.
2. **$300 - Reviewer-controlled clean-room reproduction**
   - Estimated scope: 6 hours.
   - Release only when: Evaluator returns environment fingerprint, raw verifier logs, recomputed hashes and arithmetic, discrepancy ledger, and completed reproduction receipt.
   - Payment is fixed and remains due for a negative result.
3. **$100 - Attributable validation memo and final receipt**
   - Estimated scope: 2 hours.
   - Release only when: Evaluator returns a dated decision memo stating the supported maturity level, all caveats, and the final receipt hash; publication of identity remains evaluator-controlled.
   - Payment is fixed and remains due for a negative result.

Total: **$500** across approximately **10 bounded reviewer hours**.

## Evaluator Selection Rubric

| Criterion | Weight |
| --- | ---: |
| Independence And Conflict Controls | 35 |
| Reproducibility And Python | 25 |
| Statistics And Time Series | 20 |
| Energy Or Forecasting Context | 10 |
| Clear Attributable Reporting | 10 |

Minimum score: **75 / 100**. Independence is a hard gate even when the weighted score passes.

- No prior role designing, tuning, or promoting the evaluated model.
- Discloses compensation, relationships, and any financial or professional conflicts.
- Can independently run Python and inspect time-series validation, error metrics, bootstrap uncertainty, and append-only hash chains.
- Uses a reviewer-controlled machine or cloud account and preserves raw logs.
- Agrees that missing authorities, failed gates, discrepancies, and negative results remain in the final record.
- Accepts no bonus, success fee, equity, revenue share, or future work contingent on a positive result.

## Copy-Paste Evaluator Brief

> Reproduce and audit a frozen EIA-930 hourly forecasting evidence packet on your own machine. This is a fixed-scope, outcome-independent engagement. You will review and accept or decline the protocol before scoring, verify hashes and settlement arithmetic, preserve missing-authority and negative results, and return raw logs plus an attributable decision memo. You are not being asked to tune the model, endorse LumenCore, prove trading profitability, or reach a positive conclusion. Compensation is fixed by deliverable and does not change with the result.

Required deliverables:

1. Conflict disclosure and accept-or-decline protocol memo.
2. Environment fingerprint, verifier logs, rehashed artifacts, discrepancy ledger, and completed reproduction receipt.
3. Dated final memo stating the exact maturity level supported and every material caveat.

## Use Free Infrastructure

- **Public GitHub Actions standard runner ($0):** Independent clean-runner execution and preserved logs.
- **OSF registration ($0):** Time-stamped, read-only protocol registration before scoring.
- **Zenodo release archive ($0):** Public artifact archive and DOI for a reviewer-safe release.
- **GitHub Pages ($0):** Public read-only reviewer surface when the repository is public.

These rails provide clean execution, preregistration, archival identity, and a public reviewer surface without consuming the $500.

## Do Not Spend On

- Live trading capital, exchange deposits, leverage, or paid signals.
- More model training, GPUs, tuning runs, or candidate searches before the frozen evaluation completes.
- Advertising, follower growth, press releases, or investor promotion before an attributable external receipt exists.
- A positive-result bonus, success fee, equity grant, revenue share, or future contract promised for validation.
- Generic cloud subscriptions when the public clean-runner, registration, archive, and reviewer page can be operated on free tiers.
- A data subscription unless the evaluator documents why the public frozen packet cannot answer the registered reproduction question.

## Economic Pressure-Release Path

The shortest defensible path is: independent receipt -> paid evidence review or grant-funded validation -> buyer-owned pilot -> only then a bounded economic conversion or license discussion. The receipt is a credibility asset, not revenue by itself, and it does not authorize live trading.

## Official References

- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions): Standard GitHub-hosted runners are free for public repositories.
- [OSF registrations](https://help.osf.io/article/330-welcome-to-registrations): Registrations are time-stamped, read-only records of the study plan.
- [Zenodo GitHub integration](https://help.zenodo.org/docs/github/): GitHub releases can be archived and assigned a persistent research record.
- [Upwork data analyst rates](https://www.upwork.com/hire/data-analysts/cost/): A $500 fixed scope is roughly ten hours at the upper end of the cited analyst range; evaluator quality and independence still control selection.

## Source Chain

- `config/external_validation_500_sprint_v1.json` - SHA-256 `df43e3ec7be28b7f4e7abb5acc2121f0d28876e3596d1cdd25b21f45f2873ab6`
- `evidence/external_validation/eia_grid_prospective_hourly_runtime_projection_20260716.json` - SHA-256 `bd55adf5f3c64da90827370e8c1c36032718bd474bd733db302381e2e0a7fedd`
- `evidence/external_validation/eia_grid_hourly_independent_reproduction_handoff_20260716.json` - SHA-256 `86d42f3bed3502db60c7c94fb16573a19b0a9194d8d441c88d3892c5a591185f`
- `config/eia_grid_hourly_external_evaluator_protocol_template_v1.json` - SHA-256 `f1284de55e059596a25c554d11520f5398cdae053f35a6362bab2f3e0e8776da`
- `config/eia_grid_hourly_independent_reproduction_receipt_template_v1.json` - SHA-256 `68101f795152bd5ad0a62e6ed2e1c0edffb04a7b05642f4223ecd3fa09a5b407`
- `docs/EIA_GRID_HOURLY_INDEPENDENT_REPRODUCTION_HANDOFF_2026-07-16.md` - SHA-256 `d9ec41387570092242e057e3d5b3383b6f58f925ed095040d0d8e6db884cc562`

Source-input chain SHA-256: `f9466cc99c286cf244b278e4d72360739bbb7a6013ee75544c4b515550d9bb98`

Packet SHA-256: `7e041d36d5b7eafe04b6331475596d035b84b678e06808d824af209c5e3fe6ea`

## Claim Boundary

This sprint is a budget and reviewer-engagement control. It does not hire an evaluator, authorize spending or external contact, prove independent validation, promote the evidence maturity level, establish model skill, create realized savings, authorize live trading, or guarantee revenue, funding, publication, or a positive result.
