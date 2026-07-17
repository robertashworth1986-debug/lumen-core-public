# Luma1 ↔ Luma2 Handoff Protocol

**Owner:** Robert Ashworth  
**Purpose:** Keep phone-side coordination and desktop-side execution synchronized without duplicate outreach, parallel truth states, or unsafe branch merges.

## 1. Roles

### Luma1

Phone / ChatGPT coordination lead:

- Gmail and calendar triage;
- remote GitHub and pull-request review;
- deadline and campaign-state reconciliation;
- public narrative and claim-boundary review;
- internal self-email handoffs;
- external email only when founder delegation and outreach gates pass.

### Luma2

Desktop / Codex execution lead:

- local filesystem and worktree inspection;
- code, tests, deterministic artifacts, and mirror receipts;
- explicit-path staging and commits;
- draft pull requests;
- no external sends, forms, signatures, fees, legal acceptance, or final confirmation clicks.

## 2. Canonical state order

When sources disagree, use this order:

1. official external record or portal receipt;
2. current `main` plus the relevant unmerged branch and full SHA;
3. `docs/CANONICAL_OPERATING_STATE.md`;
4. `config/outreach_registry_v1.json`;
5. verified local worktree receipt;
6. internal self-email handoff;
7. chat summary or memory.

Chat language never overrides a newer official record, commit, receipt, or campaign state.

## 3. Handoff envelope

Subject prefix:

```text
[LUMA HANDOFF] <lane> — <state> — <UTC date>
```

Required body fields:

```text
Sender role:
Receiver role:
Lane:
Canonical branch:
Full commit SHA:
Base SHA:
Changed paths:
Tests:
Artifacts and hashes:
External state:
Open gates:
Excluded work:
Actions not taken:
Requested next action:
```

When a file is required, include:

```text
Attachment filename:
Attachment bytes:
Attachment SHA-256:
```

The receiver verifies the filename, byte count, and SHA-256 before using the contents. A missing or mismatched file remains `UNAVAILABLE`; it is never reconstructed from memory.

## 4. Worktree rules

Luma2 must:

- start from current `origin/main` for judge, customer, or submission branches;
- treat old branches as donors, not merge targets, when they have large divergence;
- run `git status --short --branch` before editing;
- classify every changed path before staging;
- never use `git add -A` or `git add .` in a mixed worktree;
- stage explicit paths;
- report excluded local changes;
- preserve unrelated user work;
- stop on unexpected secrets, binary drift, or mirror mismatch.

Luma1 must compare the pushed branch against current `main` and review the public claim boundary before recommending merge or outreach.

## 5. Outreach rules

Self-email handoffs are authorized as internal coordination. External outreach remains campaign-gated.

Before an external send, Luma1 must verify:

- the recipient and purpose are covered by current founder delegation;
- the campaign key exists;
- no equivalent message is already sent or pending;
- the reply stays in the existing thread after the first outbound;
- no credential, private portal record, unpublished patent detail, customer identity, or unsupported claim is disclosed;
- the exact sent message is recorded in the next handoff.

Luma2 may prepare copy but may not send it.

## 6. Deadline queue

A deadline item may preempt normal work only when:

- the deadline is verified from an official source or receipt;
- the required deliverable is named;
- an existing package cannot simply be updated;
- legal, certification, fee, signature, and final-submit gates remain human-controlled;
- work is isolated from unrelated active branches.

MissionWeave DSIP and OpenAI Build Week remain separate lanes and must not be broadly staged together.

## 7. Founder provenance

Terms, modules, and build history are indexed through:

- `config/founder_lexicon_v1.json`;
- `docs/FOUNDER_PROVENANCE_AND_BUILD_TIMELINE.md`;
- current commits, pull requests, manifests, and public-safe artifacts.

Raw conversations and notebook pages are private evidence inputs. Public output uses extracts, dates, hashes, and source references—not transcript dumps.

## 8. Completion receipt

A pass is complete only when the receiving agent can answer:

- What changed?
- Where is it committed?
- What was tested?
- What remains unproven?
- What was intentionally not done?
- What exact next decision belongs to Robert, Luma1, or Luma2?

**Operating principle:** Bounded light speed—move at the fastest rate that preserves evidence custody, claim boundaries, reversibility, and founder control.
