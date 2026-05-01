from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = "https://api.grants.gov/v1/api/search2"


@dataclass
class MatchResult:
    score: float
    reasons: List[str]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _blob(hit: Dict[str, Any]) -> str:
    fields = [
        hit.get("title", ""),
        hit.get("oppTitle", ""),
        hit.get("agencyName", ""),
        hit.get("description", ""),
        hit.get("synopsis", ""),
        hit.get("oppNum", ""),
    ]
    return _norm(" ".join(str(v) for v in fields))


def init_profile(path: Path) -> None:
    template = {
        "organization": {
            "legal_name": "Your Organization Name",
            "uei": "",
            "ein": "",
            "sam_registered": False,
            "entity_type": "nonprofit",
            "address": {
                "street1": "",
                "street2": "",
                "city": "",
                "state": "",
                "zip": "",
                "country": "US"
            }
        },
        "contacts": {
            "authorized_rep": {
                "name": "",
                "title": "",
                "email": "",
                "phone": ""
            },
            "project_director": {
                "name": "",
                "title": "",
                "email": "",
                "phone": ""
            }
        },
        "qualification_profile": {
            "eligibility_terms": [
                "nonprofits",
                "small business",
                "county governments"
            ],
            "keyword_targets": [
                "arts",
                "music",
                "workforce",
                "community"
            ],
            "exclude_terms": [
                "tribal only",
                "state agencies only"
            ],
            "agency_allowlist": [],
            "min_award_usd": 0,
            "max_award_usd": 0
        },
        "prefill_defaults": {
            "project_title": "",
            "project_summary": "",
            "statement_of_need": "",
            "expected_outcomes": [
                ""
            ],
            "estimated_federal_funding_usd": 0,
            "estimated_non_federal_funding_usd": 0,
            "budget_narrative": {
                "personnel": "",
                "equipment": "",
                "contractual": "",
                "other_direct_costs": "",
                "indirect_costs": "",
                "cost_share": ""
            },
            "start_date": "",
            "end_date": ""
        }
    }
    save_json(path, template)


def post_search(payload: Dict[str, Any]) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except HTTPError as e:
        raise RuntimeError(f"HTTP error from Grants.gov: {e.code} {e.reason}") from e
    except URLError as e:
        raise RuntimeError(f"Network error calling Grants.gov: {e.reason}") from e


