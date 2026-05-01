import os
import json
from glob import glob
from datetime import datetime

ODDS_DIR = os.path.join(os.path.dirname(__file__), '..', 'sports_data')
OUTPUT_FILE = os.path.join(ODDS_DIR, 'sports_signals.json')

# Simple edge detection: highlight bets where implied probability < 1/odds (value bet)

def implied_prob(odds):
    try:
        return 1.0 / float(odds) if float(odds) > 0 else 0.0
    except Exception:
        return 0.0

def best_arbitrage(event):
    """Find arbitrage opportunities across bookmakers for the same market/outcome."""
    arbs = []
    market_outcomes = {}
    for bookmaker in event.get('bookmakers', []):
        for market in bookmaker.get('markets', []):
            for outcome in market.get('outcomes', []):
                key = (market.get('key'), outcome.get('name'))
                if key not in market_outcomes:
                    market_outcomes[key] = []
                market_outcomes[key].append((bookmaker.get('title'), outcome.get('price')))
    for (market_key, outcome_name), offers in market_outcomes.items():
        if len(offers) > 1:
            best = max(offers, key=lambda x: float(x[1]))
            worst = min(offers, key=lambda x: float(x[1]))
            edge = float(best[1]) - float(worst[1])
            if edge > 0.1:  # Arbitrary threshold for actionable arb
                arbs.append({
                    'market': market_key,
                    'outcome': outcome_name,
                    'best_bookmaker': best[0],
                    'best_odds': best[1],
                    'worst_bookmaker': worst[0],
                    'worst_odds': worst[1],
                    'arb_edge': round(edge, 4)
                })
    return arbs


def find_advanced_edges():
    signals = []
    for odds_file in glob(os.path.join(ODDS_DIR, '*_live_odds.json')):
        with open(odds_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception:
                continue
        for event in data if isinstance(data, list) else []:
            event_id = event.get('id')
            commence = event.get('commence_time')
            sport = event.get('sport_title')
            teams = event.get('teams')
            # Arbitrage detection
            arbs = best_arbitrage(event)
            for arb in arbs:
                signals.append({
                    'event_id': event_id,
                    'sport': sport,
                    'teams': teams,
                    'type': 'arbitrage',
                    'edge_score': arb['arb_edge'],
                    'details': arb,
                    'commence': commence
                })
            # Value bets and line movement (if previous odds available)
            for bookmaker in event.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    market_key = market.get('key')
                    for outcome in market.get('outcomes', []):
                        odds = outcome.get('price')
                        name = outcome.get('name')
                        prob = implied_prob(odds)
                        # Value bet: implied prob < 0.5 (arbitrary threshold, tune as needed)
                        if prob > 0 and prob < 0.5:
                            signals.append({
                                'event_id': event_id,
                                'sport': sport,
                                'teams': teams,
                                'type': 'value_bet',
                                'market': market_key,
                                'outcome': name,
                                'odds': odds,
                                'implied_prob': round(prob, 4),
                                'commence': commence,
                                'bookmaker': bookmaker.get('title'),
                                'edge_score': round(1.0 - prob, 4)
                            })
    # Sort by best edge (highest edge_score)
    signals.sort(key=lambda x: -x.get('edge_score', 0))
    return signals


def main():
    signals = find_advanced_edges()
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({'generated_utc': datetime.utcnow().isoformat(), 'signals': signals}, f, indent=2)
    print(f"[sports_signals] {len(signals)} advanced edges found. Output: {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
