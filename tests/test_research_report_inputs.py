"""Regression checks for the uploaded reporting defects; fixtures are synthetic."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1] / "code" / "research"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


io = load("research_artifact_io")
# Exact-file imports avoid the stdlib 'code' collision and perform no run IO.
sys.modules["research_artifact_io"] = io
overlay = load("run_quantum_overlay")
flow = load("flowform_investor")
geom = load("geom3d_extended")


def series(times=None, error=1, energy=None):
    times = range(16) if times is None else times
    return ("t,energy,stability,error\n" + "\n".join(
        f"{t},{np.sin(t) if energy is None else energy},0.5,{error}" for t in times)).encode()


def history(**changes):
    rows = [{"step": i, "Omega": 10-i, "S": .5, "E": 3, "C": 2} for i in range(3)]
    rows[1].update(changes)
    return json.dumps(rows).encode()


def test_overlay_repeats_exactly_without_random_baseline():
    raw = series()
    _, _, first = overlay.compare(raw, raw)
    _, _, second = overlay.compare(raw, raw)
    assert first == second
    assert first["candidate"]["integrated_error"] == 15
    assert first["candidate"]["sample_spacing"] == 1
    assert set(first["candidate_minus_baseline"].values()) == {0}


def test_worse_loss_stays_visible_and_zero_power_is_undefined():
    _, _, result = overlay.compare(series(error=2, energy=0), series(error=1, energy=0))
    assert result["candidate_minus_baseline"]["integrated_error"] == 15
    assert result["candidate"]["normalized_spectral_entropy"] is None
    assert result["candidate"]["spectral_peak_power_fraction"] is None


@pytest.mark.parametrize("raw", [series(range(7)), series([0, 1, 2, 4, 5, 6, 7, 8]),
    series([0, 1, 2, 2, 4, 5, 6, 7]), series(reversed(range(16))),
    series(error=-1), series(energy="nan"), series(energy="inf"),
    b"t,energy,stability,error,energy\n0,1,1,1,1\n"])
def test_overlay_rejects_invalid_input(raw):
    with pytest.raises(ValueError):
        overlay.load_series(raw)


def test_overlay_rejects_unpaired_times():
    with pytest.raises(ValueError, match="paired"):
        overlay.compare(series(), series(range(1, 17)))


def test_only_loaded_versions_are_named():
    assert flow.load_history(history())["S"].tolist() == [.5, .5, .5]
    title = flow.comparison_title(["V7"])
    assert "V7 only" in title and "V6" not in title and "V8" not in title
    assert "V6 vs V8" in flow.comparison_title(["V6", "V8"])


@pytest.mark.parametrize("raw", [history(step=0), history(E=None), history(C=True),
    history(Omega="NaN"), b"[]", b'{"step": [1,2]}',
    b'[{"step":0,"step":1}]'])
def test_hypercore_rejects_ambiguous_data(raw):
    with pytest.raises(ValueError):
        flow.load_history(raw)


def test_geometry_requires_real_input_or_explicit_illustration_mode(tmp_path):
    with pytest.raises(ValueError, match="choose"):
        geom.build_report(tmp_path / "none")
    assert not (tmp_path / "none").exists()
    data = geom.load_geometry(b"D0,D1,tau,score\n1,2,3,4\n")
    assert data["score"].tolist() == [4]
    x,y,z = geom.fibonacci_sphere(20)
    assert np.allclose(x*x+y*y+z*z, 1)


@pytest.mark.parametrize("raw", [b"D0,D1,tau\n1,2,3\n", b"D0,D1,tau,score\n1,2,3,nan\n",
                                  b"D0,D1,tau,score\n1,2,3,4,5\n"])
def test_geometry_rejects_missing_or_nonfinite_values(raw):
    with pytest.raises(ValueError):
        geom.load_geometry(raw)


def test_report_failure_does_not_publish_and_existing_output_is_preserved(tmp_path):
    out = tmp_path / "report"
    with pytest.raises(RuntimeError):
        with io.new_report(out) as stage:
            (stage / "partial").write_text("partial")
            raise RuntimeError("plot failed")
    assert not out.exists() and not list(tmp_path.iterdir())
    with io.new_report(out) as stage:
        io.write_manifest(stage, {"evidence_type":"synthetic fixture"}, {"input.csv": b"exact bytes"})
    report = json.loads((out / "manifest.json").read_text())
    assert report["files"]["input.csv"]["sha256"] == hashlib.sha256(b"exact bytes").hexdigest()
    with pytest.raises(FileExistsError):
        with io.new_report(out):
            pass
    assert (out / "input.csv").read_bytes() == b"exact bytes"
