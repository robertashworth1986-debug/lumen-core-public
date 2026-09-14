"""Bounded offline record diagnostics; no account, investment or execution claim."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRADE_LOG_DEFAULT = ROOT / 'out/execution/trade_log.json'
OUT_JSON_DEFAULT = ROOT / 'out/execution/investor_performance_report.json'
OUT_MD_DEFAULT = ROOT / 'out/execution/investor_performance_report.md'
MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 100_000
BOUNDARY = ('Descriptive arithmetic on supplied, unverified records only. Declared mode and currency '
            'are not authenticated. No broker reconciliation, account return, profitability, '
            'investment readiness, independent validation, or live authority is established.')


def _members(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON member')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError('Non-finite JSON number')


def _json_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('Non-finite JSON number')
    return result


def _validate_rows(rows):
    if not isinstance(rows, list) or len(rows) > MAX_ROWS or any(not isinstance(r, dict) for r in rows):
        raise ValueError('Trade log must be a bounded list of objects')


def read_trade_snapshot(path: Path, *, max_bytes: int = MAX_BYTES):
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_BYTES:
        raise ValueError('Invalid byte limit')
    path = Path(path)
    with path.open('rb') as handle:
        raw = handle.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError('Trade log exceeds byte limit')
    try:
        rows = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_members,
                          parse_constant=_reject_constant, parse_float=_json_float)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('Invalid trade-log encoding or nesting') from exc
    _validate_rows(rows)
    return rows, {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(),
                  'bytes': len(raw), 'records': len(rows), 'authenticity_verified': False}


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        return None
    try:
        text = str(value)
        if len(text) > 80:
            return None
        number = Decimal(text)
        if not number.is_finite() or number.copy_abs() > Decimal('1e15'):
            return None
        # Bounded decimal precision keeps aggregate arithmetic exact in the
        # declared record model; no float cancellation or exponent expansion.
        return number if number.as_tuple().exponent >= -12 else None
    except (InvalidOperation, ValueError):
        return None


def _sum(values):
    with localcontext() as context:
        context.prec = 40  # 100k rows, <=1e15 absolute value, <=12 decimal places.
        return sum(values, Decimal(0))


def _field(rows, names, *, nonnegative=False):
    values = []
    coverage = {'records': len(rows), 'valid': 0, 'missing': 0, 'invalid': 0, 'conflicting': 0}
    for row in rows:
        supplied = [row[name] for name in names if name in row]
        parsed = [_number(value) for value in supplied]
        if not supplied:
            coverage['missing'] += 1; values.append(None)
        elif any(value is None or (nonnegative and value < 0) for value in parsed):
            coverage['invalid'] += 1; values.append(None)
        elif len(set(parsed)) != 1:
            coverage['conflicting'] += 1; values.append(None)
        else:
            coverage['valid'] += 1; values.append(parsed[0])
    return values, coverage


def analyze_rows(rows):
    _validate_rows(rows)
    closed = [r for r in rows if isinstance(r.get('status'), str) and r['status'].strip().upper() == 'CLOSED']
    known_status = {'CLOSED', 'OPEN', 'PENDING', 'CANCELLED', 'CANCELED', 'REJECTED'}
    unknown_status = sum(not isinstance(r.get('status'), str) or r['status'].strip().upper() not in known_status for r in rows)
    modes = {str(r.get('mode', '')).strip().lower() for r in closed}
    mode = next(iter(modes)) if len(modes) == 1 and modes <= {'paper', 'shadow', 'synthetic', 'live'} else 'UNKNOWN_OR_MIXED'
    usd = bool(closed) and all(r.get('currency') == 'USD' for r in closed)
    identities = []
    identity_missing = 0
    for row in closed:
        identity = row.get('trade_id', row.get('id'))
        if not isinstance(identity, (str, int)) or isinstance(identity, bool) or not str(identity).strip():
            identity_missing += 1
        else:
            identities.append(str(identity))
    duplicate_ids = sum(count - 1 for count in Counter(identities).values())
    fingerprints = [json.dumps(r, sort_keys=True, default=str, ensure_ascii=True) for r in closed]
    duplicate_content = sum(count - 1 for count in Counter(fingerprints).values())
    record_basis = bool(closed) and not (duplicate_ids or duplicate_content or unknown_status) and mode != 'UNKNOWN_OR_MIXED'
    pnl, pnl_coverage = _field(closed, ['net_pnl', 'realized_pnl_usd'])
    percent, percent_coverage = _field(closed, ['net_pnl_pct'])
    fees, fee_coverage = _field(closed, ['round_trip_fee_usd'], nonnegative=True)
    pnl_complete = record_basis and usd and pnl_coverage['valid'] == len(closed)
    percent_complete = record_basis and percent_coverage['valid'] == len(closed)
    fees_complete = record_basis and usd and fee_coverage['valid'] == len(closed)
    reasons = [
        'Portfolio ratios withheld: trade-event returns are not periodic, cash-flow-adjusted account returns.',
        'Equity and drawdown withheld: initial equity, full account history and external-flow reconciliation are absent.',
        'Legacy sum-of-trade-percentages is withheld as an account return.',
        'Reported net fields are not independently reconciled to fills, fees or balances.',
    ]
    if not record_basis:
        reasons.append('Financial aggregates held: empty records, duplicate identities/content, unknown statuses, or unknown/mixed mode.')
    if not usd:
        reasons.append('USD aggregates held: each closed record must explicitly declare currency USD.')
    if not pnl_complete:
        reasons.append('Net PnL and win rate require a complete, finite, nonconflicting USD field for every eligible closed record.')
    return {
        'schema': 'lumencore.reported_trade_diagnostics.v2',
        'record_count': len(rows), 'closed_records': len(closed), 'closed_trades': None,
        'unique_closed_trades': None,
        'distinct_declared_closed_ids': len(set(identities)) if not identity_missing else None,
        'missing_identity_records': identity_missing,
        'duplicate_identity_records': duplicate_ids, 'duplicate_content_records': duplicate_content,
        'unknown_status_records': unknown_status, 'declared_mode': mode,
        'declared_currency': 'USD' if usd else 'UNKNOWN_OR_MIXED',
        'sample_quality_tier': 'UNVERIFIED_RECORDS', 'sample_confidence_note': BOUNDARY,
        'field_coverage': {'net_pnl_usd': pnl_coverage, 'net_pnl_pct': percent_coverage, 'fees_usd': fee_coverage},
        'reported_net_pnl_sum_usd': float(_sum(pnl)) if pnl_complete else None,
        'win_rate_pct': 100.0 * sum(value > 0 for value in pnl) / len(pnl) if pnl_complete else None,
        'avg_net_pnl_pct': float(_sum(percent)) / len(percent) if percent_complete else None,
        'total_round_trip_fees_usd': float(_sum(fees)) if fees_complete else None,
        'total_net_pnl_pct': None, 'sharpe': None, 'sortino': None, 'calmar': None,
        'max_drawdown': None, 'portfolio_equity_usd': None,
        'reported_pnl_by_closed_record': [float(value) for value in pnl] if pnl_complete else [],
        'investment_ready': False, 'broker_reconciled': False, 'live_authorized': False,
        'independently_validated': False, 'limitations': reasons, 'boundary': BOUNDARY,
    }


def display(value):
    return 'Unknown / not established' if value is None else str(value)


def render_markdown(payload):
    keys = ('record_count', 'closed_records', 'declared_mode', 'declared_currency',
            'sample_quality_tier', 'reported_net_pnl_sum_usd', 'win_rate_pct',
            'avg_net_pnl_pct', 'total_round_trip_fees_usd', 'sharpe', 'max_drawdown')
    lines = ['# Reported Trade Diagnostics', '', payload['boundary'], '']
    lines += [f'- {key}: {display(payload[key])}' for key in keys]
    lines += ['', '## Limits', ''] + [f'- {reason}' for reason in payload['limitations']]
    if payload.get('source_snapshot'):
        lines += ['', f"Source SHA-256: `{payload['source_snapshot']['sha256']}`"]
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trade-log', type=Path, default=TRADE_LOG_DEFAULT)
    parser.add_argument('--out-json', type=Path, default=OUT_JSON_DEFAULT)
    parser.add_argument('--out-md', type=Path, default=OUT_MD_DEFAULT)
    args = parser.parse_args()
    try:
        rows, receipt = read_trade_snapshot(args.trade_log)
        payload = analyze_rows(rows)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Trade diagnostics held: {exc}\n')
    payload['timestamp_utc'] = datetime.now(timezone.utc).isoformat()
    payload['source_snapshot'] = receipt
    payload['source_trade_log'] = str(args.trade_log)
    content = json.dumps(payload, indent=2, allow_nan=False) + '\n'
    markdown = render_markdown(payload)
    if args.out_json.resolve() == args.out_md.resolve() or args.trade_log.resolve() in {args.out_json.resolve(), args.out_md.resolve()}:
        parser.exit(2, 'Trade diagnostics held: input and output paths must be distinct\n')
    for path, text in ((args.out_json, content), (args.out_md, markdown)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
    print('Unverified record diagnostics written; portfolio claims remain held.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
