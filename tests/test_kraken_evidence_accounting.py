import importlib.util
import json
import tempfile
from unittest.mock import patch
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('kraken_evidence',ROOT/'code/build_kraken_positive_proof.py')
proof=importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)

def reconciled(value=0):
    return {'mode':'live','realized_net_pnl':value,'quote_currency':'USD',
            'time_window':{'start_utc':'2026-04-01T00:00:00Z','end_utc':'2026-04-02T00:00:00Z'},
            'reconciliation':{'status':'MATCHED','fees_included':True,'cost_basis_complete':True,
                              'closed_trade_count':3,'fills_source':'venue-fills-export.csv'}}

def test_paper_result_cannot_become_realized_even_with_positive_pnl():
    for data,path in [({'total_net_pnl_pct':70},'institutional_crypto_paper_report.json'),
                      ({'mode':'paper','portfolio':{'return_pct':50}},'report.json'),
                      ({'mode':'live','paper_profit':250},'rolling_performance.json')]:
        result=proof.classify_outcome(data,path)
        assert result['status']=='PAPER_ONLY'
        assert result['rolling_performance_net_pnl'] is None

def test_reconciled_zero_and_loss_are_preserved_with_units():
    for value in [0,-2.58,3.25]:
        result=proof.classify_outcome(reconciled(value),'report.json')
        assert result['status']=='REPORTED_RECONCILED'
        assert result['rolling_performance_net_pnl']==value
        assert result['unit']=='USD'

def test_incomplete_accounting_is_unknown():
    mutations=[('mode','paper'),('quote_currency',''),('realized_net_pnl',float('nan')),
               ('realized_net_pnl',float('inf')),('realized_net_pnl',True),('time_window',{})]
    for field,value in mutations:
        data=reconciled(10);data[field]=value
        assert proof.classify_outcome(data,'report.json')['rolling_performance_net_pnl'] is None
    for field,value in [('fees_included',False),('cost_basis_complete',False),('fills_source',''),('closed_trade_count',0),('closed_trade_count',True)]:
        data=reconciled(10);data['reconciliation'][field]=value
        assert proof.classify_outcome(data,'report.json')['rolling_performance_net_pnl'] is None

def test_missing_sources_do_not_render_as_zero():
    with tempfile.TemporaryDirectory() as directory:
        tmp_path=Path(directory)
        path=tmp_path/'paper.json';path.write_text(json.dumps({'paper_profit':100}))
        with patch.object(proof,'REALIZED_OUTCOME_SOURCES',[path]), patch.object(proof,'OUTPUT_HTML',tmp_path/'proof.html'):
            outcome=proof.pick_realized_outcome()
            assert outcome['status']=='UNKNOWN'
            assert proof.format_pnl(outcome)=='Unknown / not reconciled'
            proof.write_html({'realized_outcome':outcome})
            assert 'Unknown / not reconciled' in (tmp_path/'proof.html').read_text()

def test_order_ids_are_deduplicated_and_not_claimed_as_fills():
    events=[{'txid':'O-ONE'},{'validation_result':{'txid':['O-ONE','O-TWO']}}]
    assert proof.extract_txids(events)==['O-ONE','O-TWO']
    payload=proof.build_payload()
    assert payload['kraken_execution_evidence']['txid_count']>=5
    assert payload['kraken_execution_evidence']['evidence_basis']=='first_party_order_records_not_reconciled_exchange_fills'
    assert payload['control_integrity']['statistical_confidence_0_100'] is None

def test_validate_only_label_with_live_payload_is_flagged():
    event={'mode':'VALIDATE_ONLY','payload':{'validate':'false'},'validation_result':{'txid':['O-ONE']}}
    assert len(proof.mode_conflicts([event]))==1
    event['payload']['validate']=True
    assert proof.mode_conflicts([event])==[]
