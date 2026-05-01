from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CLEAN = ROOT / "clean_data"
OUT = ROOT / "data" / "launcher_index"
OUT.mkdir(parents=True, exist_ok=True)

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

def pick_cols(df: pd.DataFrame):
    cols = [str(c) for c in df.columns]
    low = {c.lower(): c for c in cols}

    time_col = ""
    for c in ["time","date","datetime","timestamp","observation_date","period","year","month"]:
        if c in low:
            time_col = low[c]
            break

    value_col = ""
    for c in ["value","close","price","last","gdp","demand (mwh)","net generation (mwh)","demand forecast (mwh)"]:
        if c in low:
            value_col = low[c]
            break

    if not value_col:
        numeric = []
        for c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce")
            if s.notna().sum() >= max(5, int(len(df) * 0.5)):
                numeric.append(c)
        if numeric:
            value_col = str(numeric[0])

    return time_col, value_col

rows = []
for p in sorted(CLEAN.glob("*.csv")):
    try:
        df = pd.read_csv(p, nrows=2000)
        n_rows_est = sum(1 for _ in open(p, "r", encoding="utf-8", errors="ignore")) - 1
        tcol, vcol = pick_cols(df)

        dataset_name = p.stem.lower()
        sector = "unknown"
        for s in ["macro","energy","rates","volatility","crypto","electricity","petroleum","gas","coal","renewables"]:
            if s in dataset_name:
                sector = s
                break

        engine_ready = bool(vcol)

        rows.append({
            "dataset_id": sha1_file(p),
            "file_name": p.name,
            "full_path": str(p),
            "rows_est": max(n_rows_est, 0),
            "cols": len(df.columns),
            "time_col": tcol,
            "value_col": vcol,
            "sector_guess": sector,
            "engine_ready": engine_ready,
            "size_bytes": p.stat().st_size,
            "modified_utc": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
        })
    except Exception as e:
        rows.append({
            "dataset_id": "",
            "file_name": p.name,
            "full_path": str(p),
            "rows_est": -1,
            "cols": -1,
            "time_col": "",
            "value_col": "",
            "sector_guess": "error",
            "engine_ready": False,
            "size_bytes": p.stat().st_size if p.exists() else -1,
            "modified_utc": "",
            "error": str(e)
        })

df = pd.DataFrame(rows)
df.to_csv(OUT / "DATASET_LAUNCHER_INDEX.csv", index=False)

ready = df[df["engine_ready"] == True].copy()
ready = ready.sort_values(["rows_est","size_bytes"], ascending=[False,False])
ready.to_csv(OUT / "ENGINE_READY_DATASETS.csv", index=False)

manifest = {
    "generated_utc": utc_now(),
    "canonical_root": str(ROOT),
    "clean_data_root": str(CLEAN),
    "dataset_index_csv": str(OUT / "DATASET_LAUNCHER_INDEX.csv"),
    "engine_ready_csv": str(OUT / "ENGINE_READY_DATASETS.csv"),
    "engine_ready_count": int(len(ready)),
    "notes": [
        "Use ENGINE_READY_DATASETS.csv as the only launcher source for ranking/testing.",
        "Do not point the engine at scattered folders anymore."
    ]
}
(OUT / "DATASET_LAUNCHER_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

ps_lines = []
ps_lines.append('$datasets = Import-Csv "C:\LumaTrader\INSTITUTIONAL_STACK_V2\data\launcher_index\ENGINE_READY_DATASETS.csv"')
ps_lines.append('$datasets | Select-Object -First 25 file_name, full_path, rows_est, time_col, value_col, sector_guess | Format-Table -AutoSize')
(OUT / "SHOW_ENGINE_READY_DATASETS.ps1").write_text("\n".join(ps_lines), encoding="utf-8")

print(OUT / "DATASET_LAUNCHER_INDEX.csv")
print(OUT / "ENGINE_READY_DATASETS.csv")
print(OUT / "DATASET_LAUNCHER_MANIFEST.json")
print(OUT / "SHOW_ENGINE_READY_DATASETS.ps1")
