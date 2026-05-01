$ErrorActionPreference = 'Stop'

$taskNames = @(
    'Luma-DashboardRefreshLoop',
    'Luma-PaperTraderLoop',
    'Luma-CrossSectorStack',
    'Luma-PublicDashboardTunnel'
)

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)

if (-not $isAdmin) {
    Write-Host '[WARN] Running without elevation. SYSTEM startup tasks may not be visible from this shell.'
}

$rows = foreach ($name in $taskNames) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        TaskName = $name
        Exists = if ($task) { $true } elseif ($isAdmin) { $false } else { 'unknown' }
        State = if ($task) { $task.State } elseif ($isAdmin) { 'missing' } else { 'visibility-limited' }
    }
}

$rows | Format-Table -AutoSize
