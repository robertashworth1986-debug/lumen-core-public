# LumenCore Buyer-Owned Baseline Validation Sprint — Fit Intake

**Status:** non-confidential fit-check template. This is not a contract,
invoice, commitment, validation result, or authorization to transfer data.

Use this page to determine whether one buyer-owned decision can be converted
into a bounded validation scope. Mark unknown facts `UNKNOWN`; do not guess.

## First-fit facts

1. **Buyer:** legal organization name, public website, and buyer contact role.
2. **Decision:** the one plain-language question the buyer must answer.
3. **Candidate:** name, version, owner, and non-confidential interface summary.
4. **Accepted baseline:** incumbent, naive, historical, or named comparator and
   who accepts it for this decision.
5. **Primary metric:** definition, unit, direction, and proposed threshold.
6. **Source:** public, synthetic, or buyer-authorized data/replay description;
   rights owner; time range; and known handling restrictions.
7. **Decision owner and timing:** named role, useful-by date, and timezone.
8. **Commercial route:** known budget range, purchase-order or vendor-onboarding
   requirements, and contracting contact. Use `UNKNOWN` when not confirmed.
9. **Read-only shadow boundary:** confirm no production write access, no live
   actuation, no production credentials, the incumbent fallback, matched
   comparison conditions, and the named human approval owner.
10. **Economic conversion inputs, if requested:** buyer-owned addressable
    denominator; currency, unit, and time window; eligible share; measured
    technical delta; realization factor; implementation and run costs; and a
    stable non-overlap group. Any `UNKNOWN` keeps dollar conversion disabled.

## Do not send during the first fit check

- raw or confidential datasets;
- credentials, tokens, private keys, or production access;
- classified information, CUI, PHI, payment-card data, export-controlled
  technical data, or privileged legal material;
- personal identity, tax, bank, or insurance records; or
- patent-sensitive enabling detail that has not been approved for disclosure.

Describe the source and restrictions without transferring the source. Any
non-public transfer requires an approved agreement, handling boundary, named
authorized users, approved channel, retention rule, and incident contact.

## Fit decision

The fit check returns exactly one of these non-binding outcomes:

- `scope_candidate` — enough facts exist to draft a buyer-specific SOW;
- `needs_facts` — named facts or authority are missing;
- `needs_separate_controls` — the data or operating boundary needs legal,
  security, procurement, or regulatory controls before scoping; or
- `no_fit` — a fair, lawful, decision-useful comparison cannot be defined.

A favorable performance result is not promised. LumenCore must return `hold`
or `reject` when rights, baseline fairness, metric integrity, custody, safety,
or authority gates fail.

## Scope-to-signature path

If the fit result is `scope_candidate`, use these controlled artifacts:

1. [Canonical offer](LUMENCORE_BOUNDED_VALIDATION_SPRINT_OFFER.md)
2. [Statement of Work template](LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md)
3. [Machine-readable offer registry](../config/bounded_validation_sprint_v1.json)
4. [Strategic offer boundary](STRATEGIC_TRANSACTION_BRIEF_2026-08-08.md)

Every bracketed SOW field must be completed and appropriately reviewed before
signature. Work begins only under an accepted written scope or controlling
purchase instrument and after any required initial payment is confirmed.

Public contact entrypoint: <https://lumen-core.ai/proof_to_pilot.html>
