#!/usr/bin/env python3
"""Install an idempotent, fail-closed public-route guard in nginx."""

from __future__ import annotations

import argparse
import difflib
import os
import re
import shutil
import stat
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


MAP_BEGIN = "# BEGIN LUMENCORE PUBLIC EDGE MAP V1"
MAP_END = "# END LUMENCORE PUBLIC EDGE MAP V1"
GUARD_BEGIN = "    # BEGIN LUMENCORE PUBLIC EDGE GUARD V1"
GUARD_END = "    # END LUMENCORE PUBLIC EDGE GUARD V1"

MAP_BLOCK = """# BEGIN LUMENCORE PUBLIC EDGE MAP V1
map "$request_method:$uri" $lumencore_public_route_denied {
    default 1;
    "~^(GET|HEAD):/$" 0;
    "~^(GET|HEAD):/operator_home\\.html$" 0;
    "~^(GET|HEAD):/assets/(?:lumencore|luma_command_fabric)\\.css$" 0;
    "~^(GET|HEAD):/proof_to_pilot\\.html$" 0;
    "~^(GET|HEAD):/health$" 0;
    "~^(GET|HEAD):/api/master/booth-brief$" 0;
    "~^(GET|HEAD):/evidence$" 0;
    "~^(GET|HEAD):/evidence/$" 0;
    "~^(GET|HEAD):/evidence/index_bounded\\.html$" 0;
}
# END LUMENCORE PUBLIC EDGE MAP V1
"""

GUARD_BLOCK = """    # BEGIN LUMENCORE PUBLIC EDGE GUARD V1
    if ($lumencore_public_route_denied) {
        return 404;
    }
    # END LUMENCORE PUBLIC EDGE GUARD V1
"""

_MAP_PATTERN = re.compile(
    rf"(?ms)^{re.escape(MAP_BEGIN)}\n.*?^{re.escape(MAP_END)}\n?"
)
_GUARD_PATTERN = re.compile(
    rf"(?ms)^[ \t]*{re.escape(GUARD_BEGIN.strip())}\n"
    rf".*?^[ \t]*{re.escape(GUARD_END.strip())}\n?"
)
_SERVER_START = re.compile(r"(?m)^[ \t]*server[ \t]*\{")
_REFLECTED_HTTPS_REDIRECT = re.compile(
    r"(?m)(return[ \t]+30(?:1|2|7|8)[ \t]+https://)\$host(\$request_uri;)"
)
_PRIVATE_SUBDOMAIN_REDIRECT = re.compile(
    r"(?m)^(?P<indent>[ \t]*)return[ \t]+30(?:1|2|7|8)[ \t]+"
    r"https://[^;\s]+/(?:investor_command_room|quant_lab)\.html;[ \t]*$"
)


class PublicEdgeRepairError(RuntimeError):
    """Raised when the edge guard cannot be changed without ambiguity."""


@dataclass(frozen=True)
class RepairResult:
    original: str
    repaired: str
    changed: bool


def _balanced_block_end(text: str, brace_start: int) -> int:
    depth = 0
    quote = ""
    escaped = False
    in_comment = False
    for index in range(brace_start, len(text)):
        char = text[index]
        if in_comment:
            if char == "\n":
                in_comment = False
            continue
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char == "#":
            in_comment = True
        elif char in {'"', "'"}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    raise PublicEdgeRepairError("unterminated nginx block")


def _main_https_server_span(text: str) -> tuple[int, int]:
    candidates = []
    for match in _SERVER_START.finditer(text):
        brace = text.find("{", match.start(), match.end())
        end = _balanced_block_end(text, brace)
        block = text[match.start():end]
        if (
            re.search(r"(?m)^[ \t]*listen[ \t]+443[ \t]+ssl;", block)
            and "location = /health" in block
            and "location /api/" in block
        ):
            candidates.append((match.start(), end))
    if len(candidates) != 1:
        raise PublicEdgeRepairError(
            "expected exactly one HTTPS server with /health and /api/"
        )
    return candidates[0]


