# Evidence route recovery

## Current finding

The public health ledger reported `https://lumen-core.ai/evidence/` as the only failed endpoint. The older probe concatenated `000` onto an HTTP failure, so a real `502` appeared as `502000`. The corrected probe preserves the actual status code and validates its JSON before committing.

The repository also contains two route models:

- the full VPS deployment script serves `/evidence/` from `/opt/lumencore/dashboard/evidence/`;
- an older reusable Nginx template proxies `/evidence/` to the gateway on port `8787`.

Because the public evidence index is a static asset, the bounded recovery target is a static Nginx route serving `dashboard/evidence/index_bounded.html`. This avoids making the public evidence landing page depend on the application gateway and avoids promoting the older legacy run viewer.

## Safety boundary

This recovery changes only the Nginx `/evidence` location. It does not:

- start or stop trading, execution, model, or data-ingestion services;
- alter API keys, exchange credentials, certificates, DNS, or firewall rules;
- publish new patent details or expand performance claims;
- modify evidence artifacts, hashes, ledgers, benchmark outputs, or source data.

The public page remains run-scoped and limitation-forward. Restoring the route is not external validation, agency approval, field performance, universal model superiority, or guaranteed savings.

## Inspect first

From the repository root on the VPS:

```bash
bash code/ops/REPAIR_EVIDENCE_ROUTE_ON_VPS.sh
```

The default mode is read-only. It checks for the Nginx file and `dashboard/evidence/index_bounded.html`, then prints the proposed diff. A nonzero `NEEDS_REPAIR` result means no file was changed.

## Apply after review

```bash
sudo bash code/ops/REPAIR_EVIDENCE_ROUTE_ON_VPS.sh --apply
```

The apply path:

1. requires the bounded evidence page to exist;
2. creates a timestamped rollback copy;
3. replaces only the existing `/evidence/` location block;
4. creates a second timestamped backup through the Python repair utility;
5. runs `nginx -t`;
6. restores the rollback copy if Nginx validation fails;
7. reloads Nginx only after validation succeeds;
8. checks the local and public `/evidence/` status.

## Manual verification

```bash
sudo nginx -t
curl -I https://127.0.0.1/evidence/ -k -H 'Host: lumen-core.ai'
curl -I https://lumen-core.ai/evidence/
cat data/site_health.json
```

Expected route behavior:

- `/evidence` redirects to `/evidence/`;
- `/evidence/` returns HTTP `200` from `index_bounded.html` in the static dashboard tree;
- missing files under `/evidence/` return `404` instead of falling through to the gateway;
- the next health snapshot records status `200`, not `502000`.

## Rollback

The wrapper prints the exact rollback path. To restore it manually:

```bash
sudo cp -a /etc/nginx/conf.d/lumatrader.conf.pre-evidence-repair.<UTCSTAMP> \
  /etc/nginx/conf.d/lumatrader.conf
sudo nginx -t
sudo systemctl reload nginx
```

Do not delete backups until the public route and the next scheduled health snapshot both verify.

## Public-page boundary

The static route intentionally uses `dashboard/evidence/index_bounded.html`. The older `dashboard/evidence/index.html` remains a legacy run viewer and is not promoted by this recovery because its older headline language predates the current claim-boundary register. Review and migrate any useful run-viewer features separately before public promotion.
