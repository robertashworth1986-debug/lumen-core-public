from __future__ import annotations
import os, re, json, ast, csv, hashlib
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import yaml

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CFG  = yaml.safe_load((ROOT / "config" / "universal_normalizer.yaml").read_text(encoding="utf-8"))

OUT = ROOT / "data" / "normalized_csv_lake"
PER = OUT / "per_series"
LOG = ROOT / "logs"
OUT.mkdir(parents=True, exist_ok=True)
PER.mkdir(parents=True, exist_ok=True)
LOG.mkdir(parents=True, exist_ok=True)

SCAN_ROOTS = [Path(x) for x in CFG.get("scan_roots", []) if Path(x).exists()]
ALLOWED = set([x.lower() for x in CFG.get("allowed_exts", [])])
EXCLUDE = set(CFG.get("exclude_dir_names", []))

MANIFEST_CSV = OUT / "NORMALIZATION_MANIFEST.csv"
MASTER_CSV   = OUT / "MASTER_NORMALIZED_SERIES.csv"
FAIL_CSV     = OUT / "NORMALIZATION_FAILURES.csv"
SUMMARY_TXT  = OUT / "NORMALIZATION_SUMMARY.txt"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def sha1_text(x: str) -> str:
    return hashlib.sha1(x.encode("utf-8", errors="ignore")).hexdigest()[:12]

def safe_name(x: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", x).strip("_")[:180]

def walk_files():
    for root in SCAN_ROOTS:
        for dirpath, dirnames, filenames in os.walk(root, topdown=True):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE]
            for fn in filenames:
                p = Path(dirpath) / fn
                if p.suffix.lower() in ALLOWED:
                    yield p

def longify_df(df: pd.DataFrame, source_file: str, series_hint: str | None = None) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return pd.DataFrame()

    # Standardize columns
    cols = [str(c) for c in df.columns]
    low = {c.lower(): c for c in cols}

    time_col = None
    for c in ["time","timestamp","date","datetime","period","year","month"]:
        if c in low:
            time_col = low[c]
            break

    value_col = None
    for c in ["value","close","open","high","low","price","last","adj_close","settle"]:
        if c in low:
            value_col = low[c]
            break

    series_col = None
    for c in ["series","series_id","symbol","pair","ticker","asset","name"]:
        if c in low:
            series_col = low[c]
            break

    # If already long-ish
    if time_col and value_col:
        out = pd.DataFrame({
            "time": pd.to_datetime(df[time_col], errors="coerce"),
            "value": pd.to_numeric(df[value_col], errors="coerce"),
            "series": df[series_col].astype(str) if series_col else (series_hint or Path(source_file).stem),
            "source_file": source_file
        })
        return out.dropna(subset=["time","value"])

    # Wide numeric table -> melt
    numeric_cols = []
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().sum() >= max(5, int(len(df) * 0.5)):
            numeric_cols.append(c)

    if time_col and numeric_cols:
        tmp = df[[time_col] + numeric_cols].copy()
        tmp[time_col] = pd.to_datetime(tmp[time_col], errors="coerce")
        m = tmp.melt(id_vars=[time_col], value_vars=numeric_cols, var_name="series", value_name="value")
        m["value"] = pd.to_numeric(m["value"], errors="coerce")
        m["source_file"] = source_file
        m = m.rename(columns={time_col: "time"})
        return m.dropna(subset=["time","value"])

    # Pure numeric single column
    if len(numeric_cols) == 1:
        c = numeric_cols[0]
        out = pd.DataFrame({
            "time": pd.RangeIndex(start=0, stop=len(df), step=1),
            "value": pd.to_numeric(df[c], errors="coerce"),
            "series": series_hint or c,
            "source_file": source_file
        })
        return out.dropna(subset=["value"])

    return pd.DataFrame()

def parse_json_file(path: Path) -> list[pd.DataFrame]:
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    out = []
    if not text:
        return out
    obj = json.loads(text)

    # list of dicts
    if isinstance(obj, list):
        if len(obj) == 0:
            return out
        if all(isinstance(x, dict) for x in obj):
            df = pd.DataFrame(obj)
            lf = longify_df(df, str(path))
            if len(lf):
                out.append(lf)
            return out

    # dict
    if isinstance(obj, dict):
        # EIA style single series
        if "series_id" in obj and "data" in obj:
            sid = str(obj.get("series_id", path.stem))
            rows = obj.get("data", [])
            df = pd.DataFrame(rows, columns=["time","value"])
            df["series"] = sid
            df["source_file"] = str(path)
            df["time"] = pd.to_datetime(df["time"], errors="coerce")
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            out.append(df.dropna(subset=["time","value"]))
            return out

        # object contains list under a key
        for k, v in obj.items():
            if isinstance(v, list) and len(v) and all(isinstance(x, dict) for x in v):
                df = pd.DataFrame(v)
                lf = longify_df(df, str(path), series_hint=k)
                if len(lf):
                    out.append(lf)
        if out:
            return out

        # generic dataframe attempt
        df = pd.DataFrame([obj])
        lf = longify_df(df, str(path))
        if len(lf):
            out.append(lf)
    return out

