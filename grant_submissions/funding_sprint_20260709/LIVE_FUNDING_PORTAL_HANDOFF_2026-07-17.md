# Live Funding Portal Handoff - 2026-07-17

This handoff is generated from the authoritative near-deadline command board. It contains no private contact data or credentials.

## Browser Control

- Status: `SESSION_BROWSER_RESERVED_FOR_USER_AUTHENTICATION`
- Scope: `CURRENT_CODEX_SESSION_IN_APP_BROWSER_ONLY`
- Resume signal: `I'm in`
- Navigation before resume signal: `false`
- Inspect current page before navigation: `true`
- First action after resume: Inspect the current URL and visible page without navigating. Continue the current authenticated portal to its next safe preview before switching lanes.
- Source command-board SHA-256: `53d1bcfa6cee5477fc52fdb10355d890241b72811ea677352d0b6c3d9f58976f`
- Handoff SHA-256: `e74af2dcb3ed89f8d7652f94cdd6ded599e59d7f4b13caf20abeaa4ea586e5a8`

## Portal Queue

### 1. NASHVILLE-EC-FALL-2026 - Nashville Entrepreneur Center Fall 2026 Accelerators

- Command: `STAGE_APPLICATION`
- Deadline: Applications close July 17, 2026; the official page does not list a closing time
- Portal: https://ec.co/apply/
- Next safe action:
  - If this is the current signed-in page, inspect the visible application state before navigating anywhere.
  - Run `python code/ops/CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py` and answer the six hidden prompts; require the ignored 11-answer fill map to validate without publishing values.
  - Populate only the supported answers from that private map and reach the complete preview.
  - Monitor the one deadline-support thread for the exact close time; do not resend it and do not treat it as an application.
- Action gate:
  - Status: `READY_FOR_HIDDEN_FOUNDER_INPUT`
  - Passed: `0/15`
  - Open: `15`
  - Private input present: `false`
  - Private values exposed: `false`
  - Ready for human click: `false`
- Deadline-support email:
  - Status: `DEADLINE_PRESERVATION_QUERY_SENT_RESPONSE_PENDING`
  - Sent UTC: `2026-07-17T12:05:34Z`
  - Do not duplicate: `true`
  - Email is application: `false`
- Stop conditions:
  - Any fee payment, financial-aid agreement, program terms, cohort acceptance, attestation, or final submission.
  - Any portal answer that conflicts with the founder-confirmation artifact.
- Human gates:
  - Robert answers all six prompts covering founder status, weekly hours, conversation count, revenue, founder investment, received funding, and business debt.
  - Robert reviews the final portal preview and approves submission before the July 17 close.
  - Any later program fee, financial-aid arrangement, terms, or cohort acceptance requires a separate decision.
- External send without human: `false`
- Final submit without human: `false`
- Source lane SHA-256: `85c856fe6e0262c19ef672fec63fe79d087454e510f51d5b8e417c3cde925de0`

### 2. DLA26BZ03-NV011 - Digital Twin of the Organization for Enhanced Mission Readiness

- Command: `STAGE_DSIP_PROPOSAL`
- Deadline: July 22, 2026 at 12:00 p.m. Eastern Time. The SBIR.gov topic record and DLA Release 3 schedule agree on July 22, 2026; the downloaded Amendment 2 BAA schedule line prints July 22, 2025, an apparent internal year typo. Reconfirm the live DSIP countdown before submission.
- Portal: https://www.dodsbirsttr.mil/
- Next safe action:
  - Verify the live DSIP countdown, organization linkage, and generated proposal number.
  - Use the proposal number through the existing builder, rerender Volume 2, regenerate the 15-file manifest, and require all hashes to pass.
  - Run the hidden sectioned MissionWeave collector for identity, proposal, and compliance; it accepts no Firm PIN or credential and keeps action-time approval separate.
  - Use the generated seven-volume checklist and require the public gate to move from 0/50 to 50/50 without exposing values.
  - Populate Volumes 1-7 from the bounded package and reach the complete preview.
- Action gate:
  - Status: `PRIVATE_DSIP_FACTS_NOT_CAPTURED`
  - Passed: `0/50`
  - Open: `50`
  - Private input present: `false`
  - Private values exposed: `false`
  - Ready for human click: `false`
- Stop conditions:
  - Any unsupported legal-entity, SAM, UEI, CAGE, PI-employment, cost, award-history, ITAR/JCP, CMMC, foreign-affiliation, foreign-citizen, data-rights, or support-overlap representation.
  - Fraud, Waste, and Abuse training certification, signature, attestation, or final DSIP submission.
  - A live DSIP deadline that conflicts with the cross-source July 22, 2026 record.
