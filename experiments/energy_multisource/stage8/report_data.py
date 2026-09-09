"""Reproduce bounded chart snapshots from all frozen metric shards using SQLite."""
import argparse
import json
from pathlib import Path
import sqlite3

import run_stage8 as run


def project(results):
    entries = run.strict_json(results / "INDEX.json")
    rows = [r for e in entries for r in run.strict_json(results / "metrics" / (Path(e["array_file"]).stem + ".json"))]
    columns = list(rows[0])
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE stage8_metrics (" + ",".join('"' + c + '"' for c in columns) + ")")
        db.executemany("INSERT INTO stage8_metrics VALUES (" + ",".join("?" for _ in columns) + ")",
                       [[json.dumps(r[c]) if isinstance(r[c], list) else r[c] for c in columns] for r in rows])
        db.row_factory = sqlite3.Row
        queries = (run.HERE / "report_queries.sql").read_text().strip().split("\n\n")
        datasets = {}
        for block in queries:
            label, sql = block.split("\n", 1)
            datasets[label.removeprefix("-- ")] = [dict(r) for r in db.execute(sql)]
        return datasets


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists(): raise ValueError("Refusing to replace a report snapshot")
    run.write_json(a.out, project(a.results))
