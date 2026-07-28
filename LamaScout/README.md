# LumaScout

LumaScout is a dedicated elite digital talent scouting pipeline for live artist discovery, cross-platform scoring, champion lineage, and institutional-grade evidence outputs.

## Purpose

This project is built as a standalone pipeline:
- live data ingestion from platform APIs and sector sources
- normalization to a unified talent dataset
- hybrid harmonic scoring and champion strategy optimization
- champion alerts, report outputs, and proofs

## Why LumaScout

LumaScout is designed for one mission: finding the artists who are about to break before the major labels know their names.
- US-wide talent radar that searches venues, social trends, playlists, and press signals simultaneously
- unsigned prospect prioritization so your friend can call the first mover
- audit-grade proofs and frozen evidence for every run
- clean REST endpoints and a polished prospect dashboard for non-technical users

## Project layout

- `config/` — YAML config for weights, thresholds, and active API sources
- `src/` — engine and pipeline code
- `data/raw/` — raw drops and live ingestion files
- `data/normalized/` — normalized row output and staging
- `out/` — champion ranking outputs
- `reports/` — alert files, summaries, audit outputs
- `logs/` — error and ingestion logs
- `run/` — launch scripts for the pipeline

## Design principles

- Modular core: ingest, normalize, score, audit, dashboard, and filters are separate pluggable layers.
- Config-driven: new sources, thresholds, and discovery patterns are defined in YAML, not hard-coded.
- Provenance first: every run emits audit proof, API snapshots, and frozen evidence for reliable validation.
- User-friendly interface: simple REST endpoints plus `GET /ui` make discovery accessible without platform complexity.
- US-wide radar: default search scope is nationwide, with filters for genre, state, city, and unsigned breakout urgency.

## Getting started

1. Add raw data into `data/raw/`. For optional live sources, copy the variable names
   from `.env.example` into an untracked `.env` file or the process environment.
   Never put credential values in `config/api_registry.yaml`.
2. Review `config/artist_scout_config.yaml` to set thresholds, weights, and required columns.
3. Install LumaScout dependencies:
   ```powershell
   cd C:\LumaTrader\INSTITUTIONAL_STACK_V2\LamaScout
   c:\LumaTrader\INSTITUTIONAL_STACK_V2\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
4. Run the pipeline from PowerShell:
   ```powershell
   cd C:\LumaTrader\INSTITUTIONAL_STACK_V2\LamaScout\run
   .\RUN_LAMASCOUT.ps1
   ```
5. Start the LumaScout dashboard API:
   ```powershell
   cd C:\LumaTrader\INSTITUTIONAL_STACK_V2\LamaScout\run
   .\RUN_LAMASCOUT_API.ps1
   ```

6. Use the next-level automation script to run the pipeline, start the API, check truth, and open the UI:
   ```powershell
   cd C:\LumaTrader\INSTITUTIONAL_STACK_V2\LamaScout\run
   .\RUN_LAMASCOUT_NEXTLEVEL.ps1
   ```

## Next steps

- configure optional API credentials through runtime environment variables
- implement API-specific fetch functions in `src/api_clients.py`
- add champion lineage and Monte Carlo strategy optimizer
- add live dashboard integration and report automation
- add audit-grade run proof and frozen snapshot evidence
- add filter rules for genre-specific leaderboards, city/state top-10, age cohort scouting, and AGT-style contest stages
- add a USA scope alias for broader national search

## High-impact discovery vectors

- combine venue/event scouting with local festival and open-mic keywords to catch raw rising artists before they hit mainstream radar
- use cross-platform velocity signals (views, followers, listeners, trends) rather than absolute popularity
- track press and playlist momentum for emerging scenes and secondary markets, not only major city headlines
- surface unsigned talent by filtering label signals, major collaborator flags, and manager/agent mentions
- prioritize artists with live performance traction and a short forecast to 100k views/listeners

## New live audit and proof outputs

- `reports/artist_scout_run_proof.json` — hash-verifiable run proof including input hashes, active source metadata, and top champion evidence
- `data/raw/api_snapshots/` — recorded API snapshots for each active live source
- `out/artist_portfolio_champions.csv` — Monte Carlo optimized champion portfolio from top talent
- `out/artist_hot_radar.csv` — US-wide hot urgency radar for unsigned breakout talent

## How to use the dashboard

- `GET /ui` — launch the polished prospect radar interface
- `GET /radar` — retrieve the current hot priority talent list
- `GET /prospects` — get the top unsigned breakout prospects nationwide
- `GET /search` — query the champion universe by genre, city, state, cohort, signed status, and scope
- `GET /summary` — read live run statistics, top prospect counts, and last run timestamp
- `GET /research` — retrieve a research dashboard summary and idea cluster pulse
- `GET /truth` — retrieve the rolling Truth Engine summary and live strategy pulse

## Open source signal sources
- MusicBrainz — open music metadata, no API key required
- Wikipedia — open search relevance and press-signal discovery
- Google Trends — open trend momentum through pytrends, no API key required

## New query endpoints

- `GET /search` — search champions by genre, city, state, country, age_group, agt_stage, tier, label_interest, not_signed, and scope
  - `scope=usa` returns the full US artist universe when country=USA
  - `today=country` or `tomorrow=hiphop` can also be used as query shortcuts
- `GET /prospects` — top unsigned breakout prospects, sorted by hot urgency and breakout momentum
  - supports `genre`, `city`, `state`, `country`, `age_group`, `agt_stage`, `not_signed`
  - defaults to `country=usa` for nationwide search
- `GET /radar` — US-wide hot radar for unsigned breakout talent, sorted by urgency and breakout score
- `GET /ui` — interactive US-wide prospect dashboard for rolling top-20 breakout unsigned talent
- `GET /top?field=genre&value=hiphop` — top artists for a given field value

## New LumaScout outputs

The engine now supports:
- genre-based champion discovery
- city- and state-specific top-10 ranking tables
- AGT-style age cohort and stage filters
- age-group scoring for 20s / 30s / 40s talent
- live watchlist outputs by genre, location, and performer category
