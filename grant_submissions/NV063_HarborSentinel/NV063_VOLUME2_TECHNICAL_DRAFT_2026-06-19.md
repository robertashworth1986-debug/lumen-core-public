# HarborSentinel Volume 2 Technical Draft

Topic: DON26BZ03-NV063, Anomalous Behavior Detection and Alerting for
Congested Maritime Environments

Program: Navy SBIR 2026 Release 3 Phase I

Status: Working draft for DSIP/Navy Volume 2 conversion; not approved for
submission.

Format target: single-column Phase I Technical Volume, 8.5 x 11 inch pages,
1-inch margins, no font smaller than 10 point, not to exceed 10 pages. Base
and Option work are both included here. This Markdown file is a content source,
not the final uploaded attachment.

## 1. Objective and Navy Need

HarborSentinel will develop and assess an explainable, low-storage
pattern-of-life engine for identifying anomalous surface and air contacts in
congested maritime environments. The objective is to help Ship Self-Defense
System (SSDS) watch teams review all relevant traffic in a 360-degree area
around a notional ship while preserving source identity, machine reasoning,
confidence, and operator-review context.

The Navy problem is not just classification. A useful system must detect
deviation, loitering, unusual kinematics, source loss, source conflict, and
cooperative/non-cooperative inconsistency without relying on a massive
region-specific pattern-of-life archive that becomes unusable when the ship
changes operating areas. The Phase I goal is a feasible unclassified prototype,
test harness, alert schema, and transition plan, not a completed SSDS
integration.

## 2. Technical Innovation

HarborSentinel maintains compact multi-timescale state per track rather than
retaining large historical databases. It normalizes AIS, ADS-B, notional radar,
and composite-track observations into a source-aware track record, then tests
route, kinematic, silence, and source-consistency hypotheses. Alerts are
structured for operator review and include track identity, anomaly category,
supporting observations, source freshness, machine confidence, uncertainty,
and competing benign explanations.

The innovation is the combination of:

- bounded per-track and local-regime state for low-storage operation;
- source-aware consistency checks across cooperative and radar-like inputs;
- adaptive reference windows with poison-resistance and operator-pinned
  constraints;
- source-integrity review that does not convert transmitter loss alone into a
  threat label; and
- audit-ready explanation records that can be replayed from frozen inputs,
  thresholds, source metadata, and manifests.

## 3. Technical Approach

### 3.1 Inputs and Unclassified Boundary

Phase I will define an unclassified input and output boundary for AIS
observations, ADS-B observations, notional air and surface radar contacts,
composite or correlated tracks, ship position, operating-area context, and
operator-pinned watch conditions. Adapters will normalize time, location,
speed, heading, altitude when applicable, identity fields, covariance or
quality indicators, and source freshness. Original observation identifiers
will be retained so each alert can be reconstructed.

No current draft claims access to Navy radar, classified sensor data, SSDS
interfaces, operational harbor feeds, or government-furnished data. Those
items are Phase II or government-authorized evaluation paths.

### 3.2 Compact Pattern-of-Life State

For each track, the prototype will maintain bounded statistics at multiple
time scales: corridor deviation, speed, acceleration, turn, climb/descent,
stop/loiter/orbit behavior, periodicity, source availability, cooperative
versus radar-like consistency, neighborhood density, local traffic regime, and
confidence calibration. Fast references detect abrupt changes while slower
references resist normalization of persistent threats.

### 3.3 Detection, Fusion, and Alerting

Candidate detectors include robust z-scores, two-sided cumulative-sum tests,
route-distance measures, heading-change measures, source-disagreement tests,
and density-adjusted local baselines. The fusion layer will retain
disagreement instead of forcing premature consensus. A disabled AIS or ADS-B
transmitter becomes source-integrity evidence for review; it is not by itself
a behavior-based threat candidate.

The prototype will emit a notional SSDS-facing alert object and operator
display concept with track identity, severity, source status, machine
reasoning, confidence, uncertainty, conflicting observations, acknowledgment,
disposition, and linkage back to the current tactical picture. The Phase I
deliverable is an interface-control concept, message schema, latency budget,
and Phase II integration plan, not completed combat-system integration.

## 4. Phase I Feasibility Evidence

