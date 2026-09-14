"""Synthetic offline daily-report and isolated caller return-code regressions."""
import ast
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code'))
spec = importlib.util.spec_from_file_location('daily_report_under_test', ROOT / 'code/institutional_daily_report.py')
daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daily)


def snapshot(**changes):
    value = {'schema': daily.INPUT_SCHEMA, 'as_of_utc': '2026-09-14T08:00:00Z',
             'declared_mode': 'synthetic', 'declared_currency': 'USD', 'ledger': []}
    value.update(changes)
    return value


def row(**changes):
    value = {'event_id': 'a', 'timestamp': '2026-09-14T07:30:00Z',
             'mode': 'synthetic', 'currency': 'USD', 'notional_usd': '0.01'}
    value.update(changes)
    return value


def test_empty_input_does_not_fabricate_account_or_benchmark():
    result = daily.build_report(snapshot())
    for section in ('account', 'risk', 'performance', 'execution_flow_60m'):
        assert all(value is None for value in result[section].values())
    assert result['benchmark']['excess_return_vs_spy_pct'] is None
    assert result['investment_ready'] is result['broker_reconciled'] is result['live_authority'] is False
    assert result['record_diagnostics']['declared_recent_notional_sum_usd'] is None


def test_declared_zero_and_precise_money_not_replaced_by_defaults():
    value = snapshot(status={'account': {'equity': 0, 'cash': '0', 'buying_power': '900000000000000.01'}},
                     state={'equity_usd': '500', 'paper_profit_usd': '900'})
    result = daily.build_report(value)
    assert result['declared_inputs']['status.account'] == {'equity': '0', 'cash': '0', 'buying_power': '900000000000000.01'}
    assert result['account']['equity_usd'] is result['account']['pnl_total_usd'] is None


@pytest.mark.parametrize('bad', [True, 'NaN', 'Infinity', '1e9999', '1e-13', 10**30, [], {}])
def test_invalid_declarations_remain_unknown(bad):
    result = daily.build_report(snapshot(status={'account': {'equity': bad}}))
    assert result['declared_inputs']['status.account']['equity'] is None
    assert result['invalid_declared_fields'] == ['status.account.equity']


@pytest.mark.parametrize('stamp,key', [
    ('2026-09-14T08:00:01Z', 'future_timestamp_records'),
    ('2026-09-14T06:59:59Z', 'older_records'),
    ('2026-09-14T07:30:00', 'invalid_or_naive_timestamp_records'),
    ('broken', 'invalid_or_naive_timestamp_records'),
    (None, 'invalid_or_naive_timestamp_records'),
    ('2026-09-14T08:00:00.000000001Z', 'invalid_or_naive_timestamp_records'),
])
def test_excluded_timestamp_coverage(stamp, key):
    diag = daily.build_report(snapshot(ledger=[row(timestamp=stamp)]))['record_diagnostics']
    assert diag[key] == 1
    assert diag['records_in_declared_60m_window'] == 0
    assert diag['declared_recent_notional_sum_usd'] is None


def test_fixed_inclusive_window_and_timezone_conversion():
    value = snapshot(ledger=[row(event_id='a', timestamp='2026-09-14T07:00:00Z'),
                             row(event_id='b', timestamp='2026-09-14T03:00:00-05:00')])
    result = daily.build_report(value)
    assert result == daily.build_report(deepcopy(value))
    assert result['record_diagnostics']['records_in_declared_60m_window'] == 2
    assert result['record_diagnostics']['declared_recent_notional_sum_usd'] == '0.02'
    assert result['execution_flow_60m']['events'] is None


@pytest.mark.parametrize('changes,key', [
    ({'event_id': ''}, 'missing_or_invalid_identity_records'),
    ({'event_id': True}, 'missing_or_invalid_identity_records'),
    ({'id': 'different'}, 'conflicting_identity_records'),
])
def test_identity_holds(changes, key):
    diag = daily.build_report(snapshot(ledger=[row(**changes)]))['record_diagnostics']
    assert diag[key] == 1
    assert diag['declared_recent_notional_sum_usd'] is None


def test_duplicate_records_not_silently_summed():
    diag = daily.build_report(snapshot(ledger=[row(), row()]))['record_diagnostics']
    assert diag['duplicate_identity_records'] == 1
    assert diag['records_in_declared_60m_window'] == 2
    assert diag['declared_recent_notional_sum_usd'] is None


@pytest.mark.parametrize('changes', [
    {'notional_usd': None}, {'notional_usd': -1}, {'notional_usd': True},
    {'currency': 'EUR'}, {'mode': 'live'},
])
def test_partial_or_mixed_notionals_are_held(changes):
    diag = daily.build_report(snapshot(ledger=[row(**changes)]))['record_diagnostics']
    assert diag['declared_recent_notional_sum_usd'] is None