- Human gates:
  - Robert verifies the DSIP organization, submitter authority, legal entity, UEI, CAGE, SAM status, address, and proposal number.
  - Robert confirms PI primary-employment eligibility, 640 Phase I hours, six-month scope, and no conflicting support.
  - Robert approves direct labor, fringe, indirect treatment, ODCs, and the $100,000 total cost basis.
  - Robert answers prior SBIR/STTR award history, ITAR/JCP, CMMC, foreign-citizen, foreign-affiliation, and technical-data-rights fields from current facts.
  - Robert completes required training and reviews every certification, attachment hash, total, and the final DSIP preview before submission.
- External send without human: `false`
- Final submit without human: `false`
- Source lane SHA-256: `9400ce8c52fd7cf953cf442b24ce339878b3bc51914962e14364bd01cce84431`

### 5. 26-510 - NSF Small Business Innovation Research / Small Business Technology Transfer Programs Phase I

- Command: `STAGE_PROJECT_PITCH`
- Deadline: NSF 26-510 lists July 27 and November 4, 2026, then March 4 and July 7, 2027, as full-proposal deadlines. July 27 is not currently reachable because no official Project Pitch invitation was verified; November 4 is planning only.
- Portal: https://seedfund.nsf.gov/project-pitch/
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
- Source lane SHA-256: `2beaf7a1e23f964c1bec761a476894163c81fb65f37d03ff7c324d9f24dfd511`

### 6. W912HZ26SC005 - Sovereign Defense Cloud for High-Performance Computing Commercial Solutions Opening

- Command: `STAGE_CONCEPT_PAPER`
- Deadline: August 7, 2026 at 4:00 PM Central Time
- Portal: https://www.erdcwerx.org/sovereign-defense-cloud-for-high-performance-computing/
- Next safe action:
  - Verify the live ERDCWERX questions, amendments, organization match, and current funding posture.
  - Use the QA-passed technical PDF only after a private Phase II ROM is approved and inserted without entering the public repository.
- Stop conditions:
  - Any private price, rate, SAM legal fact, terms acceptance, certification, or final portal submission.
  - Any representation that funding is currently available when the controlling source says it is not.
- Human gates:
  - Robert approves the supported Phase II-only candidate price and timestamp.
  - Robert verifies active SAM contract registration and exact legal entity and address match.
  - Robert reviews the private final PDF, portal answers, terms, and final confirmation.
- External send without human: `false`
- Final submit without human: `false`
- Source lane SHA-256: `83ac243de09311582c4dbdaafb5409c4da215b82cb7253689265052b3fec29c4`

### 7. LAUNCHTN-3686-2026 - 3686 Pitch Competition 2026, presented by Amazon

- Command: `STAGE_APPLICATION`
- Deadline: August 13, 2026 at 11:59 PM Central Daylight Time
- Portal: https://airtable.com/app6GRZNbU72OmaK1/pagudvfO1hH7SmzBl/form
- Next safe action:
  - Confirm the founder-controlled legal, Tennessee, employment, funding-history, pricing, and raise facts.
  - Upload only the two hash-verified QA-passed attachments and reach the complete preview.
- Stop conditions:
  - Any unsupported eligibility, pricing, funding, legal, or employment answer.
  - Terms acceptance, attestation, or final submission.
- Human gates:
  - Robert enters private contact and address facts only inside the authenticated portal.
  - Robert verifies the legal entity, formation year, employee count, Tennessee eligibility, and prior LaunchTN capital history.
  - Robert approves the pricing, funding assumptions, attachments, and final portal preview before submission.
- External send without human: `false`
- Final submit without human: `false`
- Source lane SHA-256: `76b5cc624247f272e469c46695bead2624dcca331b95cce013c5ee91964e6ad9`

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
- FHWA has one active replacement outreach pending after the first listed route rejected delivery; do not reuse the rejected address, follow up before the recorded control date, or claim delivery or a partner.
- DOJ/BOP remains partner-only; do not send a solo quote.
- EPRI administrative onboarding was sent; monitor for a substantive response without claiming membership or endorsement.
- LANL follow-up was sent; monitor without duplicate transmission.

## Global Stops

- Any final submit, external send, signature, legal certification, pricing approval, fee payment, terms acceptance, or irreversible confirmation.
- Any unsupported claim of agency validation, award, customer deployment, realized savings, patent validity, field performance, CMMC status, or ITAR compliance.
- Any request to expose credentials, private identifiers, unpublished patent material, controlled technical data, or private cost rates in a public artifact.

- Private contact data included: `false`
- Credentials included: `false`
- Browser navigation performed: `false`
- External action performed: `false`
- Final submit without human: `false`
