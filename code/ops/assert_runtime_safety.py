from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def resolve_root() -> Path:
    return Path(
        os.environ.get("LUMA_STACK_ROOT", str(Path(__file__).resolve().parents[2]))
    ).expanduser().resolve()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def assert_paper_mode(runtime: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    mode = str(runtime.get("mode") or "").strip().lower()
    if mode != "paper":
        failures.append(f"mode must be paper, found {mode or 'missing'}")
    if bool(runtime.get("allow_live_orders", False)):
        failures.append("allow_live_orders must be false")
    if not bool(runtime.get("paper_enabled", False)):
        failures.append("paper_enabled must be true")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail closed unless runtime is paper-only")
    parser.add_argument(
        "--runtime-file",
        type=Path,
        default=resolve_root() / "config" / "runtime_control.json",
    )
    args = parser.parse_args()

    try:
        runtime = load_json(args.runtime_file.expanduser().resolve())
    except Exception as exc:
        print(f"RUNTIME_SAFETY=FAIL reason={exc}")
        return 2

    failures = assert_paper_mode(runtime)
    if failures:
        print(f"RUNTIME_SAFETY=FAIL reason={'; '.join(failures)}")
        return 3

    print("RUNTIME_SAFETY=PASS mode=paper allow_live_orders=false paper_enabled=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
