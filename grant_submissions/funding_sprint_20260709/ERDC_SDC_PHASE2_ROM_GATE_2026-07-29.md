# ERDC SDC Phase II ROM Gate - 2026-07-29

This public-safe gate converts the remaining estimated-price blocker into a private, auditable workflow without publishing any rate or dollar amount.

## Decision

- Status: `PRIVATE_ROM_INPUT_NOT_CAPTURED`
- Submission ready: `false`
- Safest operational deadline: `4:00 PM CT on August 7, 2026`
- Original CSO PDF deadline text: `1700 EST, 07 AUG 2026`
- Current live page deadline text: `4:00 PM CT on August 7, 2026`
- Scope: `PHASE_II_PROTOTYPE_DEVELOPMENT_ONLY`
- Proposed period: `16` weeks
- Funding currently available: `false`
- Private input present: `false`
- Private target git-ignored: `true`
- Private values exposed: `false`
- Arithmetic checked: `false`
- Candidate matches formula: `false`
- Candidate price value exposed: `false`
- Founder approved: `false`
- ROM ready for private PDF insertion: `false`
- Session-browser navigation performed: `false`
- Gate SHA-256: `ccb61bf97433d44f48dcc3b98b9e4513cb51c2de180decb96f896434fa2576c2`

## Formula

candidate price = round_to_increment(((direct labor + fringe + indirect + other direct costs) * (1 + FFP risk reserve rate)) * (1 + profit rate))

## Unresolved Gates

- `PRIVATE_INPUT_CAPTURE`
- `DIRECT_RATE_SUPPORT`
- `INDIRECT_TREATMENT`
- `OTHER_DIRECT_COST_ITEMIZATION`
- `NO_UNCOMMITTED_SUBCONTRACTOR_COSTS`
- `FOUNDER_CANDIDATE_PRICE_APPROVAL`
- `PRIVATE_PDF_INSERTION`
- `SAM_ALL_AWARDS_IDENTITY_ADDRESS_AND_CONTRACT_STATUS_MATCH`
- `CURRENT_PROPOSAL_CONTACT_EMAIL`
- `SUBMITTABLE_ACCOUNT_AND_COMPLETE_FORM_ACCESS`
- `PORTAL_PREVIEW_TERMS_AND_FINAL_CONFIRMATION`

## Private Workflow

1. Copy `config/erdc_sdc_phase2_rom_private_template_v1.json` to the ignored private input path.
2. Replace every placeholder with a supported cost basis and one candidate price.
3. Invoke this builder explicitly with `--private-input`; its public output contains only gates, counts, and hashes.
4. Insert the approved amount only into the private ERDC PDF after the cost basis and founder-approval gates pass.
5. Separately verify the SAM legal identity, matching address, contract registration, portal fields, terms, and final confirmation.

## Official Source Integrity

- `grant_submissions/funding_sprint_20260709/source_attachments/W912HZ26SC005/CSO_HPCMP_SDC_30April2026_FINAL.pdf`: hash=`true` bytes=`true`
- `grant_submissions/funding_sprint_20260709/source_attachments/W912HZ26SC005/HPCMP_SDC_FAQ_20Jul2026.pdf`: hash=`true` bytes=`true`

## Claim Boundary

This public gate proves only that the private Phase II pricing workflow is structurally available and, when explicitly invoked, can verify arithmetic and approval flags without publishing private rates or dollar amounts. It is not a quote, certified accounting record, proposal submission, contract, award, Government price determination, SAM verification, or authorization to accept terms. Phase III and Phase IV costs are excluded.
