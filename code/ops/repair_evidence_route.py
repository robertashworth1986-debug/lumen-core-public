#!/usr/bin/env python3
"""Fail-closed inspection and repair for the public /evidence/ nginx route.

The utility replaces exactly one ``location /evidence/`` block with a static
route that serves ``evidence/index_bounded.html`` from the selected dashboard
root. It refuses missing, duplicate, or malformed targets and preserves the
rest of the nginx file byte-for-byte.
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import shutil
import stat
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DOCUMENT_ROOT = Path("/opt/lumencore/dashboard")
LOCATION_PATTERN = re.compile(r"(?m)^[ \t]*location[ \t]+/evidence/[ \t]*\{")
REDIRECT_PATTERN = re.compile(
    r"(?m)^[ \t]*location[ \t]+=[ \t]*/evidence[ \t]*\{"
)
SAFE_ROOT_PATTERN = re.compile(r"^/[A-Za-z0-9._/-]+$")
PUBLIC_SECURITY_HEADERS = (
    'add_header X-Content-Type-Options "nosniff" always;',
    'add_header X-Frame-Options "DENY" always;',
    'add_header Referrer-Policy "strict-origin-when-cross-origin" always;',
    'add_header Content-Security-Policy "default-src \'self\'; base-uri \'self\'; '
    "object-src 'none'; frame-ancestors 'none'; form-action 'self'; img-src 'self' data:; "
    "font-src 'self' data: https://fonts.gstatic.com; style-src 'self' 'unsafe-inline' "
    "https://fonts.googleapis.com; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "connect-src 'self'; "
    "worker-src 'self' blob:; media-src 'self'; frame-src 'none'; "
    'upgrade-insecure-requests" always;',
    'add_header Strict-Transport-Security "max-age=31536000" always;',
    'add_header Permissions-Policy "accelerometer=(), autoplay=(), camera=(), '
    'geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()" always;',
)


class RouteRepairError(RuntimeError):
    """Raised when a route cannot be changed without ambiguity."""


@dataclass(frozen=True)
class RepairResult:
    original: str
    repaired: str
    changed: bool


def _safe_document_root(path: Path | str) -> str:
    value = str(path)
    segments = value.split("/")
    if (
        not SAFE_ROOT_PATTERN.fullmatch(value)
        or "//" in value
        or any(segment in {".", ".."} for segment in segments)
    ):
        raise RouteRepairError(
            "document root must be a traversal-free absolute POSIX path "
            "containing only letters, digits, dot, underscore, slash, or hyphen"
        )
    return value.rstrip("/") or "/"


def _find_balanced_block(
    text: str, pattern: re.Pattern[str], label: str
) -> tuple[int, int]:
    matches = list(pattern.finditer(text))
    if not matches:
        raise RouteRepairError(f"No {label} block found")
    if len(matches) > 1:
        raise RouteRepairError(
            f"Found {len(matches)} {label} blocks; refusing ambiguous repair"
        )

    match = matches[0]
    line_start = text.rfind("\n", 0, match.start()) + 1
    brace_start = text.find("{", match.start(), match.end() + 1)
    if brace_start < 0:
        raise RouteRepairError(f"{label} block has no opening brace")

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
                end = pos + 1
                if end < len(text) and text[end] == "\r":
                    end += 1
                if end < len(text) and text[end] == "\n":
                    end += 1
                return line_start, end
            if depth < 0:
                break

    raise RouteRepairError(f"Unbalanced braces in {label} block")


def _find_optional_redirect(text: str) -> tuple[int, int] | None:
    matches = list(REDIRECT_PATTERN.finditer(text))
    if not matches:
        return None
    if len(matches) > 1:
        raise RouteRepairError(
            f"Found {len(matches)} exact /evidence redirect blocks; refusing ambiguity"
        )
    return _find_balanced_block(text, REDIRECT_PATTERN, "exact /evidence redirect")


def _static_blocks(document_root: Path | str) -> str:
    root = _safe_document_root(document_root)
    security_headers = "\n".join(
        f"        {header}" for header in PUBLIC_SECURITY_HEADERS
    )
    return f"""    location = /evidence {{
        return 301 /evidence/;
    }}

    location /evidence/ {{
        root {root};
        index index_bounded.html;
        try_files $uri $uri/ =404;
        add_header Cache-Control \"no-cache\" always;
{security_headers}
    }}
