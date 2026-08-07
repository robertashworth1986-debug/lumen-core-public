# LumenCore Agent Operating Contract

This file governs every AI agent and automation working in this repository.

## Canonical company story

LumenCore is a **proof-to-pilot AI infrastructure validation architecture**. It helps a buyer or reviewer lock the source, incumbent baseline, metric, threshold, holdout rule, failure definitions, and prohibited claims before scoring, then produces a reviewer-readable Proof Capsule.

Trading, grants, scouting, geometry, swarm, aviation, maritime, sensor, and other research lanes are supporting evidence or archived experiments. They are not separate company identities and must not become new top-level products without a buyer-owned decision and explicit founder approval.

## Work-in-progress limit

Only three founder outcomes may be active at once:

1. **EPRI / Open Power AI Consortium onboarding** — keep agreement status, dates, and legal terms in the private controlling record. One bounded reply supplied requested logo assets with limited-use language; EPRI/OPAI later said presence and contributions to MRC and Work Group meetings are enough. Do not send another onboarding or contribution-path follow-up, and make no endorsement, validation, award, utility-adoption, or performance claim.
2. **One external validation or paid-pilot conversion** — one private-review follow-up is active. Keep the counterparty identity and shared materials out of the public repository; the exchange does not establish a partnership, customer, pilot, endorsement, or validation. LANL and EVTit remain waiting lanes.
3. **Patent official-record protection** — retrieve and review the official Patent Center record, notices, and deadlines before creating more public patent packages.

Funding opportunities remain a deadline queue, not a product-development queue. Do not build a new package unless it is already in the canonical funding handoff, the verified deadline is near, and no existing package can be updated.

Before creating any file, branch, packet, dashboard, or module:

- search for an existing canonical artifact;
- update or supersede it instead of creating a parallel version;
- state which of the three active outcomes it advances;
- stop when it advances none of them.

## Agent roles

### Codex

Codex owns code changes, tests, deterministic artifacts, and package assembly. Codex is **draft-only for all external communication**. It must not send email, submit forms, book meetings, sign documents, pay fees, accept legal terms, or click final confirmation controls.

### ChatGPT / Luma

ChatGPT owns Gmail triage, thread summaries, and reviewable drafts. It may send only after Robert gives explicit action-time approval for that exact message and the outreach preflight passes.

### Robert Ashworth

Robert is the sole authority for sends, submissions, signatures, fees, legal certifications, account consent, and final external claims.

## Shared handoff

At the beginning of every pass, read:

- `docs/CANONICAL_OPERATING_STATE.md`
- `config/outreach_registry_v1.json`
- `docs/CLAIM_BOUNDARY_REGISTER.md`

At the end of every pass, update the existing canonical state or package. Do not email transcript dumps to Robert as the primary handoff. A self-email may be a backup, but the repository state is the shared source of truth.

## Outreach lock

Every external conversation has one `campaign_key` in `config/outreach_registry_v1.json`.

Before any send:

1. confirm the user explicitly approved the exact send at action time;
2. search Gmail Sent and the existing thread for prior messages to the same contact and purpose;
3. run `python code/ops/outreach_gate.py check ...`;
4. reply in the existing thread after the first outbound;
5. send exactly one message;
6. update the registry immediately and apply the Gmail label `LumenCore/Outreach Lock`.

A differently worded message with the same contact and purpose is still a duplicate. A receipt, referral, calendar invite, or automated acknowledgment does not reset the lock. Only a substantive inbound request or explicit founder decision can change the campaign state.

No agent may bypass the gate by creating a new subject, recipient alias, branch, packet, or campaign key.
