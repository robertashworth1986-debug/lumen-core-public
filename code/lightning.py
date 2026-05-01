import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONFIG = ROOT / "config"
OUT = ROOT / "out" / "execution"

RUNTIME_FILE = CONFIG / "runtime_control.json"
HEALTH_FILE = OUT / "health_metrics.json"
SNIPER_DECISION_FILE = OUT / "super_sniper_decision.json"
GUARDRAILS_FILE = CONFIG / "lightning_guardrails.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def atomic_write_json(path: Path, payload: Any, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=indent)
    os.replace(tmp, path)


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _i(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _live_guard_passes(cfg: Dict[str, Any]) -> Tuple[bool, List[str]]:
    live = cfg.get("live_arming", {}) or {}
    reasons: List[str] = []

    if not bool(live.get("allow_live_switch", False)):
        reasons.append("lightning_live_switch_disabled")
        return False, reasons

    if bool(live.get("require_env_arm", True)):
        env_var = str(live.get("env_var", "LUMENCORE_ARM_LIGHTNING"))
        env_val = str(live.get("env_value", "YES_ARM_LIGHTNING_LIVE"))
        if os.environ.get(env_var, "") != env_val:
            reasons.append(f"env_guard_failed:{env_var}")

    if bool(live.get("require_manual_confirm_file", True)):
        rel = str(live.get("confirm_file", "config/lightning_live_arm.confirm"))
        phrase = str(live.get("confirm_phrase", "ARM_LIGHTNING_LIVE"))
        p = ROOT / rel
        if not p.exists():
            reasons.append("lightning_confirm_file_missing")
        else:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            if phrase not in txt:
                reasons.append("lightning_confirm_phrase_missing")

    return len(reasons) == 0, reasons


def detect_constraints(runtime: Dict[str, Any], health: Dict[str, Any], guardrails: Dict[str, Any]) -> List[Dict[str, Any]]:
    upgrades = guardrails.get("upgrades", {}) or {}
    hits: List[Dict[str, Any]] = []

    def add(tag: str, severity: str, where: str, why: str, fix: str):
        hits.append(
            {
                "timestamp_utc": now_utc(),
                "tag": tag,
                "severity": severity,
                "where": where,
                "why": why,
                "fix": fix,
            }
        )

    u1 = upgrades.get("u01_volatility_circuit_breaker", {})
    if u1.get("enabled", False):
        proxy_vol = abs(_f(health.get("portfolio_pnl_pct", 0.0), 0.0))
        if proxy_vol > _f(u1.get("max_intraloop_volatility_pct", 4.0), 4.0):
            add("volatility_spike", "high", "portfolio_pnl_pct", f"proxy volatility {proxy_vol:.2f}% exceeds threshold", "Increase reserve, reduce risk fraction, slow cadence")

    u2 = upgrades.get("u02_latency_drift_guard", {})
    if u2.get("enabled", False):
        p95 = _f(health.get("latency_p95_ms", 0.0), 0.0)
        p99 = _f(health.get("latency_p99_ms", 0.0), 0.0)
        if p99 > _f(u2.get("critical_p99_ms", 900), 900):
            add("latency_drift", "critical", "latency_p99_ms", f"p99={p99:.1f}ms exceeded critical", "Switch to paper, raise cooldowns, reduce parallel attempts")
        elif p95 > _f(u2.get("warn_p95_ms", 350), 350):
            add("latency_drift", "warn", "latency_p95_ms", f"p95={p95:.1f}ms exceeded warning", "Throttle loop and limit scan size")

    u3 = upgrades.get("u03_stability_guard", {})
    if u3.get("enabled", False):
        err = _f(health.get("error_rate_pct", 0.0), 0.0)
        succ = _f(health.get("order_success_rate_pct", 100.0), 100.0)
        if err > _f(u3.get("max_error_rate_pct", 4.5), 4.5):
            add("stability", "high", "error_rate_pct", f"error rate {err:.2f}% too high", "Enter paper mode and investigate failing subsystem")
        if succ < _f(u3.get("min_order_success_rate_pct", 88.0), 88.0):
            add("stability", "high", "order_success_rate_pct", f"success rate {succ:.2f}% too low", "Cut order attempts and tighten execution filters")

    u6 = upgrades.get("u06_data_freshness_guard", {})
    if u6.get("enabled", False):
        ts = str(health.get("timestamp_utc", ""))
        if ts:
            try:
                health_ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - health_ts).total_seconds()
            except Exception:
                age = 10_000
        else:
            age = 10_000
        if age > _i(u6.get("max_health_staleness_sec", 90), 90):
            add("data_stale", "high", "health_metrics.timestamp_utc", f"health data stale by {age:.1f}s", "Freeze deltas and hold execution until fresh data")

    u7 = upgrades.get("u07_capital_preservation_floor", {})
    if u7.get("enabled", False):
        reserve = _f(runtime.get("reserve_usd", 0.0), 0.0)
        min_reserve = _f(u7.get("min_reserve_usd", 5.0), 5.0)
        if reserve < min_reserve:
            add("capital_floor", "warn", "runtime.reserve_usd", f"reserve {reserve:.2f} below floor {min_reserve:.2f}", "Raise reserve and cap max position")

    return hits


