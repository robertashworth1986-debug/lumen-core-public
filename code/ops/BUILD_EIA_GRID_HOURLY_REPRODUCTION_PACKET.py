#!/usr/bin/env python3
"""Build a frozen, offline-verifiable EIA hourly reviewer handoff packet."""

from __future__ import annotations

import argparse
import importlib.util
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
VERIFIER_SOURCE = (
    ROOT / "code" / "ops" / "VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py"
)
DEFAULT_OUTPUT_ROOT = ROOT / "out" / "reviewer_handoffs"
SOURCE_ARTIFACTS = {
    "config/eia_grid_prospective_hourly_router_protocol_v1.json": (
        "config/eia_grid_prospective_hourly_router_protocol_v1.json"
    ),
    "config/eia_grid_hourly_external_evaluator_protocol_template_v1.json": (
        "config/eia_grid_hourly_external_evaluator_protocol_template_v1.json"
    ),
    "code/eia_grid_prospective_hourly_router.py": (
        "code/eia_grid_prospective_hourly_router.py"
    ),
    "code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py": (
        "code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py"
    ),
    "code/ops/BUILD_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py": (
        "code/ops/BUILD_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py"
    ),
    "evidence/external_validation/eia_grid_hourly_router_design_benchmark_20260714.json": (
        "evidence/external_validation/eia_grid_hourly_router_design_benchmark_20260714.json"
    ),
    "evidence/external_validation/eia_grid_hourly_router_design_freeze_20260714.json": (
        "evidence/external_validation/eia_grid_hourly_router_design_freeze_20260714.json"
    ),
    "out/eia_grid_prospective_hourly_router/design_benchmark.json": (
        "design/design_benchmark.json"
    ),
    "out/eia_grid_prospective_hourly_router/source_panel_cache.json": (
        "runtime/source_panel_cache.json"
    ),
    "out/eia_grid_prospective_hourly_router/sealed_predictions.jsonl": (
        "runtime/sealed_predictions.jsonl"
    ),
    "out/eia_grid_prospective_hourly_router/settlements.jsonl": (
        "runtime/settlements.jsonl"
    ),
    "out/eia_grid_prospective_hourly_router/operational_runs.jsonl": (
        "runtime/operational_runs.jsonl"
    ),
    "out/eia_grid_prospective_hourly_router/prospective_status_latest.json": (
        "runtime/prospective_status_latest.json"
    ),
    "out/eia_grid_prospective_hourly_router/latest_cycle.json": (
        "runtime/latest_cycle.json"
    ),
}


