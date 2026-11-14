from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from .models import OpportunityDecisionRequest
from .offline import run_offline
from .repository import PublicSafeRepository, PublicSafeRepositoryError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create one public-safe, evidence-bound opportunity decision brief. "
            "The runtime has no external-action tools."
        )
    )
    parser.add_argument("--record-ref")
    parser.add_argument("--as-of-utc")
    parser.add_argument("--request")
    parser.add_argument("--model", default="gpt-5.6")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--list-records", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repository = PublicSafeRepository()
    if args.list_records:
        print(json.dumps({"record_refs": repository.record_refs}, indent=2))
        return 0
    if not args.record_ref or not args.as_of_utc or not args.request:
        print(
            "error: --record-ref, --as-of-utc, and --request are required",
            file=sys.stderr,
        )
        return 2
    try:
        request = OpportunityDecisionRequest(
            record_ref=args.record_ref,
            as_of_utc=args.as_of_utc,
            request=args.request,
        )
        if args.offline:
            brief = run_offline(request)
        else:
            if not os.environ.get("OPENAI_API_KEY", "").strip():
                print(
                    "error: live mode requires OPENAI_API_KEY in the process environment",
                    file=sys.stderr,
                )
                return 2
            from .runtime import run_live

            brief = asyncio.run(run_live(request, model=args.model))
    except (PublicSafeRepositoryError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(brief.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
