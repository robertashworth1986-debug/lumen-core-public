from typing import List
import pandas as pd
from .settings import CFG, NORM


def clamp(v, lo=0.0, hi=100.0):
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return lo


def normalize_artist_rows(df: pd.DataFrame) -> pd.DataFrame:
    required = CFG["required_columns"]
    if "source_file" not in df.columns:
        df["source_file"] = ""

    for c in required:
        if c not in df.columns:
            if c in ["artist_name", "platform", "genre", "city", "state", "country", "age_group", "agt_stage", "agt_age_group", "career_stage", "label_interest"]:
                df[c] = ""
            else:
                df[c] = 0

    df["artist_name"] = df["artist_name"].astype(str).str.strip()
    df["platform"] = df["platform"].astype(str).str.strip().str.lower()
    df["genre"] = df["genre"].astype(str).str.strip().str.lower()
    df["city"] = df["city"].astype(str).str.strip()
    df["state"] = df["state"].astype(str).str.strip()
    df["country"] = df["country"].astype(str).str.strip()
    df["age_group"] = df["age_group"].astype(str).str.strip().str.lower()
    df["agt_stage"] = df["agt_stage"].astype(str).str.strip().str.lower()
    df["agt_age_group"] = df["agt_age_group"].astype(str).str.strip().str.lower()
    df["career_stage"] = df["career_stage"].astype(str).str.strip().str.lower()
    df["label_interest"] = df["label_interest"].astype(str).str.strip().str.lower()

    def determine_source_origin(source_file: str) -> str:
        normalized = str(source_file or "").strip().lower()
        live_prefixes = ["live", "youtube:", "spotify:", "meta:", "google_trends:", "twitter:", "x:", "news_api:", "ticketmaster:"]
        return "live" if any(normalized.startswith(prefix) for prefix in live_prefixes) else "seed"

    df["source_origin"] = df["source_file"].apply(determine_source_origin)

    numeric_cols = [
        "followers_current",
        "followers_30d_ago",
        "engagement_rate",
        "avg_views_current",
        "avg_views_30d_ago",
        "posts_30d",
        "monthly_listeners_current",
        "monthly_listeners_30d_ago",
        "google_trends_current",
        "google_trends_30d_ago",
        "press_mentions_30d",
        "venue_mentions_30d",
    ]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df = df[df["artist_name"] != ""].copy()
    df.to_csv(NORM / "normalized_artist_rows.csv", index=False)
    return df
