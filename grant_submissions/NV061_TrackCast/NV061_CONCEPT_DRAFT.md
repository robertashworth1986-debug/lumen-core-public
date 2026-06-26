# TrackCast Concept Draft

**Topic:** DON26BZ03-NV061, Predictive Movement for Object Oriented Tracking  
**Program:** Navy SBIR 2026 Release 3 Phase I  
**Status:** concept draft; not approved for submission

## 1. Problem

Maritime targeting analysts must maintain custody and priority across a large,
heterogeneous object population while observations arrive from sources with
different latency, reliability, and coverage. A useful Phase I solution must
do more than extrapolate one track: it must represent uncertainty, distinguish
ordinary maneuver from meaningful change, prioritize review, and scale as
sources and objects increase.

## 2. Proposed Innovation

TrackCast is a streaming, uncertainty-calibrated movement and priority engine
with five coupled functions:

1. **Source-aware track state:** maintain compact state, source freshness,
   disagreement, covariance, and identity confidence for each object.
2. **Motion-mode ensemble:** compare constant-velocity, constant-turn,
   route-conditioned, and locally learned motion hypotheses rather than force
   one universal predictor.
3. **Regime and change detection:** identify when forecast residuals indicate a
   maneuver, route departure, source failure, or a new pattern-of-life regime.
4. **Calibrated abstention:** return a wider interval or “insufficient
   evidence” when the source mix or motion regime is outside the validated
   envelope.
5. **Hierarchical prioritization:** combine forecast uncertainty, meaningful
   change, custody risk, source quality, and mission-configurable rules into an
   explainable review priority.

The research hypothesis is that motion-mode selection plus explicit
uncertainty and change detection can improve custody and analyst prioritization
over single-model extrapolation under heterogeneous, delayed, and missing
observations. Phase I will test that hypothesis; this draft does not assert it
has already been proven.

## 3. Required Baselines

Evaluation will compare TrackCast against:

- persistence and last-observation baselines;
- constant-velocity and constant-acceleration Kalman filters;
- interacting multiple-model tracking;
- route-conditioned nearest-neighbor or historical-pattern baselines; and
- a simple fixed-rule prioritization score.

All model selection and thresholds will use development-only data. Final
results will be reported on frozen, disjoint scenarios and representative
public data with uncertainty calibration, per-regime errors, and failures.

## 4. Phase I Plan

**Month 1 - Evaluation contract**

- Define object, observation, custody, forecast, and priority schemas.
- Freeze metrics, data partitions, source-quality assumptions, and failure
  conditions.

**Month 2 - Baselines and adapters**

- Implement public AIS/ADS-B adapters and low/medium-fidelity generated
  trajectories.
- Implement kinematic and historical-pattern baselines.

**Months 3-4 - TrackCast prototype**

- Implement motion-mode ensemble, source-quality state, uncertainty intervals,
  change detection, and explainable priority.
- Add delayed, missing, contradictory, and identity-ambiguous observations.

**Month 5 - Stress and scale evaluation**

- Test congestion, route changes, maneuvers, source dropout, noise shift, and
  previously unseen regimes.
- Measure forecast error by horizon, interval coverage, custody loss,
  change-detection delay, false priority escalation, throughput, and memory.

**Month 6 - Demonstration and transition package**

- Deliver prototype, frozen test package, failure register, interface concept,
  and an advanced-phase data/security plan.

## 5. Preliminary Evidence and Boundary

The existing HarborSentinel benchmark demonstrates reproducible generated
AIS/ADS-B and radar-like streaming, compact per-track state, source-integrity
versus behavioral alert separation, and class-level anomaly evaluation. It is
useful infrastructure for TrackCast.

It is not evidence that TrackCast predicts real maritime movement accurately.
The existing leakage-resistant V7 forecasting work did not show a repeatable
universal improvement and will not be cited as maritime alpha. A
trajectory-specific benchmark and representative public data evaluation are
required before making a predictive-performance claim.

## 6. Metrics

- position error by forecast horizon and motion regime;
- negative log likelihood or proper probabilistic score;
- prediction-interval coverage and width;
- track-custody loss and reacquisition time;
- maneuver/change-detection precision, recall, and delay;
- false priority escalations per track-hour;
- top-k priority recall for defined events;
- throughput, latency, and state per track; and
- performance under missing, delayed, contradictory, and shifted sources.

## 7. Risks

- **No representative Navy data:** begin with public AIS/ADS-B and generated
  cases; document domain gaps and request authorized data only through approved
  channels.
- **Unseen maneuvers:** use uncertainty expansion and abstention rather than
  confident extrapolation.
- **Identity ambiguity:** separate identity confidence from movement
  confidence and preserve competing hypotheses.
- **False prioritization:** expose reasons and allow mission-configurable
  thresholds with operator override.
- **Advanced-phase classification:** do not claim a current facility
  clearance; create a realistic acquisition and safeguarding plan before
  submission.

## 8. Commercialization

Potential unclassified markets include port operations, fleet management,
search and rescue, fisheries monitoring, insurance risk, and logistics.
Commercial claims require customer discovery and representative-data
validation; none is implied by this concept draft.
