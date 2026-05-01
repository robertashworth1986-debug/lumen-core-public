import os
import pandas as pd

DATA_DIRS = [
    r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\data",
    r"C:\Users\Novac\iCloudDrive\Data sets"  # adjust if needed
]

OUTPUT_CLEAN = r"C:\LumaTrader\clean_data"
os.makedirs(OUTPUT_CLEAN, exist_ok=True)

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
            df = pd.read_csv(file, encoding=enc, delim_whitespace=True)
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

            print(f"Scanning: {path}")

            df = try_read(path)

            if df is None:
                print(f"Skipped (unreadable): {file}")
                continue

            numeric_cols = df.select_dtypes(include=['number']).columns

            if len(numeric_cols) == 0:
                print(f"Skipped (no numeric data): {file}")
                continue

            score = df[numeric_cols].std().mean()

            clean_path = os.path.join(OUTPUT_CLEAN, file)
            df.to_csv(clean_path, index=False)

            results.append({
                "file": file,
                "rows": len(df),
                "cols": len(df.columns),
                "score": score
            })

summary = pd.DataFrame(results).sort_values("score", ascending=False)
summary.to_csv(r"C:\LumaTrader\data_scan_summary.csv", index=False)

print("FULL DATA INGEST COMPLETE")