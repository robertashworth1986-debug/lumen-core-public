from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'out' / 'execution'
HEARTBEAT_FILE = OUT / 'live_engine_heartbeat.json'
TRADE_LOG_FILE = OUT / 'trade_log.json'
ALERT_LOG_FILE = OUT / 'live_alerts.log'


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def _heartbeat_age_sec(path: Path) -> float:
    try:
        return max(0.0, time.time() - path.stat().st_mtime)
    except Exception:
        return 999999.0


def _emit(message: str, log_path: Path) -> None:
    line = f"[{_now_utc()}] {message}"
    print(line, flush=True)
    try:
        with log_path.open('a', encoding='utf-8') as handle:
            handle.write(line + '\n')
    except Exception:
        pass


def _trade_brief(row: dict[str, Any]) -> str:
    symbol = str(row.get('symbol', '?'))
    status = str(row.get('status', '?'))
    side = str(row.get('side', '?'))
    size_usd = float(row.get('size_usd', 0.0) or 0.0)
    net_pnl = row.get('net_pnl', None)
    close_reason = str(row.get('close_reason', '') or '')
    parts = [f"trade {status}", symbol, side, f"size=${size_usd:.2f}"]
    if net_pnl is not None:
        try:
            parts.append(f"net_pnl=${float(net_pnl):.4f}")
        except Exception:
            pass
    if close_reason:
        parts.append(f"reason={close_reason}")
    return ' | '.join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description='Watch live engine heartbeat and trades for actionable alerts.')
    parser.add_argument('--poll-sec', type=float, default=3.0)
    parser.add_argument('--stale-sec', type=float, default=15.0)
    parser.add_argument('--iterations', type=int, default=0, help='0 = run forever')
    args = parser.parse_args()

    poll_sec = max(0.5, float(args.poll_sec or 3.0))
    stale_sec = max(2.0, float(args.stale_sec or 15.0))
    iterations = max(0, int(args.iterations or 0))

    last_loop: int | None = None
    last_status_key: tuple[Any, ...] | None = None
    last_trade_key: tuple[Any, ...] | None = None
    stale_alerted = False
    runs = 0

    _emit('live alert watcher started', ALERT_LOG_FILE)

    while True:
        heartbeat = _load_json(HEARTBEAT_FILE, {})
        trades = _load_json(TRADE_LOG_FILE, [])
        age_sec = _heartbeat_age_sec(HEARTBEAT_FILE)

        loop = heartbeat.get('loop')
        status = str(heartbeat.get('status', '') or '')
        selection_mode = str(heartbeat.get('selection_mode', '') or '')
        reason = str(heartbeat.get('reason', '') or '')
        symbol = str(heartbeat.get('symbol', '') or '')
        edge_bps = heartbeat.get('edge_bps')
        confidence = heartbeat.get('confidence')
        extra = heartbeat.get('extra', {}) if isinstance(heartbeat.get('extra', {}), dict) else {}
        best_symbol = str(extra.get('best_symbol', '') or '')

        status_key = (loop, status, selection_mode, reason, symbol, edge_bps, confidence, best_symbol)
        if loop != last_loop and status_key != last_status_key:
            if status == 'waiting' and selection_mode == 'capital_aware_wait_low_edge':
                candidate = best_symbol or symbol or '?'
                _emit(f"waiting for stronger edge | loop={loop} | candidate={candidate} | mode={selection_mode}", ALERT_LOG_FILE)
            elif status in {'armed', 'routing', 'managing', 'entered'}:
                _emit(
                    f"setup active | loop={loop} | status={status} | symbol={symbol or best_symbol or '?'} | edge_bps={edge_bps} | confidence={confidence}",
                    ALERT_LOG_FILE,
                )
            elif status and status not in {'selecting', 'waiting'}:
                _emit(f"engine status | loop={loop} | status={status} | reason={reason or selection_mode}", ALERT_LOG_FILE)
            last_status_key = status_key
            last_loop = loop if isinstance(loop, int) else last_loop

        if isinstance(trades, list) and trades:
            last_trade = trades[-1] if isinstance(trades[-1], dict) else None
            if last_trade is not None:
                trade_key = (
                    last_trade.get('timestamp'),
                    last_trade.get('txid'),
                    last_trade.get('status'),
                    last_trade.get('net_pnl'),
                )
                if trade_key != last_trade_key:
                    _emit(_trade_brief(last_trade), ALERT_LOG_FILE)
                    last_trade_key = trade_key

        if age_sec > stale_sec:
            if not stale_alerted:
                _emit(f"WARNING stale heartbeat | age_sec={age_sec:.1f} | last_loop={loop}", ALERT_LOG_FILE)
                stale_alerted = True
        elif stale_alerted:
            _emit(f"heartbeat recovered | age_sec={age_sec:.1f} | loop={loop}", ALERT_LOG_FILE)
            stale_alerted = False

        runs += 1
        if iterations > 0 and runs >= iterations:
            break
        time.sleep(poll_sec)

    _emit('live alert watcher stopped', ALERT_LOG_FILE)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
