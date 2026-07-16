# DICE HR001126S0010 Submission Readiness

Updated: July 16, 2026

## Current Decision

- Target: TA1 and TA2 together.
- Abstract due: June 30, 2026 at 2:00 p.m. Eastern Time.
- Full proposal due: August 25, 2026 at 2:00 p.m. Eastern Time.
- Submission system: DARPA Broad Agency Announcement Tool (BAAT).
- Amendment 01 posted July 14, 2026 changes Section 3.3 CMMC requirements.
- TA1/TA2 now has an explicit Final CMMC Level 1, CAGE-linked SPRS, and annual
  affirmation award-eligibility gate. See
  `DICE_AMENDMENT_01_DELTA_2026-07-16.md`.
- Current artifact:
  `LumenCore_DICE_Abstract_WORKING_DRAFT.docx`
- Status: working draft, not approved for submission.

## Completed

- Official DICE BAA and abstract template downloaded.
- Official Amendment 01 downloaded, hashed, and reconciled against the
  original BAA on July 16, 2026. No technical-area, deadline, portal, or
  proposal-attachment change was identified.
- TA1/TA2 requirements mapped to a single technical concept.
- Official-template working abstract generated.
- Cover sheet, six required sections, cost-by-phase estimate, compute
  capability, publications, and bibliography included.
- Template instructions and placeholder content removed.
- Preliminary benchmark implemented with a stated evidence boundary.
- Frozen paired runs completed at 500, 5,000, and 100,000 stochastic agents.
- SHA-256 manifests generated for every run.
- Constraint-carrying commitment ablation implemented with separate
  development and validation partitions and a stated evidence boundary.
- Constraint-contract manifest verified locally on June 19, 2026.
- Public-safe evidence governance is now pushed to the public repository main
  branch at commit `fb97266`:
  `https://github.com/robertashworth1986-debug/lumen-core-public`.
  The public bundle contains the Geometry Championship V1 registry,
  readiness runner, unit test, frozen scorecard, summary, registry snapshot,
  and SHA-256 manifest. It explicitly reports zero performance-ready geometry
  families and no performance champion.
- No private grant forms, portal material, secrets, contact details, or
  unreviewed partner claims were included in the public evidence commit.
- DOCX structural check passed on June 19, 2026 using `python-docx`: cover
  draft warning present, six required sections present, two tables present,
  and no unresolved placeholder/template strings found.
- DICE builder now removes hidden official-template review artifacts after
  generation: stale comments, comments-extended part, SharePoint/custom XML,
  custom document properties, inherited last-modified metadata, and stale print
  metadata.
- DICE DOCX reference/URL QA is recorded in
  `DICE_DOCX_QA_AND_REFERENCE_CHECK_2026-06-19.md`.
- DICE Heilmeier/reviewer answers are now consolidated in
  `DICE_HEILMEIER_REVIEWER_MATRIX_2026-06-20.md`, including the evidence map,
  claim boundaries, reviewer objections, baseline/metric matrix, and final
  submission gates.
- The DICE builder now adds source links for the Friston, ReSo, and Fujimoto
  bibliography entries.
- The regenerated DOCX contains 12 visible URLs, no visible trailing URL
  punctuation, and reachability/source checks passed or were otherwise
  source-confirmed for all 12 links. The two previously blocked DOI records
  now have follow-up source/metadata confirmation: the SAGE page confirms
  `10.1177/26339137231222481`, and Crossref metadata confirms both
  `10.1177/26339137231222481` and `10.1145/84537.84545`.
- June 19 follow-up session confirmed the official Grants.gov DICE detail,
  downloaded and extracted the full announcement ZIP, regenerated the working
  DOCX with the bundled document runtime, and rechecked the generated package:
  68 paragraphs, two tables, one section, no hidden comments/custom XML/custom
  properties, no missing required abstract sections, no unresolved
  placeholders, and the working-draft warning remains present.
- June 19 visual render QA passed after repairing a workspace-local
  LibreOffice copy at `C:\LumaTrader\.tools\LibreOffice\program`: the final
  render packet is
  `render_qa_20260619_manual_clean_v5/`, with a 7-page PDF and seven inspected
  page PNGs. The render loop removed inherited double heading numbering and an
  unintended blank page before Publications.
