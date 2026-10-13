"""Offline fixtures for causal scoring, bounded risk and append-only records."""
import csv
import io
import hashlib
import json
import math
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
from execution import capital_engine_core as capital
from execution import rolling_capital_engine, rolling_capital_engine_multi
from execution.risk_kernel import RiskKernel, RiskState
from execution.sizing_engine import SizingEngine, SizeInput
from execution.liquidity_guard import LiquidityGuard, LiquiditySnapshot
from execution.trade_ledger import TradeLedger, LEDGER_SCHEMA_VERSION, CSV_FIELDS
from backtest_walkforward_engine import BacktestEngine


def risk_state(**changes):
    state = RiskState(0.0, 0.0, 0.0, False, 0, 5, False, False)
    return replace(state, **changes)


@pytest.mark.parametrize('field', ['day_pnl_usd', 'open_risk_usd', 'portfolio_heat'])
@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_unknown_risk_state_never_authorizes(field, value):
    allowed, reasons = RiskKernel().allow(risk_state(**{field: value}))
    assert allowed is False and 'invalid_risk_state' in reasons


def test_daily_loss_position_and_kill_caps_stay_closed():
    kernel = RiskKernel()
    assert kernel.allow(risk_state())[0] is True
    assert kernel.allow(risk_state(day_pnl_usd=-20.0))[0] is False
    assert kernel.allow(risk_state(kill_switch=True))[0] is False
    assert kernel.allow(risk_state(open_positions=5))[0] is False
    assert kernel.allow(risk_state(open_positions=True))[0] is False
    assert kernel.allow(risk_state(symbol_cooldown_active='false'))[0] is False


@pytest.mark.parametrize('changes', [dict(bid=float('nan')), dict(ask=float('inf')), dict(bid=101, ask=100), dict(bid_size=0), dict(ask_size=-1)])
def test_invalid_or_crossed_book_cannot_supply_liquidity(changes):
    snapshot = replace(LiquiditySnapshot(100, 100.01, 10, 10, 1, 5), **changes)
    decision = LiquidityGuard().assess(snapshot)
    assert not decision.pass_trade and decision.max_notional_usd == 0 and decision.score == 0


def test_finite_large_quotes_do_not_hide_spread_by_overflowing_the_midpoint():
    decision=LiquidityGuard().assess(LiquiditySnapshot(1e308,1.1e308,10,10,1,5))
    assert 'wide_spread' in decision.reasons
    assert math.isfinite(decision.score) and math.isfinite(decision.max_notional_usd)


def sizing_input(**changes):
    return replace(SizeInput(10000, 100, 90, .01, 1, 0, urgency='ultra_aggressive', dislocation_score=1), **changes)


def test_size_multipliers_never_expand_declared_risk_or_remaining_heat():
    engine = SizingEngine()
    sized = engine.size(sizing_input())
    assert 0 < sized.risk_usd <= 10000 * engine.max_risk_pct
    assert sized.qty * (10 + 190 * .0018) == pytest.approx(sized.risk_usd)
    remaining = engine.size(sizing_input(portfolio_heat=.0199))
    assert remaining.risk_usd <= 10000 * (.02 - .0199)
    assert engine.size(sizing_input(portfolio_heat=.02)).qty == 0


def test_sizing_floor_never_overrides_a_lower_declared_maximum():
    engine=SizingEngine(max_risk_pct=.0001,max_risk_pct_floor=.0005)
    assert 0 < engine.size(sizing_input()).risk_usd <= 10000*.0001


def test_size_cash_reserve_includes_entry_fee_and_slippage():
    sized = SizingEngine().size(sizing_input(stop_price=99.99, fee_bps=100, slippage_bps=100, reserve_usd=9900))
    assert sized.notional_usd * 1.02 <= 100 + 1e-10
    assert sized.qty * 100 == pytest.approx(sized.notional_usd)


