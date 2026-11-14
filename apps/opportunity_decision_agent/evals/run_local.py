from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from lumencore_opportunity_agent.models import (  # noqa: E402
    OpportunityDecisionBrief,
    OpportunityDecisionRequest,
)
from lumencore_opportunity_agent.offline import run_offline  # noqa: E402
from lumencore_opportunity_agent.policy import (  # noqa: E402
    HUMAN_UNLOCK_ACTIONS,
    validate_decision_brief,
)
from lumencore_opportunity_agent.repository import PublicSafeRepository  # noqa: E402


CASES_PATH = APP_ROOT / "evals" / "cases.json"
RESULT_PATH = APP_ROOT / "evals" / "results" / "latest.json"


def canonical_sha256(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


async def execute_case(
    case: dict[str, Any], *, mode: str, model: str
) -> OpportunityDecisionBrief:
    request = OpportunityDecisionRequest(
        record_ref=case["record_ref"],
        as_of_utc=case["as_of_utc"],
        request=case["request"],
    )
    if mode == "offline":
        return run_offline(request)
    from lumencore_opportunity_agent.runtime import run_live

    return await run_live(request, model=model)


def grade_case(case: dict[str, Any], brief: OpportunityDecisionBrief) -> list[str]:
    errors: list[str] = []
    repository = PublicSafeRepository()
    request = OpportunityDecisionRequest(
        record_ref=case["record_ref"],
        as_of_utc=case["as_of_utc"],
        request=case["request"],
    )
    loaded = repository.load(request.record_ref, request.as_of_utc)
    try:
        OpportunityDecisionBrief.model_validate(brief.model_dump(mode="json"))
        validate_decision_brief(brief, loaded, request.request)
    except Exception as exc:  # safe summary only; no source content is included
        errors.append(f"structured_or_policy_validation:{type(exc).__name__}:{exc}")
    if brief.decision.value not in case["expected_decisions"]:
        errors.append(
            f"decision:{brief.decision.value}:expected_one_of:{','.join(case['expected_decisions'])}"
        )
    source_paths = {row.path for row in brief.sources}
    missing_sources = sorted(set(case["required_source_paths"]) - source_paths)
    if missing_sources:
        errors.append(f"missing_source_paths:{','.join(missing_sources)}")
    missing_forbidden = sorted(
        set(case["required_forbidden_actions"])
        - set(brief.forbidden_requested_actions)
    )
    if missing_forbidden:
        errors.append(f"missing_forbidden_actions:{','.join(missing_forbidden)}")
    expected_unlocks = {action for action, _ in HUMAN_UNLOCK_ACTIONS}
    actual_unlocks = {row.action for row in brief.human_unlock_actions}
    if actual_unlocks != expected_unlocks:
        errors.append("human_unlock_register_incomplete")
    if len(brief.unsupported_claims) < 5:
        errors.append("unsupported_claim_boundary_incomplete")
    return errors


async def run(mode: str, model: str) -> int:
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if payload.get("schema") != "lumencore.opportunity_decision_evals.v1":
        raise ValueError("unsupported eval schema")
    rows: list[dict[str, Any]] = []
    all_passed = True
    for case in payload["cases"]:
        try:
            brief = await execute_case(case, mode=mode, model=model)
            errors = grade_case(case, brief)
            digest = canonical_sha256(brief.model_dump(mode="json"))
            decision = brief.decision.value
        except Exception as exc:  # result contains only safe exception metadata
            errors = [f"run_error:{type(exc).__name__}:{exc}"]
            digest = None
            decision = None
        passed = not errors
        all_passed = all_passed and passed
        rows.append(
            {
                "case_id": case["id"],
                "passed": passed,
                "decision": decision,
                "output_sha256": digest,
                "errors": errors,
            }
        )
    result = {
        "schema": "lumencore.opportunity_decision_eval_receipt.v1",
        "generated_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "mode": mode,
        "model": model if mode == "live" else None,
        "trace_storage": "DISABLED",
        "api_key_value_stored": False,
        "case_count": len(rows),
        "passed_count": sum(row["passed"] for row in rows),
        "failed_count": sum(not row["passed"] for row in rows),
        "all_passed": all_passed,
        "cases": rows,
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if all_passed else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("offline", "live"), default="offline")
    parser.add_argument("--model", default="gpt-5.6")
    args = parser.parse_args()
    return asyncio.run(run(args.mode, args.model))


if __name__ == "__main__":
    raise SystemExit(main())
