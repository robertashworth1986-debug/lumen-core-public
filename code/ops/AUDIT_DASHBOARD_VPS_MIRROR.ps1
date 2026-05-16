param(
    [string]$RootDashboardPath = "C:\LumaTrader\dashboard",
    [string]$StackDashboardPath = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\dashboard",
    [string]$VpsBaseUrl = "https://lumen-core.ai",
    [string]$OutputRoot = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\ops",
    [switch]$AutoSyncStackMirror,
    [string[]]$Files = @(
        "mission_control.html",
        "quant_lab.html",
        "investor_command_room.html",
        "kraken_execution_dashboard.html",
        "luma_experience.html",
        "scenario_mission.html",
        "grants.html",
        "investor_wallboard.html"
    )
)

$ErrorActionPreference = "Stop"

function Get-UtcStamp {
    return (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
}

function Get-NormalizedSha256FromText {
    param([string]$Text)
    if ($null -eq $Text) {
        return ""
    }
    $normalized = ($Text -replace "`r`n", "`n" -replace "`r", "`n")
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($normalized)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $sha.ComputeHash($bytes)
        return ([System.BitConverter]::ToString($hashBytes)).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

function Get-NormalizedSha256FromFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return ""
    }
    try {
        $text = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    }
    catch {
        $text = Get-Content -LiteralPath $Path -Raw
    }
    return Get-NormalizedSha256FromText -Text $text
}

function Invoke-FetchVpsFile {
    param(
        [string]$BaseUrl,
        [string]$FileName
    )

    $url = ($BaseUrl.TrimEnd("/")) + "/" + $FileName
    try {
        $response = Invoke-WebRequest -Uri $url -Method Get -UseBasicParsing -TimeoutSec 25
        return [PSCustomObject]@{
            ok = $true
            status_code = [int]$response.StatusCode
            body = [string]$response.Content
            url = $url
            error = $null
        }
    }
    catch {
        $statusCode = 0
        try {
            if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
                $statusCode = [int]$_.Exception.Response.StatusCode
            }
        }
        catch {
            $statusCode = 0
        }

        return [PSCustomObject]@{
            ok = $false
            status_code = $statusCode
            body = ""
            url = $url
            error = [string]$_.Exception.Message
        }
    }
}

$stamp = Get-UtcStamp
$runDir = Join-Path $OutputRoot ("dashboard_vps_mirror_audit_" + $stamp)
New-Item -ItemType Directory -Path $runDir -Force | Out-Null

$rows = @()
$syncCount = 0

foreach ($file in $Files) {
    $rootFile = Join-Path $RootDashboardPath $file
    $stackFile = Join-Path $StackDashboardPath $file

    $rootExists = Test-Path -LiteralPath $rootFile
    $stackExists = Test-Path -LiteralPath $stackFile

    $rootHash = if ($rootExists) { Get-NormalizedSha256FromFile -Path $rootFile } else { "" }
    $stackHash = if ($stackExists) { Get-NormalizedSha256FromFile -Path $stackFile } else { "" }

    $syncApplied = $false
    if ($AutoSyncStackMirror -and $rootExists) {
        if ((-not $stackExists) -or ($rootHash -ne $stackHash)) {
            Copy-Item -LiteralPath $rootFile -Destination $stackFile -Force
            $stackExists = Test-Path -LiteralPath $stackFile
            $stackHash = if ($stackExists) { Get-NormalizedSha256FromFile -Path $stackFile } else { "" }
            $syncApplied = $true
            $syncCount += 1
        }
    }

    $vpsFetch = Invoke-FetchVpsFile -BaseUrl $VpsBaseUrl -FileName $file
    $vpsHash = if ($vpsFetch.ok) { Get-NormalizedSha256FromText -Text $vpsFetch.body } else { "" }

    $rootStackSame = ($rootExists -and $stackExists -and $rootHash -eq $stackHash)
    $rootVpsSame = ($rootExists -and $vpsFetch.ok -and $rootHash -eq $vpsHash)
    $stackVpsSame = ($stackExists -and $vpsFetch.ok -and $stackHash -eq $vpsHash)

    $rows += [PSCustomObject]@{
        file = $file
        root_exists = $rootExists
        stack_exists = $stackExists
        vps_fetch_ok = [bool]$vpsFetch.ok
        vps_status_code = [int]$vpsFetch.status_code
        root_stack_same = [bool]$rootStackSame
        root_vps_same = [bool]$rootVpsSame
        stack_vps_same = [bool]$stackVpsSame
        sync_applied = [bool]$syncApplied
        root_sha256_normalized = $rootHash
        stack_sha256_normalized = $stackHash
        vps_sha256_normalized = $vpsHash
        vps_url = $vpsFetch.url
        vps_error = [string]($vpsFetch.error)
    }
}