@pytest.mark.parametrize('changes', [dict(equity_usd=float('nan')), dict(entry_price=-1), dict(realized_vol=float('inf')), dict(liquidity_score=0), dict(fee_bps=-1), dict(drawdown_pct=float('nan'))])
def test_invalid_sizing_never_returns_an_order_quantity(changes):
    decision = SizingEngine().size(sizing_input(**changes))
    assert decision.qty == decision.notional_usd == decision.risk_usd == 0


def fixture_prices(length=260, high_vol_tail=0):
    rng = np.random.default_rng(81)
    returns = np.r_[rng.normal(0, .001, length), rng.normal(0, .07, high_vol_tail)]
    close = 100 * np.cumprod(1 + returns)
    frame = pd.DataFrame({'close': close}, index=pd.date_range('2025-01-01', periods=len(close), freq='h', tz='UTC'))
    frame['ret'] = frame.close.pct_change(fill_method=None).fillna(0)
    return frame


def test_every_family_is_prefix_invariant_when_future_volatility_changes():
    full = fixture_prices(high_vol_tail=300)
    prefix = full.iloc[:260]
    original = capital.build_families(prefix)
    extended = capital.build_families(full)
    for name, signal in original.items():
        np.testing.assert_allclose(np.asarray(signal), np.asarray(extended[name])[:260], equal_nan=True, err_msg=name)


def test_array_signal_uses_return_timestamps_and_large_loss_is_not_clipped():
    index = pd.date_range('2025-01-01', periods=3, freq='h', tz='UTC')
    returns = pd.Series([0, -.5, .2], index=index)
    net, pos, turnover = capital.build_strategy_returns([1, -1, 0], returns, cost_bps=10)
    assert net.index.equals(index)
    assert net.tolist() == pytest.approx([0, -.501, -.202])
    assert pos.tolist() == [0, 1, -1]
    assert turnover.tolist() == [0, 1, 2]


def test_scoring_rejects_index_mismatch_nonfinite_returns_and_negative_costs():
    returns = pd.Series([0, .1], index=['a', 'b'])
    with pytest.raises(ValueError, match='matching indexes'):
        capital.build_strategy_returns(pd.Series([1, 1]), returns)
    with pytest.raises(ValueError, match='nonfinite'):
        capital.build_strategy_returns([1, 1], [0, float('nan')])
    with pytest.raises(ValueError, match='nonnegative'):
        capital.build_strategy_returns([1, 1], [0, .1], cost_bps=-1)


def test_drawdown_includes_starting_capital_even_in_short_windows():
    metrics = capital.stats([-.1, 0, .01])
    assert metrics['final_nav'] == pytest.approx(.909)
    assert metrics['max_drawdown'] == pytest.approx(-.1)
    assert metrics['annualization_ready'] is False
    assert capital.stats([-1])['max_drawdown'] == -1
    with pytest.raises(ValueError, match='-100%'):
        capital.stats([-1.1])
    with pytest.raises(ValueError, match='finite numeric range'):
        capital.stats([-1, 1e308])


def test_rolling_wrappers_use_one_canonical_scoring_implementation():
    assert rolling_capital_engine.build_families is capital.build_families
    assert rolling_capital_engine_multi.build_families is capital.build_families
    assert rolling_capital_engine.stats is capital.stats
    assert rolling_capital_engine_multi.build_strategy_returns is capital.build_strategy_returns


@pytest.mark.parametrize('name',['rolling_capital_engine.py','rolling_capital_engine_multi.py'])
def test_rolling_module_can_be_loaded_by_file_without_import_paths_or_side_effects(name,tmp_path,monkeypatch):
    path=Path(__file__).resolve().parents[1]/'code'/'execution'/name
    script='''import importlib.util,sys
spec=importlib.util.spec_from_file_location("isolated_rolling_path_load",sys.argv[1])
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(module.stats([-.1])["final_nav"])
'''
    env={key:value for key,value in os.environ.items() if key not in {'PYTHONPATH','PYTHONHOME'}}
    result=subprocess.run([sys.executable,'-I','-W','error','-c',script,str(path)],cwd=tmp_path,env=env,capture_output=True,text=True,check=False)
    assert result.returncode==0,result.stderr
    assert float(result.stdout.strip())==pytest.approx(.9)
    assert not (tmp_path/'C:').exists()


