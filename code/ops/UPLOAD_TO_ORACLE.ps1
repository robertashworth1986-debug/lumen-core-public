# ============================================================
# UPLOAD_TO_ORACLE.ps1
# Zips the stack (no .venv) and SCPs it to Oracle VPS.
# Usage:
#   Set the LUMA_VPS_HOST, LUMA_VPS_USER, LUMA_VPS_SSH_KEY, and
#   LUMA_SSH_KNOWN_HOSTS environment variables, then run with -Apply.
# ============================================================
param(
    [string]$OracleIP = $env:LUMA_VPS_HOST,

    [string]$KeyPath = $env:LUMA_VPS_SSH_KEY,
    [string]$KnownHostsPath = $env:LUMA_SSH_KNOWN_HOSTS,
    [string]$OracleUser = $env:LUMA_VPS_USER,
    [string]$Domain = "lumen-core.ai",
    [switch]$FullStack,
    [switch]$SkipZip,
    [switch]$Apply,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root      = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ZipOut    = "$env:TEMP\INSTITUTIONAL_STACK_V2.zip"
$Bootstrap = "$Root\code\ops\ORACLE_LINUX_BOOTSTRAP.sh"

if ($Apply -and $DryRun) {
    throw "-Apply and -DryRun cannot be used together."
}

if (-not $Apply) {
    Write-Host "PRECHECK ONLY: no archive, key-permission change, network call, upload, bootstrap, or remote mutation was performed."
    Write-Host "Apply requires operator-supplied SSH inputs and a private LUMA_HUMAN_UNLOCK_TOKEN of at least 32 characters."
    exit 0
}

$humanUnlockToken = [string]$env:LUMA_HUMAN_UNLOCK_TOKEN
if ([string]::IsNullOrWhiteSpace($humanUnlockToken) -or $humanUnlockToken.Length -lt 32) {
    throw "Apply blocked: LUMA_HUMAN_UNLOCK_TOKEN must be configured with at least 32 characters."
}
Remove-Item Env:LUMA_HUMAN_UNLOCK_TOKEN -ErrorAction SilentlyContinue

if ([string]::IsNullOrWhiteSpace($OracleIP)) {
    throw "Apply blocked: set LUMA_VPS_HOST or pass -OracleIP."
}
if ([string]::IsNullOrWhiteSpace($OracleUser)) {
    throw "Apply blocked: set LUMA_VPS_USER or pass -OracleUser."
}
if ([string]::IsNullOrWhiteSpace($KeyPath) -or -not (Test-Path -LiteralPath $KeyPath -PathType Leaf)) {
    throw "Apply blocked: set LUMA_VPS_SSH_KEY or pass an existing -KeyPath."
}
if ([string]::IsNullOrWhiteSpace($KnownHostsPath) -and $env:USERPROFILE) {
    $KnownHostsPath = Join-Path $env:USERPROFILE ".ssh\known_hosts"
}
if ([string]::IsNullOrWhiteSpace($KnownHostsPath) -or -not (Test-Path -LiteralPath $KnownHostsPath -PathType Leaf)) {
    throw "Apply blocked: set LUMA_SSH_KNOWN_HOSTS or pass an existing -KnownHostsPath."
}
$KeyPath = (Resolve-Path -LiteralPath $KeyPath).Path
$KnownHostsPath = (Resolve-Path -LiteralPath $KnownHostsPath).Path
$sshSecurityArgs = @(
    "-o", "BatchMode=yes",
    "-o", "StrictHostKeyChecking=yes",
    "-o", "UserKnownHostsFile=$KnownHostsPath"
)

Write-Host "=================================================="
Write-Host " LumaTrader → Oracle Linux Upload"
Write-Host " Transport inputs validated; host and key values are not echoed."
Write-Host " Mode   : $(if ($FullStack) { 'full stack' } else { 'lean deploy' })"
Write-Host " DryRun : $DryRun"
Write-Host "=================================================="

# ── Validate key ──────────────────────────────────────────
if (-not (Test-Path $KeyPath)) {
    Write-Error "SSH key not found at $KeyPath"
    exit 1
}

# Fix key permissions (ssh is picky on Windows)
icacls $KeyPath /inheritance:r /grant:r "${env:USERNAME}:(R)" | Out-Null

# ── Zip the stack (exclude bulky data by default) ─────────
if (-not $SkipZip) {
    Write-Host "[1/3] Zipping stack..."
    if (Test-Path $ZipOut) { Remove-Item $ZipOut -Force }

    if ($DryRun) {
        Write-Host "  [DryRun] Would zip $Root → $ZipOut"
    } else {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $compressionLevel = [System.IO.Compression.CompressionLevel]::Optimal

        $zip = [System.IO.Compression.ZipFile]::Open($ZipOut, 'Create')
        $excludeDirs  = @(".venv", "venv", "__pycache__", ".git", "node_modules", "data", "out", "logs", "reports", "archive", "archives", "backups", "cache")
        $excludeExts  = @(".pyc", ".pyo")
        $leanRoots    = @("code", "LamaScout", "config")
        $rootFiles    = @("control_flags.json", "execution_runtime.json", "paper_trade_runtime.json", "paper_trade_state.json", "runtime_env_hydration_proof.json", "PERSISTED_RUNTIME_LOCK_PROOF.json")

        Get-ChildItem -Path $Root -Recurse -File | Where-Object {
            $rel = $_.FullName.Substring($Root.Length + 1)
            $parts = $rel.Split([IO.Path]::DirectorySeparatorChar)
            $skip = $false

            if (-not $FullStack) {
                $top = $parts[0]
                $isLeanRoot = $leanRoots -contains $top
                $isRootFile = ($parts.Count -eq 1) -and ($rootFiles -contains $_.Name)
                if (-not ($isLeanRoot -or $isRootFile)) { $skip = $true }
            }

            foreach ($ex in $excludeDirs) {
                if ($parts -contains $ex) { $skip = $true; break }
            }
            if ($excludeExts -contains $_.Extension) { $skip = $true }
            -not $skip
        } | ForEach-Object {
            $entryName = "INSTITUTIONAL_STACK_V2\" + $_.FullName.Substring($Root.Length + 1)
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $zip, $_.FullName, $entryName, $compressionLevel) | Out-Null
        }
        $zip.Dispose()
        $size = [math]::Round((Get-Item $ZipOut).Length / 1MB, 1)
        Write-Host "  Zip created: $ZipOut ($size MB)"
    }
} else {
    Write-Host "[1/3] SkipZip flag set, using existing $ZipOut"
}

