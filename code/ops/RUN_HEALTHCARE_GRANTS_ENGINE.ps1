param(
    [int]$ExpiringDays = 45,
    [double]$MinHealthcareScore = 35.0,
    [int]$TopN = 40,
    [switch]$IncludeForecasted,
    [string]$ApiKey,
    [string]$AccessRegistryPath = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\config\healthcare_pipeline_access_registry.json",
    [string]$RequiredRolePattern = "^institutional(_|$)",
    [switch]$BypassApiKey
)

$ErrorActionPreference = "Stop"

function Get-KeyDigest {
    param([Parameter(Mandatory = $true)][string]$Value)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
        $hash = $sha.ComputeHash($bytes)
        return -join ($hash | ForEach-Object { $_.ToString('x2') })
    } finally {
        if ($sha) { $sha.Dispose() }
    }
}

function Resolve-AccessOperator {
    param(
        [Parameter(Mandatory = $true)][pscustomobject]$Registry,
        [Parameter(Mandatory = $true)][string]$Digest,
        [datetime]$NowUtc = [datetime]::UtcNow
    )

    $ops = @($Registry.operators)
    foreach ($op in $ops) {
        if (-not $op) { continue }
        $stored = [string]$op.key_sha256
        if ([string]::IsNullOrWhiteSpace($stored)) { continue }
        if ($stored -ne $Digest) { continue }
        if ([bool]$op.revoked) { continue }

        $expiresRaw = [string]$op.expires_utc
        if (-not [string]::IsNullOrWhiteSpace($expiresRaw)) {
            try {
                $expiresUtc = [datetime]::Parse(
                    $expiresRaw,
                    [System.Globalization.CultureInfo]::InvariantCulture,
                    [System.Globalization.DateTimeStyles]::RoundtripKind
                ).ToUniversalTime()
                if ($expiresUtc -lt $NowUtc) {
                    continue
                }
            } catch {
                continue
            }
        }

        return $op
    }

    return $null
}

$root = "C:\LumaTrader"
$stackRoot = Join-Path $root "INSTITUTIONAL_STACK_V2"
$scriptPath = Join-Path $stackRoot "code\ops\run_healthcare_grants_engine.py"

if (-not (Test-Path $scriptPath)) {
    throw "Healthcare grants engine script not found: $scriptPath"
}

$pythonCandidates = @(
    (Join-Path $root "venv3.11\Scripts\python.exe"),
    (Join-Path $root ".venv\Scripts\python.exe")
)

$pythonCmd = $null
foreach ($candidate in $pythonCandidates) {
    if (Test-Path $candidate) {
        $pythonCmd = $candidate
        break
    }
}

if (-not $pythonCmd) {
    $resolved = Get-Command python -ErrorAction SilentlyContinue
    if ($resolved) {
        $pythonCmd = "python"
    }
}

if (-not $pythonCmd) {
    throw "Python executable not found. Checked venv3.11, .venv, and system path."
}

if (-not $BypassApiKey) {
    if (Test-Path $AccessRegistryPath) {
        $registry = $null
        try {
            $registry = Get-Content -Path $AccessRegistryPath -Raw | ConvertFrom-Json -Depth 20
        } catch {
            throw "Access registry is invalid JSON: $AccessRegistryPath"
        }

        $enabled = $true
        if ($registry -and $registry.PSObject.Properties.Name -contains 'enabled') {
            $enabled = [bool]$registry.enabled
        }

        if ($enabled) {
            if ([string]::IsNullOrWhiteSpace($ApiKey)) {
                throw "ApiKey is required. Provide -ApiKey or use -BypassApiKey for local operator override."
            }

            $digest = Get-KeyDigest -Value ([string]$ApiKey)
            $operator = Resolve-AccessOperator -Registry $registry -Digest $digest -NowUtc ([datetime]::UtcNow)
            if (-not $operator) {
                throw "ApiKey is not authorized for healthcare pipeline access."
            }

            $role = [string]$operator.role
            if ([string]::IsNullOrWhiteSpace($role)) {
                throw "ApiKey record is missing role. Institutional role is required."
            }
            if ($RequiredRolePattern -and -not ($role -match $RequiredRolePattern)) {
                throw "ApiKey role '$role' is not authorized. Required role pattern: $RequiredRolePattern"
            }

            $label = [string]$operator.label
            $keyId = [string]$operator.key_id
            Write-Output "RUN_HEALTHCARE_GRANTS_ENGINE_ACCESS operator=$label key_id=$keyId role=$role mode=registry"
        } else {
            Write-Output "RUN_HEALTHCARE_GRANTS_ENGINE_ACCESS mode=registry_disabled"
        }
    } else {
        Write-Output "RUN_HEALTHCARE_GRANTS_ENGINE_ACCESS mode=open_no_registry"
    }
} else {
    Write-Output "RUN_HEALTHCARE_GRANTS_ENGINE_ACCESS mode=bypass"
}

$argsList = @(
    $scriptPath,
    "--expiring-days", $ExpiringDays,
    "--min-healthcare-score", $MinHealthcareScore,
    "--top-n", $TopN
)

if ($IncludeForecasted) {
    $argsList += "--include-forecasted"
}

Write-Output "RUN_HEALTHCARE_GRANTS_ENGINE python=$pythonCmd"
Write-Output "RUN_HEALTHCARE_GRANTS_ENGINE expiringDays=$ExpiringDays minHealthcareScore=$MinHealthcareScore topN=$TopN includeForecasted=$IncludeForecasted"

& $pythonCmd @argsList
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    throw "Healthcare grants engine failed with exit code $exitCode"
}

Write-Output "RUN_HEALTHCARE_GRANTS_ENGINE_COMPLETE"
