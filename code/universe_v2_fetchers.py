"""
universe_v2_fetchers.py
================================================================
Extra federal + commercial data fetchers for master_universe_v2.
All return DataFrame with columns: period (datetime), value (float).
Each fetcher must fail-soft: raise RuntimeError on no data, never abort.

Sources wired in:
    EIA per-state generation (50 states x 5 fuels)        -> 250 max
    EIA per-state retail sales (50 states x 4 sectors)    -> 200 max
    NOAA NCEI Climate at a Glance per-state monthly temp  -> 50 max
    BLS employment / unemployment via public API+key      -> 50 max
    FRED top macro series (key currently truncated)       -> ~10 (soft-fail)
    AlphaVantage daily equity bars (top US tickers)       -> ~25
    Finnhub fallback for equities                         -> ~25
    TwelveData fallback for equities/FX                   -> ~25
    yfinance major indices/ETFs (no key)                  -> ~30
    NASA POWER monthly climate per city                   -> ~10
    USGS Water daily streamflow per gauge                 -> ~10
    BEA regional GDP                                      -> ~10
    Census population estimates                           -> ~5
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict

import pandas as pd
import requests

# These two come from the parent module at runtime; re-bound by master_v2
KEYS: dict = {}
EIA_BASE = "https://api.eia.gov/v2"


def set_keys(k: dict) -> None:
    global KEYS
    KEYS = k


def _eia_get(path: str, params: list[tuple[str, str]]) -> list[dict]:
    key = KEYS.get("EIA_API_KEY")
    if not key:
        raise RuntimeError("EIA_API_KEY missing")
    full = [("api_key", key), *params, ("offset", "0"), ("length", "5000")]
    r = requests.get(EIA_BASE + path, params=full, timeout=30)
    r.raise_for_status()
    return r.json().get("response", {}).get("data", [])


# ---------------------------------------------------------------------------
# EIA per-state generation
# ---------------------------------------------------------------------------
US_STATES_50 = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY",
]


def eia_state_generation(state: str, fueltypeid: str) -> pd.DataFrame:
    rows = _eia_get(
        "/electricity/electric-power-operational-data/data/",
        [("frequency", "monthly"),
         ("data[0]", "generation"),
         ("facets[location][]", state),
         ("facets[fueltypeid][]", fueltypeid),
         ("start", "2010-01"),
         ("sort[0][column]", "period"),
         ("sort[0][direction]", "asc")],
    )
    if not rows:
        raise RuntimeError(f"EIA gen empty: {state}/{fueltypeid}")
    df = pd.DataFrame(rows)
    df["period"] = pd.to_datetime(df["period"])
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    g = df.groupby("period", as_index=False)["generation"].sum()
    g = g.sort_values("period").rename(columns={"generation": "value"}).dropna()
    return g.reset_index(drop=True)


def eia_state_retail(state: str, sectorid: str) -> pd.DataFrame:
    rows = _eia_get(
        "/electricity/retail-sales/data/",
        [("frequency", "monthly"),
         ("data[0]", "sales"),
         ("facets[stateid][]", state),
         ("facets[sectorid][]", sectorid),
         ("start", "2010-01"),
         ("sort[0][column]", "period"),
         ("sort[0][direction]", "asc")],
    )
    if not rows:
        raise RuntimeError(f"EIA retail empty: {state}/{sectorid}")
    df = pd.DataFrame(rows)
    df["period"] = pd.to_datetime(df["period"])
    df["sales"] = pd.to_numeric(df["sales"], errors="coerce")
    g = df.groupby("period", as_index=False)["sales"].sum()
    g = g.sort_values("period").rename(columns={"sales": "value"}).dropna()
    return g.reset_index(drop=True)


# ---------------------------------------------------------------------------
# NOAA NCEI Climate at a Glance per-state (state codes 001..050)
# ---------------------------------------------------------------------------
# NOAA CAG state-area-id mapping (alphabetical, 1=AL, 50=WY -- no zero pad)
NOAA_CAG_STATE_CODE = {s: str(i + 1) for i, s in enumerate(US_STATES_50)}


def noaa_state_temperature(state_code: str) -> pd.DataFrame:
    url = (
        f"https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/"
        f"statewide/time-series/{state_code}/tavg/all/1/2000-2026.json"
    )
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    j = r.json()
    data = j.get("data", {})
    rows = []
    for k, v in data.items():
        try:
            val = float(v.get("value")) if v.get("value") not in (None, "") else None
        except Exception:
            val = None
        if val is None:
            continue
        rows.append({"period": pd.to_datetime(k, format="%Y%m"), "value": val})
    df = pd.DataFrame(rows).sort_values("period").reset_index(drop=True)
    if df.empty:
        raise RuntimeError(f"NOAA empty: state code {state_code}")
    return df


# ---------------------------------------------------------------------------
# BLS public API (registered key boosts to 500 series/day, 20yr)
# ---------------------------------------------------------------------------
BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


def bls_series(series_id: str, start_year: int = 2010, end_year: int = 2026) -> pd.DataFrame:
    payload = {
        "seriesid": [series_id],
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    key = KEYS.get("BLS_API_KEY")
    if key:
        payload["registrationkey"] = key
    r = requests.post(BLS_URL, json=payload, timeout=30)
    r.raise_for_status()
    j = r.json()
    if j.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS {series_id}: {j.get('message')}")
    series = j.get("Results", {}).get("series", [])
    if not series or not series[0].get("data"):
        raise RuntimeError(f"BLS {series_id}: empty")
    rows = []
    for d in series[0]["data"]:
        period = d.get("period", "M01")
        if not period.startswith("M") or period == "M13":
            continue
        month = int(period[1:])
        try:
            val = float(d["value"])
        except Exception:
            continue
        rows.append({"period": pd.Timestamp(int(d["year"]), month, 1), "value": val})
    df = pd.DataFrame(rows).sort_values("period").reset_index(drop=True)
    if df.empty:
        raise RuntimeError(f"BLS {series_id}: parsed empty")
    return df


# Per-state unemployment rate seasonally adjusted (LAUS). Series id pattern:
#   LASST<FIPS>0000000000003   -> unemployment rate
US_STATE_FIPS = {
    "AL":"01","AK":"02","AZ":"04","AR":"05","CA":"06","CO":"08","CT":"09",
    "DE":"10","FL":"12","GA":"13","HI":"15","ID":"16","IL":"17","IN":"18",
    "IA":"19","KS":"20","KY":"21","LA":"22","ME":"23","MD":"24","MA":"25",
    "MI":"26","MN":"27","MS":"28","MO":"29","MT":"30","NE":"31","NV":"32",
    "NH":"33","NJ":"34","NM":"35","NY":"36","NC":"37","ND":"38","OH":"39",
    "OK":"40","OR":"41","PA":"42","RI":"44","SC":"45","SD":"46","TN":"47",
    "TX":"48","UT":"49","VT":"50","VA":"51","WA":"53","WV":"54","WI":"55",
    "WY":"56",
}


def bls_state_unemployment(state: str) -> pd.DataFrame:
    fips = US_STATE_FIPS[state]
    sid = f"LASST{fips}0000000000003"
    return bls_series(sid)


# ---------------------------------------------------------------------------
# FRED (key currently truncated -> soft fail expected)
# ---------------------------------------------------------------------------
def fred_series(series_id: str) -> pd.DataFrame:
    key = KEYS.get("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY missing")
    url = "https://api.stlouisfed.org/fred/series/observations"
    r = requests.get(url, params={
        "series_id": series_id,
        "api_key": key,
        "file_type": "json",
        "observation_start": "2010-01-01",
    }, timeout=30)
    r.raise_for_status()
    j = r.json()
    obs = j.get("observations") or []
    if not obs:
        raise RuntimeError(f"FRED {series_id}: empty")
    rows = []
    for o in obs:
        v = o.get("value")
        if v in (None, "", "."):
            continue
        try:
            rows.append({"period": pd.to_datetime(o["date"]), "value": float(v)})
        except Exception:
            continue
    df = pd.DataFrame(rows).sort_values("period").reset_index(drop=True)
    if df.empty:
        raise RuntimeError(f"FRED {series_id}: parsed empty")
    return df


# ---------------------------------------------------------------------------
# AlphaVantage equities (5 calls/min on free, paid premium has no limit)
# ---------------------------------------------------------------------------
def alphavantage_monthly(symbol: str) -> pd.DataFrame:
    key = KEYS.get("ALPHAVANTAGE_API_KEY")
    if not key:
        raise RuntimeError("ALPHAVANTAGE_API_KEY missing")
    url = "https://www.alphavantage.co/query"
    r = requests.get(url, params={
        "function": "TIME_SERIES_MONTHLY",
        "symbol": symbol,
        "apikey": key,
    }, timeout=30)
    r.raise_for_status()
    j = r.json()
    data = j.get("Monthly Time Series") or {}
    if not data:
        raise RuntimeError(f"AlphaVantage {symbol}: {j.get('Note') or j.get('Information') or 'empty'}")
    rows = []
    for k, v in data.items():
        try:
            rows.append({"period": pd.to_datetime(k), "value": float(v["4. close"])})
        except Exception:
            continue
    df = pd.DataFrame(rows).sort_values("period").reset_index(drop=True)
    if len(df) < 30:
        raise RuntimeError(f"AlphaVantage {symbol}: too short")
    return df


# ---------------------------------------------------------------------------
# yfinance (no key, free)
# ---------------------------------------------------------------------------
def yfinance_monthly(symbol: str) -> pd.DataFrame:
    import yfinance as yf
    t = yf.Ticker(symbol)
    h = t.history(period="15y", interval="1mo", auto_adjust=False)
    if h is None or h.empty:
        raise RuntimeError(f"yfinance {symbol}: empty")
    df = pd.DataFrame({
        "period": pd.to_datetime(h.index).tz_localize(None),
        "value": h["Close"].astype(float).values,
    }).dropna().reset_index(drop=True)
    if len(df) < 30:
        raise RuntimeError(f"yfinance {symbol}: too short")
    return df


# ---------------------------------------------------------------------------
# NASA POWER monthly climate (free, key optional)
# ---------------------------------------------------------------------------
NASA_CITIES = {
    "NYC":     (40.7128, -74.0060),
    "LA":      (34.0522, -118.2437),
    "CHICAGO": (41.8781, -87.6298),
    "HOUSTON": (29.7604, -95.3698),
    "PHOENIX": (33.4484, -112.0740),
    "DENVER":  (39.7392, -104.9903),
    "SEATTLE": (47.6062, -122.3321),
    "MIAMI":   (25.7617, -80.1918),
    "BOSTON":  (42.3601, -71.0589),
    "ATLANTA": (33.7490, -84.3880),
}


def nasa_power_monthly_temp(city: str) -> pd.DataFrame:
    lat, lon = NASA_CITIES[city]
    url = "https://power.larc.nasa.gov/api/temporal/monthly/point"
    r = requests.get(url, params={
        "parameters": "T2M",
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": "2010",
        "end": "2025",
        "format": "JSON",
    }, timeout=60)
    r.raise_for_status()
    j = r.json()
    series = j.get("properties", {}).get("parameter", {}).get("T2M", {})
    if not series:
        raise RuntimeError(f"NASA POWER {city}: empty")
    rows = []
    for k, v in series.items():
        # key format YYYYMM or YYYY13 (annual)
        if not k.isdigit() or len(k) != 6 or k.endswith("13"):
            continue
        year, month = int(k[:4]), int(k[4:6])
        if month < 1 or month > 12:
            continue
        try:
            val = float(v)
        except Exception:
            continue
        if val <= -990:  # NASA missing
            continue
        rows.append({"period": pd.Timestamp(year, month, 1), "value": val})
    df = pd.DataFrame(rows).sort_values("period").reset_index(drop=True)
    if df.empty:
        raise RuntimeError(f"NASA POWER {city}: parsed empty")
    return df


# ---------------------------------------------------------------------------
# USGS Water daily streamflow (free, no key needed but provided)
# ---------------------------------------------------------------------------
USGS_GAUGES = {
    "MISSISSIPPI_VICKSBURG": "07289000",
    "COLORADO_LEES_FERRY":   "09380000",
    "COLUMBIA_THE_DALLES":   "14105700",
    "OHIO_LOUISVILLE":       "03294500",
    "POTOMAC_DC":            "01646500",
    "HUDSON_GREEN_ISLAND":   "01358000",
    "SACRAMENTO_FREEPORT":   "11447650",
    "RIO_GRANDE_EL_PASO":    "08364000",
    "MISSOURI_HERMANN":      "06934500",
    "TENNESSEE_CHATTANOOGA": "03568000",
}


def usgs_streamflow_monthly(gauge_id: str) -> pd.DataFrame:
    # daily values, parameter 00060 = discharge cfs
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=365 * 12)
    url = "https://waterservices.usgs.gov/nwis/dv/"
    r = requests.get(url, params={
        "format": "json",
        "sites": gauge_id,
        "startDT": start.isoformat(),
        "endDT": end.isoformat(),
        "parameterCd": "00060",
        "siteStatus": "all",
    }, timeout=60)
    r.raise_for_status()
    j = r.json()
    ts = j.get("value", {}).get("timeSeries", [])
    if not ts:
        raise RuntimeError(f"USGS {gauge_id}: empty")
    vals = ts[0].get("values", [{}])[0].get("value", [])
    rows = []
    for v in vals:
        try:
            rows.append({"period": pd.to_datetime(v["dateTime"]), "value": float(v["value"])})
        except Exception:
            continue
    if not rows:
        raise RuntimeError(f"USGS {gauge_id}: parsed empty")
    df = pd.DataFrame(rows).set_index("period").sort_index()
    # Aggregate to monthly mean
    m = df["value"].resample("MS").mean().dropna().reset_index()
    if len(m) < 30:
        raise RuntimeError(f"USGS {gauge_id}: too short")
    return m


# ---------------------------------------------------------------------------
# EIA-930 hourly grid demand per balancing authority -> daily mean
# Real-time grid data — strong diurnal + weekly + seasonal harmonics.
# Premium signal for the harmonic thesis.
# ---------------------------------------------------------------------------
EIA930_BAS = [
    "CAL",   # California ISO (CAISO)
    "ERCO",  # ERCOT (Texas)
    "PJM",   # PJM Interconnection
    "MIDA",  # MISO (Midcontinent)
    "NY",    # NYISO
    "NE",    # ISO New England
    "SWPP",  # Southwest Power Pool
    "BPAT",  # Bonneville Power Administration
    "FLA",   # Florida (FPL/FRCC region)
    "TVA",   # Tennessee Valley Authority
    "CAR",   # Carolinas (Duke)
    "NW",    # Northwest
    "SE",    # Southeast
    "TEN",   # Tennessee region
    "MIDW",  # Midwest
]


def eia930_daily_demand(ba: str) -> pd.DataFrame:
    """Hourly demand per balancing authority -> daily mean, ~3 yrs back."""
    # Use premium key if present, else fall back to standard
    key = KEYS.get("EIA_API_KEY_PREMIUM") or KEYS.get("EIA_API_KEY")
    if not key:
        raise RuntimeError("EIA key missing")
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365 * 3)
    rows: list[dict] = []
    offset = 0
    while True:
        params = [
            ("api_key", key),
            ("frequency", "daily"),
            ("data[0]", "value"),
            ("facets[respondent][]", ba),
            ("facets[type][]", "D"),  # demand
            ("start", start.strftime("%Y-%m-%d")),
            ("end", end.strftime("%Y-%m-%d")),
            ("sort[0][column]", "period"),
            ("sort[0][direction]", "asc"),
            ("offset", str(offset)),
            ("length", "5000"),
        ]
        r = requests.get(
            f"{EIA_BASE}/electricity/rto/daily-region-data/data/",
            params=params, timeout=30,
        )
        r.raise_for_status()
        page = r.json().get("response", {}).get("data", []) or []
        if not page:
            break
        rows.extend(page)
        if len(page) < 5000:
            break
        offset += 5000
    if not rows:
        raise RuntimeError(f"EIA-930 {ba}: empty")
    df = pd.DataFrame(rows)
    df["period"] = pd.to_datetime(df["period"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    g = (df.dropna(subset=["value"])
            .groupby("period", as_index=False)["value"].mean()
            .sort_values("period").reset_index(drop=True))
    if len(g) < 60:
        raise RuntimeError(f"EIA-930 {ba}: too short ({len(g)})")
    return g


# ---------------------------------------------------------------------------
# OpenAQ v3: daily PM2.5 per major city
# Diurnal + seasonal pollution harmonics.
# ---------------------------------------------------------------------------
OPENAQ_CITIES = {
    "NYC":     (40.7128,  -74.0060),
    "LA":      (34.0522, -118.2437),
    "CHICAGO": (41.8781,  -87.6298),
    "HOUSTON": (29.7604,  -95.3698),
    "PHOENIX": (33.4484, -112.0740),
    "DENVER":  (39.7392, -104.9903),
    "SEATTLE": (47.6062, -122.3321),
    "MIAMI":   (25.7617,  -80.1918),
    "BOSTON":  (42.3601,  -71.0589),
    "ATLANTA": (33.7490,  -84.3880),
}


def _openaq_headers() -> dict:
    k = KEYS.get("OPENAQ_API_KEY")
    if not k:
        raise RuntimeError("OPENAQ_API_KEY missing")
    return {"X-API-Key": k}


def openaq_pm25_daily(city: str) -> pd.DataFrame:
    """Find a PM2.5 sensor near city centroid; return daily mean ug/m3."""
    if city not in OPENAQ_CITIES:
        raise RuntimeError(f"OpenAQ unknown city {city}")
    lat, lon = OPENAQ_CITIES[city]
    headers = _openaq_headers()
    # Find locations within 25km that have a PM2.5 sensor
    r = requests.get(
        "https://api.openaq.org/v3/locations",
        params={
            "coordinates": f"{lat},{lon}",
            "radius": 25000,
            "parameters_id": 2,  # PM2.5
            "limit": 25,
        },
        headers=headers, timeout=30,
    )
    r.raise_for_status()
    locs = r.json().get("results", [])
    sensor_id = None
    for loc in locs:
        for s in loc.get("sensors", []) or []:
            p = (s.get("parameter") or {})
            if p.get("id") == 2 or p.get("name") == "pm25":
                sensor_id = s.get("id")
                break
        if sensor_id:
            break
    if sensor_id is None:
        raise RuntimeError(f"OpenAQ {city}: no pm25 sensor found")
    # Pull daily aggregates
    r2 = requests.get(
        f"https://api.openaq.org/v3/sensors/{sensor_id}/days",
        params={"limit": 1000},
        headers=headers, timeout=30,
    )
    r2.raise_for_status()
    results = r2.json().get("results", []) or []
    if not results:
        raise RuntimeError(f"OpenAQ {city} sensor {sensor_id}: no daily data")
    rows = []
    for d in results:
        period_obj = (d.get("period") or {}).get("datetimeFrom") or {}
        ts = period_obj.get("utc") if isinstance(period_obj, dict) else period_obj
        v = d.get("value")
        if ts is None or v is None:
            continue
        try:
            rows.append({"period": pd.to_datetime(ts).tz_localize(None),
                         "value": float(v)})
        except Exception:
            continue
    df = pd.DataFrame(rows).sort_values("period").reset_index(drop=True)
    if len(df) < 60:
        raise RuntimeError(f"OpenAQ {city}: too short ({len(df)})")
    return df


# ---------------------------------------------------------------------------
# CoinGecko daily prices per coin (free demo key tier)
# ---------------------------------------------------------------------------
COINGECKO_COINS = [
    "bitcoin", "ethereum", "solana", "ripple", "cardano",
    "dogecoin", "polkadot", "litecoin", "chainlink", "tron",
    "avalanche-2", "polygon-ecosystem-token", "stellar", "monero", "uniswap",
]


def coingecko_daily_price(coin_id: str) -> pd.DataFrame:
    """Daily USD close ~ 1 yr (free/demo tier limit)."""
    headers = {}
    k = KEYS.get("COINGECKO_API_KEY")
    if k:
        headers["x-cg-demo-api-key"] = k
    r = requests.get(
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
        params={"vs_currency": "usd", "days": "365", "interval": "daily"},
        headers=headers, timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"CoinGecko {coin_id}: HTTP {r.status_code}")
    j = r.json()
    prices = j.get("prices", []) or []
    if not prices:
        raise RuntimeError(f"CoinGecko {coin_id}: empty")
    rows = [{"period": pd.to_datetime(int(ts), unit="ms"), "value": float(v)}
            for ts, v in prices]
    df = pd.DataFrame(rows).sort_values("period").reset_index(drop=True)
    if len(df) < 60:
        raise RuntimeError(f"CoinGecko {coin_id}: too short ({len(df)})")
    return df


# ---------------------------------------------------------------------------
# Builder: produce the full DATASETS dict at the chosen scale
# ---------------------------------------------------------------------------
def build_extra_datasets(
    state_fuels: list[str] | None = None,
    state_retail_sectors: list[str] | None = None,
    n_states: int = 50,
    include_alphavantage: bool = True,
    include_yfinance: bool = True,
    include_nasa: bool = True,
    include_usgs: bool = True,
    include_bls: bool = True,
    include_fred: bool = True,
    include_eia930: bool = True,
    include_openaq: bool = True,
    include_coingecko: bool = True,
    av_symbols: list[str] | None = None,
    yf_symbols: list[str] | None = None,
) -> Dict[str, Callable]:
    """Build the extra-fetcher dict for v2."""
    state_fuels = state_fuels or ["ALL", "NG", "SUN", "WND", "COW", "NUC"]
    state_retail_sectors = state_retail_sectors or ["RES", "COM", "IND", "TRA"]
    states = US_STATES_50[:n_states]

    out: Dict[str, Callable] = {}

    # EIA per-state generation
    for st in states:
        for f in state_fuels:
            key = f"EIA_GEN_{st}_{f}"
            out[key] = (lambda s=st, ff=f: eia_state_generation(s, ff))

    # EIA per-state retail
    for st in states:
        for s in state_retail_sectors:
            key = f"EIA_RETAIL_{st}_{s}"
            out[key] = (lambda st_=st, sec=s: eia_state_retail(st_, sec))

    # NOAA per-state temperature
    for st in states:
        code = NOAA_CAG_STATE_CODE[st]
        out[f"NOAA_TEMP_{st}"] = (lambda c=code: noaa_state_temperature(c))

    # BLS per-state unemployment
    if include_bls:
        for st in states:
            out[f"BLS_UNEMP_{st}"] = (lambda s=st: bls_state_unemployment(s))

    # FRED top macro series
    if include_fred:
        for sid in ["INDPRO", "UNRATE", "PAYEMS", "CPIAUCSL", "DGS10", "M2SL",
                    "HOUST", "RSAFS", "PCE", "GDP",
                    # Treasury yield curve (constant maturity)
                    "DGS1MO", "DGS3MO", "DGS6MO", "DGS1", "DGS2", "DGS3",
                    "DGS5", "DGS7", "DGS20", "DGS30",
                    # Credit & recession signals
                    "BAMLH0A0HYM2", "T10Y2Y", "T10Y3M", "DFF", "FEDFUNDS",
                    "DCOILWTICO", "DCOILBRENTEU", "VIXCLS",
                    # Inflation expectations & PPI
                    "T5YIE", "T10YIE", "PPIACO", "PCEPI",
                    # Money & banking
                    "M1SL", "TOTALSL", "BUSLOANS", "TOTRESNS",
                    # Housing
                    "MORTGAGE30US", "CSUSHPISA", "PERMIT",
                    # Production / consumption
                    "TCU", "DSPIC96", "UMCSENT", "ICSA"]:
            out[f"FRED_{sid}"] = (lambda s=sid: fred_series(s))

    # AlphaVantage equities (premium key — assume paid tier; if rate-limited
    # the fetcher raises and we soft-fail per dataset)
    av_symbols = av_symbols or [
        "SPY", "QQQ", "DIA", "IWM", "XLE", "XLF", "XLK", "XLV", "XLI",
        "XLP", "XLU", "XLY", "XLB", "XLRE", "GLD", "SLV", "USO", "UNG",
        "TLT", "HYG", "EEM", "EFA", "VNQ", "VXX", "BTC-USD",
    ]
    if include_alphavantage:
        for sym in av_symbols:
            out[f"AV_{sym.replace('-','_')}"] = (lambda s=sym: alphavantage_monthly(s))

    # yfinance ETFs and indices (no key)
    yf_symbols = yf_symbols or [
        "^GSPC", "^DJI", "^IXIC", "^RUT", "^VIX", "^TNX",
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B",
        "JPM", "V", "WMT", "JNJ", "XOM", "CVX", "BTC-USD", "ETH-USD",
    ]
    if include_yfinance:
        for sym in yf_symbols:
            safe = sym.replace("^","IDX_").replace("-","_")
            out[f"YF_{safe}"] = (lambda s=sym: yfinance_monthly(s))

    # NASA POWER per city
    if include_nasa:
        for c in NASA_CITIES:
            out[f"NASA_TEMP_{c}"] = (lambda cc=c: nasa_power_monthly_temp(cc))

    # USGS streamflow per gauge
    if include_usgs:
        for name, gid in USGS_GAUGES.items():
            out[f"USGS_FLOW_{name}"] = (lambda g=gid: usgs_streamflow_monthly(g))

    # EIA-930 daily grid demand per BA (high-frequency harmonic gold)
    if include_eia930:
        for ba in EIA930_BAS:
            out[f"EIA930_DEMAND_{ba}"] = (lambda b=ba: eia930_daily_demand(b))

    # OpenAQ daily PM2.5 per city
    if include_openaq:
        for c in OPENAQ_CITIES:
            out[f"OPENAQ_PM25_{c}"] = (lambda cc=c: openaq_pm25_daily(cc))

    # CoinGecko daily prices per coin
    if include_coingecko:
        for coin in COINGECKO_COINS:
            safe = coin.replace("-", "_")
            out[f"COINGECKO_{safe}"] = (lambda cid=coin: coingecko_daily_price(cid))

    return out
