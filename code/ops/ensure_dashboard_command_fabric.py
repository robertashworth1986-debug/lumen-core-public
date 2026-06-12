#!/usr/bin/env python3
"""Ensure canonical dashboard pages load the shared Luma command fabric."""

from __future__ import annotations

import argparse
from pathlib import Path


CANONICAL_PAGES = (
    "mission_control.html",
    "quant_lab.html",
    "kraken_execution_dashboard.html",
    "grants.html",
    "forecast.html",
    "explain.html",
)
CSS_REF = '<link rel="stylesheet" href="./assets/luma_command_fabric.css">'
JS_REF = '<script src="./assets/luma_command_fabric.js"></script>'


def ensure_fabric(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    updated = text
    if "luma_command_fabric.css" not in updated:
        if "</head>" not in updated:
            raise ValueError(f"{path} has no closing head tag")
        updated = updated.replace("</head>", f"{CSS_REF}\n</head>", 1)
    if "luma_command_fabric.js" not in updated:
        if "</body>" not in updated:
            raise ValueError(f"{path} has no closing body tag")
        updated = updated.replace("</body>", f"{JS_REF}\n</body>", 1)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dashboard-root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "dashboard",
    )
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = args.dashboard_root.expanduser().resolve()
    missing: list[str] = []
    changed: list[str] = []
    for name in CANONICAL_PAGES:
        path = root / name
        if not path.exists():
            missing.append(name)
            continue
        if ensure_fabric(path):
            changed.append(name)

    print(
        "DASHBOARD_COMMAND_FABRIC="
        f"PASS changed={len(changed)} missing={len(missing)} root={root}"
    )
    if changed:
        print("changed=" + ",".join(changed))
    if missing:
        print("missing=" + ",".join(missing))
    return 2 if args.strict and missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
