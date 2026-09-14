"""Legacy trade rows must not silently become institutional account evidence."""
import importlib.util
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def reporter():
    return load('code/execution/investor_performance_report.py', 'ledger_report_test')


def row(identity='a', **changes):
    return dict({'trade_id': identity, 'status': 'CLOSED', 'mode': 'paper',
                 'currency': 'USD', 'net_pnl': 2.0, 'net_pnl_pct': 1.0,
                 'round_trip_fee_usd': 0.1}, **changes)


def test_empty_is_unknown_not_zero(reporter):
    result = reporter.analyze_rows([])
    assert result['closed_records'] == 0
    for key in ('reported_net_pnl_sum_usd', 'win_rate_pct', 'sharpe', 'max_drawdown'):
        assert result[key] is None


def test_record_count_never_promotes_confidence(reporter):
    result = reporter.analyze_rows([row(str(i)) for i in range(100)])
    assert result['sample_quality_tier'] == 'UNVERIFIED_RECORDS'
    assert result['investment_ready'] is False
    assert result['broker_reconciled'] is False
    assert result['reported_net_pnl_sum_usd'] == '200'
    assert result['sharpe'] is None
    assert result['total_net_pnl_pct'] is None


@pytest.mark.parametrize('bad', [None, '', 'bad', True, float('nan'), float('inf'), 'Infinity', 1e30,
                                 '1e999999999', '1e-999999999', '1' * 1000])
def test_missing_bad_or_nonfinite_amount_holds_whole_sum(reporter, bad):
    result = reporter.analyze_rows([row(), row('b', net_pnl=bad)])
    assert result['reported_net_pnl_sum_usd'] is None
    assert result['win_rate_pct'] is None
    assert result['field_coverage']['net_pnl_usd']['valid'] == 1


def test_missing_status_is_not_closed(reporter):
    item = row(); del item['status']
    result = reporter.analyze_rows([item])
    assert result['closed_records'] == 0
    assert result['unknown_status_records'] == 1


@pytest.mark.parametrize('change', [{'mode': 'live'}, {'mode': None}, {'currency': 'EUR'}])
def test_mixed_or_unknown_basis_holds_dollar_sum(reporter, change):
    result = reporter.analyze_rows([row(), row('b', **change)])
    assert result['reported_net_pnl_sum_usd'] is None


def test_declared_live_is_not_verified_live(reporter):
    result = reporter.analyze_rows([row(mode='live')])
    assert result['declared_mode'] == 'live'
    assert result['broker_reconciled'] is False
    assert result['live_authorized'] is False


def test_duplicate_id_holds_aggregates_without_dropping_records(reporter):
    result = reporter.analyze_rows([row(), row(net_pnl=-3)])
    assert result['duplicate_identity_records'] == 1
    assert result['closed_records'] == 2
    assert result['reported_net_pnl_sum_usd'] is None


def test_identical_rows_without_ids_are_not_counted_twice(reporter):
    item = row(); del item['trade_id']
    result = reporter.analyze_rows([item, item.copy()])
    assert result['duplicate_content_records'] == 1
    assert result['reported_net_pnl_sum_usd'] is None


def test_missing_id_does_not_claim_unique_trades(reporter):
    item = row(); del item['trade_id']
    result = reporter.analyze_rows([item])
    assert result['unique_closed_trades'] is None
    assert result['reported_net_pnl_sum_usd'] == '2'


def test_conflicting_aliases_hold_sum(reporter):
    result = reporter.analyze_rows([row(realized_pnl_usd=3)])
    assert result['reported_net_pnl_sum_usd'] is None
    assert result['field_coverage']['net_pnl_usd']['conflicting'] == 1


def test_zero_is_valid_when_explicitly_reported(reporter):
    result = reporter.analyze_rows([row(net_pnl=0, net_pnl_pct=0)])
    assert result['reported_net_pnl_sum_usd'] == '0'
    assert result['win_rate_pct'] == 0.0
    assert result['sharpe'] is None


def test_signed_cancellation_preserves_reported_cents(reporter):
    result = reporter.analyze_rows([row('a', net_pnl='1000000000000000'),
                                    row('b', net_pnl='0.01'),
                                    row('c', net_pnl='-1000000000000000')])
    assert result['reported_net_pnl_sum_usd'] == '0.01'


