param(
	[ValidateSet('dashboard', 'core', 'full')]
	[string]$StackGroup = 'full',

	[switch]$ForceAllPython
)

$ErrorActionPreference = 'Stop'

$manager = Join-Path $PSScriptRoot 'code\ops\MANAGE_LOCAL_STACK.ps1'
if (-not (Test-Path $manager)) {
	throw "Runtime manager not found at $manager"
}

& $manager -Action stop -StackGroup $StackGroup -Force

if ($ForceAllPython) {
	Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
	Write-Host '[EMERGENCY] Forced stop on all python.exe processes.'
}
