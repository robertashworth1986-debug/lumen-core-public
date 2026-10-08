"""Local research input validation and transactional, non-overwriting reports."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import platform
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

import numpy as np

BOUNDARY = (
    "Descriptive research output only. No independent validation, causal benefit, "
    "physical energy saving, revenue, ROI or production approval is established."
)


def snapshot(path):
    path = Path(path)
    # Bound local accidental inputs before parsing; do not silently trim rows.
    with path.open("rb") as stream:
        raw = stream.read(32 * 1024 * 1024 + 1)
    if len(raw) > 32 * 1024 * 1024:
        raise ValueError("research input exceeds 32 MiB")
    return raw


def number(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("numeric values cannot be null or boolean")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("all required numeric values must be finite")
    return result


def columns(rows, required, minimum=2):
    if not isinstance(rows, list) or len(rows) < minimum:
        raise ValueError(f"at least {minimum} rows are required")
    try:
        return {key: np.array([number(row[key]) for row in rows]) for key in required}
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError("missing, malformed or nonfinite required column") from exc


def csv_columns(raw, required, minimum=2):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    names = reader.fieldnames or []
    if len(names) != len(set(names)) or not set(required).issubset(names):
        raise ValueError("missing or duplicate CSV headers")
    rows = list(reader)
    if any(None in row for row in rows):
        raise ValueError("CSV row has more values than headers")
    return columns(rows, required, minimum)


def increasing(values, uniform=False):
    gaps = np.diff(values)
    if not np.all(gaps > 0):
        raise ValueError("steps/timestamps must be strictly increasing")
    if uniform and not np.allclose(gaps, gaps[0], rtol=1e-6, atol=1e-12):
        raise ValueError("spectral analysis requires uniform time spacing")
    return float(gaps[0])


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def reject(value):
        raise ValueError(f"nonfinite JSON constant: {value}")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=reject)


def write_manifest(folder, details, inputs):
    """Keep exact consumed bytes; hashes bind artifacts, not scientific validity."""
    for label, raw in inputs.items():
        (folder / label).write_bytes(raw)
    files = {
        path.name: {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "size_bytes": path.stat().st_size}
        for path in sorted(folder.iterdir()) if path.is_file()
    }
    report = {"schema": "lumencore.descriptive_research_report.v1",
              "boundary": BOUNDARY, "python": platform.python_version(),
              "numpy": np.__version__, **details, "files": files}
    (folder / "manifest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8")
    return report


@contextmanager
def new_report(output):
    """Only expose a report after every artifact and manifest succeeds."""
    output = Path(output)
    if output.exists():
        raise FileExistsError("choose a new output directory; reports are not overwritten")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".research-", dir=output.parent))
    try:
        yield stage
        # Reserve the destination, including against concurrent report writers.
        output.mkdir()
        try:
            stage.rename(output)
        except BaseException:
            output.rmdir()
            raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def plotting():
    # Plotting is optional; numeric validation uses the institutional test lock.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt
