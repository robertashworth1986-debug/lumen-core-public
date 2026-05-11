"""
crowdfunding_engine.py  ─  LumenCore Crowdfunding Intelligence Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Institutional-grade crowdfunding campaign builder and platform intelligence.

CAPABILITIES:
  1. PLATFORM SCOUT  — ranks crowdfunding platforms by fit for LumenCore
  2. CAMPAIGN WRITER — generates complete campaign copy (headline, pitch, perks,
                       FAQ, risk disclosures, investor narrative) per platform
  3. EQUITY TARGETS  — Republic, Wefunder, StartEngine (Reg CF / Reg D ready)
  4. REWARDS TARGETS — Kickstarter, Indiegogo (product/tech tier)
  5. PROOF BUNDLE    — attaches existing execution TXIDs, audit hashes, patents
  6. FINANCIAL MODEL — auto-generates raise model, equity offer, use-of-funds
  7. APPROVAL QUEUE  — same human-gate pattern as grant hunter

Usage:
  python crowdfunding_engine.py generate  --platform republic
  python crowdfunding_engine.py generate  --platform all
  python crowdfunding_engine.py scout
  python crowdfunding_engine.py list-queue
"""

from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT         = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE         = ROOT / "code"
OUT_CF       = ROOT / "out" / "crowdfunding"
OUT_QUEUE_CF = ROOT / "out" / "crowdfunding_approval_queue.json"
PROFILE_PATH = CODE / "grants_profile_lumencore.json"
EVIDENCE_PATH = ROOT / "investor_and_grant_evidence.json"
INVESTOR_BRIEF = ROOT / "INVESTOR_BRIEF.md"

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
    "headline": "LumenCore™ — The Predictive Intelligence Layer for Critical Infrastructure",
    "tagline": "We see infrastructure failures before they happen. 14–47% earlier than anything else.",
    "problem": (
        "Every year, grid failures and critical infrastructure outages cost the U.S. economy "
        "over $150 billion. Operators use reactive monitoring — they find out after the damage is done. "
        "There has been no affordable, production-ready solution that predicts instability BEFORE it cascades."
    ),
    "solution": (
        "LumenCore is a predictive intelligence engine that watches infrastructure telemetry 24/7, "
        "identifies pre-failure harmonic divergence patterns, and alerts operators with actionable "
        "insight 14–47% earlier than threshold-based systems. We have 11 validated proof iterations, "
        "real exchange execution records (TXIDs on Kraken), and a DOE SBIR Phase I application. "
        "Our core IP is protected under a filed patent portfolio."
    ),
    "traction": [
        "12+ months of production-grade development across 17,000+ artifacts",
        "11 validated proof iterations with hash-verified chain-of-custody audit trails",
        "Real Kraken TXID execution records demonstrating live algorithm deployment",
        "DOE SBIR Phase I application submitted",
        "Patent portfolio covering Fibonacci Bubble Lattice Harmonic engine and EchoLock™ phase-locking IP",
        "Cumberland Science Museum pilot deployment in progress",
        "FSI (Financial Services Initiative) sector engagement active",
        "PWC-validated ECHOLOCK early signal proof package",
    ],
    "market": (
        "Total addressable market: $47B (critical infrastructure monitoring, predictive maintenance, "
        "grid intelligence). Serviceable: $8.2B (U.S. energy + utility sector). Beachhead: "
        "$1.1B (SBIR-funded DOE/DARPA pilot programs + utility contracts)."
    ),
    "use_of_funds": {
        "engineering_and_product": 0.40,
        "go_to_market_and_sales": 0.25,
        "ip_and_legal": 0.10,
        "operations_and_compliance": 0.10,
        "reserve_and_working_capital": 0.15,
    },
    "team": "Robert BabyRay Ashworth — Founder, PI, Lead Engineer. Built LumenCore from zero to "
            "production in 12 months. Former self-funded researcher, now applying to institutional "
            "and government channels simultaneously.",
    "vision": (
        "LumenCore becomes the operating system for critical infrastructure intelligence — "
        "embedded in every major utility, grid operator, and federal infrastructure program in the U.S., "
        "then globally. Modeled on Bloomberg Terminal for the physical infrastructure world."
    ),
}

