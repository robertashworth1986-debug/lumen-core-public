# PowerShell: Create, save, and run a Kraken Futures API test script with single-paste block input

$scriptPath = "dashboard\kraken_futures_save_singleline.ps1"

$scriptContent = @'
# PowerShell: Prompt for Kraken API keys, auto-strip line breaks, save as single line, and test Futures API

$envFile = "config/luma_live_keys.env"

function Get-SingleLineInput($prompt) {
    Write-Host "$prompt (paste your key/secret as a single block, then press Enter):"
    $input = Read-Host
    # Remove all line breaks and spaces
    return ($input -replace "[\r\n]", "") -replace " ", ""
}

$newApiKey = Get-SingleLineInput "Paste your NEW KRAKEN_API_KEY"
$newApiSecret = Get-SingleLineInput "Paste your NEW KRAKEN_API_SECRET"

# Write/update env file as a single block
$envLines = @()
if (Test-Path $envFile) {
    $lines = Get-Content $envFile
    $foundKey = $false
    $foundSecret = $false
    foreach ($line in $lines) {
        if ($line -match "^KRAKEN_API_KEY=") {
            $envLines += "KRAKEN_API_KEY=$newApiKey"
            $foundKey = $true
        } elseif ($line -match "^KRAKEN_API_SECRET=") {
            $envLines += "KRAKEN_API_SECRET=$newApiSecret"
            $foundSecret = $true
        } else {
            $envLines += $line
        }
    }
    if (-not $foundKey) { $envLines += "KRAKEN_API_KEY=$newApiKey" }
    if (-not $foundSecret) { $envLines += "KRAKEN_API_SECRET=$newApiSecret" }
} else {
    $envLines = @("KRAKEN_API_KEY=$newApiKey", "KRAKEN_API_SECRET=$newApiSecret")
}
$envLines | Set-Content $envFile

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
'@

# Ensure dashboard directory exists
if (!(Test-Path "dashboard")) { New-Item -ItemType Directory -Path "dashboard" | Out-Null }

# Write the script file
Set-Content -Path $scriptPath -Value $scriptContent

# Run the script
& $scriptPath
