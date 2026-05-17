from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from application_context_resolver import CTX_LATEST, load_application_profile

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
DATA = ROOT / "data"
OPS_OUT = ROOT / "out" / "ops"
RESUME_OUT = ROOT / "out" / "resume"
OPP_OUT = ROOT / "out" / "opportunities"
LINKEDIN_OUT = OPP_OUT / "linkedin"

COMPANY_PROFILE_PATH = DATA / "company_profile.json"
INVESTOR_READINESS_PATH = ROOT / "out" / "ops" / "investor_metric_readiness_latest.json"
VALUE_PANEL_PATH = ROOT / "out" / "ops" / "live_breadth_value_panel_latest.json"
VPS_GROWTH_PATH = ROOT / "out" / "execution" / "vps_growth_proof.json"
LEADERBOARD_PATH = ROOT / "out" / "execution" / "institutional_leaderboard.csv"

RESUME_MD_PATH = ROOT / "RESUME_LUMENCORE.md"

IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_\.]*)", re.MULTILINE)

EXTERNAL_IMPORT_MAP = {
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "bs4": "beautifulsoup4",
    "yaml": "pyyaml",
    "PIL": "pillow",
    "Crypto": "pycryptodome",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_first_csv_row(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if isinstance(row, dict):
                    return dict(row)
    except Exception:
        return {}
    return {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content.rstrip("\r\n") + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def _fmt_money(value: float) -> str:
    return f"${value:,.2f}"


def _fmt_pct(value: float) -> str:
    return f"{value:.2f}%"


def _benchmark_dataset_count() -> int:
    latest_path = ROOT / "out" / "master_universe_v2" / "latest.txt"
    if not latest_path.exists():
        return 0
    utc = latest_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not utc:
        return 0
    summary_path = ROOT / "out" / "master_universe_v2" / utc / "summary.json"
    summary = _read_json(summary_path)
    n = summary.get("n_datasets_in_universe") or summary.get("n_datasets_succeeded")
    return _safe_int(n, 0)


def _collect_external_packages(max_packages: int) -> list[dict[str, Any]]:
    skip_parts = {
        ".venv",
        "venv",
        "venv3.11",
        "__pycache__",
        "node_modules",
        "out",
    }
    stdlib = set(getattr(sys, "stdlib_module_names", set()))
    stdlib.update({"typing_extensions"})

    internal_modules: set[str] = set()
    for child in CODE.iterdir():
        if child.is_dir():
            internal_modules.add(child.name)
    for py in CODE.rglob("*.py"):
        if any(part in skip_parts for part in py.parts):
            continue
        internal_modules.add(py.stem)

    module_counts: Counter[str] = Counter()
    for py in CODE.rglob("*.py"):
        if any(part in skip_parts for part in py.parts):
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for match in IMPORT_RE.finditer(text):
            root = match.group(1).split(".")[0]
            if not root:
                continue
            module_counts[root] += 1

    package_counts: Counter[str] = Counter()
    module_by_package: dict[str, str] = {}
    for mod, cnt in module_counts.items():
        if mod in stdlib:
            continue
        if mod in internal_modules:
            continue
        if (CODE / mod).exists():
            continue
        if mod.startswith("_"):
            continue
        package = EXTERNAL_IMPORT_MAP.get(mod, mod)
        package_counts[package] += cnt
        module_by_package[package] = mod

    rows: list[dict[str, Any]] = []
    for package, cnt in package_counts.most_common(max_packages):
        rows.append({"package": package, "module": module_by_package.get(package, package), "count": int(cnt)})
    return rows


def _build_metrics() -> dict[str, Any]:
    investor = _read_json(INVESTOR_READINESS_PATH)
    panel = _read_json(VALUE_PANEL_PATH)
    vps = _read_json(VPS_GROWTH_PATH)
    leader = _read_first_csv_row(LEADERBOARD_PATH)

    summary = investor.get("summary", {}) if isinstance(investor, dict) else {}
    signal = summary.get("signal_evidence", {}) if isinstance(summary, dict) else {}
    gates = summary.get("capital_and_risk_gate_evidence", {}) if isinstance(summary, dict) else {}
    provisional = summary.get("provisional_live_metrics", {}) if isinstance(summary, dict) else {}
    headline = panel.get("headline", {}) if isinstance(panel, dict) else {}
    vps_live = vps.get("live_trade_performance", {}) if isinstance(vps, dict) else {}

    dataset_count = _benchmark_dataset_count()
    annual_value = _safe_float(
        signal.get("annual_value_usd"),
        _safe_float(headline.get("total_estimated_annual_value_usd"), 0.0),
    )
    top_sector = str(signal.get("top_sector") or headline.get("top_sector") or "financial_market_infra")
    top_sector_hourly = _safe_float(
        signal.get("top_sector_hourly_value_usd"),
        _safe_float(headline.get("top_sector_hourly_value_usd"), 0.0),
    )
    router_edge = _safe_float(signal.get("router_edge_pct"), _safe_float(headline.get("router_edge_pct"), 0.0))
    harmonic_win_rate = _safe_float(
        signal.get("harmonic_win_rate_pct"),
        _safe_float(headline.get("harmonic_win_rate_pct"), 0.0),
    )
    kalisha_score = _safe_float(
        signal.get("kalisha_prediction_score"),
        _safe_float(headline.get("kalisha_prediction_score"), 0.0),
    )
    avoided_cost = _safe_float(headline.get("cross_sector_recommended_avoided_cost_usd"), 0.0)
    closed_trades = _safe_int(provisional.get("closed_live_trades"), _safe_int(vps_live.get("closed_live_count"), 0))
    win_rate = _safe_float(provisional.get("win_rate_pct"), _safe_float(vps_live.get("win_rate_pct"), 0.0))
    realized_net = _safe_float(provisional.get("realized_net_usd"), _safe_float(vps_live.get("realized_net_usd"), 0.0))

    return {
        "dataset_count": dataset_count,
        "annual_value_usd": annual_value,
        "top_sector": top_sector,
        "top_sector_hourly_value_usd": top_sector_hourly,
        "router_edge_pct": router_edge,
        "harmonic_win_rate_pct": harmonic_win_rate,
        "kalisha_prediction_score": kalisha_score,
        "cross_sector_avoided_cost_usd": avoided_cost,
        "runtime_mode": str(gates.get("runtime_mode") or "paper"),
        "allow_live_orders": bool(gates.get("allow_live_orders", False)),
        "max_notional_per_trade_usd": _safe_float(gates.get("max_notional_per_trade_usd"), 0.0),
        "closed_live_trades": closed_trades,
        "win_rate_pct": win_rate,
        "realized_net_usd": realized_net,
        "leader_flow": str(leader.get("flow") or "geom_gaussian"),
        "leader_strategy": str(leader.get("strategy") or "regime_switch"),
        "leader_algo": str(leader.get("algo") or "confidence_weighted"),
        "leader_test_sharpe": _safe_float(leader.get("test_sharpe"), 0.0),
        "leader_institutional_score": _safe_float(leader.get("institutional_score"), 0.0),
    }


def _build_resume_markdown(profile: dict[str, Any], metrics: dict[str, Any], packages: list[dict[str, Any]]) -> str:
    company = profile.get("company", {}) if isinstance(profile, dict) else {}
    pi = profile.get("pi", {}) if isinstance(profile, dict) else {}

    name = str(pi.get("name") or company.get("founder_pi") or "Robert BabyRay Ashworth")
    email = str(company.get("email") or "robertashworth4444@gmail.com")
    phone = str(company.get("phone") or "615-438-2502")
    website = str(company.get("website") or "https://lumen-core.ai")
    location = f"{company.get('city', 'Nashville')}, {company.get('state', 'TN')}"
    dataset_count = metrics.get("dataset_count") or 673
    package_names = [row.get("package", "") for row in packages if row.get("package")]

    tech_line = ", ".join(package_names[:20]) if package_names else "fastapi, pandas, numpy, scipy, scikit-learn, requests"

    return f"""# {name.upper()}

Principal Quant Systems Engineer | Institutional Automation Architect | Government-Grade Evidence Lead

Location: {location} (Remote/Hybrid/Relocation)  
Email: [{email}](mailto:{email})  
Phone: {phone}  
Website: [{website}]({website})

## EXECUTIVE PROFILE

Founder-operator of the LumaTrader and LumenCore platform ecosystem with end-to-end ownership of quant research, live execution controls, evidence-chain integrity, and investor/government reporting. Built and operated a production institutional stack that converts multi-source data into risk-gated actions with machine-readable proof artifacts.

## INSTITUTIONAL IMPACT SNAPSHOT

- Dataset benchmark breadth: {dataset_count} datasets with reproducible artifacts and hash-linked evidence.
- Annual modeled value signal: {_fmt_money(_safe_float(metrics.get('annual_value_usd')))}.
- Top sector and hourly signal: {metrics.get('top_sector')} at {_fmt_money(_safe_float(metrics.get('top_sector_hourly_value_usd')))} per hour.
- Router edge and harmonic consistency: {_fmt_pct(_safe_float(metrics.get('router_edge_pct')))} edge, {_fmt_pct(_safe_float(metrics.get('harmonic_win_rate_pct')))} harmonic win rate.
- Live execution telemetry: {int(_safe_float(metrics.get('closed_live_trades')))} closed trades, {_fmt_pct(_safe_float(metrics.get('win_rate_pct')))} win rate, realized net {_fmt_money(_safe_float(metrics.get('realized_net_usd')))}.

## CORE COMPETENCIES

- Mission-critical Python architecture for quant, routing, and operational control planes.
- Risk-engineering guardrails: kill switch controls, cooldown logic, approval queues, and position sizing controls.
- Government-grade traceability with SHA256 manifests, immutable ledgers, and reproducible run artifacts.
- FastAPI gateway and dashboard API integration for investor, mission-control, and ops command surfaces.
- Cross-sector data engineering across market, energy, macro, and infrastructure signal lanes.

## SELECTED PRODUCTION SYSTEMS

- INSTITUTIONAL_STACK_V2 orchestration and runtime continuity controls.
- Opportunity automation lanes for grants, funding, and outreach workflows.
- LinkedIn evidence publishing lane and profile optimization automation.
- Sports and market intelligence fusion lanes with explicit lane-boundary controls.
- End-to-end evidence packaging pipelines for investor and federal reviews.

## TECHNOLOGY STACK AND PROVEN PACKAGES

{tech_line}

## PROFESSIONAL EXPERIENCE

### Founder and Principal Systems Engineer | LumaTrader / LumenCore

2014 - Present

- Architected and maintained a production quant platform spanning data ingestion, model routing, risk controls, execution, and evidence generation.
- Built deterministic ops scripts and API endpoints to automate grant readiness, investor proof packs, and mission dashboards.
- Designed resilient live-execution safeguards with configurable runtime controls and explicit reason-code telemetry.
- Produced institutional artifacts for due diligence, including calibration summaries, anomaly scanners, and regime-shift reports.

## GOVERNMENT AND INSTITUTIONAL POSITIONING

- UEI: {company.get('duns_or_uei', 'SQY2XW71ZM51')} | CAGE: {company.get('cage_code', '14TM8')} | SAM status: {company.get('sam_gov_status', 'active')}.
- Track record generating federal-style submissions and preflight-ready package artifacts.
- Operates with evidence-first discipline: every major claim maps to machine-readable outputs.

## TARGET ROLES

- Principal Quant Systems Engineer
- Staff Platform Reliability Engineer (AI and Trading Infrastructure)
- Mission Systems Software Engineer (Government and Defense-Adjacent)
- Senior Technical Lead, AI Operations and Evidence Automation
"""


def _build_linkedin_payload(profile: dict[str, Any], metrics: dict[str, Any], packages: list[dict[str, Any]]) -> dict[str, Any]:
    company = profile.get("company", {}) if isinstance(profile, dict) else {}
    pi = profile.get("pi", {}) if isinstance(profile, dict) else {}
    name = str(pi.get("name") or company.get("founder_pi") or "Robert BabyRay Ashworth")
    dataset_count = metrics.get("dataset_count") or 673

    package_names = [row.get("package", "") for row in packages if row.get("package")]
    skill_seed = [
        "Python",
        "FastAPI",
        "Risk Controls",
        "Quant Systems",
        "Time-Series Forecasting",
        "Government-Grade Evidence",
        "Operational Automation",
        "PowerShell",
    ]
    for pkg in package_names[:12]:
        if pkg and pkg not in skill_seed:
            skill_seed.append(pkg)

    annual_value = _fmt_money(_safe_float(metrics.get("annual_value_usd")))
    headline_variants = [
        "Principal Quant Systems Engineer | Institutional Automation | Government-Grade Evidence",
        "Founder, LumaTrader/LumenCore | Quant Infrastructure | Risk-Gated Execution",
        "AI + Quant Platform Architect | Production Trading and Mission-Critical Ops",
        "Staff-Level Python Systems Engineer | Runtime Controls | Evidence Chains",
        "Institutional and Federal-Ready Technical Lead | Forecasting | Control Planes",
    ]

    about = (
        f"I build institutional-grade quant and operational intelligence systems that move from signal to action with explicit risk controls and verifiable evidence. "
        f"My platform work spans LumaTrader and LumenCore, where I operate a {dataset_count}-dataset benchmark and produce reproducible artifacts for investors and federal-style reviews. "
        f"Current modeled annual value signal: {annual_value}. Top impact lane: {metrics.get('top_sector')} with hourly signal value of "
        f"{_fmt_money(_safe_float(metrics.get('top_sector_hourly_value_usd')))}. "
        f"I specialize in Python control planes, FastAPI services, runtime guardrails, and proof-grade reporting that keeps technical claims auditable."
    )

    experience = [
        "Built and operate INSTITUTIONAL_STACK_V2 for end-to-end quant execution, risk controls, and evidence packaging.",
        "Shipped mission-control and investor dashboards with API-driven telemetry and deterministic fallback behavior.",
        "Implemented approval queues, kill-switch semantics, and pacing guardrails to enforce safe runtime posture.",
        "Automated grant and opportunity workflows with prefilled artifacts, submission checklists, and queue tracking.",
        "Maintained lane-boundary governance across trading, sector, and sports intelligence pipelines.",
    ]

    featured_links = [
        {"label": "LumenCore", "url": str(company.get("website") or "https://lumen-core.ai")},
        {"label": "Evidence Runs", "url": "https://lumen-core.ai/evidence/"},
        {"label": "Mission Control", "url": "https://lumen-core.ai/mission_control.html"},
    ]

    post_templates = [
        {
            "title": "LumaLinkedIn Edition V1 launch",
            "text": (
                f"LumaLinkedIn Edition V1 is live. I just refreshed my production resume and opportunity stack using evidence-first automation: "
                f"{dataset_count} benchmark datasets, {_fmt_pct(_safe_float(metrics.get('router_edge_pct')))} router edge, "
                f"and a modeled annual value signal of {annual_value}. Building systems where every claim maps to artifacts."
            ),
        },
        {
            "title": "Government-grade AI ops",
            "text": (
                "Working at the intersection of quant infrastructure and government-grade evidence discipline. "
                "Focus: deterministic pipelines, risk-gated runtime controls, and machine-readable proof bundles."
            ),
        },
    ]

    return {
        "generated_utc": _now_iso(),
        "version": "lumalinkedin_v1",
        "name": name,
        "headline_variants": headline_variants,
        "about": about,
        "experience_bullets": experience,
        "featured_links": featured_links,
        "skills": skill_seed[:30],
        "post_templates": post_templates,
    }


def _render_linkedin_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# LumaLinkedIn Edition V1")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append("")
    lines.append("## Headline Variants")
    lines.append("")
    for idx, item in enumerate(payload.get("headline_variants", []), start=1):
        lines.append(f"{idx}. {item}")
    lines.append("")
    lines.append("## About")
    lines.append("")
    lines.append(str(payload.get("about", "")))
    lines.append("")
    lines.append("## Experience Bullets")
    lines.append("")
    for item in payload.get("experience_bullets", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Featured Links")
    lines.append("")
    for item in payload.get("featured_links", []):
        if not isinstance(item, dict):
            continue
        lines.append(f"- {item.get('label', 'Link')}: {item.get('url', '')}")
    lines.append("")
    lines.append("## Skills")
    lines.append("")
    lines.append(", ".join(str(x) for x in payload.get("skills", [])))
    lines.append("")
    lines.append("## Post Templates")
    lines.append("")
    for item in payload.get("post_templates", []):
        if not isinstance(item, dict):
            continue
        lines.append(f"### {item.get('title', 'Post')}")
        lines.append("")
        lines.append(str(item.get("text", "")))
        lines.append("")
    return "\n".join(lines)


def _publish_linkedin_summary(payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    templates = payload.get("post_templates") if isinstance(payload.get("post_templates"), list) else []
    post = templates[0] if templates else {}
    text = str(post.get("text") or "LumaLinkedIn V1 update")
    title = str(post.get("title") or "LumaLinkedIn V1")
    links = payload.get("featured_links") if isinstance(payload.get("featured_links"), list) else []
    first_link = links[0] if links and isinstance(links[0], dict) else {}
    url = str(first_link.get("url") or "https://lumen-core.ai")

    if dry_run:
        return {"dry_run": True, "text": text, "title": title, "url": url}

    try:
        sys.path.insert(0, str(CODE))
        import linkedin_oauth as li  # type: ignore

        result = li.share_text(
            text,
            link=url,
            link_title=title,
            link_desc="LumaLinkedIn V1 profile and resume optimization update",
        )
        return {"posted": True, "response": result}
    except Exception as exc:
        return {"posted": False, "error": str(exc)}


def _run_resume_pdf_builder() -> dict[str, Any]:
    cmd = [sys.executable, str(CODE / "build_elite_resume_pdf.py")]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return {
            "rc": proc.returncode,
            "stdout_tail": (proc.stdout or "").splitlines()[-20:],
            "stderr_tail": (proc.stderr or "").splitlines()[-10:],
        }
    except subprocess.TimeoutExpired:
        return {"rc": -1, "error": "timeout"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build LumaLinkedIn Edition V1 resume and profile assets.")
    parser.add_argument("--max-packages", type=int, default=28)
    parser.add_argument("--no-pdf", action="store_true", help="Skip running build_elite_resume_pdf.py")
    parser.add_argument("--publish-linkedin-summary", action="store_true")
    parser.add_argument("--dry-run-post", action="store_true")
    args = parser.parse_args()

    if not COMPANY_PROFILE_PATH.exists() and not CTX_LATEST.exists():
        print(f"[error] missing profile: {COMPANY_PROFILE_PATH}")
        return 2

    profile = load_application_profile()
    metrics = _build_metrics()
    packages = _collect_external_packages(max_packages=max(8, args.max_packages))

    stamp = _stamp()
    RESUME_OUT.mkdir(parents=True, exist_ok=True)
    LINKEDIN_OUT.mkdir(parents=True, exist_ok=True)
    OPS_OUT.mkdir(parents=True, exist_ok=True)

    resume_md = _build_resume_markdown(profile, metrics, packages)

    tagged_resume_md = RESUME_OUT / f"resume_lumalinkedin_v1_{stamp}.md"
    tagged_resume_json = RESUME_OUT / f"resume_lumalinkedin_v1_{stamp}.json"
    latest_resume_md = RESUME_OUT / "resume_lumalinkedin_v1_latest.md"
    latest_resume_json = RESUME_OUT / "resume_lumalinkedin_v1_latest.json"

    _write_text(RESUME_MD_PATH, resume_md)
    _write_text(tagged_resume_md, resume_md)
    _write_text(latest_resume_md, resume_md)

    resume_payload = {
        "generated_utc": _now_iso(),
        "version": "lumalinkedin_v1",
        "profile_source": str(CTX_LATEST if CTX_LATEST.exists() else COMPANY_PROFILE_PATH),
        "metrics": metrics,
        "proven_packages": packages,
        "application_context": {
            "federal_readiness": profile.get("federal_readiness", {}),
            "identifiers": profile.get("identifiers", {}),
        },
        "artifacts": {
            "resume_md": str(RESUME_MD_PATH),
            "tagged_resume_md": str(tagged_resume_md),
        },
    }
    _write_json(tagged_resume_json, resume_payload)
    _write_json(latest_resume_json, resume_payload)

    linkedin_payload = _build_linkedin_payload(profile, metrics, packages)
    linkedin_md = _render_linkedin_markdown(linkedin_payload)

    tagged_linkedin_json = LINKEDIN_OUT / f"lumalinkedin_v1_{stamp}.json"
    tagged_linkedin_md = LINKEDIN_OUT / f"lumalinkedin_v1_{stamp}.md"
    latest_linkedin_json = LINKEDIN_OUT / "lumalinkedin_v1_latest.json"
    latest_linkedin_md = LINKEDIN_OUT / "lumalinkedin_v1_latest.md"

    _write_json(tagged_linkedin_json, linkedin_payload)
    _write_json(latest_linkedin_json, linkedin_payload)
    _write_text(tagged_linkedin_md, linkedin_md)
    _write_text(latest_linkedin_md, linkedin_md)

    pdf_result: dict[str, Any] | None = None
    if not args.no_pdf:
        pdf_result = _run_resume_pdf_builder()

    publish_result: dict[str, Any] | None = None
    if args.publish_linkedin_summary:
        publish_result = _publish_linkedin_summary(linkedin_payload, dry_run=args.dry_run_post)

    summary = {
        "generated_utc": _now_iso(),
        "scope": "lumalinkedin_resume_engine_v1",
        "metrics": metrics,
        "resume_artifacts": {
            "root_resume_md": str(RESUME_MD_PATH),
            "latest_resume_md": str(latest_resume_md),
            "latest_resume_json": str(latest_resume_json),
        },
        "linkedin_artifacts": {
            "latest_linkedin_md": str(latest_linkedin_md),
            "latest_linkedin_json": str(latest_linkedin_json),
        },
        "pdf_result": pdf_result,
        "publish_result": publish_result,
    }
    summary_path = OPS_OUT / f"lumalinkedin_v1_build_{stamp}.json"
    latest_summary = OPS_OUT / "lumalinkedin_v1_build_latest.json"
    _write_json(summary_path, summary)
    _write_json(latest_summary, summary)

    print(f"RESUME_MD={RESUME_MD_PATH}")
    print(f"RESUME_JSON={latest_resume_json}")
    print(f"LINKEDIN_JSON={latest_linkedin_json}")
    print(f"SUMMARY={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
