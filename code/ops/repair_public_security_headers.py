#!/usr/bin/env python3
"""Fail-closed repair for LumenCore public Nginx security headers.

Nginx stops inheriting parent ``add_header`` directives as soon as a child
location declares any header of its own. This utility installs one compatible
policy on every HTTPS server and repeats it only in header-bearing locations.
It removes the deprecated X-XSS-Protection header, refuses malformed or
ambiguous configuration, and is inspect-only unless ``--apply`` is supplied.
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


HEADER_VALUES = (
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    (
        "Content-Security-Policy",
        "default-src 'self'; base-uri 'self'; object-src 'none'; "
        "frame-ancestors 'none'; form-action 'self'; img-src 'self' data:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; connect-src 'self'; "
        "worker-src 'self' blob:; media-src 'self'; frame-src 'none'; "
        "upgrade-insecure-requests",
    ),
    ("Strict-Transport-Security", "max-age=31536000"),
    (
        "Permissions-Policy",
        "accelerometer=(), autoplay=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()",
    ),
)
PUBLIC_SECURITY_HEADERS = tuple(
    f'add_header {name} "{value}" always;' for name, value in HEADER_VALUES
)
SERVER_PATTERN = re.compile(r"(?m)^[ \t]*server[ \t]*\{")
LOCATION_PATTERN = re.compile(r"(?m)^[ \t]*location\b[^\r\n{]*\{")
HTTPS_LISTEN_PATTERN = re.compile(
    r"(?m)^[ \t]*listen[ \t]+(?:\[[^\]]+\]:)?443(?:[ \t]|;)"
)
ANY_ADD_HEADER_PATTERN = re.compile(r"(?mi)^[ \t]*add_header\b")
MANAGED_NAMES = tuple(name for name, _value in HEADER_VALUES) + (
    "X-XSS-Protection",
)
MANAGED_HEADER_PATTERN = re.compile(
    r"(?mi)^[ \t]*add_header[ \t]+(?:"
    + "|".join(re.escape(name) for name in MANAGED_NAMES)
    + r")\b[^\r\n]*(?:\r?\n|$)"
)
INSERT_ANCHOR_PATTERN = re.compile(
    r"(?m)^[ \t]*(?:ssl_certificate(?:_key)?|ssl_dhparam|include)\b"
    r"[^\r\n;]*;[ \t]*(?:\r?\n|$)"
)
SERVER_NAME_PATTERN = re.compile(
    r"(?m)^[ \t]*server_name\b[^\r\n;]*;[ \t]*(?:\r?\n|$)"
)


class SecurityHeaderRepairError(RuntimeError):
    """Raised when the Nginx policy cannot be repaired unambiguously."""


@dataclass(frozen=True)
class RepairResult:
    original: str
    repaired: str
    changed: bool


def _newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _balanced_end(text: str, brace_start: int, label: str) -> int:
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
                return end
            if depth < 0:
                break
    raise SecurityHeaderRepairError(f"Unbalanced braces in {label}")


def _block_spans(
    text: str, pattern: re.Pattern[str], label: str
) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    prior_end = -1
    for match in pattern.finditer(text):
        line_start = text.rfind("\n", 0, match.start()) + 1
        brace_start = text.find("{", match.start(), match.end())
        if brace_start < 0:
            raise SecurityHeaderRepairError(f"{label} has no opening brace")
        end = _balanced_end(text, brace_start, label)
        if line_start < prior_end:
            continue
        spans.append((line_start, end))
        prior_end = end
    return spans


def _block_indent(block: str) -> str:
    match = re.match(r"(?m)^(?P<indent>[ \t]*)", block)
    return (match.group("indent") if match else "") + "    "


def _render_headers(indent: str, newline: str) -> str:
    return "".join(f"{indent}{header}{newline}" for header in PUBLIC_SECURITY_HEADERS)


def _insert_before_close(block: str, content: str) -> str:
    closing = block.rfind("}")
    if closing < 0:
        raise SecurityHeaderRepairError("Cannot locate block closing brace")
    line_start = block.rfind("\n", 0, closing) + 1
    return block[:line_start] + content + block[line_start:]


def _server_prefix(block: str) -> str:
    locations = _block_spans(block, LOCATION_PATTERN, "location block")
    return block[: locations[0][0]] if locations else block


def _validate_https_server(block: str) -> None:
    prefix = _server_prefix(block)
    for header in PUBLIC_SECURITY_HEADERS:
        count = prefix.count(header)
        if count != 1:
            raise SecurityHeaderRepairError(
                f"HTTPS server requires exactly one direct header {header!r}; found {count}"
            )
    if re.search(r"(?mi)^[ \t]*add_header[ \t]+X-XSS-Protection\b", block):
        raise SecurityHeaderRepairError(
            "Deprecated X-XSS-Protection remains in an HTTPS server"
        )
    for start, end in _block_spans(block, LOCATION_PATTERN, "location block"):
        location = block[start:end]
        if not ANY_ADD_HEADER_PATTERN.search(location):
            continue
        for header in PUBLIC_SECURITY_HEADERS:
            count = location.count(header)
            if count != 1:
                raise SecurityHeaderRepairError(
                    "Header-bearing location does not preserve the public policy: "
                    f"{header!r} count={count}"
                )


def validate_repaired_config(text: str) -> None:
    servers = _block_spans(text, SERVER_PATTERN, "server block")
    https_servers = [text[start:end] for start, end in servers if HTTPS_LISTEN_PATTERN.search(text[start:end])]
    if not https_servers:
        raise SecurityHeaderRepairError("No HTTPS server block listening on port 443")
    for server in https_servers:
        _validate_https_server(server)


def _harden_https_server(block: str) -> str:
    newline = _newline(block)
    repaired = MANAGED_HEADER_PATTERN.sub("", block)

    locations = _block_spans(repaired, LOCATION_PATTERN, "location block")
    for start, end in reversed(locations):
        location = repaired[start:end]
        if ANY_ADD_HEADER_PATTERN.search(location):
            location = _insert_before_close(
                location,
                _render_headers(_block_indent(location), newline),
            )
            repaired = repaired[:start] + location + repaired[end:]

    prefix = _server_prefix(repaired)
    anchors = list(INSERT_ANCHOR_PATTERN.finditer(prefix))
    if not anchors:
        anchors = list(SERVER_NAME_PATTERN.finditer(prefix))
    if not anchors:
        raise SecurityHeaderRepairError(
            "HTTPS server has no safe server_name or TLS directive insertion anchor"
        )
    insert_at = anchors[-1].end()
    repaired = (
        repaired[:insert_at]
        + _render_headers(_block_indent(repaired), newline)
        + repaired[insert_at:]
    )
    return repaired


def repair_config(text: str) -> RepairResult:
    try:
        validate_repaired_config(text)
    except SecurityHeaderRepairError:
        pass
    else:
        return RepairResult(text, text, False)

    servers = _block_spans(text, SERVER_PATTERN, "server block")
    if not any(HTTPS_LISTEN_PATTERN.search(text[start:end]) for start, end in servers):
        raise SecurityHeaderRepairError("No HTTPS server block listening on port 443")

    repaired = text
    for start, end in reversed(servers):
        block = repaired[start:end]
        if HTTPS_LISTEN_PATTERN.search(block):
            hardened = _harden_https_server(block)
            repaired = repaired[:start] + hardened + repaired[end:]

    validate_repaired_config(repaired)
    return RepairResult(text, repaired, repaired != text)


def _atomic_write(path: Path, content: str) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(content.encode("utf-8"))
        temp_path = Path(handle.name)
    try:
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _backup_path(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return path.with_name(f"{path.name}.pre-security-header-repair.{stamp}")


def _diff(original: str, repaired: str, path: Path) -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            repaired.splitlines(keepends=True),
            fromfile=str(path),
            tofile=f"{path} (bounded public security headers)",
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("/etc/nginx/conf.d/lumatrader.conf"),
        help="Nginx configuration file to inspect or repair",
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
    if not config.is_file():
        print(f"ERROR: nginx config not found: {config}", file=sys.stderr)
        return 2
    try:
        original = config.read_bytes().decode("utf-8")
        result = repair_config(original)
    except (OSError, UnicodeError, SecurityHeaderRepairError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    if args.show_diff and result.changed:
        print(_diff(result.original, result.repaired, config), end="")
    if not result.changed:
        print("OK: all HTTPS routes preserve the bounded public security policy")
        return 0
    if not args.apply:
        print("NEEDS_REPAIR: public HTTPS security headers are incomplete or inconsistent")
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
