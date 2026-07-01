# NV063 HarborSentinel Data Source Access Audit

Generated UTC: 2026-06-20T01:53:36.675109+00:00

Posture: `SOURCE_LANES_IDENTIFIED_REPRESENTATIVE_DATA_NOT_EXECUTED`

Status: source-lane access/readiness audit only; not evidence of operational harbor, SSDS, Navy radar, classified sensor, watchstander, CMMC, facility-clearance, or field performance.

## Claim Boundary

This audit supports data-source readiness planning only. It does not convert generated v6 evidence into public AIS, licensed ADS-B, Navy radar, SSDS, classified, or field validation.

## Source-Lane Readiness

### AIS surface traffic

- status: `public_source_identified`
- primary source: NOAA Office for Coastal Management AccessAIS
- source URL: https://coast.noaa.gov/digitalcoast/tools/ais.html
- secondary URL: https://marinecadastre.gov/accessais/
- official basis: NOAA describes AccessAIS as a tool for interactively downloading U.S. vessel traffic data by geography and time range.
- authorized-use gate: Treat historical AIS as public representative data only after the selected files, geographies, dates, license/source notes, and NOAA quality caveats are frozen in the source registry.
- proposal use: Surface-lane density, loiter, route-deviation, speed-change, and source-integrity tests in U.S. coastal or inland-waterway regions.
- cannot claim:
  - SSDS integration
  - Navy organic sensor validation
  - satellite AIS coverage
  - tactical threat classification
- next step: Use the AIS pilot source registry to select a bounded NOAA/MarineCadastre sample, download it to an external raw-data workspace, hash raw archives, normalize schema, and split development/validation before threshold selection.

### ADS-B air traffic

- status: `authorized_or_licensed_source_required`
- primary source: OpenSky Network data/API/Trino access
- source URL: https://opensky-network.org/data
- secondary URL: https://opensky-network.org/about/faq
- official basis: OpenSky documents live and historical aircraft-position access. Its FAQ says personal/non-profit API use is free, while commercial use requires consent.
- authorized-use gate: Do not include OpenSky-derived proposal evidence for company or government-contractor use until account, access tier, and written commercial/government-contractor permission or equivalent licensed ADS-B rights are documented.
- proposal use: Air-lane density, orbit/holding, climb/descent, route deviation, ADS-B freshness, and source-disagreement tests near maritime regions.
- cannot claim:
  - Navy air-search radar performance
  - SSDS composite-track validation
  - aircraft threat classification from ADS-B alone
  - licensed data rights before written permission exists
- next step: Request/confirm authorized OpenSky or equivalent ADS-B access, then freeze account-permission notes and a minimal reproducible sample.

### radar-like and composite tracks

- status: `generated_model_only_until_authorized_data`
- primary source: LumenCore generated source-lane benchmark model
- source URL: out/harbor_sentinel_validation/20260619T_NV063_V6_SOURCE_LANE_COVERAGE/
- official basis: The Navy topic requires AIS, ADS-B, and notional radar contacts; the current v6 packet uses generated radar-like/composite observations to test explainable feasibility without claiming Navy data access.
- authorized-use gate: Keep radar/composite lanes labeled generated unless a Navy-authorized dataset, assumptions memo, simulator, or integration environment is provided in writing.
- proposal use: Source disagreement, covariance/quality, dropout, track swap, latency, and confidence-calibration stress tests.
- cannot claim:
  - field radar validation
  - classified sensor performance
  - operational watchstander workload reduction
  - SSDS interface compatibility
- next step: Add a radar-assumption profile file with explicit synthetic noise, latency, identity-conflict, and dropout parameters.

## Current Generated Evidence Anchor

- run directory: `out/harbor_sentinel_validation/20260619T_NV063_V6_SOURCE_LANE_COVERAGE`
- directory exists: True
- manifest exists: True
- summary exists: True
- source-lane summary exists: True

This generated v6 packet remains useful because it already tests source-lane coverage, availability, dropout, and source-disagreement mechanics. It must stay labeled generated until public/licensed AIS/ADS-B data and authorized radar assumptions are acquired and frozen.

## Remaining Blockers

- Actual NOAA AIS subset has not yet been acquired, hashed, partitioned, and run through the HarborSentinel gate.
- OpenSky or equivalent ADS-B commercial/government-contractor data rights are not yet documented.
- Radar/composite-track validation remains generated-model-only until authorized Navy data, assumptions, or simulator access exists.
- No operational harbor, SSDS, classified sensor, watchstander, or field validation is established by this audit.

## Execution Plan For Stronger Evidence

1. Acquire two small NOAA/MarineCadastre AIS subsets for congested U.S. maritime regions and freeze raw archives with SHA-256 hashes.
2. Keep raw NOAA/MarineCadastre AIS files on an external data volume when possible; commit source registries, hashes, schema profiles, and bounded summaries only.
3. Confirm OpenSky or equivalent ADS-B commercial/government-contractor rights before using any ADS-B-derived evaluation in a company proposal.
4. Normalize AIS and ADS-B into a source registry that records source, license/permission, schema, date range, geography, hash, and exclusion notes.
5. Partition development and validation regions/times before threshold selection, then run the HarborSentinel gate without changing thresholds on the withheld split.
6. Keep radar/composite tracks generated unless Navy-authorized data, assumptions, simulator, or integration access is provided.
7. Report source-integrity alerts separately from behavior-based threat candidates and preserve false-alert/failure regions.

## Sources Checked

- NOAA AccessAIS: https://coast.noaa.gov/digitalcoast/tools/ais.html
- MarineCadastre AccessAIS: https://marinecadastre.gov/accessais/
- NOAA Vessel Traffic data page: https://coast.noaa.gov/digitalcoast/data/vesseltraffic.html
- Harbor AIS pilot source registry: grant_submissions/NV063_HarborSentinel/NV063_AIS_PILOT_SOURCE_REGISTRY_2026-06-20.md
- OpenSky data access: https://opensky-network.org/data
- OpenSky FAQ: https://opensky-network.org/about/faq
