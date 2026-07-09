# Key Governance Firewall - 2026-07-09

Purpose: make the live-key registry useful for proof and source breadth without exposing credential values or authorizing live account actions.

This firewall records provider purpose, credential presence, and human-action boundaries only. It never stores raw credential values.

## Status

- Status: `KEY_FIREWALL_READY_HUMAN_GATED`
- Registry key slots: `63`
- Present key slots: `37`
- Missing key slots: `26`
- Coverage: `58.73`
- LumaScout sources: `9`
- LumaScout active sources: `6`
- Active LumaScout sources with credentials: `3`
- Inline credential hits: `0`
- Write/spend actions allowed: `0`
- Raw credential values stored: `false`
- Final action without human: `false`
- Live trading allowed: `false`
- Social posting allowed: `false`
- Ad spend allowed: `false`
- Firewall SHA-256: `387c320ac5bf549405462954f2c7d826cacd9a1f36812de5bb02a919479eab8f`

## LumaScout Media Sources

### YouTube

- Name: `youtube`
- Type: `streaming_platform`
- Active: `true`
- Access mode: `read_only_metrics`
- Search terms: `12`
- Credential present: `false`
- Write/spend allowed: `false`
- Account mutation requires human: `true`

### Spotify

- Name: `spotify`
- Type: `audio_platform`
- Active: `true`
- Access mode: `read_only_metrics`
- Search terms: `12`
- Credential present: `false`
- Write/spend allowed: `false`
- Account mutation requires human: `true`

### Meta Graph (Facebook/Instagram)

- Name: `meta`
- Type: `social_platform`
- Active: `true`
- Access mode: `read_only_public_signal`
- Search terms: `10`
- Credential present: `false`
- Write/spend allowed: `false`
- Account mutation requires human: `true`

### Google Trends

- Name: `google_trends`
- Type: `cultural_trend`
- Active: `true`
- Access mode: `public_signal`
- Search terms: `10`
- Credential present: `true`
- Write/spend allowed: `false`
- Account mutation requires human: `true`

### MusicBrainz

- Name: `musicbrainz`
- Type: `music_metadata`
- Active: `true`
- Access mode: `public_open_api`
- Search terms: `10`
- Credential present: `true`
- Write/spend allowed: `false`
- Account mutation requires human: `true`

### Wikipedia

- Name: `wikipedia`
- Type: `press_signal`
- Active: `true`
- Access mode: `public_open_api`
- Search terms: `10`
- Credential present: `true`
- Write/spend allowed: `false`
- Account mutation requires human: `true`

### X / Twitter

- Name: `twitter_x`
- Type: `social_platform`
- Active: `false`
- Access mode: `read_only_metrics`
- Search terms: `3`
- Credential present: `false`
- Write/spend allowed: `false`
- Account mutation requires human: `true`

### Ticketmaster

- Name: `ticketmaster`
- Type: `venue_signal`
- Active: `false`
- Access mode: `read_only_events`
- Search terms: `3`
- Credential present: `false`
- Write/spend allowed: `false`
- Account mutation requires human: `true`

### NewsAPI

- Name: `news_api`
- Type: `press_signal`
- Active: `false`
- Access mode: `read_only_press`
- Search terms: `5`
- Credential present: `false`
- Write/spend allowed: `false`
- Account mutation requires human: `true`

## Firewall Rules

- Never commit raw API values to tracked registry files.
- Use *_env fields and ignored local env files for all credential material.
- LumaScout media sources are read-only metric/source-intelligence lanes.
- No posting, messaging, comments, uploads, page edits, ad spend, trading, withdrawals, or capital movement without explicit human approval and a separate purpose-built workflow.
- Public reports may show provider names, key presence booleans, source counts, hashes, and claim boundaries only.

## Blocked Actions

- `ad`
- `ad_spend`
- `comment`
- `dm`
- `follow`
- `message`
- `order`
- `page_edit`
- `post`
- `trade`
- `upload`
- `withdraw`
