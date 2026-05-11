param(
  [string]$BaseUrl = "https://lumen-core.ai",
  [switch]$IncludeSshChecks,
  [string]$SshUser = "opc",
  [string]$SshHost = "157.151.148.234",
  [string]$SshKeyPath = "C:\Users\Novac\Downloads\ssh-key-2026-04-23.key",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Test-HttpEndpoint {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Method,
    [Parameter(Mandatory = $true)][string]$Url,
    [int[]]$ExpectedCodes = @(200),
    [string]$Body = ""
  )

  try {
    if ($Method -eq "POST") {
      $response = Invoke-WebRequest -Uri $Url -Method Post -ContentType "application/json" -Body $Body -TimeoutSec 20
    } else {
      $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 20
    }

    $code = [int]$response.StatusCode
    $ok = $ExpectedCodes -contains $code

    return [pscustomobject]@{
      name = $Name
      method = $Method
      url = $Url
      status_code = $code
      ok = $ok
      error = ""
    }
  }
  catch {
    $code = -1
    if ($_.Exception.Response) {
      try { $code = [int]$_.Exception.Response.StatusCode } catch {}
    }

    return [pscustomobject]@{
      name = $Name
      method = $Method
      url = $Url
      status_code = $code
      ok = $false
      error = $_.Exception.Message
    }
  }
}

$base = $BaseUrl.TrimEnd('/')
$httpChecks = @(
  @{ name = "Home"; method = "GET"; path = "/"; expected = @(200) },
  @{ name = "Mission control"; method = "GET"; path = "/mission_control.html"; expected = @(200) },
  @{ name = "Snapshot API"; method = "GET"; path = "/api/snapshot"; expected = @(200) },
  @{ name = "Unity edge API"; method = "GET"; path = "/api/unity/edge"; expected = @(200) },
  @{ name = "Unity unified edge API"; method = "GET"; path = "/api/unity/unified-edge"; expected = @(200) },
  @{ name = "Gateway health"; method = "GET"; path = "/health"; expected = @(200) },
  @{ name = "Edge health marker"; method = "GET"; path = "/nginx-health"; expected = @(200) },
  @{ name = "Node-RED ingest"; method = "POST"; path = "/api/nodered/ingest"; expected = @(200); body = '{"source":"ned_preflight","ok":true}' }
)

$httpResults = New-Object System.Collections.Generic.List[object]
foreach ($check in $httpChecks) {
  $url = "$base$($check.path)"
  $body = if ($check.ContainsKey("body")) { [string]$check.body } else { "" }
  $result = Test-HttpEndpoint -Name $check.name -Method $check.method -Url $url -ExpectedCodes $check.expected -Body $body
  $httpResults.Add($result)
}

$sshResults = @()
if ($IncludeSshChecks) {
  $sshCmd = Get-Command ssh -ErrorAction SilentlyContinue
  if (-not $sshCmd) {
    $sshResults += [pscustomobject]@{ service = "ssh_client"; status = "missing"; detail = "ssh command not found" }
  }
  elseif (-not (Test-Path $SshKeyPath)) {
    $sshResults += [pscustomobject]@{ service = "ssh_key"; status = "missing"; detail = "SSH key not found at $SshKeyPath" }
  }
  else {
    $remote = 'for s in caddy luma-gateway luma-dashboard-refresh luma-node-red luma-nodered-flow-sync; do if systemctl list-unit-files | grep -q "^${s}.service"; then st=$(systemctl is-active "$s" 2>/dev/null || true); echo "${s}=${st}"; else echo "${s}=missing"; fi; done'
    $target = "$SshUser@$SshHost"

    try {
      $output = & ssh -i $SshKeyPath -o StrictHostKeyChecking=accept-new $target $remote 2>&1
      if ($LASTEXITCODE -ne 0) {
        $sshResults += [pscustomobject]@{ service = "ssh"; status = "error"; detail = ($output | Out-String).Trim() }
      }
      else {
        foreach ($line in $output) {
          $text = [string]$line
          if ($text -match "^([^=]+)=([^=]+)$") {
            $sshResults += [pscustomobject]@{ service = $Matches[1]; status = $Matches[2]; detail = "" }
          }
        }
      }
    }
    catch {
      $sshResults += [pscustomobject]@{ service = "ssh"; status = "error"; detail = $_.Exception.Message }
    }
  }
}

$httpFailed = @($httpResults | Where-Object { -not $_.ok }).Count
$sshFailed = @($sshResults | Where-Object { $_.status -in @("failed", "inactive", "error", "missing") -and $_.service -notin @("luma-node-red", "luma-nodered-flow-sync") }).Count
$overallReady = ($httpFailed -eq 0 -and $sshFailed -eq 0)

$summary = [pscustomobject]@{
  generated_utc = (Get-Date).ToUniversalTime().ToString("o")
  base_url = $base
  overall_ready = $overallReady
  http_checks_total = $httpResults.Count
  http_checks_failed = $httpFailed
  ssh_checks_total = $sshResults.Count
  ssh_checks_failed = $sshFailed
  http_checks = $httpResults
  ssh_checks = $sshResults
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
  $OutFile = Join-Path $workspaceRoot "reports\NED_Showcase_2026-05-21\preflight_latest.json"
}

$parent = Split-Path -Parent $OutFile
if (-not (Test-Path $parent)) {
  New-Item -ItemType Directory -Path $parent -Force | Out-Null
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $OutFile -Encoding UTF8

Write-Host ""
Write-Host "NED preflight summary"
Write-Host "- overall_ready: $($summary.overall_ready)"
Write-Host "- http failed: $($summary.http_checks_failed) / $($summary.http_checks_total)"
if ($IncludeSshChecks) {
  Write-Host "- ssh failed:  $($summary.ssh_checks_failed) / $($summary.ssh_checks_total)"
}
Write-Host "- output: $OutFile"
Write-Host ""

$httpResults | Select-Object name, status_code, ok | Format-Table -AutoSize
if ($IncludeSshChecks -and $sshResults.Count -gt 0) {
  Write-Host ""
  $sshResults | Select-Object service, status | Format-Table -AutoSize
}

if (-not $overallReady) {
  exit 1
}
