# Live Funding Portal Handoff - 2026-07-29

This handoff is generated from the authoritative near-deadline command board. It contains no private contact data or credentials.

## Browser Control

- Status: `SESSION_BROWSER_RESERVED_FOR_USER_AUTHENTICATION`
- Scope: `CURRENT_CODEX_SESSION_IN_APP_BROWSER_ONLY`
- Resume signal: `I'm in`
- Navigation before resume signal: `false`
- Inspect current page before navigation: `true`
- First action after resume: Inspect the current URL and visible page without navigating. If the page is a submitted or closed lane, do not edit it; otherwise continue only to the next non-mutating preview before switching lanes.
- Source command-board SHA-256: `759f3635312f7c95436ca95e4fab130cbf04bf99fe454cd82c378e07f0cb1322`
- Handoff SHA-256: `e8d72de9b03defea80ba07106ce3df9d0ebfab5daa4eac064ac8f91e3f128c6c`

## Portal Queue

### 1. NASHVILLE-EC-FALL-2026 - Nashville Entrepreneur Center Fall 2026 Accelerators

- Command: `FOUNDER_ONBOARDING_ACTION_DUE`
- Deadline: Onboarding form and participation agreement due July 31, 2026; the official message does not state a time or timezone. The separate founder-controlled deposit date is August 14, 2026.
- Portal: https://ec.co/apply/
- Package files present: `true` (13/13)
- Package receipts:
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_FALL_2026_PORTAL_FIELD_MAP_2026-07-16.md` | exists=`true` | bytes=`12886` | sha256=`63bdfafebade22432a6d1ffc3509c8c5ee1685270144f12cc8124ae483bca017`
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_FALL_2026_APPLICATION_MANIFEST_2026-07-16.json` | exists=`true` | bytes=`18360` | sha256=`cd9501d1a61e248a62329595297592d00593bf0086c87da58e120df43de2ef11`
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json` | exists=`true` | bytes=`8597` | sha256=`998a267a08df9e8923fab1e57740f00f52270228a49417f40da73af4aa6d4d33`
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.md` | exists=`true` | bytes=`3671` | sha256=`c5905b7689a5643ca1ce6b793cbabd0d73166dab0b94545e100b615cae5ba16d`
  - `code/ops/CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py` | exists=`true` | bytes=`11024` | sha256=`379a150cc558d9a37ed53d8c48c291275c3a04241cb91f164377e309a5e9d165`
  - `code/ops/VALIDATE_NASHVILLE_EC_PRIVATE_FACTS.py` | exists=`true` | bytes=`10016` | sha256=`5974911c2892291f7cebb67663977af264d00e2bf1d1157476dd9ccfe0b08004`
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_PRIVATE_FACT_CAPTURE_WORKFLOW_2026-07-17.md` | exists=`true` | bytes=`2256` | sha256=`fad93e7ed7c93a1406657d5d678a3673cfd73ed29fe4de5205e223e948ea9d88`
  - `grant_submissions/funding_sprint_20260709/NASHVILLE_EC_DEADLINE_PRESERVATION_ENGAGEMENT_RECEIPT_2026-07-17.json` | exists=`true` | bytes=`1801` | sha256=`42fc996c7ebcdce4027cca5397347195d5b8fe74c90e75efd114bd8265dc20b5`
  - `grant_submissions/funding_sprint_20260709/NASHVILLE_EC_DEADLINE_PRESERVATION_RESPONSE_CONTROL_2026-07-17.md` | exists=`true` | bytes=`2610` | sha256=`81225b12c7b8b7e614a0fd50d559bce076e2142e0535e06ea15deb01fe1a9c93`
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_OFFICIAL_DEADLINE_CONFIRMATION_2026-07-17.json` | exists=`true` | bytes=`2272` | sha256=`dac4b3120d9b4ec2a822198426939b89fe96bf7294c0cc251d1a299bb76b00e2`
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_SUBMISSION_RECEIPT_2026-07-17.json` | exists=`true` | bytes=`1347` | sha256=`e606530b0ccbab06347bef60de527b4a76e5ee35bd7a15e71c3a0b49647be505`
  - `grant_submissions/funding_sprint_20260709/OFFICIAL_INBOUND_STATUS_EVENT_REGISTER_2026-07-25.json` | exists=`true` | bytes=`23069` | sha256=`320e8a6351c27a0a395dacde7bbc1fe32d1aceeb8e8a7596c77aeca485f39a6a`
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_TAKEOFF_ONBOARDING_REVIEW_PACKET_2026-07-29.md` | exists=`true` | bytes=`10778` | sha256=`0d50623f0cec857212508b30ebda5e5b7c81384979f2a8f02130ce1099d3978c`
- Next safe action:
  - Review the Takeoff onboarding packet against the current signed-in onboarding form and participation agreement.
  - Verify the attendance commitments, agreement terms, exact cutoff, and any requested private facts without accepting or submitting them.
  - Reach only the complete onboarding review screen; stop before agreement acceptance, signature, attestation, payment, or final confirmation.
  - Finish founder review before July 31 because the official message does not state a cutoff time or timezone.
