# Public metrics contract and issue #234

This maintenance supports active outcome 2: a reviewer must be able to distinguish
public-page availability from private data products. It changes monitoring only.
It does not restore a producer, publish operator data, or approve a new API.

## Confirmed failure

[Live Metrics Sync run 37128621640](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37128621640)
ran against `6be9b1456472ef01e38ebe1838539297111da406` and recorded HTTP 200 for
the homepage but zero of four JSON objects at `2026-10-03T14:09:05Z`.
The old capture discarded HTTP errors, MIME types, redirects and error bodies
into indistinguishable `null` values. It also accepted any JSON object as a feed
without validating its schema or timestamp. That could conceal an error object
or stale data if a route later returned HTTP 200.

The checked-in [operator middleware](../code/operator_api_access.py) deliberately
allows only `/health` and `/api/public/status` without authentication. Every
other `/api` route requires the operator boundary. No exact handler for any of
the four monitored filenames exists in the current gateway. Nginx sends `/api/`
to that gateway; the static-release package does not publish these four feeds.
This establishes a source-contract mismatch. It does not establish the exact
middleware, route or process deployed at a particular time.

A subsequent local read-only capture beginning `2026-10-03T23:50:33Z`
observed a reachable homepage and valid minimal gateway contracts, while all
four legacy paths returned HTTP 503 with the exact operator-access-unconfigured
response. This confirms the access-boundary explanation for that observation;
it does not prove producer or route availability behind authentication, and it
does not diagnose the separately reported intermittent origin failure. No raw
response bodies were retained. The capture used the working-tree monitor;
a committed CI receipt remains a separate gate.

## Disposition of the four legacy names

| Monitor path | Producer and actual artifact in source | Intended boundary and disposition | Freshness requirement |
|---|---|---|---|
| `/api/live_status.json` | No exact producer or handler mapped. `code/infra_live_loop_builder.py` writes `out/infra_live_status.json`; the names and contracts differ. | Protected API namespace; no approved public mapping. Do not silently substitute the infrastructure snapshot. | Unspecified for this path; freshness unknown. |
| `/api/federal_brief.json` | `code/execution/federal_brief_builder.py` writes local `out/federal_brief.json`; no gateway handler maps this path. | Local research/brief artifact; protected API namespace. Its modeled economics are not public live metrics. | Local artifact has `generated_utc`; no public SLA or source-age contract exists. |
| `/api/evidence_summary.json` | No exact producer or handler mapped. `code/luma_experience_gateway_legacy.py` exposes protected `/api/evidence/latest`; it is a different contract. | Protected API namespace; no approved public alias. Do not infer equivalence from names. | Unspecified for this path; freshness unknown. |
| `/api/executor_heartbeat.json` | `code/execution/live_executor_legacy.py` writes local `out/execution/live_executor_heartbeat.json`; no handler maps the monitored name. | Operator execution telemetry. Never expose it or enable a worker to satisfy this public monitor. | No approved public age budget; worker freshness must be assessed privately. |

None of these rows establishes an intentionally retired feed, a working private
route, a running producer or permission to expose its output. They establish
that the old monitor's four public-data assumptions are unsupported by current
source. Issue #234 remains open until an owner accepts an explicit service
contract or a documented retirement decision. Source mapping alone is not
completion of that issue.

## Monitoring behavior

The existing workflow now uses [capture_public_metrics.py](../code/ops/capture_public_metrics.py).
It retains timestamped per-endpoint status, media type, response-byte count,
SHA-256, contract verdict and failure disposition. Response payloads and error
strings are not persisted. Requests send no credentials, stay on the fixed
HTTPS origin, refuse redirects, use cache-busting/no-cache, and bound responses
to one MiB and a ten-second socket timeout.

It reports three independent observations:

- Homepage HTTP reachability, explicitly transport-only.
- The exact minimal gateway schemas. `/health` additionally needs a timezone-aware
  timestamp no more than five minutes old and not in the future. `/api/public/status`
  has no data timestamp and cannot establish data freshness.
- Legacy data availability and freshness. Access denials, unconfigured operator
  access, missing routes, redirects, transport failures and unverified JSON
  objects are distinct. A JSON object at an unmapped route is not a validated
  feed. Availability remains unproven and freshness unknown.

The aggregate legacy metrics verdict remains fail-closed (`degraded` or
`outage`); a healthy minimal gateway cannot change it to `operational`.
The artifact-only workflow keeps `contents: read`; it neither commits snapshots
nor changes production. Its retained badge identifies **legacy data feeds**,
rather than labeling the entire domain as unhealthy solely because private data
is unavailable. The independent public health workflow controls the public
availability verdict.

## Remaining resolution gate

A future owner-approved data product needs one named producer, exact route,
public-safe schema, observation/source timestamp semantics, finite freshness
budget, deployment identity and successful timestamped response receipt. A
private product stays private and must use a separate authenticated operator
monitor. Do not add operator credentials to this public workflow or remove the
access middleware. A retirement decision must name the retired path explicitly;
absence alone is not a retirement receipt.