class LastMoveStrategy:
    def run(self, frame):
        return pd.DataFrame({'signal': np.sign(frame.close.diff().fillna(0))}, index=frame.index)


class AlwaysLong:
    def __init__(self):
        self.history_ends = []
        self.fits = []
    def fit(self, frame):
        self.fits.append(frame.index[-1])
    def run(self, frame):
        self.history_ends.append(frame.index[-1])
        return pd.DataFrame({'signal': 1.0}, index=frame.index)


def test_walkforward_cannot_profit_from_the_price_change_that_created_its_signal():
    frame = pd.DataFrame({'close': [100., 100., 110., 90.]})
    result = BacktestEngine(LastMoveStrategy()).run_backtest(frame, 2, 2)[0]
    assert result.pnl.tolist() == [0, -20]
    assert result.trades.signal.tolist() == [0, 1]
    assert result.trades.signal_asof.tolist() == [1, 2]


def test_walkforward_fee_slippage_first_test_move_and_exit_are_all_counted():
    strategy = AlwaysLong()
    frame = pd.DataFrame({'close': [100., 101., 102., 103.]})
    result = BacktestEngine(strategy, fee_bps=10, slippage_bps=10).run_backtest(frame, 2, 2)[0]
    assert strategy.fits == [1] and strategy.history_ends == [1, 2]
    assert result.trades.gross_pnl.sum() == 2
    assert result.trades.fee_cost.sum() == pytest.approx(.204)
    assert result.trades.slippage_cost.sum() == pytest.approx(.204)
    assert result.metrics['total_pnl'] == pytest.approx(1.592)
    assert result.trades.turnover.tolist() == [1, 1]
    assert result.metrics['terminal_position_closed'] is True


def test_walkforward_rejects_ambiguous_times_and_unknown_market_outcomes():
    with pytest.raises(ValueError, match='index'):
        BacktestEngine(AlwaysLong()).run_backtest(pd.DataFrame({'close': [100, 101]}, index=[0, 0]), 1, 1)
    with pytest.raises(ValueError, match='finite positive'):
        BacktestEngine(AlwaysLong()).run_backtest(pd.DataFrame({'close': [100, np.nan]}), 1, 1)
    with pytest.raises(ValueError, match='positive integers'):
        BacktestEngine(AlwaysLong()).run_backtest(pd.DataFrame({'close': [100, 101]}), 0, 1)


def ledger(tmp_path):
    return TradeLedger(str(tmp_path/'trades.csv'), str(tmp_path/'trades.jsonl'))


def test_ledger_open_close_and_unknown_fields_keep_one_csv_schema(tmp_path):
    book = ledger(tmp_path)
    first = book.append({'timestamp': 't0', 'symbol': 'TOY', 'status': 'OPEN', 'gate_score': .7})
    second = book.append({'status': 'CLOSED', 'symbol': 'TOY', 'timestamp': 't1', 'pnl': -1.3, 'custom': {'source': 'synthetic'}})
    with open(book.csv_path, newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]['status'] == 'OPEN' and rows[1]['status'] == 'CLOSED'
    assert rows[1]['pnl'] == '-1.3' and None not in rows[1]
    assert json.loads(rows[1]['record_json'])['custom']['source'] == 'synthetic'
    assert book.read_records()[0]['record_hash'] == first
    assert book.read_records()[1]['record_hash'] == second
    assert book.read_records()[1]['ledger_schema_version'] == LEDGER_SCHEMA_VERSION


def test_ledger_duplicate_replay_is_idempotent_across_instances(tmp_path):
    payload = {'timestamp': 't0', 'event_id': 'one', 'symbol': 'TOY', 'status': 'OPEN', 'qty': 1}
    first = ledger(tmp_path).append(payload)
    second = ledger(tmp_path).append(payload)
    assert first == second
    assert len(ledger(tmp_path).read_records()) == 1
    with pytest.raises(ValueError, match='different payload'):
        ledger(tmp_path).append({**payload, 'qty': 2})