- Action gate:
  - Status: `COHORT_SELECTED_ONBOARDING_AND_PARTICIPATION_AGREEMENT_DUE`
  - Passed: `0/3`
  - Open: `3`
  - Private input present: `false`
  - Private values exposed: `false`
  - Ready for human click: `false`
- Stop conditions:
  - Any participation-agreement acceptance, signature, attestation, deposit, fee payment, or final onboarding confirmation.
  - Any answer that conflicts with the founder-reviewed onboarding packet or current official message.
- Human gates:
  - Robert verifies every onboarding answer and attendance commitment.
  - Robert reviews and accepts the participation agreement only after legal and founder review.
  - Robert separately approves any deposit or remaining financial commitment before August 14.
- External send without human: `false`
- Final submit without human: `false`
- Source lane SHA-256: `4ac68b158cbdb78cf0a0081e9e42d192aba24ec87663277ed520a1b04ab0826d`

### 5. 26-510 - NSF Small Business Innovation Research / Small Business Technology Transfer Programs Phase I

- Command: `STAGE_PROJECT_PITCH`
- Deadline: Project Pitch is rolling with no standalone calendar deadline. The next listed full-proposal deadline is November 4, 2026 at 5:00 PM in the submitting organization's local time, and an official invitation is required.
- Portal: https://seedfund.nsf.gov/apply/project-pitch/
- Package files present: `true` (9/9)
- Package receipts:
  - `grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PORTAL_FIELDS_2026-07-29.md` | exists=`true` | bytes=`12752` | sha256=`1bc1b5507030e2032d071d6c375795a6c4327167c3d93c57da67ddbed623eafa`
  - `grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PASTE_CHECK_2026-07-29.md` | exists=`true` | bytes=`1600` | sha256=`4aa3aaddfb806d6dab37e55f06c262cc80a1fc9d1fb49b8675eb99a4986ccaab`
  - `grant_submissions/NSF_Project_Pitch/NSF_PROJECT_PITCH_ROUTING_MANIFEST_2026-07-29.json` | exists=`true` | bytes=`3730` | sha256=`c0ef3e533b0a41f23a2e55e35d11886900706898494a3936d5ad3eba1608f5ab`
  - `grant_submissions/NSF_Project_Pitch/NSF_PROJECT_PITCH_SOURCE_AUDIT_2026-07-29.json` | exists=`true` | bytes=`2218` | sha256=`830f7652a5ba4c1c360c27034311a5e6e37a3552877b23d797290882a05fe7b3`
  - `grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_READINESS_2026-07-29.md` | exists=`true` | bytes=`1867` | sha256=`f63fdd2ad6e5b734ca62040670bde1ee694fb57c2e902749fd4bc5ed2e2ba2a6`
  - `out/ops/source_native_family_baseline_ledger_latest.json` | exists=`true` | bytes=`2244585` | sha256=`627d0add4d31514f7a47dbf8e8c51b0fa46df72635f336133f54abb85b00927a`
  - `out/ops/market_signal_source_native_benchmark_manifest_latest.json` | exists=`true` | bytes=`4503` | sha256=`b3edaa016b20971b8ebca1bca5fa23c171f9ade9e6f02b823676443129529568`
  - `out/ops/source_native_research_whitepaper_manifest_latest.json` | exists=`true` | bytes=`18044` | sha256=`bc7b2c7f1eabef62f227861abda14e88eab4f2a1bc8f4dbfac52e58a3224a6cb`
  - `grant_submissions/funding_sprint_20260709/CURRENT_OFFICIAL_OPPORTUNITY_RECHECK_2026-07-29.json` | exists=`true` | bytes=`7051` | sha256=`0c77c497790fa2b23fa83bab86ef1d52c3608580fc871474555fb35fc4633a2c`
- Next safe action:
  - Confirm whether a Project Pitch, invitation, or proposal is already pending.
  - If no pitch is pending, populate the four claim-bounded Project Pitch fields and reach final review.
- Stop conditions:
  - Any full-proposal workspace without a verified NSF invitation.
  - Legal-company, PI-eligibility, certification, or final Project Pitch submission.
- Human gates:
  - Robert confirms the legal company profile, PI eligibility, and portal status.
  - Robert reviews the final portal preview and approves the Project Pitch submission.