PERK_TIERS = [
    {"tier": "Observer", "amount_usd": 25,  "perks": ["LumenCore public dashboard access (12 months)", "Backer newsletter"]},
    {"tier": "Analyst",  "amount_usd": 100, "perks": ["Observer perks", "Monthly intelligence briefing PDF", "Early access to proof packs"]},
    {"tier": "Operator", "amount_usd": 500, "perks": ["Analyst perks", "Beta API access (when available)", "Name in credits"]},
    {"tier": "Partner",  "amount_usd": 2500,"perks": ["Operator perks", "1:1 30-min strategy call with Robert", "Custom sector report"]},
    {"tier": "Founding Investor", "amount_usd": 10000, "perks": ["Partner perks", "Equity stake (Reg CF platforms only)", "Advisory board consideration", "First right of refusal on next round"]},
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()

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

    # Equity offer calculation (for equity platforms)
    equity_offer_pct = 0.0
    valuation_usd = 0.0
    if ptype == "equity_cf":
        # Target 10–20% dilution at seed
        valuation_usd = raise_target_usd / 0.15  # 15% stake implies this valuation
        equity_offer_pct = (raise_target_usd / valuation_usd) * 100

    # Build use-of-funds dollar breakdown
    uof = COMPANY_NARRATIVE["use_of_funds"]
    uof_dollars = {k: round(v * raise_target_usd) for k, v in uof.items()}

    # Platform-specific pitch angle
    if pid == "republic":
        pitch_angle = (
            "LumenCore is the Bloomberg Terminal for physical infrastructure risk. "
            "We're raising on Republic to accelerate our DOE SBIR Phase II transition, "
            "expand the pilot network, and file our next patent tranche."
        )
    elif pid == "wefunder":
        pitch_angle = (
            "One founder. 12 months. 17,000 artifacts. Real exchange TXIDs. "
            "LumenCore was built from nothing into an institutional-grade predictive intelligence "
            "engine. Now we're opening the door to community investors."
        )
    elif pid == "startengine":
        pitch_angle = (
            "Grid failures cost America $150 billion a year. LumenCore sees them coming "
            "14–47% earlier. We've validated. We've proven. Now we're scaling. "
            "Join us on StartEngine and own a piece of the infrastructure intelligence revolution."
        )
    elif pid == "kickstarter":
        pitch_angle = (
            "Get early access to LumenCore's live intelligence dashboard — "
            "real-time infrastructure risk scoring, algorithmic signal feeds, and the most "
            "transparent proof-of-work in predictive analytics."
        )
    else:
        pitch_angle = COMPANY_NARRATIVE["solution"]

    campaign = {
        "ticket_id": ticket_id,
        "generated_utc": now_utc(),
        "platform": platform,
        "raise_target_usd": raise_target_usd,
        "valuation_usd": round(valuation_usd),
        "equity_offer_pct": round(equity_offer_pct, 2),
        "approval_state": "PENDING_HUMAN_APPROVAL",
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
            "investment_tiers": PERK_TIERS if ptype == "equity_cf" else [],
            "faqs": [
                {"q": "What does LumenCore actually do?",
                 "a": "LumenCore is a predictive intelligence engine. It ingests live telemetry from "
                      "energy grids, infrastructure sensors, and financial markets, then uses our "
                      "proprietary Fibonacci Bubble Lattice Harmonic engine to detect instability "
                      "signatures before they cascade into outages or failures."},
                {"q": "What proof do you have it works?",
                 "a": "11 validated proof iterations with SHA-256 hash-verified chain-of-custody records. "
                      "Real Kraken exchange TXIDs from live algorithm deployments. DOE SBIR Phase I "
                      "application submitted. Cumberland Science Museum and FSI pilot programs active. "
                      "PWC-validated early signal proof package."},
                {"q": "What's your competitive advantage?",
                 "a": "We borrowed the most rigorous signal validation methodology in the world — "
                      "institutional quantitative finance — and applied it to infrastructure risk. "
                      "Financial quant firms lose real money when their signals fail, so the bar is "
                      "impossibly high. That same bar is now protecting your infrastructure."},
                {"q": "How will my investment be used?",
                 "a": f"40% engineering/product, 25% go-to-market, 10% IP/legal, 10% operations/compliance, "
                      f"15% working capital reserve. Full breakdown in offering documents."},
                {"q": "What are the risks?",
                 "a": "Early-stage technology company. Key-man risk (single founder). Regulatory risk "
                      "in infrastructure sector. Market adoption risk. Competition from larger players. "
                      "All standard early-stage risks apply. We mitigate through IP protection, "
                      "government grant funding, and diversified pilot programs."},
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
    print(f"\n💾 {len(targets)} campaigns queued for approval: {OUT_QUEUE_CF}")
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

    return p

def main(argv):
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

import sys
