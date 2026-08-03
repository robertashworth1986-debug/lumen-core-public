from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "external_validation_500_sprint_v1.json"
OUT_JSON = ROOT / "out" / "ops" / "external_validation_500_sprint_latest.json"
OUT_MD = ROOT / "docs" / "EXTERNAL_VALIDATION_500_SPRINT_2026-07-16.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object at {path}")
    return payload


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def artifact_row(path: Path) -> dict[str, Any]:
    return {
        "path": repo_path(path),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    milestones = config["milestones"]
    total = sum(int(row["amount_usd"]) for row in milestones)
    milestone_ids = [row["id"] for row in milestones]
    score_weights = config["evaluator_requirements"]["selection_score_weights"]
    checks = {
        "schema_valid": config.get("schema") == "external_validation_500_sprint.v1",
        "budget_is_exactly_500": config.get("budget_usd") == 500 and total == 500,
        "milestone_ids_unique": len(milestone_ids) == len(set(milestone_ids)),
        "all_payments_outcome_independent": all(
            row.get("result_contingent") is False
            and row.get("paid_if_result_is_negative") is True
            for row in milestones
        ),
        "selection_weights_sum_to_100": sum(score_weights.values()) == 100,
        "spending_requires_human": config["human_authority"].get(
            "spending_automatically_authorized"
        )
        is False,
        "external_contact_requires_human": config["human_authority"].get(
            "external_contact_automatically_authorized"
        )
        is False,
        "operator_cannot_impersonate_evaluator": config["human_authority"].get(
            "operator_may_fill_evaluator_fields"
        )
        is False
        and config["human_authority"].get("operator_may_sign_for_evaluator") is False,
        "free_rails_cost_zero": all(
            row.get("budget_usd") == 0 for row in config["free_validation_rails"]
        ),
        "live_trading_spend_prohibited": any(
            "Live trading capital" in row for row in config["do_not_buy"]
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "milestone_total_usd": total,
    }


def build_payload(*, generated_utc: str | None = None) -> dict[str, Any]:
    config = read_json(CONFIG_PATH)
    config_validation = validate_config(config)
    if not config_validation["passed"]:
        failed = [key for key, value in config_validation["checks"].items() if not value]
        raise ValueError(f"budget config failed closed: {failed}")

    lane = config["evidence_lane"]
    runtime_path = ROOT / lane["runtime_projection_path"]
    handoff_path = ROOT / lane["independent_handoff_path"]
    evaluator_template_path = ROOT / lane["evaluator_protocol_template_path"]
    receipt_template_path = ROOT / lane["reproduction_receipt_template_path"]
    handoff_guide_path = ROOT / lane["handoff_guide_path"]
    source_paths = [
        CONFIG_PATH,
        runtime_path,
        handoff_path,
        evaluator_template_path,
        receipt_template_path,
        handoff_guide_path,
    ]
    missing = [repo_path(path) for path in source_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing sprint sources: {missing}")

    runtime = read_json(runtime_path)
    handoff = read_json(handoff_path)
    frozen = handoff["frozen_snapshot"]
    authority_rows = frozen["authority_coverage"]
    authority_total = len(authority_rows)
    authorities_with_seals = sum(
        1 for row in authority_rows.values() if row["prediction_count"] > 0
    )
    source_artifacts = [artifact_row(path) for path in source_paths]

    payload: dict[str, Any] = {
        "schema": "external_validation_500_sprint_packet.v1",
        "generated_utc": generated_utc or now_utc(),
        "status": config["status"],
        "decision": config["decision"],
        "current_state": {
            "repository_supported_level": 3,
            "level_5_attained": False,
            "runtime_state": runtime["state"],
            "runtime_integrity_gate_passed": runtime["integrity"]["gate_passed"],
            "prediction_count": runtime["sample_state"]["prediction_count"],
            "settlement_count": runtime["sample_state"]["settlement_count"],
            "common_settled_hour_count": runtime["sample_state"][
                "common_settled_hour_count"
            ],
            "authorities_total": authority_total,
            "authorities_with_valid_seals": authorities_with_seals,
            "zero_seal_authorities": frozen["zero_prospective_seal_authorities"],
            "preliminary_gate_ready": runtime["sample_state"]["preliminary_ready"],
            "confirmatory_gate_ready": runtime["sample_state"][
                "confirmatory_ready"
            ],
            "durability_gate_ready": runtime["sample_state"]["durability_ready"],
            "independent_reproduction_complete": handoff[
                "independent_reproduction_complete"
            ],
            "performance_promotion_allowed": handoff[
                "performance_promotion_allowed"
            ],
            "independent_evaluator_named": False,
        },
        "budget": {
            "total_usd": config["budget_usd"],
            "milestones": config["milestones"],
            "estimated_total_hours": sum(
                int(row["estimated_hours"]) for row in config["milestones"]
            ),
            "validation": config_validation,
        },
        "evaluator_requirements": config["evaluator_requirements"],
        "free_validation_rails": config["free_validation_rails"],
        "do_not_buy": config["do_not_buy"],
        "human_authority": config["human_authority"],
        "success_definition": config["success_definition"],
        "official_references": config["official_references"],
        "source_artifacts": source_artifacts,
        "source_input_chain_sha256": canonical_sha256(source_artifacts),
        "claim_boundary": config["claim_boundary"],
    }
    payload["packet_sha256"] = canonical_sha256(payload)
    return payload


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def render_markdown(payload: dict[str, Any]) -> str:
    current = payload["current_state"]
    budget = payload["budget"]
    requirements = payload["evaluator_requirements"]
    milestone_lines = []
    for index, row in enumerate(budget["milestones"], start=1):
        milestone_lines.extend(
            [
                f"{index}. **${row['amount_usd']} - {row['label']}**",
                f"   - Estimated scope: {row['estimated_hours']} hours.",
                f"   - Release only when: {row['release_condition']}",
                "   - Payment is fixed and remains due for a negative result.",
            ]
        )

    rubric_lines = [
        f"| {label.replace('_', ' ').title()} | {weight} |"
        for label, weight in requirements["selection_score_weights"].items()
    ]
    free_lines = [
        f"- **{row['name']} ($0):** {row['purpose']}"
        for row in payload["free_validation_rails"]
    ]
    prohibition_lines = [f"- {row}" for row in payload["do_not_buy"]]
    requirement_lines = [f"- {row}" for row in requirements["required"]]
    source_lines = [
        f"- `{row['path']}` - SHA-256 `{row['sha256']}`"
        for row in payload["source_artifacts"]
    ]
    reference_lines = [
        f"- [{row['name']}]({row['url']}): {row['use']}"
        for row in payload["official_references"]
    ]

    return "\n".join(
        [
            "# $500 External Validation Sprint",
            "",
            f"Generated UTC: `{payload['generated_utc']}`",
            "",
            "## Decision",
            "",
            "**Put the full $500 into one outcome-independent external evaluator engagement.** Do not put it into live trading, model tuning, GPUs, ads, or generic subscriptions. The repository already has the frozen packet, verifier, protocol template, receipt template, and public clean-runner infrastructure; the missing scarce input is a qualified independent human.",
            "",
            f"Status: `{payload['status']}`",
            "",
            "No spending, hiring, account creation, or external contact is authorized by this packet. A human must select the evaluator and approve each milestone.",
            "",
            "## Why This Is The Bottleneck",
            "",
            f"- Current supported maturity remains Level `{current['repository_supported_level']}`; Level 5 attained: `{bool_text(current['level_5_attained'])}`.",
            f"- The active hourly lane has `{current['prediction_count']}` sealed predictions and `{current['settlement_count']}` settlements.",
            f"- Only `{current['authorities_with_valid_seals']}` of `{current['authorities_total']}` authorities have any valid prospective seal; `{', '.join(current['zero_seal_authorities'])}` remain at zero.",
            f"- Common settled hours across the full panel: `{current['common_settled_hour_count']}`.",
            f"- Independent reproduction complete: `{bool_text(current['independent_reproduction_complete'])}`.",
            f"- Performance promotion allowed: `{bool_text(current['performance_promotion_allowed'])}`.",
            "",
            "The current incomplete sample is useful feasibility evidence, not performance validation. The evaluator must preserve that unfavorable state and freeze the next valid protocol before scoring.",
            "",
            "## Exact Milestone Allocation",
            "",
            *milestone_lines,
            "",
            f"Total: **${budget['total_usd']}** across approximately **{budget['estimated_total_hours']} bounded reviewer hours**.",
            "",
            "## Evaluator Selection Rubric",
            "",
            "| Criterion | Weight |",
            "| --- | ---: |",
            *rubric_lines,
            "",
            f"Minimum score: **{requirements['minimum_score']} / 100**. Independence is a hard gate even when the weighted score passes.",
            "",
            *requirement_lines,
            "",
            "## Copy-Paste Evaluator Brief",
            "",
            "> Reproduce and audit a frozen EIA-930 hourly forecasting evidence packet on your own machine. This is a fixed-scope, outcome-independent engagement. You will review and accept or decline the protocol before scoring, verify hashes and settlement arithmetic, preserve missing-authority and negative results, and return raw logs plus an attributable decision memo. You are not being asked to tune the model, endorse LumenCore, prove trading profitability, or reach a positive conclusion. Compensation is fixed by deliverable and does not change with the result.",
            "",
            "Required deliverables:",
            "",
            "1. Conflict disclosure and accept-or-decline protocol memo.",
            "2. Environment fingerprint, verifier logs, rehashed artifacts, discrepancy ledger, and completed reproduction receipt.",
            "3. Dated final memo stating the exact maturity level supported and every material caveat.",
            "",
            "## Use Free Infrastructure",
            "",
            *free_lines,
            "",
            "These rails provide clean execution, preregistration, archival identity, and a public reviewer surface without consuming the $500.",
            "",
            "## Do Not Spend On",
            "",
            *prohibition_lines,
            "",
            "## Economic Pressure-Release Path",
            "",
            "The shortest defensible path is: independent receipt -> paid evidence review or grant-funded validation -> buyer-owned pilot -> only then a bounded economic conversion or license discussion. The receipt is a credibility asset, not revenue by itself, and it does not authorize live trading.",
            "",
            "## Official References",
            "",
            *reference_lines,
            "",
            "## Source Chain",
            "",
            *source_lines,
            "",
            f"Source-input chain SHA-256: `{payload['source_input_chain_sha256']}`",
            "",
            f"Packet SHA-256: `{payload['packet_sha256']}`",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )


def write_outputs(payload: dict[str, Any]) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")


def output_differences(payload: dict[str, Any]) -> list[str]:
    differences: list[str] = []
    expected_json = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    expected_md = render_markdown(payload)
    if not OUT_JSON.is_file() or OUT_JSON.read_text(encoding="utf-8") != expected_json:
        differences.append(f"stale:{repo_path(OUT_JSON)}")
    if not OUT_MD.is_file() or OUT_MD.read_text(encoding="utf-8") != expected_md:
        differences.append(f"stale:{repo_path(OUT_MD)}")
    return differences


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the fail-closed $500 external-validation sprint packet."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when the published outputs do not match a stable rebuild.",
    )
    args = parser.parse_args()

    if args.check:
        if not OUT_JSON.is_file():
            raise FileNotFoundError(OUT_JSON)
        published = read_json(OUT_JSON)
        payload = build_payload(generated_utc=published["generated_utc"])
        differences = output_differences(payload)
        if differences:
            raise RuntimeError(", ".join(differences))
        print("external-validation $500 sprint outputs are current")
        return 0

    payload = build_payload()
    write_outputs(payload)
    print(repo_path(OUT_JSON))
    print(repo_path(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
