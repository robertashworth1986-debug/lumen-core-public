# SAM.gov Public Credential Rotation Control - 2026-07-16

Status: `ROTATION_OVERDUE_REPLACEMENT_NOT_DETECTED`

## Direct Answer

Do not claim the SAM key is rotated yet. The current local aliases disagree, the selected private fingerprint has not changed, and the API probe cannot verify the replacement until the aliases are reconciled.

## Evidence

- Official reminder sender: `donotreply@sam.gov`
- Official reminder received UTC: `2026-07-16T08:07:36Z`
- Rotation deadline, America/Chicago: `2026-07-16`
- Local configured aliases: `5`
- Distinct configured credential values: `2`
- Aliases consistent: `false`
- Private baseline present: `true`
- Replacement installation detected: `false`
- API probe: `HTTP_404_EMPTY_RESPONSE_INCONCLUSIVE`
- API HTTP status: `404`
- Rotation verified: `false`
- Control SHA-256: `7af5fe46c0dcd9a06b530aa1115ebbb4733a0f24d029e04e6084b1d44bdf35ee`

No credential value, request URL, response body, or credential fingerprint is published.
The guarded local installer is `code/ops/INSTALL_SAM_PUBLIC_CREDENTIAL.py`; it accepts the replacement only through a hidden prompt.

## Human Action Gate

1. Keep the existing signed-in in-app browser tab on SAM.gov.
2. Open Account Details and locate Public API Key.
3. Use the SAM.gov one-time verification flow to reveal the already-generated replacement.
4. Run `python code/ops/INSTALL_SAM_PUBLIC_CREDENTIAL.py` in a private terminal and paste the replacement only at its hidden prompt.
5. Rerun this verifier and require a changed private fingerprint; require a live authenticated response when the upstream API is observable.

## Official References

- SAM.gov Account Details: https://sam.gov/profile/details
- GSA API documentation: https://open.gsa.gov/api/get-opportunities-public-api/

## Claim Boundary

This control proves only bounded local credential-discovery state, fingerprint comparison, and the recorded API probe result. It never stores or publishes a credential value. A changed fingerprint proves that the configured value changed, not that SAM.gov accepted it. Only a successful authenticated probe can establish live API acceptance, and no browser, account, submission, or opportunity state is changed by this control.