def test_negative_fees_are_not_silently_accepted(reporter):
    result = reporter.analyze_rows([row(round_trip_fee_usd=-0.1)])
    assert result['total_round_trip_fees_usd'] is None


def test_open_records_do_not_enter_closed_statistics(reporter):
    result = reporter.analyze_rows([row(), row('b', status='OPEN', net_pnl=999)])
    assert result['closed_records'] == 1
    assert result['reported_net_pnl_sum_usd'] == '2'


def test_full_false_green_fixture_cannot_promote_scorecard(monkeypatch):
    scorecard = load('code/BUILD_INSTITUTIONAL_METRICS_SCORECARD.py', 'legacy_scorecard_positive_test')
    def fixture(path, default):
        return {
            scorecard.DAILY_REPORT: {'account': {'return_total_pct': 20},
                                    'performance': {'win_rate_pct': 99}, 'risk': {'max_drawdown_pct': 0}},
            scorecard.CHAMPION_LINEAGES: {'top_lineages': [{'wf_sharpe_mean': 5, 'test_sharpe': 5}]},
            scorecard.REGISTRY: {'rows': [{'enabled': True, 'rows': 1}]},
            scorecard.OPPORTUNITY_BRIEF: {'measured_total_hour_usd': 999},
            scorecard.SOURCE_BREADTH: {'combined_approved_sources': 60},
            scorecard.EDGE_TRUTH: {'edge_quality_score': 100, 'verdict': 'PASS'},
        }.get(path, {})
    monkeypatch.setattr(scorecard, 'load_json', fixture)
    result = scorecard.build_scorecard()
    assert result['legacy_heuristic_diagnostic']['tier'] == 'GREEN'
    assert result['readiness_tier'] == 'HOLD'
    assert result['investment_ready'] is False


def test_equity_column_does_not_supply_cash_flow_reconciliation(reporter):
    result = reporter.analyze_rows([row(equity_usd=99000), row('b', equity_usd=98000)])
    assert result['max_drawdown'] is None
    assert result['portfolio_equity_usd'] is None
    assert result['sharpe'] is None


@pytest.mark.parametrize('raw', ['{}', '[1]', '[{"x":1,"x":2}]', '[{"x":NaN}]', '[{"x":1e999}]'])
def test_invalid_source_is_rejected(reporter, tmp_path, raw):
    source = tmp_path / 'rows.json'; source.write_text(raw)
    with pytest.raises(ValueError):
        reporter.read_trade_snapshot(source)


def test_source_has_exact_byte_identity(reporter, tmp_path):
    import hashlib
    source = tmp_path / 'rows.json'
    raw = json.dumps([row()]).encode(); source.write_bytes(raw)
    rows, receipt = reporter.read_trade_snapshot(source)
    assert rows[0]['trade_id'] == 'a'
    assert str(rows[0]['round_trip_fee_usd']) == '0.1'
    assert receipt['sha256'] == hashlib.sha256(raw).hexdigest()
    assert receipt['bytes'] == len(raw)


def test_input_byte_limit_is_enforced(reporter, tmp_path):
    source = tmp_path / 'rows.json'; source.write_text(' ' * 101)
    with pytest.raises(ValueError, match='byte limit'):
        reporter.read_trade_snapshot(source, max_bytes=100)


def test_missing_file_is_not_an_empty_success(reporter, tmp_path):
    with pytest.raises(OSError):
        reporter.read_trade_snapshot(tmp_path / 'absent.json')


def test_bad_cli_input_does_not_replace_report(tmp_path):
    source = tmp_path / 'rows.json'; source.write_text('broken')
    target = tmp_path / 'report.json'; target.write_text('retain me')
    proc = subprocess.run([sys.executable, str(ROOT / 'code/execution/investor_performance_report.py'),
                           '--trade-log', str(source), '--out-json', str(target),
                           '--out-md', str(tmp_path / 'report.md')], capture_output=True, timeout=15)
    assert proc.returncode != 0
    assert target.read_text() == 'retain me'


