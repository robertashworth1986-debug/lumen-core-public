from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
EXEC_OUT = ROOT / "out" / "execution"

PY = ROOT / ".venv" / "Scripts" / "python.exe"
PREMIUM_SUPERVISOR = CODE / "execution" / "premium_mesh_supervisor.py"
SECTOR_CLOCK = CODE / "execution" / "sector_clock_beater.py"
BEEFY_SIMS = CODE / "execution" / "broader_beefier_sims.py"
PACKAGE_AUDIT = CODE / "audit_and_leverage_packages.py"
TUNNEL_SCRIPT = CODE / "RUN_PUBLIC_DASHBOARD_TUNNEL.ps1"

PREMIUM_HEARTBEAT = EXEC_OUT / "premium_mesh_supervisor_heartbeat.json"
PACKAGE_LEVERAGE = EXEC_OUT / "package_leverage_audit.json"
SECTOR_CLOCK_FILE = EXEC_OUT / "sector_clock_beater.json"
BEEFY_SIMS_FILE = EXEC_OUT / "broader_beefier_sims.json"
TUNNEL_STATUS = EXEC_OUT / "public_dashboard_tunnel_status.json"
AUTOPILOT_HEARTBEAT = EXEC_OUT / "innovation_autopilot_heartbeat.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def age_seconds(generated_utc: str | None) -> float:
    if not generated_utc:
        return float("inf")
    txt = str(generated_utc).strip().replace("Z", "+00:00")
    try:
        ts = datetime.fromisoformat(txt)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return max((datetime.now(timezone.utc) - ts).total_seconds(), 0.0)
    except Exception:
        return float("inf")


def run_detached(cmd: list[str]) -> None:
    subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )


def run_once() -> dict[str, Any]:
    actions: list[dict[str, Any]] = []

    premium = load_json(PREMIUM_HEARTBEAT, {})
    premium_age = age_seconds(premium.get("generated_utc") if isinstance(premium, dict) else None)
    if premium_age > 900:
        run_detached([str(PY), str(PREMIUM_SUPERVISOR), "300"])
        actions.append({"action": "restart_premium_supervisor", "reason": f"stale:{premium_age:.1f}s"})

    leverage = load_json(PACKAGE_LEVERAGE, {})
    leverage_age = age_seconds(leverage.get("generated_utc") if isinstance(leverage, dict) else None)
    if leverage_age > 900:
        env = os.environ.copy()
        env["PACKAGE_AUDIT_OFFLINE"] = "1"
        subprocess.run([str(PY), str(PACKAGE_AUDIT)], cwd=str(ROOT), env=env, capture_output=True, text=True)
        actions.append({"action": "refresh_package_leverage", "reason": f"stale:{leverage_age:.1f}s"})

    sector = load_json(SECTOR_CLOCK_FILE, {})
    sector_age = age_seconds(sector.get("generated_utc") if isinstance(sector, dict) else None)
    if sector_age > 180:
        subprocess.run([str(PY), str(SECTOR_CLOCK)], cwd=str(ROOT), capture_output=True, text=True)
        actions.append({"action": "refresh_sector_clock", "reason": f"stale:{sector_age:.1f}s"})

    beefy = load_json(BEEFY_SIMS_FILE, {})
    beefy_age = age_seconds(beefy.get("generated_utc") if isinstance(beefy, dict) else None)
    if beefy_age > 300:
        workers = max((os.cpu_count() or 8) - 2, 2)
        run_detached([
            str(PY),
            str(BEEFY_SIMS),
            "--loop",
            "--interval",
            "120",
            "--workers",
            str(workers),
            "--rounds",
            "8",
            "--gbm-paths",
            "20000",
            "--matrix-dim",
            "220",
            "--graph-nodes",
            "1200",
        ])
        actions.append({"action": "restart_beefy_sims", "reason": f"stale:{beefy_age:.1f}s"})

    tunnel = load_json(TUNNEL_STATUS, {})
    tunnel_state = str(tunnel.get("state", "unknown")).lower() if isinstance(tunnel, dict) else "unknown"
    tunnel_age = age_seconds(tunnel.get("generated_utc") if isinstance(tunnel, dict) else None)
    if tunnel_state in {"failed", "pending", "unknown"} or tunnel_age > 600:
        if TUNNEL_SCRIPT.exists():
            run_detached([
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(TUNNEL_SCRIPT),
            ])
            actions.append({
                "action": "restart_public_tunnel",
                "reason": f"state={tunnel_state},age={tunnel_age:.1f}s",
            })

    payload = {
        "generated_utc": now_utc(),
        "schema": "innovation_autopilot_v1",
        "premium_heartbeat_age_sec": round(premium_age, 2),
        "leverage_age_sec": round(leverage_age, 2),
        "sector_clock_age_sec": round(sector_age, 2),
        "beefy_sims_age_sec": round(beefy_age, 2),
        "tunnel_state": tunnel_state,
        "tunnel_age_sec": round(tunnel_age, 2),
        "actions": actions,
        "action_count": len(actions),
    }

    EXEC_OUT.mkdir(parents=True, exist_ok=True)
    AUTOPILOT_HEARTBEAT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main(argv: list[str]) -> int:
    interval = 60
    if argv:
        try:
            interval = int(argv[0])
        except Exception:
            interval = 60

    while True:
        out = run_once()
        print(json.dumps({
            "ts": out["generated_utc"],
            "actions": out["action_count"],
            "tunnel": out["tunnel_state"],
            "sector_age": out["sector_clock_age_sec"],
        }, indent=2))
        time.sleep(max(interval, 30))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
