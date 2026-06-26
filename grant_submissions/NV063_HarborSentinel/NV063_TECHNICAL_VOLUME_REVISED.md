# HarborSentinel

## Explainable Low-Storage Pattern-of-Life Detection for Congested Maritime Environments

**Topic:** DON26BZ03-NV063  
**Program:** Navy SBIR 2026 Release 3 Phase I  
**Status:** Working technical draft; not approved for submission

## 1. Technical Problem

Ship Self-Defense System watch teams must identify anomalous and potentially
threatening surface and air contacts while operating in congested regions.
Relevant observations may include cooperative AIS and ADS-B broadcasts,
notional radar contacts, and fused composite tracks. A threat may blend into
normal traffic, stop broadcasting, deviate from a common route, exhibit an
unusual kinematic pattern, or create inconsistent cooperative and
non-cooperative observations.

The operational challenge is not simply classification. A useful capability
must:

- evaluate all relevant surface and air traffic in a 360-degree area;
- operate without a massive onboard historical pattern-of-life database;
- adapt when the ship enters a new operating area;
- preserve track identity and evidence;
- explain why an alert was generated;
- report machine confidence; and
- provide an integration path to SSDS operator displays and composite tracks.

## 2. Innovation

HarborSentinel is a streaming pattern-of-life engine that maintains a compact,
multi-timescale state for each track instead of retaining a large regional
history. It fuses cooperative broadcasts and radar-like observations, tests
route, kinematic, silence, and source-consistency hypotheses, and emits an
operator-review alert containing:

- system or local track number;
- contact description and source status;
- anomaly type and supporting observations;
- machine confidence and uncertainty;
- competing benign explanations; and
- a recommended operator review action.

The innovation is the combination of bounded per-track state, source-aware
consistency checks, adaptive but poison-resistant reference windows, and an
audit-ready explanation record. The engine is designed to learn enough local
structure to detect deviations without requiring the combat system to store
large region-specific traffic archives.

## 3. Technical Approach

### 3.1 Input and Track Normalization

Phase I will define an unclassified message boundary for:

- AIS observations;
- ADS-B observations;
- notional air and surface radar contacts;
- composite or correlated tracks;
- ship position and operating-area context; and
- operator-pinned constraints and watch conditions.

Adapters will normalize source time, location, speed, heading, altitude where
applicable, identity fields, covariance or quality indicators, and source
freshness. The prototype will preserve the original observation identifiers
needed to reconstruct an alert.

### 3.2 Compact Pattern-of-Life State

Each track will maintain bounded statistics at multiple time scales:

- route and corridor deviation;
- speed, acceleration, turn, climb, and descent behavior;
- stop, loiter, orbit, and rendezvous-like behavior;
- periodicity and recurrence;
- source availability and silence duration;
- cooperative versus radar-like consistency;
- neighborhood density and local traffic regime; and
- confidence and calibration state.

Fast references detect abrupt change. Slower references resist adaptation to
persistent threats. Operator-pinned rules prevent selected conditions from
being normalized away.

### 3.3 Detection and Evidence Fusion

HarborSentinel will combine transparent rule/statistical baselines with
streaming change detection and calibrated anomaly scores. Candidate detectors
include robust z-scores, two-sided cumulative-sum tests, route-distance and
heading-change measures, source-disagreement tests, and density-adjusted local
baselines.

The fusion layer will retain disagreement rather than force premature
consensus. A disabled AIS or ADS-B transmitter is not automatically hostile;
it becomes one item of evidence whose significance depends on radar
continuity, route behavior, local rules, and nearby traffic.

### 3.4 Operator Alerting

The Phase I prototype will produce a notional SSDS-facing alert object and
operator display mockup. The interface will support:

- track identity;
- anomaly category and severity;
- concise machine-reasoning explanation;
- confidence and uncertainty;
- evidence source and freshness;
- conflicting observations;
- acknowledgment and disposition; and
- linkage back to the current tactical picture.

The prototype will not claim completed SSDS integration. It will deliver an
interface control concept, message schema, latency budget, and Phase II
integration plan.

Alerts will be labeled as source-integrity, behavioral, or combined. A
source-integrity alert can request operator review without automatically
becoming a threat candidate. This preserves evidence about missing or
disagreeing sensors while avoiding the unsupported inference that transmitter
loss alone establishes hostile intent.

## 4. Preliminary Evidence

Frozen run `20260613T_NV063_V4_FRESH_DEV20_VAL20` selected one threshold on 20
development scenarios and then held it fixed across seven disjoint validation
and stress conditions, with 20 scenarios per condition. Inputs represented
generated AIS/ADS-B and radar-like observations. Injected event classes were
route deviation, loitering, speed burst, sharp turn, beacon silence, and
beacon spoofing-like inconsistency.

In the nominal 24-track condition, the prototype produced precision 0.942,
recall 0.919, and F1 0.930, compared with F1 0.608 for a fixed kinematic-rule
comparator. It detected every injected event at least once, with median
detection delay of one simulation step and 100% explanation coverage. The
maximum counted algorithmic state was 139 bytes per track.

