# NV063 HarborSentinel Representative Data and Format Plan

Date: June 19, 2026

Status: submission-hardening plan only; not evidence of operational
performance, SSDS integration, field sensor validation, CMMC status, facility
clearance, or Navy domain approval.

Update: the generated v6 validation packet now reports source-lane coverage
for AIS-like surface cooperative beacons, ADS-B-like air cooperative beacons,
and notional radar-like contacts at
`out/harbor_sentinel_validation/20260619T_NV063_V6_SOURCE_LANE_COVERAGE/`.
This is still generated feasibility evidence only; it does not replace public
AIS acquisition, authorized ADS-B access, or government-furnished assumptions.

Update June 20, 2026: an AIS pilot source registry now exists at
`NV063_AIS_PILOT_SOURCE_REGISTRY_2026-06-20.md`. Live HEAD probes confirmed a
NOAA daily AIS CSV ZIP candidate and a NOAA/MarineCadastre analysis-ready
GeoParquet candidate, but both exceed the current auto-download size policy.
Use the Glyph or equivalent external data volume as the raw-data workspace;
commit only source registries, hashes, schema profiles, and bounded summaries
back into the repo.

## Purpose

This plan turns two open blockers into concrete work packages:

1. Build a credible representative-data path for HarborSentinel without
   claiming access to Navy or SSDS data.
2. Convert the revised technical draft into the official Navy/DSIP Phase I
   Technical Volume constraints.

## Official Submission Constraints

Source:
`grant_submissions/NV063_HarborSentinel/NAVY_26BZ_PH_I_R3_INSTRUCTIONS.pdf`

Key extracted constraints from the official Navy FY-26 Release 3 Phase I
instructions:

- Proposals must be submitted through DSIP; proposals submitted by other means
  are disregarded.
- Technical Volume (Volume 2) must not exceed 10 pages.
- Volume 2 must be single column, single spaced, standard 8.5 x 11 inch paper,
  with 1-inch margins on all sides.
- No font size smaller than 10 point, except where instructions specifically
  permit.
- Phase I Base and Phase I Option tasks must both be clearly identified inside
  the 10-page Technical Volume.
- Phase I Base must not exceed $200,000; Phase I Option must not exceed
  $115,000; Base and Option costs must be separated in Volume 3.
- Cost sharing is not accepted on DON Phase I proposals.
- Supporting Documents (Volume 5) must not be used to substantiate the
  Technical Volume with resumes, test data, technical reports, or publications;
  such material will not be considered.

NV063 topic extraction from the same official instructions:

- Projected CMMC level requirement: Level 2 (Self).
- Minimum source set includes AIS, ADS-B, and notional air or surface contacts
  detected by notional radars.
- Solutions should address all surface and air traffic in a 360-degree area
  around a notional ship.
- Alerts must include system track numbers, selected track details, machine
  reasoning, and machine confidence.
- The design must address storage constraints and avoid reliance on large
  region-specific pattern-of-life databases that must be expunged as operating
  areas change.
- Phase I must develop a concept and assess feasibility through modeling,
  simulation, or other means; selected methods must be explainable.
- Phase II work is probable to become classified. Advanced phases require U.S.
  ownership/operation with no foreign influence unless approved mitigations
  exist, plus ability to acquire and maintain Secret facility and personnel
  clearances.

## Representative Data Lanes

### Lane A - Public AIS Surface Traffic

Primary source: NOAA Office for Coastal Management / MarineCadastre AIS data.

Use case:

- Build surface-vessel density, corridor, loiter, stop, speed-change,
  route-deviation, and beacon-silence tests.
- Select public U.S. congested regions such as Hampton Roads/Norfolk, New York
  Harbor, Los Angeles/Long Beach, Houston/Galveston, Miami, and San Diego.
- Split by time and geography before threshold selection to prevent leakage.
- Stage raw ZIP, CSV, Parquet, or exported AccessAIS files on the external data
  volume rather than in Git or iCloud; freeze SHA-256 hashes and schema
  summaries in the repo.

Boundary:

- Public AIS does not represent SSDS organic tracks.
- AIS silence/dropout labels must be treated as source-integrity events unless
  paired with separate behavior evidence.
- AIS does not validate Navy watchstander workload, tactical displays, or
  classified operating conditions.

### Lane B - Public or Licensed ADS-B Air Traffic

Primary source candidate: OpenSky Network data access.

Use case:

- Build air-track density, route/corridor, altitude/climb/descent, orbit,
  holding-pattern, speed-change, and ADS-B source-integrity tests around
  coastal regions.
- Use only data that the company is authorized to access under OpenSky terms
  or an equivalent public/licensed ADS-B source.

Boundary:

- OpenSky access and licensing constraints must be checked before inclusion in
  a proposal budget or evaluation plan.
- ADS-B does not represent Navy air-search radar or SSDS composite tracks.
- No aircraft threat classification is claimed from ADS-B-only evaluation.

### Lane C - Notional Radar and Composite Tracks

Source path: generated low-to-medium-fidelity radar-like observations and, if
available later, authorized government-furnished assumptions or data.

Use case:

