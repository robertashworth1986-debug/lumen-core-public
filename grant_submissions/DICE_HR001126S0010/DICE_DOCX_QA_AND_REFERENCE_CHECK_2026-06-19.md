# DICE DOCX QA and Reference Check

Date: June 19, 2026

Artifact checked:
`grant_submissions/DICE_HR001126S0010/LumenCore_DICE_Abstract_WORKING_DRAFT.docx`

Builder checked:
`grant_submissions/DICE_HR001126S0010/build_dice_abstract.py`

Status: structurally checked and template-artifact-scrubbed working draft; not
approved for upload.

Latest rebuild note: after the move-on decision, the DICE abstract was
regenerated from source with "role-coherence guarantees" softened to
"role-coherence bounds" so the claim matches the current synthetic evidence.

## Visual Render QA

LibreOffice was installed but the Program Files launcher reported a corrupt
`bootstrap.ini`. Codex copied the LibreOffice tree into a writable local tool
folder, repaired only the local bootstrap placeholder, and rendered with:

`C:\LumaTrader\.tools\LibreOffice\program\soffice.com`

The packaged renderer still fails on this Windows machine because it passes a
`file://C:\...` profile URL that triggers `libpng error: Write Error`.
Manual conversion with a proper `file:///C:/...` user-profile URL succeeded,
then `pypdfium2` rendered the PDF to page PNGs.

Final render packet:

`grant_submissions/DICE_HR001126S0010/render_qa_20260619_manual_clean_v5/`

Render evidence:

- PDF produced: `LumenCore_DICE_Abstract_WORKING_DRAFT.pdf`, 154,979 bytes.
- Page count: 7.
- Page PNGs: `page-1.png` through `page-7.png`, each 1224 x 1584 pixels.
- Every page image was visually inspected on June 19, 2026.
- Result: no visible clipping, overlap, broken table geometry, missing footer,
  double heading numbering, or unintended blank page.

Layout fixes made from the render loop:

- Removed inherited template sidecar parts and normalized the DOCX package so
  LibreOffice can load it.
- Replaced template auto-numbered heading styles with deterministic direct
  heading formatting.
- Removed the forced page break before Publications that created a blank page.

## Structural Check

Bundled `python-docx` extraction after regeneration:

- ZIP package integrity: passed.
- Paragraphs: 68.
- Tables: 2.
- Sections: 1.
- Page size: 8.5 x 11 inches.
- Margins: 1 inch on all sides.
- Hidden review artifacts: `word/comments.xml`, `word/commentsExtended.xml`,
  `word/commentsExtensible.xml`, `word/commentsIds.xml`, `word/people.xml`,
  `docMetadata/LabelInfo.xml`, stale `customXml/*`, and
  `docProps/custom.xml` removed by the builder after generation.
- Tracked changes and visible comment anchors: none found.
- Core metadata now names `Robert Ashworth` as creator and `LumenCore` as last
  modifier instead of retaining inherited template reviewer metadata.
- Draft warning present: `WORKING DRAFT - NOT APPROVED FOR SUBMISSION`.
- Required sections present:
  - `1. Goals and Impact`
  - `2. Technical Approach`
  - `3. Capabilities/Management Plan`
  - `4. Cost and Schedule`
  - `5. Publications`
  - `6. Bibliography`
- Placeholder scan: no `TO_BE_FILLED`, `TODO`, `Insert`, or `placeholder`
  strings found in visible text.
- Table semantics: the cost/schedule table header row is marked with
  `w:tblHeader`; the cover-sheet table is a two-column key/value table, so the
  accessibility tool's generic `table_no_header_row` warning was reviewed as
  not applicable rather than auto-fixed into an inaccurate header.

Latest focused recheck after citation/cost regeneration:

- `tests/test_dice_preliminary_benchmark.py`,
  `tests/test_dice_constraint_contract_benchmark.py`, and
  `tests/test_grant_evidence_boundaries.py`: 9 passed.
