# First Buyer Target Board

Generated UTC: `2026-07-29T08:01:55.624742+00:00`

First-buyer target board. This artifact selects named, source-verified buyer channels for a manual paid evidence review or buyer-authorized field replay. It does not authorize auto-send, bulk outreach, contact scraping, fixed frozen-delta pricing, field-validation claims, realized-savings claims, live trading, or autonomous operational execution.

## Decision

- First buyer channel: `None`
- Channel type: `None`
- First action: Verify one current official channel, reconcile duplicate-send history, select a real recipient, and obtain exact action-time approval before outreach.
- Send without user review: `false`
- Bulk email allowed: `false`
- Field-validation claim allowed: `false`
- Realized-savings claim allowed: `false`

## Proof Snapshot

- Internal performance champion present: `false`
- Measured reference candidate: `Kuramoto phase coupling`
- Development-selected candidate: `lissajous_phase_paths`
- Reference candidate was protocol-selected: `false`
- Named baseline: `kalman_local_linear_trend`
- Holdout wins: `482/1525`
- Mean skill delta: `-0.508191`
- Reference measured rows replayed: `15,250`
- Reference source systems: `1`
- Broader measured providers: `25/29`
- Compatibility-gated sweep: `4` routes, `22` comparisons, `0` global positives, `32,608` performance rows
- Live-domain hash verified: `false`
- Business plan PDF: `C:\Users\Novac\iCloudDrive\Business plan\LumenCore_Business_Plan_Investor_Ready_UPDATED_2026-07-03.pdf`
- Stress matrix feed: https://lumen-core.ai/data/champion_stress_test_matrix.json

## Ranked Buyer Targets

### 1. EPRI AI for Power / Incubatenergy Labs

- Buyer role: AI for Power / Incubatenergy Labs program reviewer
- Fit score: `98`
- Why first: Highest leverage: one accepted demo path can expose the proof stack to multiple utilities and AI/power decision makers without pretending LumenCore is field validated already.
- First ask: Request a late technical fit review or next-cycle demo intake: a paid evidence review that uses EPRI/utility-approved baseline, holdout windows, and pass/fail metrics.
- Data needed: utility-owned time-series operating data, incumbent forecast/filter baseline, pre-registered holdout windows, accepted reliability or forecast-error metric, economic conversion factors only after technical replay passes
- Send now allowed: `false`
- Sources:
  - https://epri.brightidea.com/community/iel - Incubatenergy Labs, powered by EPRI, runs quick paid demonstrations with leading utilities, typically within 16 weeks.
  - https://epri.brightidea.com/AIforPower2026 - AI for Power 2026 connects energy companies, technology providers, and utilities through real-world demonstration projects; pitch day is listed for August 5, 2026.
  - https://openpowerai.org/ - Open Power AI describes the AI for Power Challenge as a pathway for utilities, EPRI, and technology providers to collaborate, test, validate, and de-risk AI solutions.

### 2. EPB Chattanooga / ORNL grid resilience research path

- Buyer role: Grid reliability analytics or microgrid research lead
- Fit score: `96`
- Why first: Most concrete field-validation fit: EPB has an automated grid, microgrid research, real-time usage data, and a stated history of testing controls and sensor systems with ORNL.
- First ask: Ask for a 20-minute local technical fit call to scope a sealed replay on historical outage, reroute, or microgrid time-series windows.
- Data needed: historical feeder/microgrid event windows, current automated-grid decision or forecast baseline, outage-minute, reroute-time, or false-alarm metric, guardrails for no operational control, approved anonymization and data-use terms
- Send now allowed: `false`
- Sources:
  - https://epb.com/energy/automated-grid/ - EPB reports an Automated Grid with outage-minute reduction, real-time usage data, microgrid research, and seconds-scale rerouting.
  - https://epb.com/newsroom/press-releases/microgrid-research-partnership/ - EPB and ORNL describe a long-running partnership to test and deploy innovative controls, sensor systems, building energy models, security, and quantum/supercomputing grid platforms.

### 3. TVA / Spark Cleantech Accelerator bridge

