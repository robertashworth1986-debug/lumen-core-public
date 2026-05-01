# To enable full-universe scanning (all 1290+ symbols):
# 1. Ensure out/adaptive_universe.csv contains all desired symbols (one per line, header: symbol).
#    If out/adaptive_universe.csv is not present, the script falls back to clean_data/adaptive_universe.csv.
# 2. Run this script to regenerate symbol_registry_auto.py with all unique symbols from adaptive_universe.csv, all kraken_*.csv, and all av_fx_*.csv.

import csv
import requests
from pathlib import Path

root = Path(r'C:/LumaTrader/INSTITUTIONAL_STACK_V2')
clean_data = root / 'clean_data'
registry_file = root / 'symbol_registry_auto.py'


def fetch_kraken_valid_symbols():
    valid = set()
    try:
        resp = requests.get('https://api.kraken.com/0/public/AssetPairs', timeout=20)
        resp.raise_for_status()
        payload = resp.json().get('result', {}) or {}
        for pair_info in payload.values():
            wsname = str(pair_info.get('wsname', '') or '').strip().upper()
            altname = str(pair_info.get('altname', '') or '').strip().upper()
            for candidate in {wsname, altname}:
                if not candidate:
                    continue
                candidate = candidate.replace('/', '')
                valid.add(candidate)
    except Exception:
        pass
    return valid


def fetch_binance_valid_symbols():
    valid = set()
    try:
        resp = requests.get('https://api.binance.com/api/v3/exchangeInfo', timeout=20)
        resp.raise_for_status()
        payload = resp.json().get('symbols', []) or []
        for item in payload:
            symbol = str(item.get('symbol', '') or '').strip().upper()
            if symbol:
                valid.add(symbol)
    except Exception:
        pass
    return valid


valid_kraken_symbols = fetch_kraken_valid_symbols()
valid_binance_symbols = fetch_binance_valid_symbols()
valid_exchange_symbols = valid_kraken_symbols.union(valid_binance_symbols)
print(f'Found {len(valid_kraken_symbols)} Kraken valid symbols and {len(valid_binance_symbols)} Binance valid symbols')
print(f'Using {len(valid_exchange_symbols)} exchange-valid symbols for registry filtering')


def is_exchange_valid(symbol):
    if not valid_exchange_symbols:
        return True
    name = str(symbol or '').strip().upper().replace('/', '')
    return name in valid_exchange_symbols


symbols = {}

# 1. Kraken symbols
for f in clean_data.glob('kraken_*_daily.csv'):
    sym = f.stem.replace('kraken_', '').replace('_daily', '').upper()
    if is_exchange_valid(sym) or is_exchange_valid(f'{sym}USD') or is_exchange_valid(f'{sym}USDT'):
        symbols[sym] = {'exchange': 'kraken', 'pair': f'{sym}/USD'}
        symbols[f'{sym}/USD'] = {'exchange': 'kraken', 'pair': f'{sym}/USD'}

# 2. FX symbols
for f in clean_data.glob('av_fx_*.csv'):
    sym = f.stem.replace('av_fx_', '').upper()
    pair = f'{sym[:3]}/{sym[3:]}' if len(sym) == 6 else sym
    if is_exchange_valid(sym) or is_exchange_valid(pair):
        symbols[f'AV_FX_{sym}'] = {'exchange': 'kraken', 'pair': pair}

# 3. Adaptive universe
out_adaptive_file = root / 'out' / 'adaptive_universe.csv'
adaptive_file = out_adaptive_file if out_adaptive_file.exists() else clean_data / 'adaptive_universe.csv'
if adaptive_file.exists():
    with adaptive_file.open('r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sym = str(row.get('symbol', '')).strip().upper()
            if not sym or sym in symbols:
                continue
            if is_exchange_valid(sym) or is_exchange_valid(f'{sym}USD') or is_exchange_valid(f'{sym}USDT'):
                symbols[sym] = {'exchange': 'adaptive', 'pair': sym}

with registry_file.open('w', encoding='utf-8') as f:
    f.write('SYMBOL_REGISTRY = {\n')
    for k, v in symbols.items():
        f.write(f"    '{k}': {v},\n")
    f.write('}\n')

print(f"Wrote {len(symbols)} symbols to {registry_file}")
