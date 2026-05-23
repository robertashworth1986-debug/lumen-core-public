from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_FILE = ROOT / "run" / "approval_autofire_policy.json"
OUT_OPS = ROOT / "out" / "ops"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


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


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return int(default)


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


def request_json(url: str, method: str = "GET", payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    headers: dict[str, str] = {}
    data: Optional[bytes] = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    req = Request(url=url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=25) as resp:
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


def percentile(values: list[float], p: float) -> Optional[float]:
    if not values:
        return None
    arr = sorted(float(v) for v in values)
    if len(arr) == 1:
        return arr[0]
    p_clamped = min(1.0, max(0.0, float(p)))
    idx = (len(arr) - 1) * p_clamped
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return arr[lo]
    frac = idx - lo
    return arr[lo] * (1.0 - frac) + arr[hi] * frac


def build_pair_metrics(ticket: dict[str, Any]) -> dict[str, Optional[float]]:
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

    return {
        "edge_score": first_optional_float(
            scanner_meta.get("edge_score"),
            scanner_meta.get("alpha_edge_score"),
            alpha_gate.get("alpha_edge_score"),
            profitability_meta.get("raw_edge_pct"),
        ),
        "execution_quality_score": first_optional_float(
            scanner_meta.get("execution_quality_score"),
            alpha_gate.get("execution_quality_score"),
            profitability_meta.get("execution_quality_score"),
        ),
        "liquidity_score": first_optional_float(
            scanner_meta.get("liquidity_score"),
            alpha_gate.get("liquidity_score"),
            profitability_meta.get("liquidity_score"),
        ),
        "estimated_friction_bps": first_optional_float(
            alpha_gate.get("estimated_friction_bps"),
            profitability_meta.get("estimated_friction_bps"),
            scanner_meta.get("spread_bps"),
            alpha_gate.get("spread_bps"),
        ),
        "risk_adjusted_net_edge_pct": first_optional_float(
            alpha_gate.get("risk_adjusted_net_edge_pct"),
            profitability_meta.get("risk_adjusted_net_edge_pct"),
            alpha_gate.get("net_edge_pct"),
            profitability_meta.get("net_edge_pct"),
        ),
    }


def compact_metrics(values: list[float]) -> dict[str, Optional[float]]:
    if not values:
        return {
            "count": 0,
            "p35": None,
            "p50": None,
            "p65": None,
        }
    return {
        "count": len(values),
        "p35": percentile(values, 0.35),
        "p50": percentile(values, 0.50),
        "p65": percentile(values, 0.65),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Calibrate pair-level autofire buy thresholds from live pending queue metadata.")
    ap.add_argument("--gateway-url", default="http://127.0.0.1:8787")
    ap.add_argument("--policy-file", default=str(DEFAULT_POLICY_FILE))
    ap.add_argument("--lookback-hours", type=float, default=24.0)
    ap.add_argument("--min-samples", type=int, default=2)
    ap.add_argument("--max-pairs", type=int, default=10)
    ap.add_argument("--apply", action="store_true", help="Apply recommendations into buy_pair_overrides.")
    args = ap.parse_args()

    gateway_url = str(args.gateway_url).rstrip("/")
    policy_file = Path(args.policy_file)
    lookback_hours = max(0.25, float(args.lookback_hours))
    min_samples = max(1, int(args.min_samples))
    max_pairs = max(1, int(args.max_pairs))

    queue_payload = request_json(f"{gateway_url}/api/master/approval-queue")
    tickets = queue_payload.get("tickets") if isinstance(queue_payload, dict) else None
    if not isinstance(tickets, list):
        print(json.dumps({
            "status": "error",
            "reason": "queue_unavailable",
            "queue_payload": queue_payload,
        }, indent=2))
        return 2

    policy: dict[str, Any] = {}
    if policy_file.exists():
        try:
            payload = json.loads(policy_file.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                policy = payload
        except Exception:
            policy = {}

    base_exec_floor = max(0.0, to_float(policy.get("buy_min_execution_quality_score"), 10.0))
    base_liq_floor = max(0.0, to_float(policy.get("buy_min_liquidity_score"), 8.0))
    base_friction_cap = max(0.0, to_float(policy.get("buy_max_estimated_friction_bps"), 45.0))
    base_risk_edge_floor = max(0.0, to_float(policy.get("buy_min_risk_adjusted_net_edge_pct"), 0.25))
    base_cooldown = max(0.0, to_float(policy.get("buy_pair_cooldown_sec"), 75.0))

    now_dt = datetime.now(timezone.utc)
    grouped: dict[str, dict[str, Any]] = {}

    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue
        if str(ticket.get("approval_state") or "").upper() != "PENDING_HUMAN_APPROVAL":
            continue
        if str(ticket.get("side") or "").strip().lower() != "buy":
            continue

        ts = parse_utc(ticket.get("timestamp"))
        if ts is None:
            continue
        age_hours = (now_dt - ts).total_seconds() / 3600.0
        if age_hours < 0 or age_hours > lookback_hours:
            continue

        pair = str(ticket.get("pair") or "").strip().upper()
        if not pair:
            continue

        metrics = build_pair_metrics(ticket)
        row = grouped.setdefault(
            pair,
            {
                "count": 0,
                "ticket_ids": [],
                "age_hours": [],
                "execution_quality_score": [],
                "liquidity_score": [],
                "estimated_friction_bps": [],
                "risk_adjusted_net_edge_pct": [],
                "edge_score": [],
            },
        )
        row["count"] += 1
        row["ticket_ids"].append(str(ticket.get("ticket_id") or ""))
        row["age_hours"].append(age_hours)

        for key in (
            "execution_quality_score",
            "liquidity_score",
            "estimated_friction_bps",
            "risk_adjusted_net_edge_pct",
            "edge_score",
        ):
            val = metrics.get(key)
            if val is not None:
                row[key].append(float(val))

    ranked_pairs = sorted(grouped.items(), key=lambda kv: (-int(kv[1].get("count", 0)), kv[0]))[:max_pairs]

    recommendations: list[dict[str, Any]] = []
    for pair, agg in ranked_pairs:
        sample_count = int(agg.get("count", 0))
        if sample_count < min_samples:
            continue

        exec_stats = compact_metrics(agg.get("execution_quality_score", []))
        liq_stats = compact_metrics(agg.get("liquidity_score", []))
        friction_stats = compact_metrics(agg.get("estimated_friction_bps", []))
        edge_stats = compact_metrics(agg.get("risk_adjusted_net_edge_pct", []))

        override: dict[str, Any] = {}

        exec_floor = exec_stats.get("p35")
        if exec_floor is not None:
            override["buy_min_execution_quality_score"] = round(max(base_exec_floor, float(exec_floor)), 3)

        liq_floor = liq_stats.get("p35")
        if liq_floor is not None:
            override["buy_min_liquidity_score"] = round(max(base_liq_floor, float(liq_floor)), 3)

        friction_cap = friction_stats.get("p65")
        if friction_cap is not None:
            tightened_cap = min(base_friction_cap, max(8.0, float(friction_cap)))
            override["buy_max_estimated_friction_bps"] = round(tightened_cap, 3)

        risk_edge_floor = edge_stats.get("p35")
        if risk_edge_floor is not None:
            override["buy_min_risk_adjusted_net_edge_pct"] = round(
                max(base_risk_edge_floor, float(risk_edge_floor)),
                4,
            )

        if sample_count >= 3 and base_cooldown > 0:
            cooldown = min(600.0, base_cooldown * (1.0 + 0.25 * (sample_count - 2)))
            override["buy_pair_cooldown_sec"] = round(cooldown, 2)

        recommendations.append(
            {
                "pair": pair,
                "sample_count": sample_count,
                "age_hours_min": round(min(agg.get("age_hours", [0.0])), 4),
                "age_hours_max": round(max(agg.get("age_hours", [0.0])), 4),
                "ticket_ids": [x for x in agg.get("ticket_ids", []) if x][:12],
                "stats": {
                    "execution_quality_score": exec_stats,
                    "liquidity_score": liq_stats,
                    "estimated_friction_bps": friction_stats,
                    "risk_adjusted_net_edge_pct": edge_stats,
                },
                "override": override,
            }
        )

    recommendations.sort(key=lambda row: (-int(row.get("sample_count", 0)), str(row.get("pair") or "")))

    existing_overrides = policy.get("buy_pair_overrides") if isinstance(policy.get("buy_pair_overrides"), dict) else {}
    if not isinstance(existing_overrides, dict):
        existing_overrides = {}

    merged_overrides = dict(existing_overrides)
    for row in recommendations:
        pair = str(row.get("pair") or "").strip().upper()
        if not pair:
            continue
        pair_override = row.get("override") if isinstance(row.get("override"), dict) else {}
        base_pair = merged_overrides.get(pair) if isinstance(merged_overrides.get(pair), dict) else {}
        merged = dict(base_pair)
        merged.update(pair_override)
        merged_overrides[pair] = merged

    applied = False
    if args.apply:
        policy_out = dict(policy)
        policy_out["buy_pair_overrides"] = merged_overrides
        policy_file.parent.mkdir(parents=True, exist_ok=True)
        policy_file.write_text(json.dumps(policy_out, indent=2), encoding="utf-8")
        applied = True

    OUT_OPS.mkdir(parents=True, exist_ok=True)
    slug = timestamp_slug()
    report_ts_path = OUT_OPS / f"approval_autofire_pair_calibration_{slug}.json"
    report_latest_path = OUT_OPS / "approval_autofire_pair_calibration_latest.json"
    report_md_ts_path = OUT_OPS / f"approval_autofire_pair_calibration_{slug}.md"
    report_md_latest_path = OUT_OPS / "approval_autofire_pair_calibration_latest.md"

    report = {
        "generated_utc": now_utc(),
        "schema": "approval_autofire_pair_calibration_v1",
        "scope": {
            "gateway_url": gateway_url,
            "policy_file": str(policy_file),
            "lookback_hours": lookback_hours,
            "min_samples": min_samples,
            "max_pairs": max_pairs,
            "apply": bool(args.apply),
        },
        "baseline": {
            "buy_min_execution_quality_score": base_exec_floor,
            "buy_min_liquidity_score": base_liq_floor,
            "buy_max_estimated_friction_bps": base_friction_cap,
            "buy_min_risk_adjusted_net_edge_pct": base_risk_edge_floor,
            "buy_pair_cooldown_sec": base_cooldown,
        },
        "pending_buy_ticket_count": sum(
            1
            for t in tickets
            if isinstance(t, dict)
            and str(t.get("approval_state") or "").upper() == "PENDING_HUMAN_APPROVAL"
            and str(t.get("side") or "").strip().lower() == "buy"
        ),
        "candidate_pairs_found": len(grouped),
        "recommendations_count": len(recommendations),
        "recommendations": recommendations,
        "applied": applied,
        "resulting_override_pairs": len(merged_overrides),
        "evidence": {
            "queue_endpoint": f"{gateway_url}/api/master/approval-queue",
            "report_json": str(report_ts_path),
            "report_latest_json": str(report_latest_path),
            "report_md": str(report_md_ts_path),
            "report_latest_md": str(report_md_latest_path),
        },
    }

    report_ts_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_latest_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md_lines = [
        "# Approval Autofire Pair Calibration",
        "",
        f"- generated_utc: {report['generated_utc']}",
        f"- gateway_url: {gateway_url}",
        f"- lookback_hours: {lookback_hours}",
        f"- min_samples: {min_samples}",
        f"- apply: {applied}",
        f"- recommendations_count: {len(recommendations)}",
        f"- resulting_override_pairs: {len(merged_overrides)}",
        "",
        "## Top Recommendations",
        "",
    ]

    if recommendations:
        for row in recommendations:
            pair = str(row.get("pair") or "")
            sample_count = int(row.get("sample_count") or 0)
            override = row.get("override") if isinstance(row.get("override"), dict) else {}
            md_lines.append(f"- {pair}: samples={sample_count} override={json.dumps(override, sort_keys=True)}")
    else:
        md_lines.append("- none")

    md_lines.extend(
        [
            "",
            "## Evidence",
            "",
            f"- report_json: {report_ts_path}",
            f"- report_latest_json: {report_latest_path}",
            f"- report_md: {report_md_ts_path}",
            f"- report_latest_md: {report_md_latest_path}",
        ]
    )

    md_payload = "\n".join(md_lines) + "\n"
    report_md_ts_path.write_text(md_payload, encoding="utf-8")
    report_md_latest_path.write_text(md_payload, encoding="utf-8")

    print(json.dumps(
        {
            "status": "ok",
            "applied": applied,
            "recommendations_count": len(recommendations),
            "resulting_override_pairs": len(merged_overrides),
            "report_json": str(report_ts_path),
            "report_md": str(report_md_ts_path),
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
