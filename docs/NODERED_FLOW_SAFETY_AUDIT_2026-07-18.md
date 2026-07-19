# Node-RED Flow Safety Audit

**Date:** 2026-07-18
**Policy:** `node_red_flow_safety_v1`
**Decision:** **BLOCK** (fail closed)

This was a static audit only. No Node-RED runtime, flow execution, network call, registry/API key, service, or publish operation was used.

## Scope

- `code/node_red/flows_live_truth_bridge.json`
- `code/node_red/flows_luma_bidirectional.json`
- `code/node_red/flows_luma_bootstrap.json`
- `code/ENSURE_NODERED_LUMA_FLOWS.py`

## Blocking findings

- All three flows contain automatically firing inject nodes (`once` and/or `repeat`).
- All three flows expose payloads through active debug nodes.
- HTTP request nodes lack a positive explicit timeout and a statically connected `catch`/`status` path.
- HTTP URLs are loopback-bound (`127.0.0.1`), which is the required network boundary and is not a finding.
- `ENSURE_NODERED_LUMA_FLOWS.py` can POST `/flows`; this is a replace-all flow deployment risk.

The report intentionally does not claim remediation. Existing flows and the ensure script were not changed. The audit lane exits with status `1` while any finding exists, and malformed inputs are also blockers.

## Reproduction

```text
python code/ops/AUDIT_NODERED_FLOW_SAFETY.py
pytest -q tests/test_node_red_flow_safety.py
```

The machine-readable policy is `config/node_red_flow_safety_policy_v1.json`. An optional ignored artifact can be written with `--json-out`.