def test_dashboard_reuses_report_and_does_not_invent_equity():
    pd = pytest.importorskip('pandas')
    dashboard = load('dashboard/dashboard_analytics.py', 'legacy_dashboard_test')
    frame = pd.DataFrame([row(), row('b', net_pnl=-3)])
    metrics = dashboard.compute_metrics(frame)
    assert metrics['total_pnl'] == '-1'
    assert metrics['sharpe'] is None
    assert metrics['max_drawdown'] is None
    assert dashboard.plot_equity_curve(frame) is None


def test_dashboard_escapes_supplied_labels_and_marks_unverified():
    pd = pytest.importorskip('pandas')
    dashboard = load('dashboard/dashboard_analytics.py', 'legacy_dashboard_render_test')
    frame = pd.DataFrame([row(symbol='</script><script>alert(1)</script>')])
    markup = dashboard.render_report(frame)
    assert '</script><script>alert(1)</script>' not in markup
    assert 'UNVERIFIED_RECORDS' in markup
    assert 'Unknown' in markup
    assert '100000' not in markup


def test_optional_plotly_absence_keeps_complete_table_report(monkeypatch):
    import builtins
    pd = pytest.importorskip('pandas')
    dashboard = load('dashboard/dashboard_analytics.py', 'legacy_dashboard_no_plotly_test')
    original = builtins.__import__
    def without_plotly(name, *args, **kwargs):
        if name.startswith('plotly'):
            raise ModuleNotFoundError("No module named 'plotly'", name='plotly')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', without_plotly)
    markup = dashboard.render_report(pd.DataFrame([row(net_pnl=-2.25)]))
    assert 'Optional chart unavailable' in markup
    assert '-2.25' in markup
    assert 'Unknown / not established' in markup


def test_json_decimal_amounts_survive_parse_and_sum(reporter, tmp_path):
    source = tmp_path / 'precision.json'
    source.write_text('[{"trade_id":"a","status":"CLOSED","mode":"paper","currency":"USD","net_pnl":900000000000000.01},'
                      '{"trade_id":"b","status":"CLOSED","mode":"paper","currency":"USD","net_pnl":-900000000000000}]')
    rows, _ = reporter.read_trade_snapshot(source)
    assert Decimal(str(rows[0]['net_pnl'])) == Decimal('900000000000000.01')
    result = reporter.analyze_rows(rows)
    assert result['reported_net_pnl_sum_usd'] == '0.01'


@pytest.mark.parametrize('exponent', ['99999999999999999999999999999', '-99999999999999999999999999999'])
def test_unrepresentable_decimal_exponent_is_controlled(reporter, tmp_path, exponent):
    source = tmp_path / 'rows.json'
    source.write_text('[{"trade_id":"a","status":"CLOSED","mode":"paper","currency":"USD","net_pnl":1e' + exponent + '}]')
    with pytest.raises(ValueError, match='exponent range'):
        reporter.read_trade_snapshot(source)
    target = tmp_path / 'report.json'; target.write_text('retain me')
    proc = subprocess.run([sys.executable, str(ROOT / 'code/execution/investor_performance_report.py'),
                           '--trade-log', str(source), '--out-json', str(target),
                           '--out-md', str(tmp_path / 'report.md')], capture_output=True, timeout=15)
    assert proc.returncode == 2
    assert b'Traceback' not in proc.stderr
    assert target.read_text() == 'retain me'


def test_large_single_amount_is_serialized_exactly(reporter):
    result = reporter.analyze_rows([row(net_pnl='900000000000000.01')])
    assert result['reported_net_pnl_sum_usd'] == '900000000000000.01'
    assert '900000000000000.01' in json.dumps(result, allow_nan=False)


def test_source_aliases_are_preserved_in_dashboard(tmp_path):
    pytest.importorskip('pandas')
    dashboard = load('dashboard/dashboard_analytics.py', 'ledger_source_alias_test')
    second = row('b'); del second['net_pnl']; second['realized_pnl_usd'] = 3
    source = tmp_path / 'rows.json'; source.write_text(json.dumps([row(), second]))
    frame = dashboard.load_trade_log(str(source))
    assert dashboard.compute_metrics(frame)['total_pnl'] == '5'
    assert 'realized_pnl_usd' in dashboard.render_report(frame)


