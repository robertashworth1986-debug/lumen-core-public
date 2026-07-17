# MissionWeave DSIP Assembly Map

Updated: July 16, 2026  
Topic: DLA26BZ03-NV011, Digital Twin of the Organization for Enhanced Mission Readiness  
Close: July 22, 2026 at 12:00 p.m. Eastern Time  
Portal: Defense SBIR/STTR Innovation Portal (DSIP)  
Current decision: assemble and quality-assure the full package; do not certify or submit until the action-time gates below are resolved.

## Controlling Sources

| Source | Local copy | SHA-256 |
|---|---|---|
| DoW 2026 SBIR BAA Release 3, Amendment 2 | `source_attachments/DoW_2026_SBIR_BAA_RELEASE_3_AMENDMENT_2.pdf` | `FB809186F3B43313A1877A5C36E2383A45B84F62566DDA3F6BCDB93779CE08AE` |
| DLA 26.BZ Release 3 Component Instructions, Version 2 | `source_attachments/DLA_26BZ_RELEASE_3_COMPONENT_INSTRUCTIONS.pdf` | `17B06B6FE3DBE6F2035F8287A0DD01FDBFE180858F3C490F1E91D121819239A2` |
| Official DSIP topic record | `source_attachments/DLA26BZ03_NV011_OFFICIAL_TOPIC_DETAILS.json` | `4D01354A456BF91BAFF5AB638311BD5822176B49AD7911F6DEC1C379B3B217B7` |

The official topic record controls the 12-month/$100,000 ceiling, Phase I objectives, ITAR flag, projected CMMC Level 2 (Self), and TRL/MRL 3-6 range. The current package proposes a bounded six-month, $100,000 effort.

## Portal Volume Map

| DSIP volume | Package artifact or portal action | State before certification |
|---|---|---|
| Volume 1: Proposal Cover Sheet | Enter organization, PI, corporate official, identifiers, ownership, and public abstract/benefits in DSIP. Use `MISSIONWEAVE_DSIP_VOLUME1_PUBLIC_TEXT_2026-07-16.md`. | Candidate text ready; identity and representation fields require live verification. |
| Volume 2: Technical Volume | Upload the single PDF rendered from `MISSIONWEAVE_DSIP_VOLUME2_FINAL_CANDIDATE_2026-07-16.docx`. | Candidate must pass page, layout, claim, and hash gates. |
| Volume 3: Cost Volume | Enter costs in the DSIP Excel/form using `MISSIONWEAVE_DSIP_VOLUME3_COST_INPUTS_2026-07-16.md`. | $100,000 arithmetic ready; rates and indirect treatment require corporate-official certification. |
| Volume 4: Company Commercialization Report | Select NO if there are no prior SBIR/STTR awards; otherwise complete the CCR. | Must be answered from award history at action time. |
| Volume 5: Supporting Documents | Use `MISSIONWEAVE_DSIP_VOLUME5_WORKSHEET_2026-07-16.md`. Upload only documents that are current and factually supported. | Export-control/JCP evidence and rights assertions are unresolved gates. |
| Volume 6: Fraud, Waste, and Abuse Training | Complete the annual training/certification in DSIP. | Portal action required. |
| Volume 7: Foreign Affiliations | Complete the current DSIP webform. Do not substitute an older PDF in Volume 5. | Portal action and corporate-official certification required. |

## Volume 2 Requirements Locked Into The Candidate

- One searchable PDF, no more than 20 pages.
- US Letter, portrait, one-inch margins, single column, minimum 10-point type, single-spaced.
- Page numbers and a running header containing applicant, topic, and DSIP proposal-number status.
- Required section order: Identification and Significance; Phase I Technical Objectives; Phase I Statement of Work; Related Work; Relationship with Future R/R&D; Commercialization Strategy; Key Personnel; Foreign Citizens; Facilities/Equipment; Subcontractors/Consultants; Prior/Current/Pending Support; Technical Data/Software Rights Assertions.
- Proposal-contained evidence only; reviewers are not assumed to know the firm, personnel, repository, or prior experiments.
- DLA benefit is addressed throughout the technical, personnel, and commercialization sections.
- Generated-workflow evidence is labeled synthetic and bounded. Negative seeds and poor combined-stress absolute performance are preserved.

## DLA-Specific Gates

1. Confirm the DSIP-generated proposal number and replace the neutral header phrase only through the builder argument.
2. Confirm SAM registration, legal business name, UEI, CAGE, address, EIN/TIN, ownership, and submitter authority in the live portals. Do not store those sensitive values in the public repository.
3. Confirm PI primary-employment eligibility at award and the proposed 640 Phase I labor hours.
4. Confirm the all-prime direct labor rate, fringe, indirect basis, travel need, and other direct costs. The package does not use an uncommitted consultant or subcontractor.
5. Complete Volume 4 from the actual SBIR/STTR award history.
6. Because the topic is marked ITAR, verify current JCP/DD Form 2345 status or acceptable evidence of application, determine whether a Technology Control Plan is required, and do not upload or expose controlled technical data in an unapproved environment.
7. Treat projected CMMC Level 2 (Self) as a pre-award/negotiation requirement. The applicant is not represented as assessed, certified, or operating an accredited CUI enclave.
8. Confirm that no foreign citizens will participate; if that changes, disclose each person and scope exactly as DSIP requires.
9. Review prior/current/pending support for overlap with DICE, HarborSentinel, FALCON, and any other submitted or planned effort. Disclose overlap and avoid duplicate costs or deliverables.
10. Finalize the technical-data/software-rights assertion table with qualified legal review. Do not claim a patent, registration, or rights position that is not documented.
11. Complete FWA training, foreign-affiliation disclosure, all certifications, the portal preview, and the final action-time submission approval.

## Optional Items

- Letter of support: upload only if a relevant procuring organization working with DLA provides a signed, noncontingent letter.
- TABA: do not request in this package without a named provider, contact information, hours, rates, and a topic-specific rationale.
- Oral presentation: if invited, prepare no more than 15 slides for a 15-minute presentation plus 15 minutes of questions. DLA evaluates both the technical criteria and business acumen/customer-engagement capability on a Go/No-Go basis.

## Final Assembly Sequence

1. Re-run `build_missionweave_dsip_volume2_candidate.py` with the final DSIP proposal number.
2. Run the focused package tests and document structure audits.
3. Render the DOCX to PDF and inspect every page image at 100 percent.
4. Confirm the PDF is searchable and at or below 20 pages.
5. Generate the package manifest and verify every listed SHA-256 digest.
6. Mirror the exact package to `E:\LumaProofVault\SUBMISSIONS\MISSIONWEAVE_DLA26BZ03_NV011_20260716` and verify source/destination hashes.
7. Populate DSIP volumes, save drafts, and inspect the portal preview.
8. Ask Robert for action-time confirmation only after all representations, attachments, and totals are visible in the final preview.