def test_ledger_failed_csv_projection_is_recovered_without_a_second_source_event(tmp_path):
    book = ledger(tmp_path)
    payload = {'timestamp': 't0', 'symbol': 'TOY', 'status': 'OPEN'}
    with patch.object(book, '_append_csv', side_effect=OSError('fixture write failure')):
        with pytest.raises(OSError):
            book.append(payload)
    assert len(book.read_records()) == 1
    digest = book.append(payload)
    assert len(book.read_records()) == 1 and book.read_records()[0]['record_hash'] == digest
    with open(book.csv_path, newline='') as stream:
        assert len(list(csv.DictReader(stream))) == 1


def test_ledger_preserves_legacy_bytes_and_appends_by_the_existing_header(tmp_path):
    book = ledger(tmp_path)
    historical = {'timestamp':'t0','symbol':'TOY','status':'OPEN','logged_utc':'2026-01-01T00:00:00+00:00','ledger_schema_version':'1.1.0'}
    historical['record_hash'] = hashlib.sha256(json.dumps(historical, sort_keys=True).encode()).hexdigest()
    Path(book.jsonl_path).write_text(json.dumps(historical)+'\n')
    header = ['symbol','status','timestamp','logged_utc','ledger_schema_version','record_hash']
    with open(book.csv_path,'w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=header);writer.writeheader();writer.writerow(historical)
    old_csv=Path(book.csv_path).read_bytes();old_jsonl=Path(book.jsonl_path).read_bytes()
    book.append({'timestamp':'t1','status':'CLOSED','symbol':'TOY','pnl':-3})
    assert Path(book.csv_path).read_bytes().startswith(old_csv)
    assert Path(book.jsonl_path).read_bytes().startswith(old_jsonl)
    with open(book.csv_path,newline='') as stream:
        rows=list(csv.DictReader(stream))
    assert rows[1]['symbol']=='TOY' and rows[1]['status']=='CLOSED' and None not in rows[1]
    assert book.read_records()[1]['pnl']==-3  # Legacy CSV omits that column, canonical JSONL retains it.


def test_ledger_nonfinite_or_tampered_records_fail_without_appending(tmp_path):
    book=ledger(tmp_path)
    with pytest.raises(ValueError):
        book.append({'pnl':float('nan')})
    assert not Path(book.csv_path).exists() and not Path(book.jsonl_path).exists()
    book.append({'symbol':'TOY','pnl':1})
    body=json.loads(Path(book.jsonl_path).read_text());body['pnl']=9
    Path(book.jsonl_path).write_text(json.dumps(body)+'\n')
    previous=Path(book.jsonl_path).read_bytes()
    with pytest.raises(ValueError,match='invalid trade ledger'):
        book.append({'symbol':'TOY','pnl':2})
    assert Path(book.jsonl_path).read_bytes()==previous


def test_verified_final_jsonl_record_without_newline_remains_appendable(tmp_path):
    book=ledger(tmp_path)
    first={'event_id':'one','symbol':'TOY','pnl':1}
    digest=book.append(first)
    original=Path(book.jsonl_path).read_bytes().rstrip(b'\r\n')
    Path(book.jsonl_path).write_bytes(original)
    assert book.append(first)==digest  # Retry itself leaves the verified prefix intact.
    assert Path(book.jsonl_path).read_bytes()==original
    book.append({'event_id':'two','symbol':'TOY','pnl':-2})
    assert Path(book.jsonl_path).read_bytes().startswith(original+b'\n')
    assert len(book.read_records())==2


def test_truncated_jsonl_tail_is_rejected_without_mutating_source_or_projection(tmp_path):
    book=ledger(tmp_path);book.append({'symbol':'TOY','pnl':1})
    Path(book.jsonl_path).write_bytes(Path(book.jsonl_path).read_bytes()+b'{"event_id":')
    source=Path(book.jsonl_path).read_bytes();projection=Path(book.csv_path).read_bytes()
    with pytest.raises(ValueError,match='invalid trade ledger'):
        book.append({'symbol':'TOY','pnl':2})
    assert Path(book.jsonl_path).read_bytes()==source and Path(book.csv_path).read_bytes()==projection


def test_partial_csv_row_with_a_hash_is_not_treated_as_complete(tmp_path):
    book=ledger(tmp_path);payload={'event_id':'one','symbol':'TOY','pnl':1};digest=book.append(payload)
    record=book.read_records()[0]
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=CSV_FIELDS)
    writer.writeheader();writer.writerow({**{key:record.get(key,'') for key in CSV_FIELDS},'record_json':''})
    partial=stream.getvalue().rstrip('\r\n').encode()
    Path(book.csv_path).write_bytes(partial)
    source=Path(book.jsonl_path).read_bytes()
    assert book.append(payload)==digest
    assert Path(book.jsonl_path).read_bytes()==source
    assert Path(book.csv_path).read_bytes().startswith(partial+b'\n')
    with open(book.csv_path,newline='') as fp:
        rows=list(csv.DictReader(fp))
    assert rows[-1]['record_hash']==digest and json.loads(rows[-1]['record_json'])==record
    size=Path(book.csv_path).stat().st_size
    assert book.append(payload)==digest and Path(book.csv_path).stat().st_size==size


