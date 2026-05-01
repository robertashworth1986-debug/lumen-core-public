import pandas as pd
from pathlib import Path
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../code')))
from validation_proof_pack import walk_forward_validation, generate_proof_pack

def dummy_strategy(train_df):
    # Example: always long
    return [1.0] * len(train_df)

def main():
    # Example: use a recent trade log or price data
    data_path = Path('out/execution/trade_log.json')
    if not data_path.exists():
        print('No trade log found.')
        return
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    # Synthesize 'close' price from exit_price or entry_price
    if 'close' not in df.columns:
        if 'exit_price' in df.columns:
            df['close'] = df['exit_price']
        elif 'entry_price' in df.columns:
            df['close'] = df['entry_price']
        else:
            print('No close, exit_price, or entry_price in data.')
            return
    # Run walk-forward validation
    results = walk_forward_validation(df, dummy_strategy, window=50, step=10)
    # Save proof pack
    out_path = 'dashboard/proof_live'
    json_path, hash_path = generate_proof_pack(results.to_dict(orient='records'), out_path)
    print(f'Validation proof pack saved: {json_path}, hash: {hash_path}')

if __name__ == '__main__':
    main()
