"""
LUMA AUTO-TICKET PRODUCER
─────────────────────────
Runs the spike hunter scanner and emits high-conviction setups
as PENDING_HUMAN_APPROVAL tickets into execution_approval_queue.json.

Robert (or any allowlisted controller) still has to click Approve & Fire
in the v3 dashboard. This module just keeps the queue full of the BEST
opportunities the scanner can find.

USAGE
─────
  Single shot (rescan + emit, then exit):
    python code/auto_ticket_producer.py

  Daemon (loops every INTERVAL_MIN minutes):
    python code/auto_ticket_producer.py --daemon

  Use cached spike_hunter_latest.json without rescanning:
    python code/auto_ticket_producer.py --cached

SAFETY
──────
* Defaults to `validate=true` (Kraken DRY-RUN). Pass --live to flip to real.
* Hard caps: notional <= MAX_NOTIONAL_USD ($20, under the gateway's $25 cap).
* Max MAX_PENDING_TICKETS open in the queue at once (default 3).
* Per-pair cooldown: never emit a duplicate while one is PENDING/OPEN.
* Skips signals == ['WATCH']. Requires score >= MIN_SCORE.
* Skips pairs with 24h USD volume below MIN_24H_VOL_USD (illiquid).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = ROOT / "execution_approval_queue.json"
SPIKE_LATEST = ROOT / "out" / "spike_hunter" / "spike_hunter_latest.json"
SPIKE_HISTORY_DIR = ROOT / "out" / "spike_hunter" / "history"
SPIKE_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
PRODUCER_LOG = ROOT / "out" / "execution" / "auto_ticket_producer.jsonl"
PRODUCER_LOG.parent.mkdir(parents=True, exist_ok=True)
AUTO_FIRE_CONFIG = ROOT / "run" / "auto_fire_config.json"
AUTO_FIRE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
DAEMON_PID_FILE = ROOT / "run" / "auto_ticket_producer.pid"


def _read_runtime_config(default_threshold: float | None,
                         default_enabled: bool) -> dict:
    """Read live config from disk; returns {enabled, auto_fire_score}."""
    if AUTO_FIRE_CONFIG.exists():
        try:
            cfg = json.loads(AUTO_FIRE_CONFIG.read_text(encoding="utf-8"))
            return {
                "enabled": bool(cfg.get("enabled", default_enabled)),
                "auto_fire_score": cfg.get("auto_fire_score", default_threshold),
            }
        except Exception:
            pass
    return {"enabled": default_enabled, "auto_fire_score": default_threshold}


def _write_runtime_config(cfg: dict) -> None:
    AUTO_FIRE_CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def _archive_scan(scan: dict) -> None:
    """Save a timestamped snapshot for later backtesting."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = SPIKE_HISTORY_DIR / f"spike_{ts}.json"
    try:
        out.write_text(json.dumps(scan, indent=2), encoding="utf-8")
    except Exception:
        pass

# Tunables ─────────────────────────────────────────────────────────────────
DEFAULT_CONTROLLER = "Robert"
MAX_NOTIONAL_USD   = 20.0   # under gateway cap of $25
MIN_NOTIONAL_USD   = 5.0    # Kraken minimums vary; $5 is generally safe
MAX_PENDING_TICKETS = 6     # never flood the queue
MIN_SCORE          = 35.0   # 0-100 composite
MIN_24H_VOL_USD    = 25_000 # liquidity floor
COOLDOWN_PAIRS_STATES = {"PENDING_HUMAN_APPROVAL", "EXECUTED_OPEN"}
INTERVAL_MIN_DEFAULT = 15
BANKROLL_DEFAULT     = 150.0
TOP_N_DEFAULT        = 20


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_queue() -> list[dict]:
    if not QUEUE_FILE.exists():
        return []
    try:
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_queue(rows: list[dict]) -> None:
    QUEUE_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _log_event(event: dict) -> None:
    event = {"ts": _utc_iso(), **event}
    with PRODUCER_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")