def test_unclosed_csv_quotes_are_held_for_explicit_projection_reconstruction(tmp_path):
    book=ledger(tmp_path);payload={'symbol':'TOY','pnl':1};book.append(payload)
    data=Path(book.csv_path).read_bytes();header=data.splitlines(keepends=True)[0]
    partial=header+b'"unterminated'
    Path(book.csv_path).write_bytes(partial)
    source=Path(book.jsonl_path).read_bytes()
    with pytest.raises(ValueError,match='malformed quoted'):
        book.append(payload)
    assert Path(book.csv_path).read_bytes()==partial and Path(book.jsonl_path).read_bytes()==source


def test_nested_numeric_json_keys_are_rejected_before_any_ledger_write(tmp_path):
    book=ledger(tmp_path)
    with pytest.raises(ValueError,match='every depth'):
        book.append({'event_id':'a','by_day':{2:1,10:2}})
    with pytest.raises(ValueError,match='every depth'):
        book.append({'event_id':'b','observations':[{'bad':{1:True}}]})
    assert not Path(book.csv_path).exists() and not Path(book.jsonl_path).exists()
    assert not Path(book.jsonl_path+'.lock').exists()


def test_legacy_misaligned_csv_can_be_read_from_jsonl_and_recovered_append_only(tmp_path):
    book=ledger(tmp_path)
    opening={'timestamp':'t0','symbol':'TOY','status':'OPEN','qty':1}
    closing={'status':'CLOSED','timestamp':'t1','qty':1,'pnl':-2,'symbol':'TOY'}
    records=[]
    for payload in (opening,closing):
        record={**payload,'ledger_schema_version':'1.1.0','logged_utc':'2026-01-01T00:00:00+00:00'}
        record['record_hash']=hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest()
        records.append(record)
    Path(book.jsonl_path).write_text(''.join(json.dumps(record)+'\n' for record in records))
    with open(book.csv_path,'w',newline='') as stream:
        for i,record in enumerate(records):
            writer=csv.DictWriter(stream,fieldnames=list(record))
            if i==0:writer.writeheader()
            writer.writerow(record)  # Reproduce the former per-event-column-order defect.
    old_csv=Path(book.csv_path).read_bytes();old_jsonl=Path(book.jsonl_path).read_bytes()
    with open(book.csv_path,newline='') as stream:
        broken=list(csv.DictReader(stream))[1]
    assert broken['symbol']=='t1' and broken['status']=='1'
    assert book.read_records()[1]['symbol']=='TOY' and book.read_records()[1]['pnl']==-2
    assert book.append(closing)==records[1]['record_hash']
    assert Path(book.jsonl_path).read_bytes()==old_jsonl
    assert Path(book.csv_path).read_bytes().startswith(old_csv)
    with open(book.csv_path,newline='') as stream:
        repaired=list(csv.DictReader(stream))[-1]
    assert repaired['symbol']=='TOY' and repaired['status']=='CLOSED' and repaired['qty']=='1'
