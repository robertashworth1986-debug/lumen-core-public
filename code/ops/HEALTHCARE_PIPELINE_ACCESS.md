# Healthcare Pipeline Access

This pipeline supports API-key access control through a hashed registry file.

## 1) Issue a key

Run:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File code/ops/ISSUE_HEALTHCARE_PIPELINE_ACCESS_TOKEN.ps1 -Label friend_name -DaysValid 120 -RevokeExistingForLabel
```

Output includes:

- `api_key` (share with authorized operator only)
- `key_id`
- `expires_utc`
- `registry_path`

A one-time receipt is also written to:

- `out/ops/healthcare_grants_poc/latest_access_issue_receipt.json`

## 2) Run the engine with key

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File code/ops/RUN_HEALTHCARE_GRANTS_ENGINE.ps1 -ApiKey "<api_key>" -ExpiringDays 45 -TopN 40
```

## 3) Local operator override

For trusted local operations only:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File code/ops/RUN_HEALTHCARE_GRANTS_ENGINE.ps1 -BypassApiKey
```

## 4) Registry behavior

- Registry file path: `config/healthcare_pipeline_access_registry.json`
- If the file exists and `enabled=true`, `-ApiKey` is required.
- Validation uses SHA-256 digests only; plain keys are not stored in the registry.