- Pair cooperative AIS/ADS-B tracks with notional radar-like or composite-track
  observations to test source disagreement, source-health estimation,
  covariance/quality fields, and identification-conflict alerting.
- Inject measurement noise, dropout, track swaps, delayed observations,
  density stress, and benign/cooperative-source failure separately from
  behavior anomalies.

Boundary:

- No public operational SSDS radar, composite-track, or display data is
  claimed.
- Radar-like tracks are representative-model inputs until authorized Navy data
  or assumptions are provided.
- Performance claims must distinguish public AIS/ADS-B validation from
  generated radar/composite-track feasibility tests.

## Evaluation Design

1. Freeze a source registry with license/terms, geographic bounds, time ranges,
   hash, schema, and exclusion reason for rejected files.
2. Partition data before threshold selection:
   - development regions/times for feature and threshold selection;
   - validation regions/times withheld until final scoring;
   - stress conditions generated separately and labeled as such.
3. Preserve source types:
   - cooperative-source state: AIS/ADS-B availability and freshness;
   - radar-like/composite state: generated or authorized assumptions;
   - behavior state: route, speed, loiter, turn, density, and local regime.
4. Report metrics by source and condition:
   - false alerts per track-hour;
   - class-level precision/recall/F1;
   - detection delay by anomaly class;
   - source-integrity review volume;
   - behavior-based threat-candidate false alerts;
   - calibration and confidence coverage;
   - memory per track and throughput/latency.
5. Preserve failure regions:
   - dense traffic;
   - source-noise shift;
   - benign beacon dropout;
   - delayed observations;
   - track identity conflict;
   - generated radar/composite mismatch;
   - regions where absolute performance remains poor.

Acceptance gates for stronger claims:

- No operational claim unless evaluated on authorized operational data.
- No SSDS integration claim unless an authorized integration environment exists.
- No adversarial robustness claim unless tested against an explicit threat
  model and independent red-team review.
- No CMMC/facility/personnel-clearance claim unless current evidence exists.
- No "threat" label from transmitter loss alone; transmitter loss can only
  trigger source-integrity review unless paired with behavior evidence.

## Ten-Page Technical Volume Conversion Plan

Target: convert `NV063_TECHNICAL_VOLUME_REVISED.md` into a compliant Volume 2
after DSIP opens and the official template is confirmed.

Proposed page budget:

| Section | Page budget | Purpose |
|---|---:|---|
| Problem and Navy relevance | 0.75 | SSDS, congested maritime/air traffic, operator fatigue, 360-degree scope. |
| Innovation | 1.00 | Compact PoL state, source-aware gates, explanations, low-storage design. |
| Technical approach | 2.25 | Inputs, state, detection/fusion, alert object, SSDS-facing concept. |
| Preliminary evidence | 1.50 | v6 frozen synthetic results plus clear evidence boundary, source-lane coverage, and failure modes. |
| Phase I Base work plan | 1.25 | Six-month tasks, deliverables, evaluation gates. |
| Phase I Option work plan | 0.75 | Six-month option and bridge to Phase II prototype. |
| Metrics and representative-data plan | 1.00 | Public AIS/ADS-B/generated radar lanes and acceptance gates. |
| Risks, transition, and commercialization | 1.00 | Synthetic gap, clearance path, SSDS transition, dual-use markets. |
| Total | 9.50 | Reserve about 0.5 page for template overhead and final formatting. |

Formatting checklist:

- Use the official DON Technical Volume template if available in DSIP or Navy
  forms/templates.
- Keep single-column format.
- Use 8.5 x 11 inch pages with 1-inch margins.
- Use at least 10-point font.
- Keep Base and Option tasks clearly separated inside the 10 pages.
- Do not rely on Volume 5 for technical reports, benchmark output, resumes, or
  publications.
- Treat the scorecard and manifests as internal/source evidence unless the
  final instructions explicitly allow attachment or reference.

## Immediate Package Edits

1. Completed: created `NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.md` as a
   compact Navy Volume 2-style source draft.
2. Completed: included concise representative-data lanes in the Volume 2-style
   source without bloating the technical narrative.
3. Completed: added an explicit format target, Base/Option split, and
   no-upload submission boundary.
4. Completed: added a live-probed AIS pilot source registry and size gate for
   NOAA daily CSV ZIP and analysis-ready GeoParquet candidates.
5. Remaining: convert the content source into the final DSIP/Navy attachment
   after the official template is confirmed.
6. Remaining: preserve the current no-upload boundary until DSIP account, SAM,
   CMMC,
   FOCI/export, cost, and clearance-transition checks are complete.

## Sources

- Navy FY-26 Release 3 topic list:
  https://www.navysbir.com/topics26_3.htm
- SBIR.gov NV063 topic page:
  https://www.sbir.gov/topics/12759
- DSIP submission portal:
  https://www.dodsbirsttr.mil/submissions
- NOAA MarineCadastre AIS data:
  https://coast.noaa.gov/digitalcoast/tools/ais.html
- OpenSky Network data access:
  https://opensky-network.org/data
  and https://opensky-network.org/data/trino
