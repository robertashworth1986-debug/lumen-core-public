# LumenCore Revenue Engine v1

**Status:** internal qualification and conversion control. It advances active outcome 2: one external validation or paid-pilot conversion.

This is not a new top-level LumenCore product. It is a deterministic commercial control plane around the existing Buyer-Owned Baseline Validation Sprint.

## Revenue path

1. Discover a non-confidential opportunity.
2. Record one buyer-owned decision.
3. Lock candidate, accepted baseline, one primary metric, source rights, decision owner, useful-by date, and commercial route.
4. Return exactly one fit state: `scope_candidate`, `needs_facts`, `needs_separate_controls`, or `no_fit`.
5. Only a `scope_candidate` may advance to the existing SOW template.
6. Robert approves any external communication or commitment.
7. Work starts only under an accepted written scope/purchase instrument and required payment state.
8. Execution produces the existing hash-verifiable Proof Capsule and bounded buyer decision.

## Commercial source of truth

Pricing is not invented here. The engine reads the existing commercial registry at `config/bounded_validation_sprint_v1.json`. Its current proposed tiers are Launch Replay, Standard Sprint, and Institutional Sprint. The registry itself records that legal review, buyer pricing validation, and first paid scope remain incomplete; those facts must remain visible.

## Fail-closed rules

Unknown facts are not inferred. Sensitive/regulated handling triggers stop qualification until separate controls exist. No automatic email, submission, signature, spend, production mutation, claim promotion, customer claim, revenue claim, savings claim, endorsement claim, or external-validation claim is permitted.

## CLI

`python code/revenue/revenue_engine.py path/to/opportunity.json --output decision.json`

A decision record includes a SHA-256 digest of canonicalized input facts so later changes are detectable.

## Next build gate

After this control plane passes repository CI, the next bounded increment is an evidence mapper that resolves a qualified opportunity against `config/evidence_graph_v1.json` and emits only supported claims plus explicit `does_not_support` boundaries.
