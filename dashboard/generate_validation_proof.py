"""Compatibility entry point for the canonical offline ensemble diagnostic.

Pass the same explicit input, output, window, and cost arguments accepted by
run_ensemble_meta_strategy.py. No trade-log prices are synthesized, no dummy
strategy is stamped as validation, and no proof_live files are created.
"""
from pathlib import Path
import subprocess
import sys


def main(argv=None):
    runner = Path(__file__).resolve().with_name("run_ensemble_meta_strategy.py")
    arguments = sys.argv[1:] if argv is None else list(argv)
    return subprocess.run([sys.executable, str(runner), *arguments], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
