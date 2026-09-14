param(
    [ValidateSet('start','stop','restart','status')][string]$Action='status',
    [ValidateSet('dashboard','core','full')][string]$StackGroup='core',
    [switch]$Force,
    [switch]$Json
)
$ErrorActionPreference='Stop'
$stackRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$codeRoot=Join-Path $stackRoot 'code'
$runRoot=Join-Path $stackRoot 'run'
$registryPath=Join-Path $runRoot 'managed_runtime_processes.json'
$identitySource=Join-Path $PSScriptRoot 'RUNTIME_PROCESS_IDENTITY.cs'

function Get-UtcNowIso { [DateTime]::UtcNow.ToString('o') }
function Initialize-ProcessIdentity {
    if (-not ('LumenCore.RuntimeV2.ProcessLease' -as [type])) { Add-Type -Path $identitySource -ErrorAction Stop }
}
function Resolve-PythonRuntime {
    foreach ($candidate in @(
        (Join-Path $stackRoot '.venv\Scripts\python.exe'), (Join-Path $codeRoot '.venv\Scripts\python.exe'),
        (Join-Path $stackRoot '..\venv3.11\Scripts\python.exe'), (Join-Path $stackRoot '..\.venv\Scripts\python.exe'),
        'C:\LumaTrader\venv3.11\Scripts\python.exe','C:\LumaTrader\.venv\Scripts\python.exe'
    )) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
    throw 'Python runtime not found; start is blocked.'
}
function Get-ProcessNumberFromRecord {
    param([object]$Record)
    foreach ($name in @('process_number','process','process_id','pid')) {
        if ($null -ne $Record -and $Record.PSObject.Properties.Name -contains $name) {
            $number=0
            if ([int]::TryParse([string]$Record.$name,[ref]$number) -and $number -gt 0) { return $number }
            throw 'Invalid registry process number.'
        }
    }
    throw 'Registry record has no process number.'
}
function Read-Registry {
    if (-not (Test-Path -LiteralPath $registryPath)) { return @() }
    $item=Get-Item -LiteralPath $registryPath
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $item.Length -gt 8388608) { throw 'Registry is not a bounded regular file; control is blocked.' }
    $raw=[IO.File]::ReadAllText($registryPath)
    if ([string]::IsNullOrWhiteSpace($raw)) { throw 'Empty registry is invalid; control is blocked.' }
    # Wrapping avoids Windows PowerShell's pipeline enumeration losing null
    # array members. Each member must be validated, including null entries.
    try {
        ConvertFrom-Json -InputObject $raw -ErrorAction Stop | Out-Null
        $parsed=(ConvertFrom-Json -InputObject ('{"records":'+$raw+'}') -ErrorAction Stop).records
    }
    catch { throw 'Malformed registry; control is blocked and the file is preserved.' }
    if ($null -eq $parsed -and $raw.Trim() -ne '[]') { throw 'Null registry is invalid.' }
    $rows=@($parsed)
    $names=@{}
    foreach ($row in $rows) {
        if ($null -eq $row -or [string]::IsNullOrWhiteSpace([string]$row.name) -or $names.ContainsKey([string]$row.name)) { throw 'Invalid or duplicate registry service name.' }
        $names[[string]$row.name]=$true
        $null=Get-ProcessNumberFromRecord $row
    }
    return $rows
}
function Write-Registry {
    param([object[]]$Records)
    if (-not (Test-Path -LiteralPath $runRoot -PathType Container)) { throw 'Mutation lock must be acquired before a registry write.' }
    if ((Get-Item -LiteralPath $runRoot).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse-point runtime directory is not writable by this manager.' }
    if ((Test-Path -LiteralPath $registryPath) -and ((Get-Item -LiteralPath $registryPath).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Reparse-point registry is not writable.' }
    $body=ConvertTo-Json -InputObject @($Records) -Depth 12
    if ([Text.Encoding]::UTF8.GetByteCount($body) -gt 8388608) { throw 'Registry exceeds its size limit.' }
    $temporary=Join-Path $runRoot ('.managed_runtime_'+[Guid]::NewGuid().ToString('N')+'.tmp')
    try {
        [IO.File]::WriteAllText($temporary,$body+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
        if ([IO.File]::Exists($registryPath)) { [IO.File]::Replace($temporary,$registryPath,[NullString]::Value) }
        else { [IO.File]::Move($temporary,$registryPath) }
    } finally { if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) } }
}
function Get-ServicePlan {
    param([string]$GroupName)
    $executionRoot=Join-Path $codeRoot 'execution'
    $gateway=[pscustomobject]@{Name='gateway';WorkDir=$codeRoot;Arguments=@('-m','uvicorn','luma_experience_gateway:app','--app-dir',$codeRoot,'--host','127.0.0.1','--port','8787','--log-level','warning');MatchNeedle='luma_experience_gateway:app'}
    $orchestrator=[pscustomobject]@{Name='orchestrator';WorkDir=$executionRoot;Arguments=@((Join-Path $executionRoot 'execution_orchestrator.py'));MatchNeedle='execution_orchestrator.py'}
    $rolling=[pscustomobject]@{Name='rolling_capital';WorkDir=$executionRoot;Arguments=@((Join-Path $executionRoot 'rolling_capital_engine_multi.py'));MatchNeedle='rolling_capital_engine_multi.py'}
    $live=[pscustomobject]@{Name='live_executor';WorkDir=$executionRoot;Arguments=@((Join-Path $executionRoot 'live_executor.py'));MatchNeedle='live_executor.py'}
    $watcher=[pscustomobject]@{Name='symbol_watcher';WorkDir=$executionRoot;Arguments=@((Join-Path $executionRoot 'symbol_watcher_fleet.py'));MatchNeedle='symbol_watcher_fleet.py'}
    $refresh=[pscustomobject]@{Name='dashboard_refresh';WorkDir=$codeRoot;Arguments=@((Join-Path $codeRoot 'dashboard_unified_refresh.py'),'--loop');MatchNeedle='dashboard_unified_refresh.py'}
    switch ($GroupName) {
        'dashboard' { @($gateway) }
        'core' { @($gateway,$rolling,$live) }
        'full' { @($gateway,$orchestrator,$rolling,$live,$watcher,$refresh) }
        default { throw 'Unknown stack group.' }
    }
}
function Set-RegistryRecord {
    param([object[]]$Records,[object]$Record)
    return @($Records | Where-Object { $_.name -ne $Record.name }) + @($Record)
}
function Get-PythonProcessInventory {
    $rows=@(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -OperationTimeoutSec 5 -ErrorAction Stop)
    if ($rows.Count -gt 4096) { throw 'Process inventory exceeds its bounded size.' }
    return $rows
}
function Normalize-ProcessArgument {
    param([string]$Value)
    # Most argv entries are values, not paths. .NET Framework rejects quotes
    # even in IsPathRooted; preserve such literal arguments for exact matching.
    try { if ([IO.Path]::IsPathRooted($Value)) { return [IO.Path]::GetFullPath($Value).ToUpperInvariant() } }
    catch [ArgumentException] { return $Value }
    return $Value
}
function Test-ArgumentVector {
    param([object[]]$Actual,[object[]]$Expected)
    if ($Actual.Count -ne $Expected.Count) { return $false }
    for ($index=0;$index -lt $Actual.Count;$index++) {
        if (-not [string]::Equals((Normalize-ProcessArgument ([string]$Actual[$index])),(Normalize-ProcessArgument ([string]$Expected[$index])),[StringComparison]::Ordinal)) { return $false }
    }
    return $true
}
function Get-RuntimeInterpreterPaths {
    param([string]$PythonRuntime)
    $paths=@([IO.Path]::GetFullPath($PythonRuntime))
    $configuration=Join-Path (Split-Path -Parent (Split-Path -Parent $PythonRuntime)) 'pyvenv.cfg'
    if (Test-Path -LiteralPath $configuration -PathType Leaf) {
        if ((Get-Item -LiteralPath $configuration).Length -gt 65536) { throw 'Oversized venv configuration.' }
        foreach ($line in [IO.File]::ReadAllLines($configuration)) {
            if ($line -match '^home\s*=\s*(.+)$') { $paths+= [IO.Path]::GetFullPath((Join-Path $Matches[1].Trim() 'python.exe')) }
        }
    }
    return @($paths | Select-Object -Unique)
}
function Test-ObservedServiceCommand {
    param([object]$ProcessRow,[object]$Service,[string[]]$Interpreters)
    if ([string]::IsNullOrWhiteSpace([string]$ProcessRow.CommandLine) -or [string]::IsNullOrWhiteSpace([string]$ProcessRow.ExecutablePath)) { throw 'Python process command is unreadable; start is blocked.' }
    $arguments=@([LumenCore.RuntimeV2.ProcessLease]::ParseCommand([string]$ProcessRow.CommandLine))
    $image=Normalize-ProcessArgument ([string]$ProcessRow.ExecutablePath)
    $allowed=@($Interpreters | ForEach-Object { Normalize-ProcessArgument $_ })
    if ($arguments.Count -lt 1 -or $allowed -notcontains $image -or $allowed -notcontains (Normalize-ProcessArgument $arguments[0])) { return $false }
    return Test-ArgumentVector @($arguments | Select-Object -Skip 1) @($Service.Arguments)
}
function Find-PythonProcessByNeedle {
    param([string]$Needle)
    throw 'Substring process adoption is retired; use exact service observations.'
}
function Stop-PythonProcessesByNeedle {
    param([string]$Needle,[string]$ServiceName='',[int]$ExcludeProcessNumber=0)
    throw 'Substring process termination is retired; stop requires a registered process identity.'
}
function Get-ProcessLeaseOrAbsent {
    param([int]$ProcessNumber,[bool]$AllowStop=$false)
    Initialize-ProcessIdentity
    try { return [LumenCore.RuntimeV2.ProcessLease]::new($ProcessNumber,$AllowStop) }
    catch {
        $reason=$_.Exception
        while ($null -ne $reason.InnerException) { $reason=$reason.InnerException }
        if ($reason -is [ComponentModel.Win32Exception] -and $reason.NativeErrorCode -eq 87) { return $null }
        throw
    }
}
function Get-RecordObservation {
    param([object]$Record)
    $leases=@()
    try {
        if ($Record.schema -ne 'lumencore.managed_runtime_process.v2' -or $Record.ownership -ne 'launched_by_manager') {
            $lease=Get-ProcessLeaseOrAbsent (Get-ProcessNumberFromRecord $Record)
            if ($null -eq $lease) { return 'ABSENT' }
            $leases+= $lease
            if (-not $lease.Alive) { return 'ABSENT' }
            return 'LEGACY_UNVERIFIED'
        }
        if ($Record.capture_complete -isnot [bool] -or -not $Record.capture_complete) { return 'CAPTURE_INCOMPLETE' }
        if (@($Record.members).Count -lt 1 -or @($Record.members).Count -gt 2) { return 'UNKNOWN' }
        $alive=0
        foreach ($member in @($Record.members)) {
            $lease=Get-ProcessLeaseOrAbsent ([int]$member.process_number)
            if ($null -eq $lease) { continue }
            $leases+= $lease
            if (-not $lease.Matches([UInt64]$member.creation_filetime,[string]$member.image_path)) { return 'IDENTITY_CHANGED' }
            if ($lease.Alive) { $alive++ }
        }
        if ($alive -eq 0) { return 'ABSENT' }
        return 'REGISTERED_PROCESSES_PRESENT'
    } catch { return 'UNKNOWN' }
    finally { foreach ($lease in $leases) { $lease.Dispose() } }
}
function New-MemberRecord {
    param([object]$Lease,[string]$Role)
    [pscustomobject]@{process_number=$Lease.ProcessNumber;creation_filetime=$Lease.CreationFileTime.ToString([Globalization.CultureInfo]::InvariantCulture);image_path=$Lease.ImagePath;role=$Role}
}
function Stop-ServiceRecord {
    param([object]$Record,[switch]$ForceStop)
    if ($Record.schema -ne 'lumencore.managed_runtime_process.v2' -or $Record.ownership -ne 'launched_by_manager') { throw 'Legacy or observed registry records have no stop authority.' }
    if ($Record.capture_complete -isnot [bool] -or -not $Record.capture_complete) { throw 'Incomplete launch capture requires review; no complete stop receipt can be issued.' }
    $service=@(Get-ServicePlan 'full' | Where-Object { $_.Name -eq $Record.name })
    if ($service.Count -ne 1 -or -not (Test-ArgumentVector @($Record.argument_vector) @($service[0].Arguments)) -or
        (Normalize-ProcessArgument $Record.work_dir) -ne (Normalize-ProcessArgument $service[0].WorkDir)) { throw 'Registry service contract changed; stop is blocked.' }
    $members=@($Record.members)
    if ($members.Count -lt 1 -or $members.Count -gt 2 -or @($members | Select-Object -ExpandProperty process_number -Unique).Count -ne $members.Count) { throw 'Invalid registered process members.' }
    $direct=@($members | Where-Object { $_.role -eq 'direct_launch' })
    $redirected=@($members | Where-Object { $_.role -eq 'venv_redirector_child' })
    if ($direct.Count -ne 1 -or $direct[0].process_number -ne (Get-ProcessNumberFromRecord $Record) -or $redirected.Count -ne ($members.Count-1)) { throw 'Invalid registered process roles.' }
    $interpreters=@(Get-RuntimeInterpreterPaths $Record.python_runtime | ForEach-Object { Normalize-ProcessArgument $_ })
    if ((Normalize-ProcessArgument $direct[0].image_path) -ne (Normalize-ProcessArgument $Record.python_runtime)) { throw 'Direct process image does not match its launch runtime.' }
    $leases=@()
    try {
        foreach ($member in $members) {
            if ([string]$member.creation_filetime -notmatch '^[1-9][0-9]*$' -or [string]::IsNullOrWhiteSpace($member.image_path)) { throw 'Missing process identity; stop is blocked.' }
            if ($interpreters -notcontains (Normalize-ProcessArgument $member.image_path)) { throw 'Registered image is outside the launch interpreter paths.' }
            $lease=Get-ProcessLeaseOrAbsent ([int]$member.process_number) $true
            if ($null -eq $lease) { continue }
            $leases+= [pscustomobject]@{lease=$lease;member=$member}
            if (-not $lease.Matches([UInt64]$member.creation_filetime,[string]$member.image_path)) { throw 'Process identity changed; no registered member was stopped.' }
        }
        [array]::Reverse($leases)
        foreach ($entry in $leases) { $entry.lease.StopVerified([UInt64]$entry.member.creation_filetime,[string]$entry.member.image_path) }
        Write-Host "[STOP] $($Record.name): registered process exits verified; unrecorded descendants are outside this receipt."
    } finally { foreach ($entry in $leases) { $entry.lease.Dispose() } }
}
function Start-ServiceFromPlan {
    param([object]$Service,[object[]]$Records,[string]$PythonRuntime,[string]$PythonPath,[string]$GroupName,[switch]$ForceStart)
    Initialize-ProcessIdentity
    $existing=@($Records | Where-Object { $_.name -eq $Service.Name }) | Select-Object -First 1
    if ($null -ne $existing) {
        $observation=Get-RecordObservation $existing
        if ($observation -eq 'REGISTERED_PROCESSES_PRESENT') {
            if (-not $ForceStart) { Write-Host "[REUSE] $($Service.Name): registered process identities present; application health unverified."; return $Records }
            Stop-ServiceRecord $existing -ForceStop
        } elseif ($observation -ne 'ABSENT') { throw "Existing $($Service.Name) record is $observation; launch is blocked." }
    }
    $interpreters=@(Get-RuntimeInterpreterPaths $PythonRuntime)
    foreach ($row in @(Get-PythonProcessInventory)) {
        $exact=Test-ObservedServiceCommand $row $Service $interpreters
        if ($exact -or ([string]$row.CommandLine).IndexOf([string]$Service.MatchNeedle,[StringComparison]::OrdinalIgnoreCase) -ge 0) { throw "An unregistered or legacy $($Service.Name) process was observed; it is not adopted or stopped." }
    }
    if ($Service.Name -eq 'gateway') {
        $listeners=@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object { $_.LocalPort -eq 8787 })
        if ($listeners.Count -gt 0) { throw 'Port8787 is already occupied; this manager does not clear shared ports.' }
    }
    $startInfo=[Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName=$PythonRuntime
    $startInfo.Arguments=(@($Service.Arguments | ForEach-Object { [LumenCore.RuntimeV2.ProcessLease]::QuoteArgument([string]$_) }) -join ' ')
    $startInfo.WorkingDirectory=$Service.WorkDir
    $startInfo.UseShellExecute=$false
    $startInfo.CreateNoWindow=$true
    $startInfo.EnvironmentVariables['PYTHONPATH']=$PythonPath
    # Confirm the registry can be written before launching. Process creation and
    # filesystem publication are not a transaction; post-launch failures HOLD.
    Write-Registry $Records
    $process=[Diagnostics.Process]::Start($startInfo)
    $rootLease=$null
    try {
        $rootLease=[LumenCore.RuntimeV2.ProcessLease]::FromStartedProcess($process)
        if ($null -eq $rootLease -or -not $rootLease.Alive) { throw 'Launched process exited before identity capture.' }
        $record=[pscustomobject]@{
            schema='lumencore.managed_runtime_process.v2';name=$Service.Name;process_number=$process.Id;
            ownership='launched_by_manager';launch_id=[Guid]::NewGuid().ToString();group_name=$GroupName;
            started_utc=Get-UtcNowIso;work_dir=$Service.WorkDir;python_runtime=$PythonRuntime;
            args=$startInfo.Arguments;argument_vector=@($Service.Arguments);match=$Service.MatchNeedle;
            members=@(New-MemberRecord $rootLease 'direct_launch');application_health_verified=$false;
            capture_complete=($interpreters.Count -eq 1)
        }
        $Records=Set-RegistryRecord $Records $record
        Write-Registry $Records
        if ($interpreters.Count -gt 1) {
            $timer=[Diagnostics.Stopwatch]::StartNew(); $found=$false
            while ($timer.Elapsed.TotalSeconds -lt 5 -and -not $found) {
                $children=@(Get-PythonProcessInventory | Where-Object { $_.ParentProcessId -eq $process.Id })
                foreach ($child in $children) {
                    if (-not (Test-ObservedServiceCommand $child $Service $interpreters)) { throw 'Unrecognized redirector child; launch record retained for review.' }
                    $childLease=Get-ProcessLeaseOrAbsent ([int]$child.ProcessId)
                    try {
                        if ($null -eq $childLease -or -not $childLease.Alive -or $childLease.CreationFileTime -lt $rootLease.CreationFileTime -or -not $rootLease.Alive) { throw 'Redirector child identity is uncertain.' }
                        # CIM timestamps have microsecond precision. Bind the
                        # observed command/parent to the opened process instance;
                        # a newer process reusing its PID cannot inherit the row.
                        if ($child.CreationDate -isnot [DateTime]) { throw 'Redirector child birth time is unreadable.' }
                        $birthDelta=[decimal]$childLease.CreationFileTime-[decimal]$child.CreationDate.ToFileTimeUtc()
                        if ($birthDelta -lt 0 -or $birthDelta -gt 9 -or
                            (Normalize-ProcessArgument $childLease.ImagePath) -ne (Normalize-ProcessArgument $child.ExecutablePath)) { throw 'Redirector child observation changed before identity capture.' }
                        if ($found) { throw 'Multiple redirector children are ambiguous.' }
                        $record.members+= New-MemberRecord $childLease 'venv_redirector_child'; $found=$true
                    } finally { if ($null -ne $childLease) { $childLease.Dispose() } }
                }
                if (-not $found) { Start-Sleep -Milliseconds 100 }
            }
            if (-not $found) { throw 'Venv child was not identified; initial launch record retained and no second launch attempted.' }
            $record.capture_complete=$true
            Write-Registry (Set-RegistryRecord $Records $record)
        }
        Write-Host "[START] $($Service.Name): registered process identity captured; application health unverified."
        return Set-RegistryRecord $Records $record
    } finally {
        if ($null -ne $rootLease) { $rootLease.Dispose() }
        $process.Dispose()
    }
}
function Invoke-RuntimeManager {
    $registry=@(Read-Registry)
    if ($Action -eq 'status') {
        $observations=@(foreach ($record in $registry) {
            [pscustomobject]@{name=$record.name;process_number=(Get-ProcessNumberFromRecord $record);observation=(Get-RecordObservation $record);ownership=$record.ownership;application_health_verified=$false}
        })
        if ($Json) { ConvertTo-Json -InputObject @($observations) -Depth 5 }
        elseif ($observations.Count) { $observations | Format-Table -AutoSize }
        else { Write-Host '[STATUS] No process records. Unregistered processes and application health have not been established.' }
        return
    }
    if (-not (Test-Path -LiteralPath $runRoot)) { New-Item -ItemType Directory -Path $runRoot | Out-Null }
    if ((Get-Item -LiteralPath $runRoot).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse-point runtime directory is not supported.' }
    $lock=$null
    try {
        $lockPath=Join-Path $runRoot 'runtime_manager.lock'
        if ((Test-Path -LiteralPath $lockPath) -and ((Get-Item -LiteralPath $lockPath).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Reparse-point manager lock is not supported.' }
        $lock=[IO.File]::Open($lockPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
        $registry=@(Read-Registry); $plan=@(Get-ServicePlan $StackGroup); $failed=0
        foreach ($service in $plan) {
            try {
                $registry=@(Read-Registry)
                $record=@($registry | Where-Object { $_.name -eq $service.Name }) | Select-Object -First 1
                if ($Action -in @('stop','restart') -and $null -ne $record) {
                    Stop-ServiceRecord $record -ForceStop
                    $registry=@($registry | Where-Object { $_.name -ne $service.Name }); Write-Registry $registry
                }
                if ($Action -in @('start','restart')) {
                    $pythonRuntime=Resolve-PythonRuntime
                    $registry=@(Start-ServiceFromPlan $service $registry $pythonRuntime "$stackRoot;$codeRoot" $StackGroup -ForceStart:$Force)
                }
            } catch { $failed++; Write-Host "[HOLD] $($service.Name): $($_.Exception.Message)" }
        }
        if ($failed -gt 0) { throw "$failed service action(s) held or failed; no success receipt is implied." }
        Write-Host "[DONE] $Action group '$StackGroup': registered identities only; application health unverified."
    } finally { if ($null -ne $lock) { $lock.Dispose() } }
}
Invoke-RuntimeManager
