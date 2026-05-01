import csv
import hashlib
import json
from datetime import datetime, timezone
import os


LEDGER_SCHEMA_VERSION = "1.1.0"

class TradeLedger:
    def __init__(self, csv_path: str, jsonl_path: str):
        self.csv_path = csv_path
        self.jsonl_path = jsonl_path

    def append(self, row: dict) -> str:
        row = dict(row)
        row.setdefault("ledger_schema_version", LEDGER_SCHEMA_VERSION)
        row["logged_utc"] = datetime.now(timezone.utc).isoformat()
        digest = hashlib.sha256(json.dumps(row, sort_keys=True).encode("utf-8")).hexdigest()
        row["record_hash"] = digest

        header = list(row.keys())
        exists = os.path.exists(self.csv_path)

        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=header)
            if not exists:
                w.writeheader()
            w.writerow(row)

        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return digest
