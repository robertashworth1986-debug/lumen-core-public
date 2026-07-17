from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
BUILDER_PATH = Path(__file__).with_name("BUILD_PATENT_DEADLINE_EVIDENCE_CONTROL.py")
PRIVATE_BASE = ROOT / "out" / "private"
DEFAULT_CAPTURE_ROOT = PRIVATE_BASE / "patent_center_capture"
METADATA_NAME = "metadata.private.json"
PRIVATE_DOCKET_NAME = "patent_deadline_private_docket.json"

OPTIONAL_ROLES = (
    "claims_record",
    "payment_acknowledgement",
    "payment_receipt_screenshot",
)
MAX_FILES = 200
MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 750 * 1024 * 1024
MAX_METADATA_BYTES = 64 * 1024
METADATA_SCHEMA = "lumencore.patent_center_capture_metadata.v1"


class CaptureError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "patent_deadline_evidence_builder", BUILDER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Patent deadline evidence builder could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = load_builder()
REQUIRED_ROLES = tuple(BUILDER.REQUIRED_DOCKET_ROLES)
ALL_ROLES = REQUIRED_ROLES + OPTIONAL_ROLES


def path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def git_ignored(path: Path, *, root: Path = ROOT) -> bool:
    if not path_is_within(path, root):
        return False
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", relative],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def validate_capture_root(
    capture_root: Path,
    *,
    root: Path = ROOT,
    private_base: Path = PRIVATE_BASE,
    ignored_checker: Callable[[Path], bool] | None = None,
) -> Path:
    if capture_root.is_symlink():
        raise CaptureError("SYMLINK_CAPTURE_ROOT_REJECTED")
    resolved = capture_root.resolve()
    if not path_is_within(resolved, root):
        raise CaptureError("CAPTURE_ROOT_OUTSIDE_REPOSITORY")
    if not path_is_within(resolved, private_base):
        raise CaptureError("CAPTURE_ROOT_OUTSIDE_PRIVATE_BOUNDARY")
    if resolved.exists() and not resolved.is_dir():
        raise CaptureError("CAPTURE_ROOT_NOT_DIRECTORY")
    checker = ignored_checker or (lambda path: git_ignored(path, root=root))
    if not checker(resolved):
        raise CaptureError("CAPTURE_ROOT_NOT_GIT_IGNORED")
    return resolved