@pytest.mark.parametrize('changes', [
    {'schema': 'other'}, {'as_of_utc': None}, {'as_of_utc': '2026-09-14'},
    {'as_of_utc': '2026-09-14T08:00:00.000000001Z'},
    {'status': []}, {'state': None}, {'evidence': 3}, {'status': {'account': []}},
    {'evidence': {'capital': None}}, {'ledger': {}}, {'ledger': [None]},
])
def test_invalid_snapshot_shape_rejected(changes):
    with pytest.raises(ValueError):
        daily.build_report(snapshot(**changes))


@pytest.mark.parametrize('raw', [b'{"x":1,"x":2}', b'{"x":NaN}', b'[]', b'\xff',
                                b'{"x":1e99999999999999999999999999}', b'{'])
def test_strict_snapshot_parser(tmp_path, raw):
    source = tmp_path / 'in.json'
    source.write_bytes(raw)
    with pytest.raises(ValueError):
        daily.read_snapshot(source)


def test_snapshot_byte_bound_and_row_bound(tmp_path, monkeypatch):
    source = tmp_path / 'large.json'
    source.write_bytes(b' ' * 32)
    monkeypatch.setattr(daily, 'MAX_BYTES', 31)
    with pytest.raises(ValueError):
        daily.read_snapshot(source)
    monkeypatch.setattr(daily, 'MAX_ROWS', 1)
    with pytest.raises(ValueError):
        daily.build_report(snapshot(ledger=[row(), row()]))


def test_cli_custody_outputs_and_no_overwrite(tmp_path):
    source, out = tmp_path / 'source.json', tmp_path / 'review'
    raw = json.dumps(snapshot(ledger=[row()])).encode()
    source.write_bytes(raw)
    assert daily.main(['--snapshot', str(source), '--output-dir', str(out)]) == 0
    result = json.loads((out / 'institutional_daily_report.json').read_text())
    assert result['source_snapshot']['sha256'] == hashlib.sha256(raw).hexdigest()
    receipt = json.loads((out / 'institutional_daily_report_sha256.json').read_text())
    for name, expected in receipt['files'].items():
        data = (out / name).read_bytes()
        assert expected == {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    with pytest.raises(SystemExit) as error:
        daily.main(['--snapshot', str(source), '--output-dir', str(out)])
    assert error.value.code == 2
    assert before == {p.name: p.read_bytes() for p in out.iterdir()}


def test_no_argument_cli_held_without_outputs(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / 'code/institutional_daily_report.py')],
                            cwd=tmp_path, capture_output=True, text=True, timeout=15)
    assert result.returncode == 2
    assert list(tmp_path.iterdir()) == []


def test_invalid_input_does_not_create_output(tmp_path):
    source, out = tmp_path / 'bad.json', tmp_path / 'review'
    source.write_text('{"schema":"wrong"}')
    with pytest.raises(SystemExit):
        daily.main(['--snapshot', str(source), '--output-dir', str(out)])
    assert not out.exists()


@pytest.mark.parametrize('prior', [0, 12, 999])
def test_legacy_caller_holds_without_retry_or_claiming_success(prior):
    # Execute only the selected function with inert fake dependencies. Never
    # import the credentialed legacy executor or launch a process.
    source = ast.parse((ROOT / 'code/execution/alpaca_paper_executor.py').read_text())
    function = next(node for node in source.body if isinstance(node, ast.FunctionDef) and node.name == 'run_periodic_artifacts')
    fake_path = SimpleNamespace(exists=lambda: True)
    calls = []
    namespace = {'math': math, 'INSTITUTIONAL_DAILY_REPORT_SCRIPT': fake_path,
                 'INVESTOR_EVIDENCE_PACK_SCRIPT': fake_path,
                 'ROOT': Path('synthetic-root'), 'sys': SimpleNamespace(executable='unused'),
                 'subprocess': SimpleNamespace(run=lambda *a, **k: calls.append('unexpected process'))}
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<isolated caller>', 'exec'), namespace)
    state = {'last_report_refresh_ts': prior, 'last_evidence_pack_refresh_ts': prior}
    for now in (9999, 10000, 99999):
        report_ts, pack_ts, notes = namespace['run_periodic_artifacts']({}, state, now)
        assert (report_ts, pack_ts) == (prior, prior)
        assert notes == ['report_refresh=held_explicit_snapshot_required',
                         'evidence_pack_refresh=held_legacy_financial_inputs_unreviewed']
    assert calls == []


def test_canonical_facade_installs_publication_hold_before_legacy_exports():
    source = ast.parse((ROOT / 'code/execution/alpaca_paper_executor.py').read_text())
    binding = next(node for node in source.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                           and target.value.id == '_legacy' and target.attr == 'run_periodic_artifacts'
                           for target in node.targets))
    held = object()
    legacy = SimpleNamespace()
    exec(compile(ast.Module(body=[binding], type_ignores=[]), '<isolated facade binding>', 'exec'),
         {'_legacy': legacy, 'run_periodic_artifacts': held})
    assert legacy.run_periodic_artifacts is held
    export_loop = next(node for node in source.body if isinstance(node, ast.For) and ast.unparse(node.iter) == 'dir(_legacy)')
    assert binding.lineno < export_loop.lineno
