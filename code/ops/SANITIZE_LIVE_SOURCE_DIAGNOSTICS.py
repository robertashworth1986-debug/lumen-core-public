from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CODE_DIR = ROOT / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from safe_diagnostics import sanitize_diagnostic_fields


DEFAULT_PATHS = (
    ROOT / "config" / "live_sources.json",
    ROOT / "config" / "live_source_registry.json",
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def render_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=True) + "\n"


def sanitize_path(path: Path, check: bool = False) -> bool:
    payload = read_json(path)
    sanitized = sanitize_diagnostic_fields(payload)
    changed = sanitized != payload
    if changed and not check:
        path.write_text(render_json(sanitized), encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Redact secrets from generated live-source diagnostic fields."
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()

    paths = tuple(path.resolve() for path in args.paths) or DEFAULT_PATHS
    missing = [path for path in paths if not path.exists()]
    if missing:
        for path in missing:
            print(f"missing: {path}")
        return 2

    changed_paths = [path for path in paths if sanitize_path(path, args.check)]
    result = {
        "mode": "check" if args.check else "apply",
        "path_count": len(paths),
        "changed_count": len(changed_paths),
        "changed_paths": [
            path.relative_to(ROOT).as_posix()
            if path.is_relative_to(ROOT)
            else str(path)
            for path in changed_paths
        ],
    }
    print(json.dumps(result, indent=2))
    return 1 if args.check and changed_paths else 0


if __name__ == "__main__":
    raise SystemExit(main())