- External send without human: `false`
- Final submit without human: `false`
- Source lane SHA-256: `5a7694229affe8037bade5bda056c0ae182ad33b8e7473ec478a5506f00bacd5`

### 6. W912HZ26SC005 - Sovereign Defense Cloud for High-Performance Computing Commercial Solutions Opening

- Command: `STAGE_CONCEPT_PAPER`
- Deadline: 2026-08-07 4:00 PM CT
- Portal: https://www.erdcwerx.org/sovereign-defense-cloud-for-high-performance-computing/
- Package files present: `true` (6/6)
- Package receipts:
  - `output/pdf/LumenCore_ERDC_SDC_Solution_Brief_PUBLIC_DRAFT_2026-07-29.pdf` | exists=`true` | bytes=`108736` | sha256=`f1135e0ce4564335d3d5fcc2a7ec2aa8c20e435e9a9bcae815a2619023ab0690`
  - `grant_submissions/funding_sprint_20260709/ERDC_SDC_SOLUTION_BRIEF_COMPLIANCE_GATE_2026-07-29.json` | exists=`true` | bytes=`19379` | sha256=`11fdbfec9044a8a5f23496dd9c3a642942c3ea83622b2e1d4c2ee31601d28389`
  - `grant_submissions/funding_sprint_20260709/ERDC_SDC_PHASE2_ROM_GATE_2026-07-29.json` | exists=`true` | bytes=`4009` | sha256=`f34f3d952246d090ff28ef278c0416c81b81816484c57b26659782a6c16ecf48`
  - `grant_submissions/funding_sprint_20260709/ERDC_SDC_PHASE2_ROM_APPROVAL_WORKFLOW_2026-07-29.md` | exists=`true` | bytes=`2986` | sha256=`dc3d7da63ab2d0c6ea42524a3f28168acf12569c9b8c13c14fe417c4b773e7f7`
  - `grant_submissions/funding_sprint_20260709/source_attachments/W912HZ26SC005/SOURCE_MANIFEST_2026-07-29.json` | exists=`true` | bytes=`1804` | sha256=`44a7d65cd214d97d691ecc66b3e731588fbac9cb6c22e0e4b2d221c337af56ce`
  - `grant_submissions/funding_sprint_20260709/CURRENT_OFFICIAL_OPPORTUNITY_RECHECK_2026-07-29.json` | exists=`true` | bytes=`7051` | sha256=`0c77c497790fa2b23fa83bab86ef1d52c3608580fc871474555fb35fc4633a2c`
- Next safe action:
  - Verify the live ERDCWERX questions, amendments, organization match, and current funding posture.
  - Finalize the current public draft privately only after the Phase II ROM, SAM identity, contact email, and portal terms are approved.
- Stop conditions:
  - Any private price, rate, SAM legal fact, terms acceptance, certification, or final portal submission.
  - Any representation that funding is currently available when the controlling source says it is not.
- Human gates:
  - Robert approves the supported Phase II-only candidate price and timestamp.
  - Robert verifies active SAM all-awards contract registration and exact legal entity and address match.
  - Robert signs in to Submittable and reviews the complete current form.
  - Robert reviews the private final PDF, portal answers, terms, and final confirmation.
- External send without human: `false`
- Final submit without human: `false`
- Source lane SHA-256: `39bf6524f28e45dafe4e01bbc01b0713842fe1cc0407ff18ba16b98878fa3748`

### 7. LAUNCHTN-3686-2026 - 3686 Pitch Competition 2026, presented by Amazon

- Command: `STAGE_APPLICATION`
- Deadline: 2026-08-13 11:59 PM CDT
- Portal: https://airtable.com/app6GRZNbU72OmaK1/pagudvfO1hH7SmzBl/form
- Package files present: `true` (6/6)
- Package receipts:
  - `grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_PORTAL_FIELD_MAP_2026-07-29.md` | exists=`true` | bytes=`20203` | sha256=`d547c1cd3b5bf1ecc89f4b6e7d781ffbdb835536e1901745cb80fa68a5c192ee`
  - `grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_APPLICATION_MANIFEST_2026-07-29.json` | exists=`true` | bytes=`25856` | sha256=`9669a06d9b2283bba31a06c6ba05696ce5dee2b6ca20ad8b279903faab21ab42`
  - `grant_submissions/LAUNCHTN_3686_PITCH_2026/LUMENCORE_3686_PITCH_DECK_2026-07-29_REVIEW_REQUIRED.pptx` | exists=`true` | bytes=`356729` | sha256=`f0edebdbcf0c29457b01a40a9d7238a441797e024d72404815f08f2191a23b3a`
  - `grant_submissions/LAUNCHTN_3686_PITCH_2026/LUMENCORE_3686_FINANCIAL_MODEL_2026-07-17.xlsx` | exists=`true` | bytes=`16166` | sha256=`9da46f8ad94fc53ef561ee33dcfa6df907897caeadf6afbd08fb113fc6887d94`
  - `grant_submissions/funding_sprint_20260709/CURRENT_OFFICIAL_OPPORTUNITY_RECHECK_2026-07-29.json` | exists=`true` | bytes=`7051` | sha256=`0c77c497790fa2b23fa83bab86ef1d52c3608580fc871474555fb35fc4633a2c`
  - `grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_APPLICATION_REFRESH_2026-07-29.md` | exists=`true` | bytes=`2795` | sha256=`b22968d2ff708d0880370f28af9397fa46154efe099001a578dc48483754e70e`
