# Kuramoto Field Replay Request

Generated UTC: `2026-06-29T16:50:22.653142+00:00`

Convert the strongest current internal replay result into a buyer-authorized field replay request. This is a validation ask, not a completed field-validation claim.

## Summary

- Candidate: `kuramoto_phase_coupling`
- Lane: `wave_resonance_timing`
- Status: `ready_to_request_field_replay_not_yet_field_validated`
- Internal holdout wins vs Kalman: `24/24`
- Mean delta vs Kalman: `0.139875`
- Estimated rows replayed: `2506267`
- Source systems: `4`
- Wilson lower 95% win-rate bound: `0.862024`
- Holdout chain SHA-256: `b723b3cf65d3971b0492e41cc27fc82e1fba57a5e0d672a67e9818348313f2e6`
- Manual outreach allowed: `true`
- Bulk email allowed: `false`

## Why It Matters

The evidence says this candidate is worth taking to a real owner-controlled replay. It does not say the candidate is already field validated. The next value step is to let a buyer or agency control the holdout data, accepted baseline, metrics, and result interpretation.

## What We Can Ask For Now

Authorize a field replay on pre-registered holdout windows so kuramoto_phase_coupling can be compared against the buyer's accepted incumbent baseline.

Technical question: Can the Kuramoto-style candidate beat incumbent timing/forecast baselines on pre-registered buyer holdout windows?

Buyer roles:
- Energy Forecasting Lead
- Grid Reliability Analytics Lead
- Sensor Fusion Program Manager
- Industrial Process Stability Lead
- R&D Program Manager for Cyber-Physical Systems

Data required:
- timestamped oscillatory or cyclic measurements
- incumbent forecast, filter, or timing-control baseline
- measured downstream outcome such as error, drift, outage lead time, or intervention cost
- known exogenous event markers where available
- holdout windows selected before model scoring

Baseline controls:
- `kalman_filter`
- `fft_peak_tracker`
- `arima_or_ets_forecast`
- `pll_phase_tracker`
- `seasonal_naive_forecast`

Primary KPIs:
- `candidate_score_delta_vs_named_baseline`
- `forecast_error_delta`
- `phase_error_delta`
- `lead_time_delta`
- `false_alarm_or_missed_event_delta`

## Evidence

- Holdout count: `24`
- Wins vs `kalman_filter`: `24`
- Losses or ties vs `kalman_filter`: `0`
- Estimated rows replayed: `2506267`
- Numeric samples read: `66690`
- Source systems: `energy_grid, macro_rates_labor, market_data, sports_market`
- Chain SHA-256: `b723b3cf65d3971b0492e41cc27fc82e1fba57a5e0d672a67e9818348313f2e6`

## Buyer Replay Protocol

Acceptance gate:

```json
{
  "maximum_constraint_violation_rate": "buyer_defined_before_pilot",
  "minimum_candidate_win_rate": 0.6,
  "minimum_holdout_windows": 20,
  "minimum_independent_source_or_sensor_count": 3,
  "minimum_lower_95_delta": 0.0,
  "minimum_wilson_lower_95_win_rate": 0.5,
  "required_result": "candidate must beat named baselines on pre-registered holdout windows without guardrail failure"
}
```

Pre-call questions:
- What operational decision or forecast would you want this to improve?
- What incumbent baseline does your team trust today?
- Can you provide at least 20 pre-registered holdout windows?
- Which measured outcome would make the pilot worth continuing?
- Which guardrail failure would stop the pilot immediately?
- Who can approve use of field data and economic conversion factors?

## Manual Email Copy

Subject: Paid pilot scoping: Wave / Resonance Timing Forecast Pilot

```text
Hello [Name],

I am Robert Ashworth, inventor of the LumenCore/NovaCore frozen evidence framework. I am reaching out because your team works near oscillatory or cyclic systems where earlier timing, lower phase error, or better drift detection can reduce missed events and manual review.

The current evidence is not a field-validation or savings claim. It is a narrower pilot-scoping signal:
- Candidate: kuramoto_phase_coupling
- Lane: wave_resonance_timing
- Repeat-window evidence: 24/24 positive frozen replay windows
- Lower 95% score-margin estimate: 0.044697
- Expanded internal holdout: 24/24 wins vs kalman_filter
- Mean delta vs kalman_filter: 0.139875
- Estimated rows replayed: 2506267
- Holdout chain SHA-256: b723b3cf65d3971b0492e41cc27fc82e1fba57a5e0d672a67e9818348313f2e6
- Current technical question: Can the Kuramoto-style candidate beat incumbent timing/forecast baselines on pre-registered buyer holdout windows?

I am looking for one paid technical evaluation or buyer-authorized pilot where we replay the candidate against your incumbent baselines on pre-registered holdout windows. The output would be a claim-bounded evidence report: what improved, what failed, what cannot yet be claimed, and what would be required for a procurement-grade validation.

Would you be open to a 20-minute technical fit call this week?

Best,
Robert Ashworth
[Organization / LumenCore]
[Website or proof portal link]
[Physical mailing address]

To stop further outreach, reply "remove."
```

## Claim Boundary

The current result supports a manual request for buyer-authorized replay. It does not prove external operational performance until the buyer controls the data, baseline, holdout windows, logs, and result interpretation.

- Field-validation claim allowed: `false`
- Realized savings claim allowed: `false`
- Fixed-dollar delta value claim allowed: `false`
- Live trading claim allowed: `false`

No-go claims:
- `field validated`
- `guaranteed savings`
- `$10k per frozen delta`
- `guaranteed trading edge`
- `proven institutional profit`
- `medical treatment claim`

Packet SHA-256: `90ca642e99c8239d50907cc5576789c3f6f5cac46e94111f0007b09f5098952b`
