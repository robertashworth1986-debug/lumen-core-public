from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = ROOT / "code" / "execution" / "config" / "luma_live_keys.env"
KEY_NAMES = ("SAM_API_KEY", "SAM_GOV_API_KEY", "DATA_GOV_API_KEY_PRIMARY")

SAFE_SECRET_RE = re.compile(r"[A-Za-z0-9._~-]{16,512}")
PLACEHOLDER_RE = re.compile(
    r"(?i)(?:change[-_ ]?me|placeholder|example|sample|test[-_ ]?secret|"
    r"your[-_ ]?(?:sam[-_ ]?)?(?:api[-_ ]?)?key|dummy)"
)
ASSIGNMENT_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<export>export[ \t]+)?"
    r"(?P<name>SAM_API_KEY|SAM_GOV_API_KEY|DATA_GOV_API_KEY_PRIMARY)"
    r"(?P<spacing>[ \t]*)=.*$"
)


class InstallError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def validate_replacement(value: str) -> str:
    if not value:
        raise InstallError("EMPTY_REPLACEMENT")
    if value != value.strip() or any(char.isspace() for char in value):
        raise InstallError("REPLACEMENT_CONTAINS_WHITESPACE")
    if not SAFE_SECRET_RE.fullmatch(value):
        raise InstallError("REPLACEMENT_FORMAT_REJECTED")
    if PLACEHOLDER_RE.search(value) or len(set(value.lower())) < 4:
        raise InstallError("PLACEHOLDER_REPLACEMENT_REJECTED")
    return value


def path_is_within_root(path: Path, root: Path = ROOT) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def git_ignored(path: Path, *, root: Path = ROOT) -> bool:
    if not path_is_within_root(path, root):
        return False
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", path.resolve().relative_to(root.resolve()).as_posix()],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def validate_target(
    target: Path,
    *,
    root: Path = ROOT,
    ignored_checker: Callable[[Path], bool] | None = None,
) -> Path:
    if target.is_symlink():
        raise InstallError("SYMLINK_TARGET_REJECTED")
    resolved = target.resolve()
    if not path_is_within_root(resolved, root):
        raise InstallError("TARGET_OUTSIDE_REPOSITORY")
    checker = ignored_checker or (lambda path: git_ignored(path, root=root))
    if not checker(resolved):
        raise InstallError("TARGET_NOT_GIT_IGNORED")
    if resolved.exists() and not resolved.is_file():
        raise InstallError("TARGET_NOT_REGULAR_FILE")
    return resolved


def assignment_counts(text: str) -> dict[str, int]:
    counts = {name: 0 for name in KEY_NAMES}
    for line in text.splitlines():
        match = ASSIGNMENT_RE.match(line)
        if match:
            counts[match.group("name")] += 1
    return counts


def rewrite_env_text(text: str, replacement: str) -> tuple[str, dict[str, Any]]:
    value = validate_replacement(replacement)
    newline = "\r\n" if "\r\n" in text else "\n"
    had_terminal_newline = text.endswith(("\n", "\r"))
    before = assignment_counts(text)
    seen: set[str] = set()
    rewritten: list[str] = []

    for line in text.splitlines():
        match = ASSIGNMENT_RE.match(line)
        if not match:
            rewritten.append(line)
            continue
        name = match.group("name")
        if name in seen:
            continue
        prefix = f"{match.group('indent')}{match.group('export') or ''}{name}{match.group('spacing')}"
        rewritten.append(f"{prefix}={value}")
        seen.add(name)

    if rewritten and seen != set(KEY_NAMES) and rewritten[-1] != "":
        rewritten.append("")
    for name in KEY_NAMES:
        if name not in seen:
            rewritten.append(f"{name}={value}")

    output = newline.join(rewritten)
    if had_terminal_newline or output:
        output += newline
    after = assignment_counts(output)
    if any(after[name] != 1 for name in KEY_NAMES):
        raise InstallError("ALIAS_NORMALIZATION_FAILED")

    return output, {
        "previous_alias_occurrences": sum(before.values()),
        "final_alias_occurrences": sum(after.values()),
        "aliases_normalized": list(KEY_NAMES),
        "duplicate_aliases_removed": sum(max(0, count - 1) for count in before.values()),
    }