$driftRootStack = @($rows | Where-Object { -not $_.root_stack_same }).Count
$driftRootVps = @($rows | Where-Object { -not $_.root_vps_same }).Count
$vpsErrors = @($rows | Where-Object { -not $_.vps_fetch_ok }).Count

$summary = [PSCustomObject]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString("o")
    scope = "dashboard_vps_mirror_audit"
    root_dashboard_path = $RootDashboardPath
    stack_dashboard_path = $StackDashboardPath
    vps_base_url = $VpsBaseUrl
    auto_sync_stack_mirror = [bool]$AutoSyncStackMirror
    files_checked = @($Files).Count
    stack_sync_applied_count = [int]$syncCount
    root_stack_drift_count = [int]$driftRootStack
    root_vps_drift_count = [int]$driftRootVps
    vps_fetch_error_count = [int]$vpsErrors
}

$csvPath = Join-Path $runDir "dashboard_vps_mirror_audit.csv"
$rows | Export-Csv -NoTypeInformation -Path $csvPath -Encoding UTF8

$jsonPath = Join-Path $runDir "dashboard_vps_mirror_audit.json"
[PSCustomObject]@{
    summary = $summary
    rows = $rows
} | ConvertTo-Json -Depth 8 | Set-Content -Path $jsonPath -Encoding UTF8

$mdPath = Join-Path $runDir "dashboard_vps_mirror_audit.md"
$md = @()
$md += "# Dashboard VPS Mirror Audit"
$md += ""
$md += "- generated_utc: $($summary.generated_utc)"
$md += "- vps_base_url: $($summary.vps_base_url)"
$md += "- files_checked: $($summary.files_checked)"
$md += "- stack_sync_applied_count: $($summary.stack_sync_applied_count)"
$md += "- root_stack_drift_count: $($summary.root_stack_drift_count)"
$md += "- root_vps_drift_count: $($summary.root_vps_drift_count)"
$md += "- vps_fetch_error_count: $($summary.vps_fetch_error_count)"
$md += ""
$md += "| file | root-stack | root-vps | vps_http | sync_applied |"
$md += "|---|---:|---:|---:|---:|"
foreach ($row in $rows) {
    $md += "| $($row.file) | $($row.root_stack_same) | $($row.root_vps_same) | $($row.vps_status_code) | $($row.sync_applied) |"
}
$md -join "`r`n" | Set-Content -Path $mdPath -Encoding UTF8

$latestJson = Join-Path $OutputRoot "dashboard_vps_mirror_audit_latest.json"
$latestMd = Join-Path $OutputRoot "dashboard_vps_mirror_audit_latest.md"
Copy-Item -LiteralPath $jsonPath -Destination $latestJson -Force
Copy-Item -LiteralPath $mdPath -Destination $latestMd -Force

Write-Host ("VPS_AUDIT_JSON={0}" -f $jsonPath)
Write-Host ("VPS_AUDIT_MD={0}" -f $mdPath)
Write-Host ("ROOT_STACK_DRIFT={0} ROOT_VPS_DRIFT={1} VPS_ERRORS={2} SYNC_APPLIED={3}" -f $driftRootStack, $driftRootVps, $vpsErrors, $syncCount)
