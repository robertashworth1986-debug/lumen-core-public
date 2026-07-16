from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile
from typing import Any


STACK_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GAUNTLET_ROOT = STACK_ROOT / "out" / "frequency_cluster_truth_gauntlet"
DEFAULT_PROTOCOL = STACK_ROOT / "config" / "frequency_cluster_truth_gauntlet_protocol_v1.json"
DEFAULT_RUNNER = STACK_ROOT / "code" / "frequency_cluster_truth_gauntlet.py"
DEFAULT_DOC = STACK_ROOT / "docs" / "FREQUENCY_CLUSTER_TRUTH_GAUNTLET_2026-07-16.md"
DEFAULT_REVIEWER_JSON = STACK_ROOT / "out" / "ops" / "frequency_cluster_reviewer_decision_latest.json"
DEFAULT_ERRATUM = (
    STACK_ROOT
    / "evidence"
    / "external_validation"
    / "frequency_cluster_protocol_timestamp_erratum_20260716.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(content.rstrip("\r\n") + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, indent=2))


def find_primary_run(gauntlet_root: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    audit_path = gauntlet_root / "run_identity_audit.json"
    if not audit_path.exists():
        raise FileNotFoundError(f"run identity audit missing: {audit_path}")
    audit = read_json(audit_path)
    groups = audit.get("groups") or []
    scored_groups = [
        group
        for group in groups
        if any(member.get("contains_scored_holdout") for member in group.get("members") or [])
    ]
    if not scored_groups:
        raise RuntimeError("no scored frequency-cluster identity group found")
    group = scored_groups[-1]
    primary_run = Path(str(group["primary_run"])).resolve()
    summary = read_json(primary_run / "summary.json")
    if not isinstance(summary.get("aggregate"), dict):
        raise RuntimeError("primary run does not contain aggregate results")
    return primary_run, summary, group


def mean_pair_percentage(summary: dict[str, Any]) -> float:
    rows = summary.get("pair_results") or []
    return sum(float(row["worst_baseline_improvement_pct"]) for row in rows) / max(1, len(rows))


def commitment_payload(summary: dict[str, Any]) -> dict[str, Any]:
    aggregate = summary["aggregate"]
    return {
        "decision": summary["decision"],
        "selected_periods_days": summary["selected_periods_days"],
        "eligible_pair_count": summary["eligible_pair_count"],
        "aggregate_improvement_pct_vs_global_strongest_baseline": aggregate[
            "aggregate_improvement_pct_vs_strongest_named_baseline"
        ],
        "mean_pair_worst_baseline_improvement_pct": mean_pair_percentage(summary),
        "positive_pair_count": aggregate["positive_pair_count"],
        "individually_promoted_pairs": aggregate["individually_promoted_pairs"],
        "gate_checks": aggregate["gate_checks"],
        "evidence_receipt_sha256": summary["evidence_receipt_sha256"],
    }


def build_reviewer_decision(
    primary_run: Path,
    summary: dict[str, Any],
    identity_group: dict[str, Any],
    protocol_path: Path,
    runner_path: Path,
    erratum_path: Path,
) -> dict[str, Any]:
    aggregate = summary["aggregate"]
    pair_percentages = [
        float(row["worst_baseline_improvement_pct"])
        for row in summary.get("pair_results") or []
    ]
    duplicate_runs = identity_group.get("duplicate_scored_runs") or []
    minimum_holm = min(
        float(row.get("phase_shift_p_holm") or 1.0)
        for row in summary.get("pair_results") or []
    )
    return {
        "schema": "frequency_cluster_reviewer_decision_v1",
        "primary_run": str(primary_run),
        "primary_summary_sha256": sha256_file(primary_run / "summary.json"),
        "official_source": {
            "provider": "Kraken",
            "source_authentic": bool(summary.get("source_authentic")),
            "meaning": "Normalized inputs were retrieved from Kraken public endpoints and hash-sealed.",
            "does_not_mean": "Independent validation, Kraken endorsement, or permission to trade.",
        },
        "frozen_test": {
            "protocol": str(protocol_path),
            "protocol_sha256": sha256_file(protocol_path),
            "current_locked_runner": str(runner_path),
            "current_locked_runner_sha256": sha256_file(runner_path),
            "primary_scoring_runner_sha256": summary.get("benchmark_source_sha256"),
            "current_runner_matches_primary_scoring_hash": (
                sha256_file(runner_path) == summary.get("benchmark_source_sha256")
            ),
            "primary_run_contains_scoring_source_snapshot": False,
            "provenance_disclosure": (
                "The primary manifest recorded the scoring-source hash but the run directory did "
                "not include a source snapshot. The supplied runner adds duplicate-input blocking "
                "and reviewer-report hardening after the primary score. External output is an "
                "implementation-version reproduction, not a bit-for-bit executable replay."
            ),
            "timestamp_erratum": {
                "path": "evidence/external_validation/frequency_cluster_protocol_timestamp_erratum_20260716.json",
                "sha256": sha256_file(erratum_path),
                "recorded_frozen_utc": "2026-07-16T02:15:00Z",
                "intended_frozen_utc": "2026-07-16T01:15:00Z",
                "scoring_rules_or_outputs_changed": False,
            },
            "selected_periods_days": summary["selected_periods_days"],
            "eligible_pairs": summary["eligible_pair_count"],
            "holdout_used_for_selection": False,
        },
        "diagnostic_global_comparison": {
            "improvement_pct_vs_one_global_strongest_named_baseline": aggregate[
                "aggregate_improvement_pct_vs_strongest_named_baseline"
            ],
            "pair_bootstrap_ci95_pct": aggregate[
                "aggregate_improvement_pct_pair_bootstrap_ci95"
            ],
            "promotion_metric": False,
        },
        "reviewer_grade_gate": {
            "mean_pair_improvement_pct_vs_each_pairs_strongest_baseline": (
                sum(pair_percentages) / max(1, len(pair_percentages))
            ),
            "positive_pairs": aggregate["positive_pair_count"],
            "total_pairs": aggregate["pair_count"],
            "positive_pair_fraction": aggregate["positive_pair_fraction"],
            "required_positive_pair_fraction": 0.60,
            "mean_worst_baseline_effect": aggregate["mean_worst_baseline_effect"],
            "mean_worst_baseline_effect_pair_bootstrap_ci95": aggregate[
                "mean_worst_baseline_effect_pair_bootstrap_ci95"
            ],
            "minimum_leave_one_pair_out_effect": aggregate[
                "minimum_leave_one_pair_out_effect"
            ],
            "minimum_holm_adjusted_phase_p": minimum_holm,
            "individually_promoted_pairs": aggregate["individually_promoted_pairs"],
            "gate_checks": aggregate["gate_checks"],
            "gate_pass": aggregate["gate_pass"],
        },
        "duplicate_run_audit": {
            "run_identity_sha256": identity_group["run_identity_sha256"],
            "scored_run_count": identity_group["scored_run_count"],
            "duplicate_scored_runs": duplicate_runs,
            "evidence_receipts_match": identity_group["evidence_receipts_match"],
            "duplicates_count_as_independent_confirmation": False,
            "future_identical_inputs_are_blocked_before_scoring": True,
        },
        "decision": summary["decision"],
        "execution_authorized": False,
        "independently_validated": False,
        "safest_next_action": (
            "Have one outside reviewer run the blind reproduction kit and return its summary, "
            "manifest terminal hash, environment receipt, and signed attestation. Keep economic "
            "action disabled regardless of a matching internal result until a prospective source "
            "window also passes."
        ),
    }


def build_markdown(decision: dict[str, Any]) -> str:
    global_result = decision["diagnostic_global_comparison"]
    gate = decision["reviewer_grade_gate"]
    duplicate = decision["duplicate_run_audit"]
    interval = global_result["pair_bootstrap_ci95_pct"]
    effect_interval = gate["mean_worst_baseline_effect_pair_bootstrap_ci95"]
    lines = [
        "# Frequency-Cluster Truth Gauntlet",
        "",
        "## Decision",
        "",
        f"`{decision['decision']}`",
        "",
        "The normalized inputs are source-authentic Kraken public data. The result is internally "
        "hash-sealed, not independently validated, not exchange endorsed, and not permission to trade.",
        "",
        "## Measured Result",
        "",
        f"- Fixed major-pair cohort: `{gate['total_pairs']}` pairs",
        f"- Development-selected periods: `{', '.join(str(value) for value in decision['frozen_test']['selected_periods_days'])}` days",
        f"- Diagnostic cohort improvement versus one globally strongest baseline: `{global_result['improvement_pct_vs_one_global_strongest_named_baseline']:.6f}%`",
        f"- Diagnostic pair-bootstrap CI95: `[{interval[0]:.6f}%, {interval[1]:.6f}%]`",
        f"- Reviewer metric, mean pair improvement versus each pair's strongest baseline: `{gate['mean_pair_improvement_pct_vs_each_pairs_strongest_baseline']:.6f}%`",
        f"- Mean worst-baseline effect CI95: `[{effect_interval[0]:.9f}, {effect_interval[1]:.9f}]`",
        f"- Positive pair diagnostics: `{gate['positive_pairs']}/{gate['total_pairs']}` (`{gate['positive_pair_fraction']:.1%}`; required `60.0%`)",
        f"- Individually promoted after block CI and Holm correction: `{len(gate['individually_promoted_pairs'])}`",
        f"- Minimum leave-one-pair-out effect: `{gate['minimum_leave_one_pair_out_effect']:.9f}`",
        "",
        "## Gate Checks",
        "",
    ]
    for name, passed in gate["gate_checks"].items():
        lines.append(f"- `{name}`: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(
        [
            "",
            "## Duplicate Integrity",
            "",
            f"- Run identity: `{duplicate['run_identity_sha256']}`",
            f"- Scored computations with that identity: `{duplicate['scored_run_count']}`",
            f"- Duplicate scored runs: `{len(duplicate['duplicate_scored_runs'])}`",
            f"- Matching evidence receipts: `{str(duplicate['evidence_receipts_match']).lower()}`",
            "- Duplicate computations count as independent confirmation: `false`",
            "- Identical protocol plus input hashes are now blocked before inference: `true`",
            "",
            "## Runner Provenance",
            "",
            f"- Primary scoring runner hash: `{decision['frozen_test']['primary_scoring_runner_sha256']}`",
            f"- Supplied locked runner hash: `{decision['frozen_test']['current_locked_runner_sha256']}`",
            f"- Hashes match: `{str(decision['frozen_test']['current_runner_matches_primary_scoring_hash']).lower()}`",
            "- Exact primary source snapshot stored in the run: `false`",
            "- Scope: current runner adds duplicate-input blocking and reviewer-report hardening; "
            "the external run is an implementation-version reproduction, not a bit-for-bit executable replay.",
            "",
            "## Protocol Timestamp Erratum",
            "",
            "- The immutable protocol records `2026-07-16T02:15:00Z` in `frozen_utc`.",
            "- The intended value was `2026-07-16T01:15:00Z`; this was a one-hour UTC transcription error.",
            "- Local filesystem chronology places protocol creation at `2026-07-16T01:12:45.5556419Z` and the primary summary at `2026-07-16T01:23:55.9023038Z`.",
            "- The original protocol remains unchanged because its hash is already linked to the run.",
            "- Scoring rules, inputs, numeric outputs, and the rejection decision are unchanged.",
            "",
            "## What Would Unlock Promotion",
            "",
            "1. One outside reviewer runs the blind kit without seeing the expected leaderboard.",
            "2. The reviewer returns the summary, terminal manifest hash, environment receipt, and signed attestation.",
            "3. A future prospectively sealed source window independently clears the same frozen gate.",
            "4. Economic action remains disabled until those steps pass and operational risk controls are separately reviewed.",
            "",
        ]
    )
    return "\n".join(lines)


def verification_script() -> str:
    return r'''from __future__ import annotations

import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / "input_manifest.json").read_text(encoding="utf-8"))
failed = []
for entry in manifest["entries"]:
    path = root / entry["path"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "MISSING"
    status = "PASS" if digest == entry["sha256"] else "FAIL"
    print(f"{status} {entry['path']} {digest}")
    if status == "FAIL":
        failed.append(entry["path"])
raise SystemExit(1 if failed else 0)
'''


def run_script() -> str:
    return r'''$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
python (Join-Path $Root "verify_inputs.py")
python (Join-Path $Root "code\frequency_cluster_truth_gauntlet.py") `
  --protocol (Join-Path $Root "config\frequency_cluster_truth_gauntlet_protocol_v1.json") `
  --input-dir (Join-Path $Root "inputs") `
  --out-root (Join-Path $Root "reviewer_output")
Write-Host "Return reviewer_output plus signed_reviewer_attestation.json to the requester."
'''


def kit_readme(primary_runner_hash: str, supplied_runner_hash: str) -> str:
    return f"""# Blind Frequency-Cluster Reproduction Kit v1.2

This kit contains source-authentic normalized Kraken inputs, the frozen protocol, a locked runner,
and input verification. It intentionally omits the expected leaderboard and result values.

Provenance disclosure: the primary run recorded scoring-source hash `{primary_runner_hash}` but did
not store that exact source snapshot. The supplied runner hash is `{supplied_runner_hash}` and adds
duplicate-input blocking plus reviewer-report hardening. Treat this as an implementation-version
reproduction, not a bit-for-bit replay of the original executable.

The protocol's immutable `frozen_utc` value contains a disclosed one-hour UTC transcription error.
Read `PROTOCOL_TIMESTAMP_ERRATUM.json`; scoring rules, inputs, outputs, and the rejection decision
are unchanged.

1. Run `python verify_inputs.py`.
2. Record `python --version`, the operating system, NumPy version, and Requests version in
   `signed_reviewer_attestation.json`.
3. Run `RUN_REPRODUCTION.ps1` on Windows, or invoke the equivalent Python command shown there.
4. Do not edit the protocol, runner, or input files.
5. Return the entire `reviewer_output` directory and completed attestation.

This is a research reproduction. It does not authorize orders, capital deployment, or operational use.
"""


def build_kit(args: argparse.Namespace) -> dict[str, Any]:
    gauntlet_root = Path(args.gauntlet_root).resolve()
    protocol_path = Path(args.protocol).resolve()
    runner_path = Path(args.runner).resolve()
    doc_path = Path(args.doc).resolve()
    reviewer_json_path = Path(args.reviewer_json).resolve()
    erratum_path = Path(args.erratum).resolve()
    primary_run, summary, identity_group = find_primary_run(gauntlet_root)

    reviewer_decision = build_reviewer_decision(
        primary_run,
        summary,
        identity_group,
        protocol_path,
        runner_path,
        erratum_path,
    )
    write_json(reviewer_json_path, reviewer_decision)
    write_text(doc_path, build_markdown(reviewer_decision))

    kit_dir = gauntlet_root / "independent_reproduction_v1_2_20260716"
    if kit_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing kit: {kit_dir}")
    (kit_dir / "code").mkdir(parents=True)
    (kit_dir / "config").mkdir(parents=True)
    shutil.copytree(primary_run / "inputs", kit_dir / "inputs")
    shutil.copy2(runner_path, kit_dir / "code" / runner_path.name)
    shutil.copy2(protocol_path, kit_dir / "config" / protocol_path.name)
    shutil.copy2(erratum_path, kit_dir / "PROTOCOL_TIMESTAMP_ERRATUM.json")

    commitment = commitment_payload(summary)
    write_json(
        kit_dir / "expected_result_commitment.json",
        {
            "schema": "frequency_cluster_blind_result_commitment_v1",
            "commitment_sha256": sha256_payload(commitment),
            "values_withheld_until_reviewer_returns_results": True,
            "commitment_created_from_primary_internal_receipt": summary[
                "evidence_receipt_sha256"
            ],
        },
    )
    write_json(
        kit_dir / "signed_reviewer_attestation.json",
        {
            "schema": "frequency_cluster_external_reviewer_attestation_v1",
            "reviewer_name": "",
            "reviewer_organization": "",
            "reviewer_contact": "",
            "execution_utc": "",
            "operating_system": "",
            "python_version": "",
            "numpy_version": "",
            "requests_version": "",
            "input_verification_passed": None,
            "protocol_or_code_modified": None,
            "reviewer_output_manifest_terminal_sha256": "",
            "reviewer_observed_decision": "",
            "attestation": (
                "I ran the supplied verifier and benchmark without editing the frozen protocol, "
                "runner, or normalized source inputs. I report the observed output regardless of result."
            ),
            "signature": "",
            "signature_date": "",
        },
    )
    write_text(kit_dir / "verify_inputs.py", verification_script())
    write_text(kit_dir / "RUN_REPRODUCTION.ps1", run_script())
    write_text(
        kit_dir / "README.md",
        kit_readme(
            str(summary.get("benchmark_source_sha256") or "UNKNOWN"),
            sha256_file(runner_path),
        ),
    )

    entries: list[dict[str, Any]] = []
    terminal = "0" * 64
    for path in sorted(
        [item for item in kit_dir.rglob("*") if item.is_file() and item.name != "input_manifest.json"],
        key=lambda item: str(item.relative_to(kit_dir)).lower(),
    ):
        relative = str(path.relative_to(kit_dir)).replace("\\", "/")
        digest = sha256_file(path)
        size = path.stat().st_size
        terminal = hashlib.sha256(
            f"{terminal}\n{relative}\n{digest}\n{size}".encode("utf-8")
        ).hexdigest()
        entries.append({"path": relative, "sha256": digest, "bytes": size})
    input_manifest = {
        "schema": "frequency_cluster_blind_kit_manifest_v1_2",
        "primary_run_identity_sha256": identity_group["run_identity_sha256"],
        "expected_result_values_included": False,
        "entry_count": len(entries),
        "entries": entries,
        "terminal_chain_sha256": terminal,
    }
    write_json(kit_dir / "input_manifest.json", input_manifest)

    zip_path = gauntlet_root / "FREQUENCY_CLUSTER_BLIND_REPRODUCTION_KIT_V1_2_20260716.zip"
    if zip_path.exists():
        raise FileExistsError(f"refusing to overwrite existing zip: {zip_path}")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(item for item in kit_dir.rglob("*") if item.is_file()):
            archive.write(path, arcname=str(path.relative_to(kit_dir)).replace("\\", "/"))

    receipt = {
        "schema": "frequency_cluster_reproduction_kit_receipt_v1_2",
        "primary_run": str(primary_run),
        "kit_dir": str(kit_dir),
        "kit_zip": str(zip_path),
        "kit_zip_sha256": sha256_file(zip_path),
        "kit_zip_bytes": zip_path.stat().st_size,
        "input_manifest_terminal_chain_sha256": terminal,
        "reviewer_decision_json": str(reviewer_json_path),
        "reviewer_decision_sha256": sha256_file(reviewer_json_path),
        "reviewer_markdown": str(doc_path),
        "reviewer_markdown_sha256": sha256_file(doc_path),
        "external_execution_status": "KIT_READY_EXTERNAL_REVIEWER_NOT_YET_RUN",
        "independently_validated": False,
    }
    write_json(gauntlet_root / "reproduction_kit_receipt.json", receipt)
    print(
        "FREQUENCY_REPRO_KIT "
        f"status={receipt['external_execution_status']} zip_sha256={receipt['kit_zip_sha256']} "
        f"bytes={receipt['kit_zip_bytes']}"
    )
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a blind frequency-cluster external reproduction kit.")
    parser.add_argument("--gauntlet-root", default=str(DEFAULT_GAUNTLET_ROOT))
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--runner", default=str(DEFAULT_RUNNER))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    parser.add_argument("--reviewer-json", default=str(DEFAULT_REVIEWER_JSON))
    parser.add_argument("--erratum", default=str(DEFAULT_ERRATUM))
    return parser.parse_args()


def main() -> int:
    build_kit(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
