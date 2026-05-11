import argparse
import csv
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONFIG_DIR = ROOT / "config"
OUT_DIR = ROOT / "out" / "execution"

RUNTIME_FILE = CONFIG_DIR / "runtime_control.json"
SUPER_SNIPER_FILE = CONFIG_DIR / "super_sniper.json"
UNIVERSE_FILE = ROOT / "out" / "live_universe_catalog.csv"
TRADE_LOG_FILE = OUT_DIR / "trade_log.json"
HEALTH_FILE = OUT_DIR / "health_metrics.json"

NOISE_DELTA_KEYS = {
    "super_sniper_active",
    "super_sniper_last_run_utc",
    "super_sniper_sharp",
    "super_sniper_guard_reasons",
    "selected_symbol_hint",
}

# Canonical universe import
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from canonical_extended_universe import CANONICAL_UNIVERSE
except ImportError:
    # Backward-compatible fallback for older packaging layouts.
    from out.canonical_extended_universe import CANONICAL_UNIVERSE


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


def canonical_hash(payload: Any) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_universe(path: Path) -> List[Dict[str, str]]:
    # Use canonical universe for all logic
    return [{"symbol": s, "asset_class": "unknown"} for s in CANONICAL_UNIVERSE]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def lineage_stats(trades: List[Dict[str, Any]], lookback: int) -> Dict[str, Dict[str, float]]:
    sliced = trades[-max(lookback, 1):]
    by_symbol: Dict[str, List[float]] = defaultdict(list)

    for t in sliced:
        symbol = str(t.get("symbol", "")).upper().strip()
        if not symbol:
            continue
        pnl_pct = _safe_float(t.get("pnl_pct"), None)
        if pnl_pct is None:
            entry = _safe_float(t.get("entry_price"), 0.0)
            exit_px = _safe_float(t.get("exit_price"), entry)
            if entry > 0:
                pnl_pct = ((exit_px - entry) / entry) * 100.0
            else:
                continue
        by_symbol[symbol].append(pnl_pct)

    out: Dict[str, Dict[str, float]] = {}
    for symbol, vals in by_symbol.items():
        if not vals:
            continue
        wins = sum(1 for x in vals if x > 0)
        win_rate = wins / len(vals)
        avg = sum(vals) / len(vals)
        variance = 0.0
        if len(vals) > 1:
            mean = avg
            variance = sum((x - mean) ** 2 for x in vals) / (len(vals) - 1)
        std = math.sqrt(max(variance, 0.0))
        sharp_local = (avg / std) if std > 1e-9 else 0.0
        out[symbol] = {
            "trades": float(len(vals)),
            "win_rate": float(win_rate),
            "avg_pnl_pct": float(avg),
            "std_pnl_pct": float(std),
            "lineage_sharp": float(sharp_local),
        }
    return out


def global_sharp(trades: List[Dict[str, Any]], health: Dict[str, Any]) -> float:
    health_sharp = _safe_float(health.get("rolling_sharpe"), 0.0)
    vals: List[float] = []
    for t in trades[-120:]:
        val = t.get("pnl_pct")
        if val is not None:
            vals.append(_safe_float(val, 0.0))
    if len(vals) < 8:
        return health_sharp
    mean = sum(vals) / len(vals)
    var = sum((x - mean) ** 2 for x in vals) / max(len(vals) - 1, 1)
    std = math.sqrt(max(var, 0.0))
    log_sharp = (mean / std) if std > 1e-9 else 0.0
    return round((0.65 * health_sharp) + (0.35 * log_sharp), 4)


