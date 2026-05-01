import os
import ccxt

# --- CONFIG ---
KRAKEN_API_KEY = os.getenv('KRAKEN_API_KEY')
KRAKEN_API_SECRET = os.getenv('KRAKEN_API_SECRET')
BTC_DEST_ADDRESS = '1MgpVP4GLhsPLdXRNYuUzfsqDhynbXzmSF'  # Your Binance BTC deposit address
BTC_MIN_WITHDRAW = 0.0001  # Minimum BTC to withdraw (adjust as needed)

# Try loading from luma_live_keys.env if not set
if not KRAKEN_API_KEY or not KRAKEN_API_SECRET:
    env_path = os.path.join(os.path.dirname(__file__), 'execution', 'config', 'luma_live_keys.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('KRAKEN_API_KEY='):
                    KRAKEN_API_KEY = line.strip().split('=', 1)[1]
                if line.startswith('KRAKEN_API_SECRET='):
                    KRAKEN_API_SECRET = line.strip().split('=', 1)[1]

if not KRAKEN_API_KEY or not KRAKEN_API_SECRET:
    raise Exception('Kraken API keys not found in environment or luma_live_keys.env')

kraken = ccxt.kraken({
    'apiKey': KRAKEN_API_KEY,
    'secret': KRAKEN_API_SECRET,
    'enableRateLimit': True,
})

def get_btc_balance():
    balance = kraken.fetch_balance()
    btc = balance.get('BTC', {}).get('free', 0)
    print(f"BTC balance: {btc}")
    return btc

def withdraw_btc(amount, address):
    print(f"Withdrawing {amount} BTC to {address}...")
    result = kraken.withdraw('BTC', amount, address)
    print("Withdraw result:", result)
    return result

if __name__ == '__main__':
    btc = get_btc_balance()
    if btc >= BTC_MIN_WITHDRAW:
        withdraw_btc(btc, BTC_DEST_ADDRESS)
    else:
        print(f"Not enough BTC to withdraw. Minimum: {BTC_MIN_WITHDRAW}, Available: {btc}")
