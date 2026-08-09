# Public security-header deployment receipt — 2026-08-09 UTC

Decision: **`PUBLIC_HEADER_POLICY_OBSERVED_NO_BROADER_PRODUCTION_PROMOTION`**.

This page records one successful, exact-main, first-party deployment and verification run for the bounded LumenCore public HTTP security-header policy. It is not a penetration test, security certification, external audit, uptime SLA, or proof that the whole application is secure.

## Bound subject

| Field | Value |
|---|---|
| Repository | `robertashworth1986-debug/lumen-core-public` |
| Source commit | `04f5397422cc8e651ddde5cc7e7c57a334866c01` |
| Workflow | `.github/workflows/repair-public-security-headers.yml` |
| Workflow source SHA-256 | `6ec9451af22799a5a56b1b5bd850ac1ad12e26b96e47ec1729c13341e5633f19` |
| GitHub Actions run | [31289595192](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31289595192) |
| Run state | `success` |
| Created | `2026-08-09T02:05:11Z` |
| Completed | `2026-08-09T02:05:31Z` |

The workflow refused any source that was not both the explicitly supplied 40-character commit and current `main`. It verified the uploaded repair payload before execution, required a successful Nginx configuration test, retained a rollback copy, reloaded Nginx, verified the live policy, removed the bounded remote staging directory, and uploaded a 30-day receipt artifact.

## Observed routes

All seven routes returned HTTP `200` and passed on the first attempt from each recorded origin:

- VPS loopback verification;
- VPS public-network verification; and
- an independent GitHub-hosted runner request after the VPS step.

The routes were:

1. `/`
2. `/proof_to_pilot.html`
3. `/external_review.html`
4. `/evidence/`
5. `/build_week/prooflock_console/`
6. `/health`
7. `/api/public/status`

## Bounded policy

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=31536000`
- CSP defaults to same-origin, denies objects and framing, restricts fonts/styles/scripts to the named sources required by the public site, and upgrades insecure requests.
- Permissions Policy disables accelerometer, autoplay, camera, geolocation, gyroscope, magnetometer, microphone, payment, and USB.

## Retained artifact

| Field | Value |
|---|---|
| Artifact name | `public-security-headers-31289595192-1` |
| Artifact ID | `9030952290` |
| Artifact bytes | `1,205` |
| Artifact SHA-256 | `8ac130ba2a313c795750105141cbfec4b4656c40cfe04cb3b5c58a377681f12d` |
| Retention expiry | `2026-09-08T02:05:28Z` |

The machine-readable receipt is [`deployment-receipt.json`](../evidence/public-security-headers/04f5397422cc8e651ddde5cc7e7c57a334866c01/deployment-receipt.json). Its canonical self-hash is filled and checked by the repository verifier.

## Local verification

```bash
python code/ops/VERIFY_PUBLIC_SECURITY_HEADER_RECEIPT.py
```

The local verifier checks the strict receipt shape, canonical self-hash, timestamps, route and origin coverage, exact policy, source commit, and exact workflow bytes preserved in Git. It does not contact the live domain or GitHub and therefore does not prove future behavior or independently re-run the deployment.

## Claim boundary

This evidence establishes only that the named first-party workflow completed successfully and observed the named HTTP policy on the named routes at the recorded time. It does not establish vulnerability-free status, application correctness, live-release byte parity, data protection, regulatory conformance, customer acceptance, independent validation, or a broader production-readiness decision.
