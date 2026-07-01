# CMMC Level 2 Readiness Path

Updated: June 19, 2026

This is a planning checklist, not legal advice, an assessment, or a
certification representation.

## June 19 Official Source Verification

Current source check used the public SAM.gov registration page, Defense
SBIR/STTR funding-opportunity page, SPRS CMMC page, SPRS Level 2 Self-
Assessment Quick Entry Guide version 4.0, the SPRS Affirming Official
tutorial transcript, and 32 CFR part 170 references.

Practical implications:

- SAM.gov states that a prime applicant needs an active entity registration to
  bid on contracts or apply for federal assistance, that registration assigns
  the Unique Entity ID, and that active registrations must be renewed every
  365 days.
- SAM.gov also states registration can take up to 10 business days to become
  active, so SAM status should be checked before portal work, not on the due
  date.
- Defense SBIR/STTR states that DoD SBIR/STTR proposals must be submitted
  electronically through DSIP and that proposers should register early to avoid
  delays.
- SPRS states that it is the location for vendors to certify CMMC Level 1 and
  Level 2 compliance and for the defense acquisition community to review.
- The SPRS Level 2 Self-Assessment Quick Entry Guide says PIEE access with the
  `SPRS Cyber Vendor User` role is required to enter CMMC assessment
  information.
- The same guide says the Level 2 self-assessment entry includes scope,
  employee count, included CAGE codes, and CAGE hierarchy data imported from
  SAM; CAGEs cannot be added if they are not part of the company hierarchy.
- The guide identifies Level 2 Conditional Self-Assessment scores as 88-109,
  Final Self-Assessment as 110, conditional validity as 180 days, and final
  validity as three years with annual affirmations.
- The Affirming Official tutorial defines the AO as the senior representative
  responsible for ensuring the organization seeking assessment is compliant
  and authorized to affirm continuing compliance. The AO also needs PIEE/SPRS
  access to complete the affirmation.

Do not treat any of the above as proof that LumenCore currently has CMMC,
SPRS, PIEE, CAGE hierarchy, or AO status. These are required user-verified
facts.

## First Decision: What Status Does the Award Require?

Do not buy a CMMC Level 2 assessment before confirming the required status.
The solicitation or resulting contract identifies whether the relevant
information system needs:

- CMMC Level 1 (Self);
- CMMC Level 2 (Self); or
- CMMC Level 2 (C3PAO).

Level 2 (Self) and Level 2 (C3PAO) are different statuses. A self-assessment
does not satisfy a contract requiring a C3PAO certification assessment.

For DICE, the BAA states:

- TA1 and TA2 work is anticipated at the Unclassified level;
- procurement-contract awards are subject to CMMC;
- Level 1 applies to a procurement contract handling FCI only;
- Level 2 applies when CUI is handled, including CUI work under other award
  vehicles; and
- DARPA chooses the final award instrument.

The current abstract requests an OT for Research and proposes no CUI
processing. That reduces the immediate scope risk but does not bind DARPA or
eliminate later cybersecurity requirements.

## Recommended Architecture

Create a small, separate federal-work enclave rather than trying to certify
every personal and experimental system.

The enclave plan should:

1. Identify exactly where FCI or CUI enters, is processed, is stored, and
   leaves.
2. Keep public proposal drafting and public code outside the CUI boundary.
3. Use managed identity, multifactor authentication, device management,
   encryption, logging, backup, incident response, and controlled
   administration.
4. Use a cloud service processing CUI only if its offering is FedRAMP
   Moderate authorized or meets the applicable FedRAMP Moderate-equivalent
   requirements.
5. Document each cloud or external service provider in the System Security
   Plan and customer-responsibility matrix; connected on-premises systems and
   external services may become assessment scope.
6. Keep CUI out of personal iCloud, public GitHub, ordinary email, consumer
   collaboration tools, and general AI services unless the specific
   architecture and contract authorize them.

No current file should be relabeled CUI without an authorized source or
Government marking. The present grant drafts and synthetic benchmarks are
being handled as Unclassified, non-CUI material.

## Implementation Sequence

1. **Confirm entity and access**
   - Verify legal business name, active SAM.gov registration, UEI, CAGE if
     assigned, renewal/expiration date, and company hierarchy.
   - Confirm whether SAM activation is already complete; if not, allow for
     SAM.gov's stated activation timing before depending on DSIP or SPRS.
   - Verify PIEE access and obtain the `SPRS Cyber Vendor User` role.
   - Identify the company Affirming Official.
   - Confirm that the CAGE code(s) needed for the assessment appear in the
     SAM-imported company hierarchy before attempting SPRS entry.

