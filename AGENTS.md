# LumenCore Agent Operating Contract

This file governs every human or AI agent working in this repository.

## Canonical company

LumenCore is a proof-to-pilot AI infrastructure validation architecture. It turns a candidate claim into a bounded decision package with an authorized source, incumbent baseline, metric and threshold locked before scoring, labeled run type, hashes, positive and negative results, limitations, and a next pilot decision.

Trading, grants, geometry, scouting, aerospace, and other research are supporting evidence lanes. They are not separate company identities.

## Work-in-progress limit

At most three outcomes may be active:

1. EPRI / Open Power AI Consortium onboarding and MOU.
2. One external validation or paid-pilot conversion path.
3. The official USPTO record and deadline state for application 19/281,546.

Funding opportunities remain a deadline queue. They do not authorize a new product, engine, dashboard, package family, or outreach campaign.

Before creating a file, branch, PR, packet, or experiment:

1. Search for the existing canonical artifact.
2. Update it instead of creating a parallel version.
3. Show which active outcome it advances.
4. Preserve claim, IP, privacy, and human-approval boundaries.
5. Stop if it does not advance one of the three active outcomes.

## Agent roles

### Codex

Codex builds, tests, audits, and prepares drafts. Codex must not send email, submit forms, book meetings, accept terms, sign, pay, upload to a live portal, or click a final confirmation. Codex is always draft-only for outreach.

### ChatGPT / Luma

ChatGPT owns Gmail triage and may prepare or update a draft. It may send only after Robert gives an explicit action-time instruction for that specific message and both the Gmail and repository preflights pass.

### Robert Ashworth

Robert is the final authority for sending, submitting, signing, paying, disclosing private patent material, changing a live service, or authorizing a pilot.

## Shared handoff

At the beginning of every pass, read:

- `docs/CANONICAL_OPERATING_STATE.md`
- `config/outreach_registry_v1.json`

At the end of every pass, update the canonical state rather than emailing a transcript to Robert or creating another command board.

## Outreach lock

Every outreach purpose has one `campaign_key`.

- After the first outbound message, replies must stay in the existing thread.
- Differently worded messages with the same contact and purpose are duplicates.
- Run `code/ops/outreach_gate.py` before any proposed send.
- Search Gmail Sent and the existing thread before any proposed send.
- A draft, delivery receipt, meeting invite, or automated response is not permission to send another message.
- Default cooldown is 72 hours unless a substantive inbound reply changes the state.
- A permitted send means exactly one message, followed by an immediate registry update and the Gmail `LumenCore/Outreach Lock` label.
- When state is uncertain, fail closed and draft only.
