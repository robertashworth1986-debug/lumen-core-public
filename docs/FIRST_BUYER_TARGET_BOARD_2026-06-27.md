# First Buyer Target Board

Generated UTC: `2026-06-29T16:50:23.016860+00:00`

First-buyer target board. This artifact selects named, source-verified buyer channels for a manual paid evidence review or buyer-authorized field replay. It does not authorize auto-send, bulk outreach, contact scraping, fixed frozen-delta pricing, field-validation claims, realized-savings claims, live trading, or autonomous operational execution.

## Decision

- First buyer channel: `EPRI AI for Power / Incubatenergy Labs`
- Channel type: `national_utility_demonstration_channel`
- First action: Send one manually reviewed inquiry through the official challenge/contact path.
- Send without user review: `false`
- Bulk email allowed: `false`
- Field-validation claim allowed: `false`
- Realized-savings claim allowed: `false`

## Proof Snapshot

- Champion: `Kuramoto phase coupling`
- Named baseline: `kalman_filter`
- Holdout wins: `24/24`
- Estimated rows replayed: `2,506,267`
- Live-domain hash verified: `true`
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

## Primary Manual Email

Subject: Paid field-replay scoping: LumenCore proof feed for EPRI AI for Power / Incubatenergy Labs

```text
Hello,

I am Robert Ashworth, building LumenCore, a hash-verified evidence and benchmark framework for grid and infrastructure optimization.

I am looking for the right technical reviewer for one bounded paid evidence review or buyer-authorized field replay. The current internal champion is Kuramoto phase coupling; it shows 24/24 source-conditioned holdout wins vs kalman_filter, with the public proof feeds available for review.

Important boundary: I am not claiming field validation or realized savings yet. The next step is narrower and safer: lock your approved baseline, choose pre-registered holdout windows, replay the candidate under identical constraints, and report what improved, what failed, and what still cannot be claimed.

Why I think EPRI AI for Power / Incubatenergy Labs is the right first fit:
Highest leverage: one accepted demo path can expose the proof stack to multiple utilities and AI/power decision makers without pretending LumenCore is field validated already.

Reviewer proof feed: https://lumen-core.ai/data/champion_stress_test_matrix.json
Mission console: https://lumen-core.ai/mission_control.html

Would you be open to a 20-minute technical fit call, or could you route me to the person who owns AI/grid analytics validation pilots?

Respectfully,
Robert Ashworth
[physical mailing address]

To stop further outreach, reply "remove."
```

## Claim Controls

- Allowed today: manual inquiry to one reviewed buyer channel, paid evidence review ask, buyer-authorized field replay request, public hash-verified proof feed reference
- Blocked until buyer replay: field validated, realized savings, fixed price per frozen delta, award certainty, alpha certainty, live operational control

First-buyer board SHA-256: `eee39e9c8a2a5c2810b6892b94eb8209dfd6b826b2ea24e8526bffddb1564c02`
