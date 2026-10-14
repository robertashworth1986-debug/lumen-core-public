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
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_fields,
        parse_constant=_reject_nonfinite,
    )
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate runtime JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"nonfinite runtime JSON value: {value}")


def assert_paper_mode(runtime: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if runtime.get("mode") != "paper":
        failures.append("mode must be the exact string paper")
    if runtime.get("allow_live_orders") is not False:
        failures.append("allow_live_orders must be explicitly false")
    if runtime.get("paper_enabled") is not True:
        failures.append("paper_enabled must be explicitly true")
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
