from __future__ import annotations

import atexit
import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
OUT_EXEC = ROOT / "out" / "execution"
DEFAULT_LOG_FILE = OUT_EXEC / "approval_autofire_log.jsonl"
DEFAULT_STATE_FILE = OUT_EXEC / "approval_autofire_state.json"
LOCK_FILE = OUT_EXEC / "approval_autofire_daemon.lock"
LOCK_STALE_SEC = 6 * 60 * 60


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_utc(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def request_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None, timeout: int = 20) -> dict[str, Any]:
    headers: dict[str, str] = {}
    data: bytes | None = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    req = Request(url=url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            parsed = json.loads(body)
            return parsed if isinstance(parsed, dict) else {"status": "bad_response", "body": parsed}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body[:800]}
        return {"status": "http_error", "code": exc.code, "error": parsed}
    except URLError as exc:
        return {"status": "network_error", "error": str(exc)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def load_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("seen_ticket_ids") if isinstance(payload, dict) else []
        if isinstance(rows, list):
            return {str(x).strip() for x in rows if str(x).strip()}
    except Exception:
        pass
    return set()


def save_seen(path: Path, seen: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_utc": now_utc(),
        "schema": "approval_autofire_state_v1",
        "seen_ticket_ids": sorted(seen),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _release_lock() -> None:
    if not LOCK_FILE.exists():
        return
    try:
        payload = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        owner_pid = int(payload.get("pid", 0) or 0)
    except Exception:
        owner_pid = 0
    if owner_pid and owner_pid != os.getpid():
        return
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        probe = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        out = (probe.stdout or "").strip()
        if not out:
            return False
        if "No tasks are running" in out:
            return False
        return f",\"{pid}\"," in out or out.startswith(f"\"python.exe\",\"{pid}\",")
    except Exception:
        return False


def _acquire_lock(log_file: Path) -> bool:
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

    if LOCK_FILE.exists():
        try:
            payload = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
            owner_pid = int(payload.get("pid", 0) or 0)
        except Exception:
            owner_pid = 0
        try:
            age_sec = max(0.0, time.time() - LOCK_FILE.stat().st_mtime)
        except Exception:
            age_sec = 0.0

        if owner_pid > 0 and _pid_running(owner_pid):
            append_jsonl(
                log_file,
                {
                    "ts": now_utc(),
                    "event": "daemon_lock_active_exit",
                    "lock_file": str(LOCK_FILE),
                    "lock_age_sec": round(age_sec, 3),
                    "owner_pid": owner_pid,
                },
            )
            print(
                "[APPROVAL-AUTOFIRE] lock already active; exiting duplicate process"
                + f" lock={LOCK_FILE} owner_pid={owner_pid} age_sec={age_sec:.1f}",
                flush=True,
            )
            return False

        if age_sec > LOCK_STALE_SEC:
            try:
                LOCK_FILE.unlink(missing_ok=True)
            except Exception:
                pass
        else:
            # Lock exists but owner process is gone; clear stale lock immediately.
            try:
                LOCK_FILE.unlink(missing_ok=True)
            except Exception:
                pass

    payload = {
        "pid": os.getpid(),
        "created_utc": now_utc(),
        "lock_file": str(LOCK_FILE),
    }
    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        return True
    except FileExistsError:
        return False
    except Exception:
        return False


def eligible_ticket(
    ticket: dict[str, Any],
    controller: str,
    started_at: datetime,
    include_existing: bool,
) -> bool:
    if str(ticket.get("approval_state", "")).upper() != "PENDING_HUMAN_APPROVAL":
        return False
    if not bool(ticket.get("guards_pass_all", False)):
        return False

    ticket_controller = str(ticket.get("controller", "")).strip()
    if ticket_controller != controller:
        return False

    if include_existing:
        return True

    ts = parse_utc(ticket.get("timestamp"))
    if ts is None:
        return False
    return ts >= started_at


def build_decide_payload(ticket_id: str, controller: str) -> dict[str, Any]:
    return {
        "ticket_id": ticket_id,
        "decision": "approve",
        "controller": controller,
        "reason": "approval_autofire_daemon",
        "confirm_phrase": f"FIRE {ticket_id}",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Continuously auto-approve eligible pending tickets.")
    ap.add_argument("--gateway-url", default="http://127.0.0.1:8787")
    ap.add_argument("--controller", default="Robert")
    ap.add_argument("--interval-sec", type=int, default=8)
    ap.add_argument("--include-existing", action="store_true", help="Also process pending tickets that existed before daemon start.")
    ap.add_argument("--log-file", default=str(DEFAULT_LOG_FILE))
    ap.add_argument("--state-file", default=str(DEFAULT_STATE_FILE))
    args = ap.parse_args()

    gateway_url = str(args.gateway_url).rstrip("/")
    controller = str(args.controller).strip()
    interval_sec = max(2, int(args.interval_sec))
    log_file = Path(args.log_file)
    state_file = Path(args.state_file)

    if not _acquire_lock(log_file):
        return 0
    atexit.register(_release_lock)

    started_at = datetime.now(timezone.utc)
    seen = load_seen(state_file)

    append_jsonl(
        log_file,
        {
            "ts": now_utc(),
            "event": "daemon_start",
            "gateway_url": gateway_url,
            "controller": controller,
            "include_existing": bool(args.include_existing),
            "interval_sec": interval_sec,
            "seen_count": len(seen),
        },
    )

    print(
        "[APPROVAL-AUTOFIRE] started"
        + f" gateway={gateway_url}"
        + f" controller={controller}"
        + f" include_existing={bool(args.include_existing)}"
        + f" interval={interval_sec}s",
        flush=True,
    )

    final_statuses = {"executed", "rejected", "blocked", "error"}

    while True:
        queue_payload = request_json(f"{gateway_url}/api/master/approval-queue")
        tickets = queue_payload.get("tickets") if isinstance(queue_payload, dict) else None
        if not isinstance(tickets, list):
            append_jsonl(
                log_file,
                {
                    "ts": now_utc(),
                    "event": "queue_read_error",
                    "payload": queue_payload,
                },
            )
            time.sleep(interval_sec)
            continue

        candidates: list[tuple[datetime, dict[str, Any]]] = []
        for ticket in tickets:
            if not isinstance(ticket, dict):
                continue
            tid = str(ticket.get("ticket_id", "")).strip()
            if not tid or tid in seen:
                continue
            if not eligible_ticket(ticket, controller, started_at, bool(args.include_existing)):
                continue
            ts = parse_utc(ticket.get("timestamp")) or datetime.max.replace(tzinfo=timezone.utc)
            candidates.append((ts, ticket))

        candidates.sort(key=lambda row: row[0])
        state_changed = False

        for _, ticket in candidates:
            tid = str(ticket.get("ticket_id", "")).strip()
            if not tid:
                continue

            payload = build_decide_payload(tid, controller)
            result = request_json(
                f"{gateway_url}/api/master/approval/decide",
                method="POST",
                payload=payload,
            )
            status = str(result.get("status", "unknown")) if isinstance(result, dict) else "unknown"
            txid = result.get("txid") if isinstance(result, dict) else None

            append_jsonl(
                log_file,
                {
                    "ts": now_utc(),
                    "event": "approve_attempt",
                    "ticket_id": tid,
                    "pair": ticket.get("pair"),
                    "side": ticket.get("side"),
                    "notional_usd": ticket.get("notional_usd"),
                    "status": status,
                    "txid": txid,
                    "result": result,
                },
            )

            if status in final_statuses:
                seen.add(tid)
                state_changed = True

            print(
                "[APPROVAL-AUTOFIRE]"
                + f" ticket={tid}"
                + f" pair={ticket.get('pair')}"
                + f" side={ticket.get('side')}"
                + f" status={status}",
                flush=True,
            )

        if state_changed:
            save_seen(state_file, seen)

        time.sleep(interval_sec)


if __name__ == "__main__":
    raise SystemExit(main())
