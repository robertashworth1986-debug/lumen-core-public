param(
  [string]$VpsHost = "your-vps-host",
  [string]$VpsUser = "ubuntu",
  [string]$VpsPath = "/opt/luma/live_truth",
  [string]$SshKey = "$env:USERPROFILE/.ssh/id_rsa"
)

$root = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$artifactRoot = Join-Path $root "out\live_truth_fabric"
$execHeartbeat = Join-Path $root "out\execution\live_truth_fabric_heartbeat.json"

if (!(Test-Path $artifactRoot)) {
  Write-Host "live_truth_fabric directory missing. Run live_truth_fabric_daemon.py first." -ForegroundColor Red
  exit 1
}

Write-Host "Ensuring VPS path exists..." -ForegroundColor Cyan
ssh -i $SshKey "$VpsUser@$VpsHost" "mkdir -p $VpsPath"

Write-Host "Syncing artifacts..." -ForegroundColor Cyan
scp -i $SshKey "$artifactRoot\live_truth_router.json" "$VpsUser@$VpsHost`:$VpsPath/live_truth_router.json"
scp -i $SshKey "$artifactRoot\live_truth_manifest.json" "$VpsUser@$VpsHost`:$VpsPath/live_truth_manifest.json"
if (Test-Path $execHeartbeat) {
  scp -i $SshKey $execHeartbeat "$VpsUser@$VpsHost`:$VpsPath/live_truth_fabric_heartbeat.json"
}

Write-Host "Done. Suggested VPS serve command:" -ForegroundColor Green
Write-Host "python3 -m http.server 8099 --directory $VpsPath" -ForegroundColor Gray
