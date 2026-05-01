param(
    [int]$WaitSeconds = 40
)

$ErrorActionPreference = "Stop"

$Root = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$Code = Join-Path $Root "code"
$OutDir = Join-Path $Root "out\execution"
$StdOutLog = Join-Path $OutDir "public_dashboard_tunnel_stdout.log"
$StdErrLog = Join-Path $OutDir "public_dashboard_tunnel_stderr.log"
$StatusPath = Join-Path $OutDir "public_dashboard_tunnel_status.json"
$UrlPath = Join-Path $OutDir "public_dashboard_url.txt"
$PublicUrlPattern = 'https://[a-z0-9-]+\.trycloudflare\.com'

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Get-CloudflaredPath {
    $candidates = @(
        "C:\Program Files (x86)\cloudflared\cloudflared.exe",
        "C:\ProgramData\chocolatey\lib\cloudflared\tools\cloudflared.exe",
        "C:\ProgramData\chocolatey\bin\cloudflared.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    throw "cloudflared executable not found."
}

function Write-Status {
    param(
        [string]$State,
        [string]$Url = "",
        [int]$ProcessId = 0,
        [string]$Message = ""
    )

    $payload = [ordered]@{
        generated_utc = [DateTime]::UtcNow.ToString("o")
        state = $State
        url = $Url
        pid = $ProcessId
        message = $Message
        stdout_log = $StdOutLog
        stderr_log = $StdErrLog
    }
    $payload | ConvertTo-Json -Depth 4 | Set-Content -Path $StatusPath -Encoding UTF8
    if ($Url) {
        Set-Content -Path $UrlPath -Value $Url -Encoding ASCII
    }
}

function Get-LatestTunnelUrl {
    $candidates = @($StdOutLog, $StdErrLog)
    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate)) {
            continue
        }

        $content = Get-Content -LiteralPath $candidate -Raw -ErrorAction SilentlyContinue
        if (-not $content) {
            continue
        }

        $match = [regex]::Match($content, $PublicUrlPattern)
        if ($match.Success) {
            return $match.Value
        }
    }
    return ""
}

function Get-ExistingTunnelProcess {
    $needle = "tunnel --url http://127.0.0.1:80 --no-autoupdate"
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -like "cloudflared*" -and
            $_.CommandLine -like "*${needle}*"
        } |
        Select-Object -First 1
}

$existing = Get-ExistingTunnelProcess
if ($null -ne $existing) {
    $existingUrl = Get-LatestTunnelUrl
    Write-Status -State "running" -Url $existingUrl -ProcessId $existing.ProcessId -Message "existing tunnel process detected"
    Write-Host "[OK] Existing public tunnel process detected: PID $($existing.ProcessId)"
    if ($existingUrl) {
        Write-Host "[OK] Public URL: $existingUrl"
    }
    exit 0
}

$cloudflared = Get-CloudflaredPath
Remove-Item -LiteralPath $StdOutLog, $StdErrLog -Force -ErrorAction SilentlyContinue

$startArgs = @{
    FilePath = $cloudflared
    ArgumentList = @("tunnel", "--url", "http://127.0.0.1:80", "--no-autoupdate")
    WorkingDirectory = $Code
    WindowStyle = "Hidden"
    RedirectStandardOutput = $StdOutLog
    RedirectStandardError = $StdErrLog
    PassThru = $true
}

$proc = Start-Process @startArgs

$deadline = (Get-Date).AddSeconds($WaitSeconds)
$publicUrl = ""
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 750
    $publicUrl = Get-LatestTunnelUrl
    if ($publicUrl) {
        break
    }
    if ($proc.HasExited) {
        break
    }
}

if ($proc.HasExited) {
    $stderr = if (Test-Path -LiteralPath $StdErrLog) { (Get-Content -LiteralPath $StdErrLog -Raw -ErrorAction SilentlyContinue) } else { "" }
    $stdout = if (Test-Path -LiteralPath $StdOutLog) { (Get-Content -LiteralPath $StdOutLog -Raw -ErrorAction SilentlyContinue) } else { "" }
    $msg = ($stderr, $stdout -join "`n").Trim()
    Write-Status -State "failed" -ProcessId $proc.Id -Message $msg
    throw "cloudflared exited before publishing a URL. $msg"
}

if (-not $publicUrl) {
    Write-Status -State "pending" -ProcessId $proc.Id -Message "tunnel started but URL not observed before timeout"
    Write-Host "[WARN] Tunnel started but public URL was not captured within $WaitSeconds seconds."
    exit 0
}

Write-Status -State "running" -Url $publicUrl -ProcessId $proc.Id -Message "public dashboard tunnel active"
Write-Host "[OK] Public dashboard tunnel active: $publicUrl"
