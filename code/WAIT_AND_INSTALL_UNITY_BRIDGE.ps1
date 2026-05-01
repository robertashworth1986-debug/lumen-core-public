$ErrorActionPreference = 'Stop'

param(
  [Parameter(Mandatory=$true)]
  [string]$UnityProjectRoot,
  [int]$TimeoutMinutes = 120
)

$editorRoot = "C:\Program Files\Unity\Hub\Editor"
$installer = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\unity_bridge\INSTALL_UNITY_BRIDGE.ps1"

if (-not (Test-Path $installer)) {
  throw "Bridge installer not found: $installer"
}

$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
Write-Host "[UNITY] Waiting for Unity Editor install in $editorRoot (timeout ${TimeoutMinutes}m)..."

while ((Get-Date) -lt $deadline) {
  if (Test-Path $editorRoot) {
    $editors = Get-ChildItem $editorRoot -ErrorAction SilentlyContinue
    if ($editors -and $editors.Count -gt 0) {
      Write-Host "[UNITY] Editor detected: $($editors[0].Name)"
      powershell -ExecutionPolicy Bypass -File $installer -UnityProjectRoot $UnityProjectRoot
      Write-Host "[UNITY] Bridge install complete."
      Write-Host "[UNITY] Next: Tools > LumaCore > Build Experience Rig"
      exit 0
    }
  }
  Start-Sleep -Seconds 30
}

throw "Timed out waiting for Unity Editor install."