2. **Freeze the assessment scope**
   - Inventory endpoints, identities, networks, repositories, cloud services,
     backups, external providers, and data flows.
   - Classify assets using the current CMMC Level 2 Scoping Guide.
   - Produce a network/data-flow diagram and scope statement.

3. **Build the System Security Plan**
   - Map the 110 Level 2 security requirements to implemented controls,
     responsible owners, systems, procedures, and evidence.
   - Maintain policies, configuration baselines, account records, logs,
     training, incident procedures, risk assessments, and change records.

4. **Implement and collect evidence**
   - Evidence must show the control is performed, not merely described.
   - Preserve screenshots, exports, tickets, logs, policies, approvals, test
     results, and configuration records with dates and owners.

5. **Run a readiness assessment**
   - Use NIST SP 800-171A and the current CMMC Level 2 Assessment Guide.
   - Score every requirement objective and record gaps honestly.
   - Do not enter an SPRS score that the evidence cannot support.

6. **Choose the required assessment route**
   - For Level 2 (Self), submit the assessment and scope information in SPRS.
   - For Level 2 (C3PAO), contract with an authorized/accredited C3PAO and
     complete the certification assessment.
   - For HarborSentinel and NV065, do not assume the projected topic CMMC
     level is enough; verify the actual DSIP topic instructions, award
     instrument, clause flowdown, and whether the work will handle FCI or CUI.

7. **Close allowed POA&M items**
   - A conditional Level 2 status is available only when the score and
     requirement-specific POA&M rules are satisfied.
   - SPRS quick-entry guidance shows Level 2 Conditional Self-Assessment at
     scores 88-109 and Final Self-Assessment at 110; not every missing
     requirement is eligible for a POA&M.
   - Close all permitted POA&M items and post the closeout within 180 days.

8. **Affirm and maintain**
   - An Affirming Official must affirm at assessment and annually afterward.
   - Level 2 assessments are generally renewed every three years.
   - For a C3PAO assessment, retain hashed assessment artifacts for six years.
   - If the AO cannot truthfully certify continuing compliance, do not affirm.
   - Do not let Codex, a contractor, or an advisor click an affirmation box on
     the company's behalf.

## Practical Next Actions

1. Keep the DICE abstract Unclassified and free of CUI.
2. Verify SAM.gov active status and expiration date now; record only
   non-sensitive status facts in the grant blocker board.
3. Confirm whether PIEE access, SPRS Cyber Vendor User role, CAGE hierarchy,
   and an Affirming Official exist.
4. Ask APEX Accelerators or Project Spectrum for no-cost readiness support.
5. Obtain a qualified CMMC Registered Practitioner or equivalent advisor for
   scope and evidence review before paying for a C3PAO assessment.
6. Request quotes only after the enclave scope is stable.
7. Do not claim "CMMC Level 2 compliant" or "certified" until the required
   status is actually recorded and current.

## Grant-Package Gate Language

Use this language in DICE, HarborSentinel, NV065, and MissionWeave until the
user verifies portal/security status:

- "Current proposal material is handled as Unclassified and non-CUI unless an
  authorized source marks otherwise."
- "CMMC, SPRS, CAGE hierarchy, FCI/CUI handling, export, FOCI, and clearance
  representations remain user-verified gates."
- "No CMMC Level 2, facility-clearance, personnel-clearance, SPRS score, or
  export-control status is claimed."
- "If awarded work requires FCI/CUI, LumenCore will isolate federal work in a
  scoped enclave and submit only evidence-supported cybersecurity
  representations."

## Official References

- 32 CFR 170.16, Level 2 self-assessment:
  https://www.ecfr.gov/current/title-32/subtitle-A/chapter-I/subchapter-G/part-170/subpart-D/section-170.16
- 32 CFR 170.17, Level 2 C3PAO assessment:
  https://www.ecfr.gov/current/title-32/subtitle-A/chapter-I/subchapter-G/part-170/subpart-D/section-170.17
- SPRS CMMC guidance and entry tutorials:
  https://www.sprs.csd.disa.mil/cmmc.htm
- SPRS Level 2 Self-Assessment Quick Entry Guide:
  https://www.sprs.csd.disa.mil/pdf/CMMCL2SelfQuickEntryGuide.pdf
- SPRS Affirming Official tutorial transcript:
  https://www.sprs.csd.disa.mil/pdf/training/AffirmingOfficialTutorialforCMMC-Transcript.pdf
- SAM.gov entity registration:
  https://sam.gov/entity-registration
- Defense SBIR/STTR funding opportunities and DSIP submission guidance:
  https://www.defensesbirsttr.mil/SBIR-STTR/Opportunities/
- DoD CMMC documentation:
  https://dodcio.defense.gov/CMMC/Documentation/
- Project Spectrum:
  https://www.projectspectrum.io/
- APEX Accelerators:
  https://www.apexaccelerators.us/
