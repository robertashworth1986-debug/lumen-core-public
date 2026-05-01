$ErrorActionPreference = 'Stop'
$ROOT   = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2'
$CODE   = Join-Path $ROOT 'code'
$CONFIG = Join-Path $ROOT 'config'
$REG    = Join-Path $CONFIG 'live_source_registry.json'
$SMOKE  = Join-Path $CODE 'kraken_smoke_test_stage2.py'
$PY     = 'C:\Python314\python.exe'

$json = Get-Content $REG -Raw | ConvertFrom-Json
$envNames =
    $json.sources |
    Where-Object { $_.env -and $_.status -match 'LIVE_KEY_PRESENT|LIVE_PRESENT|KEY_PRESENT|PRESENT' } |
    Select-Object -ExpandProperty env -Unique

foreach ($name in $envNames) {
    $procVal = [Environment]::GetEnvironmentVariable($name, 'Process')
    if ([string]::IsNullOrWhiteSpace($procVal)) {
        $userVal = [Environment]::GetEnvironmentVariable($name, 'User')
        $machVal = [Environment]::GetEnvironmentVariable($name, 'Machine')
        if (-not [string]::IsNullOrWhiteSpace($userVal)) {
            [Environment]::SetEnvironmentVariable($name, $userVal, 'Process')
        } elseif (-not [string]::IsNullOrWhiteSpace($machVal)) {
            [Environment]::SetEnvironmentVariable($name, $machVal, 'Process')
        }
    }
}

& $PY $SMOKE
