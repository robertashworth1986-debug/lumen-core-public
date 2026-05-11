# PowerShell: Prompt for new Kraken API keys, update env file, set env vars, and test Futures API

$envFile = "config/luma_live_keys.env"

# Prompt for new keys
$newApiKey = Read-Host "Paste your NEW KRAKEN_API_KEY"
$newApiSecret = Read-Host "Paste your NEW KRAKEN_API_SECRET"

# Read and update env file
$envLines = @()
if (Test-Path $envFile) {
    $lines = Get-Content $envFile
    foreach ($line in $lines) {
        if ($line -match "^KRAKEN_API_KEY=") {
            $envLines += "KRAKEN_API_KEY=$newApiKey"
        } elseif ($line -match "^KRAKEN_API_SECRET=") {
            $envLines += "KRAKEN_API_SECRET=$newApiSecret"
        } else {
            $envLines += $line
        }
    }
    # Add keys if not present
    if (-not ($lines -match "^KRAKEN_API_KEY=")) { $envLines += "KRAKEN_API_KEY=$newApiKey" }
    if (-not ($lines -match "^KRAKEN_API_SECRET=")) { $envLines += "KRAKEN_API_SECRET=$newApiSecret" }
} else {
    $envLines = @("KRAKEN_API_KEY=$newApiKey", "KRAKEN_API_SECRET=$newApiSecret")
}
$envLines | Set-Content $envFile

# Set environment variables for this session
$env:KRAKEN_API_KEY = $newApiKey
$env:KRAKEN_API_SECRET = $newApiSecret

# Write and run the Python test script
$pyScript = @"
import os
import time
import base64
import hashlib
import hmac
import requests

api_key = os.environ['KRAKEN_API_KEY']
api_secret = os.environ['KRAKEN_API_SECRET']
url = 'https://futures.kraken.com/derivatives/api/v3/accounts'

epoch = str(int(time.time() * 1000))
message = epoch + '/derivatives/api/v3/accounts'
sig = hmac.new(base64.b64decode(api_secret), message.encode(), hashlib.sha256).digest()
sig_b64 = base64.b64encode(sig).decode()
headers = {
    'APIKey': api_key,
    'Authent': sig_b64,
    'Nonce': epoch
}
resp = requests.get(url, headers=headers)
if resp.status_code == 200:
    print('SUCCESS: Futures API access confirmed.')
    print('Account info:', resp.json())
else:
    print(f'ERROR: {resp.status_code} - {resp.text}')
"@

$pyFile = "test_kraken_futures_api.py"
Set-Content -Path $pyFile -Value $pyScript

Write-Host "Testing Kraken Futures API access..."
python $pyFile

Remove-Item $pyFile
