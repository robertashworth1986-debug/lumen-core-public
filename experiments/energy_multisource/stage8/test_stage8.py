"""Adversarial contracts with synthetic fixtures; not added field evidence."""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_stage8 as run
import verify_stage8 as verify


@pytest.mark.parametrize("times", [[1, 1], [2, 1], []])
def test_reject_bad_timestamps(times):
    with pytest.raises(ValueError):
        run.regularize(times, [1.] * len(times), 60)


def test_closed_bucket_no_future_fill():
    t, x, q = run.regularize([0, 1, 60, 181], [2., 4., 8., 10.], 60)
    assert t.tolist() == [0, 60, 120, 180, 240]
    assert x[:2].tolist() == [2., 6.]
    assert np.isnan(x[2:4]).all() and x[4] == 10.


@pytest.mark.parametrize("text", ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'])
def test_strict_json(tmp_path, text):
    p = tmp_path / "bad.json"; p.write_text(text)
    with pytest.raises(ValueError):
        run.strict_json(p)


def test_oversized_json_must_be_sharded(tmp_path):
    p = tmp_path / "oversized.json"
    with pytest.raises(ValueError, match="shard"):
        run.write_json(p, {"value": "x" * (2 * 1024 * 1024)})
    assert not p.exists()


@pytest.mark.parametrize("scenario", run.strict_json(run.PROTOCOL)["scenarios"])
def test_stress_is_deterministic_and_truth_immutable(scenario):
    x = np.arange(300, dtype=float); original = x.copy()
    a, delay = run.corrupt(x, 100, scenario, 20.)
    b, second_delay = run.corrupt(x, 100, scenario, 20.)
    assert np.array_equal(a, b, equal_nan=True) and delay == second_delay
    assert np.array_equal(x, original) and np.array_equal(a[:100], x[:100])


@pytest.mark.parametrize("delay", [0, 1, 3, 12])
@pytest.mark.parametrize("horizon", [1, 3, 7])
def test_no_future_information_and_scalar_agreement(delay, horizon):
    x = np.arange(100, dtype=float); x[10:12] = np.nan; x[26] = -20.
    issue = np.array([20, 30, 45])
    p, _ = run.predict(x, issue, horizon, 24, delay, 10.)
    for i, at in enumerate(issue):
        mutated = x.copy(); mutated[at-delay+1:] = 1e9
        altered, _ = run.predict(mutated, np.array([at]), horizon, 24, delay, 10.)
        assert np.array_equal(p[i], altered[0], equal_nan=True)
        reference = verify.scalar_prediction(x, int(at), horizon, 24, delay, 10.)
        assert np.allclose(p[i], [np.nan if v is None else v for v in reference], equal_nan=True)


def test_freshness_and_outage_seasonal_memory():
    x = np.ones(100); x[50:] = np.nan
    issue = np.arange(54, 90)
    p, _ = run.predict(x, issue, 1, 24, 0, 0.)
    assert np.isnan(p[:, [0, 2, 3, 4]]).all()
    assert np.isfinite(p[:19, 1]).all() and np.isnan(p[19:, 1]).all()


def fixture_score(truth, p):
    protocol = run.strict_json(run.PROTOCOL)
    masks = {"all": np.ones(len(truth), dtype=bool)}
    return run.score(truth, p, masks, {}, protocol), protocol


def test_zero_denominator_is_hold():
    truth = np.ones(200); p = np.ones((200, 5))
    rows, protocol = fixture_score(truth, p)
    assert all(r["status"] == "HOLD_ZERO_BASELINE_ERROR" for r in rows)
    assert all(r["mae_improvement_pct"] is None for r in rows)
    for r in rows:
        verify.verify_metrics(r, truth, p, np.ones(200, bool), protocol)


def test_missing_truth_paired_coverage_and_negative_retention():
    truth = np.ones(200); truth[:10] = np.nan
    p = np.ones((200, 5)); p[:, :2] = 2.; p[:, 2:] = 4.; p[10:20, 2] = np.nan
    rows, protocol = fixture_score(truth, p)
    assert rows[0]["truth_count"] == 190 and rows[0]["pairs"] == 180
    assert rows[0]["status"] == "REJECT_MAE_REGRESSION"
    for r in rows:
        verify.verify_metrics(r, truth, p, np.ones(200, bool), protocol)


def test_abstention_cannot_manufacture_screen_pass():
    truth = np.ones(200); p = np.ones((200, 5)); p[:, :2] = 2.; p[:180, 2:] = np.nan
    rows, protocol = fixture_score(truth, p)
    assert all(r["status"] == "HOLD_INSUFFICIENT_SUPPORT" for r in rows)


@pytest.mark.parametrize("tamper", ["changed", "missing", "extra", "wrong_pin", "duplicate_key"])
def test_manifest_tamper_rejection(tmp_path, tamper):
    p = tmp_path / "x.txt"; p.write_text("frozen")
    run.write_json(tmp_path / "MANIFEST.json", {"schema": "lumencore.frozen_delta.manifest.v1", "files": {"x.txt": run.sha(p)}})
    digest = run.sha(tmp_path / "MANIFEST.json")
    verify.check_manifest(tmp_path, digest)
    if tamper == "changed": p.write_text("edited")
    elif tamper == "missing": p.unlink()
    elif tamper == "extra": (tmp_path / "extra.txt").write_text("extra")
    elif tamper == "wrong_pin": digest = "0" * 64
    else:
        (tmp_path / "MANIFEST.json").write_text('{"files":{},"files":{}}')
        digest = run.sha(tmp_path / "MANIFEST.json")
    with pytest.raises(ValueError): verify.check_manifest(tmp_path, digest)


@pytest.mark.parametrize("field", ["pairs", "candidate_mae", "candidate_p95", "status", "positive_quartiles"])
def test_independent_recompute_catches_metric_tampering(field):
    truth = np.ones(200); p = np.ones((200, 5)); p[:, :2] = 2.
    rows, protocol = fixture_score(truth, p)
    row = rows[0]
    row[field] = "PROMOTED" if field == "status" else row[field] + 1
    with pytest.raises(ValueError):
        verify.verify_metrics(row, truth, p, np.ones(200, bool), protocol)