- Buyer role: TVA ecosystem partnerships, future grid performance, or Spark accelerator reviewer
- Fit score: `94`
- Why first: Strong regional fit: TVA's technology priorities include future grid performance and regional grid transformation, while Spark offers customer, partner, TVA, and ORNL connections.
- First ask: Ask Spark/TVA for a technical mentor review and a route to one buyer-approved replay dataset or pilot sponsor.
- Data needed: regional grid planning or forecasting dataset, current planning/forecast baseline, accepted operational KPI, pilot sponsor and data-rights path
- Send now allowed: `false`
- Sources:
  - https://www.tva.com/energy/technology-innovation/future-grid-performance - TVA identifies future grid performance challenges tied to renewables, storage, weather-dependent resources, and inverter-based resources.
  - https://www.tnresearchpark.org/tva-%F0%9F%A4%9D-spark-cleantech-accelerator/ - TVA sponsors Spark Cleantech Accelerator activity aligned with future grid performance, regional grid transformation, storage integration, and pilot commercialization.
  - https://www.tnresearchpark.org/spark/accelerator/ - Spark Accelerator offers mentorship, prototyping, customer and partner connections, and partnership opportunities including TVA and ORNL.

### 4. DOE GRIP ecosystem partner

- Buyer role: Utility, local government, or grid-resilience project lead seeking software evidence
- Fit score: `88`
- Why first: GRIP is not a direct buyer, but it points to the exact class of utilities and public-sector partners funded for grid flexibility, resilience, reliability, and early measurable impacts.
- First ask: Use the proof stack as a subcontractor/pilot module in a utility or local-government GRIP-style resilience project.
- Data needed: project-owned grid reliability dataset, grant-recognized resilience metric, field replay authorization, awardee or applicant partner signoff
- Send now allowed: `false`
- Sources:
  - https://www.energy.gov/oe/grid-resilience-and-innovation-partnerships-grip - DOE's GRIP program targets grid flexibility, reliability, resilience, disruptive events, load growth, cybersecurity, and transformational grid projects.

### 5. Data center power/cooling operations partner

- Buyer role: Data center energy, cooling, or reliability optimization lead
- Fit score: `81`
- Why first: High potential value, but weaker immediate access. Use after the grid buyer lane because private data-center validation usually requires trust, procurement, and data-rights maturity.
- First ask: Ask for an offline replay against historical load/cooling event windows; no live operations access.
- Data needed: historical load, cooling, and temperature telemetry, current cooling-control baseline, energy and uptime metrics, security review and NDA
- Send now allowed: `false`
- Sources:
  - https://epri.brightidea.com/AIforPower2026 - AI for Power 2026 connects energy companies, technology providers, and utilities through real-world demonstration projects; pitch day is listed for August 5, 2026.
  - https://www.tva.com/energy/technology-innovation/future-grid-performance - TVA identifies future grid performance challenges tied to renewables, storage, weather-dependent resources, and inverter-based resources.

## Draft Email

Subject: Source-native benchmark and evidence protocol review

```text
Hello [Name],

I am Robert Ashworth, building LumenCore, a source-native evidence and benchmark framework for infrastructure analytics.

I am looking for the right technical reviewer for one bounded paid protocol review or benchmark implementation. The current measured result is deliberately a negative one: Kuramoto phase coupling won 482/1525 paired EIA holdout days versus kalman_local_linear_trend, had a mean skill delta of -0.508191, and did not clear the complete source-specific baseline gate.

The offer is the governed method, not a claim that this candidate wins: map one authorized source to the correct task, register accepted incumbent baselines, freeze chronology and metrics, run the comparison reproducibly, and deliver a reviewer-ready packet that preserves positive and negative results.

Would you be open to a 20-minute technical fit call about a fixed-scope source-native benchmark and evidence protocol review?

Respectfully,
Robert Ashworth
[physical mailing address]

To stop further outreach, reply "remove."
```

## Claim Controls

- Allowed today: draft a paid source-native protocol review offer, verify one current official buyer channel, reconcile sent history and routing controls, prepare a bounded benchmark implementation scope
- Blocked until action-time clearance: send any outreach, select or imply a current recipient, describe any family as a performance champion, request a field replay for the current Kuramoto result, field validated, realized savings, fixed price per frozen delta, award certainty, alpha certainty, live operational control

First-buyer board SHA-256: `510f08dea896fae8bfd82d664eea4f1aedc938cf56aa67cff3e2a347b9ad2625`
