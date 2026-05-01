# LumaScout Architecture

## Overview

LumaScout is designed as a clean, separate talent scouting engine that does not interfere with the existing trading stack.

The core purpose is to ingest live raw artist/culture data, normalize it, score artists across multiple dimensions, run optimization and Monte Carlo search for champion formulas, and publish live champion outputs.

## Data flow

1. `config/api_registry.yaml` defines active live sources, endpoints, and credentials.
2. `data/raw/` receives raw drops and API ingestion files.
3. `src/artist_scout_engine.py` loads raw data and optionally live API results.
4. `data/normalized/` stores unified row-level normalized assets.
5. The scoring engine computes artist rollups, platform signals, and champion tiers.
6. `out/` and `reports/` publish ranked champions, watchlists, summary artifacts, and audit files.

## Core modules

- `ingest` — collect live data from API sources and raw CSV drops
- `normalize` — standardize artist structure, platform names, and numeric fields
- `scoring` — compute feature scores and aggregate weighted metrics
- `audit` — build frozen run proof, API snapshots, and provenance outputs
- `dashboard_api` — expose clean search, prospects, radar, and UI endpoints
- `filters` — provide reusable query filters for genre, location, cohort, and signed state
- `optimize` — run Monte Carlo or champion lineage search for top strategies
- `report` — emit output tables, alerts, and dashboard-ready proofs

## Modular design

LumaScout is intentionally built to be modular internally while remaining simple externally.

- each source adapter is isolated in `src/api_clients.py` and driven by `config/api_registry.yaml`
- scoring features are produced in `src/scoring.py`, with new breakout and hot radar signals layered in cleanly
- ingest, normalize, and audit functions are separate so each subsystem can be replaced or extended without disrupting the rest
- the dashboard API exposes a minimal set of user-friendly endpoints, including `GET /ui`, `GET /prospects`, and `GET /radar`

## API registry design

The registry file is the single source of truth for active sources.

Each entry includes:
- source name
- source type
- active flag
- endpoint description
- auth placeholder
- last successful run metadata

This enables a live registry for your frozen deltas, audit-cut, and sector-driven pipeline.

## Live strategy pipeline

The engine is intentionally separate from the institutional trading stack.

The recommended pipeline is:

- run raw ingestion and live pulls periodically
- normalize every source into the same talent row schema
- evaluate artists over platform mix, growth, engagement, press, and venue signals
- propagate strategy/flowform lineage into champion output
- generate a live dashboard from the `out/` and `reports/` files

## Proof and audit

LumaScout should produce auditable outputs with:
- timestamped summaries
- champion lineage metadata
- data provenance from source file or API endpoint
- regeneration proof for every run

## Recommended immediate focus

1. get core APIs working: YouTube, Spotify, Meta/Instagram, Google Trends
2. ingest press and venue signals from media and event sources
3. normalize row schema across platforms
4. build a lightweight champion scoring engine and alert writer
- add audit-proof generation and frozen API snapshots
- add Monte Carlo champion portfolio optimization and lineage tracking
6. add dashboard output for live watchlist and champion scorecards
