# CMMC Level 2 Readiness Path

Updated: June 13, 2026

This is a planning checklist, not legal advice, an assessment, or a
certification representation.

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
   - Verify CAGE, UEI, SAM.gov, PIEE, and the company hierarchy.
   - Obtain the SPRS Cyber Vendor User role.
   - Identify the company Affirming Official.

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

7. **Close allowed POA&M items**
   - A conditional Level 2 status is available only when the score and
     requirement-specific POA&M rules are satisfied.
   - The current rule requires at least 80% of the maximum score for a
     conditional status, and not every missing requirement is eligible.
   - Close all permitted POA&M items and post the closeout within 180 days.

8. **Affirm and maintain**
   - An Affirming Official must affirm at assessment and annually afterward.
   - Level 2 assessments are generally renewed every three years.
   - For a C3PAO assessment, retain hashed assessment artifacts for six years.

## Practical Next Actions

1. Keep the DICE abstract Unclassified and free of CUI.
2. Ask APEX Accelerators or Project Spectrum for no-cost readiness support.
3. Obtain a qualified CMMC Registered Practitioner or equivalent advisor for
   scope and evidence review before paying for a C3PAO assessment.
4. Request quotes only after the enclave scope is stable.
5. Do not claim “CMMC Level 2 compliant” or “certified” until the required
   status is actually recorded and current.

## Official References

- 32 CFR 170.16, Level 2 self-assessment:
  https://www.ecfr.gov/current/title-32/subtitle-A/chapter-I/subchapter-G/part-170/subpart-D/section-170.16
- 32 CFR 170.17, Level 2 C3PAO assessment:
  https://www.ecfr.gov/current/title-32/subtitle-A/chapter-I/subchapter-G/part-170/subpart-D/section-170.17
- SPRS CMMC guidance and entry tutorials:
  https://www.sprs.csd.disa.mil/cmmc.htm
- DoD CMMC documentation:
  https://dodcio.defense.gov/CMMC/Documentation/
- Project Spectrum:
  https://www.projectspectrum.io/
- APEX Accelerators:
  https://www.apexaccelerators.us/
