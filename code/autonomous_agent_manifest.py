"""
Autonomous Agent Manifest — Central registry and unified approval queue.

Scans all agent output directories, aggregates pending items into a unified
human-in-the-loop approval queue, and exposes a FastAPI router at /api/agents/*
for the Agent Approval Hub dashboard.

Human-in-the-loop guarantee: Nothing submits to external systems (Kraken, LinkedIn,
grants.gov, email) without an explicit human approve action via this API.
The agent does all the prep; you approve right at ship.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stack root detection
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
_STACK_ROOT = _HERE.parent
_OUT = _STACK_ROOT / "out"
_AUDIT_LOCK = threading.Lock()
_GENESIS_HASH = "0" * 64

# ---------------------------------------------------------------------------
# Agent Registry — canonical definition of every autonomous agent
# ---------------------------------------------------------------------------
AGENT_REGISTRY: dict[str, dict[str, Any]] = {
    "trade_ticket": {
        "id": "trade_ticket",
        "name": "Trade Ticket Stager",
        "icon": "⚡",
        "description": "Stages Kraken spot-order tickets for a separate authenticated execution decision",
        "auto_fire": False,
        "requires_approval": True,
        "priority_rank": 0,
        "queue_source": "execution_approval_queue.json",
        "approval_endpoint": "/api/master/approval/decide",
        "neon_color": "#22d3ee",
        "channel": "kraken",
    },
    "grant_submission": {
        "id": "grant_submission",
        "name": "Grant Submission Agent",
        "icon": "🏛",
        "description": "Assembles local federal application drafts; portal certification and submission stay external",
        "auto_fire": False,
        "requires_approval": True,
        "priority_rank": 1,
        "queue_source": "funding/funding_approval_queue.json",
        "approval_endpoint": "/api/agents/approve",
        "neon_color": "#a855f7",
        "channel": "grants_gov",
    },
    "job_application": {
        "id": "job_application",
        "name": "Job Application Factory",
        "icon": "💼",
        "description": "Builds local job-package drafts; it does not submit them",
        "auto_fire": False,
        "requires_approval": True,
        "priority_rank": 2,
        "queue_source": "jobs/_queue/index.json",
        "approval_endpoint": "/api/agents/approve",
        "neon_color": "#34d399",
        "channel": "linkedin_usajobs",
    },
    "email_dispatch": {
        "id": "email_dispatch",
        "name": "Resume Email Dispatcher",
        "icon": "📧",
        "description": "Stages tailored email-package decisions; sending requires a separate authenticated action",
        "auto_fire": False,
        "requires_approval": True,
        "priority_rank": 3,
        "queue_source": "opportunities/email/email_opportunities_latest.json",
        "approval_endpoint": "/api/agents/approve",
        "neon_color": "#f59e0b",
        "channel": "email",
    },
    "linkedin_post": {
        "id": "linkedin_post",
        "name": "LinkedIn Profile Publisher",
        "icon": "🔗",
        "description": "Stages LinkedIn content decisions; publishing requires a separate authenticated action",
        "auto_fire": False,
        "requires_approval": True,
        "priority_rank": 4,
        "queue_source": "opportunities/linkedin/lumalinkedin_v1_latest.json",
        "approval_endpoint": "/api/agents/approve",
        "neon_color": "#0ea5e9",
        "channel": "linkedin",
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        log.debug("agent manifest read_json failed %s: %s", path, exc)
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _short_id(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _human_unlock_authorized(configured_token: str, authorization: str | None) -> bool:
    """Constant-time bearer-token check kept separate for deterministic tests."""
    if not configured_token or not authorization:
        return False
    scheme, separator, presented = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not presented:
        return False
    return hmac.compare_digest(configured_token, presented)


def _require_human_unlock(authorization: str | None = Header(default=None)) -> None:
    """Require a server-held token before any approval state can change."""
    configured_token = os.getenv("LUMA_HUMAN_UNLOCK_TOKEN", "").strip()
    if not configured_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HumanUnlock is disabled until LUMA_HUMAN_UNLOCK_TOKEN is configured.",
        )
    if not _human_unlock_authorized(configured_token, authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid HumanUnlock bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _public_queue_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove source payloads that may contain addresses, tokens, or private notes."""
    allowed = {
        "id",
        "agent_type",
        "title",
        "description",
        "confidence",
        "priority",
        "state",
        "value_usd",
        "deadline",
        "channel",
        "keywords",
    }
    snapshot = dict(payload)
    snapshot["items"] = [
        {key: value for key, value in item.items() if key in allowed}
        for item in payload.get("items", [])
    ]
    return snapshot


