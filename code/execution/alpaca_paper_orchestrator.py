from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from execution.alpaca_paper_executor import AlpacaPaperClient, load_api_keys, load_json
from execution.audit_chain import AuditChain, sha256_file

CONFIG = ROOT / "config"
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"

PAPER_RUNTIME_FILE = CONFIG / "paper_trader_runtime.json"
ORCH_STATUS_FILE = EXEC_OUT / "alpaca_orchestrator_status.json"
ORCH_AUDIT_CHAIN_FILE = EXEC_OUT / "alpaca_orchestrator_audit_chain.jsonl"
RANKED_SYMBOL_AGENTS_FILE = EXEC_OUT / "alpaca_symbol_ranked.json"
LIVE_SYNC_STATE_FILE = EXEC_OUT / "live_sync_last.json"

SYMBOL_AGENT_SCRIPT = ROOT / "code" / "execution" / "alpaca_symbol_agents.py"
EXECUTOR_SCRIPT = ROOT / "code" / "execution" / "alpaca_paper_executor.py"

DEFAULT_PROOF_FILES = [
    ORCH_STATUS_FILE,
    ORCH_AUDIT_CHAIN_FILE,
    ROOT / "infra_frozen_deltas.jsonl",
    ROOT / "CHAIN_OF_CUSTODY_SHA256.json",
    ROOT / "CHAIN_OF_CUSTODY_256.txt",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    except Exception:
        return {}
    return values


def _is_http_url(value: str) -> bool:
    txt = str(value or "").strip()
    return txt.startswith("http://") or txt.startswith("https://")


def resolve_live_sync_settings() -> dict[str, Any]:
    runtime = load_json(CONFIG / "runtime_control.json", {})
    env = load_env_file(CONFIG / "luma_live_keys.env")

    url = str(runtime.get("live_sync_webhook_url", "") or "").strip()
    token = str(runtime.get("live_sync_auth_bearer", "") or "").strip()
    timeout_sec = float(runtime.get("live_sync_timeout_sec", 8.0) or 8.0)

    if not _is_http_url(url):
        env_url = str(env.get("LUMA_LIVE_SYNC_WEBHOOK", "") or env.get("LIVE_SYNC_WEBHOOK_URL", "")).strip()
        if _is_http_url(env_url):
            url = env_url

    if not token:
        token = str(env.get("LUMA_LIVE_SYNC_BEARER", "") or env.get("LIVE_SYNC_AUTH_BEARER", "") or env.get("WEBHOOK_SHARED_SECRET", "")).strip()

    enabled = bool(runtime.get("live_sync_enabled", False)) and _is_http_url(url)

    include_files_raw = runtime.get("live_sync_include_files", [])
    include_files: list[Path] = []
    if isinstance(include_files_raw, list):
        for raw in include_files_raw:
            txt = str(raw or "").strip()
            if not txt:
                continue
            p = Path(txt)
            include_files.append(p if p.is_absolute() else ROOT / p)

    return {
        "enabled": enabled,
        "url": url,
        "token": token,
        "timeout_sec": max(1.0, timeout_sec),
        "include_files": include_files,
    }


def build_proof_manifest(extra_files: list[Path] | None = None) -> list[dict[str, Any]]:
    files = list(DEFAULT_PROOF_FILES)
    if extra_files:
        files.extend(extra_files)

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in files:
        p = Path(path)
        key = str(p).lower()
        if key in seen:
            continue
        seen.add(key)
        if not p.exists() or not p.is_file():
            continue
        try:
            out.append(
                {
                    "path": str(p),
                    "size_bytes": int(p.stat().st_size),
                    "sha256": sha256_file(p),
                    "mtime_utc": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(),
                }
            )
        except Exception:
            continue
    return out


def publish_live_sync(status: dict[str, Any], audit: AuditChain) -> dict[str, Any]:
    settings = resolve_live_sync_settings()
    if not settings.get("enabled", False):
        result = {"attempted": False, "ok": False, "reason": "live_sync_disabled"}
        write_json(LIVE_SYNC_STATE_FILE, {"generated_utc": now_utc(), **result})
        return result

    payload = {
        "event_type": "alpaca_orchestrator_live_cycle",
        "generated_utc": now_utc(),
        "service": "alpaca_paper_orchestrator",
        "status": status,
        "proof_manifest": build_proof_manifest(settings.get("include_files", [])),
    }

    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if settings.get("token"):
        headers["Authorization"] = f"Bearer {settings['token']}"

    req = request.Request(str(settings["url"]), data=body, method="POST", headers=headers)
    start = time.time()
    try:
        with request.urlopen(req, timeout=float(settings["timeout_sec"])) as resp:
            resp_body = resp.read().decode("utf-8", errors="replace")
            latency_ms = round((time.time() - start) * 1000.0, 2)
            result = {
                "attempted": True,
                "ok": 200 <= int(resp.status) < 300,
                "status_code": int(resp.status),
                "latency_ms": latency_ms,
                "reason": "ok" if 200 <= int(resp.status) < 300 else f"http_{int(resp.status)}",
                "response_excerpt": resp_body[:240],
                "proof_count": len(payload["proof_manifest"]),
            }
    except error.HTTPError as http_err:
        err_body = http_err.read().decode("utf-8", errors="replace")
        result = {
            "attempted": True,
            "ok": False,
            "status_code": int(http_err.code),
            "latency_ms": round((time.time() - start) * 1000.0, 2),
            "reason": f"http_{int(http_err.code)}",
            "response_excerpt": err_body[:240],
            "proof_count": len(payload["proof_manifest"]),
        }
    except Exception as exc:
        result = {
            "attempted": True,
            "ok": False,
            "reason": f"exception:{type(exc).__name__}",
            "latency_ms": round((time.time() - start) * 1000.0, 2),
            "response_excerpt": str(exc)[:240],
            "proof_count": len(payload["proof_manifest"]),
        }

    write_json(
        LIVE_SYNC_STATE_FILE,
        {
            "generated_utc": now_utc(),
            "url": settings.get("url", ""),
            "result": result,
        },
    )

    audit.append(
        event_type="alpaca_orchestrator_live_sync",
        payload={
            "url": settings.get("url", ""),
            "result": result,
        },
    )
    return result


def run_script(path: Path, args: list[str]) -> tuple[int, str]:
    cmd = [sys.executable, str(path), *args]
    proc = subprocess.run(cmd, cwd=str(ROOT / "code"), capture_output=True, text=True)
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, output.strip()


def update_runtime_symbols_from_agents(top_n: int) -> dict[str, Any]:
    runtime = load_json(PAPER_RUNTIME_FILE, {})
    ranked = load_json(RANKED_SYMBOL_AGENTS_FILE, {})

    top_agents = ranked.get("top_agents", []) if isinstance(ranked, dict) else []
    candidates = [
        a for a in top_agents if isinstance(a, dict) and bool(a.get("execution_ready", False))
    ]
    symbols = []
    seen = set()
    for row in candidates:
        sym = str(row.get("symbol", "")).upper().strip()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        symbols.append(sym)
        if len(symbols) >= max(5, int(top_n)):
            break

    runtime["generated_utc"] = now_utc()
    runtime["symbol_mode"] = "AGENT_RANKED"
    runtime["selection_source"] = "alpaca_paper_orchestrator"
    runtime["symbols"] = symbols
    runtime["symbol_count"] = len(symbols)
    runtime["agents_ranked_file"] = str(RANKED_SYMBOL_AGENTS_FILE)
    write_json(PAPER_RUNTIME_FILE, runtime)

    return {
        "selected_symbols": symbols,
        "selected_count": len(symbols),
        "source_top_agents": len(top_agents),
        "agent_universe_total": int(ranked.get("universe_total", 0) or 0),
        "agent_scanned_symbols": int(ranked.get("scanned_symbols", 0) or 0),
        "agent_scan_window_start": int(ranked.get("scan_window_start", 0) or 0),
        "agent_scan_window_next": int(ranked.get("scan_window_next", 0) or 0),
    }


def orchestrate_once(max_symbols: int, top_n: int, no_orders: bool, status_only_when_closed: bool, audit: AuditChain) -> dict[str, Any]:
    keys = load_api_keys()
    client = AlpacaPaperClient(
        keys.get("ALPACA_API_KEY", ""),
        keys.get("ALPACA_API_SECRET", ""),
        trading_base=keys.get("ALPACA_PAPER_BASE_URL", ""),
        data_base=keys.get("ALPACA_DATA_BASE_URL", ""),
    )
    if not client.is_configured():
        raise RuntimeError("Missing Alpaca API keys")

    clock = client.get_clock()
    is_open = bool(clock.get("is_open"))
    next_open = str(clock.get("next_open") or "")
    next_close = str(clock.get("next_close") or "")

    rc_agents, out_agents = run_script(SYMBOL_AGENT_SCRIPT, ["--max-symbols", str(max_symbols)])
    if rc_agents != 0:
        raise RuntimeError(f"symbol_agents_failed rc={rc_agents}: {out_agents[:600]}")

    symbol_selection = update_runtime_symbols_from_agents(top_n=top_n)

    exec_args: list[str] = []
    if no_orders:
        exec_args.append("--no-orders")
    elif status_only_when_closed and (not is_open):
        exec_args.append("--status-only")

    rc_exec, out_exec = run_script(EXECUTOR_SCRIPT, exec_args)

    status = {
        "generated_utc": now_utc(),
        "market_open": is_open,
        "next_open_utc": next_open,
        "next_close_utc": next_close,
        "symbol_agent": {
            "rc": rc_agents,
            "max_symbols": max_symbols,
        },
        "runtime_symbol_selection": symbol_selection,
        "executor": {
            "rc": rc_exec,
            "args": exec_args,
            "output_tail": out_exec[-1500:],
        },
        "status": "ok" if rc_exec == 0 else "executor_error",
    }

    status["live_sync"] = publish_live_sync(status, audit)
    write_json(ORCH_STATUS_FILE, status)

    audit.append(
        event_type="alpaca_paper_orchestrator_cycle",
        payload={
            "market_open": is_open,
            "selected_count": symbol_selection.get("selected_count", 0),
            "agent_universe_total": symbol_selection.get("agent_universe_total", 0),
            "agent_scanned_symbols": symbol_selection.get("agent_scanned_symbols", 0),
            "agent_scan_window_start": symbol_selection.get("agent_scan_window_start", 0),
            "agent_scan_window_next": symbol_selection.get("agent_scan_window_next", 0),
            "executor_rc": rc_exec,
            "executor_args": exec_args,
            "next_open_utc": next_open,
            "next_close_utc": next_close,
            "status": status["status"],
        },
    )

    return status


_LOCK_FILE = ROOT / "run" / "alpaca_paper_orchestrator.lock"


def _acquire_singleton_lock() -> None:
    """Prevent duplicate instances. Exits 0 immediately if this script is already running."""
    import atexit
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _LOCK_FILE.exists():
        try:
            pid = int(_LOCK_FILE.read_text().strip())
            if pid != os.getpid():
                os.kill(pid, 0)  # raises OSError if process is gone
                print(f"[singleton] alpaca_paper_orchestrator already running as PID {pid} — exiting.", flush=True)
                raise SystemExit(0)
        except (ValueError, OSError):
            pass  # stale lock
    _LOCK_FILE.write_text(str(os.getpid()))
    atexit.register(lambda: _LOCK_FILE.unlink(missing_ok=True))


def main() -> int:
    _acquire_singleton_lock()
    parser = argparse.ArgumentParser(description="Dedicated Alpaca paper orchestrator + symbol agents + executor handoff")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval-sec", type=int, default=60, help="Loop interval")
    parser.add_argument("--max-symbols", type=int, default=5000, help="Symbols scanned by symbol agents")
    parser.add_argument("--top-n", type=int, default=300, help="Top execution-ready symbols passed to executor")
    parser.add_argument("--no-orders", action="store_true", help="Never place orders; analytics only")
    parser.add_argument(
        "--status-only-when-closed",
        action="store_true",
        help="Run executor in --status-only mode when market is closed",
    )
    args = parser.parse_args()

    audit = AuditChain(ORCH_AUDIT_CHAIN_FILE)

    while True:
        try:
            status = orchestrate_once(
                max_symbols=max(20, int(args.max_symbols)),
                top_n=max(5, int(args.top_n)),
                no_orders=bool(args.no_orders),
                status_only_when_closed=bool(args.status_only_when_closed),
                audit=audit,
            )
        except Exception as exc:
            status = {
                "generated_utc": now_utc(),
                "status": "error",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            write_json(ORCH_STATUS_FILE, status)
            audit.append(
                event_type="alpaca_paper_orchestrator_error",
                payload={
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )

        print(json.dumps(status, indent=2))

        if not args.loop:
            break
        time.sleep(max(5, int(args.interval_sec)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
