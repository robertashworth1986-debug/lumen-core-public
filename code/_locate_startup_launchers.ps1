$ErrorActionPreference = 'SilentlyContinue'
Write-Host "APPDATA=$env:APPDATA"
Get-ChildItem -Path 'C:\Users\Novac' -Filter 'Luma_*_Autostart.cmd' -Recurse | Select-Object FullName | Format-List
