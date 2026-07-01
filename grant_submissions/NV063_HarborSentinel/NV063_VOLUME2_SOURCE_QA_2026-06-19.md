# NV063 HarborSentinel Volume 2 Source QA

Date: June 20, 2026

Artifact checked:
`grant_submissions/NV063_HarborSentinel/NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.md`

Generated DOCX checked:
`grant_submissions/NV063_HarborSentinel/NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.docx`

Status: compact Navy Volume 2-style content source; not approved for
submission.

## Content Checks

- Approximate source length: about 2,200 words after adding the public AIS
  full-hash split verification and controlled-injection benchmark paragraph.
- Format target stated: single-column Phase I Technical Volume, 8.5 x 11 inch
  pages, 1-inch margins, no font smaller than 10 point, not to exceed 10
  pages.
- Base and Option work are both included in the content source.
- Base budget target is stated as not to exceed $200,000.
- Option budget target is stated as not to exceed $115,000.
- Base-work milestones and success criteria now state Month 1 through Month 6
  gates and explicitly distinguish reproducible Phase I evidence from SSDS
  integration, classified sensor validation, operational threat
  classification, or CMMC/clearance readiness.
- No-upload boundary is present.

## Document Render QA

Latest render refreshed on June 20, 2026 from
`build_nv063_volume2_docx.py`.

- DOCX structural check passed: 73 paragraphs, 0 tables, 1 section.
- Page geometry check passed: US Letter portrait, 1-inch top/right/bottom/left
  margins.
- Hidden DOCX sidecar check passed: no `customXml/` parts, no
  `docProps/custom.xml`, and no stale custom XML relationship/content-type
  references.
- Local LibreOffice render passed and Poppler page rendering produced PNGs for
  visual inspection.
- Render packet:
  `grant_submissions/NV063_HarborSentinel/render_qa_20260620_baselines_v1/`.
- PDF output:
  `NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.pdf`, 99,538 bytes.
- Page count: 6 pages, below the Navy Volume 2 10-page cap.
- PNG review: `page-1.png` through `page-6.png` rendered; all six page images
  were visually inspected after the public AIS stronger-baseline update.
- Visual QA result: no clipping, overlap, broken bullets, missing glyphs,
  broken headers/footers, or blank trailing page observed.

## Evidence Checks

Canonical run:
`out/harbor_sentinel_validation/20260619T_NV063_V6_SOURCE_LANE_COVERAGE/`

Manifest verification passed for:

- `summary.json`
- `scenario_summary.csv`
- `source_lane_summary.csv`
- `SCORECARD.md`

The Volume 2 source carries the v6 frozen headline results:

- Nominal F1: 0.952.
- Combined-stress F1: 0.927.
- Severe-stress F1: 0.888.
- Combined-stress review false alerts: 144.9 per 10,000 normal points.
- Combined-stress behavior-based threat-candidate false alerts: 76.5 per
  10,000 normal points.
- Severe-stress review false alerts: 191.9 per 10,000 normal points.
- Severe-stress behavior-based threat-candidate false alerts: 77.0 per 10,000
  normal points.
- Nominal AIS-like availability: 0.960.
- Severe-stress AIS-like availability: 0.904.

The Volume 2 source now also carries the bounded public AIS controlled-injection
result:

- NOAA AIS raw ZIP bytes: 290,340,871.
- NOAA AIS raw SHA-256:
  `03ed1e16f4445361d3d7cd6e0f0b4175dce4e63b0c5c8c99252728c64de9253c`.
- Frozen development rows: 50,000.
- Frozen validation rows: 50,000.
- Split I/O preflight: 2/2 required files sample-readable and full-file
  SHA-256 matched against the frozen split manifest.
- Controlled-injection validation segments: 20,000.
- Motion-consistency recall: 1.0.
- Speed-only baseline recall: 0.25835.
- Best single-axis baseline recall: 0.5068
  (`speed_gap_consistency_p99`).
- Recall lift: 0.7416499999999999.

## Boundary Checks

The Volume 2 source explicitly states that current evidence is generated
software evidence only and does not establish:

- operational harbor performance;
- SSDS integration;
- sensor-feed performance;
- adversarial security;
- cybersecurity;
- classified-environment performance; or
- field performance.

For the public AIS controlled-injection result, the source also states that
controlled kinematic injections are not real adversary labels, multi-source
fusion, ADS-B/radar validation, Navy/SSDS integration, field performance, or
operational suitability.

It also states that no current draft claims access to Navy radar, classified
sensor data, SSDS interfaces, operational harbor feeds, or
government-furnished data.

## Tests

Focused tests passed after the milestone/success-criteria update:

- `test_grant_evidence_boundaries.py`: 4 passed.
- `test_harbor_sentinel_benchmark.py`: 11 passed.
- `test_harbor_sentinel_validation_suite.py`: 1 passed.

Manifest verification after the update matched all four frozen v6 evidence
files: `summary.json`, `scenario_summary.csv`, `source_lane_summary.csv`, and
`SCORECARD.md`.

## Remaining Before Upload

1. Confirm DSIP account, organization linkage, and submitter authority.
2. Verify SAM.gov active status, legal business name, UEI, and CAGE if
   applicable.
3. Complete DoD ownership/operation, FOCI, export-control, cybersecurity,
   SPRS/CMMC, and FCI/CUI representation checks.
4. Review the $315,000 ROM cost basis with defensible direct/indirect,
   consultant, travel, cloud, and fringe assumptions.
5. Confirm whether a credible advanced-phase Secret facility/personnel
   clearance path can be represented.
6. Confirm whether DSIP requires a specific final filename, template cover
   field, or portal-generated preview after the June 24 opening window.
7. Re-check the uploaded/portal-previewed attachment before any certification
   or submit action.
8. Execute representative public/authorized data acquisition and evaluation
   before making stronger ADS-B, radar, multi-source, field, or operational
   claims.
9. Obtain human approval before any upload, certification, consent, or submit
   action.
