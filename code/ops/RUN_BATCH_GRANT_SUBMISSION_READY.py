from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
OUT_OPS_BATCH = OUT_OPS / "grant_submission_batch"
GRANTS_ROOT = ROOT / "out" / "grants"
QUEUE_PATH = GRANTS_ROOT / "_queue" / "index.json"


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_queue() -> dict[str, Any]:
    if QUEUE_PATH.exists():
        return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    sys.path.insert(0, str(ROOT / "code"))
    from grant_application_factory import update_queue

    return update_queue()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def find_latest_run(grant_id: str) -> Path | None:
    grant_dir = GRANTS_ROOT / grant_id
    if not grant_dir.exists() or not grant_dir.is_dir():
        return None
    runs = sorted([p for p in grant_dir.iterdir() if p.is_dir()])
    return runs[-1] if runs else None


def load_csv(csv_path: Path) -> list[dict[str, str | None]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    rows: list[dict[str, str | None]] = []
    with csv_path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append({k.strip(): (v.strip() if v is not None else None) for k, v in row.items()})
    return rows


def prepare_submission(grant_id: str, catalog_entry: dict | None, force: bool, dry_run: bool) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "code"))
    from grant_submission_kit import build_preflight, write_submission_kit

    run_dir = find_latest_run(grant_id)
    if run_dir is None:
        raise FileNotFoundError(f"no grant run found for '{grant_id}'")
    preflight = build_preflight(grant_id, run_dir, catalog_entry)
    if not dry_run:
        if force or not (run_dir / "submission_packet.json").exists():
            write_submission_kit(grant_id, run_dir, preflight)
    return preflight


def mark_submitted_csv(csv_path: Path, dry_run: bool) -> list[dict[str, Any]]:
    rows = load_csv(csv_path)
    results: list[dict[str, Any]] = []
    for row in rows:
        grant_id = (row.get("grant_id") or "").strip()
        submitted_by = row.get("submitted_by") or row.get("submitted-by")
        external_tracking_id = row.get("external_tracking_id") or row.get("external-tracking-id")
        notes = row.get("notes")
        if not grant_id:
            results.append({"grant_id": None, "error": "missing grant_id"})
            continue
        try:
            state = mark_submitted(grant_id, submitted_by, external_tracking_id, notes, dry_run)
            results.append({"grant_id": grant_id, "status": "submitted", "state": state})
        except Exception as exc:
            results.append({"grant_id": grant_id, "error": str(exc)})
    return results


def mark_submitted(grant_id: str, submitted_by: str | None, external_tracking_id: str | None,
                   notes: str | None, dry_run: bool) -> dict[str, Any]:
    if not submitted_by or not external_tracking_id:
        raise ValueError("submitted_by and external_tracking_id are required")
    run_dir = find_latest_run(grant_id)
    if run_dir is None:
        raise FileNotFoundError(f"no grant run found for '{grant_id}'")
    state_path = run_dir / "approval_state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"approval_state.json missing for '{grant_id}'")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("state") not in ("approved", "submitted"):
        raise ValueError(f"grant must be approved before marking submitted (state={state.get('state')})")
    state["state"] = "submitted"
    state["submitted_utc"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    state["submitted_by"] = submitted_by
    state["external_tracking_id"] = external_tracking_id
    if notes is not None:
        state["notes"] = notes
    if not dry_run:
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        sys.path.insert(0, str(ROOT / "code"))
        from grant_application_factory import update_queue

        update_queue()
    return state


def gather_approved_items(queue: dict[str, Any], limit: int | None = None) -> list[dict[str, Any]]:
    approved = [it for it in queue.get("items", []) if str(it.get("state") or "").lower() == "approved"]
    if limit is not None:
        return approved[:limit]
    return approved


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "generated_utc": now_tag(),
        "n_approved": len(rows),
        "n_ready": sum(1 for r in rows if r.get("ready") is True),
        "n_blocked": sum(1 for r in rows if r.get("ready") is False),
        "n_errors": sum(1 for r in rows if r.get("error")),
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch prepare approved grants for submission and optionally record tracking IDs."
    )
    parser.add_argument("--prepare-approved", action="store_true",
                        help="Generate submission_packet.json and SUBMIT_HOWTO.md for every approved grant.")
    parser.add_argument("--export-csv", action="store_true",
                        help="Export approved grant status to a CSV after optionally preparing submission kits.")
    parser.add_argument("--mark-submitted-csv",
                        help="CSV file with grant_id,submitted_by,external_tracking_id,notes to mark grants submitted.")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate submission packets even if they already exist.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview actions without writing files.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit the number of approved grants processed.")
    args = parser.parse_args()

    if not (args.prepare_approved or args.export_csv or args.mark_submitted_csv):
        parser.error("Provide at least one of --prepare-approved, --export-csv, or --mark-submitted-csv")

    if args.mark_submitted_csv:
        results = mark_submitted_csv(Path(args.mark_submitted_csv), args.dry_run)
        output = {
            "generated_utc": now_tag(),
            "dry_run": args.dry_run,
            "results": results,
        }
        print(json.dumps(output, indent=2))
        return 0

    queue = load_queue()
    approved_items = gather_approved_items(queue, limit=args.limit)
    processed_rows: list[dict[str, Any]] = []
    for item in approved_items:
        grant_id = str(item.get("program_id") or "")
        if not grant_id:
            continue
        try:
            preflight = prepare_submission(grant_id, item, args.force, args.dry_run) if args.prepare_approved else build_status(grant_id, item)
            row = {
                "grant_id": grant_id,
                "agency": preflight.get("agency"),
                "program": preflight.get("program"),
                "approval_state": preflight.get("approval_state"),
                "ready": preflight.get("ready"),
                "ceiling_usd": preflight.get("ceiling_usd"),
                "deadline": preflight.get("deadline", {}).get("deadline"),
                "blockers": "; ".join(preflight.get("blockers", [])),
                "submission_system": preflight.get("portal", {}).get("submission_system"),
                "portal_url": preflight.get("portal", {}).get("portal_url"),
                "submission_packet_written": bool(args.prepare_approved and not args.dry_run),
            }
            processed_rows.append(row)
        except Exception as exc:
            processed_rows.append({
                "grant_id": grant_id,
                "error": str(exc),
            })
    summary = summarize_rows(processed_rows)
    if args.export_csv and not args.dry_run:
        OUT_OPS_BATCH.mkdir(parents=True, exist_ok=True)
        csv_path = OUT_OPS_BATCH / f"approved_grants_submission_ready_{now_tag()}.csv"
        fieldnames = [
            "grant_id", "agency", "program", "approval_state", "ready",
            "ceiling_usd", "deadline", "submission_system", "portal_url",
            "blockers", "submission_packet_written", "error"
        ]
        write_csv(csv_path, processed_rows, fieldnames)
        summary["csv_path"] = str(csv_path)
        write_json(OUT_OPS_BATCH / f"approved_grants_submission_ready_{now_tag()}.json", {
            "summary": summary,
            "items": processed_rows,
        })
    elif args.export_csv and args.dry_run:
        summary["note"] = "dry-run; no files written"

    print(json.dumps(summary, indent=2))
    return 0

    return 0


def build_status(grant_id: str, catalog_entry: dict | None) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "code"))
    from grant_submission_kit import build_preflight

    run_dir = find_latest_run(grant_id)
    if run_dir is None:
        raise FileNotFoundError(f"no grant run found for '{grant_id}'")
    return build_preflight(grant_id, run_dir, catalog_entry)


if __name__ == "__main__":
    raise SystemExit(main())
