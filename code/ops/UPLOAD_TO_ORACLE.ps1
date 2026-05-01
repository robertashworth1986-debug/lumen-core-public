# ============================================================
# UPLOAD_TO_ORACLE.ps1
# Zips the stack (no .venv) and SCPs it to Oracle VPS.
# Usage:
#   .\ops\UPLOAD_TO_ORACLE.ps1 -OracleIP 1.2.3.4 -KeyPath "$env:USERPROFILE\Downloads\oracle_new"
# ============================================================
param(
    [Parameter(Mandatory=$true)]
    [string]$OracleIP,

    [string]$KeyPath = "$env:USERPROFILE\Downloads\oracle_new",
    [string]$OracleUser = "opc",
    [string]$Domain = "lumen-core.ai",
    [switch]$FullStack,
    [switch]$SkipZip,
    [switch]$DryRun
)

$Root      = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$ZipOut    = "$env:TEMP\INSTITUTIONAL_STACK_V2.zip"
$Bootstrap = "$Root\code\ops\ORACLE_LINUX_BOOTSTRAP.sh"

Write-Host "=================================================="
Write-Host " LumaTrader → Oracle Linux Upload"
Write-Host " Target : $OracleUser@$OracleIP"
Write-Host " Key    : $KeyPath"
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
    scp -o StrictHostKeyChecking=no -i "$KeyPath" "$ZipOut" "${OracleUser}@${OracleIP}:~/"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "SCP of zip failed. Verify Oracle username, SSH key, and instance networking."
        exit 1
    }
    scp -o StrictHostKeyChecking=no -i "$KeyPath" "$Bootstrap" "${OracleUser}@${OracleIP}:~/ORACLE_LINUX_BOOTSTRAP.sh"
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
    ssh -o StrictHostKeyChecking=no -i "$KeyPath" "${OracleUser}@${OracleIP}" "$remoteCmd"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "SSH bootstrap execution failed. Verify Oracle username, SSH key, and instance networking."
        exit 1
    }
}

Write-Host ""
Write-Host "=================================================="
Write-Host " Done. Next step:"
Write-Host "   Point $Domain A record → $OracleIP"
Write-Host "   Then visit: http://$OracleIP"
Write-Host "=================================================="
