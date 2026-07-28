# Bounded Evidence Route Recovery

## Purpose

Serve `https://lumen-core.ai/evidence/` as a static, reviewer-safe proof-to-pilot page instead of proxying the route to the application gateway. The repair does not change application services, credentials, DNS, certificates, trading state, or evidence claims.

## Production contract

- Public asset: `/opt/lumencore/dashboard/evidence/index_bounded.html`
- Required marker: `proof-to-pilot-evidence-v1`
- Route behavior:
  - `/evidence` redirects to `/evidence/`
  - `/evidence/` serves the bounded static index
  - cache control is `no-cache`
- Current deployment path: `.github/workflows/deploy.yml`
- Repair utility: `code/ops/repair_evidence_route.py`
- Atomic wrapper: `code/ops/REPAIR_EVIDENCE_ROUTE_ON_VPS.sh`

## Inspect without changing production

```bash
bash code/ops/REPAIR_EVIDENCE_ROUTE_ON_VPS.sh
```

The command must identify exactly one active Nginx configuration and exactly one `location /evidence/` block. Missing or duplicate targets fail closed.

## Apply

```bash
sudo bash code/ops/REPAIR_EVIDENCE_ROUTE_ON_VPS.sh --apply
```

Apply mode:

1. confirms the bounded page exists;
2. creates a timestamped rollback copy;
3. replaces only the single `/evidence/` location contract;
4. runs `nginx -t`;
5. reloads Nginx only after validation;
6. verifies the page locally with TLS SNI and publicly through DNS;
7. requires HTTP 200 and the exact bounded-page marker;
8. restores the prior Nginx configuration and reloads if validation fails.

## Manual rollback

The wrapper prints the rollback path. To restore it:

```bash
sudo cp -a /path/to/lumatrader.conf.deploy-rollback.TIMESTAMP /path/to/lumatrader.conf
sudo nginx -t
sudo systemctl reload nginx
```

## Claim boundary

A healthy route proves only that a static public review page is reachable. It does not establish external validation, consortium membership, agency endorsement, production deployment of the underlying methods, field savings, patent outcome, or universal model superiority.

## Capacity prerequisite

The production root filesystem was observed at 100% byte utilization and 98%
inode utilization on `2026-07-28T01:59:46Z`. Do not apply this route repair
until bounded filesystem headroom exists. See
`docs/VPS_CAPACITY_AUDIT_2026-07-27.md` and
`config/vps_capacity_policy_v1.json`.
