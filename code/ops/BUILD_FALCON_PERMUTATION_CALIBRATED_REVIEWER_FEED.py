from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ROOT / "out" / "falcon_permutation_calibrated_router_v3_real_20260715"
PROTOCOL_PATH = ROOT / "config" / "falcon_permutation_calibrated_router_protocol_v3.json"
OUT_JSON = ROOT / "out" / "ops" / "falcon_permutation_calibrated_router_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "falcon_permutation_calibrated_router.json"
PUBLIC_DOC = ROOT / "docs" / "FALCON_PERMUTATION_CALIBRATED_ROUTER_V3_NULL_RESULT_2026-07-15.md"
GRANT_DOC = (
    ROOT
    / "grant_submissions"
    / "DPA26BZ04_DV016_FALCON"
    / "DPA26BZ04_DV016_PERMUTATION_CALIBRATED_ROUTER_V3_NULL_RESULT_2026-07-15.md"
)
MODEL_RECEIPT = (
    ROOT
    / "evidence"
    / "falcon"
    / "qwen2_5_1_5b_instruct_weights_receipt_20260715.json"
)
OUTPUT_MANIFEST = (
    ROOT
    / "out"
    / "ops"
    / "falcon_permutation_calibrated_router_review_manifest_latest.json"
)
BUILDER_PATH = Path(__file__).resolve()
TEST_PATH = ROOT / "tests" / "test_falcon_permutation_calibrated_reviewer_feed.py"
PACKET_NAME = "FALCON_PERMUTATION_CALIBRATED_ROUTER_V3_20260715T173357Z"

