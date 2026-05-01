import hashlib
import json
import pandas as pd
from datetime import datetime

# --- Walk-forward validation ---
def walk_forward_validation(df, strategy_func, window=250, step=50):
    results = []
    for start in range(0, len(df) - window, step):
        train = df.iloc[start:start+window]
        test = df.iloc[start+window:start+window+step]
        if len(test) == 0:
            break
        signal = strategy_func(train)
        # Apply signal to test set (simple example)
        test_result = (test['close'].pct_change().fillna(0.0) * signal[-len(test):]).sum()
        results.append({'start': train.index[0], 'end': test.index[-1], 'result': test_result})
    return pd.DataFrame(results)

# --- Hash-verifiable proof pack ---
def generate_proof_pack(obj, out_path):
    """
    Saves object as JSON and SHA256 hash for auditability.
    """
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    json_path = f"{out_path}_{ts}.json"
    hash_path = f"{out_path}_{ts}_sha256.txt"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, default=str)
    with open(json_path, 'rb') as f:
        h = hashlib.sha256(f.read()).hexdigest()
    with open(hash_path, 'w') as f:
        f.write(h)
    return json_path, hash_path
