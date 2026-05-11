from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
PY = ROOT / ".venv" / "Scripts" / "python.exe"
MESH = ROOT / "code" / "execution" / "premium_package_mesh.py"
AUDIT = ROOT / "code" / "audit_and_leverage_packages.py"
OUT = ROOT / "out" / "execution"
HEARTBEAT = OUT / "premium_mesh_supervisor_heartbeat.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_heartbeat(state: str, detail: str = "", rc: int | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_utc": now_utc(),
        "state": state,
        "detail": detail,
        "return_code": rc,
        "mesh_script": str(MESH),
        "audit_script": str(AUDIT),
    }
    HEARTBEAT.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_cmd(args: list[str], env: dict[str, str] | None = None) -> tuple[int, str]:
    proc = subprocess.run(args, cwd=str(ROOT), env=env, capture_output=True, text=True)
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, out.strip()


def loop(interval_sec: int) -> int:
    while True:
        write_heartbeat("running", "starting mesh pass")

        rc1, out1 = run_cmd([str(PY), str(MESH), "--max-packages", "228"])
        if rc1 != 0:
            write_heartbeat("error", f"mesh failed: {out1[:1600]}", rc1)
            time.sleep(max(interval_sec, 60))
            continue

        env = os.environ.copy()
        env["PACKAGE_AUDIT_OFFLINE"] = "1"
        rc2, out2 = run_cmd([str(PY), str(AUDIT)], env=env)
        if rc2 != 0:
            write_heartbeat("error", f"audit failed: {out2[:1600]}", rc2)
            time.sleep(max(interval_sec, 60))
            continue

        write_heartbeat("ok", "mesh + audit refreshed")
        time.sleep(max(interval_sec, 60))


def main(argv: list[str]) -> int:
    interval = 300
    if argv:
        try:
            interval = int(argv[0])
        except Exception:
            interval = 300
    write_heartbeat("starting", f"interval={interval}s")
    return loop(interval)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
