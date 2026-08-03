# LumenCore Live-Domain Service Contract

- Generated UTC: `2026-07-29T13:20:33.630666Z`
- Status: `LIVE_DOMAIN_SERVICE_CONTRACT_BLOCKED`
- Required endpoints passed: `3/7`
- Contract SHA-256: `fbe9369a6530f8a750a8532e9b3a8d60da77b9cd728b5bb42fcd0d118ab19bea`

## Endpoint Matrix

| Endpoint | Result | HTTP | Content type | Redirect |
|---|---:|---:|---|---|
| `public_root` | `PASS` | `200` | `text/html` | `-` |
| `edge_health` | `BLOCK` | `200` | `application/octet-stream` | `-` |
| `gateway_health` | `BLOCK` | `502` | `text/html` | `-` |
| `app_redirect` | `PASS` | `302` | `text/html` | `https://lumen-core.ai/investor_command_room.html` |
| `app_health` | `BLOCK` | `302` | `text/html` | `https://lumen-core.ai/investor_command_room.html` |
| `research_redirect` | `PASS` | `302` | `text/html` | `https://lumen-core.ai/quant_lab.html` |
| `research_health` | `BLOCK` | `302` | `text/html` | `https://lumen-core.ai/quant_lab.html` |

## Safest Next Action

Authenticate to the VPS, inspect luma-gateway service logs and free space, then restore the gateway before any API-health claim or full deployment.

## Boundary

This receipt proves only the observed public HTTP, content-type, redirect, and bounded JSON contracts at the recorded time. It does not prove service uptime outside the probe window, independent validation, model performance, realized savings, award readiness, or live-trading fitness.