- DOCX package recheck: 33,868 bytes, 68 paragraphs, 2 tables, 1 section, all
  required sections present, no hidden comments/custom XML/custom properties,
  no stale relationship/content-type references, and the working-draft warning
  remains present.
- Render packet recheck: `LumenCore_DICE_Abstract_WORKING_DRAFT.pdf` remains
  7 pages and 154,979 bytes.

## URL Extraction Check

Visible URLs in the regenerated DOCX: 12.

Trailing punctuation check: passed. No visible URL ended in `.`, `,`, or `;`.

URLs:

- https://www.darpa.mil/research/programs/decentralized-artificial-intelligence-through-controlled-emergence
- https://arxiv.org/abs/2308.10248
- https://arxiv.org/abs/2410.07283
- https://doi.org/10.1177/26339137231222481
- https://aclanthology.org/2025.emnlp-main.808/
- https://arxiv.org/abs/2605.09076
- https://github.com/modelcontextprotocol
- https://github.com/a2aproject
- https://docs.vllm.ai/
- https://doi.org/10.1145/84537.84545
- https://lumen-core.ai
- https://github.com/robertashworth1986-debug/lumen-core-public

## Reachability And Source Check

Direct `Invoke-WebRequest` checks returned HTTP 200 for:

- DARPA DICE program page.
- arXiv 2308.10248.
- arXiv 2410.07283.
- ACL Anthology ReSo page.
- arXiv 2605.09076.
- Model Context Protocol GitHub organization.
- Agent2Agent Protocol GitHub organization.
- vLLM documentation.
- `lumen-core.ai`.
- Public LumenCore GitHub repository.

Follow-up browser/source check on June 19, 2026 narrowed the two DOI issues:

- `https://doi.org/10.1177/26339137231222481`: browser/source lookup confirmed
  the SAGE `Collective Intelligence` record for "Designing ecosystems of
  intelligence from first principles"; the page displays the same DOI.
- Crossref metadata check confirmed DOI `10.1177/26339137231222481`, title
  "Designing ecosystems of intelligence from first principles", journal
  `Collective Intelligence`, publication date `2024-1`, and authors beginning
  Karl J. Friston, Maxwell JD Ramstead, and Alex B. Kiefer.
- `https://doi.org/10.1145/84537.84545`: the ACM page still returns 403 to
  direct automated fetch from this environment, but source search and Crossref
  metadata confirm DOI `10.1145/84537.84545`, title "Parallel discrete event
  simulation", author Richard M. Fujimoto, journal `Communications of the ACM`,
  publication date `1990-10`, and pages `30-53`.

Remaining reference issue: not link existence or citation style, but final
human relevance review and an optional browser check in the actual upload
environment.

## Bibliography Update

The DICE builder now adds source links for the previously unlinked external
references:

- Friston et al., "Designing Ecosystems of Intelligence from First Principles"
  now includes `https://doi.org/10.1177/26339137231222481`.
- Zhou et al., "ReSo: A Reward-Driven Self-Organizing LLM-Based Multi-Agent
  System for Reasoning Tasks" now includes
  `https://aclanthology.org/2025.emnlp-main.808/`.
- Fujimoto, "Parallel Discrete Event Simulation" now includes
  `https://doi.org/10.1145/84537.84545`.

The public repository sentence was also regenerated so the visible GitHub URL
does not include trailing punctuation.

June 19 follow-up: bibliography entries were normalized into a consistent
compact author/year style and the generated cost language now marks the
`$4,920,000` figure as an abstract-stage ROM planning estimate requiring
full-proposal cost validation.

## Remaining Before Upload

1. Optional independent check: open the DOCX in Microsoft Word or LibreOffice
   before upload and confirm the same seven-page layout in the portal/user
   environment.
2. Manually review every bibliography item for relevance; citation style has
   been normalized and the two previously blocked DOI records have
   source/metadata confirmation.
3. Confirm BAAT account, organization profile, submitter authority, and human
   approval at action time.
4. Keep the working-draft warning until portal, format, cost, compliance,
   teaming, and human approval gates clear.