- Next safe action:
  - Confirm the founder-controlled legal, Tennessee, employment, and funding-history facts.
  - Build and inspect the LaunchTN-specific deck; approve or replace every financial-model assumption.
  - Recheck the live field schema, file limits, terms, and attestations. No upload set is currently approved.
- Stop conditions:
  - Any unsupported eligibility, pricing, funding, legal, or employment answer.
  - Any attachment upload before the manifest reports a nonempty safe upload set.
  - Terms acceptance, attestation, or final submission.
- Human gates:
  - Robert enters private contact and address facts only inside the authenticated portal.
  - Robert verifies the legal entity, formation year, employee count, Tennessee eligibility, and prior LaunchTN capital history.
  - Robert approves the pricing, funding assumptions, attachments, and final portal preview before submission.
- External send without human: `false`
- Final submit without human: `false`
- Source lane SHA-256: `f9e473317a40a9b943d7f1846e426f93afcf6a7bd014d354842384bcdfcb27a2`

## Closed Lanes - No Portal Action

### DLA26BZ03-NV011 - Digital Twin of the Organization for Enhanced Mission Readiness

- Status: `EXPIRED_WITHOUT_VERIFIED_SUBMISSION_NO_PORTAL_ACTION`
- Command: `EXPIRED_NO_SUBMISSION`
- Deadline: July 22, 2026 at 12:00 p.m. Eastern Time (expired).
- Safest next action: Preserve the package and gate receipts as historical evidence. Do not reopen DSIP, edit volumes, certify, or submit.
- External send without human: `false`
- Final submit without human: `false`
- Source lane SHA-256: `4d10b4b6f1181db4cbc0de612c3078bda9db57a47fbca3ee7eeccf107c4f7bea`

## Account Maintenance

### 3. USPTO Patent Center

- Status: `PAYMENT_ACKNOWLEDGEMENT_ONLY_OFFICIAL_DOCKET_REQUIRED`
- Portal: https://patentcenter.uspto.gov/
- Next safe action: Download the six required official docket categories into the ignored private capture folders, then run the redacted completeness check.
- Stop conditions:
  - Do not infer the user-reported July 25 date from a payment acknowledgement.
  - Do not file, pay, sign, certify, or publish unpublished docket material.

### 4. SAM.gov public API credential rotation

- Status: `ROTATION_OVERDUE_REPLACEMENT_NOT_DETECTED`
- Portal: https://sam.gov/profile/details
- Next safe action: Reveal the replacement only inside SAM.gov, paste it only into the guarded hidden-input installer, and require changed-fingerprint plus live authenticated verification.
- Stop conditions:
  - Do not paste, log, publish, commit, mirror, or display the credential.
  - Do not describe entity registration as defective merely because key rotation is overdue.

## Monitor Only

- NASA, Army, and CDC responses are sent and receipt-backed; do not duplicate-send.
- FHWA replied to the replacement route and referred the request to the subject matter expert leading its response; the bounded acknowledgment is sent. Monitor for scheduling, do not reuse the rejected address or follow up before the recorded control date, and do not claim a fit check or partner.
- DOJ/BOP remains partner-only; do not send a solo quote.
- EPRI administrative onboarding was sent; monitor for a substantive response without claiming membership or endorsement.
- LANL follow-up was sent; monitor without duplicate transmission.

## Global Stops

- Any final submit, external send, signature, legal certification, pricing approval, fee payment, terms acceptance, or irreversible confirmation.
- Do not make unsupported claims of agency validation, award, customer deployment, realized savings, patent validity, field performance, CMMC status, or ITAR compliance.
- Any request to expose credentials, private identifiers, unpublished patent material, controlled technical data, or private cost rates in a public artifact.

- Private contact data included: `false`
- Credentials included: `false`
- Browser navigation performed: `false`
- External action performed: `false`
- Final submit without human: `false`