The frozen threshold was also tested under congestion, post-warmup sensor
noise shift, benign point and burst transmitter dropout, and combinations of
those conditions. Under combined 96-track congestion, 1.5x sensor noise, 2%
benign point dropout, and 20% benign burst dropout, review-alert F1 was 0.871
and false alerts rose to 268.1 per 10,000 normal points. Separating
source-integrity alerts from behavior-based threat candidates reduced the
corresponding threat-candidate false-alert measure to 192.4 per 10,000 normal
points.

A severe breakdown test at 192 tracks, 2.5x sensor noise, 5% point dropout,
and 35% burst dropout produced review-alert precision 0.340, F1 0.500, and
2,468.3 false alerts per 10,000 normal points. This is a measured failure
region, not an operating claim. Beacon-silence events were detected in the
nominal set, but their median delay was 11 simulation steps, materially slower
than the other classes.

**Evidence boundary:** these are deterministic synthetic software results.
They do not establish operational harbor, SSDS, sensor, adversarial,
cybersecurity, classified-environment, or field performance. The comparator
is a simple fixed kinematic rule, not a claimed state-of-the-art system. The
139-byte measure excludes Python/runtime/integration overhead. Phase I must
repeat evaluation using representative public and government-furnished data,
frozen partitions and thresholds, density-aware calibration, degraded-sensor
abstention, and independent review.

## 5. Phase I Work Plan

### Base: Months 1-6, not to exceed $200,000

**Month 1 - Requirements and frozen evaluation plan**

- Define scenarios, threat-independent anomaly taxonomy, baselines, metrics,
  data rights, and acceptance thresholds.
- Freeze train/development/test partitions before representative-data
  evaluation.

**Month 2 - Streaming state and input adapters**

- Implement AIS, ADS-B, and notional radar message adapters.
- Implement compact multi-timescale track state and source-quality tracking.

**Months 3-4 - Detection, calibration, and alert explanation**

- Implement route, kinematic, loiter, silence, and source-inconsistency
  detectors.
- Calibrate confidence and test adaptive-baseline poisoning.
- Build operator alert objects and a notional display.

**Month 5 - Congestion and failure evaluation**

- Test traffic-density scaling, delayed and missing observations, identity
  conflict, sensor disagreement, and persistent-threat conditions.
- Measure false alerts per track-hour, class-level precision/recall/F1,
  detection delay, calibration, memory, throughput, and latency.

**Month 6 - Demonstration and transition package**

- Deliver prototype, source, test harness, frozen manifests, failure register,
  interface concept, and Phase II SSDS integration roadmap.

### Option: Months 7-12, not to exceed $115,000

- Add representative-data connectors and composite-track correlation.
- Harden congestion scaling and source-disagreement handling.
- Conduct independent reproducibility and red-team review.
- Refine the SSDS-facing message and display integration specification.
- Prepare Phase II security, facility-clearance, data, and integration plans.

## 6. Metrics and Success Criteria

The proposal will report:

- precision, recall, F1, false-positive rate, and false-negative rate by event
  class;
- false alerts per track-hour and per traffic-density regime;
- event detection delay;
- confidence calibration;
- memory per track and total runtime footprint;
- throughput and end-to-end alert latency;
- alert explanation completeness;
- robustness to missing, delayed, and contradictory sources; and
- degradation under persistent or poisoning-like behavior.

No single aggregate score will conceal class failures. Seeds, thresholds,
dependency versions, input hashes, and failures will be preserved.

## 7. Risks and Mitigation

- **Synthetic-to-operational gap:** use public representative data, withheld
  scenarios, and government-furnished data when available.
- **Adaptive normalization of a persistent threat:** use multi-timescale
  references, change alarms, and operator-pinned constraints.
- **False alerts from source disagreement:** estimate source quality and show
  the disagreement in the alert rather than collapsing it.
- **Noise-shift breakdown:** use covariance-aware tracking, density/regime
  calibration, degraded-sensor detection, and abstention or confidence
  reduction outside the validated envelope.
- **Beacon-silence delay:** tune the persistence/false-alert tradeoff by source
  reliability and operational context, and report class-specific delay rather
  than hiding it in an aggregate.
- **Unknown-area operation:** bootstrap from physics, navigational constraints,
  local density, and short-horizon observations before longer references
  become available.
- **SSDS integration uncertainty:** isolate the analysis engine behind an
  explicit message schema and deliver latency/data-flow assumptions for Navy
  review.
- **Advanced-phase security:** treat facility and personnel clearance
  readiness as an explicit Phase I transition workstream.

## 8. Transition and Commercialization

The Navy transition path is an SSDS-compatible analysis service and operator
alert interface evaluated first with unclassified representative data, then
with authorized government data and integration environments. Commercial
adjacencies include port security, fleet operations, fisheries enforcement,
maritime insurers, and critical-infrastructure monitoring, but the Phase I
technical plan is driven by the Navy topic requirements.

The company must establish whether it can acquire and maintain the Secret
facility and personnel clearances required for advanced phases. No current
facility clearance is claimed in this draft.

## 9. Deliverables

- Unclassified HarborSentinel prototype and source.
- AIS/ADS-B/notional-radar adapter specification.
- Compact pattern-of-life state and detection library.
- Operator alert schema and display prototype.
- Frozen evaluation package and SHA-256 manifest.
- Failure register and claim-boundary statement.
- SSDS integration and Phase II security/clearance roadmap.
