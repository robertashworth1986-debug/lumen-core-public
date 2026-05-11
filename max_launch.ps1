$# === 1. SPORTS ODDS API SETUP ===
Start-Process 'https://the-odds-api.com/'
\ = Read-Host 'Paste your new SPORTS ODDS API KEY'
'SPORTS_ODDS_API_KEY=' + \ | Set-Content -Path '.env.sports' -Encoding UTF8
Write-Host 'Saved SPORTS_ODDS_API_KEY to .env.sports'

# === 2. ACTIVATE PYTHON VIRTUAL ENVIRONMENT ===
& '.venv\Scripts\Activate.ps1'
Write-Host 'Python virtual environment activated.'

# === 3. INSTALL/UPGRADE MAX PERFORMANCE PACKAGES ===
\ = @(
    'numpy', 'pandas', 'scipy', 'scikit-learn', 'ta', 'yfinance', 'ccxt', 'alpaca-trade-api',
    'requests', 'aiohttp', 'joblib', 'matplotlib', 'seaborn', 'statsmodels', 'tqdm',
    'pyarrow', 'tables', 'numba', 'bottleneck', 'lightgbm', 'xgboost', 'catboost',
    'tensorflow', 'torch', 'finplot', 'plotly', 'pytz', 'python-dotenv'
)
pip install --upgrade pip
pip install --upgrade \

# === 4. LAUNCH PROTONVPN FOR PRIVACY ===
Start-Process 'ProtonVPN'

# === 5. DOWNLOAD LATEST SPORTS DATA ===
\ = (Get-Content '.env.sports' | Select-String -Pattern 'SPORTS_ODDS_API_KEY=' | ForEach-Object { \ -replace 'SPORTS_ODDS_API_KEY=', '' })
Invoke-RestMethod -Uri \"https://api.the-odds-api.com/v4/sports/?apiKey=\\" -OutFile 'sports_list.json'

# === 6. DOWNLOAD LATEST ALPACA ASSET LIST ===
\ = \
\ = \
\ = @{
    'APCA-API-KEY-ID' = \
    'APCA-API-SECRET-KEY' = \
}
Invoke-RestMethod -Uri 'https://api.alpaca.markets/v2/assets' -Headers \ -OutFile 'alpaca_assets.json'

# === 7. LAUNCH YOUR ORCHESTRATOR ===
python code/execution/execution_orchestrator.py

Write-Host 'MAX PERFORMANCE STACK LAUNCHED. All engines go. Evolve and conquer.'
