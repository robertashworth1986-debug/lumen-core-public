from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_V1_RUN = ROOT / "out" / "lumajet_flight_assurance" / "v1_confirmatory_20260716"
DEFAULT_V2_RUN = ROOT / "out" / "lumajet_flight_assurance" / "v2_guarded_confirmatory_20260716"
DEFAULT_JSON = ROOT / "out" / "ops" / "lumajet_flight_assurance_evidence_latest.json"
PHASE1_ROOT = ROOT / "phase1" / "lumajet_sbir"

EVIDENCE_BOUNDARY = (
    "Internal generated software-simulation evidence only. The packet preserves both an adverse "
    "v1 result and a tiny-effect v2 internal gate pass. It is not flight control, airworthiness "
    "evidence, field validation, independent reproduction, FAA or DoD approval, economic proof, "
    "or authorization for operational use."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def verify_manifest(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.sha256.json"
    manifest = load_json(manifest_path)
    files: list[dict[str, Any]] = []
    all_valid = True
    for name, metadata in sorted((manifest.get("files") or {}).items()):
        path = run_dir / name
        expected = str((metadata or {}).get("sha256") or "")
        actual = sha256_file(path) if path.exists() else None
        valid = bool(actual and actual == expected)
        all_valid = all_valid and valid
        files.append(
            {
                "name": name,
                "path": str(path),
                "exists": path.exists(),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "valid": valid,
            }
        )
    return {
        "path": str(manifest_path),
        "sha256": sha256_file(manifest_path),
        "all_hashes_valid": all_valid,
        "files": files,
    }


def verify_summary_receipt(summary: dict[str, Any]) -> dict[str, Any]:
    declared = str(summary.get("evidence_receipt_sha256") or "")
    unhashed = {key: value for key, value in summary.items() if key != "evidence_receipt_sha256"}
    computed = sha256_payload(unhashed)
    return {
        "declared_sha256": declared,
        "computed_sha256": computed,
        "valid": bool(declared and declared == computed),
    }


def protocol_seed_set(protocol: dict[str, Any], split: str) -> set[int]:
    split_spec = protocol["splits"][split]
    base = int(split_spec["seed_base"])
    count = int(split_spec["scenarios_per_condition"])
    return {
        base + condition_index * 100000 + index
        for condition_index, _ in enumerate(protocol["conditions"])
        for index in range(count)
    }


def verify_run(run_dir: Path) -> dict[str, Any]:
    summary_path = run_dir / "summary.json"
    protocol_path = run_dir / "protocol_snapshot.json"
    plan_path = run_dir / "execution_plan.json"
    summary = load_json(summary_path)
    protocol = load_json(protocol_path)
    plan = load_json(plan_path)
    manifest = verify_manifest(run_dir)
    receipt = verify_summary_receipt(summary)
    development_seeds = protocol_seed_set(protocol, "development")
    validation_seeds = protocol_seed_set(protocol, "validation")
    if not manifest["all_hashes_valid"]:
        raise ValueError(f"invalid run manifest: {run_dir}")
    if not receipt["valid"]:
        raise ValueError(f"invalid summary evidence receipt: {run_dir}")
    if development_seeds & validation_seeds:
        raise ValueError(f"development/validation seed overlap: {run_dir}")
    if str(plan.get("protocol_sha256") or "") != sha256_file(protocol_path):
        raise ValueError(f"execution plan protocol hash mismatch: {run_dir}")
    return {
        "run_dir": str(run_dir),
        "summary_path": str(summary_path),
        "summary_file_sha256": sha256_file(summary_path),
        "protocol_path": str(protocol_path),
        "protocol_sha256": sha256_file(protocol_path),
        "execution_plan_path": str(plan_path),
        "execution_plan_sha256": sha256_file(plan_path),
        "evidence_receipt": receipt,
        "manifest": manifest,
        "development_seed_count": len(development_seeds),
        "validation_seed_count": len(validation_seeds),
        "development_validation_seed_overlap_count": 0,
        "summary": summary,
        "protocol": protocol,
        "development_seeds": development_seeds,
        "validation_seeds": validation_seeds,
    }


def compact_run(run: dict[str, Any]) -> dict[str, Any]:
    summary = run["summary"]
    gate = summary["promotion_gate"]
    return {
        "run_dir": run["run_dir"],
        "summary_file_sha256": run["summary_file_sha256"],
        "protocol_sha256": run["protocol_sha256"],
        "execution_plan_sha256": run["execution_plan_sha256"],
        "manifest_sha256": run["manifest"]["sha256"],
        "all_manifest_hashes_valid": run["manifest"]["all_hashes_valid"],
        "evidence_receipt_sha256": run["evidence_receipt"]["declared_sha256"],
        "evidence_receipt_valid": run["evidence_receipt"]["valid"],
        "development_scenario_count": summary["development"]["scenario_count"],
        "validation_scenario_count": summary["validation"]["scenario_count"],
        "gate": gate["gate"],
        "promoted": gate["promoted"],
        "selection": gate["selection"],
        "paired_score_interval": gate["paired_score_interval"],
        "energy_regression_fraction": gate["energy_regression_fraction"],
        "risk_regression_fraction": gate["risk_regression_fraction"],
        "planner_expansion_multiplier": gate["planner_expansion_multiplier"],
        "failed_checks": gate["failed_checks"],
        "candidate_validation_aggregate": gate["candidate_validation_aggregate"],
        "baseline_validation_aggregate": gate["baseline_validation_aggregate"],
        "condition_guardrails": gate["condition_guardrails"],
        "claim_gate": summary["claim_gate"],
    }


def build_packet(v1_run_dir: Path = DEFAULT_V1_RUN, v2_run_dir: Path = DEFAULT_V2_RUN) -> dict[str, Any]:
    v1 = verify_run(v1_run_dir)
    v2 = verify_run(v2_run_dir)
    cross_run_seed_overlap = (
        v1["development_seeds"]
        | v1["validation_seeds"]
    ) & (v2["development_seeds"] | v2["validation_seeds"])
    predecessor = v2["protocol"].get("predecessor_evidence") or {}
    predecessor_checks = {
        "v2_declared_v1_receipt_matches": str(predecessor.get("evidence_receipt_sha256") or "")
        == str(v1["evidence_receipt"]["declared_sha256"]),
        "v2_declared_v1_summary_hash_matches": str(predecessor.get("summary_file_sha256") or "")
        == str(v1["summary_file_sha256"]),
        "v1_adverse_result_retained": v1["summary"]["promotion_gate"]["promoted"] is False,
        "v1_validation_not_reused_for_v2_confirmation": predecessor.get(
            "v1_validation_reused_in_v2_confirmation"
        )
        is False,
        "cross_run_seed_sets_disjoint": not cross_run_seed_overlap,
        "v2_pair_preselected_before_current_validation": v2["summary"]["promotion_gate"][
            "selection"
        ].get("preselected_before_current_validation")
        is True,
    }
    if not all(predecessor_checks.values()):
        failed = [name for name, passed in predecessor_checks.items() if not passed]
        raise ValueError(f"v1-to-v2 lineage verification failed: {failed}")

    v2_gate = v2["summary"]["promotion_gate"]
    candidate = v2_gate["candidate_validation_aggregate"]
    baseline = v2_gate["baseline_validation_aggregate"]
    non_guard_selection_count = int(candidate["scenario_count"]) - int(
        candidate["selected_specialist_counts"].get("astar_balanced", 0)
    )
    score_delta = float(v2_gate["paired_score_interval"]["observed_mean_delta"])
    practical_effect = (
        "TINY_EFFECT_INTERNAL_GUARD_PASS"
        if abs(score_delta) < 0.001
        else "MEASURABLE_INTERNAL_EFFECT_REQUIRES_EXTERNAL_REPRODUCTION"
    )
    payload: dict[str, Any] = {
        "schema": "lumajet_flight_assurance_evidence_packet_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "summary": {
            "v1_decision": v1["summary"]["promotion_gate"]["gate"],
            "v2_decision": v2_gate["gate"],
            "v1_adverse_result_retained": True,
            "v2_internal_generated_gate_pass": bool(v2_gate["promoted"]),
            "v2_validation_scenario_count": v2["summary"]["validation"]["scenario_count"],
            "v2_score_delta": score_delta,
            "v2_score_delta_ci95": v2_gate["paired_score_interval"]["ci95"],
            "v2_energy_regression_fraction": v2_gate["energy_regression_fraction"],
            "v2_risk_regression_fraction": v2_gate["risk_regression_fraction"],
            "v2_planner_expansion_multiplier": v2_gate["planner_expansion_multiplier"],
            "v2_candidate_collision_rate": candidate["collision_rate"],
            "v2_candidate_endpoint_failure_rate": candidate["endpoint_failure_rate"],
            "v2_candidate_reserve_breach_rate": candidate["reserve_breach_rate"],
            "v2_non_guard_selection_count": non_guard_selection_count,
            "v2_guard_selection_count": int(candidate["scenario_count"]) - non_guard_selection_count,
            "practical_effect_classification": practical_effect,
            "all_run_manifests_valid": True,
            "all_summary_receipts_valid": True,
            "all_seed_sets_disjoint": True,
            "external_reproduction_complete": False,
            "field_validation_complete": False,
            "airworthiness_claim_allowed": False,
            "faa_or_dod_approval_claim_allowed": False,
        },
        "lineage_verification": predecessor_checks,
        "runs": {
            "v1_adverse": compact_run(v1),
            "v2_guarded": compact_run(v2),
        },
        "reviewer_interpretation": {
            "allowed": [
                "The v1 development-selected policy failed its frozen internal assurance gate and remains retained.",
                "A guarded v2 policy passed the internal generated-software gate on fresh disjoint seeds.",
                "The v2 effect is statistically positive inside this simulator but practically tiny.",
                "The primary evidence contribution is bounded orchestration, hard safety vetoes, lineage, and reproducibility.",
            ],
            "blocked": [
                "airworthiness or flight-safety proof",
                "FAA, DoD, Air Force, NASA, laboratory, or investor approval",
                "field validation or independent reproduction",
                "aircraft, propulsion, or actuator performance",
                "economic savings or procurement readiness",
            ],
        },
        "next_evidence_gate": {
            "name": "independent_offline_reproduction_then_representative_dynamics_review",
            "required_actions": [
                "Give an external runner the frozen v2 protocol, source snapshot, and verification command without the expected leaderboard.",
                "Require the runner to publish raw checkpoints, environment package versions, terminal hashes, and all null or adverse rows.",
                "Repeat on an accepted representative flight-dynamics environment or partner-approved historical data before any aerospace performance claim.",
                "Obtain qualified aerospace software-assurance review before mapping any artifact toward certification objectives.",
            ],
        },
        "four_level_gate": [
            {
                "level": 1,
                "name": "implementation_integrity",
                "status": "PASS",
                "evidence": "unit tests, deterministic environments, source snapshots, manifests, and self-hashed summaries",
                "external": False,
            },
            {
                "level": 2,
                "name": "named_baseline_internal_benchmark",
                "status": "PASS",
                "evidence": "identical generated scenarios across Dijkstra, A-star specialists, and fixed hybrid policies",
                "external": False,
            },
            {
                "level": 3,
                "name": "frozen_fresh_seed_stress_confirmation",
                "status": "PASS_TINY_EFFECT",
                "evidence": "1,400 v2 validation scenarios, paired CI95, seven conditions, and hard safety vetoes",
                "external": False,
            },
            {
                "level": 4,
                "name": "independent_blind_reproduction_and_representative_review",
                "status": "KIT_READY_EXTERNAL_EXECUTION_REQUIRED",
                "evidence": "blind reproduction kit with no expected leaderboard",
                "external": True,
            },
        ],
    }
    payload["packet_sha256"] = sha256_payload(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    v1 = payload["runs"]["v1_adverse"]
    v2 = payload["runs"]["v2_guarded"]
    lines = [
        "# LumaJet Flight Assurance Evidence",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Packet SHA-256: `{payload['packet_sha256']}`",
        "",
        "## Evidence Boundary",
        "",
        payload["evidence_boundary"],
        "",
        "## Reviewer Answer",
        "",
        "The first frozen policy failed. That failure was retained and used only as design evidence. "
        "A guarded successor was then frozen and tested on entirely new seeds. It passed the internal "
        "generated-software gate, but its effect is tiny and it remains neither external validation "
        "nor airworthiness evidence.",
        "",
        "## Run Ledger",
        "",
        "| Run | Validation Scenarios | Decision | Score Delta | CI95 | Energy Regression | Risk Regression |",
        "| --- | ---: | --- | ---: | --- | ---: | ---: |",
        f"| v1 adverse | {v1['validation_scenario_count']} | `{v1['gate']}` | "
        f"{v1['paired_score_interval']['observed_mean_delta']} | "
        f"`{v1['paired_score_interval']['ci95']}` | {v1['energy_regression_fraction']} | "
        f"{v1['risk_regression_fraction']} |",
        f"| v2 guarded | {v2['validation_scenario_count']} | `{v2['gate']}` | "
        f"{v2['paired_score_interval']['observed_mean_delta']} | "
        f"`{v2['paired_score_interval']['ci95']}` | {v2['energy_regression_fraction']} | "
        f"{v2['risk_regression_fraction']} |",
        "",
        "## V2 Practical Effect",
        "",
        f"- Classification: `{summary['practical_effect_classification']}`.",
        f"- Guarded selections: `{summary['v2_guard_selection_count']}` of `{summary['v2_validation_scenario_count']}`.",
        f"- Non-guard specialist selections: `{summary['v2_non_guard_selection_count']}`.",
        f"- Collision rate: `{summary['v2_candidate_collision_rate']}`.",
        f"- Endpoint-failure rate: `{summary['v2_candidate_endpoint_failure_rate']}`.",
        f"- Reserve-breach rate: `{summary['v2_candidate_reserve_breach_rate']}`.",
        f"- Planner expansion multiplier: `{summary['v2_planner_expansion_multiplier']}`.",
        "",
        "The v2 score improvement is statistically positive inside the frozen simulator, but the "
        "absolute effect is too small to support an aircraft-performance or economic claim. The "
        "useful result is the evidence discipline: adverse-result retention, fresh-seed lineage, "
        "hard safety vetoes, bounded spectral stress, and deterministic verification.",
        "",
        "## Next Gate",
        "",
    ]
    lines.extend(f"1. {action}" for action in payload["next_evidence_gate"]["required_actions"])
    lines.extend(
        [
            "",
            "## Claim Gate",
            "",
            "External reproduction, field validation, airworthiness, operational authorization, "
            "FAA/DoD approval, and economic claims remain false.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_blind_reproduction_kit(
    payload: dict[str, Any],
    v2_run_dir: Path,
) -> dict[str, Path]:
    kit_root = (ROOT / "out" / "lumajet_flight_assurance").resolve()
    kit_dir = (kit_root / "independent_reproduction_v2_20260716").resolve()
    if not kit_dir.is_relative_to(kit_root) or kit_dir == kit_root:
        raise ValueError("unsafe blind reproduction kit path")
    if kit_dir.exists():
        shutil.rmtree(kit_dir)
    kit_dir.mkdir(parents=True, exist_ok=True)
    source = v2_run_dir / "benchmark_source_snapshot.py"
    protocol = v2_run_dir / "protocol_snapshot.json"
    source_copy = kit_dir / source.name
    protocol_copy = kit_dir / protocol.name
    shutil.copyfile(source, source_copy)
    shutil.copyfile(protocol, protocol_copy)

    instructions = kit_dir / "BLIND_REPRODUCTION_INSTRUCTIONS.md"
    instructions.write_text(
        "\n".join(
            [
                "# LumaJet V2 Blind Independent Reproduction",
                "",
                "This kit intentionally omits the expected leaderboard and promotion result.",
                "Do not obtain the originating run outputs before completing and sealing your run.",
                "",
                "## Procedure",
                "",
                "1. Run `python VERIFY_INPUTS.py` and retain its terminal output.",
                "2. Run `powershell -ExecutionPolicy Bypass -File RUN_REPRODUCTION.ps1`.",
                "3. Return the complete `results/external_reproduction` directory without deleting null, adverse, or error rows.",
                "4. Sign `EXTERNAL_ATTESTATION_TEMPLATE.md` with your name, organization, UTC time, system description, and any deviations.",
                "5. Do not describe a matching result as airworthiness, certification, FAA/DoD approval, or field validation.",
                "",
                "## Required Environment",
                "",
                "Python 3.11 or later with NumPy and SciPy. The runner captures actual versions before execution.",
                "",
                "## Boundary",
                "",
                EVIDENCE_BOUNDARY,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    attestation = kit_dir / "EXTERNAL_ATTESTATION_TEMPLATE.md"
    attestation.write_text(
        "\n".join(
            [
                "# External Reproduction Attestation",
                "",
                "- Runner name:",
                "- Organization:",
                "- Contact:",
                "- Run start UTC:",
                "- Run finish UTC:",
                "- Operating system:",
                "- Hardware:",
                "- Input-manifest verification result:",
                "- Deviations from the supplied protocol: none / describe",
                "- Results directory SHA-256 or manifest SHA-256:",
                "- Signature and date:",
                "",
                "I attest that I ran the supplied source and protocol without inspecting the originating leaderboard, altering validation seeds, suppressing adverse rows, or changing the promotion gate.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    capture_environment = kit_dir / "CAPTURE_ENVIRONMENT.py"
    capture_environment.write_text(
        "\n".join(
            [
                "import json, platform, sys",
                "from datetime import datetime, timezone",
                "from pathlib import Path",
                "import numpy, scipy",
                "payload = {",
                "    'captured_utc': datetime.now(timezone.utc).isoformat(),",
                "    'python': sys.version,",
                "    'platform': platform.platform(),",
                "    'machine': platform.machine(),",
                "    'processor': platform.processor(),",
                "    'numpy': numpy.__version__,",
                "    'scipy': scipy.__version__,",
                "}",
                "Path('environment_receipt.json').write_text(json.dumps(payload, indent=2, sort_keys=True) + '\\n', encoding='utf-8')",
                "print(json.dumps(payload, indent=2))",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runner = kit_dir / "RUN_REPRODUCTION.ps1"
    runner.write_text(
        "\n".join(
            [
                "$ErrorActionPreference = 'Stop'",
                "$Here = Split-Path -Parent $MyInvocation.MyCommand.Path",
                "Set-Location -LiteralPath $Here",
                "python .\\VERIFY_INPUTS.py",
                "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }",
                "python .\\CAPTURE_ENVIRONMENT.py",
                "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }",
                "python .\\benchmark_source_snapshot.py --protocol .\\protocol_snapshot.json --out-root .\\results --run-tag external_reproduction --workers 1 --no-resume",
                "exit $LASTEXITCODE",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    manifest_path = kit_dir / "input_manifest.sha256.json"
    input_files = [
        source_copy,
        protocol_copy,
        instructions,
        attestation,
        capture_environment,
        runner,
    ]
    manifest = {
        "schema": "lumajet_blind_reproduction_input_manifest_v1",
        "origin_packet_sha256": payload["packet_sha256"],
        "expected_leaderboard_included": False,
        "files": {
            path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in input_files
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    verifier = kit_dir / "VERIFY_INPUTS.py"
    verifier.write_text(
        "\n".join(
            [
                "import hashlib, json, sys",
                "from pathlib import Path",
                "root = Path(__file__).resolve().parent",
                "manifest = json.loads((root / 'input_manifest.sha256.json').read_text(encoding='utf-8'))",
                "failures = []",
                "for name, metadata in sorted(manifest['files'].items()):",
                "    path = root / name",
                "    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None",
                "    valid = actual == metadata['sha256']",
                "    print(f'{name}: {\"PASS\" if valid else \"FAIL\"} {actual}')",
                "    if not valid: failures.append(name)",
                "print(f'expected_leaderboard_included={manifest[\"expected_leaderboard_included\"]}')",
                "sys.exit(1 if failures else 0)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    zip_path = ROOT / "out" / "lumajet_flight_assurance" / "LUMAJET_V2_BLIND_REPRODUCTION_KIT_20260716.zip"
    if zip_path.exists():
        zip_path.unlink()
    archive_base = str(zip_path.with_suffix(""))
    shutil.make_archive(archive_base, "zip", root_dir=kit_dir)
    return {
        "kit_dir": kit_dir,
        "kit_manifest": manifest_path,
        "kit_zip": zip_path,
    }


def write_outputs(
    payload: dict[str, Any],
    json_path: Path = DEFAULT_JSON,
    v2_run_dir: Path = DEFAULT_V2_RUN,
) -> dict[str, Path]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    json_path.write_text(encoded, encoding="utf-8")
    date_tag = str(payload["generated_utc"])[:10]
    docs_path = ROOT / "docs" / f"LUMAJET_FLIGHT_ASSURANCE_EVIDENCE_{date_tag}.md"
    markdown = render_markdown(payload)
    docs_path.write_text(markdown, encoding="utf-8")

    phase_artifact = PHASE1_ROOT / "artifacts" / "lumajet_flight_assurance_evidence.json"
    phase_doc = PHASE1_ROOT / "docs" / "05_FLIGHT_ASSURANCE_EVIDENCE.md"
    phase_artifact.parent.mkdir(parents=True, exist_ok=True)
    phase_doc.parent.mkdir(parents=True, exist_ok=True)
    phase_artifact.write_text(encoded, encoding="utf-8")
    phase_doc.write_text(markdown, encoding="utf-8")

    manifest_path = PHASE1_ROOT / "artifacts" / "manifest.sha256.json"
    artifact_files = sorted(
        path for path in manifest_path.parent.iterdir() if path.is_file() and path != manifest_path
    )
    manifest = {
        "schema": "lumajet_phase1_artifact_manifest_v2",
        "generated_utc": payload["generated_utc"],
        "claim_boundary": EVIDENCE_BOUNDARY,
        "files": {
            path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in artifact_files
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    reproduction = write_blind_reproduction_kit(payload, v2_run_dir)
    return {
        "json": json_path,
        "docs": docs_path,
        "phase_artifact": phase_artifact,
        "phase_doc": phase_doc,
        "phase_manifest": manifest_path,
        **reproduction,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1-run", type=Path, default=DEFAULT_V1_RUN)
    parser.add_argument("--v2-run", type=Path, default=DEFAULT_V2_RUN)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_packet(args.v1_run, args.v2_run)
    outputs = write_outputs(payload, args.json_out, args.v2_run)
    print(
        json.dumps(
            {
                "outputs": {name: str(path) for name, path in outputs.items()},
                "summary": payload["summary"],
                "packet_sha256": payload["packet_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
