from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
LATEST_PATH = OUT_OPS / "grants_email_receipts_latest.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slug(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text or "unknown"


def load_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "generated_utc": now_iso(),
            "scope": "grants_email_receipts",
            "records": [],
            "summary": {
                "record_count": 0,
                "tracking_numbers": [],
                "opportunity_numbers": [],
            },
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    if not isinstance(payload.get("records"), list):
        payload["records"] = []
    payload.setdefault("scope", "grants_email_receipts")
    return payload


def write_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def normalize_status(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text or "submitted_email_receipt"


def unique_sorted(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        out.append(text)
    out.sort()
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Upsert a Grants.gov email receipt record into grants_email_receipts_latest.json")
    parser.add_argument("--opp-num", required=True)
    parser.add_argument("--tracking-number", required=True)
    parser.add_argument("--status", default="submitted_email_receipt")
    parser.add_argument("--agency-tracking-number", default="")
    parser.add_argument("--grant-id", default="")
    parser.add_argument("--application-name", default="")
    parser.add_argument("--opportunity-name", default="")
    parser.add_argument("--uei", default="")
    parser.add_argument("--aor-name", default="")
    parser.add_argument("--event-utc", default="")
    parser.add_argument("--email-subject", default="")
    parser.add_argument("--email-received-local", default="")
    parser.add_argument("--email-link", default="")
    parser.add_argument("--source", default="gmail_manual_receipt")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    opp_num = str(args.opp_num or "").strip()
    tracking_number = str(args.tracking_number or "").strip()
    if not opp_num:
        raise SystemExit("--opp-num is required")
    if not tracking_number:
        raise SystemExit("--tracking-number is required")

    payload = load_payload(LATEST_PATH)
    records = payload.get("records", [])
    assert isinstance(records, list)

    key = (opp_num.upper(), tracking_number.upper())
    updated = False

    default_grant_id = f"live_{slug(opp_num)}"
    row: dict[str, Any] = {
        "grant_id": str(args.grant_id or default_grant_id).strip(),
        "opp_num": opp_num,
        "status": normalize_status(str(args.status or "")),
        "grants_tracking_number": tracking_number,
        "agency_tracking_number": str(args.agency_tracking_number or "").strip(),
        "uei": str(args.uei or "").strip(),
        "aor_name": str(args.aor_name or "").strip(),
        "application_name": str(args.application_name or "").strip(),
        "opportunity_name": str(args.opportunity_name or "").strip(),
        "event_utc": str(args.event_utc or "").strip(),
        "email_subject": str(args.email_subject or "").strip(),
        "email_received_local": str(args.email_received_local or "").strip(),
        "email_link": str(args.email_link or "").strip(),
        "source": str(args.source or "").strip() or "gmail_manual_receipt",
        "notes": str(args.notes or "").strip(),
    }
    row = {k: v for k, v in row.items() if v not in (None, "")}

    for idx, existing in enumerate(records):
        if not isinstance(existing, dict):
            continue
        existing_key = (
            str(existing.get("opp_num") or "").strip().upper(),
            str(existing.get("grants_tracking_number") or "").strip().upper(),
        )
        if existing_key == key:
            merged = dict(existing)
            merged.update(row)
            records[idx] = merged
            updated = True
            break

    if not updated:
        records.append(row)

    records.sort(key=lambda r: (str((r or {}).get("opp_num") or ""), str((r or {}).get("grants_tracking_number") or "")))

    payload["generated_utc"] = now_iso()
    payload["scope"] = "grants_email_receipts"
    payload["records"] = records
    payload["summary"] = {
        "record_count": len(records),
        "tracking_numbers": unique_sorted([str((r or {}).get("grants_tracking_number") or "") for r in records]),
        "opportunity_numbers": unique_sorted([str((r or {}).get("opp_num") or "") for r in records]),
    }

    stamp = now_tag()
    ts_path = OUT_OPS / f"grants_email_receipts_{stamp}.json"
    write_payload(ts_path, payload)
    write_payload(LATEST_PATH, payload)

    action = "updated" if updated else "inserted"
    print("UPSERT_GRANTS_EMAIL_RECEIPT")
    print(f"action={action}")
    print(f"opp_num={opp_num}")
    print(f"grants_tracking_number={tracking_number}")
    print(f"record_count={payload['summary']['record_count']}")
    print(f"latest={LATEST_PATH}")
    print(f"snapshot={ts_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
