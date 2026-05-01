import pandas as pd
from .ingest import load_raw_drops, fetch_live_data
from .normalize import normalize_artist_rows
from .scoring import compute_artist_rollup, score_artists, optimize_champions, build_reports
from .truth import TruthEngine
from .audit import build_run_proof
from .settings import RAW, LOG, utc_now


def run_lama_scout() -> None:
    raw = load_raw_drops()
    live = fetch_live_data()

    if raw.empty and live.empty:
        print("No raw or live artist data found.")
        return

    if not live.empty:
        combined = live
    else:
        combined = raw

    if combined.empty:
        print("No raw or live artist data found.")
        return

    normalized = normalize_artist_rows(combined)
    rollup = compute_artist_rollup(normalized)
    scored = score_artists(rollup)
    scored = optimize_champions(scored)
    build_reports(scored)

    truth_engine = TruthEngine()
    truth_engine.assess(scored)

    raw_paths = list(RAW.glob("*.csv")) + list(RAW.glob("*.xlsx"))
    source_snapshots = getattr(live, "attrs", {}).get("source_snapshots", {}) if hasattr(live, "attrs") else {}
    proof_path = build_run_proof(
        run_id=f"lama_scout_{utc_now().replace(':', '').replace('T', '_').replace('-', '')}",
        raw_paths=raw_paths,
        live_row_count=len(live) if not live.empty else 0,
        scored_rows=len(scored),
        champions=int((scored["tier"] == "CHAMPION").sum()),
        watchlist=int((scored["tier"] == "WATCHLIST").sum()),
        pass_count=int((scored["tier"] == "PASS").sum()),
        top_artists=[
            {
                "artist_name": r["artist_name"],
                "champion_score": float(r["champion_score"]),
                "genre": r.get("genre", ""),
                "city": r.get("city", ""),
                "state": r.get("state", ""),
            }
            for _, r in scored.head(10).iterrows()
        ],
        source_snapshots=source_snapshots,
    )

    print("LumaScout run complete")
    print("Outputs:")
    print("- artist_champion_rankings.csv")
    print("- artist_champions_only.csv")
    print("- artist_watchlist.csv")
    print("- artist_portfolio_champions.csv")
    print("- artist_ping_alerts.txt")
    print("- artist_scout_summary.json")
    print(f"- run proof: {proof_path}")


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="LamaScout Pipeline Runner")
    parser.add_argument("--loop", action="store_true", help="Run continuously on an interval")
    parser.add_argument("--interval", type=int, default=1800, help="Loop interval in seconds (default: 1800 = 30 min)")
    args = parser.parse_args()

    if args.loop:
        run_number = 0
        while True:
            run_number += 1
            print(f"\n[LumaScout] Loop run #{run_number} — {utc_now()}")
            try:
                run_lama_scout()
            except Exception as exc:
                print(f"[LumaScout] Run #{run_number} error: {exc}")
            print(f"[LumaScout] Sleeping {args.interval}s until next run...")
            time.sleep(args.interval)
    else:
        run_lama_scout()
