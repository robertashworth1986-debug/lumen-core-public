param(
    [string[]]$CandidateIPs = @("37.27.60.122", "5.161.52.158"),
    [string]$Domain = "lumen-core.ai",
    [switch]$ResetKnownHost,
    [switch]$TrySSH,
    [switch]$RunBootstrapHint
)

$ErrorActionPreference = "Stop"

function Get-HomeSSHPath {
    return Join-Path $env:USERPROFILE ".ssh"
}

function Get-KnownHostsPath {
    return Join-Path (Get-HomeSSHPath) "known_hosts"
}

function Test-TcpPort {
    param(
        [string]$HostName,
        [int]$Port,
        [int]$TimeoutMs = 2500
    )

    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $connectTask = $client.ConnectAsync($HostName, $Port)
        if ($connectTask.Wait($TimeoutMs)) {
            $connected = $client.Connected
        }
        else {
            $connected = $false
        }
        $client.Dispose()
        return $connected
    }
    catch {
        return $false
    }
}

function Test-PortProfile {
    param([string]$HostName)

    $tcp22 = Test-TcpPort -HostName $HostName -Port 22
    $tcp80 = Test-TcpPort -HostName $HostName -Port 80
    $tcp443 = Test-TcpPort -HostName $HostName -Port 443

    $ping = $false
    try {
        $pinger = [System.Net.NetworkInformation.Ping]::new()
        $reply = $pinger.Send($HostName, 1500)
        $ping = ($reply.Status -eq [System.Net.NetworkInformation.IPStatus]::Success)
        $pinger.Dispose()
    }
    catch {
        $ping = $false
    }

    return [pscustomobject]@{
        Host = $HostName
        Tcp22 = $tcp22
        Tcp80 = $tcp80
        Tcp443 = $tcp443
        Ping = $ping
    }
}

function Resolve-DomainIPv4 {
    param([string]$Name)
    try {
        $addresses = [System.Net.Dns]::GetHostAddresses($Name) |
            Where-Object { $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork } |
            ForEach-Object { $_.IPAddressToString }
        return @($addresses)
    }
    catch {
        return @()
    }
}

function Get-ReverseDns {
    param([string]$IP)
    try {
        $text = nslookup $IP | Out-String
        $match = [regex]::Match($text, "Name:\s+(.+)")
        if ($match.Success) {
            return $match.Groups[1].Value.Trim()
        }
    }
    catch {
    }
    return "n/a"
}

function Get-KnownHostHit {
    param([string]$IP)
    $knownHosts = Get-KnownHostsPath
    if (-not (Test-Path $knownHosts)) {
        return $false
    }
    $hit = Select-String -Path $knownHosts -Pattern ([regex]::Escape($IP)) -SimpleMatch -ErrorAction SilentlyContinue
    return ($null -ne $hit)
}

function Remove-KnownHostEntry {
    param([string]$IP)
    Write-Host "Removing stale known_hosts entry for $IP ..." -ForegroundColor Yellow
    & ssh-keygen -R $IP | Out-Host
}

function Try-SSHBatch {
    param([string]$IP)
    Write-Host "Attempting batch SSH to $IP ..." -ForegroundColor Yellow
    & ssh -o BatchMode=yes -o ConnectTimeout=6 -o StrictHostKeyChecking=accept-new root@$IP "hostnamectl --static || hostname"
}

Write-Host "VPS access recovery" -ForegroundColor Cyan
Write-Host "Domain: $Domain"
Write-Host "Candidate IPs: $($CandidateIPs -join ', ')"
Write-Host ""

$domainIPs = Resolve-DomainIPv4 -Name $Domain
if ($domainIPs.Count -gt 0) {
    Write-Host "Domain resolves to: $($domainIPs -join ', ')" -ForegroundColor Yellow
}
else {
    Write-Host "Domain resolves to: n/a" -ForegroundColor Yellow
}
Write-Host ""

$rows = @()
foreach ($ip in $CandidateIPs) {
    $port = Test-PortProfile -HostName $ip
    $rdns = Get-ReverseDns -IP $ip
    $known = Get-KnownHostHit -IP $ip
    $rows += [pscustomobject]@{
        IP = $ip
        Tcp22 = $port.Tcp22
        Tcp80 = $port.Tcp80
        Tcp443 = $port.Tcp443
        Ping = $port.Ping
        ReverseDNS = $rdns
        KnownHostsEntry = $known
        LikelyProvider = if ($rdns -like "*.your-server.de") { "Hetzner" } else { "unknown" }
    }
}

$rows | Format-Table -AutoSize | Out-Host

$primary = $rows | Where-Object { $_.IP -eq "37.27.60.122" } | Select-Object -First 1
if ($null -ne $primary) {
    Write-Host ""
    Write-Host "Primary candidate:" -ForegroundColor Green
    Write-Host "  IP: $($primary.IP)"
    Write-Host "  Provider hint: $($primary.LikelyProvider)"
    Write-Host "  Reverse DNS: $($primary.ReverseDNS)"
    Write-Host "  TCP/22 reachable: $($primary.Tcp22)"
    Write-Host "  TCP/80 reachable: $($primary.Tcp80)"
    Write-Host "  TCP/443 reachable: $($primary.Tcp443)"
}

if ($ResetKnownHost) {
    foreach ($ip in $CandidateIPs) {
        if (Get-KnownHostHit -IP $ip) {
            Remove-KnownHostEntry -IP $ip
        }
    }
}

if ($TrySSH) {
    foreach ($ip in $CandidateIPs) {
        Try-SSHBatch -IP $ip
    }
}

Write-Host ""
Write-Host "Recommended next commands" -ForegroundColor Cyan
Write-Host "1. Verify the server in Hetzner Cloud console first."
Write-Host "2. If 37.27.60.122 is your box, run:" -ForegroundColor White
Write-Host "   ssh-keygen -R 37.27.60.122" -ForegroundColor Gray
Write-Host "   ssh root@37.27.60.122" -ForegroundColor Gray
Write-Host ""
Write-Host "3. After login, bootstrap the public stack:" -ForegroundColor White
Write-Host "   powershell -ExecutionPolicy Bypass -File .\\ops\\BOOTSTRAP_PUBLIC_VPS.ps1 -Domain lumen-core.ai -RunReconnect -RunEliteOptimizer -InstallScheduledTasks" -ForegroundColor Gray

if ($RunBootstrapHint) {
    Write-Host ""
    Write-Host "Bootstrap script path:" -ForegroundColor Green
    Write-Host "  c:\LumaTrader\INSTITUTIONAL_STACK_V2\code\ops\BOOTSTRAP_PUBLIC_VPS.ps1"
}
