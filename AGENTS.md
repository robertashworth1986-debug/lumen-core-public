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

Codex owns code changes, tests, deterministic artifacts, package assembly, and completion of specifically authorized workflows. It is **not restricted to drafts because of its agent name**. For requested code changes, implement and verify the scoped change, then commit and push when that publication is authorized. Preserve unrelated dirty work; do not leave completed work uncommitted merely because it was produced by Codex.

Codex may send an exact message after Robert's action-time approval and the same outreach preflight required of ChatGPT / Luma. Record the recipient, existing thread, approved content and attachments, perform one send, and verify its authoritative receipt. Do not request a second exception solely because the executing agent is Codex.

### ChatGPT / Luma

ChatGPT / Luma owns Gmail triage, thread summaries, and reviewable drafts, and may execute approved outreach under the same rules as Codex. Both agents require explicit action-time approval for the exact message and a passing outreach preflight; neither can authorize its own send.

### Robert Ashworth

Robert remains the decision authority for sends, submissions, signatures, fees, legal certifications, account consent, and final external claims. An authorized agent may carry out an approved action only within the applicable tool and human-handoff rules. Blanket trust does not specify a trade, transfer, legal attestation, credential change, or other material commitment. Removing the agent-name restriction does not enable live orders, money movement, automatic submissions, unattended outreach, or weakened HumanUnlock controls.

## Shared handoff

At the beginning of every pass, read:

- `docs/CANONICAL_OPERATING_STATE.md`
- `config/outreach_registry_v1.json`
- `docs/CLAIM_BOUNDARY_REGISTER.md`

At the end of every pass, update the existing canonical state or package. Do not email transcript dumps to Robert as the primary handoff. A self-email may be a backup, but the repository state is the shared source of truth.

## Outreach lock

Every external conversation has one stable `campaign_key` in the controlling outreach registry. Use `config/outreach_registry_v1.json` for public-safe campaign metadata, or the existing private lane's schema-valid registry via `--registry` when recipient/content details must stay private. Reconcile missing campaign metadata before sending; do not invent a second campaign to escape a hold or publish private buyer records.

Before any send:

1. confirm the user explicitly approved the exact send at action time;
2. search Gmail Sent and the existing thread for prior messages to the same contact and purpose;
3. run `python code/ops/outreach_gate.py check ...` with the actual actor, controlling registry, and truthful approval/preflight flags; a boolean CLI flag is a recorded assertion, not an approval source;
4. reply in the existing thread after the first outbound;
5. send exactly one message;
6. verify the sent message, update the controlling registry immediately, consume that message's approval, and apply the Gmail label `LumenCore/Outreach Lock`.

The gate evaluates eligibility; it does not send, authenticate the founder, bind message bytes, or consume approvals. Retain the existing byte-bound action-time authorization and single-use dispatch/consumption controls for programmatic dispatch. No approval transfers to changed content, another recipient, a different attachment, or a later follow-up.

A differently worded message with the same contact and purpose is still a duplicate. A receipt, referral, calendar invite, or automated acknowledgment does not reset the lock. Only a substantive inbound request or explicit founder decision can change the campaign state.

No agent may bypass the gate by creating a new subject, recipient alias, branch, packet, or campaign key.
