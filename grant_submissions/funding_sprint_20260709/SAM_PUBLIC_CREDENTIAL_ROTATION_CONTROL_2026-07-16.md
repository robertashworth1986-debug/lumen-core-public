# SAM.gov API-Key Rotation Control - 2026-07-16

Status: `ROTATION_DUE_REPLACEMENT_NOT_DETECTED`

## Direct Answer

Do not claim the SAM key is rotated yet. The current local aliases are consistent, but the private fingerprint has not changed and the API probe is inconclusive.

## Evidence

- Official reminder sender: `donotreply@sam.gov`
- Official reminder received UTC: `2026-07-16T08:07:36Z`
- Rotation deadline, America/Chicago: `2026-07-16`
- Local configured aliases: `3`
- Distinct configured secret values: `1`
- Aliases consistent: `true`
- Private baseline present: `true`
- Replacement installation detected: `false`
- API probe: `HTTP_404_EMPTY_RESPONSE_INCONCLUSIVE`
- API HTTP status: `404`
- Rotation verified: `false`
- Control SHA-256: `2f53c464fc559822d28f1b5fa0794a12e5e308589c7b7848efa1686415f0f78a`

No secret value, request URL, response body, or secret fingerprint is published.

## Human Action Gate

1. Keep the existing signed-in in-app browser tab on SAM.gov.
2. Open Account Details and locate Public API Key.
3. Use the SAM.gov one-time-password flow to reveal the already-generated replacement.
4. Install the replacement into all three ignored local aliases without pasting it into chat or Git.
5. Rerun this verifier and require a changed private fingerprint; require a live authenticated response when the upstream API is observable.

## Official References

- SAM.gov Account Details: https://sam.gov/profile/details
- GSA API documentation: https://open.gsa.gov/api/assistance-listings-api/

## Claim Boundary

This control proves only bounded local secret-discovery state, fingerprint comparison, and the recorded API probe result. It never stores or publishes an API key. A changed fingerprint proves that the configured secret changed, not that SAM.gov accepted it. Only a successful authenticated probe can establish live API acceptance, and no browser, account, submission, or opportunity state is changed by this control.