- June 19 follow-up normalized bibliography entries into a compact
  author/year style and regenerated the abstract so the `$4.92 million` figure
  is explicitly labeled an abstract-stage ROM planning estimate requiring
  full-proposal cost validation.
- Sprint checklist:
  `DICE_NEXT_11_DAY_SPRINT_2026-06-19.md`.

## Blocking Before Upload

1. **BAAT consent and account access**
   - BAAT login, organization profile, and submitter authority must be
     verified by the user.
   - Codex must receive action-time confirmation before clicking any consent,
     upload, or submit control.

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
   - Amendment 01 states that TA1/TA2 requires Final CMMC Level 1, with the
     proposal CAGE code linked to a valid, unexpired status in SPRS and a
     current annual affirmation by an authorized Affirming Official.
   - The amended language is broader than the original procurement-contract
     lead-in. Treat the requirement as an award-eligibility gate unless DARPA
     provides written clarification for the selected award instrument.
   - Current PIEE access, SPRS role, CAGE linkage, CMMC status, and annual
     affirmation remain unverified. Do not represent them as complete.
   - Use `../CMMC_LEVEL_2_READINESS_2026-06-13.md` to plan a separate federal
     enclave if future work requires CUI or a Level 2 status.

6. **References and technical claims**
   - Reference URL/source checks are complete enough to remove the DOI-link
     blocker; citation style has been normalized, and final reference
     relevance should still be manually reviewed before upload.
   - Do not claim foundation-model or operational performance from the
     stochastic discrete-event benchmark.
   - Preserve the statement that mission-success differences at 5,000 and
     100,000 agents were statistically indistinguishable from zero.

7. **Document rendering**
   - Structural checks passed: 1-inch margins, 12-point body text, required
     sections, no template instructions, and no unresolved placeholders.
   - June 19 structural/package recheck passed with the bundled document
     runtime: ZIP integrity OK, no hidden comments/custom XML, no tracked
     changes, no visible comment anchors, and cost table header marked.
   - Visual page-image review passed locally using the repaired workspace-local
     LibreOffice renderer and `pypdfium2`: 7 rendered pages, all inspected,
     with no visible clipping, table breakage, missing footer, double heading
     numbering, or unintended blank page.
   - Optional independent check: open the DOCX in Word, LibreOffice, or the
     BAAT upload-preview environment and confirm the same layout before upload.

8. **Human approval**
   - Remove `WORKING DRAFT - NOT APPROVED FOR SUBMISSION` only after all
     blockers are cleared.
   - Final BAAT upload and submission require human review and action-time
     confirmation.

## Evidence Boundary

The June 18 constraint-contract validation is frozen at
`out/dice_constraint_contract/20260618T_DICE_CONTRACT_V2_ROLE_SHUFFLE/`.
It uses 30 disjoint validation scenarios per condition at 500 agents and 1,200
tasks. Safe-completion improvements ranged from 4.16 percentage points in the
benign condition to 1.35 points under 25% high collusion. The abstract must
retain the measured tradeoffs: raw completion fell 2.5-4.5 points, false
rejection reached 11.38% under monitor shift, and compromised assignments
increased 0.96 points under high collusion. Message fields were counted, but
bytes, latency, and cryptographic costs were not measured.

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

## Current Action Order

1. Human verifies BAAT access and submitter authority.
2. Human verifies PIEE/SPRS access, the proposal CAGE code, Final CMMC Level 1
   status, and the current annual affirmation or records each item as absent.
3. Optionally re-open `LumenCore_DICE_Abstract_WORKING_DRAFT.docx` in Word,
   LibreOffice, or BAAT preview and confirm the local 7-page layout.
4. Replace the planning cost estimate with a reviewed cost basis if one
   becomes available; otherwise preserve the abstract-stage ROM language.
5. Review final reference relevance; link/source existence has been checked or
   source-confirmed for all visible URLs, and citation style is normalized.
6. Add any real collaborator commitments; otherwise keep the one-person-team
   risk explicit.
7. Remove the working-draft warning only after all blockers clear.
