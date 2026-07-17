from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "RUN_REPOSITORY_TEST_SHARDS.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_repository_test_shards", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_plan_covers_each_test_file_once_and_is_stable():
    module = load_module()
    first = module.build_plan()
    second = module.build_plan()
    discovered = module.discover_test_paths()
    planned = [path for shard in first["shards"] for path in shard["files"]]

    assert first == second
    assert sorted(planned) == discovered
    assert len(planned) == len(set(planned)) == first["test_file_count"]
    assert len(first["plan_sha256"]) == 64


def test_full_universe_replay_isolated_from_balanced_shards():
    module = load_module()
    plan = module.build_plan()
    isolated = [
        shard for shard in plan["shards"] if shard["kind"] == "isolated_full_universe"
    ]
    fast = [shard for shard in plan["shards"] if shard["kind"] == "balanced_fast"]

    assert len(isolated) == 1
    assert isolated[0]["files"] == [
        "tests/test_locked_source_baseline_replay_sweep.py"
    ]
    assert all(
        "tests/test_locked_source_baseline_replay_sweep.py" not in shard["files"]
        for shard in fast
    )
    assert max(shard["file_count"] for shard in fast) - min(
        shard["file_count"] for shard in fast
    ) <= 1


def test_build_shards_rejects_duplicates_and_invalid_count():
    module = load_module()

    with pytest.raises(ValueError, match="unique"):
        module.build_shards(["tests/test_a.py", "tests/test_a.py"])
    with pytest.raises(ValueError, match="at least 1"):
        module.build_shards(["tests/test_a.py"], fast_shard_count=0)


def test_pytest_command_is_explicit_and_uses_current_runtime():
    module = load_module()
    shard = {
        "files": ["tests/test_alpha.py", "tests/test_beta.py"],
    }
    command = module.pytest_command(shard)

    assert command[:3] == [sys.executable, "-m", "pytest"]
    assert command[3:5] == shard["files"]
    assert command[-3:] == ["-q", "--tb=short", "--durations=10"]
