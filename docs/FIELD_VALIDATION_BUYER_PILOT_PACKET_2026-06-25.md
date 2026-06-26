# Field Validation Buyer Pilot Packet

Generated UTC: `2026-06-26T06:35:46.946486+00:00`

This packet is for targeted manual buyer outreach and paid pilot scoping. It does not authorize bulk email, fixed-dollar frozen-delta claims, realized-savings claims, field-validation claims, live trading, or autonomous operational execution.

## Summary

- Buyer pilot packets: `2`
- Manual outreach ready: `2`
- Bulk email allowed: `false`
- Fixed-dollar delta claim allowed: `false`
- Field-validation claim allowed: `false`
- Kuramoto holdout ready for field replay request: `true`
- Kuramoto holdout wins vs Kalman: `24/24`
- Packet chain SHA-256: `3406e3bec6b902b836d9433d5448139f778fd942fd1ce86da5bde5f7901477a4`

## Packets

### `brachistochrone_descent`

- Pilot: Constrained Transport / Routing Replay Pilot
- Lane: `optimal_curve_transport`
- Evidence stage: `ready_for_buyer_authorized_pilot_scoping`
- Evidence strength score: `182.749`
- Buyer pain: constraint-heavy routing, dispatch, airflow, or recovery decisions where small path-quality changes can reduce time, exposure, energy, or operator burden
- Pilot question: Can the brachistochrone-style candidate beat incumbent route/path baselines on pre-registered buyer holdout windows without violating constraints?
- Field replay request: buyer-authorized field replay on pre-registered holdout windows
- Paid offer: paid technical evaluation or buyer-authorized pilot scoping
- Pricing status: `quote_after_fit_call_and_data_scope`
- Priority buyer titles:
  - Director of Grid Analytics
  - Infrastructure Optimization Lead
  - Port Operations Analytics Lead
  - Datacenter Cooling Optimization Lead
  - R&D Program Manager for Critical Infrastructure
- Deliverables:
  - buyer-specific data checklist
  - pre-registered holdout and baseline plan
  - candidate replay against incumbent and named baselines
  - uncertainty and failure-mode report
  - claim-boundary memo separating proven evidence from unproven commercial claims
  - pilot result artifact with hashable chain references
- Pre-call questions:
  - What operational decision or forecast would you want this to improve?
  - What incumbent baseline does your team trust today?
  - Can you provide at least 20 pre-registered holdout windows?
  - Which measured outcome would make the pilot worth continuing?
  - Which guardrail failure would stop the pilot immediately?
  - Who can approve use of field data and economic conversion factors?

Email subject:

```text
Paid pilot scoping: Constrained Transport / Routing Replay Pilot
```

First email:

```text
Hello [Name],

I am Robert Ashworth, inventor of the LumenCore/NovaCore frozen evidence framework. I am reaching out because your team works near constraint-heavy routing, dispatch, airflow, or recovery decisions where small path-quality changes can reduce time, exposure, energy, or operator burden.

The current evidence is not a field-validation or savings claim. It is a narrower pilot-scoping signal:
- Candidate: brachistochrone_descent
- Lane: optimal_curve_transport
- Repeat-window evidence: 7/7 positive frozen replay windows
- Lower 95% score-margin estimate: 0.072454

- Current technical question: Can the brachistochrone-style candidate beat incumbent route/path baselines on pre-registered buyer holdout windows without violating constraints?

I am looking for one paid technical evaluation or buyer-authorized pilot where we replay the candidate against your incumbent baselines on pre-registered holdout windows. The output would be a claim-bounded evidence report: what improved, what failed, what cannot yet be claimed, and what would be required for a procurement-grade validation.

Would you be open to a 20-minute technical fit call this week?

Best,
Robert Ashworth
[Organization / LumenCore]
[Website or proof portal link]
[Physical mailing address]

To stop further outreach, reply "remove."
```

### `kuramoto_phase_coupling`

- Pilot: Wave / Resonance Timing Forecast Pilot
- Lane: `wave_resonance_timing`
- Evidence stage: `ready_for_buyer_authorized_pilot_scoping`
- Evidence strength score: `180.19`
- Buyer pain: oscillatory or cyclic systems where earlier timing, lower phase error, or better drift detection can reduce missed events and manual review
- Pilot question: Can the Kuramoto-style candidate beat incumbent timing/forecast baselines on pre-registered buyer holdout windows?
- Field replay request: buyer-authorized field replay on pre-registered holdout windows
- Paid offer: paid technical evaluation or buyer-authorized pilot scoping
- Pricing status: `quote_after_fit_call_and_data_scope`
- Priority buyer titles:
- Expanded internal holdout evidence:
  - Wins vs `kalman_filter`: `24/24`
  - Mean delta vs `kalman_filter`: `0.139875`
  - Estimated rows replayed: `2506267`
  - Source systems: `4`
  - Internal 20-holdout gate passed: `true`
  - Holdout chain SHA-256: `b723b3cf65d3971b0492e41cc27fc82e1fba57a5e0d672a67e9818348313f2e6`
  - Boundary: internal source-conditioned replay, not field validation or a dollar claim.
  - Energy Forecasting Lead
  - Grid Reliability Analytics Lead
  - Sensor Fusion Program Manager
  - Industrial Process Stability Lead
  - R&D Program Manager for Cyber-Physical Systems
- Deliverables:
  - buyer-specific data checklist
  - pre-registered holdout and baseline plan
  - candidate replay against incumbent and named baselines
  - uncertainty and failure-mode report
  - claim-boundary memo separating proven evidence from unproven commercial claims
  - pilot result artifact with hashable chain references
- Pre-call questions:
  - What operational decision or forecast would you want this to improve?
  - What incumbent baseline does your team trust today?
  - Can you provide at least 20 pre-registered holdout windows?
  - Which measured outcome would make the pilot worth continuing?
  - Which guardrail failure would stop the pilot immediately?
  - Who can approve use of field data and economic conversion factors?

Email subject:

```text
Paid pilot scoping: Wave / Resonance Timing Forecast Pilot
```

First email:

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

- Send manually only to reviewed contacts.
- Do not run bulk outreach from this packet.
- Do not claim fixed-dollar value per frozen delta.
- Do not claim field validation or realized savings until a buyer-authorized pilot produces that evidence.