def _round_volume(vol: float) -> str:
    # Kraken accepts up to 8 decimals on most pairs.
    if vol >= 1:
        return f"{vol:.4f}"
    if vol >= 0.01:
        return f"{vol:.6f}"
    return f"{vol:.8f}"


def _normalize_pair_for_kraken(pair: str, wsname: str) -> str:
    # Kraken AddOrder happily takes either the altname (e.g. XBTUSD) or the
    # legacy code (e.g. XXBTZUSD). The altname is what the spike hunter stores
    # under "pair", so we use it directly. wsname like "XBT/USD" also works.
    return pair or wsname.replace("/", "")


def _refresh_scan(bankroll: float, top_n: int) -> dict:
    """Re-run the live spike hunter scan."""
    sys.path.insert(0, str(ROOT / "code"))
    import kraken_spike_hunter_live as sh  # type: ignore
    return sh.run_scan(bankroll=bankroll, top_n=top_n)


def _load_cached_scan() -> dict | None:
    if not SPIKE_LATEST.exists():
        return None
    try:
        return json.loads(SPIKE_LATEST.read_text(encoding="utf-8"))
    except Exception:
        return None


def _eligible(row: dict) -> tuple[bool, str]:
    score = float(row.get("score", 0))
    signals = row.get("signals") or []
    vol_24h = float(row.get("vol_24h_usd", 0))
    price   = float(row.get("price", 0))

    if signals == ["WATCH"]:
        return False, "watch_only"
    if score < MIN_SCORE:
        return False, f"score<{MIN_SCORE}"
    if vol_24h < MIN_24H_VOL_USD:
        return False, f"vol_24h<{MIN_24H_VOL_USD}"
    if price <= 0:
        return False, "zero_price"
    return True, "ok"


def _build_ticket(row: dict, controller: str, validate: bool, note: str) -> dict | None:
    pair = _normalize_pair_for_kraken(row.get("pair", ""), row.get("wsname", ""))
    if not pair:
        return None
    price = float(row["price"])
    # Use the scanner's suggested USD size, but clamp to producer caps.
    suggested_usd = float(row.get("size_usd", 0)) or float(row.get("size_pct", 0)) * BANKROLL_DEFAULT / 100
    notional = max(MIN_NOTIONAL_USD, min(MAX_NOTIONAL_USD, suggested_usd or MAX_NOTIONAL_USD))
    volume_base = notional / price
    if volume_base <= 0:
        return None

    userref = int(time.time())
    ticket_id = f"TICKET-{int(time.time()*1000)}-{pair}"
    return {
        "ticket_id":     ticket_id,
        "timestamp":     _utc_iso(),
        "controller":    controller,
        "pair":          pair,
        "side":          "buy",  # spot long-only setups
        "notional_usd":  round(notional, 2),
        "volume_base":   volume_base,
        "payload": {
            "pair":      pair,
            "type":      "buy",
            "ordertype": "market",
            "volume":    _round_volume(volume_base),
            "validate":  "true" if validate else "false",
            "userref":   userref,
        },
        "approval_state": "PENDING_HUMAN_APPROVAL",
        "note": note,
        "scanner_meta": {
            "score":      row.get("score"),
            "signals":    row.get("signals"),
            "rsi":        row.get("rsi"),
            "dip_pct":    row.get("dip_from_high_pct"),
            "vol_surge":  row.get("vol_surge"),
            "m4h":        row.get("m4h"),
            "m24h":       row.get("m24h"),
            "vol_24h_usd": row.get("vol_24h_usd"),
            "wsname":     row.get("wsname"),
            "source":     "spike_hunter_v1",
        },
    }


