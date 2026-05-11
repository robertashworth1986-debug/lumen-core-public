# LumaTrader Production Readiness Checklist

Updated: 2026-05-08

## 1) DNS and Domain

- [ ] A record for apex domain points to VPS public IP.
- [ ] A record for www points to VPS public IP.
- [ ] DNS propagation confirmed from VPS.

Quick check:

```bash
dig +short yourdomain.com
dig +short www.yourdomain.com
```

## 2) Source and Deploy Integrity

- [ ] Repository checked out at target path.
- [ ] Branch and commit are the intended release.
- [ ] deploy_vps.sh completed without hard failure.

Quick check:

```bash
git -C /opt/lumatrader rev-parse --abbrev-ref HEAD
git -C /opt/lumatrader rev-parse --short HEAD
```

## 3) Core Services

- [ ] luma-gateway is active.
- [ ] luma-dashboard-refresh is active.
- [ ] luma-node-red is active (if Node-RED installed).
- [ ] luma-nodered-flow-sync completed successfully.

Quick check:

```bash
systemctl status luma-gateway luma-dashboard-refresh luma-node-red luma-nodered-flow-sync --no-pager
journalctl -u luma-gateway -n 80 --no-pager
```

## 4) API and WebSocket Surface

- [ ] /health returns 200.
- [ ] /api/snapshot returns 200.
- [ ] /api/unity/unified-edge returns 200.
- [ ] /api/nodered/ingest accepts POST (200 preferred).
- [ ] /ws/live reachable through reverse proxy.

Quick check:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1/health
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1/api/snapshot
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1/api/unity/unified-edge
curl -sS -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1/api/nodered/ingest -H "Content-Type: application/json" -d '{"source":"check","alive":true}'
```

## 5) Premium Stack

- [ ] Premium package install step passed.
- [ ] Premium probe passed (lightgbm, xgboost, shap, fredapi, alpaca-py and others).
- [ ] Strict mode enabled in production.

Recommended env:

```bash
export LUMA_STRICT_PREMIUM_STACK=1
export LUMA_STRICT_COHERENCE_BUILD=1
```

## 6) Unity + Node-RED Graphics Chain

- [ ] Node-RED flow contains polling and cue posts for snapshot, investor brief, harmonic feed.
- [ ] Unity bridge is installed and rig built.
- [ ] Scene cues include visual_profile payload from gateway.
- [ ] Scene profile config exists at INSTITUTIONAL_STACK_V2/config/scene_visual_profiles.json.
- [ ] Scene simulator endpoint broadcasts intensity sweeps and returns banded events.
- [ ] Scene scenario catalog endpoint returns runnable presets.
- [ ] Scene scenario run endpoint broadcasts multi-step sequences.
- [ ] Scene runs telemetry endpoint returns recent persisted run history.
- [ ] Scenario Mission cockpit page loads and can trigger scenario runs.
- [ ] Harmonic proof-pack mission API returns latest and historical benchmark runs.
- [ ] Harmonic proof-pack mission cockpit page loads with report/manifest links.

Quick check:

```bash
curl -sS http://127.0.0.1/api/scene/profile?scene=harmonic\&cue=harmonic_peak\&intensity=0.92
curl -sS -X POST http://127.0.0.1/api/scene/cue -H "Content-Type: application/json" -d '{"scene":"harmonic","cue":"harmonic_peak","intensity":0.77,"detail":{"source":"check","visual_profile_hint":"cinematic"}}'
curl -sS -X POST http://127.0.0.1/api/scene/simulate -H "Content-Type: application/json" -d '{"scene":"core","cue":"success_pulse","start_intensity":0.2,"end_intensity":0.8,"steps":3,"interval_ms":120,"include_reverse":true,"hint":"investor","detail":{"source":"check"}}'
curl -sS http://127.0.0.1/api/scene/scenarios | head -c 1000
curl -sS -X POST http://127.0.0.1/api/scene/scenario/run -H "Content-Type: application/json" -d '{"scenario":"institutional_open","interval_scale":1.0,"repeat":1,"hint":"investor","detail":{"source":"check"}}'
curl -sS "http://127.0.0.1/api/scene/runs?limit=5" | head -c 1000
curl -sS http://127.0.0.1/api/scene/profile-config | head -c 600
curl -sS http://127.0.0.1/api/proofpack/harmonic/latest | head -c 1400
curl -sS "http://127.0.0.1/api/proofpack/harmonic/runs?limit=3" | head -c 1600
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1/scenario_mission.html
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1/harmonic_proofpack_mission.html
```

## 7) HTTPS

- [ ] Certbot certificate issued.
- [ ] HTTPS endpoints return 200.
- [ ] HTTP redirects to HTTPS if required by policy.

Quick check:

```bash
certbot certificates
curl -I https://yourdomain.com/
```

## 8) Rollback Procedure Ready

- [ ] Previous known-good commit recorded.
- [ ] Scripted restart commands documented.
- [ ] Nginx config backup exists.

Suggested rollback commands:

```bash
git -C /opt/lumatrader checkout <known_good_commit>
/systemctl restart luma-gateway luma-dashboard-refresh luma-node-red luma-nodered-flow-sync
nginx -t && systemctl reload nginx
```

## 9) End-to-End Staleness Gate

- [ ] End-to-end staleness report generated from latest runtime state.
- [ ] `overall_status` is `ok` (or all critical blockers are explicitly waived with notes).
- [ ] Staleness report is accessible from API and dashboard command center.

Quick check:

```bash
python3 /opt/lumatrader/INSTITUTIONAL_STACK_V2/code/deploy/end_to_end_staleness_finder.py --api-base http://127.0.0.1 --print-json
curl -sS http://127.0.0.1/api/ops/staleness | head -c 1600
```

## 10) LumaQ Brain Gate

- [ ] LumaQ brain report generated with Micro/Meso/Macro outputs.
- [ ] LumaQ API endpoint reachable from gateway.
- [ ] LumaQ command center page loads in cockpit and fallback mode.
- [ ] Mirror drift summary reviewed and critical drift items resolved or waived.

Quick check:

```bash
python3 /opt/lumatrader/INSTITUTIONAL_STACK_V2/code/deploy/lumaq_brain_builder.py --max-files 50000 --print-json
curl -sS http://127.0.0.1/api/ops/lumaq | head -c 1800
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1/lumaq_brain_command_center.html
```

## 11) Final Acceptance

- [ ] Mission Control loads with live data.
- [ ] No file:// fallback errors in domain mode.
- [ ] Unity receives live scene cues and profile bands.
- [ ] Investor proof path is visible and coherent.
- [ ] Scenario Mission panel shows run_id telemetry after cue/sim/scenario actions.
