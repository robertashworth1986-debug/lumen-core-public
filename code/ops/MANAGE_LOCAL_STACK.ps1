param(
    [ValidateSet('start', 'stop', 'restart', 'status')]
    [string]$Action = 'status',

    [ValidateSet('dashboard', 'core', 'full')]
    [string]$StackGroup = 'core',

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$manager = Join-Path $PSScriptRoot 'STACK_RUNTIME_MANAGER.ps1'
if (-not (Test-Path $manager)) {
    throw "Runtime manager not found at $manager"
}

& $manager -Action $Action -StackGroup $StackGroup -Force:$Force