def parse_txt_bulk_series(path: Path) -> list[pd.DataFrame]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    out = []

    # Find object blocks like {"series_id":"...","name":"...","data":[...]}
    starts = [m.start() for m in re.finditer(r'\{"series_id"\s*:', text)]
    if not starts:
        return out

    starts.append(len(text))
    for i in range(len(starts)-1):
        chunk = text[starts[i]:starts[i+1]]
        chunk = chunk.strip().rstrip(",")
        if not chunk.endswith("}"):
            last = chunk.rfind("}")
            if last != -1:
                chunk = chunk[:last+1]
        try:
            obj = json.loads(chunk)
        except Exception:
            try:
                obj = ast.literal_eval(chunk)
            except Exception:
                continue

        if not isinstance(obj, dict) or "data" not in obj:
            continue

        sid = str(obj.get("series_id") or obj.get("name") or path.stem)
        rows = obj.get("data", [])
        if not isinstance(rows, list) or len(rows) == 0:
            continue

        try:
            df = pd.DataFrame(rows, columns=["time","value"])
        except Exception:
            continue

        df["series"] = sid
        df["source_file"] = str(path)
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["time","value"])
        if len(df):
            out.append(df)

    return out

def parse_csv_excel(path: Path) -> list[pd.DataFrame]:
    out = []
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        lf = longify_df(df, str(path))
        if len(lf):
            out.append(lf)
    elif path.suffix.lower() in (".xlsx",".xls"):
        book = pd.read_excel(path, sheet_name=None)
        for sheet_name, df in book.items():
            lf = longify_df(df, str(path), series_hint=sheet_name)
            if len(lf):
                out.append(lf)
    return out

manifest_rows = []
fail_rows = []
master_frames = []

for path in walk_files():
    try:
        parsed = []
        ext = path.suffix.lower()

        if ext in (".csv",".xlsx",".xls"):
            parsed = parse_csv_excel(path)
        elif ext == ".json":
            parsed = parse_json_file(path)
        elif ext == ".txt":
            parsed = parse_txt_bulk_series(path)

        if not parsed:
            fail_rows.append({
                "file": str(path),
                "reason": "no_parseable_series_found"
            })
            continue

        for df in parsed:
            if len(df) == 0:
                continue

            df = df.copy()
            df["series"] = df["series"].astype(str)
            df["source_file"] = df["source_file"].astype(str)
            df = df.sort_values(["series","time"]).reset_index(drop=True)

            for sid, g in df.groupby("series"):
                sid_safe = safe_name(sid)
                sig = sha1_text(str(path) + "|" + sid_safe)
                out_file = PER / f"{sid_safe}__{sig}.csv"
                g[["time","value","series","source_file"]].to_csv(out_file, index=False)

                manifest_rows.append({
                    "series": sid,
                    "rows": int(len(g)),
                    "source_file": str(path),
                    "normalized_csv": str(out_file)
                })

            master_frames.append(df[["time","value","series","source_file"]])

    except Exception as e:
        fail_rows.append({
            "file": str(path),
            "reason": str(e)
        })

if master_frames:
    master = pd.concat(master_frames, ignore_index=True)
    master = master.dropna(subset=["value"]).sort_values(["series","time"]).reset_index(drop=True)
    master.to_csv(MASTER_CSV, index=False)
else:
    pd.DataFrame(columns=["time","value","series","source_file"]).to_csv(MASTER_CSV, index=False)

pd.DataFrame(manifest_rows).to_csv(MANIFEST_CSV, index=False)
pd.DataFrame(fail_rows).to_csv(FAIL_CSV, index=False)

with open(SUMMARY_TXT, "w", encoding="utf-8") as f:
    f.write("UNIVERSAL NORMALIZER SUMMARY\n")
    f.write("============================\n\n")
    f.write(f"UTC: {utc_now()}\n")
    f.write(f"Scan roots: {len(SCAN_ROOTS)}\n")
    f.write(f"Manifest rows: {len(manifest_rows)}\n")
    f.write(f"Failures: {len(fail_rows)}\n")
    f.write(f"Master CSV: {MASTER_CSV}\n")
    f.write(f"Per-series folder: {PER}\n")
    f.write(f"Manifest CSV: {MANIFEST_CSV}\n")
    f.write(f"Failure CSV: {FAIL_CSV}\n")

print(MASTER_CSV)
print(MANIFEST_CSV)
print(FAIL_CSV)
print(SUMMARY_TXT)
