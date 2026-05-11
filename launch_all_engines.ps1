param(
    [ValidateSet('dashboard', 'core', 'full')]
    [string]$StackGroup = 'full',

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$manager = Join-Path $PSScriptRoot 'code\ops\MANAGE_LOCAL_STACK.ps1'
if (-not (Test-Path $manager)) {
    throw "Runtime manager not found at $manager"
}

& $manager -Action start -StackGroup $StackGroup -Force:$Force
