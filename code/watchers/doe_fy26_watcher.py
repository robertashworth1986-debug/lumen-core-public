"""DOE SBIR FY26 NOFO watcher.

Polls https://science.osti.gov/sbir/Funding-Opportunities and detects when the
FY26 funding opportunity flips from "Future" → "Current" (i.e. opens for
submission). Writes a heartbeat JSON the dashboard / federal brief can read.

Run weekly (cron / Task Scheduler / luma_experience_gateway daemon).
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://science.osti.gov/sbir/Funding-Opportunities"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "grants" / "doe_fy26_watch.json"
OUT.parent.mkdir(parents=True, exist_ok=True)


def fetch() -> str:
    req = urllib.request.Request(
        URL,
        headers={"User-Agent": "LumenCore-FY26-Watcher/1.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="replace")


def detect_state(html: str) -> dict:
    """Detect FY25 / FY26 state from the OSTI page header table.

    Header has the form: 'FY26 (Future) | FY25 (Current) | FY24 (Closed)'.
    We extract each FY's parenthetical label specifically.
    """
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    def label_for(fy: str) -> str | None:
        m = re.search(rf"FY{fy}\s*\(([^)]+)\)", text, flags=re.IGNORECASE)
        return m.group(1).strip().lower() if m else None

    return {
        "fy25": label_for("25"),
        "fy26": label_for("26"),
        "fy27": label_for("27"),
    }


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    record = {"checked_utc": now, "url": URL}
    try:
        html = fetch()
        state = detect_state(html)
        record.update(state)
        # Alert when FY26 transitions out of "future" (e.g. to "current"/"open"/"released")
        fy26 = (state.get("fy26") or "").lower()
        record["alert"] = bool(fy26) and fy26 not in {"future", "closed", ""}
        record["status"] = "ok"
    except Exception as e:  # noqa: BLE001
        record["status"] = "error"
        record["error"] = str(e)
        record["alert"] = False

    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, indent=2), encoding="utf-8")
    tmp.replace(OUT)
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
