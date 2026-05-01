import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
LAMA_ROOT = ROOT.parent / "LamaScout"
LAMA_SRC = LAMA_ROOT / "src"


def ensure_lama_paths():
    sys.path.insert(0, str(LAMA_ROOT))
    sys.path.insert(0, str(LAMA_SRC))


def run_pipeline() -> None:
    ensure_lama_paths()
    from src.artist_scout_engine import main as run_main

    run_main()


def serve_api(host: str = "0.0.0.0", port: int = 8000, reload: bool = True) -> subprocess.Popen:
    ensure_lama_paths()
    cmd = [sys.executable, "-m", "uvicorn", "src.dashboard_api:app", "--host", host, "--port", str(port)]
    if reload:
        cmd.append("--reload")
    return subprocess.Popen(cmd, cwd=str(LAMA_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def health_check(host: str = "127.0.0.1", port: int = 8000, attempts: int = 15, sleep: int = 2) -> bool:
    url = f"http://{host}:{port}/health"
    for _ in range(attempts):
        try:
            response = requests.get(url, timeout=5)
            if response.ok and response.json().get("status") == "ok":
                return True
        except Exception:
            pass
        time.sleep(sleep)
    return False


def sync_outputs(target: Path | None = None) -> None:
    target = target or ROOT / "out" / "lumascout"
    target.mkdir(parents=True, exist_ok=True)
    for src_dir_name in ("out", "reports"):
        src_dir = LAMA_ROOT / src_dir_name
        if not src_dir.exists():
            continue
        dest_dir = target / src_dir_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        for item in src_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, dest_dir / item.name)


def main():
    parser = argparse.ArgumentParser(description="LumaScout integration helper for the root code workspace.")
    parser.add_argument("--run", action="store_true", help="Run the LumaScout pipeline")
    parser.add_argument("--serve", action="store_true", help="Serve the LumaScout dashboard API")
    parser.add_argument("--nextlevel", action="store_true", help="Run the pipeline, start the API, wait for health, and sync outputs")
    parser.add_argument("--auto", action="store_true", help="Alias for --nextlevel")
    parser.add_argument("--sync", action="store_true", help="Sync LamaScout output and report files into code/out/lumascout")
    parser.add_argument("--host", default="0.0.0.0", help="API host")
    parser.add_argument("--port", type=int, default=8000, help="API port")
    parser.add_argument("--no-reload", action="store_true", help="Disable uvicorn auto reload")
    parser.add_argument("--open-ui", action="store_true", help="Open the LumaScout dashboard UI in the default browser")
    args = parser.parse_args()

    if not LAMA_ROOT.exists() or not LAMA_SRC.exists():
        raise SystemExit(f"LamaScout package not found at {LAMA_ROOT}")

    if not (args.run or args.serve or args.nextlevel or args.sync or args.auto):
        args.nextlevel = True
    if args.auto:
        args.nextlevel = True
    if args.nextlevel:
        args.open_ui = True

    api_process = None
    try:
        if args.nextlevel:
            try:
                run_pipeline()
            except (ImportError, ModuleNotFoundError) as e:
                print(f"[LUMASCOUT] Skipping pipeline because a required module is missing: {e}")
                return
            api_process = serve_api(host=args.host, port=args.port, reload=not args.no_reload)
            if not health_check(host="127.0.0.1", port=args.port):
                raise SystemExit("LumaScout API did not become healthy in time.")
            print(f"LumaScout API started at http://127.0.0.1:{args.port}/ui")
            if args.open_ui:
                import webbrowser

                webbrowser.open(f"http://127.0.0.1:{args.port}/ui")
            sync_outputs()
            return

        if args.run:
            try:
                run_pipeline()
            except (ImportError, ModuleNotFoundError) as e:
                print(f"[LUMASCOUT] Skipping pipeline because a required module is missing: {e}")
                return
        if args.serve:
            api_process = serve_api(host=args.host, port=args.port, reload=not args.no_reload)
            if not health_check(host="127.0.0.1", port=args.port):
                raise SystemExit("LumaScout API did not become healthy in time.")
            print(f"LumaScout API started at http://127.0.0.1:{args.port}/ui")
            if args.open_ui:
                import webbrowser

                webbrowser.open(f"http://127.0.0.1:{args.port}/ui")
            print("Press Ctrl+C to stop.")
            api_process.wait()
        if args.sync:
            sync_outputs()
        if not (args.run or args.serve or args.nextlevel or args.sync):
            parser.print_help()
    finally:
        if api_process and api_process.poll() is None and not args.nextlevel:
            api_process.terminate()
            api_process.wait(timeout=10)


if __name__ == "__main__":
    main()
