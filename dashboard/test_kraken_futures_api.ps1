# PowerShell script to check Kraken API key presence and test Futures API access
# Requires: Python installed, requests library, and your Kraken API key/secret in config/luma_live_keys.env

[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingWriteHost', '', Justification='No Write-Host calls in script; suppress persistent analyzer false-positive.')]
param()

$envFile = "config/luma_live_keys.env"
$apiKey = $null
$apiSecret = $null

# Read API key and secret from env file
if (Test-Path $envFile) {
    $lines = Get-Content $envFile
    foreach ($line in $lines) {
        if ($line -match "^KRAKEN_API_KEY=(.+)$") {
            $apiKey = $Matches[1].Trim()
        }
        if ($line -match "^KRAKEN_API_SECRET=(.+)$") {
            $apiSecret = $Matches[1].Trim()
        }
    }
}

if (-not $apiKey -or -not $apiSecret) {
    "KRAKEN_API_KEY or KRAKEN_API_SECRET not found in $envFile. Please add them and rerun."
    exit 1
}

# Write a quick Python script to test Kraken Futures API
$pyScript = @'
import os
import time
import base64
import hashlib
import hmac
import requests

api_key = os.environ["KRAKEN_API_KEY"]
api_secret = os.environ["KRAKEN_API_SECRET"]
url = "https://futures.kraken.com/derivatives/api/v3/accounts"

epoch = str(int(time.time() * 1000))
message = epoch + "/derivatives/api/v3/accounts"
sig = hmac.new(base64.b64decode(api_secret), message.encode(), hashlib.sha256).digest()
sig_b64 = base64.b64encode(sig).decode()
headers = {
    "APIKey": api_key,
    "Authent": sig_b64,
    "Nonce": epoch
}
resp = requests.get(url, headers=headers)
if resp.status_code == 200:
    print("SUCCESS: Futures API access confirmed.")
    print("Account info:", resp.json())
else:
    print(f"ERROR: {resp.status_code} - {resp.text}")
'@

# Save and run the Python script
$pyFile = "test_kraken_futures_api.py"
Set-Content -Path $pyFile -Value $pyScript

$env:KRAKEN_API_KEY = $apiKey
$env:KRAKEN_API_SECRET = $apiSecret

"Testing Kraken Futures API access..."
python $pyFile

Remove-Item $pyFile
