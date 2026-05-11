import os, json, urllib.request, urllib.error
def probe(name, url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        r = urllib.request.urlopen(req, timeout=15)
        d = json.loads(r.read())
        s = str(d)[:240].replace("\n"," ")
        print(f"[OK ] {name}: {s}")
    except urllib.error.HTTPError as e:
        body = e.read()[:240].decode(errors="ignore").replace("\n"," ")
        print(f"[ERR] {name}: HTTP {e.code} | {body}")
    except Exception as ex:
        print(f"[ERR] {name}: {ex}")

td = os.environ.get("TWELVE_DATA_API_KEY","")
fh = os.environ.get("FINNHUB_API_KEY","")
av = os.environ.get("ALPHAVANTAGE_API_KEY","")
fr = os.environ.get("FRED_API_KEY","")
po = os.environ.get("POLYGON_API_KEY","")
ak = os.environ.get("ALPACA_API_KEY","")
asec = os.environ.get("ALPACA_API_SECRET","")

probe("POLYGON", f"https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2024-12-01/2024-12-10?apiKey={po}")
probe("TWELVE",  f"https://api.twelvedata.com/time_series?symbol=AAPL&interval=1h&outputsize=5&apikey={td}")
probe("FINNHUB", f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={fh}")
probe("ALPHA",   f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey={av}")
probe("FRED",    f"https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&file_type=json&limit=2&api_key={fr}")
probe("ALPACA-DATA", "https://data.alpaca.markets/v2/stocks/AAPL/bars/latest",
      headers={"APCA-API-KEY-ID": ak, "APCA-API-SECRET-KEY": asec})
probe("ALPACA-CRYPTO", "https://data.alpaca.markets/v1beta3/crypto/us/latest/bars?symbols=BTC%2FUSD",
      headers={"APCA-API-KEY-ID": ak, "APCA-API-SECRET-KEY": asec})
