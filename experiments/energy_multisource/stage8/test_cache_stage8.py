"""Check the I/O cache without changing the frozen scientific test artifact."""
import importlib.util
from pathlib import Path
import sys
from unittest import mock

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_stage8_cached as cache


def test_cache_preserves_arrays_and_decodes_once(tmp_path):
    p = tmp_path / "data.npz"
    np.savez_compressed(p, values=np.array([1., np.nan, -2.]), timestamps=np.array([1, 2, 3]))
    with np.load(p, allow_pickle=False) as original:
        expected = {key: original[key] for key in original.files}
    with cache.CachedNPZ(np.load(p, allow_pickle=False)) as actual:
        assert set(actual.files) == set(expected)
        for key in expected:
            assert np.array_equal(actual[key], expected[key], equal_nan=True)
            assert actual[key] is actual[key]
    assert actual.arrays == {}


def test_cache_restores_loader_after_rejection():
    original = np.load
    with mock.patch.object(cache.frozen, "verify", side_effect=ValueError("rejected")):
        with pytest.raises(ValueError, match="rejected"):
            cache.verify(Path("unused"), Path("unused"), "0" * 64)
    assert np.load is original


def test_object_arrays_still_refused(tmp_path):
    p = tmp_path / "objects.npz"
    np.savez(p, payload=np.array([{}], dtype=object))
    with pytest.raises(ValueError, match="Object arrays"):
        cache.CachedNPZ(np.load(p, allow_pickle=False))
