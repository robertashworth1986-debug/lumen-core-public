"""Offline daily-record diagnostic. No credentials, network, or runtime mutation."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
from execution.investor_performance_report import (
    MAX_BYTES, MAX_ROWS, _members, _reject_constant, _json_float, _number, _money,
)

INPUT_SCHEMA = 'lumencore.daily_report_input.v1'
BOUNDARY = ('Supplied local declarations only; source hashes identify captured bytes, not '
            'authenticity, completeness, freshness or event chronology. No broker/account '
            'reconciliation, investment readiness, alpha, independent validation or live authority.')


def parse_iso_ts(raw):
    if not isinstance(raw, str) or len(raw) > 64:
        return None
    # datetime.fromisoformat truncates finer-than-microsecond fractions. Reject
    # unsupported precision so a future record cannot round into the window.
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', raw, flags=re.ASCII) is None:
        return None
    try:
        value = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        return value.astimezone(timezone.utc) if value.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def _mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError(label + ' must be an object')
    return value


def read_snapshot(path):
    with Path(path).open('rb') as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Snapshot exceeds byte limit')
    try:
        payload = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_members,
                             parse_float=_json_float, parse_constant=_reject_constant)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('Invalid snapshot encoding or nesting') from exc
    _mapping(payload, 'snapshot')
    return payload, {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                     'authenticity_verified': False}


def _declared_numbers(mapping, names):
    result, invalid = {}, []
    for name in names:
        value = _number(mapping.get(name))
        result[name] = None if value is None else _money([value])
        if name in mapping and value is None:
            invalid.append(name)
    return result, invalid


def build_report(snapshot):
    snapshot = _mapping(snapshot, 'snapshot')
    if snapshot.get('schema') != INPUT_SCHEMA:
        raise ValueError('Unsupported snapshot schema')
    as_of = parse_iso_ts(snapshot.get('as_of_utc'))
    if as_of is None:
        raise ValueError('A timezone-aware as_of_utc is required')
    status = _mapping(snapshot.get('status', {}), 'status')
    state = _mapping(snapshot.get('state', {}), 'state')
    evidence = _mapping(snapshot.get('evidence', {}), 'evidence')
    account = _mapping(status.get('account', {}), 'status.account')
    capital = _mapping(evidence.get('capital', {}), 'evidence.capital')
    rows = snapshot.get('ledger', [])
    if not isinstance(rows, list) or len(rows) > MAX_ROWS or any(not isinstance(r, dict) for r in rows):
        raise ValueError('Ledger must be a bounded list of objects')
    declaration_sets = [('status.account', account, ('equity', 'cash', 'buying_power')),
                        ('state', state, ('equity_usd', 'cash_usd', 'paper_profit_usd')),
                        ('evidence.capital', capital, ('starting_capital_usd', 'latest_equity_usd', 'total_return_pct'))]
    declarations, invalid_fields = {}, []
    for label, mapping, names in declaration_sets:
        declarations[label], invalid = _declared_numbers(mapping, names)
        invalid_fields.extend(label + '.' + name for name in invalid)

    recent, invalid_time, future, old = [], 0, 0, 0
    seen, duplicate, identity_missing, identity_conflict = set(), 0, 0, 0
    for row in rows:
        stamp = parse_iso_ts(row.get('timestamp'))
        if stamp is None:
            invalid_time += 1
        elif stamp > as_of:
            future += 1
        elif (as_of - stamp).total_seconds() <= 3600:
            recent.append(row)
        else:
            old += 1
        ids = [row[key] for key in ('event_id', 'id', 'trade_id') if key in row]
        if not ids or any(not isinstance(v, str) or not v.strip() or len(v) > 256 for v in ids):
            identity_missing += 1
        elif len(set(ids)) != 1:
            identity_conflict += 1
        elif ids[0] in seen:
            duplicate += 1
        else:
            seen.add(ids[0])

    mode = snapshot.get('declared_mode')
    currency = snapshot.get('declared_currency')
    mode_ok = isinstance(mode, str) and mode in {'paper', 'shadow', 'synthetic', 'live'}
    mode_consistent = mode_ok and all(row.get('mode') == mode for row in recent)
    currency_consistent = currency == 'USD' and all(row.get('currency') == 'USD' for row in recent)
    notionals = [_number(row.get('notional_usd')) for row in recent]
    complete = bool(recent) and all(value is not None and value >= 0 for value in notionals)
    hold = bool(duplicate or identity_missing or identity_conflict or invalid_time or future)
    notional = _money(notionals) if complete and not hold and mode_consistent and currency_consistent else None
    return {
        'schema': 'lumencore.daily_record_diagnostic.v2',
        'as_of_utc': as_of.isoformat(), 'as_of_basis': 'SUPPLIED_DECLARATION',
        'evidence_class': 'UNVERIFIED_LOCAL_SNAPSHOT', 'boundary': BOUNDARY,
        'broker_reconciled': False, 'investment_ready': False, 'live_authority': False,
        'source_freshness_verified': False, 'source_completeness_verified': False,
        'account': dict.fromkeys(('starting_capital_usd', 'equity_usd', 'pnl_total_usd',
                                 'return_total_pct', 'open_positions', 'cash_usd', 'buying_power_usd')),
        'risk': dict.fromkeys(('max_drawdown_pct', 'drawdown_from_peak_pct', 'risk_off_mode',
                              'entry_pause_active', 'entry_pause_until_ts')),
        'performance': dict.fromkeys(('fills_count', 'buy_count', 'sell_count', 'win_rate_pct',
                                     'sharpe_proxy', 'annualized_sharpe_proxy')),
        'benchmark': {'spy_day_change_pct': None, 'excess_return_vs_spy_pct': None,
                      'comparison_status': 'HELD_NO_RECONCILED_MATCHED_WINDOW_RETURNS'},
        'execution_flow_60m': dict.fromkeys(('events', 'opens', 'closes', 'gross_notional_usd')),
        'declared_inputs': declarations, 'invalid_declared_fields': invalid_fields,
        'record_diagnostics': {
            'records_supplied': len(rows), 'records_in_declared_60m_window': len(recent),
            'window_rule': 'as_of minus 3600 seconds <= timestamp <= as_of',
            'invalid_or_naive_timestamp_records': invalid_time,
            'future_timestamp_records': future, 'older_records': old,
            'duplicate_identity_records': duplicate, 'missing_or_invalid_identity_records': identity_missing,
            'conflicting_identity_records': identity_conflict,
            'declared_mode': mode if mode_ok else None,
            'declared_currency': 'USD' if currency == 'USD' else None,
            'mode_consistent_in_recent_records': mode_consistent,
            'currency_consistent_in_recent_records': currency_consistent,
            'declared_recent_notional_sum_usd': notional,
            'notional_basis': 'Unverified submitted record arithmetic; exact decimal string, not executed volume or account performance.',
        },
    }


def write_report(report, output_dir):
    """Create a new directory. An I/O failure may leave partial files; never overwrite."""
    if report.get('schema') != 'lumencore.daily_record_diagnostic.v2':
        raise ValueError('Unsupported report schema')
    json_data = (json.dumps(report, indent=2, allow_nan=False) + '\n').encode('utf-8')
    table = io.StringIO(newline='')
    writer = csv.writer(table)
    writer.writerow(['as_of_utc', 'records_supplied', 'records_in_declared_60m_window', 'account_performance_status', 'investment_ready'])
    diag = report['record_diagnostics']
    writer.writerow([report['as_of_utc'], diag['records_supplied'], diag['records_in_declared_60m_window'], 'UNKNOWN_NOT_RECONCILED', 'false'])
    files = {'institutional_daily_report.json': json_data,
             'institutional_daily_report.csv': table.getvalue().encode('utf-8')}
    receipt = {'schema': 'lumencore.daily_diagnostic_output_manifest.v1', 'files': {
        name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)} for name, data in files.items()},
        'boundary': 'File custody only; no financial or scientific validation.'}
    files['institutional_daily_report_sha256.json'] = (json.dumps(receipt, indent=2) + '\n').encode('utf-8')
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=False)
    for name, data in files.items():
        with (output_dir / name).open('xb') as handle:
            handle.write(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        snapshot, source = read_snapshot(args.snapshot)
        report = build_report(snapshot)
        report['source_snapshot'] = source
        write_report(report, args.output_dir)
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        parser.exit(2, 'Daily diagnostic held: ' + type(exc).__name__ + '; no shared runtime report updated.\n')
    print('OFFLINE DAILY RECORD DIAGNOSTIC WRITTEN; ACCOUNT PERFORMANCE UNKNOWN')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
