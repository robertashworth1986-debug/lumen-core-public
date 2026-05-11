param(
    [ValidateSet('start', 'stop', 'restart', 'status')]
    [string]$Action = 'status',

    [ValidateSet('dashboard', 'core', 'full')]
    [string]$StackGroup = 'core',

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$stackRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$codeRoot = Join-Path $stackRoot 'code'
$runRoot = Join-Path $stackRoot 'run'
$registryPath = Join-Path $runRoot 'managed_runtime_processes.json'

New-Item -Path $runRoot -ItemType Directory -Force | Out-Null

function Get-UtcNowIso {
    return [DateTime]::UtcNow.ToString('o')
}

function Resolve-PythonRuntime {
    $candidates = @(
        (Join-Path $stackRoot '.venv\Scripts\python.exe'),
        (Join-Path $codeRoot '.venv\Scripts\python.exe'),
        (Join-Path $stackRoot '..\venv3.11\Scripts\python.exe'),
        (Join-Path $stackRoot '..\.venv\Scripts\python.exe'),
        'C:\LumaTrader\venv3.11\Scripts\python.exe',
        'C:\LumaTrader\.venv\Scripts\python.exe'
    )

    foreach ($candidate in $candidates) {
        try {
            $resolved = (Resolve-Path $candidate -ErrorAction Stop).Path
            if (Test-Path $resolved) {
                return $resolved
            }
        } catch {
            continue
        }
    }

    throw 'Python runtime not found. Checked .venv and venv3.11 locations.'
}

function Read-Registry {
    if (-not (Test-Path $registryPath)) {
        return @()
    }

    try {
        $raw = Get-Content $registryPath -Raw -ErrorAction Stop
        if ([string]::IsNullOrWhiteSpace($raw)) {
            return @()
        }

        $parsed = $raw | ConvertFrom-Json -ErrorAction Stop
        if ($null -eq $parsed) {
            return @()
        }

        return @($parsed)
    } catch {
        return @()
    }
}

function Write-Registry {
    param([object[]]$Records)

    $safe = @($Records | Where-Object { $_ -ne $null })
    $json = $safe | ConvertTo-Json -Depth 8
    Set-Content -Path $registryPath -Value $json -Encoding UTF8
}

function Get-ProcessNumberFromRecord {
    param([object]$Record)

    if ($null -eq $Record) {
        return 0
    }

    if ($Record.PSObject.Properties.Name -contains 'process_number') {
        return [int]$Record.process_number
    }

    if ($Record.PSObject.Properties.Name -contains 'process') {
        return [int]$Record.process
    }

    if ($Record.PSObject.Properties.Name -contains 'process_id') {
        return [int]$Record.PSObject.Properties['process_id'].Value
    }

    if ($Record.PSObject.Properties.Name -contains 'pid') {
        return [int]$Record.PSObject.Properties['pid'].Value
    }

    return 0
}

function Test-ProcessAlive {
    param([int]$ProcessNumber)

    if ($ProcessNumber -le 0) {
        return $false
    }

    try {
        $null = Get-Process -Id $ProcessNumber -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Find-PythonProcessByNeedle {
    param([string]$Needle)

    if ([string]::IsNullOrWhiteSpace($Needle)) {
        return @()
    }

    $procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue
    if (-not $procs) {
        return @()
    }

    return @($procs | Where-Object { ($_.CommandLine -as [string]) -like "*$Needle*" })
}

function Stop-PythonProcessesByNeedle {
    param(
        [string]$Needle,
        [string]$ServiceName = '',
        [int]$ExcludeProcessNumber = 0
    )

    if ([string]::IsNullOrWhiteSpace($Needle)) {
        return
    }

    $matches = @(Find-PythonProcessByNeedle -Needle $Needle | Sort-Object ProcessId -Unique)
    foreach ($match in $matches) {
        $matchNumber = [int]$match.ProcessId
        if ($ExcludeProcessNumber -gt 0 -and $matchNumber -eq $ExcludeProcessNumber) {
            continue
        }

        Stop-Process -Id $matchNumber -Force -ErrorAction SilentlyContinue

        if ([string]::IsNullOrWhiteSpace($ServiceName)) {
            Write-Host "[STOP] matched process $matchNumber"
        } else {
            Write-Host "[STOP] $ServiceName process $matchNumber"
        }
    }
}

function Get-ServicePlan {
    param([string]$GroupName)

    $gateway = [PSCustomObject]@{
        Name = 'gateway'
        WorkDir = $codeRoot
        Arguments = @('-m', 'uvicorn', 'luma_experience_gateway:app', '--host', '127.0.0.1', '--port', '8787', '--log-level', 'warning')
        MatchNeedle = 'uvicorn luma_experience_gateway:app'
    }

    $orchestrator = [PSCustomObject]@{
        Name = 'orchestrator'
        WorkDir = Join-Path $codeRoot 'execution'
        Arguments = @('execution_orchestrator.py')
        MatchNeedle = 'execution_orchestrator.py'
    }

    $rolling = [PSCustomObject]@{
        Name = 'rolling_capital'
        WorkDir = Join-Path $codeRoot 'execution'
        Arguments = @('rolling_capital_engine_multi.py')
        MatchNeedle = 'rolling_capital_engine_multi.py'
    }

    $liveExec = [PSCustomObject]@{
        Name = 'live_executor'
        WorkDir = Join-Path $codeRoot 'execution'
        Arguments = @('live_executor.py')
        MatchNeedle = 'live_executor.py'
    }

    $symbolWatch = [PSCustomObject]@{
        Name = 'symbol_watcher'
        WorkDir = Join-Path $codeRoot 'execution'
        Arguments = @('symbol_watcher_fleet.py')
        MatchNeedle = 'symbol_watcher_fleet.py'
    }

    $refreshLoop = [PSCustomObject]@{
        Name = 'dashboard_refresh'
        WorkDir = $codeRoot
        Arguments = @('dashboard_unified_refresh.py', '--loop')
        MatchNeedle = 'dashboard_unified_refresh.py'
    }

    switch ($GroupName) {
        'dashboard' { return @($gateway) }
        'core'      { return @($gateway, $rolling, $liveExec) }
        'full'      { return @($gateway, $orchestrator, $rolling, $liveExec, $symbolWatch, $refreshLoop) }
        default     { return @($gateway, $rolling, $liveExec) }
    }
}

function Set-RegistryRecord {
    param(
        [object[]]$Records,
        [object]$Record
    )

    $next = @($Records | Where-Object { $_.name -ne $Record.name })
    $next += $Record
    return $next
}

function Start-ServiceFromPlan {
    param(
        [object]$Service,
        [object[]]$Records,
        [string]$PythonRuntime,
        [string]$PythonPath,
        [string]$GroupName,
        [switch]$ForceStart
    )

    $existing = @($Records | Where-Object { $_.name -eq $Service.Name }) | Select-Object -First 1
    $existingNumber = Get-ProcessNumberFromRecord -Record $existing

    if ($Service.Name -eq 'gateway') {
        $listenerNumber = Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty OwningProcess

        if ($listenerNumber) {
            if ($ForceStart) {
                Stop-Process -Id $listenerNumber -Force -ErrorAction SilentlyContinue
                Write-Host "[STOP] gateway listener process $listenerNumber"
            } else {
                Write-Host "[REUSE] gateway already listening on process $listenerNumber"
                $reuse = [PSCustomObject]@{
                    name = $Service.Name
                    process_number = [int]$listenerNumber
                    group_name = $GroupName
                    started_utc = Get-UtcNowIso
                    work_dir = $Service.WorkDir
                    args = ($Service.Arguments -join ' ')
                    match = $Service.MatchNeedle
                }
                return Set-RegistryRecord -Records $Records -Record $reuse
            }
        }
    }

    if ($existing -and (Test-ProcessAlive -ProcessNumber $existingNumber) -and -not $ForceStart) {
        Write-Host "[REUSE] $($Service.Name) already running on process $existingNumber"
        return $Records
    }

    if ($existing -and (Test-ProcessAlive -ProcessNumber $existingNumber) -and $ForceStart) {
        Stop-Process -Id $existingNumber -Force -ErrorAction SilentlyContinue
        Write-Host "[STOP] old $($Service.Name) process $existingNumber"
    }

    $matchedAll = @(Find-PythonProcessByNeedle -Needle $Service.MatchNeedle | Sort-Object ProcessId -Unique)
    if ($matchedAll.Count -gt 1) {
        $keepNumber = [int]$matchedAll[0].ProcessId
        Stop-PythonProcessesByNeedle -Needle $Service.MatchNeedle -ServiceName "duplicate $($Service.Name)" -ExcludeProcessNumber $keepNumber
        $matchedAll = @(Find-PythonProcessByNeedle -Needle $Service.MatchNeedle | Sort-Object ProcessId -Unique)
    }

    if ($ForceStart -and $matchedAll.Count -gt 0) {
        Stop-PythonProcessesByNeedle -Needle $Service.MatchNeedle -ServiceName "old $($Service.Name)"
        $matchedAll = @()
    }

    $matched = $null
    if ($matchedAll.Count -gt 0) {
        $matched = $matchedAll[0]
    }

    if ($matched -and -not $ForceStart) {
        Write-Host "[REUSE] $($Service.Name) matched unmanaged process $($matched.ProcessId)"
        $reuse = [PSCustomObject]@{
            name = $Service.Name
            process_number = [int]$matched.ProcessId
            group_name = $GroupName
            started_utc = Get-UtcNowIso
            work_dir = $Service.WorkDir
            args = ($Service.Arguments -join ' ')
            match = $Service.MatchNeedle
        }
        return Set-RegistryRecord -Records $Records -Record $reuse
    }

    $startParams = @{
        FilePath = $PythonRuntime
        ArgumentList = $Service.Arguments
        WorkingDirectory = $Service.WorkDir
        PassThru = $true
        WindowStyle = 'Hidden'
    }

    try {
        $startParams['Environment'] = @{ PYTHONPATH = $PythonPath }
        $proc = Start-Process @startParams
    } catch {
        $oldPythonPath = $env:PYTHONPATH
        $env:PYTHONPATH = $PythonPath
        try {
            $proc = Start-Process @startParams
        } finally {
            $env:PYTHONPATH = $oldPythonPath
        }
    }

    Write-Host "[START] $($Service.Name) process $($proc.Id)"
    $created = [PSCustomObject]@{
        name = $Service.Name
        process_number = [int]$proc.Id
        group_name = $GroupName
        started_utc = Get-UtcNowIso
        work_dir = $Service.WorkDir
        args = ($Service.Arguments -join ' ')
        match = $Service.MatchNeedle
    }

    return Set-RegistryRecord -Records $Records -Record $created
}

function Stop-ServiceRecord {
    param(
        [object]$Record,
        [switch]$ForceStop
    )

    $processNumber = Get-ProcessNumberFromRecord -Record $Record
    if (Test-ProcessAlive -ProcessNumber $processNumber) {
        Stop-Process -Id $processNumber -Force:$ForceStop -ErrorAction SilentlyContinue
        Write-Host "[STOP] $($Record.name) process $processNumber"
    } else {
        Write-Host "[STALE] $($Record.name) process $processNumber"
    }
}

$pythonRuntime = Resolve-PythonRuntime
$pythonPath = "$stackRoot;$codeRoot"
$plan = Get-ServicePlan -GroupName $StackGroup
$registry = Read-Registry

switch ($Action) {
    'start' {
        foreach ($service in $plan) {
            $registry = Start-ServiceFromPlan -Service $service -Records $registry -PythonRuntime $pythonRuntime -PythonPath $pythonPath -GroupName $StackGroup -ForceStart:$Force
        }
        Write-Registry -Records $registry
        Write-Host "[DONE] started group '$StackGroup'"
    }

    'stop' {
        $targetNames = @($plan | ForEach-Object { $_.Name })
        $toStop = if ($StackGroup -eq 'full') {
            @($registry)
        } else {
            @($registry | Where-Object { $targetNames -contains $_.name })
        }

        foreach ($record in $toStop) {
            Stop-ServiceRecord -Record $record -ForceStop:$true
        }

        foreach ($service in $plan) {
            Stop-PythonProcessesByNeedle -Needle $service.MatchNeedle -ServiceName "orphan $($service.Name)"
        }

        $alive = @($registry | Where-Object { Test-ProcessAlive -ProcessNumber (Get-ProcessNumberFromRecord -Record $_) })
        Write-Registry -Records $alive
        Write-Host "[DONE] stopped group '$StackGroup'"
    }

    'restart' {
        $targetNames = @($plan | ForEach-Object { $_.Name })
        $toStop = if ($StackGroup -eq 'full') {
            @($registry)
        } else {
            @($registry | Where-Object { $targetNames -contains $_.name })
        }

        foreach ($record in $toStop) {
            Stop-ServiceRecord -Record $record -ForceStop:$true
        }

        foreach ($service in $plan) {
            Stop-PythonProcessesByNeedle -Needle $service.MatchNeedle -ServiceName "orphan $($service.Name)"
        }

        $registry = @($registry | Where-Object { -not ($targetNames -contains $_.name) })

        foreach ($service in $plan) {
            $registry = Start-ServiceFromPlan -Service $service -Records $registry -PythonRuntime $pythonRuntime -PythonPath $pythonPath -GroupName $StackGroup -ForceStart:$true
        }

        Write-Registry -Records $registry
        Write-Host "[DONE] restarted group '$StackGroup'"
    }

    'status' {
        $clean = @($registry | Where-Object { Test-ProcessAlive -ProcessNumber (Get-ProcessNumberFromRecord -Record $_) })
        if ($clean.Count -ne $registry.Count) {
            Write-Registry -Records $clean
        }

        if (-not $clean.Count) {
            Write-Host '[STATUS] No managed stack processes are running.'
            Write-Host 'Run: .\code\ops\MANAGE_LOCAL_STACK.ps1 -Action start -StackGroup core'
            break
        }

        $display = @()
        foreach ($record in $clean) {
            $groupName = if ($record.PSObject.Properties.Name -contains 'group_name') {
                $record.group_name
            } elseif ($record.PSObject.Properties.Name -contains 'profile') {
                $record.profile
            } else {
                ''
            }

            $workDir = if ($record.PSObject.Properties.Name -contains 'work_dir') {
                $record.work_dir
            } elseif ($record.PSObject.Properties.Name -contains 'cwd') {
                $record.cwd
            } else {
                ''
            }

            $display += [PSCustomObject]@{
                name = $record.name
                process_number = Get-ProcessNumberFromRecord -Record $record
                group_name = $groupName
                started_utc = $record.started_utc
                work_dir = $workDir
            }
        }

        $display |
            Select-Object name, process_number, group_name, started_utc, work_dir |
            Sort-Object name |
            Format-Table -AutoSize

        Write-Host "[STATUS] Managed processes: $($clean.Count)"
    }
}
