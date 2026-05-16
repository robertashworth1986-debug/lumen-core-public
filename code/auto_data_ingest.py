import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(os.getenv("LUMA_ROOT", str(Path(__file__).resolve().parents[1]))).resolve()

DATA_DIRS = [
    ROOT / "data",
    ROOT.parent / "data",
]

_icloud_default = Path.home() / "iCloudDrive" / "Data sets"
if _icloud_default.exists():
    DATA_DIRS.append(_icloud_default)

_extra_data_dir = os.getenv("LUMA_EXTRA_DATA_DIR", "").strip()
if _extra_data_dir:
    DATA_DIRS.append(Path(_extra_data_dir))

DATA_DIRS = [p for p in DATA_DIRS if p.exists()]

OUTPUT_CLEAN = Path(os.getenv("LUMA_CLEAN_OUTPUT_DIR", str(ROOT.parent / "clean_data"))).resolve()
SUMMARY_PATH = Path(os.getenv("LUMA_DATA_SCAN_SUMMARY_PATH", str(ROOT.parent / "data_scan_summary.csv"))).resolve()

OUTPUT_CLEAN.mkdir(parents=True, exist_ok=True)


def safe_print(message: str) -> None:
    text = str(message)
    try:
        print(text)
    except UnicodeEncodeError:
        buf = getattr(sys.stdout, "buffer", None)
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        if buf is not None:
            buf.write(text.encode(enc, errors="backslashreplace") + b"\n")
        else:
            print(text.encode("utf-8", errors="backslashreplace").decode("utf-8"))

def try_read(file):
    encodings = ["utf-8", "latin1", "cp1252"]
    
    for enc in encodings:
        try:
            # Try normal read
            df = pd.read_csv(file, encoding=enc)
            if len(df.columns) > 1:
                return df
        except:
            pass

        try:
            # Try auto delimiter detection
            df = pd.read_csv(file, encoding=enc, sep=None, engine='python')
            if len(df.columns) > 1:
                return df
        except:
            pass

        try:
            # Try fixing weird spacing files
            df = pd.read_csv(file, encoding=enc, sep=r"\s+")
            if len(df.columns) > 1:
                return df
        except:
            pass

    return None

results = []

for directory in DATA_DIRS:
    for root, _, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)

            if not file.lower().endswith(".csv"):
                continue

            safe_print(f"Scanning: {path}")

            df = try_read(path)

            if df is None:
                safe_print(f"Skipped (unreadable): {file}")
                continue

            numeric_cols = df.select_dtypes(include=['number']).columns

            if len(numeric_cols) == 0:
                safe_print(f"Skipped (no numeric data): {file}")
                continue

            score = df[numeric_cols].std().mean()

            clean_path = OUTPUT_CLEAN / file
            df.to_csv(clean_path, index=False)

            results.append({
                "file": file,
                "rows": len(df),
                "cols": len(df.columns),
                "score": score
            })

if results:
    summary = pd.DataFrame(results).sort_values("score", ascending=False)
else:
    summary = pd.DataFrame(columns=["file", "rows", "cols", "score"])

SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
summary.to_csv(SUMMARY_PATH, index=False)

safe_print(f"FULL DATA INGEST COMPLETE | scanned_roots={len(DATA_DIRS)} | rows={len(summary)}")