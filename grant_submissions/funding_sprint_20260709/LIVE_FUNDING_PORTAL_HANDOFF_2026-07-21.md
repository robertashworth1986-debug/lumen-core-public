# Live Funding Portal Handoff - 2026-07-21

This handoff is generated from the authoritative near-deadline command board. It contains no private contact data or credentials.

## Browser Control

- Status: `SESSION_BROWSER_RESERVED_FOR_USER_AUTHENTICATION`
- Scope: `CURRENT_CODEX_SESSION_IN_APP_BROWSER_ONLY`
- Resume signal: `I'm in`
- Navigation before resume signal: `false`
- Inspect current page before navigation: `true`
- First action after resume: Inspect the current URL and visible page without navigating. Continue the current authenticated portal to its next safe preview before switching lanes.
- Source command-board SHA-256: `062e6577ab4d887e8fa03b5da818747ebd495ca271f0fb1f65d915144f7cf041`
- Handoff SHA-256: `7a2fa136a73bce1f5b87ae33cfa4f2e23b5e9933dea28fb463b14de7432d0f52`

## Portal Queue

### 1. NASHVILLE-EC-FALL-2026 - Nashville Entrepreneur Center Fall 2026 Accelerators

- Command: `SENT_VERIFIED`
- Deadline: The official Nashville Entrepreneur Center reply states that applications are open until 11:59 p.m. on July 17. The message does not name a timezone; America/Chicago is the explicit operational inference.
- Portal: https://ec.co/apply/
- Next safe action:
  - If this is the current signed-in page, inspect the visible application state before navigating anywhere.
  - Run `python code/ops/CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py` and answer the six hidden prompts; require the ignored 11-answer fill map to validate without publishing values.
  - Populate only the supported answers from that private map and reach the complete preview.
  - Use the confirmed 11:59 p.m. July 17 close as the outside bound and submit early; do not resend the deadline query and do not treat the support reply as an application.
- Action gate:
  - Status: `PORTAL_SUBMISSION_CONFIRMED`
  - Passed: `15/15`
  - Open: `0`
  - Private input present: `true`
  - Private values exposed: `false`
  - Ready for human click: `false`
- Deadline-support email:
  - Status: `OFFICIAL_SUPPORT_CONFIRMED_CLOSE_TIME_APPLICATION_NOT_SUBMITTED`
  - Sent UTC: `2026-07-17T12:05:34Z`
  - Do not duplicate: `true`
  - Email is application: `false`
  - Reply required: `false`
  - Timezone explicit in message: `false`
  - Operational timezone: `America/Chicago`
- Stop conditions:
  - Any fee payment, financial-aid agreement, program terms, cohort acceptance, attestation, or final submission.
  - Any portal answer that conflicts with the founder-confirmation artifact.
- Human gates:
- External send without human: `false`
- Final submit without human: `false`
- Source lane SHA-256: `e4ac50f0eb1f534eb16645905a4dc0541f013c7b1198d469340e24b813a27707`

### 2. DLA26BZ03-NV011 - Digital Twin of the Organization for Enhanced Mission Readiness

- Command: `STAGE_DSIP_PROPOSAL`
- Deadline: July 22, 2026 at 12:00 p.m. Eastern Time. The SBIR.gov topic record and DLA Release 3 schedule agree on July 22, 2026; the downloaded Amendment 2 BAA schedule line prints July 22, 2025, an apparent internal year typo. Reconfirm the live DSIP countdown before submission.
- Portal: https://www.dodsbirsttr.mil/
- Next safe action:
  - Verify the live DSIP countdown, organization linkage, and generated proposal number.
  - Capture the proposal number only in the ignored record, run the guarded private Volume 2 finalizer, and require its assigned-header PDF QA receipt without changing the public 15-file manifest, which remains neutral.
  - Run the hidden sectioned MissionWeave collector for identity, proposal, and compliance; it accepts no Firm PIN or credential and keeps action-time approval separate.
  - Use the generated seven-volume checklist and move the public gate beyond 37/50 by resolving only supported portal facts without exposing values.
  - Populate Volumes 1-7 from the bounded package and reach the complete preview.
- Action gate:
  - Status: `PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN`
  - Passed: `37/50`
  - Open: `13`
  - Private input present: `true`
  - Private values exposed: `false`
  - Ready for human click: `false`
- Stop conditions:
  - Any unsupported legal-entity, SAM, UEI, CAGE, PI-employment, cost, award-history, ITAR/JCP, CMMC, foreign-affiliation, foreign-citizen, data-rights, or support-overlap representation.
  - Fraud, Waste, and Abuse training certification, signature, attestation, or final DSIP submission.
  - A live DSIP deadline that conflicts with the cross-source July 22, 2026 record.
- Human gates:
  - The founder completes any portal certification or final JCP submit action.
  - The founder handles authentication and any secret value.
  - The founder confirms the factual cost basis; the builder checks arithmetic only.
  - No compliance, assessment, certification, or contracting-office acceptance is inferred.
  - Any legally consequential upload or representation remains founder reviewed.
  - The founder reviews the rendered Government portal preview.
  - The final certification and submit click are founder-only actions.
- External send without human: `false`
- Final submit without human: `false`
- Source lane SHA-256: `a20f3314ebf9fcb5a244a46f3224de073cd6cac25d349ed8f5e26b6f2b0c0e64`

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
- Source lane SHA-256: `c341a53c2bfd54212a930c834977c08940d6c9401e2c9f80c2296e69ee2a58a2`

### 6. W912HZ26SC005 - Sovereign Defense Cloud for High-Performance Computing Commercial Solutions Opening

- Command: `REVERIFY_SOURCE_BEFORE_STAGE`
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
- Source lane SHA-256: `ae71b50154975aedefc3d7545541026099969af4c81fb82201e267c5d39b05f4`

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
- Source lane SHA-256: `9e059c2f45e15688df024c46b62113ae8c3f224ee2d068d135df8f9921f8a1f8`

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