def extract_hits(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = response.get("data", {}) if isinstance(response, dict) else {}
    for key in ("oppHits", "rows", "hits", "opportunities"):
        candidate = data.get(key)
        if isinstance(candidate, list):
            return candidate
    if isinstance(response.get("rows"), list):
        return response["rows"]
    return []


def score_hit(hit: Dict[str, Any], profile: Dict[str, Any]) -> MatchResult:
    qp = profile.get("qualification_profile", {})
    eligibility_terms = [_norm(x) for x in qp.get("eligibility_terms", []) if str(x).strip()]
    keyword_targets = [_norm(x) for x in qp.get("keyword_targets", []) if str(x).strip()]
    exclude_terms = [_norm(x) for x in qp.get("exclude_terms", []) if str(x).strip()]
    agency_allowlist = [_norm(x) for x in qp.get("agency_allowlist", []) if str(x).strip()]

    b = _blob(hit)
    score = 0.0
    reasons: List[str] = []

    agency = _norm(str(hit.get("agencyName", "")))
    if agency_allowlist:
        if any(term in agency for term in agency_allowlist):
            score += 8
            reasons.append("agency_allowlist_match")
        else:
            score -= 6
            reasons.append("agency_not_allowlisted")

    for term in keyword_targets:
        if term and term in b:
            score += 5
            reasons.append(f"keyword:{term}")

    for term in eligibility_terms:
        if term and term in b:
            score += 7
            reasons.append(f"eligibility:{term}")

    for term in exclude_terms:
        if term and term in b:
            score -= 20
            reasons.append(f"exclude:{term}")

    posted = _norm(str(hit.get("oppStatus", hit.get("status", ""))))
    if posted in {"posted", "forecasted"}:
        score += 2
        reasons.append(f"status:{posted}")

    if not reasons:
        reasons.append("no_rule_match")
    return MatchResult(score=score, reasons=reasons)


def normalize_result(hit: Dict[str, Any], score: MatchResult) -> Dict[str, Any]:
    return {
        "oppNum": hit.get("oppNum") or hit.get("number") or "",
        "title": hit.get("title") or hit.get("oppTitle") or "",
        "agencyName": hit.get("agencyName") or "",
        "oppStatus": hit.get("oppStatus") or hit.get("status") or "",
        "openDate": hit.get("openDate") or "",
        "closeDate": hit.get("closeDate") or "",
        "score": round(score.score, 3),
        "reasons": score.reasons,
        "raw": hit,
    }


def search_and_rank(profile: Dict[str, Any], rows: int, keyword: str) -> Dict[str, Any]:
    payload = {
        "rows": rows,
        "keyword": keyword,
        "oppStatuses": "forecasted|posted",
        "sortBy": "openDate|desc",
        "eligibilities": "",
        "agencies": "",
        "fundingCategories": "",
        "fundingInstruments": "",
        "searchOnly": False,
        "resultType": "json",
    }
    response = post_search(payload)
    hits = extract_hits(response)

    ranked: List[Dict[str, Any]] = []
    for hit in hits:
        s = score_hit(hit, profile)
        ranked.append(normalize_result(hit, s))

    ranked.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return {
        "generated_utc": now_utc(),
        "query": payload,
        "total_hits": len(hits),
        "ranked": ranked,
    }


def build_prefill_packet(profile: Dict[str, Any], ranked_item: Dict[str, Any]) -> Dict[str, Any]:
    org = profile.get("organization", {})
    contacts = profile.get("contacts", {})
    defaults = profile.get("prefill_defaults", {})

    return {
        "generated_utc": now_utc(),
        "opportunity": {
            "oppNum": ranked_item.get("oppNum", ""),
            "title": ranked_item.get("title", ""),
            "agencyName": ranked_item.get("agencyName", ""),
            "openDate": ranked_item.get("openDate", ""),
            "closeDate": ranked_item.get("closeDate", ""),
            "score": ranked_item.get("score", 0),
        },
        "autofill": {
            "organization": org,
            "contacts": contacts,
            "project": {
                "title": defaults.get("project_title", ""),
                "summary": defaults.get("project_summary", ""),
                "statement_of_need": defaults.get("statement_of_need", ""),
                "expected_outcomes": defaults.get("expected_outcomes", []),
                "funding": {
                    "federal": defaults.get("estimated_federal_funding_usd", 0),
                    "non_federal": defaults.get("estimated_non_federal_funding_usd", 0),
                },
                "budget_narrative": defaults.get("budget_narrative", {}),
                "period": {
                    "start_date": defaults.get("start_date", ""),
                    "end_date": defaults.get("end_date", ""),
                },
            },
        },
        "notes": [
            "Review this packet before submission.",
            "Some forms require manual attestations/signatures in Workspace.",
            "This packet is intended for fast prefill, not blind auto-submit.",
        ],
    }


def cmd_init(args: argparse.Namespace) -> int:
    path = Path(args.profile)
    if path.exists() and not args.force:
        print(f"Profile already exists: {path}")
        print("Use --force to overwrite.")
        return 1
    init_profile(path)
    print(f"Created profile template: {path}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    profile = load_json(Path(args.profile))
    result = search_and_rank(profile, rows=args.rows, keyword=args.keyword)

    out_path = Path(args.out)
    save_json(out_path, result)

    ranked = result.get("ranked", [])
    print(f"Saved ranked opportunities: {out_path}")
    print(f"Hits: {result.get('total_hits', 0)}")
    print("Top matches:")
    for item in ranked[: min(len(ranked), args.top)]:
        print(
            f"- score={item.get('score', 0):>5}  oppNum={item.get('oppNum','')}  title={item.get('title','')[:80]}"
        )
    return 0


def cmd_prefill(args: argparse.Namespace) -> int:
    profile = load_json(Path(args.profile))
    ranked_bundle = load_json(Path(args.results))
    ranked = ranked_bundle.get("ranked", [])

    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for item in ranked[: args.top]:
        opp = str(item.get("oppNum", "")).strip() or f"unknown_{count+1}"
        packet = build_prefill_packet(profile, item)
        save_json(out_dir / f"prefill_{opp}.json", packet)
        count += 1

    print(f"Created {count} prefill packet(s) in {out_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Search Grants.gov opportunities and generate autofill packets from your qualification profile."
    )
    sub = p.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init-profile", help="Create a profile template.")
    p_init.add_argument("--profile", default="grants_profile.json")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_search = sub.add_parser("search", help="Search and rank opportunities.")
    p_search.add_argument("--profile", default="grants_profile.json")
    p_search.add_argument("--keyword", default="")
    p_search.add_argument("--rows", type=int, default=100)
    p_search.add_argument("--top", type=int, default=15)
    p_search.add_argument("--out", default="out/grants/grants_ranked.json")
    p_search.set_defaults(func=cmd_search)

    p_prefill = sub.add_parser("prefill", help="Generate prefill packets for top ranked opportunities.")
    p_prefill.add_argument("--profile", default="grants_profile.json")
    p_prefill.add_argument("--results", default="out/grants/grants_ranked.json")
    p_prefill.add_argument("--top", type=int, default=10)
    p_prefill.add_argument("--outdir", default="out/grants/prefill_packets")
    p_prefill.set_defaults(func=cmd_prefill)

    return p


def main(argv: List[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