The current feasibility evidence is a deterministic synthetic software
benchmark, not field validation. Frozen run
`20260619T_NV063_V6_SOURCE_LANE_COVERAGE` selected threshold 10.0 on 20
development scenarios and held that threshold fixed across seven validation
and stress conditions, with 30 scenarios per condition. Inputs modeled
generated AIS-like surface cooperative beacons, ADS-B-like air cooperative
beacons, and notional radar-like observations. Injected events were route
deviation, loitering, speed burst, sharp turn, beacon silence, and
beacon-spoofing-like inconsistency.

The nominal 24-track condition produced precision 0.948, recall 0.957, and
F1 0.952, compared with F1 0.566 for a simple fixed kinematic-rule comparator.
All injected event classes were detected at least once, explanation coverage
was 1.000, median detection delay was one simulation step, and nominal
beacon-silence median delay was four simulation steps.

Under combined 96-track congestion, 1.5x sensor noise, 2% benign point
dropout, and 20% benign burst dropout, review-alert F1 was 0.927 with 144.9
review false alerts per 10,000 normal points. Separating source-integrity
review from behavior-based threat candidates reduced the corresponding
threat-candidate false-alert measure to 76.5 per 10,000 normal points.

A severe stress condition at 192 tracks, 2.5x sensor noise, 5% point dropout,
and 35% burst dropout produced review-alert precision 0.865, F1 0.888, and
191.9 review false alerts per 10,000 normal points. The behavior-based
threat-candidate false-alert measure was 77.0 per 10,000 normal points because
source failure remained separated from hostile-intent inference. Source-lane
coverage was also reported: nominal AIS-like availability 0.960, ADS-B-like
availability 1.000, and radar-like availability 1.000; severe-stress AIS-like
availability 0.904 and ADS-B-like availability 0.945.

The public AIS lane has also been exercised on a frozen NOAA AIS New Orleans /
Mississippi River Delta development/validation split. The raw NOAA daily AIS
ZIP was rehydrated into private local storage, hashed to the same SHA-256 value
as the prior external-drive acquisition, and rebuilt into 50,000-row
development and 50,000-row validation splits with the same deterministic
sampling rule and the same split SHA-256 values. A current I/O preflight
returned 2/2 split files readable with full-file SHA-256 matching the frozen
split manifest. The controlled-injection benchmark built
48,624 development segments and 48,616 validation segments, then evaluated
20,000 injected validation segments across speed burst, position jump, heading
snap, and consistency-gap families. The frozen development-threshold
motion-consistency detector achieved 1.0000 recall on those controlled
injections versus 0.25835 recall for a reported-speed-only baseline and
0.5068 for the best single-axis baseline (`speed_gap_consistency_p99`). This
is detector-vs-baseline evidence on controlled kinematic perturbations, not
real adversary labeling or a false-positive-rate estimate.

Evidence boundary: these are generated software results. They do not establish
operational harbor performance, SSDS integration, sensor-feed performance,
adversarial security, cybersecurity, classified-environment performance, or
field performance. Phase I must repeat evaluation with representative public
and authorized government data, frozen partitions, density-aware calibration,
degraded-source review or abstention, and independent review.

## 5. Phase I Base Work Plan, Months 1-6

Base budget target: not to exceed $200,000.

Task 1, Requirements and evaluation plan: define the unclassified message
boundary, anomaly taxonomy, baselines, source rights, metrics, acceptance
thresholds, and failure criteria. Freeze development and validation partitions
before representative-data scoring.

Task 2, Input adapters and compact state: implement AIS, ADS-B, notional radar,
and composite-track adapter interfaces. Implement bounded multi-timescale
track state, source freshness, source-quality indicators, and replayable
observation identifiers.

Task 3, Detection and calibration: implement route, kinematic, loiter, silence,
source-disagreement, and density/regime detectors. Calibrate confidence and
test adaptive-baseline poisoning, delayed observations, identity conflict,
benign transmitter dropout, and source-noise shift.

Task 4, Operator alert prototype: build alert objects and a notional display
concept showing track identity, source status, anomaly category, supporting
observations, confidence, uncertainty, competing benign explanations, and
recommended operator review action.

Task 5, Feasibility evaluation: evaluate synthetic and representative data
lanes using frozen thresholds and partitions. Report class-level
precision/recall/F1, false alerts per track-hour and traffic-density regime,
detection delay, calibration, source-integrity review volume, memory, runtime,
and latency.

Task 6, Demonstration and transition package: deliver prototype source, test
harness, frozen manifests, failure register, interface-control concept,
latency/data-flow assumptions, and Phase II SSDS integration roadmap.

