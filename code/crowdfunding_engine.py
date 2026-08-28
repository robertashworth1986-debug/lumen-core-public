"""
crowdfunding_engine.py  ─  LumenCore Crowdfunding Intelligence Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Draft-only crowdfunding research and campaign-copy builder.

CAPABILITIES:
  1. PLATFORM SCOUT  — ranks crowdfunding platforms by fit for LumenCore
  2. CAMPAIGN WRITER — generates complete campaign copy (headline, pitch, perks,
                       FAQ, risk disclosures, investor narrative) per platform
  3. EQUITY TARGETS  — Republic, Wefunder, StartEngine (Reg CF / Reg D ready)
  4. REWARDS TARGETS — Kickstarter, Indiegogo (product/tech tier)
  5. EVIDENCE MAP    — cites only bounded public evidence and negative findings
  6. SCOPE DRAFT     — proposes a use-of-funds structure without setting legal terms
  7. APPROVAL QUEUE  — remains pending for founder, legal, and platform review

Usage:
  python crowdfunding_engine.py generate  --platform republic
  python crowdfunding_engine.py generate  --platform all
  python crowdfunding_engine.py scout
  python crowdfunding_engine.py list-queue
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parents[1]
CODE         = ROOT / "code"
OUT_CF       = ROOT / "out" / "crowdfunding"
OUT_QUEUE_CF = ROOT / "out" / "crowdfunding_approval_queue.json"
PROFILE_PATH = CODE / "grants_profile_lumencore.json"
EVIDENCE_PATH = ROOT / "investor_and_grant_evidence.json"
INVESTOR_BRIEF = ROOT / "INVESTOR_BRIEF.md"

# Campaigns, securities terms, prices, perks, and external publication remain
# founder-controlled. Generation creates a draft; it never authorizes use.
AUTO_APPROVE_ALWAYS = False
DEFAULT_APPROVAL_STATE = "APPROVED" if AUTO_APPROVE_ALWAYS else "PENDING_HUMAN_APPROVAL"
AUTO_APPROVAL_NOTE = "Human approval, current platform verification, and qualified legal review required"

# ─── Platform Definitions ─────────────────────────────────────────────────────

PLATFORMS: List[Dict[str, Any]] = [
    {
        "id": "republic",
        "name": "Republic",
        "url": "https://republic.com/raise",
        "type": "equity_cf",           # Reg CF (up to $5M from public)
        "reg_framework": "Reg CF / Reg D",
        "max_raise_usd": 5_000_000,
        "typical_raise_usd": 500_000,
        "audience": "retail + accredited investors",
        "fit_score": 95,
        "fit_reasons": [
            "Top tier for deep tech / AI / infrastructure",
            "Strong DOE/government track record companies",
            "Investor community values social impact + ROI",
            "Accept for-profit small business with evidence",
        ],
        "fees": "6% success fee + 2% equity to Republic",
        "timeline_days": 60,
    },
    {
        "id": "wefunder",
        "name": "Wefunder",
        "url": "https://wefunder.com/raise",
        "type": "equity_cf",
        "reg_framework": "Reg CF",
        "max_raise_usd": 5_000_000,
        "typical_raise_usd": 300_000,
        "audience": "community investors",
        "fit_score": 88,
        "fit_reasons": [
            "Strong community/mission-driven angle",
            "Technology + climate infrastructure high performers",
            "Founder storytelling matters — Robert's story is compelling",
        ],
        "fees": "7.5% success fee",
        "timeline_days": 60,
    },
    {
        "id": "startengine",
        "name": "StartEngine",
        "url": "https://www.startengine.com/raise-money",
        "type": "equity_cf",
        "reg_framework": "Reg CF / Reg A+",
        "max_raise_usd": 75_000_000,
        "typical_raise_usd": 1_000_000,
        "audience": "retail investors + media amplification",
        "fit_score": 82,
        "fit_reasons": [
            "Large retail investor base for tech plays",
            "Reg A+ allows up to $75M — path to full institutional round",
            "Strong marketing team helps with visibility",
        ],
        "fees": "8% success fee + 2% equity warrants",
        "timeline_days": 90,
    },
    {
        "id": "kickstarter",
        "name": "Kickstarter",
        "url": "https://www.kickstarter.com/learn",
        "type": "rewards",
        "reg_framework": "None (rewards-based)",
        "max_raise_usd": 10_000_000,
        "typical_raise_usd": 50_000,
        "audience": "tech enthusiasts, early adopters",
        "fit_score": 55,
        "fit_reasons": [
            "Better fit for consumer-facing product (dashboard access tier)",
            "Can generate early user base + press coverage",
            "Does NOT give equity — rewards only",
        ],
        "fees": "5% success fee + 3–5% payment processing",
        "timeline_days": 30,
    },
    {
        "id": "indiegogo",
        "name": "Indiegogo",
        "url": "https://go.indiegogo.com/raise-money",
        "type": "rewards",
        "reg_framework": "None (rewards-based)",
        "max_raise_usd": 5_000_000,
        "typical_raise_usd": 30_000,
        "audience": "tech and innovation community",
        "fit_score": 50,
        "fit_reasons": [
            "Flexible funding (keep what you raise even if not fully funded)",
            "InDemand feature allows ongoing post-campaign sales",
        ],
        "fees": "5% platform fee + 3% payment processing",
        "timeline_days": 30,
    },
    {
        "id": "ifundwomen",
        "name": "IFundWomen (open to diverse founders)",
        "url": "https://ifundwomen.com",
        "type": "grants_plus_rewards",
        "reg_framework": "None",
        "max_raise_usd": 100_000,
        "typical_raise_usd": 10_000,
        "audience": "mission-driven and social impact funders",
        "fit_score": 40,
        "fit_reasons": ["Smaller pool but high grant-to-donation ratio"],
        "fees": "5% platform fee",
        "timeline_days": 45,
    },
]

# ─── LumenCore Investment Narrative ───────────────────────────────────────────

COMPANY_NARRATIVE = {
    "headline": "LumenCore — Evidence-Governed Evaluation Architecture",
    "tagline": "One authorized source. One accepted baseline. One bounded decision.",
    "problem": (
        "Technical teams often have a promising AI, analytics, or engineering result but lack a "
        "reproducible way to determine whether it beats an accepted incumbent under rules fixed "
        "before scoring."
    ),
    "solution": (
        "LumenCore is a founder-built proof-to-pilot architecture. ProofLock preserves evidence "
        "identity and authority boundaries; the Frozen Delta method locks source rights, baseline, "
        "metric, threshold, holdout, failure rules, and allowed claims before a bounded comparison."
    ),
    "traction": [
        "Merged Proof Capsule verifier and deployed bounded ProofLock demonstration",
        "Pinned first-party EIA/CODECHECK replay package prepared for non-author execution",
        "Held-out public AIS controlled-injection evidence for HarborSentinel",
        "Frozen synthetic DICE and MissionWeave benchmarks with negative findings retained",
        "Grant-conformance and paper-market control implementations with final submission and live-order authority withheld",
        "No signed paid scope, buyer result, revenue, external validation, or field deployment is claimed",
    ],
    "market": (
        "No public TAM, SAM, SOM, valuation, fundraising target, or investor-return claim is "
        "authorized by this draft. Any market sizing requires current cited sources, explicit "
        "assumptions, founder review, and qualified legal review."
    ),
    "use_of_funds": {
        "engineering_and_product": 0.40,
        "go_to_market_and_sales": 0.25,
        "ip_and_legal": 0.10,
        "operations_and_compliance": 0.10,
        "reserve_and_working_capital": 0.15,
    },
    "team": "Robert Ashworth — Founder and hands-on systems architect for the LumenCore proof-to-pilot architecture.",
    "vision": (
        "Help technical decision owners reject weak claims earlier and advance only candidates that "
        "survive buyer-owned baselines, locked metrics, retained failures, and reviewable evidence."
    ),
}

PERK_TIERS = [
    {"tier": "Observer", "amount_usd": 25,  "perks": ["LumenCore public dashboard access (12 months)", "Backer newsletter"]},
    {"tier": "Analyst",  "amount_usd": 100, "perks": ["Observer perks", "Monthly intelligence briefing PDF", "Early access to proof packs"]},
    {"tier": "Operator", "amount_usd": 500, "perks": ["Analyst perks", "Beta API access (when available)", "Name in credits"]},
    {"tier": "Partner",  "amount_usd": 2500,"perks": ["Operator perks", "1:1 30-min strategy call with Robert", "Custom sector report"]},
    {"tier": "Founding Supporter", "amount_usd": 10000, "perks": ["Partner perks", "Potential non-financial supporter recognition subject to platform rules and founder approval"]},
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _approval_fields() -> Dict[str, Any]:
    fields: Dict[str, Any] = {"approval_state": DEFAULT_APPROVAL_STATE}
    if AUTO_APPROVE_ALWAYS:
        fields["approved_utc"] = now_utc()
        fields["reviewer_notes"] = AUTO_APPROVAL_NOTE
    return fields

def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_queue() -> List[Dict[str, Any]]:
    if OUT_QUEUE_CF.exists():
        try:
            return json.loads(OUT_QUEUE_CF.read_text("utf-8"))
        except Exception:
            return []
    return []

def save_queue(queue: List[Dict[str, Any]]) -> None:
    OUT_QUEUE_CF.parent.mkdir(parents=True, exist_ok=True)
    OUT_QUEUE_CF.write_text(json.dumps(queue, indent=2), encoding="utf-8")

# ─── Campaign Generator ───────────────────────────────────────────────────────

def generate_campaign(platform: Dict[str, Any], raise_target_usd: float = 500_000) -> Dict[str, Any]:
    pid = platform["id"]
    ptype = platform["type"]
    ticket_id = f"CF-TICKET-{uuid.uuid4().hex[:10].upper()}"

    # Securities valuation and equity terms require platform-specific legal
    # review. This draft-only engine deliberately leaves both unset.
    equity_offer_pct = 0.0
    valuation_usd = 0.0

    # Build use-of-funds dollar breakdown
    uof = COMPANY_NARRATIVE["use_of_funds"]
    uof_dollars = {k: round(v * raise_target_usd) for k, v in uof.items()}

    pitch_angle = (
        f"Draft-only {platform['name']} framing for LumenCore's bounded validation architecture. "
        "This text is not an offering, solicitation, platform approval, campaign submission, "
        "customer claim, or authorization to publish."
    )

    campaign = {
        "ticket_id": ticket_id,
        "generated_utc": now_utc(),
        "platform": platform,
        "raise_target_usd": raise_target_usd,
        "valuation_usd": round(valuation_usd),
        "equity_offer_pct": round(equity_offer_pct, 2),
        "financial_terms_status": "UNSET_REQUIRES_QUALIFIED_REVIEW",
        "external_use_authorized": False,
        **_approval_fields(),
        "campaign_content": {
            "headline": COMPANY_NARRATIVE["headline"],
            "tagline": COMPANY_NARRATIVE["tagline"],
            "pitch_angle": pitch_angle,
            "problem_statement": COMPANY_NARRATIVE["problem"],
            "solution_statement": COMPANY_NARRATIVE["solution"],
            "traction_bullets": COMPANY_NARRATIVE["traction"],
            "market_opportunity": COMPANY_NARRATIVE["market"],
            "team": COMPANY_NARRATIVE["team"],
            "vision": COMPANY_NARRATIVE["vision"],
            "use_of_funds": uof_dollars,
            "perk_tiers": PERK_TIERS if ptype == "rewards" else [],
            "investment_tiers": [],
            "faqs": [
                {"q": "What does LumenCore actually do?",
                 "a": "LumenCore packages one candidate-versus-baseline decision under source, metric, threshold, holdout, failure, custody, and human-authority controls."},
                {"q": "What proof do you have it works?",
                 "a": "The public repository contains first-party code, a deployed bounded ProofLock demonstration, pinned replay packages, public-data and synthetic benchmarks, and retained negative results. It does not establish independent validation, a customer, revenue, or field deployment."},
                {"q": "What's your competitive advantage?",
                 "a": "LumenCore's differentiator hypothesis is evidence and authority discipline: freeze the comparator and decision rules first, preserve failures, and return a reproducible bounded record. This remains to be commercially validated."},
                {"q": "How will my investment be used?",
                 "a": f"40% engineering/product, 25% go-to-market, 10% IP/legal, 10% operations/compliance, "
                      f"15% working capital reserve. Full breakdown in offering documents."},
                {"q": "What are the risks?",
                 "a": "Early-stage technology company. Key-man risk (single founder). Regulatory risk "
                      "in infrastructure sector. Market adoption risk. Competition from larger players. "
                      "All standard early-stage risks apply. No grant, pilot, patent scope, market demand, or investor return is assumed by this draft."},
            ],
            "risk_disclosures": [
                "Investing in early-stage companies involves high risk of total loss.",
                "Past performance of algorithms does not guarantee future results.",
                "This is not an offer to sell or solicitation to buy securities unless on a registered platform.",
                "Review the full offering circular before investing.",
            ],
        },
    }
    return campaign

# ─── CLI Commands ─────────────────────────────────────────────────────────────

def cmd_scout(args: argparse.Namespace) -> int:
    ranked = sorted(PLATFORMS, key=lambda p: p["fit_score"], reverse=True)
    print(f"\n{'RANK':<5} {'SCORE':<8} {'TYPE':<18} {'MAX RAISE':<15} PLATFORM")
    print("─" * 80)
    for i, p in enumerate(ranked, 1):
        max_r = f"${p['max_raise_usd']:>10,.0f}"
        print(f"{i:<5} {p['fit_score']:<8} {p['type']:<18} {max_r:<15} {p['name']}")
    print(f"\n🏆 Top recommendation: {ranked[0]['name']} — {', '.join(ranked[0]['fit_reasons'][:2])}")
    return 0

def cmd_generate(args: argparse.Namespace) -> int:
    platform_id = (args.platform or "all").lower()
    raise_target = float(getattr(args, "raise_target", 500_000))
    targets = PLATFORMS if platform_id == "all" else [p for p in PLATFORMS if p["id"] == platform_id]
    if not targets:
        print(f"Unknown platform: {platform_id}. Options: {[p['id'] for p in PLATFORMS]} or 'all'")
        return 1

    OUT_CF.mkdir(parents=True, exist_ok=True)
    queue = load_queue()
    for platform in targets:
        campaign = generate_campaign(platform, raise_target)
        out_path = OUT_CF / f"campaign_{platform['id']}_{campaign['ticket_id']}.json"
        save_json(out_path, campaign)
        queue.append(campaign)
        print(f"✅ Generated: {platform['name']:<20}  target=${raise_target:,.0f}  equity={campaign['equity_offer_pct']:.1f}%  → {out_path.name}")

    save_queue(queue)
    label = "auto-approved queue" if AUTO_APPROVE_ALWAYS else "approval queue"
    print(f"\n💾 {len(targets)} campaigns queued in {label}: {OUT_QUEUE_CF}")
    print("   Run `crowdfunding_engine.py list-queue` to review.")
    return 0

def cmd_list_queue(args: argparse.Namespace) -> int:
    queue = load_queue()
    if not queue:
        print("No campaigns in queue.")
        return 0
    print(f"\n{'STATE':<25} {'TICKET':<25} {'PLATFORM':<20} TARGET")
    print("─" * 90)
    for item in queue:
        state  = item.get("approval_state", "?")
        tid    = item.get("ticket_id", "?")
        pname  = item.get("platform", {}).get("name", "?")
        target = f"${item.get('raise_target_usd', 0):,.0f}"
        print(f"{state:<25} {tid:<25} {pname:<20} {target}")
    return 0

def cmd_approve(args: argparse.Namespace) -> int:
    queue = load_queue()
    updated = False
    for item in queue:
        if item.get("ticket_id") == args.ticket:
            item["approval_state"] = "APPROVED"
            item["approved_utc"] = now_utc()
            item["reviewer_notes"] = args.notes or "Approved by Robert"
            updated = True
            break
    if not updated:
        print(f"Ticket not found: {args.ticket}")
        return 1
    save_queue(queue)
    print(f"✅ APPROVED: {args.ticket}")
    print(f"   → Campaign ready. Submit to platform portal manually or via API integration.")
    return 0


def cmd_auto_approve_all(args: argparse.Namespace) -> int:
    queue = load_queue()
    updated = 0
    for item in queue:
        state = str(item.get("approval_state", "")).upper()
        if state != "PENDING_HUMAN_APPROVAL":
            continue
        item["approval_state"] = "APPROVED"
        item["approved_utc"] = now_utc()
        item["reviewer_notes"] = args.notes or AUTO_APPROVAL_NOTE
        updated += 1

    save_queue(queue)
    print(json.dumps({
        "status": "ok",
        "updated": updated,
        "queue_count": len(queue),
        "queue_file": str(OUT_QUEUE_CF),
    }, indent=2))
    return 0

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="LumenCore Crowdfunding Engine")
    sub = p.add_subparsers(dest="command", required=True)

    ps = sub.add_parser("scout", help="Rank crowdfunding platforms by fit")
    ps.set_defaults(func=cmd_scout)

    pg = sub.add_parser("generate", help="Generate campaign content")
    pg.add_argument("--platform", default="all")
    pg.add_argument("--raise-target", type=float, default=500_000,
                    dest="raise_target")
    pg.set_defaults(func=cmd_generate)

    pl = sub.add_parser("list-queue", help="Show approval queue")
    pl.set_defaults(func=cmd_list_queue)

    pa = sub.add_parser("approve", help="Approve a campaign ticket")
    pa.add_argument("--ticket", required=True)
    pa.add_argument("--notes", default="")
    pa.set_defaults(func=cmd_approve)

    paa = sub.add_parser("auto-approve-all", help="Approve all pending campaign tickets")
    paa.add_argument("--notes", default=AUTO_APPROVAL_NOTE)
    paa.set_defaults(func=cmd_auto_approve_all)

    return p

def main(argv):
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

import sys