def load_verifier():
    spec = importlib.util.spec_from_file_location(
        "verify_eia_grid_hourly_reproduction_packet",
        VERIFIER_SOURCE,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load verifier: {VERIFIER_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def require_new_publish_targets(
    public_manifest_path: Path,
    receipt_template_path: Path,
) -> None:
    """Fail closed before a packet build can mutate published evidence."""

    targets = {
        "public manifest": public_manifest_path.resolve(),
        "receipt template": receipt_template_path.resolve(),
    }
    if len(set(targets.values())) != len(targets):
        raise ValueError("public manifest and receipt template must be distinct files")
    for label, target in targets.items():
        try:
            target.relative_to(ROOT)
        except ValueError as exc:
            raise ValueError(f"{label} must remain under the repository root: {target}") from exc
        if target.exists():
            raise FileExistsError(
                f"refusing to overwrite existing {label}: {target}; choose a new versioned path"
            )


def git_source_state() -> dict[str, Any]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    ).stdout.strip()
    tracked_sources = sorted(
        relative for relative in SOURCE_ARTIFACTS if not relative.startswith("out/")
    )
    byte_mismatches = []
    for relative in tracked_sources:
        source = ROOT / relative
        committed = subprocess.run(
            ["git", "cat-file", "blob", f"HEAD:{relative}"],
            cwd=ROOT,
            capture_output=True,
            timeout=15,
        )
        if not source.is_file() or committed.returncode != 0:
            byte_mismatches.append(relative)
            continue
        if source.read_bytes() != committed.stdout:
            byte_mismatches.append(relative)
    if byte_mismatches:
        raise RuntimeError(
            "packet source bytes must exactly match the current Git commit: "
            + ", ".join(byte_mismatches)
        )
    return {
        "commit": head,
        "tracked_source_count": len(tracked_sources),
        "byte_exact_source_count": len(tracked_sources),
        "all_packet_sources_match_commit": True,
    }


def copy_stable_sources(
    packet_root: Path,
    verifier: Any,
) -> list[str]:
    initial_hashes: dict[Path, str] = {}
    copied: list[str] = []
    for source_relative, packet_relative in SOURCE_ARTIFACTS.items():
        source = ROOT / source_relative
        if not source.is_file():
            raise FileNotFoundError(source)
        initial_hashes[source] = verifier.file_sha256(source)
        destination = packet_root / packet_relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        if verifier.file_sha256(destination) != initial_hashes[source]:
            raise RuntimeError(f"copy hash mismatch: {source_relative}")
        copied.append(packet_relative)
    changed = [
        source.relative_to(ROOT).as_posix()
        for source, expected in initial_hashes.items()
        if verifier.file_sha256(source) != expected
    ]
    if changed:
        raise RuntimeError(
            "runtime changed during snapshot capture; retry after the active cycle: "
            + ", ".join(changed)
        )
    return copied


def environment_lock() -> dict[str, Any]:
    packages = {}
    for distribution in ("numpy", "scikit-learn", "xgboost", "lightgbm"):
        try:
            packages[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            packages[distribution] = None
    return {
        "schema": "eia_grid_hourly_reproduction_environment_lock.v1",
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "model_runtime_packages": packages,
        "offline_packet_verifier_dependency": "python_standard_library_only",
        "model_refit_included": False,
        "claim_boundary": (
            "This environment fingerprint describes the packet-construction host. "
            "It does not prove that every original prediction was refit in this environment."
        ),
    }


def scientific_limitations(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "eia_grid_hourly_reproduction_limitations.v1",
        "frozen_snapshot_status": snapshot["frozen_panel_feasibility_status"],
        "limitations": [
            {
                "id": "MODEL_REFIT_NOT_INCLUDED",
                "effect": (
                    "The packet verifies sealed predictions, chains, and settlement "
                    "arithmetic but does not regenerate every model prediction from training rows."
                ),
                "reason": (
                    "Prediction records retain feature and training-row hashes rather than "
                    "the complete seal-time feature and training matrices."
                ),
                "promotion_blocked": True,
            },
            {
                "id": "SEAL_TIME_SOURCE_SNAPSHOTS_NOT_RETAINED_PER_BATCH",
                "effect": (
                    "The current source cache can be verified as a frozen packet artifact, "
                    "but it may contain publisher revisions made after earlier prediction seals."
                ),
                "reason": (
                    "Earlier predictions bind source-panel hashes; the complete bytes for "
                    "every earlier panel version were not retained in this v1 lane."
                ),
                "promotion_blocked": True,
            },
            {
                "id": "INCOMPLETE_AUTHORITY_PANEL",
                "effect": (
                    "No common settled-hour sample exists across every registered authority."
                ),
                "reason": (
                    "The frozen snapshot contains zero valid prospective seals for: "
                    + ", ".join(snapshot["zero_prospective_seal_authorities"])
                    + "."
                ),
                "promotion_blocked": True,
            },
            {
                "id": "NO_INDEPENDENT_RECEIPT_YET",
                "effect": "The packet is ready for review but remains internally prepared.",
                "reason": "No reviewer-controlled completed and signed receipt exists.",
                "promotion_blocked": True,
            },
            {
                "id": "NO_FIELD_OR_ECONOMIC_ACCEPTANCE",
                "effect": (
                    "No utility-control, grid-reliability, realized-savings, deployment, "
                    "or trading claim is supported."
                ),
                "reason": (
                    "No operator-owned field pilot or accepted economic conversion has occurred."
                ),
                "promotion_blocked": True,
            },
        ],
        "required_successor_controls": [
            "Evaluator-owned held-out data or evaluator-controlled query manifest",
            "Immutable seal-time source snapshot for every prediction batch",
            "Canonical feature-vector sidecar for every prediction",
            "Canonical training-row sidecar or independently hashable fitted model artifact",
            "Pinned environment or container digest for model refit",
            "Outcome-blind authority inclusion and missing-data rules",
            "Incumbent baseline, primary metric, effect threshold, and sample floor frozen before scoring",
            "At least 10,000 paired moving-block bootstrap replications clustered by authority UTC day",
            "Holm correction for the registered comparison family",
            "Reviewer-controlled independence evidence and detached signature",
        ],
        "performance_promotion_allowed": False,
    }


def reviewer_readme(snapshot: dict[str, Any]) -> str:
    zero_seals = snapshot["zero_prospective_seal_authorities"]
    zero_text = ", ".join(zero_seals) if zero_seals else "none"
    return f"""# EIA Grid Hourly Independent Reproduction Packet

Status: `UNSIGNED_REVIEWER_HANDOFF`

## Exact Ask

On a reviewer-controlled machine, rehash this packet and run the offline verifier. Confirm whether the source-cache chain, three append-only ledgers, settlement arithmetic, frozen protocol identity, and authority-coverage result reproduce from the supplied bytes.

This packet asks for independent reproduction of a frozen evidence snapshot. It does not ask the reviewer to endorse model quality or LumenCore.

## Frozen Snapshot

- Protocol: `{snapshot['protocol_id']}`
- Predictions: `{snapshot['prediction_count']}`
- Settlements: `{snapshot['settlement_count']}`
- Common settled hours across every protocol authority: `{snapshot['common_settled_hour_count']}`
- Authorities with zero valid prospective seals: `{zero_text}`
- Panel feasibility status: `{snapshot['frozen_panel_feasibility_status']}`
- Preliminary sample gate: `{str(snapshot['sample_gates']['preliminary_ready']).lower()}`
- Confirmatory sample gate: `{str(snapshot['sample_gates']['confirmatory_ready']).lower()}`
- Performance promotion allowed: `false`

## Offline Verification

Python 3.10 or newer is sufficient; the verifier uses only the standard library.

```powershell
python code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py --packet-dir .
```

Validate the blank reviewer receipt:

```powershell
python code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py --packet-dir . --receipt REVIEWER_RECEIPT_TEMPLATE.json --expect-template
```

Validate the blank external-evaluator protocol before the evaluator fills it:

```powershell
python code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py --packet-dir . --evaluator-protocol config/eia_grid_hourly_external_evaluator_protocol_template_v1.json --expect-evaluator-template
```

After independently filling the receipt, compute its signing payload and verify the detached artifacts:

```powershell
python code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py --packet-dir . --receipt completed_receipt.json --print-signing-payload-sha256
python code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py --packet-dir . --receipt completed_receipt.json --independence-artifact reviewer_independence.txt --signature-artifact detached_signature.bin
```

LumenCore must not fill reviewer-controlled fields.

## Scientific Boundary

Read `SCIENTIFIC_LIMITATIONS.json` before evaluating the packet. The verifier recomputes integrity, settlement arithmetic, and coverage from supplied frozen bytes. It does not refit XGBoost, LightGBM, or ridge models; establish source publication timing outside the sealed records; authenticate reviewer identity by itself; prove utility control, savings, grid reliability, production readiness, trading value, patent validity, agency acceptance, or universal superiority; or convert an incomplete panel into a performance pass.

The frozen protocol is not rewritten after observing outcomes. The zero-seal authorities remain part of the retained result.
"""


def build_receipt_template(packet_report: dict[str, Any]) -> dict[str, Any]:
    snapshot = packet_report["snapshot"]
    return {
        "schema": "eia_grid_hourly_independent_reproduction_receipt.v1",
        "template_version": 1,
        "evidence_lane_id": "eia_grid_prospective_hourly_router_v1_snapshot",
        "frozen_packet": {
            "packet_manifest_file_sha256": packet_report[
                "packet_manifest_file_sha256"
            ],
            "packet_manifest_payload_sha256": packet_report[
                "packet_manifest_payload_sha256"
            ],
            "snapshot": snapshot,
        },
        "reviewer": {
            "name": None,
            "organization": None,
            "technical_role": None,
            "contact_channel": None,
            "conflict_of_interest_disclosure": None,
            "independence_basis": None,
            "independence_evidence_sha256": None,
        },
        "reproduction": {
            "executed_utc": None,
            "decision": None,
            "environment_summary": None,
            "packet_rehashed": None,
            "packet_hashes_match": None,
            "source_cache_chain_verified": None,
            "prediction_chain_verified": None,
            "settlement_chain_verified": None,
            "operational_chain_verified": None,
            "settlement_metrics_recomputed": None,
            "authority_coverage_recomputed": None,
            "prediction_count": None,
            "settlement_count": None,
            "common_settled_hour_count": None,
            "zero_prospective_seal_authorities": None,
            "prediction_terminal_sha256": None,
            "settlement_terminal_sha256": None,
            "operational_terminal_sha256": None,
            "notes": None,
            "operator_filled_reviewer_fields": None,
        },
        "signature": {
            "method": None,
            "signed_payload_sha256": None,
            "detached_signature_artifact_sha256": None,
        },
        "operator_may_fill_reviewer_fields": False,
        "performance_promotion_allowed": False,
        "privacy_rule": (
            "Keep reviewer identity and contact fields reviewer-controlled or in "
            "the private proof vault unless the reviewer explicitly authorizes publication."
        ),
        "claim_boundary": (
            "A valid completed receipt can independently bind and reproduce the frozen "
            "packet's integrity, settlement arithmetic, and authority coverage. It does "
            "not refit the models, convert the incomplete authority panel into a "
            "performance pass, establish field validation, authenticate identity or "
            "signature semantics by itself, or support agency approval, safety, savings, "
            "patent, production, trading, or universal-superiority claims."
        ),
    }


def artifact_rows(packet_root: Path, relative_paths: list[str], verifier: Any) -> list[dict[str, Any]]:
    return [
        {
            "path": relative,
            "bytes": (packet_root / relative).stat().st_size,
            "sha256": verifier.file_sha256(packet_root / relative),
        }
        for relative in sorted(relative_paths)
    ]


def deterministic_zip(packet_root: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(packet_root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(packet_root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2026, 7, 16, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)


def build_packet(
    *,
    output_root: Path,
    public_manifest_path: Path,
    receipt_template_path: Path,
) -> dict[str, Any]:
    require_new_publish_targets(public_manifest_path, receipt_template_path)
    verifier = load_verifier()
    source_state = git_source_state()
    generated = datetime.now(timezone.utc)
    timestamp = generated.strftime("%Y%m%dT%H%M%SZ")
    packet_name = f"EIA_GRID_HOURLY_REPRODUCTION_{timestamp}"
    packet_root = output_root / packet_name
    if packet_root.exists():
        raise FileExistsError(packet_root)
    packet_root.mkdir(parents=True)
    copied = copy_stable_sources(packet_root, verifier)
    snapshot = verifier.audit_snapshot(packet_root)
    evaluator_template_path = packet_root / (
        "config/eia_grid_hourly_external_evaluator_protocol_template_v1.json"
    )
    verifier.validate_evaluator_protocol(
        json.loads(evaluator_template_path.read_text(encoding="utf-8")),
        expect_template=True,
    )
    environment_path = packet_root / "ENVIRONMENT_LOCK.json"
    limitations_path = packet_root / "SCIENTIFIC_LIMITATIONS.json"
    write_json(environment_path, environment_lock())
    write_json(limitations_path, scientific_limitations(snapshot))
    copied.extend(["ENVIRONMENT_LOCK.json", "SCIENTIFIC_LIMITATIONS.json"])
    readme_path = packet_root / "README.md"
    readme_path.write_text(
        reviewer_readme(snapshot),
        encoding="utf-8",
        newline="\n",
    )
    copied.append("README.md")
    manifest = {
        "schema": "eia_grid_hourly_reproduction_packet_manifest.v1",
        "created_utc": generated.isoformat(),
        "packet_id": packet_name,
        "repository_source": source_state,
        "artifacts": artifact_rows(packet_root, copied, verifier),
        "frozen_snapshot": snapshot,
        "reviewer_control_rule": (
            "LumenCore may prepare the unsigned packet and blank template but may not "
            "fill reviewer identity, independence, execution, decision, or signature fields."
        ),
        "promotion_boundary": {
            "independent_snapshot_reproduction_possible": True,
            "model_refit_reproduction_included": False,
            "performance_promotion_allowed": False,
            "field_validation_allowed": False,
            "agency_acceptance_claim_allowed": False,
        },
        "manifest_payload_sha256": None,
    }
    manifest["manifest_payload_sha256"] = verifier.manifest_payload_sha256(manifest)
    write_json(packet_root / "PACKET_MANIFEST.json", manifest)
    packet_report = verifier.verify_packet(packet_root)
    receipt = build_receipt_template(packet_report)
    write_json(packet_root / "REVIEWER_RECEIPT_TEMPLATE.json", receipt)
    verifier.validate_receipt(
        receipt,
        packet_report,
        expect_template=True,
    )
    write_json(receipt_template_path, receipt)
    zip_path = output_root / f"{packet_name}.zip"
    deterministic_zip(packet_root, zip_path)
    public_manifest = {
        "schema": "eia_grid_hourly_independent_reproduction_handoff.v1",
        "generated_utc": generated.isoformat(),
        "status": "UNSIGNED_REVIEWER_HANDOFF_READY",
        "repository_source": source_state,
        "packet": {
            "directory_name": packet_name,
            "zip_file_name": zip_path.name,
            "zip_bytes": zip_path.stat().st_size,
            "zip_sha256": verifier.file_sha256(zip_path),
            "packet_manifest_file_sha256": packet_report[
                "packet_manifest_file_sha256"
            ],
            "packet_manifest_payload_sha256": packet_report[
                "packet_manifest_payload_sha256"
            ],
            "private_runtime_payload_published_in_repository": False,
        },
        "receipt_template": {
            "path": receipt_template_path.relative_to(ROOT).as_posix(),
            "sha256": verifier.file_sha256(receipt_template_path),
            "reviewer_fields_blank": True,
            "operator_may_fill_reviewer_fields": False,
        },
        "external_evaluator_protocol_template": {
            "path": (
                "config/eia_grid_hourly_external_evaluator_protocol_template_v1.json"
            ),
            "sha256": verifier.file_sha256(
                ROOT
                / "config"
                / "eia_grid_hourly_external_evaluator_protocol_template_v1.json"
            ),
            "evaluation_design_frozen": False,
            "operator_may_fill_evaluator_fields": False,
            "minimum_common_hours_per_authority_floor": 720,
            "minimum_bootstrap_replications_floor": 10000,
        },
        "scientific_disclosures": {
            "environment_lock_sha256": verifier.file_sha256(environment_path),
            "limitations_ledger_sha256": verifier.file_sha256(limitations_path),
            "model_refit_reproduction_included": False,
            "seal_time_source_snapshot_per_batch_included": False,
        },
        "frozen_snapshot": snapshot,
        "integrity": {
            "packet_integrity_passed": True,
            "artifact_count": packet_report["artifact_count"],
            "offline_standard_library_verifier_included": True,
            "settlement_metrics_recomputed": snapshot[
                "settlement_metrics_recomputed"
            ],
        },
        "next_valid_state": (
            "A reviewer-controlled completed receipt plus independently retained "
            "independence and detached-signature artifacts."
        ),
        "independent_reproduction_complete": False,
        "performance_promotion_allowed": False,
        "claim_boundary": receipt["claim_boundary"],
    }
    write_json(public_manifest_path, public_manifest)
    return {
        "packet_root": str(packet_root),
        "packet_zip": str(zip_path),
        "packet_zip_sha256": public_manifest["packet"]["zip_sha256"],
        "public_manifest": str(public_manifest_path),
        "receipt_template": str(receipt_template_path),
        "snapshot": snapshot,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--public-manifest",
        type=Path,
        required=True,
        help="New, non-existing public handoff path under the repository root.",
    )
    parser.add_argument(
        "--receipt-template-output",
        type=Path,
        required=True,
        help="New, non-existing reviewer receipt-template path under the repository root.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = build_packet(
        output_root=args.output_root.resolve(),
        public_manifest_path=args.public_manifest.resolve(),
        receipt_template_path=args.receipt_template_output.resolve(),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