def score_candidates(
    universe: List[Dict[str, str]],
    lineage: Dict[str, Dict[str, float]],
    min_trades: int,
    min_win_rate: float,
    min_avg_pnl: float,
) -> List[Dict[str, Any]]:
    scored: List[Dict[str, Any]] = []

    for row in universe:
        symbol = row["symbol"]
        asset_class = row["asset_class"]
        lg = lineage.get(symbol, None)

        if lg is None:
            score = 35.0
            reasons = ["no_lineage_history"]
            stats = {"trades": 0.0, "win_rate": 0.0, "avg_pnl_pct": 0.0, "lineage_sharp": 0.0}
        else:
            trades = lg["trades"]
            win_rate = lg["win_rate"]
            avg_pnl = lg["avg_pnl_pct"]
            lsharp = lg["lineage_sharp"]

            score = 30.0
            score += min(trades, 25.0) * 1.2
            score += win_rate * 35.0
            score += min(max(avg_pnl, -3.0), 3.0) * 6.0
            score += min(max(lsharp, -2.0), 3.0) * 4.0

            reasons = []
            if trades >= min_trades:
                reasons.append("sufficient_lineage")
            if win_rate >= min_win_rate:
                reasons.append("winning_lineage")
            if avg_pnl >= min_avg_pnl:
                reasons.append("positive_edge")

            stats = {
                "trades": trades,
                "win_rate": round(win_rate, 4),
                "avg_pnl_pct": round(avg_pnl, 4),
                "lineage_sharp": round(lsharp, 4),
            }

        if asset_class == "crypto":
            score += 3.5

        scored.append(
            {
                "symbol": symbol,
                "asset_class": asset_class,
                "score": round(score, 3),
                "reasons": reasons,
                "lineage": stats,
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def _live_guard_passes(cfg: Dict[str, Any]) -> Tuple[bool, List[str]]:
    arm = cfg.get("live_arming", {}) or {}
    reasons: List[str] = []

    if not bool(arm.get("allow_live_switch", False)):
        reasons.append("live_switch_disabled_in_super_sniper")
        return False, reasons

    if bool(arm.get("require_env_arm", True)):
        env_var = str(arm.get("env_var", "LUMENCORE_ARM_LIVE"))
        env_val = str(arm.get("env_value", "YES_I_ACCEPT_REAL_CAPITAL_RISK"))
        if os.environ.get(env_var, "") != env_val:
            reasons.append(f"env_guard_failed:{env_var}")

    if bool(arm.get("require_manual_confirm_file", True)):
        confirm_rel = str(arm.get("confirm_file", "config/live_arm.confirm"))
        confirm_path = ROOT / confirm_rel
        phrase = str(arm.get("confirm_phrase", "ARM_LIVE_SUPER_SNIPER"))
        if not confirm_path.exists():
            reasons.append("confirm_file_missing")
        else:
            txt = confirm_path.read_text(encoding="utf-8", errors="ignore")
            if phrase not in txt:
                reasons.append("confirm_phrase_missing")

    return len(reasons) == 0, reasons


def apply_super_sniper(
    runtime_cfg: Dict[str, Any],
    sniper_cfg: Dict[str, Any],
    top_candidates: List[Dict[str, Any]],
    sharp_value: float,
    dry_run: bool,
) -> Dict[str, Any]:
    out = dict(runtime_cfg)

    capital = sniper_cfg.get("capital", {}) or {}
    risk = sniper_cfg.get("risk_overrides", {}) or {}
    cadence = sniper_cfg.get("cadence", {}) or {}
    pyramiding = sniper_cfg.get("pyramiding", {}) or {}
    hunter = sniper_cfg.get("candidate_hunter", {}) or {}

    current_bp = _safe_float(out.get("fallback_buying_power_usd"), 0.0)
    floor = max(_safe_float(capital.get("fallback_buying_power_floor_usd"), 0.0), 0.0)

    # Prevent compounding growth on repeated apply cycles.
    out["fallback_buying_power_usd"] = round(max(current_bp, floor), 2)
    out["reserve_usd"] = round(max(_safe_float(capital.get("reserve_floor_usd"), 1.0), 0.0), 2)

    for k, v in cadence.items():
        out[k] = v
    for k, v in pyramiding.items():
        if k != "enabled":
            out[k] = v
    for k, v in risk.items():
        out[k] = v

    # Keep runtime in universe mode so scanner is not locked to a tiny symbol set.
    if top_candidates:
        out["selected_symbol_hint"] = top_candidates[0]["symbol"]
    out["symbol"] = "UNIVERSE"

    sharp_trigger = _safe_float(hunter.get("sharp_trigger"), 2.0)
    allow_live = False
    live_guard_reasons: List[str] = []

    if sharp_value >= sharp_trigger and not dry_run:
        allow_live, live_guard_reasons = _live_guard_passes(sniper_cfg)

    if allow_live:
        out["mode"] = "live"
        out["allow_live_orders"] = True
    else:
        out["mode"] = "paper"
        out["allow_live_orders"] = False

    out["super_sniper_active"] = True
    out["super_sniper_last_run_utc"] = now_utc()
    out["super_sniper_sharp"] = round(sharp_value, 4)
    out["super_sniper_guard_reasons"] = live_guard_reasons

    return out


def dict_delta(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    keys = sorted(set(before.keys()) | set(after.keys()))
    delta: Dict[str, Dict[str, Any]] = {}
    for key in keys:
        b = before.get(key)
        a = after.get(key)
        if b != a:
            delta[key] = {"before": b, "after": a}
    return delta


def run(dry_run: bool) -> int:
    runtime_cfg = read_json(RUNTIME_FILE, {})
    sniper_cfg = read_json(SUPER_SNIPER_FILE, {})
    trade_log = read_json(TRADE_LOG_FILE, [])
    health = read_json(HEALTH_FILE, {})
    universe = load_universe(UNIVERSE_FILE)

    if not runtime_cfg:
        print("[ERROR] Missing runtime control config.")
        return 1
    if not sniper_cfg:
        print("[ERROR] Missing super sniper config.")
        return 1

    hunter = sniper_cfg.get("candidate_hunter", {}) or {}
    lookback = int(hunter.get("lineage_lookback_trades", 200) or 200)
    min_trades = int(hunter.get("min_lineage_trades", 5) or 5)
    min_win_rate = _safe_float(hunter.get("min_lineage_win_rate"), 0.55)
    min_avg = _safe_float(hunter.get("min_lineage_avg_pnl_pct"), 0.10)
    min_score = _safe_float(hunter.get("min_candidate_score"), 70.0)
    burst_top_n = max(int(hunter.get("burst_top_n", 3) or 3), 1)
    scan_limit = max(int(hunter.get("scan_limit", 12) or 12), 1)

    lineage = lineage_stats(trade_log, lookback=lookback)
    sharp_value = global_sharp(trade_log, health)

    candidates = score_candidates(
        universe=universe,
        lineage=lineage,
        min_trades=min_trades,
        min_win_rate=min_win_rate,
        min_avg_pnl=min_avg,
    )

    filtered = [c for c in candidates if c["score"] >= min_score]
    top_candidates = (filtered or candidates)[:scan_limit]
    burst = top_candidates[:burst_top_n]

    patched_cfg = apply_super_sniper(
        runtime_cfg=runtime_cfg,
        sniper_cfg=sniper_cfg,
        top_candidates=burst,
        sharp_value=sharp_value,
        dry_run=dry_run,
    )

    delta = dict_delta(runtime_cfg, patched_cfg)
    material_delta = {k: v for k, v in delta.items() if k not in NOISE_DELTA_KEYS}

    audit_cfg = sniper_cfg.get("audit", {}) or {}
    delta_file = ROOT / str(audit_cfg.get("out_file", "out/execution/frozen_deltas_super_sniper.json"))
    decision_file = ROOT / str(audit_cfg.get("decision_file", "out/execution/super_sniper_decision.json"))

    decision = {
        "timestamp_utc": now_utc(),
        "dry_run": dry_run,
        "sharp_value": sharp_value,
        "sharp_trigger": _safe_float(hunter.get("sharp_trigger"), 2.0),
        "universe_size": len(universe),
        "trade_log_size": len(trade_log),
        "lineage_symbols": len(lineage),
        "top_candidates": top_candidates[:5],
        "burst_candidates": burst,
        "selected_symbol": patched_cfg.get("symbol", "UNIVERSE"),
        "mode_after": patched_cfg.get("mode", "paper"),
        "live_after": bool(patched_cfg.get("allow_live_orders", False)),
        "delta_keys": sorted(list(delta.keys())),
        "delta_count": len(delta),
        "material_delta_keys": sorted(list(material_delta.keys())),
        "material_delta_count": len(material_delta),
    }

    checksum_block = {
        "runtime_before_sha256": canonical_hash(runtime_cfg),
        "runtime_after_sha256": canonical_hash(patched_cfg),
        "delta_sha256": canonical_hash(delta),
    }

    frozen_delta = {
        "timestamp_utc": now_utc(),
        "decision": decision,
        "checksums": checksum_block,
        "delta": delta,
    }

    atomic_write_json(decision_file, decision, indent=2)
    atomic_write_json(delta_file, frozen_delta, indent=2)

    if not dry_run and material_delta:
        backup = RUNTIME_FILE.with_name(f"runtime_control.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        atomic_write_json(backup, runtime_cfg, indent=2)
        atomic_write_json(RUNTIME_FILE, patched_cfg, indent=2)
    elif not dry_run:
        print("  [SUPER-SNIPER] no material runtime change; skipped runtime write")

    print("[SUPER-SNIPER] run complete")
    print(f"  dry_run: {dry_run}")
    print(f"  sharp: {sharp_value:.4f}")
    print(f"  selected_symbol: {patched_cfg.get('symbol', 'UNIVERSE')}")
    print(f"  mode_after: {patched_cfg.get('mode')} | live: {patched_cfg.get('allow_live_orders')}")
    print(f"  delta_count: {len(delta)}")
    print(f"  material_delta_count: {len(material_delta)}")
    print(f"  decision_file: {decision_file}")
    print(f"  frozen_delta_file: {delta_file}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LUMENCORE Super Sniper / Beast Mode runtime tuner")
    parser.add_argument("--apply", action="store_true", help="Apply changes to runtime_control.json")
    args = parser.parse_args()

    dry_run = not args.apply
    return run(dry_run=dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
