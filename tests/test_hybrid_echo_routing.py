from code.hybrid_echo_routing import Candidate, aggregate, evolve


def test_reproducible():
    assert evolve(seed=77, generations=3, population=10) == evolve(seed=77, generations=3, population=10)


def test_manifest_and_lineage():
    out = evolve(seed=91, generations=4, population=12)
    assert len(out["lineage"]) == 5
    assert len(out["manifest_sha256"]) == 64
    assert out["run_type"] == "synthetic"


def test_baseline_is_finite():
    metrics = aggregate(Candidate("straight", 0, 0, 0, 0), [1, 2, 3])
    assert 0 <= metrics.transmission_efficiency <= 1
    assert metrics.score == metrics.score
