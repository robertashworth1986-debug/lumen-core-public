# DICE HR001126S0010 Submission Readiness

Updated: June 13, 2026

## Current Decision

- Target: TA1 and TA2 together.
- Abstract due: June 30, 2026 at 2:00 p.m. Eastern Time.
- Full proposal due: August 25, 2026 at 2:00 p.m. Eastern Time.
- Submission system: DARPA Broad Agency Announcement Tool (BAAT).
- Current artifact:
  `LumenCore_DICE_Abstract_WORKING_DRAFT.docx`
- Status: working draft, not approved for submission.

## Completed

- Official DICE BAA and abstract template downloaded.
- TA1/TA2 requirements mapped to a single technical concept.
- Official-template working abstract generated.
- Cover sheet, six required sections, cost-by-phase estimate, compute
  capability, publications, and bibliography included.
- Template instructions and placeholder content removed.
- Preliminary benchmark implemented with a stated evidence boundary.
- Frozen paired runs completed at 500, 5,000, and 100,000 stochastic agents.
- SHA-256 manifests generated for every run.
- Benchmark implementation, test, and public-safe report pushed to GitHub
  `main` in commit `804afcd`.
- No private identifiers or contact details were included in the public commit.

## Blocking Before Upload

1. **BAAT consent and account access**
   - The browser is at the Department of Defense monitoring and consent notice.
   - The user must confirm before Codex clicks `Agree/Continue to Site`.
   - BAAT account/login and organization profile must then be verified.

2. **Cost realism**
   - The `$4.92 million` figure remains a planning estimate, not a validated
     cost proposal.
   - A reconciled working basis now allocates 21,060 direct labor hours,
     fringe, indirect cost, subawards/consultants, cloud/HPC, travel, and
     software/data/equipment across all three phases.
   - The provisional direct rate, indirect rates, resource-sharing treatment,
     cloud quotations, and subaward scopes still require validation.

3. **Team credibility**
   - The current organization is one person.
   - The abstract identifies required roles but no named commitments.
   - Seek at least one credible distributed-systems/consensus collaborator and
     one inference-control or AI-safety collaborator before full proposal.

4. **SAM and submitter authority**
   - Verify the authenticated SAM.gov entity record, expiration date, and
     timestamp.
   - Verify BAAT submitter authority and organization linkage.

5. **Award vehicle and cybersecurity**
   - `OT for Research` is requested in the working draft, but DARPA controls
     the final award instrument.
   - Confirm the proposed information boundary remains Unclassified and does
     not require CUI processing.
   - If a procurement contract is pursued, verify CMMC Level 1 proposal
     requirements and current SPRS/CMMC status.
   - Use `../CMMC_LEVEL_2_READINESS_2026-06-13.md` to plan a separate federal
     enclave if future work requires CUI or a Level 2 status.

6. **References and technical claims**
   - Verify every publication citation and URL.
   - Do not claim foundation-model or operational performance from the
     stochastic discrete-event benchmark.
   - Preserve the statement that mission-success differences at 5,000 and
     100,000 agents were statistically indistinguishable from zero.

7. **Document rendering**
   - Structural checks passed: 1-inch margins, 12-point body text, required
     sections, no template instructions, and no unresolved placeholders.
   - Visual page-image review could not be completed because LibreOffice and
     Microsoft Word are not installed on this machine.
   - Render in Word or LibreOffice and confirm the TA1/TA2 technical content is
     no more than seven pages, excluding cover, table of contents,
     publications, and bibliography.

8. **Human approval**
   - Remove `WORKING DRAFT - NOT APPROVED FOR SUBMISSION` only after all
     blockers are cleared.
   - Final BAAT upload and submission require human review and action-time
     confirmation.

## Evidence Boundary

The preliminary benchmark uses stochastic task executors, not language models.
It supports a software-harness scalability and message-efficiency hypothesis.
It does not establish DICE metric attainment, foundation-model inference at
scale, operational defense performance, resilience to real adversaries, or
security certification.

## Official Sources

- DARPA DICE program:
  https://www.darpa.mil/research/programs/decentralized-artificial-intelligence-through-controlled-emergence
- DARPA BAAT:
  https://baa.darpa.mil/
- Official opportunity:
  https://simpler.grants.gov/opportunity/56b71085-ed91-4468-b7eb-3a04bf840794