def atomic_write_text(
    target: Path,
    text: str,
    *,
    replacer: Callable[[str | bytes | os.PathLike[str], str | bytes | os.PathLike[str]], None]
    | None = None,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    existing_mode = target.stat().st_mode if target.exists() else 0o600
    temporary_path: Path | None = None
    replace = replacer or os.replace
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=target.parent,
            prefix=".sam-key-install-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, existing_mode & 0o777)
        replace(temporary_path, target)
        temporary_path = None
    except OSError as exc:
        raise InstallError("ATOMIC_REPLACE_FAILED") from exc
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def install_replacement(
    replacement: str,
    *,
    target: Path = DEFAULT_TARGET,
    root: Path = ROOT,
    ignored_checker: Callable[[Path], bool] | None = None,
    replacer: Callable[[str | bytes | os.PathLike[str], str | bytes | os.PathLike[str]], None]
    | None = None,
) -> dict[str, Any]:
    value = validate_replacement(replacement)
    destination = validate_target(target, root=root, ignored_checker=ignored_checker)
    original = destination.read_text(encoding="utf-8") if destination.exists() else ""
    rewritten, details = rewrite_env_text(original, value)
    atomic_write_text(destination, rewritten, replacer=replacer)

    persisted = destination.read_text(encoding="utf-8")
    persisted_counts = assignment_counts(persisted)
    persisted_values = []
    for line in persisted.splitlines():
        match = ASSIGNMENT_RE.match(line)
        if match:
            persisted_values.append(line.split("=", 1)[1])
    if (
        any(persisted_counts[name] != 1 for name in KEY_NAMES)
        or len(persisted_values) != len(KEY_NAMES)
        or any(item != value for item in persisted_values)
    ):
        raise InstallError("POST_WRITE_VERIFICATION_FAILED")

    return {
        "schema": "lumencore.sam_private_api_key_install_receipt.v1",
        "generated_utc": now_utc(),
        "status": "REPLACEMENT_INSTALLED_LOCALLY",
        "target": destination.relative_to(root.resolve()).as_posix(),
        "target_git_ignored": True,
        "atomic_replace_completed": True,
        "plaintext_backup_created": False,
        **details,
        "aliases_consistent": True,
        "secret_value_printed": False,
        "secret_hash_printed": False,
        "external_api_acceptance_claimed": False,
        "next_action": (
            "Run BUILD_SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL.py and require a changed private "
            "baseline comparison plus a live authenticated response when the upstream API is observable."
        ),
    }


def inspect_target(
    target: Path = DEFAULT_TARGET,
    *,
    root: Path = ROOT,
    ignored_checker: Callable[[Path], bool] | None = None,
) -> dict[str, Any]:
    destination = validate_target(target, root=root, ignored_checker=ignored_checker)
    text = destination.read_text(encoding="utf-8") if destination.exists() else ""
    counts = assignment_counts(text)
    return {
        "schema": "lumencore.sam_private_api_key_installer_readiness.v1",
        "status": "READY_FOR_HIDDEN_REPLACEMENT_INPUT",
        "target": destination.relative_to(root.resolve()).as_posix(),
        "target_exists": destination.exists(),
        "target_git_ignored": True,
        "configured_alias_occurrences": sum(counts.values()),
        "expected_alias_count": len(KEY_NAMES),
        "private_file_content_parsed_locally": True,
        "secret_value_returned_or_printed": False,
        "browser_touched": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install a SAM.gov public API key into the ignored local secret store"
    )
    parser.add_argument(
        "--check-target",
        action="store_true",
        help="Validate the private destination without requesting or changing a secret",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if args.check_target:
            receipt = inspect_target()
        else:
            replacement = getpass.getpass("Paste the replacement SAM.gov Public API Key (hidden): ")
            receipt = install_replacement(replacement)
        print(json.dumps(receipt, indent=2, sort_keys=True))
    except InstallError as exc:
        print(
            json.dumps(
                {
                    "status": "INSTALL_NOT_COMPLETED",
                    "error_code": exc.code,
                    "secret_value_printed": False,
                    "secret_hash_printed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
