from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest


CODE = Path(__file__).resolve().parents[1] / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

WORKERS = (
    "broadcaster",
    "spike_broadcaster",
    "_kraken_equity_sampler",
    "_profit_lock_watcher",
    "_autobuy_watcher",
    "_smart_scanner_watcher",
)


@pytest.fixture
def gateway_workers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    import luma_experience_gateway as gateway
    import luma_experience_gateway_legacy as legacy

    started = []
    stopped = []
    tasks = []
    dashboard = tmp_path / "dashboard"
    monkeypatch.setattr(legacy, "DASH", dashboard)

    def worker(name):
        async def run():
            assert dashboard.is_dir()
            started.append(name)
            tasks.append(asyncio.current_task())
            try:
                await asyncio.Event().wait()
            finally:
                # Shutdown must await cleanup, not merely request cancellation.
                await asyncio.sleep(0)
                stopped.append(name)

        return run

    for name in WORKERS:
        monkeypatch.setattr(legacy, name, worker(name))
    return gateway.app, dashboard, started, stopped, tasks


def _assert_stopped(started, stopped, tasks, cycles=1):
    assert sorted(started) == sorted(WORKERS * cycles)
    assert sorted(stopped) == sorted(started)
    assert len(tasks) == len(WORKERS) * cycles
    assert all(task.done() and task.cancelled() for task in tasks)


def test_lifespan_creates_dashboard_and_owns_workers_each_cycle(gateway_workers):
    app, dashboard, started, stopped, tasks = gateway_workers

    async def exercise():
        for cycle in range(2):
            async with app.router.lifespan_context(app):
                await asyncio.sleep(0)
                assert dashboard.is_dir()
                assert len(started) == len(WORKERS) * (cycle + 1)
                assert all(not task.done() for task in tasks[-len(WORKERS):])
            _assert_stopped(started, stopped, tasks, cycles=cycle + 1)

    asyncio.run(exercise())


def test_lifespan_cleans_up_workers_when_application_body_fails(gateway_workers):
    app, _, started, stopped, tasks = gateway_workers

    async def exercise():
        with pytest.raises(RuntimeError, match="application failure"):
            async with app.router.lifespan_context(app):
                await asyncio.sleep(0)
                raise RuntimeError("application failure")
        _assert_stopped(started, stopped, tasks)

    asyncio.run(exercise())


def test_lifespan_cancellation_awaits_worker_cleanup(gateway_workers):
    app, _, started, stopped, tasks = gateway_workers

    async def exercise():
        ready = asyncio.Event()

        async def serve():
            async with app.router.lifespan_context(app):
                await asyncio.sleep(0)
                ready.set()
                await asyncio.Event().wait()

        owner = asyncio.create_task(serve())
        await asyncio.wait_for(ready.wait(), timeout=1)
        owner.cancel()
        with pytest.raises(asyncio.CancelledError):
            await owner
        _assert_stopped(started, stopped, tasks)

    asyncio.run(exercise())


def test_lifespan_startup_failure_does_not_start_workers(gateway_workers):
    app, dashboard, started, stopped, tasks = gateway_workers
    dashboard.write_text("not a directory", encoding="utf-8")

    async def exercise():
        with pytest.raises(FileExistsError):
            async with app.router.lifespan_context(app):
                pytest.fail("startup must not succeed")
        assert started == stopped == tasks == []

    asyncio.run(exercise())