Milestones and success criteria: by Month 1, freeze the unclassified message
schema, evaluation taxonomy, source-rights register, and baseline metrics; by
Month 2, demonstrate replayable AIS/ADS-B/notional-radar adapters; by Month
3, demonstrate bounded per-track state and candidate detectors; by Month 4,
emit explainable alert objects and a notional operator display; by Month 5,
run frozen synthetic plus representative-data evaluations with unchanged
thresholds; and by Month 6, deliver the prototype, manifest, failure register,
and transition package. Phase I success means reproducible evidence for
source-aware anomaly review under defined public/authorized data lanes,
density regimes, noise/dropout conditions, false-alert limits, delay,
calibration, memory, runtime, and latency. It does not mean SSDS integration,
classified sensor validation, operational threat classification, or CMMC/
clearance readiness.

## 6. Phase I Option Work Plan, Months 7-12

Option budget target: not to exceed $115,000.

The Option will add representative-data connectors, improve composite-track
correlation, harden congestion scaling, refine source-disagreement handling,
conduct independent reproducibility and red-team review, mature the
SSDS-facing message/display specification, and prepare Phase II data,
security, facility-clearance, and integration plans.

## 7. Representative Data and Evaluation Plan

The representative-data path will keep source lanes separate so public
cooperative-source validation is not confused with SSDS radar or composite
track validation.

Lane A, public AIS: use NOAA/MarineCadastre AIS data where permitted to test
surface density, corridors, route deviation, stop/loiter behavior,
speed-change, and AIS source-integrity handling. AIS does not validate Navy
organic tracks or SSDS displays.

Lane B, public or licensed ADS-B: use OpenSky or equivalent authorized ADS-B
access where terms permit to test air-track density, route/corridor behavior,
altitude/climb/descent, orbit/holding patterns, speed change, and ADS-B
source-integrity handling. ADS-B does not represent Navy air-search radar.

Lane C, notional radar and composite tracks: use generated low-to-medium
fidelity radar-like observations and later government-furnished assumptions or
data if authorized. Performance claims will distinguish generated
radar/composite feasibility from public AIS/ADS-B evaluation and from any
future government-authorized operational evaluation.

Acceptance gates for stronger claims: no operational claim without authorized
operational data; no SSDS integration claim without an authorized integration
environment; no adversarial robustness claim without an explicit threat model
and independent red-team review; and no CMMC, facility-clearance, or
personnel-clearance claim without current evidence.

## 8. Risks and Mitigations

Synthetic-to-operational gap: repeat evaluation on public AIS, authorized
ADS-B, and government-furnished assumptions or data when available.

Persistent-threat normalization: use multi-timescale references, change
alarms, and operator-pinned constraints to prevent selected behavior from
being normalized away.

False alerts from source disagreement: estimate source quality and display the
disagreement rather than collapsing it into a threat label.

Noise-shift breakdown: extend the v6 source-quality gate with covariance-aware
tracking, density/regime calibration, and explicit abstention or confidence
reduction outside the validated envelope.

Beacon-silence tradeoff: tune persistence thresholds by source reliability and
operational context, and report class-specific delay rather than hiding it in
an aggregate.

Advanced-phase security: treat projected CMMC Level 2 (Self), SPRS, FCI/CUI,
FOCI/export, U.S. ownership/operation, and Secret facility/personnel clearance
planning as explicit transition gates. No current clearance or CMMC status is
claimed here.

## 9. Transition and Commercialization

The Navy transition path is an SSDS-compatible analysis service and operator
alert interface evaluated first with unclassified representative data, then
with authorized government data and integration environments. Phase I will
produce the interface-control concept, alert schema, evaluation evidence, and
security transition plan needed for Navy review.

Commercial adjacencies include port security, fleet operations, fisheries
enforcement, maritime insurance, and critical-infrastructure monitoring.
These markets need explainable, low-storage anomaly review in congested
traffic, but the Phase I plan remains driven by the Navy topic requirements.

## 10. Deliverables

- Unclassified HarborSentinel prototype and source.
- AIS/ADS-B/notional-radar adapter specification.
- Compact pattern-of-life state and detection library.
- Operator alert schema and display concept.
- Frozen evaluation package with SHA-256 manifest.
- Failure register and claim-boundary statement.
- Representative-data source registry and partition plan.
- SSDS integration concept and Phase II security/clearance roadmap.

## 11. Submission Boundary

Do not upload this draft until DSIP account authority, SAM.gov status, DoD
representations, cost basis, export/FOCI/cybersecurity checks, CMMC/SPRS
status, clearance-transition plan, final template formatting, and human
approval are complete.
