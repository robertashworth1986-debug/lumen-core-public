# LumenCore VPS Gateway Recovery

As of UTC: `2026-07-29T11:46:51Z`

## Current Observation

- The boot disk is approximately 150 GB and the expanded root filesystem has approximately 80 GB free.
- Root filesystem utilization is 42 percent; inode utilization is 1 percent.
- Nginx is active and its configuration test passes.
- `luma-gateway` is in an automatic restart loop.
- The observed import failure is `ModuleNotFoundError: No module named 'booth_public_contract'`.
- The required local file exists at `code/booth_public_contract.py`.
- Local SHA-256: `4d92ed33e085cad525d5c3e6bfd9ba75bd0d82c89dd14cc0fddc99476994b09e`.
- The current live audit observes four dashboard routes returning HTTP 200 and four returning HTTP 502.

## Bounded Repair

The prepared repair uploads only `booth_public_contract.py`, refuses to overwrite a
different existing remote file, verifies the exact SHA-256, imports the module with
the VPS virtual environment, restarts only `luma-gateway`, and checks the loopback
health route.

Dry run:

```powershell
.\deploy\REPAIR_LUMA_GATEWAY_MODULE.ps1 -DryRun
```

Apply remains blocked until an exact action-time approval and private HumanUnlock
control are present:

```text
APPROVE LUMENCORE VPS GATEWAY REPAIR NOW: upload only code/booth_public_contract.py SHA-256 4d92ed33e085cad525d5c3e6bfd9ba75bd0d82c89dd14cc0fddc99476994b09e to /opt/lumencore/code/booth_public_contract.py, restart only luma-gateway, then verify /health and the four current 502 dashboard routes; no other files, services, DNS, billing, storage, or portal changes.
```

## Claim Boundary

This record documents a current read-only observation and a locally tested repair
path. It does not prove that the repair was applied, that the public gateway is
healthy, that all dashboard hashes are current, or that any scientific,
performance, savings, field-validation, award, or acceptance claim is supported.
