import requests
import pandas as pd
import json

# Example: CoinGecko API for crypto fundamentals

def fetch_coingecko_market_data(symbol="bitcoin", vs_currency="usd", days=30):
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart"
    params = {"vs_currency": vs_currency, "days": days}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df

# Example: Free News API (cryptopanic)
def fetch_cryptopanic_news(api_key, filter="hot"):
    url = f"https://cryptopanic.com/api/v1/posts/"
    params = {"auth_token": api_key, "filter": filter}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()

# Example: Sports odds API (OddsAPI, TheOddsAPI, etc.)
def fetch_oddsapi_sports(api_key, sport="soccer_epl", region="us"):
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
    params = {"apiKey": api_key, "regions": region, "markets": "h2h,spreads,totals"}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()

# --- BINANCE ---
def fetch_binance_ohlc(symbol="BTCUSDT", interval="1d", limit=90, api_key=None, api_secret=None):
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame(data, columns=["open_time","open","high","low","close","volume","close_time","quote_asset_volume","number_of_trades","taker_buy_base","taker_buy_quote","ignore"])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close"] = df["close"].astype(float)
    df["symbol"] = symbol
    return df[["open_time","close","symbol"]].rename(columns={"open_time":"date"})

def get_all_binance_symbols():
    url = "https://api.binance.com/api/v3/exchangeInfo"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return [s['symbol'] for s in data['symbols'] if s['status'] == 'TRADING']

# --- KRAKEN ---
def fetch_kraken_ohlc(pair="XBTUSD", interval=1440, since=None, api_key=None, api_secret=None):
    url = f"https://api.kraken.com/0/public/OHLC"
    params = {"pair": pair, "interval": interval}
    if since:
        params["since"] = since
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    pair_key = list(data["result"].keys())[0]
    ohlc = data["result"][pair_key]
    df = pd.DataFrame(ohlc, columns=["time","open","high","low","close","vwap","volume","count"])
    df["date"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df["close"] = df["close"].astype(float)
    df["symbol"] = pair
    return df[["date","close","symbol"]]

def get_all_kraken_symbols():
    url = "https://api.kraken.com/0/public/AssetPairs"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    pairs = data['result']
    # Only spot pairs with USD or USDT
    return [k for k, v in pairs.items() if v.get('quote','').upper() in ('USD','USDT')]
