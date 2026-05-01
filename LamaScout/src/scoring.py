import json
import random
from typing import Dict, List
import re
import pandas as pd
import numpy as np
from .settings import CFG, OUT, REP, NORM, utc_now


def clamp(v, lo=0.0, hi=100.0) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return lo


def pct_growth(cur, prev):
    try:
        cur = float(cur)
        prev = float(prev)
        if prev <= 0:
            return 1.0 if cur > 0 else 0.0
        return (cur - prev) / prev
    except Exception:
        return 0.0


def score_0_100(x, good_at=1.0) -> float:
    return clamp((x / good_at) * 100.0)


def mode_value(series: pd.Series) -> str:
    values = series.astype(str).str.strip().replace("nan", "").replace("", pd.NA)
    if values.dropna().empty:
        return ""
    return values.mode().iat[0]


def build_top_by_field(df: pd.DataFrame, field: str, top_n: int = 10) -> pd.DataFrame:
    rows = []
    for value, group in df.groupby(field):
        top = group.sort_values(["champion_score", "followers_current_total"], ascending=[False, False]).head(top_n)
        for _, r in top.iterrows():
            rows.append({
                field: value,
                "artist_name": r["artist_name"],
                "genre": r.get("genre", ""),
                "state": r.get("state", ""),
                "city": r.get("city", ""),
                "age_group": r.get("age_group", ""),
                "champion_score": float(r["champion_score"]),
                "tier": r["tier"],
                "followers_current_total": int(r["followers_current_total"]),
            })
    return pd.DataFrame(rows)


