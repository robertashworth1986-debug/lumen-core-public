from __future__ import annotations

import argparse
import atexit
import importlib.util
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from execution.live_action_authority import (
        DEFAULT_AUTHORITY_TTL_SEC,
        sha256_file,
        validate_live_action_authority,
    )
except ImportError:
    try:
        from live_action_authority import (
            DEFAULT_AUTHORITY_TTL_SEC,
            sha256_file,
            validate_live_action_authority,
        )
    except ImportError:
        _authority_path = Path(__file__).with_name("live_action_authority.py")
        _authority_spec = importlib.util.spec_from_file_location(
            "live_action_authority_autofire",
            _authority_path,
        )
        if _authority_spec is None or _authority_spec.loader is None:
            raise RuntimeError("live action authority validator is unavailable")
        _authority_module = importlib.util.module_from_spec(_authority_spec)
        _authority_spec.loader.exec_module(_authority_module)
        DEFAULT_AUTHORITY_TTL_SEC = _authority_module.DEFAULT_AUTHORITY_TTL_SEC
        sha256_file = _authority_module.sha256_file
        validate_live_action_authority = _authority_module.validate_live_action_authority


ROOT = Path(__file__).resolve().parents[2]
OUT_EXEC = ROOT / "out" / "execution"
DEFAULT_LOG_FILE = OUT_EXEC / "approval_autofire_log.jsonl"
DEFAULT_STATE_FILE = OUT_EXEC / "approval_autofire_state.json"
DEFAULT_HEARTBEAT_FILE = OUT_EXEC / "approval_autofire_heartbeat.json"
DEFAULT_POLICY_FILE = ROOT / "run" / "approval_autofire_policy.json"
DEFAULT_RUNTIME_FILE = ROOT / "config" / "runtime_control.json"
DEFAULT_ACTION_RECEIPT_FILE = OUT_EXEC / "live_action_time_approval_receipt_latest.json"
DEFAULT_ACTION_RECEIPT_TTL_SEC = DEFAULT_AUTHORITY_TTL_SEC
LOCK_FILE = OUT_EXEC / "approval_autofire_daemon.lock"
LOCK_STALE_SEC = 6 * 60 * 60

DEFAULT_POLICY: dict[str, Any] = {
    "schema": "approval_autofire_policy_v1",
    "max_approvals_per_cycle": 3,
    "max_buy_approvals_per_cycle": 1,
    "prioritize_sells": True,
    "buy_edge_floor": 0.50,
    "buy_win_rate_floor_pct": 50.0,
    "buy_bucket_n_floor": 5,
    "buy_pair_cooldown_sec": 240.0,
    "buy_min_execution_quality_score": 10.0,
    "buy_min_liquidity_score": 8.0,
    "buy_max_estimated_friction_bps": 45.0,
    "buy_min_risk_adjusted_net_edge_pct": 0.25,
    "buy_pending_ttl_hours": 6.0,
    "buy_pair_overrides": {},
    "buy_max_notional_usd": 0.0,
    "min_free_usd_to_buy": 0.0,
    "require_edge_score": False,
    "pause_buys_if_daily_net_lte_usd": None,
    "auto_seed_sell_tickets": False,
    "auto_seed_buy_tickets": False,
    "auto_seed_buy_force": False,
    "scan_refill_when_queue_below": 0,
    "scan_refill_validate": False,
    "scan_refill_use_cached": True,
    "disable_buy_seeding_when_paused": True,
    "skip_scan_refill_when_buy_paused": True,
    "force_zero_buy_budget_when_paused": True,
}

