#!/usr/bin/env python3
"""Safely inspect or repair the nginx /evidence/ route.

The public evidence page is a static dashboard asset. This utility replaces an
existing ``location /evidence/`` block with a static-root configuration while
preserving the rest of the nginx file byte-for-byte.

It does not reload nginx. Use the bounded shell wrapper after reviewing the
backup path and the generated diff.
"""

from __future__ import annotations

import argparse
import difflib
import os
import shutil
import stat
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

LOCATION_HEADER = "location /evidence/"
STATIC_BLOCK = """    location = /evidence {
        return 301 /evidence/;
    }

    location /evidence/ {
        root /opt/lumencore/dashboard;
        index index.html;
        try_files $uri $uri/ =404;
        add_header Cache-Control \"no-cache\" always;
    }
"""


class RouteRepairError(RuntimeError):
    """Raised when the target configuration cannot be repaired safely."""


@dataclass(frozen=True)
class RepairResult:
    original: str
    repaired: str
    changed: bool


def _find_location_block(text: str, header: str = LOCATION_HEADER) -> tuple[int, int]:
    """Return the byte offsets for one nginx location block.

    The parser is intentionally narrow. It finds the named location header,
    then balances braces while ignoring braces inside single or double quotes
    and line comments. It refuses ambiguous or malformed input.
    """

    matches: list[int] = []
    start = 0
    while True:
        idx = text.find(header, start)
        if idx < 0:
            break
        matches.append(idx)
        start = idx + len(header)

    if not matches:
        raise RouteRepairError(f"No '{header}' block found")
    if len(matches) > 1:
        raise RouteRepairError(f"Found {len(matches)} '{header}' blocks; refusing ambiguous repair")

    header_index = matches[0]
    line_start = text.rfind("\n", 0, header_index) + 1
    brace_start = text.find("{", header_index + len(header))
    if brace_start < 0:
        raise RouteRepairError("Location header has no opening brace")

    depth = 0
    quote: str | None = None
    escaped = False
    in_comment = False

    for pos in range(brace_start, len(text)):
        char = text[pos]

        if in_comment:
            if char == "\n":
                in_comment = False
            continue

        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char == "#":
            in_comment = True
        elif char in {"'", '"'}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                block_end = pos + 1
                if block_end < len(text) and text[block_end] == "\r":
                    block_end += 1
                if block_end < len(text) and text[block_end] == "\n":
                    block_end += 1
                return line_start, block_end
            if depth < 0:
                break

    raise RouteRepairError("Unbalanced braces in /evidence/ location block")


def repair_config(text: str) -> RepairResult:
    """Return a static-route version of the supplied nginx config."""

    block_start, block_end = _find_location_block(text)
    current_block = text[block_start:block_end]

    already_static = (
        "root /opt/lumencore/dashboard;" in current_block
        and "try_files $uri $uri/ =404;" in current_block
        and "proxy_pass" not in current_block
    )
    has_redirect = "location = /evidence" in text

    if already_static and has_redirect:
        return RepairResult(text, text, False)

    repaired = text[:block_start] + STATIC_BLOCK + text[block_end:]

    # If an exact redirect block already exists elsewhere, avoid introducing a
    # duplicate location. The static block remains the only replacement.
    if has_redirect:
        redirect = """    location = /evidence {
        return 301 /evidence/;
    }

"""
        repaired = repaired.replace(redirect, "", 1)
        insert_at, _ = _find_location_block(repaired)
        repaired = repaired[:insert_at] + redirect + repaired[insert_at:]

    validate_repaired_config(repaired)
    return RepairResult(text, repaired, repaired != text)


def validate_repaired_config(text: str) -> None:
    """Validate the narrow route contract before writing."""

    block_start, block_end = _find_location_block(text)
    block = text[block_start:block_end]

    required = (
        "root /opt/lumencore/dashboard;",
        "index index.html;",
        "try_files $uri $uri/ =404;",
    )
    missing = [item for item in required if item not in block]
    if missing:
        raise RouteRepairError(f"Static evidence route is missing: {', '.join(missing)}")
    if "proxy_pass" in block:
        raise RouteRepairError("Static evidence route still contains proxy_pass")
    if text.count("location = /evidence") != 1:
        raise RouteRepairError("Expected exactly one /evidence redirect block")


def _atomic_write(path: Path, content: str) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    try:
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _backup_path(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return path.with_name(f"{path.name}.bak.{stamp}")


def _diff(original: str, repaired: str, path: Path) -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            repaired.splitlines(keepends=True),
            fromfile=str(path),
            tofile=f"{path} (repaired)",
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("/etc/nginx/conf.d/lumatrader.conf"),
        help="nginx config to inspect or repair",
    )
    parser.add_argument(
        "--document-root",
        type=Path,
        default=Path("/opt/lumencore/dashboard"),
        help="dashboard root used to verify evidence/index.html",
    )
    parser.add_argument("--apply", action="store_true", help="write the repair after creating a timestamped backup")
    parser.add_argument("--show-diff", action="store_true", help="print the proposed unified diff")
    parser.add_argument(
        "--allow-missing-index",
        action="store_true",
        help="allow repair when <document-root>/evidence/index.html is not present",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config: Path = args.config

    if not config.is_file():
        print(f"ERROR: nginx config not found: {config}", file=sys.stderr)
        return 2

    index_path = args.document_root / "evidence" / "index.html"
    if not index_path.is_file() and not args.allow_missing_index:
        print(f"ERROR: static evidence page not found: {index_path}", file=sys.stderr)
        return 3

    original = config.read_text(encoding="utf-8")
    try:
        result = repair_config(original)
    except RouteRepairError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4

    if args.show_diff and result.changed:
        print(_diff(result.original, result.repaired, config), end="")

    if not result.changed:
        print("OK: /evidence/ already uses the bounded static route contract")
        return 0

    if not args.apply:
        print("NEEDS_REPAIR: /evidence/ is not using the bounded static route contract")
        print("Run again with --show-diff, then --apply after review.")
        return 1

    backup = _backup_path(config)
    shutil.copy2(config, backup)
    try:
        _atomic_write(config, result.repaired)
    except Exception:
        shutil.copy2(backup, config)
        raise

    print(f"APPLIED: repaired {config}")
    print(f"BACKUP: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
