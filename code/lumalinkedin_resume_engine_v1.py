from __future__ import annotations

import argparse
import copy
import csv
import html
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
RUNTIME_CONTROL_PATH = ROOT / "config" / "runtime_control.json"
EXECUTION_STATUS_PATH = ROOT / "out" / "execution_status.json"

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


def _fmt_money_compact(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.2f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    if abs_value >= 1_000:
        return f"${value / 1_000:,.2f}K"
    return _fmt_money(value)


def _dedupe_keep_order(values: list[str], case_insensitive: bool = True) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        value = str(raw or "").strip()
        if not value:
            continue
        key = value.casefold() if case_insensitive else value
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _humanize_sector_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "Financial Market Infra"
    text = text.replace("_", " ").replace("-", " ")
    return " ".join(part.capitalize() for part in text.split())


def _display_package_name(name: str) -> str:
    package = str(name or "").strip()
    if not package:
        return ""
    mapping = {
        "fastapi": "FastAPI",
        "scikit-learn": "scikit-learn",
        "pyyaml": "PyYAML",
        "opencv-python": "OpenCV",
    }
    return mapping.get(package.casefold(), package)


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


def _resolve_runtime_posture(gates: dict[str, Any]) -> dict[str, Any]:
    posture = {
        "runtime_mode": str(gates.get("runtime_mode") or "paper").strip().lower() or "paper",
        "allow_live_orders": bool(gates.get("allow_live_orders", False)),
        "paper_enabled": bool(gates.get("paper_enabled", True)),
        "runtime_mode_source": "investor_metric_readiness",
    }

    runtime_cfg = _read_json(RUNTIME_CONTROL_PATH)
    if isinstance(runtime_cfg, dict) and runtime_cfg:
        cfg_mode = str(runtime_cfg.get("mode") or "").strip().lower()
        if cfg_mode in {"live", "paper"}:
            posture["runtime_mode"] = cfg_mode
            posture["runtime_mode_source"] = "runtime_control"
        if "allow_live_orders" in runtime_cfg:
            posture["allow_live_orders"] = bool(runtime_cfg.get("allow_live_orders"))
        if "paper_enabled" in runtime_cfg:
            posture["paper_enabled"] = bool(runtime_cfg.get("paper_enabled"))

    execution_status = _read_json(EXECUTION_STATUS_PATH)
    if isinstance(execution_status, dict) and execution_status:
        status_mode = str(execution_status.get("execution_mode") or "").strip().lower()
        if posture["runtime_mode_source"] != "runtime_control" and status_mode in {"live", "paper"}:
            posture["runtime_mode"] = status_mode
            posture["runtime_mode_source"] = "execution_status"
        if "allow_live_orders" not in runtime_cfg and "live_arm" in execution_status:
            posture["allow_live_orders"] = str(execution_status.get("live_arm") or "").strip().upper() == "ON"

    if posture["runtime_mode"] == "live" and posture["allow_live_orders"]:
        posture["paper_enabled"] = False
    elif posture["runtime_mode"] == "paper" and "paper_enabled" not in gates and "paper_enabled" not in runtime_cfg:
        posture["paper_enabled"] = True

    return posture


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
    posture = _resolve_runtime_posture(gates)

    return {
        "dataset_count": dataset_count,
        "annual_value_usd": annual_value,
        "top_sector": top_sector,
        "top_sector_hourly_value_usd": top_sector_hourly,
        "router_edge_pct": router_edge,
        "harmonic_win_rate_pct": harmonic_win_rate,
        "kalisha_prediction_score": kalisha_score,
        "cross_sector_avoided_cost_usd": avoided_cost,
        "runtime_mode": str(posture.get("runtime_mode") or "paper"),
        "runtime_mode_source": str(posture.get("runtime_mode_source") or "unknown"),
        "allow_live_orders": bool(posture.get("allow_live_orders", False)),
        "paper_enabled": bool(posture.get("paper_enabled", True)),
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
    package_names = _dedupe_keep_order([str(row.get("package", "")) for row in packages if row.get("package")])

    tech_display = [_display_package_name(pkg) for pkg in package_names[:20] if _display_package_name(pkg)]
    tech_line = ", ".join(tech_display) if tech_display else "FastAPI, pandas, numpy, scipy, scikit-learn, requests"

    return f"""# {name.upper()}

Software Infrastructure & AI Evaluation Specialist | Python Systems | Reliability Engineering

Location: {location} (Remote/Hybrid/Relocation)  
Email: [{email}](mailto:{email})  
Phone: {phone}  
Website: [{website}]({website})

## EXECUTIVE PROFILE

Founder and hands-on systems engineer building Python automation, API services, evaluation harnesses, and evidence controls across the LumenCore and LumaTrader codebases. Designs fail-closed workflows that preserve source provenance, negative findings, exact artifacts, and human authority instead of turning internal results into unsupported claims. Seeking remote contract work in software infrastructure, AI evaluation, platform reliability, and quality engineering.

## ENGINEERING STRENGTHS

- Python architecture for verification, orchestration, data pipelines, APIs, and operator tooling.
- Infrastructure reasoning across dependency closure, deployment workflows, environment isolation, state ownership, failure handling, and recovery controls.
- AI evaluation workflows with fixed inputs, locked comparators, retained failures, reproducible commands, and machine-readable receipts.
- Reliability and quality controls including immutable dependency pinning, path safety, resource budgets, deterministic builds, and cross-platform CI.
- Clear technical communication for skeptical reviewers, program teams, buyers, and engineering stakeholders.

## SELECTED ENGINEERING WORK

- Built Proof Capsule validators that distinguish exact-byte custody, canonical JSON identity, policy state, and external authority.
- Added repository-wide GitHub Actions supply-chain controls that require immutable external-action commits and readable version annotations.
- Developed fail-closed order-safety, gateway-contract, deadline, outreach, and public-release checks that do not grant execution or submission authority.
- Built FastAPI and dashboard integration surfaces for bounded review, telemetry, and operator decision support.
- Created buyer-owned baseline-validation templates that lock the source, comparator, metric, threshold, holdout, failure policy, and claim boundary before scoring.
- Maintained Windows and Linux CI paths for evidence portability, deterministic packet generation, and reviewer reproduction.

## PROFESSIONAL EXPERIENCE

### Founder and Principal Systems Engineer | LumaTrader / LumenCore

2014 - Present

- Architected Python services and automation spanning ingestion, evaluation, routing, runtime controls, audit receipts, and reviewer-facing outputs.
- Implemented human-gated controls, kill switches, cooldowns, bounded notional policies, and explicit no-order/no-submit execution paths.
- Built reproducible evidence packages with SHA-256 manifests, deterministic JSON, fixed schemas, and retained negative results.
- Diagnosed and hardened deployment, filesystem ownership, stale-state, API-authentication, and dependency-closure failures.
- Produced technical briefs, statements of work, grant preflight materials, and public reviewer documentation with explicit proven/not-proven limits.

## TECHNOLOGY STACK

{tech_line}

Additional tools: Git, GitHub Actions, PowerShell, Linux, FastAPI, REST/WebSocket APIs, JSON/JSONL, HTML/CSS/JavaScript, pytest, unittest, Playwright, SHA-256 manifests.

## PUBLIC EVIDENCE BOUNDARY

- Public repository: [github.com/robertashworth1986-debug/lumen-core-public](https://github.com/robertashworth1986-debug/lumen-core-public)
- Reviewer entry point: [lumen-core.ai](https://lumen-core.ai)
- The public materials demonstrate first-party code, tests, reproducibility controls, bounded demonstrations, and claim governance.
- Independent validation, field performance, customer adoption, audited revenue, certification, and guaranteed savings are not established by the public repository.
- Live-order authority and final external submission authority are not granted by résumé claims, dashboards, or passing CI.

## TARGET ENGAGEMENTS

- SWE Infrastructure Specialist / AI Trainer
- Python Platform or Reliability Engineer
- AI Evaluation and Quality Engineer
- Technical Evidence and Reproducibility Engineer
- Contract Systems Architect for bounded validation and reviewer tooling
"""


def _build_linkedin_payload(profile: dict[str, Any], metrics: dict[str, Any], packages: list[dict[str, Any]]) -> dict[str, Any]:
    company = profile.get("company", {}) if isinstance(profile, dict) else {}
    pi = profile.get("pi", {}) if isinstance(profile, dict) else {}
    name = str(pi.get("name") or company.get("founder_pi") or "Robert BabyRay Ashworth")
    package_names = _dedupe_keep_order([str(row.get("package", "")) for row in packages if row.get("package")])
    skill_seed = [
        "Python",
        "FastAPI",
        "Reliability Engineering",
        "AI Evaluation",
        "Reproducible Systems",
        "Runtime Controls",
        "Operational Automation",
        "PowerShell",
    ]
    for pkg in package_names[:12]:
        label = _display_package_name(pkg)
        if label:
            skill_seed.append(label)

    skills = _dedupe_keep_order(skill_seed)

    headline_variants = [
        "Software Infrastructure & AI Evaluation Specialist | Python Systems | Reliability Engineering",
        "Founder, LumaTrader/LumenCore | Reproducible Systems | Runtime Controls",
        "Python Platform Engineer | AI Evaluation | Evidence and Reliability",
        "Systems Engineer | Deterministic Pipelines | Human-Gated Automation",
        "Technical Evidence & Reproducibility Engineer | APIs | CI | Audit Receipts",
    ]

    about_short = (
        "I build Python infrastructure and AI-evaluation workflows with explicit controls, reproducible outputs, and reviewer-readable evidence. "
        "My work spans APIs, automation, runtime safety, CI, deterministic artifacts, and failure analysis."
    )
    about_long = (
        "I build and review Python systems where behavior must be observable, bounded, and reproducible. "
        "Across LumaTrader and LumenCore, I have implemented ingestion and evaluation pipelines, API services, runtime guardrails, audit receipts, CI checks, and reviewer-facing evidence packages. "
        "I retain negative results and separate first-party software verification from claims that require independent field validation. "
        "I am seeking infrastructure, AI-evaluation, reliability, and technical-evidence engagements where careful engineering and clear failure analysis matter."
    )

    experience = [
        "Architected Python services and automation spanning ingestion, evaluation, routing, runtime controls, audit receipts, and reviewer-facing outputs.",
        "Implemented human-gated controls, kill switches, cooldowns, bounded notional policies, and explicit no-order/no-submit paths.",
        "Built reproducible evidence packages with SHA-256 manifests, deterministic JSON, fixed schemas, and retained negative results.",
        "Diagnosed deployment, filesystem ownership, stale-state, authentication, and dependency-closure failures.",
        "Produced technical briefs, statements of work, grant preflight materials, and public documentation with explicit proven/not-proven limits.",
    ]
    experience_roles = [
        {
            "title": "Founder and Principal Systems Engineer",
            "company": "LumaTrader / LumenCore",
            "dates": "2014 - Present",
            "location": "Nashville, TN",
            "bullets": experience,
        }
    ]

    featured_links = [
        {"label": "LumenCore", "url": str(company.get("website") or "https://lumen-core.ai")},
        {"label": "Evidence Runs", "url": "https://lumen-core.ai/evidence/"},
        {"label": "Mission Control", "url": "https://lumen-core.ai/mission_control.html"},
    ]

    post_templates = [
        {
            "title": "Evidence-first engineering update",
            "text": (
                "I refreshed LumenCore's public technical surface around a simple rule: show the code, controls, reproducible command, and limits of the evidence. "
                "First-party verification is visible; independent field validation remains a separate gate."
            ),
        },
        {
            "title": "Bounded AI operations",
            "text": (
                "Working at the intersection of Python infrastructure, AI evaluation, and evidence discipline. "
                "Focus: deterministic pipelines, human-gated controls, failure receipts, and machine-readable proof bundles."
            ),
        },
    ]

    runtime_mode = str(metrics.get("runtime_mode") or "paper").upper()
    live_order_mode = "ON" if bool(metrics.get("allow_live_orders")) else "OFF"
    impact_snapshot = [
        {
            "label": "Evidence",
            "value": "REPLAYABLE",
            "hint": "Deterministic artifacts and commands",
        },
        {
            "label": "Integrity",
            "value": "SHA-256",
            "hint": "Canonical manifests and receipts",
        },
        {
            "label": "Validation",
            "value": "NOT ESTABLISHED",
            "hint": "Independent field validation is a separate gate",
        },
        {
            "label": "Runtime Mode",
            "value": runtime_mode,
            "hint": f"Live orders: {live_order_mode}",
        },
    ]
    quick_apply_steps = [
        "Paste Recommended Headline into LinkedIn Headline.",
        "Use About (Short) for mobile summary and About (Full) for the main profile section.",
        "Create Experience entry from Experience Pack bullets.",
        "Add Featured Links and top skills for profile credibility.",
        "Use Post Templates only after checking every statement against a public artifact.",
    ]

    return {
        "generated_utc": _now_iso(),
        "version": "lumalinkedin_v1",
        "audience_id": "master",
        "audience_label": "Master Profile",
        "name": name,
        "headline_recommended": headline_variants[0],
        "headline_variants": headline_variants,
        "about": about_long,
        "about_short": about_short,
        "about_full": about_long,
        "experience_bullets": experience,
        "experience_roles": experience_roles,
        "featured_links": featured_links,
        "skills": skills[:30],
        "post_templates": post_templates,
        "impact_snapshot": impact_snapshot,
        "quick_apply_steps": quick_apply_steps,
        "profile_fill_pack": {
            "headline": headline_variants[0],
            "about_short": about_short,
            "about_full": about_long,
            "experience": experience_roles,
            "skills": skills[:30],
            "featured_links": featured_links,
            "impact_snapshot": impact_snapshot,
            "quick_apply_steps": quick_apply_steps,
        },
    }


def _build_linkedin_audience_variants(
    master_payload: dict[str, Any],
    metrics: dict[str, Any],
    company: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    runtime_mode = str(metrics.get("runtime_mode") or "paper").upper()
    live_orders = "ON" if bool(metrics.get("allow_live_orders")) else "OFF"

    uei = str(company.get("duns_or_uei") or "SQY2XW71ZM51")
    cage = str(company.get("cage_code") or "14TM8")
    registration_note = "VERIFY CURRENT STATUS"

    def _mk_variant(
        audience_id: str,
        audience_label: str,
        headline: str,
        about_short: str,
        about_full: str,
        role_title: str,
        experience: list[str],
        quick_apply_steps: list[str],
        post_templates: list[dict[str, str]],
        impact_snapshot: list[dict[str, str]],
    ) -> dict[str, Any]:
        payload = copy.deepcopy(master_payload)
        payload["audience_id"] = audience_id
        payload["audience_label"] = audience_label
        payload["headline_recommended"] = headline
        payload["headline_variants"] = _dedupe_keep_order(
            [headline] + [str(x) for x in payload.get("headline_variants", []) if str(x).strip()]
        )[:6]
        payload["about"] = about_full
        payload["about_short"] = about_short
        payload["about_full"] = about_full
        payload["experience_bullets"] = experience
        payload["experience_roles"] = [
            {
                "title": role_title,
                "company": "LumaTrader / LumenCore",
                "dates": "2014 - Present",
                "location": "Nashville, TN",
                "bullets": experience,
            }
        ]
        payload["post_templates"] = post_templates
        payload["impact_snapshot"] = impact_snapshot
        payload["quick_apply_steps"] = quick_apply_steps
        payload["profile_fill_pack"] = {
            "headline": headline,
            "about_short": about_short,
            "about_full": about_full,
            "experience": payload["experience_roles"],
            "skills": payload.get("skills", []),
            "featured_links": payload.get("featured_links", []),
            "impact_snapshot": impact_snapshot,
            "quick_apply_steps": quick_apply_steps,
        }
        return payload

    investor = _mk_variant(
        audience_id="investor",
        audience_label="Investor Positioning",
        headline="Founder | Buyer-Owned Baseline Validation | Reproducible Technical Evidence",
        about_short=(
            "I build bounded validation sprints that turn a buyer's baseline, test protocol, and operational data into reproducible evidence and an explicit go/no-go result."
        ),
        about_full=(
            "LumenCore's primary offer is a Buyer-Owned Baseline Validation Sprint. The buyer defines the system, metric, data-access boundary, and acceptance rule. "
            "We produce a frozen baseline, bounded comparison, failure report, reproducible command, and integrity manifest. "
            "The public repository demonstrates first-party software controls; customer outcomes, independent validation, and commercial adoption are not established by those materials."
        ),
        role_title="Founder and Technical Validation Systems Engineer",
        experience=[
            "Designed buyer-owned validation protocols with frozen inputs, explicit acceptance rules, and retained failure evidence.",
            "Built reviewer surfaces exposing control posture, artifact provenance, and known evidence limits.",
            "Implemented deterministic outputs and SHA-256 manifests for repeatable technical review.",
            "Separated software verification from independent field and commercial validation claims.",
            "Created bounded pilot statements of work that preserve customer control over data and deployment.",
        ],
        quick_apply_steps=[
            "Use investor headline for profile identity.",
            "Use investor about copy without unverified financial or performance metrics.",
            "Pin evidence and mission links in featured section.",
            "Use investor post templates only when the linked evidence is public and current.",
        ],
        post_templates=[
            {
                "title": "Investor brief: infrastructure signal",
                "text": (
                    "LumenCore is packaging buyer-owned baseline validation: a frozen baseline, bounded test, failure report, and reproducible evidence pack. "
                    "The next commercial gate is a paid, independently reviewable pilot—not a larger claim."
                ),
            },
            {
                "title": "Evidence-first growth update",
                "text": (
                    "We are looking for one infrastructure operator with a measurable baseline and a narrow validation question. "
                    "The buyer keeps control of data, acceptance criteria, and deployment authority."
                ),
            },
        ],
        impact_snapshot=[
            {"label": "Offer", "value": "BASELINE SPRINT", "hint": "One bounded customer question"},
            {"label": "Control", "value": "BUYER-OWNED", "hint": "Data, criteria, and deployment"},
            {"label": "Evidence", "value": "REPLAYABLE", "hint": "Commands, artifacts, and limits"},
            {"label": "Validation", "value": "PILOT NEEDED", "hint": "Independent result not yet established"},
        ],
    )

    government = _mk_variant(
        audience_id="government",
        audience_label="Government Positioning",
        headline="Mission Systems Architect | Reproducible Evidence | Human-Gated AI Operations",
        about_short=(
            "I build mission-oriented software with deterministic controls, auditable receipts, and explicit human approval gates. "
            f"Documented identifiers: UEI {uei} | CAGE {cage}; verify current registration status before use."
        ),
        about_full=(
            "I design mission systems that prioritize reliability, traceability, and defensible operations. "
            "Across LumaTrader and LumenCore, first-party demonstrations use reproducible outputs, reason-code telemetry, human-gated execution, and machine-readable evidence. "
            f"Documented identifiers: UEI {uei}, CAGE {cage}. Current registration, eligibility, and solicitation fit must be verified against official sources at engagement time."
        ),
        role_title="Founder and Mission Systems Software Architect",
        experience=[
            "Built deterministic, replayable pipelines that preserve chain-of-custody and evidence integrity.",
            "Implemented runtime guardrails, kill-switch semantics, and explicit reason-code telemetry for safe operations.",
            "Produced machine-readable proof bundles for technical validation and oversight workflows.",
            "Maintained API and dashboard surfaces that provide transparent operational state and fallback continuity.",
            "Aligned engineering decisions to mission reliability, control assurance, and audit readiness.",
        ],
        quick_apply_steps=[
            "Set government headline and short about with documented identifiers and a current-status verification note.",
            "Use full about to emphasize deterministic controls and evidence posture.",
            "Highlight mission links and evidence runs in featured section.",
            "Use government post templates for capability updates.",
        ],
        post_templates=[
            {
                "title": "Mission systems readiness update",
                "text": (
                    f"Mission-oriented engineering update: deterministic control lanes, runtime mode {runtime_mode}, live-order posture {live_orders}. "
                    "Public claims remain bounded to linked first-party artifacts."
                ),
            },
            {
                "title": "Evidence and control assurance",
                "text": (
                    f"Documented entity identifiers: UEI {uei}, CAGE {cage}. Current registration and opportunity eligibility require official-source verification. "
                    "Engineering focus: reliability, control integrity, and auditable execution pathways."
                ),
            },
        ],
        impact_snapshot=[
            {"label": "UEI", "value": uei, "hint": "Entity identifier"},
            {"label": "CAGE", "value": cage, "hint": "Government contract code"},
            {"label": "Registration", "value": registration_note, "hint": "Check official source at engagement time"},
            {"label": "Runtime", "value": runtime_mode, "hint": f"Live orders: {live_orders}"},
        ],
    )

    recruiting = _mk_variant(
        audience_id="recruiting",
        audience_label="Recruiting Positioning",
        headline="Python Infrastructure & AI Evaluation Engineer | Reliability | Reproducible Systems",
        about_short=(
            "I build Python infrastructure, AI-evaluation workflows, and reviewer tooling with deterministic behavior, explicit safety gates, and reproducible evidence."
        ),
        about_full=(
            "I am a hands-on builder who ships across architecture, backend systems, automation, and operator-facing dashboards. "
            "My work includes signal and data pipelines, control planes, APIs, CI policy, deterministic reporting, deployment diagnostics, and failure analysis. "
            "I focus on clear interfaces, bounded behavior, and evidence that a skeptical reviewer can replay. Public materials do not establish independent field performance or customer adoption."
        ),
        role_title="Founder and Staff-Level Platform Engineer",
        experience=[
            "Architected and shipped Python/FastAPI services for high-churn quant and operations workloads.",
            "Built end-to-end automation lanes spanning data ingestion, decisioning, and evidence/reporting outputs.",
            "Integrated risk controls, fallback logic, and instrumentation to keep runtime behavior explainable.",
            "Developed dashboard and API surfaces that allow stakeholders to act on live technical context.",
            "Maintained delivery speed while preserving reproducibility, testability, and operational integrity.",
        ],
        quick_apply_steps=[
            "Use recruiting headline to signal infrastructure, AI-evaluation, and reliability depth.",
            "Use short about for recruiter scan and full about for hiring-manager depth.",
            "Paste experience bullets into one role entry and add featured links.",
            "Use recruiting post templates when sharing build or hiring updates.",
        ],
        post_templates=[
            {
                "title": "Platform engineering snapshot",
                "text": (
                    "Platform engineering update: deterministic artifacts, human-gated runtime controls, cross-platform CI, and evidence automation from runtime to reviewer output. "
                    "The next gate is independent validation, not a stronger adjective."
                ),
            },
            {
                "title": "Builder mindset",
                "text": (
                    "I like solving hard reliability and architecture problems end-to-end: control planes, APIs, dashboards, and proof artifacts. "
                    "Shipping practical systems with measurable outcomes."
                ),
            },
        ],
        impact_snapshot=[
            {"label": "Focus", "value": "PYTHON + AI EVAL", "hint": "Infrastructure and evidence systems"},
            {"label": "Controls", "value": "HUMAN-GATED", "hint": "Explicit execution authority"},
            {"label": "Evidence", "value": "REPRODUCIBLE", "hint": "Commands, receipts, and failure reports"},
            {"label": "Runtime", "value": runtime_mode, "hint": f"Live orders: {live_orders}"},
        ],
    )

    return {
        "investor": investor,
        "government": government,
        "recruiting": recruiting,
    }


def _render_linkedin_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    audience_label = str(payload.get("audience_label") or "Master Profile").strip()
    lines.append(f"# LumaLinkedIn Edition V1 - {audience_label}")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    audience_id = str(payload.get("audience_id") or "master").strip()
    lines.append(f"Audience: {audience_id}")
    lines.append("")
    lines.append("## Quick Apply Steps")
    lines.append("")
    steps = payload.get("quick_apply_steps", []) if isinstance(payload.get("quick_apply_steps"), list) else []
    if steps:
        for idx, step in enumerate(steps, start=1):
            lines.append(f"{idx}. {step}")
    else:
        lines.append("1. Apply recommended headline, about, experience, links, and skills in order.")
    lines.append("")
    recommended = str(payload.get("headline_recommended") or "").strip()
    if recommended:
        lines.append("## Recommended Headline")
        lines.append("")
        lines.append(recommended)
        lines.append("")
    lines.append("## Executive Impact Snapshot")
    lines.append("")
    impact = payload.get("impact_snapshot", []) if isinstance(payload.get("impact_snapshot"), list) else []
    if impact:
        for item in impact:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- {item.get('label', 'Metric')}: {item.get('value', '')}"
                + (f" ({item.get('hint', '')})" if item.get("hint") else "")
            )
    else:
        lines.append("- No impact snapshot available.")
    lines.append("")
    lines.append("## Headline Variants")
    lines.append("")
    for idx, item in enumerate(payload.get("headline_variants", []), start=1):
        lines.append(f"{idx}. {item}")
    lines.append("")
    about_short = str(payload.get("about_short") or "").strip()
    if about_short:
        lines.append("## About (Short)")
        lines.append("")
        lines.append(about_short)
        lines.append("")
    lines.append("## About (Full)")
    lines.append("")
    lines.append(str(payload.get("about_full") or payload.get("about", "")))
    lines.append("")
    lines.append("## Experience (Profile Entry)")
    lines.append("")
    roles = payload.get("experience_roles", []) if isinstance(payload.get("experience_roles"), list) else []
    if roles:
        for role in roles:
            if not isinstance(role, dict):
                continue
            role_title = str(role.get("title") or "Role")
            role_company = str(role.get("company") or "Company")
            role_dates = str(role.get("dates") or "")
            role_location = str(role.get("location") or "")
            lines.append(f"### {role_title} | {role_company}")
            lines.append("")
            if role_dates or role_location:
                parts = [part for part in [role_dates, role_location] if part]
                lines.append(" | ".join(parts))
                lines.append("")
            for bullet in role.get("bullets", []):
                lines.append(f"- {bullet}")
            lines.append("")
    else:
        for item in payload.get("experience_bullets", []):
            lines.append(f"- {item}")
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


def _render_linkedin_html(payload: dict[str, Any]) -> str:
    def _esc_text(value: Any) -> str:
        return html.escape(str(value or ""), quote=True)

    def _esc_url(value: Any) -> str:
        raw = str(value or "").strip()
        if raw.startswith(("http://", "https://")):
            return html.escape(raw, quote=True)
        return "#"

    name = _esc_text(payload.get("name") or "Robert BabyRay Ashworth")
    headline_recommended = str(payload.get("headline_recommended") or "").strip()
    if not headline_recommended:
        variants = payload.get("headline_variants", []) if isinstance(payload.get("headline_variants"), list) else []
        headline_recommended = str(variants[0] if variants else "Principal Quant Systems Engineer")
    headline_recommended = _esc_text(headline_recommended)

    about_short = _esc_text(payload.get("about_short") or "")
    about_full = _esc_text(payload.get("about_full") or payload.get("about") or "")

    headline_items = [str(v).strip() for v in payload.get("headline_variants", []) if str(v).strip()]
    impact_snapshot = payload.get("impact_snapshot", []) if isinstance(payload.get("impact_snapshot"), list) else []

    roles = payload.get("experience_roles", []) if isinstance(payload.get("experience_roles"), list) else []
    if not roles:
        bullets = payload.get("experience_bullets", []) if isinstance(payload.get("experience_bullets"), list) else []
        roles = [
            {
                "title": "Founder and Principal Systems Engineer",
                "company": "LumaTrader / LumenCore",
                "dates": "2014 - Present",
                "location": "Nashville, TN",
                "bullets": bullets,
            }
        ]

    featured_links = payload.get("featured_links", []) if isinstance(payload.get("featured_links"), list) else []
    skills = payload.get("skills", []) if isinstance(payload.get("skills"), list) else []
    post_templates = payload.get("post_templates", []) if isinstance(payload.get("post_templates"), list) else []

    headline_list_html = "\n".join(f"<li>{_esc_text(item)}</li>" for item in headline_items)

    impact_html = "\n".join(
        "\n".join(
            [
                "<article class='stat-card'>",
                f"  <p class='stat-label'>{_esc_text(item.get('label') or 'Metric')}</p>",
                f"  <p class='stat-value'>{_esc_text(item.get('value') or '')}</p>",
                f"  <p class='stat-hint'>{_esc_text(item.get('hint') or '')}</p>",
                "</article>",
            ]
        )
        for item in impact_snapshot
        if isinstance(item, dict)
    )

    role_cards_html: list[str] = []
    for role in roles:
        if not isinstance(role, dict):
            continue
        title = _esc_text(role.get("title") or "Role")
        company = _esc_text(role.get("company") or "Company")
        dates = _esc_text(role.get("dates") or "")
        location = _esc_text(role.get("location") or "")
        subtitle = " | ".join(part for part in [dates, location] if part)
        bullets_html = "\n".join(f"<li>{_esc_text(b)}</li>" for b in role.get("bullets", []) if str(b).strip())
        role_cards_html.append(
            "\n".join(
                [
                    "<article class='role-card'>",
                    f"  <h4>{title} <span>@ {company}</span></h4>",
                    f"  <p class='role-sub'>{subtitle}</p>" if subtitle else "",
                    "  <ul class='role-bullets'>",
                    bullets_html,
                    "  </ul>",
                    "</article>",
                ]
            )
        )

    links_html = "\n".join(
        f"<a class='link-chip' href='{_esc_url(item.get('url'))}' target='_blank' rel='noopener noreferrer'>{_esc_text(item.get('label') or 'Link')}</a>"
        for item in featured_links
        if isinstance(item, dict)
    )

    skills_html = "\n".join(
        f"<span class='skill-chip'>{_esc_text(skill)}</span>" for skill in skills if str(skill).strip()
    )

    posts_html = "\n".join(
        "\n".join(
            [
                "<article class='post-card'>",
                f"  <h4>{_esc_text(item.get('title') or 'Post')}</h4>",
                f"  <p>{_esc_text(item.get('text') or '')}</p>",
                "</article>",
            ]
        )
        for item in post_templates
        if isinstance(item, dict)
    )

    generated = _esc_text(payload.get("generated_utc") or "")
    audience_label = _esc_text(payload.get("audience_label") or "Master Profile")
    quick_steps = payload.get("quick_apply_steps", []) if isinstance(payload.get("quick_apply_steps"), list) else []
    quick_steps_html = "\n".join(
        f"<li>{_esc_text(step)}</li>" for step in quick_steps if str(step).strip()
    )
    if not quick_steps_html:
        quick_steps_html = "<li>Apply headline, about, experience, links, and skills in sequence.</li>"

    return f"""<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>LumaLinkedIn Edition V1 - {audience_label}</title>
    <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
    <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
    <link href=\"https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=JetBrains+Mono:wght@400;700&family=Inter:wght@300;400;600;800&display=swap\" rel=\"stylesheet\">
    <style>
        :root {{
            --bg-0: #04060f;
            --bg-1: #07091c;
            --ink: #e6f0ff;
            --ink-dim: #7d8bb5;
            --neon-c: #22d3ee;
            --neon-p: #a855f7;
            --neon-g: #34d399;
            --neon-a: #f59e0b;
            --glass: rgba(15, 23, 50, 0.45);
            --border: rgba(124, 58, 237, 0.28);
            --border-2: rgba(34, 211, 238, 0.38);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html, body {{ min-height: 100%; }}
        body {{
            background: radial-gradient(ellipse at 30% 20%, #1c1052 0%, var(--bg-0) 60%);
            color: var(--ink);
            font-family: 'Inter', -apple-system, sans-serif;
            position: relative;
            overflow-x: hidden;
        }}
        body::before {{
            content: '';
            position: fixed;
            inset: 0;
            pointer-events: none;
            background-image:
                linear-gradient(rgba(34, 211, 238, 0.045) 1px, transparent 1px),
                linear-gradient(90deg, rgba(34, 211, 238, 0.045) 1px, transparent 1px);
            background-size: 44px 44px;
            mask-image: radial-gradient(ellipse at center, black 35%, transparent 80%);
            opacity: 0.85;
        }}
        body::after {{
            content: '';
            position: fixed;
            inset: 0;
            pointer-events: none;
            background: repeating-linear-gradient(0deg, transparent 0px, transparent 3px, rgba(34, 211, 238, 0.015) 3px, rgba(34, 211, 238, 0.015) 4px);
            opacity: 0.5;
        }}
        .stage {{
            max-width: 1180px;
            margin: 0 auto;
            padding: 30px 22px 60px;
            position: relative;
            z-index: 2;
        }}
        .top-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 14px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 16px;
            margin-bottom: 20px;
        }}
        .brand h1 {{
            font-family: 'Orbitron', sans-serif;
            font-size: clamp(20px, 2.8vw, 30px);
            letter-spacing: 3px;
            font-weight: 900;
            background: linear-gradient(135deg, var(--neon-c), var(--neon-p));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .brand .sub {{
            margin-top: 5px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--ink-dim);
            letter-spacing: 1px;
            font-size: 11px;
            text-transform: uppercase;
        }}
        .pill {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            border: 1px solid rgba(52, 211, 153, 0.42);
            background: rgba(52, 211, 153, 0.12);
            border-radius: 999px;
            padding: 6px 12px;
            color: var(--neon-g);
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            letter-spacing: 1px;
            white-space: nowrap;
        }}
        .pill::before {{
            content: '';
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--neon-g);
            box-shadow: 0 0 10px var(--neon-g);
            animation: pulse 1.6s ease-in-out infinite;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(12, minmax(0, 1fr));
            gap: 14px;
        }}
        .card {{
            background: var(--glass);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 16px;
            backdrop-filter: blur(12px) saturate(150%);
            -webkit-backdrop-filter: blur(12px) saturate(150%);
            position: relative;
            overflow: hidden;
            transition: transform 0.25s ease, border-color 0.25s ease;
            animation: reveal 0.5s ease both;
        }}
        .card:nth-child(2) {{ animation-delay: 0.04s; }}
        .card:nth-child(3) {{ animation-delay: 0.08s; }}
        .card:nth-child(4) {{ animation-delay: 0.12s; }}
        .card:nth-child(5) {{ animation-delay: 0.16s; }}
        .card:nth-child(6) {{ animation-delay: 0.2s; }}
        .card::before {{
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(34,211,238,0.07), transparent 45%, rgba(168,85,247,0.06));
            pointer-events: none;
        }}
        .card::after {{
            content: '';
            position: absolute;
            left: 12px;
            right: 12px;
            top: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(34,211,238,0.8), transparent);
            opacity: 0.7;
        }}
        .card:hover {{
            transform: translateY(-2px);
            border-color: var(--border-2);
        }}
        .span-12 {{ grid-column: span 12; }}
        .span-8 {{ grid-column: span 8; }}
        .span-6 {{ grid-column: span 6; }}
        .span-4 {{ grid-column: span 4; }}
        h2 {{
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 2px;
            color: var(--ink-dim);
            text-transform: uppercase;
            font-size: 11px;
            margin-bottom: 10px;
        }}
        .hero-shell {{
            border: 1px solid rgba(34, 211, 238, 0.3);
            border-radius: 12px;
            padding: 14px;
            background: linear-gradient(130deg, rgba(34,211,238,0.08), rgba(168,85,247,0.06));
        }}
        .hero-title {{
            font-size: clamp(22px, 3.8vw, 36px);
            line-height: 1.15;
            font-weight: 800;
            text-wrap: balance;
            margin-bottom: 10px;
        }}
        .hero-sub {{
            font-family: 'JetBrains Mono', monospace;
            color: var(--neon-c);
            font-size: 12px;
            letter-spacing: 0.8px;
        }}
        .workflow-list {{
            padding-left: 18px;
            display: grid;
            gap: 8px;
            line-height: 1.45;
            font-size: 13px;
        }}
        .workflow-list li::marker {{ color: var(--neon-a); }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
        }}
        .stat-card {{
            border: 1px solid rgba(125, 139, 181, 0.34);
            border-radius: 10px;
            padding: 12px;
            background: rgba(7, 9, 28, 0.5);
        }}
        .stat-label {{
            font-family: 'JetBrains Mono', monospace;
            color: var(--ink-dim);
            text-transform: uppercase;
            letter-spacing: 0.8px;
            font-size: 10px;
        }}
        .stat-value {{
            margin-top: 5px;
            font-family: 'Orbitron', sans-serif;
            font-size: 19px;
            font-weight: 700;
            color: var(--ink);
        }}
        .stat-hint {{
            margin-top: 3px;
            color: var(--ink-dim);
            font-size: 11px;
        }}
        .body-copy {{ line-height: 1.65; color: var(--ink); font-size: 15px; }}
        .headline-list {{ list-style: none; display: grid; gap: 8px; }}
        .headline-list li {{
            border: 1px solid rgba(125, 139, 181, 0.35);
            border-radius: 10px;
            padding: 10px;
            background: rgba(7, 9, 28, 0.46);
            line-height: 1.45;
        }}
        .role-card + .role-card {{ margin-top: 12px; }}
        .role-card h4 {{ font-size: 16px; margin-bottom: 6px; color: var(--ink); }}
        .role-card h4 span {{ color: var(--neon-c); font-weight: 600; }}
        .role-sub {{ color: var(--ink-dim); font-size: 12px; margin-bottom: 8px; font-family: 'JetBrains Mono', monospace; }}
        .role-bullets {{ padding-left: 18px; display: grid; gap: 6px; line-height: 1.55; }}
        .chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .link-chip {{
            text-decoration: none;
            color: var(--ink);
            border: 1px solid rgba(34, 211, 238, 0.44);
            background: rgba(34, 211, 238, 0.11);
            border-radius: 999px;
            padding: 8px 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        .link-chip:hover {{ border-color: var(--neon-g); color: var(--neon-g); }}
        .skill-chip {{
            border: 1px solid rgba(168, 85, 247, 0.44);
            background: rgba(168, 85, 247, 0.16);
            border-radius: 999px;
            padding: 7px 11px;
            font-size: 12px;
            color: var(--ink);
        }}
        .post-card + .post-card {{ margin-top: 10px; }}
        .post-card h4 {{ color: var(--neon-c); margin-bottom: 6px; font-size: 14px; }}
        .post-card p {{ line-height: 1.55; color: var(--ink); }}
        footer {{
            margin-top: 16px;
            font-size: 11px;
            color: var(--ink-dim);
            font-family: 'JetBrains Mono', monospace;
            text-align: right;
        }}
        @keyframes pulse {{ 50% {{ opacity: 0.35; }} }}
        @keyframes reveal {{ from {{ opacity: 0; transform: translateY(7px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        @media (max-width: 980px) {{
            .span-8, .span-6, .span-4 {{ grid-column: span 12; }}
            .stats-grid {{ grid-template-columns: 1fr 1fr; }}
            .top-bar {{ flex-direction: column; align-items: flex-start; }}
        }}
        @media (max-width: 620px) {{
            .stats-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <main class=\"stage\">
        <header class=\"top-bar\">
            <div class=\"brand\">
                <h1>LUMALINKEDIN EDITION V1</h1>
                <p class=\"sub\">Domain-parity premium profile pack | {audience_label}</p>
            </div>
            <div class=\"pill\">VISUAL PARITY: PREMIUM</div>
        </header>

        <section class=\"grid\">
            <article class=\"card span-8\">
                <h2>Recommended Headline</h2>
                <div class=\"hero-shell\">
                    <p class=\"hero-title\">{headline_recommended}</p>
                    <p class=\"hero-sub\">{name}</p>
                </div>
            </article>

            <article class=\"card span-4\">
                <h2>Quick Apply Order</h2>
                <ol class=\"workflow-list\">
                    {quick_steps_html}
                </ol>
            </article>

            <article class=\"card span-12\">
                <h2>Executive Impact Snapshot</h2>
                <div class=\"stats-grid\">
                    {impact_html}
                </div>
            </article>

            <article class=\"card span-6\">
                <h2>Headline Variants</h2>
                <ul class=\"headline-list\">
                    {headline_list_html}
                </ul>
            </article>

            <article class=\"card span-6\">
                <h2>About (Short)</h2>
                <p class=\"body-copy\">{about_short}</p>
            </article>

            <article class=\"card span-12\">
                <h2>About (Full)</h2>
                <p class=\"body-copy\">{about_full}</p>
            </article>

            <article class=\"card span-8\">
                <h2>Experience Pack</h2>
                {''.join(role_cards_html)}
            </article>

            <article class=\"card span-4\">
                <h2>Featured Links</h2>
                <div class=\"chips\">
                    {links_html}
                </div>
            </article>

            <article class=\"card span-12\">
                <h2>Skills</h2>
                <div class=\"chips\">
                    {skills_html}
                </div>
            </article>

            <article class=\"card span-12\">
                <h2>Post Templates</h2>
                {posts_html}
            </article>
        </section>

        <footer>Generated UTC: {generated}</footer>
    </main>
</body>
</html>
"""


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
    company = profile.get("company", {}) if isinstance(profile, dict) else {}
    audience_variants = _build_linkedin_audience_variants(linkedin_payload, metrics, company)
    linkedin_payload["available_audiences"] = sorted(audience_variants.keys())
    linkedin_payload["audience_variants"] = audience_variants
    linkedin_md = _render_linkedin_markdown(linkedin_payload)
    linkedin_html = _render_linkedin_html(linkedin_payload)

    tagged_linkedin_json = LINKEDIN_OUT / f"lumalinkedin_v1_{stamp}.json"
    tagged_linkedin_md = LINKEDIN_OUT / f"lumalinkedin_v1_{stamp}.md"
    tagged_linkedin_html = LINKEDIN_OUT / f"lumalinkedin_v1_{stamp}.html"
    latest_linkedin_json = LINKEDIN_OUT / "lumalinkedin_v1_latest.json"
    latest_linkedin_md = LINKEDIN_OUT / "lumalinkedin_v1_latest.md"
    latest_linkedin_html = LINKEDIN_OUT / "lumalinkedin_v1_latest.html"

    _write_json(tagged_linkedin_json, linkedin_payload)
    _write_json(latest_linkedin_json, linkedin_payload)
    _write_text(tagged_linkedin_md, linkedin_md)
    _write_text(latest_linkedin_md, linkedin_md)
    _write_text(tagged_linkedin_html, linkedin_html)
    _write_text(latest_linkedin_html, linkedin_html)

    variant_artifacts: dict[str, dict[str, str]] = {}
    for audience_id, audience_payload in audience_variants.items():
        audience_md = _render_linkedin_markdown(audience_payload)
        audience_html = _render_linkedin_html(audience_payload)

        tagged_variant_json = LINKEDIN_OUT / f"lumalinkedin_v1_{audience_id}_{stamp}.json"
        tagged_variant_md = LINKEDIN_OUT / f"lumalinkedin_v1_{audience_id}_{stamp}.md"
        tagged_variant_html = LINKEDIN_OUT / f"lumalinkedin_v1_{audience_id}_{stamp}.html"
        latest_variant_json = LINKEDIN_OUT / f"lumalinkedin_v1_{audience_id}_latest.json"
        latest_variant_md = LINKEDIN_OUT / f"lumalinkedin_v1_{audience_id}_latest.md"
        latest_variant_html = LINKEDIN_OUT / f"lumalinkedin_v1_{audience_id}_latest.html"

        _write_json(tagged_variant_json, audience_payload)
        _write_json(latest_variant_json, audience_payload)
        _write_text(tagged_variant_md, audience_md)
        _write_text(latest_variant_md, audience_md)
        _write_text(tagged_variant_html, audience_html)
        _write_text(latest_variant_html, audience_html)

        variant_artifacts[audience_id] = {
            "latest_json": str(latest_variant_json),
            "latest_md": str(latest_variant_md),
            "latest_html": str(latest_variant_html),
            "tagged_json": str(tagged_variant_json),
            "tagged_md": str(tagged_variant_md),
            "tagged_html": str(tagged_variant_html),
        }

    variant_manifest = {
        "generated_utc": _now_iso(),
        "scope": "lumalinkedin_v1_audience_variants",
        "audiences": variant_artifacts,
    }
    tagged_variant_manifest = LINKEDIN_OUT / f"lumalinkedin_v1_audience_variants_{stamp}.json"
    latest_variant_manifest = LINKEDIN_OUT / "lumalinkedin_v1_audience_variants_latest.json"
    _write_json(tagged_variant_manifest, variant_manifest)
    _write_json(latest_variant_manifest, variant_manifest)

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
            "latest_linkedin_html": str(latest_linkedin_html),
            "audience_variants_latest_manifest": str(latest_variant_manifest),
            "audience_variants": variant_artifacts,
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
    print(f"LINKEDIN_HTML={latest_linkedin_html}")
    print(f"LINKEDIN_AUDIENCE_VARIANTS={latest_variant_manifest}")
    print(f"SUMMARY={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