def apply_upgrades(runtime: Dict[str, Any], health: Dict[str, Any], guardrails: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
    out = dict(runtime)
    upgrades = guardrails.get("upgrades", {}) or {}

    constraints = detect_constraints(runtime, health, guardrails)
    high_or_critical = any(x["severity"] in ("high", "critical") for x in constraints)

    u8 = upgrades.get("u08_adaptive_cadence_controller", {})
    if u8.get("enabled", False):
        if high_or_critical:
            out["loop_seconds"] = _f(u8.get("slow_loop_seconds", 1.20), 1.20)
        else:
            p95 = _f(health.get("latency_p95_ms", 0.0), 0.0)
            if p95 > 250:
                out["loop_seconds"] = _f(u8.get("normal_loop_seconds", 0.50), 0.50)
            else:
                out["loop_seconds"] = _f(u8.get("fast_loop_seconds", 0.25), 0.25)

    u7 = upgrades.get("u07_capital_preservation_floor", {})
    if u7.get("enabled", False):
        out["reserve_usd"] = max(_f(out.get("reserve_usd", 0.0), 0.0), _f(u7.get("min_reserve_usd", 5.0), 5.0))
        out["max_daily_loss_usd"] = max(_f(out.get("max_daily_loss_usd", 0.0), 0.0), _f(u7.get("max_daily_loss_usd_floor", 25.0), 25.0))

    u2 = upgrades.get("u02_latency_drift_guard", {})
    p99 = _f(health.get("latency_p99_ms", 0.0), 0.0)
    if u2.get("enabled", False) and p99 > _f(u2.get("critical_p99_ms", 900), 900):
        out["parallel_order_attempts"] = 1
        out["min_order_cooldown_sec"] = max(_i(out.get("min_order_cooldown_sec", 20), 20), 60)

    u3 = upgrades.get("u03_stability_guard", {})
    err = _f(health.get("error_rate_pct", 0.0), 0.0)
    succ = _f(health.get("order_success_rate_pct", 100.0), 100.0)
    if u3.get("enabled", False) and (err > _f(u3.get("max_error_rate_pct", 4.5), 4.5) or succ < _f(u3.get("min_order_success_rate_pct", 88.0), 88.0)):
        out["mode"] = "paper"
        out["allow_live_orders"] = False

    if high_or_critical:
        out["base_risk_fraction"] = min(_f(out.get("base_risk_fraction", 0.2), 0.2), 0.35)
        out["max_position_usd"] = min(_f(out.get("max_position_usd", 50.0), 50.0), 75.0)

    # live arming guard (still explicit)
    allow_live, reasons = _live_guard_passes(guardrails)
    if not dry_run and allow_live and not high_or_critical:
        out["mode"] = "live"
        out["allow_live_orders"] = True
    else:
        out["mode"] = "paper"
        out["allow_live_orders"] = False

    out["lightning_active"] = True
    out["lightning_last_run_utc"] = now_utc()
    out["lightning_constraint_count"] = len(constraints)
    out["lightning_live_guard_reasons"] = reasons

    return out


def dict_delta(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    keys = sorted(set(before.keys()) | set(after.keys()))
    delta: Dict[str, Dict[str, Any]] = {}
    for k in keys:
        if before.get(k) != after.get(k):
            delta[k] = {"before": before.get(k), "after": after.get(k)}
    return delta


def run(dry_run: bool) -> int:
    runtime = read_json(RUNTIME_FILE, {})
    health = read_json(HEALTH_FILE, {})
    decision = read_json(SNIPER_DECISION_FILE, {})
    guardrails = read_json(GUARDRAILS_FILE, {})

    if not runtime or not guardrails:
        print("[LIGHTNING] missing required config")
        return 1

    constraints = detect_constraints(runtime, health, guardrails)
    patched = apply_upgrades(runtime, health, guardrails, dry_run=dry_run)
    delta = dict_delta(runtime, patched)

    frozen = {
        "timestamp_utc": now_utc(),
        "dry_run": dry_run,
        "selected_symbol": decision.get("selected_symbol", runtime.get("symbol", "UNIVERSE")),
        "constraints": constraints,
        "constraint_count": len(constraints),
        "delta_count": len(delta),
        "delta": delta,
        "mode_after": patched.get("mode"),
        "live_after": bool(patched.get("allow_live_orders", False)),
    }

    atomic_write_json(OUT / "lightning_frozen_delta.json", frozen, indent=2)

    remediation_out = guardrails.get("upgrades", {}).get("u10_auto_remediation_playbook", {}).get("out_file", "out/execution/lightning_remediation.json")
    remediation_path = ROOT / remediation_out
    remediation = {
        "timestamp_utc": now_utc(),
        "when": now_utc(),
        "where": [c.get("where") for c in constraints],
        "why": [c.get("why") for c in constraints],
        "what": [c.get("tag") for c in constraints],
        "how_bad": [c.get("severity") for c in constraints],
        "fix": [c.get("fix") for c in constraints],
        "next_actions": [
            "Review latency and stability metrics",
            "Keep mode in paper until constraints clear",
            "Reduce aggressiveness if high/critical persists",
            "Re-run lightning and beast_mode after remediation"
        ]
    }
    atomic_write_json(remediation_path, remediation, indent=2)

    if not dry_run:
        backup = RUNTIME_FILE.with_name(f"runtime_control.lightning_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        atomic_write_json(backup, runtime, indent=2)
        atomic_write_json(RUNTIME_FILE, patched, indent=2)

    print("[LIGHTNING] run complete")
    print(f"  dry_run: {dry_run}")
    print(f"  constraints: {len(constraints)}")
    print(f"  delta_count: {len(delta)}")
    print(f"  mode_after: {patched.get('mode')} | live: {patched.get('allow_live_orders')}")
    print(f"  frozen_delta: {OUT / 'lightning_frozen_delta.json'}")
    print(f"  remediation: {remediation_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LUMENCORE Lightning supervisor")
    parser.add_argument("--apply", action="store_true", help="Apply lightning patch to runtime config")
    args = parser.parse_args()
    return run(dry_run=not args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
