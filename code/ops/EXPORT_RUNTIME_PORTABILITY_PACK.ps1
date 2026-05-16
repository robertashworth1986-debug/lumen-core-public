param(
    [string]$GlyphRoot = 'E:\GLYPH_DRIVE',
    [string]$VaultName = 'Luma_Context_Vault',
    [switch]$WhatIfOnly,
    [int]$RoboCopyThreads = 16
)

$ErrorActionPreference = 'Stop'

function Get-UtcStamp {
    return (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
}

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Normalize-Name {
    param([string]$Raw)
    $safe = ($Raw -replace '[^A-Za-z0-9._-]', '_').Trim('_')
    if ([string]::IsNullOrWhiteSpace($safe)) {
        return 'item'
    }
    return $safe.ToLowerInvariant()
}

function Get-Sha256Safe {
    param([string]$Path)
    try {
        return (Get-FileHash -Path $Path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
    }
    catch {
        return ''
    }
}

function Invoke-RoboCopyMirror {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$DestinationPath,
        [Parameter(Mandatory = $true)][string]$LogPath,
        [switch]$ListOnly,
        [int]$Threads = 16
    )

    Ensure-Directory -Path $DestinationPath

    $args = @(
        $SourcePath,
        $DestinationPath,
        '/E',
        '/Z',
        '/FFT',
        '/COPY:DAT',
        '/DCOPY:DAT',
        '/R:1',
        '/W:1',
        '/XJ',
        '/XO',
        '/NP',
        '/NFL',
        '/NDL',
        "/MT:$Threads",
        "/LOG+:$LogPath"
    )

    if ($ListOnly) {
        $args += '/L'
    }

    $prevErrorAction = $ErrorActionPreference
    $prevNativePref = $false
    $hadNativePref = $null -ne (Get-Variable -Name PSNativeCommandUseErrorActionPreference -Scope Global -ErrorAction SilentlyContinue)
    if ($hadNativePref) {
        $prevNativePref = [bool]$Global:PSNativeCommandUseErrorActionPreference
        $Global:PSNativeCommandUseErrorActionPreference = $false
    }

    $ErrorActionPreference = 'Continue'
    try {
        & robocopy @args
    }
    finally {
        $ErrorActionPreference = $prevErrorAction
        if ($hadNativePref) {
            $Global:PSNativeCommandUseErrorActionPreference = $prevNativePref
        }
    }

    $code = [int]$LASTEXITCODE
    return [PSCustomObject]@{
        robocopy_exit_code = $code
        success = ($code -lt 8)
    }
}

function Resolve-PythonExe {
    param([string]$EnvRoot)

    $candidates = @(
        (Join-Path $EnvRoot 'Scripts\python.exe'),
        (Join-Path $EnvRoot 'bin/python')
    )

    foreach ($p in $candidates) {
        if (Test-Path -LiteralPath $p) {
            return $p
        }
    }

    return $null
}

if (-not (Test-Path -LiteralPath $GlyphRoot)) {
    throw "Glyph root does not exist: $GlyphRoot"
}

$vaultRoot = Join-Path $GlyphRoot $VaultName
$runtimeRoot = Join-Path $vaultRoot 'runtime'
$opsRoot = Join-Path $vaultRoot 'ops'
$runId = Get-UtcStamp
$runDir = Join-Path $opsRoot (Join-Path 'runtime_portability_runs' $runId)
$copyLog = Join-Path $runDir 'runtime_copy_robocopy.log'
$copySummaryCsv = Join-Path $runDir 'runtime_copy_summary.csv'
$pythonSummaryJson = Join-Path $runDir 'python_environment_summary.json'
$vscodeSummaryJson = Join-Path $runDir 'vscode_environment_summary.json'
$processCsv = Join-Path $runDir 'process_snapshot.csv'
$processJson = Join-Path $runDir 'process_snapshot.json'
$summaryJson = Join-Path $runDir 'runtime_portability_summary.json'
$ledgerTxt = Join-Path $runDir 'runtime_portability_chain_of_custody.sha256.txt'
$latestJson = Join-Path $vaultRoot 'runtime_portability_latest.json'
$pythonManifestRoot = Join-Path $runDir 'python_manifests'
$vscodeManifestRoot = Join-Path $runDir 'vscode_manifests'

Ensure-Directory -Path $runDir
Ensure-Directory -Path $runtimeRoot
Ensure-Directory -Path $pythonManifestRoot
Ensure-Directory -Path $vscodeManifestRoot

$targets = @(
    [PSCustomObject]@{ name = 'python_env_venv311'; path = 'C:\LumaTrader\venv3.11' },
    [PSCustomObject]@{ name = 'python_env_workspace_dotvenv'; path = 'C:\LumaTrader\.venv' },
    [PSCustomObject]@{ name = 'python_env_stack_code_dotvenv'; path = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\.venv' },
    [PSCustomObject]@{ name = 'python_env_stack_env311'; path = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\env311' },
    [PSCustomObject]@{ name = 'vscode_extensions'; path = 'C:\Users\Novac\.vscode\extensions' },
    [PSCustomObject]@{ name = 'vscode_user_profile'; path = 'C:\Users\Novac\AppData\Roaming\Code\User' }
)

$copyRows = New-Object System.Collections.Generic.List[object]

foreach ($target in $targets) {
    $name = Normalize-Name -Raw ([string]$target.name)
    $source = [string]$target.path
    $dest = Join-Path $runtimeRoot $name
    $exists = Test-Path -LiteralPath $source

    $started = (Get-Date).ToUniversalTime().ToString('o')
    $exitCode = -1
    $ok = $false
    $message = ''

    if (-not $exists) {
        $message = 'source_missing'
    }
    else {
        $result = Invoke-RoboCopyMirror -SourcePath $source -DestinationPath $dest -LogPath $copyLog -ListOnly:$WhatIfOnly -Threads $RoboCopyThreads
        $exitCode = [int]$result.robocopy_exit_code
        $ok = [bool]$result.success
        $message = if ($ok) { 'ok' } else { 'robocopy_error' }
    }

    $ended = (Get-Date).ToUniversalTime().ToString('o')

    $copyRows.Add([PSCustomObject]@{
        target_name = $name
        source_path = $source
        source_exists = [bool]$exists
        destination_path = $dest
        started_utc = $started
        ended_utc = $ended
        robocopy_exit_code = $exitCode
        success = [bool]$ok
        message = $message
        list_only = [bool]$WhatIfOnly
    })
}

$copyRows | Export-Csv -Path $copySummaryCsv -NoTypeInformation -Encoding UTF8

$pythonEnvs = @(
    [PSCustomObject]@{ name = 'venv311'; root = 'C:\LumaTrader\venv3.11' },
    [PSCustomObject]@{ name = 'workspace_dotvenv'; root = 'C:\LumaTrader\.venv' },
    [PSCustomObject]@{ name = 'stack_code_dotvenv'; root = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\.venv' },
    [PSCustomObject]@{ name = 'stack_env311'; root = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\env311' }
)

$pythonRows = New-Object System.Collections.Generic.List[object]

foreach ($envSpec in $pythonEnvs) {
    $envName = Normalize-Name -Raw ([string]$envSpec.name)
    $envRoot = [string]$envSpec.root
    $pyExe = Resolve-PythonExe -EnvRoot $envRoot

    $pkgDir = Join-Path $pythonManifestRoot $envName
    Ensure-Directory -Path $pkgDir
    $pkgListJson = Join-Path $pkgDir 'pip_list.json'
    $freezeTxt = Join-Path $pkgDir 'pip_freeze.txt'

    $exists = Test-Path -LiteralPath $envRoot
    $pythonFound = $null -ne $pyExe

    $pyVersion = ''
    $pipVersion = ''
    $packageCount = 0
    $status = 'missing'
    $errorText = ''

    if ($exists -and $pythonFound) {
        try {
            $pyVersion = ((& $pyExe -V) 2>&1 | Out-String).Trim()
            $pipVersion = ((& $pyExe -m pip --version) 2>&1 | Out-String).Trim()

            & $pyExe -m pip list --format json | Set-Content -Path $pkgListJson -Encoding UTF8
            & $pyExe -m pip freeze | Set-Content -Path $freezeTxt -Encoding UTF8

            $pkgDataRaw = Get-Content -Path $pkgListJson -Raw
            $pkgData = @()
            if (-not [string]::IsNullOrWhiteSpace($pkgDataRaw)) {
                $pkgData = @($pkgDataRaw | ConvertFrom-Json)
            }
            $packageCount = $pkgData.Count
            $status = 'ok'
        }
        catch {
            $status = 'error'
            $errorText = $_.Exception.Message
        }
    }
    elseif ($exists -and -not $pythonFound) {
        $status = 'python_not_found'
    }

    $pythonRows.Add([PSCustomObject]@{
        environment = $envName
        env_root = $envRoot
        exists = [bool]$exists
        python_exe = if ($pythonFound) { $pyExe } else { '' }
        python_version = $pyVersion
        pip_version = $pipVersion
        package_count = [int]$packageCount
        status = $status
        error = $errorText
        pip_list_json = if (Test-Path -LiteralPath $pkgListJson) { $pkgListJson } else { '' }
        pip_freeze_txt = if (Test-Path -LiteralPath $freezeTxt) { $freezeTxt } else { '' }
    })
}

$pythonSummary = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString('o')
    environments = $pythonRows
    total_envs = $pythonRows.Count
    envs_ok = @($pythonRows | Where-Object { $_.status -eq 'ok' }).Count
}
$pythonSummary | ConvertTo-Json -Depth 12 | Set-Content -Path $pythonSummaryJson -Encoding UTF8

$vscodeRows = New-Object System.Collections.Generic.List[object]
$extRoot = 'C:\Users\Novac\.vscode\extensions'
$codeCmd = Join-Path $env:LOCALAPPDATA 'Programs\Microsoft VS Code\bin\code.cmd'
$extListTxt = Join-Path $vscodeManifestRoot 'extensions_list.txt'
$extDirCsv = Join-Path $vscodeManifestRoot 'extensions_dir_inventory.csv'

if (Test-Path -LiteralPath $extRoot) {
    $dirs = Get-ChildItem -LiteralPath $extRoot -Directory -ErrorAction SilentlyContinue
    foreach ($d in $dirs) {
        $vscodeRows.Add([PSCustomObject]@{
            extension_folder = $d.Name
            full_path = $d.FullName
            last_write_utc = $d.LastWriteTimeUtc.ToString('o')
        })
    }
    $vscodeRows | Export-Csv -Path $extDirCsv -NoTypeInformation -Encoding UTF8
}

if (Test-Path -LiteralPath $codeCmd) {
    try {
        & $codeCmd --list-extensions --show-versions | Set-Content -Path $extListTxt -Encoding UTF8
    }
    catch {
        Set-Content -Path $extListTxt -Encoding UTF8 -Value ("failed_to_list_extensions: " + $_.Exception.Message)
    }
}

$vscodeSummary = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString('o')
    extensions_root = $extRoot
    code_cmd = $codeCmd
    extensions_count = $vscodeRows.Count
    extensions_list_txt = if (Test-Path -LiteralPath $extListTxt) { $extListTxt } else { '' }
    extensions_dir_csv = if (Test-Path -LiteralPath $extDirCsv) { $extDirCsv } else { '' }
}
$vscodeSummary | ConvertTo-Json -Depth 8 | Set-Content -Path $vscodeSummaryJson -Encoding UTF8

$processRows = Get-CimInstance Win32_Process |
    Select-Object ProcessId, ParentProcessId, Name, CreationDate, ExecutablePath, CommandLine

$processRows | Export-Csv -Path $processCsv -NoTypeInformation -Encoding UTF8
$processRows | ConvertTo-Json -Depth 6 | Set-Content -Path $processJson -Encoding UTF8

$summary = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString('o')
    glyph_root = $GlyphRoot
    vault_root = $vaultRoot
    run_id = $runId
    run_dir = $runDir
    what_if_only = [bool]$WhatIfOnly
    copy_summary_csv = $copySummaryCsv
    copy_targets_total = $copyRows.Count
    copy_targets_present = @($copyRows | Where-Object { $_.source_exists }).Count
    copy_targets_success = @($copyRows | Where-Object { $_.success }).Count
    python_summary_json = $pythonSummaryJson
    vscode_summary_json = $vscodeSummaryJson
    process_snapshot_csv = $processCsv
    process_snapshot_json = $processJson
}
$summary | ConvertTo-Json -Depth 12 | Set-Content -Path $summaryJson -Encoding UTF8

$artifacts = @(
    $copySummaryCsv,
    $pythonSummaryJson,
    $vscodeSummaryJson,
    $processCsv,
    $processJson,
    $summaryJson,
    $copyLog
)

if (Test-Path -LiteralPath $extListTxt) {
    $artifacts += $extListTxt
}
if (Test-Path -LiteralPath $extDirCsv) {
    $artifacts += $extDirCsv
}

$ledgerLines = New-Object System.Collections.Generic.List[string]
$ledgerLines.Add("generated_utc=$((Get-Date).ToUniversalTime().ToString('o'))")
$ledgerLines.Add("run_dir=$runDir")

foreach ($a in $artifacts) {
    if (Test-Path -LiteralPath $a) {
        $ledgerLines.Add("artifact=$a")
        $ledgerLines.Add("sha256=$(Get-Sha256Safe -Path $a)")
    }
}

$ledgerLines | Set-Content -Path $ledgerTxt -Encoding UTF8

$latest = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString('o')
    run_id = $runId
    run_dir = $runDir
    summary_json = $summaryJson
    chain_of_custody_sha256 = $ledgerTxt
}
$latest | ConvertTo-Json -Depth 8 | Set-Content -Path $latestJson -Encoding UTF8

Write-Output "[RUNTIME_PORTABILITY] vault_root=$vaultRoot"
Write-Output "[RUNTIME_PORTABILITY] run_dir=$runDir"
Write-Output "[RUNTIME_PORTABILITY] summary_json=$summaryJson"
Write-Output "[RUNTIME_PORTABILITY] copy_summary_csv=$copySummaryCsv"
Write-Output "[RUNTIME_PORTABILITY] python_summary_json=$pythonSummaryJson"
Write-Output "[RUNTIME_PORTABILITY] vscode_summary_json=$vscodeSummaryJson"
Write-Output "[RUNTIME_PORTABILITY] process_snapshot_csv=$processCsv"
Write-Output "[RUNTIME_PORTABILITY] chain_of_custody_sha256=$ledgerTxt"