def build_production_candidates(scored: pd.DataFrame) -> pd.DataFrame:
    """Return cleaner live unsigned candidates suitable for production outputs."""
    if scored.empty:
        return scored.copy()

    out = scored.copy()
    name_series = out["artist_name"].astype(str)

    # Block names that are clearly the raw search query text echoed back as an artist name.
    # These are the specific generic descriptor phrases used in api_registry search_terms —
    # NOT generic artist-name words (unsigned, rising, etc. can legitimately appear in real names).
    synthetic_pattern = re.compile(
        r"\b(?:breakout live circuit|open mic act|local festival performer|regional showcase artist"
        r"|unsigned pop talent|breakthrough edm producer|viral singer songwriter"
        r"|emerging country artist usa|rising hiphop artist|breakthrough indie rock)\b",
        re.IGNORECASE,
    )
    synthetic_name = name_series.str.contains(synthetic_pattern, na=False)

    # Keep live, unsigned, active-enough rows with at least one real audience signal.
    mask = (
        out["source_origin"].astype(str).eq("live")
        & out["unsigned_prospect"].eq(True)
        & out["inactive_flag"].eq(False)
        & out["suspicious_flag"].eq(False)
        & (~synthetic_name)
        & ((out["followers_current_total"] > 0) | (out["avg_views_current_total"] > 0) | (out["monthly_listeners_current_total"] > 0))
    )

    # Production-grade floor: demand either real cross-platform breadth or strong single-platform scale,
    # plus a minimum score/urgency bar so the exported shortlist looks institutional rather than generic.
    quality_gate = (
        (out["champion_score"].fillna(0.0) >= 40.0)
        & (out["hot_priority"].fillna(0.0) >= 20.0)
        & (
            (out["platform_count"].fillna(0) >= 2)
            | (out["monthly_listeners_current_total"].fillna(0) >= 25000)
            | (
                (out["followers_current_total"].fillna(0) >= 250000)
                & (out["avg_views_current_total"].fillna(0) >= 150000)
            )
        )
    )

    cleaned = out[mask & quality_gate].copy()
    cleaned = cleaned.sort_values(
        ["hot_priority", "champion_score", "followers_current_total", "avg_views_current_total"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    return cleaned


def compute_artist_rollup(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for artist, g in df.groupby("artist_name"):
        platform_count = g["platform"].nunique()
        follower_growths = [pct_growth(a, b) for a, b in zip(g["followers_current"], g["followers_30d_ago"])]
        engagement_rates = list(g["engagement_rate"].astype(float))
        view_growths = [pct_growth(a, b) for a, b in zip(g["avg_views_current"], g["avg_views_30d_ago"])]
        ml_growths = [pct_growth(a, b) for a, b in zip(g["monthly_listeners_current"], g["monthly_listeners_30d_ago"])]
        trends_growths = [pct_growth(a, b) for a, b in zip(g["google_trends_current"], g["google_trends_30d_ago"])]

        posting_consistency = min(g["posts_30d"].sum() / 20.0, 1.0)
        cross_platform_strength = min(platform_count / max(len(CFG["platforms_expected"]), 1), 1.0)

        suspicious = False
        if g["followers_current"].sum() > 0:
            total_views = g["avg_views_current"].sum()
            total_followers = g["followers_current"].sum()
            if total_followers > 10000 and total_views < total_followers * 0.02:
                suspicious = True

        genre_mode = mode_value(g.get("genre", pd.Series(dtype=str)))
        city_mode = mode_value(g.get("city", pd.Series(dtype=str)))
        state_mode = mode_value(g.get("state", pd.Series(dtype=str)))
        country_mode = mode_value(g.get("country", pd.Series(dtype=str)))
        age_group_mode = mode_value(g.get("age_group", pd.Series(dtype=str)))
        agt_stage_mode = mode_value(g.get("agt_stage", pd.Series(dtype=str)))
        agt_age_group_mode = mode_value(g.get("agt_age_group", pd.Series(dtype=str)))

        genre_signal = min(len(g["genre"].dropna().unique()) / 3.0, 1.0)
        location_signal = min(len(g[["city", "state"]].drop_duplicates()) / 3.0, 1.0)
        age_cohort_signal = 1.0 if any(str(x).strip().lower() in ["20s", "30s", "40s"] for x in g.get("age_group", [])) else 0.5
        agt_cohort_signal = 1.0 if any(str(x).strip().lower() in ["audition", "judge cuts", "semifinal", "final", "top20", "top10"] for x in g.get("agt_stage", [])) else min(len(g["agt_stage"].dropna().unique()) / 3.0, 1.0)

        label_interest = mode_value(g.get("label_interest", pd.Series(dtype=str)))
        signed_flag = str(label_interest).strip().lower() in ["major", "signed", "label", "signed artist"]
        predicted_breakout = min(max(
            0.30 * np.mean(follower_growths) +
            0.20 * np.mean(view_growths) +
            0.20 * np.mean(trends_growths) +
            0.10 * cross_platform_strength +
            0.10 * posting_consistency +
            0.10 * min(float(g["press_mentions_30d"].max()) / 10.0, 1.0),
            0.0),
            1.0
        )
        time_to_100k = 999.0
        if np.mean(follower_growths) > 0 and g["followers_current"].sum() > 0:
            current_followers = g["followers_current"].sum()
            growth_rate = np.mean(follower_growths)
            if growth_rate > 0:
                time_to_100k = min(max(100000.0 / (current_followers * growth_rate), 0.0), 999.0)

        hot_urgency = min(max(
            predicted_breakout * 0.5 +
            cross_platform_strength * 0.15 +
            posting_consistency * 0.1 +
            min(float(g["press_mentions_30d"].max()) / 10.0, 1.0) * 0.1 +
            min(float(g["venue_mentions_30d"].max()) / 10.0, 1.0) * 0.1 +
            (0.1 if not signed_flag else 0.0),
            0.0),
            1.0
        )
        live_source_count = int(g["source_origin"].astype(str).eq("live").sum())
        rows.append({
            "artist_name": artist,
            "platform_count": platform_count,
            "followers_current_total": g["followers_current"].sum(),
            "avg_views_current_total": g["avg_views_current"].sum(),
            "monthly_listeners_current_total": g["monthly_listeners_current"].sum(),
            "follower_growth_30d": float(np.mean(follower_growths)) if follower_growths else 0.0,
            "engagement_rate": float(np.mean(engagement_rates)) if engagement_rates else 0.0,
            "engagement_velocity": float(np.mean(view_growths)) if view_growths else 0.0,
            "cross_platform_strength": cross_platform_strength,
            "spotify_monthly_listeners_growth": float(np.mean(ml_growths)) if ml_growths else 0.0,
            "youtube_view_growth": float(np.mean(view_growths)) if view_growths else 0.0,
            "posting_consistency": posting_consistency,
            "google_trends_growth": float(np.mean(trends_growths)) if trends_growths else 0.0,
            "genre_signal": genre_signal,
            "location_signal": location_signal,
            "agt_cohort_signal": agt_cohort_signal,
            "age_cohort_signal": age_cohort_signal,
            "press_signal": min(float(g["press_mentions_30d"].max()) / 10.0, 1.0),
            "venue_signal": min(float(g["venue_mentions_30d"].max()) / 10.0, 1.0),
            "genre": genre_mode,
            "city": city_mode,
            "state": state_mode,
            "country": country_mode,
            "age_group": age_group_mode,
            "agt_stage": agt_stage_mode,
            "agt_age_group": agt_age_group_mode,
            "label_interest": label_interest,
            "signed_flag": signed_flag,
            "unsigned_prospect": not signed_flag,
            "predicted_breakout": float(predicted_breakout),
            "hot_urgency": float(hot_urgency),
            "time_to_100k_days": float(time_to_100k),
            "live_source_count": live_source_count,
            "source_origin": "live" if live_source_count > 0 else "seed",
            "suspicious_flag": suspicious,
            "one_platform_only_flag": platform_count <= 1,
            "inactive_flag": g["posts_30d"].sum() <= 1,
        })

    out = pd.DataFrame(rows)
    out.to_csv(NORM / "artist_rollup.csv", index=False)
    return out


def score_artists(df: pd.DataFrame) -> pd.DataFrame:
    w = CFG["weights"]
    p = CFG["penalties"]
    scored = df.copy()

    scored["score_follower_growth"] = scored["follower_growth_30d"].apply(lambda x: score_0_100(x, 1.0))
    scored["score_engagement_rate"] = scored["engagement_rate"].apply(lambda x: score_0_100(x, 0.10))
    scored["score_engagement_velocity"] = scored["engagement_velocity"].apply(lambda x: score_0_100(x, 1.0))
    scored["score_cross_platform_strength"] = scored["cross_platform_strength"].apply(lambda x: score_0_100(x, 1.0))
    scored["score_spotify_growth"] = scored["spotify_monthly_listeners_growth"].apply(lambda x: score_0_100(x, 1.0))
    scored["score_youtube_growth"] = scored["youtube_view_growth"].apply(lambda x: score_0_100(x, 1.0))
    scored["score_posting_consistency"] = scored["posting_consistency"].apply(lambda x: score_0_100(x, 1.0))
    scored["score_google_trends"] = scored["google_trends_growth"].apply(lambda x: score_0_100(x, 1.0))
    scored["score_followers_total"] = scored["followers_current_total"].apply(lambda x: score_0_100(x, 100000.0))
    scored["score_avg_views_total"] = scored["avg_views_current_total"].apply(lambda x: score_0_100(x, 100000.0))
    scored["score_genre_signal"] = scored["genre_signal"].apply(lambda x: score_0_100(x, 1.0))
    scored["score_location_signal"] = scored["location_signal"].apply(lambda x: score_0_100(x, 1.0))
    scored["score_agt_cohort"] = scored["agt_cohort_signal"].apply(lambda x: score_0_100(x, 1.0))
    scored["score_age_cohort"] = scored["age_cohort_signal"].apply(lambda x: score_0_100(x, 1.0))
    scored["score_press_signal"] = scored["press_signal"].apply(lambda x: score_0_100(x, 1.0))
    scored["score_venue_signal"] = scored["venue_signal"].apply(lambda x: score_0_100(x, 1.0))
    scored["score_breakout"] = scored["predicted_breakout"].apply(lambda x: score_0_100(x, 1.0))
    scored["score_hot_urgency"] = scored["hot_urgency"].apply(lambda x: score_0_100(x, 1.0))

    scored["raw_score"] = (
        scored["score_follower_growth"] * w["follower_growth_30d"] +
        scored["score_engagement_rate"] * w["engagement_rate"] +
        scored["score_engagement_velocity"] * w["engagement_velocity"] +
        scored["score_cross_platform_strength"] * w["cross_platform_strength"] +
        scored["score_spotify_growth"] * w["spotify_monthly_listeners_growth"] +
        scored["score_youtube_growth"] * w["youtube_view_growth"] +
        scored["score_followers_total"] * w["followers_total"] +
        scored["score_avg_views_total"] * w["avg_views_total"] +
        scored["score_posting_consistency"] * w["posting_consistency"] +
        scored["score_google_trends"] * w["google_trends_growth"] +
        scored["score_genre_signal"] * w["genre_signal"] +
        scored["score_location_signal"] * w["location_signal"] +
        scored["score_agt_cohort"] * w["agt_cohort_signal"] +
        scored["score_age_cohort"] * w["age_cohort_signal"] +
        scored["score_press_signal"] * w["press_signal"] +
        scored["score_venue_signal"] * w["venue_signal"] +
        scored["score_breakout"] * w.get("breakout_score", 0.06) +
        scored["score_hot_urgency"] * w.get("hot_urgency", 0.04)
    )

    scored["penalty_score"] = 0.0
    scored.loc[scored["suspicious_flag"], "penalty_score"] += abs(p["suspicious_engagement_penalty"])
    scored.loc[scored["one_platform_only_flag"], "penalty_score"] += abs(p["one_platform_only_penalty"])
    scored.loc[scored["inactive_flag"], "penalty_score"] += abs(p["inactive_penalty"])

    scored["champion_score"] = (scored["raw_score"] - scored["penalty_score"]).clip(lower=0, upper=100)
    scored["hot_priority"] = scored["hot_urgency"] * 1.2 + scored["champion_score"] * 0.5

    def label(x: float) -> str:
        if x >= CFG["champion_threshold"]:
            return "CHAMPION"
        if x >= CFG["watch_threshold"]:
            return "WATCHLIST"
        return "PASS"

    scored["tier"] = scored["champion_score"].apply(label)
    scored = scored.sort_values(["champion_score", "followers_current_total"], ascending=[False, False]).reset_index(drop=True)
    return scored


def optimize_champions(df: pd.DataFrame) -> pd.DataFrame:
    portfolio_candidates = df[df["champion_score"] >= CFG["watch_threshold"]].copy()
    if portfolio_candidates.empty:
        df["champion_portfolio"] = ""
        df["champion_lineage"] = ""
        return df

    candidate_records = portfolio_candidates.to_dict(orient="records")
    best_portfolio: List[str] = []
    best_value = -1.0
    runs = min(max(200, CFG.get("monte_carlo_runs", 1000)), 2000)

    for _ in range(runs):
        size = random.randint(3, min(10, len(candidate_records)))
        subset = random.sample(candidate_records, size)
        raw_score = sum(float(item.get("champion_score", 0)) for item in subset)
        diversity = len({item.get("genre", "") for item in subset}) + len({item.get("state", "") for item in subset})
        concentration_penalty = sum(1 for item in subset if item.get("platform_count", 0) <= 1)
        value = raw_score + diversity * 3.0 - concentration_penalty * 4.0
        if value > best_value:
            best_value = value
            best_portfolio = [item["artist_name"] for item in subset]

    df["champion_portfolio"] = df["artist_name"].apply(lambda name: "PORTFOLIO" if name in best_portfolio else "")
    df["champion_lineage"] = df["artist_name"].apply(
        lambda name: ":".join(sorted(best_portfolio)) if name in best_portfolio else ""
    )
    return df


def build_reports(scored: pd.DataFrame):
    scored.to_csv(OUT / "artist_champion_rankings.csv", index=False)
    scored[scored["tier"] == "CHAMPION"].to_csv(OUT / "artist_champions_only.csv", index=False)
    scored[scored["tier"].isin(["CHAMPION", "WATCHLIST"])].to_csv(OUT / "artist_watchlist.csv", index=False)
    scored[scored["champion_portfolio"] == "PORTFOLIO"].to_csv(OUT / "artist_portfolio_champions.csv", index=False)
    scored.sort_values(["hot_priority", "score_breakout", "predicted_breakout"], ascending=[False, False, False]).head(20).to_csv(OUT / "artist_top_prospects.csv", index=False)
    scored.sort_values(["hot_priority", "time_to_100k_days"], ascending=[False, True]).head(20).to_csv(OUT / "artist_hot_radar.csv", index=False)
    scored[scored["source_origin"] == "live"].to_csv(OUT / "artist_live_champion_rankings.csv", index=False)
    scored[(scored["source_origin"] == "live") & (scored["tier"] == "CHAMPION")].to_csv(OUT / "artist_live_champions_only.csv", index=False)
    scored[(scored["source_origin"] == "live") & (scored["tier"].isin(["CHAMPION", "WATCHLIST"]))].to_csv(OUT / "artist_live_watchlist.csv", index=False)

    production = build_production_candidates(scored)
    production.to_csv(OUT / "artist_production_candidates.csv", index=False)
    production.head(10).to_csv(REP / "top10_unsigned_production.csv", index=False)

    build_top_field_reports(scored)

    live_only = scored[scored["source_origin"] == "live"]
    summary = {
        "generated_utc": utc_now(),
        "total_artists": int(len(scored)),
        "live_artists": int(len(live_only)),
        "champions": int((scored["tier"] == "CHAMPION").sum()),
        "live_champions": int((live_only["tier"] == "CHAMPION").sum()),
        "watchlist": int((scored["tier"] == "WATCHLIST").sum()),
        "live_watchlist": int((live_only["tier"] == "WATCHLIST").sum()),
        "pass": int((scored["tier"] == "PASS").sum()),
        "live_pass": int((live_only["tier"] == "PASS").sum()),
        "portfolio_size": int((scored["champion_portfolio"] == "PORTFOLIO").sum()),
        "top_prospect_count": int((scored["unsigned_prospect"] & (scored["score_breakout"] >= 50)).sum()),
        "hot_radar_count": int((scored["unsigned_prospect"] & (scored["hot_priority"] >= 50)).sum()),
        "production_candidate_count": int(len(production)),
        "production_top10_count": int(min(len(production), 10)),
        "top_artist": None if len(scored) == 0 else scored.iloc[0]["artist_name"],
        "top_live_artist": None if len(live_only) == 0 else live_only.iloc[0]["artist_name"],
        "top_production_artist": None if len(production) == 0 else production.iloc[0]["artist_name"],
    }
    (REP / "artist_scout_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "LumaScout ALERTS",
        f"Generated UTC: {utc_now()}",
        ""
    ]
    champs = scored[scored["tier"] == "CHAMPION"]
    prod_top = production.head(10)
    if len(prod_top) > 0:
        lines.append("Production Top Unsigned (cleaned):")
        for _, r in prod_top.iterrows():
            lines.append(
                f"{r['artist_name']} | score={r['champion_score']:.2f} | hot={r['hot_priority']:.2f} | followers={int(r['followers_current_total'])} | views={int(r['avg_views_current_total'])}"
            )
        lines.append("")
    if len(champs) == 0:
        lines.append("No champion artists found this run.")
    else:
        for _, r in champs.head(25).iterrows():
            lines.append(
                f"{r['artist_name']} | score={r['champion_score']:.2f} | followers={int(r['followers_current_total'])} | platforms={int(r['platform_count'])} | tier={r['tier']} | genre={r.get('genre','N/A')} | city={r.get('city','N/A')} | state={r.get('state','N/A')} | portfolio={r.get('champion_portfolio', '')}"
            )
    (REP / "artist_ping_alerts.txt").write_text("\n".join(lines), encoding="utf-8")


def build_top_field_reports(scored: pd.DataFrame):
    for field in ["genre", "city", "state", "age_group", "agt_stage", "agt_age_group"]:
        top = build_top_by_field(scored, field, top_n=10)
        if not top.empty:
            top.to_csv(OUT / f"artist_top10_by_{field}.csv", index=False)
