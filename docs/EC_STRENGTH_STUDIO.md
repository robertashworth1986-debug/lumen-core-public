# EC Strength Studio

**Our strength is making everyone else stronger.**

The TakeOff community gift is a shared operational workspace with a personalized
profile and portable package for each of the 69 official Fall 2026 businesses.
Excalis is the first showcase: a design brief, approved revision fingerprint,
production handoff and whole-batch energy comparison. HopeConnect Health uses
the same foundation for nonclinical coordination practice.

Open [Excalis](https://lumen-core.ai/cohort/?member=excalis),
[HopeConnect Health](https://lumen-core.ai/cohort/?member=hopeconnect-health), or
the **Discover the cohort** view to select any other member. The **Your free
package** view provides a member-specific ZIP and a PowerShell block that checks
its SHA-256 before extraction. All packages are free MIT-licensed software;
members pay their own optional API usage.

## Included workflows

| Tool | Working behavior | Evidence and action boundary |
| --- | --- | --- |
| Workboard | Create/edit briefs, review missing inputs, track owner acceptance, stage work, hash a selected revision file locally | The file itself is not uploaded. Starting/completing work requires recorded owner acceptance. |
| Measure & improve | Record source-backed observations; calculate Wh per accepted part and complete-batch net differences | Equal accepted output, quality/conditions and full energy accounting are required for comparison. Failures, rework, warm-up and auxiliaries remain included. |
| Grant Factory | Produce and export a member-specific Markdown working draft from supplied facts | Unknown identity, organization type, costs and eligibility remain unknown. No certification or submission. |
| LumaScout | Save opportunities; the local runtime retrieves official Grants.gov search results and ranks topic keywords | Relevance is not eligibility, award likelihood, a verified deadline or a customer introduction. |
| Paper Lab | Daily CSV simulation; local hourly BTC-USD paper bot with a reconciled Decimal ledger | Fictional money only, long-only, 25% cash allocation, modeled 10 bps fees and 5 bps slippage. No broker-order endpoint. |
| LumaCare | Fictional/non-sensitive coordination IDs, owner roles, next steps and confirmation checks | No patient identifiers or clinical records. No medical decision-making or claimed regulated-data deployment. |
| Luma Assistant | An explicit prompt and the public business profile are sent to the OpenAI Responses API | Draft only; it cannot read private workboard or care data, execute arbitrary code, send messages, submit forms or trade. |

The public website stores work in the member's browser. The downloaded runtime
also saves a local SQLite backup outside its public directory. Export/import
preserves member identity. A saved revision is required for each local backup
write; the revision check and update share one SQLite transaction. If another
session saved first, the server preserves that backup and returns a conflict.
On startup, different nonempty browser and local versions pause backup until
the owner reviews them. The recovery screen offers separate downloads and an
explicit choice. An empty browser can restore its local backup automatically.
These are local workspaces, not hosted multi-user
accounts. Team access, business-system connections and regulated data require
an owner-approved deployment and review. Government certification, HIPAA
compliance, independent validation, achieved savings and trading profit are not
established by these tools.

## Runtime

Python 3.11+ is sufficient; no third-party Python installation is needed.

```powershell
python .\luma_runtime.py --member excalis
```

The runtime listens only on `127.0.0.1:8766`. It validates the Host and Origin,
rejects cross-origin JSON operations, serves an explicit static file list, bounds
input and source response sizes, preserves failed requests, and prevents duplicate
AI/source actions with request IDs. Existing `OPENAI_API_KEY` is read only from
the process environment. The package README supplies a hidden temporary key
prompt for members who need one; no key is distributed or saved.

The local scheduler owns the hourly public-source jobs. It does not run arbitrary
model tools or a sandbox. OpenAI Responses handles bounded drafts, with no retries,
four requests per hour and 1,800 output tokens per request. A successful key
presence check does not prove inference access or an available credit balance.
Closing the Python process stops scheduled tasks. The local audit chain is a
custody aid, not an external attestation.

The browser's daily simulator uses previous-close signals and next-open fills.
The hourly paper bot uses only completed hourly candles and then the public quote
observed at the run. Both are simple comparison baselines. They exclude real
liquidity, taxes and actual brokerage execution. Missing/stale quotes or incomplete
history hold the paper tick. Coinbase was observed returning 350 candles without
an explicit range, despite its documented 300-candle maximum; the runtime uses an
explicit 25-hour request, a 500-row safety bound and independent timing validation.

## Reproducible builders and source reuse

```powershell
python code\ops\build_ec_cohort_workspace.py
python code\ops\build_ec_member_packages.py
python -m pytest tests\test_ec_member_runtime.py -q
node --test tests\ec_studio_core.test.mjs
```

The catalog builder reads the already reviewed public
`EC_COHORT_STRENGTH_RESEARCH_2026-09-11.csv` and verifies 69 identities and 207
hypotheses. It never reads the private proof vault. Package files and hashes are
explicitly enumerated; fixed ZIP timestamps make repeated builds reproducible.
No secrets, patient records, member email lists or private runtime state are
packaged. The renderer reuses the existing Three.js assets from the ProofLock
surface and pauses motion when requested. It renders a proposed workflow, not a
measured dependency graph or a claim of quantum computation.

The runtime reuses `grants_autofill.extract_hits`, `score_hit` and
`normalize_result` for supplied public search data, and
`audit_paper_accounting.audit_paper_ledger` for exact paper accounting. The legacy
application factory's LumenCore-specific identity, demographic defaults, budgets
and submission paths are excluded from member workspaces.

## Publication

The existing manual exact-snapshot workflow publishes the 189 explicitly allowed
files: the original 43 public files plus 146 cohort files, including 69 ZIPs,
69 standalone public member profiles and one public directory.
It uses existing production deployment credentials. It does not redeploy the
gateway, modify server secrets, or expose a shared API key.

Historical receipt reconstruction reads the literal release membership from
the recorded source commit through Python's AST parser. It never executes old
source files. Old 43-file receipts remain immutable and verifiable after the
current allowlist expands. CycloneDX inventories each ZIP as a file component;
the package's own manifest records its contents. Neither inventory is a software
certification or a vulnerability-free assertion.

## Primary documentation

- [OpenAI model and Responses guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [Grants.gov search](https://www.grants.gov/search-grants)
- [Coinbase public candle contract](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles)
- [Official TakeOff Fall 2026 cohort](https://ec.co/takeoff-fall-2026-accelerator-cohort/)

Public business descriptions and improvement questions remain subject to owner
correction. This contribution does not imply EC or individual member endorsement.

## Public member discovery

Each business has a permanent, pre-rendered strength profile under
`/cohort/members/<member-id>.html`, linked from `/cohort/directory.html` and the
interactive directory. The returned HTML includes the business name, public
strength, three hypotheses, measurement plans, source links and toolkit access.
Unique title, description, canonical and Open Graph metadata identify that
profile. The sitemap lists all 69 profiles and the public directory. This makes
the pages available to crawlers and link previews; indexing, ranking and actual
discovery are not established by publication.

The existing catalog builder generates these pages from the same reviewed public
CSV. It makes no AI request. The static profile remains readable without
JavaScript, and links to the shared interactive workspace and the matching ZIP.
Member profiles identify the contribution as independent, preserve unknown
baselines and direct readers to each business's source material.

Google's [JavaScript SEO guidance](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
supports pre-rendered content, crawlable links, unique metadata and consistent
canonical URLs. Its [sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview)
describes discovery assistance without guaranteeing indexing.
