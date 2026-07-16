# Open Power AI Consortium Public Intelligence Engine

## Purpose

This engine converts the Open Power AI Consortium's public website into a bounded, hash-addressed LumenCore intelligence snapshot. It is designed to turn a useful introduction into an operating asset: an inspectable map of public member organizations, work groups, events, models, datasets, documents, and official contact channels.

It does **not** automate membership consent or submit web forms. Membership enrollment remains a founder-authorized communication with the consortium. The collector is read-only and public-only.

## Why this fits LumenCore

The consortium's public structure directly overlaps LumenCore's proof-to-pilot lane:

- **Use Case Work Group:** prioritizes use cases and creates sandboxes that protect data and IP.
- **Domain-Specific Model Work Group:** curates governed datasets and benchmarks model performance.
- **Implementation Work Group:** develops deployment lessons, case studies, playbooks, and roadmaps.
- **Data Sharing Work Group:** develops responsible data-sharing methods, contractual templates, anonymization, aggregation, and synthetic-data options.
- **Member Representative Committee:** coordinates member participation and asks each organization to designate a representative.

LumenCore's safe contribution is narrow: frozen baselines, metrics locked before scoring, held-out replay, manifest verification, negative-result retention, and reviewer-readable claim boundaries.

## Run

```bash
python code/ops/BUILD_OPAI_PUBLIC_INTELLIGENCE.py \
  --output out/opai/opai_public_intelligence.json
```

The default run:

1. fetches and enforces `robots.txt`;
2. restricts crawling to public pages on `openpowerai.org`;
3. blocks login, account, admin, user, and form paths;
4. rate-limits requests;
5. limits response sizes and page count;
6. stores SHA-256 hashes for every fetched page;
7. creates a stable manifest hash that excludes the generation timestamp;
8. records fetch failures rather than inventing missing content.

If `robots.txt` cannot be checked, the collector stops by default. `--allow-on-robots-error` exists only for a reviewed manual run and records that weaker posture in the output.

## Output schema

The generated JSON contains:

- `pages`: source URL, title, status, content type, source hash, headings, and public-link counts;
- `organizations`: public organization names exposed on the consortium membership page;
- `work_groups`: public group names, leads, and descriptions;
- `events`: public event titles, dates, and descriptions;
- `models`: public model names and descriptions;
- `datasets`: public dataset names, source/license language, and descriptions;
- `documents`: public PDF/public-attachment links;
- `official_contacts`: organization-published consortium email addresses;
- `errors`: bounded fetch or robots/scope failures;
- `manifest_sha256`: cryptographic identity of the stable snapshot content.

## Claim and IP boundary

This output is public-source intelligence, not consortium endorsement, membership confirmation, a utility partnership, field validation, or permission to reuse member-owned material outside its stated license. Do not copy paid, authenticated, or restricted content into the snapshot. Do not place utility data, credentials, private emails, unpublished patent details, or protected LumenCore implementation constants into consortium public channels.

## Validation

```bash
python -m pytest tests/test_opai_public_intelligence.py
```

Tests cover organization, work-group, event, model, dataset, document, and official-contact extraction; stable manifest behavior; same-domain and sensitive-path restrictions; and the no-form-submission boundary.
