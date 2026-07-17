from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = ROOT / "grant_submissions" / "DLA26BZ03_NV011_MissionWeave"
PRIVATE_DIR = PACKAGE_DIR / "private"
PRIVATE_INPUT = PRIVATE_DIR / "MISSIONWEAVE_DSIP_ACTION.private.json"
SOURCE_MD = PACKAGE_DIR / "MISSIONWEAVE_DSIP_VOLUME2_FINAL_CANDIDATE_2026-07-16.md"
FINAL_DOCX = PRIVATE_DIR / "MISSIONWEAVE_DSIP_VOLUME2_FINAL.private.docx"
FINAL_PDF = PRIVATE_DIR / "MISSIONWEAVE_DSIP_VOLUME2_FINAL.private.pdf"
FINAL_METADATA = PRIVATE_DIR / "MISSIONWEAVE_DSIP_VOLUME2_BUILD_METADATA.private.json"
FINAL_MANIFEST = PRIVATE_DIR / "MISSIONWEAVE_DSIP_VOLUME2_FINAL_MANIFEST.private.json"

GATE_PATH = Path(__file__).with_name("BUILD_MISSIONWEAVE_DSIP_ACTION_GATE.py")
COLLECTOR_PATH = Path(__file__).with_name("CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py")
CANDIDATE_BUILDER_PATH = (
    PACKAGE_DIR / "build_missionweave_dsip_volume2_candidate.py"
)