def _append_audit_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Append a process-serialized, SHA-256 chained approval receipt."""
    log_path = _OUT / "ops" / "agent_approval_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with _AUDIT_LOCK:
        previous_hash = _GENESIS_HASH
        if log_path.exists():
            for line in reversed(log_path.read_text(encoding="utf-8-sig").splitlines()):
                try:
                    previous_hash = str(json.loads(line).get("entry_hash") or _GENESIS_HASH)
                    break
                except json.JSONDecodeError:
                    continue
        chained = {**entry, "previous_hash": previous_hash}
        canonical = json.dumps(chained, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        chained["entry_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with log_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(chained, sort_keys=True, ensure_ascii=True) + "\n")
    return chained


# ---------------------------------------------------------------------------
# Per-agent queue builders
# ---------------------------------------------------------------------------

def _build_trade_items() -> list[dict[str, Any]]:
    for candidate in [
        _STACK_ROOT / "execution_approval_queue.json",
        _OUT / "execution_approval_queue.json",
    ]:
        data = _read_json(candidate)
        if data is None:
            continue
        tickets = data if isinstance(data, list) else data.get("tickets", [])
        items = []
        for t in tickets:
            state = str(t.get("status", t.get("approval_state", ""))).upper()
            if state in ("PENDING_HUMAN_APPROVAL", "PENDING"):
                pair = t.get("pair", "")
                side = t.get("side", "BUY")
                notional = float(t.get("notional_usd", t.get("amount", 0)) or 0)
                conf = float(t.get("confidence", t.get("alpha_score", 0.7)) or 0)
                items.append({
                    "id": str(t.get("id", t.get("ticket_id", _short_id(pair + side)))),
                    "agent_type": "trade_ticket",
                    "title": f"{side} {pair}",
                    "description": f"${notional:.2f} notional · {conf * 100:.0f}% confidence",
                    "confidence": conf,
                    "priority": "P0",
                    "state": "pending",
                    "value_usd": notional,
                    "channel": t.get("channel", "kraken"),
                    "metadata": t,
                })
        return items
    return []


def _build_grant_items() -> list[dict[str, Any]]:
    queue_data = _read_json(_OUT / "funding" / "funding_approval_queue.json")
    if not queue_data:
        return []
    pending = queue_data if isinstance(queue_data, list) else queue_data.get("pending", [])
    items = []
    for g in pending:
        state = str(g.get("approval_state", "pending")).upper()
        if state in ("PENDING_HUMAN_APPROVAL", "PENDING", ""):
            items.append({
                "id": str(g.get("id", g.get("opp_id", _short_id(g.get("title", "") + g.get("agency", ""))))),
                "agent_type": "grant_submission",
                "title": g.get("title", "Funding Opportunity"),
                "description": (g.get("agency", "") + " — " + g.get("program", "")).strip(" —"),
                "confidence": float(g.get("fit_score", g.get("score", 0.7)) or 0),
                "priority": g.get("priority", "P1"),
                "state": "pending",
                "value_usd": float(g.get("award_ceiling", g.get("amount", 0)) or 0),
                "deadline": g.get("deadline", g.get("close_date", "")),
                "channel": g.get("source", "grants_gov"),
                "metadata": g,
            })
    return items


def _build_job_items() -> list[dict[str, Any]]:
    index_data = _read_json(_OUT / "jobs" / "_queue" / "index.json")
    if not index_data:
        return []
    items_raw = index_data.get("items", []) if isinstance(index_data, dict) else index_data
    items = []
    for pkg in items_raw:
        if str(pkg.get("state", "draft")).lower() == "draft":
            job_id = str(pkg.get("job_id", pkg.get("id", _short_id(pkg.get("title", "")))))
            priority = str(pkg.get("priority", "P1"))
            items.append({
                "id": job_id,
                "agent_type": "job_application",
                "title": pkg.get("title", "Job Application"),
                "description": f"Channel: {pkg.get('channel', 'linkedin')} · Priority: {priority}",
                "confidence": float(pkg.get("fit_score", 0.7) or 0),
                "priority": priority,
                "state": "pending",
                "value_usd": 0.0,
                "channel": pkg.get("channel", "linkedin"),
                "keywords": pkg.get("matched_keywords", []),
                "metadata": pkg,
            })
    return items


def _build_email_items() -> list[dict[str, Any]]:
    queue_data = _read_json(_OUT / "opportunities" / "email" / "email_opportunities_latest.json")
    if not queue_data:
        return []
    opps = queue_data if isinstance(queue_data, list) else queue_data.get("opportunities", [])
    items = []
    for opp in opps[:10]:
        state = str(opp.get("status", "new")).lower()
        if state in ("new", "queued", "pending"):
            items.append({
                "id": str(opp.get("id", opp.get("message_id", _short_id(opp.get("subject", ""))))),
                "agent_type": "email_dispatch",
                "title": opp.get("subject", "Email Opportunity"),
                "description": opp.get("from_address", opp.get("sender", "Unknown sender")),
                "confidence": float(opp.get("score", opp.get("relevance_score", 0.5)) or 0),
                "priority": "P2",
                "state": "pending",
                "value_usd": 0.0,
                "channel": "email",
                "metadata": opp,
            })
    return items


def _build_linkedin_items() -> list[dict[str, Any]]:
    linkedin_data = _read_json(_OUT / "opportunities" / "linkedin" / "lumalinkedin_v1_latest.json")
    if not linkedin_data:
        return []
    post_templates = linkedin_data.get("post_templates", [])
    sent_path = _OUT / "opportunities" / "linkedin" / "sent_post_ids.json"
    sent_ids: set[str] = set(_read_json(sent_path) or [])
    items = []
    for post in post_templates[:3]:
        text = post.get("text", post.get("content", ""))
        post_id = post.get("id", _short_id(text[:48]))
        if post_id not in sent_ids:
            preview = (text[:120] + "…") if len(text) > 120 else text
            items.append({
                "id": f"linkedin_{post_id}",
                "agent_type": "linkedin_post",
                "title": "LinkedIn Profile Post",
                "description": preview,
                "confidence": 0.92,
                "priority": "P1",
                "state": "pending",
                "value_usd": 0.0,
                "channel": "linkedin",
                "metadata": post,
            })
    return items


# ---------------------------------------------------------------------------
# Unified queue builder
# ---------------------------------------------------------------------------
_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "critical": 0, "high": 1, "medium": 2, "low": 3}


def build_unified_queue() -> dict[str, Any]:
    """Aggregate all pending agent actions into a single approval queue."""
    all_items: list[dict[str, Any]] = []
    all_items.extend(_build_trade_items())
    all_items.extend(_build_grant_items())
    all_items.extend(_build_job_items())
    all_items.extend(_build_email_items())
    all_items.extend(_build_linkedin_items())

    all_items.sort(key=lambda x: (
        _PRIORITY_ORDER.get(str(x.get("priority", "P2")), 5),
        -float(x.get("confidence", 0) or 0),
    ))

    by_type: dict[str, list[dict]] = {}
    for item in all_items:
        by_type.setdefault(item["agent_type"], []).append(item)

    total_value = sum(float(x.get("value_usd", 0) or 0) for x in all_items)

    return {
        "generated_utc": _utc_now(),
        "total_pending": len(all_items),
        "total_value_usd": total_value,
        "items": all_items,
        "by_type": {k: len(v) for k, v in by_type.items()},
        "registry": {
            k: {kk: vv for kk, vv in v.items() if kk not in ("queue_source",)}
            for k, v in AGENT_REGISTRY.items()
        },
    }


# ---------------------------------------------------------------------------
# Approval dispatch handlers
# ---------------------------------------------------------------------------

def _approve_job(item_id: str) -> dict[str, Any]:
    index_path = _OUT / "jobs" / "_queue" / "index.json"
    data = _read_json(index_path)
    if not data:
        return {"success": False, "message": "Job queue index not found"}
    items_raw = data.get("items", []) if isinstance(data, dict) else data
    updated = False
    for pkg in items_raw:
        if str(pkg.get("job_id", pkg.get("id", ""))) == item_id:
            if str(pkg.get("state", "")).lower() == "approved":
                return {
                    "success": True,
                    "idempotent": True,
                    "message": f"Job {item_id!r} was already approved",
                }
            pkg["state"] = "approved"
            pkg["approved_utc"] = _utc_now()
            updated = True
            break
    if not updated:
        return {"success": False, "message": f"Job {item_id!r} not found in queue"}
    if isinstance(data, dict):
        data["items"] = items_raw
        data["n_draft"] = sum(1 for p in items_raw if p.get("state") == "draft")
        data["n_approved"] = sum(1 for p in items_raw if p.get("state") == "approved")
        write_data = data
    else:
        write_data = items_raw
    try:
        index_path.write_text(json.dumps(write_data, indent=2), encoding="utf-8")
        return {
            "success": True,
            "message": f"Job {item_id!r} moved to approved",
            "next_action": "Open run_dir/SUBMIT_HOWTO.md for submission instructions",
        }
    except Exception as exc:
        return {"success": False, "message": str(exc)}


def _approve_grant(item_id: str) -> dict[str, Any]:
    queue_path = _OUT / "funding" / "funding_approval_queue.json"
    data = _read_json(queue_path)
    if not data:
        return {"success": False, "message": "Grant queue not found"}
    pending = data if isinstance(data, list) else data.get("pending", [])
    target = next((g for g in pending if str(g.get("id", g.get("opp_id", ""))) == item_id), None)
    if isinstance(data, dict) and target is None:
        approved = data.get("approved", [])
        already = next(
            (g for g in approved if str(g.get("id", g.get("opp_id", ""))) == item_id),
            None,
        )
        if already is not None:
            return {
                "success": True,
                "idempotent": True,
                "message": f"Grant {item_id!r} was already approved",
            }
    if target is None:
        return {"success": False, "message": f"Grant {item_id!r} not found"}
    target["approval_state"] = "APPROVED"
    target["approved_utc"] = _utc_now()
    if isinstance(data, dict):
        data["pending"] = [g for g in pending if str(g.get("id", g.get("opp_id", ""))) != item_id]
        data.setdefault("approved", []).append(target)
        write_data = data
    else:
        write_data = pending
    try:
        queue_path.write_text(json.dumps(write_data, indent=2), encoding="utf-8")
        return {
            "success": True,
            "message": f"Grant {item_id!r} approved",
            "next_action": "Open grants.html and use the 3-minute submit lane",
        }
    except Exception as exc:
        return {"success": False, "message": str(exc)}


def _approve_linkedin(item_id: str) -> dict[str, Any]:
    publish_queue_path = _OUT / "opportunities" / "linkedin" / "publish_queue.json"
    publish_queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue = list(_read_json(publish_queue_path) or [])
    post_id = item_id.replace("linkedin_", "")
    if any(str(row.get("post_id", "")) == post_id for row in queue):
        return {
            "success": True,
            "idempotent": True,
            "message": f"LinkedIn post {post_id!r} was already staged",
        }
    queue.append({"post_id": post_id, "approved_utc": _utc_now(), "status": "approved"})
    try:
        publish_queue_path.write_text(json.dumps(queue, indent=2), encoding="utf-8")
        return {
            "success": True,
            "message": f"LinkedIn post {post_id!r} queued for publish",
            "next_action": "Run lumalinkedin_resume_engine_v1.py --publish-linkedin-summary (requires OAuth token)",
        }
    except Exception as exc:
        return {"success": False, "message": str(exc)}


def _approve_email(item_id: str) -> dict[str, Any]:
    dispatch_queue_path = _OUT / "opportunities" / "email" / "email_dispatch_approved.json"
    dispatch_queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue = list(_read_json(dispatch_queue_path) or [])
    if any(str(row.get("item_id", "")) == item_id for row in queue):
        return {
            "success": True,
            "idempotent": True,
            "message": f"Email dispatch {item_id!r} was already staged",
        }
    queue.append({"item_id": item_id, "approved_utc": _utc_now(), "status": "approved"})
    try:
        dispatch_queue_path.write_text(json.dumps(queue, indent=2), encoding="utf-8")
        return {
            "success": True,
            "message": f"Email dispatch {item_id!r} approved",
            "next_action": "Run RUN_OPPORTUNITY_AUTONOMY_LOOP.ps1 to dispatch",
        }
    except Exception as exc:
        return {"success": False, "message": str(exc)}


def _dispatch_approval(item_id: str, item_type: str, action: str) -> dict[str, Any]:
    if action == "skip":
        return {
            "success": True,
            "message": f"Recorded a skip decision for {item_id}; the source queue was not changed",
            "action": "skip",
            "source_queue_changed": False,
        }
    if action == "delay":
        return {
            "success": True,
            "message": f"Recorded a delay decision for {item_id}; it will re-surface next cycle",
            "action": "delay",
            "source_queue_changed": False,
        }
    # approve
    if item_type == "trade_ticket":
        return {
            "success": True,
            "message": f"Trade ticket {item_id!r} staged — complete via /api/master/approval/decide",
            "redirect_endpoint": "/api/master/approval/decide",
            "action": "approve",
        }
    if item_type == "job_application":
        return _approve_job(item_id)
    if item_type == "grant_submission":
        return _approve_grant(item_id)
    if item_type == "linkedin_post":
        return _approve_linkedin(item_id)
    if item_type == "email_dispatch":
        return _approve_email(item_id)
    return {"success": False, "message": f"Unknown agent type: {item_type!r}"}


# ---------------------------------------------------------------------------
# FastAPI Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api/agents", tags=["agents"])


class ApproveRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9_.:-]+$")
    item_type: Literal[
        "trade_ticket",
        "grant_submission",
        "job_application",
        "email_dispatch",
        "linkedin_post",
    ]
    action: Literal["approve", "skip", "delay"] = "approve"
    notes: str = Field(default="", max_length=1000)


@router.get("/queue")
def get_agent_queue() -> dict[str, Any]:
    """Public-safe queue summary with private source payloads removed."""
    return _public_queue_snapshot(build_unified_queue())


@router.get("/registry")
def get_agent_registry() -> dict[str, Any]:
    """Agent registry — definitions and capabilities of all autonomous agents."""
    return {"agents": AGENT_REGISTRY, "generated_utc": _utc_now(), "count": len(AGENT_REGISTRY)}


@router.post("/approve")
def approve_agent_action(
    req: ApproveRequest,
    _: None = Depends(_require_human_unlock),
) -> dict[str, Any]:
    """
    Human-in-the-loop approval gate.
    Approve, skip, or delay a queued agent action.
    All external submissions require this call — nothing auto-ships.
    """
    result = _dispatch_approval(req.item_id, req.item_type, req.action)

    entry = {
        "timestamp_utc": _utc_now(),
        "item_id": req.item_id,
        "item_type": req.item_type,
        "action": req.action,
        "notes": req.notes,
        "success": result.get("success", False),
        "message": result.get("message", ""),
    }
    try:
        entry = _append_audit_entry(entry)
    except Exception as exc:
        log.warning("Failed to write agent approval log: %s", exc)
        entry["audit_write_error"] = type(exc).__name__

    return {**entry, **result}


@router.get("/log")
def get_approval_log(
    limit: int = 50,
    _: None = Depends(_require_human_unlock),
) -> dict[str, Any]:
    """Recent agent approval audit log."""
    log_path = _OUT / "ops" / "agent_approval_log.jsonl"
    entries: list[dict] = []
    limit = max(1, min(limit, 250))
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8-sig").strip().splitlines()
        for line in lines[-limit:][::-1]:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    return {"entries": entries, "total": len(entries), "generated_utc": _utc_now()}
