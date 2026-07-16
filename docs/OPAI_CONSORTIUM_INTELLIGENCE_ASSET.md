# Open Power AI Consortium Intelligence Asset

**Purpose:** Convert the Open Power AI Consortium's public website into a bounded, repeatable intelligence feed for LumenCore's validation, partnership, and pilot-routing work.

## Why this is an asset

The consortium is not merely a link directory. Its public materials describe a working ecosystem spanning utilities, technology providers, researchers, data, models, working groups, benchmarking, controlled evaluation, and demonstration pathways. For LumenCore, the high-value surface is the relationship between public use cases and a reviewer-controlled proof-to-pilot protocol.

Current official public signals captured on July 16, 2026 include:

- an electric-sector AI consortium with utilities, energy companies, technology providers, researchers, and laboratories;
- working-group lanes for the Member Representative Committee, Data Sharing, Domain-Specific Model, Implementation, and Use Case activity;
- public goals around datasets, open-source libraries, AI models, benchmarking, sandbox evaluation, and implementation with utilities;
- a startup benefit path covering industry access, early testing, visibility, and market entry;
- flexible participation ranging from webcasts to working groups, workshops, data sharing, use cases, and model/tool development;
- an AI for Power Challenge pathway that describes paid utility demonstrations typically completed within 16 weeks.

## LumenCore fit map

| Consortium lane | LumenCore contribution | Safe current posture |
|---|---|---|
| Benchmarking / sandbox evaluation | Frozen source, incumbent baseline, locked metric, held-out replay, hash manifest, offline verifier | Internal replay and reproducibility evidence; not field validation |
| Data Sharing | Buyer-authorized held-out data protocol and explicit rights labels | No private utility data requested or claimed |
| Use Case | EIA-930 forecasting and replay-validation lane | Public-data reproduction handoff; full composite gate remains closed |
| Implementation | Reviewer-owned pilot contract, acceptance threshold, failure retention, and next-gate report | Proposed pilot method; no deployment claim |
| Domain-Specific Model | Model-vs-baseline evaluation and evidence packaging | Benchmark method; no consortium endorsement |
| AI for Power Challenge | Bounded utility demonstration scope with pre-registered acceptance rules | Candidate future path; no selection or award claim |

## Crawler behavior

`code/ops/build_opai_consortium_intelligence.py` performs a read-only crawl of allowlisted public OPAI pages and creates a hash-addressed JSON asset.

It deliberately:

- respects `robots.txt` and fails closed when the policy cannot be established;
- follows only exact allowlisted OPAI hosts;
- uses GET requests only;
- never submits forms;
- never attempts login, authentication, CAPTCHA handling, or member-only access;
- records public page hashes, headings, links, image-alt member candidates, working-group links, event date mentions, public documents, and contact emails;
- separates crawl failures and disallowed/external URLs instead of hiding them;
- emits an explicit claim boundary that the artifact does not prove membership, endorsement, pilot selection, private-data access, or external validation.

## Run

```bash
python code/ops/build_opai_consortium_intelligence.py
```

Primary output:

```text
out/opai/opai_consortium_intelligence_latest.json
```

Dashboard-safe copy:

```text
dashboard/data/opai_consortium_intelligence.json
```

For a one-off local run that does not update the dashboard surface:

```bash
python code/ops/build_opai_consortium_intelligence.py --no-dashboard
```

## Membership status boundary

On July 16, 2026, LumenCore submitted an expression of interest through the consortium's published contact channel after an EPRI Incubatenergy Labs referral. That action initiates onboarding; it does **not** establish accepted membership. Public language must remain `membership interest submitted` until OPAI confirms acceptance or completes onboarding.

## Next validation gate

After onboarding, the strongest initial ask is not a broad product pitch. It is a narrow consortium-controlled evaluation:

1. identify the appropriate working group or utility owner;
2. select buyer-authorized data and the incumbent comparator;
3. lock the primary metric, threshold, replay window, and economic conversion rule before scoring;
4. run without post-outcome tuning;
5. retain positive, neutral, incomplete, and negative results;
6. issue an independent-review receipt and bounded next-pilot decision.

*Founder-owned. Public-source intelligence only. Evidence before claims.*
