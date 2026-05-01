param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 5016,
    [int]$MaxHeartbeatAgeSeconds = 180,
    [string]$LatestFile = "",
    [string]$HistoryFile = "",
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$HEARTBEAT = Join-Path $ROOT "out\execution\institutional_crypto_dashboard_heartbeat.json"
$URL = "http://$BindHost`:$Port"

$heartbeatOk = $false
$httpOk = $false
$details = @{}

if (Test-Path $HEARTBEAT) {
    try {
        $hb = Get-Content $HEARTBEAT -Raw | ConvertFrom-Json
        $ts = [datetimeoffset]::Parse($hb.timestamp_utc)
        $age = ([datetimeoffset]::UtcNow - $ts).TotalSeconds
        $hbMode = [string]$hb.mode
        $hbStatus = [string]$hb.status
        $hbPort = [int]($hb.port)

        $details.heartbeat_status = $hb.status
        $details.heartbeat_mode = $hb.mode
        $details.heartbeat_port = [int]$hb.port
        $details.heartbeat_age_seconds = [math]::Round($age, 2)

        $serveHeartbeatOk = (
            $hbMode -eq "serve" -and
            $hbStatus -eq "ok" -and
            $hbPort -eq $Port -and
            $age -le $MaxHeartbeatAgeSeconds
        )
        $exportHeartbeatOk = (
            $hbMode -eq "export" -and
            $hbStatus -eq "ok" -and
            $age -le $MaxHeartbeatAgeSeconds
        )

        $heartbeatOk = ($serveHeartbeatOk -or $exportHeartbeatOk)
        if ($serveHeartbeatOk) {
            $details.heartbeat_acceptance = "serve_mode"
        } elseif ($exportHeartbeatOk) {
            $details.heartbeat_acceptance = "export_mode"
        } else {
            $details.heartbeat_acceptance = "none"
        }
    } catch {
        $details.heartbeat_error = $_.Exception.Message
    }
} else {
    $details.heartbeat_error = "missing_heartbeat_file"
}

try {
    $resp = Invoke-WebRequest -Uri $URL -UseBasicParsing -TimeoutSec 5
    $body = [string]$resp.Content
    $details.http_status_code = [int]$resp.StatusCode
    $httpOk = ($resp.StatusCode -eq 200 -and $body -like "*Nobel Tier Institutional Crypto Deck*")
} catch {
    $details.http_error = $_.Exception.Message
}

$result = [ordered]@{
    timestamp_utc = [datetime]::UtcNow.ToString("o")
    dashboard_url = $URL
    heartbeat_file = $HEARTBEAT
    heartbeat_ok = $heartbeatOk
    http_ok = $httpOk
    healthy = ($heartbeatOk -and $httpOk)
    details = $details
}

$resultJson = $result | ConvertTo-Json -Depth 6

if ($LatestFile -ne "") {
    try {
        $latestDir = Split-Path -Parent $LatestFile
        if ($latestDir -and -not (Test-Path $latestDir)) {
            New-Item -ItemType Directory -Path $latestDir -Force | Out-Null
        }
        Set-Content -Path $LatestFile -Value $resultJson -Encoding UTF8
    } catch {
    }
}

if ($HistoryFile -ne "") {
    try {
        $historyDir = Split-Path -Parent $HistoryFile
        if ($historyDir -and -not (Test-Path $historyDir)) {
            New-Item -ItemType Directory -Path $historyDir -Force | Out-Null
        }
        Add-Content -Path $HistoryFile -Value ($resultJson -replace "`r?`n", "") -Encoding UTF8
    } catch {
    }
}

if (-not $Quiet) {
    Write-Output $resultJson
}

if (-not $result.healthy) {
    exit 1
}
