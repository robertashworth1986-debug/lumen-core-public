import requests
import pandas as pd
import time
from pathlib import Path

# Odds API config (replace with your key)
ODDS_API_KEY = 'YOUR_ODDS_API_KEY'
SPORT = 'soccer_epl'  # Example: English Premier League
REGIONS = 'uk'        # Regions: us, uk, eu, au
MARKETS = 'h2h,spreads,totals'
ODDS_API_URL = f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds/'

# Fetch live odds
def fetch_live_odds():
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': REGIONS,
        'markets': MARKETS,
        'oddsFormat': 'decimal',
        'dateFormat': 'iso',
    }
    resp = requests.get(ODDS_API_URL, params=params)
    if resp.status_code != 200:
        print('Failed to fetch odds:', resp.text)
        return None
    return resp.json()

# Save odds to CSV for backtest/live use
def save_odds_snapshot(odds, out_path):
    rows = []
    for event in odds:
        for bookmaker in event.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                for outcome in market.get('outcomes', []):
                    rows.append({
                        'event': event['id'],
                        'commence_time': event['commence_time'],
                        'home_team': event.get('home_team'),
                        'away_team': event.get('away_team'),
                        'bookmaker': bookmaker['key'],
                        'market': market['key'],
                        'outcome': outcome['name'],
                        'price': outcome['price'],
                    })
    df = pd.DataFrame(rows)
    df.to_csv(out_path, index=False)
    print(f'Saved odds snapshot: {out_path}')

if __name__ == '__main__':
    odds = fetch_live_odds()
    if odds:
        ts = int(time.time())
        out_path = Path(f'clean_data/oddsapi_snapshot_{ts}.csv')
        save_odds_snapshot(odds, out_path)