def atomic_write_text(
    target: Path,
    text: str,
    *,
    replacer: Callable[[str | bytes | os.PathLike[str], str | bytes | os.PathLike[str]], None]
    | None = None,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    replace = replacer or os.replace
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            prefix=".patent-center-private-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o600)
        replace(temporary_path, target)
        temporary_path = None
    except OSError as exc:
        raise CaptureError("ATOMIC_WRITE_FAILED") from exc
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(
    target: Path,
    payload: dict[str, Any],
    *,
    replacer: Callable[[str | bytes | os.PathLike[str], str | bytes | os.PathLike[str]], None]
    | None = None,
) -> None:
    atomic_write_text(
        target,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        replacer=replacer,
    )


def metadata_template() -> dict[str, Any]:
    return {
        "schema": METADATA_SCHEMA,
        "application_number": None,
        "application_type": None,
        "payment_received_date": None,
        "basic_filing_fee_only_observed": False,
    }


def initialize_capture(
    capture_root: Path = DEFAULT_CAPTURE_ROOT,
    *,
    root: Path = ROOT,
    private_base: Path = PRIVATE_BASE,
    ignored_checker: Callable[[Path], bool] | None = None,
) -> dict[str, Any]:
    destination = validate_capture_root(
        capture_root,
        root=root,
        private_base=private_base,
        ignored_checker=ignored_checker,
    )
    destination.mkdir(parents=True, exist_ok=True)
    for role in ALL_ROLES:
        role_path = destination / role
        if role_path.is_symlink():
            raise CaptureError("SYMLINK_EVIDENCE_DIRECTORY_REJECTED")
        role_path.mkdir(exist_ok=True)
    metadata_path = destination / METADATA_NAME
    if metadata_path.is_symlink():
        raise CaptureError("SYMLINK_PRIVATE_METADATA_REJECTED")
    if metadata_path.exists() and not metadata_path.is_file():
        raise CaptureError("PRIVATE_METADATA_NOT_FILE")
    if not metadata_path.exists():
        atomic_write_json(metadata_path, metadata_template())

    return {
        "schema": "lumencore.patent_center_private_capture_initialization.v1",
        "status": "PRIVATE_CAPTURE_DIRECTORIES_READY",
        "required_role_directory_count": len(REQUIRED_ROLES),
        "optional_role_directory_count": len(OPTIONAL_ROLES),
        "metadata_template_created_or_present": metadata_path.is_file(),
        "target_git_ignored": True,
        "private_values_returned_or_printed": False,
        "browser_navigation_performed": False,
        "legal_filing_performed": False,
        "fee_payment_performed": False,
    }


def scan_role_files(capture_root: Path) -> dict[str, list[Path]]:
    role_paths: dict[str, list[Path]] = {}
    total_files = 0
    total_bytes = 0
    for role in ALL_ROLES:
        role_dir = capture_root / role
        paths: list[Path] = []
        if role_dir.is_symlink():
            raise CaptureError("SYMLINK_EVIDENCE_DIRECTORY_REJECTED")
        if role_dir.is_dir():
            for path in sorted(role_dir.rglob("*")):
                if path.is_symlink():
                    raise CaptureError("SYMLINK_EVIDENCE_REJECTED")
                if not path.is_file():
                    continue
                size = path.stat().st_size
                if size <= 0:
                    raise CaptureError("EMPTY_EVIDENCE_FILE_REJECTED")
                if size > MAX_FILE_BYTES:
                    raise CaptureError("EVIDENCE_FILE_TOO_LARGE")
                total_files += 1
                total_bytes += size
                if total_files > MAX_FILES:
                    raise CaptureError("EVIDENCE_FILE_COUNT_LIMIT_EXCEEDED")
                if total_bytes > MAX_TOTAL_BYTES:
                    raise CaptureError("EVIDENCE_TOTAL_SIZE_LIMIT_EXCEEDED")
                paths.append(path)
        role_paths[role] = paths
    return role_paths


def validate_metadata(payload: Any) -> dict[str, Any]:
    template = metadata_template()
    if not isinstance(payload, dict):
        raise CaptureError("PRIVATE_METADATA_NOT_OBJECT")
    if set(payload) != set(template):
        raise CaptureError("PRIVATE_METADATA_KEYS_INVALID")
    if payload.get("schema") != METADATA_SCHEMA:
        raise CaptureError("PRIVATE_METADATA_SCHEMA_INVALID")

    normalized = dict(payload)
    for key, maximum in (("application_number", 64), ("application_type", 160)):
        value = normalized[key]
        if value is not None:
            if not isinstance(value, str) or not value.strip() or len(value) > maximum:
                raise CaptureError("PRIVATE_METADATA_VALUE_INVALID")
            if any(char in value for char in "\r\n\x00"):
                raise CaptureError("PRIVATE_METADATA_VALUE_INVALID")
            normalized[key] = value.strip()

    payment_date = normalized["payment_received_date"]
    if payment_date is not None and (
        not isinstance(payment_date, str)
        or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", payment_date)
    ):
        raise CaptureError("PRIVATE_METADATA_DATE_INVALID")
    if payment_date is not None:
        try:
            date.fromisoformat(payment_date)
        except ValueError as exc:
            raise CaptureError("PRIVATE_METADATA_DATE_INVALID") from exc
    if not isinstance(normalized["basic_filing_fee_only_observed"], bool):
        raise CaptureError("PRIVATE_METADATA_BOOLEAN_INVALID")
    return normalized


def read_private_metadata(capture_root: Path) -> dict[str, Any]:
    metadata_path = capture_root / METADATA_NAME
    if metadata_path.is_symlink():
        raise CaptureError("SYMLINK_PRIVATE_METADATA_REJECTED")
    if not metadata_path.exists():
        return metadata_template()
    if not metadata_path.is_file():
        raise CaptureError("PRIVATE_METADATA_NOT_FILE")
    size = metadata_path.stat().st_size
    if size <= 0 or size > MAX_METADATA_BYTES:
        raise CaptureError("PRIVATE_METADATA_SIZE_INVALID")
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CaptureError("PRIVATE_METADATA_JSON_INVALID") from exc
    return validate_metadata(payload)


def role_counts(role_paths: dict[str, list[Path]]) -> dict[str, int]:
    return {role: len(role_paths.get(role, [])) for role in ALL_ROLES}


def inspect_capture(
    capture_root: Path = DEFAULT_CAPTURE_ROOT,
    *,
    root: Path = ROOT,
    private_base: Path = PRIVATE_BASE,
    ignored_checker: Callable[[Path], bool] | None = None,
) -> dict[str, Any]:
    destination = validate_capture_root(
        capture_root,
        root=root,
        private_base=private_base,
        ignored_checker=ignored_checker,
    )
    role_paths = scan_role_files(destination) if destination.is_dir() else {
        role: [] for role in ALL_ROLES
    }
    counts = role_counts(role_paths)
    missing = [role for role in REQUIRED_ROLES if counts[role] == 0]
    return {
        "schema": "lumencore.patent_center_private_capture_readiness.v1",
        "status": "COMPLETE_CAPTURE_READY_TO_BUILD" if not missing else "PRIVATE_CAPTURE_INCOMPLETE",
        "required_role_count": len(REQUIRED_ROLES),
        "captured_required_role_count": len(REQUIRED_ROLES) - len(missing),
        "missing_required_roles": missing,
        "role_file_counts": counts,
        "total_evidence_file_count": sum(counts.values()),
        "metadata_file_present": (destination / METADATA_NAME).is_file(),
        "source_filenames_returned_or_printed": False,
        "source_hashes_returned_or_printed": False,
        "private_metadata_values_read_or_printed": False,
        "target_git_ignored": True,
        "browser_navigation_performed": False,
    }


def build_capture(
    capture_root: Path = DEFAULT_CAPTURE_ROOT,
    *,
    root: Path = ROOT,
    private_base: Path = PRIVATE_BASE,
    private_output: Path | None = None,
    public_json: Path = BUILDER.OUT_JSON,
    public_markdown: Path = BUILDER.OUT_MD,
    ignored_checker: Callable[[Path], bool] | None = None,
    require_complete: bool = True,
) -> dict[str, Any]:
    destination = validate_capture_root(
        capture_root,
        root=root,
        private_base=private_base,
        ignored_checker=ignored_checker,
    )
    role_paths = scan_role_files(destination)
    counts = role_counts(role_paths)
    missing = [role for role in REQUIRED_ROLES if counts[role] == 0]
    if require_complete and missing:
        raise CaptureError("REQUIRED_DOCKET_CATEGORIES_MISSING")
    if not any(counts.values()):
        raise CaptureError("NO_EVIDENCE_FILES_FOUND")
    metadata = read_private_metadata(destination)
    records = BUILDER.collect_evidence(role_paths)
    private_payload = BUILDER.build_private_payload(
        records=records,
        application_number=metadata["application_number"],
        application_type=metadata["application_type"],
        payment_received_date=metadata["payment_received_date"],
        basic_filing_fee_only_observed=metadata["basic_filing_fee_only_observed"],
    )
    public_payload = BUILDER.build_public_payload(private_payload)
    rendered = BUILDER.render_markdown(public_payload)
    BUILDER.validate_public_redaction(public_payload, private_payload)
    private_target = private_output or destination / PRIVATE_DOCKET_NAME
    if not path_is_within(private_target, private_base):
        raise CaptureError("PRIVATE_DOCKET_OUTPUT_OUTSIDE_PRIVATE_BOUNDARY")

    atomic_write_json(private_target, private_payload)
    atomic_write_json(public_json, public_payload)
    atomic_write_text(public_markdown, rendered)
    return {
        "schema": "lumencore.patent_center_private_capture_build_receipt.v1",
        "status": public_payload["status"],
        "required_role_count": len(REQUIRED_ROLES),
        "captured_required_role_count": len(REQUIRED_ROLES) - len(missing),
        "missing_required_roles": missing,
        "evidence_file_count": sum(counts.values()),
        "private_docket_written": True,
        "public_control_written": True,
        "source_filenames_returned_or_printed": False,
        "source_hashes_returned_or_printed": False,
        "private_metadata_values_returned_or_printed": False,
        "browser_navigation_performed": False,
        "legal_filing_performed": False,
        "fee_payment_performed": False,
        "signature_performed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare and validate a private role-folder capture of Patent Center docket downloads."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--initialize", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--build", action="store_true")
    mode.add_argument(
        "--build-partial",
        action="store_true",
        help="Explicitly rebuild the public control from an incomplete private capture",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if args.initialize:
            result = initialize_capture()
        elif args.check:
            result = inspect_capture()
        else:
            result = build_capture(require_complete=not args.build_partial)
        print(json.dumps(result, indent=2, sort_keys=True))
    except CaptureError as exc:
        print(
            json.dumps(
                {
                    "status": "PATENT_CENTER_PRIVATE_CAPTURE_NOT_COMPLETED",
                    "error_code": exc.code,
                    "private_values_returned_or_printed": False,
                    "browser_navigation_performed": False,
                    "legal_filing_performed": False,
                    "fee_payment_performed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
