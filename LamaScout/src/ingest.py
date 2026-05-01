from pathlib import Path
from typing import List
import pandas as pd
from .api_clients import client_for_source
from .audit import save_api_snapshot
from .settings import RAW, LOG, API_REGISTRY, utc_now


def load_raw_drops() -> pd.DataFrame:
    files = list(RAW.glob("*.csv")) + list(RAW.glob("*.xlsx"))
    frames = []
    for f in files:
        try:
            if f.suffix.lower() == ".csv":
                df = pd.read_csv(f)
            else:
                df = pd.read_excel(f)
            df["source_file"] = f.name
            frames.append(df)
        except Exception as exc:
            with open(LOG / "artist_scout_errors.log", "a", encoding="utf-8") as logf:
                logf.write(f"[{utc_now()}] failed_load {f}: {exc}\n")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def fetch_live_data() -> pd.DataFrame:
    active_sources = [source for source in API_REGISTRY.get("sources", []) if source.get("active")]
    rows = []

    source_snapshots = {}
    for source in active_sources:
        try:
            client = client_for_source(source)
            source_rows = client.fetch_artist_rows()
            if source_rows:
                rows.extend(source_rows)
                try:
                    snapshot_path = save_api_snapshot(source.get("name", "unknown"), source, source_rows)
                    source_snapshots[source.get("name", "unknown")] = source_snapshots.get(source.get("name", "unknown"), 0) + len(source_rows)
                except Exception:
                    source_snapshots[source.get("name", "unknown")] = source_snapshots.get(source.get("name", "unknown"), 0) + len(source_rows)
        except Exception as exc:
            with open(LOG / "artist_scout_errors.log", "a", encoding="utf-8") as logf:
                logf.write(f"[{utc_now()}] live_source_error {source.get('name')} : {exc}\n")

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df.attrs["source_snapshots"] = source_snapshots
    return df
