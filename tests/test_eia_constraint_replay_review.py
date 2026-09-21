from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('constraint_review', ROOT / 'code/ops/REPLAY_EIA_CONSTRAINT_REVIEW.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def rows():
    return [
        {'respondent': 'A', 'target_date': '2026-01-01', 'strategy': 'candidate', 'actual_mwh': 100., 'predicted_mwh': 105.},
        {'respondent': 'A', 'target_date': '2026-01-01', 'strategy': 'eia_day_ahead_forecast', 'actual_mwh': 100., 'predicted_mwh': 110.},
        {'respondent': 'B', 'target_date': '2026-01-01', 'strategy': 'candidate', 'actual_mwh': 200., 'predicted_mwh': 215.},
        {'respondent': 'B', 'target_date': '2026-01-01', 'strategy': 'eia_day_ahead_forecast', 'actual_mwh': 200., 'predicted_mwh': 210.},
    ]


def test_paired_metric_keeps_adverse_authority_and_native_denominator():
    result = module.paired_summary(rows(), 'candidate')
    assert result['paired_authority_days'] == 2
    assert result['relative_mae_reduction_pct'] == 0
    assert result['relative_p95_reduction_pct'] == -50
    assert result['scores']['candidate']['wape_pct'] == pytest.approx(100 * 20 / 300)


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'disagree', 'nonfinite'])
def test_paired_metrics_fail_closed_on_noncomparable_rows(mutation):
    value = rows()
    if mutation == 'missing':
        value.pop()
    elif mutation == 'duplicate':
        value.append(value[0].copy())
    elif mutation == 'disagree':
        value[0]['actual_mwh'] = 101
    else:
        value[0]['predicted_mwh'] = float('nan')
    with pytest.raises(ValueError):
        module.paired_summary(value, 'candidate')


def test_manifest_rejects_tampering_and_path_escape(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    receipt = tmp_path / 'receipt'
    receipt.mkdir()
    result = receipt / 'result.json'
    result.write_text('{}')
    item = {'sha256': module.digest(result), 'bytes': result.stat().st_size}
    manifest = {'inputs': {}, 'outputs': {'result.json': item}}
    (receipt / 'manifest.json').write_text(json.dumps(manifest))
    assert module.verify(receipt)['verified']
    result.write_text('{"faked": true}')
    with pytest.raises(ValueError, match='mismatch'):
        module.verify(receipt)
    manifest['outputs'] = {'../result.json': item}
    (receipt / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='leaves'):
        module.verify(receipt)
