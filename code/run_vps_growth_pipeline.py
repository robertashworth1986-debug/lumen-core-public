from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
EXEC = CODE / "execution"

BUILD_PROOF_SCRIPT = CODE / "build_vps_growth_proof.py"
CONTROLLER_SCRIPT = EXEC / "kraken_live_growth_controller.py"


def run_step(cmd: List[str], label: str) -> None:
    print(f"[VPS-RUNNER] {label}: {' '.join(cmd)}", flush=True)
    completed = subprocess.run(cmd, cwd=str(ROOT))
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def build_controller_cmd(args: argparse.Namespace) -> List[str]:
    cmd: List[str] = [
        sys.executable,
        str(CONTROLLER_SCRIPT),
        "--controller",
        args.controller,
        "--bankroll",
        str(args.bankroll),
        "--top-n",
        str(args.top_n),
        "--auto-fire-score",
        str(args.auto_fire_score),
        "--gateway-url",
        str(args.gateway_url),
        "--max-daily-loss-usd",
        str(args.max_daily_loss_usd),
        "--max-open-lots",
        str(args.max_open_lots),
        "--min-portfolio-usd",
        str(args.min_portfolio_usd),
        "--heartbeat-max-age-min",
        str(args.heartbeat_max_age_min),
    ]

    if args.cached:
        cmd.append("--cached")
    if args.live:
        cmd.append("--live")
    if args.daemon:
        cmd.extend(["--daemon", "--interval-min", str(args.interval_min)])

    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "One-command VPS growth pipeline: build proof artifacts, then run the guarded "
            "Kraken growth controller with consistent runtime flags."
        )
    )
    parser.add_argument("--skip-proof", action="store_true", help="Skip proof rebuild and run controller only.")
    parser.add_argument("--daemon", action="store_true", help="Keep controller running in loop mode.")
    parser.add_argument("--interval-min", type=int, default=8, help="Loop interval when --daemon is enabled.")
    parser.add_argument("--cached", action="store_true", help="Use cached spike-hunter snapshot in controller.")
    parser.add_argument("--live", action="store_true", help="Request live mode in controller (still guard-gated).")
    parser.add_argument("--controller", default="Robert", help="Controller identity stamped into events.")
    parser.add_argument("--bankroll", type=float, default=150.0)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--auto-fire-score", type=float, default=86.0)
    parser.add_argument("--gateway-url", default="http://127.0.0.1:8787")
    parser.add_argument("--max-daily-loss-usd", type=float, default=20.0)
    parser.add_argument("--max-open-lots", type=int, default=2)
    parser.add_argument("--min-portfolio-usd", type=float, default=40.0)
    parser.add_argument("--heartbeat-max-age-min", type=float, default=20.0)
    args = parser.parse_args()

    mode_line = "LIVE_REQUESTED" if args.live else "SAFE_DRY_RUN"
    print(f"[VPS-RUNNER] mode={mode_line} daemon={args.daemon} cached={args.cached}", flush=True)

    if not args.skip_proof:
        run_step([sys.executable, str(BUILD_PROOF_SCRIPT)], "build_vps_growth_proof")

    run_step(build_controller_cmd(args), "kraken_live_growth_controller")

    print("[VPS-RUNNER] artifacts:", flush=True)
    print(str(ROOT / "out" / "execution" / "vps_growth_proof.json"), flush=True)
    print(str(ROOT / "out" / "execution" / "vps_growth_controller_status.json"), flush=True)
    print(str(ROOT / "dashboard" / "data" / "vps_growth_proof.json"), flush=True)
    print(str(ROOT / "dashboard" / "data" / "vps_growth_controller_status.json"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
