# Private Conversation and Notebook Audit Protocol

**Purpose:** Convert private historical conversations, notebooks, notes, screenshots, and local artifacts into a public-safe provenance index without publishing private content or overstating what the sources prove.

## Boundary

This protocol may establish chronology, design continuity, terminology, and build intent. It does not establish:

- scientific validity;
- external validation;
- legal priority;
- trademark registration;
- patentability;
- customer adoption;
- revenue;
- agency endorsement;
- certification;
- field performance.

The raw source corpus remains private unless Robert explicitly releases a bounded item.

## Source classes

| Class | Examples | Default handling |
|---|---|---|
| Conversation export | ChatGPT account export, shared-conversation metadata | Private; hash and parse locally |
| Digital notebook | iCloud Notes export, Google Docs, Markdown, text files | Private; hash and parse locally |
| Paper notebook | Scans or photographs | Private; date and page custody required |
| Local build evidence | Worktree files, terminal receipts, screenshots, manifests | Private until reviewed and redacted |
| Public repository | commits, PRs, issues, workflows, artifacts | Public-safe subject to claim boundary |
| External record | portal receipt, official email, signed document | Preserve exact source; publish only with permission and redaction |

## Intake receipt

Every source receives a private receipt containing:

```json
{
  "source_id": "stable internal identifier",
  "source_class": "conversation_export | digital_notebook | paper_notebook | local_build | public_repo | external_record",
  "title": "source title",
  "created_or_claimed_date": "ISO date or unknown",
  "acquired_utc": "ISO timestamp",
  "bytes": 0,
  "sha256": "64 lowercase hex characters",
  "rights_status": "founder_owned | authorized | public | unknown",
  "contains_sensitive_data": true,
  "public_release_state": "private | excerpt_approved | public_safe",
  "notes": "bounded handling note"
}
```

A source with missing bytes, hash, rights status, or sensitivity classification remains unprocessed.

## Extraction unit

Each candidate timeline event uses:

```json
{
  "event_id": "stable identifier",
  "date": "ISO date or date range",
  "term_or_build": "name",
  "event_type": "idea | definition | design | code | test | artifact | outreach | submission | receipt | review | rejection | approval",
  "source_ids": [],
  "public_safe_summary": "bounded summary",
  "repo_links": [],
  "evidence_type": "founder_record | commit | test | manifest | external_record",
  "claim_boundary": "what this event does and does not prove",
  "publication_state": "hold | private | public_safe"
}
```

No event becomes public solely because a phrase appears in a chat. Public promotion requires a source receipt and a bounded claim.

## Deduplication

Treat these as one lineage unless evidence supports separation:

- spelling variants;
- capitalization changes;
- repeated prompts;
- regenerated drafts;
- copied messages;
- self-emails carrying the same attachment;
- branches created from the same donor commit;
- screenshots of the same underlying artifact.

Preserve the earliest verified source and the strongest later implementation evidence.

## Conversation-export workflow

1. Obtain the official ChatGPT data export.
2. Preserve the original ZIP unchanged.
3. Record ZIP bytes and SHA-256.
4. Extract into a private, read-only audit directory.
5. Inventory conversations by ID, title, created time, updated time, and message count.
6. Search for founder terms, module names, architecture decisions, tests, external contacts, deadlines, and explicit claim boundaries.
7. Link conversation events to later commits, artifacts, or external records.
8. Mark unsupported recollections as `hold`.
9. Generate only public-safe summaries and source receipts.
10. Never commit the raw export to a public repository.

## Notebook workflow

1. Identify the authoritative notebook source.
2. Export or scan without altering original dates or pages.
3. Preserve page order and file metadata.
4. Hash every source file.
5. Record whether dates are written contemporaneously, inferred, or added later.
6. Extract terms, diagrams, equations, module definitions, and build decisions.
7. Separate original marks from later annotations.
8. Link later code or artifacts where possible.
9. Keep unpublished patent-sensitive detail private.
10. Publish only a bounded index after founder review.

## Public output

The public provenance page may show:

- term or artifact name;
- first verified date;
- source class;
- public-safe excerpt or summary;
- commit, PR, manifest, or artifact link;
- current status;
- explicit limitation.

It must not expose raw private messages, private notebook images, credentials, account data, customer names, family information, legal strategy, or unpublished patent detail.

## Audit completion levels

- **Level 0 — inventory only:** source existence recorded.
- **Level 1 — custody verified:** bytes, hash, metadata, and rights status recorded.
- **Level 2 — events extracted:** dated terms and build events identified.
- **Level 3 — repo-linked:** events linked to commits, tests, or artifacts.
- **Level 4 — public-safe:** redacted timeline approved for publication.
- **Level 5 — externally corroborated:** a qualified outside record confirms the bounded event.

A source can support founder chronology at Level 2 or 3 while remaining private.

## Safety stop conditions

Stop and hold the source when it contains:

- credentials, security codes, API keys, or tokens;
- private portal data;
- family or medical information;
- third-party confidential material;
- unpublished patent-sensitive detail;
- unclear ownership or rights;
- altered metadata or uncertain page order;
- a conflict with a newer official record.

## Final audit receipt

A complete pass reports:

- source count by class;
- hashed bytes;
- date range;
- candidate events;
- deduplicated events;
- repo-linked events;
- public-safe events;
- held events and reasons;
- sources not processed;
- exact code commit used for extraction.

**Rule:** Preserve the private source. Publish the bounded proof. Never turn a conversation archive into a performance claim.
