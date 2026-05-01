
import os
import glob

# Directory containing kraken CSV files
data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'clean_data')
csv_files = glob.glob(os.path.join(data_dir, 'kraken_*_daily.csv'))

symbol_registry = {}

def csv_filename_to_symbol(filename):
    # e.g., kraken_btc_daily.csv -> BTC/USD
    base = filename.replace('kraken_', '').replace('_daily.csv', '').upper()
    return base, f'{base}/USD'

for csv_file in csv_files:
    fname = os.path.basename(csv_file)
    base, pair = csv_filename_to_symbol(fname)
    symbol_registry[base] = {'exchange': 'kraken', 'pair': pair}
    symbol_registry[pair] = {'exchange': 'kraken', 'pair': pair}

# Save registry to file
out_path = os.path.join(os.path.dirname(__file__), '..', '..', 'symbol_registry_auto.py')
with open(out_path, 'w') as out:
    out.write('SYMBOL_REGISTRY = ' + repr(symbol_registry) + '\n')

print(f'Registry generated with {len(symbol_registry)} symbols.')
