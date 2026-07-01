# NV063 HarborSentinel Readiness

Updated: June 20, 2026

## Opportunity

- Topic: DON26BZ03-NV063
- Title: Anomalous Behavior Detection and Alerting for Congested Maritime
  Environments
- Opens: June 24, 2026
- Closes: July 22, 2026 at 12:00 p.m. Eastern Time
- Portal: Defense SBIR/STTR Innovation Portal (DSIP)
- Phase I ceiling: $315,000
- Required structure: Base up to $200,000 for six months plus Option up to
  $115,000 for six months

## Strengths

- The topic explicitly requires AIS, ADS-B, notional radar, low-storage
  pattern-of-life analysis, explainable alerts, confidence, and an SSDS
  integration plan.
- A deterministic synthetic prototype benchmark exists with class-level event
  coverage, delay, explanation, compact-state, fixed-rule comparator, and
  separate development/validation results.
- The frozen validation suite covers nominal, congested, sensor-shift, benign
  dropout, combined-stress, and severe-breakdown conditions.
- Source-integrity alerts are separated from behavior-based threat candidates,
  so missing transmitters are not automatically labeled hostile.
- The v6 evidence packet preserves the v5 source-quality gate and adds
  explicit generated source-lane coverage for AIS-like, ADS-B-like, and
  notional radar-like observations while preserving a synthetic-only evidence
  boundary.
- The evidence package preserves negative results and states its operational
  boundary.
- A topic traceability section now maps the draft to AIS, ADS-B, radar-like
  observations, low-storage operation, alert content, and SSDS transition
  concept without claiming integration.
- A working cost basis and finalization audit now exist locally.
- A compact Navy Volume 2-style content source now exists with Base and Option
  tasks, v6 evidence, representative-data lanes, risks, transition, and a
  submission boundary.
- The compact source now includes Month 1 through Month 6 milestones and
  success criteria that distinguish reproducible Phase I evidence from SSDS
  integration, classified sensor validation, operational threat
  classification, or CMMC/clearance readiness.
- A generated 6-page Volume 2 DOCX now exists and passed local LibreOffice
  render/visual QA; hidden DOCX custom XML sidecars were removed and the
  package was normalized for reliable rendering.
- A representative-data and format-conversion plan now maps public AIS,
  authorized ADS-B, generated/authorized radar-like tracks, official 10-page
  Navy Volume 2 constraints, and the projected CMMC Level 2 (Self) / advanced
  phase clearance boundary.
- Public NOAA AIS was rehydrated locally, hash-matched, frozen into
  development/validation splits, full-file SHA-256 verified for both split
  files, and evaluated with a bounded controlled-injection benchmark. This
  supports detector-vs-baseline evidence only, not real adversary labels,
  ADS-B/radar validation, SSDS integration, or field performance.
- A Navy reviewer proof matrix now consolidates evidence, boundaries,
  objections, and final submission gates.

## Critical Blockers

1. Verify SAM.gov status, expiration, and DSIP submitter authority.
2. Complete DoD representations, foreign ownership/influence review, export
   review, and required cybersecurity assessment.
3. Confirm the company is U.S. owned and operated under the topic definition.
4. Establish a credible plan to acquire and maintain the Secret facility and
   personnel clearances required for advanced phases.
5. Replace provisional indirect costs with a defensible rate/base treatment.
6. Obtain scopes and quotes for any consultant or subcontract amount.
7. Confirm the final DSIP attachment filename/template/portal preview after
   the submission window opens, even though the local 6-page DOCX render QA has
   passed.
8. Do not claim SSDS integration, operational sensor validation, or field
   performance.
9. Extend the current public AIS controlled-injection lane beyond the new
   single-axis baseline suite with labels or analyst adjudication,
   density-aware calibration, source-health estimation, and frozen acceptance
   gates before making stronger claims.
10. Keep beacon-loss handling framed as source-integrity review. The synthetic
    median beacon-silence delay improved from 11 to 4 steps, but operational
    delay/false-alert tradeoffs remain unvalidated.
11. Confirm final DSIP/Navy page limits, volume naming, and required
    attachments after the June 24 opening window.

## Current Local Artifacts

- `NV063_TECHNICAL_VOLUME_REVISED.md`
- `NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.md`
- `NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.docx`
- `NV063_COST_BASIS_WORKING.md`
- `NV063_FINALIZATION_AUDIT_2026-06-19.md`
- `NV063_REPRESENTATIVE_DATA_AND_FORMAT_PLAN_2026-06-19.md`
- `NV063_VOLUME2_SOURCE_QA_2026-06-19.md`
- `render_qa_20260619_volume2_v2/`
- `NAVY_26BZ_PH_I_R3_INSTRUCTIONS.pdf`
- `docs/HARBOR_SENTINEL_VALIDATION_2026-06-13.md`
- `out/harbor_sentinel_validation/20260619T_NV063_V6_SOURCE_LANE_COVERAGE/`

## Current Recommendation

Proceed with final-format preparation. The technical story is stronger after
the v6 source-lane coverage freeze and the compact Volume 2-style source
draft plus latest local 6-page DOCX/PDF visual QA, public AIS held-out split
full-hash verification, controlled-injection benchmark, and explicit Month 1
through Month 6 success gates. Do not submit until the clearance transition plan, DoD compliance
representations, reviewed cost basis, final DSIP portal-preview review,
ADS-B/radar authorization paths, and human action-time approval are credible.
DICE remains the earlier and cleaner near-term opportunity because it does not
impose this topic's advanced phase facility-clearance requirement.
