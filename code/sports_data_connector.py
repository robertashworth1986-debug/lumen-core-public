import glob
import json
import os
import pandas as pd

def load_all_sports_odds(path=None):
    """
    Loads all *_live_odds.json files in the given directory into a dictionary of DataFrames.
    """
    if path is None:
        path = os.path.join(os.path.dirname(__file__), '../sports_data')
    files = glob.glob(os.path.join(path, '*_live_odds.json'))
    odds = {}
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as infile:
                data = json.load(infile)
                odds[os.path.basename(f)] = pd.DataFrame(data)
        except Exception as e:
            print(f'Error loading {f}: {e}')
    return odds

def load_sports_registry(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(__file__), '../sports_data/sports_registry.json')
    with open(path, 'r', encoding='utf-8') as infile:
        return json.load(infile)

def load_sports_list(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(__file__), '../sports_data/sports_list.json')
    with open(path, 'r', encoding='utf-8') as infile:
        return json.load(infile)
