from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT_OPS = ROOT / "out" / "ops"
OUT_EXEC = ROOT / "out" / "execution"
CONFIG = ROOT / "config"

RUNTIME_FILE = CONFIG / "runtime_control.json"
LATEST_ROSTER_FILE = OUT_EXEC / "clean_ops_roster_latest.json"

SYMBOL_ALIAS = {
    "XBT": "BTC",
    "XDG": "DOGE",
    "XXRP": "XRP",
    "XETH": "ETH",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(value, hi))


def latest_symbol_metrics_csv() -> Path | None:
    candidates = sorted(
        OUT_OPS.glob("symbol_spike_study_*/symbol_metrics.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def load_symbol_metrics(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = SYMBOL_ALIAS.get(str(row.get("symbol", "")).upper().strip(), str(row.get("symbol", "")).upper().strip())
            quote = str(row.get("quote", "")).upper().strip()
            if not symbol or not quote:
                continue
            out.append(
                {
                    "symbol": symbol,
                    "quote": quote,
                    "pair": f"{symbol}{quote}",
                    "bars": int(safe_float(row.get("bars", 0.0), 0.0)),
                    "quick_gain_score": safe_float(row.get("quick_gain_score", 0.0), 0.0),
                    "spike_power_score": safe_float(row.get("spike_power_score", 0.0), 0.0),
                    "trap_rate_pct": safe_float(row.get("trap_rate_pct", 0.0), 0.0),
                    "best_buy_hour_utc": int(safe_float(row.get("best_buy_hour_utc", 0.0), 0.0)),
                    "best_buy_median_net_pct": safe_float(row.get("best_buy_median_net_pct", 0.0), 0.0),
                    "best_buy_win_rate_pct": safe_float(row.get("best_buy_win_rate_pct", 0.0), 0.0),
                    "style": str(row.get("style", "")).upper().strip(),
                    "source_file": str(row.get("source_file", "")),
                }
            )
    return out


def score_row(row: dict[str, Any]) -> float:
    quick = safe_float(row.get("quick_gain_score", 0.0), 0.0)
    spike = safe_float(row.get("spike_power_score", 0.0), 0.0)
    win_rate = safe_float(row.get("best_buy_win_rate_pct", 0.0), 0.0) / 100.0
    trap = safe_float(row.get("trap_rate_pct", 100.0), 100.0)

    quality = (0.52 * quick) + (0.30 * spike) + (0.18 * win_rate)
    trap_factor = clamp((55.0 - trap) / 20.0, 0.20, 1.0)
    quote_bonus = 0.08 if str(row.get("quote", "")) == "USD" else (0.04 if str(row.get("quote", "")) == "USDT" else 0.0)
    return float(max(quality * trap_factor + quote_bonus, 0.0))


def unique_by_pair(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        pair = str(row.get("pair", "")).upper().strip()
        if not pair or pair in seen:
            continue
        seen.add(pair)
        out.append(row)
    return out


def build_roster() -> dict[str, Any]:
    runtime = load_json(RUNTIME_FILE, {})
    metrics_path = latest_symbol_metrics_csv()
    if metrics_path is None:
        return {
            "status": "error",
            "reason": "missing_symbol_metrics",
            "generated_utc": now_utc(),
        }

    target_clean_ops = int(max(safe_float(runtime.get("target_clean_ops", 5), 5.0), 1.0))
    quote_allow = runtime.get("clean_ops_quote_allow", ["USD", "USDT", "EUR"])
    quote_allow_set = {str(q).upper().strip() for q in quote_allow if str(q).strip()}
    whitelist = runtime.get("symbol_whitelist", [])
    whitelist_set = {SYMBOL_ALIAS.get(str(s).upper().strip(), str(s).upper().strip()) for s in whitelist if str(s).strip()}

    rows = load_symbol_metrics(metrics_path)

    profiles = [
        {
            "name": "strict",
            "min_quick": 1.00,
            "max_trap": 40.0,
            "min_bars": 220,
            "min_win_rate": 80.0,
            "allowed_styles": {"BASKET_SCALP"},
        },
        {
            "name": "balanced",
            "min_quick": 0.75,
            "max_trap": 44.0,
            "min_bars": 180,
            "min_win_rate": 74.0,
            "allowed_styles": {"BASKET_SCALP", "POWER_SPIKE"},
        },
        {
            "name": "relaxed",
            "min_quick": 0.55,
            "max_trap": 48.0,
            "min_bars": 140,
            "min_win_rate": 68.0,
            "allowed_styles": {"BASKET_SCALP", "POWER_SPIKE"},
        },
    ]

    selected: list[dict[str, Any]] = []
    profile_used = "strict"

    for profile in profiles:
        candidates: list[dict[str, Any]] = []
        for row in rows:
            symbol = str(row.get("symbol", "")).upper().strip()
            quote = str(row.get("quote", "")).upper().strip()
            if quote_allow_set and quote not in quote_allow_set:
                continue
            if whitelist_set and symbol not in whitelist_set:
                continue
            if int(row.get("bars", 0)) < int(profile["min_bars"]):
                continue
            if safe_float(row.get("quick_gain_score", 0.0), 0.0) < safe_float(profile["min_quick"], 0.0):
                continue
            if safe_float(row.get("trap_rate_pct", 100.0), 100.0) > safe_float(profile["max_trap"], 100.0):
                continue
            if safe_float(row.get("best_buy_win_rate_pct", 0.0), 0.0) < safe_float(profile["min_win_rate"], 0.0):
                continue
            if str(row.get("style", "")).upper().strip() not in profile["allowed_styles"]:
                continue

            scored = dict(row)
            scored["clean_score"] = round(score_row(row), 6)
            candidates.append(scored)

        candidates.sort(key=lambda r: safe_float(r.get("clean_score", 0.0), 0.0), reverse=True)
        candidates = unique_by_pair(candidates)
        selected = candidates
        profile_used = str(profile["name"])
        if len(selected) >= target_clean_ops:
            break

    selected = selected[: max(target_clean_ops, 12)]

    recommended_symbols: list[str] = []
    seen_symbols: set[str] = set()
    for row in selected:
        sym = str(row.get("symbol", "")).upper().strip()
        if sym and sym not in seen_symbols:
            seen_symbols.add(sym)
            recommended_symbols.append(sym)

    return {
        "status": "ok",
        "generated_utc": now_utc(),
        "target_clean_ops": target_clean_ops,
        "profile_used": profile_used,
        "candidate_count": len(selected),
        "symbol_metrics_path": str(metrics_path),
        "runtime_control_path": str(RUNTIME_FILE),
        "recommended_symbol_whitelist": recommended_symbols,
        "candidates": selected,
    }


def write_outputs(payload: dict[str, Any]) -> tuple[Path, Path, Path]:
    OUT_OPS.mkdir(parents=True, exist_ok=True)
    OUT_EXEC.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_json = OUT_OPS / f"clean_ops_roster_{stamp}.json"
    out_md = OUT_OPS / f"clean_ops_roster_{stamp}.md"

    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    LATEST_ROSTER_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Clean Ops Roster",
        "",
        f"Generated UTC: {payload.get('generated_utc', '')}",
        f"Profile Used: {payload.get('profile_used', '')}",
        f"Target Clean Ops: {payload.get('target_clean_ops', 0)}",
        f"Candidate Count: {payload.get('candidate_count', 0)}",
        "",
        "## Top Candidates",
    ]

    for row in (payload.get("candidates", []) or [])[:12]:
        lines.append(
            "- "
            + f"{row.get('symbol', '')}{row.get('quote', '')} | score={row.get('clean_score', 0)} | "
            + f"quick={row.get('quick_gain_score', 0)} | trap={row.get('trap_rate_pct', 0)}% | "
            + f"win={row.get('best_buy_win_rate_pct', 0)}% | style={row.get('style', '')}"
        )

    out_md.write_text("\n".join(lines), encoding="utf-8")
    return out_json, out_md, LATEST_ROSTER_FILE


def main() -> None:
    payload = build_roster()
    out_json, out_md, latest = write_outputs(payload)
    print(
        json.dumps(
            {
                "status": payload.get("status", "ok"),
                "target_clean_ops": payload.get("target_clean_ops", 0),
                "candidate_count": payload.get("candidate_count", 0),
                "profile_used": payload.get("profile_used", ""),
                "top_symbols": payload.get("recommended_symbol_whitelist", [])[:10],
                "out_json": str(out_json),
                "out_md": str(out_md),
                "latest": str(latest),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
