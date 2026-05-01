import os
import ccxt

# Load Binance API keys from environment or .env file
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')

if not BINANCE_API_KEY or not BINANCE_API_SECRET:
    # Try loading from luma_live_keys.env
    env_path = os.path.join(os.path.dirname(__file__), 'execution', 'config', 'luma_live_keys.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('BINANCE_API_KEY='):
                    BINANCE_API_KEY = line.strip().split('=', 1)[1]
                if line.startswith('BINANCE_API_SECRET='):
                    BINANCE_API_SECRET = line.strip().split('=', 1)[1]

if not BINANCE_API_KEY or not BINANCE_API_SECRET:
    raise Exception('Binance API keys not found in environment or luma_live_keys.env')

binance = ccxt.binance({
    'apiKey': BINANCE_API_KEY,
    'secret': BINANCE_API_SECRET,
    'enableRateLimit': True,
})

asset = 'BTC'  # Change to 'USDT' if you prefer
network = 'BTC'  # Change to 'TRC20', 'ERC20', etc. for USDT

# Fetch deposit address
def get_deposit_address(asset, network=None):
    params = {'network': network} if network else {}
    address_info = binance.fetch_deposit_address(asset, params)
    print(f"Deposit address for {asset} ({network}): {address_info['address']}")
    if address_info.get('tag'):
        print(f"Tag/Memo: {address_info['tag']}")
    return address_info

if __name__ == '__main__':
    get_deposit_address(asset, network)