def emit_tickets(use_cached: bool, validate: bool, controller: str,
                 bankroll: float, top_n: int,
                 auto_fire_score: float | None = None,
                 gateway_url: str = "http://127.0.0.1:8787") -> dict:
    scan = _load_cached_scan() if use_cached else None
    if scan is None:
        scan = _refresh_scan(bankroll=bankroll, top_n=top_n)
        # Archive every fresh scan for later backtesting
        _archive_scan(scan)
    else:
        # Even cached scans get archived (deduped by timestamp filename)
        _archive_scan(scan)

    leaderboard = scan.get("leaderboard") or []
    rows = _load_queue()

    # Pairs already pending or in flight ─ skip duplicates
    blocked_pairs = {
        r.get("pair")
        for r in rows
        if r.get("approval_state") in COOLDOWN_PAIRS_STATES
    }
    pending_count = sum(
        1 for r in rows if r.get("approval_state") == "PENDING_HUMAN_APPROVAL"
    )
    slots = max(0, MAX_PENDING_TICKETS - pending_count)

    emitted = []
    skipped = []

    for row in leaderboard:
        if slots <= 0:
            break
        pair = _normalize_pair_for_kraken(row.get("pair", ""), row.get("wsname", ""))
        if pair in blocked_pairs:
            skipped.append({"pair": pair, "reason": "in_queue"})
            continue
        ok, why = _eligible(row)
        if not ok:
            skipped.append({"pair": pair, "reason": why})
            continue
        ticket = _build_ticket(
            row,
            controller=controller,
            validate=validate,
            note=f"auto_ticket_producer: score={row.get('score')} signals={row.get('signals')}",
        )
        if not ticket:
            skipped.append({"pair": pair, "reason": "build_failed"})
            continue
        rows.append(ticket)
        blocked_pairs.add(pair)
        emitted.append({
            "ticket_id": ticket["ticket_id"],
            "pair": pair,
            "score": row.get("score"),
            "signals": row.get("signals"),
            "notional_usd": ticket["notional_usd"],
            "validate": ticket["payload"]["validate"],
        })
        slots -= 1

    if emitted:
        _save_queue(rows)

    # ── Optional auto-fire ─────────────────────────────────────────────
    auto_fired = []
    if auto_fire_score is not None and emitted:
        for e in emitted:
            score = e.get("score") or 0.0
            if score < auto_fire_score:
                continue
            if e.get("validate"):
                # never auto-fire DRY-RUN; pointless
                continue
            tid = e["ticket_id"]
            body = json.dumps({
                "ticket_id": tid,
                "decision": "approve",
                "controller": controller,
                "reason": f"auto-fire: score {score} >= {auto_fire_score}",
                "confirm_phrase": f"FIRE {tid}",
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{gateway_url}/api/master/approval/decide",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                auto_fired.append({
                    "ticket_id": tid,
                    "pair": e["pair"],
                    "score": score,
                    "status": res.get("status"),
                    "txid": res.get("txid"),
                    "reason": res.get("reason"),
                })
            except urllib.error.HTTPError as he:
                auto_fired.append({"ticket_id": tid, "pair": e["pair"], "status": "http_error",
                                   "code": he.code, "body": he.read().decode("utf-8", "ignore")[:200]})
            except Exception as exc:  # noqa: BLE001
                auto_fired.append({"ticket_id": tid, "pair": e["pair"], "status": "error", "error": str(exc)})

    summary = {
        "scan_generated_utc": scan.get("generated_utc"),
        "pairs_scanned": scan.get("pairs_scanned"),
        "leaderboard_size": len(leaderboard),
        "pending_before": pending_count,
        "slots_available": MAX_PENDING_TICKETS - pending_count,
        "emitted_count": len(emitted),
        "emitted": emitted,
        "skipped_count": len(skipped),
        "skipped_top10": skipped[:10],
        "validate_mode": validate,
        "controller": controller,
        "auto_fire_score": auto_fire_score,
        "auto_fired": auto_fired,
        "auto_fired_count": len(auto_fired),
    }
    _log_event(summary)
    return summary