# ── SCP zip to Oracle ─────────────────────────────────────
Write-Host "[2/3] Uploading zip to $OracleUser@${OracleIP}:~/ ..."
if ($DryRun) {
    Write-Host "  [DryRun] scp -i `"$KeyPath`" `"$ZipOut`" $OracleUser@${OracleIP}:~/"
    Write-Host "  [DryRun] scp -i `"$KeyPath`" `"$Bootstrap`" $OracleUser@${OracleIP}:~/ORACLE_LINUX_BOOTSTRAP.sh"
} else {
    & scp @sshSecurityArgs -i "$KeyPath" "$ZipOut" "${OracleUser}@${OracleIP}:~/"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "SCP of zip failed. Verify Oracle username, SSH key, and instance networking."
        exit 1
    }
    & scp @sshSecurityArgs -i "$KeyPath" "$Bootstrap" "${OracleUser}@${OracleIP}:~/ORACLE_LINUX_BOOTSTRAP.sh"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "SCP of bootstrap script failed. Verify Oracle username, SSH key, and instance networking."
        exit 1
    }
    Write-Host "  Upload complete."
}

# ── SSH and run bootstrap ─────────────────────────────────
Write-Host "[3/3] Running bootstrap on Oracle VPS..."
$remoteCmd = "chmod +x ~/ORACLE_LINUX_BOOTSTRAP.sh && bash ~/ORACLE_LINUX_BOOTSTRAP.sh $Domain"
if ($DryRun) {
    Write-Host "  [DryRun] ssh -i `"$KeyPath`" $OracleUser@$OracleIP `"$remoteCmd`""
} else {
    & ssh @sshSecurityArgs -i "$KeyPath" "${OracleUser}@${OracleIP}" "$remoteCmd"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "SSH bootstrap execution failed. Verify Oracle username, SSH key, and instance networking."
        exit 1
    }
}

Write-Host ""
Write-Host "=================================================="
Write-Host " Done. Next step:"
Write-Host "   Verify DNS against the operator-approved host, then run the public canary."
Write-Host "=================================================="