PINNED_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
PINNED_MODEL_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
PINNED_MODEL_WEIGHTS_SHA256 = (
    "dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee"
)
PINNED_MODEL_WEIGHTS_BYTES = 3_087_467_144
ZERO_HASH = "0" * 64
EXPECTED_ARTIFACTS = {
    "ROUTER_QUALIFICATION_REPORT.md",
    "router_qualification_result.json",
    "traces.jsonl",
}
EXPECTED_SOURCE_PATHS = {
    "code/falcon_constrained_context_router.py",
    "code/falcon_hybrid_context_benchmark.py",
    "code/falcon_permutation_calibrated_router.py",
    "config/falcon_permutation_calibrated_router_protocol_v3.json",
}
EXPECTED_FAILED_GATE_CHECKS = {
    "mean_permutation_agreement",
    "minimum_permutation_agreement",
    "per_context_accuracy",
}
PRIVATE_PATTERNS = (
    re.compile(r"[A-Za-z]:[/\\]Users[/\\]", re.I),
    re.compile(r"[A-Za-z]:[/\\]LumaRuntime[/\\]", re.I),
    re.compile(r"CP575Notice", re.I),
    re.compile(r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret)", re.I),
)


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object at {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def artifact_receipt(path: Path, *, label: str | None = None) -> dict[str, Any]:
    return {
        "path": label or repo_path(path),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def assert_public_safe(payload: Any) -> None:
    rendered = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    hits = [pattern.pattern for pattern in PRIVATE_PATTERNS if pattern.search(rendered)]
    if hits:
        raise ValueError(f"public projection contains private markers: {hits}")


def verify_trace_chain(path: Path) -> dict[str, Any]:
    previous = ZERO_HASH
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"trace line {line_number} is not an object")
            if record.get("prior_record_sha256") != previous:
                raise ValueError(f"trace prior hash mismatch at line {line_number}")
            material = {
                key: value for key, value in record.items() if key != "record_sha256"
            }
            expected = canonical_sha256(material)
            if record.get("record_sha256") != expected:
                raise ValueError(f"trace record hash mismatch at line {line_number}")
            previous = expected
            count += 1
    return {"record_count": count, "terminal_sha256": previous, "verified": True}


def verify_source_packet(run_dir: Path = RUN_DIR) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.sha256.json"
    result_path = run_dir / "router_qualification_result.json"
    traces_path = run_dir / "traces.jsonl"
    manifest = read_json_object(manifest_path)
    result = read_json_object(result_path)

    if manifest.get("schema") != "falcon_permutation_calibrated_router_manifest.v3":
        raise ValueError("unexpected FALCON v3 manifest schema")
    if result.get("schema") != "falcon_permutation_calibrated_router_qualification.v3":
        raise ValueError("unexpected FALCON v3 result schema")
    if set(manifest.get("files", {})) != EXPECTED_ARTIFACTS:
        raise ValueError("FALCON v3 manifest artifact set changed")
    if set(manifest.get("source_files", {})) != EXPECTED_SOURCE_PATHS:
        raise ValueError("FALCON v3 manifest source set changed")

    manifest_material = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    if canonical_sha256(manifest_material) != manifest.get("manifest_sha256"):
        raise ValueError("FALCON v3 manifest self-hash mismatch")

    artifact_rows: list[dict[str, Any]] = []
    for name, expected in sorted(manifest["files"].items()):
        path = run_dir / name
        if not path.is_file():
            raise FileNotFoundError(path)
        row = {
            "path": (
                repo_path(path)
                if path.resolve().is_relative_to(ROOT.resolve())
                else f"{run_dir.name}/{name}"
            ),
            "bytes": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        if row["bytes"] != expected["bytes"] or row["sha256"] != expected["sha256"]:
            raise ValueError(f"FALCON v3 artifact receipt mismatch: {name}")
        artifact_rows.append(row)

    source_rows: list[dict[str, Any]] = []
    for relative, expected_sha256 in sorted(manifest["source_files"].items()):
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
            raise ValueError(f"unsafe or missing FALCON v3 source: {relative}")
        actual = file_sha256(path)
        if actual != expected_sha256:
            raise ValueError(f"FALCON v3 source hash mismatch: {relative}")
        source_rows.append(
            {"path": relative, "bytes": path.stat().st_size, "sha256": actual}
        )

    trace = verify_trace_chain(traces_path)
    result_trace = result.get("trace_chain", {})
    if trace["record_count"] != result_trace.get("record_count"):
        raise ValueError("FALCON v3 trace count does not match result")
    if trace["terminal_sha256"] != result_trace.get("terminal_sha256"):
        raise ValueError("FALCON v3 trace terminal does not match result")
    if trace["terminal_sha256"] != result_trace.get("verified_terminal_sha256"):
        raise ValueError("FALCON v3 verified trace terminal does not match result")

    if result.get("protocol_sha256") != manifest["source_files"][repo_path(PROTOCOL_PATH)]:
        raise ValueError("result protocol hash does not match source manifest")
    if result.get("runner_sha256") != manifest["source_files"][
        "code/falcon_permutation_calibrated_router.py"
    ]:
        raise ValueError("result runner hash does not match source manifest")
    if result.get("model", {}).get("model_id") != PINNED_MODEL_ID:
        raise ValueError("result model identity changed")
    if result.get("model", {}).get("resolved_revision") != PINNED_MODEL_REVISION:
        raise ValueError("result model revision changed")
    gate = result.get("qualification_gate", {})
    if gate.get("qualification_gate_passed") is not False:
        raise ValueError("published v3 packet is expected to preserve the null result")
    failed_checks = {
        key for key, passed in gate.get("checks", {}).items() if passed is not True
    }
    if failed_checks != EXPECTED_FAILED_GATE_CHECKS:
        raise ValueError("FALCON v3 failed-gate set changed")

    error_rows = [row for row in result.get("decision_rows", []) if row.get("correct") is False]
    if len(error_rows) != 3:
        raise ValueError("FALCON v3 error count changed")
    if any(
        row.get("expected_context_class") != "nominal"
        or row.get("selected_context_class") != "noise"
        for row in error_rows
    ):
        raise ValueError("FALCON v3 error pattern changed")

    return {
        "manifest": manifest,
        "manifest_receipt": artifact_receipt(
            manifest_path,
            label=(
                repo_path(manifest_path)
                if manifest_path.resolve().is_relative_to(ROOT.resolve())
                else f"{run_dir.name}/{manifest_path.name}"
            ),
        ),
        "result": result,
        "artifact_receipts": artifact_rows,
        "source_receipts": source_rows,
        "trace": trace,
        "failed_gate_checks": sorted(failed_checks),
        "error_rows": error_rows,
    }


def verify_model_blob(
    path: Path,
    *,
    expected_sha256: str = PINNED_MODEL_WEIGHTS_SHA256,
    expected_bytes: int = PINNED_MODEL_WEIGHTS_BYTES,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_bytes = path.stat().st_size
    actual_sha256 = file_sha256(path)
    if actual_bytes != expected_bytes or actual_sha256 != expected_sha256:
        raise ValueError("pinned model blob byte identity mismatch")
    receipt: dict[str, Any] = {
        "schema": "falcon_model_weights_receipt.v1",
        "model_id": PINNED_MODEL_ID,
        "resolved_revision": PINNED_MODEL_REVISION,
        "filename": "model.safetensors",
        "bytes": actual_bytes,
        "sha256": actual_sha256,
        "expected_bytes": expected_bytes,
        "expected_sha256": expected_sha256,
        "byte_identity_verified": True,
        "local_path_published": False,
        "license": "Apache-2.0",
        "model_card": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct",
        "boundary": (
            "This receipt proves local byte identity for the pinned model artifact. "
            "It does not prove model quality, safety, external validation, or FALCON qualification."
        ),
    }
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    assert_public_safe(receipt)
    return receipt


def metric_gate_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    gate = result["qualification_gate"]
    observed = gate["observed"]
    thresholds = gate["thresholds"]
    return [
        {
            "gate": "overall_accuracy",
            "passed": gate["checks"]["overall_accuracy"],
            "observed": observed["overall_accuracy"],
            "threshold": thresholds["minimum_overall_accuracy"],
        },
        {
            "gate": "per_domain_accuracy",
            "passed": gate["checks"]["per_domain_accuracy"],
            "observed": observed["per_domain_accuracy"],
            "threshold": thresholds["minimum_per_domain_accuracy"],
        },
        {
            "gate": "per_context_accuracy",
            "passed": gate["checks"]["per_context_accuracy"],
            "observed": observed["per_context_accuracy"],
            "threshold": thresholds["minimum_per_context_accuracy"],
        },
        {
            "gate": "unsupported_output_rate",
            "passed": gate["checks"]["unsupported_output_rate"],
            "observed": observed["unsupported_output_rate"],
            "threshold": thresholds["maximum_unsupported_output_rate"],
            "comparison": "maximum",
        },
        {
            "gate": "mean_permutation_agreement",
            "passed": gate["checks"]["mean_permutation_agreement"],
            "observed": observed["mean_permutation_agreement"],
            "threshold": thresholds["minimum_mean_permutation_agreement"],
        },
        {
            "gate": "minimum_permutation_agreement",
            "passed": gate["checks"]["minimum_permutation_agreement"],
            "observed": observed["minimum_permutation_agreement"],
            "threshold": thresholds["minimum_per_decision_permutation_agreement"],
        },
    ]


def build_feed(packet: dict[str, Any], model_receipt: dict[str, Any]) -> dict[str, Any]:
    result = packet["result"]
    metrics = result["aggregate_metrics"]
    protocol = read_json_object(PROTOCOL_PATH)
    errors = [
        {
            "dataset_id": row["dataset_id"],
            "note_index": row["note_index"],
            "expected_context_class": row["expected_context_class"],
            "selected_context_class": row["selected_context_class"],
            "permutation_agreement": row["permutation_agreement"],
            "score_margin": row["score_margin"],
        }
        for row in packet["error_rows"]
    ]
    feed: dict[str, Any] = {
        "schema": "falcon_permutation_calibrated_router_reviewer_feed.v1",
        "generated_utc": result["run_utc"],
        "topic": result["topic"],
        "status": "FROZEN_NULL_RESULT_PRESERVED",
        "evidence_class": "BOUNDED_INTERNAL_MODEL_QUALIFICATION_NULL_RESULT",
        "decision": {
            "qualification_gate_passed": False,
            "correct_decision_count": metrics["correct_decision_count"],
            "decision_count": metrics["decision_count"],
            "overall_accuracy": metrics["overall_accuracy"],
            "unsupported_output_rate": metrics["unsupported_output_rate"],
            "mean_permutation_agreement": metrics["mean_permutation_agreement"],
            "minimum_permutation_agreement": metrics["minimum_permutation_agreement"],
            "per_domain_accuracy": metrics["per_domain_accuracy"],
            "per_context_accuracy": metrics["per_context_accuracy"],
            "failed_gate_checks": packet["failed_gate_checks"],
        },
        "gate_rows": metric_gate_rows(result),
        "error_pattern": {
            "error_count": len(errors),
            "summary": "All three observed errors mapped a nominal note to noise.",
            "rows": errors,
            "raw_prompts_published": False,
            "raw_model_outputs_published": False,
        },
        "model": {
            "model_id": result["model"]["model_id"],
            "resolved_revision": result["model"]["resolved_revision"],
            "model_class": result["model"]["model_class"],
            "parameter_count": result["model"]["parameter_count"],
            "device": result["model"]["device"],
            "cuda_device_name": result["model"]["cuda_device_name"],
            "parameter_dtype": result["model"]["parameter_dtype"],
            "license": protocol["model"]["license"],
            "model_card": protocol["model"]["model_card"],
            "weights_receipt": {
                "bytes": model_receipt["bytes"],
                "sha256": model_receipt["sha256"],
                "byte_identity_verified": model_receipt["byte_identity_verified"],
                "receipt_sha256": model_receipt["receipt_sha256"],
            },
        },
        "method": result["decision_method"],
        "runtime": result["runtime"],
        "integrity": {
            "source_packet_verified": True,
            "manifest_self_hash_verified": True,
            "source_file_hashes_verified": True,
            "artifact_hashes_verified": True,
            "trace_chain_verified": True,
            "trace_record_count": packet["trace"]["record_count"],
            "trace_terminal_sha256": packet["trace"]["terminal_sha256"],
            "source_manifest_sha256": packet["manifest"]["manifest_sha256"],
            "protocol_sha256": result["protocol_sha256"],
            "runner_sha256": result["runner_sha256"],
            "input_receipts": [
                packet["manifest_receipt"],
                *packet["artifact_receipts"],
                *packet["source_receipts"],
                {
                    "path": repo_path(MODEL_RECEIPT),
                    "bytes": MODEL_RECEIPT.stat().st_size,
                    "sha256": file_sha256(MODEL_RECEIPT),
                },
            ],
        },
        "development_lineage": {
            "v2_gate_passed": protocol["development_history"]["prior_gate_passed"],
            "v2_failure": protocol["development_history"]["prior_failure"],
            "v3_observation": (
                "The v3 frozen run classified every noise and dropout note correctly, "
                "but nominal accuracy fell to 0.7 and permutation-stability gates failed."
            ),
            "cross_protocol_lift_claim_allowed": False,
            "reason": (
                "The model, note wording, and scoring protocol changed between v2 and v3; "
                "their class accuracies are diagnostic lineage, not an apples-to-apples lift estimate."
            ),
        },
        "claim_gate": {
            "hybrid_performance_lift_established": False,
            "external_validation_complete": False,
            "field_validation_complete": False,
            "agency_acceptance_complete": False,
            "patent_scope_established": False,
            "safety_claim_allowed": False,
            "savings_claim_allowed": False,
            "medical_performance_claim_allowed": False,
            "enterprise_scale_established": False,
            "universal_superiority_established": False,
        },
        "next_allowed_experiment": {
            "requires_new_protocol_identity": True,
            "description": (
                "Freeze a new same-row comparative protocol for ML-only, LLM-only, and hybrid "
                "systems on a reserved holdout. Preserve v1-v3 unchanged and test lift, calibration, "
                "abstention, latency, and failure modes against named baselines."
            ),
            "external_evaluator_required_for_external_validation": True,
        },
        "claim_boundary": result["claim_boundary"],
    }
    feed["feed_sha256"] = canonical_sha256(feed)
    assert_public_safe(feed)
    return feed


def render_markdown(feed: dict[str, Any], *, grant_context: bool = False) -> str:
    decision = feed["decision"]
    lines = [
        (
            "# DPA26BZ04-DV016 FALCON Permutation-Calibrated Router v3 Null Result"
            if grant_context
            else "# FALCON Permutation-Calibrated Router v3 Null Result"
        ),
        "",
        f"Run UTC: `{feed['generated_utc']}`",
        f"Status: `{feed['status']}`",
        f"Qualification gate passed: `{str(decision['qualification_gate_passed']).lower()}`",
        "",
        "## Decision",
        "",
        (
            "The frozen v3 qualification gate failed. The run is retained as a null result and "
            "must not be described as a qualified router, hybrid lift, field validation, or agency acceptance."
        ),
        "",
        "## Observed Result",
        "",
        f"- Correct decisions: `{decision['correct_decision_count']}/{decision['decision_count']}`",
        f"- Overall accuracy: `{decision['overall_accuracy']:.6f}`",
        f"- Unsupported output rate: `{decision['unsupported_output_rate']:.6f}`",
        f"- Mean permutation agreement: `{decision['mean_permutation_agreement']:.6f}`",
        f"- Minimum permutation agreement: `{decision['minimum_permutation_agreement']:.6f}`",
        f"- Failed checks: `{', '.join(decision['failed_gate_checks'])}`",
        "",
        "### Per Context",
        "",
        "| Context | Accuracy |",
        "| --- | ---: |",
    ]
    for context, value in sorted(decision["per_context_accuracy"].items()):
        lines.append(f"| `{context}` | `{value:.6f}` |")
    lines.extend(
        [
            "",
            "### Error Receipt",
            "",
            "| Dataset | Note | Expected | Selected | Agreement | Margin |",
            "| --- | ---: | --- | --- | ---: | ---: |",
        ]
    )
    for row in feed["error_pattern"]["rows"]:
        lines.append(
            f"| `{row['dataset_id']}` | `{row['note_index']}` | "
            f"`{row['expected_context_class']}` | `{row['selected_context_class']}` | "
            f"`{row['permutation_agreement']:.6f}` | `{row['score_margin']:.6f}` |"
        )
    lines.extend(
        [
            "",
            "## Integrity",
            "",
            f"- Source manifest SHA-256: `{feed['integrity']['source_manifest_sha256']}`",
            f"- Protocol SHA-256: `{feed['integrity']['protocol_sha256']}`",
            f"- Runner SHA-256: `{feed['integrity']['runner_sha256']}`",
            f"- Trace records: `{feed['integrity']['trace_record_count']}`",
            f"- Trace terminal SHA-256: `{feed['integrity']['trace_terminal_sha256']}`",
            f"- Model weights SHA-256: `{feed['model']['weights_receipt']['sha256']}`",
            "- Raw prompts and model outputs are retained in the source packet, not this public projection.",
            "",
            "## Requirement Impact",
            "",
            (
                "This attempt adds bounded real-model, CUDA, single-token, prior-calibrated routing evidence. "
                "It does not close the FALCON requirement for a same-row ML-only, LLM-only, and hybrid comparison."
            ),
            "",
            "## Next Allowed Step",
            "",
            feed["next_allowed_experiment"]["description"],
            "",
            "## Claim Boundary",
            "",
            feed["claim_boundary"],
            "",
            f"Reviewer feed SHA-256: `{feed['feed_sha256']}`",
        ]
    )
    return "\n".join(lines)


def build_outputs(model_blob_path: Path) -> dict[str, Any]:
    packet = verify_source_packet()
    model_receipt = verify_model_blob(model_blob_path)
    write_json(MODEL_RECEIPT, model_receipt)
    feed = build_feed(packet, model_receipt)
    write_json(OUT_JSON, feed)
    write_json(DASHBOARD_JSON, feed)
    write_text(PUBLIC_DOC, render_markdown(feed))
    write_text(GRANT_DOC, render_markdown(feed, grant_context=True))

    artifact_rows = [
        artifact_receipt(path)
        for path in [MODEL_RECEIPT, OUT_JSON, DASHBOARD_JSON, PUBLIC_DOC, GRANT_DOC]
    ]
    manifest: dict[str, Any] = {
        "schema": "falcon_permutation_calibrated_router_review_manifest.v1",
        "generated_utc": feed["generated_utc"],
        "source_manifest_sha256": packet["manifest"]["manifest_sha256"],
        "feed_sha256": feed["feed_sha256"],
        "artifacts": artifact_rows,
        "artifact_chain_sha256": canonical_sha256(artifact_rows),
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    write_json(OUTPUT_MANIFEST, manifest)
    return {"feed": feed, "manifest": manifest, "packet": packet}


def mirror_source_paths(packet: dict[str, Any]) -> list[Path]:
    source_paths = [ROOT / row["path"] for row in packet["source_receipts"]]
    paths = [
        RUN_DIR / "manifest.sha256.json",
        RUN_DIR / "ROUTER_QUALIFICATION_REPORT.md",
        RUN_DIR / "router_qualification_result.json",
        RUN_DIR / "traces.jsonl",
        *source_paths,
        BUILDER_PATH,
        TEST_PATH,
        MODEL_RECEIPT,
        OUT_JSON,
        DASHBOARD_JSON,
        PUBLIC_DOC,
        GRANT_DOC,
        OUTPUT_MANIFEST,
    ]
    unique = {path.resolve(): path.resolve() for path in paths}
    return sorted(unique.values(), key=repo_path)


def render_packet_readme(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# FALCON Permutation-Calibrated Router v3 Evidence Packet",
            "",
            f"Source run UTC: `{manifest['source_run_utc']}`",
            f"Status: `{manifest['status']}`",
            f"Qualification gate passed: `{str(manifest['qualification_gate_passed']).lower()}`",
            f"Files: `{len(manifest['files'])}`",
            f"Packet chain SHA-256: `{manifest['packet_chain_sha256']}`",
            f"Packet manifest SHA-256: `{manifest['manifest_sha256']}`",
            "",
            "This is a non-destructive custody mirror of the frozen source packet and its public-safe projection.",
            "It preserves a null result. It is not hybrid lift, external validation, field validation, agency acceptance, patent scope, safety, savings, or enterprise-scale evidence.",
        ]
    )


def stage_mirror_packet(mirror_root: Path, packet: dict[str, Any]) -> dict[str, Any]:
    mirror_root.mkdir(parents=True, exist_ok=True)
    packet_dir = (mirror_root / PACKET_NAME).resolve()
    if not packet_dir.is_relative_to(mirror_root.resolve()):
        raise ValueError("unsafe mirror packet path")
    packet_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for index, source in enumerate(mirror_source_paths(packet), start=1):
        relative = repo_path(source)
        source_sha256 = file_sha256(source)
        suffix = "".join(source.suffixes)
        stem = source.name[: -len(suffix)] if suffix else source.name
        compact_name = f"{stem[:48]}{suffix}"
        destination_relative = (
            Path("artifacts")
            / f"{index:02d}_{source_sha256[:12]}_{compact_name}"
        )
        destination = packet_dir / destination_relative
        if destination.exists() and file_sha256(destination) != source_sha256:
            raise ValueError(f"immutable mirror collision: {relative}")
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        destination_sha256 = file_sha256(destination)
        row = {
            "source_path": relative,
            "packet_path": destination_relative.as_posix(),
            "bytes": destination.stat().st_size,
            "sha256": source_sha256,
            "verified": destination_sha256 == source_sha256,
        }
        if not row["verified"] or row["bytes"] != source.stat().st_size:
            raise ValueError(f"mirror verification failed: {relative}")
        rows.append(row)

    manifest: dict[str, Any] = {
        "schema": "falcon_permutation_calibrated_router_custody_packet.v1",
        "packet_name": PACKET_NAME,
        "source_run_utc": packet["result"]["run_utc"],
        "status": "FROZEN_NULL_RESULT_PRESERVED",
        "qualification_gate_passed": False,
        "source_manifest_sha256": packet["manifest"]["manifest_sha256"],
        "files": rows,
        "packet_chain_sha256": canonical_sha256(rows),
        "all_file_hashes_verified": all(row["verified"] for row in rows),
        "copy_policy": "Non-destructive copy; an existing destination with different bytes fails closed.",
        "claim_boundary": (
            "Custody mirroring proves byte preservation only. It does not establish hybrid lift, "
            "external validation, field validation, agency acceptance, patent scope, safety, savings, "
            "enterprise scale, or universal superiority."
        ),
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    assert_public_safe(manifest)

    manifest_path = packet_dir / "packet_manifest.json"
    readme_path = packet_dir / "README.md"
    if manifest_path.exists() and read_json_object(manifest_path) != manifest:
        raise ValueError("immutable mirror manifest collision")
    write_json(manifest_path, manifest)
    write_text(readme_path, render_packet_readme(manifest))
    return {
        "packet_dir": str(packet_dir),
        "manifest_path": str(manifest_path),
        "manifest_sha256": file_sha256(manifest_path),
        "packet_chain_sha256": manifest["packet_chain_sha256"],
        "file_count": len(rows),
        "all_file_hashes_verified": manifest["all_file_hashes_verified"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the public-safe FALCON v3 null-result reviewer feed."
    )
    parser.add_argument(
        "--model-blob",
        type=Path,
        required=True,
        help="Local model.safetensors file to hash. The path is never published.",
    )
    parser.add_argument(
        "--mirror-root",
        type=Path,
        action="append",
        default=[],
        help="Optional custody root. May be repeated; packet contents are hash-verified.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outputs = build_outputs(args.model_blob)
    mirrors = [stage_mirror_packet(root, outputs["packet"]) for root in args.mirror_root]
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {PUBLIC_DOC}")
    print(f"Wrote {GRANT_DOC}")
    print(f"Wrote {MODEL_RECEIPT}")
    print(f"Wrote {OUTPUT_MANIFEST}")
    print(
        "Qualification gate passed: "
        f"{outputs['feed']['decision']['qualification_gate_passed']}"
    )
    for mirror in mirrors:
        print(
            f"Mirrored {mirror['file_count']} files to {mirror['packet_dir']} "
            f"(verified={mirror['all_file_hashes_verified']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