def main() -> int:
    # Force UTF-8 on stdout/stderr so unicode arrows etc don't crash the daemon
    # when output is redirected to a file on Windows (cp1252 default).
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--daemon", action="store_true", help="loop forever")
    ap.add_argument("--interval-min", type=int, default=INTERVAL_MIN_DEFAULT)
    ap.add_argument("--cached", action="store_true",
                    help="use last spike_hunter_latest.json instead of rescanning")
    ap.add_argument("--live", action="store_true",
                    help="emit tickets with validate=false (REAL orders on approve)")
    ap.add_argument("--controller", default=DEFAULT_CONTROLLER)
    ap.add_argument("--bankroll", type=float, default=BANKROLL_DEFAULT)
    ap.add_argument("--top-n", type=int, default=TOP_N_DEFAULT)
    ap.add_argument("--auto-fire-score", type=float, default=None,
                    help="Auto-approve+fire any LIVE ticket whose score >= this threshold "
                         "(0-100). Requires --live. Skipped for DRY-RUN tickets.")
    ap.add_argument("--gateway-url", default="http://127.0.0.1:8787")
    args = ap.parse_args()

    validate = not args.live
    if args.auto_fire_score is not None and validate:
        print("[AUTO-TKT] WARNING: --auto-fire-score has no effect in DRY-RUN mode; "
              "pass --live to actually auto-fire.", flush=True)

    # Seed runtime config file with CLI defaults so the dashboard can edit live
    if not AUTO_FIRE_CONFIG.exists():
        _write_runtime_config({
            "enabled": True,
            "auto_fire_score": args.auto_fire_score,
        })

    # Write PID for dashboard control
    try:
        DAEMON_PID_FILE.write_text(str(__import__("os").getpid()), encoding="utf-8")
    except Exception:
        pass

    print(f"[AUTO-TKT] validate_mode={'DRY-RUN' if validate else 'LIVE'} "
          f"max_notional=${MAX_NOTIONAL_USD} max_pending={MAX_PENDING_TICKETS} "
          f"min_score={MIN_SCORE} auto_fire_score={args.auto_fire_score}", flush=True)

    while True:
        # Re-read live config every cycle (dashboard can edit without restart)
        rt = _read_runtime_config(args.auto_fire_score, True)
        live_threshold = rt["auto_fire_score"] if rt["enabled"] else None
        try:
            summary = emit_tickets(
                use_cached=args.cached,
                validate=validate,
                controller=args.controller,
                bankroll=args.bankroll,
                top_n=args.top_n,
                auto_fire_score=live_threshold,
                gateway_url=args.gateway_url,
            )
            print(f"[AUTO-TKT] cycle enabled={rt['enabled']} "
                  f"threshold={live_threshold} emitted={summary['emitted_count']} "
                  f"skipped={summary['skipped_count']} "
                  f"auto_fired={summary['auto_fired_count']} "
                  f"slots_left={summary['slots_available'] - summary['emitted_count']}",
                  flush=True)
            for e in summary["emitted"]:
                print(f"  + {e['pair']:<12} score={e['score']:<5} "
                      f"signals={e['signals']} ${e['notional_usd']} "
                      f"validate={e['validate']}", flush=True)
            for f in summary["auto_fired"]:
                print(f"  ⚡ AUTO-FIRED {f.get('pair','?'):<12} "
                      f"score={f.get('score','?')} status={f.get('status')} "
                      f"txid={f.get('txid')}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[AUTO-TKT] error: {exc}", flush=True)
            _log_event({"event": "error", "error": str(exc)})

        if not args.daemon:
            return 0
        sleep_s = max(60, args.interval_min * 60)
        print(f"[AUTO-TKT] sleeping {sleep_s}s...", flush=True)
        time.sleep(sleep_s)


if __name__ == "__main__":
    sys.exit(main())
