from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_GRANTS = ROOT / "out" / "grants"


def find_latest_run(grant_id: str) -> Path | None:
    grant_dir = OUT_GRANTS / grant_id
    if not grant_dir.exists():
        return None
    runs = [p for p in grant_dir.iterdir() if p.is_dir()]
    if not runs:
        return None
    return max(runs, key=lambda p: p.name)


def load_state(run_dir: Path) -> dict:
    state_path = run_dir / "approval_state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"approval_state.json not found in {run_dir}")
    return json.loads(state_path.read_text(encoding="utf-8"))


def write_state(run_dir: Path, state: dict) -> None:
    state_path = run_dir / "approval_state.json"
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def mark_submitted(grant_id: str, submitted_by: str, external_tracking_id: str, notes: str | None = None) -> dict:
    run_dir = find_latest_run(grant_id)
    if run_dir is None:
        raise FileNotFoundError(f"No grant run found for '{grant_id}'")

    state = load_state(run_dir)
    if state.get("state") not in ("approved", "submitted"):
        raise ValueError(f"grant must be approved before marking submitted (current state={state.get('state')})")

    state["state"] = "submitted"
    state["submitted_utc"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    state["submitted_by"] = submitted_by
    state["external_tracking_id"] = external_tracking_id
    if notes is not None:
        state["notes"] = notes

    write_state(run_dir, state)

    sys.path.insert(0, str(ROOT / "code"))
    from grant_application_factory import update_queue

    queue = update_queue()
    return {"grant_id": grant_id, "run_dir": str(run_dir), "state": state, "queue": queue}


def load_csv(csv_path: Path) -> list[dict[str, str | None]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    rows: list[dict[str, str | None]] = []
    header = None
    with csv_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if header is None:
                header = [p.lower() for p in parts]
                continue
            entry = {header[i]: parts[i] if i < len(parts) and parts[i] else None
                     for i in range(len(header))}
            rows.append(entry)
    return rows


def mark_submitted_batch(entries: list[dict[str, str | None]], dry_run: bool = False) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for entry in entries:
        grant_id = str(entry.get("grant_id") or "").strip()
        submitted_by = entry.get("submitted_by") or entry.get("submitted-by")
        external_tracking_id = entry.get("external_tracking_id") or entry.get("external-tracking-id")
        notes = entry.get("notes")
        if not grant_id:
            results.append({"grant_id": None, "error": "missing grant_id"})
            continue
        try:
            if dry_run:
                run_dir = find_latest_run(grant_id)
                if run_dir is None:
                    raise FileNotFoundError(f"No grant run found for '{grant_id}'")
                state = load_state(run_dir)
                results.append({"grant_id": grant_id, "dry_run": True, "run_dir": str(run_dir), "state": state})
                continue
            if not submitted_by or not external_tracking_id:
                raise ValueError("submitted_by and external_tracking_id are required for each entry")
            result = mark_submitted(grant_id, submitted_by, external_tracking_id, notes)
            results.append({"grant_id": grant_id, "run_dir": result["run_dir"], "state": result["state"]})
        except Exception as exc:
            results.append({"grant_id": grant_id, "error": str(exc)})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Mark one or more grant packages as submitted in the local grant queue.")
    parser.add_argument("grant_id", nargs="*", help="Grant identifier(s), e.g. doe_sbir_phase_i_25_2")
    parser.add_argument("--csv", help="CSV file with header row: grant_id,submitted_by,external_tracking_id,notes")
    parser.add_argument("--submitted-by", help="Name of the submitter / AOR for positional grant IDs")
    parser.add_argument("--external-tracking-id", help="Grants.gov or agency tracking number for positional grant IDs")
    parser.add_argument("--notes", default=None, help="Optional notes to attach to the submission state for positional grant IDs")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without writing files")
    args = parser.parse_args()

    try:
        entries: list[dict[str, str | None]] = []
        if args.csv:
            entries = load_csv(Path(args.csv))
            if args.grant_id:
                raise ValueError("Cannot use positional grant_id arguments with --csv")
        elif args.grant_id:
            if len(args.grant_id) == 0:
                raise ValueError("At least one grant_id is required")
            for grant_id in args.grant_id:
                entries.append({
                    "grant_id": grant_id,
                    "submitted_by": args.submitted_by,
                    "external_tracking_id": args.external_tracking_id,
                    "notes": args.notes,
                })
        else:
            raise ValueError("Provide either one or more grant_id values or --csv")

        results = mark_submitted_batch(entries, dry_run=args.dry_run)
        print(json.dumps(results, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
