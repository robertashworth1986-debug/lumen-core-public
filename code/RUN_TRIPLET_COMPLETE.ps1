# ============================================================================
# RUN_TRIPLET_COMPLETE.ps1
# LumaTrader Institutional Stack - Complete Execution Block
# Runs: Triplet Engine + Scout + Intel + Reports
# ============================================================================

param(
    [int]$Cycles = 20,
    [int]$SeedCapital = 100000,
    [string]$Profile = "triplet"
)

Write-Host "============================================================================"
Write-Host "LumaTrader Triplet Engine - Complete Execution"
Write-Host "============================================================================"
Write-Host ""

# Setup
$ErrorActionPreference = 'Continue'
$CodeDir = $PSScriptRoot
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

Write-Host "[1/4] ENVIRONMENT SETUP"
Write-Host "-" * 80

# Activate venv
& "$CodeDir\.venv\Scripts\Activate.ps1"
Write-Host "  [OK] Environment activated"

# Clear old state
if (Test-Path "$CodeDir\out\execution\binanceus_paper_state.json") {
    Remove-Item "$CodeDir\out\execution\binanceus_paper_state.json" -Force -ErrorAction SilentlyContinue
    Write-Host "  [OK] Old state cleared"
}

Write-Host ""
Write-Host "[2/4] RUNNING TRIPLET ENGINE ($Cycles cycles)"
Write-Host "-" * 80

# Run the triplet engine
$python = & where python.exe | Select-Object -First 1
$output = & $python -c @"
import sys
sys.path.insert(0, '$CodeDir')
from multi_exchange_paper_ticker import tick
import json
import time

results = {'cycles': [], 'stats': {'buys': 0, 'sells': 0, 'holds': 0, 'engines': {'breakout': 0, 'moonshot': 0, 'fallback': 0}}}

for cycle in range(1, $Cycles + 1):
    try:
        result = tick('$python', cycle=cycle, profile='$Profile', seed_capital=$SeedCapital)
        action = result.get('action', 'HOLD')
        regime = result.get('regime', 'unknown')
        symbol = result.get('symbol', '')
        
        if action == 'BUY':
            results['stats']['buys'] += 1
            if regime in results['stats']['engines']:
                results['stats']['engines'][regime] += 1
            print(f'  [{cycle:2d}] BUY  {symbol:8} (engine: {regime})')
        elif action == 'SELL':
            results['stats']['sells'] += 1
            print(f'  [{cycle:2d}] SELL {symbol:8}')
        else:
            results['stats']['holds'] += 1
            if cycle % 5 == 0:
                print(f'  [{cycle:2d}] HOLD')
        
        time.sleep(0.1)
    except Exception as e:
        print(f'  [{cycle:2d}] ERROR: {str(e)[:60]}')

print()
print('SUMMARY:')
print(f'  BUYs:   {results["stats"]["buys"]}')
print(f'  SELLs:  {results["stats"]["sells"]}')
print(f'  HOLDs:  {results["stats"]["holds"]}')
print()
print('Per-Engine BUYs:')
for eng, count in results['stats']['engines'].items():
    print(f'  {eng:10}: {count}')
"@ 2>&1

Write-Host $output

Write-Host ""
Write-Host "[3/4] SCOUT DATA QUALITY CHECK"
Write-Host "-" * 80

$scoutCheck = & $python -c @"
import sys
sys.path.insert(0, '$CodeDir/../LamaScout')
from src.api_clients import is_real_artist_name

test_artists = [
    ('The Weeknd', True),
    ('artist-channel-123', False),
    ('SZA', True),
    ('Spotify Playlist', False),
    ('Drake', True),
]

passed = 0
for name, expected in test_artists:
    result = is_real_artist_name(name)
    status = 'PASS' if result == expected else 'FAIL'
    if status == 'PASS':
        passed += 1
    print(f'  [{status}] {name:30} -> {result}')

print()
print(f'Scout Validation: {passed}/{len(test_artists)} passed')
"@ 2>&1

Write-Host $scoutCheck

Write-Host ""
Write-Host "[4/4] FINAL STATE SNAPSHOT"
Write-Host "-" * 80

$finalState = & $python -c @"
import json
import os

state_file = '$CodeDir/out/execution/binanceus_paper_state.json'
if os.path.exists(state_file):
    with open(state_file, 'r') as f:
        state = json.load(f)
    
    print(f'  Open positions: {len(state.get(\"positions\", []))}')
    print(f'  Last action: {state.get(\"last_action\")}')
    print(f'  Triplet mode: {state.get(\"triplet\", False)}')
    print()
    print('  Sleeve Usage:')
    sleeves = state.get('capital_tank', {}).get('sleeve_notional_usd', {})
    caps = state.get('capital_tank', {}).get('sleeve_cap_usd', {})
    for eng in ['breakout', 'moonshot', 'fallback']:
        usage = sleeves.get(eng, 0)
        cap = caps.get(eng, 0)
        pct = (usage / cap * 100) if cap > 0 else 0
        print(f'    {eng:10}: \${usage:>10,.2f} / \${cap:>10,.2f} ({pct:>5.1f}%)')
    
    if len(state.get('positions', [])) > 0:
        print()
        print('  Open Positions:')
        for sym, pos in state.get('positions', {}).items():
            engine = pos.get('engine', 'unknown')
            qty = pos.get('qty', 0)
            entry = pos.get('entry', 0)
            print(f'    {sym:12} | Qty: {qty:>10.6f} | Entry: \${entry:>10.2f} | Engine: {engine}')
else:
    print('  State file not found')
"@ 2>&1

Write-Host $finalState

Write-Host ""
Write-Host "============================================================================"
Write-Host "EXECUTION COMPLETE"
Write-Host "============================================================================"
Write-Host ""
Write-Host "Files Generated:"
Write-Host "  - $CodeDir/out/execution/binanceus_paper_state.json (current state)"
Write-Host "  - $CodeDir/out/execution/binanceus_paper_ledger.jsonl (event log)"
Write-Host "  - $CodeDir/out/execution/institutional_crypto_paper_report.json (investor report)"
Write-Host ""
Write-Host "Next Step: Review investor brief at ../INVESTOR_BRIEF.md"
Write-Host ""
