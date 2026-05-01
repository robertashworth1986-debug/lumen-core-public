param(
  [Parameter(Mandatory=$true)]
  [string]$UnityProjectRoot
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $UnityProjectRoot)) {
  throw "Unity project root not found: $UnityProjectRoot"
}

$src = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\unity_bridge"
$runtimeTarget = Join-Path $UnityProjectRoot "Assets\LumaCore\Runtime"
$editorTarget = Join-Path $UnityProjectRoot "Assets\LumaCore\Editor"

New-Item -ItemType Directory -Force -Path $runtimeTarget | Out-Null
New-Item -ItemType Directory -Force -Path $editorTarget | Out-Null

Copy-Item (Join-Path $src "LumaRealtimeBridge.cs") -Destination $runtimeTarget -Force
Copy-Item (Join-Path $src "LumaVoiceGuideController.cs") -Destination $runtimeTarget -Force
Copy-Item (Join-Path $src "LumaSceneCueReceiver.cs") -Destination $runtimeTarget -Force
Copy-Item (Join-Path $src "LumaWsClientBridge.cs") -Destination $runtimeTarget -Force
Copy-Item (Join-Path $src "LumaSceneCueDriver.cs") -Destination $runtimeTarget -Force
Copy-Item (Join-Path $src "Editor\LumaExperienceAutoRigEditor.cs") -Destination $editorTarget -Force

Write-Host "Luma Unity bridge installed."
Write-Host "1) Open Unity"
Write-Host "2) Use menu: Tools > LumaCore > Build Experience Rig"
Write-Host "3) Press Play with gateway running on http://127.0.0.1:8787"
