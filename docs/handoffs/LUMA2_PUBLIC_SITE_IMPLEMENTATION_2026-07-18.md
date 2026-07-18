# Luma2 Public-Site Implementation Handoff — 2026-07-18

## Operating branch

`agent/public-site-conversion-v1`

Base: `main` at `5eed39965f29e86ae7700a805f579592718de0e1`.

## Completed and locally validated design package

A complete public-site package was built and validated before this handoff. It contains:

- rebuilt `dashboard/operator_home.html` as a buyer-readable public homepage while retaining the phrase `One proof path. One bounded decision.`;
- new `dashboard/bounded_validation.html` service page;
- responsive `dashboard/assets/public_site.css`;
- local SVG brand mark/favicon;
- 1200×630 social-sharing card;
- `dashboard/robots.txt` that excludes internal operational surfaces;
- `dashboard/sitemap.xml` limited to stable public conversion surfaces;
- `dashboard/site.webmanifest`;
- `tests/test_public_site_contract.py`;
- `.github/workflows/public-site-contract.yml`;
- exact Skip profile/service copy for authenticated entry.

Local validation completed before handoff:

- 8/8 public-site contract tests passed;
- no missing local destinations;
- no duplicate IDs;
- valid manifest and sitemap;
- 1200×630 social card verified;
- Chromium desktop QA at 1440×1100;
- Chromium mobile QA at 390×844;
- zero horizontal overflow;
- zero browser-console errors.

## Confirmed defects to fix

1. `dashboard/operator_home.html` links to `/proof_to_pilot.html`, but no such repository file exists on `main`.
2. The homepage is strong for technical review but weak for buyer conversion: no plain-language service page, buyer deliverables, fit criteria, or structured intake.
3. The homepage links visitors into `mission_control.html`, an internal operational surface containing broad and potentially stale experimental scope.
4. The dashboard tree lacks a complete public SEO/discovery layer: focused `robots.txt`, `sitemap.xml`, manifest, local favicon, social preview, canonical URL, Open Graph, Twitter metadata, and structured organization data.
5. Skip has prompted LumenCore to add products/services; the public site needs matching bounded service language.

## Required buyer-facing architecture

### Homepage

Lead with the bounded decision proposition, not the internal platform universe.

Required visitor path:

1. Understand the problem: evidence, baseline, metric, and authority are commonly blurred.
2. Understand the solution: LumenCore packages a claim into a reproducible, fail-closed review path.
3. See the outputs: source manifest, baseline lock, metric definition, replay/verifier, result record, limitations, and next-gate decision.
4. Determine fit.
5. Start a Bounded Validation Review through a structured intake.

Remove Mission Control as a primary public CTA. Keep internal and experimental consoles out of the buyer journey and out of the sitemap.

### Bounded Validation Review page

Include:

- who it is for;
- the exact entry requirements;
- the process;
- buyer deliverables;
- what LumenCore does not certify;
- explicit exclusions;
- FAQs;
- intake fields for claim, authorized source, incumbent baseline, metric/acceptance rule, decision owner, timing, and disclosure constraints.

Use a mailto or otherwise repository-compatible bounded intake unless a tested backend is already available. Do not imply that submission creates a contract, certification, validation result, or confidentiality agreement.

## Skip profile copy

Use these bounded service names:

1. **Bounded Technical Fit Check** — determine whether a claim has an authorized data source, comparison baseline, measurable acceptance rule, and accountable decision owner before deeper work begins.
2. **Proof Capsule Validation Review** — assemble a reproducible evidence packet with source identity, frozen baseline, metrics, verifier/replay path, results, limitations, and an explicit HOLD/PROMOTE/REJECT-style next-gate record.
3. **Evidence and Reproducibility Audit** — review an existing technical result for source lineage, chronological integrity, leakage risk, baseline fairness, metric reproducibility, and unsupported claims.

Do not publish the proposed `$7,500`, `$15,000`, or `$25,000` tiers. Founder approval, legal review, buyer-price validation, and first signed scope remain open.

## Hard claim boundaries

Do not add or imply:

- customer or partner status;
- EPRI membership completion until the MOU is fully executed;
- agency endorsement;
- independent scientific validation;
- field validation;
- production deployment;
- savings or revenue achieved;
- certification;
- award wins;
- patentability;
- engineering safety or manufacturability;
- superiority or `number one` claims.

Keep `ProofLock` and `MissionWeave` production/submission lanes isolated. Do not change their runtime files, certification state, deployment state, or final-action gates from this branch.

## Required checks

```bash
python -m unittest -v tests.test_public_site_contract
python -m unittest -v tests.test_proof_capsule_verifier
```

Also run:

- HTML/local-link audit;
- duplicate-ID check;
- manifest and sitemap parse;
- sensitive-string scan;
- desktop and mobile browser QA;
- console-error check;
- signed-out URL check after deployment;
- existing production smoke tests.

## Release sequence

1. Implement only on `agent/public-site-conversion-v1`.
2. Keep the PR draft.
3. Return the exact head SHA and test evidence.
4. Verify no overlap with active ProofLock deployment work.
5. Deploy through the existing production workflow only after review.
6. Verify live root, service page, assets, canonical metadata, sitemap, robots, and signed-out behavior.
7. Save a dated deployment receipt.

Evidence before claims. Bounded light speed.
