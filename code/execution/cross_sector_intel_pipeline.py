"""Offline sensitivity calculator for three retained, hardcoded scenarios.

The legacy entry point is retained, but no scenario is promoted to a live
source, government-ready evidence, measured savings, or runtime configuration.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
CONFIG = ROOT / "config"
# Legacy paths are retained as explicit compatibility markers, never written.
INFRA_DELTA_FILE = OUT / "infra_frozen_deltas.jsonl"
INFRA_AUDIT_FILE = OUT / "infra_audit_ledger.jsonl"
FAILURE_PRED_FILE = OUT / "cross_sector_failure_predictions.jsonl"
GRANT_EVIDENCE_FILE = OUT / "investor_and_grant_evidence.json"
CHAIN_FILE = OUT / "infra_chain_of_custody_sha256.json"
OPTIMIZATION_REPORT_JSON = OUT / "cross_sector_optimization_report.json"
OPTIMIZATION_MATRIX_CSV = OUT / "cross_sector_optimization_matrix.csv"
OPTIMIZATION_REPORT_MD = OUT / "cross_sector_optimization_report.md"
RUNTIME_FILE = CONFIG / "cross_sector_intel_runtime.json"
MAX_AXIS_VALUES = 101
MAX_CASES = 5000
BOUNDARY = ("Hardcoded scenario and formula sensitivity only. No source feed is fetched, "
            "no detection or mitigation is measured, and no failure forecast, realized "
            "savings, buyer ROI, government readiness, independent validation, valuation "
            "or operating recommendation is established. Repeated runs are not new evidence.")


def _number(value: Any, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    try:
        value = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{label} is out of range") from exc
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{label} is out of range")
    return value


def _fraction(config: dict, name: str, default: float) -> float:
    return _number(config.get(name, default), name, 0, 1)


def _config(value: Any) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Scenario assumptions must be an object")
    result = dict(value)
    if 'optimization_auto_apply' in result and type(result['optimization_auto_apply']) is not bool:
        raise ValueError("optimization_auto_apply must be a boolean; application is always disabled")
    budget = result.get('max_optimization_sims', 120)
    if type(budget) is not int or not 1 <= budget <= MAX_CASES:
        raise ValueError("max_optimization_sims must be an integer from 1 to 5000")
    _fraction(result, 'lumen_detection_efficiency', .72)
    _fraction(result, 'mitigation_multiplier', .86)
    return result


def _build_axis(config: dict, prefix: str, low: float, high: float, step: float) -> list[float]:
    key = prefix + '_values'
    if key in config:
        values = config[key]
        if not isinstance(values, list) or not 1 <= len(values) <= MAX_AXIS_VALUES:
            raise ValueError(f"{key} must contain 1 to {MAX_AXIS_VALUES} values")
        return sorted({_number(v, key, 0, 1) for v in values})
    low = _number(config.get(prefix+'_min', low), prefix+'_min', 0, 1)
    high = _number(config.get(prefix+'_max', high), prefix+'_max', 0, 1)
    step = _number(config.get(prefix+'_step', step), prefix+'_step', 0, 1)
    if high < low or step <= 0:
        raise ValueError("Scenario axis requires min <= max and a positive step")
    ratio = (high-low)/step
    if not math.isfinite(ratio) or ratio >= MAX_AXIS_VALUES:
        raise ValueError("Scenario axis exceeds value limit")
    count = math.floor(ratio + 1e-9)+1
    if count > MAX_AXIS_VALUES:
        raise ValueError("Scenario axis exceeds value limit")
    return sorted({min(high,low+i*step) for i in range(count)})


@dataclass
class SectorDelta:
    sector: str
    stream: str
    constraint: str
    observed_drift_score: float
    incident_rate_pct: float
    affected_asset_value_usd: float
    baseline_failure_cost_usd_per_hour: float
    estimated_detection_lag_hours: float
    confidence: float


def _validate_delta(delta: SectorDelta) -> None:
    if not isinstance(delta, SectorDelta):
        raise ValueError("Scenario row must be a SectorDelta")
    for field in ['sector', 'stream', 'constraint']:
        value = getattr(delta, field)
        if not isinstance(value, str) or not value.strip() or len(value) > 120:
            raise ValueError(f"Invalid scenario label: {field}")
    for field, maximum in [('observed_drift_score',1),('incident_rate_pct',100),
                           ('affected_asset_value_usd',1e18),('baseline_failure_cost_usd_per_hour',1e15),
                           ('estimated_detection_lag_hours',8760),('confidence',1)]:
        _number(getattr(delta,field),field,0,maximum)


class CrossSectorIntelPipeline:
    def __init__(self, runtime_cfg: dict) -> None:
        self.runtime_cfg = _config(runtime_cfg)

    def estimate_failure_cost(self, delta: SectorDelta) -> dict[str,float]:
        """Retain the legacy hypothetical formula; this is not a measured model."""
        _validate_delta(delta)
        drift_multiplier = max(.25, min(3.5, 1.0+delta.observed_drift_score))
        confidence_multiplier = max(.35, min(1.0, delta.confidence))
        hourly = delta.baseline_failure_cost_usd_per_hour*drift_multiplier*confidence_multiplier
        projected = hourly*max(.05, delta.estimated_detection_lag_hours)
        detection = _fraction(self.runtime_cfg,'lumen_detection_efficiency',.72)
        mitigation = _fraction(self.runtime_cfg,'mitigation_multiplier',.86)
        avoided = projected*detection*mitigation
        return {'projected_failure_cost_usd':round(projected,2), 'avoided_cost_usd':round(avoided,2),
                'residual_cost_usd':round(projected-avoided,2),'hourly_failure_cost_usd':round(hourly,2)}

    def freeze_delta(self, delta: SectorDelta, estimate: dict[str,float]) -> dict:
        """Compatibility name: returns a scenario record; does not freeze or append."""
        _validate_delta(delta)
        expected = self.estimate_failure_cost(delta)
        if estimate != expected:
            raise ValueError("Scenario estimate does not match the declared assumptions")
        return {'evidence_class':'HARDCODED_SCENARIO','source':'NO_SOURCE_FETCHED',
                'scenario_label':delta.stream,'sector':delta.sector,'constraint':delta.constraint,
                'trust_tier':'MODELED_ONLY','key_present':None,'rows_written':0,
                'measured_savings_usd':None,'predicted_failure_utc':None,
                'promotion_allowed':False,'modeled_costs_usd':expected,'claim_boundary':BOUNDARY}


def sample_sector_deltas() -> list[SectorDelta]:
    # Original labels and values are retained for lineage, not source identity.
    return [
        SectorDelta('energy_grid','ISO_NE','frequency_stability',.58,3.2,3_200_000_000.,1_150_000.,2.4,.88),
        SectorDelta('healthcare_supply_chain','HHS_FEED','cold_chain_compliance',.41,2.1,1_850_000_000.,620_000.,3.1,.82),
        SectorDelta('financial_market_infra','FEDWIRE_OPS','settlement_window_integrity',.67,4.6,6_100_000_000.,2_400_000.,1.7,.91),
    ]


def run_optimization_simulations(runtime_cfg: dict, deltas: list[SectorDelta]) -> dict:
    """Pure bounded formula sweep; never applies assumptions or writes files."""
    config = _config(runtime_cfg)
    if not isinstance(deltas,list) or not 1 <= len(deltas) <= 100:
        raise ValueError("Expected 1 to 100 scenario rows")
    for delta in deltas:
        _validate_delta(delta)
    detections = _build_axis(config,'sim_detection_efficiency',.55,.95,.05)
    mitigations = _build_axis(config,'sim_mitigation_multiplier',.60,.98,.04)
    budget = config.get('max_optimization_sims',120)
    rows = []
    for detection in detections:
        for mitigation in mitigations:
            if len(rows) == budget:
                break
            model = CrossSectorIntelPipeline({**config,'lumen_detection_efficiency':detection,'mitigation_multiplier':mitigation})
            estimates = [model.estimate_failure_cost(delta) for delta in deltas]
            projected = math.fsum(e['projected_failure_cost_usd'] for e in estimates)
            avoided = math.fsum(e['avoided_cost_usd'] for e in estimates)
            residual = math.fsum(e['residual_cost_usd'] for e in estimates)
            rows.append({'lumen_detection_efficiency':detection,'mitigation_multiplier':mitigation,
                         'projected_failure_cost_usd':round(projected,2),'avoided_cost_usd':round(avoided,2),
                         'residual_cost_usd':round(residual,2),
                         'prevented_pct':round(100*avoided/projected,4) if projected else None,
                         'efficiency_score':round(avoided-.05*residual,4)})
        if len(rows) == budget:
            break
    ranked = sorted(rows,key=lambda row:(row['efficiency_score'],row['avoided_cost_usd']),reverse=True)
    return {'schema':'lumencore.cross_sector_scenario_sensitivity.v2',
            'evidence_class':'HARDCODED_SCENARIO','trust_tier':'MODELED_ONLY',
            'sims_run':len(rows),'max_sims_budget':budget,
            'declared_grid_cases':len(detections)*len(mitigations),
            'sweep_truncated':len(rows)<len(detections)*len(mitigations),
            'recommended':None,'model_maximum':ranked[0],'top_5':ranked[:5],'rows':ranked,
            'measured_effect':None,'measured_savings_usd':None,'model_validated':False,
            'promotion_allowed':False,'auto_apply_requested':config.get('optimization_auto_apply',False),
            'auto_applied':False,'claim_boundary':BOUNDARY,
            'interpretation':'Larger assumed detection and mitigation mechanically improve this formula. The highest evaluated case is not learned performance or an operating recommendation.'}


def _unique_members(pairs):
    result = {}
    for key,value in pairs:
        if key in result:
            raise ValueError('Duplicate scenario JSON member')
        result[key] = value
    return result


def load_runtime_cfg(path: Path | None = None) -> dict:
    """Optional explicit scenario input; never reads or updates runtime defaults."""
    if path is None:
        return {}
    with Path(path).open('rb') as handle:
        raw = handle.read(65537)
    if len(raw)>65536:
        raise ValueError('Scenario assumptions exceed 64 KiB')
    try:
        value = json.loads(raw.decode('utf-8-sig'),object_pairs_hook=_unique_members,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite JSON number')))
    except (UnicodeError,RecursionError) as exc:
        raise ValueError('Invalid scenario JSON encoding or nesting') from exc
    return _config(value)


def run_pipeline(output_dir: Path | None = None, *, runtime_cfg: dict | None = None) -> dict:
    """Write a new, explicitly selected scenario directory; preserve all old outputs."""
    if output_dir is None:
        raise ValueError('An explicit new scenario output directory is required')
    target = Path(output_dir)
    if target.exists() or target.is_symlink():
        raise ValueError('Scenario output directory must not already exist')
    config = _config({} if runtime_cfg is None else runtime_cfg)
    deltas = sample_sector_deltas()
    report = run_optimization_simulations(config,deltas)
    model = CrossSectorIntelPipeline(config)
    report['declared_assumptions'] = config
    report['scenario_inputs'] = [asdict(delta) for delta in deltas]
    report['base_scenario_records'] = [model.freeze_delta(delta,model.estimate_failure_cost(delta)) for delta in deltas]
    report['generated_utc'] = datetime.now(timezone.utc).isoformat()
    # Validate serialization before creating any output. No source acquisition,
    # shared ledger append, investor report or runtime configuration write occurs.
    raw = (json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    target.mkdir(parents=True,exist_ok=False)
    (target/'scenario_report.json').write_bytes(raw)
    with (target/'scenario_matrix.csv').open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(report['rows'][0]))
        writer.writeheader(); writer.writerows(report['rows'])
    text = '# Cross-sector scenario sensitivity\n\n'+BOUNDARY+'\n\n'+report['interpretation']+'\n\n'
    text += f"Evaluated formula cases: {report['sims_run']} of {report['declared_grid_cases']}; truncated: {report['sweep_truncated']}.\n\n"
    text += ('The ISO_NE, HHS_FEED and FEDWIRE_OPS labels are retained historical scenario names; no such feed was accessed. '
             'The legacy cost formula, including its drift/confidence/lag clamps, is hypothetical. Dollar fields are modeled arithmetic, not economic evidence.\n\n'
             'No operating parameters were applied. The three base records use the declared assumptions, separately from the sensitivity sweep.\n')
    (target/'scenario_readme.md').write_text(text,encoding='utf-8')
    files=[]
    for name in ['scenario_report.json','scenario_matrix.csv','scenario_readme.md']:
        data=(target/name).read_bytes()
        files.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    (target/'SCENARIO_MANIFEST.json').write_text(json.dumps({'files':files,'claim_boundary':'File custody only; '+BOUNDARY},indent=2)+'\n',encoding='utf-8')
    return report


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True,help='New directory for hypothetical scenario outputs')
    parser.add_argument('--assumptions',type=Path,help='Optional bounded JSON assumptions; runtime defaults are not read')
    args=parser.parse_args(argv)
    try:
        report=run_pipeline(args.output_dir,runtime_cfg=load_runtime_cfg(args.assumptions))
    except (OSError,ValueError) as exc:
        parser.exit(2,f'Scenario held: {exc}\n')
    print(json.dumps({'status':'MODELED_ONLY','formula_cases':report['sims_run'],
                      'measured_savings_usd':None,'auto_applied':False,'output_dir':str(args.output_dir)},indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
