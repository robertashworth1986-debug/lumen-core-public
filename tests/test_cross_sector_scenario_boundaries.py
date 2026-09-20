"""Synthetic boundary checks for the existing legacy scenario calculator."""
import importlib.util
import json
from pathlib import Path
import sys
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def scenario(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('cross_sector_scenario_test', ROOT / 'code/execution/cross_sector_intel_pipeline.py')
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    for name in ['OUT','CONFIG']:
        monkeypatch.setattr(module, name, tmp_path)
    for name in ['INFRA_DELTA_FILE','INFRA_AUDIT_FILE','FAILURE_PRED_FILE','GRANT_EVIDENCE_FILE',
                 'CHAIN_FILE','OPTIMIZATION_REPORT_JSON','OPTIMIZATION_MATRIX_CSV','OPTIMIZATION_REPORT_MD','RUNTIME_FILE']:
        monkeypatch.setattr(module, name, tmp_path / getattr(module, name).name)
    return module


def test_scenario_cannot_claim_audit_tier_or_key_presence(scenario):
    model = scenario.CrossSectorIntelPipeline({'trust_tier':'gov_audit_ready'})
    delta = scenario.sample_sector_deltas()[0]
    record = model.freeze_delta(delta, model.estimate_failure_cost(delta))
    assert record['trust_tier'] == 'MODELED_ONLY'
    assert record['key_present'] is None
    assert record['measured_savings_usd'] is None
    assert record['evidence_class'] == 'HARDCODED_SCENARIO'


def test_parameter_sweep_cannot_write_runtime_configuration(scenario):
    config = {'optimization_auto_apply':True,'sim_detection_efficiency_values':[0.5,0.9],
              'sim_mitigation_multiplier_values':[0.5,0.9]}
    scenario.RUNTIME_FILE.write_text('retain original config')
    report = scenario.run_optimization_simulations(config, scenario.sample_sector_deltas())
    assert scenario.RUNTIME_FILE.read_text() == 'retain original config'
    assert report['auto_applied'] is False
    assert report['promotion_allowed'] is False
    assert report['recommended'] is None


def test_sweep_is_a_formula_sensitivity_not_a_performance_experiment(scenario):
    config = {'sim_detection_efficiency_values':[0.5], 'sim_mitigation_multiplier_values':[0.8]}
    report = scenario.run_optimization_simulations(config, scenario.sample_sector_deltas())
    assert report['evidence_class'] == 'HARDCODED_SCENARIO'
    assert report['measured_effect'] is None
    assert report['model_maximum']['prevented_pct'] == pytest.approx(40.0)
    assert report['sims_run'] == 1


def test_zero_efficiency_is_not_replaced_with_a_default(scenario):
    model = scenario.CrossSectorIntelPipeline({'lumen_detection_efficiency':0.0,'mitigation_multiplier':0.8})
    assert model.estimate_failure_cost(scenario.sample_sector_deltas()[0])['avoided_cost_usd'] == 0


@pytest.mark.parametrize('value',[True,'0.5',None,float('nan'),float('inf'),-0.1,1.1,10**1000])
def test_invalid_assumed_efficiency_rejected(scenario,value):
    with pytest.raises(ValueError):
        scenario.CrossSectorIntelPipeline({'lumen_detection_efficiency':value})


@pytest.mark.parametrize('config',[
    {'sim_detection_efficiency_step':0},
    {'sim_detection_efficiency_step':5e-324},
    {'sim_detection_efficiency_values':[]},
    {'sim_detection_efficiency_values':[.5]*102},
    {'sim_detection_efficiency_values':[float('nan')]},
    {'sim_detection_efficiency_values':[True]},
    {'sim_detection_efficiency_min':.9,'sim_detection_efficiency_max':.1},
    {'max_optimization_sims':True},
    {'max_optimization_sims':5001},
    {'optimization_auto_apply':'false'},
])
def test_invalid_sweep_is_bounded_and_does_not_write(scenario,config,tmp_path):
    with pytest.raises(ValueError):
        scenario.run_pipeline(tmp_path/'new-report',runtime_cfg=config)
    assert not (tmp_path/'new-report').exists()


def test_case_budget_reports_truncation(scenario):
    result=scenario.run_optimization_simulations({'max_optimization_sims':2},scenario.sample_sector_deltas())
    assert result['sims_run']==2
    assert result['declared_grid_cases']==90
    assert result['sweep_truncated'] is True
    assert result['model_maximum'] in result['rows']


def test_duplicate_axis_values_do_not_add_cases(scenario):
    result=scenario.run_optimization_simulations({'sim_detection_efficiency_values':[.5,.5],
                                                  'sim_mitigation_multiplier_values':[.8]},scenario.sample_sector_deltas())
    assert result['sims_run']==1


def test_scenario_record_rejects_resealed_false_estimate(scenario):
    model=scenario.CrossSectorIntelPipeline({}); delta=scenario.sample_sector_deltas()[0]
    estimate=model.estimate_failure_cost(delta); estimate['avoided_cost_usd']=999
    with pytest.raises(ValueError,match='does not match'):
        model.freeze_delta(delta,estimate)


def test_existing_directory_and_implicit_run_are_rejected(scenario,tmp_path):
    marker=tmp_path/'marker'; marker.write_text('preserve')
    with pytest.raises(ValueError,match='explicit'):
        scenario.run_pipeline()
    with pytest.raises(ValueError,match='already exist'):
        scenario.run_pipeline(tmp_path)
    assert marker.read_text()=='preserve'


def test_report_preserves_legacy_outputs_and_runtime(scenario,tmp_path):
    import hashlib
    legacy=[scenario.RUNTIME_FILE,scenario.GRANT_EVIDENCE_FILE,scenario.INFRA_DELTA_FILE,scenario.INFRA_AUDIT_FILE]
    for path in legacy:
        path.write_text('preserve')
    target=tmp_path/'new-scenario'
    report=scenario.run_pipeline(target,runtime_cfg={'optimization_auto_apply':True})
    assert all(path.read_text()=='preserve' for path in legacy)
    assert report['auto_applied'] is False
    assert report['recommended'] is None
    assert report['measured_savings_usd'] is None
    assert {p.name for p in target.iterdir()}=={'scenario_report.json','scenario_matrix.csv','scenario_readme.md','SCENARIO_MANIFEST.json'}
    for row in json.loads((target/'SCENARIO_MANIFEST.json').read_text())['files']:
        raw=(target/row['path']).read_bytes()
        assert row['bytes']==len(raw) and row['sha256']==hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize('raw',['[]','{"x":1,"x":2}','{"x":NaN}','{"lumen_detection_efficiency":1e999}'])
def test_invalid_explicit_assumptions(scenario,tmp_path,raw):
    source=tmp_path/'assumptions.json'; source.write_text(raw)
    with pytest.raises(ValueError):
        scenario.load_runtime_cfg(source)


def test_legacy_launcher_requires_explicit_output(tmp_path):
    proc=subprocess.run([sys.executable,str(ROOT/'code/execution/run_cross_sector_intel.py')],
                        cwd=tmp_path,capture_output=True,timeout=10)
    assert proc.returncode==2
    assert b'--output-dir' in proc.stderr
    assert not list(tmp_path.iterdir())


def test_cli_smoke_is_modeled_only(tmp_path):
    target=tmp_path/'scenario'
    proc=subprocess.run([sys.executable,str(ROOT/'code/execution/run_cross_sector_intel.py'),
                         '--output-dir',str(target)],cwd=tmp_path,capture_output=True,timeout=10)
    assert proc.returncode==0,proc.stderr
    result=json.loads(proc.stdout)
    assert result['status']=='MODELED_ONLY'
    assert result['measured_savings_usd'] is None
    assert result['auto_applied'] is False