"""


def repair_config(
    text: str,
    document_root: Path | str = DEFAULT_DOCUMENT_ROOT,
) -> RepairResult:
    """Return the bounded static-route version of an nginx config."""
    root = _safe_document_root(document_root)
    block_start, block_end = _find_balanced_block(
        text, LOCATION_PATTERN, "location /evidence/"
    )
    current = text[block_start:block_end]
    redirect = _find_optional_redirect(text)

    already_static = (
        f"root {root};" in current
        and "index index_bounded.html;" in current
        and "try_files $uri $uri/ =404;" in current
        and "proxy_pass" not in current
        and redirect is not None
        and all(header in current for header in PUBLIC_SECURITY_HEADERS)
    )
    if already_static:
        validate_repaired_config(text, root)
        return RepairResult(text, text, False)

    working = text
    if redirect is not None:
        redirect_start, redirect_end = redirect
        if redirect_start < block_start:
            removed = redirect_end - redirect_start
            working = working[:redirect_start] + working[redirect_end:]
            block_start -= removed
            block_end -= removed
        else:
            working = working[:redirect_start] + working[redirect_end:]

    repaired = working[:block_start] + _static_blocks(root) + working[block_end:]
    validate_repaired_config(repaired, root)
    return RepairResult(text, repaired, repaired != text)


def validate_repaired_config(
    text: str,
    document_root: Path | str = DEFAULT_DOCUMENT_ROOT,
) -> None:
    root = _safe_document_root(document_root)
    block_start, block_end = _find_balanced_block(
        text, LOCATION_PATTERN, "location /evidence/"
    )
    block = text[block_start:block_end]
    required = (
        f"root {root};",
        "index index_bounded.html;",
        "try_files $uri $uri/ =404;",
        'add_header Cache-Control "no-cache" always;',
        *PUBLIC_SECURITY_HEADERS,
    )
    missing = [item for item in required if item not in block]
    if missing:
        raise RouteRepairError(
            f"Static evidence route is missing: {', '.join(missing)}"
        )
    if "proxy_pass" in block:
        raise RouteRepairError("Static evidence route still contains proxy_pass")
    redirects = list(REDIRECT_PATTERN.finditer(text))
    if len(redirects) != 1:
        raise RouteRepairError(
            f"Expected exactly one exact /evidence redirect block; found {len(redirects)}"
        )


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
    return path.with_name(f"{path.name}.pre-evidence-repair.{stamp}")


def _diff(original: str, repaired: str, path: Path) -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            repaired.splitlines(keepends=True),
            fromfile=str(path),
            tofile=f"{path} (bounded evidence route)",
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("/etc/nginx/conf.d/lumatrader.conf"),
        help="nginx configuration file to inspect or repair",
    )
    parser.add_argument(
        "--document-root",
        type=Path,
        default=DEFAULT_DOCUMENT_ROOT,
        help="dashboard root containing evidence/index_bounded.html",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the repair after creating a timestamped backup",
    )
    parser.add_argument(
        "--show-diff",
        action="store_true",
        help="print the proposed unified diff",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config: Path = args.config
    document_root: Path = args.document_root

    if not config.is_file():
        print(f"ERROR: nginx config not found: {config}", file=sys.stderr)
        return 2

    index_path = document_root / "evidence" / "index_bounded.html"
    if not index_path.is_file():
        print(f"ERROR: bounded evidence page not found: {index_path}", file=sys.stderr)
        return 3

    try:
        original = config.read_text(encoding="utf-8")
        result = repair_config(original, document_root)
    except (OSError, UnicodeError, RouteRepairError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4

    if args.show_diff and result.changed:
        print(_diff(result.original, result.repaired, config), end="")

    if not result.changed:
        print("OK: /evidence/ already uses the bounded static route contract")
        return 0

    if not args.apply:
        print("NEEDS_REPAIR: /evidence/ is not using the bounded static route contract")
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
