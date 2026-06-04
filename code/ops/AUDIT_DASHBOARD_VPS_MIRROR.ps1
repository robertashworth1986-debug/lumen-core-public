param(
    [string]$RootDashboardPath = "C:\LumaTrader\dashboard",
    [string]$StackDashboardPath = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\dashboard",
    [string]$VpsBaseUrl = "https://lumen-core.ai",
    [string[]]$VpsBaseUrls = @(),
    [bool]$TreatSinglePageDashboardAsHealthy = $true,
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

function Resolve-VpsBaseUrls {
    param(
        [string]$Primary,
        [string[]]$Extras
    )

    $bases = New-Object System.Collections.Generic.List[string]

    if (-not [string]::IsNullOrWhiteSpace($Primary)) {
        $bases.Add($Primary.Trim())
    }

    foreach ($candidate in $Extras) {
        if (-not [string]::IsNullOrWhiteSpace($candidate)) {
            $bases.Add($candidate.Trim())
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($Primary)) {
        try {
            $uri = [System.Uri]::new($Primary)
            if ($uri.Scheme -and $uri.Host) {
                $root = "{0}://{1}" -f $uri.Scheme, $uri.Host
                if (-not $uri.IsDefaultPort) {
                    $root = "{0}:{1}" -f $root, $uri.Port
                }
                $bases.Add($root)
                $bases.Add(($root.TrimEnd("/")) + "/dashboard")
            }
        }
        catch {
            # Ignore URI parse errors and continue with explicit candidates only.
        }
    }

    $seen = @{}
    $resolved = @()
    foreach ($base in $bases) {
        $trimmed = $base.Trim().TrimEnd("/")
        if ([string]::IsNullOrWhiteSpace($trimmed)) {
            continue
        }
        if (-not $seen.ContainsKey($trimmed)) {
            $seen[$trimmed] = $true
            $resolved += $trimmed
        }
    }

    if (@($resolved).Count -eq 0) {
        $resolved = @("https://lumen-core.ai")
    }

    return $resolved
}

function Invoke-FetchVpsUrl {
    param(
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -UseBasicParsing -TimeoutSec 25
        return [PSCustomObject]@{
            ok = $true
            status_code = [int]$response.StatusCode
            body = [string]$response.Content
            url = $Url
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
            url = $Url
            error = [string]$_.Exception.Message
        }
    }
}

function Invoke-FetchVpsFile {
    param(
        [string]$BaseUrl,
        [string]$FileName
    )

    $url = ($BaseUrl.TrimEnd("/")) + "/" + $FileName
    return Invoke-FetchVpsUrl -Url $url
}

$stamp = Get-UtcStamp
$runDir = Join-Path $OutputRoot ("dashboard_vps_mirror_audit_" + $stamp)
New-Item -ItemType Directory -Path $runDir -Force | Out-Null

$resolvedVpsBases = Resolve-VpsBaseUrls -Primary $VpsBaseUrl -Extras $VpsBaseUrls
$vpsIndexProbeByBase = @{}
$singlePageHealthyBase = ""
$accessLimitedBases = @()

foreach ($base in $resolvedVpsBases) {
    $indexUrl = ($base.TrimEnd("/")) + "/"
    $indexProbe = Invoke-FetchVpsUrl -Url $indexUrl
    $vpsIndexProbeByBase[$base] = $indexProbe
    if (@(401, 403) -contains [int]$indexProbe.status_code) {
        $accessLimitedBases += $base
    }
    if ($indexProbe.ok -and [string]::IsNullOrWhiteSpace($singlePageHealthyBase) -and $base.ToLowerInvariant().Contains("/dashboard")) {
        $singlePageHealthyBase = $base
    }
}

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

    $candidateFetches = @()
    foreach ($base in $resolvedVpsBases) {
        $candidateFetches += Invoke-FetchVpsFile -BaseUrl $base -FileName $file
    }

    $vpsFetch = $null
    foreach ($candidate in $candidateFetches) {
        if ($candidate.ok) {
            $vpsFetch = $candidate
            break
        }
    }
    if ($null -eq $vpsFetch -and @($candidateFetches).Count -gt 0) {
        $vpsFetch = $candidateFetches[0]
    }
    if ($null -eq $vpsFetch) {
        $vpsFetch = [PSCustomObject]@{
            ok = $false
            status_code = 0
            body = ""
            url = ""
            error = "no_vps_candidates_resolved"
        }
    }

    $vpsHash = if ($vpsFetch.ok) { Get-NormalizedSha256FromText -Text $vpsFetch.body } else { "" }

    $allCandidates404 = $true
    foreach ($candidate in $candidateFetches) {
        if ([int]$candidate.status_code -ne 404) {
            $allCandidates404 = $false
            break
        }
    }

    $singlePageFallbackApplied = $false
    if (
        $TreatSinglePageDashboardAsHealthy -and
        $allCandidates404 -and
        -not [string]::IsNullOrWhiteSpace($singlePageHealthyBase)
    ) {
        $singlePageFallbackApplied = $true
    }

    $rootStackSame = ($rootExists -and $stackExists -and $rootHash -eq $stackHash)
    $rootVpsSameStrict = ($rootExists -and $vpsFetch.ok -and $rootHash -eq $vpsHash)
    $stackVpsSameStrict = ($stackExists -and $vpsFetch.ok -and $stackHash -eq $vpsHash)

    $rootVpsSame = $rootVpsSameStrict
    $stackVpsSame = $stackVpsSameStrict
    if ($singlePageFallbackApplied) {
        $rootVpsSame = [bool]$rootExists
        $stackVpsSame = [bool]$stackExists
    }

    $candidateUrls = @($candidateFetches | ForEach-Object { [string]$_.url })
    $candidateStatusCodes = @($candidateFetches | ForEach-Object { [int]$_.status_code })
    $candidateAccessLimited = (@($candidateStatusCodes | Where-Object { $_ -in @(401, 403) }).Count -gt 0)

    $rows += [PSCustomObject]@{
        file = $file
        root_exists = $rootExists
        stack_exists = $stackExists
        vps_fetch_ok = [bool]$vpsFetch.ok
        vps_status_code = [int]$vpsFetch.status_code
        root_stack_same = [bool]$rootStackSame
        root_vps_same = [bool]$rootVpsSame
        root_vps_same_strict = [bool]$rootVpsSameStrict
        stack_vps_same = [bool]$stackVpsSame
        stack_vps_same_strict = [bool]$stackVpsSameStrict
        single_page_fallback_applied = [bool]$singlePageFallbackApplied
        vps_access_limited = [bool]$candidateAccessLimited
        sync_applied = [bool]$syncApplied
        root_sha256_normalized = $rootHash
        stack_sha256_normalized = $stackHash
        vps_sha256_normalized = $vpsHash
        vps_url = $vpsFetch.url
        vps_candidate_urls = ($candidateUrls -join ";")
        vps_candidate_status_codes = ($candidateStatusCodes -join ",")
        vps_error = [string]($vpsFetch.error)
    }
}

$driftRootStack = @($rows | Where-Object { -not $_.root_stack_same }).Count
$driftRootVpsStrict = @($rows | Where-Object { -not $_.root_vps_same_strict }).Count
$driftRootVps = @($rows | Where-Object { -not $_.root_vps_same }).Count
$singlePageFallbackCount = @($rows | Where-Object { $_.single_page_fallback_applied }).Count
$vpsAccessLimitedCount = @($rows | Where-Object { $_.vps_access_limited }).Count
$vpsErrors = @($rows | Where-Object { -not $_.vps_fetch_ok -and -not $_.single_page_fallback_applied -and -not $_.vps_access_limited }).Count

$summary = [PSCustomObject]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString("o")
    scope = "dashboard_vps_mirror_audit"
    root_dashboard_path = $RootDashboardPath
    stack_dashboard_path = $StackDashboardPath
    vps_base_url = $VpsBaseUrl
    vps_base_candidates = @($resolvedVpsBases)
    vps_access_limited_bases = @($accessLimitedBases)
    auto_sync_stack_mirror = [bool]$AutoSyncStackMirror
    treat_single_page_dashboard_as_healthy = [bool]$TreatSinglePageDashboardAsHealthy
    single_page_dashboard_base = $singlePageHealthyBase
    single_page_fallback_count = [int]$singlePageFallbackCount
    files_checked = @($Files).Count
    stack_sync_applied_count = [int]$syncCount
    root_stack_drift_count = [int]$driftRootStack
    root_vps_drift_count_strict = [int]$driftRootVpsStrict
    root_vps_drift_count = [int]$driftRootVps
    vps_access_limited_count = [int]$vpsAccessLimitedCount
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
$md += "- root_vps_drift_count_strict: $($summary.root_vps_drift_count_strict)"
$md += "- root_vps_drift_count: $($summary.root_vps_drift_count)"
$md += "- vps_access_limited_count: $($summary.vps_access_limited_count)"
$md += "- vps_fetch_error_count: $($summary.vps_fetch_error_count)"
$md += "- single_page_fallback_count: $($summary.single_page_fallback_count)"
$md += "- single_page_dashboard_base: $($summary.single_page_dashboard_base)"
$md += ""
$md += "| file | root-stack | root-vps (effective) | root-vps (strict) | vps_http | vps_access_limited | single_page_fallback | sync_applied |"
$md += "|---|---:|---:|---:|---:|---:|---:|---:|"
foreach ($row in $rows) {
    $md += "| $($row.file) | $($row.root_stack_same) | $($row.root_vps_same) | $($row.root_vps_same_strict) | $($row.vps_status_code) | $($row.vps_access_limited) | $($row.single_page_fallback_applied) | $($row.sync_applied) |"
}
$md -join "`r`n" | Set-Content -Path $mdPath -Encoding UTF8

$latestJson = Join-Path $OutputRoot "dashboard_vps_mirror_audit_latest.json"
$latestMd = Join-Path $OutputRoot "dashboard_vps_mirror_audit_latest.md"
Copy-Item -LiteralPath $jsonPath -Destination $latestJson -Force
Copy-Item -LiteralPath $mdPath -Destination $latestMd -Force

Write-Host ("VPS_AUDIT_JSON={0}" -f $jsonPath)
Write-Host ("VPS_AUDIT_MD={0}" -f $mdPath)
Write-Host ("ROOT_STACK_DRIFT={0} ROOT_VPS_DRIFT_STRICT={1} ROOT_VPS_DRIFT={2} VPS_ACCESS_LIMITED={3} VPS_ERRORS={4} SINGLE_PAGE_FALLBACK={5} SYNC_APPLIED={6}" -f $driftRootStack, $driftRootVpsStrict, $driftRootVps, $vpsAccessLimitedCount, $vpsErrors, $singlePageFallbackCount, $syncCount)