def _install_map(text: str) -> str:
    matches = list(_MAP_PATTERN.finditer(text))
    if len(matches) > 1:
        raise PublicEdgeRepairError("multiple public edge map blocks found")
    if matches:
        match = matches[0]
        return text[:match.start()] + MAP_BLOCK + text[match.end():]
    if "$lumencore_public_route_denied" in text:
        raise PublicEdgeRepairError("public edge variable collision")
    anchor = re.search(r"(?m)^[ \t]*(?:upstream|server)[ \t]+", text)
    if anchor is None:
        raise PublicEdgeRepairError("no top-level nginx insertion anchor found")
    return text[:anchor.start()] + MAP_BLOCK + "\n" + text[anchor.start():]


def _install_server_guard(text: str) -> str:
    server_start, server_end = _main_https_server_span(text)
    block = text[server_start:server_end]
    matches = list(_GUARD_PATTERN.finditer(block))
    if len(matches) > 1:
        raise PublicEdgeRepairError("multiple public edge server guards found")
    if matches:
        match = matches[0]
        repaired_block = (
            block[:match.start()] + GUARD_BLOCK + block[match.end():]
        )
    else:
        anchor = re.search(r"(?m)^[ \t]*server_name[^\n]*\n", block)
        if anchor is None:
            raise PublicEdgeRepairError("HTTPS server has no server_name line")
        repaired_block = (
            block[:anchor.end()]
            + "\n"
            + GUARD_BLOCK
            + "\n"
            + block[anchor.end():]
        )
    return text[:server_start] + repaired_block + text[server_end:]


def _harden_redirects(text: str) -> str:
    hardened = _REFLECTED_HTTPS_REDIRECT.sub(
        r"\1$server_name\2",
        text,
    )
    return _PRIVATE_SUBDOMAIN_REDIRECT.sub(
        lambda match: f"{match.group('indent')}return 404;",
        hardened,
    )


def repair_config(text: str) -> RepairResult:
    if "\x00" in text:
        raise PublicEdgeRepairError("nginx config contains a NUL byte")
    repaired = _harden_redirects(_install_server_guard(_install_map(text)))
    validate_repaired_config(repaired)
    return RepairResult(text, repaired, repaired != text)


def validate_repaired_config(text: str) -> None:
    if len(list(_MAP_PATTERN.finditer(text))) != 1:
        raise PublicEdgeRepairError("public edge map is missing or duplicated")
    server_start, server_end = _main_https_server_span(text)
    block = text[server_start:server_end]
    if len(list(_GUARD_PATTERN.finditer(block))) != 1:
        raise PublicEdgeRepairError("public edge server guard is missing or duplicated")
    if MAP_BLOCK not in text:
        raise PublicEdgeRepairError("public edge map differs from the contract")
    if GUARD_BLOCK not in block:
        raise PublicEdgeRepairError("public edge guard differs from the contract")
    if text.index(MAP_BEGIN) > server_start:
        raise PublicEdgeRepairError("public edge map must precede the HTTPS server")
    if _REFLECTED_HTTPS_REDIRECT.search(text):
        raise PublicEdgeRepairError("HTTPS redirect must not reflect the Host header")
    if _PRIVATE_SUBDOMAIN_REDIRECT.search(text):
        raise PublicEdgeRepairError("private dashboard subdomain redirect is not retired")


def _write_atomic(path: Path, text: str) -> Path:
    source_stat = path.stat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.name}.pre-public-edge-repair.{stamp}")
    if backup.exists():
        raise PublicEdgeRepairError(f"backup already exists: {backup}")
    shutil.copy2(path, backup)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, stat.S_IMODE(source_stat.st_mode))
        try:
            os.chown(temporary, source_stat.st_uid, source_stat.st_gid)
        except (AttributeError, PermissionError):
            pass
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return backup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install a bounded public-route guard in nginx."
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--show-diff", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    original = args.config.read_text(encoding="utf-8")
    result = repair_config(original)
    if args.show_diff and result.changed:
        print(
            "".join(
                difflib.unified_diff(
                    original.splitlines(keepends=True),
                    result.repaired.splitlines(keepends=True),
                    fromfile=str(args.config),
                    tofile=f"{args.config}.public-edge",
                )
            ),
            end="",
        )
    if not result.changed:
        print("PUBLIC_EDGE_CONTRACT_CURRENT")
        return 0
    if not args.apply:
        print("PUBLIC_EDGE_REPAIR_REQUIRED")
        return 1
    backup = _write_atomic(args.config, result.repaired)
    validate_repaired_config(args.config.read_text(encoding="utf-8"))
    print(f"PUBLIC_EDGE_REPAIRED backup={backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