BUY_POLICY_OVERRIDE_KEYS = (
    "require_edge_score",
    "buy_edge_floor",
    "buy_win_rate_floor_pct",
    "buy_bucket_n_floor",
    "buy_pair_cooldown_sec",
    "buy_min_execution_quality_score",
    "buy_min_liquidity_score",
    "buy_max_estimated_friction_bps",
    "buy_min_risk_adjusted_net_edge_pct",
    "buy_max_notional_usd",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_utc(value: Any) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def to_optional_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def first_optional_float(*values: Any) -> Optional[float]:
    for value in values:
        parsed = to_optional_float(value)
        if parsed is not None:
            return parsed
    return None


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return int(default)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


autofire_authority_state = validate_live_action_authority


def request_json(
    url: str,
    method: str = "GET",
    payload: Optional[dict[str, Any]] = None,
    timeout: int = 20,
) -> dict[str, Any]:
    headers: dict[str, str] = {}
    data: Optional[bytes] = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    req = Request(url=url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            parsed = json.loads(body)
            return parsed if isinstance(parsed, dict) else {"status": "bad_response", "body": parsed}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body[:800]}
        return {"status": "http_error", "code": exc.code, "error": parsed}
    except URLError as exc:
        return {"status": "network_error", "error": str(exc)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def load_policy(path: Path) -> dict[str, Any]:
    policy = dict(DEFAULT_POLICY)
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                for key in DEFAULT_POLICY.keys():
                    if key in payload:
                        policy[key] = payload[key]
        else:
            write_json(path, policy)
    except Exception:
        pass
    return policy


def ticket_age_hours(ticket: dict[str, Any], now_ts: Optional[float] = None) -> float:
    dt = parse_utc(ticket.get("timestamp"))
    if dt is None:
        return float("inf")
    ref_ts = now_ts if now_ts is not None else time.time()
    return max(0.0, ref_ts - dt.timestamp()) / 3600.0


def resolve_pair_buy_policy(policy: dict[str, Any], pair: str) -> dict[str, Any]:
    effective = {key: policy.get(key) for key in BUY_POLICY_OVERRIDE_KEYS}
    pair_clean = str(pair or "").strip().upper()
    if not pair_clean:
        return effective

    overrides = policy.get("buy_pair_overrides")
    if not isinstance(overrides, dict):
        return effective

    pair_override: Optional[dict[str, Any]] = None
    for raw_pair, cfg in overrides.items():
        if not isinstance(cfg, dict):
            continue
        if str(raw_pair or "").strip().upper() == pair_clean:
            pair_override = cfg
            break

    if pair_override is None:
        return effective

    for key in BUY_POLICY_OVERRIDE_KEYS:
        if key in pair_override:
            effective[key] = pair_override[key]
    return effective


def reason_histogram(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        side = str(row.get("side") or "unknown").strip().lower() or "unknown"
        raw_reasons = row.get("reasons")
        if isinstance(raw_reasons, list):
            reasons = [str(x or "unspecified").strip() or "unspecified" for x in raw_reasons]
        else:
            reason = str(row.get("reason") or "unspecified").strip() or "unspecified"
            reasons = [reason]

        for reason in reasons:
            key = f"{side}:{reason}"
            counts[key] = counts.get(key, 0) + 1

    return [
        {"reason": reason, "count": count}
        for reason, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def load_state(path: Path) -> tuple[set[str], dict[str, float]]:
    seen: set[str] = set()
    pair_last_buy_approval_ts: dict[str, float] = {}
    if not path.exists():
        return seen, pair_last_buy_approval_ts

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return seen, pair_last_buy_approval_ts

    rows = payload.get("seen_ticket_ids") if isinstance(payload, dict) else []
    if isinstance(rows, list):
        seen = {str(x).strip() for x in rows if str(x).strip()}

    pair_rows = payload.get("pair_last_buy_approval_ts") if isinstance(payload, dict) else {}
    if isinstance(pair_rows, dict):
        for pair, raw_ts in pair_rows.items():
            p = str(pair or "").strip().upper()
            if not p:
                continue
            if isinstance(raw_ts, (int, float)):
                pair_last_buy_approval_ts[p] = float(raw_ts)
                continue
            dt = parse_utc(raw_ts)
            if dt is not None:
                pair_last_buy_approval_ts[p] = dt.timestamp()

    return seen, pair_last_buy_approval_ts


def save_state(path: Path, seen: set[str], pair_last_buy_approval_ts: dict[str, float]) -> None:
    pair_rows: dict[str, str] = {}
    for pair, ts in pair_last_buy_approval_ts.items():
        if ts <= 0:
            continue
        pair_rows[str(pair).upper()] = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    payload = {
        "generated_utc": now_utc(),
        "schema": "approval_autofire_state_v2",
        "seen_ticket_ids": sorted(seen),
        "pair_last_buy_approval_ts": pair_rows,
    }
    write_json(path, payload)


def _release_lock() -> None:
    if not LOCK_FILE.exists():
        return
    try:
        payload = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        owner_pid = int(payload.get("pid", 0) or 0)
    except Exception:
        owner_pid = 0
    if owner_pid and owner_pid != os.getpid():
        return
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        probe = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        out = (probe.stdout or "").strip()
        if not out:
            return False
        if "No tasks are running" in out:
            return False
        return f",\"{pid}\"," in out or out.startswith(f"\"python.exe\",\"{pid}\",")
    except Exception:
        return False


def _acquire_lock(log_file: Path) -> bool:
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

    if LOCK_FILE.exists():
        try:
            payload = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
            owner_pid = int(payload.get("pid", 0) or 0)
        except Exception:
            owner_pid = 0
        try:
            age_sec = max(0.0, time.time() - LOCK_FILE.stat().st_mtime)
        except Exception:
            age_sec = 0.0

        if owner_pid > 0 and _pid_running(owner_pid):
            append_jsonl(
                log_file,
                {
                    "ts": now_utc(),
                    "event": "daemon_lock_active_exit",
                    "lock_file": str(LOCK_FILE),
                    "lock_age_sec": round(age_sec, 3),
                    "owner_pid": owner_pid,
                },
            )
            print(
                "[APPROVAL-AUTOFIRE] lock already active; exiting duplicate process"
                + f" lock={LOCK_FILE} owner_pid={owner_pid} age_sec={age_sec:.1f}",
                flush=True,
            )
            return False

        if age_sec > LOCK_STALE_SEC:
            try:
                LOCK_FILE.unlink(missing_ok=True)
            except Exception:
                pass
        else:
            try:
                LOCK_FILE.unlink(missing_ok=True)
            except Exception:
                pass

    payload = {
        "pid": os.getpid(),
        "created_utc": now_utc(),
        "lock_file": str(LOCK_FILE),
    }
    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        return True
    except FileExistsError:
        return False
    except Exception:
        return False


def eligible_ticket(
    ticket: dict[str, Any],
    controller: str,
    started_at: datetime,
    include_existing: bool,
) -> bool:
    if str(ticket.get("approval_state", "")).upper() != "PENDING_HUMAN_APPROVAL":
        return False
    if not bool(ticket.get("guards_pass_all", False)):
        return False

    ticket_controller = str(ticket.get("controller", "")).strip()
    if ticket_controller != controller:
        return False

    if include_existing:
        return True

    ts = parse_utc(ticket.get("timestamp"))
    if ts is None:
        return False
    return ts >= started_at


def build_decide_payload(ticket_id: str, controller: str, reason: str) -> dict[str, Any]:
    return {
        "ticket_id": ticket_id,
        "decision": "approve",
        "controller": controller,
        "reason": reason,
        "confirm_phrase": f"FIRE {ticket_id}",
    }


def build_reject_payload(ticket_id: str, controller: str, reason: str) -> dict[str, Any]:
    return {
        "ticket_id": ticket_id,
        "decision": "reject",
        "controller": controller,
        "reason": reason,
        "confirm_phrase": "",
    }


def expire_stale_pending_buys(
    tickets: list[dict[str, Any]],
    gateway_url: str,
    controller: str,
    max_pending_buy_age_hours: float,
    log_file: Path,
) -> dict[str, Any]:
    now_ts = time.time()
    attempted = 0
    expired = 0
    failed = 0
    details: list[dict[str, Any]] = []

    ttl_hours = max(0.0, float(max_pending_buy_age_hours))
    if ttl_hours <= 0:
        return {
            "enabled": False,
            "attempted": 0,
            "expired_count": 0,
            "failed_count": 0,
            "max_pending_buy_age_hours": ttl_hours,
            "details": [],
        }

    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue
        if str(ticket.get("approval_state") or "").upper() != "PENDING_HUMAN_APPROVAL":
            continue
        if str(ticket.get("side") or "").strip().lower() != "buy":
            continue

        age_hours = ticket_age_hours(ticket, now_ts=now_ts)
        if age_hours < ttl_hours:
            continue

        ticket_id = str(ticket.get("ticket_id") or "").strip()
        if not ticket_id:
            continue

        attempted += 1
        reason = (
            "approval_autofire_stale_buy_expiry "
            f"age_hours={age_hours:.2f} ttl_hours={ttl_hours:.2f}"
        )
        payload = build_reject_payload(ticket_id=ticket_id, controller=controller, reason=reason)
        result = request_json(
            f"{gateway_url}/api/master/approval/decide",
            method="POST",
            payload=payload,
        )
        status = str(result.get("status") if isinstance(result, dict) else "unknown")
        ok = status == "rejected"
        if ok:
            expired += 1
        else:
            failed += 1

        row = {
            "ticket_id": ticket_id,
            "pair": str(ticket.get("pair") or "").strip().upper(),
            "status": status,
            "age_hours": round(age_hours, 4),
        }
        if not ok:
            row["result"] = result
        details.append(row)

        append_jsonl(
            log_file,
            {
                "ts": now_utc(),
                "event": "stale_buy_auto_expire_attempt",
                "ticket_id": ticket_id,
                "pair": row["pair"],
                "age_hours": row["age_hours"],
                "ttl_hours": round(ttl_hours, 4),
                "status": status,
                "result": result,
            },
        )

    return {
        "enabled": True,
        "attempted": attempted,
        "expired_count": expired,
        "failed_count": failed,
        "max_pending_buy_age_hours": ttl_hours,
        "details": details[:25],
    }


def extract_perf_net(perf_payload: dict[str, Any]) -> tuple[Optional[float], Optional[str]]:
    session = perf_payload.get("session") if isinstance(perf_payload, dict) else {}
    if not isinstance(session, dict):
        session = {}

    net_today = to_optional_float(session.get("realized_pnl_net_usd"))
    sells_today = to_int(session.get("sells_count"), 0)
    if net_today is not None and sells_today > 0:
        return net_today, "today_utc"

    last_24h = perf_payload.get("last_24h") if isinstance(perf_payload, dict) else {}
    if not isinstance(last_24h, dict):
        last_24h = {}
    net_24h = to_optional_float(last_24h.get("realized_pnl_net_usd"))
    if net_24h is not None:
        return net_24h, "last_24h"

    if net_today is not None:
        return net_today, "today_utc"
    return None, None


def resolve_buy_pause(
    policy: dict[str, Any],
    queue_payload: dict[str, Any],
    perf_payload: dict[str, Any],
) -> tuple[bool, str, Optional[float], Optional[float], Optional[str]]:
    floor = to_optional_float(policy.get("pause_buys_if_daily_net_lte_usd"))
    if floor is None:
        flags = queue_payload.get("control_flags") if isinstance(queue_payload, dict) else {}
        if not isinstance(flags, dict):
            flags = {}
        max_daily_loss_usd = abs(to_float(flags.get("max_daily_loss_usd"), 0.0))
        if max_daily_loss_usd > 0:
            floor = -max_daily_loss_usd

    net_usd, scope = extract_perf_net(perf_payload)
    if floor is None or net_usd is None:
        return False, "no_daily_loss_floor", floor, net_usd, scope

    if net_usd <= floor:
        return True, f"{scope} net ${net_usd:.2f} <= floor ${floor:.2f}", floor, net_usd, scope
    return False, f"{scope} net ${net_usd:.2f} above floor ${floor:.2f}", floor, net_usd, scope


def resolve_buy_notional_cap(policy: dict[str, Any], queue_payload: dict[str, Any]) -> float:
    cap = to_float(policy.get("buy_max_notional_usd"), 0.0)
    if cap > 0:
        return cap
    flags = queue_payload.get("control_flags") if isinstance(queue_payload, dict) else {}
    if not isinstance(flags, dict):
        flags = {}
    return max(0.0, to_float(flags.get("max_notional_per_trade_usd"), 0.0))


def resolve_usd_equity(balance_payload: dict[str, Any]) -> Optional[float]:
    if not isinstance(balance_payload, dict):
        return None
    value = to_optional_float(balance_payload.get("usd_equity"))
    if value is None:
        return None
    return max(0.0, float(value))


def compute_sell_priority(ticket: dict[str, Any]) -> float:
    note = str(ticket.get("note") or "").upper()
    age_hours = max(0.0, to_float(ticket.get("age_hours"), 0.0))
    if "HARD" in note:
        base = 120.0
    elif "TRAIL" in note:
        base = 100.0
    elif "TP" in note or "LOCK" in note:
        base = 80.0
    else:
        base = 60.0
    return base + min(age_hours * 2.0, 24.0)


def compute_buy_priority(ticket: dict[str, Any], metrics: dict[str, Any]) -> float:
    edge = to_float(metrics.get("edge_score"), 0.0)
    risk_adj_edge = to_float(metrics.get("risk_adjusted_net_edge_pct"), edge)
    wr = to_float(metrics.get("bucket_win_rate_pct"), 0.0)
    n = max(0, to_int(metrics.get("bucket_n"), 0))
    exec_quality = to_float(metrics.get("execution_quality_score"), 0.0)
    friction_bps = max(0.0, to_float(metrics.get("estimated_friction_bps"), 0.0))
    age_hours = max(0.0, to_float(ticket.get("age_hours"), 0.0))
    effective_edge = risk_adj_edge if risk_adj_edge > 0 else edge
    return (
        effective_edge * 100.0
        + wr
        + min(n, 100) * 0.10
        + exec_quality * 0.75
        - min(friction_bps, 120.0) * 0.20
        + min(age_hours, 24.0) * 0.20
    )


def evaluate_buy_ticket(
    ticket: dict[str, Any],
    policy: dict[str, Any],
    now_ts: float,
    pair_last_buy_approval_ts: dict[str, float],
    buy_paused: bool,
    buy_pause_reason: str,
    buy_notional_cap: float,
) -> tuple[bool, list[str], dict[str, Any]]:
    reasons: list[str] = []

    pair = str(ticket.get("pair") or "").strip().upper()
    pair_policy = resolve_pair_buy_policy(policy=policy, pair=pair)
    notional_usd = to_float(ticket.get("notional_usd"), 0.0)
    scanner_meta = ticket.get("scanner_meta")
    if not isinstance(scanner_meta, dict):
        scanner_meta = {}

    alpha_gate = scanner_meta.get("alpha_gate")
    if not isinstance(alpha_gate, dict):
        alpha_gate = {}

    strategy_meta = scanner_meta.get("strategy")
    if not isinstance(strategy_meta, dict):
        strategy_meta = {}

    profitability_meta = strategy_meta.get("profitability")
    if not isinstance(profitability_meta, dict):
        profitability_meta = {}

    edge_score = first_optional_float(
        scanner_meta.get("edge_score"),
        scanner_meta.get("alpha_edge_score"),
        alpha_gate.get("risk_adjusted_net_edge_pct"),
        alpha_gate.get("net_edge_pct"),
        alpha_gate.get("alpha_edge_score"),
        profitability_meta.get("risk_adjusted_net_edge_pct"),
        profitability_meta.get("net_edge_pct"),
        profitability_meta.get("raw_edge_pct"),
    )
    win_rate_pct = to_optional_float(scanner_meta.get("bucket_win_rate_pct"))
    execution_quality_score = first_optional_float(
        scanner_meta.get("execution_quality_score"),
        alpha_gate.get("execution_quality_score"),
        profitability_meta.get("execution_quality_score"),
    )
    liquidity_score = first_optional_float(
        scanner_meta.get("liquidity_score"),
        alpha_gate.get("liquidity_score"),
        profitability_meta.get("liquidity_score"),
    )
    estimated_friction_bps = first_optional_float(
        alpha_gate.get("estimated_friction_bps"),
        profitability_meta.get("estimated_friction_bps"),
    )
    risk_adjusted_net_edge_pct = first_optional_float(
        alpha_gate.get("risk_adjusted_net_edge_pct"),
        profitability_meta.get("risk_adjusted_net_edge_pct"),
        alpha_gate.get("net_edge_pct"),
        profitability_meta.get("net_edge_pct"),
    )

    bucket_n = None
    if scanner_meta.get("bucket_n") not in (None, ""):
        try:
            bucket_n = int(float(scanner_meta.get("bucket_n")))
        except Exception:
            bucket_n = None

    if buy_paused:
        reasons.append(buy_pause_reason)

    pair_notional_cap = max(0.0, to_float(pair_policy.get("buy_max_notional_usd"), 0.0))
    effective_notional_cap = buy_notional_cap
    if pair_notional_cap > 0:
        effective_notional_cap = (
            min(effective_notional_cap, pair_notional_cap)
            if effective_notional_cap > 0
            else pair_notional_cap
        )
    if effective_notional_cap > 0 and notional_usd > effective_notional_cap:
        reasons.append(f"notional ${notional_usd:.2f} exceeds cap ${effective_notional_cap:.2f}")

    require_edge = bool(pair_policy.get("require_edge_score", False))
    edge_floor = to_float(pair_policy.get("buy_edge_floor"), 0.0)
    if edge_score is None:
        if require_edge:
            reasons.append("missing edge_score")
    elif edge_score < edge_floor:
        reasons.append(f"edge {edge_score:.3f} < floor {edge_floor:.3f}")

    win_floor = to_float(pair_policy.get("buy_win_rate_floor_pct"), 0.0)
    if win_rate_pct is not None and win_rate_pct < win_floor:
        reasons.append(f"win_rate {win_rate_pct:.1f}% < floor {win_floor:.1f}%")

    n_floor = max(0, to_int(pair_policy.get("buy_bucket_n_floor"), 0))
    if bucket_n is not None and bucket_n < n_floor:
        reasons.append(f"bucket_n {bucket_n} < floor {n_floor}")

    min_exec_quality = max(0.0, to_float(pair_policy.get("buy_min_execution_quality_score"), 0.0))
    if execution_quality_score is not None and execution_quality_score < min_exec_quality:
        reasons.append(
            f"execution_quality {execution_quality_score:.2f} < floor {min_exec_quality:.2f}"
        )

    min_liquidity = max(0.0, to_float(pair_policy.get("buy_min_liquidity_score"), 0.0))
    if liquidity_score is not None and liquidity_score < min_liquidity:
        reasons.append(
            f"liquidity_score {liquidity_score:.2f} < floor {min_liquidity:.2f}"
        )

    max_friction_bps = max(0.0, to_float(pair_policy.get("buy_max_estimated_friction_bps"), 0.0))
    if (
        max_friction_bps > 0
        and estimated_friction_bps is not None
        and estimated_friction_bps > max_friction_bps
    ):
        reasons.append(
            f"estimated_friction_bps {estimated_friction_bps:.2f} > cap {max_friction_bps:.2f}"
        )

    risk_edge_floor = max(0.0, to_float(pair_policy.get("buy_min_risk_adjusted_net_edge_pct"), 0.0))
    if risk_adjusted_net_edge_pct is not None and risk_adjusted_net_edge_pct < risk_edge_floor:
        reasons.append(
            f"risk_adjusted_net_edge_pct {risk_adjusted_net_edge_pct:.3f} < floor {risk_edge_floor:.3f}"
        )

    cooldown_sec = max(0.0, to_float(pair_policy.get("buy_pair_cooldown_sec"), 0.0))
    if pair and cooldown_sec > 0:
        last_ts = pair_last_buy_approval_ts.get(pair, 0.0)
        if last_ts > 0 and (now_ts - last_ts) < cooldown_sec:
            reasons.append(
                f"pair cooldown active ({now_ts - last_ts:.0f}s < {cooldown_sec:.0f}s)"
            )

    metrics = {
        "pair": pair,
        "notional_usd": round(notional_usd, 4),
        "edge_score": edge_score,
        "bucket_win_rate_pct": win_rate_pct,
        "bucket_n": bucket_n,
        "execution_quality_score": execution_quality_score,
        "liquidity_score": liquidity_score,
        "estimated_friction_bps": estimated_friction_bps,
        "risk_adjusted_net_edge_pct": risk_adjusted_net_edge_pct,
        "effective_notional_cap": effective_notional_cap,
        "pair_policy": {
            "require_edge_score": bool(pair_policy.get("require_edge_score", False)),
            "buy_edge_floor": edge_floor,
            "buy_win_rate_floor_pct": win_floor,
            "buy_bucket_n_floor": n_floor,
            "buy_pair_cooldown_sec": cooldown_sec,
            "buy_min_execution_quality_score": min_exec_quality,
            "buy_min_liquidity_score": min_liquidity,
            "buy_max_estimated_friction_bps": max_friction_bps,
            "buy_min_risk_adjusted_net_edge_pct": risk_edge_floor,
            "buy_max_notional_usd": pair_notional_cap,
        },
    }
    return len(reasons) == 0, reasons, metrics


def build_candidates(
    tickets: list[dict[str, Any]],
    controller: str,
    started_at: datetime,
    include_existing: bool,
    seen: set[str],
    policy: dict[str, Any],
    buy_paused: bool,
    buy_pause_reason: str,
    buy_notional_cap: float,
    pair_last_buy_approval_ts: dict[str, float],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    now_ts = time.time()
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue
        tid = str(ticket.get("ticket_id") or "").strip()
        if not tid or tid in seen:
            continue
        if not eligible_ticket(ticket, controller, started_at, include_existing):
            continue

        side = str(ticket.get("side") or "").strip().lower()
        ts = parse_utc(ticket.get("timestamp")) or datetime.max.replace(tzinfo=timezone.utc)

        if side == "buy":
            ok, reasons, metrics = evaluate_buy_ticket(
                ticket=ticket,
                policy=policy,
                now_ts=now_ts,
                pair_last_buy_approval_ts=pair_last_buy_approval_ts,
                buy_paused=buy_paused,
                buy_pause_reason=buy_pause_reason,
                buy_notional_cap=buy_notional_cap,
            )
            if not ok:
                skipped.append({"ticket_id": tid, "side": side, "reasons": reasons})
                continue
            priority = compute_buy_priority(ticket, metrics)
        elif side == "sell":
            metrics = {
                "pair": str(ticket.get("pair") or "").strip().upper(),
                "notional_usd": round(to_float(ticket.get("notional_usd"), 0.0), 4),
                "edge_score": None,
                "bucket_win_rate_pct": None,
                "bucket_n": None,
            }
            priority = compute_sell_priority(ticket)
        else:
            skipped.append({"ticket_id": tid, "side": side or "unknown", "reasons": ["unsupported side"]})
            continue

        candidates.append(
            {
                "ticket": ticket,
                "ticket_id": tid,
                "side": side,
                "timestamp_dt": ts,
                "priority": float(priority),
                "metrics": metrics,
            }
        )

    prioritize_sells = bool(policy.get("prioritize_sells", True))
    if prioritize_sells:
        candidates.sort(
            key=lambda row: (
                0 if row["side"] == "sell" else 1,
                -float(row["priority"]),
                row["timestamp_dt"],
            )
        )
    else:
        candidates.sort(key=lambda row: (-float(row["priority"]), row["timestamp_dt"]))

    return candidates, skipped


def seed_queue_candidates(
    gateway_url: str,
    controller: str,
    policy: dict[str, Any],
    pending_count: int,
    buy_paused: bool,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    pause_buy_seeding = buy_paused and bool(policy.get("disable_buy_seeding_when_paused", True))

    if bool(policy.get("auto_seed_sell_tickets", False)):
        result = request_json(
            f"{gateway_url}/api/sells/lock_in",
            method="POST",
            payload={"all": True, "force": False},
        )
        actions.append(
            {
                "action": "seed_sell_tickets",
                "status": result.get("status", "ok"),
                "created_count": to_int(result.get("created_count"), 0),
            }
        )

    if bool(policy.get("auto_seed_buy_tickets", False)):
        if pause_buy_seeding:
            actions.append(
                {
                    "action": "seed_buy_tickets",
                    "status": "skipped",
                    "created_count": 0,
                    "reason": "buy_paused",
                }
            )
        else:
            result = request_json(
                f"{gateway_url}/api/buys/autobuy/run",
                method="POST",
                payload={"force": bool(policy.get("auto_seed_buy_force", False))},
            )
            created = result.get("created") if isinstance(result, dict) else []
            created_count = len(created) if isinstance(created, list) else 0
            actions.append(
                {
                    "action": "seed_buy_tickets",
                    "status": result.get("status", "ok"),
                    "created_count": created_count,
                }
            )

    refill_threshold = max(0, to_int(policy.get("scan_refill_when_queue_below"), 0))
    if refill_threshold > 0 and pending_count < refill_threshold:
        if pause_buy_seeding and bool(policy.get("skip_scan_refill_when_buy_paused", True)):
            actions.append(
                {
                    "action": "scan_refill",
                    "status": "skipped",
                    "reason": "buy_paused",
                    "pending_count": pending_count,
                }
            )
        else:
            result = request_json(
                f"{gateway_url}/api/master/approval/scan-refill",
                method="POST",
                payload={
                    "use_cached": bool(policy.get("scan_refill_use_cached", True)),
                    "validate": bool(policy.get("scan_refill_validate", False)),
                    "controller": controller,
                },
            )
            actions.append(
                {
                    "action": "scan_refill",
                    "status": result.get("status", "ok"),
                    "pending_count": to_int(result.get("pending_count"), 0),
                }
            )

    return actions


def main() -> int:
    ap = argparse.ArgumentParser(description="Continuously auto-approve eligible pending tickets.")
    ap.add_argument("--gateway-url", default="http://127.0.0.1:8787")
    ap.add_argument("--controller", default="Robert")
    ap.add_argument("--interval-sec", type=int, default=8)
    ap.add_argument("--include-existing", action="store_true", help="Also process pending tickets that existed before daemon start.")
    ap.add_argument("--log-file", default=str(DEFAULT_LOG_FILE))
    ap.add_argument("--state-file", default=str(DEFAULT_STATE_FILE))
    ap.add_argument("--heartbeat-file", default=str(DEFAULT_HEARTBEAT_FILE))
    ap.add_argument("--policy-file", default=str(DEFAULT_POLICY_FILE))
    ap.add_argument("--runtime-file", default=str(DEFAULT_RUNTIME_FILE))
    ap.add_argument("--action-receipt-file", default=str(DEFAULT_ACTION_RECEIPT_FILE))
    ap.add_argument("--action-receipt-ttl-sec", type=int, default=DEFAULT_ACTION_RECEIPT_TTL_SEC)
    args = ap.parse_args()

    gateway_url = str(args.gateway_url).rstrip("/")
    controller = str(args.controller).strip()
    interval_sec = max(2, int(args.interval_sec))
    log_file = Path(args.log_file)
    state_file = Path(args.state_file)
    heartbeat_file = Path(args.heartbeat_file)
    policy_file = Path(args.policy_file)
    runtime_file = Path(args.runtime_file)
    action_receipt_file = Path(args.action_receipt_file)
    action_receipt_ttl_sec = max(1, int(args.action_receipt_ttl_sec))

    if not _acquire_lock(log_file):
        return 0
    atexit.register(_release_lock)

    started_at = datetime.now(timezone.utc)
    seen, pair_last_buy_approval_ts = load_state(state_file)

    append_jsonl(
        log_file,
        {
            "ts": now_utc(),
            "event": "daemon_start",
            "gateway_url": gateway_url,
            "controller": controller,
            "include_existing": bool(args.include_existing),
            "interval_sec": interval_sec,
            "seen_count": len(seen),
            "state_file": str(state_file),
            "heartbeat_file": str(heartbeat_file),
            "policy_file": str(policy_file),
            "runtime_file": str(runtime_file),
            "action_receipt_file": str(action_receipt_file),
            "action_receipt_ttl_sec": action_receipt_ttl_sec,
        },
    )

    print(
        "[APPROVAL-AUTOFIRE] started"
        + f" gateway={gateway_url}"
        + f" controller={controller}"
        + f" include_existing={bool(args.include_existing)}"
        + f" interval={interval_sec}s"
        + f" policy={policy_file}",
        flush=True,
    )

    final_statuses = {"executed", "rejected", "blocked", "error"}

    while True:
        cycle_start = time.time()
        policy = load_policy(policy_file)

        authority = autofire_authority_state(
            runtime_path=runtime_file,
            receipt_path=action_receipt_file,
            controller=controller,
            ttl_seconds=action_receipt_ttl_sec,
        )
        if not authority["authorized"]:
            append_jsonl(
                log_file,
                {
                    "ts": now_utc(),
                    "event": "action_time_authority_required",
                    "controller": controller,
                    "authority_reasons": authority["reasons"],
                },
            )
            write_json(
                heartbeat_file,
                {
                    "generated_utc": now_utc(),
                    "schema": "approval_autofire_heartbeat_v3",
                    "status": "disarmed",
                    "reason": "action_time_authority_required",
                    "controller": controller,
                    "interval_sec": interval_sec,
                    "policy_file": str(policy_file),
                    "runtime_file": str(runtime_file),
                    "action_receipt_file": str(action_receipt_file),
                    "authority": authority,
                    "queue_count": 0,
                    "pending_count": 0,
                    "eligible_count": 0,
                    "approved_count": 0,
                    "approved_sell_count": 0,
                    "approved_buy_count": 0,
                },
            )
            time.sleep(interval_sec)
            continue

        queue_payload = request_json(f"{gateway_url}/api/master/approval-queue")
        tickets = queue_payload.get("tickets") if isinstance(queue_payload, dict) else None
        if not isinstance(tickets, list):
            append_jsonl(
                log_file,
                {
                    "ts": now_utc(),
                    "event": "queue_read_error",
                    "payload": queue_payload,
                },
            )
            write_json(
                heartbeat_file,
                {
                    "generated_utc": now_utc(),
                    "schema": "approval_autofire_heartbeat_v3",
                    "status": "degraded",
                    "reason": "queue_read_error",
                    "gateway_url": gateway_url,
                    "controller": controller,
                    "interval_sec": interval_sec,
                    "policy_file": str(policy_file),
                },
            )
            time.sleep(interval_sec)
            continue

        perf_payload = request_json(f"{gateway_url}/api/perf/session")
        buy_paused, buy_pause_reason, buy_pause_floor, daily_net_usd, daily_scope = resolve_buy_pause(
            policy=policy,
            queue_payload=queue_payload,
            perf_payload=perf_payload,
        )

        balance_payload = request_json(f"{gateway_url}/api/kraken/balance")
        usd_equity = resolve_usd_equity(balance_payload)
        min_free_usd_to_buy = max(0.0, to_float(policy.get("min_free_usd_to_buy"), 0.0))
        if (
            min_free_usd_to_buy > 0
            and usd_equity is not None
            and usd_equity < min_free_usd_to_buy
        ):
            buy_paused = True
            buy_pause_reason = (
                f"free_usd ${usd_equity:.2f} below minimum ${min_free_usd_to_buy:.2f}"
            )

        buy_seeding_paused = buy_paused and bool(policy.get("disable_buy_seeding_when_paused", True))
        pending_count_pre_seed = sum(
            1
            for t in tickets
            if isinstance(t, dict)
            and str(t.get("approval_state") or "").upper() == "PENDING_HUMAN_APPROVAL"
        )
        seed_actions = seed_queue_candidates(
            gateway_url=gateway_url,
            controller=controller,
            policy=policy,
            pending_count=pending_count_pre_seed,
            buy_paused=buy_paused,
        )

        if seed_actions:
            queue_payload = request_json(f"{gateway_url}/api/master/approval-queue")
            refreshed_tickets = queue_payload.get("tickets") if isinstance(queue_payload, dict) else None
            if isinstance(refreshed_tickets, list):
                tickets = refreshed_tickets

        stale_buy_expiry = expire_stale_pending_buys(
            tickets=tickets,
            gateway_url=gateway_url,
            controller=controller,
            max_pending_buy_age_hours=max(0.0, to_float(policy.get("buy_pending_ttl_hours"), 0.0)),
            log_file=log_file,
        )
        if to_int(stale_buy_expiry.get("attempted"), 0) > 0:
            queue_payload = request_json(f"{gateway_url}/api/master/approval-queue")
            refreshed_tickets = queue_payload.get("tickets") if isinstance(queue_payload, dict) else None
            if isinstance(refreshed_tickets, list):
                tickets = refreshed_tickets

        buy_notional_cap = resolve_buy_notional_cap(policy=policy, queue_payload=queue_payload)
        if usd_equity is not None:
            available_cap = max(0.0, usd_equity * 0.90)
            buy_notional_cap = (
                min(buy_notional_cap, available_cap)
                if buy_notional_cap > 0
                else available_cap
            )

        candidates, skipped_by_policy = build_candidates(
            tickets=tickets,
            controller=controller,
            started_at=started_at,
            include_existing=bool(args.include_existing),
            seen=seen,
            policy=policy,
            buy_paused=buy_paused,
            buy_pause_reason=buy_pause_reason,
            buy_notional_cap=buy_notional_cap,
            pair_last_buy_approval_ts=pair_last_buy_approval_ts,
        )

        max_approvals = max(0, to_int(policy.get("max_approvals_per_cycle"), 3))
        max_buy_approvals = max(0, to_int(policy.get("max_buy_approvals_per_cycle"), 1))
        if buy_paused and bool(policy.get("force_zero_buy_budget_when_paused", True)):
            max_buy_approvals = 0

        approved_total = 0
        approved_sell = 0
        approved_buy = 0
        rate_limited: list[dict[str, Any]] = []
        state_changed = False

        for row in candidates:
            if approved_total >= max_approvals:
                rate_limited.append(
                    {
                        "ticket_id": row["ticket_id"],
                        "side": row["side"],
                        "reason": "cycle_budget_exhausted",
                    }
                )
                continue

            if row["side"] == "buy" and approved_buy >= max_buy_approvals:
                rate_limited.append(
                    {
                        "ticket_id": row["ticket_id"],
                        "side": "buy",
                        "reason": "buy_budget_exhausted",
                    }
                )
                continue

            ticket = row["ticket"]
            tid = row["ticket_id"]
            decision_authority = autofire_authority_state(
                runtime_path=runtime_file,
                receipt_path=action_receipt_file,
                controller=controller,
                ttl_seconds=action_receipt_ttl_sec,
            )
            if not decision_authority["authorized"]:
                authority = decision_authority
                rate_limited.append(
                    {
                        "ticket_id": tid,
                        "side": row["side"],
                        "reason": "action_time_authority_lost_before_decision",
                    }
                )
                append_jsonl(
                    log_file,
                    {
                        "ts": now_utc(),
                        "event": "action_time_authority_lost_before_decision",
                        "controller": controller,
                        "ticket_id": tid,
                        "authority_reasons": decision_authority["reasons"],
                    },
                )
                break
            reason = f"approval_autofire_policy/{row['side']}"
            payload = build_decide_payload(tid, controller, reason=reason)
            result = request_json(
                f"{gateway_url}/api/master/approval/decide",
                method="POST",
                payload=payload,
            )
            status = str(result.get("status", "unknown")) if isinstance(result, dict) else "unknown"
            txid = result.get("txid") if isinstance(result, dict) else None

            append_jsonl(
                log_file,
                {
                    "ts": now_utc(),
                    "event": "approve_attempt",
                    "ticket_id": tid,
                    "pair": ticket.get("pair"),
                    "side": row["side"],
                    "notional_usd": ticket.get("notional_usd"),
                    "priority": round(float(row["priority"]), 5),
                    "metrics": row.get("metrics") or {},
                    "status": status,
                    "txid": txid,
                    "result": result,
                },
            )

            if status in final_statuses:
                seen.add(tid)
                state_changed = True

            if status == "executed":
                approved_total += 1
                if row["side"] == "sell":
                    approved_sell += 1
                elif row["side"] == "buy":
                    approved_buy += 1
                    pair = str(ticket.get("pair") or "").strip().upper()
                    if pair:
                        pair_last_buy_approval_ts[pair] = time.time()
                        state_changed = True

            print(
                "[APPROVAL-AUTOFIRE]"
                + f" ticket={tid}"
                + f" pair={ticket.get('pair')}"
                + f" side={row['side']}"
                + f" status={status}",
                flush=True,
            )

        if state_changed:
            save_state(state_file, seen, pair_last_buy_approval_ts)

        pending_count = sum(
            1
            for t in tickets
            if isinstance(t, dict)
            and str(t.get("approval_state") or "").upper() == "PENDING_HUMAN_APPROVAL"
        )
        cycle_duration_sec = max(0.0, time.time() - cycle_start)
        skipped_reason_hist = reason_histogram(skipped_by_policy)
        rate_limited_reason_hist = reason_histogram(rate_limited)

        heartbeat = {
            "generated_utc": now_utc(),
            "schema": "approval_autofire_heartbeat_v3",
            "status": "running",
            "gateway_url": gateway_url,
            "controller": controller,
            "interval_sec": interval_sec,
            "policy_file": str(policy_file),
            "runtime_file": str(runtime_file),
            "action_receipt_file": str(action_receipt_file),
            "authority": authority,
            "state_file": str(state_file),
            "queue_count": len(tickets),
            "pending_count": pending_count,
            "eligible_count": len(candidates),
            "skipped_by_policy_count": len(skipped_by_policy),
            "rate_limited_count": len(rate_limited),
            "approved_count": approved_total,
            "approved_sell_count": approved_sell,
            "approved_buy_count": approved_buy,
            "buy_paused": buy_paused,
            "buy_pause_reason": buy_pause_reason,
            "buy_pause_floor_usd": buy_pause_floor,
            "daily_realized_net_usd": daily_net_usd,
            "daily_scope": daily_scope,
            "buy_seeding_paused": buy_seeding_paused,
            "buy_notional_cap_usd": buy_notional_cap,
            "usd_equity": usd_equity,
            "min_free_usd_to_buy": min_free_usd_to_buy,
            "buy_pending_ttl_hours": max(0.0, to_float(policy.get("buy_pending_ttl_hours"), 0.0)),
            "stale_buy_expiry": stale_buy_expiry,
            "seed_actions": seed_actions,
            "skipped_reason_histogram": skipped_reason_hist[:40],
            "rate_limited_reason_histogram": rate_limited_reason_hist[:20],
            "cycle_duration_sec": round(cycle_duration_sec, 4),
            "seen_count": len(seen),
            "policy": policy,
        }
        write_json(heartbeat_file, heartbeat)

        time.sleep(interval_sec)


if __name__ == "__main__":
    raise SystemExit(main())