class FinalizationError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = load_module("missionweave_dsip_action_gate", GATE_PATH)
COLLECTOR = load_module("missionweave_dsip_private_collector", COLLECTOR_PATH)
CANDIDATE_BUILDER = load_module(
    "missionweave_dsip_volume2_candidate", CANDIDATE_BUILDER_PATH
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


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


def validate_private_artifact_target(
    path: Path,
    *,
    root: Path = ROOT,
    private_dir: Path = PRIVATE_DIR,
    ignored_checker: Callable[[Path], bool] | None = None,
) -> Path:
    if path.is_symlink():
        raise FinalizationError("PRIVATE_ARTIFACT_SYMLINK_REJECTED")
    resolved = path.resolve()
    if not path_is_within(resolved, root):
        raise FinalizationError("PRIVATE_ARTIFACT_OUTSIDE_REPOSITORY")
    if not path_is_within(resolved, private_dir):
        raise FinalizationError("PRIVATE_ARTIFACT_OUTSIDE_BOUNDED_DIRECTORY")
    if resolved.exists() and not resolved.is_file():
        raise FinalizationError("PRIVATE_ARTIFACT_NOT_REGULAR_FILE")
    checker = ignored_checker or (lambda target: git_ignored(target, root=root))
    if not checker(resolved):
        raise FinalizationError("PRIVATE_ARTIFACT_NOT_GIT_IGNORED")
    return resolved


def validate_bounded_source(
    path: Path,
    *,
    root: Path = ROOT,
    private_dir: Path = PRIVATE_DIR,
) -> Path:
    if path.is_symlink():
        raise FinalizationError("BOUNDED_SOURCE_SYMLINK_REJECTED")
    resolved = path.resolve()
    package_dir = private_dir.resolve().parent
    if not path_is_within(resolved, root):
        raise FinalizationError("BOUNDED_SOURCE_OUTSIDE_REPOSITORY")
    if not path_is_within(resolved, package_dir) or path_is_within(
        resolved, private_dir
    ):
        raise FinalizationError("BOUNDED_SOURCE_OUTSIDE_PACKAGE")
    if not resolved.is_file():
        raise FinalizationError("BOUNDED_SOURCE_NOT_AVAILABLE")
    return resolved


def load_private_input(
    path: Path,
    *,
    root: Path = ROOT,
    private_dir: Path = PRIVATE_DIR,
    ignored_checker: Callable[[Path], bool] | None = None,
) -> dict[str, Any]:
    target = validate_private_artifact_target(
        path,
        root=root,
        private_dir=private_dir,
        ignored_checker=ignored_checker,
    )
    if not target.is_file():
        raise FinalizationError("PRIVATE_INPUT_NOT_FOUND")
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FinalizationError("PRIVATE_INPUT_UNREADABLE") from exc
    try:
        payload = deepcopy(COLLECTOR.validate_payload_shape(payload))
        COLLECTOR.ensure_private_record_has_no_credential_material(payload)
    except COLLECTOR.CaptureError as exc:
        raise FinalizationError(exc.code) from exc
    if payload["template_only"] is True:
        raise FinalizationError("PRIVATE_TEMPLATE_NOT_ACTION_RECORD")
    proposal_number = payload["proposal"]["proposal_number"]
    if not GATE.valid_proposal_number(proposal_number):
        raise FinalizationError("ASSIGNED_PROPOSAL_NUMBER_NOT_CAPTURED")
    return payload


def find_soffice(
    *,
    candidates: list[Path] | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> Path:
    launchers = list(
        candidates
        or [
            Path("C:/Program Files/LibreOffice/program/soffice.com"),
            ROOT.parent / ".tools" / "LibreOffice" / "program" / "soffice.com",
            Path("C:/Program Files/LibreOffice/program/soffice.exe"),
        ]
    )
    for command in ("soffice.com", "soffice.exe", "soffice"):
        discovered = which(command)
        if discovered:
            launchers.append(Path(discovered))
    for candidate in launchers:
        if candidate.is_file():
            return candidate.resolve()
    raise FinalizationError("LIBREOFFICE_NOT_AVAILABLE")


def convert_docx_to_pdf(
    docx_path: Path,
    output_dir: Path,
    *,
    soffice_path: Path | None = None,
) -> Path:
    executable = (soffice_path or find_soffice()).resolve()
    output = output_dir / f"{docx_path.stem}.pdf"
    profile = Path(tempfile.mkdtemp(prefix="lumencore-lo-"))
    try:
        result = subprocess.run(
            [
                str(executable),
                "--headless",
                f"-env:UserInstallation={profile.resolve().as_uri()}",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_dir),
                str(docx_path),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if result.returncode == 0:
            deadline = time.monotonic() + 30
            while not output.is_file() and time.monotonic() < deadline:
                time.sleep(0.25)
        if result.returncode != 0 or not output.is_file():
            raise FinalizationError("PRIVATE_PDF_CONVERSION_FAILED")
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    return output


def inspect_final_pdf(pdf_path: Path, proposal_number: str) -> dict[str, Any]:
    info_text = GATE.run_pdf_tool("pdfinfo.exe", [str(pdf_path)])
    pages_match = re.search(r"^Pages:\s+(\d+)\s*$", info_text, re.MULTILINE)
    encrypted_match = re.search(r"^Encrypted:\s+(\S+)\s*$", info_text, re.MULTILINE)
    size_match = re.search(
        r"^Page size:\s+([\d.]+) x ([\d.]+) pts", info_text, re.MULTILINE
    )
    pages = int(pages_match.group(1)) if pages_match else 0
    encrypted = encrypted_match.group(1).lower() if encrypted_match else "unknown"
    letter_size = bool(
        size_match
        and abs(float(size_match.group(1)) - 612.0) < 0.5
        and abs(float(size_match.group(2)) - 792.0) < 0.5
    )
    text = GATE.run_pdf_tool("pdftotext", [str(pdf_path), "-"])
    required_sections_present = all(
        heading in text for heading in GATE.REQUIRED_VOLUME2_SECTIONS
    )
    searchable = len(text.strip()) >= 10000
    proposal_number_embedded = proposal_number in text
    neutral_header_absent = GATE.NEUTRAL_PROPOSAL_HEADER not in text
    all_checks_pass = bool(
        1 <= pages <= GATE.VOLUME2_PAGE_LIMIT
        and encrypted == "no"
        and letter_size
        and searchable
        and required_sections_present
        and proposal_number_embedded
        and neutral_header_absent
    )
    return {
        "pages": pages,
        "page_limit": GATE.VOLUME2_PAGE_LIMIT,
        "letter_size": letter_size,
        "encrypted": encrypted != "no",
        "searchable": searchable,
        "required_sections_present": required_sections_present,
        "proposal_number_embedded": proposal_number_embedded,
        "neutral_header_absent": neutral_header_absent,
        "all_checks_pass": all_checks_pass,
    }


def build_private_manifest(
    artifacts: list[tuple[str, Path]], *, private_dir: Path
) -> dict[str, Any]:
    rows = []
    for role, path in artifacts:
        rows.append(
            {
                "role": role,
                "filename": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schema": "lumencore.missionweave_dsip_private_volume2_manifest.v1",
        "generated_utc": now_utc(),
        "topic": GATE.TOPIC,
        "artifact_count": len(rows),
        "artifacts": rows,
        "proposal_number_value_exposed": False,
        "absolute_private_path_exposed": False,
        "private_directory_name": private_dir.name,
        "claim_boundary": (
            "This ignored private manifest proves only the byte identities of the locally "
            "rebuilt Volume 2 artifacts. It does not prove portal upload, submission, "
            "Government receipt, acceptance, selection, contract, or award."
        ),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def finalize_private_volume2(
    *,
    private_input_path: Path = PRIVATE_INPUT,
    source_md: Path = SOURCE_MD,
    final_docx: Path = FINAL_DOCX,
    final_pdf: Path = FINAL_PDF,
    final_metadata: Path = FINAL_METADATA,
    final_manifest: Path = FINAL_MANIFEST,
    root: Path = ROOT,
    private_dir: Path = PRIVATE_DIR,
    ignored_checker: Callable[[Path], bool] | None = None,
    replace_existing: bool = False,
    document_builder: Callable[[Path, Path, Path, str], None] | None = None,
    converter: Callable[[Path, Path], Path] | None = None,
    inspector: Callable[[Path, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    targets = [final_docx, final_pdf, final_metadata, final_manifest]
    resolved_targets = [
        validate_private_artifact_target(
            target,
            root=root,
            private_dir=private_dir,
            ignored_checker=ignored_checker,
        )
        for target in targets
    ]
    if not replace_existing and any(target.exists() for target in resolved_targets):
        raise FinalizationError("PRIVATE_FINAL_OUTPUT_ALREADY_EXISTS")
    bounded_source = validate_bounded_source(
        source_md,
        root=root,
        private_dir=private_dir,
    )

    private_payload = load_private_input(
        private_input_path,
        root=root,
        private_dir=private_dir,
        ignored_checker=ignored_checker,
    )
    proposal_number = str(private_payload["proposal"]["proposal_number"])
    build = document_builder or CANDIDATE_BUILDER.build_document
    convert = converter or convert_docx_to_pdf
    inspect = inspector or inspect_final_pdf

    private_dir.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(
        tempfile.mkdtemp(prefix=".missionweave-private-finalize-", dir=private_dir)
    )
    try:
        temporary_docx = temporary_dir / final_docx.name
        temporary_metadata = temporary_dir / final_metadata.name
        temporary_manifest = temporary_dir / final_manifest.name
        build(bounded_source, temporary_docx, temporary_metadata, proposal_number)
        if (
            temporary_docx.is_symlink()
            or temporary_metadata.is_symlink()
            or not temporary_docx.is_file()
            or not temporary_metadata.is_file()
        ):
            raise FinalizationError("PRIVATE_DOCX_BUILD_INCOMPLETE")

        try:
            metadata = json.loads(temporary_metadata.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FinalizationError("PRIVATE_BUILD_METADATA_INVALID") from exc
        metadata_serialized = json.dumps(metadata, sort_keys=True)
        if (
            metadata.get("schema") != "missionweave_dsip_volume2_build_metadata.v2"
            or metadata.get("proposal_number_header_state") != "ASSIGNED_PRIVATE_VALUE"
            or metadata.get("proposal_number_value_exposed") is not False
            or proposal_number in metadata_serialized
        ):
            raise FinalizationError("PRIVATE_BUILD_METADATA_EXPOSES_PROPOSAL_NUMBER")

        converted_pdf = convert(temporary_docx, temporary_dir)
        if (
            converted_pdf.is_symlink()
            or not path_is_within(converted_pdf, temporary_dir)
            or not converted_pdf.is_file()
        ):
            raise FinalizationError("PRIVATE_PDF_CONVERSION_OUTPUT_MISSING")
        pdf_state = inspect(converted_pdf, proposal_number)
        if pdf_state.get("all_checks_pass") is not True:
            raise FinalizationError("PRIVATE_FINAL_PDF_QA_FAILED")

        manifest = build_private_manifest(
            [
                ("private_final_docx", temporary_docx),
                ("private_final_pdf", converted_pdf),
                ("private_build_metadata", temporary_metadata),
            ],
            private_dir=private_dir,
        )
        if proposal_number in json.dumps(manifest, sort_keys=True):
            raise FinalizationError("PRIVATE_MANIFEST_EXPOSES_PROPOSAL_NUMBER")
        write_json(temporary_manifest, manifest)

        updated_private_payload = deepcopy(private_payload)
        updated_private_payload["proposal"][
            "volume2_pdf_rebuilt_with_assigned_proposal_number"
        ] = True
        updated_private_payload["proposal"]["volume2_pdf_sha256"] = sha256_file(
            converted_pdf
        )
        updated_private_payload["captured_utc"] = now_utc()
        try:
            COLLECTOR.validate_payload_shape(updated_private_payload)
            COLLECTOR.ensure_private_record_has_no_credential_material(
                updated_private_payload
            )
        except COLLECTOR.CaptureError as exc:
            raise FinalizationError(exc.code) from exc

        for temporary, destination in (
            (temporary_docx, resolved_targets[0]),
            (converted_pdf, resolved_targets[1]),
            (temporary_metadata, resolved_targets[2]),
            (temporary_manifest, resolved_targets[3]),
        ):
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(temporary, destination)
        try:
            COLLECTOR.atomic_write_json(
                private_input_path.resolve(), updated_private_payload
            )
        except COLLECTOR.CaptureError as exc:
            raise FinalizationError(exc.code) from exc
    finally:
        shutil.rmtree(temporary_dir, ignore_errors=True)

    return {
        "schema": "lumencore.missionweave_dsip_private_volume2_finalization_receipt.v1",
        "status": "PRIVATE_VOLUME2_REBUILT_AND_QA_PASSED",
        "artifact_count": 4,
        "page_count": pdf_state["pages"],
        "page_limit": pdf_state["page_limit"],
        "letter_size": pdf_state["letter_size"],
        "encrypted": pdf_state["encrypted"],
        "searchable": pdf_state["searchable"],
        "required_sections_present": pdf_state["required_sections_present"],
        "assigned_proposal_number_embedded": pdf_state["proposal_number_embedded"],
        "neutral_header_absent": pdf_state["neutral_header_absent"],
        "private_input_updated": True,
        "proposal_number_value_exposed": False,
        "private_pdf_sha256_exposed": False,
        "absolute_private_path_exposed": False,
        "credential_values_requested": False,
        "browser_navigation_performed": False,
        "portal_upload_performed": False,
        "final_submission_performed": False,
        "next_action": (
            "Run the public MissionWeave action gate with the ignored private input, then "
            "complete the malware scan and remaining portal-review gates."
        ),
    }


def inspect_readiness(
    *,
    private_input_path: Path = PRIVATE_INPUT,
    root: Path = ROOT,
    private_dir: Path = PRIVATE_DIR,
    ignored_checker: Callable[[Path], bool] | None = None,
    output_paths: tuple[Path, Path, Path, Path] | None = None,
    soffice_finder: Callable[[], Path] | None = None,
) -> dict[str, Any]:
    target = validate_private_artifact_target(
        private_input_path,
        root=root,
        private_dir=private_dir,
        ignored_checker=ignored_checker,
    )
    output_states = []
    for path in output_paths or (FINAL_DOCX, FINAL_PDF, FINAL_METADATA, FINAL_MANIFEST):
        resolved = validate_private_artifact_target(
            path,
            root=root,
            private_dir=private_dir,
            ignored_checker=ignored_checker,
        )
        output_states.append(resolved.is_file())
    try:
        (soffice_finder or find_soffice)()
        soffice_available = True
    except FinalizationError:
        soffice_available = False
    return {
        "schema": "lumencore.missionweave_dsip_private_volume2_readiness.v1",
        "status": (
            "READY_FOR_PRIVATE_VOLUME2_FINALIZATION"
            if soffice_available
            else "LIBREOFFICE_NOT_AVAILABLE"
        ),
        "private_input_present": target.is_file(),
        "private_input_contents_read": False,
        "private_output_count": len(output_states),
        "existing_private_output_count": sum(output_states),
        "soffice_available": soffice_available,
        "assigned_proposal_number_cli_argument_allowed": False,
        "proposal_number_value_exposed": False,
        "browser_navigation_performed": False,
        "portal_upload_performed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild MissionWeave Volume 2 from the ignored DSIP proposal number without "
            "putting that value in shell history or public artifacts."
        )
    )
    parser.add_argument("--check-target", action="store_true")
    parser.add_argument("--replace-existing", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        receipt = (
            inspect_readiness()
            if args.check_target
            else finalize_private_volume2(replace_existing=args.replace_existing)
        )
        print(json.dumps(receipt, indent=2, sort_keys=True))
    except FinalizationError as exc:
        print(
            json.dumps(
                {
                    "status": "PRIVATE_VOLUME2_FINALIZATION_NOT_COMPLETED",
                    "error_code": exc.code,
                    "proposal_number_value_exposed": False,
                    "private_pdf_sha256_exposed": False,
                    "credential_values_requested": False,
                    "browser_navigation_performed": False,
                    "portal_upload_performed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
