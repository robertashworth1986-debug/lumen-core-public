with open(r'C:/LumaTrader/INSTITUTIONAL_STACK_V2/symbol_registry_auto.py', 'w', encoding='utf-8') as f:
    f.write('SYMBOL_REGISTRY = {"FORCED_TEST": 1}\n')
print("[COPILOT DIAG] rebuild_full_universe.py script started!")
# FORCE TEST ENTRY
symbols_dict['TEST_WRITE'] = {'exchange': 'test', 'pair': 'TEST/USD'}
# Diagnostics: print absolute path and cwd, try writing a test file
import os
print(f"[DIAG] registry_file absolute path: {registry_file.resolve()}")
print(f"[DIAG] current working directory: {os.getcwd()}")
try:
    with open(root / 'test_write.txt', 'w', encoding='utf-8') as tf:
        tf.write('test')
    print("[DIAG] test_write.txt written successfully")
except Exception as e:
    print(f"[DIAG] Failed to write test_write.txt: {e}")
# This script will scan all CSVs in clean_data/ for a column named 'symbol',
# collect all unique symbols, and write them to adaptive_universe.csv with the correct header.
# It will then regenerate symbol_registry_auto.py with the full set.

import csv
from pathlib import Path


root = Path(r'C:/LumaTrader/INSTITUTIONAL_STACK_V2')
clean_data = root / 'clean_data'
adaptive_file = clean_data / 'adaptive_universe.csv'
registry_file = root / 'symbol_registry_auto.py'

symbols = set()

# 1. Extract from all CSVs with a 'symbol' column
for f in clean_data.glob('*.csv'):
    try:
        with f.open('r', encoding='utf-8') as fin:
            reader = csv.DictReader(fin)
            if reader.fieldnames and 'symbol' in reader.fieldnames:
                for row in reader:
                    sym = row['symbol'].strip().upper()
                    if sym:
                        symbols.add(sym)
    except Exception:
        pass

# 2. Extract from kraken_*_daily.csv filenames
for f in clean_data.glob('kraken_*_daily.csv'):
    sym = f.stem.replace('kraken_', '').replace('_daily', '').upper()
    if sym:
        symbols.add(sym)

# 3. Extract from av_fx_*.csv filenames
for f in clean_data.glob('av_fx_*.csv'):
    sym = f.stem.replace('av_fx_', '').upper()
    if sym:
        symbols.add(f'AV_FX_{sym}')

# 4. Extract from twelvedata_*.csv filenames
for f in clean_data.glob('twelvedata_*.csv'):
    sym = f.stem.replace('twelvedata_', '').upper()
    if sym:
        symbols.add(sym)

# 5. Add any other single-symbol CSVs by filename pattern (customize as needed)
# ...

# Write adaptive_universe.csv with all unique symbols
with adaptive_file.open('w', encoding='utf-8', newline='') as fout:
    writer = csv.writer(fout)
    writer.writerow(['symbol'])
    for sym in sorted(symbols):
        writer.writerow([sym])

# Now regenerate the registry

# Ensure symbols_dict is defined before use
symbols_dict = {}
# 1. Kraken symbols
for f in clean_data.glob('kraken_*_daily.csv'):
    sym = f.stem.replace('kraken_', '').replace('_daily', '').upper()
    if sym:
        symbols_dict[sym] = {'exchange': 'kraken', 'pair': f'{sym}/USD'}
        symbols_dict[f'{sym}/USD'] = {'exchange': 'kraken', 'pair': f'{sym}/USD'}
# 2. FX symbols
for f in clean_data.glob('av_fx_*.csv'):
    sym = f.stem.replace('av_fx_', '').upper()
    if sym:
        symbols_dict[f'AV_FX_{sym}'] = {'exchange': 'kraken', 'pair': f'{sym[:3]}/{sym[3:]}' if len(sym) == 6 else sym}
# 3. Adaptive universe
for sym in symbols:
    if sym not in symbols_dict:
        symbols_dict[sym] = {'exchange': 'adaptive', 'pair': sym}

# Forced test entry to confirm file writing
symbols_dict['TEST_WRITE'] = {'exchange': 'test', 'pair': 'TEST/USD'}

# FORCE TEST ENTRY
symbols_dict['TEST_WRITE'] = {'exchange': 'test', 'pair': 'TEST/USD'}

# Ensure the registry file is truncated before writing
print(f"[INFO] symbols_dict size: {len(symbols_dict)}")
with registry_file.open('w', encoding='utf-8') as f:
    f.write('SYMBOL_REGISTRY = {\n')
    items = list(symbols_dict.items())
    for i, (k, v) in enumerate(items):
        comma = ',' if i < len(items) - 1 else ''
        f.write(f"    '{k}': {v}{comma}\n")
    f.write('}\n')
print(f"[INFO] Wrote {len(symbols_dict)} symbols to {registry_file}")
print(f"[INFO] Wrote {len(symbols)} unique symbols to {adaptive_file}")

# FINAL FORCED WRITE: Guarantee registry file is not empty
try:
    with registry_file.open('a', encoding='utf-8') as f:
        f.write('\n# FINAL FORCED BLOCK\nSYMBOL_REGISTRY["COPILOT_FINAL"] = {"exchange": "copilot", "pair": "FINAL/TEST"}\n')
    print("[COPILOT DIAG] FINAL FORCED BLOCK written to symbol_registry_auto.py")
except Exception as e:
    print(f"[COPILOT DIAG] FINAL FORCED BLOCK failed: {e}")
