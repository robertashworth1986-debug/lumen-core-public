import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "qmpl_sim.py"
spec = importlib.util.spec_from_file_location("qmpl_sim", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_quantization_wraps():
    import numpy as np
    values = np.array([-4.0, -3.0, 0.0, 3.0, 4.0])
    quantized = module.quantize_angle(values, 8)
    assert np.all(quantized <= np.pi + 1e-9)
    assert np.all(quantized >= -np.pi - 1e-9)


def test_phase_run_is_deterministic():
    spec = module.RunSpec(
        agent_count=8,
        coupling_gain=1.1,
        phase_bins=16,
        packet_loss=0.0,
        sensor_noise=0.0,
        latency_steps=0,
        frequency_spread=0.15,
        damping=0.9,
        inertia=1.0,
        seed=7,
        duration_s=8.0,
        dt_s=0.03,
        disturbance_time_s=4.0,
        disturbance_phase_rad=1.0,
    )
    a = module.simulate_phase_lock(spec)
    b = module.simulate_phase_lock(spec)
    assert a["final_coherence"] == b["final_coherence"]
    assert a["final_frequency_std"] == b["final_frequency_std"]


def test_formation_transition_returns_boundary():
    result = module.simulate_formation_transition(
        n=8, start_shape="line", end_shape="v", seed=3, duration_s=5.0
    )
    assert "not aerodynamic" in result["claim_boundary"].lower()