def test_changed_source_frame_cannot_keep_old_receipt(tmp_path):
    pytest.importorskip('pandas')
    dashboard = load('dashboard/dashboard_analytics.py', 'ledger_source_mutation_test')
    source = tmp_path / 'rows.json'; source.write_text(json.dumps([row()]))
    frame = dashboard.load_trade_log(str(source)); frame.loc[0, 'net_pnl'] = 300
    with pytest.raises(ValueError, match='changed'):
        dashboard.render_report(frame)


def test_explicit_invalid_alias_is_not_erased_in_dashboard(tmp_path):
    pytest.importorskip('pandas')
    dashboard = load('dashboard/dashboard_analytics.py', 'ledger_invalid_alias_test')
    source = tmp_path / 'rows.json'; source.write_text(json.dumps([row(realized_pnl_usd=None)]))
    frame = dashboard.load_trade_log(str(source))
    assert dashboard.compute_metrics(frame)['total_pnl'] is None


@pytest.mark.parametrize('other', ['common', None, True, ''])
def test_conflicting_identity_alias_holds_aggregate(reporter, other):
    result = reporter.analyze_rows([row('a', id=other), row('b', id=other)])
    assert result['conflicting_identity_records'] == 2
    assert result['reported_net_pnl_sum_usd'] is None


def test_equal_identity_aliases_are_one_declaration(reporter):
    result = reporter.analyze_rows([row('a', id='a')])
    assert result['conflicting_identity_records'] == 0
    assert result['distinct_declared_closed_ids'] == 1


@pytest.mark.parametrize('target,payload', [('INVESTOR_PERF', []), ('DAILY_REPORT', {'account': None}),
                                         ('CHAMPION_LINEAGES', {'top_lineages': [1]}),
                                         ('SEED_VALIDATION', {'champion': None})])
def test_scorecard_malformed_shapes_are_controlled_hold(monkeypatch, target, payload):
    scorecard = load('code/BUILD_INSTITUTIONAL_METRICS_SCORECARD.py', 'scorecard_bad_shape_test')
    monkeypatch.setattr(scorecard, 'load_json', lambda path, default: payload if path == getattr(scorecard, target) else {})
    result = scorecard.build_scorecard()
    assert result['readiness_tier'] == 'HOLD'
    assert result['source_shape_issues']


def test_scorecard_nonfinite_input_cannot_escape_as_json_nan(monkeypatch):
    scorecard = load('code/BUILD_INSTITUTIONAL_METRICS_SCORECARD.py', 'scorecard_nonfinite_test')
    monkeypatch.setattr(scorecard, 'load_json', lambda path, default: {'measured_total_hour_usd': float('nan')} if path == scorecard.OPPORTUNITY_BRIEF else {})
    result = scorecard.build_scorecard()
    assert result['opportunity_kpis']['measured_total_hour_usd'] is None
    json.dumps(result, allow_nan=False)


def test_scorecard_string_false_and_rows_do_not_prove_measurement(monkeypatch):
    scorecard = load('code/BUILD_INSTITUTIONAL_METRICS_SCORECARD.py', 'scorecard_declarations_test')
    monkeypatch.setattr(scorecard, 'load_json', lambda path, default: {'rows': [{'enabled': 'false', 'rows': 1}]} if path == scorecard.REGISTRY else {})
    result = scorecard.build_scorecard()
    assert result['source_coverage']['enabled_sources'] == 0
    assert result['source_coverage']['measured_sources'] is None
    assert result['source_coverage']['declared_row_presence_sources'] == 1


def test_scorecard_does_not_convert_unverified_diagnostics_to_green(monkeypatch):
    scorecard = load('code/BUILD_INSTITUTIONAL_METRICS_SCORECARD.py', 'legacy_scorecard_test')
    monkeypatch.setattr(scorecard, 'load_json', lambda *args: {})
    result = scorecard.build_scorecard()
    assert result['readiness_tier'] == 'HOLD'
    assert result['readiness_score'] is None
    assert result['trading_kpis']['max_drawdown_pct'] is None
    assert 'Unknown' in scorecard.render_markdown(result)
